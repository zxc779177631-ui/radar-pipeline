#!/usr/bin/env python3
"""Validate source-level skeleton cards without external dependencies."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_FIELDS = (
    "type",
    "source_skeleton_id",
    "name",
    "source_path",
    "source_locator",
    "source_format",
    "pattern_family_ids",
    "family_status",
    "curation_status",
    "curation_basis",
    "performance_status",
    "transfer_scope",
)
REQUIRED_HEADINGS = (
    "## 来源与适用边界",
    "## 原文演绎轨迹",
    "## 注意力推进",
    "## 关键表达锚点",
    "## 不可压缩的差异",
    "## 迁移规则",
    "## 骨架族归属",
    "## 表现证据",
)
TRAFFIC_SIGNATURE_FIELDS = (
    "首句动作",
    "受众识别",
    "停留理由",
    "未闭合问题",
    "兑现位置",
    "证据节奏",
    "最低素材门槛",
    "失效条件",
)
ALLOWED = {
    "family_status": {"existing", "new-candidate", "unclassified"},
    "curation_status": {"curated", "candidate", "retired"},
    "performance_status": {"unknown", "signal", "verified"},
}


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end < 0:
        return {}
    data: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip("\"'")
    return data


def table_data_rows(text: str, heading: str) -> int:
    start = text.find(heading)
    if start < 0:
        return 0
    tail = text[start + len(heading):]
    next_heading = re.search(r"\n##\s", tail)
    block = tail[: next_heading.start()] if next_heading else tail
    rows = [line for line in block.splitlines() if line.lstrip().startswith("|")]
    return max(0, len(rows) - 2)


def validate(path: Path) -> tuple[list[str], list[str], str | None]:
    errors: list[str] = []
    warnings: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    meta = parse_frontmatter(text)
    for field in REQUIRED_FIELDS:
        if field not in meta or meta[field] == "":
            errors.append(f"缺少字段: {field}")
    if meta.get("type") != "source-skeleton":
        errors.append("type 必须是 source-skeleton")
    identifier = meta.get("source_skeleton_id")
    if identifier and not re.fullmatch(r"RS\d+", identifier):
        errors.append("source_skeleton_id 必须为 RS<number>")
    if meta.get("transfer_scope") and meta["transfer_scope"] != "global-method":
        errors.append("transfer_scope 必须是 global-method")
    for field, allowed in ALLOWED.items():
        if meta.get(field) and meta[field] not in allowed:
            errors.append(f"{field} 取值无效: {meta[field]}")
    for heading in REQUIRED_HEADINGS:
        if heading not in text:
            errors.append(f"缺少章节: {heading}")
    if table_data_rows(text, "## 原文演绎轨迹") < 2:
        warnings.append("演绎轨迹少于2个有效节点，检查是否过度抽象")
    if table_data_rows(text, "## 关键表达锚点") < 2:
        warnings.append("关键表达锚点少于2个，可能丢失原文手艺")
    if meta.get("family_status") == "existing" and meta.get("pattern_family_ids") in {"[]", ""}:
        errors.append("family_status=existing 时 pattern_family_ids 不能为空")
    if meta.get("performance_status") in {"signal", "verified"} and "指标、统计窗口与样本量" not in text:
        warnings.append("存在表现判断，但未看到平台、指标、统计窗口与样本量")
    if "## 流量机制签名" not in text:
        warnings.append("缺少流量机制签名；使用本卡写稿前必须回读原文补做 RS Fit")
    else:
        signature_start = text.find("## 流量机制签名")
        signature_tail = text[signature_start:]
        next_heading = re.search(r"\n##\s", signature_tail[3:])
        signature = (
            signature_tail[: next_heading.start() + 3]
            if next_heading
            else signature_tail
        )
        for field in TRAFFIC_SIGNATURE_FIELDS:
            if not re.search(rf"(?m)^-\s*{re.escape(field)}：\s*\S", signature):
                warnings.append(f"流量机制签名未填写: {field}")
    return errors, warnings, identifier


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--file")
    target.add_argument("--dir")
    args = parser.parse_args()
    paths = [Path(args.file)] if args.file else sorted(Path(args.dir).glob("RS*.md"))
    if not paths:
        print("错误：未找到待验证的 RS 卡", file=sys.stderr)
        return 2
    failed = False
    seen: dict[str, Path] = {}
    for path in paths:
        if not path.is_file():
            print(f"FAIL {path}: 文件不存在")
            failed = True
            continue
        errors, warnings, identifier = validate(path)
        if identifier in seen:
            errors.append(f"ID 重复，已用于 {seen[identifier]}")
        elif identifier:
            seen[identifier] = path
        print(("PASS" if not errors else "FAIL") + f" {path}")
        for error in errors:
            print(f"  ERROR: {error}")
        for warning in warnings:
            print(f"  WARNING: {warning}")
        failed = failed or bool(errors)
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
