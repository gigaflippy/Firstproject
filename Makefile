# Local Kubernetes workflow for Pulsewatch. Needs: docker, kind, kubectl.
CLUSTER ?= pulsewatch
NS      ?= pulsewatch
IMAGE   ?= pulsewatch:dev
OVERLAY ?= deploy/k8s/overlays/kind

.PHONY: help kind-up kind-down k8s-apply k8s-wait k8s-validate k8s-forward k8s-status

help:
	@echo "make kind-up       create kind cluster, build + load image, deploy, wait for rollout"
	@echo "make k8s-forward   port-forward API :8000, Prometheus :9090, Grafana :3000"
	@echo "make k8s-status    show pods/services in the $(NS) namespace"
	@echo "make k8s-validate  render manifests and schema-check them (kubectl + kubeconform)"
	@echo "make kind-down     delete the kind cluster"

kind-up:
	@kind get clusters | grep -qx '$(CLUSTER)' || kind create cluster --config deploy/k8s/kind-config.yaml --name $(CLUSTER)
	docker build -t $(IMAGE) .
	kind load docker-image $(IMAGE) --name $(CLUSTER)
	$(MAKE) k8s-apply k8s-wait
	# Same tag every build: restart so the freshly loaded image is picked up.
	kubectl -n $(NS) rollout restart deployment/pulsewatch
	kubectl -n $(NS) rollout status deployment/pulsewatch --timeout=180s

k8s-apply:
	kubectl apply -k $(OVERLAY)

k8s-wait:
	kubectl -n $(NS) rollout status deployment/pulsewatch --timeout=180s
	kubectl -n $(NS) rollout status deployment/prometheus --timeout=180s
	kubectl -n $(NS) rollout status deployment/grafana --timeout=180s

k8s-forward:
	@echo "API http://localhost:8000/docs  Prometheus http://localhost:9090  Grafana http://localhost:3000  (Ctrl-C to stop)"
	@trap 'kill 0' INT TERM; \
	kubectl -n $(NS) port-forward svc/pulsewatch 8000:8000 & \
	kubectl -n $(NS) port-forward svc/prometheus 9090:9090 & \
	kubectl -n $(NS) port-forward svc/grafana 3000:3000 & \
	wait

k8s-status:
	kubectl -n $(NS) get pods,svc,pvc

k8s-validate:
	kubectl kustomize $(OVERLAY) | kubeconform -strict -summary -

kind-down:
	kind delete cluster --name $(CLUSTER)
