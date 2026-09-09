#!/usr/bin/env bash
set -euo pipefail

STREAM_ID="${1:-drone_001}"
PROBE_MS="${2:-3000}"
ZLM_URL="${ZLM_URL:-http://127.0.0.1:8080}"
ZLM_SECRET="${DRONE_STREAM_ZLM_SECRET:-}"
APP="${APP:-live}"
VHOST="${VHOST:-__defaultVhost__}"

if [[ -z "${ZLM_SECRET}" ]]; then
  echo "DRONE_STREAM_ZLM_SECRET must be set" >&2
  exit 1
fi
if [[ ! "${PROBE_MS}" =~ ^[0-9]+$ ]] || ((PROBE_MS < 100 || PROBE_MS > 30000)); then
  echo "probe_ms must be an integer between 100 and 30000" >&2
  exit 2
fi

curl --fail --silent --show-error --get "${ZLM_URL}/index/api/getStreamQos" \
  --data-urlencode "secret=${ZLM_SECRET}" \
  --data-urlencode "vhost=${VHOST}" \
  --data-urlencode "app=${APP}" \
  --data-urlencode "stream=${STREAM_ID}" \
  --data-urlencode "probe_ms=${PROBE_MS}"
printf '\n'
