#!/usr/bin/env bash
# First-time push of all four images (ECS services need them to exist before they can start).
# Usage: ./scripts/push-images.sh ap-southeast-1
set -euo pipefail
cd "$(dirname "$0")/.."   # always run from the repo root, wherever the script is called from
REGION="${1:?usage: push-images.sh <region>}"
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REG="$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REG"
for s in web voice worker scheduler; do
  docker build -t "$REG/jazzaiconcierge-test-$s:latest" "services/$s"
  docker push "$REG/jazzaiconcierge-test-$s:latest"
done
