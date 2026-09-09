#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"
ZLM_URL="${ZLM_URL:-http://127.0.0.1:8080}"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-drone-backend}"
ZLM_CONTAINER="${ZLM_CONTAINER:-drone-zlm}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-60}"

if [[ -z "${DRONE_STREAM_ZLM_SECRET:-}" ]]; then
  echo "DRONE_STREAM_ZLM_SECRET must be set" >&2
  exit 2
fi

for command in docker curl; do
  command -v "${command}" >/dev/null || {
    echo "missing required command: ${command}" >&2
    exit 2
  }
done

wait_for_backend() {
  local deadline=$((SECONDS + TIMEOUT_SECONDS))
  while ((SECONDS < deadline)); do
    if curl --fail --silent "${BACKEND_URL}/api/health" >/dev/null; then
      return 0
    fi
    sleep 1
  done
  echo "backend did not recover within ${TIMEOUT_SECONDS}s" >&2
  return 1
}

wait_for_zlm() {
  local deadline=$((SECONDS + TIMEOUT_SECONDS))
  while ((SECONDS < deadline)); do
    if curl --fail --silent --get "${ZLM_URL}/index/api/getServerConfig" \
      --data-urlencode "secret=${DRONE_STREAM_ZLM_SECRET}" >/dev/null; then
      return 0
    fi
    sleep 1
  done
  echo "ZLM did not recover within ${TIMEOUT_SECONDS}s" >&2
  return 1
}

wait_for_backend
wait_for_zlm

docker restart "${BACKEND_CONTAINER}" >/dev/null
wait_for_backend

docker restart "${ZLM_CONTAINER}" >/dev/null
wait_for_zlm
wait_for_backend

STREAM_ID="recovery_$(date +%s)" \
  BACKEND_URL="${BACKEND_URL}" \
  ZLM_URL="${ZLM_URL}" \
  "${ROOT_DIR}/scripts/integration_smoke_test.sh"

echo "backend and ZLM restart recovery test passed"
