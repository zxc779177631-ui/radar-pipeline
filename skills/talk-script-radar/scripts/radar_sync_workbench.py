#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
口播雷达 · AI 筛选结果 → 工作台备份 JSON 同步
把 AI 预筛分类写入工作台可导入的备份格式：
  ingest → status=ingested（已入库，工作台不显示为待办）
  review → status=reviewed_ok + note 注明「AI预筛待人工确认」原因
  reject → status=reviewed_bad + note 注明剔除原因
用法：python3 radar_sync_workbench.py <清单md> <filter.json> <主题> <输出.json>
"""
import json
import os
import re
import sys

TXDIR = os.path.expanduser("~/Downloads/douyin-transcripts")

def read_transcript(video_id):
    p = os.path.join(TXDIR, f"{video_id}.txt")
    if not os.path.exists(p):
        return "", ""
    txt = open(p, encoding="utf-8", errors="ignore").read()
    body = txt.split("## transcript", 1)[-1] if "## transcript" in txt else txt
    desc = ""
    if "## desc/hashtags" in txt:
        desc = txt.split("## desc/hashtags",1)[-1].split("## transcript")[0].strip()
    return body.strip(), desc.strip()

def parse_list(md_path):
    items = []
    cur = None
    for line in open(md_path, encoding="utf-8"):
        m = re.match(r"^\*\*(\d+)\.\*\*\s*\[(.+?)\]\((https://www\.douyin\.com/video/(\d+))\)", line)
        if m:
            cur = {"id": m.group(4), "title": m.group(2), "url": m.group(3),
                   "liked": 0, "comment": 0, "share": 0, "collect": 0,
                   "author": "", "tags": [], "keyword": ""}
            items.append(cur)
            continue
        m2 = re.match(r"\s*👍([\d,]+) · 💬([\d,]+) · 🔁([\d,]+) · ⭐([\d,]+) · @(\S+) ·", line)
        if m2 and cur:
            cur["liked"] = int(m2.group(1).replace(",", ""))
            cur["comment"] = int(m2.group(2).replace(",", ""))
            cur["share"] = int(m2.group(3).replace(",", ""))
            cur["collect"] = int(m2.group(4).replace(",", ""))
            cur["author"] = m2.group(5)
        m3 = re.match(r".*· #(\S+) ·", line)
        if m3 and cur and not cur["keyword"]:
            cur["keyword"] = m3.group(1)
    return items

def main():
    md_path, filter_path, topic, out_path = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    items = parse_list(md_path)
    with open(filter_path, encoding="utf-8") as f:
        flt = json.load(f)
    act_map = {}
    for act in ("ingest", "review", "reject", "missing"):
        for it in flt.get(act, []):
            act_map[it["id"]] = (act, it.get("reason", ""))
    candidates = []
    for it in items:
        act, reason = act_map.get(it["id"], ("missing", "无判定"))
        body, desc = read_transcript(it["id"])
        status = {"ingest": "ingested", "review": "reviewed_ok",
                  "reject": "reviewed_bad", "missing": "pending"}[act]
        transcribe_state = "done" if body else ("skipped" if act == "reject" else "pending")
        cand = {
            "id": it["id"], "title": it["title"], "url": it["url"],
            "comments": [], "tags": [it["keyword"]] if it["keyword"] else [],
            "liked": it["liked"], "comment": it["comment"], "share": it["share"],
            "collect": it["collect"], "author": it["author"], "date": "",
            "isTalk": act != "reject", "transcript": body, "grade": "abs",
            "status": status, "transcribeState": transcribe_state,
            "transcriptDesc": desc or it["title"], "note": reason,
            "ingestFolder": topic if act == "ingest" else "",
        }
        candidates.append(cand)
    state = {
        "version": 1,
        "candidates": candidates,
        "transcripts": {},
        "tags": {"durable_seeds": [], "exclude": [], "notes": ""},
        "meta": {
            "listDate": "2026-08-14",
            "lastRun": None,
            "seeded": False,
            "aiFilter": True,
            "aiFilterSource": os.path.basename(filter_path),
        },
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    from collections import Counter
    print(f"=== 主题: {topic} ===")
    print(f"总候选: {len(candidates)}")
    print(f"状态分布: {dict(Counter(c['status'] for c in candidates))}")
    print(f"输出: {out_path}")

if __name__ == "__main__":
    main()
