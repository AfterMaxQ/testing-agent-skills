#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import tempfile
from datetime import datetime, timezone

TERMINAL_STATUSES = ("PASS", "FAIL", "BLOCKED", "NOT_EXECUTED")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_progress(path: pathlib.Path) -> dict:
    if not path.exists():
        raise ValueError(f"progress file does not exist: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read progress file: {path}") from exc


def atomic_write_json(path: pathlib.Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: pathlib.Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = pathlib.Path(handle.name)
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def require_running(data: dict) -> None:
    if data.get("status") != "RUNNING":
        raise ValueError("progress run is not RUNNING")


def recalculate_progress(data: dict) -> None:
    records = data.get("completed_cases", [])
    counts = {status: 0 for status in TERMINAL_STATUSES}
    for record in records:
        status = record.get("status")
        if status in counts:
            counts[status] += 1
    data["progress"].update(
        {
            "completed": len(records),
            "passed": counts["PASS"],
            "failed": counts["FAIL"],
            "blocked": counts["BLOCKED"],
            "not_executed": counts["NOT_EXECUTED"],
        }
    )


def command_init(args: argparse.Namespace) -> None:
    timestamp = now_iso()
    data = {
        "schema_version": "1.0",
        "suite_id": args.suite_id,
        "context_id": args.context_id,
        "status": "RUNNING",
        "started_at": timestamp,
        "updated_at": timestamp,
        "current_case": None,
        "progress": {
            "total": args.total,
            "completed": 0,
            "passed": 0,
            "failed": 0,
            "blocked": 0,
            "not_executed": 0,
        },
        "completed_cases": [],
    }
    atomic_write_json(args.progress_file, data)


def command_start_case(args: argparse.Namespace) -> None:
    data = load_progress(args.progress_file)
    require_running(data)
    if data.get("current_case") is not None:
        raise ValueError(f"current case is already {data['current_case']}")
    if any(record.get("case_id") == args.case for record in data.get("completed_cases", [])):
        raise ValueError(f"case is already completed: {args.case}")
    data["current_case"] = args.case
    data["updated_at"] = now_iso()
    atomic_write_json(args.progress_file, data)


def command_finish_case(args: argparse.Namespace) -> None:
    data = load_progress(args.progress_file)
    require_running(data)
    if data.get("current_case") != args.case:
        raise ValueError(f"current case is {data.get('current_case')!r}, not {args.case!r}")
    if any(record.get("case_id") == args.case for record in data.get("completed_cases", [])):
        raise ValueError(f"case is already completed: {args.case}")

    timestamp = now_iso()
    record = {
        "case_id": args.case,
        "status": args.status,
        "finished_at": timestamp,
        "evidence": list(args.evidence or []),
    }
    if args.failure_description:
        record["failure_description"] = args.failure_description

    data.setdefault("completed_cases", []).append(record)
    data["current_case"] = None
    data["updated_at"] = timestamp
    recalculate_progress(data)
    atomic_write_json(args.progress_file, data)


def command_complete(args: argparse.Namespace) -> None:
    data = load_progress(args.progress_file)
    require_running(data)
    if data.get("current_case") is not None:
        raise ValueError(f"cannot complete while current case is {data['current_case']}")
    progress = data.get("progress", {})
    if progress.get("completed") != progress.get("total"):
        raise ValueError(
            f"cannot complete: {progress.get('completed', 0)} of {progress.get('total', 0)} cases completed"
        )
    timestamp = now_iso()
    data["status"] = "COMPLETED"
    data["completed_at"] = timestamp
    data["updated_at"] = timestamp
    atomic_write_json(args.progress_file, data)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="维护测试执行中的 execution-progress.json")
    parser.add_argument("progress_file", type=pathlib.Path)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="创建一次新的执行进度文件")
    init_parser.add_argument("--suite-id", required=True)
    init_parser.add_argument("--context-id", required=True)
    init_parser.add_argument("--total", type=int, required=True)
    init_parser.set_defaults(handler=command_init)

    start_parser = subparsers.add_parser("start-case", help="记录当前正在执行的 Case")
    start_parser.add_argument("--case", required=True)
    start_parser.set_defaults(handler=command_start_case)

    finish_parser = subparsers.add_parser("finish-case", help="记录一个 Case 的终态和证据路径")
    finish_parser.add_argument("--case", required=True)
    finish_parser.add_argument("--status", choices=TERMINAL_STATUSES, required=True)
    finish_parser.add_argument("--evidence", action="append", default=[])
    finish_parser.add_argument("--failure-description")
    finish_parser.set_defaults(handler=command_finish_case)

    complete_parser = subparsers.add_parser("complete", help="全部 Case 结束后标记执行完成")
    complete_parser.set_defaults(handler=command_complete)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "init" and args.total < 0:
        parser.error("--total must be >= 0")
    try:
        args.handler(args)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
