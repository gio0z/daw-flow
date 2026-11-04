"""Behavioral regression tests for expense-tracker acceptance.py R6 list ordering."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parent.parent
ACCEPTANCE_SCRIPT = REPO_ROOT / "references" / "wizard-bench" / "expense-tracker" / "acceptance.py"

EXPECTED_ALL_PASS = {
    "R1_entrypoint_exists": "pass",
    "R2_csv_persistence": "pass",
    "R3_add_command": "pass",
    "R4_validation_exit_code_2": "pass",
    "R5_summary_command": "pass",
    "R6_list_command_format": "pass",
    "R7_missing_file_handling": "pass",
}

TOY_EXPENSES_CLI = '''#!/usr/bin/env python3
import csv
from datetime import datetime, timezone
from pathlib import Path
import sys

csv_file = Path("expenses.csv")

def main():
    args = sys.argv[1:]
    if not args:
        return 0
    cmd = args[0]
    if cmd == "list":
        if not csv_file.exists():
            print("No expenses found.")
            return 0
        with open(csv_file, mode="r", encoding="utf-8") as f:
            rows = [
                {"id": int(r["id"]), "date": r["date"], "amount": float(r["amount"]), "category": r["category"], "description": r["description"]}
                for r in csv.DictReader(f)
            ]
        if not rows:
            print("No expenses found.")
            return 0
        rows.sort(key=lambda x: (x["date"], x["id"]))
        for r in rows:
            print(f"#{r['id']} | {r['date']} | ${r['amount']:.2f} | {r['category']} | {r['description']}")
        return 0

    if cmd == "summary":
        if not csv_file.exists():
            print("Total: $0.00")
            return 0
        cat_filter = None
        if "--category" in args:
            cat_filter = args[args.index("--category") + 1].strip().lower()
        with open(csv_file, mode="r", encoding="utf-8") as f:
            total = sum(
                float(r["amount"]) for r in csv.DictReader(f)
                if cat_filter is None or r["category"].strip().lower() == cat_filter
            )
        print(f"Total: ${total:.2f}")
        return 0

    if cmd == "add":
        amt, cat, desc, date = None, None, None, None
        i = 1
        while i < len(args):
            flag, val = args[i], args[i + 1]
            if flag == "--amount": amt = float(val)
            elif flag == "--category": cat = val
            elif flag == "--description": desc = val
            elif flag == "--date": date = val
            i += 2

        if amt is None or amt <= 0:
            sys.stderr.write("Error: amount must be > 0\\n")
            return 2
        if date is not None:
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                sys.stderr.write("Error: invalid date format\\n")
                return 2
        else:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        exists = csv_file.exists()
        next_id = 1
        if exists:
            with open(csv_file, mode="r", encoding="utf-8") as f:
                ids = [int(r["id"]) for r in csv.DictReader(f) if r.get("id")]
                if ids: next_id = max(ids) + 1

        with open(csv_file, mode="a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            if not exists:
                writer.writerow(["id", "date", "amount", "category", "description"])
            writer.writerow([next_id, date, f"{amt:.2f}", cat, desc])

        print(f"Added expense #{next_id}")
        return 0

    return 0

if __name__ == "__main__":
    sys.exit(main())
'''

FAULTY_EXPENSES_CLI_SORT_BY_ID = TOY_EXPENSES_CLI.replace(
    'rows.sort(key=lambda x: (x["date"], x["id"]))',
    'rows.sort(key=lambda x: x["id"])',
)

FAULTY_EXPENSES_CLI_WRONG_FORMAT = TOY_EXPENSES_CLI.replace(
    'print(f"#{r[\'id\']} | {r[\'date\']} | ${r[\'amount\']:.2f} | {r[\'category\']} | {r[\'description\']}")',
    'print(f"#{r[\'id\']} - {r[\'date\']} - {r[\'amount\']} - {r[\'category\']} - {r[\'description\']}")',
)

SITECUSTOMIZE_CODE = '''import os
from datetime import datetime, timezone
import datetime as datetime_module

sim_date = os.environ.get("_SIMULATED_UTC_DATE")
if sim_date:
    target_dt = datetime.strptime(sim_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    real_dt = datetime_module.datetime

    class SimulatedDatetime(real_dt):
        @classmethod
        def now(cls, tz=None):
            if tz == timezone.utc:
                return target_dt
            return super().now(tz)

    datetime_module.datetime = SimulatedDatetime
'''


class ExpenseAcceptanceDateOrderTests(unittest.TestCase):
    def _init_workspace(self, workspace: Path, cli_code: str) -> None:
        (workspace / "expenses.py").write_text(cli_code, encoding="utf-8")
        sim_lib = workspace / "_sim_lib"
        sim_lib.mkdir(parents=True, exist_ok=True)
        (sim_lib / "sitecustomize.py").write_text(SITECUSTOMIZE_CODE, encoding="utf-8")

    def _run_acceptance(
        self,
        workspace: Path,
        sim_date: str | None = None,
        expected_returncode: int = 0,
    ) -> dict[str, dict]:
        env = os.environ.copy()
        if sim_date is not None:
            env["_SIMULATED_UTC_DATE"] = sim_date
            sim_lib = str(workspace / "_sim_lib")
            existing = env.get("PYTHONPATH")
            env["PYTHONPATH"] = f"{sim_lib}{os.pathsep}{existing}" if existing else sim_lib

        res = subprocess.run(
            [sys.executable, str(ACCEPTANCE_SCRIPT), str(workspace)],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(
            res.returncode,
            expected_returncode,
            f"Acceptance exited with code {res.returncode} (expected {expected_returncode}).\n"
            f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}",
        )
        checks = {}
        for line in res.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if "check" in record:
                checks[record["check"]] = record
        return checks

    def test_list_order_all_date_boundaries(self):
        cases = [
            ("before_jan10", "2026-01-05"),
            ("equal_jan10", "2026-01-10"),
            ("between_jan10_and_jan15", "2026-01-12"),
            ("equal_jan15", "2026-01-15"),
            ("after_jan15", "2026-01-20"),
        ]
        for name, sim_date in cases:
            with self.subTest(case=name, sim_date=sim_date):
                with tempfile.TemporaryDirectory(prefix=f"expense-{name}-") as td:
                    workspace = Path(td)
                    self._init_workspace(workspace, TOY_EXPENSES_CLI)
                    checks = self._run_acceptance(workspace, sim_date=sim_date, expected_returncode=0)
                    self.assertEqual(checks.get("R6_list_command_format", {}).get("status"), "pass")

    def test_ambient_system_clock_passes(self):
        with tempfile.TemporaryDirectory(prefix="expense-ambient-") as td:
            workspace = Path(td)
            self._init_workspace(workspace, TOY_EXPENSES_CLI)
            checks = self._run_acceptance(workspace, sim_date=None, expected_returncode=0)
            actual_statuses = {name: data.get("status") for name, data in checks.items()}
            self.assertEqual(actual_statuses, EXPECTED_ALL_PASS)

    def test_faulty_cli_wrong_date_sorting_fails(self):
        with tempfile.TemporaryDirectory(prefix="expense-faulty-sort-") as td:
            workspace = Path(td)
            self._init_workspace(workspace, FAULTY_EXPENSES_CLI_SORT_BY_ID)
            checks = self._run_acceptance(workspace, sim_date="2026-01-20", expected_returncode=1)
            self.assertEqual(checks.get("R6_list_command_format", {}).get("status"), "fail")

    def test_faulty_cli_wrong_format_fails(self):
        with tempfile.TemporaryDirectory(prefix="expense-faulty-fmt-") as td:
            workspace = Path(td)
            self._init_workspace(workspace, FAULTY_EXPENSES_CLI_WRONG_FORMAT)
            checks = self._run_acceptance(workspace, sim_date="2026-01-20", expected_returncode=1)
            self.assertEqual(checks.get("R6_list_command_format", {}).get("status"), "fail")


if __name__ == "__main__":
    unittest.main()
