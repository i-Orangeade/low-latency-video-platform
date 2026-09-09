#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEAK_NETWORK="${SCRIPT_DIR}/mock_weak_network.sh"
LOAD_TEST="${SCRIPT_DIR}/load_test_streams.sh"

tmp_dir="$(mktemp -d)"
trap 'rm -rf "${tmp_dir}"' EXIT

pass_count=0

pass() {
  printf 'ok %d - %s\n' "$((++pass_count))" "$1"
}

fail() {
  printf 'not ok - %s\n' "$1" >&2
  exit 1
}

assert_contains() {
  local file="$1" pattern="$2" description="$3"
  grep -Fq -- "${pattern}" "${file}" || fail "${description}"
  pass "${description}"
}

bash -n "${WEAK_NETWORK}" "${LOAD_TEST}" "$0"
pass "shell syntax is valid"

weak_output="${tmp_dir}/weak.out"
bash "${WEAK_NETWORK}" apply \
  --dev test0 --rate 3mbit --delay 80 --loss 1.5 \
  --burst 24kbit --latency 300 --dry-run >"${weak_output}"

assert_contains "${weak_output}" "root handle 1: htb" "dry-run creates an HTB root"
assert_contains "${weak_output}" "parent 1:1 handle 10: tbf" "dry-run attaches TBF to HTB"
assert_contains "${weak_output}" "parent 10:1 handle 20: netem" "dry-run attaches netem below TBF"
assert_contains "${weak_output}" "delay 80ms loss 1.5%" "delay and loss are propagated"
assert_contains "${weak_output}" "tc -s qdisc show dev test0" "dry-run includes qdisc verification commands"

if grep -Eq '(^|[[:space:]])sudo([[:space:]]|$)' "${weak_output}"; then
  fail "dry-run must not invoke sudo"
fi
pass "weak-network dry-run does not invoke sudo"

bash "${WEAK_NETWORK}" clear --dev test0 --dry-run >"${tmp_dir}/clear.out"
bash "${WEAK_NETWORK}" show --dev test0 --dry-run >"${tmp_dir}/show.out"
pass "clear and show support dry-run"

if bash "${WEAK_NETWORK}" apply --loss 100.01 --dry-run >"${tmp_dir}/bad.out" 2>&1; then
  fail "loss above 100 must be rejected"
fi
pass "invalid weak-network parameters are rejected"

load_output="${tmp_dir}/load.out"
bash "${LOAD_TEST}" --streams 3 --duration 7 --prefix drone \
  --base-url rtmp://127.0.0.1/live --dry-run >"${load_output}"

assert_contains "${load_output}" "rtmp://127.0.0.1/live/drone_001" "first stream ID is generated"
assert_contains "${load_output}" "rtmp://127.0.0.1/live/drone_002" "second stream ID is generated"
assert_contains "${load_output}" "rtmp://127.0.0.1/live/drone_003" "third stream ID is generated"
assert_contains "${load_output}" "-t 7" "configured duration is propagated"

ffmpeg_count="$(grep -c '^+ ffmpeg ' "${load_output}")"
[[ "${ffmpeg_count}" == "3" ]] || fail "expected 3 ffmpeg commands, got ${ffmpeg_count}"
pass "load dry-run emits one ffmpeg process per stream"

if grep -Eq '(^|[[:space:]])sudo([[:space:]]|$)' "${load_output}"; then
  fail "load dry-run must not invoke sudo"
fi
pass "load dry-run does not invoke sudo"

touch "${tmp_dir}/source.flv"
bash "${LOAD_TEST}" --streams 1 --duration 7 \
  --input "${tmp_dir}/source.flv" --ramp-ms 25 --dry-run \
  >"${tmp_dir}/copy-load.out"
assert_contains "${tmp_dir}/copy-load.out" "-stream_loop -1" "pre-encoded input is looped"
assert_contains "${tmp_dir}/copy-load.out" "-c:v copy" "pre-encoded input avoids re-encoding"

if bash "${LOAD_TEST}" --streams 0 --dry-run >"${tmp_dir}/bad-load.out" 2>&1; then
  fail "zero streams must be rejected"
fi
pass "invalid load-test parameters are rejected"

if bash "${LOAD_TEST}" --ramp-ms invalid --dry-run >"${tmp_dir}/bad-ramp.out" 2>&1; then
  fail "invalid publisher ramp must be rejected"
fi
pass "invalid publisher ramp is rejected"

printf '1..%d\n' "${pass_count}"
