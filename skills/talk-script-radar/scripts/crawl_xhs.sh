#!/usr/bin/env bash
# 薄封装：按场景调 MediaCrawler 小红书(XHS)搜索。不改 base_config.py。
# 镜像 crawl_douyin.sh，仅把平台换成 xhs。
#
# 重要：XHS 强制登录。MediaCrawler 用 --lt qrcode 弹出浏览器二维码，
# 需要本机已装 playwright 浏览器 + 你本人扫码登录。无显示器/无浏览器的
# 沙箱环境跑不起来（会卡在登录）。首次在本机 Mac 跑一次登录后，cookie
# 会缓存，后续可复用。
#
# 反爬提示：XHS 风控比抖音凶，单次关键词别太多、COUNT 别太大，避免封号。
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
  echo "用法: crawl_xhs.sh daily|collect \"词1,词2,词3\"" >&2
  exit 1
fi

if [[ "$MODE" == "collect" ]]; then
  COUNT=30
  GET_COMMENT="${GET_COMMENT:-false}"
else
  COUNT=10
  GET_COMMENT="${GET_COMMENT:-true}"
fi

cd "$MC"
if [[ "$GET_COMMENT" == "true" ]]; then
  exec "$PY" main.py \
    --platform xhs \
    --lt qrcode \
    --type search \
    --keywords "$KEYWORDS" \
    --crawler_max_notes_count "$COUNT" \
    --get_comment true \
    --max_comments_count_singlenotes 10 \
    --headless false \
    --save_data_option jsonl
else
  exec "$PY" main.py \
    --platform xhs \
    --lt qrcode \
    --type search \
    --keywords "$KEYWORDS" \
    --crawler_max_notes_count "$COUNT" \
    --get_comment false \
    --headless false \
    --save_data_option jsonl
fi
