#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
口播雷达 · AI 批量入库（AI 预筛 → 自动入库）
输入：radar_ai_filter.py 输出的 JSON（ingest 部分）
流程：
  1. 对每条 ingest 稿生成 `口播雷达入库_{主题}_{标题}.md`（frontmatter + 逐字稿）
  2. 直接 mv 进 Obsidian 【03.参考资料】/文案参考/{主题}/
用法：python3 radar_ai_ingest.py <filter.json> <主题目录名>
      --dry 只预览不写
"""
import json
import os
import re
import sys
import shutil

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
    desc = txt.split("## desc/hashtags", 1)[-1].split("## transcript")[0].strip()
    return desc, body.strip()


def build_md(it, folder):
    desc, body = read_transcript(it["id"]) or ("", "")
    lines = [
        "---",
        f"title: {json.dumps(it['title'], ensure_ascii=False)}",
        f"source_url: {it['url']}",
        f"author: {json.dumps(it.get('author',''), ensure_ascii=False)}",
        "platform: 抖音",
        f"grade: {it.get('grade','')}",
        f"grade_label: {it.get('gradeLabel', it.get('grade',''))}",
        f"tags: [{json.dumps(it.get('keyword',''), ensure_ascii=False)}]",
        "format: null",
        f"suggest_folder: {json.dumps(folder, ensure_ascii=False)}",
        f"liked: {it.get('liked', 0)}",
        "comment: 0",
        "share: 0",
        "collect: 0",
        f"date: {it.get('date','')}",
        "ingested_at: 2026-08-14T00:00:00",
        "curation_status: ai_reviewed_valid",
        "---",
        "",
        f"# {it['title']}",
        "",
        f"> 来源：[{it.get('author','')}]({it['url']}) · 抖音 · 👍{it.get('liked',0):,}",
        "",
        "## 标签",
        f"#{it.get('keyword','')}",
        "",
        "## 口播逐字稿",
        body,
        "",
        "---",
        "*由口播雷达 AI 预筛入库 · 2026-08-14*",
    ]
    return "\n".join(lines)


def main():
    json_path = sys.argv[1]
    folder = sys.argv[2]  # 主题目录名，如 同城 / 商业 / AI工具
    dry = "--dry" in sys.argv
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    items = data["ingest"]
    dest_dir = os.path.join(BASE, folder)
    os.makedirs(dest_dir, exist_ok=True)
    ok = skip = 0
    for it in items:
        fn = f"口播雷达入库_{folder}_{sanitize(it['title'])}.md"
        dest = os.path.join(dest_dir, fn)
        if os.path.exists(dest):
            skip += 1
            continue
        content = build_md(it, folder)
        if dry:
            print(f"  → {folder}/{fn}")
        else:
            with open(dest, "w", encoding="utf-8") as f:
                f.write(content)
        ok += 1
    print(f"=== 入库完成: 写入 {ok} 条, 已存在跳过 {skip} 条 ===")
    print(f"目标: {dest_dir}")


if __name__ == "__main__":
    main()
