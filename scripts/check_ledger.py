"""Spec ledger validation (`validate.py ledger`): persisted per-document workflow state."""

from __future__ import annotations

import os
import pathlib
import re
from typing import Any

try:
    from scripts.daw_common import (
        build_result as _build_result,
        compute_sha256,
        make_error as _error,
        make_warning as _warning,
        parse_strict_json,
        resolve_bounded_path,
        is_durable_evidence_path,
    )
except ImportError:
    from daw_common import (  # type: ignore[import-not-found]
        build_result as _build_result,
        compute_sha256,
        make_error as _error,
        make_warning as _warning,
        parse_strict_json,
        resolve_bounded_path,
        is_durable_evidence_path,
    )

try:
    from scripts.check_docs import (
        validate_docs,
    )
except ImportError:
    from check_docs import (  # type: ignore[import-not-found]
        validate_docs,
    )

LEDGER_STATES = ("intake", "authoring", "review", "rework", "ready")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

LEDGER_LIMITATIONS = [
    "Structural verification only; does not certify semantic truth, completeness, or real-world operational accuracy.",
    "Validator is read-only and does not persist state; parent workflow must verify transition provenance and record actual state changes.",
    "Durable-path check is a deterministic path-segment denylist (tmp/temp/.tmp/scratch/.cache/__pycache__/dot-segments except .github); it cannot detect gitignored paths.",
]


def is_durable(path_str: str) -> bool:
    return bool(is_durable_evidence_path(path_str))


def _resolve_record_for_docs(
    record_path: pathlib.Path,
    project_root: pathlib.Path,
    transition: str,
    documents: list[str],
) -> dict[str, Any]:
    """Invoke existing docs validation for ledger `ready` state (contract-specified)."""
    return validate_docs(record_path, project_root, transition, documents)


def validate_ledger(
    ledger_data: Any,
    project_root: pathlib.Path,
) -> dict[str, Any]:
    """Validate an already-parsed ledger object against project root."""
    findings: list[dict[str, str]] = []
    try:
        root = pathlib.Path(project_root).resolve()
    except (OSError, RuntimeError, ValueError):
        findings.append(_error("project_root_error", "$", "Cannot resolve project root."))
        return _build_result("ledger", findings, LEDGER_LIMITATIONS)

    if not root.is_dir():
        findings.append(_error("project_root_not_dir", str(project_root), "Project root is not a valid directory."))
        return _build_result("ledger", findings, LEDGER_LIMITATIONS)

    if not isinstance(ledger_data, dict):
        findings.append(_error("ledger_not_object", "$", "Ledger root must be a JSON object."))
        return _build_result("ledger", findings, LEDGER_LIMITATIONS)

    for k in ledger_data:
        if k not in {"schema_version", "documents"}:
            findings.append(_error("unknown_field", str(k), "Unknown field in ledger root."))
    for required in ("schema_version", "documents"):
        if required not in ledger_data:
            findings.append(_error("missing_required_field", required, f"Missing required field: {required}"))

    version = ledger_data.get("schema_version")
    if isinstance(version, bool) or not isinstance(version, int) or version != 1:
        findings.append(_error("invalid_schema_version", "schema_version", "schema_version must be integer 1."))

    documents = ledger_data.get("documents")
    if not isinstance(documents, list):
        findings.append(_error("invalid_documents", "documents", "documents must be an array."))
        return _build_result("ledger", findings, LEDGER_LIMITATIONS)
    if len(documents) == 0:
        findings.append(_error("empty_documents", "documents", "documents must not be empty."))

    seen_paths: dict[str, int] = {}
    for idx, entry in enumerate(documents):
        label = f"documents[{idx}]"
        if not isinstance(entry, dict):
            findings.append(_error("invalid_document_entry", label, "Document entry must be an object."))
            continue
        allowed = {"path", "state", "sha256", "record", "history"}
        for k in entry:
            if k not in allowed:
                findings.append(_error("unknown_field", f"{label}.{k}", "Unknown field in ledger document."))
        for req in ("path", "state", "sha256", "record"):
            if req not in entry:
                findings.append(_error("missing_required_field", f"{label}.{req}", f"Missing required field: {req}"))

        doc_path_str = entry.get("path")
        state = entry.get("state")
        expected_sha = entry.get("sha256")
        record_path_str = entry.get("record")
        if "record" in entry and (not isinstance(record_path_str, str) or not record_path_str.strip()):
            findings.append(
                _error("invalid_record", f"{label}.record", "record must be a non-empty string.")
            )

        if not isinstance(doc_path_str, str) or not doc_path_str.strip():
            findings.append(_error("invalid_path", f"{label}.path", "Document path must be a non-empty string."))
        else:
            # Duplicate detection on normalized path.
            norm = os.path.normpath(doc_path_str).replace("\\", "/")
            if norm in seen_paths:
                findings.append(
                    _error("ledger_duplicate_document", f"{label}.path", "Duplicate document path in ledger.")
                )
            else:
                seen_paths[norm] = idx
            resolved_doc, doc_err = resolve_bounded_path(root, doc_path_str)
            if doc_err or resolved_doc is None:
                findings.append(_error("boundary_violation", f"{label}.path", f"Document path violates boundary: {doc_err}"))
            elif not resolved_doc.is_file():
                findings.append(_error("file_not_found", f"{label}.path", "Document file does not exist."))
            else:
                if isinstance(expected_sha, str) and SHA256_RE.match(expected_sha):
                    try:
                        actual = compute_sha256(resolved_doc)
                    except (OSError, RuntimeError):
                        findings.append(_error("file_read_error", f"{label}.path", "Failed to read document file."))
                    else:
                        if actual != expected_sha:
                            findings.append(
                                _error("ledger_doc_drift", f"{label}.sha256", "Document SHA256 does not match ledger hash.")
                            )
        if not isinstance(expected_sha, str) or not SHA256_RE.match(expected_sha or ""):
            findings.append(_error("invalid_sha256", f"{label}.sha256", "sha256 must be a 64-character lowercase hex string."))

        if not isinstance(state, str) or state not in LEDGER_STATES:
            findings.append(_error("invalid_state", f"{label}.state", f"state must be one of {list(LEDGER_STATES)}."))

        record_resolved: pathlib.Path | None = None
        record_rel_for_docs: str | None = None
        record_obj: Any = None
        record_ok = False
        if isinstance(record_path_str, str) and record_path_str.strip():
            if not is_durable(record_path_str):
                findings.append(_error("evidence_not_durable", f"{label}.record", "Record path is not durable."))
            record_res, rec_err = resolve_bounded_path(root, record_path_str)
            if rec_err or record_res is None:
                findings.append(_error("boundary_violation", f"{label}.record", f"Record path violates boundary: {rec_err}"))
            elif not record_res.is_file():
                findings.append(_error("file_not_found", f"{label}.record", "Record file does not exist."))
            else:
                record_resolved = record_res
                record_rel_for_docs = record_path_str
                try:
                    raw = record_res.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError, RuntimeError):
                    findings.append(_error("record_unreadable", f"{label}.record", "Record file cannot be read as UTF-8."))
                else:
                    try:
                        record_obj = parse_strict_json(raw)
                    except Exception:
                        findings.append(_error("record_malformed_json", f"{label}.record", "Record contains malformed JSON or duplicate keys."))
                    else:
                        record_ok = True

        history = entry.get("history")
        if history is not None:
            if not isinstance(history, list):
                findings.append(_error("invalid_history", f"{label}.history", "history must be an array if present."))
            else:
                for h_idx, h_path in enumerate(history):
                    h_label = f"{label}.history[{h_idx}]"
                    if not isinstance(h_path, str) or not h_path.strip():
                        findings.append(_error("invalid_path", h_label, "History path must be a non-empty string."))
                        continue
                    if not is_durable(h_path):
                        findings.append(_error("evidence_not_durable", h_label, "History path is not durable."))
                    h_res, h_err = resolve_bounded_path(root, h_path)
                    if h_err or h_res is None:
                        findings.append(_error("boundary_violation", h_label, f"History path violates boundary: {h_err}"))
                    elif not h_res.is_file():
                        findings.append(_error("file_not_found", h_label, "History file does not exist."))

        if record_ok and isinstance(record_obj, dict):
            rec_docs = record_obj.get("documents")
            matched: dict[str, Any] | None = None
            if isinstance(doc_path_str, str) and isinstance(rec_docs, list):
                norm_target = os.path.normpath(doc_path_str).replace("\\", "/")
                for rec_idx, rec_doc in enumerate(rec_docs):
                    if isinstance(rec_doc, dict) and isinstance(rec_doc.get("path"), str):
                        if os.path.normpath(rec_doc["path"]).replace("\\", "/") == norm_target:
                            matched = rec_doc
                            matched_idx = rec_idx
                            break
            if matched is None:
                findings.append(_error("ledger_record_mismatch", f"{label}.record", "Record contains no entry for this document."))
            else:
                rec_sha = matched.get("sha256")
                if rec_sha != expected_sha:
                    findings.append(_error("ledger_record_mismatch", f"{label}.sha256", "Record sha256 does not match ledger sha256."))
            rec_transition = record_obj.get("transition")
            rec_to = rec_transition.get("to") if isinstance(rec_transition, dict) else None
            if rec_to != state:
                findings.append(_error("ledger_state_mismatch", f"{label}.state", "Record transition.to does not match ledger state."))
            if state == "ready" and matched is not None and record_resolved is not None:
                record_doc_paths = [
                    d["path"] for d in rec_docs if isinstance(d, dict) and isinstance(d.get("path"), str)
                ]
                own_prefix = f"documents[{matched_idx}]"
                try:
                    docs_res = _resolve_record_for_docs(
                        record_resolved, root, "review-ready", record_doc_paths
                    )
                except Exception:
                    findings.append(_error("ledger_record_mismatch", f"{label}.record", "Ready-state docs validation could not run."))
                else:
                    # Keep record-level findings and findings for this document only.
                    for f in docs_res.get("findings", []):
                        f_path = f.get("path", "")
                        if f_path.startswith("documents[") and not (
                            f_path == own_prefix or f_path.startswith(own_prefix + ".")
                        ):
                            continue
                        findings.append(
                            {
                                "severity": f.get("severity", "error"),
                                "code": f.get("code", "unknown"),
                                "path": f"{label}.record:{f_path}",
                                "message": f.get("message", ""),
                            }
                        )
        elif record_ok:
            findings.append(_error("ledger_record_mismatch", f"{label}.record", "Record root must be a JSON object."))

    return _build_result("ledger", findings, LEDGER_LIMITATIONS)
