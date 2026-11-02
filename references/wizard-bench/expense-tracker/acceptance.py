#!/usr/bin/env python3
"""Acceptance test suite for expense-tracker scenario."""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def emit_result(check: str, status: str, detail: str) -> None:
    print(json.dumps({"check": check, "status": status, "detail": detail}))


def run_cli(entrypoint: Path, args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(entrypoint)] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=10,
    )


def main() -> int:
    if len(sys.argv) < 2:
        emit_result("setup", "fail", "Usage: acceptance.py <workspace>")
        return 1

    workspace = Path(sys.argv[1]).resolve()
    entrypoint = workspace / "expenses.py"

    all_checks = [
        "R1_entrypoint_exists",
        "R2_csv_persistence",
        "R3_add_command",
        "R4_validation_exit_code_2",
        "R5_summary_command",
        "R6_list_command_format",
        "R7_missing_file_handling",
    ]

    if not entrypoint.is_file():
        for check in all_checks:
            emit_result(check, "fail", f"Missing required entrypoint: {entrypoint.name}")
        return 1

    failures = 0

    # R7: Missing file handling prior to creation
    try:
        proc_list_empty = run_cli(entrypoint, ["list"], cwd=workspace)
        proc_sum_empty = run_cli(entrypoint, ["summary"], cwd=workspace)
        if (
            proc_list_empty.returncode == 0
            and "No expenses found." in proc_list_empty.stdout
            and proc_sum_empty.returncode == 0
            and "Total: $0.00" in proc_sum_empty.stdout
        ):
            emit_result("R7_missing_file_handling", "pass", "Handled missing expenses.csv cleanly")
        else:
            failures += 1
            emit_result(
                "R7_missing_file_handling",
                "fail",
                f"list output: {proc_list_empty.stdout.strip()!r}, summary: {proc_sum_empty.stdout.strip()!r}",
            )
    except Exception as exc:
        failures += 1
        emit_result("R7_missing_file_handling", "fail", str(exc))

    # R1: Entry point exists
    emit_result("R1_entrypoint_exists", "pass", "expenses.py exists in workspace")

    # R3: Add command basic functionality
    today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        proc_add1 = run_cli(
            entrypoint,
            ["add", "--amount", "15.50", "--category", "Food", "--description", "Lunch"],
            cwd=workspace,
        )
        if proc_add1.returncode == 0 and "Added expense #1" in proc_add1.stdout:
            emit_result("R3_add_command", "pass", "Added expense #1 with default UTC date")
        else:
            failures += 1
            emit_result(
                "R3_add_command",
                "fail",
                f"rc={proc_add1.returncode}, out={proc_add1.stdout.strip()!r}, err={proc_add1.stderr.strip()!r}",
            )
    except Exception as exc:
        failures += 1
        emit_result("R3_add_command", "fail", str(exc))

    # R2: CSV persistence
    csv_file = workspace / "expenses.csv"
    try:
        if csv_file.is_file():
            content = csv_file.read_text(encoding="utf-8").strip().splitlines()
            expected_header = "id,date,amount,category,description"
            if content and content[0] == expected_header:
                emit_result("R2_csv_persistence", "pass", "expenses.csv has correct header and row")
            else:
                failures += 1
                emit_result("R2_csv_persistence", "fail", f"Header was: {content[0] if content else 'empty'}")
        else:
            failures += 1
            emit_result("R2_csv_persistence", "fail", "expenses.csv was not created")
    except Exception as exc:
        failures += 1
        emit_result("R2_csv_persistence", "fail", str(exc))

    # R4: Validation
    try:
        proc_invalid_amt = run_cli(
            entrypoint,
            ["add", "--amount", "-5", "--category", "Food", "--description", "Bad"],
            cwd=workspace,
        )
        proc_invalid_date = run_cli(
            entrypoint,
            ["add", "--amount", "10", "--category", "Food", "--description", "BadDate", "--date", "2024-99-99"],
            cwd=workspace,
        )
        if (
            proc_invalid_amt.returncode == 2
            and "Error:" in proc_invalid_amt.stderr
            and proc_invalid_date.returncode == 2
            and "Error:" in proc_invalid_date.stderr
        ):
            emit_result("R4_validation_exit_code_2", "pass", "Invalid inputs exited with code 2 and Error: prefix")
        else:
            failures += 1
            emit_result(
                "R4_validation_exit_code_2",
                "fail",
                f"amt rc={proc_invalid_amt.returncode} err={proc_invalid_amt.stderr.strip()!r}; date rc={proc_invalid_date.returncode} err={proc_invalid_date.stderr.strip()!r}",
            )
    except Exception as exc:
        failures += 1
        emit_result("R4_validation_exit_code_2", "fail", str(exc))

    # Add second and third expenses for summary and list tests
    run_cli(
        entrypoint,
        ["add", "--amount", "42.00", "--category", "Travel", "--description", "Taxi", "--date", "2026-01-15"],
        cwd=workspace,
    )
    run_cli(
        entrypoint,
        ["add", "--amount", "8.50", "--category", "food", "--description", "Snack", "--date", "2026-01-10"],
        cwd=workspace,
    )

    # R5: Summary command with case-insensitive category
    try:
        proc_sum_all = run_cli(entrypoint, ["summary"], cwd=workspace)
        proc_sum_food = run_cli(entrypoint, ["summary", "--category", "FOOD"], cwd=workspace)
        # Total: 15.50 + 42.00 + 8.50 = 66.00
        # Food total: 15.50 + 8.50 = 24.00
        if (
            proc_sum_all.returncode == 0
            and "Total: $66.00" in proc_sum_all.stdout
            and proc_sum_food.returncode == 0
            and "Total: $24.00" in proc_sum_food.stdout
        ):
            emit_result("R5_summary_command", "pass", "Summary calculates total and case-insensitive category filter")
        else:
            failures += 1
            emit_result(
                "R5_summary_command",
                "fail",
                f"sum_all: {proc_sum_all.stdout.strip()!r}, sum_food: {proc_sum_food.stdout.strip()!r}",
            )
    except Exception as exc:
        failures += 1
        emit_result("R5_summary_command", "fail", str(exc))

    # R6: List command format and sorting (sorted by date asc, then id asc)
    # Expected order:
    # 1. 2026-01-10 (id 3)
    # 2. 2026-01-15 (id 2)
    # 3. today_utc (id 1)
    try:
        proc_list = run_cli(entrypoint, ["list"], cwd=workspace)
        expected_line_snack = "#3 | 2026-01-10 | $8.50 | food | Snack"
        expected_line_taxi = "#2 | 2026-01-15 | $42.00 | Travel | Taxi"
        expected_line_lunch = f"#1 | {today_utc} | $15.50 | Food | Lunch"

        out_lines = [line.strip() for line in proc_list.stdout.strip().splitlines() if line.strip()]
        if (
            proc_list.returncode == 0
            and len(out_lines) == 3
            and out_lines[0] == expected_line_snack
            and out_lines[1] == expected_line_taxi
            and out_lines[2] == expected_line_lunch
        ):
            emit_result("R6_list_command_format", "pass", "List command sorted correctly with expected columns")
        else:
            failures += 1
            emit_result(
                "R6_list_command_format",
                "fail",
                f"rc={proc_list.returncode}, lines={out_lines!r}",
            )
    except Exception as exc:
        failures += 1
        emit_result("R6_list_command_format", "fail", str(exc))

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
