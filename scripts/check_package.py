"""Skill package structure and link validation (`validate.py package`)."""

from __future__ import annotations

import json
import os
import pathlib
import re
import urllib.parse
from typing import Any, Callable

try:
    from scripts.daw_common import (
        CANONICAL_TEMPLATES,
        SCHEMA_VERSION,
        DuplicateKeyError,
        check_skill_references,
        extract_frontmatter_metadata_version,
        extract_markdown_links,
        parse_frontmatter,
        parse_strict_json,
        resolve_bounded_path,
    )
except ImportError:
    from daw_common import (  # type: ignore[import-not-found]
        CANONICAL_TEMPLATES,
        SCHEMA_VERSION,
        DuplicateKeyError,
        check_skill_references,
        extract_frontmatter_metadata_version,
        extract_markdown_links,
        parse_frontmatter,
        parse_strict_json,
        resolve_bounded_path,
    )

ROUTING_SECTION_FIELDS = (
    "Trigger",
    "Inputs & Prerequisites",
    "Required Capability",
    "Conditional Capabilities",
    "Template Link",
    "Output Contract",
    "Exit Criterion",
    "Downstream Handoff",
    "Stop / Replan Trigger",
)

PACKAGE_LIMITATIONS = [
    "Structural and link verification only; does not verify semantic quality of instructions.",
    "Structural check does not assess capability or host integration availability; no external skills expected.",
]

_PLUGIN_NAME = "deterministic-agentic-workflow"


def _read_bounded_json_object(
    root_path: pathlib.Path,
    rel_path: str,
    add_error: Callable[[str, str, str], None],
) -> dict[str, Any] | None:
    """Resolve rel_path within root_path and parse it as a strict JSON object."""
    resolved, err = resolve_bounded_path(root_path, rel_path)
    if err == "symlink_escapes_root":
        add_error("symlink_escapes_package", rel_path, f"Manifest path escapes package root: {rel_path}")
        return None
    if err:
        add_error("path_escapes_package", rel_path, f"Manifest path escapes package root: {rel_path}")
        return None
    if resolved is None or not resolved.is_file():
        add_error("invalid_plugin_manifest", rel_path, f"Manifest exists but is not a regular file: {rel_path}")
        return None
    try:
        raw_text = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        add_error("utf8_decode_error", rel_path, f"{rel_path} could not be decoded as UTF-8.")
        return None
    except OSError:
        add_error("file_read_error", rel_path, f"Failed to read {rel_path}.")
        return None
    try:
        data = parse_strict_json(raw_text)
    except (json.JSONDecodeError, DuplicateKeyError, RecursionError, ValueError) as exc:
        add_error("invalid_plugin_json", rel_path, f"Invalid JSON in {rel_path}: {exc}")
        return None
    if not isinstance(data, dict):
        add_error("invalid_plugin_json", rel_path, f"{rel_path} must be a JSON object.")
        return None
    return data


def _check_bounded_manifest_path(
    root_path: pathlib.Path,
    manifest_rel: str,
    candidate_rel: str,
    add_error: Callable[[str, str, str], None],
) -> None:
    """Verify a relative path declared inside a plugin manifest stays within root_path."""
    _, err = resolve_bounded_path(root_path, candidate_rel)
    if err == "symlink_escapes_root":
        add_error("symlink_escapes_package", manifest_rel, f"Manifest path escapes package root: {candidate_rel}")
    elif err:
        add_error("path_escapes_package", manifest_rel, f"Manifest path escapes package root: {candidate_rel}")


_PLUGIN_DIRS = (".claude-plugin", ".cursor-plugin", ".codex-plugin")


def _validate_single_plugin_dir(
    root_path: pathlib.Path,
    plugin_rel: str,
    ver_text: str | None,
    add_error: Callable[[str, str, str], None],
) -> None:
    """Validate optional `<plugin_rel>/plugin.json` (and `marketplace.json` if present)."""
    plugin_dir_raw = root_path / plugin_rel
    if not (plugin_dir_raw.exists() or plugin_dir_raw.is_symlink()):
        return
    plugin_dir, dir_err = resolve_bounded_path(root_path, plugin_rel)
    if dir_err == "symlink_escapes_root":
        add_error("symlink_escapes_package", plugin_rel, "Plugin directory escapes package root or cannot be safely resolved.")
        return
    if dir_err:
        add_error("path_escapes_package", plugin_rel, "Plugin directory escapes package root or cannot be safely resolved.")
        return
    if plugin_dir is None or not plugin_dir.is_dir():
        return

    plugin_json_rel = f"{plugin_rel}/plugin.json"
    plugin_raw = plugin_dir / "plugin.json"
    if plugin_raw.exists() or plugin_raw.is_symlink():
        plugin_data = _read_bounded_json_object(root_path, plugin_json_rel, add_error)
        if plugin_data is not None:
            plugin_name = plugin_data.get("name")
            if not isinstance(plugin_name, str) or plugin_name != _PLUGIN_NAME:
                add_error(
                    "plugin_name_mismatch",
                    plugin_json_rel,
                    f"plugin.json 'name' must be '{_PLUGIN_NAME}'.",
                )
            plugin_version = plugin_data.get("version")
            if not isinstance(plugin_version, str) or not plugin_version.strip():
                add_error(
                    "plugin_version_mismatch",
                    plugin_json_rel,
                    "plugin.json 'version' must be a non-empty string.",
                )
            elif ver_text is not None and plugin_version != ver_text:
                add_error(
                    "plugin_version_mismatch",
                    plugin_json_rel,
                    "plugin.json 'version' does not match package VERSION.",
                )
            skills_val = plugin_data.get("skills")
            if skills_val is not None:
                if not isinstance(skills_val, list) or any(not isinstance(s, str) for s in skills_val):
                    add_error(
                        "invalid_plugin_json",
                        plugin_json_rel,
                        "plugin.json 'skills' must be a list of relative paths.",
                    )
                else:
                    for entry in skills_val:
                        _check_bounded_manifest_path(root_path, plugin_json_rel, entry, add_error)

    mkt_json_rel = f"{plugin_rel}/marketplace.json"
    marketplace_raw = plugin_dir / "marketplace.json"
    if marketplace_raw.exists() or marketplace_raw.is_symlink():
        mkt_data = _read_bounded_json_object(root_path, mkt_json_rel, add_error)
        if mkt_data is not None and isinstance(mkt_data.get("plugins"), list):
            for entry in mkt_data["plugins"]:
                if not isinstance(entry, dict):
                    continue
                if isinstance(entry.get("source"), str):
                    _check_bounded_manifest_path(
                        root_path, mkt_json_rel, entry["source"], add_error
                    )
                entry_ver = entry.get("version")
                if entry_ver is not None and ver_text is not None and entry_ver != ver_text:
                    add_error(
                        "plugin_version_mismatch",
                        mkt_json_rel,
                        "marketplace.json plugin 'version' does not match package VERSION.",
                    )


def _validate_claude_plugin(
    root_path: pathlib.Path,
    ver_text: str | None,
    add_error: Callable[[str, str, str], None],
) -> None:
    """Validate optional plugin manifest directories (`.claude-plugin`, `.cursor-plugin`, `.codex-plugin`)."""
    for plugin_rel in _PLUGIN_DIRS:
        _validate_single_plugin_dir(root_path, plugin_rel, ver_text, add_error)


def validate_package(root_path: pathlib.Path) -> dict[str, Any]:
    root_path = root_path.resolve()
    findings: list[dict[str, str]] = []
    ver_text: str | None = None

    def add_error(code: str, path: str, message: str) -> None:
        findings.append({"severity": "error", "code": code, "path": path, "message": message})

    def add_warning(code: str, path: str, message: str) -> None:
        findings.append({"severity": "warning", "code": code, "path": path, "message": message})

    # 1. Required files
    required_files = [
        "SKILL.md",
        "references/routing.md",
        "references/operations.md",
        "references/validation.md",
        "references/installation.md",
        "references/task-contract.example.json",
        "scripts/validate.py",
    ]

    for rf in required_files:
        p, err = resolve_bounded_path(root_path, rf)
        if err == "symlink_escapes_root":
            add_error("symlink_escapes_package", rf, "Required file path escapes package root or cannot be safely resolved.")
            continue
        elif err:
            add_error("path_escapes_package", rf, "Required file path escapes package root or cannot be safely resolved.")
            continue
        if p is None or not p.is_file():
            add_error("missing_required_file", rf, f"Required file is missing: {rf}")

    # 2. Templates directory
    tpl_dir, tpl_err = resolve_bounded_path(root_path, "templates")
    if tpl_err == "symlink_escapes_root":
        add_error("symlink_escapes_package", "templates", "Templates directory escapes package root or cannot be safely resolved.")
    elif tpl_err:
        add_error("path_escapes_package", "templates", "Templates directory escapes package root or cannot be safely resolved.")
    elif tpl_dir is None or not tpl_dir.is_dir():
        add_error("missing_templates_dir", "templates", "Templates directory is missing.")
    else:
        for ct in CANONICAL_TEMPLATES:
            cp = tpl_dir / ct
            if cp.is_symlink():
                try:
                    resolved_cp = cp.resolve()
                    resolved_cp.relative_to(root_path)
                except (ValueError, OSError):
                    add_error("symlink_escapes_package", f"templates/{ct}", f"Template symlink escapes package root: {ct}")
                    continue
            if not cp.is_file():
                add_error("missing_canonical_template", f"templates/{ct}", f"Canonical template is missing: {ct}")

        try:
            for item in tpl_dir.iterdir():
                if item.name.endswith(".md"):
                    if item.is_symlink():
                        try:
                            item.resolve().relative_to(root_path)
                        except (ValueError, OSError):
                            add_error("symlink_escapes_package", f"templates/{item.name}", f"Template symlink escapes package root: {item.name}")
                            continue
                    if item.is_file() and item.name not in CANONICAL_TEMPLATES:
                        add_error("unrecognized_template", f"templates/{item.name}", f"Unrecognized template in templates/: {item.name}")
        except OSError:
            add_error("templates_read_error", "templates", "Failed to inspect templates directory.")

    # 3. Frontmatter validation in SKILL.md
    skill_file = root_path / "SKILL.md"
    if skill_file.is_file() and not any(f["path"] == "SKILL.md" and f["code"] in ("symlink_escapes_package", "path_escapes_package") for f in findings):
        try:
            skill_content = skill_file.read_text(encoding="utf-8")
            fm, fm_errors = parse_frontmatter(skill_content)
            for f_err in fm_errors:
                add_error("invalid_frontmatter", "SKILL.md", f_err)

            if fm is not None:
                name_val = fm.get("name")
                if not name_val:
                    add_error("missing_frontmatter_name", "SKILL.md:name", "Missing 'name' in frontmatter.")
                else:
                    # Stricter kebab-case syntax: lowercase alphanumeric and hyphens, no leading/trailing hyphens, no consecutive hyphens
                    if len(name_val) > 64 or not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", name_val):
                        add_error(
                            "invalid_frontmatter_name",
                            "SKILL.md:name",
                            "Frontmatter 'name' must be lowercase kebab-case (alphanumeric and hyphens, no leading/trailing/consecutive hyphens) and <= 64 characters.",
                        )
                    elif name_val != root_path.name and not (name_val == _PLUGIN_NAME and root_path.name == "daw-flow"):
                        add_error(
                            "frontmatter_name_mismatch",
                            "SKILL.md:name",
                            "Frontmatter 'name' does not match the package root directory name.",
                        )

                desc_val = fm.get("description")
                if not desc_val or not desc_val.strip():
                    add_error("missing_frontmatter_description", "SKILL.md:description", "Missing or empty 'description' in frontmatter.")
                elif len(desc_val) > 1024:
                    add_error("invalid_frontmatter_description", "SKILL.md:description", "Frontmatter 'description' exceeds 1024 characters.")

                compat_val = fm.get("compatibility")
                if compat_val and len(compat_val) > 500:
                    add_error("invalid_frontmatter_compatibility", "SKILL.md:compatibility", "Frontmatter 'compatibility' exceeds 500 characters.")

            # Version consistency check
            version_file, version_err = resolve_bounded_path(root_path, "VERSION")
            if version_err:
                add_error("path_escapes_package", "VERSION", "VERSION path escapes package root or cannot be safely resolved.")
            elif version_file is not None and version_file.is_file():
                try:
                    ver_text = version_file.read_text(encoding="utf-8").strip()
                    meta_ver = extract_frontmatter_metadata_version(skill_content)
                    if meta_ver is None or meta_ver != ver_text:
                        add_error("version_mismatch", "VERSION", "Package VERSION does not match SKILL.md metadata.version.")
                except (OSError, UnicodeError):
                    add_error("version_mismatch", "VERSION", "Package VERSION could not be read as UTF-8 text.")
        except UnicodeDecodeError:
            add_error("utf8_decode_error", "SKILL.md", "SKILL.md could not be decoded as UTF-8.")
        except OSError:
            add_error("file_read_error", "SKILL.md", "Failed to read SKILL.md.")

    # 4. Check routing.md sections and 9 fields
    routing_file = root_path / "references" / "routing.md"
    if routing_file.is_file() and not any(
        "routing.md" in f["path"]
        and f["code"] in ("symlink_escapes_package", "path_escapes_package")
        for f in findings
    ):
        try:
            r_content = routing_file.read_text(encoding="utf-8")
            pattern = r"###\s+(\d+)\.\s+`([^`]+)`"
            sections = re.findall(pattern, r_content)
            found_templates = [s[1] for s in sections]
            if len(sections) != len(CANONICAL_TEMPLATES) or set(found_templates) != set(
                CANONICAL_TEMPLATES
            ):
                add_error(
                    "routing_sections_mismatch",
                    "references/routing.md",
                    f"references/routing.md must contain exactly {len(CANONICAL_TEMPLATES)} sections for canonical templates.",
                )

            section_splits = re.split(r"(?=###\s+\d+\.\s+`[^`]+`)", r_content)
            for chunk in section_splits:
                m_sec = re.match(r"###\s+(\d+)\.\s+`([^`]+)`", chunk)
                if not m_sec:
                    continue
                sec_name = m_sec.group(2)
                for field in ROUTING_SECTION_FIELDS:
                    f_pattern = rf"\*\*{re.escape(field)}:?\*\*:?"
                    if not re.search(f_pattern, chunk):
                        section_path = f"references/routing.md:{sec_name}" if sec_name in CANONICAL_TEMPLATES else "references/routing.md"
                        add_error("routing_field_missing", section_path, f"Routing section missing required field `{field}`.")
        except UnicodeDecodeError:
            add_error("utf8_decode_error", "references/routing.md", "references/routing.md could not be decoded as UTF-8.")
        except OSError:
            add_error("file_read_error", "references/routing.md", "Failed to read references/routing.md.")

    # 5. Check markdown files for balanced code fences, skill://, and valid relative links
    all_md_files: list[pathlib.Path] = []
    try:
        for cur_root, dirs, files in os.walk(root_path, followlinks=False):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("__pycache__", "venv", ".venv")]
            cur_root_p = pathlib.Path(cur_root)
            for directory in dirs[:]:
                rel_dir = (cur_root_p / directory).relative_to(root_path).as_posix()
                _, err = resolve_bounded_path(root_path, rel_dir)
                if err == "symlink_escapes_root":
                    add_error("symlink_escapes_package", rel_dir, "Directory escapes package root or cannot be safely resolved.")
                    dirs.remove(directory)
                elif err:
                    add_error("path_escapes_package", rel_dir, "Directory escapes package root or cannot be safely resolved.")
                    dirs.remove(directory)
            for f in files:
                if f.endswith(".md"):
                    item_p = cur_root_p / f
                    if item_p.is_symlink():
                        try:
                            item_p.resolve().relative_to(root_path)
                        except (ValueError, OSError):
                            add_error(
                                "symlink_escapes_package",
                                item_p.relative_to(root_path).as_posix(),
                                f"Markdown symlink escapes package root: {f}",
                            )
                            continue
                    all_md_files.append(item_p)
    except OSError:
        add_error("walk_error", ".", "Failed to walk package directory.")

    for md_file in all_md_files:
        try:
            rel_md = md_file.relative_to(root_path).as_posix()
        except ValueError:
            continue

        try:
            text = md_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            add_error("utf8_decode_error", rel_md, f"Markdown file {rel_md} could not be decoded as UTF-8.")
            continue
        except OSError:
            add_error("file_read_error", rel_md, f"Failed to read {rel_md}.")
            continue

        for _, line_no in check_skill_references(text):
            add_error("prohibited_uri_scheme", f"{rel_md}:{line_no}", "Prohibited non-portable 'skill://' URI outside code fence.")

        # Check code fence balance with length tracking
        fence_stack: list[tuple[str, int]] = []
        for line_no, line in enumerate(text.splitlines(), start=1):
            m_f = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
            if m_f:
                marker = m_f.group(1)
                info = m_f.group(2).strip()
                char = marker[0]
                cur_len = len(marker)
                if not fence_stack:
                    fence_stack.append((char, cur_len))
                else:
                    top_char, top_len = fence_stack[-1]
                    if char == top_char and cur_len >= top_len and not info:
                        fence_stack.pop()
        if fence_stack:
            add_error("unbalanced_code_fence", rel_md, "Unbalanced code fence in markdown file.")

        for target, line_no in extract_markdown_links(text):
            if re.match(r"^(https?://|mailto:|#)", target):
                continue

            # Percent-decode before path checking
            decoded_target = urllib.parse.unquote(target)

            # Reject Windows absolute links like C:\... or \\UNC even on Linux
            if re.match(r"^[a-zA-Z]:", decoded_target) or decoded_target.startswith(("\\\\", "//")):
                add_error("absolute_link_rejected", f"{rel_md}:{line_no}", "Absolute Windows path or drive letter link rejected.")
                continue
            if decoded_target.startswith(("/", "\\")):
                add_error("absolute_link_rejected", f"{rel_md}:{line_no}", "Absolute path link rejected.")
                continue

            clean_target = decoded_target.split("#")[0].split("?")[0].strip()
            if not clean_target:
                continue

            link_resolved = md_file.parent / clean_target
            try:
                resolved_abs = link_resolved.resolve()
                resolved_abs.relative_to(root_path)
            except (ValueError, OSError):
                add_error("link_escapes_package", f"{rel_md}:{line_no}", "Link destination escapes package root.")
                continue

            if not (resolved_abs.is_file() or resolved_abs.is_dir()):
                add_error("broken_relative_link", f"{rel_md}:{line_no}", "Link destination does not exist.")

    if ver_text is None:
        v_file, v_err = resolve_bounded_path(root_path, "VERSION")
        if v_err is None and v_file is not None and v_file.is_file():
            try:
                ver_text = v_file.read_text(encoding="utf-8").strip()
            except (OSError, UnicodeError):
                pass
    _validate_claude_plugin(root_path, ver_text, add_error)

    valid = not any(f["severity"] == "error" for f in findings)
    return {
        "schema_version": SCHEMA_VERSION,
        "check": "package",
        "valid": valid,
        "findings": findings,
        "limitations": PACKAGE_LIMITATIONS,
    }
