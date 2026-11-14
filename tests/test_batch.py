#!/usr/bin/env python3
"""Behavior tests for `scripts/batch.py` and the runner's `batch` verb.

Three sections: write-set disjointness and batch selection, the composite
merge gate, and the batch execution itself. The last two run against real git
repositories — the gate only means something when git actually merges the
members and the record's claims are checked against the history it produced,
and the batch only means something when git actually merges the composite.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNNER = PROJECT_ROOT / "scripts" / "run.py"
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
        # The gate derives the composite's base from the integration branch, so
        # it must exist before a record can be validated.
        self.integration_rel = worktree.integration_worktree_rel(self.worktree_root)
        _git(
            self.repo,
            "worktree",
            "add",
            "-q",
            "-b",
            worktree.INTEGRATION_BRANCH,
            self.integration_rel,
            self.base_commit,
        )

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

        outcome = batch.merge_composite_branch(
            self.repo,
            self.integration_rel,
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

        with self.assertRaises(worktree.IsolationError) as caught:
            batch.merge_composite_branch(
                self.repo,
                self.integration_rel,
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

        missing = self.repo / "docs" / "daw" / "evidence" / self.batch_id / "composite-1.json"
        with self.assertRaises(worktree.IsolationError) as caught:
            batch.merge_composite_branch(
                self.repo,
                self.integration_rel,
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


class CompositeGateHardeningTests(CompositeRepoBase):
    """Regressions for the review findings on the composite merge gate."""

    # -- Critical: the merge-history bound may not come from the record -------

    def test_a_tampered_base_commit_cannot_hide_a_merged_member(self) -> None:
        """A one-field edit of the record must not turn a red composite green.

        The composite holds two merged members. The record lists only the green
        one and points ``base_commit`` at the merge commit of the red member,
        which hides that member from ``git rev-list --merges --parents
        <composite> --not <bound>``.
        """
        composite = self.build()
        record = self.make_record(composite)

        # The merge commit of T-1 (the older merge): using it as the bound
        # hides T-1's merge and T-1's commit from the reconstruction.
        merges = _git(
            self.repo,
            "rev-list",
            "--merges",
            "--parents",
            composite["commit"],
            "--not",
            self.base_commit,
        ).strip().splitlines()
        red_merge = merges[1].split()[0]
        self.assertNotEqual(red_merge, self.base_commit)

        red_member = self.members[0]
        green_member = self.members[1]

        # The record keeps only the green member and claims the tampered bound.
        record["base_commit"] = red_merge
        record["members"] = [
            member
            for member in record["members"]
            if member["task_id"] == green_member["task_id"]
        ]
        self.assertNotIn(
            red_member["task_id"], [m["task_id"] for m in record["members"]]
        )

        ok, reason = batch.validate_composite_record(
            self.repo, record, composite["commit"], composite["branch"]
        )
        self.assertFalse(ok, "the tampered bound must not validate")
        self.assertIn("base commit", reason)

    def test_a_record_whose_base_commit_disagrees_with_the_derived_base_is_refused(
        self,
    ) -> None:
        composite = self.build()
        record = self.make_record(composite)
        record["base_commit"] = "0" * 40
        ok, reason = batch.validate_composite_record(
            self.repo, record, composite["commit"], composite["branch"]
        )
        self.assertFalse(ok)
        self.assertIn("base", reason.lower())

    def test_the_base_is_derived_and_stays_stable_when_the_integration_moves(
        self,
    ) -> None:
        """The derived base does not follow the integration branch forward."""
        composite = self.build()
        derived = batch.derive_base_commit(self.repo, composite["commit"])
        self.assertEqual(derived, self.base_commit)

        integration = self.repo / self.integration_rel
        (integration / "c.py").write_text("C = 1\n", encoding="utf-8")
        _git(integration, "add", "-A")
        _git(integration, "commit", "-qm", "another task")

        self.assertEqual(
            batch.derive_base_commit(self.repo, composite["commit"]), self.base_commit
        )
        # The reconstruction still sees both members.
        merged = batch._merged_member_commits(self.repo, composite["commit"], derived)
        self.assertEqual(merged, {member["commit"] for member in self.members})

    def test_a_missing_integration_branch_fails_closed(self) -> None:
        """Without the integration branch the base cannot be derived."""
        composite = self.build()
        record = self.make_record(composite)
        _git(self.repo, "worktree", "remove", "--force", self.integration_rel)
        _git(self.repo, "branch", "-D", worktree.INTEGRATION_BRANCH)

        with self.assertRaises(worktree.IsolationError) as caught:
            batch.validate_composite_record(
                self.repo, record, composite["commit"], composite["branch"]
            )
        self.assertIn(
            "merge_not_verified", [f["code"] for f in caught.exception.findings]
        )

    # -- Important: the record is checked against the merge's own arguments ---

    def test_a_record_naming_another_branch_is_refused(self) -> None:
        """The record is checked against the branch the merge is actually for.

        The log header is edited too, so the record and its logs agree with
        each other about the wrong branch. Only a comparison against the
        merge's own argument catches that.
        """
        composite = self.build()
        record = self.make_record(composite)
        record["composite_branch"] = "TOTALLY-DIFFERENT-BRANCH"
        for member in record["members"]:
            log_path = self.repo / member["log_path"]
            log_path.write_text(
                self.log_header(
                    exit_code=0,
                    branch="TOTALLY-DIFFERENT-BRANCH",
                    commit=composite["commit"],
                )
                + "ok\n",
                encoding="utf-8",
            )
            member["log_sha256"] = hashlib.sha256(log_path.read_bytes()).hexdigest()
        record_path = self.write_record(record)

        with self.assertRaises(worktree.IsolationError) as caught:
            batch.merge_composite_branch(
                self.repo,
                self.integration_rel,
                composite["branch"],
                self.batch_id,
                self.repo,
                record_path,
            )
        self.assertIn(
            "merge_not_verified", [f["code"] for f in caught.exception.findings]
        )
        # The refusal must name the branch mismatch, not something else.
        self.assertIn("TOTALLY-DIFFERENT-BRANCH", str(caught.exception))
        self.assertIn("branch", str(caught.exception))

    def test_a_record_naming_another_batch_is_refused(self) -> None:
        composite = self.build()
        record = self.make_record(composite)
        record["batch_id"] = "batch-0000000000"
        record_path = self.write_record(record)

        with self.assertRaises(worktree.IsolationError) as caught:
            batch.merge_composite_branch(
                self.repo,
                self.integration_rel,
                composite["branch"],
                self.batch_id,
                self.repo,
                record_path,
            )
        self.assertIn(
            "merge_not_verified", [f["code"] for f in caught.exception.findings]
        )
        self.assertIn("batch-0000000000", str(caught.exception))

    def test_a_log_naming_another_branch_is_refused(self) -> None:
        """The log header is checked against the branch being merged."""
        composite = self.build()
        record = self.make_record(composite)
        log_path = self.repo / record["members"][0]["log_path"]
        log_path.write_text(
            self.log_header(
                exit_code=0, branch="SOME-OTHER-BRANCH", commit=composite["commit"]
            )
            + "ok\n",
            encoding="utf-8",
        )
        record["members"][0]["log_sha256"] = hashlib.sha256(
            log_path.read_bytes()
        ).hexdigest()
        ok, reason = batch.validate_composite_record(
            self.repo, record, composite["commit"], composite["branch"]
        )
        self.assertFalse(ok)
        self.assertIn("SOME-OTHER-BRANCH", reason)

    # -- Important: a protected branch is never merged ------------------------

    def test_merging_a_protected_composite_branch_is_refused(self) -> None:
        composite = self.build()
        record = self.make_record(composite)
        record["composite_branch"] = "main"
        record_path = self.write_record(record)

        with self.assertRaises(worktree.IsolationError) as caught:
            batch.merge_composite_branch(
                self.repo,
                self.integration_rel,
                "main",
                self.batch_id,
                self.repo,
                record_path,
            )
        self.assertIn(
            "merge_not_verified", [f["code"] for f in caught.exception.findings]
        )
        # The refusal must be the protected-branch one.
        self.assertIn("protected", str(caught.exception).lower())

    # -- Minor: findings, removal failures, and the log's directory ------------

    def test_a_merge_history_read_failure_carries_a_finding(self) -> None:
        """A failure to read the merge history is a refusal with a finding."""
        composite = self.build()
        record = self.make_record(composite)

        original = batch.run_git

        def failing(args, repo, timeout=120):
            if args[:2] == ["rev-list", "--merges"]:
                return 1, "", "boom"
            return original(args, repo, timeout)

        batch.run_git = failing
        self.addCleanup(setattr, batch, "run_git", original)

        with self.assertRaises(worktree.IsolationError) as caught:
            batch.validate_composite_record(
                self.repo, record, composite["commit"], composite["branch"]
            )
        self.assertIn(
            "merge_not_verified", [f["code"] for f in caught.exception.findings]
        )

    def test_an_unreadable_merge_history_refuses_the_merge(self) -> None:
        """The gate refuses the merge when the merge history cannot be read."""
        composite = self.build()
        record = self.make_record(composite)
        record_path = self.write_record(record)

        original = batch.run_git

        def failing(args, repo, timeout=120):
            if args[:2] == ["rev-list", "--merges"]:
                return 1, "", "boom"
            return original(args, repo, timeout)

        batch.run_git = failing
        self.addCleanup(setattr, batch, "run_git", original)

        with self.assertRaises(worktree.IsolationError) as caught:
            batch.merge_composite_branch(
                self.repo,
                self.integration_rel,
                composite["branch"],
                self.batch_id,
                self.repo,
                record_path,
            )
        self.assertIn(
            "merge_not_verified", [f["code"] for f in caught.exception.findings]
        )
        # Nothing was merged.
        tree = _git(self.repo, "ls-tree", "--name-only", worktree.INTEGRATION_BRANCH).split()
        self.assertNotIn("a.py", tree)

    def test_a_log_outside_the_evidence_directory_is_refused(self) -> None:
        """A record may not point the gate at an arbitrary file in the repo."""
        composite = self.build()
        record = self.make_record(composite)

        stray = self.repo / "docs" / "daw" / "evidence" / "stray.log"
        stray.write_text(
            self.log_header(
                exit_code=0, branch=composite["branch"], commit=composite["commit"]
            )
            + "ok\n",
            encoding="utf-8",
        )
        record["members"][0]["log_path"] = stray.relative_to(self.repo).as_posix()
        record["members"][0]["log_sha256"] = hashlib.sha256(
            stray.read_bytes()
        ).hexdigest()

        ok, reason = batch.validate_composite_record(
            self.repo, record, composite["commit"], composite["branch"]
        )
        self.assertFalse(ok)
        self.assertIn("evidence directory", reason)

    def test_a_failing_composite_removal_surfaces_the_error(self) -> None:
        """A worktree that cannot be removed is reported, not swallowed."""
        composite = self.build()
        original = batch.run_git

        def failing(args, repo, timeout=120):
            if args[:2] == ["worktree", "remove"]:
                return 1, "", "cannot remove"
            return original(args, repo, timeout)

        batch.run_git = failing
        self.addCleanup(setattr, batch, "run_git", original)

        with self.assertRaises(worktree.IsolationError) as caught:
            batch.build_composite(
                self.repo,
                self.worktree_root,
                self.base_commit,
                self.batch_id,
                self.members,
            )
        self.assertIn(
            "merge_not_verified", [f["code"] for f in caught.exception.findings]
        )


# --------------------------------------------------------------------------
# The `batch` verb
# --------------------------------------------------------------------------

BATCH_PLAN_TEMPLATE = """# Plan: batch test

<!-- daw-task-manifest -->
```json
{
  "schema_version": 1,
  "workflow_id": "wf-batch",
  "tasks": [
    {
      "task_id": "TASK-ALPHA",
      "title": "Alpha change",
      "autonomy": "afk",
      "depends_on": [],
      "parallel_safe": true,
      "target_files": ["src/alpha.py"],
      "acceptance_criteria": ["alpha is green"],
      "verification_command": "python3 -c \\"import src.alpha; assert src.alpha.VALUE == 2\\"",
      "expected_outcome": "0 exit code"
    },
    {
      "task_id": "TASK-BETA",
      "title": "Beta change",
      "autonomy": "afk",
      "depends_on": [],
      "parallel_safe": true,
      "target_files": ["src/beta.py"],
      "acceptance_criteria": ["beta is green"],
      "verification_command": "python3 -c \\"import src.beta; assert src.beta.VALUE == 2\\"",
      "expected_outcome": "0 exit code"
    }
  ]
}
```
"""

#: A plan whose two tasks declare the same write set, so the runner must
#: serialize them into separate batches.
OVERLAPPING_PLAN_TEMPLATE = BATCH_PLAN_TEMPLATE.replace(
    '"target_files": ["src/beta.py"]', '"target_files": ["src/alpha.py"]'
)

#: Disjoint declarations let these tasks run together; both edit different
#: lines of an undeclared shared file so the composite can be verified.
BREAKING_PLAN_TEMPLATE = """# Plan: batch test

<!-- daw-task-manifest -->
```json
{
  "schema_version": 1,
  "workflow_id": "wf-batch",
  "tasks": [
    {
      "task_id": "TASK-ALPHA",
      "title": "Alpha change",
      "autonomy": "afk",
      "depends_on": [],
      "parallel_safe": true,
      "target_files": ["src/alpha.py"],
      "acceptance_criteria": ["alpha is green"],
      "verification_command": "python3 -c \\"import src.shared; assert src.shared.A == 2 and src.shared.B == 1\\"",
      "expected_outcome": "0 exit code"
    },
    {
      "task_id": "TASK-BETA",
      "title": "Beta change",
      "autonomy": "afk",
      "depends_on": [],
      "parallel_safe": true,
      "target_files": ["src/beta.py"],
      "acceptance_criteria": ["beta is green"],
      "verification_command": "python3 -c \\"import src.shared; assert src.shared.A == 1 and src.shared.B == 2\\"",
      "expected_outcome": "0 exit code"
    }
  ]
}
```
"""

#: Both members verify independently, but their commits edit the same line.
CONFLICT_PLAN_TEMPLATE = BREAKING_PLAN_TEMPLATE.replace(
    'assert src.shared.A == 1 and src.shared.B == 2',
    'assert src.shared.A == 8 and src.shared.B == 1',
)


class BatchRepoBase(unittest.TestCase):
    """A repository with two disjoint source files and the runner's plan."""

    plan_template = BATCH_PLAN_TEMPLATE

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
        _git(self.repo, "config", "user.name", "Batch Test")
        (self.repo / ".gitignore").write_text(
            ".worktrees/\n__pycache__/\n", encoding="utf-8"
        )
        source = self.repo / "src"
        source.mkdir()
        (source / "__init__.py").write_text("", encoding="utf-8")
        (source / "alpha.py").write_text("VALUE = 1\n", encoding="utf-8")
        (source / "beta.py").write_text("VALUE = 1\n", encoding="utf-8")
        (source / "gamma.py").write_text("VALUE = 1\n", encoding="utf-8")
        (source / "shared.py").write_text(
            "A = 1\n# -\n# -\n# -\n# -\nB = 1\n", encoding="utf-8"
        )
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-qm", "init")

        self.plan = self.repo / "docs" / "plans" / "wf.md"
        self.plan.parent.mkdir(parents=True)
        self.plan.write_text(self.plan_template, encoding="utf-8")

        self.worktree_root = ".worktrees"

    # -- agents -----------------------------------------------------------

    def agent(self, name: str, body: str) -> pathlib.Path:
        """Write an executable agent script and return its path."""
        path = self.root / name
        path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        path.chmod(0o755)
        return path

    def writing_agent(self, task_id: str, relative: str, content: str) -> pathlib.Path:
        """An agent that writes ``content`` into ``relative`` in its own cwd."""
        return self.agent(
            f"agent-{task_id}.sh",
            f"printf '%s\\n' '{content}' > {relative}\n"
            f"echo '{task_id}' > ran-{task_id}.txt\nexit 0",
        )

    def run_batch(
        self,
        agents: dict[str, pathlib.Path] | pathlib.Path | None = None,
        extra: list[str] | None = None,
    ) -> tuple[int, dict]:
        """Drive ``run.py batch`` and return (exit code, envelope)."""
        if isinstance(agents, pathlib.Path):
            agent_command = json.dumps([str(agents), "{prompt_file}"])
        elif agents is None:
            agent_command = json.dumps(["/nonexistent/agent", "{prompt_file}"])
        else:
            # One command per task, selected by the runner through the
            # {task_id} substitution.
            agent_command = json.dumps(
                [str(self.root / "agent.sh"), "{prompt_file}", "{task_id}"]
            )
        argv = [
            sys.executable,
            str(RUNNER),
            "batch",
            "--plan",
            str(self.plan),
            "--project-root",
            str(self.repo),
            "--agent-command",
            agent_command,
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

    # -- assertions -------------------------------------------------------

    def integration_tree(self) -> str:
        """The integration branch's tree listing, or "" when it has none."""
        branches = _git(self.repo, "branch", "--list")
        if worktree.INTEGRATION_BRANCH not in branches:
            return ""
        return _git(self.repo, "ls-tree", "-r", "--name-only", worktree.INTEGRATION_BRANCH)

    def integration_content(self, relative: str) -> str:
        return _git(self.repo, "show", f"{worktree.INTEGRATION_BRANCH}:{relative}")

    def assert_integration_unchanged(self, commit: str) -> None:
        self.assertEqual(
            _git(self.repo, "rev-parse", worktree.INTEGRATION_BRANCH).strip(), commit
        )

    def findings(self, payload: dict) -> list[str]:
        return [f["code"] for f in payload.get("findings", [])]

    def batch_entry(self, payload: dict) -> dict:
        batches = payload.get("batches") or []
        self.assertTrue(batches, payload)
        return batches[0]


class BatchExecutionTests(BatchRepoBase):
    """The `batch` verb, driven through the CLI against a real repository."""

    def test_two_disjoint_tasks_are_batched_and_integrated_as_one_composite(self) -> None:
        alpha = self.writing_agent("TASK-ALPHA", "src/alpha.py", "VALUE = 2")
        beta = self.writing_agent("TASK-BETA", "src/beta.py", "VALUE = 2")
        self.agent(
            "agent.sh",
            f"if [ \"$2\" = 'TASK-ALPHA' ]; then exec {alpha}; fi\nexec {beta}",
        )
        code, payload = self.run_batch(agents="per-task")
        self.assertEqual(code, 0, payload)

        entry = self.batch_entry(payload)
        self.assertEqual(entry["members"], ["TASK-ALPHA", "TASK-BETA"])
        self.assertEqual(entry["size"], 2)
        self.assertTrue(entry["integrated"])
        self.assertTrue(entry["composite_branch"])
        self.assertTrue(entry["composite_commit"])

        branches = _git(self.repo, "branch", "--list")
        self.assertIn(entry["composite_branch"], branches)
        self.assertIn("VALUE = 2", self.integration_content("src/alpha.py"))
        self.assertIn("VALUE = 2", self.integration_content("src/beta.py"))

    def test_each_member_runs_in_its_own_worktree(self) -> None:
        alpha = self.writing_agent("TASK-ALPHA", "src/alpha.py", "VALUE = 2")
        beta = self.writing_agent("TASK-BETA", "src/beta.py", "VALUE = 2")
        self.agent(
            "agent.sh",
            f"if [ \"$2\" = 'TASK-ALPHA' ]; then exec {alpha}; fi\nexec {beta}",
        )
        code, payload = self.run_batch(agents="per-task")
        self.assertEqual(code, 0, payload)

        container = self.repo / self.worktree_root
        markers = [
            container / task_id / f"ran-{task_id}.txt"
            for task_id in ("TASK-ALPHA", "TASK-BETA")
        ]
        self.assertTrue(all(marker.is_file() for marker in markers), markers)
        # Composite and integration verification also run in worktrees; only
        # the task-named worktrees prove where each agent ran.
        parents = {marker.parent for marker in markers}
        self.assertEqual(len(parents), 2, parents)
        for task_id in ("TASK-ALPHA", "TASK-BETA"):
            self.assertFalse(
                (self.repo / f"ran-{task_id}.txt").exists(),
                "the agent must not write into the main tree",
            )

    def test_the_broken_combination_is_refused_and_the_integration_branch_is_untouched(
        self,
    ) -> None:
        self.plan.write_text(BREAKING_PLAN_TEMPLATE, encoding="utf-8")
        alpha = self.writing_agent(
            "TASK-ALPHA", "src/shared.py", "A = 2\n# -\n# -\n# -\n# -\nB = 1"
        )
        beta = self.writing_agent(
            "TASK-BETA", "src/shared.py", "A = 1\n# -\n# -\n# -\n# -\nB = 2"
        )
        self.agent(
            "agent.sh",
            f"if [ \"$2\" = 'TASK-ALPHA' ]; then exec {alpha}; fi\nexec {beta}",
        )
        before = _git(self.repo, "rev-parse", "HEAD").strip()
        code, payload = self.run_batch(agents="per-task")
        self.assertEqual(code, 1, payload)
        self.assertIn("batch_composite_verification_failed", self.findings(payload))

        self.assert_integration_unchanged(before)
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").strip(), before)
        state = worktree.load_state(worktree.resolve_state_path(self.repo, None))
        for task_id in ("TASK-ALPHA", "TASK-BETA"):
            marker = worktree.batch_failure_marker(state, task_id)
            self.assertIsNotNone(marker, task_id)
            assert marker is not None
            self.assertEqual(marker["member_exit_code"], 0)
            self.assertNotEqual(marker["composite_exit_code"], 0)
            self.assertTrue(marker["composite_record_path"])
            self.assertTrue(marker["composite_record_sha256"])

    def test_a_red_member_is_excluded_and_its_sibling_still_integrates(self) -> None:
        alpha = self.writing_agent("TASK-ALPHA", "src/alpha.py", "VALUE = 2")
        failing = self.agent("agent-fail.sh", "exit 1")
        self.agent(
            "agent.sh",
            f"if [ \"$2\" = 'TASK-ALPHA' ]; then exec {alpha}; fi\nexec {failing}",
        )
        code, payload = self.run_batch(agents="per-task")
        self.assertEqual(code, 1, payload)
        self.assertIn("batch_task_agent_failed", self.findings(payload))

        self.assertIn("TASK-BETA", payload.get("failed", []))
        self.assertNotIn("TASK-BETA", payload.get("accepted", []))
        # The healthy sibling, alpha, still integrated; beta was excluded.
        self.assertIn("TASK-ALPHA", payload.get("accepted", []))
        self.assertIn("VALUE = 2", self.integration_content("src/alpha.py"))
        self.assertIn("VALUE = 1", self.integration_content("src/beta.py"))

    def test_a_no_op_member_is_accepted_and_does_not_fail_the_batch(self) -> None:
        # Two green members (alpha, gamma) force a composite so we can verify
        # that the no-op member (beta) left no merge commit in its history.
        manifest_data = json.loads(
            BATCH_PLAN_TEMPLATE.split("```json\n", 1)[1].split("\n```", 1)[0]
        )
        manifest_data["tasks"][1]["verification_command"] = (
            'python3 -c "import src.beta; assert src.beta.VALUE == 1"'
        )
        manifest_data["tasks"].append(
            {
                "task_id": "TASK-GAMMA",
                "title": "Gamma change",
                "autonomy": "afk",
                "depends_on": [],
                "parallel_safe": True,
                "target_files": ["src/gamma.py"],
                "acceptance_criteria": ["gamma is green"],
                "verification_command": 'python3 -c "import src.gamma; assert src.gamma.VALUE == 2"',
                "expected_outcome": "0 exit code",
            }
        )
        self.plan.write_text(
            f"# Plan: batch test\n\n<!-- daw-task-manifest -->\n```json\n{json.dumps(manifest_data, indent=2)}\n```\n",
            encoding="utf-8",
        )
        alpha = self.writing_agent("TASK-ALPHA", "src/alpha.py", "VALUE = 2")
        noop = self.agent("agent-noop.sh", "exit 0")
        gamma = self.writing_agent("TASK-GAMMA", "src/gamma.py", "VALUE = 2")
        self.agent(
            "agent.sh",
            f"if [ \"$2\" = 'TASK-ALPHA' ]; then exec {alpha}; fi\n"
            f"if [ \"$2\" = 'TASK-BETA' ]; then exec {noop}; fi\n"
            f"exec {gamma}",
        )
        code, payload = self.run_batch(agents="per-task")
        self.assertEqual(code, 0, payload)
        self.assertIn("TASK-BETA", payload.get("accepted", []))
        self.assertEqual(payload.get("failed", []), [])

        # Only the two green members left merge commits in the composite's
        # history; the no-op member left none.
        entry = self.batch_entry(payload)
        merges = _git(
            self.repo,
            "rev-list",
            "--merges",
            "--parents",
            entry["composite_commit"],
            "--not",
            entry["base_commit"],
        ).strip().splitlines()
        self.assertEqual(len(merges), 2, merges)

    def test_a_conflicting_member_fails_the_batch_with_the_integration_untouched(
        self,
    ) -> None:
        self.plan.write_text(CONFLICT_PLAN_TEMPLATE, encoding="utf-8")
        alpha = self.writing_agent(
            "TASK-ALPHA", "src/shared.py", "A = 2\n# -\n# -\n# -\n# -\nB = 1"
        )
        beta = self.writing_agent(
            "TASK-BETA", "src/shared.py", "A = 8\n# -\n# -\n# -\n# -\nB = 1"
        )
        self.agent(
            "agent.sh",
            f"if [ \"$2\" = 'TASK-ALPHA' ]; then exec {alpha}; fi\nexec {beta}",
        )
        code, payload = self.run_batch(agents="per-task")
        self.assertEqual(code, 1, payload)
        self.assertIn("batch_merge_conflict", self.findings(payload))
        base = _git(self.repo, "rev-parse", "HEAD").strip()
        self.assert_integration_unchanged(base)
        state = worktree.load_state(worktree.resolve_state_path(self.repo, None))
        for task_id in ("TASK-ALPHA", "TASK-BETA"):
            marker = worktree.batch_failure_marker(state, task_id)
            self.assertIsNotNone(marker, task_id)

    def test_overlapping_declared_writes_are_serialized_and_reported(self) -> None:
        self.plan.write_text(OVERLAPPING_PLAN_TEMPLATE, encoding="utf-8")
        alpha = self.writing_agent("TASK-ALPHA", "src/alpha.py", "VALUE = 2")
        beta = self.writing_agent("TASK-BETA", "src/beta.py", "VALUE = 2")
        self.agent(
            "agent.sh",
            f"if [ \"$2\" = 'TASK-ALPHA' ]; then exec {alpha}; fi\nexec {beta}",
        )
        code, payload = self.run_batch(agents="per-task")
        self.assertEqual(code, 0, payload)
        self.assertIn("batch_write_set_overlap", self.findings(payload))
        # Two separate batches, one member each.
        self.assertEqual(len(payload["batches"]), 2, payload)
        for entry in payload["batches"]:
            self.assertEqual(entry["size"], 1, entry)

    def test_a_pinned_task_that_is_not_ready_is_refused(self) -> None:
        alpha = self.writing_agent("TASK-ALPHA", "src/alpha.py", "VALUE = 2")
        beta = self.writing_agent("TASK-BETA", "src/beta.py", "VALUE = 2")
        self.agent(
            "agent.sh",
            f"if [ \"$2\" = 'TASK-ALPHA' ]; then exec {alpha}; fi\nexec {beta}",
        )
        code, payload = self.run_batch(
            agents="per-task", extra=["--tasks", "TASK-NOT-READY"]
        )
        self.assertEqual(code, 2, payload)
        self.assertIn("batch_task_not_ready", self.findings(payload))

    def test_a_stale_task_branch_is_refused(self) -> None:
        # Keep the untracked plan out of the stale-branch commit; switching back
        # to the base branch would otherwise remove it from the working tree.
        _git(self.repo, "add", "docs/plans/wf.md")
        _git(self.repo, "commit", "-qm", "add batch plan")
        # Pre-create the task's branch with a commit: its tip is no longer the
        # batch's base, so the member's prior work is at risk.
        _git(self.repo, "checkout", "-q", "-b", "daw/TASK-ALPHA-alpha-change")
        (self.repo / "src" / "alpha.py").write_text("VALUE = 99\n", encoding="utf-8")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-qm", "prior attempt")
        tip = _git(self.repo, "rev-parse", "HEAD").strip()
        _git(self.repo, "checkout", "-q", "-")

        alpha = self.writing_agent("TASK-ALPHA", "src/alpha.py", "VALUE = 2")
        beta = self.writing_agent("TASK-BETA", "src/beta.py", "VALUE = 2")
        self.agent(
            "agent.sh",
            f"if [ \"$2\" = 'TASK-ALPHA' ]; then exec {alpha}; fi\nexec {beta}",
        )
        code, payload = self.run_batch(agents="per-task")
        self.assertEqual(code, 2, payload)
        self.assertIn("batch_stale_branch", self.findings(payload))

        message = next(
            f["message"]
            for f in payload["findings"]
            if f["code"] == "batch_stale_branch"
        )
        self.assertIn("daw/TASK-ALPHA-alpha-change", message)
        self.assertIn(tip, message)
        self.assertIn("worktree.py remove", message)
        self.assertFalse("daw/integration" in _git(self.repo, "branch", "--list"))

    def test_a_member_writing_into_the_main_tree_fails_the_batch(self) -> None:
        escaping = self.agent(
            "agent-escape.sh", f"echo corrupted >> {self.repo / 'src' / 'alpha.py'}"
        )
        beta = self.writing_agent("TASK-BETA", "src/beta.py", "VALUE = 2")
        self.agent(
            "agent.sh",
            f"if [ \"$2\" = 'TASK-ALPHA' ]; then exec {escaping}; fi\nexec {beta}",
        )
        code, payload = self.run_batch(agents="per-task")
        self.assertEqual(code, 1, payload)
        self.assertIn("worktree_escape_detected", self.findings(payload))
        base = _git(self.repo, "rev-parse", "HEAD").strip()
        self.assert_integration_unchanged(base)

    def test_a_member_writing_into_a_sibling_worktree_is_not_reported_as_an_escape(
        self,
    ) -> None:
        # The escape check watches the main tree, not sibling worktrees. The
        # corruption must surface as a merge conflict or a red composite
        # instead — never as a false escape.
        signal = self.root / "alpha-wrote-sibling"
        sibling = self.agent(
            "agent-sibling.sh",
            f"printf 'CORRUPTED = True\\n' > {self.repo / self.worktree_root / 'TASK-BETA' / 'src' / 'alpha.py'}\n"
            f"printf '%s\\n' 'VALUE = 2' > src/alpha.py\ntouch {signal}",
        )
        beta = self.agent(
            "agent-TASK-BETA.sh",
            f"while [ ! -f {signal} ]; do sleep 0.01; done\n"
            "printf '%s\\n' 'VALUE = 2' > src/beta.py\nexit 0",
        )
        self.agent(
            "agent.sh",
            f"if [ \"$2\" = 'TASK-ALPHA' ]; then exec {sibling}; fi\nexec {beta}",
        )
        code, payload = self.run_batch(agents="per-task")
        self.assertNotIn("worktree_escape_detected", self.findings(payload))
        self.assertEqual(code, 1, payload)
        self.assertIn("batch_merge_conflict", self.findings(payload))
        self.assert_integration_unchanged(_git(self.repo, "rev-parse", "HEAD").strip())

    def test_an_accepted_task_that_was_never_integrated_is_reported(self) -> None:
        alpha = self.writing_agent("TASK-ALPHA", "src/alpha.py", "VALUE = 2")
        beta = self.writing_agent("TASK-BETA", "src/beta.py", "VALUE = 2")
        self.agent(
            "agent.sh",
            f"if [ \"$2\" = 'TASK-ALPHA' ]; then exec {alpha}; fi\nexec {beta}",
        )
        # Seed an accepted task whose state entry names a commit that was never
        # merged into the integration branch.
        state_dir = self.repo / "docs" / "daw" / "evidence" / "runner"
        state_dir.mkdir(parents=True)
        (state_dir / "isolation.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "integration": {"branch": worktree.INTEGRATION_BRANCH},
                    "tasks": {
                        "TASK-BETA": {
                            "branch": "daw/TASK-BETA-beta-change",
                            "merged": True,
                            "accepted": True,
                            "merge_commit": "0" * 40,
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        code, payload = self.run_batch(
            agents="per-task", extra=["--accepted", "TASK-BETA"]
        )
        self.assertEqual(code, 2, payload)
        self.assertIn("batch_accepted_not_integrated", self.findings(payload))

    def test_an_accepted_task_without_a_state_entry_is_only_a_warning(self) -> None:
        alpha = self.writing_agent("TASK-ALPHA", "src/alpha.py", "VALUE = 2")
        beta = self.writing_agent("TASK-BETA", "src/beta.py", "VALUE = 2")
        self.agent(
            "agent.sh",
            f"if [ \"$2\" = 'TASK-ALPHA' ]; then exec {alpha}; fi\nexec {beta}",
        )
        code, payload = self.run_batch(
            agents="per-task", extra=["--accepted", "TASK-BETA"]
        )
        self.assertEqual(code, 0, payload)
        self.assertIn("batch_accepted_unverified", self.findings(payload))

    def test_dry_run_creates_nothing(self) -> None:
        alpha = self.writing_agent("TASK-ALPHA", "src/alpha.py", "VALUE = 2")
        beta = self.writing_agent("TASK-BETA", "src/beta.py", "VALUE = 2")
        self.agent(
            "agent.sh",
            f"if [ \"$2\" = 'TASK-ALPHA' ]; then exec {alpha}; fi\nexec {beta}",
        )
        code, payload = self.run_batch(agents="per-task", extra=["--dry-run"])
        self.assertEqual(code, 0, payload)
        self.assertTrue(payload.get("dry_run"))

        branches = _git(self.repo, "branch", "--list")
        self.assertNotIn(worktree.INTEGRATION_BRANCH, branches)
        self.assertNotIn("daw/TASK-ALPHA", branches)
        self.assertNotIn("daw/TASK-BETA", branches)
        self.assertFalse((self.repo / self.worktree_root).exists())


class ReviewDispatchTests(BatchRepoBase):
    """Fact-only review dispatch packages produced for failed or conflicting batches."""

    def _dispatch_path(self, task_id: str) -> pathlib.Path:
        return self.repo / "docs" / "daw" / "evidence" / task_id / "review-dispatch.json"

    def _read_dispatch(self, task_id: str) -> dict:
        path = self._dispatch_path(task_id)
        self.assertTrue(path.is_file(), f"missing review-dispatch.json for {task_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def test_a_red_member_produces_a_package_with_its_evidence(self) -> None:
        alpha = self.writing_agent("TASK-ALPHA", "src/alpha.py", "VALUE = 2")
        failing = self.agent("agent-fail.sh", "exit 1")
        self.agent(
            "agent.sh",
            f"if [ \"$2\" = 'TASK-ALPHA' ]; then exec {alpha}; fi\nexec {failing}",
        )
        code, payload = self.run_batch(agents="per-task")
        self.assertEqual(code, 1, payload)

        self.assertFalse(
            self._dispatch_path("TASK-ALPHA").exists(),
            "healthy sibling in a non-conflicting batch gets no package",
        )
        pkg = self._read_dispatch("TASK-BETA")
        entry = self.batch_entry(payload)

        self.assertEqual(pkg["schema_version"], 1)
        self.assertEqual(pkg["task_id"], "TASK-BETA")
        self.assertEqual(pkg["title"], "Beta change")
        self.assertEqual(pkg["branch"], "daw/TASK-BETA-beta-change")
        self.assertIsNone(pkg["commit"])
        self.assertEqual(pkg["base_commit"], entry["base_commit"])
        self.assertEqual(pkg["diff_range"], "")
        self.assertIsNotNone(pkg["self_verification"]["exit_code"])
        self.assertNotEqual(pkg["self_verification"]["exit_code"], 0)
        self.assertTrue(
            (self.repo / pkg["self_verification"]["log_path"]).is_file(),
            pkg["self_verification"],
        )
        self.assertEqual(len(pkg["self_verification"]["log_sha256"]), 64)
        self.assertIsNone(pkg["composite_verification"])
        self.assertEqual(pkg["combination_dependent_task_ids"], [])
        self.assertEqual(pkg["declared_target_files"], ["src/beta.py"])
        self.assertEqual(pkg["actual_changed_paths"], [])
        self.assertEqual(pkg["undeclared_paths"], [])
        self.assertEqual(pkg["findings"], ["batch_task_agent_failed"])

        rows = {row["task_id"]: row for row in pkg["members"]}
        self.assertEqual(set(rows), {"TASK-ALPHA", "TASK-BETA"})
        self.assertEqual(rows["TASK-BETA"]["agent_exit_code"], 1)
        self.assertIsNone(rows["TASK-BETA"]["composite_exit_code"])
        self.assertEqual(rows["TASK-ALPHA"]["agent_exit_code"], 0)
        self.assertEqual(rows["TASK-ALPHA"]["self_verification_exit_code"], 0)
        self.assertIsNone(rows["TASK-ALPHA"]["composite_exit_code"])

    def test_a_red_composite_produces_a_package_for_every_member(self) -> None:
        self.plan.write_text(BREAKING_PLAN_TEMPLATE, encoding="utf-8")
        alpha = self.writing_agent(
            "TASK-ALPHA", "src/shared.py", "A = 2\n# -\n# -\n# -\n# -\nB = 1"
        )
        beta = self.writing_agent(
            "TASK-BETA", "src/shared.py", "A = 1\n# -\n# -\n# -\n# -\nB = 2"
        )
        self.agent(
            "agent.sh",
            f"if [ \"$2\" = 'TASK-ALPHA' ]; then exec {alpha}; fi\nexec {beta}",
        )
        code, payload = self.run_batch(agents="per-task")
        self.assertEqual(code, 1, payload)
        entry = self.batch_entry(payload)

        for task_id in ("TASK-ALPHA", "TASK-BETA"):
            pkg = self._read_dispatch(task_id)
            self.assertEqual(pkg["schema_version"], 1)
            self.assertEqual(pkg["task_id"], task_id)
            self.assertTrue(pkg["commit"])
            self.assertEqual(pkg["base_commit"], entry["base_commit"])
            self.assertEqual(pkg["diff_range"], f"{entry['base_commit']}..{pkg['commit']}")
            self.assertEqual(pkg["self_verification"]["exit_code"], 0)
            self.assertIsNotNone(pkg["composite_verification"])
            self.assertTrue(
                (self.repo / pkg["composite_verification"]["log_path"]).is_file()
            )
            self.assertEqual(len(pkg["composite_verification"]["log_sha256"]), 64)
            self.assertEqual(
                pkg["actual_changed_paths"],
                sorted([f"ran-{task_id}.txt", "src/shared.py"]),
            )
            self.assertEqual(
                pkg["undeclared_paths"],
                sorted([f"ran-{task_id}.txt", "src/shared.py"]),
            )
            self.assertEqual(pkg["findings"], ["batch_composite_verification_failed"])

    def test_the_package_distinguishes_red_alone_from_red_only_on_the_composite(
        self,
    ) -> None:
        manifest_data = json.loads(
            BREAKING_PLAN_TEMPLATE.split("```json\n", 1)[1].split("\n```", 1)[0]
        )
        manifest_data["tasks"][1]["verification_command"] = (
            'python3 -c "import src.shared; assert src.shared.B == 2"'
        )
        manifest_data["tasks"].append(
            {
                "task_id": "TASK-GAMMA",
                "title": "Gamma change",
                "autonomy": "afk",
                "depends_on": [],
                "parallel_safe": True,
                "target_files": ["src/gamma.py"],
                "acceptance_criteria": ["gamma is green"],
                "verification_command": 'python3 -c "import src.gamma; assert src.gamma.VALUE == 2"',
                "expected_outcome": "0 exit code",
            }
        )
        self.plan.write_text(
            f"# Plan: batch test\n\n<!-- daw-task-manifest -->\n```json\n{json.dumps(manifest_data, indent=2)}\n```\n",
            encoding="utf-8",
        )
        alpha = self.writing_agent(
            "TASK-ALPHA", "src/shared.py", "A = 2\n# -\n# -\n# -\n# -\nB = 1"
        )
        beta = self.writing_agent(
            "TASK-BETA", "src/shared.py", "A = 1\n# -\n# -\n# -\n# -\nB = 2"
        )
        gamma_noop = self.agent("agent-gamma-noop.sh", "exit 0")
        self.agent(
            "agent.sh",
            f"if [ \"$2\" = 'TASK-ALPHA' ]; then exec {alpha}; fi\n"
            f"if [ \"$2\" = 'TASK-BETA' ]; then exec {beta}; fi\n"
            f"exec {gamma_noop}",
        )
        code, payload = self.run_batch(agents="per-task")
        self.assertEqual(code, 1, payload)

        pkg = self._read_dispatch("TASK-ALPHA")
        rows = {row["task_id"]: row for row in pkg["members"]}
        self.assertEqual(rows["TASK-ALPHA"]["self_verification_exit_code"], 0)
        self.assertIsNotNone(rows["TASK-ALPHA"]["composite_exit_code"])
        self.assertNotEqual(rows["TASK-ALPHA"]["composite_exit_code"], 0)

        self.assertEqual(rows["TASK-BETA"]["self_verification_exit_code"], 0)
        self.assertEqual(rows["TASK-BETA"]["composite_exit_code"], 0)

        self.assertNotEqual(rows["TASK-GAMMA"]["self_verification_exit_code"], 0)
        self.assertIsNone(rows["TASK-GAMMA"]["composite_exit_code"])

        self.assertEqual(pkg["combination_dependent_task_ids"], ["TASK-ALPHA"])

    def test_the_package_carries_no_verdict(self) -> None:
        self.plan.write_text(BREAKING_PLAN_TEMPLATE, encoding="utf-8")
        alpha = self.writing_agent(
            "TASK-ALPHA", "src/shared.py", "A = 2\n# -\n# -\n# -\n# -\nB = 1"
        )
        beta = self.writing_agent(
            "TASK-BETA", "src/shared.py", "A = 1\n# -\n# -\n# -\n# -\nB = 2"
        )
        self.agent(
            "agent.sh",
            f"if [ \"$2\" = 'TASK-ALPHA' ]; then exec {alpha}; fi\nexec {beta}",
        )
        code, payload = self.run_batch(agents="per-task")
        self.assertEqual(code, 1, payload)

        forbidden_keys = ("verdict", "culprit", "guilty")
        responsibility_words = (
            "verdict",
            "culprit",
            "guilty",
            "blame",
            "fault",
            "responsible",
        )

        def check_node(node: object) -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    lowered = str(key).lower()
                    for word in forbidden_keys:
                        self.assertNotIn(word, lowered, f"forbidden key: {key}")
                    check_node(value)
            elif isinstance(node, list):
                for item in node:
                    check_node(item)
            elif isinstance(node, str):
                lowered = node.lower()
                for word in responsibility_words:
                    self.assertNotIn(word, lowered, f"responsibility prose: {node}")
                self.assertFalse(
                    node.rstrip().endswith("."),
                    f"unexpected prose sentence in package: {node!r}",
                )

        for task_id in ("TASK-ALPHA", "TASK-BETA"):
            check_node(self._read_dispatch(task_id))

    def test_the_package_names_its_own_path_in_the_envelope(self) -> None:
        self.plan.write_text(BREAKING_PLAN_TEMPLATE, encoding="utf-8")
        alpha = self.writing_agent(
            "TASK-ALPHA", "src/shared.py", "A = 2\n# -\n# -\n# -\n# -\nB = 1"
        )
        beta = self.writing_agent(
            "TASK-BETA", "src/shared.py", "A = 1\n# -\n# -\n# -\n# -\nB = 2"
        )
        self.agent(
            "agent.sh",
            f"if [ \"$2\" = 'TASK-ALPHA' ]; then exec {alpha}; fi\nexec {beta}",
        )
        code, payload = self.run_batch(agents="per-task")
        self.assertEqual(code, 1, payload)

        dispatch = payload.get("review_dispatch")
        self.assertIsInstance(dispatch, list, payload)
        by_task = {entry["task_id"]: entry["path"] for entry in dispatch}
        self.assertEqual(set(by_task), {"TASK-ALPHA", "TASK-BETA"})
        for task_id, rel_path in by_task.items():
            self.assertFalse(pathlib.Path(rel_path).is_absolute(), rel_path)
            self.assertEqual(
                rel_path, f"docs/daw/evidence/{task_id}/review-dispatch.json"
            )
            disk_path = self.repo / rel_path
            self.assertTrue(disk_path.is_file(), disk_path)
            pkg = json.loads(disk_path.read_text(encoding="utf-8"))
            self.assertEqual(pkg["task_id"], task_id)

    def test_a_conflicting_batch_produces_a_package_for_every_green_member(self) -> None:
        self.plan.write_text(CONFLICT_PLAN_TEMPLATE, encoding="utf-8")
        alpha = self.writing_agent(
            "TASK-ALPHA", "src/shared.py", "A = 2\n# -\n# -\n# -\n# -\nB = 1"
        )
        beta = self.writing_agent(
            "TASK-BETA", "src/shared.py", "A = 8\n# -\n# -\n# -\n# -\nB = 1"
        )
        self.agent(
            "agent.sh",
            f"if [ \"$2\" = 'TASK-ALPHA' ]; then exec {alpha}; fi\nexec {beta}",
        )
        code, payload = self.run_batch(agents="per-task")
        self.assertEqual(code, 1, payload)

        by_task = {entry["task_id"]: entry["path"] for entry in payload.get("review_dispatch", [])}
        self.assertEqual(set(by_task), {"TASK-ALPHA", "TASK-BETA"})
        for task_id in ("TASK-ALPHA", "TASK-BETA"):
            pkg = self._read_dispatch(task_id)
            self.assertIsNone(pkg["composite_verification"])
            self.assertEqual(pkg["combination_dependent_task_ids"], [])
            self.assertEqual(pkg["findings"], ["batch_merge_conflict"])
            rows = {row["task_id"]: row for row in pkg["members"]}
            self.assertIsNone(rows["TASK-ALPHA"]["composite_exit_code"])
            self.assertIsNone(rows["TASK-BETA"]["composite_exit_code"])

    def test_a_fully_green_batch_produces_no_packages(self) -> None:
        alpha = self.writing_agent("TASK-ALPHA", "src/alpha.py", "VALUE = 2")
        beta = self.writing_agent("TASK-BETA", "src/beta.py", "VALUE = 2")
        self.agent(
            "agent.sh",
            f"if [ \"$2\" = 'TASK-ALPHA' ]; then exec {alpha}; fi\nexec {beta}",
        )
        code, payload = self.run_batch(agents="per-task")
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload.get("review_dispatch"), [])
        for task_id in ("TASK-ALPHA", "TASK-BETA"):
            self.assertFalse(self._dispatch_path(task_id).exists())


if __name__ == "__main__":
    unittest.main()
