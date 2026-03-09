#!/bin/bash
# Deploy Echoes to Google Cloud Run (minimal cost)
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-your-project-id}"
REGION="us-central1"
SERVICE_NAME="echoes"
IMAGE="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo "==> Building and pushing image to $IMAGE"
gcloud builds submit --tag "$IMAGE" .

echo "==> Deploying to Cloud Run ($SERVICE_NAME)"
gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 1 \
  --timeout 300 \
  --set-env-vars "GOOGLE_API_KEY=${GOOGLE_API_KEY}" \
  --port 8000

echo "==> Done! Service URL:"
gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format 'value(status.url)'
