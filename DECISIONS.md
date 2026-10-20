# Decisions

Open questions from nightly runs. Answer under **Georgi's answer** (one line is enough) and the next run acts on it first.

---

## D-001 — What should nightly runs work on? (opened 2026-10-19)

**Status:** resolved — Pulsewatch v0.1 core built on `nightly/2026-10-19-pulsewatch-core`

**Context.** The nightly task is pointed at `gigaflippy/Firstproject`. That repo currently holds only `HELLO.md` (the push test from 2026-10-19). There is no code, no tests, no `main` branch (the default branch is `claude/hello-test`), and no description of what it is for. None of the side projects you've been working on (Pulsewatch, CharmMatch, Хранко, Огледалото, Canary, the drone project) exist as repos under `gigaflippy`. Picking a project and a stack for an empty repo would be guessing, so this run stopped here.

**Options.**

1. **Point the nightly task at a real project repo (recommended).** Push one of your top-priority projects (Pulsewatch or CharmMatch) to its own GitHub repo, even if it's rough, and change the scheduled task to target it.
   - + Runs do real work on code you actually care about: tests, bug fixes, features.
   - + Keeps each project's history clean and separate.
   - − Needs 5 minutes from you to create/push the repo and edit the scheduled task.

2. **Turn Firstproject into one of those projects from scratch.** Tell me which project and, if you have a preference, the stack (e.g. CharmMatch → Vite + React + TypeScript; Pulsewatch → Python service). Next run scaffolds it, adds tests/lint/CI, and builds from there.
   - + Zero setup on your side beyond one line here.
   - − Starts from nothing; any existing code/artifact you have would need to be pasted in or redone.
   - − Repo name "Firstproject" stays misleading unless renamed.

3. **Keep Firstproject as a sandbox.** Runs do small self-contained things only (README, a `main` branch, CI template, a repo-hygiene checklist).
   - + No decisions needed.
   - − Low value; mostly busywork.

**Recommendation:** Option 1 with Pulsewatch or CharmMatch. If you'd rather not create a repo, Option 2 — just name the project and stack.

**Also worth deciding (small):** create a `main` branch as the default? Right now the default branch is `claude/hello-test`, so PRs target that.

**Georgi's answer:** Pulsewatch (2026-10-19). Build it in this repo (Option 2).

**Spec (from Georgi's Pulsewatch project notes):** distributed uptime/latency monitor; flagship DevOps portfolio project; zero cost.
- Python/FastAPI probes + API, Docker, GitHub Actions CI
- Local Kubernetes (kind/k3d) instead of paid cloud; Azure/AKS dropped
- Terraform for the local platform, ArgoCD for deploys, Prometheus/Grafana for metrics

**Plan for next run:** scaffold the probe + API service (FastAPI, SQLite/Postgres-ready storage, pytest, ruff, Dockerfile, GitHub Actions). K8s/Terraform/ArgoCD come in later runs.

**Open, non-blocking:** if Pulsewatch code already exists on Georgi's laptop, push it here instead so runs build on it rather than starting fresh.

---

## D-002 — Terraform or OpenTofu for the local platform (roadmap item 5)? (opened 2026-10-20)

**Status:** resolved — Terraform (2026-10-20)

**Context.** Item 5 is infrastructure-as-code for the local platform: create the kind cluster, the namespaces and the monitoring stack from code instead of `make kind-up`. Since 2023, HashiCorp Terraform is under the BUSL 1.1 licence (source-available, not open source). OpenTofu is the Linux Foundation fork under MPL 2.0. It's a drop-in replacement: same HCL, same providers (`tehcyx/kind`, `hashicorp/kubernetes`), same workflow (`tofu plan/apply` instead of `terraform plan/apply`). Using either one for a personal portfolio project is free and allowed. The choice is about what you want the repo to say about you, and it's a licensing call, so it's yours.

**Options.**

1. **Terraform (recommended).**
   - + It's the name in job postings, Canonical's and Team.Blue's included. Recruiters and ATS filters search for "Terraform".
   - + Same skills transfer 1:1 to OpenTofu if an employer uses it.
   - − BUSL licence. That doesn't matter for personal use, but some people care on principle.
2. **OpenTofu.**
   - + Truly open source (MPL 2.0), and it's increasingly adopted, by Canonical-adjacent and open-source-first shops among others.
   - − Less recognised by name. You'd want "Terraform/OpenTofu" in the README and on your CV anyway.
3. **Both: write it for Terraform and test it in CI with OpenTofu too.**
   - + Shows you know the ecosystem split; the HCL is identical.
   - − A bit more CI time and one more thing to explain.

**Recommendation:** Option 1, with a README note that it runs unchanged on OpenTofu. If you care about open-source licensing, Option 3.

**Georgi's answer:** Terraform (2026-10-20): it's what job postings ask for. The README notes it also runs on OpenTofu.
