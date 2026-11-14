#!/usr/bin/env python3
"""Behavior tests for `scripts/batch.py` (write-set disjointness and batch selection)."""

from __future__ import annotations

import unittest

try:
    from scripts import batch
except ImportError:
    import batch  # type: ignore[import-not-found]


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


if __name__ == "__main__":
    unittest.main()
