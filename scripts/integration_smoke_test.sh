#!/usr/bin/env bash
set -euo pipefail

# 端到端冒烟测试。
# 验证范围：
# 1. FastAPI 健康检查；
# 2. 通过 API 登记视频源；
# 3. FFmpeg 向 ZLM 推送 RTMP；
# 4. FastAPI 能从 ZLM 查询到流上线；
# 5. 停止推流后最终查询到流离线。
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"
STREAM_ID="${STREAM_ID:-smoke_001}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-30}"
PUSH_PID=""

cleanup() {
  # 无论测试成功、失败还是被中断，都终止后台 FFmpeg 推流进程。
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

# 先通过业务 API 注册视频源；409 表示测试流已经注册过，也可继续执行。
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

# 后台启动 FFmpeg，保留 PID 便于测试结束后可靠清理。
STREAM_ID="${STREAM_ID}" \
RTMP_URL="rtmp://127.0.0.1/live/${STREAM_ID}" \
  "${ROOT_DIR}/deploy/ffmpeg/push_demo.sh" >"/tmp/${STREAM_ID}-push.log" 2>&1 &
PUSH_PID=$!

wait_for_state() {
  # 轮询后端状态接口，等待 ZLM 感知流上线或离线，避免固定 sleep 造成偶发失败。
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

# 停止推流后继续等待离线，验证状态不是只会上线而不会回落。
kill "${PUSH_PID}"
wait "${PUSH_PID}" 2>/dev/null || true
PUSH_PID=""
wait_for_state false

echo "integration smoke test passed for ${STREAM_ID}"
