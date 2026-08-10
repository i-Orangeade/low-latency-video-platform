#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

STREAM_ID="${STREAM_ID:-drone_001}"
RTMP_URL="${RTMP_URL:-rtmp://127.0.0.1/live/${STREAM_ID}}"

echo "Pushing stream to ${RTMP_URL}"
echo "HTTP-FLV playback: http://127.0.0.1:8080/live/${STREAM_ID}.live.flv"

exec "${PROJECT_ROOT}/deploy/ffmpeg/push_demo.sh" "${1:-}"
