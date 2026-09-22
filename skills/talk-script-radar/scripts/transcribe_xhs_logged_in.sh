#!/usr/bin/env bash
# 带登录 cookie 抓 XHS 笔记页 → 从 HTML 抽 masterUrl/sns-video → 云端 ASR
# 输出 ~/Downloads/douyin-transcripts/<note_id>.txt
set -u
OUT_DIR="${DOUYIN_TRANSCRIPT_DIR:-${HOME}/Downloads/douyin-transcripts}"
COOKIE_FILE="${XHS_COOKIE_FILE:-/tmp/xhs_cookies.txt}"
XHS_UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0 Safari/537.36'
ASR_MODEL="${V2T_ASR_MODEL:-FunAudioLLM/SenseVoiceSmall}"
SRT2TXT="/Users/a1-6/.workbuddy/skills/xiaohongshu-video-to-text/shared/scripts/srt_to_readable.py"

if [ ! -f "$COOKIE_FILE" ]; then
  echo "[xv2t] missing cookie file $COOKIE_FILE" >&2; exit 1
fi
if [ -z "${SILICONFLOW_API_KEY:-}" ] && [ ! -f "$HOME/.workbuddy/secrets/siliconflow" ]; then
  echo "[xv2t] no SiliconFlow key" >&2; exit 1
fi
read_key() {
  if [ -n "${SILICONFLOW_API_KEY:-}" ]; then printf '%s' "$SILICONFLOW_API_KEY"
  else sed -e 's/[[:space:]]*$//' "$HOME/.workbuddy/secrets/siliconflow"; fi
}
mkdir -p "$OUT_DIR"
COOKIE=$(cat "$COOKIE_FILE")
PY=/Users/a1-6/.workbuddy/binaries/python/versions/3.13.12/bin/python3
TMP=$(mktemp -d -t xv2tli.XXXXXX)
rc=0
n=0
for url in "$@"; do
  n=$((n+1))
  CID=$($PY -c "import re,sys; m=re.search(r'explore/([0-9a-f]+)',sys.argv[1]); print(m.group(1) if m else '')" "$url")
  if [ -z "$CID" ]; then echo "[xv2t FAIL] bad url $url" >&2; rc=1; continue; fi
  if [ -s "$OUT_DIR/$CID.txt" ]; then
    echo "[xv2t SKIP] $CID already transcribed" >&2; continue
  fi
  echo "[xv2t] ($n) $CID — fetch with cookie ..." >&2
  html="$TMP/$CID.html"
  code=$(curl -sSL --connect-timeout 10 --max-time 30 -A "$XHS_UA" \
    -H 'Accept-Language: zh-CN,zh;q=0.9,en;q=0.8' \
    -H 'Referer: https://www.xiaohongshu.com/' \
    -H "Cookie: $COOKIE" \
    -o "$html" -w '%{http_code}' "$url")
  if [ "$code" != "200" ]; then echo "[xv2t FAIL] page HTTP $code $CID" >&2; rc=1; continue; fi

  info="$TMP/$CID.info.json"
  if ! $PY - "$html" "$url" >"$info" <<'PY'
import json, re, sys, html as htmllib
from urllib.parse import unquote
path, url = sys.argv[1], sys.argv[2]
raw = open(path, encoding="utf-8", errors="ignore").read()
nid = re.search(r"explore/([0-9a-f]+)", url).group(1)

def unescape(s):
    s = s.replace("\\u002F", "/").replace("\\/", "/")
    s = s.replace("\\u0026", "&").replace("\\u003D", "=")
    s = htmllib.unescape(s)
    return unquote(s)

cands = []
for m in re.finditer(r'masterUrl["\']?\s*[:=]\s*["\']([^"\']+)', raw):
    cands.append(unescape(m.group(1)))
for m in re.finditer(r'https?:\\u002F\\u002Fsns-video[^"\\]+', raw):
    cands.append(unescape(m.group(0)))
for m in re.finditer(r'https://sns-video[^"\\\s]+', raw):
    cands.append(unescape(m.group(0)))

# prefer mp4
mp4 = [u for u in cands if ".mp4" in u]
vurl = (mp4[0] if mp4 else (cands[0] if cands else ""))

desc = ""
m = re.search(r'"desc"\s*:\s*"((?:\\.|[^"\\])*)"', raw)
if m:
    try:
        desc = json.loads('"' + m.group(1) + '"')
    except Exception:
        desc = m.group(1)

if not vurl:
    sys.stderr.write("no video url in html\n")
    sys.exit(4)
json.dump({"note_id": nid, "video_url": vurl, "desc": desc}, sys.stdout, ensure_ascii=False)
PY
  then
    echo "[xv2t FAIL] extract $CID" >&2; rc=1; continue
  fi
  VURL=$($PY -c "import json,sys; print(json.load(open(sys.argv[1])).get('video_url',''))" "$info")
  DESC=$($PY -c "import json,sys; print(json.load(open(sys.argv[1])).get('desc',''))" "$info")
  echo "[xv2t] $CID — download ..." >&2
  mp4="$TMP/$CID.mp4"
  dcode=$(curl -sSL --connect-timeout 10 --max-time 120 -A "$XHS_UA" \
    -H "Referer: $url" -H "Cookie: $COOKIE" \
    -o "$mp4" -w '%{http_code}' "$VURL")
  if [ "$dcode" != "200" ] || [ ! -s "$mp4" ]; then
    echo "[xv2t FAIL] download HTTP $dcode $CID" >&2; rc=1; continue
  fi
  wav="$TMP/$CID.wav"
  if ! ffmpeg -nostdin -loglevel error -i "$mp4" -vn -acodec pcm_s16le -ar 16000 -ac 1 "$wav" -y 2>"$TMP/ff.log"; then
    echo "[xv2t FAIL] ffmpeg $CID" >&2; rc=1; continue
  fi
  echo "[xv2t] $CID — ASR ..." >&2
  srt="$TMP/$CID.srt"; resp="$TMP/$CID.resp"
  hc=$(curl -sS -o "$resp" -w '%{http_code}' --connect-timeout 15 --max-time 600 \
    -H "Authorization: Bearer $(read_key)" \
    -F "file=@$wav;type=audio/wav" \
    -F "model=$ASR_MODEL" -F "language=zh" -F "response_format=srt" \
    "https://api.siliconflow.cn/v1/audio/transcriptions")
  if [ "$hc" != "200" ]; then
    echo "[xv2t FAIL] ASR HTTP $hc $CID" >&2; head -c 300 "$resp" >&2; echo >&2; rc=1; continue
  fi
  if [ "$(head -c 1 "$resp")" = "{" ]; then
    txt=$(grep -o '"text"[[:space:]]*:[[:space:]]*"[^"]*"' "$resp" | sed -E 's/.*:[[:space:]]*"([^"]*)".*/\1/' | sed 's/\\n/\n/g')
    { echo "1"; echo "00:00:00,000 --> 99:59:59,999"; echo "$txt"; } >"$srt"
  else
    mv "$resp" "$srt"
  fi
  if ! $PY "$SRT2TXT" "$srt" "$TMP/$CID.readable.txt" 2>"$TMP/srt.log"; then
    echo "[xv2t FAIL] srt $CID" >&2; rc=1; continue
  fi
  { echo "## desc/hashtags"; echo "$DESC"; echo; echo "## transcript"; cat "$TMP/$CID.readable.txt"; } >"$OUT_DIR/$CID.txt"
  echo "[xv2t DONE] -> $OUT_DIR/$CID.txt" >&2
done
rm -rf "$TMP"
echo "[xv2t] batch finished rc=$rc"
exit $rc
