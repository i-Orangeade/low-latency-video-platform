#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"
ZLM_URL="${ZLM_URL:-http://127.0.0.1:8080}"
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
if [[ -z "${DRONE_STREAM_ZLM_SECRET:-}" ]]; then
  echo "DRONE_STREAM_ZLM_SECRET must be set" >&2
  exit 2
fi

curl --fail --silent --show-error "${BACKEND_URL}/api/health" >/dev/null

status="$(
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"Smoke test\",\"stream_id\":\"${STREAM_ID}\",\"enabled\":true}" \
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
ZLM_URL="${ZLM_URL}" "${ROOT_DIR}/scripts/query_stream_qos.sh" "${STREAM_ID}" 1000 >/dev/null

kill "${PUSH_PID}"
wait "${PUSH_PID}" 2>/dev/null || true
PUSH_PID=""
wait_for_state false

curl --fail --silent "${BACKEND_URL}/api/alerts" |
  python3 -c \
    'import json,sys
stream=sys.argv[1]
alerts=json.load(sys.stdin)
ok=any(a.get("stream_id")==stream and a.get("category")=="stream_offline" for a in alerts)
raise SystemExit(not ok)' \
    "${STREAM_ID}"

echo "integration smoke test passed for ${STREAM_ID}"
