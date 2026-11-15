#!/usr/bin/env python3
"""Offline, standard-library installation of the complete DAW skill bundle."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

try:
    import check_package
    import daw_common
    import package_layout
    import route
except ImportError:
    from scripts import check_package  # type: ignore[import-not-found]
    from scripts import daw_common  # type: ignore[import-not-found]
    from scripts import package_layout  # type: ignore[import-not-found]
    from scripts import route  # type: ignore[import-not-found]


SUITE = "deterministic-agentic-workflow"


def _resolve_source_root() -> Path:
    """Resolve the suite source root from a checkout or installed wheel data dir."""
    parent = Path(__file__).resolve().parents[1]
    if (parent / "SKILL.md").is_file() and (parent / "VERSION").is_file():
        return parent
    shared = Path(sys.prefix).resolve() / "share" / SUITE
    if (shared / "SKILL.md").is_file() and (shared / "VERSION").is_file():
        return shared
    return parent


SOURCE = _resolve_source_root()
RECEIPT = ".daw-install.json"
LINK_RECEIPT = ".daw-install-link.json"
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
    "opencode": (".opencode/skills", ".config/opencode/skills"),
    "antigravity": (".gemini/antigravity/skills", ".gemini/antigravity/skills"),
}
IGNORED = {"__pycache__", ".pytest_cache", ".git", ".DS_Store"}


class InstallError(ValueError):
    pass


def _is_ignored(name: str) -> bool:
    return name in IGNORED or name.endswith((".pyc", ".pyo"))


def _iter_tree(root: Path):
    """Yield non-ignored entries under root without following symlinks."""
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(name for name in dirs if not _is_ignored(name))
        for name in sorted(dirs + [f for f in files if not _is_ignored(f)]):
            yield Path(current) / name


def ignore_copy(directory: str, names: list[str]) -> list[str]:
    return [name for name in names if _is_ignored(name)]


def inventory(root: Path) -> dict[str, str]:
    """Hash every owned file and record directories without following symlinks."""
    records = {}
    for path in _iter_tree(root):
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
    source_resolved = SOURCE.resolve()
    for entry in entries:
        paths = [entry]
        if entry.is_dir() and not entry.is_symlink():
            paths.extend(_iter_tree(entry))
        for path in paths:
            if path.is_symlink():
                raise InstallError("Source bundle contains a symlink; refusing to copy its target.")
            if not path.is_file() and not path.is_dir():
                raise InstallError("Source bundle contains a non-regular entry.")
            try:
                path.resolve().relative_to(source_resolved)
            except ValueError:
                raise InstallError("Source bundle contains an entry that escapes source root.")
    ensure_valid_bundle(SOURCE, allow_root_name_mismatch=True)
    return entries


HISTORICAL_8_MODULES = frozenset({
    "daw-design", "daw-plan", "daw-debug", "daw-build",
    "daw-review", "daw-verify", "daw-workspace", "daw-ask",
})
HISTORICAL_10_MODULES = HISTORICAL_8_MODULES | {"daw-setup", "daw-wizard"}
HISTORICAL_11_MODULES = HISTORICAL_10_MODULES | {"daw-untangle"}

HISTORICAL_8_ROUTES = {
    "bootstrap": {"documentation_only": True, "read_only": False, "stages": ["daw-design", "daw-plan"], "allow_unclear_requirements": True, "evaluates_workspace": False},
    "adopt": {"documentation_only": True, "read_only": False, "stages": ["daw-design", "daw-plan"], "allow_unclear_requirements": True, "evaluates_workspace": False},
    "feature": {"documentation_only": False, "read_only": False, "stages_clear": ["daw-plan", "daw-build", "daw-review", "daw-verify"], "stages_unclear": ["daw-design", "daw-plan", "daw-build", "daw-review", "daw-verify"], "evaluates_workspace": True},
    "bugfix": {"documentation_only": False, "read_only": False, "stages": ["daw-debug", "daw-plan", "daw-build", "daw-review", "daw-verify"], "evaluates_workspace": True},
    "patch": {"documentation_only": False, "read_only": False, "stages": ["daw-build", "daw-verify"], "evaluates_workspace": True},
    "review": {"documentation_only": False, "read_only": True, "stages": ["daw-review"], "evaluates_workspace": False},
    "ask": {"documentation_only": False, "read_only": True, "stages": ["daw-ask"], "evaluates_workspace": False},
}
HISTORICAL_10_ROUTES = {
    **HISTORICAL_8_ROUTES,
    "bootstrap": {**HISTORICAL_8_ROUTES["bootstrap"], "stages": ["daw-wizard", "daw-design", "daw-plan"]},
    "setup": {"documentation_only": True, "read_only": False, "stages": ["daw-setup"], "allow_unclear_requirements": True, "evaluates_workspace": False},
}
HISTORICAL_11_ROUTES = {
    **HISTORICAL_10_ROUTES,
    "untangle": {"documentation_only": False, "read_only": True, "stages": ["daw-untangle"], "evaluates_workspace": False},
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
    routes = data.get("routes")
    if not isinstance(modules, dict) or not isinstance(routes, dict):
        return False

    matched_profile = next(
        (
            (exp_mods, exp_routes)
            for exp_mods, exp_routes in HISTORICAL_PROFILES
            if set(modules.keys()) == exp_mods and set(routes.keys()) == set(exp_routes.keys())
        ),
        None,
    )
    if matched_profile is None:
        return False

    _, expected_routes = matched_profile
    for mod_name, mod_info in modules.items():
        if (
            not isinstance(mod_info, dict)
            or not {"path", "description"}.issubset(mod_info.keys())
            or not isinstance(mod_info.get("path"), str)
            or not isinstance(mod_info.get("description"), str)
            or mod_info["path"] != f"skills/{mod_name}/SKILL.md"
            or not (root / mod_info["path"]).is_file()
        ):
            return False

    # Compare canonical keys only; ignore optional enterprise keys.
    canonical_route_keys = (
        "documentation_only", "read_only", "stages", "stages_clear", "stages_unclear",
        "evaluates_workspace", "allow_unclear_requirements",
    )
    for r_name, r_expected in expected_routes.items():
        route_actual = routes.get(r_name)
        if not isinstance(route_actual, dict):
            return False
        if any(ck in r_expected and route_actual.get(ck) != r_expected[ck] for ck in canonical_route_keys):
            return False
    return True


def _only_root_name_mismatch(root: Path, pkg: dict) -> bool:
    errors = [f for f in pkg.get("findings", []) if f.get("severity") == "error"]
    if not errors or any(f.get("code") != "frontmatter_name_mismatch" for f in errors):
        return False
    skill_md = root / "SKILL.md"
    if not skill_md.is_file():
        return False
    try:
        fm, fm_errors = daw_common.parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return False
    return not fm_errors and fm is not None and fm.get("name") == SUITE


def ensure_valid_bundle(root: Path, allow_historical: bool = False, allow_root_name_mismatch: bool = False) -> None:
    root = Path(root).expanduser().resolve()
    pkg = check_package.validate_package(root)
    if not pkg["valid"]:
        if not (allow_root_name_mismatch and _only_root_name_mismatch(root, pkg)):
            raise InstallError("Package or suite validation failed; no installation was applied.")
    findings = route.check_suite(root)
    if findings and allow_historical and is_valid_historical_suite(root):
        findings = []
    if findings:
        raise InstallError("Package or suite validation failed; no installation was applied.")


def payload_inventory(entries: list[Path]) -> dict[str, str]:
    records = {}
    for entry in entries:
        paths = [entry]
        if entry.is_dir():
            paths.extend(_iter_tree(entry))
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


def _read_strict_receipt(receipt_file: Path) -> dict:
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
        or not isinstance(receipt.get("version"), str)
    ):
        raise InstallError("Invalid installer receipt; preserving the existing suite.")
    return receipt


def _verify_aliases(skills_dir: Path, bundle: Path, aliases: list[str]) -> None:
    for module in aliases:
        alias = skills_dir / module
        if not alias.is_symlink() or os.readlink(alias) != str(alias_path(module)):
            raise InstallError("A module alias was changed or removed; preserving local work.")
        if alias.resolve() != (bundle / "skills" / module).resolve():
            raise InstallError("A module alias resolves outside its owned target.")


def inspect_installation(skills_dir: Path) -> dict | None:
    skills_dir = Path(skills_dir).expanduser().resolve()
    bundle = skills_dir / SUITE
    link_receipt_file = skills_dir / LINK_RECEIPT
    if not exists(bundle):
        if exists(link_receipt_file):
            raise InstallError("No valid installer receipt; preserving the existing suite.")
        return None
    if bundle.is_symlink():
        if not exists(link_receipt_file):
            raise InstallError("The suite path is not an owned directory; preserving it.")
        receipt = _read_strict_receipt(link_receipt_file)
        target = receipt.get("target")
        if receipt.get("mode") != "link" or not isinstance(target, str) or not Path(target).is_absolute() or "files" in receipt:
            raise InstallError("Invalid installer receipt; preserving the existing suite.")
        if os.readlink(bundle) != target:
            raise InstallError("The suite symlink target was changed; preserving local work.")
        if not bundle.is_dir() or bundle.resolve() != Path(target).resolve():
            raise InstallError("The linked suite target is missing or invalid; preserving local work.")
        _verify_aliases(skills_dir, bundle, receipt["aliases"])
        return receipt
    if exists(link_receipt_file):
        raise InstallError("Invalid installer receipt; preserving the existing suite.")
    if not bundle.is_dir():
        raise InstallError("The suite path is not an owned directory; preserving it.")
    receipt = _read_strict_receipt(bundle / RECEIPT)
    if "mode" in receipt or not isinstance(receipt.get("files"), dict):
        raise InstallError("Invalid installer receipt; preserving the existing suite.")
    if inventory(bundle) != receipt["files"]:
        raise InstallError("Installed files were changed, added, or removed; preserving local work.")
    _verify_aliases(skills_dir, bundle, receipt["aliases"])
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
        if (staging / "previous").exists() or (staging / "previous-link-receipt.json").exists():
            raise InstallError(f"Rollback could not finish. The previous bundle is preserved at {staging}; inspect it before retrying.") from None
        shutil.rmtree(staging)
        raise
    else:
        shutil.rmtree(staging)


def _probe_symlinks(staging: Path, *, required_for_link: bool) -> None:
    try:
        probe = staging / "symlink-probe"
        probe.symlink_to(SUITE, target_is_directory=True)
        probe.unlink()
    except OSError:
        msg = (
            "Directory symlinks are unavailable; --link requires directory symlink support."
            if required_for_link
            else "Directory symlinks are unavailable; rerun with --no-aliases for root-only discovery."
        )
        raise InstallError(msg) from None


def _sync_aliases(skills_dir: Path, previous_aliases: list[str], aliases: list[str], added: list[str], removed: list[str]) -> None:
    for module in previous_aliases:
        if module not in aliases:
            (skills_dir / module).unlink()
            removed.append(module)
    for module in aliases:
        if module not in previous_aliases:
            (skills_dir / module).symlink_to(alias_path(module), target_is_directory=True)
            added.append(module)


def _restore_aliases(skills_dir: Path, added: list[str], removed: list[str]) -> None:
    for module in added:
        (skills_dir / module).unlink()
    for module in removed:
        (skills_dir / module).symlink_to(alias_path(module), target_is_directory=True)


def _swap_bundle(
    skills_dir: Path,
    bundle: Path,
    staging: Path,
    previous: dict | None,
    aliases: list[str],
    place_new,
    undo_new,
) -> None:
    """Atomically swap an existing copy/link bundle for the staged replacement with rollback."""
    previous_aliases = previous["aliases"] if previous else []
    previous_is_link = bool(previous and previous.get("mode") == "link")
    link_receipt_file = skills_dir / LINK_RECEIPT
    backup = staging / "previous"
    backup_link_receipt = staging / "previous-link-receipt.json"
    previous_link_target = os.readlink(bundle) if previous_is_link else None
    moved_dir = False
    moved_link_receipt = False
    unlinked_bundle = False
    added, removed = [], []
    try:
        if previous_is_link:
            link_receipt_file.rename(backup_link_receipt)
            moved_link_receipt = True
            bundle.unlink()
            unlinked_bundle = True
        elif previous:
            bundle.rename(backup)
            moved_dir = True
        place_new()
        _sync_aliases(skills_dir, previous_aliases, aliases, added, removed)
    except OSError:
        _restore_aliases(skills_dir, added, removed)
        undo_new()
        if moved_dir and backup.exists():
            backup.rename(bundle)
        if unlinked_bundle and previous_link_target is not None:
            bundle.symlink_to(previous_link_target, target_is_directory=True)
        if moved_link_receipt and backup_link_receipt.exists():
            backup_link_receipt.rename(link_receipt_file)
        raise


def _apply_link_install(
    skills_dir: Path,
    bundle: Path,
    staging: Path,
    previous: dict | None,
    receipt: dict,
    aliases: list[str],
) -> None:
    link_receipt_file = skills_dir / LINK_RECEIPT
    staged_receipt = staging / LINK_RECEIPT
    staged_receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    def place_new() -> None:
        bundle.symlink_to(receipt["target"], target_is_directory=True)
        staged_receipt.rename(link_receipt_file)

    def undo_new() -> None:
        if exists(link_receipt_file):
            link_receipt_file.unlink()
        if bundle.is_symlink():
            bundle.unlink()

    _swap_bundle(skills_dir, bundle, staging, previous, aliases, place_new, undo_new)


def _apply_copy_install(
    skills_dir: Path,
    bundle: Path,
    staging: Path,
    entries: list[Path],
    previous: dict | None,
    receipt: dict,
    aliases: list[str],
) -> None:
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
    (candidate / RECEIPT).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    if aliases:
        _probe_symlinks(staging, required_for_link=False)

    def place_new() -> None:
        candidate.rename(bundle)

    def undo_new() -> None:
        if exists(bundle) and not bundle.is_symlink() and not candidate.exists():
            bundle.rename(candidate)

    _swap_bundle(skills_dir, bundle, staging, previous, aliases, place_new, undo_new)


def install(skills_dir: Path, update: bool, no_aliases: bool, dry_run: bool, link: bool = False) -> dict:
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
    version = (SOURCE / "VERSION").read_text(encoding="utf-8").strip()
    if link:
        source_target = str(SOURCE.resolve())
        receipt = {"schema_version": 1, "suite": SUITE, "mode": "link", "target": source_target, "version": version, "aliases": aliases}
        result = {"action": "install", "skills_dir": str(skills_dir), "aliases": aliases, "version": version, "mode": "link", "target": source_target}
    else:
        receipt = {"schema_version": 1, "suite": SUITE, "version": version, "aliases": aliases, "files": payload_inventory(entries)}
        result = {"action": "install", "skills_dir": str(skills_dir), "aliases": aliases, "version": version}
    if previous and previous != receipt and not update:
        raise InstallError("A different managed version exists; pass --update to replace it.")
    if dry_run:
        return dict(result, status="planned")
    with installation_lock(skills_dir):
        previous = inspect_installation(skills_dir)
        check_alias_collisions(skills_dir, previous, aliases)
        if previous == receipt:
            return dict(result, status="unchanged")
        if previous and not update:
            raise InstallError("A different managed version exists; pass --update to replace it.")
        with staging_area(skills_dir, ".daw-stage-") as staging:
            if link:
                _probe_symlinks(staging, required_for_link=True)
                _apply_link_install(skills_dir, bundle, staging, previous, receipt, aliases)
            else:
                _apply_copy_install(skills_dir, bundle, staging, entries, previous, receipt, aliases)
    return dict(result, status="updated" if previous else "installed")


def uninstall(skills_dir: Path, dry_run: bool) -> dict:
    skills_dir = Path(skills_dir).expanduser().resolve()
    previous = inspect_installation(skills_dir)
    if previous is None:
        raise InstallError("No managed installation exists in this skills directory.")
    is_link = previous.get("mode") == "link"
    result = {"action": "uninstall", "skills_dir": str(skills_dir), "status": "planned" if dry_run else "removed"}
    if is_link:
        result["mode"] = "link"
    if dry_run:
        return result
    with installation_lock(skills_dir):
        previous = inspect_installation(skills_dir)
        if previous is None:
            raise InstallError("The installation was removed before the operation started.")
        with staging_area(skills_dir, ".daw-remove-") as staging:
            bundle = skills_dir / SUITE
            if previous.get("mode") == "link":
                link_receipt_file = skills_dir / LINK_RECEIPT
                backup_link_receipt = staging / "previous-link-receipt.json"
                old_target = os.readlink(bundle)
                link_receipt_file.rename(backup_link_receipt)
                removed = []
                unlinked_bundle = False
                try:
                    bundle.unlink()
                    unlinked_bundle = True
                    for module in previous["aliases"]:
                        (skills_dir / module).unlink()
                        removed.append(module)
                except OSError:
                    if unlinked_bundle and not exists(bundle):
                        bundle.symlink_to(old_target, target_is_directory=True)
                    backup_link_receipt.rename(link_receipt_file)
                    _restore_aliases(skills_dir, [], removed)
                    raise
            else:
                backup = staging / "previous"
                removed = []
                bundle.rename(backup)
                try:
                    for module in previous["aliases"]:
                        (skills_dir / module).unlink()
                        removed.append(module)
                except OSError:
                    backup.rename(bundle)
                    _restore_aliases(skills_dir, [], removed)
                    raise
    return result


def resolve_skills_dir(agent: str, scope: str, project_root: Path) -> Path:
    local, personal = SKILL_DIRS[agent]
    base = (project_root.expanduser() / local) if scope == "project" else (Path.home() / personal)
    return base.expanduser().resolve()


def _status_for_dir(skills_dir: Path) -> dict:
    skills_dir = Path(skills_dir).expanduser().resolve()
    receipt = inspect_installation(skills_dir)
    if receipt is None:
        return {"action": "status", "skills_dir": str(skills_dir), "status": "missing", "version": None}
    is_link = receipt.get("mode") == "link"
    bundle = skills_dir / SUITE
    ensure_valid_bundle(bundle, allow_historical=True, allow_root_name_mismatch=is_link)
    version = receipt["version"]
    if is_link and (bundle / "VERSION").is_file():
        version = (bundle / "VERSION").read_text(encoding="utf-8").strip()
    result = {
        "action": "status",
        "skills_dir": str(skills_dir),
        "status": "ready",
        "version": version,
        "mode": "link" if is_link else "copy",
    }
    if is_link:
        result["target"] = receipt["target"]
    return result


def _run_single_target(action: str, skills_dir: Path, args: argparse.Namespace) -> dict:
    if action == "install":
        return install(skills_dir, args.update, args.no_aliases, args.dry_run, link=args.link)
    if action == "uninstall":
        return uninstall(skills_dir, args.dry_run)
    return _status_for_dir(skills_dir)


def _format_error(exc: Exception) -> str:
    return str(exc) if isinstance(exc, InstallError) else "Filesystem operation failed; inspect destination permissions and paths."


def _run_all_agents(action: str, args: argparse.Namespace) -> tuple[dict, int]:
    results = []
    counts: dict[str, int] = {}
    for agent in SKILL_DIRS:
        skills_dir = resolve_skills_dir(agent, args.scope, args.project_root)
        try:
            if action == "uninstall" and inspect_installation(skills_dir) is None:
                entry = {"action": "uninstall", "skills_dir": str(skills_dir), "status": "missing"}
            else:
                entry = _run_single_target(action, skills_dir, args)
        except (InstallError, OSError, RuntimeError, UnicodeError) as exc:
            entry = {"action": action, "skills_dir": str(skills_dir), "status": "error", "error": _format_error(exc)}
        item = {"agent": agent, **entry}
        results.append(item)
        counts[item["status"]] = counts.get(item["status"], 0) + 1

    has_error = counts.get("error", 0) > 0
    if has_error:
        overall_status, code = "error", 1
    elif action == "status":
        if counts.get("ready", 0) == len(results):
            overall_status, code = "ready", 0
        elif counts.get("ready", 0) == 0:
            overall_status, code = "missing", 1
        else:
            overall_status, code = "partial", 1
    elif action == "install":
        if args.dry_run:
            overall_status = "planned"
        elif counts.get("unchanged", 0) == len(results):
            overall_status = "unchanged"
        elif counts.get("updated", 0) > 0:
            overall_status = "updated"
        else:
            overall_status = "installed"
        code = 0
    else:  # uninstall
        if counts.get("missing", 0) == len(results):
            overall_status, code = "missing", 1
        elif args.dry_run:
            overall_status, code = "planned", 0
        else:
            overall_status, code = "removed", 0

    summary = {"total": len(results), **counts}
    payload = {
        "action": action,
        "agent": "all",
        "scope": args.scope,
        "status": overall_status,
        "summary": summary,
        "results": results,
    }
    return payload, code


def _check_git_version() -> dict:
    try:
        proc = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return {"ok": False, "available": False, "version": None, "required": ">=2.20"}
    if proc.returncode != 0:
        return {"ok": False, "available": False, "version": None, "required": ">=2.20"}
    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", proc.stdout)
    if not match:
        return {"ok": False, "available": True, "version": proc.stdout.strip(), "required": ">=2.20"}
    major, minor = int(match.group(1)), int(match.group(2))
    version_str = f"{major}.{minor}.{match.group(3)}" if match.group(3) is not None else f"{major}.{minor}"
    return {"ok": (major, minor) >= (2, 20), "available": True, "version": version_str, "required": ">=2.20"}


def _check_symlink_support() -> dict:
    with tempfile.TemporaryDirectory(prefix="daw-doctor-") as tmp:
        tmp_path = Path(tmp)
        target = tmp_path / "target"
        target.mkdir()
        link = tmp_path / "link"
        try:
            link.symlink_to(target, target_is_directory=True)
            supported = link.is_symlink() and link.resolve() == target.resolve()
        except OSError:
            supported = False
    return {"ok": supported, "supported": supported}


def _detect_preset_overlaps(presets: list[dict], scope: str) -> list[dict]:
    active = [p for p in presets if p["status"] == "ready" or p.get("_bundle_present")]
    if len(active) < 2:
        return []
    by_agent = {p["agent"]: p for p in active}
    overlaps = []
    if "codex" in by_agent:
        others = [p for p in active if p["agent"] != "codex"]
        involved = [by_agent["codex"], *others]
        overlaps.append({
            "agents": [p["agent"] for p in involved],
            "skills_dirs": [p["skills_dir"] for p in involved],
            "message": (
                f"Overlapping installations at {scope} scope: {', '.join(p['agent'] for p in involved)} "
                "(shared .agents/skills overlaps with client-specific skill directories)."
            ),
        })
    if "gemini" in by_agent and "antigravity" in by_agent:
        pair = [by_agent["gemini"], by_agent["antigravity"]]
        overlaps.append({
            "agents": ["gemini", "antigravity"],
            "skills_dirs": [p["skills_dir"] for p in pair],
            "message": (
                f"Overlapping installations at {scope} scope: gemini and antigravity "
                "(.gemini/skills and .gemini/antigravity/skills both reside under .gemini/)."
            ),
        })
    if not overlaps:
        overlaps.append({
            "agents": [p["agent"] for p in active],
            "skills_dirs": [p["skills_dir"] for p in active],
            "message": f"Multiple DAW installations detected at {scope} scope: {', '.join(p['agent'] for p in active)}.",
        })
    return overlaps


def doctor(scope: str, project_root: Path) -> tuple[dict, int]:
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_check = {"ok": sys.version_info >= (3, 10), "version": py_ver, "required": ">=3.10"}
    git_check = _check_git_version()
    symlink_check = _check_symlink_support()

    errors: list[str] = []
    warnings: list[str] = []
    if not py_check["ok"]:
        errors.append(f"Python {py_ver} does not meet required >=3.10.")
    if not git_check["ok"]:
        errors.append(f"git >=2.20 is required (found: {git_check['version'] or 'missing'}).")
    if not symlink_check["ok"]:
        warnings.append("Directory symlinks unavailable; use --no-aliases (--link unavailable).")

    presets: list[dict] = []
    for agent in SKILL_DIRS:
        skills_dir = resolve_skills_dir(agent, scope, project_root)
        bundle_present = exists(skills_dir / SUITE)
        try:
            if not skills_dir.exists() and not exists(skills_dir / LINK_RECEIPT):
                entry = {"agent": agent, "skills_dir": str(skills_dir), "status": "missing", "version": None}
            else:
                st = _status_for_dir(skills_dir)
                entry = {"agent": agent, **{k: v for k, v in st.items() if k != "action"}}
        except (InstallError, OSError, RuntimeError, UnicodeError) as exc:
            msg = _format_error(exc)
            entry = {"agent": agent, "skills_dir": str(skills_dir), "status": "error", "version": None, "error": msg}
            errors.append(f"{agent} ({skills_dir}): {msg}")
        entry["_bundle_present"] = bundle_present
        presets.append(entry)

    overlaps = _detect_preset_overlaps(presets, scope)
    for overlap in overlaps:
        warnings.append(overlap["message"])
    for entry in presets:
        entry.pop("_bundle_present", None)

    overall_status = "error" if errors else ("warning" if warnings else "ok")
    code = 1 if errors else 0
    payload = {
        "action": "doctor",
        "scope": scope,
        "project_root": str(project_root.expanduser().resolve()),
        "status": overall_status,
        "checks": {"python": py_check, "git": git_check, "symlinks": symlink_check},
        "presets": presets,
        "overlaps": overlaps,
        "warnings": warnings,
        "errors": errors,
    }
    return payload, code


def _find_existing_config_file(project_root: Path) -> Path | None:
    """Return AGENTS.md or CLAUDE.md if either already contains a daw-config block."""
    for name in ("AGENTS.md", "CLAUDE.md"):
        resolved, err = daw_common.resolve_bounded_path(project_root, name)
        if err or resolved is None or not resolved.is_file():
            continue
        try:
            text = resolved.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "<!-- daw-config:start -->" in text:
            return resolved
    return None


def _select_config_target(project_root: Path) -> Path:
    """Choose AGENTS.md (preferred/default) or existing CLAUDE.md for config bootstrap."""
    agents_file = project_root / "AGENTS.md"
    claude_file = project_root / "CLAUDE.md"
    if agents_file.is_file() or not claude_file.is_file():
        return agents_file
    return claude_file


def _render_config_block(project_root: Path) -> tuple[str, str]:
    """Build a valid <!-- daw-config --> block and return (block_text, spec_dir)."""
    version = (SOURCE / "VERSION").read_text(encoding="utf-8").strip()
    if (project_root / "docs" / "specs").is_dir():
        spec_dir = "docs/specs"
    elif (project_root / "docs").is_dir():
        spec_dir = "docs"
    else:
        spec_dir = "docs/specs"

    test_command = (
        'python3 -m unittest discover -s tests -p "test_*.py"'
        if (project_root / "tests").is_dir() and shutil.which("python3")
        else "none"
    )
    wf_resolved, wf_err = daw_common.resolve_bounded_path(project_root, ".github/workflows/")
    high_risk_paths = (
        ".github/workflows/"
        if wf_err is None and wf_resolved is not None and wf_resolved.exists()
        else "none"
    )

    block = "\n".join(
        [
            "<!-- daw-config:start -->",
            "",
            "## DAW Configuration",
            "",
            "- schema: 1",
            f"- daw_version: {version}",
            f"- spec_dir: {spec_dir}",
            f"- test_command: {test_command}",
            "- lint_command: none",
            "- build_command: none",
            "- workspace: in-place",
            f"- high_risk_paths: {high_risk_paths}",
            "- issue_tracker: github",
            "- default_branch: main",
            "- commit_convention: conventional",
            "- pr_template: none",
            "- ci_checks: Checks",
            "- release_process: changelog+tags",
            "- branch_pattern: feature/*",
            "",
            "<!-- daw-config:end -->",
        ]
    )
    return block, spec_dir


def init_project_config(project_root: Path, dry_run: bool = False) -> dict:
    """Initialize a valid `<!-- daw-config -->` block in project AGENTS.md or CLAUDE.md."""
    root = Path(project_root).expanduser().resolve()
    existing = _find_existing_config_file(root)
    if existing is not None:
        return {"file": str(existing), "status": "unchanged"}

    target = _select_config_target(root)
    resolved_target, err = daw_common.resolve_bounded_path(root, target.name)
    if err or resolved_target is None:
        raise InstallError(f"Refusing to write config outside project root: {target.name}")
    if target.is_symlink():
        raise InstallError(f"Refusing to write config through symlink: {target.name}")

    block, spec_dir = _render_config_block(root)
    existed = target.exists()
    if existed and not target.is_file():
        raise InstallError(f"Config target exists and is not a regular file: {target}")

    if dry_run:
        return {"file": str(target), "status": "planned", "spec_dir": spec_dir}

    root.mkdir(parents=True, exist_ok=True)
    (root / spec_dir).mkdir(parents=True, exist_ok=True)
    if existed:
        current = target.read_text(encoding="utf-8")
        new_text = f"{current.rstrip()}\n\n{block}\n" if current.strip() else f"{block}\n"
        target.write_text(new_text, encoding="utf-8")
    else:
        target.write_text(f"# {target.name}\n\n{block}\n", encoding="utf-8")
    return {
        "file": str(target),
        "status": "updated" if existed else "created",
        "spec_dir": spec_dir,
    }


def detect_agents(scope: str, project_root: Path) -> list[str]:
    """Return preset agent names whose config directory already exists at the given scope."""
    base = Path(project_root).expanduser().resolve() if scope == "project" else Path.home().expanduser().resolve()
    detected: list[str] = []
    for agent, (local, personal) in SKILL_DIRS.items():
        rel_skills = local if scope == "project" else personal
        config_dir = base / Path(rel_skills).parent
        if config_dir.is_dir():
            detected.append(agent)
    return detected


def _parse_agent_selection(raw: str, agents_list: tuple[str, ...], default_agents: list[str]) -> list[str] | None:
    """Parse comma-separated numbers, agent names, or 'a'/'all' into an ordered list of agents."""
    cleaned = raw.strip().lower()
    if not cleaned:
        return list(default_agents)
    tokens = [tok.strip() for tok in cleaned.split(",") if tok.strip()]
    if not tokens:
        return list(default_agents)
    if any(tok in ("a", "all") for tok in tokens):
        return list(agents_list)
    selected: list[str] = []
    for tok in tokens:
        if tok.isdigit():
            idx = int(tok)
            if 1 <= idx <= len(agents_list):
                agent = agents_list[idx - 1]
                if agent not in selected:
                    selected.append(agent)
                continue
            return None
        if tok in SKILL_DIRS:
            if tok not in selected:
                selected.append(tok)
            continue
        return None
    return selected


def run_interactive_wizard(args: argparse.Namespace) -> tuple[dict, int]:
    """Prompt the operator for scope, target agents, and optional project config bootstrap."""
    project_root = args.project_root.expanduser().resolve()
    version = (SOURCE / "VERSION").read_text(encoding="utf-8").strip()
    print(f"Deterministic Agentic Workflow (DAW) v{version}")
    print("")

    try:
        while True:
            scope_raw = input(
                f"Where do you want to install DAW?\n"
                f"  1) User / Global (recommended)\n"
                f"  2) Current project ({project_root})\n"
                f"Choice [1]: "
            ).strip().lower()
            if scope_raw in ("", "1", "user", "global", "u"):
                scope = "user"
                break
            if scope_raw in ("2", "project", "p"):
                scope = "project"
                break
            print("Please enter 1 (user) or 2 (project).")

        agents_list = tuple(SKILL_DIRS.keys())
        detected = detect_agents(scope, project_root)
        default_agents = detected if detected else ["codex"]
        print("")
        print("Select target agent(s):")
        for idx, agent in enumerate(agents_list, start=1):
            skills_dir = resolve_skills_dir(agent, scope, project_root)
            tag = " [detected]" if agent in detected else ""
            print(f"  {idx}) {agent:<12} ({skills_dir}){tag}")
        print("  a) all          (every preset agent above)")

        default_label = ",".join(default_agents)
        while True:
            agent_raw = input(f"Agents (numbers/names, comma-separated, or 'a' for all) [{default_label}]: ")
            selected_agents = _parse_agent_selection(agent_raw, agents_list, default_agents)
            if selected_agents:
                break
            print(f"Please enter numbers 1-{len(agents_list)}, agent names, or 'a' for all.")

        do_init_config = False
        if scope == "project" and _find_existing_config_file(project_root) is None:
            target_name = _select_config_target(project_root).name
            if args.init_config:
                do_init_config = True
            else:
                while True:
                    cfg_raw = input(f"\nInitialize DAW configuration block in {target_name}? [Y/n]: ").strip().lower()
                    if cfg_raw in ("", "y", "yes"):
                        do_init_config = True
                        break
                    if cfg_raw in ("n", "no"):
                        do_init_config = False
                        break
                    print("Please enter y or n.")
    except (EOFError, KeyboardInterrupt):
        print("\nInstallation cancelled.", file=sys.stderr)
        return {"action": "install", "status": "cancelled"}, 1

    print("")
    results: list[dict] = []
    any_error = False
    for agent in selected_agents:
        skills_dir = resolve_skills_dir(agent, scope, project_root)
        try:
            existing = inspect_installation(skills_dir)
            entry = install(
                skills_dir,
                update=(existing is not None or args.update),
                no_aliases=args.no_aliases,
                dry_run=args.dry_run,
                link=args.link,
            )
        except (InstallError, OSError, RuntimeError, UnicodeError) as exc:
            entry = {"action": "install", "skills_dir": str(skills_dir), "status": "error", "error": _format_error(exc)}
            any_error = True
        item = {"agent": agent, **entry}
        results.append(item)
        print(f"  {agent}: {item['status']} ({item['skills_dir']})")
        if "error" in item:
            print(f"  {agent}: {item['error']}", file=sys.stderr)

    config_res: dict | None = None
    if do_init_config and not any_error:
        try:
            config_res = init_project_config(project_root, dry_run=args.dry_run)
            print(f"  config ({config_res['status']}): {config_res['file']}")
        except (InstallError, OSError, RuntimeError, UnicodeError) as exc:
            any_error = True
            print(f"  config error: {_format_error(exc)}", file=sys.stderr)

    if not any_error and not args.dry_run:
        print("\nRestart or reload your agent's skills, then invoke deterministic-agentic-workflow.")

    suffix_parts = [f"--scope {scope}"]
    if scope == "project":
        suffix_parts.append(f"--project-root {project_root}")
    if args.link:
        suffix_parts.append("--link")
    if args.no_aliases:
        suffix_parts.append("--no-aliases")
    if do_init_config and scope == "project":
        suffix_parts.append("--init-config")
    suffix = " ".join(suffix_parts)
    if len(selected_agents) == len(agents_list):
        repro_cmds = [f"daw install install --agent all {suffix}"]
    else:
        repro_cmds = [f"daw install install --agent {agent} {suffix}" for agent in selected_agents]

    print("Non-interactive command:")
    for cmd in repro_cmds:
        print(f"  {cmd}")

    overall_status = "error" if any_error else ("planned" if args.dry_run else "installed")
    payload: dict = {
        "action": "install",
        "scope": scope,
        "status": overall_status,
        "results": results,
        "commands": repro_cmds,
    }
    if config_res is not None:
        payload["config"] = config_res
    return payload, (1 if any_error else 0)


def _print_text_result(action: str, result: dict, args: argparse.Namespace) -> None:
    if action == "doctor":
        checks = result["checks"]
        print(f"doctor ({result['scope']}): {result['status']}")
        print(f"  python: {checks['python']['version']} ({'ok' if checks['python']['ok'] else 'fail'}, {checks['python']['required']})")
        git_ver = checks["git"]["version"] or "missing"
        print(f"  git: {git_ver} ({'ok' if checks['git']['ok'] else 'fail'}, {checks['git']['required']})")
        print(f"  symlinks: {'supported' if checks['symlinks']['supported'] else 'unsupported'}")
        print("presets:")
        for item in result["presets"]:
            detail = f"{item['version']}, {item.get('mode', 'copy')}, " if item["status"] == "ready" else ""
            print(f"  {item['agent']}: {item['status']} ({detail}{item['skills_dir']})")
        for warning in result["warnings"]:
            print(f"warning: {warning}")
        for err in result["errors"]:
            print(err, file=sys.stderr)
        return

    if "results" in result:
        print(f"{result['status']}: all ({result['scope']})")
        for item in result["results"]:
            print(f"  {item['agent']}: {item['status']} ({item['skills_dir']})")
            if "error" in item:
                print(f"  {item['agent']}: {item['error']}", file=sys.stderr)
        if "config" in result:
            cfg = result["config"]
            print(f"  config ({cfg['status']}): {cfg['file']}")
        if action == "install" and result["status"] != "error" and not args.dry_run:
            print("Restart or reload your agent's skills, then invoke deterministic-agentic-workflow.")
        return

    print(f"{result['status']}: {result['skills_dir']}")
    if "config" in result:
        cfg = result["config"]
        print(f"config ({cfg['status']}): {cfg['file']}")
    if "error" in result:
        print(result["error"], file=sys.stderr)
    elif action == "install":
        print("Restart or reload your agent's skills, then invoke deterministic-agentic-workflow.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", choices=("install", "status", "uninstall", "doctor"))
    parser.add_argument("--agent", choices=tuple(SKILL_DIRS) + ("all",), default="codex")
    parser.add_argument("--scope", choices=("project", "user"), default="project")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--skills-dir", type=Path, help="Explicit skill directory, overriding agent/scope presets")
    parser.add_argument("--update", action="store_true", help="Replace an unchanged, installer-owned bundle")
    parser.add_argument("--no-aliases", action="store_true", help="Install complete bundle with only root discovery")
    parser.add_argument("--link", action="store_true", help="Install via symlink to source checkout (dev mode)")
    parser.add_argument("--dry-run", action="store_true", help="Inspect without creating files or directories")
    parser.add_argument("-i", "--interactive", action="store_true", help="Run interactive installation wizard")
    parser.add_argument("--init-config", action="store_true", help="Initialize <!-- daw-config --> block in project AGENTS.md/CLAUDE.md")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.interactive and args.json:
        parser.error("--interactive cannot be combined with --json")
    if args.interactive and args.action not in (None, "install"):
        parser.error("--interactive applies only to install")
    if args.interactive and args.skills_dir is not None:
        parser.error("--interactive cannot be combined with --skills-dir")

    if args.action is None:
        if args.interactive or (sys.stdin.isatty() and sys.stdout.isatty() and not args.json):
            _, code = run_interactive_wizard(args)
            return code
        parser.error("the following arguments are required: action")

    if args.interactive:
        _, code = run_interactive_wizard(args)
        return code

    if args.action != "install" and (args.update or args.no_aliases or args.link or args.init_config):
        parser.error("--update, --no-aliases, --link, and --init-config apply only to install")
    if args.init_config and args.scope != "project":
        parser.error("--init-config applies only when --scope is project")
    if args.action == "doctor" and args.dry_run:
        parser.error("--dry-run does not apply to doctor")
    if args.skills_dir is not None and args.agent == "all":
        parser.error("--agent all cannot be combined with --skills-dir")

    if args.action == "doctor":
        result, code = doctor(args.scope, args.project_root)
    elif args.skills_dir is None and args.agent == "all":
        result, code = _run_all_agents(args.action, args)
    else:
        skills_dir = (
            args.skills_dir.expanduser().resolve()
            if args.skills_dir is not None
            else resolve_skills_dir(args.agent, args.scope, args.project_root)
        )
        try:
            result = _run_single_target(args.action, skills_dir, args)
            code = 1 if result["status"] == "missing" else 0
        except (InstallError, OSError, RuntimeError, UnicodeError) as exc:
            result = {"action": args.action, "skills_dir": str(skills_dir), "status": "error", "error": _format_error(exc)}
            code = 1

    if args.action == "install" and args.init_config and code == 0:
        try:
            result["config"] = init_project_config(args.project_root, dry_run=args.dry_run)
        except (InstallError, OSError, RuntimeError, UnicodeError) as exc:
            result["status"] = "error"
            result["error"] = _format_error(exc)
            code = 1

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        _print_text_result(args.action, result, args)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
