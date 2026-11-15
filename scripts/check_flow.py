"""Best Practice Flow mapping check (`validate.py flow`).

Validates that the machine-readable mapping embedded in
``references/best-practice-flow.md`` is well-formed, that its nine adopted
steps point at anchors that resolve in this repository, that every cross-link
document still references the flow, and that ``references/suite-manifest.json``
carries the matching ``flow_gate`` wiring. Read-only; owns no other rules.
"""

from __future__ import annotations

import json
import pathlib
import re
import string
from typing import Any

try:
    from scripts.daw_common import (
        DuplicateKeyError,
        build_result,
        make_error,
        parse_strict_json,
        resolve_bounded_path,
    )
except ImportError:
    from daw_common import (  # type: ignore[import-not-found]
        DuplicateKeyError,
        build_result,
        make_error,
        parse_strict_json,
        resolve_bounded_path,
    )

FLOW_LIMITATIONS = [
    "Read-only: never writes files, never runs subprocesses or builds, and never evaluates the semantic truth of the mapped rules.",
    "Anchor resolution is limited to the exact heading-slug rule documented in _heading_slug; anchors stored elsewhere or using a different slugger are not checked.",
    "Oversize inputs over 1 MiB are rejected unread rather than truncated, so a large file never yields a partial verdict.",
]

_FLOW_DOC_PATH = "references/best-practice-flow.md"
_MANIFEST_PATH = "references/suite-manifest.json"
_FLOW_SCHEMA_VERSION = 1
_EXPECTED_STEP_COUNT = 9
_ALLOWED_SOURCES = frozenset({"spec-kit", "superpowers", "pocock", "original"})
_REQUIRED_CROSS_LINKS = ("SKILL.md", "references/routing.md")
_JSON_PARSE_ERRORS = (json.JSONDecodeError, DuplicateKeyError, RecursionError, ValueError)

# Local bounded-input guard: daw_common does not expose a shared constant.
MAX_INPUT_BYTES = 1024 * 1024  # 1 MiB


def _heading_slug(heading_text: str) -> str:
    """Slugify a markdown heading the way the flow anchors were generated.

    Rule: lowercase the text, drop every character outside ``[a-z0-9 -]``,
    turn spaces into ``-``, collapse runs of ``-`` into one, and strip leading
    or trailing ``-``.
    """
    lowered = heading_text.strip().lower()
    filtered = "".join(ch for ch in lowered if ch in string.ascii_lowercase + string.digits + " -")
    hyphenated = filtered.replace(" ", "-")
    collapsed = re.sub(r"-+", "-", hyphenated)
    return collapsed.strip("-")


def _read_bounded(path: pathlib.Path, code: str, findings: list[dict[str, str]]) -> str | None:
    """Read a file as UTF-8, adding a finding instead of reading oversize/unreadable files."""
    try:
        if path.stat().st_size > MAX_INPUT_BYTES:
            findings.append(
                make_error(code, str(path), f"Input file exceeds maximum allowed size ({MAX_INPUT_BYTES} bytes).")
            )
            return None
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        findings.append(make_error(code, str(path), "Input file cannot be read as UTF-8 text."))
        return None


def _extract_first_json_block(text: str) -> str | None:
    fence = text.find("```json")
    if fence < 0:
        return None
    start = fence + len("```json")
    end = text.find("```", start)
    if end < 0:
        return None
    return text[start:end].strip()


def _parse_flow_mapping(
    root: pathlib.Path, findings: list[dict[str, str]]
) -> tuple[dict[str, Any] | None, int]:
    """Validate the flow document and return (mapping or None, step count)."""
    doc, err = resolve_bounded_path(root, _FLOW_DOC_PATH)
    if doc is None or err is not None:
        findings.append(make_error("flow_doc_missing", _FLOW_DOC_PATH, f"Flow document path is unsafe ({err})."))
        return None, 0
    text = _read_bounded(doc, "flow_doc_missing", findings)
    if text is None:
        return None, 0
    block = _extract_first_json_block(text)
    if block is None:
        findings.append(
            make_error("flow_mapping_missing", f"{_FLOW_DOC_PATH}:$", "Flow document has no fenced json mapping block.")
        )
        return None, 0
    try:
        mapping = parse_strict_json(block)
    except _JSON_PARSE_ERRORS:
        findings.append(
            make_error("flow_malformed", f"{_FLOW_DOC_PATH}:$", "Flow document JSON mapping is not strict JSON.")
        )
        return None, 0
    if not isinstance(mapping, dict):
        findings.append(
            make_error("flow_malformed", f"{_FLOW_DOC_PATH}:$", "Flow mapping must be a JSON object.")
        )
        return None, 0
    return mapping, _validate_mapping_fields(root, mapping, findings)


def _validate_mapping_fields(root: pathlib.Path, mapping: dict[str, Any], findings: list[dict[str, str]]) -> int:
    version = mapping.get("flow_schema_version")
    if isinstance(version, bool) or not isinstance(version, int) or version != _FLOW_SCHEMA_VERSION:
        findings.append(
            make_error(
                "flow_schema_version_invalid",
                "flow_schema_version",
                f"flow_schema_version must be integer {_FLOW_SCHEMA_VERSION}.",
            )
        )
    steps = mapping.get("steps")
    if not isinstance(steps, list) or len(steps) != _EXPECTED_STEP_COUNT:
        count = len(steps) if isinstance(steps, list) else 0
        findings.append(
            make_error(
                "flow_step_count",
                "steps",
                f"steps must be an array of exactly {_EXPECTED_STEP_COUNT} entries (found {count}).",
            )
        )
        return count
    step_ids = _validate_steps(root, steps, findings)
    _validate_artifact_steps(mapping.get("artifact_steps"), step_ids, findings)
    _validate_cross_links(root, mapping.get("cross_links"), findings)
    return len(steps)


def _validate_steps(root: pathlib.Path, steps: list[Any], findings: list[dict[str, str]]) -> set[str]:
    seen: set[str] = set()
    known: set[str] = set()
    for index, step in enumerate(steps):
        expected_id = f"BPF-{index + 1}"
        if not isinstance(step, dict):
            findings.append(
                make_error("flow_step_field_invalid", f"steps[{index}]", "Each step must be a JSON object.")
            )
            continue
        step_id = step.get("id")
        if step_id != expected_id:
            findings.append(
                make_error(
                    "flow_step_id_invalid",
                    f"steps[{index}].id",
                    f"Step id must be {expected_id!r} at index {index}.",
                )
            )
        if isinstance(step_id, str):
            if step_id in seen:
                findings.append(
                    make_error("flow_duplicate_step", f"steps[{index}].id", f"Duplicate step id {step_id!r}.")
                )
            else:
                seen.add(step_id)
            known.add(step_id)
        for field in ("name", "anchor"):
            value = step.get(field)
            if not isinstance(value, str) or not value.strip():
                findings.append(
                    make_error(
                        "flow_step_field_invalid",
                        f"steps[{index}].{field}",
                        f"Step field {field!r} must be a non-blank string.",
                    )
                )
        if step.get("mandatory") is not True:
            findings.append(
                make_error(
                    "flow_step_field_invalid",
                    f"steps[{index}].mandatory",
                    "Step field 'mandatory' must be true.",
                )
            )
        source = step.get("source")
        if not isinstance(source, str) or source not in _ALLOWED_SOURCES:
            findings.append(
                make_error(
                    "flow_source_invalid",
                    f"steps[{index}].source",
                    f"Step source must be one of {sorted(_ALLOWED_SOURCES)}.",
                )
            )
        anchor = step.get("anchor")
        if isinstance(anchor, str) and anchor.strip():
            _validate_anchor(root, anchor, index, findings)
    return known


def _validate_artifact_steps(
    artifact_steps: Any, step_ids: set[str], findings: list[dict[str, str]]
) -> None:
    """Validate artifact_steps entries against the known step ids."""
    if not isinstance(artifact_steps, list):
        findings.append(
            make_error(
                "flow_artifact_step_invalid",
                "artifact_steps",
                "artifact_steps must be an array of objects.",
            )
        )
        return
    for index, entry in enumerate(artifact_steps):
        label = f"artifact_steps[{index}]"
        if not isinstance(entry, dict):
            findings.append(
                make_error(
                    "flow_artifact_step_invalid",
                    label,
                    "Each artifact_steps entry must be a JSON object.",
                )
            )
            continue
        step = entry.get("step")
        if not isinstance(step, str) or not step.strip():
            findings.append(
                make_error(
                    "flow_artifact_step_invalid",
                    f"{label}.step",
                    "artifact_steps[].step must be a non-blank string.",
                )
            )
        elif step not in step_ids:
            findings.append(
                make_error(
                    "flow_artifact_step_unknown",
                    f"{label}.step",
                    f"Unknown artifact step {step!r}.",
                )
            )
        patterns = entry.get("patterns")
        if (
            not isinstance(patterns, list)
            or not patterns
            or not all(isinstance(pattern, str) and pattern.strip() for pattern in patterns)
        ):
            findings.append(
                make_error(
                    "flow_artifact_step_invalid",
                    f"{label}.patterns",
                    "artifact_steps[].patterns must be a non-empty array of non-blank strings.",
                )
            )
        require_text = entry.get("require_text")
        if require_text is not None and (not isinstance(require_text, str) or not require_text.strip()):
            findings.append(
                make_error(
                    "flow_artifact_step_invalid",
                    f"{label}.require_text",
                    "artifact_steps[].require_text must be a non-empty string or null.",
                )
            )


def _validate_anchor(root: pathlib.Path, anchor: str, index: int, findings: list[dict[str, str]]) -> None:
    path_part, _, fragment = anchor.partition("#")
    if not path_part:
        findings.append(
            make_error(
                "flow_anchor_unresolved",
                f"steps[{index}].anchor",
                "Anchor must name a document path, optionally followed by #fragment.",
            )
        )
        return
    resolved, err = resolve_bounded_path(root, path_part)
    if resolved is None or err is not None:
        findings.append(
            make_error(
                "flow_anchor_unresolved",
                f"steps[{index}].anchor",
                f"Anchor document {path_part!r} is unsafe ({err}).",
            )
        )
        return
    if not resolved.is_file():
        findings.append(
            make_error(
                "flow_anchor_unresolved",
                f"steps[{index}].anchor",
                f"Anchor document {path_part!r} does not exist.",
            )
        )
        return
    if not fragment:
        return
    target = _read_bounded(resolved, "flow_anchor_unresolved", findings)
    if target is None:
        return
    slugs = {
        _heading_slug(line.lstrip("#").strip())
        for line in target.splitlines()
        if line.startswith("#")
    }
    if fragment not in slugs:
        findings.append(
            make_error(
                "flow_anchor_unresolved",
                f"steps[{index}].anchor",
                f"Anchor fragment {fragment!r} matches no heading slug in {path_part!r}.",
            )
        )


def _validate_cross_links(root: pathlib.Path, cross_links: Any, findings: list[dict[str, str]]) -> None:
    if not isinstance(cross_links, list):
        findings.append(
            make_error("flow_missing_link", "cross_links", "cross_links must be an array of document paths.")
        )
        return
    for entry in cross_links:
        if not isinstance(entry, str) or not entry.strip():
            findings.append(
                make_error("flow_missing_link", "cross_links", "Each cross-link must be a non-blank document path.")
            )
            continue
        resolved, err = resolve_bounded_path(root, entry)
        if resolved is None or err is not None or not resolved.is_file():
            findings.append(
                make_error(
                    "flow_missing_link",
                    entry,
                    f"Cross-link {entry!r} does not exist or is unsafe ({err}).",
                )
            )
            continue
        body = _read_bounded(resolved, "flow_missing_link", findings)
        if body is None:
            continue
        if "best-practice-flow.md" not in body:
            findings.append(
                make_error(
                    "flow_missing_link",
                    entry,
                    f"Cross-link {entry!r} does not mention best-practice-flow.md.",
                )
            )
    for required in _REQUIRED_CROSS_LINKS:
        if required not in cross_links:
            findings.append(
                make_error(
                    "flow_missing_link",
                    required,
                    f"cross_links must include {required!r}.",
                )
            )


def _validate_manifest(
    root: pathlib.Path, step_ids: set[str], artifact_steps: Any, findings: list[dict[str, str]]
) -> None:
    manifest, err = resolve_bounded_path(root, _MANIFEST_PATH)
    if manifest is None or err is not None:
        findings.append(make_error("flow_manifest_gate_missing", "flow_gate", f"Manifest path is unsafe ({err})."))
        return
    text = _read_bounded(manifest, "flow_manifest_gate_missing", findings)
    if text is None:
        return
    try:
        data = parse_strict_json(text)
    except _JSON_PARSE_ERRORS:
        findings.append(
            make_error("flow_manifest_gate_missing", "flow_gate", "Manifest is not strict JSON.")
        )
        return
    if not isinstance(data, dict):
        findings.append(
            make_error("flow_manifest_gate_missing", "flow_gate", "Manifest must be a JSON object.")
        )
        return
    gate = data.get("flow_gate")
    if not isinstance(gate, dict):
        findings.append(
            make_error("flow_manifest_gate_missing", "flow_gate", "Manifest flow_gate must be an object.")
        )
        return
    document = gate.get("document")
    if not isinstance(document, str) or not document.strip():
        findings.append(
            make_error("flow_manifest_gate_missing", "flow_gate", "flow_gate.document must be a non-empty string.")
        )
    elif document != _FLOW_DOC_PATH:
        findings.append(
            make_error(
                "flow_gate_document_mismatch",
                "flow_gate.document",
                f"flow_gate.document must be {_FLOW_DOC_PATH!r} so both gates read the same document.",
            )
        )
    required_steps = gate.get("required_steps")
    if not isinstance(required_steps, list) or not required_steps:
        findings.append(
            make_error("flow_manifest_gate_missing", "flow_gate", "flow_gate.required_steps must be a non-empty array.")
        )
    else:
        checked_steps = {
            entry.get("step")
            for entry in artifact_steps
            if isinstance(entry, dict) and isinstance(entry.get("step"), str)
        }
        for entry in required_steps:
            if not isinstance(entry, str):
                findings.append(
                    make_error(
                        "flow_gate_step_unknown",
                        "flow_gate.required_steps",
                        "flow_gate.required_steps entries must be strings.",
                    )
                )
                continue
            if entry not in step_ids:
                findings.append(
                    make_error(
                        "flow_gate_step_unknown",
                        "flow_gate.required_steps",
                        f"Unknown flow gate step {entry!r}.",
                    )
                )
            elif entry not in checked_steps:
                findings.append(
                    make_error(
                        "flow_artifact_step_missing",
                        "flow_gate.required_steps",
                        f"Required flow gate step {entry!r} has no artifact_steps entry.",
                    )
                )
    affected = gate.get("affected_intents")
    if not isinstance(affected, list) or not affected:
        findings.append(
            make_error("flow_manifest_gate_missing", "flow_gate", "flow_gate.affected_intents must be a non-empty array.")
        )
    else:
        routes = data.get("routes")
        route_keys = set(routes) if isinstance(routes, dict) else set()
        for entry in affected:
            if not isinstance(entry, str):
                findings.append(
                    make_error(
                        "flow_gate_intent_unknown",
                        "flow_gate.affected_intents",
                        "flow_gate.affected_intents entries must be strings.",
                    )
                )
                continue
            if entry not in route_keys:
                findings.append(
                    make_error(
                        "flow_gate_intent_unknown",
                        "flow_gate.affected_intents",
                        f"Unknown manifest route {entry!r}.",
                    )
                )


def validate_flow(project_root: pathlib.Path) -> dict[str, Any]:
    root = pathlib.Path(project_root).resolve()
    findings: list[dict[str, str]] = []
    mapping, steps_count = _parse_flow_mapping(root, findings)
    step_ids: set[str] = set()
    if isinstance(mapping, dict) and isinstance(mapping.get("steps"), list):
        step_ids = {
            step.get("id")
            for step in mapping["steps"]
            if isinstance(step, dict) and isinstance(step.get("id"), str)
        }
    if mapping is not None:
        _validate_manifest(root, step_ids, mapping.get("artifact_steps"), findings)
    return build_result("flow", findings, FLOW_LIMITATIONS, extra={"steps": steps_count})
