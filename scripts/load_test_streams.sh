#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: load_test_streams.sh [options]

Options:
  -n, --streams N       Concurrent streams (default: 4)
  -d, --duration SEC    Duration of each stream (default: 60)
  --base-url URL        RTMP application URL (default: rtmp://127.0.0.1/live)
  --prefix PREFIX       Stream ID prefix (default: loadtest)
  --size WIDTHxHEIGHT   Generated video size (default: 1280x720)
  --fps FPS             Generated video frame rate (default: 25)
  --bitrate RATE        Encoder bitrate (default: 1500k)
  --input FILE          Loop a pre-encoded input and copy H.264 instead of encoding
  --ramp-ms MS          Delay between publisher starts (default: 0)
  --dry-run             Print ffmpeg commands without starting them
  -h, --help            Show this help

Stream IDs are PREFIX_001 through PREFIX_NNN.
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 2
}

STREAMS="${STREAMS:-4}"
DURATION="${DURATION:-60}"
BASE_URL="${BASE_URL:-rtmp://127.0.0.1/live}"
PREFIX="${PREFIX:-loadtest}"
VIDEO_SIZE="${VIDEO_SIZE:-1280x720}"
FPS="${FPS:-25}"
BITRATE="${BITRATE:-1500k}"
INPUT_FILE="${INPUT_FILE:-}"
RAMP_MS="${RAMP_MS:-0}"
DRY_RUN=0

while (($#)); do
  case "$1" in
    -n|--streams)
      (($# >= 2)) || die "$1 requires a value"
      STREAMS="$2"
      shift 2
      ;;
    -d|--duration)
      (($# >= 2)) || die "$1 requires a value"
      DURATION="$2"
      shift 2
      ;;
    --base-url|--prefix|--size|--fps|--bitrate|--input|--ramp-ms)
      (($# >= 2)) || die "$1 requires a value"
      case "$1" in
        --base-url) BASE_URL="$2" ;;
        --prefix) PREFIX="$2" ;;
        --size) VIDEO_SIZE="$2" ;;
        --fps) FPS="$2" ;;
        --bitrate) BITRATE="$2" ;;
        --input) INPUT_FILE="$2" ;;
        --ramp-ms) RAMP_MS="$2" ;;
      esac
      shift 2
      ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
done

[[ "${STREAMS}" =~ ^[1-9][0-9]*$ ]] || die "streams must be a positive integer"
[[ "${DURATION}" =~ ^[1-9][0-9]*([.][0-9]+)?$ ]] || die "duration must be positive"
[[ "${FPS}" =~ ^[1-9][0-9]*$ ]] || die "fps must be a positive integer"
[[ "${RAMP_MS}" =~ ^[0-9]+$ ]] || die "ramp-ms must be a non-negative integer"
[[ "${VIDEO_SIZE}" =~ ^[1-9][0-9]*x[1-9][0-9]*$ ]] ||
  die "size must have the form WIDTHxHEIGHT"
[[ "${BITRATE}" =~ ^[1-9][0-9]*([kKmM])?$ ]] || die "invalid bitrate: ${BITRATE}"
[[ "${PREFIX}" =~ ^[[:alnum:]_-]+$ ]] || die "prefix may contain letters, digits, _ and -"
[[ "${BASE_URL}" =~ ^rtmps?://[^[:space:]]+$ ]] || die "base-url must be an RTMP URL"
BASE_URL="${BASE_URL%/}"
if [[ -n "${INPUT_FILE}" ]]; then
  [[ -r "${INPUT_FILE}" ]] || die "input file is not readable: ${INPUT_FILE}"
  INPUT_FILE="$(realpath "${INPUT_FILE}")"
fi

if ((!DRY_RUN)); then
  command -v ffmpeg >/dev/null 2>&1 || die "ffmpeg is required"
fi

pids=()
stream_ids=()

cleanup() {
  local pid
  trap - EXIT INT TERM
  for pid in "${pids[@]:-}"; do
    if kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
    fi
  done
  for pid in "${pids[@]:-}"; do
    wait "${pid}" 2>/dev/null || true
  done
}

on_signal() {
  cleanup
  exit 130
}

trap cleanup EXIT
trap on_signal INT TERM

print_command() {
  printf '+'
  printf ' %q' "$@"
  printf '\n'
}

for ((i = 1; i <= STREAMS; i++)); do
  printf -v stream_id '%s_%03d' "${PREFIX}" "${i}"
  output_url="${BASE_URL}/${stream_id}"
  if [[ -n "${INPUT_FILE}" ]]; then
    command=(
      ffmpeg -hide_banner -loglevel warning -re -stream_loop -1
      -i "${INPUT_FILE}" -t "${DURATION}"
      -map 0:v:0 -c:v copy -an -f flv "${output_url}"
    )
  else
    command=(
      ffmpeg -hide_banner -loglevel warning -re
      -f lavfi -i "testsrc2=size=${VIDEO_SIZE}:rate=${FPS}"
      -t "${DURATION}"
      -c:v libx264 -preset ultrafast -tune zerolatency
      -b:v "${BITRATE}" -maxrate "${BITRATE}" -bufsize "${BITRATE}"
      -g "$((FPS * 2))" -pix_fmt yuv420p
      -an -f flv "${output_url}"
    )
  fi

  if ((DRY_RUN)); then
    print_command "${command[@]}"
  else
    printf 'starting %-20s -> %s\n' "${stream_id}" "${output_url}"
    "${command[@]}" &
    pids+=("$!")
    stream_ids+=("${stream_id}")
    if ((RAMP_MS > 0 && i < STREAMS)); then
      sleep "$(printf '%d.%03d' "$((RAMP_MS / 1000))" "$((RAMP_MS % 1000))")"
    fi
  fi
done

if ((DRY_RUN)); then
  printf 'dry-run: %d stream(s), %s second(s)\n' "${STREAMS}" "${DURATION}"
  exit 0
fi

status=0
for i in "${!pids[@]}"; do
  if ! wait "${pids[$i]}"; then
    printf 'stream failed: %s (pid %s)\n' "${stream_ids[$i]}" "${pids[$i]}" >&2
    status=1
  fi
done

exit "${status}"
