#!/bin/sh
set -eu

template="${ZLM_CONFIG_TEMPLATE:-/opt/media/conf/config.template.ini}"
runtime_config="/tmp/zlm-config.ini"
secret="${LLVP_ZLM_SECRET:-}"

if [ -z "${secret}" ]; then
  echo "LLVP_ZLM_SECRET must be set" >&2
  exit 1
fi

case "${secret}" in
  *[!A-Za-z0-9._-]*)
    echo "LLVP_ZLM_SECRET contains unsupported characters" >&2
    exit 1
    ;;
esac

if [ ! -r "${template}" ]; then
  echo "ZLM config template is not readable: ${template}" >&2
  exit 1
fi

sed "s/__ZLM_SECRET__/${secret}/g" "${template}" > "${runtime_config}"

exec ./MediaServer \
  -s default.pem \
  -c "${runtime_config}" \
  -l "${ZLM_LOG_LEVEL:-0}"
