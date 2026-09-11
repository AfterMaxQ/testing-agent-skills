#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import pathlib
import urllib.parse

STATUS_LABELS = {
    "PASS": "✅ PASS",
    "FAIL": "❌ FAIL",
    "BLOCKED": "⛔ BLOCKED",
    "NOT_EXECUTED": "⏸ NOT_EXECUTED",
}

INLINE_SCREENSHOT_LIMITS = {
    "FAIL": 2,
    "BLOCKED": 1,
    "PASS": 1,
    "NOT_EXECUTED": 0,
}


def load(path: str | None):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8")) if path else None


def table_cell(value: object) -> str:
    return str(value or "—").replace("\r\n", "\n").replace("\r", "\n").replace("|", "\\|").replace("\n", "<br>")


def markdown_text(value: object) -> str:
    return str(value or "证据").replace("[", "\\[").replace("]", "\\]")


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)


def artifact_href(report_path: pathlib.Path, out_path: pathlib.Path, artifact_path: str) -> str:
    artifact = pathlib.Path(artifact_path)
    if not artifact.is_absolute():
        artifact = report_path.parent / artifact
    try:
        relative = pathlib.Path(os.path.relpath(artifact, out_path.parent)).as_posix()
    except ValueError:
        relative = artifact.as_posix()
    return urllib.parse.quote(relative, safe="/._-~")


def case_core_result(result: dict) -> str:
    status = result.get("status")
    if status == "FAIL" and str(result.get("failure_description") or "").strip():
        return str(result["failure_description"]).strip()
    if status == "BLOCKED" and result.get("blockers"):
        return str(result["blockers"][0].get("reason") or "测试条件受阻")
    if status == "NOT_EXECUTED" and result.get("notes"):
        return str(result["notes"][0])
    for actual in result.get("actuals", []):
        if str(actual.get("observed") or "").strip():
            return str(actual["observed"]).strip()
    return "—"


def evidence_records(result: dict) -> list[tuple[str, int, dict]]:
    records: list[tuple[str, int, dict]] = []
    for actual in result.get("actuals", []):
        assertion_id = actual.get("assertion_id", "")
        for index, evidence in enumerate(actual.get("evidence", [])):
            records.append((assertion_id, index, evidence))
    return records


def append_evidence_sections(
    lines: list[str],
    result: dict,
    report_path: pathlib.Path,
    out_path: pathlib.Path,
) -> None:
    records = evidence_records(result)
    screenshots = [record for record in records if record[2].get("kind") == "screenshot" and record[2].get("artifact_path")]
    limit = INLINE_SCREENSHOT_LIMITS.get(result.get("status"), 0)
    inline = screenshots[:limit]
    inline_keys = {(assertion_id, index) for assertion_id, index, _ in inline}

    if inline:
        lines += ["#### 关键截图", ""]
        for assertion_id, _, evidence in inline:
            href = artifact_href(report_path, out_path, evidence["artifact_path"])
            alt = markdown_text(evidence.get("summary") or f"{assertion_id} 截图")
            lines.append(f"![{alt}]({href})")
            lines.append("")

    other = [record for record in records if (record[0], record[1]) not in inline_keys]
    if other:
        lines += ["#### 其他证据", ""]
        for assertion_id, _, evidence in other:
            kind = evidence.get("kind", "evidence")
            summary = markdown_text(evidence.get("summary") or kind)
            prefix = f"`{assertion_id}` [{kind}]"
            if evidence.get("artifact_path"):
                href = artifact_href(report_path, out_path, evidence["artifact_path"])
                lines.append(f"- {prefix} [{summary}]({href})")
            else:
                lines.append(f"- {prefix} {summary}")
        lines.append("")


def main() -> int:
    parser = argparse.ArgumentParser(description="将标准 JSON 测试报告渲染为 Markdown")
    parser.add_argument("report")
    parser.add_argument("--suite")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    report_path = pathlib.Path(args.report).resolve()
    out_path = pathlib.Path(args.out).resolve()
    report = load(str(report_path))
    suite = load(args.suite)
    cases = {c["id"]: c for c in (suite or {}).get("cases", [])}
    summary = report["summary"]

    lines = [
        f"# 测试报告 — {report['suite_id']}",
        "",
        f"**运行上下文：** `{report['context_id']}`",
        "",
        "## 1. 测试结果总览",
        "",
        "| 总用例 | ✅ PASS | ❌ FAIL | ⛔ BLOCKED | ⏸ NOT_EXECUTED |",
        "|---:|---:|---:|---:|---:|",
        f"| {summary['total']} | {summary['passed']} | {summary['failed']} | {summary['blocked']} | {summary['not_executed']} |",
        "",
        "## 2. 用例总览",
        "",
        "| Case | 用例 | 结果 | 核心结果 |",
        "|---|---|---|---|",
    ]

    for result in report["case_results"]:
        case = cases.get(result["case_id"], {})
        lines.append(
            f"| {table_cell(result['case_id'])} | {table_cell(case.get('title', ''))} | "
            f"{status_label(result['status'])} | {table_cell(case_core_result(result))} |"
        )
    lines.append("")

    if report.get("provisioning"):
        lines += [
            "## 3. 环境准备与清理",
            "",
            "| Provisioner | 状态 | 实际表现 | Cleanup |",
            "|---|---|---|---|",
        ]
        for record in report["provisioning"]:
            cleanup = f"{record['cleanup_status']} — {record['cleanup_observed'] or '无'}"
            lines.append(
                f"| `{table_cell(record['provisioner_id'])}` | {status_label(record['status'])} | "
                f"{table_cell(record['observed'] or '未记录环境准备表现')} | {table_cell(cleanup)} |"
            )
        lines.append("")

        provisioning_evidence = [
            (record["provisioner_id"], evidence)
            for record in report["provisioning"]
            for evidence in record.get("evidence", [])
        ]
        if provisioning_evidence:
            lines += ["### 环境证据", ""]
            for provisioner_id, evidence in provisioning_evidence:
                kind = evidence.get("kind", "evidence")
                summary_text = markdown_text(evidence.get("summary") or kind)
                if evidence.get("artifact_path"):
                    href = artifact_href(report_path, out_path, evidence["artifact_path"])
                    if kind == "screenshot":
                        lines += [f"**`{provisioner_id}`**", "", f"![{summary_text}]({href})", ""]
                    else:
                        lines.append(f"- `{provisioner_id}` [{kind}] [{summary_text}]({href})")
                else:
                    lines.append(f"- `{provisioner_id}` [{kind}] {summary_text}")
            lines.append("")

    detail_number = 4 if report.get("provisioning") else 3
    lines += [f"## {detail_number}. 详细结果", ""]

    for result in report["case_results"]:
        case = cases.get(result["case_id"], {})
        title = case.get("title", "")
        lines += [
            f"### {result['case_id']}{' — ' + title if title else ''}",
            "",
            f"**结果：{status_label(result['status'])}**",
            "",
        ]
        if case.get("source_refs"):
            lines += [f"**需求来源：** {', '.join(case['source_refs'])}", ""]

        assertions = {assertion["id"]: assertion for assertion in case.get("assertions", [])}
        actuals = {actual["assertion_id"]: actual for actual in result.get("actuals", [])}
        assertion_ids = list(assertions)
        assertion_ids += [aid for aid in actuals if aid not in assertions]

        if assertion_ids:
            lines += [
                "| 断言 | 预期 | 实际 | 结果 |",
                "|---|---|---|---|",
            ]
            for assertion_id in assertion_ids:
                expected = assertions.get(assertion_id, {}).get("expected", "—")
                actual = actuals.get(assertion_id, {})
                lines.append(
                    f"| `{table_cell(assertion_id)}` | {table_cell(expected)} | "
                    f"{table_cell(actual.get('observed', '—'))} | {status_label(actual.get('status', 'NOT_EXECUTED'))} |"
                )
            lines.append("")

        if result.get("blockers"):
            lines += ["#### 阻塞条件", ""]
            for blocker in result["blockers"]:
                lines.append(f"- `{blocker['category']}:{blocker['name']}` — {blocker['reason']}")
            lines.append("")

        if result.get("failure_description"):
            lines += ["#### 失败表现", "", result["failure_description"], ""]

        append_evidence_sections(lines, result, report_path, out_path)

        if result.get("notes"):
            lines += ["#### 备注", ""] + [f"- {note}" for note in result["notes"]] + [""]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
