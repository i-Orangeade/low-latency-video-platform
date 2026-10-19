#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing .env. Copy .env.example first: cp .env.example .env" >&2
  exit 1
fi

detect_default_ip() {
  local interface
  interface="${NETWORK_INTERFACE:-$(
    ip -4 route show default |
      awk '$1 == "default" { print $5; exit }'
  )}"
  if [[ -z "${interface}" ]]; then
    echo "Could not determine the default network interface" >&2
    exit 1
  fi

  ip -4 -o addr show dev "${interface}" scope global |
    awk 'NR == 1 { split($4, address, "/"); print address[1] }'
}

is_ipv4() {
  local value="$1"
  local -a octets
  local octet

  IFS=. read -r -a octets <<< "${value}"
  [[ ${#octets[@]} -eq 4 ]] || return 1
  for octet in "${octets[@]}"; do
    [[ "${octet}" =~ ^[0-9]{1,3}$ ]] || return 1
    ((10#${octet} <= 255)) || return 1
  done
}

public_ip="${1:-$(detect_default_ip)}"

if ! is_ipv4 "${public_ip}"; then
  echo "Invalid IPv4 address: ${public_ip}" >&2
  exit 2
fi

tmp_file="$(mktemp "${ENV_FILE}.XXXXXX")"
trap 'rm -f "${tmp_file}"' EXIT
awk -v value="${public_ip}" '
  BEGIN { replaced = 0 }
  /^LLVP_PUBLIC_ZLM_HOST=/ {
    print "LLVP_PUBLIC_ZLM_HOST=" value
    replaced = 1
    next
  }
  { print }
  END {
    if (!replaced) {
      print "LLVP_PUBLIC_ZLM_HOST=" value
    }
  }
' "${ENV_FILE}" > "${tmp_file}"
mv "${tmp_file}" "${ENV_FILE}"
trap - EXIT

docker compose -f "${ROOT_DIR}/docker-compose.yml" \
  --project-directory "${ROOT_DIR}" \
  up -d
docker compose -f "${ROOT_DIR}/docker-compose.yml" \
  --project-directory "${ROOT_DIR}" \
  up -d --force-recreate --no-deps backend

public_http_port="$(
  awk -F= '/^LLVP_PUBLIC_ZLM_HTTP_PORT=/ { print $2; exit }' "${ENV_FILE}"
)"
public_http_port="${public_http_port:-8080}"

echo "LLVP_PUBLIC_ZLM_HOST=${public_ip}"
echo "Frontend: http://${public_ip}:5173/live"
echo "Media:    http://${public_ip}:${public_http_port}/live/<stream_id>.live.flv"

ready=false
for _ in {1..30}; do
  if curl --fail --silent --show-error \
    "http://127.0.0.1:8000/api/health" >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 1
done
if [[ "${ready}" != true ]]; then
  echo "Backend did not become healthy after restarting" >&2
  exit 1
fi

curl --fail --silent --show-error \
  "http://127.0.0.1:8000/api/streams/config-check/play-url" |
  python3 -c 'import json, sys; print("Play URL:", json.load(sys.stdin)["url"])'

curl --fail --silent --show-error --max-time 5 \
  -o /dev/null "http://${public_ip}:5173/api/health"
media_http_status="$(
  curl --silent --show-error --max-time 5 \
    -o /dev/null --write-out '%{http_code}' \
    "http://${public_ip}:${public_http_port}/"
)"
if [[ "${media_http_status}" == "000" ]]; then
  echo "Media port is unreachable: http://${public_ip}:${public_http_port}/" >&2
  exit 1
fi

echo "Frontend proxy and media port are reachable from ${public_ip}"
