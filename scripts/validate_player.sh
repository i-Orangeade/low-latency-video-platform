#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PLAYER_FILE="${ROOT_DIR}/frontend/src/components/VideoPlayer.vue"

require_pattern() {
  local pattern="$1"
  local description="$2"
  if ! grep -Fq -- "${pattern}" "${PLAYER_FILE}"; then
    echo "missing player contract: ${description}" >&2
    exit 1
  fi
}

require_pattern "const RECONNECT_DELAY_MS = 3000;" "three-second reconnect delay"
require_pattern "const MAX_RECONNECT_ATTEMPTS = 5;" "five-attempt reconnect limit"
require_pattern "function retryPlayback()" "manual retry action"
require_pattern "mpegts.Events.ERROR" "mpegts error listener"
require_pattern "mpegts.Events.LOADING_COMPLETE" "stream completion listener"
require_pattern "video.addEventListener(\"playing\"" "native playing listener"
require_pattern "video.addEventListener(\"error\"" "native video error listener"
require_pattern "window.clearTimeout(reconnectTimer)" "reconnect timer cleanup"

echo "player source checks passed"

cd "${ROOT_DIR}/frontend"
npm run build

echo "player validation passed"
