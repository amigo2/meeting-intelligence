#!/usr/bin/env bash
# Build the frontend, upload to S3, and invalidate CloudFront.
# Prereq: `terraform apply` created the S3 bucket + CloudFront distribution.
set -euo pipefail
cd "$(dirname "$0")"

echo "→ Building frontend"
(cd ../frontend && npm run build)

BUCKET="$(terraform output -raw frontend_bucket)"
DIST_ID="$(terraform output -raw cloudfront_distribution_id)"

echo "→ Uploading to s3://$BUCKET"
aws s3 sync ../frontend/dist "s3://$BUCKET" --delete

echo "→ Invalidating CloudFront cache"
aws cloudfront create-invalidation --distribution-id "$DIST_ID" --paths "/*" >/dev/null

echo "✅ Frontend deployed:"
terraform output -raw frontend_url
echo ""
