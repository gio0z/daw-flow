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
    "next_actions are advisory suggestions carrying $SKILL_DIR/$PROJECT_DIR placeholders; they never authorize execution or grant mutation rights.",
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
        if any(spec_path.glob("*.md")):
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


def _status_plans(root: pathlib.Path, spec_dir: str | None) -> str:
    """Report whether a saved plan satisfies the route gate's BPF-4 requirement.

    The route flow gate blocks feature/bugfix/refactor/maintain unless a
    `docs/plans/*.md` file contains the literal token `expected`; a status that
    answered `ok` for any plan file would send two different answers to the
    operator.
    """
    if not spec_dir:
        return "not_applicable"
    spec_path, err = resolve_bounded_path(root, spec_dir)
    if err or spec_path is None or not spec_path.is_dir():
        return "not_applicable"
    if not any(spec_path.glob("*.md")):
        return "not_applicable"
    plan_dir, plan_err = resolve_bounded_path(root, "docs/plans")
    if plan_err or plan_dir is None or not plan_dir.is_dir():
        return "missing"
    for matched in sorted(plan_dir.glob("*.md")):
        if not matched.is_file():
            continue
        try:
            text = matched.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "expected" in text:
            return "ok"
    return "missing"


def _status_tasks(root: pathlib.Path, findings: list[dict[str, str]]) -> tuple[dict[str, int], str | None]:
    counts = {"complete_valid": 0, "complete_invalid": 0, "in_progress": 0}
    first_failing: str | None = None
    evidence_dir = root / "docs" / "evidence"
    if not evidence_dir.is_dir():
        return counts, first_failing
    for contract_path in sorted(evidence_dir.glob("*/contract.json")):
        rel = contract_path.relative_to(root).as_posix()
        prefix = f"contract[{rel}]:"
        try:
            data = parse_strict_json(contract_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, *_JSON_PARSE_ERRORS):
            counts["complete_invalid"] += 1
            if first_failing is None:
                first_failing = rel
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
        if has_errors(res["findings"]):
            counts["complete_invalid"] += 1
            if first_failing is None:
                first_failing = rel
        else:
            counts["complete_valid"] += 1
    return counts, first_failing


def _recommended_route(config: str, ledger: str, plans: str, tasks: dict[str, int]) -> str:
    if config in ("missing", "invalid"):
        return "setup"
    if config == "stale":
        return "upgrade-recheck"
    if ledger in ("missing", "invalid"):
        return "design-rework"
    if plans == "missing":
        return "plan"
    if tasks["complete_invalid"]:
        return "verify"
    return "none"


def _area_blocking(findings: list[dict[str, str]], area: str) -> bool:
    """True when an error-severity finding names the area or one of its sub-paths.

    A bare area path ("config", "ledger") counts as part of the area, as do
    prefixed ("config:...", "ledger:...") and contract ("contract[...]:...") paths.
    """
    prefixes = (area, f"{area}:", f"{area}[")
    return any(
        f.get("severity") == "error" and str(f.get("path", "")).startswith(prefixes) for f in findings
    )


def _next_actions(
    config: str,
    ledger: str,
    plans: str,
    tasks: dict[str, int],
    spec_dir: str | None,
    first_failing: str | None,
    findings: list[dict[str, str]],
    root: pathlib.Path,
) -> list[dict[str, Any]]:
    route = _recommended_route(config, ledger, plans, tasks)
    if route == "setup":
        blocking = _area_blocking(findings, "config")
        return [
            {
                "action": "setup",
                "kind": "author",
                "command": None,
                "why": (
                    "No usable `<!-- daw-config:start -->` block in the agent file; "
                    "run the setup route to discover commands and author it."
                ),
                "blocking": blocking,
            },
            {
                "action": "setup-verify",
                "kind": "run",
                "command": (
                    'python3 "$SKILL_DIR/scripts/validate.py" config "AGENTS.md" '
                    '--project-root "$PROJECT_DIR"'
                ),
                "why": "Confirm the authored config block parses and its commands resolve.",
                "blocking": blocking,
            },
        ]
    if route == "upgrade-recheck":
        blocking = _area_blocking(findings, "config")
        return [
            {
                "action": "upgrade-recheck",
                "kind": "author",
                "command": None,
                "why": (
                    "The config block's `daw_version` is older than the installed VERSION; "
                    "review CHANGELOG.md and update `daw_version`."
                ),
                "blocking": blocking,
            },
            {
                "action": "upgrade-recheck-verify",
                "kind": "run",
                "command": 'python3 "$SKILL_DIR/scripts/validate.py" status --project-root "$PROJECT_DIR"',
                "why": "Re-run status; the config is current when summary.config is `ok`.",
                "blocking": blocking,
            },
        ]
    if route == "design-rework":
        blocking = _area_blocking(findings, "ledger")
        spec = spec_dir or "docs/specs"
        verify_entry = {
            "action": "design-rework-verify",
            "kind": "run",
            "command": (
                f'python3 "$SKILL_DIR/scripts/validate.py" ledger "{spec}/ledger.json" '
                '--project-root "$PROJECT_DIR"'
            ),
            "why": "After the ledger is written, run this to confirm it validates; before it exists the command exits 2.",
            "blocking": blocking,
        }
        records_source = any(
            (root / candidate).is_dir()
            for candidate in ("docs/decisions", "docs/specs/records", "docs/evidence")
        )
        if records_source:
            primary = {
                "action": "design-derive",
                "kind": "run",
                "command": 'python3 "$SKILL_DIR/scripts/derive_ledger.py" --project-root "$PROJECT_DIR" --write',
                "why": (
                    "Transition records already name these documents; derive "
                    f"{spec}/ledger.json from them instead of hand-writing it (the deriver "
                    "refuses to re-pin a hash that no record declares)."
                ),
                "blocking": blocking,
            }
        else:
            detail = (
                "spec dir has documents but no ledger.json"
                if ledger == "missing"
                else "ledger.json does not validate"
            )
            primary = {
                "action": "design-rework",
                "kind": "author",
                "command": None,
                "why": (
                    f"{detail}; re-enter the document workflow (review-rework -> rework-review -> "
                    f"review-ready) and persist state in {spec}/ledger.json."
                ),
                "blocking": blocking,
            }
        return [primary, verify_entry]
    if route == "plan":
        return [
            {
                "action": "plan",
                "kind": "author",
                "command": None,
                "why": (
                    "Specifications exist but no saved plan does; the route flow gate blocks "
                    "feature/bugfix/refactor/maintain until a plan with per-step expected "
                    "results is saved under docs/plans/."
                ),
                "blocking": True,
            },
            {
                "action": "plan-verify",
                "kind": "run",
                "command": (
                    'python3 "$SKILL_DIR/scripts/validate.py" status '
                    '--project-root "$PROJECT_DIR"'
                ),
                "why": "Re-run status; summary.plans becomes `ok` once the plan is saved.",
                "blocking": True,
            },
        ]
    if route == "verify":
        blocking = _area_blocking(findings, "contract")
        n = tasks["complete_invalid"]
        contract = first_failing or ""
        return [
            {
                "action": "verify",
                "kind": "author",
                "command": None,
                "why": (
                    f"{n} completed task contract(s) fail complete-stage validation; "
                    "re-verify each against the current revision before claiming completion."
                ),
                "blocking": blocking,
            },
            {
                "action": "verify-run",
                "kind": "run",
                "command": (
                    f'python3 "$SKILL_DIR/scripts/validate.py" contract "{contract}" '
                    '--stage complete --project-root "$PROJECT_DIR"'
                ),
                "why": "After the fix, run this to reproduce or clear the failing contract validation.",
                "blocking": blocking,
            },
        ]
    return [
        {
            "action": "none",
            "kind": "decide",
            "command": None,
            "why": (
                "No preflight blocker detected; continue the authorized route "
                "(or dispatch the classified route) and keep the plan/progress record current."
            ),
            "blocking": False,
        }
    ]


def validate_status(project_root: pathlib.Path, agent_file: str | None = None) -> dict[str, Any]:
    root = pathlib.Path(project_root).resolve()
    findings: list[dict[str, str]] = []
    config, spec_dir = _status_config(root, agent_file, findings)
    ledger = _status_ledger(root, spec_dir, findings)
    plans = _status_plans(root, spec_dir)
    tasks, first_failing = _status_tasks(root, findings)
    route = _recommended_route(config, ledger, plans, tasks)
    return {
        "valid": not has_errors(findings),
        "check": "status",
        "schema_version": SCHEMA_VERSION,
        "summary": {"config": config, "ledger": ledger, "plans": plans, "tasks": tasks},
        "recommended_route": route,
        "next_actions": _next_actions(config, ledger, plans, tasks, spec_dir, first_failing, findings, root),
        "findings": findings,
        "limitations": STATUS_LIMITATIONS,
    }
