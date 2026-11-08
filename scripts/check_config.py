"""daw-config block validation (`validate.py config`), including `daw_version` comparison."""

from __future__ import annotations

import pathlib
import re
import shutil
from typing import Any

try:
    from scripts.daw_common import (
        SCHEMA_VERSION,
        make_error as _error,
        make_warning as _warning,
        resolve_bounded_path,
    )
except ImportError:
    from daw_common import (  # type: ignore[import-not-found]
        SCHEMA_VERSION,
        make_error as _error,
        make_warning as _warning,
        resolve_bounded_path,
    )

CONFIG_LIMITATIONS = [
    "Structural verification only; config values are validated syntactically and for filesystem/lookup resolvability only.",
    "Validator never executes test/lint/build commands; command resolution uses shutil.which lookup only.",
    "Validator is read-only and does not persist state or modify agent files.",
]

CONFIG_KEYS = (
    "schema",
    "daw_version",
    "spec_dir",
    "test_command",
    "lint_command",
    "build_command",
    "workspace",
    "high_risk_paths",
    "issue_tracker",
    "default_branch",
    "commit_convention",
    "pr_template",
    "ci_checks",
    "release_process",
    "branch_pattern",
)

WORKSPACES = ("in-place", "isolated")
_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
_PACKAGE_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _installed_suite_version() -> str | None:
    """Read the installed suite VERSION from this validator's own package root."""
    try:
        text = (_PACKAGE_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return None
    return text if _SEMVER_RE.match(text) else None


def _check_daw_version(value: str, findings: list[dict[str, str]]) -> None:
    m = _SEMVER_RE.match(value)
    if not m:
        findings.append(_error("config_line_invalid", "daw_version", "daw_version must be X.Y.Z."))
        return
    installed = _installed_suite_version()
    if installed is None:
        findings.append(
            _warning("config_daw_version_unverified", "daw_version", "Installed suite VERSION could not be read.")
        )
        return
    project_v = tuple(int(p) for p in m.groups())
    installed_v = tuple(int(p) for p in _SEMVER_RE.match(installed).groups())  # type: ignore[union-attr]
    if project_v < installed_v:
        findings.append(
            _warning(
                "config_daw_version_stale",
                "daw_version",
                f"Project last passed DAW {value}; installed suite is {installed}. Run daw-setup Upgrade Re-check.",
            )
        )
    elif project_v > installed_v:
        findings.append(
            _error(
                "config_daw_version_ahead",
                "daw_version",
                f"Project records DAW {value}, newer than installed suite {installed}. Update the installed suite.",
            )
        )


def _build_result(
    check: str,
    findings: list[dict[str, str]],
    limitations: list[str],
) -> dict[str, Any]:
    valid = not any(f["severity"] == "error" for f in findings)
    return {
        "valid": valid,
        "check": check,
        "schema_version": SCHEMA_VERSION,
        "findings": findings,
        "limitations": limitations,
    }


_CONFIG_LINE_RE = re.compile(r"^-\s+([A-Za-z0-9_-]+):\s*(.*)$")
_ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def _command_first_token(command: str) -> str | None:
    text = command.strip()
    if not text:
        return None
    # Strip leading VAR=val assignments.
    tokens = text.split()
    i = 0
    while i < len(tokens) and _ENV_ASSIGN_RE.match(tokens[i]):
        i += 1
    if i >= len(tokens):
        return None
    return tokens[i]


def parse_config_block(text: str) -> dict[str, str]:
    """Return the first-seen `- key: value` pairs of a single daw-config block; {} when absent or ambiguous."""
    lines = text.splitlines()
    starts = [i for i, ln in enumerate(lines) if ln.strip() == "<!-- daw-config:start -->"]
    ends = [i for i, ln in enumerate(lines) if ln.strip() == "<!-- daw-config:end -->"]
    if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0]:
        return {}
    config: dict[str, str] = {}
    for raw_line in lines[starts[0] + 1 : ends[0]]:
        m = _CONFIG_LINE_RE.match(raw_line.rstrip())
        if m and m.group(1) not in config:
            config[m.group(1)] = m.group(2).strip()
    return config


def validate_config_text(
    text: str,
    project_root: pathlib.Path,
    agent_label: str = "agent file",
) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    try:
        root = pathlib.Path(project_root).resolve()
    except (OSError, RuntimeError, ValueError):
        findings.append(_error("project_root_error", "$", "Cannot resolve project root."))
        return _build_result("config", findings, CONFIG_LIMITATIONS)
    if not root.is_dir():
        findings.append(_error("project_root_not_dir", str(project_root), "Project root is not a valid directory."))
        return _build_result("config", findings, CONFIG_LIMITATIONS)

    lines = text.splitlines()
    starts = [i for i, ln in enumerate(lines) if ln.strip() == "<!-- daw-config:start -->"]
    ends = [i for i, ln in enumerate(lines) if ln.strip() == "<!-- daw-config:end -->"]
    if len(starts) == 0 or len(ends) == 0:
        findings.append(_error("config_block_missing", agent_label, "DAW configuration block markers are missing."))
        return _build_result("config", findings, CONFIG_LIMITATIONS)
    if len(starts) > 1 or len(ends) > 1:
        findings.append(_error("config_block_duplicate", agent_label, "Multiple DAW configuration blocks detected."))
        return _build_result("config", findings, CONFIG_LIMITATIONS)
    start_idx, end_idx = starts[0], ends[0]
    if end_idx < start_idx:
        findings.append(_error("config_block_missing", agent_label, "DAW configuration end marker precedes start marker."))
        return _build_result("config", findings, CONFIG_LIMITATIONS)

    block = lines[start_idx + 1 : end_idx]
    # After the `## DAW Configuration` heading, every non-blank line must be `- key: value`.
    heading_idx: int | None = None
    for j, ln in enumerate(block):
        if ln.strip() == "## DAW Configuration":
            heading_idx = j
            break
    if heading_idx is None:
        findings.append(_error("config_heading_missing", agent_label, "DAW Configuration heading is missing."))
        body_offset = start_idx + 1
        body = block
    else:
        body_offset = start_idx + 2 + heading_idx
        body = block[heading_idx + 1 :]

    config: dict[str, str] = {}
    seen: dict[str, int] = {}
    for body_idx, raw_line in enumerate(body):
        line = raw_line.rstrip()
        if not line.strip():
            continue
        m = _CONFIG_LINE_RE.match(line)
        if not m:
            line_no = body_offset + body_idx + 1
            findings.append(_error("config_line_invalid", f"line {line_no}", "Line must be '- key: value'."))
            continue
        key, value = m.group(1), m.group(2).strip()
        if key in seen:
            findings.append(_error("config_key_duplicate", key, f"Duplicate config key: {key}"))
            continue
        seen[key] = 1
        config[key] = value

    for key in CONFIG_KEYS:
        if key not in config:
            findings.append(_error("config_key_missing", key, f"Missing required config key: {key}"))

    for key in config:
        if key not in CONFIG_KEYS:
            findings.append(_error("config_line_invalid", key, f"Unknown config key: {key}"))

    if "schema" in config and config["schema"] != "1":
        findings.append(_error("config_line_invalid", "schema", "schema must be 1."))
    if "workspace" in config and config["workspace"] not in WORKSPACES:
        findings.append(_error("config_line_invalid", "workspace", "workspace must be one of in-place|isolated."))
    if "daw_version" in config:
        _check_daw_version(config["daw_version"], findings)

    if "spec_dir" in config:
        spec_dir = config["spec_dir"]
        resolved, err = resolve_bounded_path(root, spec_dir)
        if err or resolved is None or not resolved.is_dir():
            findings.append(_error("config_path_missing", "spec_dir", "spec_dir must exist as a directory under project root."))
    if "pr_template" in config and config["pr_template"] != "none":
        resolved, err = resolve_bounded_path(root, config["pr_template"])
        if err or resolved is None or not resolved.is_file():
            findings.append(_error("config_path_missing", "pr_template", "pr_template must exist under project root."))
    if "high_risk_paths" in config:
        value = config["high_risk_paths"]
        if value != "none":
            for entry in [e.strip() for e in value.split(",") if e.strip()]:
                if entry == "none":
                    continue
                resolved, err = resolve_bounded_path(root, entry)
                if err or resolved is None or not resolved.exists():
                    findings.append(_error("config_path_missing", "high_risk_paths", f"high_risk_paths entry does not exist: {entry}"))

    for cmd_key in ("test_command", "lint_command", "build_command"):
        if cmd_key not in config:
            continue
        value = config[cmd_key]
        if value == "none":
            continue
        first = _command_first_token(value)
        if first is None:
            findings.append(_error("config_command_unresolved", cmd_key, f"{cmd_key} has no command token."))
            continue
        # Existing project-relative file check (bounded, read-only).
        if "/" in first and not first.startswith(("/", "\\")):
            resolved, err = resolve_bounded_path(root, first)
            if err is None and resolved is not None and resolved.exists():
                continue
            elif err is None and resolved is not None and not resolved.exists():
                # File path given but missing: check PATH as fallback before failing.
                pass
            else:
                pass
        if shutil.which(first) is not None:
            continue
        findings.append(_error("config_command_unresolved", cmd_key, f"{cmd_key} command is not resolvable: {first}"))

    return _build_result("config", findings, CONFIG_LIMITATIONS)


def validate_config_file(
    agent_path: pathlib.Path,
    project_root: pathlib.Path,
) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    try:
        root = pathlib.Path(project_root).resolve()
    except (OSError, RuntimeError, ValueError):
        findings.append(_error("project_root_error", "$", "Cannot resolve project root."))
        return _build_result("config", findings, CONFIG_LIMITATIONS)
    if not root.is_dir():
        findings.append(_error("project_root_not_dir", str(project_root), "Project root is not a valid directory."))
        return _build_result("config", findings, CONFIG_LIMITATIONS)

    # Resolve agent file bound to project root where possible; absolute paths OK.
    if agent_path.is_absolute():
        try:
            resolved = agent_path.resolve()
            resolved.relative_to(root)
        except (ValueError, OSError, RuntimeError):
            findings.append(_error("config_file_outside_root", str(agent_path), "Agent file is outside project root."))
            return _build_result("config", findings, CONFIG_LIMITATIONS)
    else:
        resolved_bound, err = resolve_bounded_path(root, str(agent_path))
        if err or resolved_bound is None:
            findings.append(_error("config_file_outside_root", str(agent_path), "Agent file escapes project root."))
            return _build_result("config", findings, CONFIG_LIMITATIONS)
        resolved = resolved_bound

    if not resolved.is_file():
        findings.append(_error("config_file_missing", str(agent_path), "Agent file does not exist or is not a file."))
        return _build_result("config", findings, CONFIG_LIMITATIONS)
    try:
        text = resolved.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError, RuntimeError):
        findings.append(_error("config_file_unreadable", str(agent_path), "Agent file cannot be read as UTF-8."))
        return _build_result("config", findings, CONFIG_LIMITATIONS)
    return validate_config_text(text, root, str(agent_path))
