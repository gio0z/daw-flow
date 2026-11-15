#!/usr/bin/env python3
"""Unified CLI entrypoint for the Deterministic Agentic Workflow (DAW) suite."""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path
import sys

sys.dont_write_bytecode = True

SUBCOMMANDS: dict[str, tuple[str, str]] = {
    "route": ("route", "Resolve a routing request or verify suite integrity."),
    "validate": ("validate", "Run read-only structural and contract validators."),
    "run": ("run", "Run deterministic task-manifest execution commands."),
    "worktree": ("worktree", "Manage isolated git task worktrees."),
    "install": ("install", "Install, inspect, diagnose, or uninstall the DAW skill bundle."),
    "derive-ledger": ("derive_ledger", "Derive <spec_dir>/ledger.json from transition records."),
    "derive-tasks": ("derive_tasks", "Derive a plan's embedded task manifest from task files."),
    "feedback": ("feedback", "Generate or submit sanitized skill usage feedback."),
}


def _suite_root() -> Path:
    parent = Path(__file__).resolve().parents[1]
    if (parent / "SKILL.md").is_file() and (parent / "VERSION").is_file():
        return parent
    shared = Path(sys.prefix).resolve() / "share" / "deterministic-agentic-workflow"
    if (shared / "SKILL.md").is_file() and (shared / "VERSION").is_file():
        return shared
    return parent


def _read_version() -> str:
    version_file = _suite_root() / "VERSION"
    if version_file.is_file():
        return version_file.read_text(encoding="utf-8").strip()
    try:
        from importlib.metadata import version as pkg_version

        return pkg_version("deterministic-agentic-workflow")
    except Exception:
        return "unknown"


def _format_help() -> str:
    lines = [
        "usage: daw [-h] [-V] <subcommand> [args...]",
        "",
        "Unified CLI for the Deterministic Agentic Workflow (DAW) suite.",
        "",
        "subcommands:",
    ]
    width = max(len(name) for name in SUBCOMMANDS) + 2
    for name, (_, desc) in SUBCOMMANDS.items():
        lines.append(f"  {name:<{width}}{desc}")
    lines.extend(
        [
            "",
            "options:",
            "  -h, --help     show this help message and exit",
            "  -V, --version  show program's version number and exit",
        ]
    )
    return "\n".join(lines)


def _ensure_import_paths() -> None:
    scripts_dir = str(Path(__file__).resolve().parent)
    root_dir = str(_suite_root())
    for entry in (scripts_dir, root_dir):
        if entry not in sys.path:
            sys.path.insert(0, entry)


def _load_module(module_name: str):
    _ensure_import_paths()
    try:
        return importlib.import_module(f"scripts.{module_name}")
    except ImportError:
        return importlib.import_module(module_name)


def _dispatch(subcommand: str, rest: list[str]) -> int:
    module_name, _ = SUBCOMMANDS[subcommand]
    mod = _load_module(module_name)
    main_fn = mod.main
    params = inspect.signature(main_fn).parameters
    prev_argv = sys.argv[:]
    sys.argv = [f"daw {subcommand}", *rest]
    try:
        try:
            rc = main_fn(rest) if params else main_fn()
        except SystemExit as exc:
            if exc.code is None:
                return 0
            if isinstance(exc.code, int):
                return exc.code
            sys.stderr.write(f"{exc.code}\n")
            return 1
        return 0 if rc is None else int(rc)
    finally:
        sys.argv = prev_argv


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        sys.stderr.write(_format_help() + "\n")
        return 2

    cmd = args[0]
    if cmd in ("-h", "--help"):
        print(_format_help())
        return 0
    if cmd in ("-V", "--version"):
        print(f"daw {_read_version()}")
        return 0
    if cmd not in SUBCOMMANDS:
        sys.stderr.write(
            f"daw: unknown subcommand {cmd!r}. Run 'daw --help' for available subcommands.\n"
        )
        return 2

    return _dispatch(cmd, args[1:])


if __name__ == "__main__":
    raise SystemExit(main())
