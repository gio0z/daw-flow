#!/usr/bin/env python3
"""Deterministic Agentic Workflow Validator CLI.

Read-only, zero-dependency Python 3.10+ entry point. Parses arguments, dispatches to the
`check_*` modules, and maps results to exit codes (0 valid, 1 findings, 2 usage/IO error).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Callable, NoReturn

try:
    from scripts.check_config import validate_config_file
    from scripts.check_contract import validate_contract
    from scripts.check_docs import validate_docs
    from scripts.check_flow import validate_flow
    from scripts.check_ledger import validate_ledger
    from scripts.check_package import validate_package
    from scripts.check_status import validate_status
    from scripts.check_surface import SURFACE_LIMITATIONS, validate_surface_session
    from scripts.check_tasks import validate_plan_manifest
    from scripts.daw_common import DuplicateKeyError, build_result, output_result, parse_strict_json, resolve_bounded_path
except ImportError:
    from check_config import validate_config_file  # type: ignore[import-not-found]
    from check_contract import validate_contract  # type: ignore[import-not-found]
    from check_docs import validate_docs  # type: ignore[import-not-found]
    from check_flow import validate_flow  # type: ignore[import-not-found]
    from check_ledger import validate_ledger  # type: ignore[import-not-found]
    from check_package import validate_package  # type: ignore[import-not-found]
    from check_status import validate_status  # type: ignore[import-not-found]
    from check_surface import (  # type: ignore[import-not-found]
        SURFACE_LIMITATIONS,
        validate_surface_session,
    )
    from check_tasks import validate_plan_manifest  # type: ignore[import-not-found]
    from daw_common import (  # type: ignore[import-not-found]
        DuplicateKeyError,
        build_result,
        output_result,
        parse_strict_json,
        resolve_bounded_path,
    )


_JSON_ERRORS = (json.JSONDecodeError, DuplicateKeyError, RecursionError, ValueError)


def _die(message: str) -> NoReturn:
    sys.stderr.write(f"{message}\n")
    sys.exit(2)


def _add_subparser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    name: str,
    help_text: str,
    *,
    file_help: str | None = None,
    project_root_help: str | None = None,
    format_help: str = "Output format: text or json.",
) -> argparse.ArgumentParser:
    sub = subparsers.add_parser(name, help=help_text)
    if file_help is not None:
        sub.add_argument("file", help=file_help)
    if project_root_help is not None:
        sub.add_argument("--project-root", required=True, help=project_root_help)
    sub.add_argument("--format", choices=["text", "json"], default="text", help=format_help)
    return sub


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deterministic Agentic Workflow standalone package and task contract validator."
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    pkg_parser = _add_subparser(subparsers, "package", "Validate skill package structure and links.")
    pkg_parser.add_argument(
        "--root",
        default=None,
        help="Path to the skill package root directory. Defaults to parent of scripts/ directory.",
    )

    contract_parser = _add_subparser(
        subparsers,
        "contract",
        "Validate a project task contract JSON file.",
        file_help="Path to the task contract JSON file (relative or absolute).",
        project_root_help="Project root directory bounding all documents, baselines, and evidence.",
    )
    contract_parser.add_argument(
        "--stage",
        choices=["plan", "execute", "complete"],
        default="plan",
        help="Lifecycle stage: plan (default), execute, or complete.",
    )

    docs_parser = _add_subparser(
        subparsers,
        "docs",
        "Validate document quality workflow transition fact records.",
        file_help="Path to the document quality record JSON file (relative or absolute).",
        project_root_help="Project root directory bounding all documents and evidence.",
    )
    docs_parser.add_argument(
        "--transition",
        choices=[
            "intake-authoring",
            "authoring-review",
            "review-ready",
            "review-rework",
            "rework-review",
        ],
        required=True,
        help="Workflow transition edge.",
    )
    docs_parser.add_argument(
        "--documents",
        nargs="+",
        required=True,
        help="Expected target document relative paths (one or more).",
    )

    _add_subparser(
        subparsers,
        "ledger",
        "Validate a spec ledger JSON file.",
        file_help="Path to the ledger JSON file (relative or absolute).",
        project_root_help="Project root directory bounding documents and records.",
    )
    _add_subparser(
        subparsers,
        "config",
        "Validate a daw-config block in an agent file.",
        file_help="Path to the agent file (relative or absolute).",
        project_root_help="Project root directory bounding paths and commands.",
    )

    verify_parser = _add_subparser(
        subparsers,
        "verify",
        "Validate a recorded role-based surface session (UI work).",
        file_help="Path to the surface session JSON file (relative or absolute).",
        project_root_help="Project root directory.",
        format_help="Output format.",
    )
    verify_parser.add_argument(
        "--stage",
        choices=["execute", "complete"],
        default="complete",
        help="execute checks shape only; complete requires every leg passed (default).",
    )

    status_parser = _add_subparser(
        subparsers,
        "status",
        "Aggregate read-only project status preflight.",
        project_root_help="Project root directory to inspect.",
    )
    status_parser.add_argument(
        "--agent-file",
        default=None,
        help="Agent file holding the daw-config block (default: AGENTS.md, then CLAUDE.md).",
    )

    _add_subparser(
        subparsers,
        "flow",
        "Validate the best-practice-flow mapping and suite-manifest flow_gate wiring.",
        project_root_help="Project root directory to inspect.",
    )
    _add_subparser(
        subparsers,
        "tasks",
        "Validate the task manifest carried by a saved plan document.",
        file_help="Path to the plan document carrying the task manifest.",
        project_root_help="Project root directory bounding the plan and its target files.",
    )
    return parser


def _resolve_project_root(raw_root: str) -> pathlib.Path:
    try:
        proj_root = pathlib.Path(raw_root).resolve()
    except (OSError, RuntimeError, ValueError):
        _die("Error: Cannot resolve project root.")
    if not proj_root.is_dir():
        _die("Error: Project root is not a directory.")
    return proj_root


def _read_strict_json_file(
    file_path: pathlib.Path,
    *,
    missing_msg: str,
    access_msg: str,
    read_msg: str,
    json_msg: str,
) -> Any:
    try:
        if not file_path.is_file():
            _die(missing_msg)
    except (OSError, RuntimeError):
        _die(access_msg)
    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        _die(read_msg)
    try:
        return parse_strict_json(raw_text)
    except _JSON_ERRORS:
        _die(json_msg)


def _run_package(args: argparse.Namespace) -> dict[str, Any]:
    root_path = pathlib.Path(args.root).resolve() if args.root else pathlib.Path(__file__).resolve().parent.parent
    if not root_path.is_dir():
        _die("Error: Specified package root is not a directory.")
    try:
        return validate_package(root_path)
    except OSError:
        _die("OS error reading package.")


def _run_flow(args: argparse.Namespace) -> dict[str, Any]:
    proj_root = _resolve_project_root(args.project_root)
    try:
        return validate_flow(proj_root)
    except OSError:
        _die("OS error computing flow.")


def _run_contract(args: argparse.Namespace) -> dict[str, Any]:
    proj_root = _resolve_project_root(args.project_root)
    contract_file_raw = pathlib.Path(args.file)
    contract_file_path = contract_file_raw if contract_file_raw.is_absolute() else proj_root / contract_file_raw
    contract_data = _read_strict_json_file(
        contract_file_path,
        missing_msg="Error: Contract file does not exist or is not a file.",
        access_msg="Error accessing contract file.",
        read_msg="Error reading contract file.",
        json_msg="Error parsing contract JSON: malformed JSON, duplicate keys, or unsupported values.",
    )
    try:
        return validate_contract(contract_data, proj_root, args.stage)
    except OSError:
        _die("OS error validating contract.")


def _resolve_docs_record_path(proj_root: pathlib.Path, raw_file_str: str) -> pathlib.Path | None:
    """Return a bounded record path, or None when validate_docs should emit the path finding."""
    rec_p = pathlib.Path(raw_file_str)
    rec_anchor = rec_p.anchor if rec_p.is_absolute() else ""
    rec_tail = raw_file_str[len(rec_anchor):] if rec_anchor else raw_file_str
    if "\0" in raw_file_str or ":" in rec_tail or (not rec_p.is_absolute() and "\\" in raw_file_str):
        return None
    try:
        if rec_p.is_absolute():
            resolved_rec = rec_p.resolve()
            resolved_rec.relative_to(proj_root)
            return resolved_rec
        rec_bound, rec_err = resolve_bounded_path(proj_root, raw_file_str)
        return None if (rec_err or rec_bound is None) else rec_bound
    except (ValueError, OSError, RuntimeError):
        return None


def _run_docs(args: argparse.Namespace) -> dict[str, Any]:
    proj_root = _resolve_project_root(args.project_root)
    raw_file_str = str(args.file)
    record_file_path = _resolve_docs_record_path(proj_root, raw_file_str)
    if record_file_path is None:
        return validate_docs(pathlib.Path(raw_file_str), proj_root, args.transition, args.documents)

    _read_strict_json_file(
        record_file_path,
        missing_msg="Error: Record file does not exist or is not a file.",
        access_msg="Error accessing record file.",
        read_msg="Error reading record file.",
        json_msg="Error parsing record JSON: malformed JSON, duplicate keys, or unsupported values.",
    )
    try:
        return validate_docs(record_file_path, proj_root, args.transition, args.documents)
    except OSError:
        _die("OS error validating docs.")


def _resolve_loose_input_file(proj_root: pathlib.Path, raw_file_str: str) -> pathlib.Path:
    file_raw = pathlib.Path(raw_file_str)
    if file_raw.is_absolute():
        file_path = file_raw
    else:
        bound_path, bound_err = resolve_bounded_path(proj_root, raw_file_str)
        file_path = proj_root / raw_file_str if (bound_err or bound_path is None) else bound_path
    try:
        if not file_path.is_file():
            _die("Error: Input file does not exist or is not a file.")
    except (OSError, RuntimeError):
        _die("Error accessing input file.")
    return file_path


def _run_ledger(args: argparse.Namespace) -> dict[str, Any]:
    proj_root = _resolve_project_root(args.project_root)
    file_path = _resolve_loose_input_file(proj_root, str(args.file))
    ledger_data = _read_strict_json_file(
        file_path,
        missing_msg="Error: Input file does not exist or is not a file.",
        access_msg="Error accessing input file.",
        read_msg="Error reading ledger file.",
        json_msg="Error parsing ledger JSON: malformed JSON, duplicate keys, or unsupported values.",
    )
    try:
        return validate_ledger(ledger_data, proj_root)
    except OSError:
        _die("OS error validating ledger.")


def _run_config(args: argparse.Namespace) -> dict[str, Any]:
    proj_root = _resolve_project_root(args.project_root)
    file_path = _resolve_loose_input_file(proj_root, str(args.file))
    try:
        return validate_config_file(file_path, proj_root)
    except OSError:
        _die("OS error validating config.")


def _run_bounded_file(proj_root: pathlib.Path, raw_file_str: str, label: str) -> pathlib.Path:
    file_path = pathlib.Path(raw_file_str)
    if file_path.is_absolute():
        return file_path
    bounded, err = resolve_bounded_path(proj_root, raw_file_str)
    if err or bounded is None:
        _die(f"Error: {label} path is not bounded by the project root: {raw_file_str}")
    return bounded


def _run_verify(args: argparse.Namespace) -> dict[str, Any]:
    proj_root = _resolve_project_root(args.project_root)
    session_file = _run_bounded_file(proj_root, str(args.file), "Session file")
    session_data = _read_strict_json_file(
        session_file,
        missing_msg="Error: Session file does not exist or is not a file.",
        access_msg="Error reading session file.",
        read_msg="Error reading session file.",
        json_msg="Error parsing session JSON: malformed JSON or duplicate keys.",
    )
    findings = validate_surface_session(
        session_data,
        prefix="surface_session",
        enforce_passed=args.stage == "complete",
        required=True,
    )
    return build_result("verify", findings, SURFACE_LIMITATIONS)


def _run_tasks(args: argparse.Namespace) -> dict[str, Any]:
    proj_root = _resolve_project_root(args.project_root)
    plan_path = _run_bounded_file(proj_root, str(args.file), "Plan")
    try:
        if not plan_path.is_file():
            _die("Error: Plan file does not exist or is not a file.")
    except OSError:
        _die("Error accessing plan file.")
    try:
        return validate_plan_manifest(plan_path, proj_root)
    except OSError:
        _die("OS error validating task manifest.")


def _run_status(args: argparse.Namespace) -> dict[str, Any]:
    proj_root = _resolve_project_root(args.project_root)
    try:
        return validate_status(proj_root, args.agent_file)
    except OSError:
        _die("OS error computing status.")


_DISPATCH: dict[str, Callable[[argparse.Namespace], dict[str, Any]]] = {
    "package": _run_package,
    "flow": _run_flow,
    "contract": _run_contract,
    "docs": _run_docs,
    "ledger": _run_ledger,
    "config": _run_config,
    "verify": _run_verify,
    "tasks": _run_tasks,
    "status": _run_status,
}


def main() -> None:
    parser = _build_parser()
    try:
        args = parser.parse_args()
    except SystemExit as e:
        sys.exit(e.code)

    res = _DISPATCH[args.subcommand](args)
    output_result(res, args.format)
    sys.exit(0 if res["valid"] else 1)


if __name__ == "__main__":
    main()
