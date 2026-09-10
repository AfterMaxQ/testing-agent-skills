from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "update_progress.py"


class UpdateProgressTests(unittest.TestCase):
    def run_cli(self, *args: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(expect, result.returncode, msg=result.stderr or result.stdout)
        return result

    def read(self, path: pathlib.Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def test_full_progress_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            progress = pathlib.Path(tmp) / "execution-progress.json"

            self.run_cli(
                str(progress),
                "init",
                "--suite-id", "suite-1",
                "--context-id", "ctx-1",
                "--total", "2",
            )
            data = self.read(progress)
            self.assertEqual("1.0", data["schema_version"])
            self.assertEqual("RUNNING", data["status"])
            self.assertIsNone(data["current_case"])
            self.assertEqual(
                {
                    "total": 2,
                    "completed": 0,
                    "passed": 0,
                    "failed": 0,
                    "blocked": 0,
                    "not_executed": 0,
                },
                data["progress"],
            )

            self.run_cli(str(progress), "start-case", "--case", "CASE-1")
            self.assertEqual("CASE-1", self.read(progress)["current_case"])

            self.run_cli(
                str(progress),
                "finish-case",
                "--case", "CASE-1",
                "--status", "PASS",
                "--evidence", "evidence/case-1.png",
            )
            data = self.read(progress)
            self.assertIsNone(data["current_case"])
            self.assertEqual(1, data["progress"]["completed"])
            self.assertEqual(1, data["progress"]["passed"])
            self.assertEqual(
                ["evidence/case-1.png"],
                data["completed_cases"][0]["evidence"],
            )

            self.run_cli(str(progress), "start-case", "--case", "CASE-2")
            self.run_cli(
                str(progress),
                "finish-case",
                "--case", "CASE-2",
                "--status", "FAIL",
                "--failure-description", "observed mismatch",
            )
            data = self.read(progress)
            self.assertEqual(2, data["progress"]["completed"])
            self.assertEqual(1, data["progress"]["failed"])
            self.assertEqual("observed mismatch", data["completed_cases"][1]["failure_description"])

            self.run_cli(str(progress), "complete")
            data = self.read(progress)
            self.assertEqual("COMPLETED", data["status"])
            self.assertIn("completed_at", data)

    def test_complete_rejects_incomplete_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            progress = pathlib.Path(tmp) / "execution-progress.json"
            self.run_cli(
                str(progress),
                "init",
                "--suite-id", "suite-1",
                "--context-id", "ctx-1",
                "--total", "1",
            )
            result = self.run_cli(str(progress), "complete", expect=2)
            self.assertIn("cannot complete", result.stderr.lower())
            self.assertEqual("RUNNING", self.read(progress)["status"])

    def test_finish_requires_matching_current_case(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            progress = pathlib.Path(tmp) / "execution-progress.json"
            self.run_cli(
                str(progress),
                "init",
                "--suite-id", "suite-1",
                "--context-id", "ctx-1",
                "--total", "1",
            )
            self.run_cli(str(progress), "start-case", "--case", "CASE-1")
            result = self.run_cli(
                str(progress),
                "finish-case",
                "--case", "CASE-2",
                "--status", "PASS",
                expect=2,
            )
            self.assertIn("current case", result.stderr.lower())
            self.assertEqual("CASE-1", self.read(progress)["current_case"])


if __name__ == "__main__":
    unittest.main()
