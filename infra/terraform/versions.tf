terraform {
  # Also runs unchanged on OpenTofu >= 1.6 (`tofu init && tofu apply`).
  required_version = ">= 1.6"

  required_providers {
    kind = {
      source  = "tehcyx/kind"
      version = "~> 0.6"
    }
    kustomization = {
      source  = "kbst/kustomization"
      version = "~> 0.9"
    }
  }
}
