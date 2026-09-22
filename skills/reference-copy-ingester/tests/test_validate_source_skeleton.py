from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_source_skeleton.py"
TEMPLATE = ROOT / "assets" / "source-skeleton-template.md"


class SourceSkeletonValidationTest(unittest.TestCase):
    def run_card(self, text: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "RS999_test.md"
            path.write_text(text, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPT), "--file", str(path)],
                capture_output=True,
                text=True,
                check=False,
            )

    def valid_card(self) -> str:
        text = TEMPLATE.read_text(encoding="utf-8")
        text = text.replace("RS000", "RS999")
        text = text.replace('name: ""', 'name: "测试卡"')
        text = text.replace('source_path: ""', 'source_path: "source.md"')
        text = text.replace("family_status: unclassified", "family_status: existing")
        text = text.replace("pattern_family_ids: []", "pattern_family_ids: [A1]")
        text = text.replace('created: "<ISO date>"', 'created: "2026-07-24"')
        text = text.replace('updated: "<ISO date>"', 'updated: "2026-07-24"')
        text = text.replace(
            "| 1 |  |  |  |  |",
            "| 1 | 开头判断 | 锁定受众 | 提出问题 | 等待答案 |\n"
            "| 2 | 正文解释 | 兑现判断 | 给出证据 | 获得答案 |",
        )
        text = text.replace(
            "|  |  |  |  |  |\n|  |  |  |  |  |",
            "| 开头判断 | 首句 | 锁定受众 | 迁移功能 | 不迁事实 |\n"
            "| 正文收刀 | 结尾 | 完成兑现 | 迁移节奏 | 不迁 CTA |",
        )
        for field in (
            "首句动作",
            "受众识别",
            "停留理由",
            "未闭合问题",
            "兑现位置",
            "证据节奏",
            "最低素材门槛",
            "失效条件",
        ):
            text = text.replace(f"- {field}：", f"- {field}：已填写")
        return text

    def test_complete_traffic_signature_has_no_signature_warning(self) -> None:
        result = self.run_card(self.valid_card())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("流量机制签名未填写", result.stdout)

    def test_legacy_card_warns_before_rs_fit(self) -> None:
        text = self.valid_card().replace(
            "## 流量机制签名\n\n"
            "- 首句动作：已填写\n"
            "- 受众识别：已填写\n"
            "- 停留理由：已填写\n"
            "- 未闭合问题：已填写\n"
            "- 兑现位置：已填写\n"
            "- 证据节奏：已填写\n"
            "- 最低素材门槛：已填写\n"
            "- 失效条件：已填写\n\n",
            "",
        )
        result = self.run_card(text)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("缺少流量机制签名", result.stdout)


if __name__ == "__main__":
    unittest.main()
