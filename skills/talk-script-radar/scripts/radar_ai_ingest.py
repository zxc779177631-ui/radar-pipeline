#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
口播雷达 · 规则预筛后入库
输入：radar_ai_filter.py 输出的 JSON
一次做完：
  1. ingest 条搬进 Obsidian 【03.参考资料】/文案参考/{主题}/
  2. 回写账本 ingested（已存在文件也补账）
  3. reject 条标账本 excluded，下次不再转
  4. 写出待出 RS 队列（reference-copy-ingester 没有可调用批量命令，必须由 agent 出卡）
用法：python3 radar_ai_ingest.py <filter.json> <主题目录名>
      --dry 只预览不写
      --no-rs-queue 不写待出 RS 队列
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from ledger import default_ledger_path, load_ledger, save_ledger, upsert  # noqa: E402

OBSIDIAN = os.path.expanduser(
    "~/Library/Mobile Documents/iCloud~md~obsidian/Documents/git")
BASE = os.path.join(OBSIDIAN, "【03.参考资料】", "文案参考")
TXDIR = os.path.expanduser("~/Downloads/douyin-transcripts")


def sanitize(name):
    return re.sub(r'[\\/:*?"<>|\s#]+', "_", name).strip("_")[:60]


def read_transcript(video_id):
    p = os.path.join(TXDIR, f"{video_id}.txt")
    if not os.path.exists(p):
        return None
    txt = open(p, encoding="utf-8", errors="ignore").read()
    body = txt.split("## transcript", 1)[-1] if "## transcript" in txt else txt
    desc = ""
    if "## desc/hashtags" in txt:
        desc = txt.split("## desc/hashtags", 1)[-1].split("## transcript")[0].strip()
    return desc, body.strip()


def build_md(it, folder, now_iso, today, platform="douyin"):
    _desc, body = read_transcript(it["id"]) or ("", "")
    lines = [
        "---",
        f"title: {json.dumps(it['title'], ensure_ascii=False)}",
        f"source_url: {it['url']}",
        f"author: {json.dumps(it.get('author',''), ensure_ascii=False)}",
        f"platform: {'小红书' if platform == 'xhs' else '抖音'}",
        f"grade: {json.dumps(it.get('grade',''), ensure_ascii=False)}",
        f"grade_label: {json.dumps(it.get('gradeLabel', it.get('grade','')), ensure_ascii=False)}",
        f"tags: [{json.dumps(it.get('keyword',''), ensure_ascii=False)}]",
        "format: null",
        f"suggest_folder: {json.dumps(folder, ensure_ascii=False)}",
        f"liked: {it.get('liked', 0)}",
        "comment: 0",
        "share: 0",
        "collect: 0",
        f"date: {json.dumps(it.get('date',''), ensure_ascii=False)}",
        f"ingested_at: {now_iso}",
        "curation_status: ai_reviewed_valid",
        "rs_status: queued",
        "---",
        "",
        f"# {it['title']}",
        "",
        f"> 来源：[{it.get('author','')}]({it['url']}) · {'小红书' if platform == 'xhs' else '抖音'} · 👍{it.get('liked',0):,}",
        "",
        "## 标签",
        f"#{it.get('keyword','')}",
        "",
        "## 口播逐字稿",
        body,
        "",
        "---",
        f"*由口播雷达规则预筛入库 · {today}*",
    ]
    return "\n".join(lines)


def write_rs_queue(paths, folder, today, dest_dir):
    radar_dir = os.path.join(BASE, "雷达清单")
    os.makedirs(radar_dir, exist_ok=True)
    queue_path = os.path.join(radar_dir, f"待出RS卡_{folder}_{today}.md")
    lines = [
        f"# 待出 RS 卡 · {folder} · {today}",
        "",
        f"- 共 {len(paths)} 条已入库，尚未提炼单篇演绎卡",
        "- `reference-copy-ingester` 没有可调用的批量脚本，必须由 agent 按该 skill 逐篇出卡",
        "- 出完一张就把本清单对应行删掉，或把入库 md 的 `rs_status` 改成 `done`",
        "",
    ]
    for p in paths:
        lines.append(f"- [ ] `{p}`")
    lines.append("")
    with open(queue_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return queue_path


def main():
    if len(sys.argv) < 3:
        print("用法: radar_ai_ingest.py <filter.json> <主题目录名> [--dry] [--no-rs-queue] [--platform douyin|xhs]", file=sys.stderr)
        sys.exit(2)
    json_path = sys.argv[1]
    folder = sys.argv[2]
    dry = "--dry" in sys.argv
    no_queue = "--no-rs-queue" in sys.argv
    platform = "douyin"
    if "--platform" in sys.argv:
        _pi = sys.argv.index("--platform")
        if _pi + 1 < len(sys.argv):
            platform = sys.argv[_pi + 1]
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("ingest") or []
    rejects = data.get("reject") or []
    dest_dir = os.path.join(BASE, folder)
    os.makedirs(dest_dir, exist_ok=True)

    today = dt.date.today().isoformat()
    now_iso = dt.datetime.now().isoformat(timespec="seconds")
    ledger = load_ledger()
    ok = skip = ledger_n = excl_n = 0
    written_paths = []

    for it in items:
        vid = str(it.get("id") or "")
        fn = f"口播雷达入库_{folder}_{sanitize(it['title'])}.md"
        dest = os.path.join(dest_dir, fn)
        rel = os.path.relpath(dest, OBSIDIAN)
        existed = os.path.exists(dest)
        if not existed:
            content = build_md(it, folder, now_iso, today, platform)
            if dry:
                print(f"  → {folder}/{fn}")
            else:
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(content)
            ok += 1
        else:
            skip += 1
        if upsert(
            ledger,
            vid,
            status="ingested",
            title=(it.get("title") or "")[:80],
            url=it.get("url"),
            liked=it.get("liked", 0),
            source="radar_ai_ingest",
            path=rel,
            folder=folder,
        ):
            ledger_n += 1
        written_paths.append(rel)

    for it in rejects:
        vid = str(it.get("id") or "")
        if upsert(
            ledger,
            vid,
            status="excluded",
            title=(it.get("title") or "")[:80],
            url=it.get("url"),
            liked=it.get("liked", 0),
            source="radar_ai_ingest",
            note=it.get("reason", ""),
        ):
            excl_n += 1

    queue_path = ""
    if not dry:
        save_ledger(ledger)
        if written_paths and not no_queue:
            queue_path = write_rs_queue(written_paths, folder, today, dest_dir)

    print(f"=== 入库完成: 写入 {ok} 条, 已存在跳过 {skip} 条 ===")
    print(f"目标: {dest_dir}")
    print(f"账本: ingested+={ledger_n} excluded+={excl_n} → {default_ledger_path()}")
    if queue_path:
        print(f"待出 RS 队列: {queue_path}（{len(written_paths)} 条，下一步跑 reference-copy-ingester）")
    elif written_paths and not dry and not no_queue:
        print("待出 RS 队列: 未写出")
    if dry:
        print("(dry-run，未写文件/账本)")


if __name__ == "__main__":
    main()
