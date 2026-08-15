#!/usr/bin/env python3
"""跨天/跨机视频号账本。vid 必须当字符串，禁止 int()。"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

VID_RE = re.compile(r"(?:video/)?(\d{15,})")

DEFAULT_STATUSES_BLOCK_LIST = (
    "seen",
    "transcribed",
    "reviewed_ok",
    "reviewed_bad",
    "ingested",
    "excluded",
)

# 只升不降：merge_inbox / bootstrap 不能把 ingested 打回 transcribed/seen
STATUS_RANK = {
    "seen": 1,
    "transcribed": 2,
    "reviewed_ok": 3,
    "reviewed_bad": 3,
    "excluded": 4,
    "ingested": 5,
}


def obs_vault() -> Path:
    return Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/git"


def default_ledger_path() -> Path:
    ref = obs_vault() / "【03.参考资料】/文案参考"
    preferred = ref / "雷达清单" / "seen-ledger.json"
    if ref.exists() or preferred.exists():
        return preferred
    return Path(__file__).resolve().parent.parent / "data" / "seen-ledger.json"


def vid_of(value) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in ("vid", "id", "aweme_id", "url", "source_url", "aweme_url"):
            found = vid_of(value.get(key))
            if found:
                return found
        return ""
    s = str(value).strip()
    m = VID_RE.search(s)
    return m.group(1) if m else ""


def empty_ledger() -> dict:
    return {"version": 1, "updated": None, "items": {}}


def load_ledger(path: Path | None = None) -> dict:
    path = path or default_ledger_path()
    if not path.exists():
        return empty_ledger()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_ledger()
    if not isinstance(data, dict):
        return empty_ledger()
    items = data.get("items")
    if not isinstance(items, dict):
        data["items"] = {}
    else:
        data["items"] = {str(k): v for k, v in items.items() if vid_of(k)}
    data.setdefault("version", 1)
    return data


def save_ledger(data: dict, path: Path | None = None) -> Path:
    path = path or default_ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data["version"] = 1
    data["updated"] = dt.datetime.now().isoformat(timespec="seconds")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def status_rank(status: str | None) -> int:
    return STATUS_RANK.get(str(status or ""), 0)


def upsert(data: dict, vid: str, **fields) -> bool:
    vid = vid_of(vid)
    if not vid:
        return False
    items = data.setdefault("items", {})
    row = items.get(vid) or {}
    if not isinstance(row, dict):
        row = {}
    now = dt.datetime.now().isoformat(timespec="seconds")
    row.setdefault("first_seen", now)
    row["updated"] = now
    new_status = fields.pop("status", None)
    for key, value in fields.items():
        if value is not None:
            row[key] = value
    if new_status is not None:
        if status_rank(new_status) >= status_rank(row.get("status")):
            row["status"] = new_status
    elif "status" not in row:
        row["status"] = "seen"
    items[vid] = row
    return True


def known_vids(data: dict, statuses: tuple[str, ...] | None = None) -> set[str]:
    statuses = statuses or DEFAULT_STATUSES_BLOCK_LIST
    out = set()
    for vid, row in (data.get("items") or {}).items():
        key = vid_of(vid)
        if not key:
            continue
        status = ""
        if isinstance(row, dict):
            status = str(row.get("status") or "")
        if status in statuses or not statuses:
            out.add(key)
    return out
