output "cluster_name" {
  value = kind_cluster.this.name
}

output "kubeconfig_path" {
  description = "export KUBECONFIG=<this> to use kubectl against the cluster."
  value       = abspath(kind_cluster.this.kubeconfig_path)
}

output "next_steps" {
  value = <<-EOT
    export KUBECONFIG=${abspath(kind_cluster.this.kubeconfig_path)}
    kubectl get pods -A -l app.kubernetes.io/part-of=pulsewatch
    make k8s-forward${var.overlay == "multi-region" ? " API_NS=pulsewatch-eu" : ""}
  EOT
}
