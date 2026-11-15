#!/usr/bin/env python3
"""Derive the machine task manifest from hand-authored task files.

The task files are the single hand-authored source for a workflow's task list.
This tool projects them into the machine manifest embedded in the plan (the
fenced ```json block after the ``<!-- daw-task-manifest -->`` marker), so the
plan prose and the executable task list cannot describe different work.

It is the suite's second writer, alongside `scripts/derive_ledger.py`, and it
follows the same discipline:

- Without `--write` it prints the manifest it would write and touches nothing.
- It never invents a task field: every copied field comes from a task file.
- It refuses to write when the task files themselves fail validation.
- It writes only the manifest block inside the named plan.

Usage:

    python3 scripts/derive_tasks.py --plan docs/daw/plans/<workflow-id>.md --project-root .
    python3 scripts/derive_tasks.py --plan docs/daw/plans/<workflow-id>.md --project-root . --write
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any

try:
    from scripts.check_tasks import (
        MANIFEST_MARKER,
        MANIFEST_SCHEMA_VERSION,
        derive_manifest,
        extract_manifest,
        extract_sources,
        load_task_files,
    )
    from scripts.daw_common import (
        DuplicateKeyError,
        build_result,
        has_errors,
        make_error,
        parse_strict_json,
        resolve_bounded_path,
    )
except ImportError:
    from check_tasks import (  # type: ignore[import-not-found]
        MANIFEST_MARKER,
        MANIFEST_SCHEMA_VERSION,
        derive_manifest,
        extract_manifest,
        extract_sources,
        load_task_files,
    )
    from daw_common import (  # type: ignore[import-not-found]
        DuplicateKeyError,
        build_result,
        has_errors,
        make_error,
        parse_strict_json,
        resolve_bounded_path,
    )

DERIVE_LIMITATIONS = [
    "Projects task files into a manifest; never invents, guesses, or defaults a task field.",
    "Without --write nothing is modified: the derived manifest is printed for review.",
    "Writes only the manifest block inside the named plan document.",
]

_JSON_PARSE_ERRORS = (json.JSONDecodeError, DuplicateKeyError, RecursionError, ValueError)
_FENCE_RE = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)


def _render_manifest(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, indent=2, ensure_ascii=False)


def _replace_manifest_block(text: str, rendered: str) -> tuple[str, bool]:
    """Return (new_text, replaced) with the manifest block rewritten in place.

    Only the fenced block's bytes change; the surrounding plan text, including
    the blank line after the marker, is preserved exactly.
    """
    marker_index = text.find(MANIFEST_MARKER)
    if marker_index == -1:
        return text, False
    tail = text[marker_index + len(MANIFEST_MARKER) :]
    match = _FENCE_RE.search(tail)
    if match is None:
        return text, False
    block_start = marker_index + len(MANIFEST_MARKER) + match.start()
    block_end = marker_index + len(MANIFEST_MARKER) + match.end()
    replacement = f"```json\n{rendered}\n```"
    return text[:block_start] + replacement + text[block_end:], True


def _insert_manifest_block(text: str, rendered: str) -> str:
    """Append the manifest block to a plan that declares sources but has no block."""
    addition = f"\n\n{MANIFEST_MARKER}\n```json\n{rendered}\n```\n"
    return text.rstrip("\n") + addition


def derive(
    plan_path: pathlib.Path, project_root: pathlib.Path, write: bool
) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    try:
        text = plan_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return _result(
            findings + [make_error("plan_unreadable", str(plan_path), "Plan cannot be read as UTF-8 text.")],
            None,
            write,
        )

    sources = extract_sources(text)
    if not sources:
        return _result(
            findings
            + [
                make_error(
                    "task_sources_undeclared",
                    str(plan_path),
                    "Plan declares no task-source directory; add a "
                    "`<!-- daw-task-sources: <dir> -->` marker to derive a manifest from task files.",
                )
            ],
            None,
            write,
        )

    resolved, err = resolve_bounded_path(project_root, sources)
    if err or resolved is None:
        return _result(
            findings
            + [
                make_error(
                    "task_sources_unsafe",
                    sources,
                    f"Task-source path is unsafe or escapes the project root ({err}).",
                )
            ],
            None,
            write,
        )

    tasks, _bodies, load_findings = load_task_files(resolved)
    if load_findings:
        return _result(findings + load_findings, None, write)

    embedded, _ = extract_manifest(text)
    workflow_id = embedded.get("workflow_id") if isinstance(embedded, dict) else None
    manifest = derive_manifest(tasks, workflow_id if isinstance(workflow_id, str) else None)
    rendered = _render_manifest(manifest)

    if not write:
        return _result(findings, {"manifest": manifest, "rendered": rendered}, write)

    new_text, replaced = _replace_manifest_block(text, rendered)
    if not replaced:
        new_text = _insert_manifest_block(text, rendered)
    try:
        plan_path.write_text(new_text, encoding="utf-8")
    except OSError as exc:
        return _result(
            findings + [make_error("plan_write_failed", str(plan_path), f"Plan cannot be written: {exc}")],
            None,
            write,
        )
    return _result(findings, {"manifest": manifest, "written": True, "replaced": replaced}, write)


def _result(findings: list[dict[str, str]], payload: dict[str, Any] | None, write: bool) -> dict[str, Any]:
    valid = not has_errors(findings)
    extra: dict[str, Any] = {
        "written": bool(write and valid and payload and payload.get("written")),
    }
    if payload is not None:
        extra["manifest"] = payload["manifest"]
        if payload.get("written"):
            extra["replaced_existing_block"] = bool(payload.get("replaced"))
        else:
            extra["rendered"] = payload["rendered"]
    return build_result(
        "derive_tasks",
        findings,
        DERIVE_LIMITATIONS,
        schema_version=MANIFEST_SCHEMA_VERSION,
        extra=extra,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Derive the plan's machine task manifest from its hand-authored task files."
    )
    parser.add_argument("--plan", required=True, help="Plan document carrying the task-source marker.")
    parser.add_argument(
        "--project-root",
        required=True,
        help="Project root directory bounding the plan and its task files.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write the derived manifest into the plan. Without it, nothing is modified.",
    )
    args = parser.parse_args(argv)

    project_root = pathlib.Path(args.project_root).resolve()
    if not project_root.is_dir():
        sys.stderr.write("Error: Project root is not a directory.\n")
        return 2
    plan_path = pathlib.Path(args.plan)
    if not plan_path.is_absolute():
        bounded, err = resolve_bounded_path(project_root, str(plan_path))
        if err or bounded is None:
            sys.stderr.write(f"Error: Plan path is not bounded by the project root: {args.plan}\n")
            return 2
        plan_path = bounded
    if not plan_path.is_file():
        sys.stderr.write("Error: Plan file does not exist or is not a file.\n")
        return 2

    result = derive(plan_path, project_root, args.write)
    if result["valid"]:
        print(f"[OK] Check: derive_tasks (schema_version: {result['schema_version']})")
        if result.get("written"):
            print("Wrote: the plan's task manifest now matches the task files.")
        else:
            print("Rendered manifest (not written; pass --write to apply):")
            print(result["rendered"])
    else:
        print("[INVALID] Check: derive_tasks")
        for finding in result["findings"]:
            print(f"  [{finding['severity'].upper()}] {finding['code']} @ {finding['path']}: {finding['message']}")
    for limitation in result["limitations"]:
        print(f"  - {limitation}")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
