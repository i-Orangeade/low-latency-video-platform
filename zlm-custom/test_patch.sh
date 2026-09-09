#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="${1:-}"
EXPECTED_COMMIT="da9b2017fbdd1738da4d68ff442b5eca3542c3ba"
PATCH_FILE="${SCRIPT_DIR}/patches/0001-add-stream-qos-api.patch"

if [[ -z "${SOURCE_DIR}" || ! -d "${SOURCE_DIR}/.git" ]]; then
  echo "Usage: $0 /path/to/ZLMediaKit" >&2
  exit 2
fi

actual_commit="$(git -C "${SOURCE_DIR}" rev-parse HEAD)"
if [[ "${actual_commit}" != "${EXPECTED_COMMIT}" ]]; then
  echo "Expected ZLMediaKit ${EXPECTED_COMMIT}, got ${actual_commit}" >&2
  exit 1
fi

if git -C "${SOURCE_DIR}" apply --reverse --check "${PATCH_FILE}" 2>/dev/null; then
  echo "Patch is already applied and reversible."
elif git -C "${SOURCE_DIR}" apply --check "${PATCH_FILE}"; then
  echo "Patch applies cleanly."
else
  echo "Patch does not apply cleanly." >&2
  exit 1
fi

grep -q 'api_regist("/index/api/getStreamQos"' "${SOURCE_DIR}/server/WebApi.cpp" 2>/dev/null \
  && echo "QoS API registration found." \
  || echo "QoS API registration will be added by the patch."
