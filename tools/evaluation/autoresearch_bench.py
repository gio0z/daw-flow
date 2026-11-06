#!/usr/bin/env python3
"""Deterministic regression harness for autoresearch.

Executes full test discovery across tests/test_*.py programmatically and runs
real public CLI smoke commands against validate, route, and wizard_oracle.
Prints standard METRIC key=value pairs for regression conformance tracking.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_unit_tests() -> tuple[int, int]:
    """Discover and execute unit tests programmatically, streaming logs to stderr."""
    tests_dir = REPO_ROOT / "tests"
    loader = unittest.defaultTestLoader
    suite = loader.discover(str(tests_dir), pattern="test_*.py")
    runner = unittest.TextTestRunner(stream=sys.stderr, verbosity=2)
    result = runner.run(suite)
    
    total = result.testsRun
    failures = (
        len(result.failures) + len(result.errors) + len(result.skipped)
        + len(result.expectedFailures) + len(result.unexpectedSuccesses)
    )
    passed = total - failures
    return total, passed


def run_cli_smoke_checks() -> tuple[int, int]:
    """Execute public CLI smoke checks using disposable temporary directories."""
    total = 0
    passed = 0

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # 1. validate package
        total += 1
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "validate.py"), "package", "--root", str(REPO_ROOT), "--format", "json"],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            try:
                data = json.loads(proc.stdout)
                if data.get("valid") is True and data.get("check") == "package":
                    passed += 1
                else:
                    sys.stderr.write(f"Smoke check validate package payload invalid: {proc.stdout}\n")
            except Exception as exc:
                sys.stderr.write(f"Smoke check validate package json parse error: {exc}\n")
        else:
            sys.stderr.write(f"Smoke check validate package failed with exit {proc.returncode}: {proc.stderr}\n")

        # 2. route --check-suite
        total += 1
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "route.py"), "--check-suite", "--root", str(REPO_ROOT), "--format", "json"],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            try:
                data = json.loads(proc.stdout)
                if data.get("status") == "ready":
                    passed += 1
                else:
                    sys.stderr.write(f"Smoke check route --check-suite status not ready: {proc.stdout}\n")
            except Exception as exc:
                sys.stderr.write(f"Smoke check route --check-suite json parse error: {exc}\n")
        else:
            sys.stderr.write(f"Smoke check route --check-suite failed with exit {proc.returncode}: {proc.stderr}\n")

        # 3. setup/blank workspace route
        total += 1
        req_file = tmp_path / "setup_request.json"
        req_data = {
            "schema_version": 1,
            "intent": "setup",
            "requirements": "clear",
            "risk": "low",
            "workspace": "in-place",
        }
        req_file.write_text(json.dumps(req_data), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "route.py"), str(req_file), "--root", str(REPO_ROOT), "--format", "json"],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            try:
                data = json.loads(proc.stdout)
                if data.get("status") == "ready" and data.get("stages") == ["daw-setup"]:
                    passed += 1
                else:
                    sys.stderr.write(f"Smoke check route setup invalid payload: {proc.stdout}\n")
            except Exception as exc:
                sys.stderr.write(f"Smoke check route setup json parse error: {exc}\n")
        else:
            sys.stderr.write(f"Smoke check route setup failed with exit {proc.returncode}: {proc.stderr}\n")

        # 4. wizard oracle request
        total += 1
        scenario_file = REPO_ROOT / "tests" / "fixtures" / "wizard-bench" / "bookmark-manager" / "scenario.json"

        questions_file = tmp_path / "questions.md"
        questions_file.write_text("1. What is the entrypoint bookmarks.py file?\n", encoding="utf-8")

        proc = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "tools" / "evaluation" / "wizard_oracle.py"),
                "--scenario",
                str(scenario_file),
                "--questions",
                str(questions_file),
            ],
            capture_output=True,
            text=True,
        )
        expected_answer = json.loads(scenario_file.read_text(encoding="utf-8"))["hidden_requirements"][0]["answer"]
        if proc.returncode == 0 and proc.stdout.strip() == expected_answer:
            passed += 1
        else:
            sys.stderr.write(f"Smoke check wizard oracle failed with exit {proc.returncode}: {proc.stderr}\n")

    return total, passed


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if "-h" in args or "--help" in args:
        print("usage: autoresearch_bench.py [-h]\n\nDeterministic regression harness for autoresearch.")
        return 0
    unit_total, unit_passed = run_unit_tests()
    smoke_total, smoke_passed = run_cli_smoke_checks()

    total_checks = unit_total + smoke_total
    passed_checks = unit_passed + smoke_passed
    failure_count = total_checks - passed_checks

    pass_rate = round(passed_checks / total_checks, 4) if total_checks > 0 else 0.0

    print(f"METRIC regression_pass_rate={pass_rate}")
    print(f"METRIC check_count={total_checks}")
    print(f"METRIC failure_count={failure_count}")

    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
