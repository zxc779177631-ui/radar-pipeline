#!/usr/bin/env python3
"""把雷达清单 + 逐字稿合成 inbox.json（人只过已转写稿）。"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ledger import default_ledger_path, load_ledger, upsert, vid_of  # noqa: E402

ITEM_RE = re.compile(
    r"\*\*(\d+)\.\*\*\s+\[(.*?)\]\((https?://www\.douyin\.com/video/\d+)\)"
)
META_RE = re.compile(
    r"👍([\d,]+).*?💬([\d,]+).*?🔁([\d,]+).*?⭐([\d,]+).*?@([^\s·]+).*?(\d{4}-\d{2}-\d{2})?"
)
MIN_CHARS = 150


def to_int(v, default=0) -> int:
    try:
        return int(str(v).replace(",", "") or default)
    except (TypeError, ValueError):
        return default


def grade_of(liked: int) -> str:
    if liked >= 50_000:
        return "abs"
    if liked >= 5_000:
        return "mid"
    return "low"


def parse_markdown(md: str) -> list[dict]:
    lines = md.splitlines()
    items: list[dict] = []
    cur = None
    for line in lines:
        m = ITEM_RE.search(line)
        if m:
            if cur:
                items.append(cur)
            url = m.group(3)
            cur = {
                "id": vid_of(url),
                "title": m.group(2).strip(),
                "url": url,
                "comments": [],
                "tags": [],
                "liked": 0,
                "comment": 0,
                "share": 0,
                "collect": 0,
                "author": "",
                "date": "",
                "isTalk": False,
                "transcript": "",
            }
            continue
        if not cur:
            continue
        if "评" not in line and "👍" in line:
            mm = META_RE.search(line)
            if mm:
                cur["liked"] = to_int(mm.group(1))
                cur["comment"] = to_int(mm.group(2))
                cur["share"] = to_int(mm.group(3))
                cur["collect"] = to_int(mm.group(4))
                cur["author"] = mm.group(5) or ""
                cur["date"] = mm.group(6) or ""
            cur["tags"] = re.findall(r"#([^\s·]+)", line)
            cur["isTalk"] = "口播" in line
        elif "评" in line and "👍" in line:
            cm = re.search(r"评\s*👍([\d,]+)\s*[:：]\s*(.*)", line)
            if cm:
                cur["comments"].append(
                    {"likes": to_int(cm.group(1)), "text": cm.group(2).strip()}
                )
        elif re.match(r"\s*稿[：:]", line):
            cur["transcript"] = re.sub(r"^\s*稿[：:]\s*", "", line).strip()
    if cur:
        items.append(cur)
    for it in items:
        it["grade"] = grade_of(it["liked"])
    return [it for it in items if it.get("id")]


def read_transcript(txdir: Path, vid: str) -> str:
    fp = txdir / f"{vid}.txt"
    if not fp.exists():
        return ""
    text = fp.read_text(encoding="utf-8", errors="replace")
    parts = re.split(r"^##\s*transcript\s*$", text, flags=re.I | re.M)
    body = parts[-1] if parts else text
    return body.strip()


def main() -> None:
    p = argparse.ArgumentParser(description="Merge radar markdown + transcripts into inbox")
    p.add_argument("--md", required=True, help="爆款口播候选清单 md")
    p.add_argument(
        "--out",
        default="",
        help="inbox json；默认 雷达inbox_YYYY-MM-DD.json",
    )
    p.add_argument(
        "--txdir",
        default=str(Path.home() / "Downloads" / "douyin-transcripts"),
    )
    p.add_argument("--ledger", default="")
    p.add_argument("--min-chars", type=int, default=MIN_CHARS)
    args = p.parse_args()

    md_path = Path(args.md)
    items = parse_markdown(md_path.read_text(encoding="utf-8"))
    txdir = Path(args.txdir)
    ledger_path = Path(args.ledger) if args.ledger else default_ledger_path()
    ledger = load_ledger(ledger_path)

    ready, short, missing = [], [], []
    for it in items:
        vid = it["id"]
        text = it.get("transcript") or read_transcript(txdir, vid)
        it["transcript"] = text
        n = len(text.strip())
        upsert(ledger, vid, title=it["title"][:80], url=it["url"], liked=it["liked"])
        if n >= args.min_chars:
            it["status"] = "transcribed"
            it["transcribeState"] = "done"
            ready.append(it)
            upsert(ledger, vid, status="transcribed", chars=n)
        elif n > 0:
            it["status"] = "pending"
            it["transcribeState"] = "short"
            short.append(it)
            upsert(ledger, vid, status="seen", chars=n, note="short")
        else:
            it["status"] = "pending"
            it["transcribeState"] = "pending"
            missing.append(it)
            upsert(ledger, vid, status="seen")

    today = dt.date.today().isoformat()
    out_path = Path(args.out) if args.out else Path.cwd() / f"雷达inbox_{today}.json"
    payload = {
        "version": 1,
        "date": today,
        "source": str(md_path),
        "min_chars": args.min_chars,
        "counts": {
            "parsed": len(items),
            "ready": len(ready),
            "short": len(short),
            "missing": len(missing),
        },
        "candidates": ready,
        "skipped_short": [{"id": x["id"], "title": x["title"], "chars": len(x["transcript"])} for x in short],
        "missing": [{"id": x["id"], "title": x["title"], "url": x["url"]} for x in missing],
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    from ledger import save_ledger

    save_ledger(ledger, ledger_path)
    print(
        f"wrote {out_path} ready={len(ready)} short={len(short)} "
        f"missing={len(missing)} ledger={ledger_path}"
    )


if __name__ == "__main__":
    main()
