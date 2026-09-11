from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "render_report.py"


def base_suite() -> dict:
    return {
        "suite_id": "suite-1",
        "cases": [
            {
                "id": "TC-001",
                "title": "昵称长度校验",
                "source_refs": ["AC-001"],
                "assertions": [
                    {"id": "A1", "expected": "超过 20 字符时显示错误", "required": True},
                    {"id": "A2", "expected": "非法昵称不得保存", "required": True},
                ],
            }
        ],
    }


class RenderReportTest(unittest.TestCase):
    def run_renderer(self, report: dict, suite: dict, *, output_dir: str = "rendered") -> str:
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = pathlib.Path(temp_dir)
            report_dir = tmp_path / "run"
            report_dir.mkdir()
            report_path = report_dir / "report.json"
            suite_path = report_dir / "test-cases.json"
            report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            suite_path.write_text(json.dumps(suite, ensure_ascii=False), encoding="utf-8")

            for result in report.get("case_results", []):
                for actual in result.get("actuals", []):
                    for evidence in actual.get("evidence", []):
                        artifact = evidence.get("artifact_path")
                        if artifact:
                            path = report_dir / artifact
                            path.parent.mkdir(parents=True, exist_ok=True)
                            path.write_text("artifact", encoding="utf-8")

            out = tmp_path / output_dir / "test-report.md"
            out.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                [sys.executable, str(SCRIPT), str(report_path), "--suite", str(suite_path), "--out", str(out)],
                check=True,
            )
            return out.read_text(encoding="utf-8")

    def test_renders_hybrid_tables_and_inline_screenshot_relative_to_output(self) -> None:
        report = {
            "suite_id": "suite-1",
            "context_id": "staging",
            "provisioning": [],
            "summary": {"total": 1, "passed": 0, "failed": 1, "blocked": 0, "not_executed": 0},
            "case_results": [
                {
                    "case_id": "TC-001",
                    "status": "FAIL",
                    "actuals": [
                        {
                            "assertion_id": "A1",
                            "status": "FAIL",
                            "observed": "页面未显示错误",
                            "evidence": [
                                {"kind": "screenshot", "summary": "昵称超长仍可保存", "artifact_path": "artifacts/fail.png"},
                                {"kind": "browser_dom", "summary": "错误提示节点不存在", "artifact_path": "artifacts/dom.txt"},
                            ],
                        },
                        {"assertion_id": "A2", "status": "FAIL", "observed": "刷新后昵称仍保留", "evidence": []},
                    ],
                    "blockers": [],
                    "failure_description": "输入 21 字符昵称后仍能保存。",
                    "notes": [],
                }
            ],
        }

        rendered = self.run_renderer(report, base_suite())

        self.assertIn("| 总用例 | ✅ PASS | ❌ FAIL | ⛔ BLOCKED | ⏸ NOT_EXECUTED |", rendered)
        self.assertIn("| TC-001 | 昵称长度校验 | ❌ FAIL | 输入 21 字符昵称后仍能保存。 |", rendered)
        self.assertIn("| `A1` | 超过 20 字符时显示错误 | 页面未显示错误 | ❌ FAIL |", rendered)
        self.assertIn("![昵称超长仍可保存](../run/artifacts/fail.png)", rendered)
        self.assertIn("[错误提示节点不存在](../run/artifacts/dom.txt)", rendered)

    def test_embeds_only_key_screenshots_and_links_auxiliary_screenshots(self) -> None:
        report = {
            "suite_id": "suite-1",
            "context_id": "staging",
            "provisioning": [],
            "summary": {"total": 1, "passed": 0, "failed": 1, "blocked": 0, "not_executed": 0},
            "case_results": [
                {
                    "case_id": "TC-001",
                    "status": "FAIL",
                    "actuals": [
                        {
                            "assertion_id": "A1",
                            "status": "FAIL",
                            "observed": "异常",
                            "evidence": [
                                {"kind": "screenshot", "summary": "关键图 1", "artifact_path": "artifacts/1.png"},
                                {"kind": "screenshot", "summary": "关键图 2", "artifact_path": "artifacts/2.png"},
                                {"kind": "screenshot", "summary": "辅助图 3", "artifact_path": "artifacts/3.png"},
                            ],
                        },
                        {"assertion_id": "A2", "status": "PASS", "observed": "无关", "evidence": []},
                    ],
                    "blockers": [],
                    "failure_description": "异常",
                    "notes": [],
                }
            ],
        }

        rendered = self.run_renderer(report, base_suite())

        self.assertIn("![关键图 1](../run/artifacts/1.png)", rendered)
        self.assertIn("![关键图 2](../run/artifacts/2.png)", rendered)
        self.assertNotIn("![辅助图 3]", rendered)
        self.assertIn("[辅助图 3](../run/artifacts/3.png)", rendered)

    def test_escapes_multiline_and_pipe_content_in_tables(self) -> None:
        suite = base_suite()
        suite["cases"][0]["title"] = "昵称 | 校验"
        suite["cases"][0]["assertions"][0]["expected"] = "显示错误 | 不保存\n保持原值"
        report = {
            "suite_id": "suite-1",
            "context_id": "staging",
            "provisioning": [],
            "summary": {"total": 1, "passed": 1, "failed": 0, "blocked": 0, "not_executed": 0},
            "case_results": [
                {
                    "case_id": "TC-001",
                    "status": "PASS",
                    "actuals": [
                        {"assertion_id": "A1", "status": "PASS", "observed": "正确 | 拦截\n未保存", "evidence": []},
                        {"assertion_id": "A2", "status": "PASS", "observed": "未保存", "evidence": []},
                    ],
                    "blockers": [],
                    "failure_description": None,
                    "notes": [],
                }
            ],
        }

        rendered = self.run_renderer(report, suite)

        self.assertIn("昵称 \\| 校验", rendered)
        self.assertIn("显示错误 \\| 不保存<br>保持原值", rendered)
        self.assertIn("正确 \\| 拦截<br>未保存", rendered)

    def test_pass_case_inlines_at_most_one_representative_screenshot(self) -> None:
        report = {
            "suite_id": "suite-1",
            "context_id": "staging",
            "provisioning": [],
            "summary": {"total": 1, "passed": 1, "failed": 0, "blocked": 0, "not_executed": 0},
            "case_results": [
                {
                    "case_id": "TC-001",
                    "status": "PASS",
                    "actuals": [
                        {
                            "assertion_id": "A1",
                            "status": "PASS",
                            "observed": "正确拦截",
                            "evidence": [
                                {"kind": "screenshot", "summary": "代表图", "artifact_path": "artifacts/pass-1.png"},
                                {"kind": "screenshot", "summary": "辅助图", "artifact_path": "artifacts/pass-2.png"},
                            ],
                        },
                        {"assertion_id": "A2", "status": "PASS", "observed": "未保存", "evidence": []},
                    ],
                    "blockers": [],
                    "failure_description": None,
                    "notes": [],
                }
            ],
        }

        rendered = self.run_renderer(report, base_suite())

        self.assertIn("![代表图](../run/artifacts/pass-1.png)", rendered)
        self.assertNotIn("![辅助图]", rendered)
        self.assertIn("[辅助图](../run/artifacts/pass-2.png)", rendered)


if __name__ == "__main__":
    unittest.main()
