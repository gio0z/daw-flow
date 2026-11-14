#!/usr/bin/env python3
"""Batch mechanism for the Deterministic Agentic Workflow execution layer.

This module decides *which* tasks may run together. It never imports
``scripts/run.py``: the runner consumes this module, so the dependency runs
one way only.

A plan's ``parallel_safe`` flag is necessary but not sufficient. Two tasks may
share a batch only when their declared write sets are pairwise disjoint, and
the runner re-derives that disjointness from the manifest itself rather than
trusting the plan's declaration. The comparison is prefix-aware, because a
declared ``target_files`` entry may be a directory (``src/auth``) and would
otherwise be treated as disjoint from the file inside it (``src/auth/x.py``).

The merge gate for a composite — the branch that proves the *combination* and
not just each part — lives in ``merge_composite_branch``.
"""

from __future__ import annotations

import hashlib
import pathlib
from typing import Any, Sequence

try:
    from scripts.daw_common import finding
except ImportError:
    from daw_common import finding  # type: ignore[import-not-found]

#: Finding code for two selected tasks whose declared write sets overlap.
OVERLAP_CODE = "batch_write_set_overlap"


def _normalize_path(path: str) -> str:
    """Strip a leading ``./`` and any trailing ``/`` from a relative path."""
    normalized = path
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.rstrip("/")


def paths_overlap(left: str, right: str) -> bool:
    """Return True when two paths are equal or one contains the other.

    Containment is by path segment: ``src/auth`` overlaps ``src/auth/x.py``
    but not ``src/authz/x.py``.
    """
    first = _normalize_path(left)
    second = _normalize_path(right)
    if first == second:
        return True
    return first.startswith(second + "/") or second.startswith(first + "/")


def write_sets_disjoint(left: Sequence[str], right: Sequence[str]) -> bool:
    """Return True when no path in ``left`` overlaps a path in ``right``."""
    return not any(paths_overlap(one, other) for one in left for other in right)


def undeclared_paths(declared: Sequence[str], actual: Sequence[str]) -> list[str]:
    """Return the actual paths that no declared path covers."""
    return [
        path
        for path in actual
        if not any(paths_overlap(cover, path) for cover in declared)
    ]


def _target_files(task: dict[str, Any]) -> list[str]:
    files = task.get("target_files")
    if not isinstance(files, list):
        return []
    return [path for path in files if isinstance(path, str)]


def _first_conflict(
    members: Sequence[str],
    candidate_files: Sequence[str],
    tasks_by_id: dict[str, dict[str, Any]],
) -> tuple[str, str] | None:
    """Return the first (member id, overlapping path) pair, or None."""
    for member in members:
        member_files = _target_files(tasks_by_id.get(member, {}))
        for path in candidate_files:
            if any(paths_overlap(path, member_path) for member_path in member_files):
                return member, path
    return None


def select_batch_members(
    manifest: dict[str, Any],
    ready: list[dict[str, Any]],
    pinned: Sequence[str] | None = None,
    max_concurrency: int | None = None,
    max_tasks: int | None = None,
) -> tuple[list[list[str]], list[dict[str, str]]]:
    """Group the ready tasks into batches that may run together.

    ``ready`` supplies the deterministic order (dependency depth, then task id);
    the manifest supplies each task's declared write set. ``pinned`` restricts
    the selection to the given task ids without changing the ready order.
    ``max_concurrency`` caps the size of a single group; ``max_tasks`` caps the
    total number of members across all groups and is spent *during* grouping,
    so the selected members are the ones grouping chose.

    Grouping is greedy first-fit: a task joins the first group whose members
    are all disjoint from its own write set, and otherwise opens a new one. A
    task marked ``parallel_safe: false`` always runs alone.

    Returns the groups and the warnings describing write-set overlaps that
    separated two otherwise-batchable tasks.
    """
    tasks_by_id: dict[str, dict[str, Any]] = {
        task["task_id"]: task
        for task in manifest.get("tasks", [])
        if isinstance(task, dict) and "task_id" in task
    }

    candidates = list(ready)
    if pinned is not None:
        pinned_ids = set(pinned)
        candidates = [entry for entry in candidates if entry.get("task_id") in pinned_ids]

    groups: list[list[str]] = []
    warnings: list[dict[str, str]] = []
    parallel_safe_by_id: dict[str, bool] = {}
    remaining = max_tasks

    for entry in candidates:
        if remaining is not None and remaining <= 0:
            break
        task_id = entry["task_id"]
        task = tasks_by_id.get(task_id, {})
        candidate_files = _target_files(task)
        parallel_safe = bool(entry.get("parallel_safe", task.get("parallel_safe", False)))
        parallel_safe_by_id[task_id] = parallel_safe

        # Every group is scanned, not only the ones up to the candidate's home:
        # whether two selected tasks overlap does not depend on which group the
        # candidate happened to join first.
        conflicts = [_first_conflict(group, candidate_files, tasks_by_id) for group in groups]
        blocker = next((conflict for conflict in conflicts if conflict is not None), None)

        home: list[str] | None = None
        if parallel_safe:
            for group, conflict in zip(groups, conflicts):
                if max_concurrency is not None and len(group) >= max_concurrency:
                    continue
                if not all(parallel_safe_by_id.get(member, False) for member in group):
                    continue
                if conflict is not None:
                    continue
                home = group
                break

        if home is None:
            groups.append([task_id])
        else:
            home.append(task_id)

        if blocker is not None:
            blocking_id, overlapping_path = blocker
            warnings.append(
                finding(
                    "warning",
                    OVERLAP_CODE,
                    task_id,
                    f"Task {task_id} was not batched with {blocking_id}: "
                    f"their declared write sets overlap on {overlapping_path}.",
                )
            )

        if remaining is not None:
            remaining -= 1

    return groups, warnings
