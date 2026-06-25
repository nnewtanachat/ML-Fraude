# Deploy Guide

## Folder Structure (k8s/)

```
k8s/
├── base/           ← Core resources (ใช้ทุก environment)
├── overlays/
│   ├── dev/        ← Dev-specific (minikube, test passwords)
│   └── prod/       ← Prod-specific (ingress, cert, real secrets)
├── tools/          ← Internal tools (pgAdmin, MLflow)
├── jobs/           ← Jobs & CronJobs (migration, batch, drift, backup)
└── helm-values/    ← Helm configs (PostgreSQL, Kafka, Airflow)
```

## Deploy Commands

### Minikube (Dev):
```bash
minikube start
eval $(minikube docker-env)
docker build -t ml-fraud:v1 .

kubectl apply -f k8s/base/
kubectl apply -f k8s/overlays/dev/
kubectl apply -f k8s/tools/
```

### Production (GCP):
```bash
# 1. Helm install managed services
helm install postgres bitnami/postgresql -n fraud-detection -f k8s/helm-values/postgres-values.yaml
helm install kafka bitnami/kafka -n fraud-detection -f k8s/helm-values/kafka-values.yaml
helm install ingress-nginx ingress-nginx/ingress-nginx -n ingress-nginx --create-namespace
helm install cert-manager jetstack/cert-manager -n cert-manager --create-namespace --set crds.enabled=true

# 2. Deploy app
kubectl apply -f k8s/base/
kubectl apply -f k8s/overlays/prod/

# 3. Deploy tools
kubectl apply -f k8s/tools/

# 4. Run migration
kubectl apply -f k8s/jobs/migration-job.yaml

# 5. Deploy scheduled jobs
kubectl apply -f k8s/jobs/
```
