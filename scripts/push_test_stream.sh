#!/usr/bin/env bash
set -euo pipefail

# 一键演示脚本。
# 执行顺序：注册视频源 -> 调用 FFmpeg 推送到 ZLM -> 输出 HTTP-FLV 地址。
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

STREAM_ID="${STREAM_ID:-stream_001}"
RTMP_URL="${RTMP_URL:-rtmp://127.0.0.1/live/${STREAM_ID}}"
BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"

if [[ ! "${STREAM_ID}" =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo "STREAM_ID may only contain letters, numbers, underscore, and hyphen" >&2
  exit 2
fi

# 先在业务数据库登记 stream_id。
# 201 表示新登记；409 表示此前已经登记，可以直接继续推流。
status="$(
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"Demo source ${STREAM_ID}\",\"stream_id\":\"${STREAM_ID}\"}" \
    "${BACKEND_URL}/api/devices"
)"
case "${status}" in
  201) echo "Registered demo device ${STREAM_ID}" ;;
  409) echo "Demo device ${STREAM_ID} already exists" ;;
  *)
    echo "Failed to register demo device: backend returned HTTP ${status}" >&2
    exit 1
    ;;
esac

echo "Pushing stream to ${RTMP_URL}"
echo "HTTP-FLV playback: http://127.0.0.1:8080/live/${STREAM_ID}.live.flv"

export STREAM_ID RTMP_URL
# 将输入文件和推流参数交给底层 FFmpeg 脚本，当前脚本本身不启动 ffmpeg 子进程。
exec "${PROJECT_ROOT}/deploy/ffmpeg/push_demo.sh" "${1:-}"
