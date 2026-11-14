#!/usr/bin/env python3
"""Behavior tests for `scripts/batch.py`.

Two sections: write-set disjointness and batch selection, and the composite
merge gate. The composite tests run against real git repositories — the gate
only means something when git actually merges the members and the record's
claims are checked against the history it produced.
"""

from __future__ import annotations

import hashlib
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

try:
    from scripts import batch
except ImportError:
    import batch  # type: ignore[import-not-found]

try:
    from scripts import worktree
except ImportError:
    import worktree  # type: ignore[import-not-found]

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


def _manifest(tasks: list[dict], workflow_id: str = "wf-test") -> dict:
    return {"schema_version": 1, "workflow_id": workflow_id, "tasks": tasks}


def _task(
    task_id: str,
    *,
    parallel_safe: bool = True,
    target_files: list[str] | None = None,
) -> dict:
    return {
        "task_id": task_id,
        "title": f"Task {task_id}",
        "autonomy": "afk",
        "depends_on": [],
        "parallel_safe": parallel_safe,
        "target_files": target_files or ["src/app.py"],
        "acceptance_criteria": ["behavior works"],
        "verification_command": "python3 -c \"print('ok')\"",
        "expected_outcome": "exit code 0",
    }


def _ready(manifest: dict) -> list[dict]:
    """The ready view the runner hands to the selector: id, depth, parallel_safe."""
    return [
        {
            "task_id": task["task_id"],
            "title": task["title"],
            "depth": 0,
            "parallel_safe": task["parallel_safe"],
            "verification_command": task["verification_command"],
        }
        for task in manifest["tasks"]
    ]


class PathOverlapTests(unittest.TestCase):
    def test_identical_paths_overlap(self) -> None:
        self.assertTrue(batch.paths_overlap("src/app.py", "src/app.py"))

    def test_directory_prefix_overlaps_the_file_inside_it(self) -> None:
        self.assertTrue(batch.paths_overlap("src/auth", "src/auth/x.py"))
        self.assertTrue(batch.paths_overlap("src/auth/x.py", "src/auth"))

    def test_sibling_prefix_is_not_an_overlap(self) -> None:
        self.assertFalse(batch.paths_overlap("src/auth", "src/authz/x.py"))
        self.assertFalse(batch.paths_overlap("src/app.py", "src/b.py"))

    def test_leading_dot_slash_and_trailing_slash_are_normalized(self) -> None:
        self.assertTrue(batch.paths_overlap("./src/app.py", "src/app.py"))
        self.assertTrue(batch.paths_overlap("src/auth/", "src/auth/x.py"))


class WriteSetTests(unittest.TestCase):
    def test_disjoint_sets(self) -> None:
        self.assertTrue(batch.write_sets_disjoint(["src/a.py"], ["src/b.py"]))

    def test_overlapping_sets(self) -> None:
        self.assertFalse(batch.write_sets_disjoint(["src/app.py"], ["src/app.py"]))

    def test_empty_set_is_disjoint(self) -> None:
        self.assertTrue(batch.write_sets_disjoint([], ["src/app.py"]))


class UndeclaredPathTests(unittest.TestCase):
    def test_covered_paths_are_not_reported(self) -> None:
        self.assertEqual(
            batch.undeclared_paths(["src/auth"], ["src/auth/x.py", "src/auth/y.py"]),
            [],
        )

    def test_uncovered_paths_are_reported(self) -> None:
        self.assertEqual(
            batch.undeclared_paths(["src/auth"], ["src/auth/x.py", "src/app.py"]),
            ["src/app.py"],
        )


class BatchSelectionTests(unittest.TestCase):
    def test_disjoint_tasks_share_one_batch(self) -> None:
        manifest = _manifest(
            [
                _task("T-1", target_files=["src/a.py"]),
                _task("T-2", target_files=["src/b.py"]),
            ]
        )
        groups, warnings = batch.select_batch_members(manifest, _ready(manifest))
        self.assertEqual(groups, [["T-1", "T-2"]])
        self.assertEqual(warnings, [])

    def test_overlapping_target_files_are_not_batched_together(self) -> None:
        manifest = _manifest(
            [
                _task("T-1", target_files=["src/app.py"]),
                _task("T-2", target_files=["src/app.py"]),
            ]
        )
        groups, warnings = batch.select_batch_members(manifest, _ready(manifest))
        self.assertEqual(groups, [["T-1"], ["T-2"]])
        codes = [w["code"] for w in warnings]
        self.assertIn("batch_write_set_overlap", codes)
        overlap = next(w for w in warnings if w["code"] == "batch_write_set_overlap")
        self.assertEqual(overlap["severity"], "warning")
        self.assertEqual(overlap["path"], "T-2")
        self.assertIn("T-1", overlap["message"])
        self.assertIn("src/app.py", overlap["message"])

    def test_a_directory_target_file_overlaps_a_file_inside_it(self) -> None:
        manifest = _manifest(
            [
                _task("T-1", target_files=["src/auth"]),
                _task("T-2", target_files=["src/auth/x.py"]),
            ]
        )
        groups, warnings = batch.select_batch_members(manifest, _ready(manifest))
        self.assertEqual(groups, [["T-1"], ["T-2"]])
        self.assertIn("batch_write_set_overlap", [w["code"] for w in warnings])

    def test_a_task_that_is_not_parallel_safe_runs_alone(self) -> None:
        manifest = _manifest(
            [
                _task("T-1", parallel_safe=False, target_files=["src/a.py"]),
                _task("T-2", parallel_safe=True, target_files=["src/b.py"]),
            ]
        )
        groups, _ = batch.select_batch_members(manifest, _ready(manifest))
        self.assertEqual(groups, [["T-1"], ["T-2"]])

    def test_max_concurrency_caps_a_group(self) -> None:
        manifest = _manifest(
            [
                _task("T-1", target_files=["src/a.py"]),
                _task("T-2", target_files=["src/b.py"]),
                _task("T-3", target_files=["src/c.py"]),
            ]
        )
        groups, _ = batch.select_batch_members(
            manifest, _ready(manifest), max_concurrency=2
        )
        self.assertEqual(groups, [["T-1", "T-2"], ["T-3"]])

    def test_max_tasks_is_applied_during_grouping(self) -> None:
        manifest = _manifest(
            [
                _task("T-1", target_files=["src/a.py"]),
                _task("T-2", target_files=["src/b.py"]),
                _task("T-3", target_files=["src/c.py"]),
            ]
        )
        groups, _ = batch.select_batch_members(
            manifest, _ready(manifest), max_tasks=2
        )
        total = sum(len(group) for group in groups)
        self.assertEqual(total, 2)
        self.assertEqual(groups, [["T-1", "T-2"]])

    def test_grouping_is_stable_across_manifest_order(self) -> None:
        tasks = [
            _task("T-1", target_files=["src/a.py"]),
            _task("T-2", target_files=["src/b.py"]),
            _task("T-3", target_files=["src/c.py"]),
        ]
        forward = _manifest(tasks)
        reversed_manifest = _manifest(list(reversed(tasks)))
        ready = _ready(forward)
        first, _ = batch.select_batch_members(forward, ready)
        second, _ = batch.select_batch_members(reversed_manifest, ready)
        self.assertEqual(first, second)

    def test_pinned_tasks_with_overlapping_writes_are_serialized(self) -> None:
        manifest = _manifest(
            [
                _task("T-1", target_files=["src/app.py"]),
                _task("T-2", target_files=["src/app.py"]),
                _task("T-3", target_files=["src/other.py"]),
            ]
        )
        groups, warnings = batch.select_batch_members(
            manifest, _ready(manifest), pinned=["T-1", "T-2"]
        )
        self.assertEqual(groups, [["T-1"], ["T-2"]])
        self.assertIn("batch_write_set_overlap", [w["code"] for w in warnings])

    def test_pinned_filter_drops_unpinned_ready_tasks(self) -> None:
        manifest = _manifest(
            [
                _task("T-1", target_files=["src/a.py"]),
                _task("T-2", target_files=["src/b.py"]),
            ]
        )
        groups, warnings = batch.select_batch_members(
            manifest, _ready(manifest), pinned=["T-2"]
        )
        self.assertEqual(groups, [["T-2"]])
        self.assertEqual(warnings, [])

    def test_the_plan_flag_cannot_talk_the_runner_into_a_conflict(self) -> None:
        """Two overlapping tasks both marked parallel_safe are still separated."""
        manifest = _manifest(
            [
                _task("T-1", parallel_safe=True, target_files=["src/app.py"]),
                _task("T-2", parallel_safe=True, target_files=["src/app.py"]),
            ]
        )
        groups, _ = batch.select_batch_members(manifest, _ready(manifest))
        self.assertEqual(groups, [["T-1"], ["T-2"]])

    def test_an_overlap_is_reported_even_when_the_candidate_joins_another_group(self) -> None:
        """The overlap is reported because it exists, not because of scan order."""
        manifest = _manifest(
            [
                _task("T-1", target_files=["src/a.py"]),
                _task("T-2", target_files=["src/a.py", "src/b.py"]),
                _task("T-3", target_files=["src/b.py"]),
            ]
        )
        # T-2 overlaps T-1, so it opens a second group. T-3 is disjoint from
        # T-1 and joins the first group, yet it overlaps T-2 in the second one:
        # the split is reported all the same.
        groups, warnings = batch.select_batch_members(manifest, _ready(manifest))
        self.assertEqual(groups, [["T-1", "T-3"], ["T-2"]])
        overlaps = {w["path"]: w["message"] for w in warnings if w["code"] == "batch_write_set_overlap"}
        self.assertIn("T-2", overlaps)
        self.assertIn("T-3", overlaps)
        self.assertIn("src/b.py", overlaps["T-3"])


class CompositeRepoBase(unittest.TestCase):
    """A temporary git repository with two divergent task branches."""

    def setUp(self) -> None:
        if not GIT_AVAILABLE:
            self.skipTest("git is not available")
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.repo = pathlib.Path(self.temp_dir.name).resolve()
        _git(self.repo, "init", "-q", ".")
        _git(self.repo, "config", "user.email", "test@example.invalid")
        _git(self.repo, "config", "user.name", "Batch Test")
        (self.repo / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        (self.repo / ".gitignore").write_text(".worktrees/\n__pycache__/\n", encoding="utf-8")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-qm", "init")
        self.base_commit = _git(self.repo, "rev-parse", "HEAD").strip()

        self.worktree_root = ".worktrees"
        self.members = [
            self._make_member("T-1", "a.py", "A = 1\n"),
            self._make_member("T-2", "b.py", "B = 1\n"),
        ]
        self.batch_id = batch.batch_id(self.base_commit, ["T-1", "T-2"])

    def _make_member(self, task_id: str, filename: str, content: str) -> dict:
        """Create a task branch off the base with one committed file."""
        branch = f"daw/{task_id}-work"
        _git(self.repo, "checkout", "-q", "-b", branch, self.base_commit)
        (self.repo / filename).write_text(content, encoding="utf-8")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-qm", f"task({task_id}): work")
        commit = _git(self.repo, "rev-parse", "HEAD").strip()
        _git(self.repo, "checkout", "-q", "-")
        return {
            "task_id": task_id,
            "title": f"Task {task_id}",
            "branch": branch,
            "commit": commit,
        }

    def _make_conflicting_member(self, task_id: str, content: str) -> dict:
        """Create a task branch off the base that edits the same line."""
        branch = f"daw/{task_id}-conflict"
        _git(self.repo, "checkout", "-q", "-b", branch, self.base_commit)
        (self.repo / "app.py").write_text(content, encoding="utf-8")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-qm", f"task({task_id}): work")
        commit = _git(self.repo, "rev-parse", "HEAD").strip()
        _git(self.repo, "checkout", "-q", "-")
        return {
            "task_id": task_id,
            "title": f"Task {task_id}",
            "branch": branch,
            "commit": commit,
        }

    # -- composite construction ------------------------------------------------

    def build(self) -> dict:
        """Build the composite and return its description."""
        return batch.build_composite(
            self.repo,
            self.worktree_root,
            self.base_commit,
            self.batch_id,
            self.members,
        )

    def make_record(self, composite: dict) -> dict:
        """Write one composite log per member and return the composite record."""
        project_root = self.repo
        evidence = project_root / "docs" / "daw" / "evidence" / self.batch_id
        evidence.mkdir(parents=True, exist_ok=True)
        members = []
        for index, member in enumerate(self.members, start=1):
            log_path = evidence / f"composite-{index}.log"
            log_path.write_text(
                self.log_header(exit_code=0, branch=composite["branch"], commit=composite["commit"])
                + "ok\n",
                encoding="utf-8",
            )
            members.append(
                {
                    "task_id": member["task_id"],
                    "branch": member["branch"],
                    "commit": member["commit"],
                    "command": "python3 -c 'pass'",
                    "exit_code": 0,
                    "log_path": log_path.relative_to(project_root).as_posix(),
                    "log_sha256": hashlib.sha256(log_path.read_bytes()).hexdigest(),
                }
            )
        return {
            "schema_version": batch.composite_record_schema_version,
            "batch_id": self.batch_id,
            "composite_branch": composite["branch"],
            "composite_commit": composite["commit"],
            "base_commit": self.base_commit,
            "members": members,
        }

    def log_header(self, *, exit_code: int, branch: str, commit: str) -> str:
        """The header `run.py`'s `run_verification` writes."""
        return (
            "$ python3 -c 'pass'\n"
            f"exit_code: {exit_code}\n"
            f"branch: {branch}\n"
            f"commit: {commit}\n"
            f"cwd: {self.repo}\n"
            "\n"
        )

    def write_record(self, record: dict) -> pathlib.Path:
        path = self.repo / "docs" / "daw" / "evidence" / self.batch_id / "composite-1.json"
        batch.write_composite_record(path, record)
        return path


class CompositeGateTests(CompositeRepoBase):
    def test_the_composite_holds_every_member(self) -> None:
        composite = self.build()
        self.assertEqual(composite["merged_task_ids"], ["T-1", "T-2"])
        self.assertEqual(composite["branch"], batch.composite_branch_name(self.batch_id))

        tree = _git(self.repo, "ls-tree", "--name-only", composite["commit"]).split()
        self.assertIn("a.py", tree)
        self.assertIn("b.py", tree)

        merges = _git(
            self.repo,
            "rev-list",
            "--merges",
            "--parents",
            composite["commit"],
            "--not",
            self.base_commit,
        ).strip().splitlines()
        self.assertEqual(len(merges), 2)
        for member in self.members:
            self.assertIn(member["commit"], merges[0] + " " + merges[1])

    def test_a_record_whose_commit_is_stale_is_refused(self) -> None:
        composite = self.build()
        record = self.make_record(composite)
        record["composite_commit"] = "0" * 40
        ok, reason = batch.validate_composite_record(
            self.repo, record, composite["commit"]
        )
        self.assertFalse(ok)
        self.assertIn("commit", reason)

    def test_a_record_missing_a_member_is_refused(self) -> None:
        composite = self.build()
        record = self.make_record(composite)
        missing = record["members"][1]["commit"]
        record["members"] = record["members"][:1]
        ok, reason = batch.validate_composite_record(
            self.repo, record, composite["commit"]
        )
        self.assertFalse(ok)
        self.assertIn(missing, reason)

    def test_a_record_with_a_non_zero_exit_code_is_refused(self) -> None:
        composite = self.build()
        record = self.make_record(composite)
        record["members"][0]["exit_code"] = 1
        ok, reason = batch.validate_composite_record(
            self.repo, record, composite["commit"]
        )
        self.assertFalse(ok)
        self.assertIn("exit", reason.lower())

    def test_an_edited_exit_code_is_caught_by_the_log_cross_check(self) -> None:
        composite = self.build()
        record = self.make_record(composite)
        log_path = self.repo / record["members"][0]["log_path"]
        log_path.write_text(
            self.log_header(exit_code=1, branch=composite["branch"], commit=composite["commit"])
            + "failed\n",
            encoding="utf-8",
        )
        record["members"][0]["log_sha256"] = hashlib.sha256(
            log_path.read_bytes()
        ).hexdigest()
        ok, reason = batch.validate_composite_record(
            self.repo, record, composite["commit"]
        )
        self.assertFalse(ok)
        self.assertIn("exit", reason.lower())

    def test_a_tampered_log_digest_is_refused(self) -> None:
        composite = self.build()
        record = self.make_record(composite)
        record["members"][0]["log_sha256"] = "0" * 64
        ok, reason = batch.validate_composite_record(
            self.repo, record, composite["commit"]
        )
        self.assertFalse(ok)
        self.assertIn("sha256", reason.lower())

    def test_a_log_missing_the_composite_commit_is_refused(self) -> None:
        composite = self.build()
        record = self.make_record(composite)
        log_path = self.repo / record["members"][0]["log_path"]
        log_path.write_text(
            self.log_header(exit_code=0, branch=composite["branch"], commit="0" * 40)
            + "ok\n",
            encoding="utf-8",
        )
        record["members"][0]["log_sha256"] = hashlib.sha256(
            log_path.read_bytes()
        ).hexdigest()
        ok, reason = batch.validate_composite_record(
            self.repo, record, composite["commit"]
        )
        self.assertFalse(ok)
        self.assertIn("commit", reason)

    def test_a_green_record_is_accepted(self) -> None:
        composite = self.build()
        record = self.make_record(composite)
        ok, reason = batch.validate_composite_record(
            self.repo, record, composite["commit"]
        )
        self.assertTrue(ok, reason)

    def test_a_member_with_no_commit_leaves_no_merge_commit(self) -> None:
        """A no-op member is not in the merged set, and the record must not list it."""
        no_op = {
            "task_id": "T-3",
            "title": "Task T-3",
            "branch": "daw/T-3-noop",
            "commit": self.base_commit,
        }
        _git(self.repo, "branch", "daw/T-3-noop", self.base_commit)
        composite = batch.build_composite(
            self.repo,
            self.worktree_root,
            self.base_commit,
            self.batch_id,
            self.members + [no_op],
        )
        self.assertEqual(composite["merged_task_ids"], ["T-1", "T-2"])

        merges = _git(
            self.repo,
            "rev-list",
            "--merges",
            "--parents",
            composite["commit"],
            "--not",
            self.base_commit,
        ).strip().splitlines()
        self.assertEqual(len(merges), 2)

    def test_the_composite_is_recreated_at_the_base_on_a_retry(self) -> None:
        """A failed attempt must not contaminate the next one."""
        first = self.build()
        self.assertEqual(first["merged_task_ids"], ["T-1", "T-2"])

        # A second attempt starts from the base again, not from the first
        # attempt's merges.
        second = batch.build_composite(
            self.repo,
            self.worktree_root,
            self.base_commit,
            self.batch_id,
            self.members,
        )
        merges = _git(
            self.repo,
            "rev-list",
            "--merges",
            "--parents",
            second["commit"],
            "--not",
            self.base_commit,
        ).strip().splitlines()
        self.assertEqual(len(merges), 2)

    def test_a_composite_left_behind_by_a_deleted_directory_is_recreated(self) -> None:
        """A stale worktree registration must not block the next attempt."""
        self.build()
        shutil.rmtree(self.repo / self.worktree_root / "_composite")
        composite = self.build()
        self.assertEqual(composite["merged_task_ids"], ["T-1", "T-2"])

    def test_merging_a_green_composite_lands_both_members(self) -> None:
        composite = self.build()
        record = self.make_record(composite)
        record_path = self.write_record(record)

        integration_rel = worktree.integration_worktree_rel(self.worktree_root)
        _git(self.repo, "worktree", "add", "-q", "-b", worktree.INTEGRATION_BRANCH, integration_rel, self.base_commit)

        outcome = batch.merge_composite_branch(
            self.repo,
            integration_rel,
            composite["branch"],
            self.batch_id,
            self.repo,
            record_path,
        )
        self.assertTrue(outcome["merged"])
        self.assertEqual(outcome["batch_id"], self.batch_id)
        self.assertEqual(outcome["composite_commit"], composite["commit"])

        tree = _git(self.repo, "ls-tree", "--name-only", worktree.INTEGRATION_BRANCH).split()
        self.assertIn("a.py", tree)
        self.assertIn("b.py", tree)

    def test_merging_a_composite_with_a_stale_record_is_refused(self) -> None:
        composite = self.build()
        record = self.make_record(composite)
        record["composite_commit"] = "0" * 40
        record_path = self.write_record(record)

        integration_rel = worktree.integration_worktree_rel(self.worktree_root)
        _git(self.repo, "worktree", "add", "-q", "-b", worktree.INTEGRATION_BRANCH, integration_rel, self.base_commit)

        with self.assertRaises(worktree.IsolationError) as caught:
            batch.merge_composite_branch(
                self.repo,
                integration_rel,
                composite["branch"],
                self.batch_id,
                self.repo,
                record_path,
            )
        self.assertIn(
            "merge_not_verified", [f["code"] for f in caught.exception.findings]
        )

    def test_merging_a_composite_with_a_missing_record_is_refused(self) -> None:
        composite = self.build()
        integration_rel = worktree.integration_worktree_rel(self.worktree_root)
        _git(self.repo, "worktree", "add", "-q", "-b", worktree.INTEGRATION_BRANCH, integration_rel, self.base_commit)

        missing = self.repo / "docs" / "daw" / "evidence" / self.batch_id / "composite-1.json"
        with self.assertRaises(worktree.IsolationError) as caught:
            batch.merge_composite_branch(
                self.repo,
                integration_rel,
                composite["branch"],
                self.batch_id,
                self.repo,
                missing,
            )
        self.assertIn(
            "merge_not_verified", [f["code"] for f in caught.exception.findings]
        )

    def test_a_conflicting_member_fails_the_build(self) -> None:
        members = [
            self._make_conflicting_member("T-1", "VALUE = 2\n"),
            self._make_conflicting_member("T-2", "VALUE = 3\n"),
        ]
        with self.assertRaises(worktree.IsolationError) as caught:
            batch.build_composite(
                self.repo,
                self.worktree_root,
                self.base_commit,
                self.batch_id,
                members,
            )
        self.assertIn(
            "batch_merge_conflict", [f["code"] for f in caught.exception.findings]
        )
        # The composite holds no partial merge of the conflicting member.
        composite_branch = batch.composite_branch_name(self.batch_id)
        merges = _git(
            self.repo,
            "rev-list",
            "--merges",
            "--parents",
            composite_branch,
            "--not",
            self.base_commit,
        ).strip()
        self.assertEqual(merges, "")


if __name__ == "__main__":
    unittest.main()
