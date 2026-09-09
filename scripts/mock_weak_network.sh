#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: mock_weak_network.sh apply|clear|show [options]

Options:
  --dev DEVICE       Network interface (default: $DEV or lo)
  --rate RATE        Bandwidth, for example 4mbit (default: $RATE or 4mbit)
  --delay MS         One-way delay in milliseconds (default: $DELAY_MS or 120)
  --loss PERCENT     Packet loss percentage, 0..100 (default: $LOSS_PERCENT or 2)
  --burst SIZE       TBF burst size (default: $BURST or 32kbit)
  --latency MS       TBF queue latency (default: $LATENCY_MS or 400)
  --dry-run          Print commands without running tc or sudo
  -h, --help         Show this help

The hierarchy is HTB root -> TBF rate limiter -> netem.
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 2
}

ACTION="${1:-}"
[[ -n "${ACTION}" ]] || { usage >&2; exit 2; }
shift

DEV="${DEV:-lo}"
RATE="${RATE:-4mbit}"
DELAY_MS="${DELAY_MS:-120}"
LOSS_PERCENT="${LOSS_PERCENT:-2}"
BURST="${BURST:-32kbit}"
LATENCY_MS="${LATENCY_MS:-400}"
DRY_RUN=0

while (($#)); do
  case "$1" in
    --dev|--rate|--delay|--loss|--burst|--latency)
      (($# >= 2)) || die "$1 requires a value"
      case "$1" in
        --dev) DEV="$2" ;;
        --rate) RATE="$2" ;;
        --delay) DELAY_MS="$2" ;;
        --loss) LOSS_PERCENT="$2" ;;
        --burst) BURST="$2" ;;
        --latency) LATENCY_MS="$2" ;;
      esac
      shift 2
      ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
done

case "${ACTION}" in
  apply|clear|show) ;;
  *) die "action must be apply, clear, or show" ;;
esac

[[ "${DEV}" =~ ^[[:alnum:]_.:@-]+$ ]] || die "invalid device: ${DEV}"
[[ "${RATE}" =~ ^[1-9][0-9]*([.][0-9]+)?(bit|kbit|mbit|gbit)$ ]] ||
  die "invalid rate: ${RATE}"
[[ "${BURST}" =~ ^[1-9][0-9]*([.][0-9]+)?(b|bit|kbit|kb|mbit|mb)$ ]] ||
  die "invalid burst: ${BURST}"
[[ "${DELAY_MS}" =~ ^[0-9]+([.][0-9]+)?$ ]] || die "delay must be non-negative"
[[ "${LATENCY_MS}" =~ ^[0-9]+([.][0-9]+)?$ ]] || die "latency must be non-negative"
[[ "${LOSS_PERCENT}" =~ ^[0-9]+([.][0-9]+)?$ ]] ||
  die "loss must be a number between 0 and 100"
awk -v loss="${LOSS_PERCENT}" 'BEGIN { exit !(loss >= 0 && loss <= 100) }' ||
  die "loss must be between 0 and 100"

print_command() {
  printf '+'
  printf ' %q' "$@"
  printf '\n'
}

run_tc() {
  if ((DRY_RUN)); then
    print_command tc "$@"
  elif ((EUID == 0)); then
    tc "$@"
  else
    sudo tc "$@"
  fi
}

show_qdisc() {
  if ((DRY_RUN)); then
    print_command tc -s qdisc show dev "${DEV}"
    print_command tc -s class show dev "${DEV}"
  else
    tc -s qdisc show dev "${DEV}"
    tc -s class show dev "${DEV}"
  fi
}

clear_qdisc() {
  local qdiscs
  if ((DRY_RUN)); then
    run_tc qdisc del dev "${DEV}" root
    return
  fi

  qdiscs="$(tc qdisc show dev "${DEV}")"
  if grep -Eq '^qdisc (noqueue|mq) .* root' <<<"${qdiscs}"; then
    printf 'no configurable root qdisc on %s\n' "${DEV}"
    return
  fi
  run_tc qdisc del dev "${DEV}" root
}

verify_applied() {
  local qdiscs classes
  qdiscs="$(tc qdisc show dev "${DEV}")"
  classes="$(tc class show dev "${DEV}")"
  grep -Eq 'qdisc htb 1:' <<<"${qdiscs}" || die "verification failed: HTB 1: missing"
  grep -Eq 'qdisc tbf 10:' <<<"${qdiscs}" || die "verification failed: TBF 10: missing"
  grep -Eq 'qdisc netem 20:' <<<"${qdiscs}" || die "verification failed: netem 20: missing"
  grep -Eq 'class htb 1:1 ' <<<"${classes}" || die "verification failed: class 1:1 missing"
  printf 'qdisc hierarchy verified on %s\n' "${DEV}"
}

if ((!DRY_RUN)); then
  command -v tc >/dev/null 2>&1 || die "tc is required (install iproute2)"
  if [[ "${ACTION}" != "show" ]] && ((EUID != 0)); then
    command -v sudo >/dev/null 2>&1 || die "sudo is required for ${ACTION}"
  fi
fi

case "${ACTION}" in
  apply)
    run_tc qdisc replace dev "${DEV}" root handle 1: htb default 1
    run_tc class replace dev "${DEV}" parent 1: classid 1:1 htb \
      rate "${RATE}" ceil "${RATE}"
    run_tc qdisc replace dev "${DEV}" parent 1:1 handle 10: tbf \
      rate "${RATE}" burst "${BURST}" latency "${LATENCY_MS}ms"
    run_tc qdisc replace dev "${DEV}" parent 10:1 handle 20: netem \
      delay "${DELAY_MS}ms" loss "${LOSS_PERCENT}%"
    if ((DRY_RUN)); then
      printf '# verification not executed in dry-run\n'
      show_qdisc
    else
      verify_applied
      show_qdisc
    fi
    ;;
  clear)
    clear_qdisc
    ;;
  show)
    show_qdisc
    ;;
esac
