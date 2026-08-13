#!/usr/bin/env bash
# Build the backend image for Fargate (linux/amd64) and push it to ECR.
# Prereq: `terraform apply` has created the ECR repo. Run from anywhere.
set -euo pipefail

REGION="eu-west-2"
cd "$(dirname "$0")"

ECR="$(terraform output -raw ecr_repository_url)"
REGISTRY="${ECR%/*}"   # strip the repo name to get the registry host

echo "→ Logging in to $REGISTRY"
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "$REGISTRY"

echo "→ Building linux/amd64 image and pushing to $ECR:latest"
docker buildx build --platform linux/amd64 -t "$ECR:latest" --push ../backend

echo "✅ Pushed $ECR:latest"
