# Pulsewatch

Distributed uptime and latency monitor. Probes HTTP endpoints on a schedule, stores results, serves uptime/latency stats over a REST API, and exposes Prometheus metrics. It is built to run entirely on local infrastructure (Docker, local Kubernetes) at zero cost.

> Status: **v0.1, the core service.** Each probe instance carries a `region` label so several instances can feed one Prometheus. Multi-region agents, Kubernetes manifests, Terraform and ArgoCD are on the [roadmap](#roadmap).

## Quick start

```bash
cp targets.example.yaml targets.yaml   # edit to taste
docker compose up --build
```

- API: http://localhost:8000/docs
- Metrics: http://localhost:8000/metrics
- Prometheus: http://localhost:9090 (try `pulsewatch_up` or `pulsewatch:latency_p95_seconds`)

Without Docker:

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
cp targets.example.yaml targets.yaml
pulsewatch
```

## Configuration

Targets live in a YAML file:

```yaml
targets:
  - name: my-api                # unique, [a-zA-Z0-9_.-]
    url: https://api.example.com/health
    interval_seconds: 30        # >= 1
    timeout_seconds: 5
    method: GET                 # GET or HEAD
    expected_status: [200]      # anything else counts as down
```

Runtime settings come from environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `PULSEWATCH_TARGETS_FILE` | `targets.yaml` | Path to the targets file |
| `PULSEWATCH_DB_PATH` | `pulsewatch.db` | SQLite database path |
| `PULSEWATCH_REGION` | `local` | Region label attached to every result and metric |
| `PULSEWATCH_RETENTION_HOURS` | `72` | Results older than this are pruned hourly |
| `PULSEWATCH_HOST` / `PULSEWATCH_PORT` | `0.0.0.0` / `8000` | Bind address |
| `PULSEWATCH_SCHEDULER_ENABLED` | `true` | Set `false` to serve the API without probing |

## API

| Method | Path | Description |
|---|---|---|
| GET | `/healthz` | Liveness, with region and version |
| GET | `/targets` | Configured targets |
| GET | `/status?window=3600` | Per-target uptime %, p50/p95 latency and last result over the window (60s to 7d) |
| GET | `/targets/{name}/results?limit=50` | Most recent raw results |
| POST | `/targets/{name}/check` | Run one probe now |
| GET | `/metrics` | Prometheus exposition |

## Metrics

| Metric | Type | Labels |
|---|---|---|
| `pulsewatch_up` | gauge | `target`, `region` |
| `pulsewatch_probe_latency_seconds` | histogram | `target`, `region` |
| `pulsewatch_probes_total` | counter | `target`, `region`, `result` (`up`/`down`) |

`deploy/prometheus/` includes recording rules for 1h uptime ratio and p95 latency, plus a `TargetDown` alert (down for 2 minutes).

## Design

```
targets.yaml ─► Scheduler ──(one asyncio loop per target, jittered start)──► probe()
                    │                                                         │
                    │                                         ProbeResult (up, status, latency, error)
                    ▼                                                         │
               Storage (SQLite) ◄───────────────────────┬────────────────────┘
                    │                                    ▼
             FastAPI /status, /results          Metrics ─► /metrics ─► Prometheus
```

- Probes never raise: timeouts and connection errors become `up=false` results with an `error` string.
- Latency is measured only for responses that came back; failed connections record no latency, so failures don't skew the percentiles.
- SQLite keeps v0.1 dependency-free. The `Storage` class is the seam for swapping in Postgres later.

## Development

```bash
pip install -e '.[dev]'
ruff check . && ruff format --check .
pytest
```

CI (GitHub Actions) runs lint, tests on Python 3.11 to 3.13, and a Docker build on every push and PR.

## Roadmap

1. **v0.1:** core probe service, REST API, Prometheus metrics, Docker, CI *(this)*
2. Grafana dashboard provisioned in compose
3. Kubernetes manifests and Helm chart, running on kind/k3d
4. Multi-region: probe agents in separate namespaces/clusters with distinct `region` labels, one Prometheus scraping all of them
5. Terraform for the local platform (kind cluster, namespaces, monitoring stack)
6. ArgoCD GitOps deploys
7. Alert routing (Alertmanager to Telegram or email)
