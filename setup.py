"""Build configuration for bundling DAW operational files alongside the `daw` CLI."""

from __future__ import annotations

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import package_layout

SUITE = "deterministic-agentic-workflow"
IGNORED = {"__pycache__", ".pytest_cache", ".git", ".DS_Store"}


def _is_ignored(name: str) -> bool:
    return name in IGNORED or name.endswith((".pyc", ".pyo"))


def collect_data_files(root: Path = ROOT) -> list[tuple[str, list[str]]]:
    """Return setuptools `data_files` entries placing operational files under `share/<suite>/`."""
    grouped: dict[str, list[str]] = {}
    for entry in package_layout.operational_entries(root):
        if entry.is_file() and not entry.is_symlink():
            rel = entry.relative_to(root)
            parent = rel.parent.as_posix()
            target = f"share/{SUITE}" if parent == "." else f"share/{SUITE}/{parent}"
            grouped.setdefault(target, []).append(rel.as_posix())
        elif entry.is_dir() and not entry.is_symlink():
            for current, dirs, files in os.walk(entry, followlinks=False):
                dirs[:] = sorted(d for d in dirs if not _is_ignored(d))
                for fname in sorted(files):
                    if _is_ignored(fname):
                        continue
                    fpath = Path(current) / fname
                    if fpath.is_symlink() or not fpath.is_file():
                        continue
                    rel = fpath.relative_to(root)
                    parent = rel.parent.as_posix()
                    target = f"share/{SUITE}" if parent == "." else f"share/{SUITE}/{parent}"
                    grouped.setdefault(target, []).append(rel.as_posix())
    return sorted((target, sorted(files)) for target, files in grouped.items())


if __name__ == "__main__":
    from setuptools import setup

    setup(data_files=collect_data_files(ROOT))
