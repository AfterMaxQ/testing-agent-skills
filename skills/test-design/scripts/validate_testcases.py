#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import sys

from jsonschema import Draft202012Validator

SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = SKILL_DIR / "schema.json"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_testcases.py <test-cases.json>", file=sys.stderr)
        return 2

    target = pathlib.Path(sys.argv[1])
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.absolute_path))
    semantic: list[str] = []
    case_ids: set[str] = set()

    for case in data.get("cases", []):
        cid = case.get("id")
        if cid in case_ids:
            semantic.append(f"duplicate case id: {cid}")
        case_ids.add(cid)

        assertion_ids: set[str] = set()
        for assertion in case.get("assertions", []):
            aid = assertion.get("id")
            if aid in assertion_ids:
                semantic.append(f"{cid}: duplicate assertion id: {aid}")
            assertion_ids.add(aid)
            if assertion.get("required") and assertion.get("observe_via") == ["screenshot"]:
                semantic.append(f"{cid}/{aid}: required assertion cannot rely on screenshot alone")

        if case.get("design_status") == "NEEDS_CLARIFICATION" and not case.get("ambiguity_note"):
            semantic.append(f"{cid}: NEEDS_CLARIFICATION requires ambiguity_note")

        required_capabilities = set(case.get("execution_requirements", {}).get("capabilities", []))
        channels = set(case.get("execution_channels", []))
        missing_caps = sorted(channels - required_capabilities)
        if missing_caps:
            semantic.append(f"{cid}: execution_requirements.capabilities missing channels: {', '.join(missing_caps)}")

    if errors or semantic:
        for err in errors:
            path = ".".join(str(x) for x in err.absolute_path) or "<root>"
            print(f"SCHEMA {path}: {err.message}", file=sys.stderr)
        for message in semantic:
            print(f"SEMANTIC: {message}", file=sys.stderr)
        return 1

    print(f"OK: {target} ({len(data['cases'])} cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
