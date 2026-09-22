#!/usr/bin/env bash
# transcribe_robust.sh — 对 video-to-text 的转写做「自动重试 + 指数退避」封装
# 用法: bash transcribe_robust.sh <urls.txt> [workers=4] [max_attempts=6]
# 行为:
#   1) 跑 transcribe.sh(云端 SiliconFlow)
#   2) 验收 ~/Downloads/douyin-transcripts/<id>.txt 是否真实存在且正文>20字
#   3) 对仍缺失的 ID 重建 urls 重跑, 退避 sleep(attempt*20s), 直到全过或耗尽重试
#   4) 打印最终统计: 成功/失败 ID 列表
set -u

URLS="${1:?用法: transcribe_robust.sh <urls.txt> [workers] [max_attempts]}"
WORKERS="${2:-4}"
MAX_ATTEMPTS="${3:-6}"
TX_DIR="$HOME/Downloads/douyin-transcripts"
SCRIPT="$HOME/.workbuddy/skills/video-to-text/scripts/transcribe.sh"

export SILICONFLOW_API_KEY="$(cat ~/.workbuddy/secrets/siliconflow 2>/dev/null)"
export V2T_TRANSCRIBER=api

urls_to_ids() { grep -oE '[0-9]{15,}' "$1" | sort -u; }

total=$(urls_to_ids "$URLS" | wc -l | tr -d ' ')
echo "=== 待转写总数: $total | workers=$WORKERS | max_attempts=$MAX_ATTEMPTS ==="

cur="$URLS"
for (( attempt=1; attempt<=MAX_ATTEMPTS; attempt++ )); do
  echo "--- 第 $attempt/$MAX_ATTEMPTS 轮 ---"
  bash "$SCRIPT" "$cur" "$WORKERS" >/dev/null 2>&1

  # 验收
  missing=()
  while IFS= read -r id; do
    [ -z "$id" ] && continue
    f="$TX_DIR/$id.txt"
    ok=0
    if [ -f "$f" ]; then
      body=$(sed -n '1,99999p' "$f" | grep -vE '^(#|title:|url:|author:|desc:|date:|liked:|grade:)' | tr -d '[:space:]')
      [ "${#body}" -gt 20 ] && ok=1
    fi
    [ "$ok" -eq 0 ] && missing+=("$id")
  done < <(urls_to_ids "$cur")

  done_count=$(( total - ${#missing[@]} ))
  echo "    已转写: $done_count / $total"
  if [ "${#missing[@]}" -eq 0 ]; then
    echo "=== 全部完成 ==="
    exit 0
  fi

  # 重建缺失 urls
  miss_urls=$(mktemp)
  for id in "${missing[@]}"; do echo "https://www.douyin.com/video/$id" >> "$miss_urls"; done
  cur="$miss_urls"
  if [ "$attempt" -lt "$MAX_ATTEMPTS" ]; then
    backoff=$(( attempt * 20 ))
    echo "    仍有 ${#missing[@]} 条缺失, 退避 ${backoff}s 后重试"
    sleep "$backoff"
  fi
done

echo "=== 耗尽重试, 仍缺失 ${#missing[@]} 条 ==="
for id in "${missing[@]}"; do echo "  FAIL $id"; done
exit 1
