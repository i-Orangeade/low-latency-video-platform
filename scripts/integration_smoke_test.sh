#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"
STREAM_ID="${STREAM_ID:-smoke_001}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-30}"
PUSH_PID=""

cleanup() {
  if [[ -n "${PUSH_PID}" ]] && kill -0 "${PUSH_PID}" 2>/dev/null; then
    kill "${PUSH_PID}" 2>/dev/null || true
    wait "${PUSH_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

if [[ ! "${STREAM_ID}" =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo "invalid STREAM_ID" >&2
  exit 2
fi

curl --fail --silent --show-error "${BACKEND_URL}/api/health" >/dev/null

status="$(
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"Smoke test\",\"stream_id\":\"${STREAM_ID}\"}" \
    "${BACKEND_URL}/api/devices"
)"
if [[ "${status}" != "201" && "${status}" != "409" ]]; then
  echo "device registration failed with HTTP ${status}" >&2
  exit 1
fi

STREAM_ID="${STREAM_ID}" \
RTMP_URL="rtmp://127.0.0.1/live/${STREAM_ID}" \
  "${ROOT_DIR}/deploy/ffmpeg/push_demo.sh" >"/tmp/${STREAM_ID}-push.log" 2>&1 &
PUSH_PID=$!

wait_for_state() {
  local expected="$1"
  local deadline=$((SECONDS + TIMEOUT_SECONDS))
  while ((SECONDS < deadline)); do
    if curl --fail --silent "${BACKEND_URL}/api/streams/${STREAM_ID}/status" |
      python3 -c \
        'import json,sys; expected=sys.argv[1]=="true"; raise SystemExit(json.load(sys.stdin).get("online") != expected)' \
        "${expected}"; then
      return 0
    fi
    sleep 1
  done
  echo "timed out waiting for stream online=${expected}" >&2
  return 1
}

wait_for_state true

kill "${PUSH_PID}"
wait "${PUSH_PID}" 2>/dev/null || true
PUSH_PID=""
wait_for_state false

echo "integration smoke test passed for ${STREAM_ID}"
