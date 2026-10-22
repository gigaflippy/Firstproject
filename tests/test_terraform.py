"""Keeps infra/terraform in sync with the overlays it deploys.

`terraform validate` and a real `terraform apply` against kind run in CI; these checks
need no Terraform binary.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TF = ROOT / "infra" / "terraform"
OVERLAYS = ROOT / "deploy" / "k8s" / "overlays"


def _variable_block(name: str) -> str:
    text = (TF / "variables.tf").read_text()
    m = re.search(rf'variable "{name}" \{{(.*?)\n\}}', text, re.S)
    assert m, f"variable {name} not found"
    return m.group(1)


def test_overlay_validation_lists_every_overlay():
    block = _variable_block("overlay")
    allowed = set(re.findall(r'"([^"]+)"', re.search(r"contains\(\[(.*?)\]", block).group(1)))
    on_disk = {p.name for p in OVERLAYS.iterdir() if (p / "kustomization.yaml").exists()}
    assert allowed == on_disk
    default = re.search(r'default\s*=\s*"([^"]+)"', block).group(1)
    assert default in on_disk


def test_image_default_matches_overlay_pins():
    default = re.search(r'default\s*=\s*"([^"]+)"', _variable_block("image")).group(1)
    for k in OVERLAYS.rglob("kustomization.yaml"):
        for img in yaml.safe_load(k.read_text()).get("images", []):
            assert f"{img['newName']}:{img['newTag']}" == default, k


def test_state_and_kubeconfig_never_committed():
    ignored = (TF / ".gitignore").read_text().split()
    for pattern in ("*.tfstate", "kubeconfig", ".terraform/"):
        assert pattern in ignored


def test_node_image_is_pinned():
    """Unpinned, the node image follows the provider's default, and a newer node broke
    `kind load` (containerd config version 4) without any change in this repo."""
    default = re.search(r'default\s*=\s*"([^"]+)"', _variable_block("node_image")).group(1)
    assert re.fullmatch(r"kindest/node:v\d+\.\d+\.\d+(@sha256:[0-9a-f]{64})?", default), default
    assert "node_image      = var.node_image" in (TF / "main.tf").read_text()
