#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import sys

from jsonschema import Draft202012Validator

SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = SKILL_DIR / "context.schema.json"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_context.py <test-context.json>", file=sys.stderr)
        return 2
    path = pathlib.Path(sys.argv[1])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.absolute_path))
    semantic: list[str] = []
    ids: set[str] = set()
    provided: set[tuple[str, str]] = set()
    for p in data.get("provisioners", []):
        pid = p.get("id")
        if pid in ids:
            semantic.append(f"duplicate provisioner id: {pid}")
        ids.add(pid)
        for item in p.get("provides", []):
            key = (item.get("category"), item.get("name"))
            if key in provided:
                # Multiple provisioners are valid, so do not reject; just keep structure simple.
                pass
            provided.add(key)
    if errors or semantic:
        for err in errors:
            p = ".".join(str(x) for x in err.absolute_path) or "<root>"
            print(f"SCHEMA {p}: {err.message}", file=sys.stderr)
        for msg in semantic:
            print(f"SEMANTIC: {msg}", file=sys.stderr)
        return 1
    print(f"OK: {path} ({len(data.get('provisioners', []))} provisioners)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
