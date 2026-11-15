#!/usr/bin/env python3
"""Packaging and distribution layout definition for deterministic-agentic-workflow."""

from __future__ import annotations

from pathlib import Path

OPERATIONAL_SCRIPTS = (
    "scripts/install.py",
    "scripts/route.py",
    "scripts/validate.py",
    "scripts/daw_common.py",
    "scripts/check_package.py",
    "scripts/check_contract.py",
    "scripts/check_docs.py",
    "scripts/check_ledger.py",
    "scripts/check_config.py",
    "scripts/check_status.py",
    "scripts/check_flow.py",
    "scripts/check_surface.py",
    "scripts/check_tasks.py",
    "scripts/batch.py",
    "scripts/daw.py",
    "scripts/derive_ledger.py",
    "scripts/derive_tasks.py",
    "scripts/feedback.py",
    "scripts/package_layout.py",
    "scripts/run.py",
    "scripts/worktree.py",
)

REQUIRED_FILES = (
    "SKILL.md",
    "LICENSE",
    "VERSION",
    *OPERATIONAL_SCRIPTS,
)

REQUIRED_DIRS = (
    "references",
    "templates",
    "skills",
)

OPTIONAL_DIRS = (
    "agents",
    ".claude-plugin",
    ".cursor-plugin",
    ".codex-plugin",
)


def operational_entries(root: Path) -> list[Path]:
    """Return all operational files and directory roots anchored to root.

    Each returned path satisfies `entry.relative_to(root)` so callers preserve
    relative hierarchy without flattening nested paths (e.g. scripts/).
    """
    root_path = Path(root)
    entries: list[Path] = [root_path / f for f in REQUIRED_FILES]
    entries.extend(root_path / d for d in REQUIRED_DIRS)
    for opt_name in OPTIONAL_DIRS:
        opt_path = root_path / opt_name
        if opt_path.exists() or opt_path.is_symlink():
            entries.append(opt_path)
    return entries
