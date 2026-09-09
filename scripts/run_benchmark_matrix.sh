#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
COUNTS="${COUNTS:-1 10 50 100}"
DURATION="${DURATION:-120}"
WARMUP="${WARMUP:-15}"
SAMPLE_INTERVAL="${SAMPLE_INTERVAL:-1}"
RAMP_MS="${RAMP_MS:-20}"
STARTUP_TIMEOUT="${STARTUP_TIMEOUT:-60}"
RESULT_ROOT="${RESULT_ROOT:-${ROOT_DIR}/benchmark-results/$(date -u +%Y%m%dT%H%M%SZ)}"
ZLM_CONTAINER="${ZLM_CONTAINER:-drone-zlm}"
ZLM_URL="${ZLM_URL:-http://127.0.0.1:8080}"
BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"
LOAD_PID=""
STATS_PID=""

cleanup() {
  if [[ -n "${LOAD_PID}" ]] && kill -0 "${LOAD_PID}" 2>/dev/null; then
    kill "${LOAD_PID}" 2>/dev/null || true
    wait "${LOAD_PID}" 2>/dev/null || true
  fi
  if [[ -n "${STATS_PID}" ]] && kill -0 "${STATS_PID}" 2>/dev/null; then
    kill "${STATS_PID}" 2>/dev/null || true
    wait "${STATS_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

for command in docker ffmpeg curl python3; do
  command -v "${command}" >/dev/null || {
    echo "missing required command: ${command}" >&2
    exit 2
  }
done
if [[ -z "${DRONE_STREAM_ZLM_SECRET:-}" ]]; then
  echo "DRONE_STREAM_ZLM_SECRET must be set" >&2
  exit 2
fi
[[ "${DURATION}" =~ ^[1-9][0-9]*$ ]] || { echo "invalid DURATION" >&2; exit 2; }
[[ "${WARMUP}" =~ ^[0-9]+$ ]] || { echo "invalid WARMUP" >&2; exit 2; }
[[ "${STARTUP_TIMEOUT}" =~ ^[1-9][0-9]*$ ]] || {
  echo "invalid STARTUP_TIMEOUT" >&2
  exit 2
}
((WARMUP < DURATION)) || { echo "WARMUP must be less than DURATION" >&2; exit 2; }

mkdir -p "${RESULT_ROOT}"
SOURCE_FILE="${RESULT_ROOT}/benchmark-source.flv"
ffmpeg -y -hide_banner -loglevel error \
  -f lavfi -i "testsrc2=size=1280x720:rate=25" \
  -t 4 -c:v libx264 -preset ultrafast -tune zerolatency \
  -b:v 1500k -maxrate 1500k -bufsize 1500k \
  -g 50 -pix_fmt yuv420p -an -f flv "${SOURCE_FILE}"
{
  echo "timestamp_utc=$(date -u +%FT%TZ)"
  echo "counts=${COUNTS}"
  echo "duration_seconds=${DURATION}"
  echo "warmup_seconds=${WARMUP}"
  echo "sample_interval_seconds=${SAMPLE_INTERVAL}"
  echo "publisher_ramp_ms=${RAMP_MS}"
  echo "startup_timeout_seconds=${STARTUP_TIMEOUT}"
  echo "load_source=pre-encoded H.264 copy"
  echo "git_commit=$(git -C "${ROOT_DIR}" rev-parse HEAD 2>/dev/null || echo unknown)"
  echo "kernel=$(uname -srvmo)"
  echo "cpu_count=$(nproc)"
  echo "ffmpeg=$(ffmpeg -version | sed -n '1p')"
  echo "docker=$(docker version --format '{{.Server.Version}}')"
} >"${RESULT_ROOT}/environment.txt"

for count in ${COUNTS}; do
  [[ "${count}" =~ ^[1-9][0-9]*$ ]] || {
    echo "invalid stream count: ${count}" >&2
    exit 2
  }
  run_dir="${RESULT_ROOT}/streams-${count}"
  mkdir -p "${run_dir}"
  : >"${run_dir}/media-list.jsonl"
  echo "starting ${count}-stream benchmark"

  for ((index = 1; index <= count; index++)); do
    printf -v stream_id 'bench%s_%03d' "${count}" "${index}"
    status="$(
      curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
        -H 'Content-Type: application/json' \
        -d "{\"name\":\"Benchmark ${stream_id}\",\"stream_id\":\"${stream_id}\",\"enabled\":true}" \
        "${BACKEND_URL}/api/devices"
    )"
    if [[ "${status}" != "201" && "${status}" != "409" ]]; then
      echo "failed to register ${stream_id}: HTTP ${status}" >&2
      exit 1
    fi
  done

  "${ROOT_DIR}/scripts/load_test_streams.sh" \
    --streams "${count}" \
    --duration "$((DURATION + STARTUP_TIMEOUT + (count * RAMP_MS + 999) / 1000))" \
    --prefix "bench${count}" \
    --input "${SOURCE_FILE}" \
    --ramp-ms "${RAMP_MS}" \
    >"${run_dir}/load.log" 2>&1 &
  LOAD_PID=$!

  sleep "${WARMUP}"
  ready_deadline=$((SECONDS + STARTUP_TIMEOUT))
  online_count=0
  while ((SECONDS < ready_deadline)); do
    online_count="$(
      curl --fail --silent --get "${ZLM_URL}/index/api/getMediaList" \
        --data-urlencode "secret=${DRONE_STREAM_ZLM_SECRET}" \
        --data-urlencode "vhost=__defaultVhost__" \
        --data-urlencode "app=live" |
        python3 -c 'import json,sys; print(len({x["stream"] for x in json.load(sys.stdin).get("data", [])}))'
    )"
    if ((online_count >= count)); then
      break
    fi
    if ! kill -0 "${LOAD_PID}" 2>/dev/null; then
      echo "load generator exited before all streams registered" >&2
      wait "${LOAD_PID}" || true
      exit 1
    fi
    sleep 1
  done
  if ((online_count < count)); then
    echo "timed out waiting for ${count} streams; observed ${online_count}" >&2
    exit 1
  fi

  measurement_seconds=$((DURATION - WARMUP))
  python3 - "${run_dir}/docker-stats.jsonl" "${ZLM_CONTAINER}" \
    "${measurement_seconds}" "${SAMPLE_INTERVAL}" <<'PY' &
import http.client
import json
import socket
import sys
import time


class UnixHttpConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect("/var/run/docker.sock")


output_path, container, duration, interval = sys.argv[1:]
deadline = time.monotonic() + float(duration)
with open(output_path, "w", encoding="utf-8") as output:
    while time.monotonic() < deadline:
        connection = UnixHttpConnection("localhost", timeout=5)
        connection.request(
            "GET", f"/containers/{container}/stats?stream=false"
        )
        response = connection.getresponse()
        if response.status != 200:
            raise RuntimeError(f"Docker stats returned HTTP {response.status}")
        item = json.loads(response.read())
        connection.close()

        cpu = item.get("cpu_stats", {})
        previous_cpu = item.get("precpu_stats", {})
        cpu_delta = (
            cpu.get("cpu_usage", {}).get("total_usage", 0)
            - previous_cpu.get("cpu_usage", {}).get("total_usage", 0)
        )
        system_delta = (
            cpu.get("system_cpu_usage", 0)
            - previous_cpu.get("system_cpu_usage", 0)
        )
        online_cpus = cpu.get("online_cpus") or len(
            cpu.get("cpu_usage", {}).get("percpu_usage", [])
        ) or 1
        cpu_percent = (
            cpu_delta / system_delta * online_cpus * 100
            if cpu_delta > 0 and system_delta > 0
            else 0
        )

        memory = item.get("memory_stats", {})
        cache = memory.get("stats", {}).get(
            "inactive_file",
            memory.get("stats", {}).get("cache", 0),
        )
        networks = list(item.get("networks", {}).values())
        sample = {
            "timestamp": time.time(),
            "cpu_percent": cpu_percent,
            "memory_bytes": max(0, memory.get("usage", 0) - cache),
            "network_rx_bytes": sum(value.get("rx_bytes", 0) for value in networks),
            "network_tx_bytes": sum(value.get("tx_bytes", 0) for value in networks),
        }
        output.write(json.dumps(sample, separators=(",", ":")) + "\n")
        output.flush()
        time.sleep(float(interval))
PY
  STATS_PID=$!
  sample_end=$((SECONDS + DURATION - WARMUP))
  while ((SECONDS < sample_end)); do
    snapshot="$(
      curl --fail --silent --get "${ZLM_URL}/index/api/getMediaList" \
      --data-urlencode "secret=${DRONE_STREAM_ZLM_SECRET}" \
      --data-urlencode "vhost=__defaultVhost__" \
      --data-urlencode "app=live" \
    )"
    printf '%s' "${snapshot}" |
      python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)))' \
      >>"${run_dir}/media-list.jsonl"
    online_count="$(
      printf '%s' "${snapshot}" |
        python3 -c 'import json,sys; print(len({x["stream"] for x in json.load(sys.stdin).get("data", [])}))'
    )"
    if ((online_count < count)); then
      echo "expected at least ${count} media sources, observed ${online_count}" >&2
      exit 1
    fi
    sleep "${SAMPLE_INTERVAL}"
  done
  wait "${STATS_PID}" 2>/dev/null || true
  STATS_PID=""

  printf -v sample_stream 'bench%s_%03d' "${count}" "${count}"
  STREAM_ID="${sample_stream}" \
    "${ROOT_DIR}/scripts/query_stream_qos.sh" "${sample_stream}" 3000 \
    >"${run_dir}/qos.json"

  kill "${LOAD_PID}" 2>/dev/null || true
  wait "${LOAD_PID}" 2>/dev/null || true
  LOAD_PID=""
  tc -s qdisc show >"${run_dir}/qdisc.txt" 2>&1 || true
done

python3 - "${RESULT_ROOT}" <<'PY'
import json
import pathlib
import statistics
import sys

root = pathlib.Path(sys.argv[1])
rows = []
for run_dir in sorted(root.glob("streams-*"), key=lambda p: int(p.name.split("-")[1])):
    qos = json.loads((run_dir / "qos.json").read_text())
    data = qos.get("data", {})
    stats = []
    memory_bytes = []
    network_samples = []
    media_counts = []
    for line in (run_dir / "docker-stats.jsonl").read_text().splitlines():
        item = json.loads(line)
        stats.append(float(item["cpu_percent"]))
        memory_bytes.append(float(item["memory_bytes"]))
        network_samples.append((
            float(item["timestamp"]),
            float(item["network_rx_bytes"]),
            float(item["network_tx_bytes"]),
        ))
    for line in (run_dir / "media-list.jsonl").read_text().splitlines():
        payload = json.loads(line)
        media_counts.append(len({
            item["stream"] for item in payload.get("data", [])
        }))
    elapsed = (
        max(0.001, network_samples[-1][0] - network_samples[0][0])
        if len(network_samples) > 1 else 1
    )
    rows.append({
        "streams": int(run_dir.name.split("-")[1]),
        "samples": len(stats),
        "online_streams_min": min(media_counts) if media_counts else None,
        "online_streams_max": max(media_counts) if media_counts else None,
        "cpu_mean_percent": statistics.fmean(stats) if stats else None,
        "cpu_p95_percent": (
            sorted(stats)[max(0, int(len(stats) * 0.95 + 0.999999) - 1)]
            if stats else None
        ),
        "container_memory_mean_mib": (
            statistics.fmean(memory_bytes) / 1024 ** 2 if memory_bytes else None
        ),
        "container_memory_p95_mib": (
            sorted(memory_bytes)[max(0, int(len(memory_bytes) * 0.95 + 0.999999) - 1)]
            / 1024 ** 2
            if memory_bytes else None
        ),
        "network_rx_kbps": (
            (network_samples[-1][1] - network_samples[0][1]) * 8 / elapsed / 1000
            if len(network_samples) > 1 else None
        ),
        "network_tx_kbps": (
            (network_samples[-1][2] - network_samples[0][2]) * 8 / elapsed / 1000
            if len(network_samples) > 1 else None
        ),
        "sample_stream_bitrate_kbps": data.get("bitrateKbps"),
        "sample_stream_video_fps": data.get("videoFps"),
        "sample_stream_timestamp_rollbacks": data.get("timestampRollbackCount"),
    })
(root / "summary.json").write_text(
    json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(root / "summary.json")
PY

echo "benchmark matrix complete: ${RESULT_ROOT}"
