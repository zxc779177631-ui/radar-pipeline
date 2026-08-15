#!/usr/bin/env python3
"""把 ~/Downloads/douyin-transcripts/<id>.txt 灌进工作台 SEED。vid 当字符串。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

VID_RE = re.compile(r"video/(\d{15,})")


def parse_txt(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    desc, text = "", raw.strip()
    if re.search(r"^##\s*transcript\s*$", raw, re.I | re.M):
        head, body = re.split(r"^##\s*transcript\s*$", raw, maxsplit=1, flags=re.I | re.M)
        dm = re.search(r"^##\s*desc/hashtags\s*\n([^\n]*)", head, re.I | re.M)
        desc = dm.group(1).strip() if dm else ""
        text = body.strip()
    return {"desc": desc, "text": text}


def extract_object(html: str, needle: str) -> tuple[int, int, dict]:
    i = html.find(needle)
    if i < 0:
        raise SystemExit(f"missing {needle}")
    j = i + len(needle)
    while j < len(html) and html[j].isspace():
        j += 1
    if html[j] != "{":
        raise SystemExit(f"{needle} not object")
    depth = 0
    end = None
    for k, ch in enumerate(html[j:], j):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = k + 1
                break
    if end is None:
        raise SystemExit(f"{needle} unclosed")
    return j, end, json.loads(html[j:end])


def compact_line(text: str, limit: int = 1800) -> str:
    s = text.replace("\r", " ").replace("\n", " / ").replace("`", "'").replace("${", "｛")
    return s[:limit] + ("…" if len(s) > limit else "")


def patch_seed_md(html: str, recs: dict[str, dict]) -> str:
    m = re.search(r"const SEED_MD = `([\s\S]*?)`;", html)
    if not m:
        raise SystemExit("SEED_MD not found")
    lines = m.group(1).split("\n")
    out = []
    current = None
    after_metrics = False
    for line in lines:
        tm = re.search(r"\*\*\d+\.\*\*\s*\[.*?\]\((https://[^)]+)\)", line)
        if tm:
            mid = VID_RE.search(tm.group(1))
            current = mid.group(1) if mid else None
            after_metrics = False
            out.append(line)
            continue
        if current and re.match(r"^\s*稿[：:]", line):
            if after_metrics:
                continue
            rec = recs.get(current)
            if rec and rec.get("text") and len(rec["text"]) >= 10:
                out.append("　　稿：" + compact_line(rec["text"]))
            else:
                out.append(line)
            after_metrics = True
            continue
        out.append(line)
        if current and (not after_metrics) and "👍" in line and "评" not in line:
            rec = recs.get(current)
            if rec and rec.get("text") and len(rec["text"]) >= 10:
                out.append("　　稿：" + compact_line(rec["text"]))
            after_metrics = True
    return html[: m.start(1)] + "\n".join(out) + html[m.end(1) :]


def collect_ids(html: str, extra: list[str]) -> list[str]:
    found = []
    seen = set()
    for vid in extra + VID_RE.findall(html):
        if vid not in seen:
            seen.add(vid)
            found.append(vid)
    return found


def main() -> None:
    p = argparse.ArgumentParser(description="Inject local transcripts into workbench SEED")
    p.add_argument("--html", required=True, help="口播雷达工作台.html")
    p.add_argument("--archive", default="", help="Obsidian 归档副本，有则同步")
    p.add_argument("--txdir", default=str(Path.home() / "Downloads" / "douyin-transcripts"))
    p.add_argument("--ids", default="", help="逗号分隔 vid；空则扫工作台里所有视频号")
    p.add_argument("--min-chars", type=int, default=10)
    args = p.parse_args()

    html_path = Path(args.html)
    html = html_path.read_text(encoding="utf-8")
    extra = [x.strip() for x in args.ids.split(",") if x.strip()] if args.ids else []
    ids = extra or collect_ids(html, [])
    txdir = Path(args.txdir)
    recs = {}
    for vid in ids:
        fp = txdir / f"{vid}.txt"
        if not fp.exists():
            continue
        rec = parse_txt(fp)
        n = len(rec.get("text") or "")
        if n < args.min_chars:
            print(f"SKIP {vid} {n} 字")
            continue
        recs[vid] = rec
        print(f"OK   {vid} {n} 字")
    if not recs:
        raise SystemExit("没有可导入的新稿")

    j, end, obj = extract_object(html, "const SEED_TRANSCRIPTS =")
    for vid, rec in recs.items():
        old = obj.get(vid) or {}
        if not old.get("text") or len(rec["text"]) >= len(str(old.get("text") or "")):
            obj[vid] = rec
    dumped = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    html = html[:j] + dumped + html[end:]
    html = patch_seed_md(html, recs)
    html_path.write_text(html, encoding="utf-8")
    if args.archive:
        ap = Path(args.archive)
        ap.parent.mkdir(parents=True, exist_ok=True)
        ap.write_text(html, encoding="utf-8")
    print(f"wrote {len(recs)} transcripts -> {html_path}")


if __name__ == "__main__":
    main()
