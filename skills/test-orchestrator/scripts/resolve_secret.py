#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import getpass
import json
import os
import pathlib
import re
import stat
import subprocess
import sys
from datetime import datetime, timezone

from jsonschema import Draft202012Validator, SchemaError

SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
SECRET_SCHEMA = SKILL_DIR / "secret.schema.json"
SUITE_SCHEMA = SKILL_DIR.parent / "test-design" / "schema.json"
CONTEXT_SCHEMA = SKILL_DIR / "context.schema.json"
DEFAULT_CONFIG = pathlib.Path(".testing-agent/config.json")
DEFAULT_LOCAL_STORE = pathlib.Path(".testing-agent/secrets.env")
DEFAULT_RUNTIME_STORE = pathlib.Path(".testing-agent/runtime/secrets.env")
ENV_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

PROVIDER_ORDER = (
    "runtime",
    "local",
    "environment",
    "vault",
    "aws_secrets_manager",
    "github_actions",
    "kubernetes",
    "manual",
)
EXTERNAL_PROVIDERS = {
    "vault": "Vault",
    "aws_secrets_manager": "AWS Secrets Manager",
    "github_actions": "GitHub Actions Secret",
    "kubernetes": "Kubernetes Secret",
}
SOURCE_LABELS = {
    "runtime": "runtime_secret_store",
    "local": "local_secret_store",
    "environment": "environment",
    "manual": "manual",
}

SECRET_DECLARATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["schema_version", "secrets"],
    "properties": {
        "schema_version": {"const": "1.0"},
        "secrets": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "name", "env_key", "type", "sensitivity", "providers", "persist_policy"
                ],
                "properties": {
                    "name": {"type": "string", "pattern": "^[a-z][a-z0-9_.-]*$"},
                    "env_key": {"type": "string", "pattern": "^[A-Za-z_][A-Za-z0-9_]*$"},
                    "type": {"enum": ["credential", "token", "key"]},
                    "sensitivity": {"const": "secret"},
                    "providers": {
                        "type": "array",
                        "minItems": 1,
                        "uniqueItems": True,
                        "items": {"enum": [
                            "runtime", "local", "environment", "vault",
                            "aws_secrets_manager", "github_actions", "kubernetes", "manual"
                        ]},
                    },
                    "persist_policy": {"enum": ["never", "allowed", "session"]},
                    "expires": {"type": ["string", "null"]},
                },
            },
        },
    },
}


class ResolutionError(Exception):
    pass


def load_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def schema_errors(data: dict, schema: dict) -> list[str]:
    return [
        f"{'.'.join(str(item) for item in error.absolute_path) or '<root>'}: {error.message}"
        for error in sorted(
            Draft202012Validator(schema).iter_errors(data),
            key=lambda item: list(item.absolute_path),
        )
    ]


def parse_env_file(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    if not path.is_file():
        raise ResolutionError(f"Secret store is not a file: {path}")

    if os.name != "nt":
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode & 0o077:
            os.chmod(path, 0o600)

    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ResolutionError(f"Invalid Secret store line {path}:{line_number}")
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not ENV_KEY_PATTERN.fullmatch(key):
            raise ResolutionError(f"Invalid environment variable name {key!r} at {path}:{line_number}")
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            try:
                value = ast.literal_eval(value)
            except (SyntaxError, ValueError) as exc:
                raise ResolutionError(f"Invalid quoted value at {path}:{line_number}") from exc
        values[key] = str(value)
    return values


def load_config(path: pathlib.Path) -> dict:
    if not path.exists():
        return {}
    config = load_json(path)
    if not isinstance(config, dict):
        raise ResolutionError(f"Secret config must be an object: {path}")
    return config


def validate_secret_declarations(data: dict) -> list[str]:
    try:
        Draft202012Validator.check_schema(SECRET_DECLARATION_SCHEMA)
    except SchemaError as exc:
        raise ResolutionError(f"invalid Secret declaration contract: {exc.message}") from exc
    errors = schema_errors(data, SECRET_DECLARATION_SCHEMA)
    if errors:
        return errors
    names: set[str] = set()
    env_keys: set[str] = set()
    for item in data["secrets"]:
        if item["name"] in names:
            errors.append(f"secrets: duplicate name: {item['name']}")
        if item["env_key"] in env_keys:
            errors.append(f"secrets: duplicate env_key: {item['env_key']}")
        names.add(item["name"])
        env_keys.add(item["env_key"])
    return errors


def non_empty(value: str | None) -> bool:
    return value is not None and bool(value.strip())


def expired(value: str | None, now: datetime) -> bool:
    if not value:
        return False
    try:
        expiry = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    return expiry <= now


def collect_requirements(suite: dict | None, context: dict | None) -> dict[str, dict]:
    requirements: dict[str, dict] = {}
    if suite:
        for case in suite.get("cases", []):
            for item in case.get("execution_requirements", {}).get("secret_requirements", []):
                name = item["name"]
                current = requirements.setdefault(name, {"required": False, "persist": False})
                current["required"] = current["required"] or item["required"]
                current["persist"] = current["persist"] or item["persist"]
    if context:
        for provisioner in context.get("provisioners", []):
            for item in provisioner.get("secret_requirements", []):
                name = item["name"]
                current = requirements.setdefault(name, {"required": False, "persist": False})
                current["required"] = current["required"] or item["required"]
                current["persist"] = current["persist"] or item["persist"]
    return requirements


def resolve_one(
    definition: dict,
    requirement: dict,
    stores: dict[str, dict[str, str]],
    allow_manual: bool,
) -> tuple[str, str | None, str | None]:
    allowed = set(definition["providers"])
    unavailable: list[str] = []
    for provider in PROVIDER_ORDER:
        if provider not in allowed:
            continue
        if provider in stores:
            value = stores[provider].get(definition["env_key"])
            if non_empty(value):
                return SOURCE_LABELS[provider], value, None
        elif provider in EXTERNAL_PROVIDERS:
            unavailable.append(EXTERNAL_PROVIDERS[provider])
        elif provider == "manual":
            if not allow_manual:
                return "manual", None, "manual input is disabled; rerun with --allow-manual"
            value = getpass.getpass(f"Secret required ({definition['name']}): ")
            if non_empty(value):
                return "manual", value, None
            return "manual", None, "manual input was empty"

    if unavailable:
        return "none", None, "unavailable providers: " + ", ".join(unavailable)
    return "none", None, "no configured provider returned a non-empty value"


def resolve(
    definitions: dict[str, dict],
    requirements: dict[str, dict],
    stores: dict[str, dict[str, str]],
    allow_manual: bool,
) -> tuple[list[dict], dict[str, str]]:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    now_dt = datetime.fromisoformat(now.replace("Z", "+00:00"))
    metadata: list[dict] = []
    resolved_values: dict[str, str] = {}
    for name, requirement in sorted(requirements.items()):
        definition = definitions.get(name)
        if definition is None:
            raise ResolutionError(f"Secret Schema 中没有该名称: {name}")
        if expired(definition.get("expires"), now_dt):
            metadata.append({
                "name": name,
                "env_key": definition["env_key"],
                "source": "none",
                "status": "expired",
                "persist_policy": definition["persist_policy"] if requirement["persist"] else "session",
                "resolved_at": None,
                "expires": definition.get("expires"),
                "reason": "Secret 已过期",
            })
            continue
        source, value, reason = resolve_one(definition, requirement, stores, allow_manual)
        status = "resolved" if value is not None else ("manual_required" if source == "manual" else "unavailable" if reason and "unavailable providers" in reason else "missing")
        persist_policy = definition["persist_policy"] if requirement["persist"] else "session"
        entry = {
            "name": name,
            "env_key": definition["env_key"],
            "source": source,
            "status": status,
            "persist_policy": persist_policy,
            "resolved_at": now if value is not None else None,
            "expires": definition.get("expires"),
        }
        if reason:
            entry["reason"] = reason
        metadata.append(entry)
        if value is not None:
            resolved_values[definition["env_key"]] = value

    return metadata, resolved_values


def build_output(context: dict | None, metadata: list[dict]) -> dict:
    if context is None:
        return {
            "schema_version": "1.0",
            "runtime_secrets": metadata,
        }
    output = json.loads(json.dumps(context))
    output["schema_version"] = "1.2"
    output["runtime_secrets"] = metadata
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="解析 Secret 并将值只注入子进程环境")
    parser.add_argument("--schema", default=str(SECRET_SCHEMA))
    parser.add_argument("--suite")
    parser.add_argument("--context")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--runtime-env-file", default=None)
    parser.add_argument("--out", required=True)
    parser.add_argument("--allow-manual", action="store_true")
    parser.add_argument("--exec", nargs=argparse.REMAINDER, dest="command")
    args = parser.parse_args()

    try:
        secret_schema = load_json(pathlib.Path(args.schema))
        secret_errors = validate_secret_declarations(secret_schema)
        if secret_errors:
            raise ResolutionError("Secret declaration errors: " + "; ".join(secret_errors))
        suite = load_json(pathlib.Path(args.suite)) if args.suite else None
        context = load_json(pathlib.Path(args.context)) if args.context else None
        if suite:
            suite_schema = load_json(SUITE_SCHEMA)
            suite_errors = schema_errors(suite, suite_schema)
            if suite_errors:
                raise ResolutionError("Test Suite Schema errors: " + "; ".join(suite_errors))
        if context:
            context_schema = load_json(CONTEXT_SCHEMA)
            context_errors = schema_errors(context, context_schema)
            if context_errors:
                raise ResolutionError("Test Context Schema errors: " + "; ".join(context_errors))
        config = load_config(pathlib.Path(args.config))
    except (OSError, json.JSONDecodeError, ResolutionError, SchemaError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    definitions_list = secret_schema.get("secrets", [])
    definitions = {item["name"]: item for item in definitions_list}
    requirements = collect_requirements(suite, context)
    if not requirements:
        requirements = {name: {"required": True, "persist": False} for name in definitions}

    local_path = pathlib.Path(args.env_file or config.get("local_store", DEFAULT_LOCAL_STORE))
    runtime_path = pathlib.Path(args.runtime_env_file or config.get("runtime_store", DEFAULT_RUNTIME_STORE))
    try:
        stores = {
            "runtime": parse_env_file(runtime_path),
            "local": parse_env_file(local_path),
            "environment": {key: value for key, value in os.environ.items()},
        }
        allow_manual = args.allow_manual or bool(config.get("allow_manual", False))
        metadata, resolved_values = resolve(definitions, requirements, stores, allow_manual)
    except (OSError, ResolutionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    output = build_output(context, metadata)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for item in metadata:
        print(f"{item['name']}: {item['status']} ({item['source']})")

    missing_required = [
        item["name"]
        for item in metadata
        if requirements.get(item["name"], {}).get("required") and item["status"] != "resolved"
    ]
    if missing_required:
        for name in missing_required:
            item = next(row for row in metadata if row["name"] == name)
            definition = definitions[name]
            providers = ", ".join(definition["providers"])
            print(
                f"Secret {name} unresolved ({item['status']}); allowed providers: {providers}",
                file=sys.stderr,
            )
            print(
                "Provide a value through the configured local/runtime store or process environment; "
                "use --allow-manual for one-time input.",
                file=sys.stderr,
            )
        print("Missing required secrets: " + ", ".join(missing_required), file=sys.stderr)
        return 1

    command = list(args.command or [])
    if command and command[0] == "--":
        command = command[1:]
    if command:
        child_env = os.environ.copy()
        child_env.update(resolved_values)
        return subprocess.run(command, env=child_env, check=False).returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
