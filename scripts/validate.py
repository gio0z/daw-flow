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

try:
    from scripts.check_config import validate_config_file
    from scripts.check_contract import validate_contract
    from scripts.check_docs import validate_docs
    from scripts.check_flow import validate_flow
    from scripts.check_ledger import validate_ledger
    from scripts.check_package import validate_package
    from scripts.check_status import validate_status
    from scripts.check_surface import SURFACE_LIMITATIONS, validate_surface_session
    from scripts.daw_common import DuplicateKeyError, output_result, parse_strict_json, resolve_bounded_path
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
    from daw_common import (  # type: ignore[import-not-found]
        DuplicateKeyError,
        output_result,
        parse_strict_json,
        resolve_bounded_path,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deterministic Agentic Workflow standalone package and task contract validator."
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    pkg_parser = subparsers.add_parser("package", help="Validate skill package structure and links.")
    pkg_parser.add_argument(
        "--root",
        default=None,
        help="Path to the skill package root directory. Defaults to parent of scripts/ directory.",
    )
    pkg_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format: text or json.",
    )

    contract_parser = subparsers.add_parser("contract", help="Validate a project task contract JSON file.")
    contract_parser.add_argument("file", help="Path to the task contract JSON file (relative or absolute).")
    contract_parser.add_argument(
        "--project-root",
        required=True,
        help="Project root directory bounding all documents, baselines, and evidence.",
    )
    contract_parser.add_argument(
        "--stage",
        choices=["plan", "execute", "complete"],
        default="plan",
        help="Lifecycle stage: plan (default), execute, or complete.",
    )
    contract_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format: text or json.",
    )

    docs_parser = subparsers.add_parser("docs", help="Validate document quality workflow transition fact records.")
    docs_parser.add_argument("file", help="Path to the document quality record JSON file (relative or absolute).")
    docs_parser.add_argument(
        "--project-root",
        required=True,
        help="Project root directory bounding all documents and evidence.",
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
    docs_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format: text or json.",
    )
    ledger_parser = subparsers.add_parser("ledger", help="Validate a spec ledger JSON file.")
    ledger_parser.add_argument("file", help="Path to the ledger JSON file (relative or absolute).")
    ledger_parser.add_argument("--project-root", required=True, help="Project root directory bounding documents and records.")
    ledger_parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format: text or json.")

    config_parser = subparsers.add_parser("config", help="Validate a daw-config block in an agent file.")
    config_parser.add_argument("file", help="Path to the agent file (relative or absolute).")
    config_parser.add_argument("--project-root", required=True, help="Project root directory bounding paths and commands.")
    config_parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format: text or json.")

    verify_parser = subparsers.add_parser(
        "verify", help="Validate a recorded role-based surface session (UI work)."
    )
    verify_parser.add_argument("file", help="Path to the surface session JSON file (relative or absolute).")
    verify_parser.add_argument("--project-root", required=True, help="Project root directory.")
    verify_parser.add_argument(
        "--stage",
        choices=["execute", "complete"],
        default="complete",
        help="execute checks shape only; complete requires every leg passed (default).",
    )
    verify_parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format.")

    status_parser = subparsers.add_parser("status", help="Aggregate read-only project status preflight.")
    status_parser.add_argument("--project-root", required=True, help="Project root directory to inspect.")
    status_parser.add_argument("--agent-file", default=None, help="Agent file holding the daw-config block (default: AGENTS.md, then CLAUDE.md).")
    status_parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format: text or json.")

    flow_parser = subparsers.add_parser("flow", help="Validate the best-practice-flow mapping and suite-manifest flow_gate wiring.")
    flow_parser.add_argument("--project-root", required=True, help="Project root directory to inspect.")
    flow_parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format: text or json.")

    try:
        args = parser.parse_args()
    except SystemExit as e:
        sys.exit(e.code)
    if args.subcommand == "package":
        if args.root:
            root_path = pathlib.Path(args.root).resolve()
        else:
            root_path = pathlib.Path(__file__).resolve().parent.parent

        if not root_path.is_dir():
            sys.stderr.write("Error: Specified package root is not a directory.\n")
            sys.exit(2)

        try:
            res = validate_package(root_path)
        except OSError:
            sys.stderr.write("OS error reading package.\n")
            sys.exit(2)

        output_result(res, args.format)
        sys.exit(0 if res["valid"] else 1)

    elif args.subcommand == "flow":
        try:
            proj_root = pathlib.Path(args.project_root).resolve()
        except (OSError, RuntimeError, ValueError):
            sys.stderr.write("Error: Cannot resolve project root.\n")
            sys.exit(2)
        if not proj_root.is_dir():
            sys.stderr.write("Error: Project root is not a directory.\n")
            sys.exit(2)
        try:
            res = validate_flow(proj_root)
        except OSError:
            sys.stderr.write("OS error computing flow.\n")
            sys.exit(2)
        output_result(res, args.format)
        sys.exit(0 if res["valid"] else 1)

    elif args.subcommand == "contract":
        proj_root_raw = pathlib.Path(args.project_root)
        try:
            proj_root = proj_root_raw.resolve()
        except OSError:
            sys.stderr.write("Error: Cannot resolve project root.\n")
            sys.exit(2)

        if not proj_root.is_dir():
            sys.stderr.write("Error: Project root is not a directory.\n")
            sys.exit(2)

        contract_file_raw = pathlib.Path(args.file)
        if contract_file_raw.is_absolute():
            contract_file_path = contract_file_raw
        else:
            contract_file_path = proj_root / contract_file_raw

        try:
            if not contract_file_path.is_file():
                sys.stderr.write("Error: Contract file does not exist or is not a file.\n")
                sys.exit(2)
        except OSError:
            sys.stderr.write("Error accessing contract file.\n")
            sys.exit(2)

        try:
            raw_text = contract_file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            sys.stderr.write("Error reading contract file.\n")
            sys.exit(2)

        try:
            contract_data = parse_strict_json(raw_text)
        except (json.JSONDecodeError, DuplicateKeyError, RecursionError, ValueError):
            sys.stderr.write("Error parsing contract JSON: malformed JSON, duplicate keys, or unsupported values.\n")
            sys.exit(2)

        try:
            res = validate_contract(contract_data, proj_root, args.stage)
        except OSError:
            sys.stderr.write("OS error validating contract.\n")
            sys.exit(2)

        output_result(res, args.format)
        sys.exit(0 if res["valid"] else 1)

    elif args.subcommand == "docs":
        proj_root_raw = pathlib.Path(args.project_root)
        try:
            proj_root = proj_root_raw.resolve()
            if not proj_root.is_dir():
                sys.stderr.write("Error: Project root is not a directory.\n")
                sys.exit(2)
        except (OSError, RuntimeError, ValueError):
            sys.stderr.write("Error: Cannot resolve project root.\n")
            sys.exit(2)

        raw_file_str = str(args.file)
        rec_p = pathlib.Path(raw_file_str)
        rec_anchor = rec_p.anchor if rec_p.is_absolute() else ""
        rec_tail = raw_file_str[len(rec_anchor):] if rec_anchor else raw_file_str
        if "\0" in raw_file_str or ":" in rec_tail or (not rec_p.is_absolute() and "\\" in raw_file_str):
            res = validate_docs(rec_p, proj_root, args.transition, args.documents)
            output_result(res, args.format)
            sys.exit(0 if res["valid"] else 1)
        try:
            record_file_raw = pathlib.Path(raw_file_str)
            if record_file_raw.is_absolute():
                try:
                    resolved_rec = record_file_raw.resolve()
                    resolved_rec.relative_to(proj_root)
                    record_file_path = resolved_rec
                except (ValueError, OSError, RuntimeError):
                    res = validate_docs(record_file_raw, proj_root, args.transition, args.documents)
                    output_result(res, args.format)
                    sys.exit(0 if res["valid"] else 1)
            else:
                try:
                    rec_bound, rec_err = resolve_bounded_path(proj_root, raw_file_str)
                except (OSError, RuntimeError, ValueError):
                    rec_bound, rec_err = None, "fs_error"
                if rec_err or rec_bound is None:
                    res = validate_docs(record_file_raw, proj_root, args.transition, args.documents)
                    output_result(res, args.format)
                    sys.exit(0 if res["valid"] else 1)
                record_file_path = rec_bound
        except (OSError, RuntimeError, ValueError):
            res = validate_docs(pathlib.Path(raw_file_str), proj_root, args.transition, args.documents)
            output_result(res, args.format)
            sys.exit(0 if res["valid"] else 1)

        try:
            if not record_file_path.is_file():
                sys.stderr.write("Error: Record file does not exist or is not a file.\n")
                sys.exit(2)
        except (OSError, RuntimeError):
            sys.stderr.write("Error accessing record file.\n")
            sys.exit(2)
        try:
            raw_text = record_file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            sys.stderr.write("Error reading record file.\n")
            sys.exit(2)

        try:
            parse_strict_json(raw_text)
        except (json.JSONDecodeError, DuplicateKeyError, RecursionError, ValueError):
            sys.stderr.write("Error parsing record JSON: malformed JSON, duplicate keys, or unsupported values.\n")
            sys.exit(2)

        try:
            res = validate_docs(record_file_path, proj_root, args.transition, args.documents)
        except OSError:
            sys.stderr.write("OS error validating docs.\n")
            sys.exit(2)

        output_result(res, args.format)
        sys.exit(0 if res["valid"] else 1)
    elif args.subcommand in ("ledger", "config"):
        proj_root_raw = pathlib.Path(args.project_root)
        try:
            proj_root = proj_root_raw.resolve()
            if not proj_root.is_dir():
                sys.stderr.write("Error: Project root is not a directory.\n")
                sys.exit(2)
        except (OSError, RuntimeError, ValueError):
            sys.stderr.write("Error: Cannot resolve project root.\n")
            sys.exit(2)
        raw_file_str = str(args.file)
        file_raw = pathlib.Path(raw_file_str)
        if file_raw.is_absolute():
            file_path = file_raw
        else:
            bound_path, bound_err = resolve_bounded_path(proj_root, raw_file_str)
            if bound_err or bound_path is None:
                # Let the validator produce the bounded-path finding.
                file_path = proj_root / raw_file_str
            else:
                file_path = bound_path
        try:
            if not file_path.is_file():
                sys.stderr.write("Error: Input file does not exist or is not a file.\n")
                sys.exit(2)
        except (OSError, RuntimeError):
            sys.stderr.write("Error accessing input file.\n")
            sys.exit(2)
        if args.subcommand == "ledger":
            try:
                raw_text = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                sys.stderr.write("Error reading ledger file.\n")
                sys.exit(2)
            try:
                ledger_data = parse_strict_json(raw_text)
            except (json.JSONDecodeError, DuplicateKeyError, RecursionError, ValueError):
                sys.stderr.write("Error parsing ledger JSON: malformed JSON, duplicate keys, or unsupported values.\n")
                sys.exit(2)
            try:
                res = validate_ledger(ledger_data, proj_root)
            except OSError:
                sys.stderr.write("OS error validating ledger.\n")
                sys.exit(2)
        else:
            try:
                res = validate_config_file(file_path, proj_root)
            except OSError:
                sys.stderr.write("OS error validating config.\n")
                sys.exit(2)
        output_result(res, args.format)
        sys.exit(0 if res["valid"] else 1)

    elif args.subcommand == "verify":
        proj_root_raw = pathlib.Path(args.project_root)
        try:
            proj_root = proj_root_raw.resolve()
        except OSError:
            sys.stderr.write("Error: Cannot resolve project root.\n")
            sys.exit(2)
        if not proj_root.is_dir():
            sys.stderr.write("Error: Project root is not a directory.\n")
            sys.exit(2)

        session_file = pathlib.Path(args.file)
        if not session_file.is_absolute():
            session_file = proj_root / session_file
        try:
            if not session_file.is_file():
                sys.stderr.write("Error: Session file does not exist or is not a file.\n")
                sys.exit(2)
            raw = session_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            sys.stderr.write("Error reading session file.\n")
            sys.exit(2)
        try:
            session_data = parse_strict_json(raw)
        except (json.JSONDecodeError, DuplicateKeyError, RecursionError, ValueError):
            sys.stderr.write("Error parsing session JSON: malformed JSON or duplicate keys.\n")
            sys.exit(2)

        findings = validate_surface_session(
            session_data,
            prefix="surface_session",
            enforce_passed=args.stage == "complete",
            required=True,
        )
        res = {
            "valid": not any(f["severity"] == "error" for f in findings),
            "check": "verify",
            "schema_version": 1,
            "findings": findings,
            "limitations": SURFACE_LIMITATIONS,
        }
        output_result(res, args.format)
        sys.exit(0 if res["valid"] else 1)

    elif args.subcommand == "status":
        try:
            proj_root = pathlib.Path(args.project_root).resolve()
        except (OSError, RuntimeError, ValueError):
            sys.stderr.write("Error: Cannot resolve project root.\n")
            sys.exit(2)
        if not proj_root.is_dir():
            sys.stderr.write("Error: Project root is not a directory.\n")
            sys.exit(2)
        try:
            res = validate_status(proj_root, args.agent_file)
        except OSError:
            sys.stderr.write("OS error computing status.\n")
            sys.exit(2)
        output_result(res, args.format)
        sys.exit(0 if res["valid"] else 1)


if __name__ == "__main__":
    main()
