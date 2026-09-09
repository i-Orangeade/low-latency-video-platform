#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

STREAM_ID="${STREAM_ID:-drone_001}"
RTMP_URL="${RTMP_URL:-rtmp://127.0.0.1/live/${STREAM_ID}}"
BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"

if [[ ! "${STREAM_ID}" =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo "STREAM_ID may only contain letters, numbers, underscore, and hyphen" >&2
  exit 2
fi

status="$(
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"Test drone ${STREAM_ID}\",\"stream_id\":\"${STREAM_ID}\",\"enabled\":true}" \
    "${BACKEND_URL}/api/devices"
)"
case "${status}" in
  201) echo "Registered test device ${STREAM_ID}" ;;
  409) echo "Test device ${STREAM_ID} already exists" ;;
  *)
    echo "Failed to register test device: backend returned HTTP ${status}" >&2
    exit 1
    ;;
esac

echo "Pushing stream to ${RTMP_URL}"
echo "HTTP-FLV playback: http://127.0.0.1:8080/live/${STREAM_ID}.live.flv"

exec "${PROJECT_ROOT}/deploy/ffmpeg/push_demo.sh" "${1:-}"
