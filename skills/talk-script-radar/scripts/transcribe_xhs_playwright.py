#!/usr/bin/env python3
"""用 MediaCrawler 的 XHS 浏览器档案打开笔记页，抽 masterUrl，再走云端 ASR。

可见浏览器：若弹出二维码 / 安全验证，等人过完再继续。
每条间隔默认 12 秒，避免 curl 连打把 cookie 打进登录墙。
视频只落临时目录，结束删除；本地只留逐字稿。
"""
from __future__ import annotations

import html as htmllib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright

USER_DATA = os.environ.get(
    "XHS_USER_DATA",
    str(Path.home() / "MediaCrawler/browser_data/xhs_user_data_dir"),
)
OUT_DIR = Path(os.environ.get("DOUYIN_TRANSCRIPT_DIR", str(Path.home() / "Downloads/douyin-transcripts")))
SRT2TXT = Path.home() / ".workbuddy/skills/xiaohongshu-video-to-text/shared/scripts/srt_to_readable.py"
ASR_MODEL = os.environ.get("V2T_ASR_MODEL", "FunAudioLLM/SenseVoiceSmall")
SLEEP_SEC = float(os.environ.get("XHS_SLEEP_SEC", "12"))
HEADLESS = os.environ.get("XHS_HEADLESS", "0") == "1"
KEY_FILE = Path.home() / ".workbuddy/secrets/siliconflow"


def read_key() -> str:
    if os.environ.get("SILICONFLOW_API_KEY"):
        return os.environ["SILICONFLOW_API_KEY"].strip()
    return KEY_FILE.read_text(encoding="utf-8").strip()


def note_id_of(url: str) -> str:
    m = re.search(r"explore/([0-9a-f]+)", url)
    return m.group(1) if m else ""


def unescape(s: str) -> str:
    s = s.replace("\\u002F", "/").replace("\\/", "/")
    s = s.replace("\\u0026", "&").replace("\\u003D", "=")
    s = htmllib.unescape(s)
    return urllib.parse.unquote(s)


def extract_video_and_desc(raw: str) -> tuple[str, str]:
    cands: list[str] = []
    for m in re.finditer(r"""masterUrl["']?\s*[:=]\s*["']([^"']+)""", raw):
        cands.append(unescape(m.group(1)))
    for m in re.finditer(r"https?:\\u002F\\u002Fsns-video[^\"\\]+", raw):
        cands.append(unescape(m.group(0)))
    for m in re.finditer(r"https://sns-video[^\"\\\s]+", raw):
        cands.append(unescape(m.group(0)))
    mp4 = [u for u in cands if ".mp4" in u]
    vurl = mp4[0] if mp4 else (cands[0] if cands else "")
    desc = ""
    m = re.search(r'"desc"\s*:\s*"((?:\\.|[^"\\])*)"', raw)
    if m:
        try:
            desc = json.loads('"' + m.group(1) + '"')
        except Exception:
            desc = m.group(1)
    return vurl, desc


def dump_cookies(ctx) -> None:
    cookies = ctx.cookies()
    parts = []
    have_session = False
    for c in cookies:
        domain = c.get("domain") or ""
        if "xiaohongshu" not in domain and "xhscdn" not in domain:
            continue
        parts.append(f"{c['name']}={c['value']}")
        if c["name"] == "web_session":
            have_session = True
    Path("/tmp/xhs_cookies.txt").write_text("; ".join(parts), encoding="utf-8")
    print(f"[pw] dumped cookies={len(parts)} web_session={have_session}", flush=True)


def wait_for_human(page, timeout_sec: int = 600) -> bool:
    print("[pw] 请在弹出的浏览器里过安全验证 / 扫码登录。最多等 10 分钟。", flush=True)
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        title = (page.title() or "").strip()
        html = page.content()
        ok = (
            title not in {"安全验证", "小红书", ""}
            and ("__INITIAL_STATE__" in html or "masterUrl" in html or "sns-video" in html)
        )
        if ok:
            print(f"[pw] 登录/验证已通过 title={title!r}", flush=True)
            return True
        remain = int(deadline - time.time())
        if remain % 15 == 0:
            print(f"[pw] 仍在等扫码/验证 title={title!r} html={len(html)} remain={remain}s", flush=True)
        page.wait_for_timeout(2000)
    print("[pw] 超时仍未过验证", flush=True)
    return False


def asr_wav(wav: Path, srt: Path) -> None:
    resp = wav.with_suffix(".resp")
    cmd = [
        "curl", "-sS", "-o", str(resp), "-w", "%{http_code}",
        "--connect-timeout", "15", "--max-time", "600",
        "-H", f"Authorization: Bearer {read_key()}",
        "-F", f"file=@{wav};type=audio/wav",
        "-F", f"model={ASR_MODEL}",
        "-F", "language=zh",
        "-F", "response_format=srt",
        "https://api.siliconflow.cn/v1/audio/transcriptions",
    ]
    hc = subprocess.check_output(cmd, text=True).strip()
    if hc != "200":
        snippet = resp.read_text(encoding="utf-8", errors="ignore")[:300]
        raise RuntimeError(f"ASR HTTP {hc}: {snippet}")
    raw = resp.read_text(encoding="utf-8", errors="ignore")
    if raw[:1] == "{":
        try:
            payload = json.loads(raw)
            txt = payload.get("text") or ""
        except Exception:
            m = re.search(r'"text"\s*:\s*"(.*?)"', raw, re.S)
            txt = m.group(1) if m else ""
            txt = txt.replace("\\n", "\n").replace('\\"', '"')
        srt.write_text(f"1\n00:00:00,000 --> 99:59:59,999\n{txt}\n", encoding="utf-8")
    else:
        srt.write_text(raw, encoding="utf-8")


def main() -> int:
    urls = [u.strip() for u in sys.argv[1:] if u.strip()]
    url_file = Path(os.environ.get("XHS_URL_FILE", "/tmp/xhs_remain16_urls.txt"))
    if not urls and url_file.exists():
        urls = [u.strip() for u in url_file.read_text().splitlines() if u.strip()]
    if not urls:
        print("usage: transcribe_xhs_playwright.py <url> ...", file=sys.stderr)
        return 2
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    done = fail = skip = 0
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            USER_DATA,
            headless=HEADLESS,
            viewport={"width": 1280, "height": 860},
            locale="zh-CN",
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.new_page()
        first = urls[0]
        print(f"[pw] open first note to check session: {note_id_of(first)}", flush=True)
        page.goto(first, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        title = (page.title() or "").strip()
        html = page.content()
        if title in {"安全验证", "小红书"} or ("masterUrl" not in html and "sns-video" not in html):
            if not wait_for_human(page):
                ctx.close()
                return 3
        dump_cookies(ctx)

        tmp = Path(tempfile.mkdtemp(prefix="xv2tpw."))
        try:
            for i, url in enumerate(urls, 1):
                nid = note_id_of(url)
                out = OUT_DIR / f"{nid}.txt"
                if out.exists() and out.stat().st_size > 80:
                    print(f"[pw SKIP] ({i}/{len(urls)}) {nid} already transcribed", flush=True)
                    skip += 1
                    continue
                print(f"[pw] ({i}/{len(urls)}) {nid} goto ...", flush=True)
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(2800)
                    raw = page.content()
                    title = (page.title() or "").strip()
                    if title in {"安全验证", "小红书"}:
                        print(f"[pw] 再次撞墙 title={title!r}，等人过验证", flush=True)
                        if not wait_for_human(page):
                            fail += 1
                            break
                        raw = page.content()
                    vurl, desc = extract_video_and_desc(raw)
                    if not vurl:
                        print(f"[pw FAIL] no video url {nid} title={title!r} html={len(raw)}", flush=True)
                        fail += 1
                        time.sleep(SLEEP_SEC)
                        continue
                    mp4 = tmp / f"{nid}.mp4"
                    wav = tmp / f"{nid}.wav"
                    srt = tmp / f"{nid}.srt"
                    readable = tmp / f"{nid}.readable.txt"
                    print(f"[pw] {nid} download ...", flush=True)
                    with page.expect_download(timeout=120000) as dl_info:
                        # 有的 CDN 不走 download 事件；改用 request
                        raise RuntimeError("use request")
                except Exception:
                    pass
                try:
                    vurl, desc = extract_video_and_desc(page.content())
                    if not vurl:
                        raise RuntimeError("empty video url")
                    mp4 = tmp / f"{nid}.mp4"
                    wav = tmp / f"{nid}.wav"
                    srt = tmp / f"{nid}.srt"
                    readable = tmp / f"{nid}.readable.txt"
                    # 用浏览器上下文拿视频，带上当前 cookie / 防盗链
                    resp = page.request.get(vurl, timeout=120000)
                    if not resp.ok:
                        raise RuntimeError(f"download HTTP {resp.status}")
                    mp4.write_bytes(resp.body())
                    if mp4.stat().st_size < 1000:
                        raise RuntimeError(f"tiny mp4 {mp4.stat().st_size}")
                    print(f"[pw] {nid} ffmpeg+ASR ...", flush=True)
                    subprocess.check_call(
                        ["ffmpeg", "-nostdin", "-loglevel", "error", "-i", str(mp4),
                         "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", str(wav), "-y"]
                    )
                    asr_wav(wav, srt)
                    subprocess.check_call([sys.executable, str(SRT2TXT), str(srt), str(readable)])
                    text = readable.read_text(encoding="utf-8", errors="ignore")
                    out.write_text(f"## desc/hashtags\n{desc}\n\n## transcript\n{text}\n", encoding="utf-8")
                    print(f"[pw DONE] {nid} -> {out} ({len(text)} chars)", flush=True)
                    done += 1
                    mp4.unlink(missing_ok=True)
                    wav.unlink(missing_ok=True)
                except Exception as e:
                    print(f"[pw FAIL] {nid}: {e}", flush=True)
                    fail += 1
                time.sleep(SLEEP_SEC)
        finally:
            dump_cookies(ctx)
            ctx.close()
            for pth in tmp.glob("*"):
                pth.unlink(missing_ok=True)
            tmp.rmdir()
    print(f"[pw] batch finished done={done} fail={fail} skip={skip}", flush=True)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
