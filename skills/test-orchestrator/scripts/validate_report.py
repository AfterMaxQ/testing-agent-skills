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


def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report")
    parser.add_argument("--suite")
    parser.add_argument("--context")
    args = parser.parse_args()

    try:
        report = load(pathlib.Path(args.report))
        schema = load(SCHEMA)
        suite = load(pathlib.Path(args.suite)) if args.suite else None
        context = load(pathlib.Path(args.context)) if args.context else None
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    errors = sorted(Draft202012Validator(schema).iter_errors(report), key=lambda e: list(e.absolute_path))
    semantic: list[str] = []

    results = report.get("case_results", [])
    counts = collections.Counter(r.get("status") for r in results)
    expected_summary = {
        "total": len(results), "passed": counts["PASS"], "failed": counts["FAIL"],
        "blocked": counts["BLOCKED"], "not_executed": counts["NOT_EXECUTED"],
    }
    if report.get("summary") != expected_summary:
        semantic.append(f"summary mismatch: expected {expected_summary}, got {report.get('summary')}")

    if suite and report.get("suite_id") != suite.get("suite_id"):
        semantic.append("report suite_id does not match suite")
    if context and report.get("context_id") != context.get("context_id"):
        semantic.append("report context_id does not match context")

    suite_cases = {c["id"]: c for c in (suite or {}).get("cases", [])}

    for result in results:
        cid = result.get("case_id")
        actuals = result.get("actuals", [])
        actual_by_id = {a.get("assertion_id"): a for a in actuals}

        for actual in actuals:
            if actual.get("status") == "PASS" and not actual.get("evidence"):
                semantic.append(f"{cid}/{actual.get('assertion_id')}: PASS requires evidence")

        if result.get("status") == "BLOCKED" and not result.get("blockers"):
            semantic.append(f"{cid}: BLOCKED requires blockers")
        if result.get("status") != "BLOCKED" and result.get("blockers"):
            semantic.append(f"{cid}: blockers are only valid for BLOCKED case result")

        if suite and cid not in suite_cases:
            semantic.append(f"{cid}: case not found in suite")
            continue

        if suite:
            required_ids = [a["id"] for a in suite_cases[cid]["assertions"] if a["required"]]
            missing = [aid for aid in required_ids if aid not in actual_by_id]
            if missing:
                semantic.append(f"{cid}: missing required assertion results: {', '.join(missing)}")
                continue
            statuses = [actual_by_id[aid]["status"] for aid in required_ids]
        else:
            statuses = [a.get("status") for a in actuals]

        if "FAIL" in statuses:
            expected_case_status = "FAIL"
        elif "BLOCKED" in statuses:
            expected_case_status = "BLOCKED"
        elif "NOT_EXECUTED" in statuses or not statuses:
            expected_case_status = "NOT_EXECUTED"
        else:
            expected_case_status = "PASS"

        if result.get("status") != expected_case_status:
            semantic.append(f"{cid}: expected case status {expected_case_status}, got {result.get('status')}")

    if errors or semantic:
        for err in errors:
            path = ".".join(str(x) for x in err.absolute_path) or "<root>"
            print(f"SCHEMA {path}: {err.message}", file=sys.stderr)
        for message in semantic:
            print(f"SEMANTIC: {message}", file=sys.stderr)
        return 1

    print(f"OK: {args.report} ({len(results)} results)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
