#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${LATENCY_BUILD_DIR:-${TMPDIR:-/tmp}/drone-stream-latency-build}"
PROBE="${LATENCY_PROBE_BIN:-${BUILD_DIR}/latency_probe}"

usage() {
  cat <<'EOF'
Usage:
  scripts/run_latency_experiment.sh --self-test
  scripts/run_latency_experiment.sh PLAYBACK_URL SOURCE_SIDECAR [OUTPUT_CSV]

Example:
  deploy/ffmpeg/push_demo.sh
  scripts/run_latency_experiment.sh \
    http://127.0.0.1/live/drone_001.live.flv \
    /tmp/drone_001.latency-source latency.csv

Environment:
  MAX_FRAMES=250 TIMEOUT_SECONDS=30 LATENCY_PROBE_BIN=/path/to/latency_probe
  BACKEND_URL=http://127.0.0.1:8000 PROTOCOL=flv NETWORK_PROFILE=normal
EOF
}

build_probe() {
  if [[ -n "${LATENCY_PROBE_BIN:-}" ]]; then
    if [[ ! -x "${PROBE}" ]]; then
      printf 'LATENCY_PROBE_BIN is not executable: %s\n' "${PROBE}" >&2
      exit 2
    fi
    return
  fi
  cmake -S "${ROOT_DIR}/cpp-tools" -B "${BUILD_DIR}" -DCMAKE_BUILD_TYPE=Release
  cmake --build "${BUILD_DIR}" --target latency_probe --parallel
}

self_test() {
  build_probe
  local summary
  SELF_TEST_TEMP_DIR="$(mktemp -d)"
  trap 'rm -rf -- "${SELF_TEST_TEMP_DIR:-}"' EXIT

  cat >"${SELF_TEST_TEMP_DIR}/source.sidecar" <<'EOF'
schema=drone-stream-latency-source-v1
clock=CLOCK_REALTIME
source_start_epoch_ns=1000000000000000000
pts_origin_seconds=0
measurement_boundary=offline-self-test
EOF
  cat >"${SELF_TEST_TEMP_DIR}/frames.csv" <<'EOF'
# pts_seconds,receive_epoch_ns
0.000000,1000000000010000000
0.040000,1000000000060000000
0.080000,1000000000110000000
0.120000,1000000000160000000
0.160000,1000000000210000000
EOF

  summary="$("${PROBE}" \
    --timestamps-file "${SELF_TEST_TEMP_DIR}/frames.csv" \
    --sidecar "${SELF_TEST_TEMP_DIR}/source.sidecar" \
    --output "${SELF_TEST_TEMP_DIR}/result.csv")"

  awk -F, '
    NR == 1 {
      if ($0 != "frame,pts_seconds,capture_epoch_ns,receive_epoch_ns,latency_ms") exit 1
      next
    }
    {
      expected = (NR - 1) * 10
      if (($5 + 0) != expected) exit 1
    }
    END { if (NR != 6) exit 1 }
  ' "${SELF_TEST_TEMP_DIR}/result.csv"
  [[ "${summary}" == "samples=5 p50_ms=30.000 p95_ms=48.000 p99_ms=49.600" ]]
  printf 'self-test passed: %s\n' "${summary}"
}

if [[ "${1:-}" == "--self-test" ]]; then
  self_test
  exit 0
fi
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi
if (( $# < 2 || $# > 3 )); then
  usage >&2
  exit 2
fi

build_probe
url="$1"
sidecar="$2"
output="${3:-latency.csv}"

summary="$("${PROBE}" \
  --url "${url}" \
  --sidecar "${sidecar}" \
  --output "${output}" \
  --max-frames "${MAX_FRAMES:-250}" \
  --timeout "${TIMEOUT_SECONDS:-30}")"
printf '%s\n' "${summary}"

if [[ -n "${BACKEND_URL:-}" ]]; then
  command -v python3 >/dev/null 2>&1 || {
    echo "python3 is required to upload experiment results" >&2
    exit 1
  }
  command -v curl >/dev/null 2>&1 || {
    echo "curl is required to upload experiment results" >&2
    exit 1
  }

  read -r sample_count p50 p95 p99 <<<"$(
    sed -nE \
      's/^samples=([0-9]+) p50_ms=([-0-9.]+) p95_ms=([-0-9.]+) p99_ms=([-0-9.]+)$/\1 \2 \3 \4/p' \
      <<<"${summary}"
  )"
  [[ -n "${sample_count:-}" ]] || {
    echo "unable to parse latency summary: ${summary}" >&2
    exit 1
  }

  read -r average maximum <<<"$(
    awk -F, '
      NR > 1 {sum += $5; if (count == 0 || $5 > max) max = $5; count++}
      END {if (!count) exit 1; printf "%.3f %.3f\n", sum / count, max}
    ' "${output}"
  )"

  payload="$(
    python3 - \
      "${EXPERIMENT_NAME:-$(date -u +%Y%m%dT%H%M%SZ)-latency}" \
      "${STREAM_ID:-drone_001}" \
      "${PROTOCOL:-flv}" \
      "${NETWORK_PROFILE:-normal}" \
      "${ENCODER_PARAMS:-x264-zerolatency}" \
      "${average}" "${maximum}" "${p50}" "${p95}" "${p99}" "${sample_count}" <<'PY'
import json
import sys

(
    name,
    stream_id,
    protocol,
    network_profile,
    encoder_params,
    average,
    maximum,
    p50,
    p95,
    p99,
    sample_count,
) = sys.argv[1:]
print(json.dumps({
    "name": name,
    "stream_id": stream_id,
    "protocol": protocol,
    "network_profile": network_profile,
    "encoder_params": encoder_params,
    "avg_latency_ms": float(average),
    "max_latency_ms": float(maximum),
    "p50_latency_ms": float(p50),
    "p95_latency_ms": float(p95),
    "p99_latency_ms": float(p99),
    "sample_count": int(sample_count),
    "measurement_method": "same-host-source-pts",
    "stutter_count": 0,
}))
PY
  )"

  curl --fail --silent --show-error \
    -H 'Content-Type: application/json' \
    -d "${payload}" \
    "${BACKEND_URL%/}/api/experiments/latency"
  printf '\n'
fi
