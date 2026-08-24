#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

from jsonschema import Draft202012Validator

SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = SKILL_DIR / "schema.json"
CONTEXT_SCHEMA = SKILL_DIR / "context.schema.json"
SUITE_SCHEMA = SKILL_DIR.parent / "test-design" / "schema.json"

TEST_DESIGN_SCRIPTS = SKILL_DIR.parent / "test-design" / "scripts"
if str(TEST_DESIGN_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(TEST_DESIGN_SCRIPTS))

from validate_context import semantic_errors as context_semantic_errors  # noqa: E402
from validate_testcases import semantic_errors as suite_semantic_errors  # noqa: E402


def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def duplicate_values(values) -> list[str]:
    counts = collections.Counter(value for value in values if isinstance(value, str))
    return sorted(value for value, count in counts.items() if count > 1)


def artifact_error(report_path: pathlib.Path, artifact_path: str) -> str | None:
    candidate = pathlib.Path(artifact_path)
    if not candidate.is_absolute():
        candidate = report_path.parent / candidate
    if not candidate.exists():
        return f"artifact_path does not exist: {artifact_path}"
    return None


def semantic_errors(report: dict, suite: dict, context: dict, report_path: pathlib.Path) -> list[str]:
    semantic: list[str] = []
    results = report.get("case_results", [])
    counts = collections.Counter(result.get("status") for result in results)
    expected_summary = {
        "total": len(suite.get("cases", [])),
        "passed": counts["PASS"],
        "failed": counts["FAIL"],
        "blocked": counts["BLOCKED"],
        "not_executed": counts["NOT_EXECUTED"],
    }
    if report.get("summary") != expected_summary:
        semantic.append(f"summary mismatch: expected {expected_summary}, got {report.get('summary')}")

    if report.get("suite_id") != suite.get("suite_id"):
        semantic.append("report suite_id does not match suite")
    if report.get("context_id") != context.get("context_id"):
        semantic.append("report context_id does not match context")

    suite_cases = {case["id"]: case for case in suite.get("cases", []) if isinstance(case.get("id"), str)}
    result_ids = [result.get("case_id") for result in results]
    for cid in duplicate_values(result_ids):
        semantic.append(f"duplicate case result: {cid}")
    valid_result_ids = {cid for cid in result_ids if isinstance(cid, str)}
    unknown_cases = sorted(valid_result_ids - set(suite_cases))
    missing_cases = sorted(set(suite_cases) - valid_result_ids)
    if unknown_cases:
        semantic.append("unknown case results: " + ", ".join(unknown_cases))
    if missing_cases:
        semantic.append("missing case results: " + ", ".join(missing_cases))

    provisioners = {
        provisioner["id"]: provisioner
        for provisioner in context.get("provisioners", [])
        if isinstance(provisioner.get("id"), str)
    }
    provision_ids = [record.get("provisioner_id") for record in report.get("provisioning", [])]
    for pid in duplicate_values(provision_ids):
        semantic.append(f"duplicate provision result: {pid}")

    for record in report.get("provisioning", []):
        pid = record.get("provisioner_id")
        provisioner = provisioners.get(pid)
        if provisioner is None:
            semantic.append(f"{pid}: provisioner not found in context")
            continue

        if record.get("status") in {"PASS", "FAIL"}:
            if not str(record.get("observed", "")).strip():
                semantic.append(f"{pid}: provision {record.get('status')} requires observed")
            if not record.get("evidence"):
                semantic.append(f"{pid}: provision {record.get('status')} requires evidence")

        cleanup_action = provisioner.get("cleanup_action")
        cleanup_status = record.get("cleanup_status")
        if cleanup_action and cleanup_status == "NOT_REQUIRED":
            semantic.append(f"{pid}: cleanup_action cannot have cleanup_status NOT_REQUIRED")
        if not cleanup_action and cleanup_status != "NOT_REQUIRED":
            semantic.append(f"{pid}: cleanup without cleanup_action must be NOT_REQUIRED")
        if cleanup_status in {"PASS", "FAIL", "NOT_EXECUTED"} and not str(
            record.get("cleanup_observed", "")
        ).strip():
            semantic.append(f"{pid}: cleanup {cleanup_status} requires cleanup_observed")

        for evidence in record.get("evidence", []):
            if evidence.get("artifact_path"):
                message = artifact_error(report_path, evidence["artifact_path"])
                if message:
                    semantic.append(f"{pid}: {message}")

    for result in results:
        cid = result.get("case_id")
        case = suite_cases.get(cid)
        if case is None:
            continue

        assertions = {
            assertion["id"]: assertion
            for assertion in case.get("assertions", [])
            if isinstance(assertion.get("id"), str)
        }
        actuals = result.get("actuals", [])
        actual_ids = [actual.get("assertion_id") for actual in actuals]
        for aid in duplicate_values(actual_ids):
            semantic.append(f"{cid}: duplicate assertion actual: {aid}")

        valid_actual_ids = {aid for aid in actual_ids if isinstance(aid, str)}
        unknown_actuals = sorted(valid_actual_ids - set(assertions))
        if unknown_actuals:
            semantic.append(f"{cid}: unknown assertion actuals: {', '.join(unknown_actuals)}")

        actual_by_id = {
            actual.get("assertion_id"): actual
            for actual in actuals
            if isinstance(actual.get("assertion_id"), str)
        }
        required_ids = [assertion["id"] for assertion in case.get("assertions", []) if assertion.get("required")]
        missing_required = [aid for aid in required_ids if aid not in actual_by_id]
        if missing_required:
            semantic.append(f"{cid}: missing required assertion results: {', '.join(missing_required)}")

        for actual in actuals:
            aid = actual.get("assertion_id")
            assertion = assertions.get(aid)
            if assertion is None:
                continue

            status = actual.get("status")
            evidence = actual.get("evidence", [])
            if status in {"PASS", "FAIL"}:
                if not str(actual.get("observed", "")).strip():
                    semantic.append(f"{cid}/{aid}: {status} requires observed")
                if not evidence:
                    semantic.append(f"{cid}/{aid}: {status} requires evidence")

                allowed = set(assertion.get("observe_via", []))
                actual_kinds = {item.get("kind") for item in evidence}
                disallowed = sorted(kind for kind in actual_kinds - allowed if isinstance(kind, str))
                missing_kinds = sorted(allowed - actual_kinds)
                if disallowed:
                    semantic.append(f"{cid}/{aid}: evidence kinds not allowed by observe_via: {', '.join(disallowed)}")
                if missing_kinds:
                    semantic.append(f"{cid}/{aid}: missing planned evidence kinds: {', '.join(missing_kinds)}")

            for item in evidence:
                if item.get("artifact_path"):
                    message = artifact_error(report_path, item["artifact_path"])
                    if message:
                        semantic.append(f"{cid}/{aid}: {message}")

        required_statuses = [
            actual_by_id[aid].get("status")
            for aid in required_ids
            if aid in actual_by_id
        ]
        if "FAIL" in required_statuses:
            expected_case_status = "FAIL"
        elif "BLOCKED" in required_statuses:
            expected_case_status = "BLOCKED"
        elif "NOT_EXECUTED" in required_statuses or not required_statuses:
            expected_case_status = "NOT_EXECUTED"
        else:
            expected_case_status = "PASS"

        if result.get("status") != expected_case_status:
            semantic.append(f"{cid}: expected case status {expected_case_status}, got {result.get('status')}")

        has_blocked_assertion = "BLOCKED" in required_statuses
        if has_blocked_assertion and not result.get("blockers"):
            semantic.append(f"{cid}: blocked assertion requires blockers")
        if not has_blocked_assertion and result.get("blockers"):
            semantic.append(f"{cid}: blockers require a blocked assertion")
        if result.get("status") == "FAIL" and not str(result.get("failure_description") or "").strip():
            semantic.append(f"{cid}: FAIL requires failure_description")
        if result.get("status") == "NOT_EXECUTED" and not result.get("notes"):
            semantic.append(f"{cid}: NOT_EXECUTED requires notes")

        if case.get("design_status") == "NEEDS_CLARIFICATION":
            categories = {blocker.get("category") for blocker in result.get("blockers", [])}
            if "requirement_clarification" not in categories:
                semantic.append(f"{cid}: NEEDS_CLARIFICATION requires requirement_clarification blocker")

    return semantic


def main() -> int:
    parser = argparse.ArgumentParser(description="校验统一测试报告及其与 Suite/Context 的一致性")
    parser.add_argument("report")
    parser.add_argument("--suite", required=True)
    parser.add_argument("--context", required=True)
    args = parser.parse_args()

    report_path = pathlib.Path(args.report)
    try:
        report = load(report_path)
        schema = load(SCHEMA)
        suite = load(pathlib.Path(args.suite))
        context = load(pathlib.Path(args.context))
        suite_schema = load(SUITE_SCHEMA)
        context_schema = load(CONTEXT_SCHEMA)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    errors = []
    for label, data, contract in (
        ("REPORT", report, schema),
        ("SUITE", suite, suite_schema),
        ("CONTEXT", context, context_schema),
    ):
        errors.extend(
            (label, error)
            for error in sorted(
                Draft202012Validator(contract).iter_errors(data),
                key=lambda item: list(item.absolute_path),
            )
        )
    semantic = []
    if not errors:
        semantic = semantic_errors(report, suite, context, report_path)
        semantic += [f"SUITE: {message}" for message in suite_semantic_errors(suite)]
        semantic += [f"CONTEXT: {message}" for message in context_semantic_errors(context)]

    if errors or semantic:
        for label, error in errors:
            path = ".".join(str(item) for item in error.absolute_path) or "<root>"
            print(f"SCHEMA {label} {path}: {error.message}", file=sys.stderr)
        for message in semantic:
            print(f"SEMANTIC: {message}", file=sys.stderr)
        return 1

    print(f"OK: {args.report} ({len(report.get('case_results', []))} results)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
