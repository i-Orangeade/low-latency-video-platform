#!/usr/bin/env bash
set -euo pipefail

STREAM_ID="${STREAM_ID:-drone_001}"
RTMP_URL="${RTMP_URL:-rtmp://127.0.0.1/live/${STREAM_ID}}"
INPUT="${1:-}"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is required. Install it with: sudo apt install ffmpeg"
  exit 1
fi

if [[ -n "${INPUT}" ]]; then
  exec ffmpeg -re -stream_loop -1 -i "${INPUT}" \
    -c:v libx264 -preset veryfast -tune zerolatency -g 50 -bf 0 \
    -c:a aac -ar 44100 -b:a 96k \
    -f flv "${RTMP_URL}"
fi

exec ffmpeg -re -f lavfi -i testsrc=size=1280x720:rate=25 \
  -f lavfi -i sine=frequency=1000:sample_rate=44100 \
  -c:v libx264 -preset veryfast -tune zerolatency -g 50 -bf 0 \
  -pix_fmt yuv420p \
  -c:a aac -ar 44100 -b:a 96k \
  -f flv "${RTMP_URL}"
