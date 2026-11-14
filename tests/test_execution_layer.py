#!/usr/bin/env python3
"""Integration tests for the deterministic execution layer.

These exercise the wiring between the route flow gate, `validate.py tasks`,
`validate.py status`, and `scripts/run.py` — the paths a real project takes
after `daw-plan` saves a plan.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATE = PROJECT_ROOT / "scripts" / "validate.py"
ROUTE = PROJECT_ROOT / "scripts" / "route.py"
RUNNER = PROJECT_ROOT / "scripts" / "run.py"

MANIFEST_MARKER = "<!-- daw-task-manifest -->"


def _manifest_block(tasks: list[dict], workflow_id: str = "wf-integration") -> str:
    payload = {"schema_version": 1, "workflow_id": workflow_id, "tasks": tasks}
    return MANIFEST_MARKER + "\n```json\n" + json.dumps(payload, indent=2) + "\n```\n"


def _task(task_id: str, **overrides) -> dict:
    task = {
        "task_id": task_id,
        "title": f"Task {task_id}",
        "autonomy": "afk",
        "depends_on": [],
        "parallel_safe": False,
        "target_files": ["src/app.py"],
        "acceptance_criteria": ["the behavior works"],
        "verification_command": "python3 -c \"print('ok')\"",
        "expected_outcome": "exit code 0",
    }
    task.update(overrides)
    return task


def _run(argv: list[str]) -> tuple[int, dict]:
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)
    try:
        return proc.returncode, json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise AssertionError(f"non-JSON output.\nstdout={proc.stdout}\nstderr={proc.stderr}")


class ExecutionLayerIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = pathlib.Path(self.temp_dir.name).resolve()
        (self.root / "src").mkdir()
        (self.root / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        (self.root / "docs" / "specs").mkdir(parents=True)
        (self.root / "docs" / "specs" / "prd.md").write_text("# PRD\n", encoding="utf-8")
        (self.root / "docs" / "plans").mkdir(parents=True)
        self.plan = self.root / "docs" / "plans" / "wf-integration.md"

    def write_plan(self, body: str) -> None:
        self.plan.write_text(body, encoding="utf-8")

    def write_manifest_plan(self, tasks: list[dict]) -> None:
        self.write_plan(
            "# Plan\n\n"
            "- [ ] step: edit src/app.py, expected: tests pass\n\n"
            + _manifest_block(tasks)
        )

    def route_request(self) -> pathlib.Path:
        request = self.root / "request.json"
        request.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "intent": "feature",
                    "requirements": "clear",
                    "risk": "low",
                    "workspace": "in-place",
                }
            ),
            encoding="utf-8",
        )
        return request

    def test_gate_blocks_plan_without_manifest(self) -> None:
        self.write_plan("# Plan\n\n- [ ] step: edit file, expected: tests pass\n")
        code, payload = _run(
            [sys.executable, str(ROUTE), str(self.route_request()), "--root", str(PROJECT_ROOT), "--project-root", str(self.root)]
        )
        self.assertEqual(code, 1)
        self.assertEqual(payload["status"], "blocked")
        blockers = [b for b in payload["blockers"] if b["code"] == "FLOW_GATE_MISSING_ARTIFACT"]
        self.assertTrue(blockers)
        self.assertIn("BPF-9", blockers[0]["message"])

    def test_gate_passes_plan_with_manifest(self) -> None:
        self.write_manifest_plan([_task("TASK-01")])
        code, payload = _run(
            [sys.executable, str(ROUTE), str(self.route_request()), "--root", str(PROJECT_ROOT), "--project-root", str(self.root)]
        )
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["status"], "ready")

    def test_validate_tasks_accepts_a_runner_ready_manifest(self) -> None:
        self.write_manifest_plan([_task("TASK-01"), _task("TASK-02", depends_on=["TASK-01"])])
        code, payload = _run(
            [sys.executable, str(VALIDATE), "tasks", str(self.plan), "--project-root", str(self.root), "--format", "json"]
        )
        self.assertEqual(code, 0, payload)
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["task_count"], 2)

    def test_validate_tasks_rejects_a_manifest_the_runner_cannot_execute(self) -> None:
        self.write_manifest_plan([_task("TASK-01"), _task("TASK-02", depends_on=["TASK-01"]), _task("TASK-03", depends_on=["TASK-02"])])
        self.plan.write_text(
            self.plan.read_text(encoding="utf-8").replace('"depends_on": []', '"depends_on": ["TASK-99"]', 1),
            encoding="utf-8",
        )
        code, payload = _run(
            [sys.executable, str(VALIDATE), "tasks", str(self.plan), "--project-root", str(self.root), "--format", "json"]
        )
        self.assertEqual(code, 1)
        self.assertIn("task_dependency_unknown", [f["code"] for f in payload["findings"]])

    def test_runner_next_and_verify_line_up_with_the_gate(self) -> None:
        self.write_manifest_plan(
            [_task("TASK-01"), _task("TASK-02", depends_on=["TASK-01"], verification_command="python3 -c \"raise SystemExit(2)\"")]
        )
        code, payload = _run(
            [sys.executable, str(RUNNER), "next", "--plan", str(self.plan), "--project-root", str(self.root), "--format", "json"]
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["next_task_id"], "TASK-01")

        code, payload = _run(
            [sys.executable, str(RUNNER), "verify", "--plan", str(self.plan), "--project-root", str(self.root), "--task", "TASK-02", "--format", "json"]
        )
        self.assertEqual(code, 1)
        self.assertEqual(payload["verification"]["exit_code"], 2)
        evidence = self.root / payload["verification"]["evidence_path"]
        self.assertTrue(evidence.is_file())

    def test_status_agrees_with_the_gate_on_a_missing_manifest(self) -> None:
        self.write_plan("# Plan\n\n- [ ] step: edit file, expected: tests pass\n")
        (self.root / "AGENTS.md").write_text(
            "<!-- daw-config:start -->\n\n## DAW Configuration\n\n"
            "- schema: 1\n- daw_version: 0.5.0\n- spec_dir: docs/specs\n"
            "- test_command: none\n- lint_command: none\n- build_command: none\n"
            "- workspace: in-place\n- high_risk_paths: none\n- issue_tracker: none\n"
            "- default_branch: main\n- commit_convention: conventional\n"
            "- pr_template: none\n- ci_checks: none\n- release_process: none\n"
            "- branch_pattern: none\n\n<!-- daw-config:end -->\n",
            encoding="utf-8",
        )
        code, payload = _run(
            [sys.executable, str(VALIDATE), "status", "--project-root", str(self.root), "--format", "json"]
        )
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["summary"]["plans"], "missing")

    def test_runner_writes_only_inside_the_project_root(self) -> None:
        self.write_manifest_plan([_task("TASK-01")])
        outside = pathlib.Path(self.temp_dir.name).parent / "daw-escape-probe.txt"
        self.write_manifest_plan(
            [_task("TASK-01", target_files=["../daw-escape-probe.txt"])]
        )
        code, payload = _run(
            [sys.executable, str(RUNNER), "context", "--plan", str(self.plan), "--project-root", str(self.root), "--task", "TASK-01", "--format", "json"]
        )
        self.assertEqual(code, 2)
        self.assertIn("task_target_file_unsafe", [f["code"] for f in payload["findings"]])
        self.assertFalse(outside.exists())


if __name__ == "__main__":
    unittest.main()
