#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
口播雷达 · AI 预筛（人工过眼 → AI 预筛升级版）
规则（2026-08-14 用户确认）：
  1. reject（不入库）：无口播（混剪/跳舞/卡点/BGM/翻唱等）、重策划访谈（访谈/专访/对谈/对话节目）
  2. review（交人工）：字数特别短(<150)或特别长(>2500)，可能转写不全或重策划
  3. ingest（直接入库）：其余（有连续口播、数据正常）
用法：python3 radar_ai_filter.py <清单md> <输出json>
"""
import json
import os
import re
import sys

TXDIR = os.path.expanduser("~/Downloads/douyin-transcripts")
OBSIDIAN = os.path.expanduser(
    "~/Library/Mobile Documents/iCloud~md~obsidian/Documents/git")

# 无口播特征词（标题命中即剔除）——只保留"强无口播"特征，vlog 类交给字数兜底
NONTALK_TITLE_HINTS = (
    "跳舞", "变装", "BGM", "翻唱", "街拍", "跑酷",
    "舞蹈", "特效", "快闪", "广场舞", "手势舞", "魔术", "穿搭展示",
    "健身操", "舞蹈教学",
)
# 重策划访谈特征词（标题命中即剔除）
INTERVIEW_TITLE_HINTS = (
    "访谈", "专访", "对谈", "对话", "做客", "夜话", "面对面",
    "圆桌", "论坛", "访谈录", "对话录", "深度对话",
)
# 口播特征词（命中加分，帮助区分）
TALK_HINTS = (
    "避坑", "误区", "认知", "思维", "法则", "干货", "揭秘", "底层",
    "逻辑", "融资", "合伙", "创业", "老板", "管理", "财富", "商业",
    "黄金", "秘诀", "陷阱", "贷款", "估值", "口播", "赚钱", "生意",
)

MIN_OK = 150      # 少于=review（可能转写不全/碎片）
MAX_OK = 4000     # 多于=review（可能重策划访谈/超长口播，交人工确认）
MIN_LIKES = 5000  # 赞数门槛（用户 2026-08-14 定：抖音 ≥5000 才入库，小红书 ≥1000）


def read_transcript(video_id):
    p = os.path.join(TXDIR, f"{video_id}.txt")
    if not os.path.exists(p):
        return None
    txt = open(p, encoding="utf-8", errors="ignore").read()
    body = txt.split("## transcript", 1)[-1] if "## transcript" in txt else txt
    return body.strip()


def classify(title, body_len, body_text, liked=0):
    """返回 (action, reason)。action: ingest | review | reject"""
    title = title or ""
    body = body_text or ""
    # 0. 赞数门槛：低于门槛直接剔除（未被市场验证，不算「爆款口播」）
    if liked < MIN_LIKES:
        return "reject", f"仅{liked:,}赞，低于门槛{MIN_LIKES:,}（未验证）"
    # 1. 标题特征强命中 → reject（混剪/跳舞/重策划访谈，标题都会有明确字样）
    hit_nt = [w for w in NONTALK_TITLE_HINTS if w in title]
    if hit_nt:
        return "reject", f"标题像无口播: {'/'.join(hit_nt)}"
    hit_it = [w for w in INTERVIEW_TITLE_HINTS if w in title]
    if hit_it:
        return "reject", f"标题像重策划访谈: {'/'.join(hit_it)}"
    # 2. 字数边界 → review（交人工确认，不硬剔）
    if body_len < MIN_OK:
        return "review", f"仅{body_len}字，过短（可能转写不全/碎片）"
    if body_len > MAX_OK:
        return "review", f"{body_len}字，过长（请人工确认是否重策划访谈）"
    # 3. 其余 → ingest
    return "ingest", f"{body_len}字，正常口播"


def parse_list(md_path):
    """解析候选清单 md，提取 (id, title, url, liked, keyword)"""
    items = []
    cur = None
    for line in open(md_path, encoding="utf-8"):
        m = re.match(r"^\*\*(\d+)\.\*\*\s*\[(.+?)\]\((https://www\.douyin\.com/video/(\d+))\)", line)
        if m:
            cur = {"title": m.group(2), "url": m.group(3), "id": m.group(4),
                   "liked": 0, "keyword": ""}
            items.append(cur)
            continue
        m2 = re.match(r"\s*👍([\d,]+).*?· #(\S+)", line)
        if m2 and cur:
            cur["liked"] = int(m2.group(1).replace(",", ""))
            cur["keyword"] = m2.group(2)
    return items


def main():
    md_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else "radar_ai_filter.json"
    items = parse_list(md_path)
    result = {"ingest": [], "review": [], "reject": [], "missing": []}
    for it in items:
        body = read_transcript(it["id"])
        if body is None:
            it["reason"] = "无逐字稿（视频被删/未转写）"
            result["missing"].append(it)
            continue
        it["body_len"] = len(body)
        act, reason = classify(it["title"], it["body_len"], body, it.get("liked", 0))
        it["action"] = act
        it["reason"] = reason
        it["body_snippet"] = body[:120].replace("\n", " ")
        result[act].append(it)
    # 排序：ingest/review 按赞降序
    for k in ("ingest", "review"):
        result[k].sort(key=lambda x: x.get("liked", 0), reverse=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"=== {os.path.basename(md_path)} ===")
    print(f"直接入库: {len(result['ingest'])} | 交人工: {len(result['review'])} | 剔除: {len(result['reject'])} | 无稿: {len(result['missing'])}")
    print("\n-- 剔除（reject）--")
    for it in result["reject"][:15]:
        print(f"  ✗ {it['liked']:,}赞 | {it['reason']} | {it['title'][:40]}")
    print("\n-- 交人工（review）--")
    for it in result["review"][:15]:
        print(f"  ? {it['liked']:,}赞 | {it['reason']} | {it['title'][:40]}")
    print("\n-- 直接入库（ingest）top 5 --")
    for it in result["ingest"][:5]:
        print(f"  ✓ {it['liked']:,}赞 | {it['reason']} | {it['title'][:40]}")
    return result


if __name__ == "__main__":
    main()
