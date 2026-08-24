#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import sys

from jsonschema import Draft202012Validator

SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = SKILL_DIR / "context.schema.json"

VALID_ITEM_NAMES = {
    "capabilities": {"browser", "api", "log_trace", "static_inspection"},
    "observability": {
        "browser_dom", "browser_url", "browser_network", "api_response", "sse",
        "log", "trace", "file", "source_code", "screenshot", "human",
    },
}


def semantic_errors(data: dict) -> list[str]:
    semantic: list[str] = []
    ids: set[str] = set()

    for provisioner in data.get("provisioners", []):
        pid = provisioner.get("id")
        if pid in ids:
            semantic.append(f"duplicate provisioner id: {pid}")
        if isinstance(pid, str):
            ids.add(pid)

        provided: set[tuple[str, str]] = set()
        for item in provisioner.get("provides", []):
            category = item.get("category")
            name = item.get("name")
            key = (category, name)
            if key in provided:
                semantic.append(f"{pid}: duplicate provided item: {category}:{name}")
            provided.add(key)

            valid_names = VALID_ITEM_NAMES.get(category)
            if valid_names is not None and name not in valid_names:
                semantic.append(f"{pid}: invalid provided item: {category}:{name}")

    return semantic


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
    semantic = [] if errors else semantic_errors(data)
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
