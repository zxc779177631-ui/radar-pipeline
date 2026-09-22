#!/usr/bin/env bash
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

for url in "$@"; do
  if echo "$url" | grep -qE '(^|[./])douyin\.com|iesdouyin\.com'; then
    echo "[v2t FAIL] category=parse  platform=xhs  content_id=?  Douyin URL belongs to the video-to-text skill" >&2
    exit 2
  fi
done

for shared_root in "${SCRIPT_DIR}/../shared" "${SCRIPT_DIR}/../../../shared" "${SCRIPT_DIR}/../../shared"; do
  if [ -f "${shared_root}/scripts/run.sh" ]; then
    exec bash "${shared_root}/scripts/run.sh" "$@"
  fi
done
echo "[v2t FAIL] category=parse  platform=xhs  content_id=?  shared/scripts/run.sh not found" >&2
exit 1
