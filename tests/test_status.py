#!/usr/bin/env python3
"""Behavior tests for `python3 scripts/validate.py status`."""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATOR_SCRIPT = PROJECT_ROOT / "scripts" / "validate.py"
INSTALLED_VERSION = (PROJECT_ROOT / "VERSION").read_text(encoding="utf-8").strip()


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class StatusTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp_dir.name).resolve()
        (self.root / "docs" / "specs").mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_config(self, daw_version: str = INSTALLED_VERSION, **overrides: str) -> None:
        config = {
            "schema": "1",
            "daw_version": daw_version,
            "spec_dir": "docs/specs",
            "test_command": "python3 -m unittest",
            "lint_command": "none",
            "build_command": "none",
            "workspace": "in-place",
            "high_risk_paths": "none",
            "issue_tracker": "none",
            "default_branch": "main",
            "commit_convention": "conventional",
            "pr_template": "none",
            "ci_checks": "none",
            "release_process": "none",
            "branch_pattern": "none",
        }
        config.update(overrides)
        lines = ["<!-- daw-config:start -->", "", "## DAW Configuration", ""]
        lines += [f"- {k}: {v}" for k, v in config.items()]
        lines += ["", "<!-- daw-config:end -->", ""]
        (self.root / "AGENTS.md").write_text("\n".join(lines), encoding="utf-8")

    def write_task(self, task_id: str, *, complete: bool, break_result: bool = False) -> None:
        src = self.root / "src" / f"{task_id}.py"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("v1\n", encoding="utf-8")
        base_sha = _sha(src)
        src.write_text("v2\n", encoding="utf-8")
        task_dir = self.root / "docs" / "evidence" / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        log = task_dir / "test.log"
        log.write_text("OK\n", encoding="utf-8")
        contract: dict = {
            "schema_version": 1,
            "objective": "Change module.",
            "baseline": {"revision": "r1", "files": [{"path": f"src/{task_id}.py", "sha256": base_sha}]},
            "documents": [],
            "acceptance_criteria": [{"id": "AC-1", "criterion": "Module changed."}],
            "operation": {"risk": "low", "action": "edit", "target": "src", "revision": "r1", "scope": ["src"]},
        }
        if complete:
            contract["result"] = {"revision": "r2", "files": [{"path": f"src/{task_id}.py", "sha256": _sha(src)}]}
            contract["evidence"] = [
                {
                    "criterion_id": "AC-1",
                    "status": "passed",
                    "reference": f"docs/evidence/{task_id}/test.log",
                    "summary": "Tests passed.",
                    "sha256": _sha(log),
                    "revision": "r2",
                }
            ]
        (task_dir / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
        if break_result:
            src.write_text("edited after verify\n", encoding="utf-8")

    def run_status(self) -> tuple[int, dict]:
        res = subprocess.run(
            [sys.executable, str(VALIDATOR_SCRIPT), "status", "--project-root", str(self.root), "--format", "json"],
            capture_output=True,
            text=True,
        )
        return res.returncode, json.loads(res.stdout)


class TestStatus(StatusTestBase):
    def test_clean_project_recommends_none(self) -> None:
        self.write_config()
        self.write_task("T1", complete=True)
        code, data = self.run_status()
        self.assertEqual(code, 0, data)
        self.assertEqual(data["check"], "status")
        self.assertEqual(data["summary"]["config"], "ok")
        self.assertEqual(data["summary"]["ledger"], "not_applicable")
        self.assertEqual(data["summary"]["tasks"], {"complete_valid": 1, "complete_invalid": 0, "in_progress": 0})
        self.assertEqual(data["recommended_route"], "none")

    def test_missing_config_recommends_setup(self) -> None:
        code, data = self.run_status()
        self.assertEqual(data["summary"]["config"], "missing")
        self.assertEqual(data["recommended_route"], "setup")

    def test_stale_version_recommends_upgrade_recheck(self) -> None:
        major, minor, patch = (int(p) for p in INSTALLED_VERSION.split("."))
        self.write_config(daw_version=f"{major}.{max(minor - 1, 0)}.{patch}" if minor else f"{major - 1}.0.0")
        code, data = self.run_status()
        self.assertEqual(code, 0, data)
        self.assertEqual(data["summary"]["config"], "stale")
        self.assertEqual(data["recommended_route"], "upgrade-recheck")

    def test_specs_without_ledger_recommend_design_rework(self) -> None:
        self.write_config()
        (self.root / "docs" / "specs" / "prd.md").write_text("# PRD\n", encoding="utf-8")
        _, data = self.run_status()
        self.assertEqual(data["summary"]["ledger"], "missing")
        self.assertIn("status_ledger_missing", [f["code"] for f in data["findings"]])
        self.assertEqual(data["recommended_route"], "design-rework")

    def test_code_edited_after_verify_recommends_verify(self) -> None:
        self.write_config()
        self.write_task("T1", complete=True, break_result=True)
        code, data = self.run_status()
        self.assertEqual(code, 1, data)
        self.assertEqual(data["summary"]["tasks"]["complete_invalid"], 1)
        self.assertEqual(data["recommended_route"], "verify")
        result_changed = [f for f in data["findings"] if f["code"] == "result_changed"]
        self.assertTrue(result_changed)
        self.assertTrue(result_changed[0]["path"].startswith("contract[docs/evidence/T1/contract.json]:"))

    def test_in_progress_task_is_warning_only(self) -> None:
        self.write_config()
        self.write_task("T2", complete=False)
        code, data = self.run_status()
        self.assertEqual(code, 0, data)
        self.assertEqual(data["summary"]["tasks"]["in_progress"], 1)
        self.assertIn("status_task_in_progress", [f["code"] for f in data["findings"]])
        self.assertEqual(data["recommended_route"], "none")

    def test_config_problem_outranks_task_problem(self) -> None:
        self.write_config(workspace="sideways")
        self.write_task("T1", complete=True, break_result=True)
        _, data = self.run_status()
        self.assertEqual(data["summary"]["config"], "invalid")
        self.assertEqual(data["recommended_route"], "setup")

    def test_root_not_directory_is_usage_error(self) -> None:
        res = subprocess.run(
            [sys.executable, str(VALIDATOR_SCRIPT), "status", "--project-root", str(self.root / "nope")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 2)


if __name__ == "__main__":
    unittest.main()
