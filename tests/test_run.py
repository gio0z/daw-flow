#!/usr/bin/env python3
"""Behavior tests for `python3 scripts/run.py` (deterministic execution runner)."""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNNER = PROJECT_ROOT / "scripts" / "run.py"

MANIFEST_MARKER = "<!-- daw-task-manifest -->"


def _manifest(tasks: list[dict], workflow_id: str = "wf-test") -> str:
    payload = {"schema_version": 1, "workflow_id": workflow_id, "tasks": tasks}
    return MANIFEST_MARKER + "\n```json\n" + json.dumps(payload, indent=2) + "\n```\n"


def _task(
    task_id: str,
    *,
    title: str | None = None,
    autonomy: str = "afk",
    depends_on: list[str] | None = None,
    parallel_safe: bool = True,
    target_files: list[str] | None = None,
    verification_command: str = "python3 -c \"print('ok')\"",
    expected_outcome: str = "exit code 0",
) -> dict:
    return {
        "task_id": task_id,
        "title": title or f"Task {task_id}",
        "autonomy": autonomy,
        "depends_on": depends_on or [],
        "parallel_safe": parallel_safe,
        "target_files": target_files or ["src/app.py"],
        "acceptance_criteria": ["behavior works"],
        "verification_command": verification_command,
        "expected_outcome": expected_outcome,
    }


class RunnerTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = pathlib.Path(self.temp_dir.name).resolve()
        (self.root / "src").mkdir()
        (self.root / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")

    def write_plan(self, body: str, name: str = "plan.md") -> pathlib.Path:
        path = self.root / "docs" / "plans" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def run_cli(self, *args: str) -> tuple[int, dict]:
        proc = subprocess.run(
            [sys.executable, str(RUNNER), *args, "--format", "json"],
            capture_output=True,
            text=True,
            check=False,
        )
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            self.fail(f"runner did not emit JSON.\nstdout={proc.stdout}\nstderr={proc.stderr}")
        return proc.returncode, payload


class ManifestExtractionTests(RunnerTestBase):
    def test_manifest_requires_marker(self) -> None:
        plan = self.write_plan("```json\n{\"schema_version\": 1, \"tasks\": []}\n```\n")
        code, payload = self.run_cli("next", "--plan", str(plan), "--project-root", str(self.root))
        self.assertEqual(code, 2)
        self.assertIn("manifest_missing", [f["code"] for f in payload["findings"]])

    def test_duplicate_markers_are_ambiguous(self) -> None:
        plan = self.write_plan(_manifest([_task("T-1")]) + _manifest([_task("T-2")]))
        code, payload = self.run_cli("next", "--plan", str(plan), "--project-root", str(self.root))
        self.assertEqual(code, 2)
        self.assertIn("manifest_ambiguous", [f["code"] for f in payload["findings"]])

    def test_duplicate_task_id_rejected(self) -> None:
        plan = self.write_plan(_manifest([_task("T-1"), _task("T-1")]))
        code, payload = self.run_cli("next", "--plan", str(plan), "--project-root", str(self.root))
        self.assertEqual(code, 2)
        self.assertIn("task_id_duplicate", [f["code"] for f in payload["findings"]])

    def test_unknown_dependency_rejected(self) -> None:
        plan = self.write_plan(_manifest([_task("T-1", depends_on=["T-missing"])]))
        code, payload = self.run_cli("next", "--plan", str(plan), "--project-root", str(self.root))
        self.assertEqual(code, 2)
        self.assertIn("task_dependency_unknown", [f["code"] for f in payload["findings"]])

    def test_dependency_cycle_rejected(self) -> None:
        plan = self.write_plan(
            _manifest([_task("T-1", depends_on=["T-2"]), _task("T-2", depends_on=["T-1"])])
        )
        code, payload = self.run_cli("next", "--plan", str(plan), "--project-root", str(self.root))
        self.assertEqual(code, 2)
        self.assertIn("task_dependency_cycle", [f["code"] for f in payload["findings"]])

    def test_unsafe_target_path_rejected(self) -> None:
        plan = self.write_plan(_manifest([_task("T-1", target_files=["../outside.py"])]))
        code, payload = self.run_cli("next", "--plan", str(plan), "--project-root", str(self.root))
        self.assertEqual(code, 2)
        self.assertIn("task_target_file_unsafe", [f["code"] for f in payload["findings"]])

    def test_invalid_autonomy_rejected(self) -> None:
        plan = self.write_plan(_manifest([_task("T-1", autonomy="maybe")]))
        code, payload = self.run_cli("next", "--plan", str(plan), "--project-root", str(self.root))
        self.assertEqual(code, 2)
        self.assertIn("task_autonomy_invalid", [f["code"] for f in payload["findings"]])


class ReadySetTests(RunnerTestBase):
    def test_ready_set_respects_dependencies(self) -> None:
        plan = self.write_plan(
            _manifest([_task("T-1"), _task("T-2", depends_on=["T-1"]), _task("T-3", depends_on=["T-2"])])
        )
        code, payload = self.run_cli("next", "--plan", str(plan), "--project-root", str(self.root))
        self.assertEqual(code, 0)
        self.assertEqual(payload["next_task_id"], "T-1")
        self.assertEqual([entry["task_id"] for entry in payload["ready"]], ["T-1"])
        self.assertEqual([entry["task_id"] for entry in payload["blocked"]], ["T-2", "T-3"])

    def test_accepted_task_unblocks_dependent(self) -> None:
        plan = self.write_plan(
            _manifest([_task("T-1"), _task("T-2", depends_on=["T-1"])])
        )
        code, payload = self.run_cli(
            "next", "--plan", str(plan), "--project-root", str(self.root), "--accepted", "T-1"
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["next_task_id"], "T-2")
        self.assertEqual(payload["blocked"], [])

    def test_hitl_task_never_becomes_ready(self) -> None:
        plan = self.write_plan(_manifest([_task("T-1", autonomy="hitl")]))
        code, payload = self.run_cli("next", "--plan", str(plan), "--project-root", str(self.root))
        self.assertEqual(code, 0)
        self.assertEqual(payload["ready"], [])
        self.assertEqual([entry["task_id"] for entry in payload["requires_human"]], ["T-1"])
        self.assertIsNone(payload["next_task_id"])

    def test_ready_order_is_depth_then_id(self) -> None:
        plan = self.write_plan(
            _manifest(
                [
                    _task("T-3", depends_on=["T-1"]),
                    _task("T-1"),
                    _task("T-2"),
                    _task("T-4"),
                ]
            )
        )
        code, payload = self.run_cli("next", "--plan", str(plan), "--project-root", str(self.root))
        self.assertEqual(code, 0)
        self.assertEqual([entry["task_id"] for entry in payload["ready"]], ["T-1", "T-2", "T-4"])


class ContextAssemblyTests(RunnerTestBase):
    def test_context_pack_includes_task_and_file(self) -> None:
        plan = self.write_plan(_manifest([_task("T-1")]))
        code, payload = self.run_cli(
            "context", "--plan", str(plan), "--project-root", str(self.root), "--task", "T-1"
        )
        self.assertEqual(code, 0)
        meta = payload["context"]
        self.assertEqual(meta["task_id"], "T-1")
        self.assertEqual([f["path"] for f in meta["files_included"]], ["src/app.py"])
        self.assertEqual(meta["files_truncated"], [])
        self.assertEqual(len(meta["pack_sha256"]), 64)

    def test_context_budget_truncates_and_records(self) -> None:
        (self.root / "src" / "big.py").write_text("x" * 5000, encoding="utf-8")
        plan = self.write_plan(_manifest([_task("T-1", target_files=["src/big.py"])]))
        code, payload = self.run_cli(
            "context",
            "--plan",
            str(plan),
            "--project-root",
            str(self.root),
            "--task",
            "T-1",
            "--budget-chars",
            "1200",
        )
        self.assertEqual(code, 0)
        meta = payload["context"]
        self.assertTrue(meta["files_truncated"])
        self.assertEqual(meta["files_truncated"][0]["reason"], "truncated to context budget")
        self.assertLessEqual(meta["pack_chars"], 1200 + 2000)

    def test_context_output_file_written(self) -> None:
        plan = self.write_plan(_manifest([_task("T-1")]))
        out = self.root / "docs" / "evidence" / "runner" / "context-T-1.md"
        code, _ = self.run_cli(
            "context",
            "--plan",
            str(plan),
            "--project-root",
            str(self.root),
            "--task",
            "T-1",
            "--out",
            str(out),
        )
        self.assertEqual(code, 0)
        self.assertTrue(out.is_file())
        self.assertIn("Task T-1", out.read_text(encoding="utf-8"))


class VerificationTests(RunnerTestBase):
    def test_passing_command_captures_evidence(self) -> None:
        plan = self.write_plan(
            _manifest([_task("T-1", verification_command="python3 -c \"print('hello')\"")])
        )
        code, payload = self.run_cli(
            "verify", "--plan", str(plan), "--project-root", str(self.root), "--task", "T-1"
        )
        self.assertEqual(code, 0)
        outcome = payload["verification"]
        self.assertEqual(outcome["exit_code"], 0)
        self.assertTrue(outcome["passed"])
        log = self.root / outcome["evidence_path"]
        self.assertTrue(log.is_file())
        self.assertIn("hello", log.read_text(encoding="utf-8"))
        self.assertEqual(len(outcome["evidence_sha256"]), 64)

    def test_failing_command_is_not_a_pass(self) -> None:
        plan = self.write_plan(
            _manifest([_task("T-1", verification_command="python3 -c \"raise SystemExit(3)\"")])
        )
        code, payload = self.run_cli(
            "verify", "--plan", str(plan), "--project-root", str(self.root), "--task", "T-1"
        )
        self.assertEqual(code, 1)
        outcome = payload["verification"]
        self.assertEqual(outcome["exit_code"], 3)
        self.assertFalse(outcome["passed"])

    def test_missing_command_binary_is_reported(self) -> None:
        plan = self.write_plan(
            _manifest([_task("T-1", verification_command="definitely-not-a-real-binary-xyz")])
        )
        code, payload = self.run_cli(
            "verify", "--plan", str(plan), "--project-root", str(self.root), "--task", "T-1"
        )
        self.assertEqual(code, 1)
        self.assertEqual(payload["verification"]["exit_code"], 127)

    def test_evidence_attempts_increment(self) -> None:
        plan = self.write_plan(_manifest([_task("T-1")]))
        for _ in range(2):
            self.run_cli("verify", "--plan", str(plan), "--project-root", str(self.root), "--task", "T-1")
        logs = sorted((self.root / "docs" / "daw" / "evidence" / "T-1").glob("verify-*.log"))
        self.assertEqual([p.name for p in logs], ["verify-1.log", "verify-2.log"])

    def test_evidence_uses_the_projects_existing_evidence_directory(self) -> None:
        # A project that already keeps evidence at docs/evidence/ keeps it:
        # the runner writes where the project already writes.
        (self.root / "docs" / "evidence").mkdir(parents=True)
        plan = self.write_plan(_manifest([_task("T-1")]))
        code, payload = self.run_cli(
            "verify", "--plan", str(plan), "--project-root", str(self.root), "--task", "T-1"
        )
        self.assertEqual(code, 0, payload)
        logs = sorted((self.root / "docs" / "evidence" / "T-1").glob("verify-*.log"))
        self.assertEqual([p.name for p in logs], ["verify-1.log"])
        self.assertFalse((self.root / "docs" / "daw" / "evidence").exists())

    def test_shell_metacharacters_are_not_executed(self) -> None:
        marker = self.root / "pwned.txt"
        plan = self.write_plan(
            _manifest([_task("T-1", verification_command=f"python3 -c pass && touch {marker}")])
        )
        code, payload = self.run_cli(
            "verify", "--plan", str(plan), "--project-root", str(self.root), "--task", "T-1"
        )
        # The runner executes argv without a shell: the `&&` chain is never
        # interpreted, so the marker file is never created.
        self.assertFalse(marker.exists())
        self.assertEqual(payload["verification"]["exit_code"], 0)
        self.assertIn("&&", payload["verification"]["command"])


class RunLoopTests(RunnerTestBase):
    def setUp(self) -> None:
        if not shutil.which("git"):
            self.skipTest("git is not available")
        super().setUp()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        (self.repo / ".gitignore").write_text(".worktrees/\n__pycache__/\n", encoding="utf-8")
        (self.repo / "src").mkdir()
        (self.repo / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        for args in (
            ["init", "-q", "."],
            ["config", "user.email", "test@example.invalid"],
            ["config", "user.name", "Runner Test"],
            ["add", "-A"],
            ["commit", "-qm", "init"],
        ):
            proc = subprocess.run(["git", *args], cwd=str(self.repo), capture_output=True, text=True, check=False)
            if proc.returncode != 0:
                self.fail(f"git {args} failed: {proc.stderr}")

    def write_repo_plan(self, body: str, name: str = "plan.md") -> pathlib.Path:
        path = self.repo / "docs" / "plans" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def test_dry_run_does_not_execute_agent(self) -> None:
        marker = self.root / "agent-ran.txt"
        plan = self.write_repo_plan(_manifest([_task("T-1")]))
        code, payload = self.run_cli(
            "run",
            "--plan",
            str(plan),
            "--project-root",
            str(self.repo),
            "--agent-command",
            json.dumps(["python3", "-c", f"open({str(marker)!r}, 'w').write('x')"]),
            "--dry-run",
        )
        self.assertEqual(code, 0)
        self.assertFalse(marker.exists())
        self.assertTrue(payload["completed"][0]["dry_run"])

    def test_agent_receives_the_context_pack_on_stdin(self) -> None:
        plan = self.write_repo_plan(_manifest([_task("T-1")]))
        captured = self.root / "received.md"
        code, payload = self.run_cli(
            "run",
            "--plan",
            str(plan),
            "--project-root",
            str(self.repo),
            "--agent-command",
            json.dumps(
                ["python3", "-c", f"import sys;open({str(captured)!r},'w').write(sys.stdin.read())"]
            ),
        )
        self.assertEqual(code, 0, payload)
        received = captured.read_text(encoding="utf-8")
        self.assertIn("# Task T-1", received)
        self.assertIn("Verification command:", received)

    def test_run_executes_agent_then_verifies(self) -> None:
        plan = self.write_repo_plan(
            _manifest([_task("T-1", verification_command="python3 -c \"print('verified')\"")])
        )
        code, payload = self.run_cli(
            "run",
            "--plan",
            str(plan),
            "--project-root",
            str(self.repo),
            "--agent-command",
            json.dumps(["python3", "-c", "print('agent ran')"]),
        )
        self.assertEqual(code, 0, payload)
        entry = payload["completed"][0]
        self.assertEqual(entry["agent_exit_code"], 0)
        self.assertTrue(entry["verification"]["passed"])
        self.assertIn("T-1", payload["accepted"])

    def test_run_stops_on_failed_verification(self) -> None:
        plan = self.write_repo_plan(
            _manifest(
                [
                    _task("T-1", verification_command="python3 -c \"raise SystemExit(1)\""),
                    _task("T-2", depends_on=["T-1"]),
                ]
            )
        )
        code, payload = self.run_cli(
            "run",
            "--plan",
            str(plan),
            "--project-root",
            str(self.repo),
            "--agent-command",
            json.dumps(["python3", "-c", "print('agent ran')"]),
            "--max-tasks",
            "5",
        )
        self.assertEqual(code, 1, payload)
        self.assertEqual(len(payload["completed"]), 1)
        self.assertEqual(payload["accepted"], [])

    def test_hitl_task_is_not_dispatched(self) -> None:
        marker = self.root / "agent-ran.txt"
        plan = self.write_repo_plan(_manifest([_task("T-1", autonomy="hitl")]))
        code, payload = self.run_cli(
            "run",
            "--plan",
            str(plan),
            "--project-root",
            str(self.repo),
            "--agent-command",
            json.dumps(["python3", "-c", f"open({str(marker)!r}, 'w').write('x')"]),
            "--max-tasks",
            "3",
        )
        self.assertEqual(code, 0, payload)
        self.assertFalse(marker.exists())
        self.assertEqual(payload["completed"], [])


class SafetyTests(RunnerTestBase):
    def test_missing_plan_file_exits_two(self) -> None:
        code, payload = self.run_cli(
            "next", "--plan", str(self.root / "nope.md"), "--project-root", str(self.root)
        )
        self.assertEqual(code, 2)
        self.assertFalse(payload["valid"])

    def test_unknown_task_id_exits_two(self) -> None:
        plan = self.write_plan(_manifest([_task("T-1")]))
        code, payload = self.run_cli(
            "context", "--plan", str(plan), "--project-root", str(self.root), "--task", "T-missing"
        )
        self.assertEqual(code, 2)
        self.assertFalse(payload["valid"])

    def test_envelope_declares_no_push_or_deploy(self) -> None:
        plan = self.write_plan(_manifest([_task("T-1")]))
        _, payload = self.run_cli("next", "--plan", str(plan), "--project-root", str(self.root))
        joined = " ".join(payload["limitations"]).lower()
        self.assertIn("never pushes", joined)
        self.assertIn("never a daemon", joined)


if __name__ == "__main__":
    unittest.main()
