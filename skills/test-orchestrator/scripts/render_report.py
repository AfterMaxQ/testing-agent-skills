#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib


def load(path: str | None):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8")) if path else None


def main() -> int:
    parser = argparse.ArgumentParser(description="将标准 JSON 测试报告渲染为 Markdown")
    parser.add_argument("report")
    parser.add_argument("--suite")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    report = load(args.report)
    suite = load(args.suite)
    cases = {c["id"]: c for c in (suite or {}).get("cases", [])}
    summary = report["summary"]
    lines = [
        f"# 测试报告 — {report['suite_id']}", "",
        f"**运行上下文：** `{report['context_id']}`", "",
        "## 汇总", "",
        f"- 总数：{summary['total']}", f"- 通过：{summary['passed']}",
        f"- 失败：{summary['failed']}", f"- 阻塞：{summary['blocked']}",
        f"- 未执行：{summary['not_executed']}", "",
    ]

    for result in report["case_results"]:
        case = cases.get(result["case_id"], {})
        title = case.get("title", "")
        lines += [f"## {result['case_id']}{' — ' + title if title else ''}", "", f"**结果：** {result['status']}", ""]
        if case:
            lines += [f"**需求来源：** {', '.join(case.get('source_refs', []))}", "", "### 预期", ""]
            for assertion in case.get("assertions", []):
                lines.append(f"- `{assertion['id']}` {assertion['expected']}")
            lines.append("")

        if result.get("blockers"):
            lines += ["### 阻塞条件", ""]
            for b in result["blockers"]:
                lines.append(f"- `{b['category']}:{b['name']}` — {b['reason']}")
            lines.append("")

        lines += ["### 实际", ""]
        for actual in result.get("actuals", []):
            lines.append(f"- `{actual['assertion_id']}` **{actual['status']}** — {actual['observed']}")
            for evidence in actual.get("evidence", []):
                path = f" (`{evidence['artifact_path']}`)" if evidence.get("artifact_path") else ""
                lines.append(f"  - 证据 [{evidence['kind']}]：{evidence['summary']}{path}")

        if result.get("failure_description"):
            lines += ["", "### 失败 / 阻塞表现", "", result["failure_description"]]
        if result.get("notes"):
            lines += ["", "### 备注", ""] + [f"- {note}" for note in result["notes"]]
        lines.append("")

    pathlib.Path(args.out).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
