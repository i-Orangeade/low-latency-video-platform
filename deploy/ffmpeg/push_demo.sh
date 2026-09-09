#!/usr/bin/env bash
set -euo pipefail

STREAM_ID="${STREAM_ID:-drone_001}"
RTMP_URL="${RTMP_URL:-rtmp://127.0.0.1/live/${STREAM_ID}}"
LATENCY_SIDECAR="${LATENCY_SIDECAR:-/tmp/${STREAM_ID}.latency-source}"
INPUT="${1:-}"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is required. Install it with: sudo apt install ffmpeg"
  exit 1
fi

# Outgoing PTS is derived from RTCTIME relative to this anchor, so every encoded
# frame remains associated with the wall-clock time at the source video filter.
# See docs/latency-methodology.md for the exact boundary and limitations.
sidecar_dir="$(dirname -- "${LATENCY_SIDECAR}")"
mkdir -p -- "${sidecar_dir}"
sidecar_tmp="$(mktemp "${sidecar_dir}/.latency-source.XXXXXX")"
cleanup() {
  rm -f -- "${sidecar_tmp}"
}
trap cleanup EXIT

source_start_epoch_ns="$(date +%s%N)"
source_start_epoch_us="$((source_start_epoch_ns / 1000))"
video_pts_filter="setpts=(RTCTIME-${source_start_epoch_us})/(TB*1000000)"
{
  printf '%s\n' 'schema=drone-stream-latency-source-v1'
  printf '%s\n' 'clock=CLOCK_REALTIME'
  printf 'source_start_epoch_ns=%s\n' "${source_start_epoch_ns}"
  printf '%s\n' 'pts_origin_seconds=0'
  printf '%s\n' 'measurement_boundary=source-playout-to-ffmpeg-decoded-frame-report'
} >"${sidecar_tmp}"
chmod 0644 "${sidecar_tmp}"
mv -f -- "${sidecar_tmp}" "${LATENCY_SIDECAR}"
trap - EXIT
printf 'Latency source sidecar: %s\n' "${LATENCY_SIDECAR}" >&2

if [[ -n "${INPUT}" ]]; then
  exec ffmpeg -re -stream_loop -1 -i "${INPUT}" \
    -vf "${video_pts_filter}" \
    -c:v libx264 -preset veryfast -tune zerolatency -g 50 -bf 0 \
    -c:a aac -ar 44100 -b:a 96k \
    -f flv "${RTMP_URL}"
fi

exec ffmpeg -re -f lavfi -i testsrc=size=1280x720:rate=25 \
  -f lavfi -i sine=frequency=1000:sample_rate=44100 \
  -vf "${video_pts_filter}" \
  -c:v libx264 -preset veryfast -tune zerolatency -g 50 -bf 0 \
  -pix_fmt yuv420p \
  -c:a aac -ar 44100 -b:a 96k \
  -f flv "${RTMP_URL}"
