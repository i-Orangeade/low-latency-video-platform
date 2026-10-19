#!/bin/sh
set -eu

# ZLM 官方镜像不直接读取项目中的变量文件。
# 这里在容器启动时读取环境变量、校验 secret，并生成实际运行配置。
template="${ZLM_CONFIG_TEMPLATE:-/opt/media/conf/config.template.ini}"
runtime_config="/tmp/zlm-config.ini"
secret="${LLVP_ZLM_SECRET:-}"
hook_secret="${LLVP_ZLM_HOOK_SECRET:-}"

# LLVP_ZLM_SECRET 用于调用 ZLM HTTP API。
# 如果缺失则拒绝启动，避免服务以默认或不安全密钥运行。
if [ -z "${secret}" ]; then
  echo "LLVP_ZLM_SECRET must be set" >&2
  exit 1
fi

if [ -z "${hook_secret}" ]; then
  echo "LLVP_ZLM_HOOK_SECRET must be set" >&2
  exit 1
fi

case "${secret}" in
  *[!A-Za-z0-9._-]*)
    echo "LLVP_ZLM_SECRET contains unsupported characters" >&2
    exit 1
    ;;
esac

case "${hook_secret}" in
  *[!A-Za-z0-9._-]*)
    echo "LLVP_ZLM_HOOK_SECRET contains unsupported characters" >&2
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

# 使用 exec 让 MediaServer 替换 shell 成为 PID 1。
# 这样 docker stop 发送的信号可以直接到达媒体服务，而不是被 shell 吞掉。
exec ./MediaServer \
  -s default.pem \
  -c "${runtime_config}" \
  -l "${ZLM_LOG_LEVEL:-0}"
