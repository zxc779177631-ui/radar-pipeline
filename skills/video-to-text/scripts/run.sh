#!/usr/bin/env bash
# video-to-text（嘉润版）入口
# 用法: run.sh "<url>" ["<url2>" ...]
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

for shared_root in "${SCRIPT_DIR}/../shared" "${SCRIPT_DIR}/../../../shared" "${SCRIPT_DIR}/../../shared"; do
  if [ -f "${shared_root}/scripts/run.sh" ]; then
    exec bash "${shared_root}/scripts/run.sh" "$@"
  fi
done
echo "[v2t FAIL] category=parse  platform=video  content_id=?  shared/scripts/run.sh not found" >&2
exit 1
