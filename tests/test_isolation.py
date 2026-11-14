#!/usr/bin/env python3
"""Tests for the runner's isolated-task execution path.

These exercise `run.py isolate` against real git repositories: the behaviour
under test (worktree isolation, the merge gate, escape detection) only means
something when git actually does it.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNNER = PROJECT_ROOT / "scripts" / "run.py"

GIT_AVAILABLE = shutil.which("git") is not None

PLAN_TEMPLATE = """# Plan: isolation test

<!-- daw-task-manifest -->
```json
{
  "schema_version": 1,
  "workflow_id": "wf-iso",
  "tasks": [
    {
      "task_id": "TASK-01",
      "title": "Rotate token version",
      "autonomy": "afk",
      "depends_on": [],
      "parallel_safe": false,
      "target_files": ["app.py"],
      "acceptance_criteria": ["the app still imports"],
      "verification_command": "python3 -c \\"import app; assert app.ok()\\"",
      "expected_outcome": "0 exit code"
    }
  ]
}
```
"""


def _git(repo: pathlib.Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return result.stdout.decode("utf-8", errors="replace")


class IsolatedRunBase(unittest.TestCase):
    def setUp(self) -> None:
        if not GIT_AVAILABLE:
            self.skipTest("git is not available")
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = pathlib.Path(self.temp_dir.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        _git(self.repo, "init", "-q", ".")
        _git(self.repo, "config", "user.email", "test@example.invalid")
        _git(self.repo, "config", "user.name", "Isolation Test")
        (self.repo / "app.py").write_text("def ok():\n    return True\n", encoding="utf-8")
        (self.repo / ".gitignore").write_text(".worktrees/\n__pycache__/\n", encoding="utf-8")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-qm", "init")

        self.plan = self.repo / "docs" / "plans" / "wf.md"
        self.plan.parent.mkdir(parents=True)
        self.plan.write_text(PLAN_TEMPLATE, encoding="utf-8")

        self.agent = self.root / "agent.sh"
        self.escape_agent = self.root / "escape.sh"
        self.agent.write_text(
            "#!/bin/sh\ncat > app.py <<'INNER'\ndef ok():\n    return True\nINNER\nexit 0\n",
            encoding="utf-8",
        )
        self.escape_agent.write_text(
            f"#!/bin/sh\necho escaped >> {self.repo / 'app.py'}\nexit 0\n", encoding="utf-8"
        )
        self.agent.chmod(0o755)
        self.escape_agent.chmod(0o755)

    def isolate(
        self, agent: pathlib.Path | None = None, extra: list[str] | None = None
    ) -> tuple[int, dict]:
        argv = [
            sys.executable,
            str(RUNNER),
            "isolate",
            "--plan",
            str(self.plan),
            "--project-root",
            str(self.repo),
            "--task",
            "TASK-01",
            "--agent-command",
            json.dumps([str(agent or self.agent), "{prompt_file}"]),
            "--format",
            "json",
            *(extra or []),
        ]
        proc = subprocess.run(argv, capture_output=True, text=True, check=False)
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            payload = {"stdout": proc.stdout, "stderr": proc.stderr}
        return proc.returncode, payload


class IsolateTests(IsolatedRunBase):
    def test_a_verified_task_is_committed_and_merged(self) -> None:
        code, payload = self.isolate()
        self.assertEqual(code, 0, payload)
        self.assertTrue(payload["verification"]["passed"])
        self.assertTrue(payload["merged"]["merged"])
        self.assertEqual(payload["branch"], "daw/TASK-01-rotate-token-version")
        content = _git(self.repo, "show", "daw/integration:app.py")
        self.assertIn("def ok()", content)

    def test_the_agent_works_inside_the_worktree(self) -> None:
        code, payload = self.isolate()
        self.assertEqual(code, 0, payload)
        worktree = pathlib.Path(payload["worktree_path"])
        self.assertTrue(worktree.is_dir())
        self.assertEqual(
            worktree.parent.name, ".worktrees", "the worktree must live in the container"
        )

    def test_verification_runs_inside_the_worktree(self) -> None:
        code, payload = self.isolate()
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["verification"]["cwd"], payload["worktree_path"])

    def test_evidence_records_the_branch_and_commit(self) -> None:
        code, payload = self.isolate()
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["verification"]["branch"], payload["branch"])
        self.assertEqual(payload["verification"]["commit"], payload["commit"])

    def test_a_failing_verification_is_never_merged(self) -> None:
        failing = self.root / "fail.sh"
        failing.write_text("#!/bin/sh\necho 'def ok():\n    return False\n' > app.py\nexit 0\n", encoding="utf-8")
        failing.chmod(0o755)
        code, payload = self.isolate(agent=failing)
        self.assertEqual(code, 1)
        self.assertFalse(payload["verification"]["passed"])
        self.assertFalse(payload["merged"]["merged"])

    def test_an_escaping_agent_is_detected_and_not_merged(self) -> None:
        code, payload = self.isolate(agent=self.escape_agent)
        self.assertEqual(code, 2)
        codes = [f["code"] for f in payload["findings"]]
        self.assertIn("worktree_escape_detected", codes)

    def test_an_absolute_path_write_into_the_main_tree_is_detected(self) -> None:
        # The worktree is a working directory, not a sandbox: an absolute path
        # bypasses it. A write that lands in the user's main tree must still be
        # caught, because that is what would corrupt their work.
        absolute_agent = self.root / "absolute.sh"
        absolute_agent.write_text(
            f"#!/bin/sh\necho corrupted >> {self.repo / 'app.py'}\nexit 0\n", encoding="utf-8"
        )
        absolute_agent.chmod(0o755)
        code, payload = self.isolate(agent=absolute_agent)
        self.assertEqual(code, 2)
        codes = [f["code"] for f in payload["findings"]]
        self.assertIn("worktree_escape_detected", codes)

    def test_an_agent_modifying_an_already_dirty_path_is_detected(self) -> None:
        # A path that was already dirty before the run appears in the before
        # and after path sets alike, so comparing path sets cannot see the
        # agent's write. Comparing content hashes can.
        (self.repo / "app.py").write_text("def ok():\n    return True\n# dirty\n", encoding="utf-8")
        code, payload = self.isolate(agent=self.escape_agent)
        self.assertEqual(code, 2, payload)
        codes = [f["code"] for f in payload["findings"]]
        self.assertIn("worktree_escape_detected", codes)

    def test_the_users_working_tree_is_never_modified(self) -> None:
        before = (self.repo / "app.py").read_text(encoding="utf-8")
        self.isolate()
        after = (self.repo / "app.py").read_text(encoding="utf-8")
        self.assertEqual(before, after)

    def test_a_subagent_spawned_by_the_agent_stays_in_the_worktree(self) -> None:
        # The working directory is inherited by the whole process tree, so a
        # worker that spawns its own swarm keeps the swarm inside the worktree.
        swarm_agent = self.root / "swarm.sh"
        swarm_agent.write_text(
            "#!/bin/sh\n"
            "sh -c 'echo written-by-subagent > swarm_output.txt'\n"
            "echo done\n"
            "exit 0\n",
            encoding="utf-8",
        )
        swarm_agent.chmod(0o755)
        code, payload = self.isolate(agent=swarm_agent)
        self.assertEqual(code, 0, payload)
        worktree = pathlib.Path(payload["worktree_path"])
        self.assertTrue((worktree / "swarm_output.txt").is_file())
        self.assertFalse((self.repo / "swarm_output.txt").exists())

    def test_the_runners_own_writes_are_not_mistaken_for_an_escape(self) -> None:
        # The runner writes the context pack and the evidence directory into the
        # project root. Those are the runner's own artifacts, not an agent that
        # escaped its worktree.
        code, payload = self.isolate()
        self.assertEqual(code, 0, payload)
        codes = [f["code"] for f in payload["findings"]]
        self.assertNotIn("worktree_escape_detected", codes)

    def test_dry_run_changes_nothing(self) -> None:
        code, payload = self.isolate(extra=["--dry-run"])
        self.assertEqual(code, 0, payload)
        self.assertTrue(payload["dry_run"])
        self.assertFalse(payload["merged"]["merged"])
        branches = _git(self.repo, "branch", "--list")
        self.assertNotIn("daw/integration", branches)
        self.assertNotIn("daw/TASK-01", branches)

    def test_isolate_refuses_while_the_lock_is_held(self) -> None:
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import worktree

        path = worktree.lock_path(self.repo)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "pid": os.getpid(),
                    "start_time": worktree.process_start_time(os.getpid()),
                }
            ),
            encoding="utf-8",
        )
        code, payload = self.isolate()
        self.assertEqual(code, 2, payload)
        self.assertIn(
            "integration_locked", [finding["code"] for finding in payload["findings"]]
        )

    def test_the_worktree_container_must_be_ignored(self) -> None:
        (self.repo / ".gitignore").write_text("*.log\n", encoding="utf-8")
        _git(self.repo, "commit", "-aqm", "unignore")
        code, payload = self.isolate()
        self.assertEqual(code, 2)
        codes = [f["code"] for f in payload["findings"]]
        self.assertIn("worktree_root_not_ignored", codes)

    def test_add_ignore_uses_the_repository_local_exclude_file(self) -> None:
        (self.repo / ".gitignore").write_text("*.log\n", encoding="utf-8")
        _git(self.repo, "commit", "-aqm", "unignore")
        code, payload = self.isolate(extra=["--add-ignore"])
        self.assertEqual(code, 0, payload)
        self.assertEqual((self.repo / ".gitignore").read_text(encoding="utf-8"), "*.log\n")
        exclude = (self.repo / ".git" / "info" / "exclude").read_text(encoding="utf-8")
        self.assertIn(".worktrees/", exclude)


class SubstituteArgvTests(unittest.TestCase):
    def test_placeholders_are_substituted(self) -> None:
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run as runner_module

        resolved = runner_module.substitute_argv(
            ["agent", "-p", "{prompt_file}", "--task", "{task_id}", "--dir", "{workspace}"],
            {"{prompt_file}": "/tmp/p.md", "{workspace}": "/tmp/wt", "{task_id}": "TASK-01"},
        )
        self.assertEqual(
            resolved, ["agent", "-p", "/tmp/p.md", "--task", "TASK-01", "--dir", "/tmp/wt"]
        )

    def test_unrelated_braces_are_left_alone(self) -> None:
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run as runner_module

        resolved = runner_module.substitute_argv(
            ["agent", "{\"key\": \"value\"}"], {"{prompt_file}": "/tmp/p.md"}
        )
        self.assertEqual(resolved[1], "{\"key\": \"value\"}")


if __name__ == "__main__":
    unittest.main()
