---
name: xiaohongshu-video-to-text
description: Turn a Xiaohongshu video note URL into readable Chinese text (transcript + caption/hashtags) on macOS. Zero user setup - no browser, no browser cookie, no login. Triggers on Xiaohongshu/XHS URLs and asks like "小红书转文字", "小红书视频转文字", "extract 文案". Works in Claude Code, Codex, OMX, and plain CLI.
compatibility: Requires macOS 12+ and Homebrew. Auto-installs uv, ffmpeg, whisper-cpp, and the whisper base model on first run. ~200 MB disk (base model) or 1.5 GB (turbo).
---

# xiaohongshu-video-to-text

Given one or more Xiaohongshu video note URLs, produce a readable `<note_id>.txt` per video in `~/Downloads/douyin-transcripts/`. Pure CLI pipeline - no browser, no logged-in cookie, no Chrome extension, no MCP.

## Trigger

The user provides one or more Xiaohongshu URLs and asks to extract 文案 / transcript / video-to-text / 转文字. Accepted URL form:
- `https://www.xiaohongshu.com/explore/<note_id>?xsec_token=...`

The initial implementation intentionally requires `xsec_token` and does not support `xhslink.com` short links, image notes, login walls, or CAPTCHA pages.

## How it works

1. Fetch the anonymous server-rendered note page.
2. Parse `window.__INITIAL_STATE__` for desc/tags and `video.media.stream` mp4 URLs.
3. Download the mp4 with `curl`.
4. Shared pipeline: `ffmpeg` -> 16 kHz mono WAV -> `whisper-cli` SRT -> `srt_to_readable.py` paragraphs.

Xiaohongshu uses only anonymous page/session cookies created by `curl`; browser cookies are never read.

## Steps

### Step 1 - Preflight

```bash
bash "$SKILL_DIR/scripts/preflight.sh"
```

### Step 2 - Process URLs

```bash
bash "$SKILL_DIR/scripts/run.sh" "<xiaohongshu_url1>" ["<xiaohongshu_url2>" ...]
```

The output uses the same blocks as the Douyin skill:

```text
## desc/hashtags
<caption + tags from Xiaohongshu>

## transcript
<readable Chinese paragraphs>
```

## Failure modes

`run.sh` tags failures with `category=<cat>`. See the repository's `shared/references/failure-modes.md` for the full playbook when available.

Quick reference:
- `xhs-parse` -> paste a canonical `/explore/<note_id>?xsec_token=...` URL.
- `xhs-network` -> check network/VPN, retry once.
- `xhs-auth` -> login/captcha/access wall. Skip and continue.
- `xhs-download` -> not a video note or mp4 download failed. Skip and continue.
- `ffmpeg` -> audio extraction error.
- `whisper` -> model missing or corrupted.
- `srt-format` -> empty transcript.
- `output-write` -> output directory is not writable or disk is full.
