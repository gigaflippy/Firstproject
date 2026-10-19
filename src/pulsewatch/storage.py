"""SQLite-backed result storage."""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pulsewatch.probe import ProbeResult

_SCHEMA = """
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target TEXT NOT NULL,
    region TEXT NOT NULL,
    ts TEXT NOT NULL,
    up INTEGER NOT NULL,
    status_code INTEGER,
    latency_ms REAL,
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_results_target_ts ON results (target, ts);
"""


@dataclass(frozen=True)
class TargetStats:
    target: str
    window_seconds: int
    checks: int
    uptime_percent: float | None
    latency_p50_ms: float | None
    latency_p95_ms: float | None
    last: ProbeResult | None


def _percentile(sorted_values: list[float], pct: float) -> float | None:
    """Nearest-rank percentile on an already sorted list."""
    if not sorted_values:
        return None
    rank = max(1, round(pct / 100 * len(sorted_values)))
    return sorted_values[min(rank, len(sorted_values)) - 1]


def _row_to_result(row: sqlite3.Row) -> ProbeResult:
    return ProbeResult(
        target=row["target"],
        region=row["region"],
        timestamp=datetime.fromisoformat(row["ts"]),
        up=bool(row["up"]),
        status_code=row["status_code"],
        latency_ms=row["latency_ms"],
        error=row["error"],
    )


class Storage:
    def __init__(self, path: Path | str) -> None:
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def add(self, r: ProbeResult) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO results (target, region, ts, up, status_code, latency_ms, error) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    r.target,
                    r.region,
                    r.timestamp.astimezone(UTC).isoformat(),
                    int(r.up),
                    r.status_code,
                    r.latency_ms,
                    r.error,
                ),
            )
            self._conn.commit()

    def recent(self, target: str, limit: int = 50) -> list[ProbeResult]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM results WHERE target = ? ORDER BY ts DESC, id DESC LIMIT ?",
                (target, limit),
            ).fetchall()
        return [_row_to_result(r) for r in rows]

    def stats(self, target: str, window: timedelta, now: datetime | None = None) -> TargetStats:
        now = now or datetime.now(UTC)
        since = (now - window).astimezone(UTC).isoformat()
        with self._lock:
            rows = self._conn.execute(
                "SELECT up, latency_ms FROM results WHERE target = ? AND ts >= ?",
                (target, since),
            ).fetchall()
        last = self.recent(target, limit=1)
        checks = len(rows)
        ups = sum(r["up"] for r in rows)
        latencies = sorted(r["latency_ms"] for r in rows if r["latency_ms"] is not None)
        return TargetStats(
            target=target,
            window_seconds=int(window.total_seconds()),
            checks=checks,
            uptime_percent=round(100 * ups / checks, 3) if checks else None,
            latency_p50_ms=_percentile(latencies, 50),
            latency_p95_ms=_percentile(latencies, 95),
            last=last[0] if last else None,
        )

    def prune(self, older_than: timedelta, now: datetime | None = None) -> int:
        now = now or datetime.now(UTC)
        cutoff = (now - older_than).astimezone(UTC).isoformat()
        with self._lock:
            cur = self._conn.execute("DELETE FROM results WHERE ts < ?", (cutoff,))
            self._conn.commit()
            return cur.rowcount
