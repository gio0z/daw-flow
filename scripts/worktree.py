#!/usr/bin/env python3
"""Deterministic per-task worktree isolation.

The suite's execution layer decides *which* task runs next and *whether* it
passed. It does not decide *where* the work happens. This tool fills that gap:
it gives every task its own git branch and its own worktree, runs the task
there, and integrates the result only after the task's own verification
command exited ``0``.

Design rules (the same ones the rest of the suite follows):

- **One authority.** Branch names, worktree paths, and the integration branch
  are derived from the task id, never guessed and never hand-written.
- **Isolation is real.** The worktree lives inside the project root, so the
  user's own working tree is never touched and their uncommitted work is never
  at risk. The container directory must be git-ignored; the tool refuses to
  create a worktree in a directory git would track.
- **Integration is earned.** A task branch is merged into the integration
  branch only when that task's verification evidence is green *and* was
  produced at the exact commit being merged.
- **Nothing leaves the machine.** No push, no tag, no publish, no deploy, no
  protected branch is ever written. The integration branch is a local branch
  this tool created; merging it into a working branch is the ship route's job.

The tool is explicitly invoked, never a daemon or a background service. It
writes two things: the worktree metadata inside the project root, and a state
file recording what it did. It never edits a specification, never rewrites a
plan, and never records parent acceptance.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
from typing import Any

try:
    from scripts.daw_common import compute_sha256, resolve_bounded_path
except ImportError:
    from daw_common import compute_sha256, resolve_bounded_path  # type: ignore[import-not-found]

STATE_SCHEMA_VERSION = 1

#: Container directory (relative to the project root) holding every task
#: worktree. It must be git-ignored before the first worktree is created.
DEFAULT_WORKTREE_ROOT = ".worktrees"

#: Local branch this tool creates to collect verified task work.
INTEGRATION_BRANCH = "daw/integration"

#: Default location of the isolation state file, relative to the project root.
DEFAULT_STATE_PATH = "docs/evidence/runner/isolation.json"

#: Branches this tool must never write to.
PROTECTED_BRANCHES = ("main", "master", "develop", "trunk")
PROTECTED_BRANCH_PREFIXES = ("release/", "refs/heads/release/")

#: Maximum bytes read from one file when hashing or scanning.
MAX_TEXT_BYTES = 1_000_000


class IsolationError(Exception):
    """Usage or environment error: exits with code 2."""

    def __init__(self, message: str, findings: list[dict[str, str]] | None = None) -> None:
        super().__init__(message)
        self.findings = findings or []


def _error(code: str, path: str, message: str) -> dict[str, str]:
    return {"severity": "error", "code": code, "path": path, "message": message}


def _warning(code: str, path: str, message: str) -> dict[str, str]:
    return {"severity": "warning", "code": code, "path": path, "message": message}


ISOLATION_LIMITATIONS = [
    "Explicitly invoked per unit of work; never a daemon, scheduler, or background service.",
    "Never pushes, tags, publishes, or deploys; never writes to a protected branch.",
    "A merged task branch proves its verification command exited 0 at that commit; it does not prove the change is correct.",
    "The state file records what this tool did; it never records parent acceptance.",
]


# --------------------------------------------------------------------------
# Git primitives
# --------------------------------------------------------------------------


def git_available() -> bool:
    return shutil.which("git") is not None


def run_git(
    args: list[str], cwd: pathlib.Path, timeout: int = 120
) -> tuple[int, str, str]:
    """Run one git command as argv (never a shell) and return (code, out, err)."""
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["git", *args],
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        raise IsolationError("git is not installed or not on PATH.") from None
    except subprocess.TimeoutExpired:
        raise IsolationError(f"git {' '.join(args)} timed out after {timeout}s.") from None
    return (
        completed.returncode,
        completed.stdout.decode("utf-8", errors="replace"),
        completed.stderr.decode("utf-8", errors="replace"),
    )


def git_out(args: list[str], cwd: pathlib.Path, timeout: int = 120) -> str:
    code, out, err = run_git(args, cwd, timeout)
    if code != 0:
        raise IsolationError(f"git {' '.join(args)} failed: {err.strip() or out.strip()}")
    return out.strip()


def repo_toplevel(project_root: pathlib.Path) -> pathlib.Path | None:
    """Return the repository top level, or None when the path is not a repo."""
    code, out, _ = run_git(["rev-parse", "--show-toplevel"], project_root)
    if code != 0:
        return None
    try:
        return pathlib.Path(out.strip()).resolve()
    except OSError:
        return None


def require_repo(project_root: pathlib.Path) -> pathlib.Path:
    """Return the repository top level, refusing when it differs from the root."""
    top = repo_toplevel(project_root)
    if top is None:
        raise IsolationError(
            f"Project root is not a git repository: {project_root}. "
            "Per-task isolation requires git (2.20+)."
        )
    if top != project_root:
        raise IsolationError(
            f"Project root {project_root} is not the repository top level ({top}). "
            "Point the tool at the repository root so worktree paths stay inside it."
        )
    return top


def path_is_ignored(repo: pathlib.Path, relative: str) -> bool:
    """Return True when git would ignore the given repository-relative directory."""
    candidate = relative.rstrip("/") + "/"
    code, _, _ = run_git(["check-ignore", "-q", candidate], repo)
    return code == 0


def exclude_file(repo: pathlib.Path) -> pathlib.Path:
    """Resolve the repository-local exclude file (``git rev-parse --git-path``).

    This is the file daw-workspace Procedure B names: it is repository-local,
    never global, and never the project's own ``.gitignore``.
    """
    raw = git_out(["rev-parse", "--git-path", "info/exclude"], repo)
    candidate = pathlib.Path(raw)
    if not candidate.is_absolute():
        candidate = repo / candidate
    return candidate


def ensure_ignored(repo: pathlib.Path, relative: str) -> bool:
    """Make a repository-relative directory ignored, using the repo-local exclude file.

    Returns True when the directory is ignored afterwards. The project's own
    ``.gitignore`` is never touched and global git configuration is never
    modified: only the repository-local exclude file is appended to, and only
    when the exact pattern is absent.
    """
    if path_is_ignored(repo, relative):
        return True
    pattern = f"{relative.rstrip('/')}/"
    target = exclude_file(repo)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        existing = target.read_text(encoding="utf-8") if target.is_file() else ""
    except (OSError, UnicodeDecodeError) as exc:
        raise IsolationError(f"Exclude file cannot be read: {target} ({exc})") from exc
    if pattern not in existing.splitlines():
        addition = "" if not existing or existing.endswith("\n") else "\n"
        addition += f"# Added by the DAW deterministic runner for per-task worktrees.\n{pattern}\n"
        try:
            target.write_text(existing + addition, encoding="utf-8")
        except OSError as exc:
            raise IsolationError(f"Exclude file cannot be written: {target} ({exc})") from exc
    return path_is_ignored(repo, relative)


def branch_exists(repo: pathlib.Path, branch: str) -> bool:
    code, _, _ = run_git(["rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"], repo)
    return code == 0


def branch_commit(repo: pathlib.Path, branch: str) -> str | None:
    code, out, _ = run_git(["rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"], repo)
    if code != 0:
        return None
    return out.strip() or None


def list_worktrees(repo: pathlib.Path) -> list[dict[str, Any]]:
    """Parse ``git worktree list --porcelain`` into a list of dictionaries."""
    code, out, err = run_git(["worktree", "list", "--porcelain"], repo)
    if code != 0:
        raise IsolationError(f"git worktree list failed: {err.strip()}")
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for raw in out.splitlines():
        line = raw.rstrip()
        if not line:
            if current:
                entries.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            current = {"path": value, "head": None, "branch": None, "detached": False}
        elif key == "HEAD":
            current["head"] = value
        elif key == "branch":
            current["branch"] = value.replace("refs/heads/", "", 1)
        elif key == "detached":
            current["detached"] = True
    if current:
        entries.append(current)
    return entries


def worktree_for_branch(repo: pathlib.Path, branch: str) -> dict[str, Any] | None:
    """Return the registered worktree for a branch, pruning a stale registration.

    A worktree whose directory was deleted by hand leaves a registration git
    still lists. Treating that as an existing worktree would hand back a path
    that does not exist, so stale registrations are pruned first.
    """
    entries = list_worktrees(repo)
    for entry in entries:
        if entry.get("branch") != branch:
            continue
        path = entry.get("path")
        if isinstance(path, str) and pathlib.Path(path).is_dir():
            return entry
        prune_worktrees(repo)
        return None
    return None


def prune_worktrees(repo: pathlib.Path) -> None:
    """Drop git's registrations for worktrees whose directory no longer exists."""
    run_git(["worktree", "prune"], repo)


def worktree_is_clean(path: pathlib.Path) -> bool:
    code, out, _ = run_git(["status", "--porcelain"], path)
    if code != 0:
        return False
    return not out.strip()


def dirty_paths(path: pathlib.Path) -> list[str]:
    """List the paths git reports as modified in a working tree."""
    code, out, _ = run_git(["status", "--porcelain"], path)
    if code != 0:
        return []
    entries: list[str] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        # Porcelain format: two status columns then the path.
        entry = line[3:].strip() if len(line) > 3 else ""
        if " -> " in entry:
            entry = entry.split(" -> ", 1)[1]
        entries.append(entry.strip('"'))
    return entries


def snapshot_main_tree(repo: pathlib.Path) -> list[str]:
    """Snapshot the main working tree's dirty paths, to detect an escaped agent."""
    return dirty_paths(repo)


def is_protected_branch(branch: str) -> bool:
    name = branch.strip()
    if name in PROTECTED_BRANCHES:
        return True
    return any(name.startswith(prefix) for prefix in PROTECTED_BRANCH_PREFIXES)


# --------------------------------------------------------------------------
# Naming
# --------------------------------------------------------------------------


def slugify(text: str, max_length: int = 40) -> str:
    """Lowercase kebab-case slug, bounded in length."""
    slug = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug or "task"


def branch_name_for(task_id: str, title: str) -> str:
    """Deterministic branch name for a task: ``daw/<task-id>-<title-slug>``."""
    safe_id = re.sub(r"[^A-Za-z0-9._-]+", "-", str(task_id)).strip("-")
    if not safe_id:
        raise IsolationError(f"Task id cannot be turned into a branch name: {task_id!r}")
    return f"daw/{safe_id}-{slugify(title)}"


def container_dir(worktree_root: str) -> str:
    return worktree_root.strip().strip("/") or DEFAULT_WORKTREE_ROOT


def task_worktree_rel(worktree_root: str, task_id: str) -> str:
    safe_id = re.sub(r"[^A-Za-z0-9._-]+", "-", str(task_id)).strip("-")
    if not safe_id:
        raise IsolationError(f"Task id cannot be turned into a worktree path: {task_id!r}")
    return f"{container_dir(worktree_root)}/{safe_id}"


def integration_worktree_rel(worktree_root: str) -> str:
    return f"{container_dir(worktree_root)}/_integration"


# --------------------------------------------------------------------------
# State file
# --------------------------------------------------------------------------


def empty_state() -> dict[str, Any]:
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "integration": {
            "branch": INTEGRATION_BRANCH,
            "worktree_path": None,
            "base_ref": None,
            "base_commit": None,
        },
        "tasks": {},
    }


def load_state(state_path: pathlib.Path) -> dict[str, Any]:
    if not state_path.is_file():
        return empty_state()
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return empty_state()
    if not isinstance(data, dict):
        return empty_state()
    state = empty_state()
    integration = data.get("integration")
    if isinstance(integration, dict):
        state["integration"].update(integration)
    tasks = data.get("tasks")
    if isinstance(tasks, dict):
        for task_id, entry in tasks.items():
            if isinstance(entry, dict):
                state["tasks"][str(task_id)] = entry
    return state


def save_state(state_path: pathlib.Path, state: dict[str, Any]) -> None:
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise IsolationError(f"State file cannot be written: {state_path} ({exc})") from exc


def accepted_task_ids(state: dict[str, Any]) -> list[str]:
    """Task ids whose work is integrated (verified and merged)."""
    return sorted(
        task_id
        for task_id, entry in state.get("tasks", {}).items()
        if isinstance(entry, dict) and entry.get("merged") is True
    )


# --------------------------------------------------------------------------
# Worktree lifecycle
# --------------------------------------------------------------------------


def ensure_integration_worktree(
    repo: pathlib.Path, worktree_root: str, base_ref: str | None
) -> dict[str, Any]:
    """Create (or reuse) the integration branch and its worktree."""
    rel = integration_worktree_rel(worktree_root)
    path = repo / rel
    existing = worktree_for_branch(repo, INTEGRATION_BRANCH)
    if existing is not None:
        return {
            "branch": INTEGRATION_BRANCH,
            "worktree_path": existing["path"],
            "worktree_rel": rel,
            "reused": True,
            "commit": existing.get("head"),
        }
    if branch_exists(repo, INTEGRATION_BRANCH):
        # The branch exists but its worktree was removed. Check it out again
        # rather than refusing: the branch keeps whatever work it already
        # carries, and nothing is lost.
        code, _, err = run_git(["worktree", "add", rel, INTEGRATION_BRANCH], repo)
        if code != 0:
            raise IsolationError(
                f"Integration worktree cannot be restored for branch {INTEGRATION_BRANCH}: "
                f"{err.strip()}"
            )
        return {
            "branch": INTEGRATION_BRANCH,
            "worktree_path": str(path),
            "worktree_rel": rel,
            "reused": True,
            "commit": branch_commit(repo, INTEGRATION_BRANCH),
        }
    start_point = base_ref or "HEAD"
    code, _, err = run_git(["worktree", "add", "-b", INTEGRATION_BRANCH, rel, start_point], repo)
    if code != 0:
        raise IsolationError(f"Integration worktree cannot be created: {err.strip()}")
    return {
        "branch": INTEGRATION_BRANCH,
        "worktree_path": str(path),
        "worktree_rel": rel,
        "reused": False,
        "commit": branch_commit(repo, INTEGRATION_BRANCH),
    }


def ensure_task_worktree(
    repo: pathlib.Path,
    worktree_root: str,
    task_id: str,
    title: str,
    base_ref: str | None,
) -> dict[str, Any]:
    """Create (or reuse) the branch and worktree that hold one task's work."""
    branch = branch_name_for(task_id, title)
    rel = task_worktree_rel(worktree_root, task_id)
    path = repo / rel

    existing = worktree_for_branch(repo, branch)
    if existing is not None:
        return {
            "branch": branch,
            "worktree_path": existing["path"],
            "worktree_rel": rel,
            "reused": True,
            "commit": existing.get("head"),
        }

    if branch_exists(repo, branch):
        code, _, err = run_git(["worktree", "add", rel, branch], repo)
        if code != 0:
            raise IsolationError(
                f"Worktree for existing branch {branch} cannot be created: {err.strip()}"
            )
        return {
            "branch": branch,
            "worktree_path": str(path),
            "worktree_rel": rel,
            "reused": True,
            "commit": branch_commit(repo, branch),
        }

    start_point = base_ref or "HEAD"
    code, _, err = run_git(["worktree", "add", "-b", branch, rel, start_point], repo)
    if code != 0:
        raise IsolationError(f"Task worktree cannot be created: {err.strip()}")
    return {
        "branch": branch,
        "worktree_path": str(path),
        "worktree_rel": rel,
        "reused": False,
        "commit": branch_commit(repo, branch),
    }


def commit_task_work(
    worktree_path: pathlib.Path, task_id: str, title: str
) -> dict[str, Any]:
    """Commit whatever the worker left in the worktree, on the task branch.

    The worktree is isolated: it contains this task's work and nothing else,
    so the whole working tree is the logical change. The commit is a local
    integration artifact, not a ship commit.
    """
    code, out, err = run_git(["status", "--porcelain"], worktree_path)
    if code != 0:
        raise IsolationError(f"git status failed in {worktree_path}: {err.strip()}")
    if not out.strip():
        head = git_out(["rev-parse", "HEAD"], worktree_path)
        return {"committed": False, "commit": head, "reason": "no changes in the worktree"}
    message = f"task({task_id}): {title}"
    code, _, err = run_git(["add", "-A"], worktree_path)
    if code != 0:
        raise IsolationError(f"git add failed in {worktree_path}: {err.strip()}")
    code, _, err = run_git(["commit", "-m", message], worktree_path)
    if code != 0:
        raise IsolationError(f"git commit failed in {worktree_path}: {err.strip()}")
    return {
        "committed": True,
        "commit": git_out(["rev-parse", "HEAD"], worktree_path),
        "message": message,
    }


def merge_task_branch(
    repo: pathlib.Path,
    integration_worktree: str,
    task_branch: str,
    task_id: str,
    title: str,
    project_root: pathlib.Path | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge a task branch into the integration branch, aborting on conflict.

    The merge gate lives here, not in the caller: a task branch is merged only
    when its verification evidence is green *at the commit being merged*. The
    gate is enforced for every entry point, so a caller cannot bypass it by
    calling this function directly.
    """
    if is_protected_branch(task_branch):
        raise IsolationError(f"Refusing to merge protected branch {task_branch}.")
    worktree_path = repo / integration_worktree
    if not worktree_path.is_dir():
        raise IsolationError(f"Integration worktree is missing: {worktree_path}")

    commit = branch_commit(repo, task_branch)
    ok, reason = verification_supports_merge(evidence, task_branch, commit)
    if not ok:
        raise IsolationError(
            f"Task {task_id} is not mergeable: {reason}.",
            [_error("merge_not_verified", str(task_id), reason)],
        )

    message = f"merge(task): {task_id} {title}"
    code, out, err = run_git(["merge", "--no-ff", "-m", message, task_branch], worktree_path)
    if code != 0:
        run_git(["merge", "--abort"], worktree_path)
        raise IsolationError(
            f"Merging {task_branch} into {INTEGRATION_BRANCH} failed and was aborted: "
            f"{(err.strip() or out.strip())}"
        )
    return {
        "merged": True,
        "merge_commit": git_out(["rev-parse", "HEAD"], worktree_path),
        "message": message,
        "reason": reason,
    }


def remove_task_worktree(repo: pathlib.Path, worktree_rel: str) -> dict[str, Any]:
    """Remove a task worktree. The branch is kept; deleting it is not this tool's job."""
    path = repo / worktree_rel
    if not path.is_dir():
        return {"removed": False, "reason": "worktree does not exist"}
    code, _, err = run_git(["worktree", "remove", worktree_rel], repo)
    if code != 0:
        raise IsolationError(f"Worktree {worktree_rel} cannot be removed: {err.strip()}")
    return {"removed": True}


# --------------------------------------------------------------------------
# Evidence
# --------------------------------------------------------------------------


def latest_verification(root: pathlib.Path, task_id: str) -> dict[str, Any] | None:
    """Return the newest verification evidence recorded for a task under ``root``."""
    directory = root / "docs" / "evidence" / task_id
    if not directory.is_dir():
        return None
    attempts: list[tuple[int, pathlib.Path]] = []
    for entry in directory.glob("verify-*.log"):
        match = re.match(r"verify-(\d+)\.log$", entry.name)
        if match:
            attempts.append((int(match.group(1)), entry))
    if not attempts:
        return None
    attempts.sort()
    index, path = attempts[-1]
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    fields: dict[str, str] = {}
    for line in text.splitlines()[:12]:
        if ":" in line and not line.startswith("$"):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    exit_code = fields.get("exit_code")
    try:
        exit_code_int = int(exit_code) if exit_code is not None else None
    except ValueError:
        exit_code_int = None
    return {
        "attempt": index,
        "path": str(path),
        "exit_code": exit_code_int,
        "passed": exit_code_int == 0,
        "branch": fields.get("branch"),
        "commit": fields.get("commit"),
        "sha256": compute_sha256(path),
    }


def verification_for_task(
    project_root: pathlib.Path, state: dict[str, Any], task_id: str
) -> dict[str, Any] | None:
    """Find a task's verification evidence, preferring the isolated worktree."""
    entry = state.get("tasks", {}).get(task_id)
    if isinstance(entry, dict):
        worktree_path = entry.get("worktree_path")
        if isinstance(worktree_path, str) and worktree_path:
            candidate = pathlib.Path(worktree_path)
            if candidate.is_dir():
                evidence = latest_verification(candidate, task_id)
                if evidence is not None:
                    return evidence
    return latest_verification(project_root, task_id)


def verification_supports_merge(
    evidence: dict[str, Any] | None, branch: str, commit: str | None
) -> tuple[bool, str]:
    """Decide whether the recorded evidence proves this exact commit passed."""
    if evidence is None:
        return False, "no verification evidence was recorded for this task"
    if not evidence.get("passed"):
        return False, (
            f"the latest verification exited {evidence.get('exit_code')}, not 0"
        )
    recorded_branch = evidence.get("branch")
    if recorded_branch and recorded_branch != branch:
        return False, (
            f"the evidence was produced on branch {recorded_branch}, not {branch}"
        )
    recorded_commit = evidence.get("commit")
    if recorded_commit and commit and recorded_commit != commit:
        return False, (
            f"the evidence was produced at commit {recorded_commit}, but the branch now "
            f"points at {commit}"
        )
    return True, "verification evidence is green at this commit"


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------


def resolve_state_path(project_root: pathlib.Path, raw: str) -> pathlib.Path:
    candidate = pathlib.Path(raw)
    if candidate.is_absolute():
        return candidate
    resolved, err = resolve_bounded_path(project_root, raw)
    if err or resolved is None:
        raise IsolationError(f"State path is not bounded by the project root: {raw} ({err}).")
    return resolved


def prepare_isolation(
    project_root: pathlib.Path,
    worktree_root: str,
    base_ref: str | None,
    task_id: str | None,
    title: str | None,
    add_ignore: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Create the integration worktree and (optionally) one task worktree.

    With ``dry_run`` set, nothing is created: the tool reports the branch and
    worktree names it *would* use and checks the preconditions, so a caller can
    inspect the plan before any branch or worktree exists.
    """
    repo = require_repo(project_root)
    findings: list[dict[str, str]] = []
    container = container_dir(worktree_root)
    if not path_is_ignored(repo, container):
        if not add_ignore:
            findings.append(
                _error(
                    "worktree_root_not_ignored",
                    container,
                    f"git would track {container}/. Add it to .gitignore, or re-run with "
                    "--add-ignore to append it to the repository-local exclude file "
                    "(never the project's .gitignore, never global git config).",
                )
            )
            raise IsolationError(
                f"The worktree container {container}/ is not git-ignored.", findings
            )
        if dry_run:
            raise IsolationError(
                f"The worktree container {container}/ is not git-ignored.",
                [
                    _error(
                        "worktree_root_not_ignored",
                        container,
                        f"git would track {container}/; a dry run does not modify the "
                        "exclude file, so it cannot proceed.",
                    )
                ],
            )
        if not ensure_ignored(repo, container):
            findings.append(
                _error(
                    "worktree_root_not_ignored",
                    container,
                    f"{container}/ could not be made ignored; the worktree container would be "
                    "tracked by git.",
                )
            )
            raise IsolationError(
                f"The worktree container {container}/ is not git-ignored.", findings
            )

    if dry_run:
        integration = {
            "branch": INTEGRATION_BRANCH,
            "worktree_path": str(repo / integration_worktree_rel(worktree_root)),
            "worktree_rel": integration_worktree_rel(worktree_root),
            "reused": False,
            "commit": branch_commit(repo, INTEGRATION_BRANCH),
            "dry_run": True,
        }
        task = None
        if task_id:
            if not title:
                raise IsolationError("A task title is required to name the task branch.")
            task = {
                "branch": branch_name_for(task_id, title),
                "worktree_path": str(repo / task_worktree_rel(worktree_root, task_id)),
                "worktree_rel": task_worktree_rel(worktree_root, task_id),
                "reused": False,
                "commit": None,
                "base_ref": integration.get("commit") or base_ref,
                "dry_run": True,
            }
        return {"integration": integration, "task": task}

    integration = ensure_integration_worktree(repo, worktree_root, base_ref)
    result: dict[str, Any] = {
        "integration": integration,
        "task": None,
    }
    if task_id:
        if not title:
            raise IsolationError("A task title is required to name the task branch.")
        base = integration.get("commit") or base_ref
        task = ensure_task_worktree(repo, worktree_root, task_id, title, base)
        task["base_ref"] = base
        result["task"] = task
    return result


def record_prepared_task(
    state_path: pathlib.Path,
    state: dict[str, Any],
    task_id: str,
    task: dict[str, Any],
    integration: dict[str, Any],
    base_ref: str | None,
) -> None:
    """Persist what preparation produced, without discarding merge history."""
    state["integration"] = {
        "branch": integration["branch"],
        "worktree_path": integration["worktree_path"],
        "worktree_rel": integration["worktree_rel"],
        "base_ref": base_ref or "HEAD",
        "base_commit": integration.get("commit"),
    }
    entry = state["tasks"].setdefault(task_id, {})
    entry.update(
        {
            "branch": task["branch"],
            "worktree_path": task["worktree_path"],
            "worktree_rel": task["worktree_rel"],
            "base_ref": task.get("base_ref"),
            "merged": bool(entry.get("merged", False)),
        }
    )
    save_state(state_path, state)


def command_prepare(args: argparse.Namespace) -> int:
    project_root = pathlib.Path(args.project_root).resolve()
    if not project_root.is_dir():
        raise IsolationError(f"Project root is not a directory: {project_root}")
    state_path = resolve_state_path(project_root, args.state)
    state = load_state(state_path)
    outcome = prepare_isolation(
        project_root,
        args.worktree_root,
        args.base_ref,
        args.task,
        args.title,
        args.add_ignore,
    )
    integration = outcome["integration"]
    task = outcome.get("task")
    if task:
        record_prepared_task(
            state_path, state, args.task, task, integration, args.base_ref
        )
    else:
        state["integration"] = {
            "branch": integration["branch"],
            "worktree_path": integration["worktree_path"],
            "worktree_rel": integration["worktree_rel"],
            "base_ref": args.base_ref or "HEAD",
            "base_commit": integration.get("commit"),
        }
        save_state(state_path, state)
    payload = {
        "integration": integration,
        "task": task,
        "state_path": str(state_path),
    }
    print(json.dumps(payload, indent=2))
    return 0


def command_list(args: argparse.Namespace) -> int:
    project_root = pathlib.Path(args.project_root).resolve()
    state_path = resolve_state_path(project_root, args.state)
    state = load_state(state_path)
    repo = repo_toplevel(project_root)
    worktrees = list_worktrees(repo) if repo is not None else []
    tasks: list[dict[str, Any]] = []
    for task_id in sorted(state.get("tasks", {})):
        entry = state["tasks"][task_id]
        branch = entry.get("branch")
        record = {
            "task_id": task_id,
            "branch": branch,
            "worktree_path": entry.get("worktree_path"),
            "merged": bool(entry.get("merged")),
            "merge_commit": entry.get("merge_commit"),
            "verified_commit": entry.get("verified_commit"),
            "present": any(w.get("branch") == branch for w in worktrees),
        }
        tasks.append(record)
    print(
        json.dumps(
            {
                "integration": state.get("integration"),
                "accepted": accepted_task_ids(state),
                "tasks": tasks,
            },
            indent=2,
        )
    )
    return 0


def command_commit(args: argparse.Namespace) -> int:
    project_root = pathlib.Path(args.project_root).resolve()
    repo = require_repo(project_root)
    state_path = resolve_state_path(project_root, args.state)
    state = load_state(state_path)
    task_id = args.task
    entry = state.get("tasks", {}).get(task_id)
    if not isinstance(entry, dict):
        raise IsolationError(f"No isolation record for task {task_id}.")
    worktree_path = entry.get("worktree_path")
    if not isinstance(worktree_path, str) or not worktree_path:
        raise IsolationError(f"Isolation record for task {task_id} has no worktree path.")
    path = pathlib.Path(worktree_path)
    if not path.is_dir():
        raise IsolationError(f"Task worktree is missing: {path}")
    title = args.title or entry.get("title") or task_id
    outcome = commit_task_work(path, task_id, title)
    entry["commit"] = outcome.get("commit")
    entry["title"] = title
    save_state(state_path, state)
    print(json.dumps({"task_id": task_id, "worktree_path": str(path), **outcome}, indent=2))
    return 0


def command_merge(args: argparse.Namespace) -> int:
    project_root = pathlib.Path(args.project_root).resolve()
    repo = require_repo(project_root)
    state_path = resolve_state_path(project_root, args.state)
    state = load_state(state_path)
    task_id = args.task
    entry = state.get("tasks", {}).get(task_id)
    if not isinstance(entry, dict):
        raise IsolationError(f"No isolation record for task {task_id}.")
    branch = entry.get("branch")
    if not branch:
        raise IsolationError(f"Isolation record for task {task_id} has no branch.")
    if is_protected_branch(branch):
        raise IsolationError(f"Refusing to merge protected branch {branch}.")

    commit = branch_commit(repo, branch)
    evidence = verification_for_task(project_root, state, task_id)

    integration = state.get("integration", {})
    integration_rel = integration.get("worktree_rel") or integration_worktree_rel(
        args.worktree_root
    )
    outcome = merge_task_branch(
        repo,
        integration_rel,
        branch,
        task_id,
        args.title or task_id,
        project_root=project_root,
        evidence=evidence,
    )
    reason = outcome.get("reason", "")
    entry["merged"] = True
    entry["merge_commit"] = outcome["merge_commit"]
    entry["verified_commit"] = commit
    save_state(state_path, state)
    print(
        json.dumps(
            {
                "task_id": task_id,
                "branch": branch,
                "commit": commit,
                "merge_commit": outcome["merge_commit"],
                "evidence": evidence,
                "reason": reason,
            },
            indent=2,
        )
    )
    return 0


def command_remove(args: argparse.Namespace) -> int:
    project_root = pathlib.Path(args.project_root).resolve()
    repo = require_repo(project_root)
    state_path = resolve_state_path(project_root, args.state)
    state = load_state(state_path)
    task_id = args.task
    entry = state.get("tasks", {}).get(task_id)
    if not isinstance(entry, dict):
        raise IsolationError(f"No isolation record for task {task_id}.")
    rel = entry.get("worktree_rel") or task_worktree_rel(args.worktree_root, task_id)
    outcome = remove_task_worktree(repo, rel)
    print(json.dumps({"task_id": task_id, "worktree_rel": rel, **outcome}, indent=2))
    return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deterministic per-task worktree isolation."
    )
    subparsers = parser.add_subparsers(dest="verb", required=True)

    def add_common(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--project-root", required=True, help="Project root (repository top level).")
        sub.add_argument(
            "--worktree-root",
            default=DEFAULT_WORKTREE_ROOT,
            help=f"Container directory for worktrees (default {DEFAULT_WORKTREE_ROOT}).",
        )
        sub.add_argument(
            "--state",
            default=DEFAULT_STATE_PATH,
            help=f"Isolation state file (default {DEFAULT_STATE_PATH}).",
        )

    prepare_parser = subparsers.add_parser("prepare", help="Create the isolation worktrees.")
    add_common(prepare_parser)
    prepare_parser.add_argument("--task", help="Task id to prepare a worktree for.")
    prepare_parser.add_argument("--title", help="Task title (used in the branch name).")
    prepare_parser.add_argument("--base-ref", help="Base ref for the integration branch.")
    prepare_parser.add_argument(
        "--add-ignore",
        action="store_true",
        help="Append the worktree container to the repository-local exclude file "
        "when it is not already ignored. Never touches .gitignore or global git config.",
    )
    prepare_parser.set_defaults(func=command_prepare)

    list_parser = subparsers.add_parser("list", help="Report the isolation state.")
    add_common(list_parser)
    list_parser.set_defaults(func=command_list)

    commit_parser = subparsers.add_parser(
        "commit", help="Commit a task's work inside its worktree."
    )
    add_common(commit_parser)
    commit_parser.add_argument("--task", required=True, help="Task id to commit.")
    commit_parser.add_argument("--title", help="Task title (used in the commit message).")
    commit_parser.set_defaults(func=command_commit)

    merge_parser = subparsers.add_parser(
        "merge", help="Merge a verified task branch into the integration branch."
    )
    add_common(merge_parser)
    merge_parser.add_argument("--task", required=True, help="Task id to merge.")
    merge_parser.add_argument("--title", help="Task title (used in the merge message).")
    merge_parser.set_defaults(func=command_merge)

    remove_parser = subparsers.add_parser("remove", help="Remove a task worktree.")
    add_common(remove_parser)
    remove_parser.add_argument("--task", required=True, help="Task id whose worktree to remove.")
    remove_parser.set_defaults(func=command_remove)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not git_available():
        sys.stderr.write("Error: git is not installed or not on PATH.\n")
        return 2
    try:
        return int(args.func(args))
    except IsolationError as exc:
        payload = {
            "valid": False,
            "check": f"worktree:{args.verb}",
            "schema_version": STATE_SCHEMA_VERSION,
            "findings": exc.findings
            or [{"severity": "error", "code": "isolation_error", "path": "worktree", "message": str(exc)}],
            "limitations": ISOLATION_LIMITATIONS,
        }
        print(json.dumps(payload, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
