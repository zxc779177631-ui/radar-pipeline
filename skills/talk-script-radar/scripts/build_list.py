#!/usr/bin/env python3
"""把 MediaCrawler 抖音 jsonl 收成候选清单。不抓数据，只过滤+渲染。"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from ledger import default_ledger_path, known_vids, load_ledger, vid_of  # noqa: E402

TALK_HINTS = (
    "避坑",
    "误区",
    "认知",
    "思维",
    "法则",
    "干货",
    "揭秘",
    "底层",
    "逻辑",
    "融资",
    "合伙",
    "创业",
    "老板",
    "管理",
    "财富",
    "商业",
    "黄金",
    "秘诀",
    "陷阱",
    "贷款",
    "估值",
    "口播",
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Render talk-script radar candidate list")
    p.add_argument("--mode", choices=["daily", "collect"], default="daily")
    p.add_argument("--platform", choices=["douyin", "xhs"], default="douyin",
                   help="数据源平台（默认 douyin；xhs=小红书）")
    p.add_argument("--max-age-days", type=int, default=90)
    p.add_argument(
        "--min-likes",
        type=int,
        default=None,
        help="最低点赞门槛（默认 抖音5000 / 小红书1000）。0 关闭门槛。",
    )
    p.add_argument(
        "--contents",
        default="",
        help="search_contents jsonl；默认取 MediaCrawler 当天文件（按 --platform 选目录）",
    )
    p.add_argument(
        "--comments",
        default="",
        help="search_comments jsonl；默认取 MediaCrawler 当天文件",
    )
    p.add_argument(
        "--out",
        default="",
        help="输出 markdown；daily 默认 爆款候选清单_YYYY-MM-DD.md",
    )
    p.add_argument("--discovery", default="", help="发现层说明，写入清单头部")
    p.add_argument("--keep", type=int, default=0, help="daily 默认 25，collect 不截断")
    p.add_argument(
        "--ledger",
        default="",
        help="seen-ledger.json；默认知识库雷达清单目录。空账本不挡清单。",
    )
    p.add_argument(
        "--no-ledger",
        action="store_true",
        help="不过历史账本（仅当天去重）。小红书默认即跳过，因其 note_id 非数字、不入抖音账本",
    )
    p.add_argument(
        "--exclude",
        default="",
        help="逗号分隔排除词，命中标题/关键词则剔除。默认同 assets/default-tags.yaml",
    )
    return p.parse_args()


def default_jsonl(kind: str, platform: str = "douyin") -> Path:
    today = dt.date.today().isoformat()
    return Path.home() / "MediaCrawler" / "data" / platform / "jsonl" / f"{kind}_{today}.jsonl"


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        raise FileNotFoundError(f"找不到数据文件: {path}")
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def to_int(v, default=0) -> int:
    s = str(v).strip().replace(",", "")
    if not s:
        return default
    # XHS 赞数常是中文「万」格式，如 "1.2万" / "3万"
    m = re.match(r"^\s*([\d.]+)\s*万", s)
    if m:
        try:
            return int(float(m.group(1)) * 10000)
        except (TypeError, ValueError):
            return default
    try:
        return int(s)
    except (TypeError, ValueError):
        return default


def publish_dt(v: dict, platform: str = "douyin") -> dt.datetime | None:
    ts = v.get("time") or v.get("last_update_time") if platform == "xhs" else v.get("create_time")
    try:
        ts = int(ts)
    except (TypeError, ValueError):
        return None
    if ts > 10**12:
        ts //= 1000
    try:
        return dt.datetime.fromtimestamp(ts)
    except (OverflowError, OSError, ValueError):
        return None


def tier(likes: int) -> str:
    if likes >= 50_000:
        return "绝对爆款"
    if likes >= 5_000:
        return "中等热度"
    return "中小热度"


def format_hint(title: str) -> str:
    t = title or ""
    if any(k in t for k in TALK_HINTS):
        return "口播(启发式)"
    return "待确认"


def dedupe(videos: list[dict], platform: str = "douyin") -> list[dict]:
    best: dict[str, dict] = {}
    for v in videos:
        aid = str(v.get("note_id") if platform == "xhs" else (v.get("aweme_id") or v.get("aweme_url")) or "")
        if not aid:
            continue
        cur = best.get(aid)
        if cur is None or to_int(v.get("liked_count")) > to_int(cur.get("liked_count")):
            best[aid] = v
    return list(best.values())


def top_comments(comments: list[dict], note_key: str, platform: str = "douyin", n: int = 3) -> list[dict]:
    key_field = "note_id" if platform == "xhs" else "aweme_id"
    items = [c for c in comments if str(c.get(key_field)) == str(note_key)]
    items.sort(key=lambda c: to_int(c.get("like_count") or c.get("liked_count")), reverse=True)
    return items[:n]


def default_excludes() -> list[str]:
    yml = Path(__file__).resolve().parent.parent / "assets" / "default-tags.yaml"
    words = []
    if not yml.exists():
        return words
    in_ex = False
    for line in yml.read_text(encoding="utf-8").splitlines():
        if line.startswith("exclude:"):
            in_ex = True
            continue
        if in_ex:
            if line.startswith("  - "):
                words.append(line[4:].strip().strip("'\""))
            elif line.strip() and not line.startswith(" "):
                break
    return words


def hit_exclude(v: dict, words: list[str]) -> bool:
    if not words:
        return False
    hay = " ".join(
        [
            str(v.get("title") or ""),
            str(v.get("desc") or ""),
            str(v.get("source_keyword") or ""),
        ]
    )
    return any(w and w in hay for w in words)


def render(
    mode: str,
    videos: list[dict],
    comments: list[dict],
    max_age_days: int,
    discovery: str,
    dropped_old: int,
    dropped_seen: int = 0,
    dropped_exclude: int = 0,
    dropped_likes: int = 0,
    platform: str = "douyin",
) -> str:
    today = dt.date.today().isoformat()
    platform_name = "小红书" if platform == "xhs" else "抖音"
    key_field = "note_id" if platform == "xhs" else "aweme_id"
    cmap = defaultdict(list)
    for c in comments:
        cmap[str(c.get(key_field))].append(c)

    by_tier = {"绝对爆款": [], "中等热度": [], "中小热度": []}
    for v in videos:
        by_tier[tier(to_int(v.get("liked_count")))].append(v)

    lines = [
        f"# 爆款候选清单 · {platform_name} · {today}",
        "",
        f"- 场景：`{mode}`"
        + (f"（时间过滤 ≤{max_age_days} 天）" if mode == "daily" else "（不过时间）"),
        f"- 去重后保留：{len(videos)} 条"
        + (f"；因超期剔除 {dropped_old} 条" if dropped_old else "")
        + (f"；账本已见剔除 {dropped_seen} 条" if dropped_seen else "")
        + (f"；排除词剔除 {dropped_exclude} 条" if dropped_exclude else "")
        + (f"；低赞剔除 {dropped_likes} 条" if dropped_likes else ""),
        f"- 评论样本：{len(comments)} 条（每条展示最多 3 条高赞评）",
        f"- 分档：绝对爆款 {len(by_tier['绝对爆款'])} · 中等 {len(by_tier['中等热度'])} · 中小热度 {len(by_tier['中小热度'])}",
        "- 注意：无粉丝数字段，中小热度 ≠ 已验证低粉；口播栏仅为标题启发式",
        "",
        "> 用法：清单已过赞数/标题排除/账本。只转本清单幸存者 → 规则预筛看稿 → 入库回写账本+出 RS 队列",
        "",
    ]
    if discovery.strip():
        lines += ["## 发现层", "", discovery.strip(), "", "---", ""]
    else:
        lines += ["---", ""]

    headings = {
        "绝对爆款": "## 绝对爆款（≥5万赞，选题天花板）",
        "中等热度": "## 中等热度（5千–5万赞）",
        "中小热度": "## 中小热度（<5千赞，可能小号，未验粉丝）",
    }
    idx = 1
    for name in ("绝对爆款", "中等热度", "中小热度"):
        rows = by_tier[name]
        lines += [headings[name], ""]
        if not rows:
            lines += ["（本档为空）", ""]
            continue
        for v in rows:
            likes = to_int(v.get("liked_count"))
            pub = publish_dt(v, platform)
            pub_s = pub.strftime("%Y-%m-%d") if pub else "未知日期"
            age = f"{(dt.datetime.now() - pub).days}天前" if pub else ""
            title = (v.get("title") or v.get("desc") or "无标题").replace("\n", " ").strip()
            if platform == "xhs":
                note_id = v.get("note_id") or ""
                url = v.get("note_url") or (f"https://www.xiaohongshu.com/explore/{note_id}" if note_id else "")
                user = v.get("user") if isinstance(v.get("user"), dict) else {}
                nick = user.get("nickname") or v.get("nickname") or "?"
                ntype = "视频笔记" if str(v.get("type", "")).lower() == "video" else "图文笔记"
            else:
                url = v.get("aweme_url") or ""
                nick = v.get("nickname") or "?"
                ntype = ""
            kw = v.get("source_keyword") or ""
            hint = format_hint(title)
            typetag = f" · {ntype}" if ntype else ""
            lines.append(f"**{idx}.** [{title}]({url})")
            lines.append(
                f"　　👍{likes:,} · 💬{to_int(v.get('comment_count')):,} · "
                f"🔁{to_int(v.get('share_count')):,} · ⭐{to_int(v.get('collected_count')):,} · "
                f"@{nick} · {pub_s} {age} · #{kw} · {hint}{typetag}"
            )
            for c in top_comments(comments, str(v.get(key_field)), platform):
                text = (c.get("content") or "").replace("\n", " ").strip()
                if not text:
                    continue
                if len(text) > 80:
                    text = text[:80] + "…"
                clike = to_int(c.get("like_count") or c.get("liked_count"))
                lines.append(f"　　- 评 👍{clike}: {text}")
            lines.append("")
            idx += 1
        lines += ["---", ""]
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    args = parse_args()
    platform = args.platform
    contents_path = Path(args.contents) if args.contents else default_jsonl("search_contents", platform)
    comments_path = Path(args.comments) if args.comments else default_jsonl("search_comments", platform)
    today = dt.date.today().isoformat()
    if args.out:
        out_path = Path(args.out)
    elif args.mode == "collect":
        out_path = Path.cwd() / f"爆款候选清单_全量_{today}.md"
    else:
        out_path = Path.cwd() / f"爆款候选清单_{today}.md"

    videos = dedupe(load_jsonl(contents_path), platform)
    comments = load_jsonl(comments_path) if comments_path.exists() else []
    dropped_old = 0
    dropped_seen = 0
    dropped_exclude = 0
    dropped_likes = 0
    if args.mode == "daily":
        kept = []
        cutoff = dt.datetime.now() - dt.timedelta(days=args.max_age_days)
        for v in videos:
            pub = publish_dt(v, platform)
            if pub is None or pub >= cutoff:
                kept.append(v)
            else:
                dropped_old += 1
        videos = kept

    words = [w.strip() for w in args.exclude.split(",") if w.strip()] if args.exclude else default_excludes()
    if words:
        kept = []
        for v in videos:
            if hit_exclude(v, words):
                dropped_exclude += 1
            else:
                kept.append(v)
        videos = kept

    # 赞数门槛：抖音默认 5000，小红书默认 1000；0 关闭。
    min_likes = args.min_likes if args.min_likes is not None else (1000 if platform == "xhs" else 5000)
    if min_likes > 0:
        kept = []
        for v in videos:
            if to_int(v.get("liked_count")) < min_likes:
                dropped_likes += 1
                continue
            kept.append(v)
        videos = kept

    # 账本去重仅对抖音生效：小红书 note_id 非数字、不入抖音账本，默认跳过
    use_ledger = (not args.no_ledger) and platform == "douyin"
    if use_ledger:
        ledger = load_ledger(Path(args.ledger) if args.ledger else default_ledger_path())
        seen = known_vids(ledger)
        if seen:
            kept = []
            for v in videos:
                key = vid_of(v.get("aweme_id") or v.get("aweme_url") or "")
                if key and key in seen:
                    dropped_seen += 1
                else:
                    kept.append(v)
            videos = kept

    videos.sort(key=lambda v: to_int(v.get("liked_count")), reverse=True)
    keep = args.keep or (25 if args.mode == "daily" else 0)
    if keep:
        videos = videos[:keep]

    text = render(
        args.mode,
        videos,
        comments,
        args.max_age_days,
        args.discovery,
        dropped_old,
        dropped_seen,
        dropped_exclude,
        dropped_likes,
        platform,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    print(
        f"wrote {out_path} ({len(videos)} videos, dropped_old={dropped_old}, "
        f"dropped_seen={dropped_seen}, dropped_exclude={dropped_exclude}, "
        f"dropped_likes={dropped_likes}, min_likes={min_likes}, platform={platform})"
    )


if __name__ == "__main__":
    main()
