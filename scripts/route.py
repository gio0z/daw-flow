#!/usr/bin/env python3
"""Deterministic Agentic Workflow Request Router.

A read-only, zero-dependency Python 3.10+ command-line utility for resolving
procedural pipeline routes according to references/suite-manifest.json.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from typing import Any, Tuple

# Bundled helper imports must not modify the installed suite.
sys.dont_write_bytecode = True
import validate

SCHEMA_VERSION = 1
MAX_INPUT_BYTES = 1024 * 1024  # 1 MiB bounded input limit
MAX_MODULE_BYTES = 256 * 1024  # 256 KiB bounded module read limit

VALID_ENUMS: dict[str, frozenset[str]] = {
    "intent": frozenset({"bootstrap", "adopt", "feature", "bugfix", "patch", "review", "ask", "setup"}),
    "requirements": frozenset({"clear", "unclear", "unknown"}),
    "risk": frozenset({"low", "high", "unknown"}),
    "workspace": frozenset({"in-place", "isolated", "unknown"}),
}

REQUIRED_REQUEST_KEYS = frozenset({"schema_version", "intent", "requirements", "risk", "workspace"})

MANIFEST_MODULE_KEYS = frozenset({
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

# Invariant stage definitions per intent (v1 fixed canonical policy)
CANONICAL_ROUTE_STAGES: dict[str, Any] = {
    "bootstrap": ["daw-wizard", "daw-design", "daw-plan"],
    "adopt": ["daw-design", "daw-plan"],
    "feature": {
        "stages_clear": ["daw-plan", "daw-build", "daw-review", "daw-verify"],
        "stages_unclear": ["daw-design", "daw-plan", "daw-build", "daw-review", "daw-verify"],
    },
    "bugfix": ["daw-debug", "daw-plan", "daw-build", "daw-review", "daw-verify"],
    "patch": ["daw-build", "daw-verify"],
    "review": ["daw-review"],
    "ask": ["daw-ask"],
    "setup": ["daw-setup"],
}


def _reject_constant(_: str) -> None:
    raise ValueError("Non-standard JSON constant rejected.")


def parse_strict_json(raw_text: str) -> Tuple[Any, str | None]:
    """Parse JSON strictly: reject duplicate keys, NaN, Infinity, and non-finite values."""
    if not isinstance(raw_text, str):
        return None, "Input must be a string."

    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        obj: dict[str, Any] = {}
        seen_keys: set[str] = set()
        for k, v in pairs:
            if k in seen_keys:
                raise ValueError("Duplicate key encountered in JSON object.")
            seen_keys.add(k)
            obj[k] = v
        return obj

    try:
        data = json.loads(
            raw_text,
            object_pairs_hook=pairs_hook,
            parse_constant=_reject_constant,
        )
        return data, None
    except json.JSONDecodeError:
        return None, "JSON syntax error."
    except ValueError as exc:
        msg = str(exc)
        if "Duplicate key" in msg:
            return None, "Duplicate key encountered in JSON object."
        if "Non-standard JSON constant" in msg:
            return None, "Non-standard JSON numeric constant rejected."
        return None, "JSON value error."
    except RecursionError:
        return None, "JSON exceeds maximum nesting depth."


def create_response(
    status: str,
    stages: list[str] | None = None,
    reasons: list[str] | None = None,
    blockers: list[dict[str, str]] | None = None,
    read_only: bool = False,
    documentation_only: bool = False,
    interactive_approval_required: bool = False,
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    """Create a standard output envelope with fixed constraints."""
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "stages": stages or [],
        "reasons": reasons or [],
        "blockers": blockers or [],
        "constraints": {
            "read_only": read_only,
            "documentation_only": documentation_only,
            "interactive_approval_required": interactive_approval_required,
            "authorization_granted": False,  # Invariant: Always false
        },
        "limitations": limitations or [
            "Routing resolution is deterministic based on declared manifest policy.",
            "Resolution does not grant runtime authorization for high-risk operations.",
        ],
    }


def find_suite_root(explicit_root: pathlib.Path | str | None = None) -> pathlib.Path:
    """Resolve the suite root directory."""
    if explicit_root:
        return pathlib.Path(explicit_root).resolve()
    return pathlib.Path(__file__).resolve().parent.parent


def validate_module_file(root: pathlib.Path, expected_name: str, rel_path: Any) -> list[dict[str, str]]:
    """Verify that a module file exists within root, is canonical, and has matching frontmatter name."""
    expected_rel = f"skills/{expected_name}/SKILL.md"
    if not isinstance(rel_path, str) or rel_path != expected_rel:
        return [{
            "code": "MODULE_NON_CANONICAL_PATH",
            "message": f"Module {expected_name} path must match canonical pattern 'skills/{expected_name}/SKILL.md'",
        }]

    resolved, err = validate.resolve_bounded_path(root, rel_path)
    if err or resolved is None:
        return [{
            "code": "MODULE_ROOT_ESCAPE",
            "message": f"Module {expected_name} path escapes suite root or traverses boundaries.",
        }]

    if not resolved.is_file():
        return [{
            "code": "MODULE_NOT_FOUND",
            "message": f"Module {expected_name} file does not exist at expected canonical path.",
        }]

    try:
        st = resolved.stat()
        if st.st_size > MAX_MODULE_BYTES:
            return [{
                "code": "MODULE_SIZE_EXCEEDED",
                "message": f"Module {expected_name} file size exceeds maximum limit ({MAX_MODULE_BYTES} bytes).",
            }]
        content = resolved.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return [{
            "code": "MODULE_READ_ERROR",
            "message": f"Error reading module {expected_name} file.",
        }]

    frontmatter, fm_errors = validate.parse_frontmatter(content)
    if fm_errors or frontmatter is None:
        return [{
            "code": "MODULE_FRONTMATTER_INVALID",
            "message": f"Module {expected_name} frontmatter is missing or invalid.",
        }]

    if frontmatter.get("name") != expected_name:
        return [{
            "code": "MODULE_NAME_MISMATCH",
            "message": f"Module frontmatter name does not match expected module name '{expected_name}'.",
        }]

    return []


def _validate_module_entries(modules: Any) -> list[dict[str, str]]:
    """Validate manifest modules object and all 10 entries."""
    findings: list[dict[str, str]] = []
    if not isinstance(modules, dict):
        return [{"code": "MANIFEST_INVALID_MODULES", "message": "Manifest modules must be a JSON object."}]

    mod_keys = set(modules.keys())
    missing_modules = MANIFEST_MODULE_KEYS - mod_keys
    extra_modules = mod_keys - MANIFEST_MODULE_KEYS
    if missing_modules:
        findings.append({
            "code": "MANIFEST_MISSING_MODULES",
            "message": f"Manifest is missing required module(s): count={len(missing_modules)}.",
        })
    if extra_modules:
        findings.append({
            "code": "MANIFEST_EXTRA_MODULES",
            "message": f"Manifest contains {len(extra_modules)} unexpected module(s). Raw module names redacted.",
        })

    for mod_name in sorted(MANIFEST_MODULE_KEYS):
        if mod_name not in modules:
            continue
        mod_info = modules[mod_name]
        if not isinstance(mod_info, dict):
            findings.append({"code": "MANIFEST_MODULE_NOT_OBJECT", "message": f"Module entry '{mod_name}' must be an object."})
            continue
        if set(mod_info.keys()) != {"path", "description"}:
            findings.append({"code": "MANIFEST_MODULE_UNKNOWN_KEYS", "message": f"Module entry '{mod_name}' has invalid keys."})
        if not isinstance(mod_info.get("path"), str):
            findings.append({"code": "MANIFEST_MODULE_PATH_INVALID", "message": f"Module '{mod_name}' path must be string."})
        if not isinstance(mod_info.get("description"), str):
            findings.append({"code": "MANIFEST_MODULE_DESCRIPTION_INVALID", "message": f"Module '{mod_name}' description must be string."})

    return findings


def _validate_route_entries(routes: Any) -> list[dict[str, str]]:
    """Validate manifest routes against fixed v1 canonical invariants."""
    findings: list[dict[str, str]] = []
    valid_intents = VALID_ENUMS["intent"]
    if not isinstance(routes, dict):
        return [{"code": "MANIFEST_INVALID_ROUTES", "message": "Manifest routes must be a JSON object."}]

    route_keys = set(routes.keys())
    missing_routes = valid_intents - route_keys
    extra_routes = route_keys - valid_intents
    if missing_routes:
        findings.append({
            "code": "MANIFEST_MISSING_ROUTES",
            "message": f"Manifest routes missing required intent(s): count={len(missing_routes)}.",
        })
    if extra_routes:
        findings.append({
            "code": "MANIFEST_EXTRA_ROUTES",
            "message": f"Manifest routes contains {len(extra_routes)} unexpected intent(s). Raw intent names redacted.",
        })

    for r_name in sorted(valid_intents):
        if r_name not in routes:
            continue
        r_def = routes[r_name]
        if not isinstance(r_def, dict):
            findings.append({"code": "MANIFEST_ROUTE_NOT_OBJECT", "message": f"Route '{r_name}' definition must be an object."})
            continue

        # Invariant checks for flags
        expected_doc = (r_name in ("bootstrap", "adopt", "setup"))
        expected_ro = (r_name in ("review", "ask"))
        expected_ws = (r_name in ("feature", "bugfix", "patch"))

        if r_def.get("documentation_only") is not expected_doc:
            findings.append({"code": "MANIFEST_ROUTE_INVARIANT_VIOLATION", "message": f"Route '{r_name}' documentation_only must be {expected_doc}."})
        if r_def.get("read_only") is not expected_ro:
            findings.append({"code": "MANIFEST_ROUTE_INVARIANT_VIOLATION", "message": f"Route '{r_name}' read_only must be {expected_ro}."})
        if r_def.get("evaluates_workspace") is not expected_ws:
            findings.append({"code": "MANIFEST_ROUTE_INVARIANT_VIOLATION", "message": f"Route '{r_name}' evaluates_workspace must be {expected_ws}."})

        # Stages invariants
        expected_stage_spec = CANONICAL_ROUTE_STAGES[r_name]
        if r_name == "feature":
            if r_def.get("stages_clear") != expected_stage_spec["stages_clear"] or r_def.get("stages_unclear") != expected_stage_spec["stages_unclear"]:
                findings.append({"code": "MANIFEST_ROUTE_INVARIANT_VIOLATION", "message": "Route 'feature' stages do not match canonical specification."})
            if set(r_def.keys()) != {"documentation_only", "read_only", "stages_clear", "stages_unclear", "evaluates_workspace"}:
                findings.append({"code": "MANIFEST_ROUTE_SHAPE_INVALID", "message": "Route 'feature' contains unexpected or missing keys."})
        else:
            if r_def.get("stages") != expected_stage_spec:
                findings.append({"code": "MANIFEST_ROUTE_INVARIANT_VIOLATION", "message": f"Route '{r_name}' stages must match canonical {expected_stage_spec}."})
            expected_keys = {"documentation_only", "read_only", "stages", "evaluates_workspace"}
            if r_name in ("bootstrap", "adopt", "setup"):
                expected_keys.add("allow_unclear_requirements")
                if r_def.get("allow_unclear_requirements") is not True:
                    findings.append({"code": "MANIFEST_ROUTE_INVARIANT_VIOLATION", "message": f"Route '{r_name}' allow_unclear_requirements must be True."})
            if set(r_def.keys()) != expected_keys:
                findings.append({"code": "MANIFEST_ROUTE_SHAPE_INVALID", "message": f"Route '{r_name}' contains unexpected or missing keys."})

    return findings


def load_manifest(root: pathlib.Path) -> Tuple[dict[str, Any] | None, list[dict[str, str]]]:
    """Load and strictly validate references/suite-manifest.json."""
    manifest_rel = "references/suite-manifest.json"
    manifest_path, err = validate.resolve_bounded_path(root, manifest_rel)
    if err or manifest_path is None:
        return None, [{"code": "MANIFEST_ESCAPE", "message": "Suite manifest path escapes root or contains unsafe traversal."}]

    if not manifest_path.is_file():
        return None, [{"code": "MANIFEST_NOT_FOUND", "message": "Suite manifest not found at expected path references/suite-manifest.json."}]

    try:
        st = manifest_path.stat()
        if st.st_size > MAX_INPUT_BYTES:
            return None, [{"code": "MANIFEST_SIZE_EXCEEDED", "message": f"Manifest file exceeds maximum allowed size ({MAX_INPUT_BYTES} bytes)."}]
        content = manifest_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None, [{"code": "MANIFEST_READ_ERROR", "message": "Failed reading suite manifest file."}]

    data, parse_err = parse_strict_json(content)
    if parse_err:
        return None, [{"code": "MANIFEST_PARSE_ERROR", "message": f"Failed parsing suite manifest JSON: {parse_err}"}]

    if not isinstance(data, dict):
        return None, [{"code": "MANIFEST_MALFORMED", "message": "Manifest root must be a JSON object."}]

    findings: list[dict[str, str]] = []
    allowed_keys = {"schema_version", "suite", "modules", "routes"}
    unknown_keys = set(data.keys()) - allowed_keys
    if unknown_keys:
        findings.append({"code": "MANIFEST_UNKNOWN_KEYS", "message": f"Manifest contains {len(unknown_keys)} unknown key(s). Raw keys redacted."})

    schema_ver = data.get("schema_version")
    if isinstance(schema_ver, bool) or not isinstance(schema_ver, int) or schema_ver != SCHEMA_VERSION:
        findings.append({"code": "MANIFEST_INVALID_SCHEMA_VERSION", "message": f"Manifest schema_version must be integer {SCHEMA_VERSION}."})

    if data.get("suite") != "deterministic-agentic-workflow":
        findings.append({"code": "MANIFEST_INVALID_SUITE_NAME", "message": "Manifest suite field must be 'deterministic-agentic-workflow'."})

    findings.extend(_validate_module_entries(data.get("modules")))
    findings.extend(_validate_route_entries(data.get("routes")))

    return data, findings


def check_suite_modules(root: pathlib.Path, manifest: dict[str, Any]) -> list[dict[str, str]]:
    """Verify that all 10 canonical modules exist on disk within root."""
    findings: list[dict[str, str]] = []
    modules = manifest.get("modules", {})
    for mod_name in sorted(MANIFEST_MODULE_KEYS):
        mod_info = modules.get(mod_name)
        if not isinstance(mod_info, dict):
            findings.append({"code": "MODULE_CONFIG_MISSING", "message": f"Module {mod_name} configuration missing in manifest."})
            continue
        findings.extend(validate_module_file(root, mod_name, mod_info.get("path")))
    return findings


def check_suite(root: pathlib.Path | str | None = None) -> list[dict[str, str]]:
    """Validate suite manifest and verify all 10 canonical modules on disk within root."""
    resolved_root = find_suite_root(root)
    manifest, findings = load_manifest(resolved_root)
    if findings:
        return findings

    assert manifest is not None
    findings.extend(check_suite_modules(resolved_root, manifest))
    return findings


def validate_request(req_data: Any) -> Tuple[dict[str, Any] | None, list[dict[str, str]]]:
    """Validate input request object with strict type and key constraints, redacting unknown values."""
    if not isinstance(req_data, dict):
        return None, [{"code": "REQUEST_NOT_OBJECT", "message": "Request must be a JSON object."}]

    req_keys = set(req_data.keys())
    missing_keys = REQUIRED_REQUEST_KEYS - req_keys
    unexpected_keys = req_keys - REQUIRED_REQUEST_KEYS
    blockers: list[dict[str, str]] = []

    if missing_keys:
        blockers.append({"code": "REQUEST_MISSING_KEYS", "message": f"Request missing {len(missing_keys)} required key(s)."})
    if unexpected_keys:
        blockers.append({"code": "REQUEST_UNKNOWN_KEYS", "message": f"Request contains {len(unexpected_keys)} unexpected key(s). Raw keys redacted."})

    if blockers:
        return None, blockers

    schema_ver = req_data.get("schema_version")
    if isinstance(schema_ver, bool) or not isinstance(schema_ver, int) or schema_ver != SCHEMA_VERSION:
        blockers.append({"code": "REQUEST_INVALID_SCHEMA_VERSION", "message": f"schema_version must be integer {SCHEMA_VERSION}."})

    for field, valid_set in VALID_ENUMS.items():
        val = req_data.get(field)
        if not isinstance(val, str) or val not in valid_set:
            blockers.append({"code": f"REQUEST_INVALID_{field.upper()}", "message": f"{field} must be a valid scalar enum."})

    if blockers:
        return None, blockers

    return req_data, []


def resolve_route(
    request_data: Any,
    root: pathlib.Path | str | None = None,
) -> dict[str, Any]:
    """Resolve procedural route from request and manifest."""
    valid_req, req_blockers = validate_request(request_data)
    if req_blockers:
        return create_response(status="error", blockers=req_blockers, reasons=["Request validation failed."])

    assert valid_req is not None
    intent = valid_req["intent"]
    requirements = valid_req["requirements"]
    risk = valid_req["risk"]
    workspace = valid_req["workspace"]

    resolved_root = find_suite_root(root)
    manifest, manifest_findings = load_manifest(resolved_root)
    if manifest_findings:
        return create_response(status="error", blockers=manifest_findings, reasons=["Manifest validation failed."])

    assert manifest is not None
    routes = manifest.get("routes", {})
    route_def = routes[intent]

    read_only = bool(route_def.get("read_only", False))
    documentation_only = bool(route_def.get("documentation_only", False))
    evaluates_workspace = bool(route_def.get("evaluates_workspace", False))

    reasons: list[str] = []
    blockers: list[dict[str, str]] = []
    needs_input = False

    if requirements == "unknown":
        if intent in ("bootstrap", "feature", "patch"):
            needs_input = True
            reasons.append(f"Requirements unknown for {intent}; detailed input required before planning stages.")
            blockers.append({"code": "REQUIREMENTS_UNKNOWN", "message": f"Requirements are unknown for intent '{intent}'."})
        elif intent == "adopt":
            reasons.append("Requirements unknown for adopt: proceeding with source observation and intake.")
        else:
            reasons.append(f"Requirements unknown for {intent}: proceeding without blocking initial investigation.")
    elif requirements == "unclear" and intent == "patch":
        # Patch is pre-diagnosed with well-defined constraints; unclear requirements contradict that premise.
        needs_input = True
        reasons.append("Requirements unclear for patch; patch requires pre-diagnosed, well-defined constraints.")
        blockers.append({"code": "REQUIREMENTS_UNCLEAR", "message": "Requirements must be clear ('clear') for intent 'patch'."})

    interactive_approval_required = False
    if read_only:
        reasons.append(f"Read-only intent '{intent}' ignores risk classification.")
    else:
        if risk == "unknown":
            needs_input = True
            reasons.append(f"Risk is unknown for mutating intent '{intent}'.")
            blockers.append({"code": "RISK_UNKNOWN", "message": f"Risk must be assessed ('low' or 'high') for mutating intent '{intent}'."})
        elif risk == "high":
            interactive_approval_required = True
            reasons.append(f"High-risk mutating intent '{intent}' requires interactive approval.")

    prepend_workspace = False
    if evaluates_workspace:
        if workspace == "unknown":
            needs_input = True
            reasons.append(f"Workspace selection is unknown for mutating intent '{intent}'.")
            blockers.append({"code": "WORKSPACE_UNKNOWN", "message": f"Workspace selection must be specified for intent '{intent}'."})
        elif workspace == "isolated":
            prepend_workspace = True
            reasons.append("Isolated workspace requested: prepending daw-workspace stage.")
        else:
            reasons.append("In-place workspace selected.")
    else:
        reasons.append(f"Intent '{intent}' does not evaluate workspace isolation.")

    if needs_input:
        return create_response(
            status="needs-input",
            stages=[],
            reasons=reasons,
            blockers=blockers,
            read_only=read_only,
            documentation_only=documentation_only,
            interactive_approval_required=interactive_approval_required,
        )

    # All 10 core suite modules must exist on disk
    module_findings = check_suite_modules(resolved_root, manifest)
    if module_findings:
        return create_response(
            status="blocked",
            stages=[],
            reasons=reasons + ["Suite verification identified missing or invalid core modules."],
            blockers=module_findings,
            read_only=read_only,
            documentation_only=documentation_only,
            interactive_approval_required=interactive_approval_required,
        )

    if intent == "feature":
        if requirements == "unclear":
            stages = list(route_def.get("stages_unclear", []))
            reasons.append("Requirements unclear for feature: prepending daw-design stage.")
        else:
            stages = list(route_def.get("stages_clear", []))
    else:
        stages = list(route_def.get("stages", []))

    if prepend_workspace:
        stages = ["daw-workspace"] + [s for s in stages if s != "daw-workspace"]

    reasons.append("Route resolved successfully.")
    return create_response(
        status="ready",
        stages=stages,
        reasons=reasons,
        blockers=[],
        read_only=read_only,
        documentation_only=documentation_only,
        interactive_approval_required=interactive_approval_required,
    )


def format_text_output(result: dict[str, Any]) -> str:
    """Format resolution result as human-readable text."""
    lines = [
        f"Status: {result['status']}",
        f"Stages: {' -> '.join(result['stages']) if result['stages'] else '(none)'}",
        f"Constraints: read_only={result['constraints']['read_only']}, "
        f"documentation_only={result['constraints']['documentation_only']}, "
        f"interactive_approval_required={result['constraints']['interactive_approval_required']}, "
        f"authorization_granted={result['constraints']['authorization_granted']}",
    ]
    if result["reasons"]:
        lines.append("Reasons:")
        for r in result["reasons"]:
            lines.append(f"  - {r}")
    if result["blockers"]:
        lines.append("Blockers:")
        for b in result["blockers"]:
            lines.append(f"  - [{b['code']}] {b['message']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic Agentic Workflow Request Router")
    parser.add_argument("request", nargs="?", help="Path to JSON request file")
    parser.add_argument("--check-suite", action="store_true", help="Validate suite manifest and module paths across workspace")
    parser.add_argument("--format", choices=["json", "text"], default="json", help="Output format (default: json)")
    parser.add_argument("--root", help="Explicit suite root directory")

    args = parser.parse_args(argv)
    root = find_suite_root(args.root)

    # Mode 1: Check Suite
    if args.check_suite:
        manifest_data, manifest_findings = load_manifest(root)
        if manifest_findings:
            res = create_response(
                status="error",
                blockers=manifest_findings,
                reasons=["Suite manifest syntax, schema, or invariant validation failed."],
            )
            exit_code = 2
        else:
            module_findings = check_suite_modules(root, manifest_data)
            if not module_findings:
                res = create_response(
                    status="ready",
                    reasons=["Suite manifest and all declared modules exist and are structurally valid."],
                )
                exit_code = 0
            else:
                res = create_response(
                    status="blocked",
                    blockers=module_findings,
                    reasons=["Suite verification identified missing or invalid module files on disk."],
                )
                exit_code = 1

        print(json.dumps(res, indent=2) if args.format == "json" else format_text_output(res))
        return exit_code

    # Mode 2: Request Route
    if not args.request:
        parser.error("REQUEST filepath required unless --check-suite is specified.")
        return 2

    req_path = pathlib.Path(args.request)
    if not req_path.is_file():
        err_res = create_response(status="error", blockers=[{"code": "REQUEST_FILE_NOT_FOUND", "message": "Request file does not exist."}], reasons=["Failed to read request file."])
        print(json.dumps(err_res, indent=2) if args.format == "json" else format_text_output(err_res))
        return 2

    try:
        if req_path.stat().st_size > MAX_INPUT_BYTES:
            err_res = create_response(status="error", blockers=[{"code": "REQUEST_SIZE_EXCEEDED", "message": f"Request file exceeds size limit ({MAX_INPUT_BYTES} bytes)."}], reasons=["Input file too large."])
            print(json.dumps(err_res, indent=2) if args.format == "json" else format_text_output(err_res))
            return 2
        raw_text = req_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        err_res = create_response(status="error", blockers=[{"code": "REQUEST_FILE_READ_ERROR", "message": "Failed reading request file."}], reasons=["Read error."])
        print(json.dumps(err_res, indent=2) if args.format == "json" else format_text_output(err_res))
        return 2

    req_data, err = parse_strict_json(raw_text)
    if err:
        err_res = create_response(status="error", blockers=[{"code": "REQUEST_PARSE_ERROR", "message": f"Request file is not valid JSON: {err}"}], reasons=["JSON parse error."])
        print(json.dumps(err_res, indent=2) if args.format == "json" else format_text_output(err_res))
        return 2

    result = resolve_route(req_data, root=root)
    print(json.dumps(result, indent=2) if args.format == "json" else format_text_output(result))

    status = result["status"]
    if status == "ready":
        return 0
    elif status in ("needs-input", "blocked"):
        return 1
    else:
        return 2


if __name__ == "__main__":
    sys.exit(main())
