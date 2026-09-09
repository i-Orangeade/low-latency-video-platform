#!/usr/bin/env bash
set -euo pipefail

MEDIA_SERVER="${1:-}"
SOURCE_CONFIG="${2:-}"
API_SECRET="runtime-test-secret"
HTTP_PORT="${HTTP_PORT:-18080}"
RTMP_PORT="${RTMP_PORT:-11935}"
WORK_DIR=""
SERVER_PID=""
PUSH_PID=""

cleanup() {
  for pid in "${PUSH_PID}" "${SERVER_PID}"; do
    if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
      wait "${pid}" 2>/dev/null || true
    fi
  done
  if [[ -n "${WORK_DIR}" && "${KEEP_WORK:-0}" != "1" ]]; then
    rm -rf -- "${WORK_DIR}"
  elif [[ -n "${WORK_DIR}" ]]; then
    echo "kept runtime test files in ${WORK_DIR}" >&2
  fi
}
trap cleanup EXIT INT TERM

if [[ -z "${MEDIA_SERVER}" || ! -x "${MEDIA_SERVER}" ]]; then
  echo "Usage: $0 /path/to/MediaServer [/path/to/config.ini]" >&2
  exit 2
fi
MEDIA_SERVER="$(realpath "${MEDIA_SERVER}")"
if [[ -z "${SOURCE_CONFIG}" ]]; then
  SOURCE_CONFIG="$(dirname -- "${MEDIA_SERVER}")/config.ini"
fi
if [[ ! -r "${SOURCE_CONFIG}" ]]; then
  echo "config not readable: ${SOURCE_CONFIG}" >&2
  exit 2
fi
SOURCE_CONFIG="$(realpath "${SOURCE_CONFIG}")"
command -v ffmpeg >/dev/null
command -v curl >/dev/null
command -v python3 >/dev/null

WORK_DIR="$(mktemp -d)"
python3 - "${SOURCE_CONFIG}" "${WORK_DIR}/config.ini" \
  "${API_SECRET}" "${HTTP_PORT}" "${RTMP_PORT}" <<'PY'
import sys

source, destination, secret, http_port, rtmp_port = sys.argv[1:]
section = ""
replacements = {
    ("api", "secret"): secret,
    ("api", "enableStreamQos"): "1",
    ("hook", "enable"): "0",
    ("http", "port"): http_port,
    ("http", "sslport"): "0",
    ("rtmp", "port"): rtmp_port,
    ("rtsp", "port"): "0",
    ("shell", "port"): "0",
}
seen = set()
output = []
with open(source, encoding="utf-8") as handle:
    for raw in handle:
        line = raw.rstrip("\n")
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if section == "api" and ("api", "enableStreamQos") not in seen:
                output.append("enableStreamQos=1")
                seen.add(("api", "enableStreamQos"))
            section = stripped[1:-1]
        if "=" in stripped and not stripped.startswith("#"):
            key = stripped.split("=", 1)[0].strip()
            lookup = (section, key)
            if lookup in replacements:
                line = f"{key}={replacements[lookup]}"
                seen.add(lookup)
        output.append(line)
if section == "api" and ("api", "enableStreamQos") not in seen:
    output.append("enableStreamQos=1")
with open(destination, "w", encoding="utf-8") as handle:
    handle.write("\n".join(output) + "\n")
PY

(
  cd "$(dirname -- "${MEDIA_SERVER}")"
  exec "${MEDIA_SERVER}" -c "${WORK_DIR}/config.ini" -l 0
) >"${WORK_DIR}/zlm.log" 2>&1 &
SERVER_PID=$!

server_ready=0
for _ in $(seq 1 50); do
  if curl --fail --silent \
    "http://127.0.0.1:${HTTP_PORT}/index/api/getServerConfig?secret=${API_SECRET}" \
    >/dev/null; then
    server_ready=1
    break
  fi
  sleep 0.2
done
if ((server_ready == 0)) || ! kill -0 "${SERVER_PID}" 2>/dev/null; then
  cat "${WORK_DIR}/zlm.log" >&2
  exit 1
fi

ffmpeg -nostdin -hide_banner -loglevel error -re \
  -f lavfi -i "testsrc=size=320x180:rate=25" \
  -an -c:v libx264 -preset ultrafast -tune zerolatency \
  -g 25 -bf 0 -t 8 -f flv \
  "rtmp://127.0.0.1:${RTMP_PORT}/live/qos_runtime_test" \
  >"${WORK_DIR}/ffmpeg.log" 2>&1 &
PUSH_PID=$!

stream_online=0
for _ in $(seq 1 50); do
  if curl --fail --silent --get \
    "http://127.0.0.1:${HTTP_PORT}/index/api/isMediaOnline" \
    --data-urlencode "secret=${API_SECRET}" \
    --data-urlencode "schema=rtmp" \
    --data-urlencode "vhost=__defaultVhost__" \
    --data-urlencode "app=live" \
    --data-urlencode "stream=qos_runtime_test" >"${WORK_DIR}/online.json" &&
    python3 -c 'import json,sys; raise SystemExit(not json.load(sys.stdin).get("online"))' \
      <"${WORK_DIR}/online.json"
  then
    stream_online=1
    break
  fi
  sleep 0.2
done
if ((stream_online == 0)); then
  cat "${WORK_DIR}/ffmpeg.log" >&2
  cat "${WORK_DIR}/zlm.log" >&2
  exit 1
fi

curl --fail --silent --get \
  "http://127.0.0.1:${HTTP_PORT}/index/api/getStreamQos" \
  --data-urlencode "secret=${API_SECRET}" \
  --data-urlencode "vhost=__defaultVhost__" \
  --data-urlencode "app=live" \
  --data-urlencode "stream=qos_runtime_test" \
  --data-urlencode "probe_ms=1000" |
  python3 -c '
import json, sys
payload = json.load(sys.stdin)
data = payload.get("data", {})
assert payload.get("code") == 0, payload
assert data.get("videoFrameCount", 0) > 0, data
assert data.get("bitrateKbps", 0) > 0, data
assert "timestampRollbackCount" in data, data
print(json.dumps(data, ensure_ascii=False, sort_keys=True))
'

kill "${PUSH_PID}"
wait "${PUSH_PID}" 2>/dev/null || true
PUSH_PID=""

stream_offline=0
for _ in $(seq 1 50); do
  if curl --fail --silent --get \
    "http://127.0.0.1:${HTTP_PORT}/index/api/isMediaOnline" \
    --data-urlencode "secret=${API_SECRET}" \
    --data-urlencode "schema=rtmp" \
    --data-urlencode "vhost=__defaultVhost__" \
    --data-urlencode "app=live" \
    --data-urlencode "stream=qos_runtime_test" >"${WORK_DIR}/offline.json" &&
    python3 -c 'import json,sys; raise SystemExit(json.load(sys.stdin).get("online") is not False)' \
      <"${WORK_DIR}/offline.json"
  then
    stream_offline=1
    break
  fi
  sleep 0.2
done
if ((stream_offline == 0)); then
  echo "stream did not unregister after publisher exit" >&2
  exit 1
fi

echo "custom ZLM QoS runtime test passed"
