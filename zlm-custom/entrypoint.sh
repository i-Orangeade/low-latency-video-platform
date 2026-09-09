#!/usr/bin/env sh
set -eu

template="${ZLM_CONFIG_TEMPLATE:-/opt/media/conf/config.template.ini}"
runtime_config="/tmp/zlm-config.ini"
secret="${DRONE_STREAM_ZLM_SECRET:-}"
hook_secret="${DRONE_STREAM_ZLM_HOOK_SECRET:-}"

if [ -z "${secret}" ]; then
  echo "DRONE_STREAM_ZLM_SECRET must be set" >&2
  exit 1
fi
if [ -z "${hook_secret}" ]; then
  echo "DRONE_STREAM_ZLM_HOOK_SECRET must be set" >&2
  exit 1
fi

case "${secret}" in
  *[!A-Za-z0-9._-]*)
    echo "DRONE_STREAM_ZLM_SECRET contains unsupported characters" >&2
    exit 1
    ;;
esac
case "${hook_secret}" in
  *[!A-Za-z0-9._-]*)
    echo "DRONE_STREAM_ZLM_HOOK_SECRET contains unsupported characters" >&2
    exit 1
    ;;
esac

if [ ! -r "${template}" ]; then
  echo "ZLM config template is not readable: ${template}" >&2
  exit 1
fi

sed \
  -e "s/__ZLM_SECRET__/${secret}/g" \
  -e "s/__ZLM_HOOK_SECRET__/${hook_secret}/g" \
  "${template}" > "${runtime_config}"

exec ./MediaServer \
  -s default.pem \
  -c "${runtime_config}" \
  -l "${ZLM_LOG_LEVEL:-0}"
