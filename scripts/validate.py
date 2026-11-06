#!/usr/bin/env python3
"""Deterministic Agentic Workflow Validator.

A read-only, zero-dependency Python 3.10+ command-line utility for structural
and boundary validation of the agent skill package and task contracts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.parse
from typing import Any

SCHEMA_VERSION = 1

CANONICAL_TEMPLATES = (
    "blueprint.md",
    "brd.md",
    "deployment.md",
    "design.md",
    "frd.md",
    "prd.md",
    "qa.md",
    "roadmap.md",
    "runbook.md",
    "security.md",
    "techstack.md",
    "ui-ux.md",
    "wireframe.md",
)

CANONICAL_DOC_STEMS = set(t.removesuffix(".md") for t in CANONICAL_TEMPLATES)

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

CONTRACT_LIMITATIONS = [
    "Structural verification only; does not authenticate evidence authenticity, runtime safety, or operational authorization.",
    "Approval presence captures an opaque reference only and does not constitute runtime authorization.",
    "Baseline hashes verify current files only at plan/execute; complete checks historical record structure and boundaries. Revision strings are not verified against VCS history.",
]


class DuplicateKeyError(ValueError):
    """Raised when duplicate keys are encountered in JSON payload."""


def _strict_json_object_pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for k, v in pairs:
        if k in obj:
            raise DuplicateKeyError("Duplicate key detected in JSON object.")
        obj[k] = v
    return obj


def _reject_nonstandard_json_constants(val: str) -> None:
    raise ValueError("Non-standard JSON constant rejected.")


def parse_strict_json(raw_text: str) -> Any:
    return json.loads(
        raw_text,
        object_pairs_hook=_strict_json_object_pairs_hook,
        parse_constant=_reject_nonstandard_json_constants,
    )

def is_safe_relative_path(path_str: str) -> bool:
    if not path_str or not path_str.strip():
        return False
    if re.match(r"^[a-zA-Z]:", path_str):
        return False
    if path_str.startswith(("\\\\", "//")):
        return False
    # Check absolute POSIX path
    if path_str.startswith(("/", "\\")):
        return False
    # Check traversal
    parts = re.split(r"[\\/]+", path_str)
    if not parts or parts[0] == "":
        return False
    depth = 0
    for p in parts:
        if p == "..":
            depth -= 1
            if depth < 0:
                return False
        elif p != "." and p != "":
            depth += 1
    return True


def resolve_bounded_path(root_dir: pathlib.Path, rel_path_str: str) -> tuple[pathlib.Path | None, str | None]:
    if not is_safe_relative_path(rel_path_str):
        return None, "absolute_or_traversal_path"
    try:
        candidate = root_dir / rel_path_str
        # If candidate path or any parent is a symlink, verify it stays within root_dir
        if candidate.is_symlink():
            try:
                resolved = candidate.resolve()
                resolved.relative_to(root_dir.resolve())
            except (ValueError, OSError):
                return None, "symlink_escapes_root"
            return resolved, None
        else:
            try:
                resolved = candidate.resolve()
                resolved.relative_to(root_dir.resolve())
            except (ValueError, OSError):
                return None, "path_escapes_root"
            return resolved, None
    except Exception:
        return None, "path_resolution_error"


def compute_sha256(file_path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower()


def parse_frontmatter(content: str) -> tuple[dict[str, str] | None, list[str]]:
    """Parse YAML frontmatter strictly for required scalar fields.

    Returns (data_dict, errors).
    """
    errors: list[str] = []
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, ["Missing frontmatter opening delimiter (---)."]
    end_idx = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx == -1:
        return None, ["Missing frontmatter closing delimiter (---)."]

    f_lines = lines[1:end_idx]
    result: dict[str, str] = {}
    i = 0
    while i < len(f_lines):
        line = f_lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        # Look for top-level key: value
        m = re.match(r"^([a-zA-Z0-9_-]+)\s*:\s*(.*)$", line)
        if not m:
            i += 1
            continue

        key = m.group(1).strip()
        val = m.group(2).strip()

        # Check if value is a folded or literal multiline indicator
        if val in (">", "|", ">-", "|-"):
            val_lines = []
            i += 1
            while i < len(f_lines):
                subline = f_lines[i]
                if subline.startswith("  ") or subline.startswith("\t"):
                    val_lines.append(subline.strip())
                    i += 1
                else:
                    break
            result[key] = " ".join(val_lines)
            continue

        # If value is empty, check if next line is nested mapping or list (which makes this non-scalar)
        if not val:
            if i + 1 < len(f_lines):
                next_line = f_lines[i + 1]
                if next_line.startswith("  ") or next_line.startswith("\t"):
                    # This is a nested structure (e.g. map or list)
                    # If this is one of the required scalar keys, record an error
                    if key in ("name", "description", "compatibility"):
                        errors.append("Required frontmatter field must be a scalar string, not a nested mapping or list.")
                    # Skip the nested lines
                    i += 1
                    while i < len(f_lines) and (f_lines[i].startswith("  ") or f_lines[i].startswith("\t") or not f_lines[i].strip()):
                        i += 1
                    continue

        # Check quoted strings for proper matching quotes
        if val.startswith('"'):
            if not val.endswith('"') or len(val) < 2:
                errors.append("Unclosed or unterminated double quote in frontmatter scalar field.")
                i += 1
                continue
            val = val[1:-1]
        elif val.startswith("'"):
            if not val.endswith("'") or len(val) < 2:
                errors.append("Unclosed or unterminated single quote in frontmatter scalar field.")
                i += 1
                continue
            val = val[1:-1]
        else:
            # Check for illegal trailing unclosed quote
            if val.endswith('"') or val.endswith("'"):
                errors.append("Mismatched quotes in frontmatter scalar field.")
                i += 1
                continue
            if key in ("name", "description", "compatibility"):
                plain = re.split(r"\s+#", val, maxsplit=1)[0].strip()
                nonstring_word = plain.lower() in {
                    "null", "~", "true", "false", "yes", "no", "on", "off", ".nan", ".inf", "+.inf", "-.inf",
                }
                numeric = re.fullmatch(
                    r"[-+]?(?:0[xX][0-9a-fA-F_]+|0[oO][0-7_]+|0[bB][01_]+|"
                    r"(?:[0-9][0-9_]*(?:\.[0-9_]*)?|\.[0-9_]+)(?:[eE][-+]?[0-9]+)?|"
                    r"[0-9][0-9_]*(?::[0-5]?[0-9])+(?:\.[0-9_]*)?)",
                    plain,
                )
                timestamp = re.match(r"^\d{4}-\d{1,2}-\d{1,2}(?:$|[Tt\s])", plain)
                unsupported = plain.startswith(("[", "{", "&", "*", "!", "- ", "? ", ": "))
                if nonstring_word or numeric or timestamp or unsupported:
                    errors.append("Required frontmatter field must use a supported scalar string; quote string values that resemble YAML types.")
                    i += 1
                    continue

        result[key] = val
        i += 1

    return result, errors


def extract_markdown_links(content: str) -> list[tuple[str, int]]:
    """Extract local file links from markdown, honoring nested code fences and inline code spans.

    Returns a list of (link_target, line_number).
    """
    links: list[tuple[str, int]] = []
    lines = content.splitlines()
    in_fence = False
    fence_char = ""
    fence_len = 0

    for line_no, line in enumerate(lines, start=1):
        # A code fence may have up to 3 leading spaces
        m_fence = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if m_fence:
            marker = m_fence.group(1)
            info = m_fence.group(2).strip()
            char = marker[0]
            cur_len = len(marker)
            if not in_fence:
                # Open fence
                in_fence = True
                fence_char = char
                fence_len = cur_len
                continue
            else:
                # Close fence requires same char, length >= opener, and no info string
                if char == fence_char and cur_len >= fence_len and not info:
                    in_fence = False
                    fence_char = ""
                    fence_len = 0
                    continue

        if in_fence:
            continue

        # Strip inline code spans: `...`
        sanitized = re.sub(r"`[^`]*`", "", line)

        # Match markdown links: [text](target) and images ![text](target)
        for m in re.finditer(r"(?:!?)\[.*?\]\(([^)\s]+)(?:\s+[\"'].*?[\"'])?\)", sanitized):
            target = m.group(1).strip()
            links.append((target, line_no))

        # Match reference-style link definitions: [label]: target
        m_ref = re.match(r"^\s*\[[^\]]+\]:\s*(\S+)", sanitized)
        if m_ref:
            target = m_ref.group(1).strip()
            links.append((target, line_no))

    return links


def check_skill_references(content: str) -> list[tuple[str, int]]:
    """Find proprietary skill:// references outside code fences."""
    issues: list[tuple[str, int]] = []
    lines = content.splitlines()
    in_fence = False
    fence_char = ""
    fence_len = 0

    for line_no, line in enumerate(lines, start=1):
        m_fence = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if m_fence:
            marker = m_fence.group(1)
            info = m_fence.group(2).strip()
            char = marker[0]
            cur_len = len(marker)
            if not in_fence:
                in_fence = True
                fence_char = char
                fence_len = cur_len
                continue
            else:
                if char == fence_char and cur_len >= fence_len and not info:
                    in_fence = False
                    fence_char = ""
                    fence_len = 0
                    continue

        if in_fence:
            continue

        if "skill://" in line:
            issues.append(("skill://", line_no))

    return issues


def extract_frontmatter_metadata_version(content: str) -> str | None:
    """Extract metadata.version from YAML frontmatter block if present."""
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    end_idx = -1
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break
    if end_idx == -1:
        return None
    f_lines = lines[1:end_idx]
    in_metadata = False
    for line in f_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m_top = re.match(r"^([a-zA-Z0-9_-]+)\s*:\s*(.*)$", line)
        if m_top:
            key = m_top.group(1).strip()
            val = m_top.group(2).strip()
            if key == "metadata" and not val:
                in_metadata = True
                continue
            else:
                in_metadata = False
        elif in_metadata:
            m_sub = re.match(r"^\s+([a-zA-Z0-9_-]+)\s*:\s*(.*)$", line)
            if m_sub:
                sub_key = m_sub.group(1).strip()
                sub_val = m_sub.group(2).strip()
                if sub_key == "version":
                    if (sub_val.startswith('"') and sub_val.endswith('"') and len(sub_val) >= 2) or (
                        sub_val.startswith("'") and sub_val.endswith("'") and len(sub_val) >= 2
                    ):
                        return sub_val[1:-1]
                    return sub_val
    return None


def validate_package(root_path: pathlib.Path) -> dict[str, Any]:
    root_path = root_path.resolve()
    findings: list[dict[str, str]] = []

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
                    elif name_val != root_path.name:
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

    # 4. Check routing.md 13 sections and 9 fields
    routing_file = root_path / "references" / "routing.md"
    if routing_file.is_file() and not any("routing.md" in f["path"] and f["code"] in ("symlink_escapes_package", "path_escapes_package") for f in findings):
        try:
            r_content = routing_file.read_text(encoding="utf-8")
            pattern = r"###\s+(\d+)\.\s+`([^`]+)`"
            sections = re.findall(pattern, r_content)
            found_templates = [s[1] for s in sections]
            if len(sections) != 13 or set(found_templates) != set(CANONICAL_TEMPLATES):
                add_error("routing_sections_mismatch", "references/routing.md", "references/routing.md must contain exactly 13 sections for canonical templates.")

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

    valid = not any(f["severity"] == "error" for f in findings)
    return {
        "schema_version": SCHEMA_VERSION,
        "check": "package",
        "valid": valid,
        "findings": findings,
        "limitations": PACKAGE_LIMITATIONS,
    }


def validate_contract(
    contract_data: Any,
    project_root: pathlib.Path,
    stage: str,
) -> dict[str, Any]:
    findings: list[dict[str, str]] = []

    def add_error(code: str, path: str, message: str) -> None:
        findings.append({"severity": "error", "code": code, "path": path, "message": message})

    def add_warning(code: str, path: str, message: str) -> None:
        findings.append({"severity": "warning", "code": code, "path": path, "message": message})

    if not isinstance(contract_data, dict):
        add_error("invalid_contract_type", "$", "Task contract must be a JSON object.")
        return {
            "schema_version": SCHEMA_VERSION,
            "check": "contract",
            "valid": False,
            "findings": findings,
            "limitations": CONTRACT_LIMITATIONS,
        }

    ALLOWED_TOP_FIELDS = {
        "schema_version",
        "objective",
        "baseline",
        "documents",
        "acceptance_criteria",
        "operation",
        "approval",
        "evidence",
    }
    REQUIRED_TOP_FIELDS = {
        "schema_version",
        "objective",
        "baseline",
        "documents",
        "acceptance_criteria",
        "operation",
    }

    # Unknown fields: do NOT echo user-controlled key names
    has_unknown_top = False
    for k in contract_data.keys():
        if k not in ALLOWED_TOP_FIELDS:
            has_unknown_top = True
    if has_unknown_top:
        add_error("unknown_field", "$", "Unknown field detected in task contract root schema.")

    for k in REQUIRED_TOP_FIELDS:
        if k not in contract_data:
            add_error("missing_required_field", k, f"Missing required top-level field: {k}")

    # schema_version
    sv = contract_data.get("schema_version")
    if isinstance(sv, bool) or not isinstance(sv, int) or sv != 1:
        add_error("invalid_schema_version", "schema_version", "Field 'schema_version' must be integer 1.")

    # objective
    obj = contract_data.get("objective")
    if not isinstance(obj, str) or not obj.strip():
        add_error("invalid_objective", "objective", "Field 'objective' must be a non-blank string.")

    # baseline
    base_data = contract_data.get("baseline")
    baseline_revision: str | None = None
    if not isinstance(base_data, dict):
        add_error("invalid_baseline", "baseline", "Field 'baseline' must be an object.")
    else:
        ALLOWED_BASELINE_FIELDS = {"revision", "files"}
        has_unknown_base = False
        for bk in base_data.keys():
            if bk not in ALLOWED_BASELINE_FIELDS:
                has_unknown_base = True
        if has_unknown_base:
            add_error("unknown_field", "baseline", "Unknown field detected in baseline schema.")

        b_rev = base_data.get("revision")
        if not isinstance(b_rev, str) or not b_rev.strip():
            add_error("invalid_baseline_revision", "baseline.revision", "Field 'baseline.revision' must be a non-blank string.")
        else:
            baseline_revision = b_rev

        b_files = base_data.get("files")
        if not isinstance(b_files, list):
            add_error("invalid_baseline_files", "baseline.files", "Field 'baseline.files' must be an array.")
        else:
            if len(b_files) == 0:
                if stage == "plan":
                    add_warning(
                        "baseline_unverified",
                        "baseline.files",
                        "Baseline file list is empty; pre-execution state cannot be verified against file hashes.",
                    )
                else:
                    add_error(
                        "baseline_files_required",
                        "baseline.files",
                        f"Stage '{stage}' requires at least 1 file in baseline.files.",
                    )
            seen_base_paths: set[str] = set()
            for idx, bf in enumerate(b_files):
                f_path_loc = f"baseline.files[{idx}]"
                if not isinstance(bf, dict):
                    add_error("invalid_baseline_entry", f_path_loc, "Baseline file entry must be an object.")
                    continue
                ALLOWED_BF_FIELDS = {"path", "sha256"}
                has_unknown_bf = False
                for bfk in bf.keys():
                    if bfk not in ALLOWED_BF_FIELDS:
                        has_unknown_bf = True
                if has_unknown_bf:
                    add_error("unknown_field", f_path_loc, "Unknown field detected in baseline file schema.")

                f_rel = bf.get("path")
                f_hash = bf.get("sha256")
                if not isinstance(f_rel, str) or not f_rel.strip():
                    add_error("invalid_path", f"{f_path_loc}.path", "Baseline file path must be non-blank string.")
                    continue
                if f_rel in seen_base_paths:
                    add_error("duplicate_baseline_path", f"{f_path_loc}.path", "Duplicate path in baseline files.")
                seen_base_paths.add(f_rel)

                if not isinstance(f_hash, str) or not re.match(r"^[0-9a-f]{64}$", f_hash.lower()):
                    add_error("invalid_sha256", f"{f_path_loc}.sha256", "Baseline sha256 must be a 64-character lowercase hex string.")

                resolved_p, err = resolve_bounded_path(project_root, f_rel)
                if err:
                    add_error("boundary_violation", f"{f_path_loc}.path", f"Baseline path violates boundary: {err}")
                elif stage != "complete":
                    if resolved_p is None or not resolved_p.is_file():
                        add_error("file_not_found", f"{f_path_loc}.path", "Baseline file does not exist.")
                    else:
                        try:
                            actual_hash = compute_sha256(resolved_p)
                            if isinstance(f_hash, str) and actual_hash != f_hash.lower():
                                add_error(
                                    "baseline_changed",
                                    f"{f_path_loc}",
                                    "Baseline file content changed since the recorded hash.",
                                )
                        except OSError:
                            add_error("file_read_error", f"{f_path_loc}.path", "Failed to read baseline file.")
    # documents
    docs_data = contract_data.get("documents")
    if not isinstance(docs_data, list):
        add_error("invalid_documents", "documents", "Field 'documents' must be an array.")
    else:
        seen_kinds: set[str] = set()
        for idx, doc in enumerate(docs_data):
            d_loc = f"documents[{idx}]"
            if not isinstance(doc, dict):
                add_error("invalid_document_entry", d_loc, "Document entry must be an object.")
                continue
            ALLOWED_DOC_FIELDS = {"kind", "path", "status"}
            has_unknown_doc = False
            for dk in doc.keys():
                if dk not in ALLOWED_DOC_FIELDS:
                    has_unknown_doc = True
            if has_unknown_doc:
                add_error("unknown_field", d_loc, "Unknown field detected in document schema.")

            d_kind = doc.get("kind")
            d_path = doc.get("path")
            d_status = doc.get("status")

            if not isinstance(d_kind, str) or d_kind not in CANONICAL_DOC_STEMS:
                add_error("invalid_document_kind", f"{d_loc}.kind", "Document kind must be one of the 13 canonical stems.")
            elif d_kind in seen_kinds:
                add_error("duplicate_document_kind", f"{d_loc}.kind", f"Duplicate document kind: {d_kind}")
            else:
                seen_kinds.add(d_kind)

            if not isinstance(d_status, str) or d_status not in ("current", "draft", "stale", "conflicting"):
                add_error("invalid_document_status", f"{d_loc}.status", "Document status must be current|draft|stale|conflicting.")
            else:
                if d_status in ("stale", "conflicting"):
                    add_error("disallowed_document_status", f"{d_loc}.status", f"Document status '{d_status}' is rejected across all stages.")
                elif d_status == "draft" and stage in ("execute", "complete"):
                    add_error("draft_document_in_execution", f"{d_loc}.status", f"Draft document disallowed in stage '{stage}'.")

            if not isinstance(d_path, str) or not d_path.strip():
                add_error("invalid_path", f"{d_loc}.path", "Document path must be a non-blank string.")
            else:
                resolved_p, err = resolve_bounded_path(project_root, d_path)
                if err:
                    add_error("boundary_violation", f"{d_loc}.path", f"Document path violates boundary: {err}")
                elif resolved_p is None or not resolved_p.is_file():
                    add_error("file_not_found", f"{d_loc}.path", "Document file does not exist.")

    # acceptance_criteria
    ac_data = contract_data.get("acceptance_criteria")
    known_ac_ids: set[str] = set()
    if not isinstance(ac_data, list):
        add_error("invalid_acceptance_criteria", "acceptance_criteria", "Field 'acceptance_criteria' must be an array.")
    else:
        if len(ac_data) == 0:
            add_error("empty_acceptance_criteria", "acceptance_criteria", "Field 'acceptance_criteria' must not be empty.")
        for idx, ac in enumerate(ac_data):
            ac_loc = f"acceptance_criteria[{idx}]"
            if not isinstance(ac, dict):
                add_error("invalid_acceptance_criterion_entry", ac_loc, "Acceptance criterion entry must be an object.")
                continue
            ALLOWED_AC_FIELDS = {"id", "criterion"}
            has_unknown_ac = False
            for ack in ac.keys():
                if ack not in ALLOWED_AC_FIELDS:
                    has_unknown_ac = True
            if has_unknown_ac:
                add_error("unknown_field", ac_loc, "Unknown field detected in acceptance criterion schema.")

            ac_id = ac.get("id")
            ac_crit = ac.get("criterion")

            if not isinstance(ac_id, str) or not ac_id.strip():
                add_error("invalid_acceptance_criterion_id", f"{ac_loc}.id", "Acceptance criterion ID must be a non-blank string.")
            elif ac_id in known_ac_ids:
                add_error("duplicate_acceptance_criterion_id", f"{ac_loc}.id", "Duplicate acceptance criterion ID.")
            else:
                known_ac_ids.add(ac_id)

            if not isinstance(ac_crit, str) or not ac_crit.strip():
                add_error("invalid_acceptance_criterion_text", f"{ac_loc}.criterion", "Acceptance criterion text must be a non-blank string.")

    # operation
    op_data = contract_data.get("operation")
    op_risk: str | None = None
    op_action: str | None = None
    op_target: str | None = None
    op_revision: str | None = None
    op_scope: list[str] | None = None

    if not isinstance(op_data, dict):
        add_error("invalid_operation", "operation", "Field 'operation' must be an object.")
    else:
        ALLOWED_OP_FIELDS = {"risk", "action", "target", "revision", "scope"}
        has_unknown_op = False
        for opk in op_data.keys():
            if opk not in ALLOWED_OP_FIELDS:
                has_unknown_op = True
        if has_unknown_op:
            add_error("unknown_field", "operation", "Unknown field detected in operation schema.")

        op_risk = op_data.get("risk")
        if not isinstance(op_risk, str) or op_risk not in ("low", "high"):
            add_error("invalid_operation_risk", "operation.risk", "Operation risk must be 'low' or 'high'.")

        op_action = op_data.get("action")
        if not isinstance(op_action, str) or not op_action.strip():
            add_error("invalid_operation_action", "operation.action", "Operation action must be a non-blank string.")

        op_target = op_data.get("target")
        if not isinstance(op_target, str) or not op_target.strip():
            add_error("invalid_operation_target", "operation.target", "Operation target must be a non-blank string.")

        op_revision = op_data.get("revision")
        if not isinstance(op_revision, str) or not op_revision.strip():
            add_error("invalid_operation_revision", "operation.revision", "Operation revision must be a non-blank string.")
        elif baseline_revision is not None and op_revision != baseline_revision:
            add_error("revision_mismatch", "operation.revision", "operation.revision must match baseline.revision.")

        raw_scope = op_data.get("scope")
        if not isinstance(raw_scope, list) or len(raw_scope) == 0:
            add_error("invalid_operation_scope", "operation.scope", "Operation scope must be a non-empty array of strings.")
        else:
            seen_scope: set[str] = set()
            valid_scope = True
            for s in raw_scope:
                if not isinstance(s, str) or not s.strip():
                    valid_scope = False
                    break
                if s in seen_scope:
                    add_error("duplicate_operation_scope", "operation.scope", "Duplicate scope entry.")
                seen_scope.add(s)
            if not valid_scope:
                add_error("invalid_operation_scope_item", "operation.scope", "Scope entries must be non-blank strings.")
            else:
                op_scope = list(raw_scope)

    # approval (optional)
    app_data = contract_data.get("approval")
    if app_data is not None:
        if not isinstance(app_data, dict):
            add_error("invalid_approval", "approval", "Field 'approval' must be an object if present.")
        else:
            add_warning("approval_not_authorization", "approval", "Captured approval reference records user confirmation; does not authorize execution.")
            ALLOWED_APP_FIELDS = {"reference", "action", "target", "revision", "scope"}
            has_unknown_app = False
            for appk in app_data.keys():
                if appk not in ALLOWED_APP_FIELDS:
                    has_unknown_app = True
            if has_unknown_app:
                add_error("unknown_field", "approval", "Unknown field detected in approval schema.")

            app_ref = app_data.get("reference")
            if not isinstance(app_ref, str) or not app_ref.strip():
                add_error("invalid_approval_reference", "approval.reference", "Approval reference must be a non-blank opaque string.")

            app_action = app_data.get("action")
            app_target = app_data.get("target")
            app_rev = app_data.get("revision")
            app_scope = app_data.get("scope")

            if app_action != op_action:
                add_error("approval_binding_mismatch", "approval.action", "approval.action must equal operation.action.")
            if app_target != op_target:
                add_error("approval_binding_mismatch", "approval.target", "approval.target must equal operation.target.")
            if app_rev != op_revision:
                add_error("approval_binding_mismatch", "approval.revision", "approval.revision must equal operation.revision.")

            if not isinstance(app_scope, list) or len(app_scope) == 0:
                add_error("invalid_approval_scope", "approval.scope", "Approval scope must be a non-empty array of strings.")
            else:
                seen_app_scope: set[str] = set()
                valid_app_scope = True
                for s in app_scope:
                    if not isinstance(s, str) or not s.strip():
                        valid_app_scope = False
                        break
                    if s in seen_app_scope:
                        add_error("duplicate_approval_scope", "approval.scope", "Duplicate scope entry in approval.")
                    seen_app_scope.add(s)
                if not valid_app_scope:
                    add_error("invalid_approval_scope_item", "approval.scope", "Approval scope entries must be non-blank strings.")
                elif op_scope is not None:
                    if seen_app_scope != set(op_scope) or len(app_scope) != len(op_scope):
                        add_error("approval_binding_mismatch", "approval.scope", "approval.scope must exactly match operation.scope.")
    else:
        if op_risk == "high" and stage in ("execute", "complete"):
            add_error("missing_approval", "approval", f"Stage '{stage}' requires an approval object for high-risk operations.")

    # evidence (optional)
    seen_ev_criterion_ids: set[str] = set()
    ev_data = contract_data.get("evidence")
    if ev_data is not None:
        if not isinstance(ev_data, list):
            add_error("invalid_evidence", "evidence", "Field 'evidence' must be an array if present.")
        else:
            add_warning("evidence_unverified", "evidence", "Evidence files verified for presence only; semantic truth and authenticity not evaluated.")
            for idx, ev in enumerate(ev_data):
                ev_loc = f"evidence[{idx}]"
                if not isinstance(ev, dict):
                    add_error("invalid_evidence_entry", ev_loc, "Evidence entry must be an object.")
                    continue
                ALLOWED_EV_FIELDS = {"criterion_id", "status", "reference", "summary"}
                has_unknown_ev = False
                for evk in ev.keys():
                    if evk not in ALLOWED_EV_FIELDS:
                        has_unknown_ev = True
                if has_unknown_ev:
                    add_error("unknown_field", ev_loc, "Unknown field detected in evidence schema.")

                c_id = ev.get("criterion_id")
                e_stat = ev.get("status")
                e_ref = ev.get("reference")
                e_sum = ev.get("summary")

                if not isinstance(c_id, str) or not c_id.strip():
                    add_error("invalid_evidence_criterion_id", f"{ev_loc}.criterion_id", "Evidence criterion_id must be a non-blank string.")
                elif c_id not in known_ac_ids:
                    add_error("unknown_evidence_criterion_id", f"{ev_loc}.criterion_id", "Evidence references unknown acceptance criterion.")
                elif c_id in seen_ev_criterion_ids:
                    add_error("duplicate_evidence_criterion_id", f"{ev_loc}.criterion_id", "Duplicate evidence entry for criterion.")
                else:
                    seen_ev_criterion_ids.add(c_id)

                if not isinstance(e_stat, str) or e_stat not in ("passed", "failed", "blocked", "unexercised"):
                    add_error("invalid_evidence_status", f"{ev_loc}.status", "Evidence status must be passed|failed|blocked|unexercised.")
                elif stage == "complete" and e_stat != "passed":
                    add_error("unpassed_evidence_at_complete", f"{ev_loc}.status", f"Complete stage requires all evidence to be 'passed', got: {e_stat}")

                if not isinstance(e_sum, str) or not e_sum.strip():
                    add_error("invalid_evidence_summary", f"{ev_loc}.summary", "Evidence summary must be a non-blank string.")

                if not isinstance(e_ref, str) or not e_ref.strip():
                    add_error("invalid_path", f"{ev_loc}.reference", "Evidence reference must be a non-blank string.")
                else:
                    resolved_p, err = resolve_bounded_path(project_root, e_ref)
                    if err:
                        add_error("boundary_violation", f"{ev_loc}.reference", f"Evidence reference violates boundary: {err}")
                    elif resolved_p is None or not resolved_p.is_file():
                        add_error("file_not_found", f"{ev_loc}.reference", "Evidence file does not exist.")

    if stage == "complete":
        if not isinstance(ev_data, list) or len(ev_data) == 0:
            add_error("missing_complete_evidence", "evidence", "Stage 'complete' requires evidence array covering all acceptance criteria.")
        else:
            missing_acs = known_ac_ids - seen_ev_criterion_ids
            if missing_acs:
                add_error(
                    "incomplete_evidence_coverage",
                    "evidence",
                    f"Evidence does not cover all acceptance criteria; missing: {len(missing_acs)} criteria",
                )

    valid = not any(f["severity"] == "error" for f in findings)
    return {
        "schema_version": SCHEMA_VERSION,
        "check": "contract",
        "valid": valid,
        "findings": findings,
        "limitations": CONTRACT_LIMITATIONS,
    }


def output_result(result: dict[str, Any], fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(result, indent=2))
    else:
        status_str = "VALID" if result["valid"] else "INVALID"
        print(f"[{status_str}] Check: {result['check']} (schema_version: {result['schema_version']})")
        if "transition" in result:
            print(f"Transition: {result['transition']} (eligible: {result.get('eligible', result['valid'])})")
            print("\nFindings:")
            for f in result["findings"]:
                print(f"  [{f['severity'].upper()}] {f['code']} @ {f['path']}: {f['message']}")
        if result["limitations"]:
            print("\nLimitations:")
            for lim in result["limitations"]:
                print(f"  - {lim}")

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
        try:
            from scripts.doc_quality import validate_docs
        except ImportError:
            from doc_quality import validate_docs  # type: ignore[import-not-found]

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


if __name__ == "__main__":
    main()
