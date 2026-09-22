#!/usr/bin/env bash
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
for shared_root in "${SCRIPT_DIR}/../shared" "${SCRIPT_DIR}/../../../shared" "${SCRIPT_DIR}/../../shared"; do
  if [ -f "${shared_root}/scripts/preflight.sh" ]; then
    exec bash "${shared_root}/scripts/preflight.sh" "$@"
  fi
done
echo "[v2t FAIL] shared/scripts/preflight.sh not found" >&2
exit 1
