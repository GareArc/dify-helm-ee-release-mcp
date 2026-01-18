#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

DOCKER_REGISTRY="${DOCKER_REGISTRY:-ghcr.io}"
DOCKER_ORG="${DOCKER_ORG:-}" 
APP_NAME="${APP_NAME:-helm-release-mcp}"
IMAGE_NAME="${DOCKER_IMAGE:-}"
TAG="${TAG:-}"
PUSH="${PUSH:-false}"

if [[ -z "$TAG" ]]; then
  TAG="$(git -C "$ROOT_DIR" rev-parse --short HEAD)"
fi

if [[ -n "$IMAGE_NAME" ]]; then
  IMAGE="$IMAGE_NAME"
else
  if [[ -z "$DOCKER_ORG" ]]; then
    echo "DOCKER_ORG is not set. Set DOCKER_ORG or DOCKER_IMAGE." >&2
    exit 1
  fi
  IMAGE="$DOCKER_REGISTRY/$DOCKER_ORG/$APP_NAME"
fi

echo "Building image: $IMAGE:$TAG"

docker build -t "$IMAGE:$TAG" -t "$IMAGE:latest" "$ROOT_DIR"

if [[ "$PUSH" == "true" ]]; then
  echo "Pushing image: $IMAGE:$TAG"
  docker push "$IMAGE:$TAG"
  docker push "$IMAGE:latest"
fi
