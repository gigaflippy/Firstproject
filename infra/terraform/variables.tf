variable "cluster_name" {
  description = "Name of the local kind cluster."
  type        = string
  default     = "pulsewatch"
}

variable "overlay" {
  description = "Kustomize overlay under deploy/k8s/overlays to deploy."
  type        = string
  default     = "multi-region"

  validation {
    condition     = contains(["kind", "multi-region"], var.overlay)
    error_message = "overlay must be one of: kind, multi-region."
  }
}

variable "image" {
  description = "Local Pulsewatch image tag. Must match the tag the overlays pin (pulsewatch:dev)."
  type        = string
  default     = "pulsewatch:dev"
}

variable "build_image" {
  description = "Build the image with docker and load it into the cluster with `kind load`. Set false if you load it yourself."
  type        = bool
  default     = true
}
