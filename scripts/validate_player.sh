#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PLAYER_FILE="${ROOT_DIR}/frontend/src/components/VideoPlayer.vue"
SHARE_PAGE_FILE="${ROOT_DIR}/frontend/src/views/SharePlayback.vue"
SHARE_PANEL_FILE="${ROOT_DIR}/frontend/src/components/StreamSharePanel.vue"
ROUTER_FILE="${ROOT_DIR}/frontend/src/router/index.ts"

require_pattern() {
  local file="$1"
  local pattern="$2"
  local description="$3"
  if ! grep -Fq -- "${pattern}" "${file}"; then
    echo "missing player contract: ${description}" >&2
    exit 1
  fi
}

require_pattern "${PLAYER_FILE}" "const RECONNECT_DELAY_MS = 3000;" "three-second reconnect delay"
require_pattern "${PLAYER_FILE}" "const MAX_RECONNECT_ATTEMPTS = 5;" "five-attempt reconnect limit"
require_pattern "${PLAYER_FILE}" "function retryPlayback()" "manual retry action"
require_pattern "${PLAYER_FILE}" "mpegts.Events.ERROR" "mpegts error listener"
require_pattern "${PLAYER_FILE}" "mpegts.Events.LOADING_COMPLETE" "stream completion listener"
require_pattern "${PLAYER_FILE}" "video.addEventListener(\"playing\"" "native playing listener"
require_pattern "${PLAYER_FILE}" "video.addEventListener(\"error\"" "native video error listener"
require_pattern "${PLAYER_FILE}" "window.clearTimeout(reconnectTimer)" "reconnect timer cleanup"

for entry in \
  "${SHARE_PAGE_FILE}|<VideoPlayer v-if=\"mediaUrl\" :url=\"mediaUrl\" />|shared player rendering" \
  "${SHARE_PAGE_FILE}|parsed.protocol === \"http:\" || parsed.protocol === \"https:\"|shared URL protocol guard" \
  "${SHARE_PANEL_FILE}|navigator.clipboard|clipboard copy path" \
  "${SHARE_PANEL_FILE}|document.execCommand(\"copy\")|clipboard fallback path" \
  "${ROUTER_FILE}|path: \"/play/share\"|share route"; do
  IFS="|" read -r file pattern description <<< "${entry}"
  require_pattern "${file}" "${pattern}" "${description}"
done

require_pattern "${ROOT_DIR}/frontend/src/views/LiveMonitor.vue" "StreamSharePanel" "share link panel"

echo "player source checks passed"

cd "${ROOT_DIR}/frontend"
npm run build

echo "player validation passed"
