#!/usr/bin/env bash
set -euo pipefail

# Configurations
PROJECT_ID=$(gcloud config get-value project)
REGION=${REGION:-"us-central1"}
CLUSTER_NAME=${CLUSTER_NAME:-"pdf-fanout-cluster"}

INGEST_BUCKET="${PROJECT_ID}-pdf-ingest"
DATA_BUCKET="${PROJECT_ID}-pdf-data"

WEBAPP_IMAGE="gcr.io/${PROJECT_ID}/pdf-webapp:latest"
INGEST_IMAGE="gcr.io/${PROJECT_ID}/pdf-ingest-job:latest"
ANALYSIS_IMAGE="gcr.io/${PROJECT_ID}/pdf-analysis-job:latest"

echo "=================================================="
echo "Deploying PDF Fanout System to Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "=================================================="

# 1. Create GCS Buckets if they don't exist
echo "Step 1: Creating GCS Buckets..."
gsutil mb -p "${PROJECT_ID}" -l "${REGION}" "gs://${INGEST_BUCKET}" 2>/dev/null || echo "Ingest bucket already exists"
gsutil mb -p "${PROJECT_ID}" -l "${REGION}" "gs://${DATA_BUCKET}" 2>/dev/null || echo "Data bucket already exists"

# 2. Build Container Images using Google Cloud Build
echo "Step 2: Building container images via Cloud Build..."
gcloud builds submit webapp/ --tag "${WEBAPP_IMAGE}"
gcloud builds submit jobs/ingest/ --tag "${INGEST_IMAGE}"
gcloud builds submit jobs/analysis/ --tag "${ANALYSIS_IMAGE}"

# 3. Connect to GKE Autopilot Cluster
echo "Step 3: Fetching GKE cluster credentials..."
gcloud container clusters get-credentials "${CLUSTER_NAME}" --region "${REGION}"

# 4. Apply Kubernetes Manifests
echo "Step 4: Applying Kubernetes manifests..."
kubectl apply -f infra/k8s/rbac.yaml
kubectl apply -f infra/k8s/pvc.yaml

# Replace project references dynamically in webapp.yaml
sed "s/gke-llm-testing-env/${PROJECT_ID}/g" infra/k8s/webapp.yaml | kubectl apply -f -

# 5. Deploy Cloud Function Trigger for GCS Ingest
echo "Step 5: Deploying GCS Cloud Function Trigger..."
gcloud functions deploy pdf-ingest-trigger \
    --gen2 \
    --runtime=python311 \
    --region="${REGION}" \
    --source=cloud_functions/gcs_trigger \
    --entry-point=handle_pdf_upload \
    --trigger-event-filters="type=google.cloud.storage.object.v1.finalized" \
    --trigger-event-filters="bucket=${INGEST_BUCKET}" \
    --set-env-vars="WEBAPP_URL=http://pdf-webapp-service.default.svc.cluster.local:8000"

echo "=================================================="
echo "Deployment Complete!"
echo "Ingest Bucket: gs://${INGEST_BUCKET}"
echo "Data Bucket:   gs://${DATA_BUCKET}"
echo "=================================================="
