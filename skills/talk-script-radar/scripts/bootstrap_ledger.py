#!/usr/bin/env python3
"""从已入库 md、雷达清单、工作台 SEED 回填 seen-ledger。"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ledger import (  # noqa: E402
    default_ledger_path,
    load_ledger,
    obs_vault,
    save_ledger,
    upsert,
    vid_of,
)

ITEM_RE = re.compile(r"\*\*\d+\.\*\*\s+\[(.*?)\]\((https?://www\.douyin\.com/video/\d+)\)")
SOURCE_RE = re.compile(r"^source_url:\s*(\S+)", re.M)
TITLE_RE = re.compile(r"^title:\s*(.*)$", re.M)


def parse_md_items(text: str) -> list[tuple[str, str]]:
    out = []
    for title, url in ITEM_RE.findall(text):
        vid = vid_of(url)
        if vid:
            out.append((vid, title.strip()))
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Bootstrap talk-script-radar seen ledger")
    p.add_argument("--ledger", default="", help="账本路径；默认知识库雷达清单目录")
    p.add_argument("--workbench", default="", help="口播雷达工作台.html，用来扫 SEED")
    args = p.parse_args()
    path = Path(args.ledger) if args.ledger else default_ledger_path()
    data = load_ledger(path)
    vault = obs_vault()
    n_ingested = n_seen = 0

    ref = vault / "【03.参考资料】/文案参考"
    if ref.exists():
        for fp in ref.rglob("口播雷达入库_*.md"):
            text = fp.read_text(encoding="utf-8")
            m = SOURCE_RE.search(text)
            vid = vid_of(m.group(1) if m else "")
            if not vid:
                continue
            tm = TITLE_RE.search(text)
            title = (tm.group(1).strip().strip('"') if tm else fp.stem)[:80]
            upsert(
                data,
                vid,
                status="ingested",
                title=title,
                source="obsidian-ref",
                path=str(fp.relative_to(vault)),
            )
            n_ingested += 1

    radar_dir = vault / "【03.参考资料】/文案参考/雷达清单"
    extra_lists = [
        Path.cwd() / "爆款口播候选清单_2026-08-13.md",
        Path.cwd() / "爆款口播候选清单_2026-08-14.md",
        Path.cwd() / "爆款口播候选清单_全量_2026-08-14.md",
    ]
    if radar_dir.exists():
        extra_lists.extend(sorted(radar_dir.glob("爆款口播候选清单_*.md")))
    seen_from_lists = set()
    for lp in extra_lists:
        if not lp.exists():
            continue
        for vid, title in parse_md_items(lp.read_text(encoding="utf-8")):
            if vid in (data.get("items") or {}) and (data["items"][vid] or {}).get("status") == "ingested":
                continue
            upsert(data, vid, status="seen", title=title[:80], source=lp.name)
            seen_from_lists.add(vid)
            n_seen += 1

    workbench = Path(args.workbench) if args.workbench else Path.cwd() / "口播雷达工作台.html"
    if workbench.exists():
        html = workbench.read_text(encoding="utf-8")
        m = re.search(r"const SEED_MD = `(.*?)`;", html, re.S)
        if m:
            for vid, title in parse_md_items(m.group(1)):
                if vid in (data.get("items") or {}) and (data["items"][vid] or {}).get("status") == "ingested":
                    continue
                upsert(data, vid, status="seen", title=title[:80], source=workbench.name)
                n_seen += 1

    out = save_ledger(data, path)
    items = data.get("items") or {}
    ingested = sum(1 for v in items.values() if isinstance(v, dict) and v.get("status") == "ingested")
    print(
        f"wrote {out} total={len(items)} ingested={ingested} "
        f"touched_ingested={n_ingested} touched_seen={n_seen} "
        f"lists={len(seen_from_lists)} at={dt.datetime.now().isoformat(timespec='seconds')}"
    )


if __name__ == "__main__":
    main()
