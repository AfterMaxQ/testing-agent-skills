#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import sys

from jsonschema import Draft202012Validator

SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = SKILL_DIR / "schema.json"

EVIDENCE_CHANNELS = {
    "browser_dom": {"browser"},
    "browser_url": {"browser"},
    "browser_network": {"browser"},
    "api_response": {"api"},
    "sse": {"api"},
    "log": {"log_trace"},
    "trace": {"browser", "log_trace"},
    "file": {"static_inspection"},
    "source_code": {"static_inspection"},
    "screenshot": {"browser"},
    "human": {"browser", "api", "log_trace", "static_inspection"},
}


def _strings(value) -> set[str]:
    if isinstance(value, str):
        return {value}
    if isinstance(value, dict):
        found = set(value)
        for child in value.values():
            found |= _strings(child)
        return found
    if isinstance(value, list):
        found: set[str] = set()
        for child in value:
            found |= _strings(child)
        return found
    return set()


def semantic_errors(data: dict) -> list[str]:
    semantic: list[str] = []

    source_ids: set[str] = set()
    for source in data.get("source_documents", []):
        sid = source.get("id")
        if sid in source_ids:
            semantic.append(f"duplicate source document id: {sid}")
        if isinstance(sid, str):
            source_ids.add(sid)

    question_ids: set[str] = set()
    for question in data.get("open_questions", []):
        qid = question.get("id")
        if qid in question_ids:
            semantic.append(f"duplicate open question id: {qid}")
        if isinstance(qid, str):
            question_ids.add(qid)

    case_ids: set[str] = set()
    for case in data.get("cases", []):
        cid = case.get("id")
        if cid in case_ids:
            semantic.append(f"duplicate case id: {cid}")
        if isinstance(cid, str):
            case_ids.add(cid)

        question_refs = case.get("open_question_refs", [])
        unknown_questions = sorted(set(question_refs) - question_ids)
        if unknown_questions:
            semantic.append(f"{cid}: unknown open question refs: {', '.join(unknown_questions)}")

        if case.get("design_status") == "NEEDS_CLARIFICATION":
            if not case.get("ambiguity_note"):
                semantic.append(f"{cid}: NEEDS_CLARIFICATION requires ambiguity_note")
            if not question_refs:
                semantic.append(f"{cid}: NEEDS_CLARIFICATION requires open_question_refs")

        requirements = case.get("execution_requirements", {})
        secret_names: set[str] = set()
        for secret in requirements.get("secret_requirements", []):
            name = secret.get("name")
            if name in secret_names:
                semantic.append(f"{cid}: duplicate secret requirement: {name}")
            if isinstance(name, str):
                secret_names.add(name)

        required_capabilities = set(requirements.get("capabilities", []))
        channels = set(case.get("execution_channels", []))
        missing_caps = sorted(channels - required_capabilities)
        if missing_caps:
            semantic.append(f"{cid}: execution_requirements.capabilities missing channels: {', '.join(missing_caps)}")

        required_observability = set(requirements.get("observability", []))
        assertion_ids: set[str] = set()
        for assertion in case.get("assertions", []):
            aid = assertion.get("id")
            if aid in assertion_ids:
                semantic.append(f"{cid}: duplicate assertion id: {aid}")
            if isinstance(aid, str):
                assertion_ids.add(aid)

            observe_via = set(assertion.get("observe_via", []))
            missing_observability = sorted(observe_via - required_observability)
            if missing_observability:
                semantic.append(
                    f"{cid}/{aid}: execution_requirements.observability missing evidence sources: "
                    + ", ".join(missing_observability)
                )

            for evidence_kind in sorted(observe_via):
                supported = EVIDENCE_CHANNELS.get(evidence_kind, set())
                if supported and not channels.intersection(supported):
                    semantic.append(
                        f"{cid}/{aid}: evidence source {evidence_kind} is not supported by execution_channels"
                    )

            if assertion.get("required") and observe_via and observe_via <= {"screenshot", "human"}:
                semantic.append(f"{cid}/{aid}: required assertion cannot rely on screenshot/human evidence alone")

        declared_data = set(requirements.get("test_data", []))
        described_data = _strings(case.get("test_data", {}))
        missing_data = sorted(declared_data - described_data)
        if missing_data:
            semantic.append(f"{cid}: test_data does not describe required resources: {', '.join(missing_data)}")

    return semantic


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
    semantic = [] if errors else semantic_errors(data)

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
