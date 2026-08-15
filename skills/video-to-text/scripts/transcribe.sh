#!/bin/bash
# video-to-text 批量转写（嘉润版）
# 用法: transcribe.sh <urls.txt> [JOBS]
#   urls.txt 每行一个视频 URL；自动跳过已转写的；按行均分 N worker 并行
#   日志写在 urls 同目录 transcribe_<时间戳>.log
set -u

URLS_FILE="${1:?用法: transcribe.sh <urls.txt> [JOBS]}"
JOBS="${2:-5}"
RUN="$HOME/.workbuddy/skills/video-to-text/scripts/run.sh"
TXDIR="$HOME/Downloads/douyin-transcripts"
LOG="$(dirname "$URLS_FILE")/transcribe_$(date '+%Y%m%d_%H%M%S').log"
PENDING="$(mktemp -t v2t_pending.XXXXXX)"
PART_DIR="$(mktemp -d -t v2t_parts.XXXXXX)"

export V2T_TRANSCRIBER=api
export V2T_NO_SPINNER=1

# 1) 生成待转写列表（排除已有）
: > "$PENDING"
while IFS= read -r url; do
  [ -z "$url" ] && continue
  id=$(printf '%s' "$url" | grep -oE '(video|note)/[0-9]+' | grep -oE '[0-9]+')
  if [ -n "$id" ] && [ -f "$TXDIR/$id.txt" ]; then
    continue
  fi
  echo "$url" >> "$PENDING"
done < "$URLS_FILE"

TOTAL=$(wc -l < "$PENDING" | tr -d ' ')
echo "=== $(date '+%H:%M:%S') 待转写: $TOTAL 条, workers=$JOBS ===" | tee -a "$LOG"
[ "$TOTAL" -eq 0 ] && { echo "全部已完成，无需转写" | tee -a "$LOG"; rm -f "$PENDING"; rm -rf "$PART_DIR"; exit 0; }

# 2) 按行均分给 JOBS 个 worker
split -n l/$JOBS -d "$PENDING" "$PART_DIR/part_" 2>/dev/null || split -l $(( (TOTAL + JOBS - 1) / JOBS )) "$PENDING" "$PART_DIR/part_"

worker() {
  local part="$1"
  while IFS= read -r url; do
    [ -z "$url" ] && continue
    local id
    id=$(printf '%s' "$url" | grep -oE '(video|note)/[0-9]+' | grep -oE '[0-9]+')
    if [ -f "$TXDIR/$id.txt" ]; then
      echo "[skip] $id" >> "$LOG"
      continue
    fi
    echo "[start] $id $(date '+%H:%M:%S')" >> "$LOG"
    if bash "$RUN" "$url" > "/tmp/v2t_$id.log" 2>&1 && [ -f "$TXDIR/$id.txt" ]; then
      echo "[done] $id $(date '+%H:%M:%S')" >> "$LOG"
    else
      echo "[FAIL] $id" >> "$LOG"
      tail -2 "/tmp/v2t_$id.log" >> "$LOG"
    fi
  done < "$part"
}

for part in "$PART_DIR"/part_*; do
  worker "$part" &
done
wait

# 3) 汇总
DONE=0
while IFS= read -r url; do
  id=$(printf '%s' "$url" | grep -oE '(video|note)/[0-9]+' | grep -oE '[0-9]+')
  [ -f "$TXDIR/$id.txt" ] && DONE=$((DONE+1))
done < "$URLS_FILE"
echo "=== $(date '+%H:%M:%S') 完成统计: $DONE/$(wc -l < "$URLS_FILE" | tr -d ' ') 条有稿 ===" | tee -a "$LOG"
rm -f "$PENDING"
rm -rf "$PART_DIR"
