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
import json
import pathlib
from typing import Any, Sequence

try:
    from scripts.daw_common import artifact_dir, compute_sha256, finding, resolve_bounded_path
    from scripts.worktree import (
        INTEGRATION_BRANCH,
        IsolationError,
        branch_commit,
        branch_exists,
        container_dir,
        is_protected_branch,
        merge_branch_into_worktree,
        prune_worktrees,
        run_git,
        worktree_for_branch,
    )
except ImportError:
    from daw_common import (  # type: ignore[import-not-found]
        artifact_dir,
        compute_sha256,
        finding,
        resolve_bounded_path,
    )
    from worktree import (  # type: ignore[import-not-found]
        INTEGRATION_BRANCH,
        IsolationError,
        branch_commit,
        branch_exists,
        container_dir,
        is_protected_branch,
        merge_branch_into_worktree,
        prune_worktrees,
        run_git,
        worktree_for_branch,
    )

#: Finding code for two selected tasks whose declared write sets overlap.
OVERLAP_CODE = "batch_write_set_overlap"

#: Finding code for a member that cannot be merged into the composite.
CONFLICT_CODE = "batch_merge_conflict"

#: Finding code for a composite the merge gate refuses to integrate.
NOT_VERIFIED_CODE = "merge_not_verified"

#: Schema version of the composite record — the gate's input.
composite_record_schema_version = 1


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


# --------------------------------------------------------------------------
# Composite branch, record, and merge gate
# --------------------------------------------------------------------------


def batch_hash(base_commit: str, task_ids: Sequence[str]) -> str:
    """The first 10 hex characters of the batch's identity hash."""
    payload = base_commit + "|" + "|".join(sorted(task_ids))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:10]


def batch_id(base_commit: str, task_ids: Sequence[str]) -> str:
    """The batch's id: ``batch-<hash>``, derived from its base and members."""
    return "batch-" + batch_hash(base_commit, task_ids)


def composite_branch_name(batch_id: str) -> str:
    """The scratch branch that holds the composite of one batch."""
    return "daw/batch/" + batch_id.removeprefix("batch-")


def composite_worktree_rel(worktree_root: str) -> str:
    """The worktree path (relative to the project root) holding the composite."""
    return f"{container_dir(worktree_root)}/_composite"


def composite_evidence_dir(repo: pathlib.Path, batch_id: str) -> pathlib.Path:
    """The directory holding one batch's composite evidence.

    ``docs/daw/evidence/<batch-id>/`` by default, honouring a project's own
    evidence convention.
    """
    return artifact_dir(repo, "evidence") / batch_id


def write_composite_record(path: pathlib.Path, record: dict[str, Any]) -> None:
    """Write the composite record — the gate's input — as JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_composite_record(path: pathlib.Path) -> dict[str, Any] | None:
    """Read the composite record, or None when it is missing or unreadable."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _log_header_fields(path: pathlib.Path) -> dict[str, str]:
    """Parse a verification log's header fields.

    The header is read from the first twelve lines, the same way
    ``worktree.latest_verification`` reads a task log.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    fields: dict[str, str] = {}
    for line in text.splitlines()[:12]:
        if ":" in line and not line.startswith("$"):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    return fields


def derive_base_commit(repo: pathlib.Path, composite_commit: str) -> str:
    """Derive the composite's base commit from git, not from the record.

    The record is the untrusted artifact the gate exists to cross-check, so
    the ``--not`` bound of the merge-history reconstruction cannot come from
    it. The base is instead the merge base of the composite's tip and the
    integration branch's tip: the composite is created *at* the base and
    merges members into it, so it descends from the base and from nothing
    else. That stays true when the integration branch later moves forward
    with another task's merge — the composite's own ancestry does not.

    Raises ``IsolationError`` when the integration branch does not exist or
    the merge base cannot be computed: the gate fails closed rather than
    falling back to a bound the record controls.
    """
    if not branch_exists(repo, INTEGRATION_BRANCH):
        raise IsolationError(
            f"The composite's base cannot be derived: the integration branch "
            f"{INTEGRATION_BRANCH} does not exist.",
            [
                finding(
                    "error",
                    NOT_VERIFIED_CODE,
                    INTEGRATION_BRANCH,
                    f"The integration branch {INTEGRATION_BRANCH} does not exist, so the "
                    f"composite's base commit cannot be derived.",
                )
            ],
        )
    code, out, err = run_git(
        ["merge-base", composite_commit, INTEGRATION_BRANCH], repo
    )
    base = out.strip()
    if code != 0 or not base:
        raise IsolationError(
            f"The composite's base cannot be derived at {composite_commit}: "
            f"{err.strip() or out.strip()}",
            [
                finding(
                    "error",
                    NOT_VERIFIED_CODE,
                    str(composite_commit),
                    f"The merge base of {composite_commit} and {INTEGRATION_BRANCH} "
                    f"cannot be computed: {err.strip() or out.strip()}",
                )
            ],
        )
    return base


def _merged_member_commits(repo: pathlib.Path, composite_commit: str, base_commit: str) -> set[str]:
    """Reconstruct the merged member commits from the composite's own history.

    ``git rev-list --merges --parents`` exposes each merge commit's second
    parent — the exact commit that was merged. The ``--not`` bound keeps the
    base branch's own history out of the reconstruction.
    """
    code, out, err = run_git(
        ["rev-list", "--merges", "--parents", composite_commit, "--not", base_commit],
        repo,
    )
    if code != 0:
        raise IsolationError(
            f"The composite's merge history cannot be read at {composite_commit}: "
            f"{err.strip() or out.strip()}",
            [
                finding(
                    "error",
                    NOT_VERIFIED_CODE,
                    str(composite_commit),
                    f"The composite's merge history cannot be read at "
                    f"{composite_commit}: {err.strip() or out.strip()}",
                )
            ],
        )
    merged: set[str] = set()
    for line in out.splitlines():
        parts = line.split()
        # ``<merge> <first parent> <second parent>``: the second parent is the
        # commit that was merged in.
        if len(parts) >= 3:
            merged.add(parts[2])
    return merged


def validate_composite_record(
    repo: pathlib.Path,
    record: dict[str, Any],
    composite_commit: str | None,
    composite_branch: str | None = None,
) -> tuple[bool, str]:
    """Decide whether the composite record proves the composite green.

    The record is a derived summary and it is mutable, so it is not trusted:
    the member set is reconstructed from the composite's own merge history, the
    record's commit must equal the composite's tip, every member must be
    green, and every exit code is re-derived from the log the record names.

    The base commit of that reconstruction is derived from git, never read
    from the record — otherwise editing one field of the record would shrink
    the reconstructed set and hide a member. The record keeps its
    ``base_commit`` field, but only as a cross-checked value: it must equal
    the derived base.

    ``composite_branch`` is the branch the merge is actually for. When it is
    given, the log headers are checked against it rather than against the
    record's own ``composite_branch`` field, which the record also controls.

    Returns ``(ok, reason)``; ``reason`` explains a refusal.
    """
    recorded_commit = record.get("composite_commit")
    if not isinstance(recorded_commit, str) or not recorded_commit:
        return False, "the composite record names no composite commit"
    if composite_commit is None:
        return False, "the composite branch has no commit"
    if recorded_commit != composite_commit:
        return (
            False,
            f"the composite record was written at commit {recorded_commit}, but the "
            f"composite branch now points at {composite_commit}",
        )

    members = record.get("members")
    if not isinstance(members, list) or not members:
        return False, "the composite record lists no members"

    base_commit = derive_base_commit(repo, composite_commit)
    recorded_base = record.get("base_commit")
    if not isinstance(recorded_base, str) or not recorded_base:
        return False, "the composite record names no base commit"
    if recorded_base != base_commit:
        return (
            False,
            f"the composite record names base commit {recorded_base}, but the "
            f"composite's base is {base_commit}",
        )

    merged = _merged_member_commits(repo, composite_commit, base_commit)

    recorded_commits = {
        member.get("commit") for member in members if isinstance(member, dict)
    }
    for member in members:
        if not isinstance(member, dict):
            return False, "the composite record holds a member that is not an object"
        task_id = member.get("task_id")
        commit = member.get("commit")
        if not isinstance(commit, str) or not commit:
            return False, f"the composite record's member {task_id} names no commit"
        if commit not in merged:
            return (
                False,
                f"the composite record's member {task_id} (commit {commit}) was never "
                "merged into the composite",
            )
    for commit in sorted(merged - recorded_commits):
        listed = ", ".join(
            str(member.get("task_id")) for member in members if isinstance(member, dict)
        )
        return (
            False,
            f"the composite merged commit {commit}, which the composite record does "
            f"not list as a member; the record lists {listed}",
        )

    for member in members:
        task_id = member.get("task_id")
        exit_code = member.get("exit_code")
        if exit_code != 0:
            return (
                False,
                f"the composite record's member {task_id} exited {exit_code}, not 0",
            )

        log_path = member.get("log_path")
        if not isinstance(log_path, str) or not log_path:
            return False, f"the composite record's member {task_id} names no log"
        log, err = resolve_bounded_path(repo, log_path)
        if err is not None or log is None:
            return (
                False,
                f"the composite log for member {task_id} is not bounded by the project "
                f"root: {log_path}",
            )
        if not log.is_file():
            return (
                False,
                f"the composite log for member {task_id} does not exist: {log_path}",
            )
        # The log must live in this batch's own evidence directory: a record
        # may not point the gate at an arbitrary file inside the repository.
        evidence_dir = composite_evidence_dir(repo, str(record.get("batch_id") or ""))
        try:
            log.resolve().relative_to(evidence_dir.resolve())
        except (ValueError, OSError):
            return (
                False,
                f"the composite log for member {task_id} is outside the batch's "
                f"evidence directory {evidence_dir}: {log_path}",
            )
        digest = compute_sha256(log)
        if digest != member.get("log_sha256"):
            return (
                False,
                f"the composite log for member {task_id} has sha256 {digest}, but the "
                f"composite record says {member.get('log_sha256')}",
            )

        fields = _log_header_fields(log)
        logged_exit = fields.get("exit_code")
        try:
            logged_exit_int = int(logged_exit) if logged_exit is not None else None
        except ValueError:
            logged_exit_int = None
        if logged_exit_int != exit_code:
            return (
                False,
                f"the composite log for member {task_id} records exit code "
                f"{logged_exit_int}, but the composite record says {exit_code}",
            )
        expected_branch = (
            composite_branch
            if composite_branch is not None
            else record.get("composite_branch")
        )
        if fields.get("branch") != expected_branch:
            return (
                False,
                f"the composite log for member {task_id} was produced on branch "
                f"{fields.get('branch')}, not {expected_branch}",
            )
        if fields.get("commit") != composite_commit:
            return (
                False,
                f"the composite log for member {task_id} was produced at commit "
                f"{fields.get('commit')}, not {composite_commit}",
            )

    return True, "the composite record proves every member green at the composite commit"


def _remove_composite(repo: pathlib.Path, branch: str, worktree_rel: str) -> None:
    """Remove the composite's worktree and branch, so a retry starts clean.

    A failure is surfaced rather than swallowed: a silently surviving
    worktree or branch makes the next ``git worktree add -b`` fail with a
    message that does not name the real cause.
    """
    if worktree_for_branch(repo, branch) is not None or (repo / worktree_rel).is_dir():
        code, _, err = run_git(["worktree", "remove", "--force", worktree_rel], repo)
        if code != 0:
            raise IsolationError(
                f"The composite worktree {worktree_rel} cannot be removed: {err.strip()}",
                [
                    finding(
                        "error",
                        NOT_VERIFIED_CODE,
                        str(worktree_rel),
                        f"The composite worktree {worktree_rel} cannot be removed: "
                        f"{err.strip()}",
                    )
                ],
            )
    # A stale registration would keep the branch checked out, and git would
    # then refuse to delete it.
    prune_worktrees(repo)
    if branch_exists(repo, branch):
        code, _, err = run_git(["branch", "-D", branch], repo)
        if code != 0:
            raise IsolationError(
                f"The composite branch {branch} cannot be deleted: {err.strip()}",
                [
                    finding(
                        "error",
                        NOT_VERIFIED_CODE,
                        str(branch),
                        f"The composite branch {branch} cannot be deleted: {err.strip()}",
                    )
                ],
            )


def build_composite(
    repo: pathlib.Path,
    worktree_root: str,
    base_commit: str,
    batch_id: str,
    members: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Build the composite branch: every member merged into one scratch branch.

    The members are merged with ``--no-ff`` so each leaves a merge commit; the
    composite's merge history is the authority on which members were merged. A
    member whose branch carries no commit beyond the base produces no merge
    commit and is simply not in the merged set.

    The composite is recreated on every attempt: a failed attempt must not
    contaminate the next one.
    """
    branch = composite_branch_name(batch_id)
    worktree_rel = composite_worktree_rel(worktree_root)
    worktree_path = repo / worktree_rel

    _remove_composite(repo, branch, worktree_rel)

    code, _, err = run_git(
        ["worktree", "add", "-q", "-b", branch, worktree_rel, base_commit], repo
    )
    if code != 0:
        raise IsolationError(
            f"The composite worktree cannot be created at {worktree_rel}: {err.strip()}"
        )

    merged_task_ids: list[str] = []
    for member in sorted(members, key=lambda entry: str(entry.get("task_id", ""))):
        task_id = member["task_id"]
        member_branch = member["branch"]
        title = member.get("title", task_id)
        message = f"merge(task): {task_id} {title}"
        before = branch_commit(repo, branch)
        outcome = merge_branch_into_worktree(repo, worktree_rel, member_branch, message)
        if not outcome["merged"]:
            # The composite must not keep a partial merge: reset it to the base
            # so the failed attempt leaves no trace in its history.
            run_git(["reset", "--hard", base_commit], repo / worktree_rel)
            raise IsolationError(
                f"Merging {member_branch} into the composite {branch} failed and was "
                f"aborted: {outcome['reason']}",
                [
                    finding(
                        "error",
                        CONFLICT_CODE,
                        str(task_id),
                        f"Member {task_id} conflicts with the composite: "
                        f"{outcome['reason']}",
                    )
                ],
            )
        if outcome["merge_commit"] == before:
            # The member carried no commit beyond the base: git reported
            # "Already up to date" and left no merge commit behind, so the
            # member has no trace in the composite's history.
            continue
        merged_task_ids.append(task_id)

    return {
        "branch": branch,
        "worktree_path": str(worktree_path),
        "commit": branch_commit(repo, branch),
        "merged_task_ids": merged_task_ids,
    }


def merge_composite_branch(
    repo: pathlib.Path,
    integration_worktree: str,
    composite_branch: str,
    batch_id: str,
    project_root: pathlib.Path,
    record_path: pathlib.Path,
) -> dict[str, Any]:
    """Merge the composite into the integration branch, gated by its record.

    The gate lives here, not in the caller: a composite reaches the integration
    branch only when its record proves every member green at the exact
    composite commit. A caller cannot merge a composite without the record
    passing.

    The record is checked against the branch and the batch this merge is
    actually for, never against its own fields: a record that names another
    branch or another batch describes a different composite.
    """
    if is_protected_branch(composite_branch):
        raise IsolationError(
            f"Refusing to merge protected branch {composite_branch}.",
            [
                finding(
                    "error",
                    NOT_VERIFIED_CODE,
                    str(composite_branch),
                    f"The composite branch {composite_branch} is protected and must "
                    f"never be merged.",
                )
            ],
        )
    if not record_path.is_absolute():
        record_path = project_root / record_path
    record = read_composite_record(record_path)
    if record is None:
        reason = f"the composite record cannot be read: {record_path}"
        raise IsolationError(
            f"Batch {batch_id} is not mergeable: {reason}.",
            [finding("error", NOT_VERIFIED_CODE, str(record_path), reason)],
        )

    recorded_branch = record.get("composite_branch")
    if recorded_branch != composite_branch:
        reason = (
            f"the composite record names branch {recorded_branch}, but the merge is "
            f"for branch {composite_branch}"
        )
        raise IsolationError(
            f"Batch {batch_id} is not mergeable: {reason}.",
            [finding("error", NOT_VERIFIED_CODE, str(record_path), reason)],
        )

    recorded_batch = record.get("batch_id")
    if recorded_batch != batch_id:
        reason = (
            f"the composite record names batch {recorded_batch}, but the merge is "
            f"for batch {batch_id}"
        )
        raise IsolationError(
            f"Batch {batch_id} is not mergeable: {reason}.",
            [finding("error", NOT_VERIFIED_CODE, str(record_path), reason)],
        )

    integration_path = repo / integration_worktree
    if not integration_path.is_dir():
        raise IsolationError(
            f"Batch {batch_id} is not mergeable: the integration worktree is missing: "
            f"{integration_path}",
            [
                finding(
                    "error",
                    NOT_VERIFIED_CODE,
                    str(integration_worktree),
                    f"The integration worktree is missing: {integration_path}",
                )
            ],
        )

    composite_commit = branch_commit(repo, composite_branch)
    ok, reason = validate_composite_record(
        repo, record, composite_commit, composite_branch
    )
    if not ok:
        raise IsolationError(
            f"Batch {batch_id} is not mergeable: {reason}.",
            [finding("error", NOT_VERIFIED_CODE, str(record_path), reason)],
        )

    message = f"merge(batch): {batch_id}"
    outcome = merge_branch_into_worktree(
        repo, integration_worktree, composite_branch, message
    )
    if not outcome["merged"]:
        raise IsolationError(
            f"Merging {composite_branch} into the integration branch failed and was "
            f"aborted: {outcome['reason']}",
            [
                finding(
                    "error",
                    CONFLICT_CODE,
                    str(batch_id),
                    f"The composite {composite_branch} conflicts with the integration "
                    f"branch: {outcome['reason']}",
                )
            ],
        )

    return {
        "merged": True,
        "merge_commit": outcome["merge_commit"],
        "batch_id": batch_id,
        "composite_commit": composite_commit,
    }
