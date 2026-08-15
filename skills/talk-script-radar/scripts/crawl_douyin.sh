#!/usr/bin/env bash
# 薄封装：按场景调 MediaCrawler 抖音搜索。不改 base_config.py。
set -euo pipefail

MODE="${1:-daily}"
KEYWORDS="${2:-}"
MC="${MEDIACRAWLER_HOME:-$HOME/MediaCrawler}"
PY="$MC/.venv/bin/python"

if [[ ! -x "$PY" ]]; then
  echo "MediaCrawler 引擎未就绪: $PY" >&2
  echo "先跑: bash ~/.workbuddy/skills/media-crawler/scripts/setup.sh" >&2
  exit 1
fi

if [[ -z "$KEYWORDS" ]]; then
  echo "用法: crawl_douyin.sh daily|collect \"词1,词2,词3\"" >&2
  exit 1
fi

if [[ "$MODE" == "collect" ]]; then
  COUNT=30
else
  COUNT=10
fi

cd "$MC"
exec "$PY" main.py \
  --platform dy \
  --lt qrcode \
  --type search \
  --keywords "$KEYWORDS" \
  --crawler_max_notes_count "$COUNT" \
  --get_comment true \
  --max_comments_count_singlenotes 10 \
  --headless false \
  --save_data_option jsonl
