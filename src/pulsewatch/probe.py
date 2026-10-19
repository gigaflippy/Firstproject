"""HTTP probing."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from pulsewatch.config import Target


@dataclass(frozen=True)
class ProbeResult:
    target: str
    region: str
    timestamp: datetime
    up: bool
    status_code: int | None
    latency_ms: float | None
    error: str | None


async def probe(client: httpx.AsyncClient, target: Target, region: str) -> ProbeResult:
    """Probe one target once. Never raises; failures become a down result."""
    started = time.perf_counter()
    ts = datetime.now(UTC)
    try:
        resp = await client.request(
            target.method,
            str(target.url),
            timeout=target.timeout_seconds,
            follow_redirects=True,
        )
    except httpx.TimeoutException:
        return ProbeResult(target.name, region, ts, False, None, None, "timeout")
    except httpx.HTTPError as exc:
        return ProbeResult(target.name, region, ts, False, None, None, type(exc).__name__)

    latency_ms = (time.perf_counter() - started) * 1000
    up = resp.status_code in target.expected_status
    error = None if up else f"unexpected status {resp.status_code}"
    return ProbeResult(target.name, region, ts, up, resp.status_code, latency_ms, error)
