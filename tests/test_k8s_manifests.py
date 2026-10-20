"""Static checks for deploy/k8s.

Full rendering and schema validation run in CI (kustomize + kubeconform) and the
kind job deploys for real; these tests catch drift between the manifests and the
code/config they depend on, without needing any Kubernetes tooling.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from pulsewatch.api import create_app
from pulsewatch.config import Settings, load_targets

ROOT = Path(__file__).resolve().parent.parent
K8S = ROOT / "deploy" / "k8s"
BASE = K8S / "base"
MONITORING = K8S / "monitoring"
OVERLAY = K8S / "overlays" / "kind"
PROM_CONFIG = ROOT / "deploy" / "prometheus" / "prometheus.yml"
GRAFANA_DATASOURCE = ROOT / "deploy" / "grafana" / "provisioning" / "datasources" / "prometheus.yml"


def _docs(path: Path) -> list[dict]:
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def _find(kind: str, name: str) -> dict:
    for path in [*BASE.glob("*.yaml"), *MONITORING.glob("*.yaml")]:
        for doc in _docs(path):
            if doc.get("kind") == kind and doc["metadata"]["name"] == name:
                return doc
    raise AssertionError(f"{kind}/{name} not found")


def _container(deployment: dict) -> dict:
    [c] = deployment["spec"]["template"]["spec"]["containers"]
    return c


def _env(container: dict) -> dict[str, str]:
    return {e["name"]: e["value"] for e in container.get("env", [])}


def test_in_cluster_targets_file_is_valid():
    assert load_targets(BASE / "targets.yaml")


def test_pulsewatch_container_matches_app_settings(tmp_path):
    c = _container(_find("Deployment", "pulsewatch"))
    env = _env(c)
    # Every PULSEWATCH_* var must be a real setting, or it is silently ignored.
    known = {f"PULSEWATCH_{name.upper()}" for name in Settings.model_fields}
    unknown = {k for k in env if k.startswith("PULSEWATCH_")} - known
    assert not unknown, f"unknown settings in deployment env: {unknown}"

    assert c["ports"][0]["containerPort"] == Settings().port
    mounts = {m["name"]: m["mountPath"] for m in c["volumeMounts"]}
    assert env["PULSEWATCH_TARGETS_FILE"].startswith(mounts["targets"] + "/")
    assert env["PULSEWATCH_DB_PATH"].startswith(mounts["data"] + "/")

    # Probe path must exist in the app.
    app = create_app(
        Settings(db_path=tmp_path / "x.db", scheduler_enabled=False),
        targets=load_targets(BASE / "targets.yaml"),
    )
    routes = {r.path for r in app.routes}
    for probe in ("startupProbe", "readinessProbe", "livenessProbe"):
        assert c[probe]["httpGet"]["path"] in routes


def test_settings_reject_injected_service_env(monkeypatch):
    """Documents why enableServiceLinks must stay false: Kubernetes would inject this."""
    from pydantic import ValidationError

    monkeypatch.setenv("PULSEWATCH_PORT", "tcp://10.96.0.10:8000")
    with pytest.raises(ValidationError):
        Settings()


def test_pulsewatch_runs_as_dockerfile_user():
    dockerfile = (ROOT / "Dockerfile").read_text()
    pod = _find("Deployment", "pulsewatch")["spec"]["template"]["spec"]
    assert f"--uid {pod['securityContext']['runAsUser']}" in dockerfile


def test_single_writer_for_sqlite():
    spec = _find("Deployment", "pulsewatch")["spec"]
    assert spec["replicas"] == 1
    assert spec["strategy"]["type"] == "Recreate"


@pytest.mark.parametrize("name", ["pulsewatch", "prometheus", "grafana"])
def test_containers_are_hardened(name):
    dep = _find("Deployment", name)
    pod = dep["spec"]["template"]["spec"]
    c = _container(dep)
    assert pod["securityContext"]["runAsNonRoot"] is True
    assert pod["automountServiceAccountToken"] is False
    # Service env injection would set PULSEWATCH_PORT=tcp://... and crash Settings().
    assert pod["enableServiceLinks"] is False
    assert c["securityContext"]["allowPrivilegeEscalation"] is False
    assert c["securityContext"]["readOnlyRootFilesystem"] is True
    assert c["securityContext"]["capabilities"]["drop"] == ["ALL"]
    assert "memory" in c["resources"]["limits"]
    assert "readinessProbe" in c


def test_services_match_shared_config_hostnames():
    """compose and k8s share deploy/prometheus and deploy/grafana, so Service names/ports
    must match the hosts those files point at."""
    prom = yaml.safe_load(PROM_CONFIG.read_text())
    [scrape_target] = prom["scrape_configs"][0]["static_configs"][0]["targets"]
    host, port = scrape_target.split(":")
    svc = _find("Service", host)
    assert svc["spec"]["ports"][0]["port"] == int(port)

    ds = yaml.safe_load(GRAFANA_DATASOURCE.read_text())["datasources"][0]
    host, port = ds["url"].removeprefix("http://").split(":")
    assert _find("Service", host)["spec"]["ports"][0]["port"] == int(port)


def test_images_pinned_like_compose():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())["services"]
    for name in ("prometheus", "grafana"):
        assert _container(_find("Deployment", name))["image"] == compose[name]["image"]


def test_overlay_pins_local_image():
    k = yaml.safe_load((OVERLAY / "kustomization.yaml").read_text())
    [img] = k["images"]
    assert img["name"] == _container(_find("Deployment", "pulsewatch"))["image"]
    assert _container(_find("Deployment", "pulsewatch"))["imagePullPolicy"] == "IfNotPresent"


@pytest.mark.skipif(
    not (shutil.which("kustomize") or shutil.which("kubectl")), reason="no kustomize/kubectl"
)
def test_overlay_renders():
    cmd = ["kustomize", "build"] if shutil.which("kustomize") else ["kubectl", "kustomize"]
    out = subprocess.run([*cmd, str(OVERLAY)], check=True, capture_output=True, text=True).stdout
    docs = [d for d in yaml.safe_load_all(out) if d]
    workloads = {d["metadata"]["name"] for d in docs if d["kind"] == "Deployment"}
    assert workloads == {"pulsewatch", "prometheus", "grafana"}
    assert all(
        d["metadata"].get("namespace") == "pulsewatch" for d in docs if d["kind"] != "Namespace"
    )
