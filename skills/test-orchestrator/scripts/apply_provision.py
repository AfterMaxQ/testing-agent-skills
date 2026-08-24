#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from jsonschema import Draft202012Validator

from validate_context import semantic_errors

SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = SKILL_DIR / "context.schema.json"


def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def apply_verified(context: dict, provisioner_ids: list[str]) -> dict:
    provisioners = {item["id"]: item for item in context.get("provisioners", [])}
    unknown = [pid for pid in provisioner_ids if pid not in provisioners]
    if unknown:
        raise ValueError("unknown provisioner ids: " + ", ".join(unknown))

    runtime = json.loads(json.dumps(context))
    available = runtime["available"]
    for pid in provisioner_ids:
        for item in provisioners[pid]["provides"]:
            values = available[item["category"]]
            if item["name"] not in values:
                values.append(item["name"])
    return runtime


def main() -> int:
    parser = argparse.ArgumentParser(
        description="将已验证成功的 Provisioner provides 合并到本次 Runtime Context"
    )
    parser.add_argument("context")
    parser.add_argument("--verified", action="append", required=True, dest="verified_ids")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    try:
        context = load(pathlib.Path(args.context))
        schema = load(SCHEMA)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    errors = sorted(
        Draft202012Validator(schema).iter_errors(context),
        key=lambda error: list(error.absolute_path),
    )
    messages = [
        f"SCHEMA {'.'.join(str(item) for item in error.absolute_path) or '<root>'}: {error.message}"
        for error in errors
    ]
    if not errors:
        messages += [f"SEMANTIC: {message}" for message in semantic_errors(context)]
    if messages:
        for message in messages:
            print(message, file=sys.stderr)
        return 1

    try:
        runtime = apply_verified(context, args.verified_ids)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    output_errors = sorted(
        Draft202012Validator(schema).iter_errors(runtime),
        key=lambda error: list(error.absolute_path),
    )
    if output_errors:
        for error in output_errors:
            path = ".".join(str(item) for item in error.absolute_path) or "<root>"
            print(f"SCHEMA {path}: {error.message}", file=sys.stderr)
        return 1

    out = pathlib.Path(args.out)
    out.write_text(json.dumps(runtime, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {out} (verified={','.join(args.verified_ids)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
