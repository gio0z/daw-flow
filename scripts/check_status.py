"""Project status preflight (`validate.py status`).

Composes the config, ledger, and complete-stage contract checks into one read-only summary
with a recommended next route. Owns no validation rules of its own.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

try:
    from scripts.daw_common import (
        SCHEMA_VERSION,
        DuplicateKeyError,
        has_errors,
        make_error,
        make_warning,
        parse_strict_json,
        resolve_bounded_path,
    )
except ImportError:
    from daw_common import (  # type: ignore[import-not-found]
        SCHEMA_VERSION,
        DuplicateKeyError,
        has_errors,
        make_error,
        make_warning,
        parse_strict_json,
        resolve_bounded_path,
    )

try:
    from scripts.check_config import parse_config_block, validate_config_text
    from scripts.check_contract import validate_contract
    from scripts.check_ledger import validate_ledger
except ImportError:
    from check_config import parse_config_block, validate_config_text  # type: ignore[import-not-found]
    from check_contract import validate_contract  # type: ignore[import-not-found]
    from check_ledger import validate_ledger  # type: ignore[import-not-found]

STATUS_LIMITATIONS = [
    "Read-only aggregate: never runs tests, evidence commands, or builds, and never writes files.",
    "Task discovery is limited to the convention path docs/evidence/<task-id>/contract.json; contracts stored elsewhere are not checked.",
    "Inherits every composed check's limitations (config, ledger, docs, contract); semantic truth of evidence is never evaluated.",
]

_AGENT_FILES = ("AGENTS.md", "CLAUDE.md")
_JSON_PARSE_ERRORS = (json.JSONDecodeError, DuplicateKeyError, RecursionError, ValueError)


def _prefixed(findings: list[dict[str, str]], prefix: str) -> list[dict[str, str]]:
    return [{**f, "path": f"{prefix}{f['path']}"} for f in findings]


def _locate_agent_file(root: pathlib.Path, agent_file: str | None) -> pathlib.Path | None:
    candidates = (agent_file,) if agent_file else _AGENT_FILES
    for name in candidates:
        resolved, err = resolve_bounded_path(root, name)
        if err is None and resolved is not None and resolved.is_file():
            return resolved
    return None


def _status_config(
    root: pathlib.Path, agent_file: str | None, findings: list[dict[str, str]]
) -> tuple[str, str | None]:
    """Return (summary value, spec_dir or None)."""
    path = _locate_agent_file(root, agent_file)
    if path is None:
        findings.append(make_error("status_config_missing", "config", "No agent file with a DAW configuration block was found."))
        return "missing", None
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        findings.append(make_error("status_config_missing", "config", "Agent file cannot be read as UTF-8."))
        return "missing", None
    res = validate_config_text(text, root, path.name)
    codes = {f["code"] for f in res["findings"]}
    findings.extend(_prefixed(res["findings"], "config:"))
    spec_dir = parse_config_block(text).get("spec_dir")
    if "config_block_missing" in codes:
        return "missing", None
    if has_errors(res["findings"]):
        return "invalid", spec_dir
    if "config_daw_version_stale" in codes:
        return "stale", spec_dir
    return "ok", spec_dir


def _status_ledger(root: pathlib.Path, spec_dir: str | None, findings: list[dict[str, str]]) -> str:
    if not spec_dir:
        return "not_applicable"
    spec_path, err = resolve_bounded_path(root, spec_dir)
    if err or spec_path is None or not spec_path.is_dir():
        return "not_applicable"
    ledger_path = spec_path / "ledger.json"
    if not ledger_path.is_file():
        if any(p.name != "ledger.json" for p in spec_path.glob("*.md")):
            findings.append(
                make_warning(
                    "status_ledger_missing",
                    "ledger",
                    "Spec directory contains documents but no ledger.json; spec workflow state is not persisted.",
                )
            )
            return "missing"
        return "not_applicable"
    try:
        ledger_data = parse_strict_json(ledger_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, *_JSON_PARSE_ERRORS):
        findings.append(make_error("ledger_malformed", "ledger:$", "Ledger cannot be read as strict JSON."))
        return "invalid"
    res = validate_ledger(ledger_data, root)
    findings.extend(_prefixed(res["findings"], "ledger:"))
    return "invalid" if has_errors(res["findings"]) else "ok"


def _status_tasks(root: pathlib.Path, findings: list[dict[str, str]]) -> dict[str, int]:
    counts = {"complete_valid": 0, "complete_invalid": 0, "in_progress": 0}
    evidence_dir = root / "docs" / "evidence"
    if not evidence_dir.is_dir():
        return counts
    for contract_path in sorted(evidence_dir.glob("*/contract.json")):
        rel = contract_path.relative_to(root).as_posix()
        prefix = f"contract[{rel}]:"
        try:
            data = parse_strict_json(contract_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, *_JSON_PARSE_ERRORS):
            counts["complete_invalid"] += 1
            findings.append(make_error("contract_malformed", f"{prefix}$", "Task contract cannot be read as strict JSON."))
            continue
        if not isinstance(data, dict) or "result" not in data:
            counts["in_progress"] += 1
            findings.append(
                make_warning("status_task_in_progress", rel, "Task contract has no result snapshot; it is not claimed complete.")
            )
            continue
        res = validate_contract(data, root, "complete")
        findings.extend(_prefixed(res["findings"], prefix))
        counts["complete_invalid" if has_errors(res["findings"]) else "complete_valid"] += 1
    return counts


def _recommended_route(config: str, ledger: str, tasks: dict[str, int]) -> str:
    if config in ("missing", "invalid"):
        return "setup"
    if config == "stale":
        return "upgrade-recheck"
    if ledger in ("missing", "invalid"):
        return "design-rework"
    if tasks["complete_invalid"]:
        return "verify"
    return "none"


def validate_status(project_root: pathlib.Path, agent_file: str | None = None) -> dict[str, Any]:
    root = pathlib.Path(project_root).resolve()
    findings: list[dict[str, str]] = []
    config, spec_dir = _status_config(root, agent_file, findings)
    ledger = _status_ledger(root, spec_dir, findings)
    tasks = _status_tasks(root, findings)
    return {
        "valid": not has_errors(findings),
        "check": "status",
        "schema_version": SCHEMA_VERSION,
        "summary": {"config": config, "ledger": ledger, "tasks": tasks},
        "recommended_route": _recommended_route(config, ledger, tasks),
        "findings": findings,
        "limitations": STATUS_LIMITATIONS,
    }
