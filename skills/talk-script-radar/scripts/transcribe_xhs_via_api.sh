#!/usr/bin/env bash
# transcribe_xhs_via_api.sh — 小红书视频笔记 → 逐字稿 txt（云端 SiliconFlow ASR）
#
# 背景：xiaohongshu-video-to-text 的 run.sh 强制要求本地 whisper 模型才往下走，
#       即便已配 SILICONFLOW_API_KEY（云端）也会在最开始 exit。本脚本绕过该限制，
#       直接走云端 ASR，且复用其 xhs_extract.py（抓页/抽 video_url/desc）与
#       srt_to_readable.py（SRT→可读文本）。
#
# 输出：~/Downloads/douyin-transcripts/<note_id>.txt
#       格式与 xiaohongshu-video-to-text 完全一致（## desc/hashtags + ## transcript），
#       供 radar_ai_filter.py / radar_ai_ingest.py 直接消费。
#
# 用法：transcribe_xhs_via_api.sh <xhs_url> [<xhs_url> ...]
set -u

XHS_EXTRACT="/Users/a1-6/.workbuddy/skills/xiaohongshu-video-to-text/shared/scripts/xhs_extract.py"
SRT2TXT="/Users/a1-6/.workbuddy/skills/xiaohongshu-video-to-text/shared/scripts/srt_to_readable.py"
OUT_DIR="${DOUYIN_TRANSCRIPT_DIR:-${HOME}/Downloads/douyin-transcripts}"
XHS_UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0 Safari/537.36'
ASR_MODEL="${V2T_ASR_MODEL:-FunAudioLLM/SenseVoiceSmall}"

if [ -z "${SILICONFLOW_API_KEY:-}" ] && [ ! -f "$HOME/.workbuddy/secrets/siliconflow" ]; then
  echo "[xv2t] no SiliconFlow key (SILICONFLOW_API_KEY / ~/.workbuddy/secrets/siliconflow)" >&2
  exit 1
fi
mkdir -p "$OUT_DIR"
TMP="$(mktemp -d -t xv2t.XXXXXX)"

read_key() {
  if [ -n "${SILICONFLOW_API_KEY:-}" ]; then
    printf '%s' "$SILICONFLOW_API_KEY"
  else
    sed -e 's/[[:space:]]*$//' "$HOME/.workbuddy/secrets/siliconflow"
  fi
}

rc=0
for url in "$@"; do
  pjson="$TMP/url.json"
  if ! python3 "$XHS_EXTRACT" parse-url "$url" >"$pjson" 2>"$TMP/e1"; then
    echo "[xv2t FAIL] parse-url $url" >&2; cat "$TMP/e1" >&2; rc=1; continue
  fi
  CID="$(python3 "$XHS_EXTRACT" field "$pjson" note_id)"
  CURL="$(python3 "$XHS_EXTRACT" field "$pjson" canonical_url)"
  echo "[xv2t] $CID — fetching SSR page ..." >&2

  html="$TMP/$CID.html"
  code="$(curl -sSL --connect-timeout 10 --max-time 30 -A "$XHS_UA" \
    -H 'Accept-Language: zh-CN,zh;q=0.9,en;q=0.8' \
    -H 'Referer: https://www.xiaohongshu.com/' -o "$html" -w '%{http_code}' "$CURL")"
  if [ "$code" != "200" ]; then
    echo "[xv2t FAIL] page HTTP $code (login-walled?)" >&2; rc=1; continue
  fi

  info="$TMP/$CID.info.json"
  if ! python3 "$XHS_EXTRACT" extract "$html" "$CURL" >"$info" 2>"$TMP/e2"; then
    echo "[xv2t FAIL] extract" >&2; cat "$TMP/e2" >&2; rc=1; continue
  fi
  VURL="$(python3 "$XHS_EXTRACT" field "$info" video_url)"
  DESC="$(python3 "$XHS_EXTRACT" field "$info" desc)"
  if [ -z "$VURL" ]; then
    echo "[xv2t SKIP] $CID — no video_url (likely an image note)" >&2; continue
  fi

  mp4="$TMP/$CID.mp4"
  dcode="$(curl -sSL --connect-timeout 10 --max-time 120 -A "$XHS_UA" \
    -H "Referer: $CURL" -o "$mp4" -w '%{http_code}' "$VURL")"
  if [ "$dcode" != "200" ] || [ ! -s "$mp4" ]; then
    echo "[xv2t FAIL] download HTTP $dcode" >&2; rc=1; continue
  fi

  wav="$TMP/$CID.wav"
  if ! ffmpeg -nostdin -loglevel error -i "$mp4" -vn -acodec pcm_s16le -ar 16000 -ac 1 "$wav" -y 2>"$TMP/ff.log"; then
    echo "[xv2t FAIL] ffmpeg audio" >&2; tail -10 "$TMP/ff.log" >&2; rc=1; continue
  fi

  echo "[xv2t] $CID — transcribing via SiliconFlow ($ASR_MODEL) ..." >&2
  srt="$TMP/$CID.srt"
  resp="$TMP/$CID.resp"
  hc="$(curl -sS -o "$resp" -w '%{http_code}' --connect-timeout 15 --max-time 600 \
    -H "Authorization: Bearer $(read_key)" \
    -F "file=@$wav;type=audio/wav" \
    -F "model=$ASR_MODEL" -F "language=zh" -F "response_format=srt" \
    "https://api.siliconflow.cn/v1/audio/transcriptions")"
  if [ "$hc" != "200" ]; then
    echo "[xv2t FAIL] ASR HTTP $hc" >&2; head -c 500 "$resp" >&2; rc=1; continue
  fi
  if [ "$(head -c 1 "$resp")" = "{" ]; then
    txt="$(grep -o '"text"[[:space:]]*:[[:space:]]*"[^"]*"' "$resp" | sed -E 's/.*:[[:space:]]*"([^"]*)".*/\1/' | sed 's/\\n/\n/g')"
    { echo "1"; echo "00:00:00,000 --> 99:59:59,999"; echo "$txt"; } >"$srt"
  else
    mv "$resp" "$srt"
  fi

  if ! python3 "$SRT2TXT" "$srt" "$TMP/$CID.readable.txt" 2>"$TMP/srt.log"; then
    echo "[xv2t FAIL] srt_to_readable" >&2; cat "$TMP/srt.log" >&2; rc=1; continue
  fi

  out="$OUT_DIR/$CID.txt"
  { echo "## desc/hashtags"; echo "$DESC"; echo; echo "## transcript"; cat "$TMP/$CID.readable.txt"; } >"$out"
  echo "[xv2t DONE] -> $out" >&2
done

rm -rf "$TMP"
exit $rc
