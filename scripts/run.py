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
import hashlib
import json
import pathlib
import re
import shlex
import subprocess
import sys
from typing import Any

try:
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
    from scripts.daw_common import artifact_dir, compute_sha256, resolve_bounded_path
    from scripts.worktree import (
        IsolationError,
        commit_task_work,
        merge_task_branch,
        prepare_isolation,
        snapshot_main_tree,
    )
except ImportError:
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
    from daw_common import artifact_dir, compute_sha256, resolve_bounded_path  # type: ignore[import-not-found]
    from worktree import (  # type: ignore[import-not-found]
        IsolationError,
        commit_task_work,
        merge_task_branch,
        prepare_isolation,
        snapshot_main_tree,
    )

DEFAULT_CONTEXT_BUDGET_CHARS = 100_000
DEFAULT_VERIFY_TIMEOUT_SECONDS = 600
DEFAULT_WORKTREE_ROOT = ".worktrees"


class RunnerError(Exception):
    """Usage or environment error: exits with code 2."""

    def __init__(self, message: str, findings: list[dict[str, str]] | None = None) -> None:
        super().__init__(message)
        self.findings = findings or []


def _error(code: str, path: str, message: str) -> dict[str, str]:
    return {"severity": "error", "code": code, "path": path, "message": message}


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

    constitution = _constitution_excerpt()
    if constitution:
        header += "\n\n## Suite constitution (excerpt)\n\n" + constitution
    project_config = _project_config_excerpt(project_root)
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
            content = content[:allowance] + "\n<!-- truncated by context budget -->\n"
            truncated.append({"path": rel, "reason": "truncated to context budget"})
            included.append({"path": rel, "sha256": digest, "bytes": allowance, "truncated": True})
        else:
            included.append({"path": rel, "sha256": digest, "bytes": len(content), "truncated": False})
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
    """
    if not raw:
        return artifact_dir(project_root, "evidence") / "runner"
    candidate = pathlib.Path(raw)
    if not candidate.is_absolute():
        candidate = project_root / candidate
    return candidate


def next_attempt_index(directory: pathlib.Path) -> int:
    if not directory.is_dir():
        return 1
    indexes = []
    for entry in directory.glob("verify-*.log"):
        match = re.match(r"verify-(\d+)\.log$", entry.name)
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
) -> dict[str, Any]:
    """Execute the task's prescribed verification command and capture evidence.

    The command is executed without a shell: it is split with ``shlex`` and run
    as an argv, so plan text cannot inject shell syntax.

    ``work_dir`` is the directory the command runs in. It equals the project
    root by default; under per-task isolation it is the task's worktree, so the
    command observes the isolated code rather than the user's working tree.
    The evidence itself is always written under the project root, which keeps a
    single canonical evidence location.
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

    directory = evidence_dir(project_root, task["task_id"])
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RunnerError(f"Evidence directory cannot be created: {directory} ({exc})") from exc
    attempt = next_attempt_index(directory)
    log_path = directory / f"verify-{attempt}.log"

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

    pack, meta = assemble_context(
        manifest,
        task,
        project_root,
        args.budget_chars,
        bodies.get(task["task_id"], ""),
        work_root=worktree_path,
    )
    pack_path = work_dir / f"context-{task['task_id']}.md"
    pack_path.write_text(pack, encoding="utf-8")
    substitutions = {
        "{prompt_file}": str(pack_path),
        "{workspace}": str(worktree_path),
        "{task_id}": task["task_id"],
    }
    argv = substitute_argv(argv_template, substitutions)

    # Snapshot the main working tree immediately before the agent runs, so the
    # comparison afterwards isolates what the *agent* changed. The runner's own
    # writes (the context pack and the evidence directory) are already in place
    # at this point and are therefore not mistaken for an escape.
    before_dirty = snapshot_main_tree(project_root)

    agent_exit = 0
    agent_output = ""
    try:
        agent = subprocess.run(  # noqa: S603 - operator-supplied argv, no shell
            argv,
            cwd=str(worktree_path),
            input=pack.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=args.agent_timeout,
            check=False,
        )
        agent_exit = agent.returncode
        agent_output = agent.stdout.decode("utf-8", errors="replace")
    except FileNotFoundError:
        agent_exit, agent_output = 127, f"<!-- agent command not found: {argv[0]} -->"
    except subprocess.TimeoutExpired:
        agent_exit, agent_output = 124, f"<!-- agent timed out after {args.agent_timeout}s -->"
    agent_log = work_dir / f"agent-{task['task_id']}.log"
    agent_log.write_text(agent_output, encoding="utf-8")

    # The isolation boundary is only real if the agent's writes stayed inside
    # the worktree. Compare the main working tree before and after the agent
    # ran: any new dirty path there means the agent escaped its sandbox, and a
    # task that escaped is never merged.
    escaped = sorted(set(snapshot_main_tree(project_root)) - set(before_dirty))
    if escaped:
        raise RunnerError(
            "The agent modified files outside its worktree; the task is not mergeable.",
            [
                _error(
                    "worktree_escape_detected",
                    str(project_root),
                    "The agent left changes in the main working tree: "
                    + ", ".join(escaped)
                    + ". Isolation requires the worker to operate inside its worktree.",
                )
            ],
        )

    committed: dict[str, Any] = {"committed": False, "reason": "agent did not run"}
    commit = worktree.get("commit")
    if agent_exit == 0:
        try:
            committed = commit_task_work(worktree_path, task["task_id"], task["title"])
        except IsolationError as exc:
            raise RunnerError(str(exc), exc.findings) from exc
        commit = committed.get("commit")

    outcome = run_verification(
        task,
        project_root,
        args.timeout,
        work_dir=worktree_path,
        branch=branch,
        commit=commit,
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
            "agent_log": agent_log.relative_to(project_root).as_posix(),
            "commit": commit,
            "verification": outcome,
            "merged": merged,
        },
    )
    _print(result, args.format)
    return 0 if result["valid"] and outcome["passed"] and merged.get("merged") else 1


def verb_run(args: argparse.Namespace) -> int:
    """AFK loop: take ready tasks, hand each its context pack, then verify."""
    project_root = pathlib.Path(args.project_root).resolve()
    if not project_root.is_dir():
        raise RunnerError(f"Project root is not a directory: {project_root}")
    manifest, bodies, findings = load_manifest(pathlib.Path(args.plan), project_root)
    accepted = parse_accepted(args.accepted, args.accepted_file)
    work_dir = resolve_work_dir(project_root, args.work_dir)
    try:
        work_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RunnerError(f"Work directory cannot be created: {work_dir} ({exc})") from exc

    argv_template = json.loads(args.agent_command)
    if not isinstance(argv_template, list) or not argv_template or not all(
        isinstance(part, str) for part in argv_template
    ):
        raise RunnerError("--agent-command must be a JSON array of strings.")

    completed_tasks: list[dict[str, Any]] = []
    for _ in range(args.max_tasks):
        ready, _, _ = compute_ready(manifest, accepted)
        if not ready:
            break
        entry = ready[0]
        task = find_task(manifest, entry["task_id"])
        pack, meta = assemble_context(
        manifest, task, project_root, args.budget_chars, bodies.get(task['task_id'], '')
    )
        pack_path = work_dir / f"context-{task['task_id']}.md"
        pack_path.write_text(pack, encoding="utf-8")
        substitutions = {
            "{prompt_file}": str(pack_path),
            "{workspace}": str(project_root),
            "{task_id}": task["task_id"],
        }
        argv = substitute_argv(argv_template, substitutions)
        if args.dry_run:
            completed_tasks.append(
                {"task_id": task["task_id"], "dry_run": True, "argv": argv, "context": meta}
            )
            accepted.add(task["task_id"])
            continue
        try:
            agent = subprocess.run(  # noqa: S603 - operator-supplied argv, no shell
                argv,
                cwd=str(project_root),
                input=pack.encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=args.agent_timeout,
                check=False,
            )
            agent_exit = agent.returncode
            agent_output = agent.stdout.decode("utf-8", errors="replace")
        except FileNotFoundError:
            agent_exit, agent_output = 127, f"<!-- agent command not found: {argv[0]} -->"
        except subprocess.TimeoutExpired:
            agent_exit, agent_output = 124, f"<!-- agent timed out after {args.agent_timeout}s -->"
        agent_log = work_dir / f"agent-{task['task_id']}.log"
        agent_log.write_text(agent_output, encoding="utf-8")
        outcome = run_verification(task, project_root, args.timeout)
        completed_tasks.append(
            {
                "task_id": task["task_id"],
                "agent_exit_code": agent_exit,
                "agent_log": agent_log.relative_to(project_root).as_posix(),
                "context": meta,
                "verification": outcome,
            }
        )
        if outcome["passed"] and agent_exit == 0:
            accepted.add(task["task_id"])
        else:
            break
    result = _envelope(
        "run",
        findings,
        {
            "workflow_id": manifest.get("workflow_id"),
            "completed": completed_tasks,
            "accepted": sorted(accepted),
            "stopped": "no_ready_task" if len(completed_tasks) < args.max_tasks else "max_tasks",
        },
    )
    _print(result, args.format)
    return 0 if result["valid"] and all(
        entry.get("verification", {}).get("passed", True) for entry in completed_tasks
    ) else 1


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

    next_parser = subparsers.add_parser("next", help="Compute the deterministic ready set.")
    add_common(next_parser)
    next_parser.add_argument(
        "--accepted",
        action="append",
        help="Task id (or comma-separated ids) already accepted at the current revision.",
    )
    next_parser.add_argument("--accepted-file", help="File with one accepted task id per line.")
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
    isolate_parser.add_argument(
        "--agent-command", required=True, help="JSON argv array for the agent command."
    )
    isolate_parser.add_argument(
        "--worktree-root",
        default=DEFAULT_WORKTREE_ROOT,
        help=f"Container directory for worktrees (default {DEFAULT_WORKTREE_ROOT}).",
    )
    isolate_parser.add_argument(
        "--base-ref", help="Base ref for the integration branch (default the current HEAD)."
    )
    isolate_parser.add_argument(
        "--add-ignore",
        action="store_true",
        help="Append the worktree container to the repository-local exclude file when it "
        "is not already ignored. Never touches .gitignore or global git config.",
    )
    isolate_parser.add_argument("--budget-chars", type=int, default=DEFAULT_CONTEXT_BUDGET_CHARS, help="Context budget.")
    isolate_parser.add_argument("--timeout", type=int, default=DEFAULT_VERIFY_TIMEOUT_SECONDS, help="Verification timeout.")
    isolate_parser.add_argument("--agent-timeout", type=int, default=1800, help="Agent command timeout.")
    isolate_parser.add_argument("--work-dir", default=None, help="Directory for context packs and agent logs (default: the project's evidence directory + runner/).")
    isolate_parser.add_argument("--dry-run", action="store_true", help="Prepare only; do not run the agent or merge.")
    isolate_parser.set_defaults(func=verb_isolate)

    run_parser = subparsers.add_parser("run", help="AFK loop over ready tasks using an operator-supplied agent command.")
    add_common(run_parser)
    run_parser.add_argument("--agent-command", required=True, help="JSON argv array for the agent command.")
    run_parser.add_argument("--accepted", action="append", help="Already accepted task ids.")
    run_parser.add_argument("--accepted-file", help="File with one accepted task id per line.")
    run_parser.add_argument("--max-tasks", type=int, default=1, help="Maximum tasks to process in this run.")
    run_parser.add_argument("--budget-chars", type=int, default=DEFAULT_CONTEXT_BUDGET_CHARS, help="Context budget.")
    run_parser.add_argument("--timeout", type=int, default=DEFAULT_VERIFY_TIMEOUT_SECONDS, help="Verification timeout.")
    run_parser.add_argument("--agent-timeout", type=int, default=1800, help="Agent command timeout.")
    run_parser.add_argument("--work-dir", default=None, help="Directory for context packs and agent logs (default: the project's evidence directory + runner/).")
    run_parser.add_argument("--dry-run", action="store_true", help="Print the agent argv without executing it.")
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
            or [{"severity": "error", "code": "runner_error", "path": "runner", "message": str(exc)}],
            "limitations": ["Explicitly invoked per unit of work; never a daemon, scheduler, or background service."],
        }
        _print(payload, getattr(args, "format", "text"))
        return 2


if __name__ == "__main__":
    sys.exit(main())
