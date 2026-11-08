"""Shared read-only primitives for Deterministic Agentic Workflow validators.

Strict JSON parsing, bounded path resolution, hashing, frontmatter/link parsing,
durable-evidence path policy, finding constructors, and result output.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
from typing import Any

SCHEMA_VERSION = 1

CANONICAL_TEMPLATES = (
    "blueprint.md",
    "brd.md",
    "deployment.md",
    "design.md",
    "erd.md",
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


_NON_DURABLE_FIRST_SEGMENTS = frozenset({"tmp", "temp", ".tmp", "scratch", ".cache"})


def is_durable_evidence_path(path: str) -> bool:
    """Return True when ``path`` is not under a known ephemeral segment.

    Deterministic segment denylist only: rejects first-segment ephemeral
    names, any ``__pycache__`` segment, and any dot-prefixed segment
    except ``.github``. Cannot detect gitignored paths.
    """
    if not isinstance(path, str) or not path.strip():
        return False
    segments = [seg for seg in path.replace("\\", "/").split("/") if seg not in ("", ".")]
    if not segments:
        return False
    if segments[0] in _NON_DURABLE_FIRST_SEGMENTS:
        return False
    for seg in segments:
        if seg == "__pycache__":
            return False
        if seg.startswith(".") and seg != ".github":
            return False
    return True


def make_error(code: str, path: str, message: str) -> dict[str, str]:
    return {"severity": "error", "code": code, "path": path, "message": message}


def make_warning(code: str, path: str, message: str) -> dict[str, str]:
    return {"severity": "warning", "code": code, "path": path, "message": message}


def has_errors(findings: list[dict[str, str]]) -> bool:
    return any(f.get("severity") == "error" for f in findings)


def output_result(result: dict[str, Any], fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(result, indent=2))
    else:
        status_str = "VALID" if result["valid"] else "INVALID"
        print(f"[{status_str}] Check: {result['check']} (schema_version: {result['schema_version']})")
        if "transition" in result:
            print(f"Transition: {result['transition']} (eligible: {result.get('eligible', result['valid'])})")
        if "summary" in result:
            print(f"Summary: {json.dumps(result['summary'], sort_keys=False)}")
        if "recommended_route" in result:
            print(f"Recommended route: {result['recommended_route']}")
        if result["findings"]:
            print("\nFindings:")
            for f in result["findings"]:
                print(f"  [{f['severity'].upper()}] {f['code']} @ {f['path']}: {f['message']}")
        if result["limitations"]:
            print("\nLimitations:")
            for lim in result["limitations"]:
                print(f"  - {lim}")
