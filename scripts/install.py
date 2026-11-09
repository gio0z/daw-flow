#!/usr/bin/env python3
"""Offline, standard-library installation of the complete DAW skill bundle."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True

import check_package
import daw_common
import route

try:
    import package_layout
except ImportError:
    from scripts import package_layout


SUITE = "deterministic-agentic-workflow"
SOURCE = Path(__file__).resolve().parents[1]
RECEIPT = ".daw-install.json"
MODULES = tuple(sorted(route.MANIFEST_MODULE_KEYS))
REQUIRED = package_layout.REQUIRED_FILES + package_layout.REQUIRED_DIRS
OPTIONAL = package_layout.OPTIONAL_DIRS
PAYLOAD = REQUIRED + OPTIONAL
SKILL_DIRS = {
    "codex": (".agents/skills", ".agents/skills"),
    "claude": (".claude/skills", ".claude/skills"),
    "gemini": (".gemini/skills", ".gemini/skills"),
    "cursor": (".cursor/skills", ".cursor/skills"),
    "copilot": (".github/skills", ".copilot/skills"),
}
IGNORED = {"__pycache__", ".pytest_cache", ".git", ".DS_Store"}


class InstallError(ValueError):
    pass


def inventory(root: Path) -> dict[str, str]:
    """Hash every owned file and record directories without following symlinks."""
    records = {}
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [name for name in dirs if name not in IGNORED and not name.endswith((".pyc", ".pyo"))]
        for name in sorted(dirs + files):
            if name in IGNORED or name.endswith((".pyc", ".pyo")):
                continue
            path = Path(current) / name
            relative = path.relative_to(root).as_posix()
            if relative == RECEIPT:
                continue
            if path.is_symlink():
                raise InstallError("A bundle entry is a symlink; preserving the installation.")
            if path.is_dir():
                records[relative] = "directory"
            elif path.is_file():
                records[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
            else:
                raise InstallError("A bundle entry is not a regular file or directory.")
    return records


def source_entries() -> list[Path]:
    missing = [name for name in REQUIRED if not (SOURCE / name).exists()]
    if missing:
        raise InstallError("Source bundle is incomplete; use a complete release or checkout.")
    entries = package_layout.operational_entries(SOURCE)
    for entry in entries:
        paths = [entry]
        if entry.is_dir() and not entry.is_symlink():
            for current, dirs, files in os.walk(entry, followlinks=False):
                dirs[:] = [name for name in dirs if name not in IGNORED and not name.endswith((".pyc", ".pyo"))]
                for name in dirs + files:
                    if name in IGNORED or name.endswith((".pyc", ".pyo")):
                        continue
                    paths.append(Path(current) / name)
        for path in paths:
            if path.is_symlink():
                raise InstallError("Source bundle contains a symlink; refusing to copy its target.")
            if not path.is_file() and not path.is_dir():
                raise InstallError("Source bundle contains a non-regular entry.")
            try:
                path.resolve().relative_to(SOURCE.resolve())
            except ValueError:
                raise InstallError("Source bundle contains an entry that escapes source root.")
    ensure_valid_bundle(SOURCE)
    return entries


HISTORICAL_8_MODULES = frozenset({
    "daw-design",
    "daw-plan",
    "daw-debug",
    "daw-build",
    "daw-review",
    "daw-verify",
    "daw-workspace",
    "daw-ask",
})
HISTORICAL_8_ROUTES = {
    "bootstrap": {"documentation_only": True, "read_only": False, "stages": ["daw-design", "daw-plan"], "allow_unclear_requirements": True, "evaluates_workspace": False},
    "adopt": {"documentation_only": True, "read_only": False, "stages": ["daw-design", "daw-plan"], "allow_unclear_requirements": True, "evaluates_workspace": False},
    "feature": {"documentation_only": False, "read_only": False, "stages_clear": ["daw-plan", "daw-build", "daw-review", "daw-verify"], "stages_unclear": ["daw-design", "daw-plan", "daw-build", "daw-review", "daw-verify"], "evaluates_workspace": True},
    "bugfix": {"documentation_only": False, "read_only": False, "stages": ["daw-debug", "daw-plan", "daw-build", "daw-review", "daw-verify"], "evaluates_workspace": True},
    "patch": {"documentation_only": False, "read_only": False, "stages": ["daw-build", "daw-verify"], "evaluates_workspace": True},
    "review": {"documentation_only": False, "read_only": True, "stages": ["daw-review"], "evaluates_workspace": False},
    "ask": {"documentation_only": False, "read_only": True, "stages": ["daw-ask"], "evaluates_workspace": False},
}

HISTORICAL_10_MODULES = frozenset({
    "daw-design",
    "daw-plan",
    "daw-debug",
    "daw-build",
    "daw-review",
    "daw-verify",
    "daw-workspace",
    "daw-ask",
    "daw-setup",
    "daw-wizard",
})
HISTORICAL_10_ROUTES = {
    "bootstrap": {"documentation_only": True, "read_only": False, "stages": ["daw-wizard", "daw-design", "daw-plan"], "allow_unclear_requirements": True, "evaluates_workspace": False},
    "adopt": {"documentation_only": True, "read_only": False, "stages": ["daw-design", "daw-plan"], "allow_unclear_requirements": True, "evaluates_workspace": False},
    "feature": {"documentation_only": False, "read_only": False, "stages_clear": ["daw-plan", "daw-build", "daw-review", "daw-verify"], "stages_unclear": ["daw-design", "daw-plan", "daw-build", "daw-review", "daw-verify"], "evaluates_workspace": True},
    "bugfix": {"documentation_only": False, "read_only": False, "stages": ["daw-debug", "daw-plan", "daw-build", "daw-review", "daw-verify"], "evaluates_workspace": True},
    "patch": {"documentation_only": False, "read_only": False, "stages": ["daw-build", "daw-verify"], "evaluates_workspace": True},
    "review": {"documentation_only": False, "read_only": True, "stages": ["daw-review"], "evaluates_workspace": False},
    "ask": {"documentation_only": False, "read_only": True, "stages": ["daw-ask"], "evaluates_workspace": False},
    "setup": {"documentation_only": True, "read_only": False, "stages": ["daw-setup"], "allow_unclear_requirements": True, "evaluates_workspace": False},
}

HISTORICAL_11_MODULES = frozenset({
    "daw-design",
    "daw-plan",
    "daw-debug",
    "daw-build",
    "daw-review",
    "daw-verify",
    "daw-workspace",
    "daw-ask",
    "daw-setup",
    "daw-wizard",
    "daw-untangle",
})
HISTORICAL_11_ROUTES = {
    "bootstrap": {"documentation_only": True, "read_only": False, "stages": ["daw-wizard", "daw-design", "daw-plan"], "allow_unclear_requirements": True, "evaluates_workspace": False},
    "adopt": {"documentation_only": True, "read_only": False, "stages": ["daw-design", "daw-plan"], "allow_unclear_requirements": True, "evaluates_workspace": False},
    "feature": {"documentation_only": False, "read_only": False, "stages_clear": ["daw-plan", "daw-build", "daw-review", "daw-verify"], "stages_unclear": ["daw-design", "daw-plan", "daw-build", "daw-review", "daw-verify"], "evaluates_workspace": True},
    "bugfix": {"documentation_only": False, "read_only": False, "stages": ["daw-debug", "daw-plan", "daw-build", "daw-review", "daw-verify"], "evaluates_workspace": True},
    "patch": {"documentation_only": False, "read_only": False, "stages": ["daw-build", "daw-verify"], "evaluates_workspace": True},
    "review": {"documentation_only": False, "read_only": True, "stages": ["daw-review"], "evaluates_workspace": False},
    "untangle": {"documentation_only": False, "read_only": True, "stages": ["daw-untangle"], "evaluates_workspace": False},
    "ask": {"documentation_only": False, "read_only": True, "stages": ["daw-ask"], "evaluates_workspace": False},
    "setup": {"documentation_only": True, "read_only": False, "stages": ["daw-setup"], "allow_unclear_requirements": True, "evaluates_workspace": False},
}

HISTORICAL_MODULES = HISTORICAL_8_MODULES
HISTORICAL_ROUTES = HISTORICAL_8_ROUTES

HISTORICAL_PROFILES = (
    (HISTORICAL_8_MODULES, HISTORICAL_8_ROUTES),
    (HISTORICAL_10_MODULES, HISTORICAL_10_ROUTES),
    (HISTORICAL_11_MODULES, HISTORICAL_11_ROUTES),
)


def is_valid_historical_suite(root: Path) -> bool:
    manifest_path = root / "references" / "suite-manifest.json"
    if not manifest_path.is_file() or manifest_path.stat().st_size > 1024 * 1024:
        return False
    try:
        data = daw_common.parse_strict_json(manifest_path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError, RecursionError):
        return False
    if not isinstance(data, dict) or data.get("schema_version") != 1 or data.get("suite") != SUITE:
        return False
    modules = data.get("modules")
    if not isinstance(modules, dict):
        return False
    routes = data.get("routes")
    if not isinstance(routes, dict):
        return False

    matched_profile = None
    for expected_modules, expected_routes in HISTORICAL_PROFILES:
        if set(modules.keys()) == expected_modules and set(routes.keys()) == set(expected_routes.keys()):
            matched_profile = (expected_modules, expected_routes)
            break

    if matched_profile is None:
        return False

    expected_modules, expected_routes = matched_profile
    for mod_name, mod_info in modules.items():
        if not isinstance(mod_info, dict):
            return False
        if not {"path", "description"}.issubset(set(mod_info.keys())):
            return False
        if not isinstance(mod_info.get("path"), str) or not isinstance(mod_info.get("description"), str):
            return False
        if mod_info["path"] != f"skills/{mod_name}/SKILL.md":
            return False
        mod_file = root / mod_info["path"]
        if not mod_file.is_file():
            return False
    for r_name, r_expected in expected_routes.items():
        route_actual = routes.get(r_name)
        if not isinstance(route_actual, dict):
            return False
        # Compare canonical keys only; ignore optional enterprise keys.
        canonical_route_keys = {
            "documentation_only", "read_only", "stages", "stages_clear", "stages_unclear",
            "evaluates_workspace", "allow_unclear_requirements",
        }
        for ck in canonical_route_keys:
            if ck in r_expected and route_actual.get(ck) != r_expected[ck]:
                return False
    return True


def ensure_valid_bundle(root: Path, allow_historical: bool = False) -> None:
    root = Path(root).expanduser().resolve()
    if not check_package.validate_package(root)["valid"]:
        raise InstallError("Package or suite validation failed; no installation was applied.")
    findings = route.check_suite(root)
    if findings and allow_historical and is_valid_historical_suite(root):
        findings = []
    if findings:
        raise InstallError("Package or suite validation failed; no installation was applied.")


def ignore_copy(directory: str, names: list[str]) -> list[str]:
    return [name for name in names if name in IGNORED or name.endswith((".pyc", ".pyo"))]


def payload_inventory(entries: list[Path]) -> dict[str, str]:
    records = {}
    for entry in entries:
        paths = [entry]
        if entry.is_dir():
            for current, dirs, files in os.walk(entry, followlinks=False):
                dirs[:] = [name for name in dirs if name not in ignore_copy(current, dirs)]
                for name in dirs + files:
                    if name not in ignore_copy(current, [name]):
                        paths.append(Path(current) / name)
        for path in paths:
            rel = path.relative_to(SOURCE)
            for parent in rel.parents:
                if parent != Path("."):
                    records[parent.as_posix()] = "directory"
            records[rel.as_posix()] = "directory" if path.is_dir() else hashlib.sha256(path.read_bytes()).hexdigest()
    return records


def alias_path(module: str) -> Path:
    return Path(SUITE) / "skills" / module


def exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()

def validate_receipt_aliases(aliases: object) -> bool:
    if not isinstance(aliases, list):
        return False
    seen = set()
    for item in aliases:
        if not isinstance(item, str) or item not in MODULES or item in seen:
            return False
        seen.add(item)
    return True



def inspect_installation(skills_dir: Path) -> dict | None:
    skills_dir = Path(skills_dir).expanduser().resolve()
    bundle = skills_dir / SUITE
    if not exists(bundle):
        return None
    if bundle.is_symlink() or not bundle.is_dir():
        raise InstallError("The suite path is not an owned directory; preserving it.")
    receipt_file = bundle / RECEIPT
    if receipt_file.is_symlink() or not receipt_file.is_file() or receipt_file.stat().st_size > 2 * 1024 * 1024:
        raise InstallError("No valid installer receipt; preserving the existing suite.")
    try:
        receipt = daw_common.parse_strict_json(receipt_file.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError, RecursionError):
        raise InstallError("Invalid installer receipt; preserving the existing suite.") from None
    if (
        not isinstance(receipt, dict)
        or receipt.get("schema_version") != 1
        or receipt.get("suite") != SUITE
        or not validate_receipt_aliases(receipt.get("aliases"))
        or not isinstance(receipt.get("files"), dict)
        or not isinstance(receipt.get("version"), str)
    ):
        raise InstallError("Invalid installer receipt; preserving the existing suite.")
    if inventory(bundle) != receipt["files"]:
        raise InstallError("Installed files were changed, added, or removed; preserving local work.")
    for module in receipt["aliases"]:
        alias = skills_dir / module
        if not alias.is_symlink() or os.readlink(alias) != str(alias_path(module)):
            raise InstallError("A module alias was changed or removed; preserving local work.")
        if alias.resolve() != (bundle / "skills" / module).resolve():
            raise InstallError("A module alias resolves outside its owned target.")
    return receipt


def check_alias_collisions(skills_dir: Path, previous: dict | None, aliases: list[str]) -> None:
    owned = previous["aliases"] if previous else []
    for module in aliases:
        if module not in owned and exists(skills_dir / module):
            raise InstallError("A module name is already used by another skill; preserving it.")


@contextmanager
def installation_lock(skills_dir: Path):
    skills_dir.mkdir(parents=True, exist_ok=True)
    lock = skills_dir / ".daw-install.lock"
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise InstallError(f"Another installation holds the lock at {lock}; if no installer is running, delete that file and retry.") from None
    try:
        os.close(descriptor)
        yield
    finally:
        lock.unlink()


@contextmanager
def staging_area(skills_dir: Path, prefix: str):
    staging = Path(tempfile.mkdtemp(prefix=prefix, dir=skills_dir))
    try:
        yield staging
    except BaseException:
        if (staging / "previous").exists():
            raise InstallError(f"Rollback could not finish. The previous bundle is preserved at {staging / 'previous'}; inspect it before retrying.") from None
        shutil.rmtree(staging)
        raise
    else:
        shutil.rmtree(staging)


def install(skills_dir: Path, update: bool, no_aliases: bool, dry_run: bool) -> dict:
    skills_dir = Path(skills_dir).expanduser().resolve()
    entries = source_entries()
    bundle = skills_dir / SUITE
    if bundle == SOURCE or SOURCE.is_relative_to(bundle) or bundle.is_relative_to(SOURCE) or skills_dir == SOURCE or skills_dir.is_relative_to(SOURCE):
        raise InstallError("Installation cannot replace or contain its source checkout.")
    if any(entry.is_dir() and skills_dir.is_relative_to(entry) for entry in entries):
        raise InstallError("Installation cannot be nested in source resources.")
    previous = inspect_installation(skills_dir)
    aliases = [] if no_aliases else list(MODULES)
    check_alias_collisions(skills_dir, previous, aliases)
    result = {"action": "install", "skills_dir": str(skills_dir), "aliases": aliases, "version": (SOURCE / "VERSION").read_text(encoding="utf-8").strip()}
    receipt = {"schema_version": 1, "suite": SUITE, "version": result["version"], "aliases": aliases, "files": payload_inventory(entries)}
    if previous and previous != receipt and not update:
        raise InstallError("A different managed version exists; pass --update to replace it.")
    if dry_run:
        return dict(result, status="planned")
    with installation_lock(skills_dir):
        previous = inspect_installation(skills_dir)
        check_alias_collisions(skills_dir, previous, aliases)
        with staging_area(skills_dir, ".daw-stage-") as staging:
            candidate = staging / SUITE
            candidate.mkdir()
            for entry in entries:
                rel = entry.relative_to(SOURCE)
                target = candidate / rel
                if entry.is_dir():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(entry, target, ignore=ignore_copy)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(entry, target)
            ensure_valid_bundle(candidate)
            if inventory(candidate) != receipt["files"]:
                raise InstallError("Source contents changed during installation; no installation was applied.")
            if previous == receipt:
                return dict(result, status="unchanged")
            if previous and not update:
                raise InstallError("A different managed version exists; pass --update to replace it.")
            (candidate / RECEIPT).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
            if aliases:
                try:
                    probe = staging / "symlink-probe"
                    probe.symlink_to(SUITE, target_is_directory=True)
                    probe.unlink()
                except OSError:
                    raise InstallError("Directory symlinks are unavailable; rerun with --no-aliases for root-only discovery.") from None
            previous_aliases = previous["aliases"] if previous else []
            backup = staging / "previous"
            added, removed = [], []
            try:
                if previous:
                    bundle.rename(backup)
                candidate.rename(bundle)
                for module in previous_aliases:
                    if module not in aliases:
                        (skills_dir / module).unlink()
                        removed.append(module)
                for module in aliases:
                    if module not in previous_aliases:
                        (skills_dir / module).symlink_to(alias_path(module), target_is_directory=True)
                        added.append(module)
            except OSError:
                for module in added:
                    (skills_dir / module).unlink()
                if exists(bundle) and not candidate.exists():
                    bundle.rename(candidate)
                if backup.exists():
                    backup.rename(bundle)
                for module in removed:
                    (skills_dir / module).symlink_to(alias_path(module), target_is_directory=True)
                raise
    return dict(result, status="updated" if previous else "installed")


def uninstall(skills_dir: Path, dry_run: bool) -> dict:
    skills_dir = Path(skills_dir).expanduser().resolve()
    previous = inspect_installation(skills_dir)
    if previous is None:
        raise InstallError("No managed installation exists in this skills directory.")
    result = {"action": "uninstall", "skills_dir": str(skills_dir), "status": "planned" if dry_run else "removed"}
    if dry_run:
        return result
    with installation_lock(skills_dir):
        previous = inspect_installation(skills_dir)
        if previous is None:
            raise InstallError("The installation was removed before the operation started.")
        with staging_area(skills_dir, ".daw-remove-") as staging:
            bundle = skills_dir / SUITE
            backup = staging / "previous"
            removed = []
            bundle.rename(backup)
            try:
                for module in previous["aliases"]:
                    (skills_dir / module).unlink()
                    removed.append(module)
            except OSError:
                backup.rename(bundle)
                for module in removed:
                    (skills_dir / module).symlink_to(alias_path(module), target_is_directory=True)
                raise
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "status", "uninstall"))
    parser.add_argument("--agent", choices=tuple(SKILL_DIRS), default="codex")
    parser.add_argument("--scope", choices=("project", "user"), default="project")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--skills-dir", type=Path, help="Explicit skill directory, overriding agent/scope presets")
    parser.add_argument("--update", action="store_true", help="Replace an unchanged, installer-owned bundle")
    parser.add_argument("--no-aliases", action="store_true", help="Install complete bundle with only root discovery")
    parser.add_argument("--dry-run", action="store_true", help="Inspect without creating files or directories")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.action != "install" and (args.update or args.no_aliases):
        parser.error("--update and --no-aliases apply only to install")
    if args.skills_dir is not None:
        skills_dir = args.skills_dir.expanduser().resolve()
    else:
        local, personal = SKILL_DIRS[args.agent]
        skills_dir = ((args.project_root / local) if args.scope == "project" else Path.home() / personal).expanduser().resolve()
    try:
        if args.action == "install":
            result = install(skills_dir, args.update, args.no_aliases, args.dry_run)
        elif args.action == "uninstall":
            result = uninstall(skills_dir, args.dry_run)
        else:
            receipt = inspect_installation(skills_dir)
            result = {"action": "status", "skills_dir": str(skills_dir), "status": "ready" if receipt else "missing", "version": receipt["version"] if receipt else None}
            if receipt:
                ensure_valid_bundle(skills_dir / SUITE, allow_historical=True)
        code = 1 if result["status"] == "missing" else 0
    except (InstallError, OSError, RuntimeError, UnicodeError) as exc:
        message = str(exc) if isinstance(exc, InstallError) else "Filesystem operation failed; inspect destination permissions and paths."
        result = {"action": args.action, "skills_dir": str(skills_dir), "status": "error", "error": message}
        code = 1
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"{result['status']}: {skills_dir}")
        if "error" in result:
            print(result["error"], file=sys.stderr)
        elif args.action == "install":
            print("Restart or reload your agent's skills, then invoke deterministic-agentic-workflow.")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
