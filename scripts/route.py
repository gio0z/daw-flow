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
import re
import sys
from typing import Any, Tuple

# Bundled helper imports must not modify the installed suite.
sys.dont_write_bytecode = True
import daw_common

SCHEMA_VERSION = 1
MAX_INPUT_BYTES = 1024 * 1024  # 1 MiB bounded input limit
MAX_MODULE_BYTES = 256 * 1024  # 256 KiB bounded module read limit

VALID_ENUMS: dict[str, frozenset[str]] = {
    "intent": frozenset({
        "bootstrap", "adopt", "feature", "bugfix", "patch", "review", "untangle", "ask", "setup",
        "refactor", "maintain", "spike", "ship",
    }),
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
    "daw-untangle",
    "daw-ship",
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
    "untangle": ["daw-untangle"],
    "ask": ["daw-ask"],
    "setup": ["daw-setup"],
    "refactor": ["daw-untangle", "daw-plan", "daw-build", "daw-review", "daw-verify"],
    "maintain": ["daw-plan", "daw-build", "daw-review", "daw-verify"],
    "spike": ["daw-workspace", "daw-build", "daw-ask"],
    "ship": ["daw-ship"],
}

# Mutating intents that select in-place vs isolated workspace before stages run.
WORKSPACE_EVALUATING_INTENTS = frozenset({"feature", "bugfix", "patch", "refactor", "maintain"})

# Intents whose stages cannot start while requirements are entirely unknown.
REQUIREMENTS_GATED_INTENTS = frozenset({"bootstrap", "feature", "patch", "refactor", "maintain"})


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

    resolved, err = daw_common.resolve_bounded_path(root, rel_path)
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

    frontmatter, fm_errors = daw_common.parse_frontmatter(content)
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
    """Validate manifest modules object and all canonical entries."""
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
        required_mod_keys = {"path", "description"}
        optional_mod_keys = {"maturity", "bucket"}
        allowed_mod_keys = required_mod_keys | optional_mod_keys
        if not required_mod_keys.issubset(set(mod_info.keys())):
            findings.append({"code": "MANIFEST_MODULE_MISSING_KEYS", "message": f"Module entry '{mod_name}' missing required keys: path, description."})
        unknown_mod_keys = set(mod_info.keys()) - allowed_mod_keys
        if unknown_mod_keys:
            findings.append({"code": "MANIFEST_MODULE_UNKNOWN_KEYS", "message": f"Module entry '{mod_name}' has unknown keys."})
        if not isinstance(mod_info.get("path"), str):
            findings.append({"code": "MANIFEST_MODULE_PATH_INVALID", "message": f"Module '{mod_name}' path must be string."})
        if not isinstance(mod_info.get("description"), str):
            findings.append({"code": "MANIFEST_MODULE_DESCRIPTION_INVALID", "message": f"Module '{mod_name}' description must be string."})
        maturity = mod_info.get("maturity", "stable")
        if maturity not in ("stable", "beta", "deprecated", "experimental"):
            findings.append({"code": "MANIFEST_MODULE_MATURITY_INVALID", "message": f"Module '{mod_name}' maturity must be one of: stable, beta, deprecated, experimental."})
        bucket = mod_info.get("bucket", "engineering")
        if bucket not in ("engineering", "productivity", "misc", "in-progress", "deprecated"):
            findings.append({"code": "MANIFEST_MODULE_BUCKET_INVALID", "message": f"Module '{mod_name}' bucket must be one of: engineering, productivity, misc, in-progress, deprecated."})

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
        expected_ro = (r_name in ("review", "untangle", "ask"))
        expected_ws = (r_name in WORKSPACE_EVALUATING_INTENTS)

        if r_def.get("documentation_only") is not expected_doc:
            findings.append({"code": "MANIFEST_ROUTE_INVARIANT_VIOLATION", "message": f"Route '{r_name}' documentation_only must be {expected_doc}."})
        if r_def.get("read_only") is not expected_ro:
            findings.append({"code": "MANIFEST_ROUTE_INVARIANT_VIOLATION", "message": f"Route '{r_name}' read_only must be {expected_ro}."})
        if r_def.get("evaluates_workspace") is not expected_ws:
            findings.append({"code": "MANIFEST_ROUTE_INVARIANT_VIOLATION", "message": f"Route '{r_name}' evaluates_workspace must be {expected_ws}."})

        # Allow optional enterprise fields alongside canonical keys (defined before use).
        optional_route_keys = {"conditional_stages", "parallel_groups", "extension_hooks"}

        # Stages invariants
        expected_stage_spec = CANONICAL_ROUTE_STAGES[r_name]
        if r_name == "feature":
            if r_def.get("stages_clear") != expected_stage_spec["stages_clear"] or r_def.get("stages_unclear") != expected_stage_spec["stages_unclear"]:
                findings.append({"code": "MANIFEST_ROUTE_INVARIANT_VIOLATION", "message": "Route 'feature' stages do not match canonical specification."})
            expected_feature_keys = {"documentation_only", "read_only", "stages_clear", "stages_unclear", "evaluates_workspace"} | optional_route_keys
            if set(r_def.keys()) != expected_feature_keys:
                findings.append({"code": "MANIFEST_ROUTE_SHAPE_INVALID", "message": "Route 'feature' contains unexpected or missing keys."})
            allowed_route_keys = expected_feature_keys
        else:
            if r_def.get("stages") != expected_stage_spec:
                findings.append({"code": "MANIFEST_ROUTE_INVARIANT_VIOLATION", "message": f"Route '{r_name}' stages must match canonical {expected_stage_spec}."})
            expected_keys = {"documentation_only", "read_only", "stages", "evaluates_workspace"} | optional_route_keys
            if r_name in ("bootstrap", "adopt", "setup"):
                expected_keys.add("allow_unclear_requirements")
                if r_def.get("allow_unclear_requirements") is not True:
                    findings.append({"code": "MANIFEST_ROUTE_INVARIANT_VIOLATION", "message": f"Route '{r_name}' allow_unclear_requirements must be True."})
            allowed_route_keys = expected_keys

        unknown_route_keys = set(r_def.keys()) - allowed_route_keys
        if unknown_route_keys:
            findings.append({"code": "MANIFEST_ROUTE_SHAPE_INVALID", "message": f"Route '{r_name}' contains unexpected or missing keys."})

        # Validate conditional_stages: list of {stage, if, insert_before?, insert_after?, duplicate_allowed?}
        cond_stages = r_def.get("conditional_stages", [])
        if not isinstance(cond_stages, list):
            findings.append({"code": "MANIFEST_ROUTE_CONDITIONAL_INVALID", "message": f"Route '{r_name}' conditional_stages must be a list."})
        else:
            for i, cs in enumerate(cond_stages):
                if not isinstance(cs, dict):
                    findings.append({"code": "MANIFEST_ROUTE_CONDITIONAL_INVALID", "message": f"Route '{r_name}' conditional_stages[{i}] must be an object."})
                    continue
                if not isinstance(cs.get("stage"), str) or not cs.get("stage"):
                    findings.append({"code": "MANIFEST_ROUTE_CONDITIONAL_INVALID", "message": f"Route '{r_name}' conditional_stages[{i}] stage must be a non-empty string."})
                if not isinstance(cs.get("if"), str) or not cs.get("if"):
                    findings.append({"code": "MANIFEST_ROUTE_CONDITIONAL_INVALID", "message": f"Route '{r_name}' conditional_stages[{i}] if must be a non-empty string."})
                if cs.get("duplicate_allowed") is not None and not isinstance(cs.get("duplicate_allowed"), bool):
                    findings.append({"code": "MANIFEST_ROUTE_CONDITIONAL_INVALID", "message": f"Route '{r_name}' conditional_stages[{i}] duplicate_allowed must be boolean."})

        # Validate parallel_groups: list of [stage, stage] with disjoint module names.
        par_groups = r_def.get("parallel_groups", [])
        if not isinstance(par_groups, list):
            findings.append({"code": "MANIFEST_ROUTE_PARALLEL_INVALID", "message": f"Route '{r_name}' parallel_groups must be a list."})
        else:
            for i, pg in enumerate(par_groups):
                if not isinstance(pg, list) or len(pg) != 2:
                    findings.append({"code": "MANIFEST_ROUTE_PARALLEL_INVALID", "message": f"Route '{r_name}' parallel_groups[{i}] must be a pair of stage names."})
                elif pg[0] == pg[1]:
                    findings.append({"code": "MANIFEST_ROUTE_PARALLEL_INVALID", "message": f"Route '{r_name}' parallel_groups[{i}] stages must be distinct."})

        # Validate extension_hooks: dict of hook_point -> [hook_id, ...].
        ext_hooks = r_def.get("extension_hooks", {})
        if not isinstance(ext_hooks, dict):
            findings.append({"code": "MANIFEST_ROUTE_HOOKS_INVALID", "message": f"Route '{r_name}' extension_hooks must be an object."})
        else:
            for hp, hook_ids in ext_hooks.items():
                if not isinstance(hp, str):
                    findings.append({"code": "MANIFEST_ROUTE_HOOKS_INVALID", "message": f"Route '{r_name}' extension_hooks point must be string."})
                if not isinstance(hook_ids, list):
                    findings.append({"code": "MANIFEST_ROUTE_HOOKS_INVALID", "message": f"Route '{r_name}' extension_hooks[{hp}] must be a list of hook IDs."})

    return findings

FLOW_GATE_STEP_RE = re.compile(r"^BPF-[1-8]$")


def _validate_flow_gate(gate: Any, routes: Any) -> list[dict[str, str]]:
    """Validate optional manifest flow_gate block, if present."""
    if gate is None:
        return []
    if not isinstance(gate, dict):
        return [{"code": "MANIFEST_FLOW_GATE_INVALID", "message": "Manifest flow_gate must be a JSON object."}]
    findings: list[dict[str, str]] = []
    document = gate.get("document")
    if not isinstance(document, str) or not document.strip():
        findings.append({"code": "MANIFEST_FLOW_GATE_INVALID", "message": "Manifest flow_gate.document must be a non-empty string."})
    required_steps = gate.get("required_steps")
    if not isinstance(required_steps, list) or not required_steps:
        findings.append({"code": "MANIFEST_FLOW_GATE_INVALID", "message": "Manifest flow_gate.required_steps must be a non-empty array."})
    else:
        for entry in required_steps:
            if not isinstance(entry, str) or not FLOW_GATE_STEP_RE.match(entry):
                findings.append({"code": "MANIFEST_FLOW_GATE_UNKNOWN_STEP", "message": "Manifest flow_gate.required_steps contains a step id not matching ^BPF-[1-8]$."})
                break
    affected_intents = gate.get("affected_intents")
    if not isinstance(affected_intents, list) or not affected_intents:
        findings.append({"code": "MANIFEST_FLOW_GATE_INVALID", "message": "Manifest flow_gate.affected_intents must be a non-empty array."})
    else:
        route_keys = set(routes.keys()) if isinstance(routes, dict) else set()
        for entry in affected_intents:
            if not isinstance(entry, str) or entry not in route_keys:
                findings.append({"code": "MANIFEST_FLOW_GATE_UNKNOWN_INTENT", "message": "Manifest flow_gate.affected_intents entry must be a key of routes."})
                break
    return findings


def load_manifest(root: pathlib.Path) -> Tuple[dict[str, Any] | None, list[dict[str, str]]]:
    """Load and strictly validate references/suite-manifest.json."""
    manifest_rel = "references/suite-manifest.json"
    manifest_path, err = daw_common.resolve_bounded_path(root, manifest_rel)
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
    allowed_keys = {"schema_version", "suite", "modules", "routes", "flow_gate"}
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
    findings.extend(_validate_flow_gate(data.get("flow_gate"), data.get("routes")))

    return data, findings


def check_suite_modules(root: pathlib.Path, manifest: dict[str, Any]) -> list[dict[str, str]]:
    """Verify that all canonical modules exist on disk within root."""
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
    """Validate suite manifest and verify all canonical modules on disk within root."""
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


def _eval_condition(cond_expr: str, ctx: dict[str, Any]) -> bool:
    """Evaluate a simple boolean condition expression against request context.

    Supports: ==, !=, and, or, not, parentheses, string literals (single-quoted),
    and context variable references (intent, requirements, risk, workspace).
    Intentionally restricted: no function calls, no attribute access, no imports.
    """
    if not isinstance(cond_expr, str) or not cond_expr.strip():
        return False

    expr = cond_expr.strip()

    safe_ctx = {k: v for k, v in ctx.items() if isinstance(v, str)}

    import re as _re

    if not _re.match(r"^[A-Za-z0-9_' \.\!\=\>\<\(\)\n\r\t]+$", expr):
        return False
    if "." in expr:
        return False

    normalized = expr.replace(" and ", " AND ").replace(" or ", " OR ").replace(" not ", " NOT ")

    def _replace_var(m: _re.Match[str]) -> str:
        name = m.group(0)
        if name in ("AND", "OR", "NOT", "True", "False", "None"):
            return name
        if name in safe_ctx:
            return repr(safe_ctx[name])
        return name

    normalized = _re.sub(r"\b[A-Za-z_][A-Za-z0-9_]*\b", _replace_var, normalized)
    normalized = normalized.replace(" AND ", " and ").replace(" OR ", " or ").replace(" NOT ", " not ")

    try:
        result = eval(normalized, {"__builtins__": {}}, {})
        return bool(result)
    except Exception:
        return False



FENCED_JSON_RE = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)
FLOW_NEVER_GATED_INTENTS = frozenset({"review", "untangle", "ask", "setup", "spike", "ship", "patch", "bootstrap", "adopt"})


def _load_flow_mapping(suite_root: pathlib.Path, document_rel: str) -> dict[str, Any] | None:
    """Read the first fenced ```json block from the flow document under suite root."""
    doc_path, err = daw_common.resolve_bounded_path(suite_root, document_rel)
    if err or doc_path is None or not doc_path.is_file():
        return None
    try:
        if doc_path.stat().st_size > MAX_INPUT_BYTES:
            return None
        content = doc_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    match = FENCED_JSON_RE.search(content)
    if not match:
        return None
    try:
        data = daw_common.parse_strict_json(match.group(1))
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _project_spec_dir(project_root: pathlib.Path) -> str:
    """Resolve {spec_dir} from the project's daw-config when parseable, else docs/specs."""
    try:
        from check_config import parse_config_block
    except ImportError:
        return "docs/specs"
    for agent_file in ("AGENTS.md", "CLAUDE.md"):
        af = project_root / agent_file
        if not af.is_file():
            continue
        try:
            text = af.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        config = parse_config_block(text)
        spec_dir = config.get("spec_dir")
        if spec_dir and spec_dir.strip():
            return spec_dir.strip()
        if "<!-- daw-config:start -->" in text and config:
            return "docs/specs"
        if "<!-- daw-config:start -->" in text:
            return "docs/specs"
    return "docs/specs"


def _flow_gate_blockers(
    suite_root: pathlib.Path,
    project_root: pathlib.Path,
    manifest: dict[str, Any],
    intent: str,
) -> list[dict[str, str]]:
    """Evaluate the flow artifact gate for an affected intent. Fail closed."""
    gate = manifest.get("flow_gate")
    if not isinstance(gate, dict):
        return [{"code": "FLOW_GATE_UNREADABLE", "message": "Flow gate configuration is missing or invalid in the suite manifest."}]
    affected = gate.get("affected_intents", [])
    if intent not in affected:
        return []
    if intent in FLOW_NEVER_GATED_INTENTS:
        return []
    document = gate.get("document")
    if not isinstance(document, str) or not document.strip():
        return [{"code": "FLOW_GATE_UNREADABLE", "message": "Flow gate document is missing or invalid in the suite manifest."}]
    mapping = _load_flow_mapping(suite_root, document)
    if mapping is None:
        return [{"code": "FLOW_GATE_UNREADABLE", "message": f"Flow gate document {document} is unreadable or unparseable."}]
    required_steps = gate.get("required_steps", [])
    if not isinstance(required_steps, list):
        required_steps = []
    required_set = {s for s in required_steps if isinstance(s, str)}
    step_names = {}
    steps = mapping.get("steps")
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict) and isinstance(step.get("id"), str):
                name = step.get("name")
                step_names[step["id"]] = name if isinstance(name, str) and name.strip() else step["id"]
    spec_dir = _project_spec_dir(project_root)
    blockers: list[dict[str, str]] = []
    artifact_steps = mapping.get("artifact_steps")
    if not isinstance(artifact_steps, list):
        return [{"code": "FLOW_GATE_UNREADABLE", "message": "Flow gate machine mapping has no artifact_steps."}]
    for entry in artifact_steps:
        if not isinstance(entry, dict):
            continue
        step_id = entry.get("step")
        if not isinstance(step_id, str) or step_id not in required_set:
            continue
        patterns = entry.get("patterns")
        if not isinstance(patterns, list) or not patterns:
            patterns = []
        require_text = entry.get("require_text")
        satisfied = False
        for pattern in patterns:
            if not isinstance(pattern, str) or not pattern.strip():
                continue
            expanded = pattern.replace("{spec_dir}", spec_dir)
            if pathlib.PurePosixPath(expanded).is_absolute() or expanded.startswith("/") or expanded.startswith("\\"):
                continue
            if ".." in pathlib.PurePosixPath(expanded).parts:
                continue
            for matched in sorted(project_root.glob(expanded)):
                if not matched.is_file():
                    continue
                try:
                    if matched.stat().st_size > MAX_INPUT_BYTES:
                        continue
                except OSError:
                    continue
                if require_text is None:
                    satisfied = True
                    break
                if not isinstance(require_text, str):
                    continue
                try:
                    text = matched.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                if require_text in text:
                    satisfied = True
                    break
            if satisfied:
                break
        if not satisfied:
            step_name = step_names.get(step_id, step_id)
            shown = [p.replace("{spec_dir}", spec_dir) for p in patterns if isinstance(p, str)]
            requirement = f" containing '{require_text}'" if isinstance(require_text, str) else ""
            blockers.append({
                "code": "FLOW_GATE_MISSING_ARTIFACT",
                "message": (
                    f"Flow step {step_id} ({step_name}): no artifact matching {shown}{requirement}"
                ),
            })
    return blockers


def resolve_route(
    request_data: Any,
    root: pathlib.Path | str | None = None,
    project_root: pathlib.Path | str | None = None,
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
        if intent in REQUIREMENTS_GATED_INTENTS:
            needs_input = True
            reasons.append(f"Requirements unknown for {intent}; detailed input required before planning stages.")
            blockers.append({"code": "REQUIREMENTS_UNKNOWN", "message": f"Requirements are unknown for intent '{intent}'."})
        elif intent == "spike":
            reasons.append("Requirements unknown for spike: a time-boxed throwaway experiment exists to resolve them.")
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

    # All canonical suite modules must exist on disk
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

    # --- Enterprise: conditional stage resolution ---
    cond_stages = route_def.get("conditional_stages", [])
    if isinstance(cond_stages, list):
        for cs in cond_stages:
            if not isinstance(cs, dict):
                continue
            cond_expr = cs.get("if", "")
            stage_name = cs.get("stage", "")
            duplicate_allowed = bool(cs.get("duplicate_allowed", False))
            insert_before = cs.get("insert_before")
            insert_after = cs.get("insert_after")

            # Evaluate simple condition expressions against request data.
            cond_met = _eval_condition(cond_expr, {
                "intent": intent,
                "requirements": requirements,
                "risk": risk,
                "workspace": workspace,
            })
            if not cond_met:
                continue

            if stage_name in stages and not duplicate_allowed:
                reasons.append(f"Conditional stage '{stage_name}' already present; skipping duplicate.")
                continue

            if insert_before and insert_before in stages:
                idx = stages.index(insert_before)
                stages.insert(idx, stage_name)
                reasons.append(f"Conditional stage '{stage_name}' inserted before '{insert_before}' (condition: {cond_expr}).")
            elif insert_after and insert_after in stages:
                idx = stages.index(insert_after) + 1
                stages.insert(idx, stage_name)
                reasons.append(f"Conditional stage '{stage_name}' inserted after '{insert_after}' (condition: {cond_expr}).")
            else:
                stages.append(stage_name)
                reasons.append(f"Conditional stage '{stage_name}' appended (condition: {cond_expr}).")

    # --- Enterprise: parallel group validation ---
    par_groups = route_def.get("parallel_groups", [])
    if isinstance(par_groups, list):
        for pg in par_groups:
            if isinstance(pg, list) and len(pg) == 2 and pg[0] != pg[1]:
                if pg[0] in stages and pg[1] in stages:
                    reasons.append(f"Parallel group [{pg[0]}, {pg[1]}]: both stages present; may execute concurrently if disjoint.")

    if prepend_workspace:
        stages = ["daw-workspace"] + [s for s in stages if s != "daw-workspace"]

    # --- Enterprise: module maturity check ---
    maturity_findings = []
    modules = manifest.get("modules", {})
    for stage in stages:
        mod_info = modules.get(stage)
        if isinstance(mod_info, dict):
            maturity = mod_info.get("maturity", "stable")
            bucket = mod_info.get("bucket", "engineering")
            if maturity == "deprecated":
                maturity_findings.append({
                    "code": "MODULE_DEPRECATED",
                    "message": f"Module '{stage}' is deprecated; avoid in active route.",
                })
            elif maturity == "experimental":
                reasons.append(f"Module '{stage}' is experimental ({bucket}); use with caution.")
    if maturity_findings:
        return create_response(
            status="blocked",
            stages=stages,
            reasons=reasons + ["Route blocked due to deprecated module(s)."],
            blockers=maturity_findings,
            read_only=read_only,
            documentation_only=documentation_only,
            interactive_approval_required=interactive_approval_required,
        )

    if intent == "spike":
        reasons.append("Spike output is throwaway: findings return through daw-ask; production code re-enters feature/refactor.")
    elif intent == "refactor":
        reasons.append("Refactor must preserve observable behavior: characterization tests precede structural edits.")
    elif intent == "ship":
        reasons.append("Ship prepares integration only: push, merge, tag, and publish each need point-of-risk authorization.")

    # --- Enterprise: extension hook declaration ---
    ext_hooks = route_def.get("extension_hooks", {})
    if isinstance(ext_hooks, dict):
        for hp, hook_ids in ext_hooks.items():
            if isinstance(hook_ids, list) and hook_ids:
                reasons.append(f"Extension hook '{hp}': {len(hook_ids)} hook(s) declared.")

    reasons.append("Route resolved successfully.")
    if project_root is not None and intent not in FLOW_NEVER_GATED_INTENTS:
        gate = manifest.get("flow_gate")
        affected: list[Any] = gate.get("affected_intents", []) if isinstance(gate, dict) else []
        if intent in affected:
            gate_blockers = _flow_gate_blockers(resolved_root, pathlib.Path(project_root), manifest, intent)
            if gate_blockers:
                missing = ", ".join(
                    b["message"].split(": ")[0].removeprefix("Flow step ").strip()
                    for b in gate_blockers
                    if b.get("code") == "FLOW_GATE_MISSING_ARTIFACT" and ": " in b.get("message", "")
                )
                suffix = f" Missing flow steps: {missing}." if missing else " Missing flow artifacts."
                return create_response(
                    status="blocked",
                    stages=stages,
                    reasons=reasons + [f"Flow gate blocked intent '{intent}': required artifacts are missing.{suffix}"],
                    blockers=gate_blockers,
                    read_only=read_only,
                    documentation_only=documentation_only,
                    interactive_approval_required=interactive_approval_required,
                )
    return create_response(
        status="ready",
        stages=stages,
        reasons=reasons,
        blockers=[],
        read_only=read_only,
        documentation_only=documentation_only,
        interactive_approval_required=interactive_approval_required,
    )


def _session_start_resolve(root: pathlib.Path) -> dict[str, Any]:
    """Analyze project context for bare invocation and suggest an initial route.

    Detection is read-only and heuristic: inspects for DAW artifacts (config block,
    specs, plans, workflows, evidence) to recommend the most appropriate entry point.
    Never mutates files; returns a suggested intent plus rationale.
    """
    reasons: list[str] = []
    blockers: list[dict[str, str]] = []

    # Detect existing DAW configuration block.
    has_config_block = False
    for agent_file in ("AGENTS.md", "CLAUDE.md"):
        af = root / agent_file
        if af.is_file():
            try:
                content = af.read_text(encoding="utf-8")
                if "<!-- daw-config:start -->" in content:
                    has_config_block = True
                    reasons.append(f"DAW configuration block found in {agent_file}.")
                    break
            except (OSError, UnicodeDecodeError):
                pass

    # Detect DAW artifact directories.
    spec_dir = root / "docs" / "specs"
    plan_dir = root / "docs" / "plans"
    workflow_dir = root / "docs" / "workflows"
    evidence_dir = root / "docs" / "evidence"

    has_specs = spec_dir.is_dir() and any(spec_dir.iterdir())
    has_plans = plan_dir.is_dir() and any(plan_dir.iterdir())
    has_workflows = workflow_dir.is_dir() and any(workflow_dir.iterdir())
    has_evidence = evidence_dir.is_dir() and any(evidence_dir.iterdir())

    # Suggest intent based on artifact maturity.
    if not has_config_block:
        suggested_intent = "setup"
        reasons.append("No DAW configuration block found: recommend setup to initialize project conventions.")
    elif has_evidence:
        suggested_intent = "ship"
        reasons.append("Task evidence contracts detected: recommend ship for integration and delivery.")
    elif has_workflows:
        suggested_intent = "verify"
        reasons.append("Workflow progress record detected: recommend verify to resume and confirm completion.")
    elif has_plans:
        suggested_intent = "build"
        reasons.append("Plan artifacts detected: recommend build route for implementation.")
    elif has_specs:
        suggested_intent = "plan"
        reasons.append("Specification artifacts detected: recommend plan for tactical decomposition.")
    else:
        suggested_intent = "bootstrap"
        reasons.append("No DAW artifacts found: recommend bootstrap for greenfield specification.")

    # Build a sample request to validate the suggested intent is routable.
    sample_req = {
        "schema_version": 1,
        "intent": suggested_intent,
        "requirements": "clear",
        "risk": "low",
        "workspace": "in-place",
    }

    # Adjust for intents with special requirements.
    if suggested_intent == "bootstrap":
        sample_req["requirements"] = "unclear"
    if suggested_intent in ("setup", "adopt"):
        sample_req["requirements"] = "unclear"

    # Resolve the suggested route to validate it.
    resolved = resolve_route(sample_req, root=root)

    if resolved["status"] == "ready":
        return create_response(
            status="ready",
            stages=resolved["stages"],
            reasons=reasons + resolved["reasons"],
            blockers=[],
            read_only=resolved["constraints"]["read_only"],
            documentation_only=resolved["constraints"]["documentation_only"],
            interactive_approval_required=resolved["constraints"]["interactive_approval_required"],
        )
    elif resolved["status"] == "needs-input":
        return create_response(
            status="needs-input",
            stages=[],
            reasons=reasons + resolved["reasons"],
            blockers=resolved["blockers"],
            read_only=resolved["constraints"]["read_only"],
            documentation_only=resolved["constraints"]["documentation_only"],
            interactive_approval_required=resolved["constraints"]["interactive_approval_required"],
        )
    else:
        return create_response(
            status="blocked",
            stages=[],
            reasons=reasons + resolved["reasons"],
            blockers=resolved["blockers"],
            read_only=resolved["constraints"]["read_only"],
            documentation_only=resolved["constraints"]["documentation_only"],
            interactive_approval_required=resolved["constraints"]["interactive_approval_required"],
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
    parser.add_argument(
        "--session-start",
        action="store_true",
        help="Bare invocation: analyze project context and suggest an initial route.",
    )
    parser.add_argument("--project-root", default=None, help="Project root for flow artifact gate (affected intents only)")

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

    # Mode 3: Session Start — bare invocation, analyze project context and suggest route.
    if args.session_start:
        res = _session_start_resolve(root)
        print(json.dumps(res, indent=2) if args.format == "json" else format_text_output(res))
        status = res["status"]
        if status == "ready":
            return 0
        elif status in ("needs-input", "blocked"):
            return 1
        else:
            return 2

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
    result = resolve_route(req_data, root=root, project_root=args.project_root)
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
