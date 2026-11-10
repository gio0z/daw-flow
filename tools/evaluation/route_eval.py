#!/usr/bin/env python3
"""Route Eval Harness — enterprise-grade routing validation for DAW.

Reads a JSON fixture file containing routing scenarios and asserts that
`scripts/route.py` resolves each one to the expected status, stages, and
constraints. Zero third-party dependencies; stdlib only. Read-only: it never
mutates the suite, only reads the manifest and invokes the route engine.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import tempfile
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Maps route.py response status to the exit code it must terminate with.
STATUS_EXIT_CODES = {"ready": 0, "needs-input": 1, "blocked": 1, "error": 2}

FIXTURE_SCHEMA = {
    "schema_version": 1,
    "scenarios": [
        {
            "name": "str",
            "request": {
                "schema_version": 1,
                "intent": "str",
                "requirements": "str",
                "risk": "str",
                "workspace": "str",
            },
            "expected": {
                "status": "ready|needs-input|blocked|error",
                "exit_code": "int (0=ready, 1=needs-input/blocked, 2=error)",
                "stages": ["list", "of", "stage", "names"],
                "read_only": bool,
                "documentation_only": bool,
                "interactive_approval_required": bool,
                "authorization_granted": bool,
                "contains_reason": "optional substring",
                "contains_blocker_code": "optional code",
            },
        }
    ],
}


def run_route(request: dict, root: pathlib.Path) -> tuple[int, Any]:
    """Invoke <root>/scripts/route.py with a JSON request file.

    Returns (process exit code, parsed JSON envelope). The root selects the
    suite under test; it is passed through to route.py via --root so a stale
    or wrong suite cannot be validated by accident.
    """
    script = root / "scripts" / "route.py"
    if not script.is_file():
        raise RuntimeError(f"route.py not found under suite root: {script}")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
        json.dump(request, tf)
        path = pathlib.Path(tf.name)
    try:
        result = subprocess.run(
            [sys.executable, str(script), str(path), "--format", "json", "--root", str(root)],
            capture_output=True,
            text=True,
            timeout=30,
        )
    finally:
        path.unlink(missing_ok=True)
    if result.returncode not in (0, 1, 2):
        raise RuntimeError(
            f"route.py exited {result.returncode}: {result.stderr.strip()}"
        )
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"route.py emitted unparseable JSON (exit {result.returncode}): {exc}"
        ) from exc
    return result.returncode, output


def load_fixture(path: pathlib.Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("Fixture schema_version must be 1.")
    if "scenarios" not in data or not isinstance(data["scenarios"], list):
        raise ValueError('Fixture must contain "scenarios" list.')
    return data


def check_scenario(scenario: dict, root: pathlib.Path) -> list[str]:
    """Return list of failure messages for one scenario."""
    failures: list[str] = []
    name = scenario.get("name", "<unnamed>")
    request = scenario.get("request", {})
    expected = scenario.get("expected", {})

    try:
        exit_code, result = run_route(request, root)
    except Exception as exc:  # noqa: BLE001
        return [f"{name}: route invocation failed: {exc}"]

    if not isinstance(result, dict):
        return [f"{name}: route.py emitted a non-object JSON envelope"]

    # Exit-code check: an explicit expectation wins; otherwise derive the
    # expected exit code from the status.
    expected_exit = expected.get("exit_code")
    if expected_exit is None and expected.get("status") in STATUS_EXIT_CODES:
        expected_exit = STATUS_EXIT_CODES[expected["status"]]
    if expected_exit is not None and exit_code != expected_exit:
        failures.append(
            f"{name}: expected exit code {expected_exit}, got {exit_code}"
        )

    # Status check.
    exp_status = expected.get("status")
    if exp_status and result.get("status") != exp_status:
        failures.append(
            f"{name}: expected status '{exp_status}', got '{result.get('status')}'"
        )

    # Stages check (exact match when provided).
    exp_stages = expected.get("stages")
    if exp_stages is not None:
        got_stages = result.get("stages", [])
        if got_stages != exp_stages:
            failures.append(
                f"{name}: expected stages {exp_stages}, got {got_stages}"
            )

    # Constraint checks.
    constraints = result.get("constraints", {})
    for key, exp_val in (
        ("read_only", expected.get("read_only")),
        ("documentation_only", expected.get("documentation_only")),
        ("interactive_approval_required", expected.get("interactive_approval_required")),
        ("authorization_granted", expected.get("authorization_granted")),
    ):
        if exp_val is not None and constraints.get(key) != exp_val:
            failures.append(
                f"{name}: expected constraint {key}={exp_val}, "
                f"got {constraints.get(key)}"
            )

    # Substring presence checks on reasons.
    contains_reason = expected.get("contains_reason")
    if contains_reason:
        reasons = " ".join(result.get("reasons", []))
        if contains_reason not in reasons:
            failures.append(
                f"{name}: expected reason containing '{contains_reason}' not found"
            )

    # Blocker code presence check.
    contains_blocker = expected.get("contains_blocker_code")
    if contains_blocker:
        codes = [b.get("code", "") for b in result.get("blockers", [])]
        if contains_blocker not in codes:
            failures.append(
                f"{name}: expected blocker code '{contains_blocker}' not found in {codes}"
            )

    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="DAW Route Eval Harness — validate routing scenarios."
    )
    parser.add_argument("fixture", help="Path to JSON fixture file.")
    parser.add_argument(
        "--root",
        help="Explicit suite root directory.",
    )
    args = parser.parse_args(argv)

    root = pathlib.Path(args.root).resolve() if args.root else REPO_ROOT
    fixture_path = pathlib.Path(args.fixture)
    if not fixture_path.is_file():
        print(f"Fixture not found: {fixture_path}", file=sys.stderr)
        return 2

    try:
        fixture = load_fixture(fixture_path)
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as exc:
        print(f"Fixture load error: {exc}", file=sys.stderr)
        return 2

    scenarios = fixture["scenarios"]
    total = len(scenarios)
    failures: list[str] = []

    for scenario in scenarios:
        failures.extend(check_scenario(scenario, root))

    print(f"Route Eval: {total} scenario(s), {len(failures)} failure(s).")
    for f in failures:
        print(f"  - {f}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
