#!/usr/bin/env python3
"""Tests for per-task worktree isolation.

The isolation tool is exercised against real git repositories in temporary
directories: the behaviour under test (branch naming, ignore checks, the
merge gate) only means something when git actually does it.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import worktree  # noqa: E402

GIT_AVAILABLE = shutil.which("git") is not None


def _git(repo: pathlib.Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return result.stdout.decode("utf-8", errors="replace")


class IsolationRepoBase(unittest.TestCase):
    """A temporary git repository with one committed file."""

    def setUp(self) -> None:
        if not GIT_AVAILABLE:
            self.skipTest("git is not available")
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.repo = pathlib.Path(self.temp_dir.name).resolve()
        _git(self.repo, "init", "-q", ".")
        _git(self.repo, "config", "user.email", "test@example.invalid")
        _git(self.repo, "config", "user.name", "Isolation Test")
        (self.repo / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        (self.repo / ".gitignore").write_text(".worktrees/\n__pycache__/\n", encoding="utf-8")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-qm", "init")

    def evidence(self, task_id: str, exit_code: int, branch: str | None = None, commit: str | None = None) -> pathlib.Path:
        directory = self.repo / "docs" / "evidence" / task_id
        directory.mkdir(parents=True, exist_ok=True)
        header = f"$ echo test\nexit_code: {exit_code}\n"
        if branch:
            header += f"branch: {branch}\n"
        if commit:
            header += f"commit: {commit}\n"
        path = directory / "verify-1.log"
        path.write_text(header + "\noutput\n", encoding="utf-8")
        return path


class NamingTests(unittest.TestCase):
    def test_branch_name_is_derived_from_task_id_and_title(self) -> None:
        self.assertEqual(
            worktree.branch_name_for("TASK-01", "Rotate token_version"),
            "daw/TASK-01-rotate-token-version",
        )

    def test_branch_name_is_deterministic(self) -> None:
        first = worktree.branch_name_for("TASK-07", "Add the cache")
        second = worktree.branch_name_for("TASK-07", "Add the cache")
        self.assertEqual(first, second)

    def test_branch_name_slugs_unsafe_characters(self) -> None:
        branch = worktree.branch_name_for("TASK/01", "Fix the  parser!!")
        self.assertNotIn(" ", branch)
        self.assertNotIn("/", branch.replace("daw/", "", 1))

    def test_worktree_path_is_inside_the_container(self) -> None:
        self.assertEqual(
            worktree.task_worktree_rel(".worktrees", "TASK-01"),
            ".worktrees/TASK-01",
        )
        self.assertEqual(
            worktree.integration_worktree_rel(".worktrees"),
            ".worktrees/_integration",
        )

    def test_protected_branches_are_recognized(self) -> None:
        for branch in ("main", "master", "release/1.2", "develop"):
            self.assertTrue(worktree.is_protected_branch(branch), branch)
        self.assertFalse(worktree.is_protected_branch("daw/TASK-01-thing"))


class PrepareTests(IsolationRepoBase):
    def test_prepare_creates_integration_and_task_worktrees(self) -> None:
        outcome = worktree.prepare_isolation(
            self.repo, ".worktrees", None, "TASK-01", "Rotate token"
        )
        self.assertEqual(outcome["integration"]["branch"], "daw/integration")
        self.assertEqual(outcome["task"]["branch"], "daw/TASK-01-rotate-token")
        self.assertTrue((self.repo / ".worktrees" / "TASK-01" / "app.py").is_file())

    def test_prepare_refuses_an_unignored_container(self) -> None:
        (self.repo / ".gitignore").write_text("*.log\n", encoding="utf-8")
        _git(self.repo, "commit", "-aqm", "unignore worktrees")
        with self.assertRaises(worktree.IsolationError) as caught:
            worktree.prepare_isolation(self.repo, ".worktrees", None, "TASK-01", "Rotate token")
        codes = [f["code"] for f in caught.exception.findings]
        self.assertIn("worktree_root_not_ignored", codes)

    def test_prepare_can_add_the_ignore_entry_to_the_exclude_file(self) -> None:
        (self.repo / ".gitignore").write_text("*.log\n", encoding="utf-8")
        _git(self.repo, "commit", "-aqm", "unignore worktrees")
        outcome = worktree.prepare_isolation(
            self.repo, ".worktrees", None, "TASK-01", "Rotate token", add_ignore=True
        )
        self.assertTrue(outcome["task"]["worktree_path"])
        # The project's own .gitignore is never rewritten.
        self.assertEqual((self.repo / ".gitignore").read_text(encoding="utf-8"), "*.log\n")
        exclude = (self.repo / ".git" / "info" / "exclude").read_text(encoding="utf-8")
        self.assertIn(".worktrees/", exclude)

    def test_prepare_is_idempotent(self) -> None:
        first = worktree.prepare_isolation(
            self.repo, ".worktrees", None, "TASK-01", "Rotate token"
        )
        second = worktree.prepare_isolation(
            self.repo, ".worktrees", None, "TASK-01", "Rotate token"
        )
        self.assertFalse(first["task"]["reused"])
        self.assertTrue(second["task"]["reused"])
        self.assertEqual(first["task"]["branch"], second["task"]["branch"])

    def test_task_worktree_is_based_on_the_integration_branch(self) -> None:
        outcome = worktree.prepare_isolation(
            self.repo, ".worktrees", None, "TASK-02", "Second task"
        )
        integration = worktree.branch_commit(self.repo, "daw/integration")
        self.assertEqual(outcome["task"]["base_ref"], integration)

    def test_a_deleted_worktree_is_recreated_not_refused(self) -> None:
        worktree.prepare_isolation(self.repo, ".worktrees", None, "TASK-01", "Rotate token")
        # Simulate an operator deleting the worktree directory by hand.
        shutil.rmtree(self.repo / ".worktrees")
        outcome = worktree.prepare_isolation(
            self.repo, ".worktrees", None, "TASK-01", "Rotate token"
        )
        self.assertTrue(outcome["integration"]["reused"])
        self.assertTrue(outcome["task"]["reused"])
        self.assertTrue((self.repo / ".worktrees" / "TASK-01" / "app.py").is_file())

    def test_a_deleted_worktree_keeps_the_existing_branch_content(self) -> None:
        worktree.prepare_isolation(self.repo, ".worktrees", None, "TASK-01", "Rotate token")
        (self.repo / ".worktrees" / "TASK-01" / "app.py").write_text("VALUE = 99\n", encoding="utf-8")
        worktree.commit_task_work(
            self.repo / ".worktrees" / "TASK-01", "TASK-01", "Rotate token"
        )
        shutil.rmtree(self.repo / ".worktrees")
        worktree.prepare_isolation(self.repo, ".worktrees", None, "TASK-01", "Rotate token")
        content = _git(self.repo, "show", "daw/TASK-01-rotate-token:app.py")
        self.assertIn("VALUE = 99", content)

    def test_dry_run_creates_nothing(self) -> None:
        outcome = worktree.prepare_isolation(
            self.repo, ".worktrees", None, "TASK-01", "Rotate token", dry_run=True
        )
        self.assertTrue(outcome["task"]["dry_run"])
        self.assertFalse((self.repo / ".worktrees").exists())
        self.assertNotIn("daw/integration", _git(self.repo, "branch", "--list"))


class CommitTests(IsolationRepoBase):
    def test_commit_records_the_task_in_the_message(self) -> None:
        worktree.prepare_isolation(self.repo, ".worktrees", None, "TASK-01", "Rotate token")
        task_worktree = self.repo / ".worktrees" / "TASK-01"
        (task_worktree / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
        outcome = worktree.commit_task_work(task_worktree, "TASK-01", "Rotate token")
        self.assertTrue(outcome["committed"])
        message = _git(task_worktree, "log", "-1", "--pretty=%s").strip()
        self.assertEqual(message, "task(TASK-01): Rotate token")

    def test_commit_is_a_noop_when_nothing_changed(self) -> None:
        worktree.prepare_isolation(self.repo, ".worktrees", None, "TASK-01", "Rotate token")
        outcome = worktree.commit_task_work(
            self.repo / ".worktrees" / "TASK-01", "TASK-01", "Rotate token"
        )
        self.assertFalse(outcome["committed"])
        self.assertEqual(outcome["reason"], "no changes in the worktree")


class MergeGateTests(IsolationRepoBase):
    def setUp(self) -> None:
        super().setUp()
        worktree.prepare_isolation(self.repo, ".worktrees", None, "TASK-01", "Rotate token")
        self.task_worktree = self.repo / ".worktrees" / "TASK-01"

    def test_merge_is_refused_without_evidence(self) -> None:
        with self.assertRaises(worktree.IsolationError):
            worktree.merge_task_branch(
                self.repo,
                ".worktrees/_integration",
                "daw/TASK-01-rotate-token",
                "TASK-01",
                "Rotate token",
            )

    def test_merge_gate_requires_green_evidence(self) -> None:
        self.evidence("TASK-01", exit_code=1, branch="daw/TASK-01-rotate-token")
        ok, reason = worktree.verification_supports_merge(
            worktree.latest_verification(self.repo, "TASK-01"),
            "daw/TASK-01-rotate-token",
            None,
        )
        self.assertFalse(ok)
        self.assertIn("not 0", reason)

    def test_merge_gate_rejects_evidence_from_another_branch(self) -> None:
        self.evidence("TASK-01", exit_code=0, branch="daw/some-other-task")
        ok, reason = worktree.verification_supports_merge(
            worktree.latest_verification(self.repo, "TASK-01"),
            "daw/TASK-01-rotate-token",
            None,
        )
        self.assertFalse(ok)
        self.assertIn("daw/some-other-task", reason)

    def test_merge_gate_rejects_stale_evidence(self) -> None:
        self.evidence("TASK-01", exit_code=0, branch="daw/TASK-01-rotate-token", commit="aaaa")
        ok, reason = worktree.verification_supports_merge(
            worktree.latest_verification(self.repo, "TASK-01"),
            "daw/TASK-01-rotate-token",
            "bbbb",
        )
        self.assertFalse(ok)
        self.assertIn("bbbb", reason)

    def test_merge_gate_accepts_green_evidence_at_the_current_commit(self) -> None:
        commit = worktree.branch_commit(self.repo, "daw/TASK-01-rotate-token")
        self.evidence(
            "TASK-01", exit_code=0, branch="daw/TASK-01-rotate-token", commit=commit
        )
        ok, _ = worktree.verification_supports_merge(
            worktree.latest_verification(self.repo, "TASK-01"),
            "daw/TASK-01-rotate-token",
            commit,
        )
        self.assertTrue(ok)

    def test_merge_refuses_a_protected_branch(self) -> None:
        with self.assertRaises(worktree.IsolationError) as caught:
            worktree.merge_task_branch(
                self.repo, ".worktrees/_integration", "main", "TASK-01", "Rotate token"
            )
        self.assertIn("protected", str(caught.exception))

    def test_merge_refuses_a_protected_target_branch(self) -> None:
        with self.assertRaises(worktree.IsolationError):
            worktree.merge_task_branch(
                self.repo,
                ".worktrees/_integration",
                "release/1.0",
                "TASK-01",
                "Rotate token",
            )

    def test_successful_merge_lands_the_work_in_the_integration_branch(self) -> None:
        (self.task_worktree / "app.py").write_text("VALUE = 42\n", encoding="utf-8")
        worktree.commit_task_work(self.task_worktree, "TASK-01", "Rotate token")
        commit = worktree.branch_commit(self.repo, "daw/TASK-01-rotate-token")
        self.evidence(
            "TASK-01", exit_code=0, branch="daw/TASK-01-rotate-token", commit=commit
        )
        outcome = worktree.merge_task_branch(
            self.repo,
            ".worktrees/_integration",
            "daw/TASK-01-rotate-token",
            "TASK-01",
            "Rotate token",
            project_root=self.repo,
            evidence=worktree.latest_verification(self.repo, "TASK-01"),
        )
        self.assertTrue(outcome["merged"])
        content = _git(self.repo, "show", "daw/integration:app.py")
        self.assertIn("VALUE = 42", content)


class StateTests(IsolationRepoBase):
    def test_state_records_what_was_prepared(self) -> None:
        state_path = self.repo / "docs" / "evidence" / "runner" / "isolation.json"
        state = worktree.load_state(state_path)
        worktree.save_state(state_path, state)
        self.assertTrue(state_path.is_file())
        self.assertEqual(state["schema_version"], worktree.STATE_SCHEMA_VERSION)

    def test_accepted_ids_reflect_merged_tasks(self) -> None:
        state = worktree.empty_state()
        state["tasks"]["TASK-01"] = {"merged": True}
        state["tasks"]["TASK-02"] = {"merged": False}
        self.assertEqual(worktree.accepted_task_ids(state), ["TASK-01"])

    def test_corrupt_state_falls_back_to_empty(self) -> None:
        state_path = self.repo / "state.json"
        state_path.write_text("{not json", encoding="utf-8")
        self.assertEqual(worktree.load_state(state_path), worktree.empty_state())


class CliTests(IsolationRepoBase):
    def run_cli(self, *args: str) -> tuple[int, dict]:
        proc = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "worktree.py"), *args],
            capture_output=True,
            text=True,
            check=False,
        )
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            payload = {"stdout": proc.stdout, "stderr": proc.stderr}
        return proc.returncode, payload

    def test_prepare_and_list_round_trip(self) -> None:
        code, payload = self.run_cli(
            "prepare",
            "--project-root",
            str(self.repo),
            "--task",
            "TASK-01",
            "--title",
            "Rotate token",
        )
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["task"]["branch"], "daw/TASK-01-rotate-token")

        code, payload = self.run_cli("list", "--project-root", str(self.repo))
        self.assertEqual(code, 0, payload)
        self.assertEqual([t["task_id"] for t in payload["tasks"]], ["TASK-01"])
        self.assertTrue(payload["tasks"][0]["present"])

    def test_merge_without_evidence_exits_with_code_two(self) -> None:
        self.run_cli(
            "prepare",
            "--project-root",
            str(self.repo),
            "--task",
            "TASK-01",
            "--title",
            "Rotate token",
        )
        code, payload = self.run_cli(
            "merge", "--project-root", str(self.repo), "--task", "TASK-01"
        )
        self.assertEqual(code, 2)
        codes = [f["code"] for f in payload.get("findings", [])]
        self.assertIn("merge_not_verified", codes)

    def test_outside_a_repository_is_refused(self) -> None:
        outside = pathlib.Path(self.temp_dir.name).resolve() / "not-a-repo"
        outside.mkdir()
        code, payload = self.run_cli("prepare", "--project-root", str(outside))
        self.assertEqual(code, 2)
        self.assertFalse(payload["valid"])


if __name__ == "__main__":
    unittest.main()
