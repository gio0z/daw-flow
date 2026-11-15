#!/usr/bin/env python3
"""Deterministic execution runner for the Deterministic Agentic Workflow suite.

Explicitly invoked, stdlib-only, bounded-scope executor. It is NOT a daemon, a
scheduler, or a background service: every invocation does one bounded unit of
work and exits.

Verbs
-----
``next``     Compute the deterministic ready set from the plan's task manifest.
              Read-only: no file is written, no command is executed.
``context``  Assemble a bounded context pack ("smart zone") for one task.
              Writes one file when ``--out`` is given; otherwise prints it.
``verify``   Execute one task's prescribed verification command and capture the
              observed output as durable evidence.
``isolate``  Run one task inside its own git worktree: prepare the worktree,
              hand the worker a context pack assembled from that worktree, run
              the task's verification command there, commit the result on the
              task branch, and merge it into the local integration branch only
              when that verification exited ``0``.
``run``      AFK loop: repeatedly take the next ready task, hand its context pack
              to an explicitly configured agent command, then verify it. The
              agent command is operator-supplied; the runner never discovers,
              installs, or enables one.

Task manifest
-------------
The plan document owns the task list. A plan carries a fenced ```json block
whose object has a ``tasks`` array; that block is the machine-readable manifest
the runner consumes. Field names match the planning module's task contract, so
the manifest and the plan prose cannot drift into different vocabularies.

Safety boundaries
-----------------
- The runner never pushes, tags, publishes, or deploys.
- The runner never writes to a protected branch. Task branches and the local
  integration branch are branches the runner created; merging them into a
  working branch remains the ship route's job.
- The runner never installs, discovers, or enables an agent command.
- The runner writes only inside the project root, and only the paths it is
  given (``--out``, evidence directory, worktree container).
- Point-of-risk authorization stays with the operator and the parent
  orchestrator; a passing verification is evidence, never authorization.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import pathlib
import re
import shlex
import subprocess
import sys
from typing import Any

try:
    from scripts import batch
    from scripts.check_config import parse_config_block
    from scripts.check_tasks import (
        MANIFEST_MARKER,
        MANIFEST_SCHEMA_VERSION,
        compare_manifests,
        derive_manifest,
        extract_manifest,
        extract_sources,
        load_task_files,
        topological_depth,
        validate_manifest,
    )
    from scripts.daw_common import (
        artifact_dir,
        compute_sha256,
        make_error,
        make_warning,
        resolve_bounded_path,
    )
    from scripts.worktree import (
        INTEGRATION_BRANCH,
        IntegrationLock,
        IsolationError,
        accepted_task_ids,
        branch_commit,
        branch_exists,
        branch_name_for,
        check_task_branch_tip,
        clear_batch_failure,
        commit_task_work,
        ensure_task_worktree,
        escape_paths,
        load_state,
        lock_path,
        merge_task_branch,
        prepare_isolation,
        record_batch_failure,
        record_task_entry,
        require_repo,
        resolve_state_path,
        run_git,
        save_state,
        snapshot_tree_state,
    )
except ImportError:
    import batch  # type: ignore[import-not-found]
    from check_config import parse_config_block  # type: ignore[import-not-found]
    from check_tasks import (  # type: ignore[import-not-found]
        MANIFEST_MARKER,
        MANIFEST_SCHEMA_VERSION,
        compare_manifests,
        derive_manifest,
        extract_manifest,
        extract_sources,
        load_task_files,
        topological_depth,
        validate_manifest,
    )
    from daw_common import (  # type: ignore[import-not-found]
        artifact_dir,
        compute_sha256,
        make_error,
        make_warning,
        resolve_bounded_path,
    )
    from worktree import (  # type: ignore[import-not-found]
        INTEGRATION_BRANCH,
        IntegrationLock,
        IsolationError,
        accepted_task_ids,
        branch_commit,
        branch_exists,
        branch_name_for,
        check_task_branch_tip,
        clear_batch_failure,
        commit_task_work,
        ensure_task_worktree,
        escape_paths,
        load_state,
        lock_path,
        merge_task_branch,
        prepare_isolation,
        record_batch_failure,
        record_task_entry,
        require_repo,
        resolve_state_path,
        run_git,
        save_state,
        snapshot_tree_state,
    )

DEFAULT_CONTEXT_BUDGET_CHARS = 100_000
DEFAULT_VERIFY_TIMEOUT_SECONDS = 600
DEFAULT_WORKTREE_ROOT = ".worktrees"
CONTEXT_TRUNCATION_MARKER = "\n<!-- truncated by context budget -->\n"


class RunnerError(Exception):
    """Usage or environment error: exits with code 2."""

    def __init__(self, message: str, findings: list[dict[str, str]] | None = None) -> None:
        super().__init__(message)
        self.findings = findings or []


def _envelope(verb: str, findings: list[dict[str, str]], payload: dict[str, Any]) -> dict[str, Any]:
    valid = not any(f.get("severity") == "error" for f in findings)
    return {
        "valid": valid,
        "check": f"run:{verb}",
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "findings": findings,
        "limitations": [
            "Explicitly invoked per unit of work; never a daemon, scheduler, or background service.",
            "Never pushes, merges, tags, publishes, or deploys; never grants point-of-risk authorization.",
            "Context assembly is byte-bounded, not token-modeled: budget is enforced in characters.",
            "A passing verification is observed evidence, never proof of semantic correctness or deployment readiness.",
        ],
        **payload,
    }


def _print(result: dict[str, Any], fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(result, indent=2))
        return
    status = "OK" if result["valid"] else "INVALID"
    print(f"[{status}] Check: {result['check']}")
    for key, value in result.items():
        if key in ("valid", "check", "schema_version", "findings", "limitations"):
            continue
        print(f"{key}: {json.dumps(value, sort_keys=False)}")
    for finding in result["findings"]:
        print(f"  [{finding['severity'].upper()}] {finding['code']} @ {finding['path']}: {finding['message']}")
    for limitation in result["limitations"]:
        print(f"  - {limitation}")


# --------------------------------------------------------------------------
# Manifest extraction & validation
# --------------------------------------------------------------------------


def load_manifest(
    plan_path: pathlib.Path, project_root: pathlib.Path | None = None
) -> tuple[dict[str, Any], dict[str, str], list[dict[str, str]]]:
    """Load the task list for a plan, plus any hand-authored task bodies.

    When the plan declares a task-source directory, the task files are the
    source of truth: the runner reads them directly and refuses to run when
    they have drifted from the plan's derived manifest. Otherwise the plan's
    embedded manifest is the source.
    """
    try:
        text = plan_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise RunnerError(f"Plan cannot be read as UTF-8 text: {plan_path} ({exc})") from exc

    findings: list[dict[str, str]] = []
    manifest, extract_findings = extract_manifest(text)
    findings.extend(extract_findings)

    sources = extract_sources(text)
    if sources and project_root is not None:
        resolved, err = resolve_bounded_path(project_root, sources)
        if err or resolved is None:
            raise RunnerError(
                f"Task-source path is unsafe or escapes the project root: {sources} ({err})."
            )
        tasks, bodies, load_findings = load_task_files(resolved)
        findings.extend(load_findings)
        if any(f["severity"] == "error" for f in findings):
            raise RunnerError("Task files failed structural validation.", findings)
        workflow_id = manifest.get("workflow_id") if isinstance(manifest, dict) else None
        source_manifest = derive_manifest(
            tasks, workflow_id if isinstance(workflow_id, str) else None
        )
        if manifest is not None and manifest != source_manifest:
            findings.extend(compare_manifests(manifest, source_manifest, plan_path, sources))
        if any(f["severity"] == "error" for f in findings):
            raise RunnerError(
                "Task files and the plan manifest disagree; re-derive with "
                "python3 scripts/derive_tasks.py --plan <plan> --write.",
                findings,
            )
        return source_manifest, bodies, findings

    if manifest is None:
        raise RunnerError("No usable task manifest in the plan.", findings)
    findings.extend(validate_manifest(manifest))
    if any(f["severity"] == "error" for f in findings):
        raise RunnerError("Task manifest failed structural validation.", findings)
    return manifest, {}, findings


def find_task(manifest: dict[str, Any], task_id: str) -> dict[str, Any]:
    for task in manifest["tasks"]:
        if isinstance(task, dict) and task.get("task_id") == task_id:
            return task
    raise RunnerError(f"Task {task_id!r} is not declared in the manifest.")


def compute_ready(
    manifest: dict[str, Any], accepted: set[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (ready, requires_human, blocked) task views.

    ``accepted`` holds task ids the parent has already accepted at the current
    revision. A task is ready when every dependency is accepted and the task
    itself is ``afk`` — ``hitl`` tasks always wait for a human decision.
    Ordering is deterministic: dependency depth first, then task id.
    """
    tasks = [t for t in manifest["tasks"] if isinstance(t, dict)]
    by_id = {t["task_id"]: t for t in tasks}
    accepted = {a for a in accepted if a in by_id}
    depth = topological_depth(tasks)
    ready: list[dict[str, Any]] = []
    requires_human: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for task in tasks:
        task_id = task["task_id"]
        if task_id in accepted:
            continue
        pending = [d for d in task.get("depends_on", []) if d in by_id and d not in accepted]
        if task.get("autonomy") == "hitl":
            requires_human.append(
                {
                    "task_id": task_id,
                    "title": task.get("title"),
                    "reason": "hitl: requires a live human decision before dispatch",
                    "pending_dependencies": pending,
                }
            )
            continue
        if pending:
            blocked.append(
                {
                    "task_id": task_id,
                    "title": task.get("title"),
                    "reason": "waiting on dependency acceptance: " + ", ".join(sorted(pending)),
                    "pending_dependencies": sorted(pending),
                }
            )
            continue
        ready.append(
            {
                "task_id": task_id,
                "title": task.get("title"),
                "depth": depth.get(task_id, 0),
                "parallel_safe": bool(task.get("parallel_safe")),
                "verification_command": task.get("verification_command"),
            }
        )
    ready.sort(key=lambda entry: (entry["depth"], entry["task_id"]))
    requires_human.sort(key=lambda entry: entry["task_id"])
    blocked.sort(key=lambda entry: entry["task_id"])
    return ready, requires_human, blocked


def parse_accepted(values: list[str] | None, accepted_file: str | None) -> set[str]:
    accepted: set[str] = set()
    for value in values or []:
        for part in value.split(","):
            if part.strip():
                accepted.add(part.strip())
    if accepted_file:
        try:
            raw = pathlib.Path(accepted_file).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise RunnerError(f"Accepted-task file cannot be read: {accepted_file} ({exc})") from exc
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            accepted.add(line.split()[0])
    return accepted


# --------------------------------------------------------------------------
# Context assembly (bounded "smart zone")
# --------------------------------------------------------------------------


def _suite_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent.parent


def _constitution_excerpt(budget: int = 4000) -> str:
    path = _suite_root() / "references" / "constitution.md"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    start = text.find("## Core Axiom")
    end = text.find("## Hard Rules")
    if start == -1:
        return ""
    excerpt = text[start : end if end > start else start + budget].strip()
    return excerpt[:budget]


def _project_config_excerpt(project_root: pathlib.Path) -> str:
    for name in ("AGENTS.md", "CLAUDE.md"):
        candidate = project_root / name
        if not candidate.is_file():
            continue
        try:
            text = candidate.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        config = parse_config_block(text)
        if config:
            lines = [f"- {key}: {value}" for key, value in sorted(config.items())]
            return "\n".join(lines)
    return ""


def assemble_context(
    manifest: dict[str, Any],
    task: dict[str, Any],
    project_root: pathlib.Path,
    budget_chars: int = DEFAULT_CONTEXT_BUDGET_CHARS,
    body: str = "",
    work_root: pathlib.Path | None = None,
    *,
    constitution_excerpt: str | None = None,
    project_config_excerpt: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Assemble a bounded context pack for one task.

    The pack is deterministic: fixed section order, explicit truncation, and a
    per-file SHA-256 so the consumer can prove which bytes it received. When
    the task came from a hand-authored task file, its prose body is included —
    that is the human-written "what and why", which the machine fields only
    summarize.

    ``work_root`` is where the target files are read from. It equals the
    project root in the default case; under per-task isolation it is the task's
    worktree, so the worker sees the state that its own branch will merge.
    """
    if budget_chars <= 0:
        raise RunnerError("Context budget must be a positive number of characters.")
    source_root = work_root or project_root

    sections: list[str] = []
    included: list[dict[str, Any]] = []
    truncated: list[dict[str, Any]] = []
    remaining = budget_chars

    header_lines = [
        f"# Task {task['task_id']}: {task['title']}",
        "",
        f"- Workflow: {manifest.get('workflow_id', 'unknown')}",
        f"- Autonomy: {task['autonomy']}",
        f"- Depends on: {', '.join(task['depends_on']) if task['depends_on'] else '(none)'}",
        f"- Verification command: {task['verification_command']}",
        f"- Expected outcome: {task['expected_outcome']}",
        "",
        "## Acceptance criteria",
    ]
    header_lines += [f"- {item}" for item in task["acceptance_criteria"]]
    if task.get("steps"):
        header_lines += ["", "## Steps (action / run / expected)"]
        for step in task["steps"]:
            if not isinstance(step, dict):
                continue
            header_lines.append(
                f"- {step.get('action', '')} | file: {step.get('file', '')} | run: {step.get('run', '')} | expected: {step.get('expected', '')}"
            )
    if task.get("interfaces"):
        header_lines += ["", "## Interfaces"]
        interfaces = task["interfaces"]
        if isinstance(interfaces, dict):
            header_lines.append(f"- consumes: {interfaces.get('consumes')}")
            header_lines.append(f"- produces: {interfaces.get('produces')}")
    if task.get("notes"):
        header_lines += ["", "## Notes", str(task["notes"])]
    header = "\n".join(header_lines)

    if body:
        header += "\n\n## Task brief\n\n" + body

    constitution = (
        _constitution_excerpt()
        if constitution_excerpt is None
        else constitution_excerpt
    )
    if constitution:
        header += "\n\n## Suite constitution (excerpt)\n\n" + constitution
    project_config = (
        _project_config_excerpt(project_root)
        if project_config_excerpt is None
        else project_config_excerpt
    )
    if project_config:
        header += "\n\n## Project commands (from the agent file config block)\n\n" + project_config

    sections.append(header)
    remaining -= len(header)

    context_files: list[str] = list(task.get("target_files") or [])
    for extra in task.get("context_files") or []:
        if isinstance(extra, str) and extra not in context_files:
            context_files.append(extra)

    for rel in context_files:
        if remaining <= 0:
            truncated.append({"path": rel, "reason": "budget exhausted"})
            continue
        resolved, err = resolve_bounded_path(source_root, rel)
        if err or resolved is None:
            truncated.append({"path": rel, "reason": f"unresolvable path ({err})"})
            continue
        if not resolved.is_file():
            truncated.append({"path": rel, "reason": "file does not exist"})
            continue
        try:
            content = resolved.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            truncated.append({"path": rel, "reason": "file is not readable as UTF-8 text"})
            continue
        digest = compute_sha256(resolved)
        block = f"\n\n## File: {rel}\n\n<!-- sha256: {digest} -->\n\n"
        allowance = remaining - len(block)
        if allowance <= 0:
            truncated.append({"path": rel, "reason": "budget exhausted"})
            continue
        if len(content) > allowance:
            content_allowance = allowance - len(CONTEXT_TRUNCATION_MARKER)
            if content_allowance <= 0:
                truncated.append({"path": rel, "reason": "budget exhausted"})
                continue
            sliced = content[:content_allowance]
            content = sliced + CONTEXT_TRUNCATION_MARKER
            truncated.append({"path": rel, "reason": "truncated to context budget"})
            included.append(
                {
                    "path": rel,
                    "sha256": digest,
                    "bytes": len(sliced.encode("utf-8")),
                    "truncated": True,
                }
            )
        else:
            included.append(
                {
                    "path": rel,
                    "sha256": digest,
                    "bytes": len(content.encode("utf-8")),
                    "truncated": False,
                }
            )
        block += content
        sections.append(block)
        remaining -= len(block)

    pack = "".join(sections)
    digest = hashlib.sha256(pack.encode("utf-8")).hexdigest()
    meta = {
        "task_id": task["task_id"],
        "budget_chars": budget_chars,
        "pack_chars": len(pack),
        "pack_sha256": digest,
        "files_included": included,
        "files_truncated": truncated,
    }
    return pack, meta


# --------------------------------------------------------------------------
# Verification & evidence
# --------------------------------------------------------------------------


def evidence_dir(project_root: pathlib.Path, task_id: str) -> pathlib.Path:
    return artifact_dir(project_root, "evidence") / task_id


def resolve_work_dir(project_root: pathlib.Path, raw: str | None) -> pathlib.Path:
    """Resolve the runner's scratch directory: context packs and agent logs.

    With no explicit path it sits under the project's evidence directory, so
    the runner's own writes land beside the evidence they produce and are
    recognised as runner-owned by the escape check.

    An explicit path must stay under the project root. A directory outside it
    could never be expressed as a repository-relative path, so the escape
    check could not recognise the runner's own writes there and would report
    them as an escape; refusing the path is clearer than that.
    """
    if not raw:
        return artifact_dir(project_root, "evidence") / "runner"
    candidate = pathlib.Path(raw)
    if not candidate.is_absolute():
        candidate = project_root / candidate
    try:
        candidate.resolve().relative_to(project_root.resolve())
    except (ValueError, OSError):
        raise RunnerError(
            f"Work directory must be inside the project root: {candidate}"
        ) from None
    return candidate


def repo_relative(project_root: pathlib.Path, target: pathlib.Path) -> str:
    """Return ``target`` as a repository-relative, forward-slash path.

    The escape check compares paths in the same form ``git status
    --porcelain=v1`` reports, so a runner-owned path must be spelled the same
    way on both sides of the comparison. Only a path under the project root
    can be owned: a path outside it has no repository-relative spelling, so
    it is never treated as runner-owned.
    """
    try:
        relative = target.resolve().relative_to(project_root.resolve())
    except (ValueError, OSError):
        return ""
    return relative.as_posix()


def next_attempt_index(directory: pathlib.Path, log_prefix: str = "verify") -> int:
    """Return the next free attempt number for a log stem in a directory."""
    if not directory.is_dir():
        return 1
    indexes = []
    pattern = re.compile(rf"{re.escape(log_prefix)}-(\d+)\.log$")
    for entry in directory.glob(f"{log_prefix}-*.log"):
        match = pattern.match(entry.name)
        if match:
            indexes.append(int(match.group(1)))
    return max(indexes) + 1 if indexes else 1


def run_verification(
    task: dict[str, Any],
    project_root: pathlib.Path,
    timeout_seconds: int = DEFAULT_VERIFY_TIMEOUT_SECONDS,
    work_dir: pathlib.Path | None = None,
    branch: str | None = None,
    commit: str | None = None,
    log_dir: pathlib.Path | None = None,
    log_prefix: str = "verify",
) -> dict[str, Any]:
    """Execute the task's prescribed verification command and capture evidence.

    The command is executed without a shell: it is split with ``shlex`` and run
    as an argv, so plan text cannot inject shell syntax.

    ``work_dir`` is the directory the command runs in. It equals the project
    root by default; under per-task isolation it is the task's worktree, so the
    command observes the isolated code rather than the user's working tree.
    The evidence itself is always written under the project root, which keeps a
    single canonical evidence location.

    ``log_dir`` and ``log_prefix`` place the log somewhere else: the
    composite's verification writes ``composite-<n>.log`` into the batch's own
    evidence directory, and the gate reads those files by that exact name.
    """
    command_text = task["verification_command"]
    try:
        argv = shlex.split(command_text)
    except ValueError as exc:
        raise RunnerError(f"Verification command cannot be parsed: {exc}") from exc
    if not argv:
        raise RunnerError("Verification command is empty.")

    cwd = work_dir or project_root
    if not cwd.is_dir():
        raise RunnerError(f"Verification working directory does not exist: {cwd}")

    directory = log_dir or evidence_dir(project_root, task["task_id"])
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RunnerError(f"Evidence directory cannot be created: {directory} ({exc})") from exc
    attempt = next_attempt_index(directory, log_prefix)
    log_path = directory / f"{log_prefix}-{attempt}.log"

    try:
        completed = subprocess.run(  # noqa: S603 - argv from the plan, no shell
            argv,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
            check=False,
        )
        exit_code = completed.returncode
        output = completed.stdout.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        partial = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else ""
        output = partial + f"\n<!-- verification timed out after {timeout_seconds}s -->\n"
    except FileNotFoundError:
        exit_code = 127
        output = f"<!-- verification command not found: {argv[0]} -->\n"

    header = f"$ {' '.join(shlex.quote(part) for part in argv)}\nexit_code: {exit_code}\n"
    if branch:
        header += f"branch: {branch}\n"
    if commit:
        header += f"commit: {commit}\n"
    header += f"cwd: {cwd}\n\n"
    try:
        log_path.write_text(header + output, encoding="utf-8")
    except OSError as exc:
        raise RunnerError(f"Evidence log cannot be written: {log_path} ({exc})") from exc

    return {
        "task_id": task["task_id"],
        "command": command_text,
        "exit_code": exit_code,
        "passed": exit_code == 0,
        "expected_outcome": task["expected_outcome"],
        "evidence_path": log_path.relative_to(project_root).as_posix(),
        "evidence_sha256": compute_sha256(log_path),
        "timeout_seconds": timeout_seconds,
        "cwd": str(cwd),
        "branch": branch,
        "commit": commit,
    }


# --------------------------------------------------------------------------
# Verbs
# --------------------------------------------------------------------------


def verb_next(args: argparse.Namespace) -> int:
    project_root = pathlib.Path(args.project_root).resolve()
    if not project_root.is_dir():
        raise RunnerError(f"Project root is not a directory: {project_root}")
    manifest, bodies, findings = load_manifest(pathlib.Path(args.plan), project_root)
    accepted = parse_accepted(args.accepted, args.accepted_file)
    ready, requires_human, blocked = compute_ready(manifest, accepted)
    result = _envelope(
        "next",
        findings,
        {
            "workflow_id": manifest.get("workflow_id"),
            "accepted": sorted(accepted),
            "ready": ready,
            "requires_human": requires_human,
            "blocked": blocked,
            "next_task_id": ready[0]["task_id"] if ready else None,
        },
    )
    _print(result, args.format)
    return 0 if result["valid"] else 1


def verb_context(args: argparse.Namespace) -> int:
    project_root = pathlib.Path(args.project_root).resolve()
    if not project_root.is_dir():
        raise RunnerError(f"Project root is not a directory: {project_root}")
    manifest, bodies, findings = load_manifest(pathlib.Path(args.plan), project_root)
    task = find_task(manifest, args.task)
    worktree = resolve_worktree(project_root, args.worktree)
    pack, meta = assemble_context(
        manifest,
        task,
        project_root,
        args.budget_chars,
        bodies.get(task['task_id'], ''),
        work_root=worktree,
    )
    if args.out:
        out_path = pathlib.Path(args.out)
        if not out_path.is_absolute():
            out_path = project_root / out_path
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(pack, encoding="utf-8")
        except OSError as exc:
            raise RunnerError(f"Context pack cannot be written: {out_path} ({exc})") from exc
        meta["output_path"] = str(out_path)
    result = _envelope("context", findings, {"context": meta})
    if args.format == "json":
        _print(result, args.format)
    else:
        if args.out:
            _print(result, args.format)
        else:
            sys.stdout.write(pack)
    return 0 if result["valid"] else 1


def verb_verify(args: argparse.Namespace) -> int:
    project_root = pathlib.Path(args.project_root).resolve()
    if not project_root.is_dir():
        raise RunnerError(f"Project root is not a directory: {project_root}")
    manifest, bodies, findings = load_manifest(pathlib.Path(args.plan), project_root)
    task = find_task(manifest, args.task)
    worktree = resolve_worktree(project_root, args.worktree)
    outcome = run_verification(task, project_root, args.timeout, work_dir=worktree)
    result = _envelope("verify", findings, {"verification": outcome})
    _print(result, args.format)
    return 0 if result["valid"] and outcome["passed"] else 1


def resolve_worktree(project_root: pathlib.Path, raw: str | None) -> pathlib.Path | None:
    """Resolve an operator-supplied worktree path inside the project root."""
    if not raw:
        return None
    candidate = pathlib.Path(raw)
    if not candidate.is_absolute():
        candidate = project_root / raw
    resolved, err = resolve_bounded_path(project_root, str(candidate))
    if err or resolved is None:
        raise RunnerError(f"Worktree path is not bounded by the project root: {raw} ({err}).")
    if not resolved.is_dir():
        raise RunnerError(f"Worktree path is not a directory: {resolved}")
    return resolved


def substitute_argv(argv_template: list[str], substitutions: dict[str, str]) -> list[str]:
    """Replace ``{placeholder}`` tokens in an argv template.

    ``str.format`` is not used: an operator-supplied command may legitimately
    contain braces (a JSON payload, a shell-free format string), and those must
    reach the agent command untouched. Only the exact tokens this runner
    defines are substituted.
    """
    resolved: list[str] = []
    for part in argv_template:
        for token, value in substitutions.items():
            part = part.replace(token, value)
        resolved.append(part)
    return resolved


def run_agent_in_worktree(
    task: dict[str, Any],
    manifest: dict[str, Any],
    bodies: dict[str, str],
    project_root: pathlib.Path,
    worktree_path: pathlib.Path,
    branch: str,
    argv_template: list[str],
    work_dir: pathlib.Path,
    agent_timeout: int,
    timeout_seconds: int,
    budget_chars: int = DEFAULT_CONTEXT_BUDGET_CHARS,
    *,
    constitution_excerpt: str | None = None,
    project_config_excerpt: str | None = None,
) -> dict[str, Any]:
    """Run one task's agent inside its worktree and verify it there.

    The order is mechanical: assemble the context pack **from the worktree**
    (so the worker sees the state its own branch will merge), hand it the
    pack, let the agent edit, commit what it left behind, and run the task's
    verification command *inside* the worktree.

    The returned ``category`` is the batch's member taxonomy: ``green`` when
    the agent exited ``0``, the verification is green, and a commit was
    produced; ``no-op`` when the agent exited ``0`` and the verification is
    green but nothing was committed; ``red`` otherwise.
    """
    task_id = task["task_id"]
    pack, meta = assemble_context(
        manifest,
        task,
        project_root,
        budget_chars,
        bodies.get(task_id, ""),
        work_root=worktree_path,
        constitution_excerpt=constitution_excerpt,
        project_config_excerpt=project_config_excerpt,
    )
    pack_path = work_dir / f"context-{task_id}.md"
    pack_path.write_text(pack, encoding="utf-8")
    substitutions = {
        "{prompt_file}": str(pack_path),
        "{workspace}": str(worktree_path),
        "{task_id}": task_id,
    }
    argv = substitute_argv(argv_template, substitutions)

    agent_exit = 0
    agent_output = ""
    try:
        agent = subprocess.run(  # noqa: S603 - operator-supplied argv, no shell
            argv,
            cwd=str(worktree_path),
            input=pack.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=agent_timeout,
            check=False,
        )
        agent_exit = agent.returncode
        agent_output = agent.stdout.decode("utf-8", errors="replace")
    except FileNotFoundError:
        agent_exit, agent_output = 127, f"<!-- agent command not found: {argv[0]} -->"
    except subprocess.TimeoutExpired:
        agent_exit, agent_output = 124, f"<!-- agent timed out after {agent_timeout}s -->"
    agent_log = work_dir / f"agent-{task_id}.log"
    agent_log.write_text(agent_output, encoding="utf-8")

    committed: dict[str, Any] = {"committed": False, "reason": "agent did not run"}
    commit = branch_commit(worktree_path, "HEAD")
    if agent_exit == 0:
        try:
            committed = commit_task_work(worktree_path, task_id, task["title"])
        except IsolationError as exc:
            raise RunnerError(str(exc), exc.findings) from exc
        commit = committed.get("commit")

    outcome = run_verification(
        task,
        project_root,
        timeout_seconds,
        work_dir=worktree_path,
        branch=branch,
        commit=commit,
    )

    if agent_exit == 0 and outcome["passed"] and committed.get("committed"):
        category = "green"
    elif agent_exit == 0 and outcome["passed"]:
        category = "no-op"
    else:
        category = "red"

    return {
        "task_id": task_id,
        "branch": branch,
        "commit": commit,
        "agent_exit_code": agent_exit,
        "agent_log": agent_log.relative_to(project_root).as_posix(),
        "committed": bool(committed.get("committed")),
        "context": meta,
        "verification": outcome,
        "category": category,
        "changed_paths": [],
        "undeclared_paths": [],
    }


def verb_isolate(args: argparse.Namespace) -> int:
    """Run one task in its own worktree and integrate it when it verifies green.

    The order is fixed and mechanical: prepare the worktree, hand the worker a
    bounded context assembled from that worktree, let the worker edit, run the
    task's own verification command *inside* the worktree, commit the result on
    the task branch, and merge that branch into the integration branch. A task
    whose verification did not exit 0 is never merged.
    """
    project_root = pathlib.Path(args.project_root).resolve()
    if not project_root.is_dir():
        raise RunnerError(f"Project root is not a directory: {project_root}")
    manifest, bodies, findings = load_manifest(pathlib.Path(args.plan), project_root)
    task = find_task(manifest, args.task)

    argv_template = json.loads(args.agent_command)
    if not isinstance(argv_template, list) or not argv_template or not all(
        isinstance(part, str) for part in argv_template
    ):
        raise RunnerError("--agent-command must be a JSON array of strings.")

    lock = IntegrationLock(project_root)
    try:
        lock.acquire()
    except IsolationError as exc:
        raise RunnerError(str(exc), exc.findings) from exc
    try:
        try:
            prepared = prepare_isolation(
                project_root,
                args.worktree_root,
                args.base_ref,
                task["task_id"],
                task["title"],
                args.add_ignore,
                dry_run=args.dry_run,
            )
        except IsolationError as exc:
            raise RunnerError(str(exc), exc.findings) from exc

        integration = prepared["integration"]
        worktree = prepared["task"]
        if worktree is None:
            raise RunnerError("Isolation did not produce a task worktree.")
        worktree_path = pathlib.Path(worktree["worktree_path"])
        branch = worktree["branch"]

        if args.dry_run:
            # A dry run creates nothing: report the layout it would use and stop.
            result = _envelope(
                "isolate",
                findings,
                {
                    "workflow_id": manifest.get("workflow_id"),
                    "task_id": task["task_id"],
                    "title": task["title"],
                    "branch": branch,
                    "worktree_path": str(worktree_path),
                    "integration_branch": integration["branch"],
                    "dry_run": True,
                    "merged": {"merged": False, "reason": "dry run"},
                },
            )
            _print(result, args.format)
            return 0 if result["valid"] else 1

        work_dir = resolve_work_dir(project_root, args.work_dir)
        try:
            work_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise RunnerError(f"Work directory cannot be created: {work_dir} ({exc})") from exc

        # Snapshot the main working tree immediately before the agent runs, so the
        # comparison afterwards isolates what the *agent* changed. The runner's own
        # writes (the context pack and the evidence directory) are already in place
        # at this point and are therefore not mistaken for an escape.
        owned = _owned_runner_paths(project_root, work_dir)
        before_state = snapshot_tree_state(
            project_root, owned_prefixes=owned[0], owned_paths=owned[1]
        )

        result = run_agent_in_worktree(
            task,
            manifest,
            bodies,
            project_root,
            worktree_path,
            branch,
            argv_template,
            work_dir,
            args.agent_timeout,
            args.timeout,
            args.budget_chars,
        )
        meta = result["context"]
        agent_exit = result["agent_exit_code"]
        agent_log = result["agent_log"]
        commit = result["commit"]
        outcome = result["verification"]

        # The isolation boundary is only real if the agent's writes stayed inside
        # the worktree. Compare the main working tree before and after the agent
        # ran: any path whose content hash changed there means the agent escaped
        # its sandbox, and a task that escaped is never merged. Comparing hashes
        # rather than path sets is what catches a path that was already dirty
        # before the run and was modified further by the agent.
        escaped = _batch_escape_paths(project_root, before_state, work_dir, owned=owned)
        if escaped:
            raise RunnerError(
                "The agent modified files outside its worktree; the task is not mergeable.",
                [
                    make_error(
                        "worktree_escape_detected",
                        str(project_root),
                        "The agent left changes in the main working tree: "
                        + ", ".join(escaped)
                        + ". Isolation requires the worker to operate inside its worktree.",
                    )
                ],
            )

        merged: dict[str, Any] = {"merged": False, "reason": "verification did not pass"}
        if outcome["passed"] and agent_exit == 0:
            try:
                merged = merge_task_branch(
                    project_root,
                    integration["worktree_rel"],
                    branch,
                    task["task_id"],
                    task["title"],
                    project_root=project_root,
                    evidence={
                        "passed": True,
                        "branch": branch,
                        "commit": commit,
                    },
                )
            except IsolationError as exc:
                raise RunnerError(str(exc), exc.findings) from exc

        result = _envelope(
            "isolate",
            findings,
            {
                "workflow_id": manifest.get("workflow_id"),
                "task_id": task["task_id"],
                "title": task["title"],
                "branch": branch,
                "worktree_path": str(worktree_path),
                "integration_branch": integration["branch"],
                "context": meta,
                "agent_exit_code": agent_exit,
                "agent_log": agent_log,
                "commit": commit,
                "verification": outcome,
                "merged": merged,
            },
        )
        _print(result, args.format)
        return 0 if result["valid"] and outcome["passed"] and merged.get("merged") else 1
    finally:
        lock.release()


# --------------------------------------------------------------------------
# Batch execution
# --------------------------------------------------------------------------


def _changed_paths(repo: pathlib.Path, base_commit: str, commit: str | None) -> list[str]:
    """Return the paths a member changed relative to the batch's base."""
    if not commit:
        return []
    code, out, err = run_git(
        ["diff", "--name-only", f"{base_commit}..{commit}"], repo
    )
    if code != 0:
        return []
    return sorted(line.strip() for line in out.splitlines() if line.strip())


def _owned_runner_paths(
    project_root: pathlib.Path,
    work_dir: pathlib.Path,
    state_path: pathlib.Path | None = None,
) -> tuple[list[str], list[str]]:
    """Return (owned_prefixes, owned_paths) relative to ``project_root``."""
    resolved_state = state_path or resolve_state_path(project_root, None)
    return (
        [
            repo_relative(project_root, artifact_dir(project_root, "evidence")),
            repo_relative(project_root, work_dir),
        ],
        [
            repo_relative(project_root, lock_path(project_root)),
            repo_relative(project_root, resolved_state),
        ],
    )


def _batch_escape_paths(
    project_root: pathlib.Path,
    before_state: dict[str, str],
    work_dir: pathlib.Path,
    state_path: pathlib.Path | None = None,
    owned: tuple[list[str], list[str]] | None = None,
) -> list[str]:
    """Return main-tree changes outside the runner's artifact paths."""
    owned_prefixes, owned_paths = owned or _owned_runner_paths(
        project_root, work_dir, state_path
    )
    after_state = snapshot_tree_state(
        project_root,
        owned_prefixes=owned_prefixes,
        owned_paths=owned_paths,
    )
    return escape_paths(
        before_state,
        after_state,
        owned_prefixes=owned_prefixes,
        owned_paths=owned_paths,
    )


def _accepted_set_findings(
    project_root: pathlib.Path,
    repo: pathlib.Path,
    accepted: set[str],
    base_commit: str | None,
    state_path: pathlib.Path | None = None,
    state: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Check the accepted set against the integration branch's actual content.

    An accepted task id claims "this task's work is already in the integration
    branch". When the isolation state names the commit the task was merged at,
    that claim is checkable: the commit must be an ancestor of the branch's
    tip. When it is not, the branch does not hold the work the plan says it
    holds, and verifying a tree that lacks it would be a false result.

    An accepted id with no state entry was seeded by the operator and cannot be
    checked this way; it is a warning, not an error.
    """
    findings: list[dict[str, str]] = []
    loaded_state = (
        state
        if state is not None
        else load_state(state_path or resolve_state_path(project_root, None))
    )
    for task_id in sorted(accepted):
        entry = loaded_state.get("tasks", {}).get(task_id)
        if not isinstance(entry, dict):
            findings.append(
                make_warning(
                    "batch_accepted_unverified",
                    task_id,
                    f"Task {task_id} is accepted but the isolation state holds no "
                    f"entry for it, so its integration cannot be verified against "
                    f"the integration branch.",
                )
            )
            continue
        merge_commit = entry.get("merge_commit")
        if not isinstance(merge_commit, str) or not merge_commit:
            continue
        if not base_commit:
            continue
        code, _, _ = run_git(
            ["merge-base", "--is-ancestor", merge_commit, base_commit], repo
        )
        if code != 0:
            findings.append(
                make_error(
                    "batch_accepted_not_integrated",
                    task_id,
                    f"Task {task_id} is accepted, but its merge commit {merge_commit} "
                    f"is not an ancestor of the integration branch's tip {base_commit}. "
                    f"The branch does not hold the work the plan says is already "
                    f"there, so the batch would verify a tree that lacks it.",
                )
            )
    return findings


def _expected_base_commit(repo: pathlib.Path, base_ref: str | None) -> str | None:
    """Resolve the batch's base commit without creating any branch or worktree."""
    if branch_exists(repo, INTEGRATION_BRANCH):
        return branch_commit(repo, INTEGRATION_BRANCH)
    start_point = base_ref or "HEAD"
    code, out, _ = run_git(["rev-parse", "--verify", "--quiet", f"{start_point}^{{commit}}"], repo)
    if code != 0:
        return None
    return out.strip() or None


def _prepare_batch_members(
    manifest: dict[str, Any],
    project_root: pathlib.Path,
    member_ids: list[str],
    options: dict[str, Any],
) -> tuple[str, dict[str, Any], str, str, list[dict[str, Any]]]:
    """Run batch preflight, ensure integration base, and prepare member worktrees."""
    worktree_root = options["worktree_root"]
    try:
        require_repo(project_root)
        expected_base = _expected_base_commit(project_root, options.get("base_ref"))
        if expected_base is not None:
            for task_id in sorted(member_ids):
                task = find_task(manifest, task_id)
                check_task_branch_tip(project_root, task_id, task["title"], expected_base)
    except IsolationError as exc:
        raise RunnerError(str(exc), exc.findings) from exc

    try:
        prepared = prepare_isolation(
            project_root,
            worktree_root,
            options.get("base_ref"),
            None,
            None,
            options.get("add_ignore", False),
        )
    except IsolationError as exc:
        raise RunnerError(str(exc), exc.findings) from exc
    integration = prepared["integration"]
    base_commit = branch_commit(project_root, INTEGRATION_BRANCH)
    if not base_commit:
        raise RunnerError(
            "The integration branch has no commit to branch from.",
            [
                make_error(
                    "batch_no_base_commit",
                    INTEGRATION_BRANCH,
                    f"The integration branch {INTEGRATION_BRANCH} has no commit.",
                )
            ],
        )

    batch_id = batch.batch_id(base_commit, member_ids)
    composite_branch = batch.composite_branch_name(batch_id)

    members: list[dict[str, Any]] = []
    for task_id in sorted(member_ids):
        task = find_task(manifest, task_id)
        try:
            worktree_info = ensure_task_worktree(
                project_root,
                worktree_root,
                task_id,
                task["title"],
                base_commit,
                require_tip=base_commit,
            )
        except IsolationError as exc:
            raise RunnerError(str(exc), exc.findings) from exc
        members.append(
            {
                "task_id": task_id,
                "title": task["title"],
                "task": task,
                "branch": worktree_info["branch"],
                "worktree_path": worktree_info["worktree_path"],
                "worktree_rel": worktree_info["worktree_rel"],
                "worktree": worktree_info,
            }
        )
    return base_commit, integration, batch_id, composite_branch, members


def _prepare_batch_state(
    project_root: pathlib.Path,
    work_dir: pathlib.Path,
    members: list[dict[str, Any]],
    options: dict[str, Any],
) -> tuple[pathlib.Path, dict[str, Any]]:
    """Resolve/load isolation state, clear stale failure markers, and create work_dir."""
    provided_path = options.get("state_path")
    if isinstance(provided_path, pathlib.Path):
        state_path = provided_path
    else:
        try:
            state_path = resolve_state_path(project_root, options.get("state"))
        except IsolationError as exc:
            raise RunnerError(str(exc), exc.findings) from exc
    provided_state = options.get("isolation_state")
    state = provided_state if isinstance(provided_state, dict) else load_state(state_path)

    # Clear any prior batch failure marker once the member is prepared for
    # this batch: a stale marker from an earlier batch must not block a retry.
    cleared = False
    for member in members:
        if clear_batch_failure(state_path, state, member["task_id"], save=False):
            cleared = True
    if cleared:
        save_state(state_path, state)

    try:
        work_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RunnerError(f"Work directory cannot be created: {work_dir} ({exc})") from exc
    return state_path, state


def _run_and_categorize_members(
    manifest: dict[str, Any],
    bodies: dict[str, str],
    project_root: pathlib.Path,
    members: list[dict[str, Any]],
    base_commit: str,
    before_state: dict[str, str],
    work_dir: pathlib.Path,
    state_path: pathlib.Path,
    owned: tuple[list[str], list[str]],
    options: dict[str, Any],
) -> tuple[list[dict[str, str]], bool]:
    """Run batch members concurrently, detect escapes, and collect findings."""
    findings: list[dict[str, str]] = []
    argv_template = options["argv_template"]
    agent_timeout = options["agent_timeout"]
    timeout_seconds = options["timeout_seconds"]
    budget_chars = options.get("budget_chars", DEFAULT_CONTEXT_BUDGET_CHARS)
    constitution_excerpt = options.get("constitution_excerpt")
    if constitution_excerpt is None:
        constitution_excerpt = _constitution_excerpt()
    project_config_excerpt = options.get("project_config_excerpt")
    if project_config_excerpt is None:
        project_config_excerpt = _project_config_excerpt(project_root)

    def run_member(member: dict[str, Any]) -> dict[str, Any]:
        return run_agent_in_worktree(
            member["task"],
            manifest,
            bodies,
            project_root,
            pathlib.Path(member["worktree_path"]),
            member["branch"],
            argv_template,
            work_dir,
            agent_timeout,
            timeout_seconds,
            budget_chars,
            constitution_excerpt=constitution_excerpt,
            project_config_excerpt=project_config_excerpt,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(members))) as pool:
        outcomes = list(pool.map(run_member, members))

    escaped_paths = _batch_escape_paths(
        project_root, before_state, work_dir, state_path, owned=owned
    )
    escaped = bool(escaped_paths)
    if escaped:
        findings.append(
            make_error(
                "worktree_escape_detected",
                str(project_root),
                "A batch member modified files outside its worktree: "
                + ", ".join(escaped_paths)
                + ". Isolation requires workers to operate inside their own worktrees.",
            )
        )

    for member, outcome in zip(members, outcomes):
        member["result"] = outcome
        member["category"] = outcome["category"]
        member["commit"] = outcome["commit"]
        member["agent_exit_code"] = outcome["agent_exit_code"]
        member["verification"] = outcome["verification"]
        if outcome["category"] == "red":
            if outcome["agent_exit_code"] != 0:
                findings.append(
                    make_error(
                        "batch_task_agent_failed",
                        member["task_id"],
                        f"Task {member['task_id']} was excluded: its agent exited "
                        f"{outcome['agent_exit_code']}, not 0.",
                    )
                )
            else:
                findings.append(
                    make_error(
                        "batch_task_verification_failed",
                        member["task_id"],
                        f"Task {member['task_id']} was excluded: its own verification "
                        f"exited {outcome['verification'].get('exit_code')}, not 0.",
                    )
                )

    for member in members:
        changed = _changed_paths(
            pathlib.Path(member["worktree_path"]), base_commit, member["commit"]
        )
        declared = member["task"].get("target_files") or []
        undeclared = batch.undeclared_paths(declared, changed)
        member["changed_paths"] = changed
        member["undeclared_paths"] = undeclared
        if undeclared:
            findings.append(
                make_warning(
                    "batch_undeclared_write",
                    member["task_id"],
                    f"Task {member['task_id']} changed paths its declared "
                    f"target_files do not cover: {', '.join(undeclared)}.",
                )
            )
    return findings, escaped


def _integrate_batch_members(
    *,
    repo: pathlib.Path,
    project_root: pathlib.Path,
    integration: dict[str, Any],
    members: list[dict[str, Any]],
    base_commit: str,
    batch_id: str,
    composite_branch: str,
    timeout_seconds: int,
    before_state: dict[str, str],
    work_dir: pathlib.Path,
    state_path: pathlib.Path,
    state: dict[str, Any],
    owned: tuple[list[str], list[str]],
    escaped: bool,
) -> dict[str, Any]:
    """Integrate green batch members directly (singleton) or via composite."""
    green = [m for m in members if m["category"] == "green"]
    red = [m for m in members if m["category"] == "red"]
    findings: list[dict[str, str]] = []
    integration_findings: list[dict[str, str]] = []
    composite: dict[str, Any] | None = None
    integrated = False
    merge_commit: str | None = None
    record_path: pathlib.Path | None = None
    record_sha256: str | None = None
    exit_codes: dict[str, int] = {}
    verifications: dict[str, dict[str, Any]] = {}
    composite_red = False
    conflict_occurred = False

    if escaped:
        # An escaping member may have modified the user's working tree. Do not
        # integrate any branch from this batch, even if its own verification is green.
        integrated = False
    elif not green:
        # Nothing to integrate. The batch fails when a member was red and
        # succeeds when every member needed no work at all.
        integrated = not red
    elif len(green) == 1:
        # A lone green member has no combination to verify: it integrates on
        # its own green evidence, which is exactly the guarantee `isolate`
        # gives.
        member = green[0]
        try:
            merged = merge_task_branch(
                repo,
                integration["worktree_rel"],
                member["branch"],
                member["task_id"],
                member["title"],
                project_root=project_root,
                evidence={
                    "passed": True,
                    "branch": member["branch"],
                    "commit": member["commit"],
                },
                state_path=state_path,
                state=state,
            )
        except IsolationError as exc:
            merge_findings = exc.findings or [
                make_error("merge_not_verified", member["task_id"], str(exc))
            ]
            findings.extend(merge_findings)
            integration_findings.extend(merge_findings)
            conflict_occurred = True
        else:
            integrated = True
            merge_commit = merged.get("merge_commit")
            member["merge_commit"] = merge_commit
            member["verified_commit"] = member["commit"]
    else:
        outcome = _integrate_composite(
            repo,
            project_root,
            integration,
            green,
            base_commit,
            batch_id,
            composite_branch,
            timeout_seconds,
            before_state,
            work_dir,
            state_path,
            owned=owned,
        )
        findings.extend(outcome["findings"])
        integration_findings.extend(outcome["findings"])
        composite = outcome["composite"]
        if outcome["integrated"]:
            integrated = True
            merge_commit = outcome["merge_commit"]
            for member in green:
                member["merge_commit"] = merge_commit
                member["verified_commit"] = outcome["composite"]["commit"]
        record_path = outcome.get("record_path")
        record_sha256 = outcome.get("record_sha256")
        exit_codes = outcome.get("exit_codes", {})
        verifications = outcome.get("verifications", {})
        composite_red = bool(outcome.get("composite_red"))
        conflict_occurred = bool(outcome.get("conflict_occurred"))
        if any(f.get("code") == "worktree_escape_detected" for f in outcome["findings"]):
            escaped = True

    return {
        "integrated": integrated,
        "merge_commit": merge_commit,
        "composite": composite,
        "record_path": record_path,
        "record_sha256": record_sha256,
        "exit_codes": exit_codes,
        "verifications": verifications,
        "composite_red": composite_red,
        "conflict_occurred": conflict_occurred,
        "integration_findings": integration_findings,
        "findings": findings,
        "escaped": escaped,
    }


def _persist_batch_state(
    project_root: pathlib.Path,
    state_path: pathlib.Path,
    state: dict[str, Any],
    batch_id: str,
    composite_branch: str,
    members: list[dict[str, Any]],
    integration_outcome: dict[str, Any],
) -> None:
    """Persist member isolation entries and any batch failure markers in phases."""
    integrated = integration_outcome["integrated"]
    escaped = integration_outcome["escaped"]
    composite = integration_outcome["composite"]
    record_path = integration_outcome["record_path"]
    record_sha256 = integration_outcome["record_sha256"]
    exit_codes = integration_outcome["exit_codes"]
    conflict_occurred = integration_outcome["conflict_occurred"]

    for member in members:
        was_integrated = bool(member.get("merge_commit")) and integrated
        entry: dict[str, Any] = {
            "branch": member["branch"],
            "worktree_path": member["worktree_path"],
            "worktree_rel": member["worktree_rel"],
            "merged": was_integrated,
            "accepted": (not escaped)
            and member["category"] in ("green", "no-op")
            and (was_integrated or member["category"] == "no-op"),
            "batch_id": batch_id,
            "commit": member["commit"],
            "merge_commit": member.get("merge_commit"),
            "verified_commit": member.get("verified_commit") or member["commit"],
        }
        record_task_entry(state_path, state, member["task_id"], entry, save=False)
    if members:
        save_state(state_path, state)

    if not integrated and (record_path is not None or conflict_occurred):
        marker = {
            "batch_id": batch_id,
            "composite_branch": composite_branch,
            "composite_commit": composite["commit"] if composite else None,
            "composite_record_path": (
                record_path.relative_to(project_root).as_posix()
                if record_path is not None
                else None
            ),
            "composite_record_sha256": record_sha256,
        }
        for member in members:
            per_member = dict(marker)
            per_member["member_exit_code"] = member["verification"].get("exit_code")
            per_member["composite_exit_code"] = exit_codes.get(member["task_id"])
            record_batch_failure(
                state_path, state, member["task_id"], per_member, save=False
            )
        if members:
            save_state(state_path, state)


def execute_batch(
    manifest: dict[str, Any],
    bodies: dict[str, str],
    project_root: pathlib.Path,
    member_ids: list[str],
    options: dict[str, Any],
) -> dict[str, Any]:
    """Run one batch end to end and return what it did.

    Every member branches from the same base commit, so the members are
    siblings rather than a chain. The green members are merged into a scratch
    composite branch, and the composite is verified with **every** green
    member's command before it reaches the integration branch: the gate proves
    the combination, not just each part.

    The caller holds the integration lock for the whole batch.
    """
    work_dir = options["work_dir"]
    timeout_seconds = options["timeout_seconds"]

    base_commit, integration, batch_id, composite_branch, members = (
        _prepare_batch_members(manifest, project_root, member_ids, options)
    )
    state_path, state = _prepare_batch_state(project_root, work_dir, members, options)

    # The escape check spans the whole batch, including the composite phase:
    # a write into the main tree after the members finished is still an escape.
    owned = _owned_runner_paths(project_root, work_dir, state_path)
    before_state = snapshot_tree_state(
        project_root, owned_prefixes=owned[0], owned_paths=owned[1]
    )

    findings, escaped = _run_and_categorize_members(
        manifest,
        bodies,
        project_root,
        members,
        base_commit,
        before_state,
        work_dir,
        state_path,
        owned,
        options,
    )

    integration_outcome = _integrate_batch_members(
        repo=project_root,
        project_root=project_root,
        integration=integration,
        members=members,
        base_commit=base_commit,
        batch_id=batch_id,
        composite_branch=composite_branch,
        timeout_seconds=timeout_seconds,
        before_state=before_state,
        work_dir=work_dir,
        state_path=state_path,
        state=state,
        owned=owned,
        escaped=escaped,
    )
    findings.extend(integration_outcome["findings"])

    _persist_batch_state(
        project_root,
        state_path,
        state,
        batch_id,
        composite_branch,
        members,
        integration_outcome,
    )

    integrated = integration_outcome["integrated"]
    review_dispatch = _dispatch_batch_reviews(
        project_root=project_root,
        base_commit=base_commit,
        members=members,
        findings=findings,
        integration_findings=integration_outcome["integration_findings"],
        composite_exit_codes=integration_outcome["exit_codes"],
        composite_verifications=integration_outcome["verifications"],
        composite_red=integration_outcome["composite_red"],
        conflict_occurred=integration_outcome["conflict_occurred"],
    )

    return {
        "batch_id": batch_id,
        "base_commit": base_commit,
        "members": [
            {
                "task_id": member["task_id"],
                "title": member["title"],
                "branch": member["branch"],
                "worktree_path": member["worktree_path"],
                "commit": member["commit"],
                "category": member["category"],
                "agent_exit_code": member["agent_exit_code"],
                "agent_log": member["result"]["agent_log"],
                "context": member["result"]["context"],
                "verification": member["verification"],
                "changed_paths": member["changed_paths"],
                "undeclared_paths": member["undeclared_paths"],
                "integrated": bool(member.get("merge_commit")) and integrated,
            }
            for member in members
        ],
        "integrated": integrated,
        "composite": integration_outcome["composite"],
        "findings": findings,
        "review_dispatch": review_dispatch,
    }


def _dispatch_batch_reviews(
    *,
    project_root: pathlib.Path,
    base_commit: str,
    members: list[dict[str, Any]],
    findings: list[dict[str, str]],
    integration_findings: list[dict[str, str]],
    composite_exit_codes: dict[str, int],
    composite_verifications: dict[str, dict[str, Any]],
    composite_red: bool,
    conflict_occurred: bool,
) -> list[dict[str, str]]:
    """Write fact-only review-dispatch packages for excluded or at-risk members."""
    member_rows = [
        {
            "task_id": row_member["task_id"],
            "agent_exit_code": row_member["agent_exit_code"],
            "self_verification_exit_code": (
                row_member["verification"].get("exit_code")
                if isinstance(row_member.get("verification"), dict)
                else None
            ),
            "composite_exit_code": composite_exit_codes.get(row_member["task_id"]),
        }
        for row_member in members
    ]
    combination_dependent_task_ids = [
        row["task_id"]
        for row in member_rows
        if row["composite_exit_code"] is not None
        and row["self_verification_exit_code"] is not None
        and row["composite_exit_code"] != row["self_verification_exit_code"]
    ]
    integration_error_codes = list(
        dict.fromkeys(
            f["code"]
            for f in integration_findings
            if f.get("severity") == "error" and f.get("code")
        )
    )
    project_target = str(project_root)

    dispatches: list[dict[str, str]] = []
    for member in members:
        is_red = member["category"] == "red"
        is_at_risk_green = (composite_red or conflict_occurred) and member[
            "category"
        ] == "green"
        if not (is_red or is_at_risk_green):
            continue

        if is_red:
            member_findings = list(
                dict.fromkeys(
                    f["code"]
                    for f in findings
                    if f.get("severity") == "error"
                    and f.get("code")
                    and f.get("path") in (member["task_id"], project_target)
                )
            )
        else:
            member_findings = list(integration_error_codes)

        verification = member.get("verification")
        self_verification = {
            "exit_code": (
                verification.get("exit_code")
                if isinstance(verification, dict)
                else None
            ),
            "log_path": (
                verification.get("evidence_path")
                if isinstance(verification, dict)
                else None
            ),
            "log_sha256": (
                verification.get("evidence_sha256")
                if isinstance(verification, dict)
                else None
            ),
        }
        produced_commit = (
            member["commit"]
            if member["result"].get("committed")
            and member["commit"]
            and member["commit"] != base_commit
            else None
        )
        facts = {
            "task_id": member["task_id"],
            "title": member["title"],
            "branch": member["branch"],
            "commit": produced_commit,
            "base_commit": base_commit,
            "diff_range": (
                f"{base_commit}..{produced_commit}" if produced_commit else ""
            ),
            "self_verification": self_verification,
            "composite_verification": composite_verifications.get(member["task_id"]),
            "members": member_rows,
            "combination_dependent_task_ids": combination_dependent_task_ids,
            "declared_target_files": list(member["task"].get("target_files") or []),
            "actual_changed_paths": list(member["changed_paths"]),
            "undeclared_paths": list(member["undeclared_paths"]),
            "findings": member_findings,
        }
        dispatch_path = batch.write_review_dispatch(
            project_root, member["task_id"], facts
        )
        dispatches.append(
            {
                "task_id": member["task_id"],
                "path": repo_relative(project_root, dispatch_path),
            }
        )
    return dispatches


def _integrate_composite(
    repo: pathlib.Path,
    project_root: pathlib.Path,
    integration: dict[str, Any],
    green: list[dict[str, Any]],
    base_commit: str,
    batch_id: str,
    composite_branch: str,
    timeout_seconds: int,
    before_state: dict[str, str],
    work_dir: pathlib.Path,
    state_path: pathlib.Path | None = None,
    owned: tuple[list[str], list[str]] | None = None,
) -> dict[str, Any]:
    """Build the composite, verify it with every member's command, and merge it.

    The composite's logs live in the batch's own evidence directory, which is
    the directory the merge gate bounds them against. The record carries the
    batch's base commit, which the gate cross-checks against the base it
    derives from git.
    """
    findings: list[dict[str, str]] = []
    evidence_dir = artifact_dir(project_root, "evidence") / batch_id
    try:
        evidence_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RunnerError(
            f"The batch's evidence directory cannot be created: {evidence_dir} ({exc})"
        ) from exc

    try:
        composite = batch.build_composite(
            repo,
            integration["worktree_rel"].rsplit("/", 1)[0],
            base_commit,
            batch_id,
            [
                {
                    "task_id": member["task_id"],
                    "title": member["title"],
                    "branch": member["branch"],
                    "commit": member["commit"],
                }
                for member in green
            ],
        )
    except IsolationError as exc:
        findings.extend(exc.findings or [make_error("batch_merge_conflict", batch_id, str(exc))])
        return {
            "integrated": False,
            "composite": None,
            "findings": findings,
            "exit_codes": {},
            "verifications": {},
            "composite_red": False,
            "conflict_occurred": True,
        }

    # The composite's tip is what the members are verified at, and it is what
    # the record names.
    composite_commit = composite["commit"]
    composite_worktree = pathlib.Path(composite["worktree_path"])

    exit_codes: dict[str, int] = {}
    verifications: dict[str, dict[str, Any]] = {}
    record_members: list[dict[str, Any]] = []
    composite_red = False
    for member in sorted(green, key=lambda m: m["task_id"]):
        outcome = run_verification(
            member["task"],
            project_root,
            timeout_seconds,
            work_dir=composite_worktree,
            branch=composite_branch,
            commit=composite_commit,
            log_dir=evidence_dir,
            log_prefix="composite",
        )
        exit_codes[member["task_id"]] = outcome["exit_code"]
        verifications[member["task_id"]] = {
            "exit_code": outcome["exit_code"],
            "log_path": outcome["evidence_path"],
            "log_sha256": outcome["evidence_sha256"],
        }
        if outcome["exit_code"] != 0:
            composite_red = True
            findings.append(
                make_error(
                    "batch_composite_verification_failed",
                    member["task_id"],
                    f"The composite of batch {batch_id} failed task "
                    f"{member['task_id']}'s verification: it exited "
                    f"{outcome['exit_code']}, not 0. The members are green "
                    f"individually, so the combination is what is broken.",
                )
            )
        record_members.append(
            {
                "task_id": member["task_id"],
                "branch": member["branch"],
                "commit": member["commit"],
                "command": outcome["command"],
                "exit_code": outcome["exit_code"],
                "log_path": outcome["evidence_path"],
                "log_sha256": outcome["evidence_sha256"],
            }
        )

    record = {
        "schema_version": batch.composite_record_schema_version,
        "batch_id": batch_id,
        "base_commit": base_commit,
        "composite_branch": composite_branch,
        "composite_commit": composite_commit,
        "members": record_members,
    }
    record_path = evidence_dir / "composite-1.json"
    batch.write_composite_record(record_path, record)
    record_sha256 = compute_sha256(record_path)

    if composite_red:
        return {
            "integrated": False,
            "composite": composite,
            "findings": findings,
            "exit_codes": exit_codes,
            "verifications": verifications,
            "composite_red": True,
            "record_path": record_path,
            "record_sha256": record_sha256,
        }

    escaped = _batch_escape_paths(
        project_root, before_state, work_dir, state_path, owned=owned
    )
    if escaped:
        findings.append(
            make_error(
                "worktree_escape_detected",
                str(project_root),
                "Composite verification modified files outside its worktree: "
                + ", ".join(escaped)
                + ". Isolation requires verification to operate inside its worktree.",
            )
        )
        return {
            "integrated": False,
            "composite": composite,
            "findings": findings,
            "exit_codes": exit_codes,
            "verifications": verifications,
            "composite_red": False,
            "record_path": record_path,
            "record_sha256": record_sha256,
        }

    try:
        merged = batch.merge_composite_branch(
            repo,
            integration["worktree_rel"],
            composite_branch,
            batch_id,
            project_root,
            record_path,
        )
    except IsolationError as exc:
        findings.extend(exc.findings or [make_error("batch_merge_conflict", batch_id, str(exc))])
        return {
            "integrated": False,
            "composite": composite,
            "findings": findings,
            "exit_codes": exit_codes,
            "verifications": verifications,
            "composite_red": False,
            "record_path": record_path,
            "record_sha256": record_sha256,
            "conflict_occurred": True,
        }

    return {
        "integrated": True,
        "composite": composite,
        "findings": findings,
        "exit_codes": exit_codes,
        "verifications": verifications,
        "composite_red": False,
        "merge_commit": merged.get("merge_commit"),
        "record_path": record_path,
        "record_sha256": record_sha256,
    }


def verb_batch(args: argparse.Namespace) -> int:
    """Run a batch of independent tasks concurrently and integrate the composite.

    The selection is mechanical: the ready set, the plan's ``parallel_safe``
    flag, and a prefix-aware write-set disjointness the runner re-derives from
    the manifest. The plan's flag alone never puts two tasks in one batch.
    """
    project_root = pathlib.Path(args.project_root).resolve()
    if not project_root.is_dir():
        raise RunnerError(f"Project root is not a directory: {project_root}")
    manifest, bodies, findings = load_manifest(pathlib.Path(args.plan), project_root)

    argv_template = json.loads(args.agent_command)
    if not isinstance(argv_template, list) or not argv_template or not all(
        isinstance(part, str) for part in argv_template
    ):
        raise RunnerError("--agent-command must be a JSON array of strings.")

    pinned = [
        part.strip()
        for value in (args.tasks or [])
        for part in value.split(",")
        if part.strip()
    ]
    accepted = parse_accepted(args.accepted, args.accepted_file)
    ready, _, _ = compute_ready(manifest, accepted)
    ready_ids = [entry["task_id"] for entry in ready]

    # A pinned task that is not ready would break its dependency contract, so
    # the run is refused before any work happens.
    not_ready = [task_id for task_id in pinned if task_id not in ready_ids]
    if not_ready:
        raise RunnerError(
            "Pinned task(s) are not ready: " + ", ".join(sorted(not_ready)) + ".",
            [
                make_error(
                    "batch_task_not_ready",
                    task_id,
                    f"Task {task_id} is pinned but not ready. A task is ready when "
                    f"every dependency is accepted and the task itself is afk.",
                )
                for task_id in sorted(not_ready)
            ],
        )

    groups, selection_warnings = batch.select_batch_members(
        manifest, ready, pinned or None, args.max_concurrency, None
    )
    findings.extend(selection_warnings)

    if args.dry_run:
        planned = []
        for group in groups:
            planned.append(
                {
                    "id": batch.batch_id("base", group),
                    "size": len(group),
                    "members": group,
                    "branches": [
                        branch_name_for(task_id, find_task(manifest, task_id)["title"])
                        for task_id in group
                    ],
                    "argv": argv_template,
                }
            )
        result = _envelope(
            "batch",
            findings,
            {
                "workflow_id": manifest.get("workflow_id"),
                "batches": planned,
                "accepted": sorted(accepted),
                "failed": [],
                "review_dispatch": [],
                "dry_run": True,
            },
        )
        _print(result, args.format)
        return 0 if result["valid"] else 1

    work_dir = resolve_work_dir(project_root, args.work_dir)
    try:
        work_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RunnerError(f"Work directory cannot be created: {work_dir} ({exc})") from exc

    lock = IntegrationLock(project_root)
    try:
        lock.acquire()
    except IsolationError as exc:
        raise RunnerError(str(exc), exc.findings) from exc
    try:
        try:
            state_path = resolve_state_path(project_root, None)
        except IsolationError as exc:
            raise RunnerError(str(exc), exc.findings) from exc
        isolation_state = load_state(state_path)
        accepted = set(accepted) | set(accepted_task_ids(isolation_state))

        repo = project_root
        try:
            require_repo(project_root)
        except IsolationError as exc:
            raise RunnerError(str(exc), exc.findings) from exc
        base_commit = _expected_base_commit(repo, args.base_ref)
        accepted_findings = _accepted_set_findings(
            project_root,
            repo,
            accepted,
            base_commit,
            state_path=state_path,
            state=isolation_state,
        )
        findings.extend(accepted_findings)
        if any(f["severity"] == "error" for f in accepted_findings):
            raise RunnerError(
                "The accepted set does not match the integration branch's content.",
                accepted_findings,
            )

        options = {
            "worktree_root": args.worktree_root,
            "work_dir": work_dir,
            "argv_template": argv_template,
            "agent_timeout": args.agent_timeout,
            "timeout_seconds": args.timeout,
            "base_ref": args.base_ref,
            "add_ignore": args.add_ignore,
            "budget_chars": args.budget_chars,
            "state_path": state_path,
            "isolation_state": isolation_state,
            "constitution_excerpt": _constitution_excerpt(),
            "project_config_excerpt": _project_config_excerpt(project_root),
        }

        batches: list[dict[str, Any]] = []
        failed: set[str] = set()
        review_dispatch: list[dict[str, str]] = []
        for group in groups:
            outcome = execute_batch(manifest, bodies, project_root, group, options)
            findings.extend(outcome["findings"])
            review_dispatch.extend(outcome.get("review_dispatch", []))
            batches.append(_batch_summary(outcome))
            _apply_batch_outcome(outcome, accepted, failed)
    finally:
        lock.release()

    result = _envelope(
        "batch",
        findings,
        {
            "workflow_id": manifest.get("workflow_id"),
            "batches": batches,
            "accepted": sorted(accepted),
            "failed": sorted(failed),
            "review_dispatch": review_dispatch,
        },
    )
    _print(result, args.format)
    if not result["valid"]:
        return 1
    return 0 if not failed else 1


def _batch_summary(outcome: dict[str, Any]) -> dict[str, Any]:
    """Summarize one batch outcome for the CLI envelope."""
    composite = outcome.get("composite") or {}
    green = [m for m in outcome["members"] if m["category"] == "green"]
    return {
        "id": outcome["batch_id"],
        "size": len(outcome["members"]),
        "members": [m["task_id"] for m in outcome["members"]],
        "base_commit": outcome["base_commit"],
        "composite_branch": composite.get("branch"),
        "composite_commit": composite.get("commit"),
        "integrated": outcome["integrated"],
        "members_at_risk": len(green) if not outcome["integrated"] else 0,
    }


def _apply_batch_outcome(
    outcome: dict[str, Any],
    accepted: set[str],
    failed: set[str],
) -> bool:
    """Update ``accepted`` and ``failed`` from one batch outcome."""
    batch_escaped = any(
        f.get("code") == "worktree_escape_detected"
        for f in outcome["findings"]
    )
    progressed = False
    for member in outcome["members"]:
        if member["category"] == "green":
            if member["integrated"]:
                accepted.add(member["task_id"])
                progressed = True
            else:
                failed.add(member["task_id"])
        elif member["category"] == "no-op" and not batch_escaped:
            accepted.add(member["task_id"])
            progressed = True
        else:
            failed.add(member["task_id"])
    return progressed


def _dry_run_afk(
    manifest: dict[str, Any],
    bodies: dict[str, str],
    project_root: pathlib.Path,
    accepted: set[str],
    findings: list[dict[str, str]],
    argv_template: list[str],
    args: argparse.Namespace,
) -> dict[str, Any]:
    """Plan isolated batches for ``run --dry-run`` without touching disk or git."""
    dry_accepted = set(accepted)
    completed_tasks: list[dict[str, Any]] = []
    planned_batches: list[dict[str, Any]] = []
    processed = 0
    stopped = "no_ready_task"
    work_dir = resolve_work_dir(project_root, args.work_dir)
    constitution_excerpt = _constitution_excerpt()
    project_config_excerpt = _project_config_excerpt(project_root)
    while processed < args.max_tasks:
        ready, _, _ = compute_ready(manifest, dry_accepted)
        if not ready:
            stopped = "no_ready_task"
            break
        groups, selection_warnings = batch.select_batch_members(
            manifest, ready, None, args.max_concurrency, args.max_tasks - processed
        )
        findings.extend(selection_warnings)
        if not groups:
            stopped = "no_ready_task"
            break
        group = groups[0]
        planned_batches.append(
            {
                "id": batch.batch_id("base", group),
                "size": len(group),
                "members": group,
                "branches": [
                    branch_name_for(task_id, find_task(manifest, task_id)["title"])
                    for task_id in group
                ],
                "argv": argv_template,
            }
        )
        for task_id in group:
            task = find_task(manifest, task_id)
            _, meta = assemble_context(
                manifest,
                task,
                project_root,
                args.budget_chars,
                bodies.get(task_id, ""),
                constitution_excerpt=constitution_excerpt,
                project_config_excerpt=project_config_excerpt,
            )
            substitutions = {
                "{prompt_file}": str(work_dir / f"context-{task_id}.md"),
                "{workspace}": str(project_root),
                "{task_id}": task_id,
            }
            completed_tasks.append(
                {
                    "task_id": task_id,
                    "dry_run": True,
                    "argv": substitute_argv(argv_template, substitutions),
                    "context": meta,
                }
            )
            dry_accepted.add(task_id)
        processed += len(group)
    if processed >= args.max_tasks:
        stopped = "max_tasks"
    return _envelope(
        "run",
        findings,
        {
            "workflow_id": manifest.get("workflow_id"),
            "completed": completed_tasks,
            "batches": planned_batches,
            "accepted": sorted(dry_accepted),
            "failed": [],
            "review_dispatch": [],
            "stopped": stopped,
            "dry_run": True,
        },
    )


def verb_run(args: argparse.Namespace) -> int:
    """AFK loop: execute ready tasks as isolated batches until done or budgeted."""
    project_root = pathlib.Path(args.project_root).resolve()
    if not project_root.is_dir():
        raise RunnerError(f"Project root is not a directory: {project_root}")
    manifest, bodies, findings = load_manifest(pathlib.Path(args.plan), project_root)
    accepted = set(parse_accepted(args.accepted, args.accepted_file))

    argv_template = json.loads(args.agent_command)
    if not isinstance(argv_template, list) or not argv_template or not all(
        isinstance(part, str) for part in argv_template
    ):
        raise RunnerError("--agent-command must be a JSON array of strings.")

    try:
        state_path = resolve_state_path(project_root, args.state)
    except IsolationError as exc:
        raise RunnerError(str(exc), exc.findings) from exc

    if args.dry_run:
        accepted |= set(accepted_task_ids(load_state(state_path)))
        result = _dry_run_afk(
            manifest, bodies, project_root, accepted, findings, argv_template, args
        )
        _print(result, args.format)
        return 0 if result["valid"] else 1

    work_dir = resolve_work_dir(project_root, args.work_dir)
    try:
        work_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RunnerError(f"Work directory cannot be created: {work_dir} ({exc})") from exc

    lock = IntegrationLock(project_root)
    try:
        lock.acquire()
    except IsolationError as exc:
        raise RunnerError(str(exc), exc.findings) from exc

    completed_tasks: list[dict[str, Any]] = []
    batches_summary: list[dict[str, Any]] = []
    review_dispatch: list[dict[str, str]] = []
    failed: set[str] = set()
    processed = 0
    progressed = False
    stopped = "no_ready_task"

    try:
        isolation_state = load_state(state_path)
        accepted |= set(accepted_task_ids(isolation_state))

        try:
            require_repo(project_root)
        except IsolationError as exc:
            raise RunnerError(str(exc), exc.findings) from exc

        base_ref = getattr(args, "base_ref", None)
        base_commit = _expected_base_commit(project_root, base_ref)
        accepted_findings = _accepted_set_findings(
            project_root,
            project_root,
            accepted,
            base_commit,
            state_path=state_path,
            state=isolation_state,
        )
        findings.extend(accepted_findings)
        if any(f["severity"] == "error" for f in accepted_findings):
            raise RunnerError(
                "The accepted set does not match the integration branch's content.",
                accepted_findings,
            )

        options = {
            "worktree_root": getattr(args, "worktree_root", DEFAULT_WORKTREE_ROOT),
            "work_dir": work_dir,
            "argv_template": argv_template,
            "agent_timeout": args.agent_timeout,
            "timeout_seconds": args.timeout,
            "base_ref": base_ref,
            "add_ignore": getattr(args, "add_ignore", False),
            "budget_chars": args.budget_chars,
            "state": args.state,
            "state_path": state_path,
            "isolation_state": isolation_state,
            "constitution_excerpt": _constitution_excerpt(),
            "project_config_excerpt": _project_config_excerpt(project_root),
        }

        while processed < args.max_tasks:
            raw_ready, _, _ = compute_ready(manifest, accepted)
            ready = [entry for entry in raw_ready if entry["task_id"] not in failed]
            if not ready:
                stopped = (
                    "all_failed"
                    if (raw_ready and failed and not progressed)
                    else "no_ready_task"
                )
                break
            groups, selection_warnings = batch.select_batch_members(
                manifest, ready, None, args.max_concurrency, args.max_tasks - processed
            )
            findings.extend(selection_warnings)
            if not groups:
                stopped = "no_ready_task"
                break
            group = groups[0]
            outcome = execute_batch(manifest, bodies, project_root, group, options)
            findings.extend(outcome["findings"])
            review_dispatch.extend(outcome.get("review_dispatch", []))
            batches_summary.append(_batch_summary(outcome))
            for member in outcome["members"]:
                completed_tasks.append({"batch_id": outcome["batch_id"], **member})
            if _apply_batch_outcome(outcome, accepted, failed):
                progressed = True
            processed += len(group)
        if processed >= args.max_tasks:
            stopped = "max_tasks"
    finally:
        lock.release()

    result = _envelope(
        "run",
        findings,
        {
            "workflow_id": manifest.get("workflow_id"),
            "completed": completed_tasks,
            "batches": batches_summary,
            "accepted": sorted(accepted),
            "failed": sorted(failed),
            "review_dispatch": review_dispatch,
            "stopped": stopped,
        },
    )
    _print(result, args.format)
    return 0 if result["valid"] and not failed else 1


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deterministic execution runner: next / context / verify / run."
    )
    subparsers = parser.add_subparsers(dest="verb", required=True)

    def add_common(sub: argparse.ArgumentParser, *, plan_required: bool = True) -> None:
        sub.add_argument("--plan", required=plan_required, help="Plan document carrying the task manifest.")
        sub.add_argument("--project-root", required=True, help="Project root directory.")
        sub.add_argument("--format", choices=["text", "json"], default="text", help="Output format.")

    def add_accepted_args(sub: argparse.ArgumentParser, *, accepted_help: str) -> None:
        sub.add_argument("--accepted", action="append", help=accepted_help)
        sub.add_argument("--accepted-file", help="File with one accepted task id per line.")

    def add_isolated_execution_args(
        sub: argparse.ArgumentParser, *, dry_run_help: str
    ) -> None:
        sub.add_argument(
            "--agent-command", required=True, help="JSON argv array for the agent command."
        )
        sub.add_argument(
            "--worktree-root",
            default=DEFAULT_WORKTREE_ROOT,
            help=f"Container directory for worktrees (default {DEFAULT_WORKTREE_ROOT}).",
        )
        sub.add_argument(
            "--base-ref", help="Base ref for the integration branch (default the current HEAD)."
        )
        sub.add_argument(
            "--add-ignore",
            action="store_true",
            help="Append the worktree container to the repository-local exclude file when it "
            "is not already ignored. Never touches .gitignore or global git config.",
        )
        sub.add_argument(
            "--budget-chars",
            type=int,
            default=DEFAULT_CONTEXT_BUDGET_CHARS,
            help="Context budget.",
        )
        sub.add_argument(
            "--timeout",
            type=int,
            default=DEFAULT_VERIFY_TIMEOUT_SECONDS,
            help="Verification timeout.",
        )
        sub.add_argument("--agent-timeout", type=int, default=1800, help="Agent command timeout.")
        sub.add_argument(
            "--work-dir",
            default=None,
            help="Directory for context packs and agent logs (default: the project's evidence directory + runner/).",
        )
        sub.add_argument("--dry-run", action="store_true", help=dry_run_help)

    next_parser = subparsers.add_parser("next", help="Compute the deterministic ready set.")
    add_common(next_parser)
    add_accepted_args(
        next_parser,
        accepted_help="Task id (or comma-separated ids) already accepted at the current revision.",
    )
    next_parser.set_defaults(func=verb_next)

    context_parser = subparsers.add_parser("context", help="Assemble a bounded context pack for one task.")
    add_common(context_parser)
    context_parser.add_argument("--task", required=True, help="Task id to assemble context for.")
    context_parser.add_argument(
        "--budget-chars",
        type=int,
        default=DEFAULT_CONTEXT_BUDGET_CHARS,
        help=f"Context budget in characters (default {DEFAULT_CONTEXT_BUDGET_CHARS}).",
    )
    context_parser.add_argument("--out", help="Write the context pack to this path instead of stdout.")
    context_parser.add_argument(
        "--worktree",
        help="Read the target files from this worktree instead of the project root.",
    )
    context_parser.set_defaults(func=verb_context)

    verify_parser = subparsers.add_parser("verify", help="Run one task's verification command and capture evidence.")
    add_common(verify_parser)
    verify_parser.add_argument("--task", required=True, help="Task id to verify.")
    verify_parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_VERIFY_TIMEOUT_SECONDS,
        help=f"Verification timeout in seconds (default {DEFAULT_VERIFY_TIMEOUT_SECONDS}).",
    )
    verify_parser.add_argument(
        "--worktree",
        help="Run the verification command in this worktree instead of the project root.",
    )
    verify_parser.set_defaults(func=verb_verify)

    isolate_parser = subparsers.add_parser(
        "isolate",
        help="Run one task in its own git worktree and integrate it when it verifies green.",
    )
    add_common(isolate_parser)
    isolate_parser.add_argument("--task", required=True, help="Task id to isolate.")
    add_isolated_execution_args(
        isolate_parser, dry_run_help="Prepare only; do not run the agent or merge."
    )
    isolate_parser.set_defaults(func=verb_isolate)

    batch_parser = subparsers.add_parser(
        "batch",
        help="Run independent ready tasks concurrently and integrate the composite.",
    )
    add_common(batch_parser)
    batch_parser.add_argument(
        "--tasks",
        action="append",
        help="Task id (or comma-separated ids) to consider. Every pinned task must be ready.",
    )
    batch_parser.add_argument(
        "--max-concurrency",
        type=int,
        default=None,
        help="Maximum members per batch (default: unlimited).",
    )
    add_accepted_args(batch_parser, accepted_help="Already accepted task ids.")
    add_isolated_execution_args(
        batch_parser, dry_run_help="Report the planned batches; create nothing."
    )
    batch_parser.set_defaults(func=verb_batch)

    run_parser = subparsers.add_parser("run", help="AFK loop over ready tasks using an operator-supplied agent command.")
    add_common(run_parser)
    add_accepted_args(run_parser, accepted_help="Already accepted task ids.")
    run_parser.add_argument("--max-tasks", type=int, default=1, help="Maximum tasks to process in this run.")
    run_parser.add_argument(
        "--max-concurrency",
        type=int,
        default=None,
        help="Maximum members per batch (default: unlimited).",
    )
    run_parser.add_argument(
        "--state",
        default=None,
        help="Isolation state file path (default: project evidence directory).",
    )
    add_isolated_execution_args(
        run_parser, dry_run_help="Print the agent argv without executing it."
    )
    run_parser.set_defaults(func=verb_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except RunnerError as exc:
        payload = {
            "valid": False,
            "check": f"run:{args.verb}",
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "findings": exc.findings
            or [make_error("runner_error", "runner", str(exc))],
            "limitations": ["Explicitly invoked per unit of work; never a daemon, scheduler, or background service."],
        }
        _print(payload, getattr(args, "format", "text"))
        return 2


if __name__ == "__main__":
    sys.exit(main())
