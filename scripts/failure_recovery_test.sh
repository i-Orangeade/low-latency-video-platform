#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"
STREAM_ID="${STREAM_ID:-recovery_001}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-45}"
PUSH_PID=""

cleanup() {
  if [[ -n "${PUSH_PID}" ]] && kill -0 "${PUSH_PID}" 2>/dev/null; then
    kill "${PUSH_PID}" 2>/dev/null || true
    wait "${PUSH_PID}" 2>/dev/null || true
  fi
  (
    cd "${ROOT_DIR}"
    docker compose start backend >/dev/null 2>&1 || true
  )
}
trap cleanup EXIT INT TERM

for name in DRONE_STREAM_ZLM_SECRET DRONE_STREAM_ZLM_HOOK_SECRET; do
  if [[ -z "${!name:-}" ]]; then
    echo "${name} must be set" >&2
    exit 2
  fi
done

status="$(
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"Recovery test\",\"stream_id\":\"${STREAM_ID}\",\"enabled\":true}" \
    "${BACKEND_URL}/api/devices"
)"
if [[ "${status}" != "201" && "${status}" != "409" ]]; then
  echo "device registration failed with HTTP ${status}" >&2
  exit 1
fi

(
  cd "${ROOT_DIR}"
  docker compose stop backend >/dev/null
)

STREAM_ID="${STREAM_ID}" \
RTMP_URL="rtmp://127.0.0.1/live/${STREAM_ID}" \
  "${ROOT_DIR}/deploy/ffmpeg/push_demo.sh" \
  >"/tmp/${STREAM_ID}-recovery-push.log" 2>&1 &
PUSH_PID=$!

sleep 1
(
  cd "${ROOT_DIR}"
  docker compose start backend >/dev/null
)

deadline=$((SECONDS + TIMEOUT_SECONDS))
while ((SECONDS < deadline)); do
  if curl --fail --silent "${BACKEND_URL}/api/health" >/dev/null &&
    curl --fail --silent "${BACKEND_URL}/api/streams/${STREAM_ID}/status" |
      python3 -c \
        'import json,sys; raise SystemExit(not json.load(sys.stdin).get("online"))'
  then
    break
  fi
  if ! kill -0 "${PUSH_PID}" 2>/dev/null; then
    cat "/tmp/${STREAM_ID}-recovery-push.log" >&2
    echo "publisher exited before Hook retry recovered" >&2
    exit 1
  fi
  sleep 1
done

if ((SECONDS >= deadline)); then
  echo "stream did not recover after backend restart" >&2
  exit 1
fi

"${ROOT_DIR}/scripts/query_stream_qos.sh" "${STREAM_ID}" 1000 >/dev/null

kill "${PUSH_PID}"
wait "${PUSH_PID}" 2>/dev/null || true
PUSH_PID=""

deadline=$((SECONDS + TIMEOUT_SECONDS))
while ((SECONDS < deadline)); do
  if curl --fail --silent "${BACKEND_URL}/api/streams/${STREAM_ID}/status" |
    python3 -c \
      'import json,sys; raise SystemExit(json.load(sys.stdin).get("online") is not False)'
  then
    echo "Hook retry and backend restart recovery test passed"
    exit 0
  fi
  sleep 1
done

echo "stream did not transition offline after recovery test" >&2
exit 1
