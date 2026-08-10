#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-show}"
DEV="${DEV:-lo}"
DELAY_MS="${DELAY_MS:-120}"
LOSS_PERCENT="${LOSS_PERCENT:-2}"
RATE="${RATE:-4mbit}"

case "${ACTION}" in
  apply)
    sudo tc qdisc replace dev "${DEV}" root netem delay "${DELAY_MS}ms" loss "${LOSS_PERCENT}%"
    sudo tc qdisc add dev "${DEV}" parent 1:1 handle 10: tbf rate "${RATE}" burst 32kbit latency 400ms 2>/dev/null || true
    ;;
  clear)
    sudo tc qdisc del dev "${DEV}" root 2>/dev/null || true
    ;;
  show)
    tc qdisc show dev "${DEV}"
    ;;
  *)
    echo "Usage: $0 apply|clear|show"
    exit 1
    ;;
esac
