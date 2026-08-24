#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import sys

from jsonschema import Draft202012Validator

SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
SUITE_SCHEMA = SKILL_DIR.parent / "test-design" / "schema.json"
CONTEXT_SCHEMA = SKILL_DIR / "context.schema.json"
READINESS_SCHEMA = SKILL_DIR / "readiness.schema.json"
CATEGORIES = ("capabilities", "auth_roles", "test_data", "observability", "fault_injection", "permissions", "env_vars")

TEST_DESIGN_SCRIPTS = SKILL_DIR.parent / "test-design" / "scripts"
if str(TEST_DESIGN_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(TEST_DESIGN_SCRIPTS))

from validate_context import semantic_errors as context_semantic_errors  # noqa: E402
from validate_testcases import semantic_errors as suite_semantic_errors  # noqa: E402


def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate(data, schema, label: str) -> list[str]:
    return [f"{label} {'.'.join(str(x) for x in e.absolute_path) or '<root>'}: {e.message}"
            for e in sorted(Draft202012Validator(schema).iter_errors(data), key=lambda x: list(x.absolute_path))]


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 Test Suite 在当前测试环境中的执行就绪状态")
    parser.add_argument("suite")
    parser.add_argument("context")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    try:
        suite = load(pathlib.Path(args.suite))
        context = load(pathlib.Path(args.context))
        suite_schema = load(SUITE_SCHEMA)
        context_schema = load(CONTEXT_SCHEMA)
        readiness_schema = load(READINESS_SCHEMA)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    suite_errors = validate(suite, suite_schema, "SUITE")
    context_errors = validate(context, context_schema, "CONTEXT")
    input_errors = suite_errors + context_errors
    if not suite_errors:
        input_errors += [f"SUITE semantic: {message}" for message in suite_semantic_errors(suite)]
    if not context_errors:
        input_errors += [f"CONTEXT semantic: {message}" for message in context_semantic_errors(context)]
    if input_errors:
        for err in input_errors:
            print(err, file=sys.stderr)
        return 1

    available = {k: set(context["available"].get(k, [])) for k in CATEGORIES}
    runtime_env = {name for name, value in os.environ.items() if value and value.strip()}
    # Environment variables may be declared in context or be present in the actual runtime.
    available["env_vars"] |= runtime_env

    providers_by_item: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    for p in context.get("provisioners", []):
        for item in p.get("provides", []):
            providers_by_item[(item["category"], item["name"])].append(p)

    runtime_secrets = {
        item["name"]: item for item in context.get("runtime_secrets", [])
    }

    def unresolved_provisioner_secrets(provisioner: dict) -> list[str]:
        unresolved = []
        for secret in provisioner.get("secret_requirements", []):
            if not secret.get("required", False):
                continue
            metadata = runtime_secrets.get(secret["name"])
            env_key = metadata.get("env_key") if metadata else None
            if not metadata or metadata.get("status") != "resolved" or not env_key:
                unresolved.append(secret["name"])
                continue
            if not os.environ.get(env_key, "").strip():
                unresolved.append(secret["name"])
        return unresolved

    case_rows = []
    gap_aggregate: dict[tuple[str, str, str], dict] = {}

    for case in suite["cases"]:
        cid = case["id"]
        gaps = []
        notes = []

        if case["design_status"] == "NEEDS_CLARIFICATION":
            reason = case.get("ambiguity_note") or "需求存在待澄清项"
            gaps.append({
                "category": "requirement_clarification", "name": cid,
                "resolution": "CLARIFY", "provisioner_ids": [], "reason": reason,
            })
            status = "NEEDS_CLARIFICATION"
        else:
            reqs = case["execution_requirements"]
            for secret in reqs.get("secret_requirements", []):
                name = secret["name"]
                metadata = runtime_secrets.get(name)
                env_key = metadata.get("env_key") if metadata else None
                injected = bool(env_key and os.environ.get(env_key, "").strip())
                resolved = bool(metadata and metadata.get("status") == "resolved" and injected)
                if resolved:
                    continue

                if not secret.get("required", False):
                    if metadata:
                        notes.append(
                            f"可选 Secret {name} 未在当前子进程解析："
                            f"{metadata.get('status', 'missing')}"
                        )
                    else:
                        notes.append(f"可选 Secret {name} 未提供 Runtime Context 元数据")
                    continue

                if metadata and metadata.get("status") == "resolved" and not injected:
                    reason = f"Secret 已标记 resolved，但环境变量 {env_key} 未注入当前子进程"
                elif metadata:
                    reason = metadata.get("reason") or f"Secret 当前状态为 {metadata.get('status', 'missing')}"
                else:
                    reason = "未找到 Runtime Context 中的 Secret 解析元数据"
                gaps.append({
                    "category": "secret_requirements", "name": name,
                    "resolution": "BLOCKED", "provisioner_ids": [], "reason": reason,
                })

            for category in CATEGORIES:
                for name in reqs.get(category, []):
                    if name in available[category]:
                        continue
                    candidates = providers_by_item.get((category, name), [])
                    auto = []
                    manual = []
                    unavailable_env = []
                    unavailable_secret = []
                    for p in candidates:
                        missing_env = [e for e in p.get("requires_env", []) if e not in runtime_env]
                        if p["kind"] == "manual":
                            manual.append(p)
                        elif missing_env:
                            unavailable_env.append((p, missing_env))
                        elif (missing_secret := unresolved_provisioner_secrets(p)):
                            unavailable_secret.append((p, missing_secret))
                        else:
                            auto.append(p)
                    if auto:
                        gaps.append({
                            "category": category, "name": name, "resolution": "PROVISIONABLE",
                            "provisioner_ids": [p["id"] for p in auto],
                            "reason": "当前未就绪，但存在可自动执行的 provisioner",
                        })
                    else:
                        ids = [p["id"] for p in candidates]
                        if manual:
                            reason = "需要人工完成环境准备：" + "；".join(p["action"] for p in manual)
                        elif unavailable_env:
                            names = sorted({e for _, envs in unavailable_env for e in envs})
                            reason = "存在 provisioner，但缺少其运行所需环境变量：" + ", ".join(names)
                        elif unavailable_secret:
                            names = sorted({name for _, secrets in unavailable_secret for name in secrets})
                            reason = "存在 provisioner，但缺少其必需 Secret：" + ", ".join(names)
                        else:
                            reason = "当前环境未提供该条件，且没有可用 provisioner"
                        gaps.append({
                            "category": category, "name": name, "resolution": "BLOCKED",
                            "provisioner_ids": ids, "reason": reason,
                        })

            resolutions = {g["resolution"] for g in gaps}
            if "BLOCKED" in resolutions:
                status = "BLOCKED"
            elif "PROVISIONABLE" in resolutions:
                status = "PROVISIONABLE"
            else:
                status = "READY"

        case_rows.append({"case_id": cid, "status": status, "gaps": gaps, "notes": notes})

        for gap in gaps:
            key = (gap["category"], gap["name"], gap["resolution"])
            row = gap_aggregate.setdefault(key, {
                "category": gap["category"], "name": gap["name"], "resolution": gap["resolution"],
                "affected_case_ids": [], "provisioner_ids": [], "reason": gap["reason"],
            })
            row["affected_case_ids"].append(cid)
            row["provisioner_ids"] = sorted(set(row["provisioner_ids"]) | set(gap["provisioner_ids"]))

    counts = collections.Counter(r["status"] for r in case_rows)
    readiness = {
        "schema_version": "1.0",
        "suite_id": suite["suite_id"],
        "context_id": context["context_id"],
        "summary": {
            "total": len(case_rows),
            "ready": counts["READY"],
            "provisionable": counts["PROVISIONABLE"],
            "blocked": counts["BLOCKED"],
            "needs_clarification": counts["NEEDS_CLARIFICATION"],
        },
        "case_readiness": case_rows,
        "aggregated_gaps": list(gap_aggregate.values()),
    }

    output_errors = validate(readiness, readiness_schema, "READINESS")
    if output_errors:
        for err in output_errors:
            print(err, file=sys.stderr)
        return 1

    out = pathlib.Path(args.out)
    out.write_text(json.dumps(readiness, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {out} (ready={counts['READY']}, provisionable={counts['PROVISIONABLE']}, blocked={counts['BLOCKED']}, clarification={counts['NEEDS_CLARIFICATION']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
