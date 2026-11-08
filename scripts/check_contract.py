"""Task contract lifecycle validation (`validate.py contract`).

`validate_contract` checks the root schema, then delegates each contract section to a
private `_check_<section>` helper. Sections only exchange the explicit values they return.
"""

from __future__ import annotations

import pathlib
import re
from typing import Any, Callable

try:
    from scripts.daw_common import (
        CANONICAL_DOC_STEMS,
        SCHEMA_VERSION,
        compute_sha256,
        is_durable_evidence_path,
        is_safe_relative_path,
        resolve_bounded_path,
    )
except ImportError:
    from daw_common import (  # type: ignore[import-not-found]
        CANONICAL_DOC_STEMS,
        SCHEMA_VERSION,
        compute_sha256,
        is_durable_evidence_path,
        is_safe_relative_path,
        resolve_bounded_path,
    )

CONTRACT_LIMITATIONS = [
    "Structural verification only; does not authenticate evidence authenticity, runtime safety, or operational authorization.",
    "Approval presence captures an opaque reference only and does not constitute runtime authorization.",
    "Baseline hashes verify current files only at plan/execute; complete checks historical record structure and boundaries. Revision strings are not verified against VCS history.",
]

_Emit = Callable[[str, str, str], None]


def _check_baseline(
    contract_data: dict[str, Any],
    project_root: pathlib.Path,
    stage: str,
    add_error: _Emit,
    add_warning: _Emit,
) -> str | None:
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
    return baseline_revision


def _check_documents(
    contract_data: dict[str, Any],
    project_root: pathlib.Path,
    stage: str,
    add_error: _Emit,
    add_warning: _Emit,
) -> None:
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
                add_error("invalid_document_kind", f"{d_loc}.kind", "Document kind must be one of the canonical stems.")
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


def _check_acceptance_criteria(
    contract_data: dict[str, Any],
    project_root: pathlib.Path,
    stage: str,
    add_error: _Emit,
    add_warning: _Emit,
) -> set[str]:
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
    return known_ac_ids


def _check_operation(
    contract_data: dict[str, Any],
    project_root: pathlib.Path,
    stage: str,
    add_error: _Emit,
    add_warning: _Emit,
    baseline_revision: str | None,
) -> tuple[str | None, str | None, str | None, str | None, list[str] | None]:
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
    return op_risk, op_action, op_target, op_revision, op_scope


def _check_approval(
    contract_data: dict[str, Any],
    project_root: pathlib.Path,
    stage: str,
    add_error: _Emit,
    add_warning: _Emit,
    op_risk: str | None,
    op_action: str | None,
    op_target: str | None,
    op_revision: str | None,
    op_scope: list[str] | None,
) -> None:
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


def _check_result(
    contract_data: dict[str, Any],
    project_root: pathlib.Path,
    stage: str,
    add_error: _Emit,
    add_warning: _Emit,
    baseline_revision: str | None,
) -> str | None:
    # result object (E3)
    result_data = contract_data.get("result")
    result_revision: str | None = None
    if result_data is not None:
        if stage == "plan":
            add_error("result_not_allowed", "result", "Result snapshot is forbidden at plan stage.")
        if not isinstance(result_data, dict):
            add_error("invalid_result", "result", "Result must be an object if present.")
        else:
            ALLOWED_RESULT_FIELDS = {"revision", "files"}
            has_unknown_res = False
            for rk in result_data.keys():
                if rk not in ALLOWED_RESULT_FIELDS:
                    has_unknown_res = True
            if has_unknown_res:
                add_error("unknown_field", "result", "Unknown field detected in result schema.")

            r_rev = result_data.get("revision")
            if not isinstance(r_rev, str) or not r_rev.strip():
                add_error("invalid_result_revision", "result.revision", "result.revision must be a non-blank string.")
            else:
                result_revision = r_rev

            r_files = result_data.get("files")
            if not isinstance(r_files, list):
                add_error("invalid_result_files", "result.files", "result.files must be an array.")
            else:
                if len(r_files) == 0:
                    add_error("empty_result_files", "result.files", "result.files must be a non-empty array.")
                seen_res_paths: set[str] = set()
                for idx, rf in enumerate(r_files):
                    f_loc = f"result.files[{idx}]"
                    if not isinstance(rf, dict):
                        add_error("invalid_result_entry", f_loc, "Result file entry must be an object.")
                        continue
                    ALLOWED_RF_FIELDS = {"path", "sha256"}
                    has_unknown_rf = False
                    for rfk in rf.keys():
                        if rfk not in ALLOWED_RF_FIELDS:
                            has_unknown_rf = True
                    if has_unknown_rf:
                        add_error("unknown_field", f_loc, "Unknown field detected in result file schema.")

                    fr_rel = rf.get("path")
                    fr_hash = rf.get("sha256")
                    if not isinstance(fr_rel, str) or not fr_rel.strip():
                        add_error("invalid_path", f"{f_loc}.path", "Result file path must be non-blank string.")
                        continue
                    if fr_rel in seen_res_paths:
                        add_error("duplicate_result_path", f"{f_loc}.path", "Duplicate path in result files.")
                    seen_res_paths.add(fr_rel)

                    if not isinstance(fr_hash, str) or not re.match(r"^[0-9a-f]{64}$", fr_hash.lower()):
                        add_error("invalid_sha256", f"{f_loc}.sha256", "Result sha256 must be a 64-character lowercase hex string.")

                    resolved_p, err = resolve_bounded_path(project_root, fr_rel)
                    if err:
                        add_error("boundary_violation", f"{f_loc}.path", f"Result path violates boundary: {err}")
                    elif resolved_p is None or not resolved_p.is_file():
                        add_error("file_not_found", f"{f_loc}.path", "Result file does not exist.")
                    else:
                        try:
                            actual_hash = compute_sha256(resolved_p)
                            if isinstance(fr_hash, str) and actual_hash != fr_hash.lower():
                                add_error("result_changed", f_loc, "Result file content changed since the recorded hash.")
                        except OSError:
                            add_error("file_read_error", f"{f_loc}.path", "Failed to read result file.")
    else:
        if stage == "complete":
            add_error("missing_result", "result", "Stage 'complete' requires a result object.")

    if result_revision is not None and baseline_revision is not None and result_revision == baseline_revision:
        add_error("result_revision_unchanged", "result.revision", "result.revision must differ from baseline.revision.")
    return result_revision


def _check_evidence(
    contract_data: dict[str, Any],
    project_root: pathlib.Path,
    stage: str,
    add_error: _Emit,
    add_warning: _Emit,
    known_ac_ids: set[str],
    result_revision: str | None,
) -> tuple[Any, set[str]]:
    # evidence (optional, E1/E2/E4)
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
                ALLOWED_EV_FIELDS = {"criterion_id", "status", "reference", "summary", "sha256", "revision"}
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

                # E2: sha256
                e_sha = ev.get("sha256")
                if e_sha is None:
                    if stage == "complete":
                        add_error("missing_evidence_sha256", f"{ev_loc}.sha256", "Stage 'complete' requires evidence sha256.")
                elif not isinstance(e_sha, str) or not re.match(r"^[0-9a-f]{64}$", e_sha.lower()):
                    add_error("invalid_sha256", f"{ev_loc}.sha256", "Evidence sha256 must be a 64-character lowercase hex string.")

                # E4: revision
                e_rev = ev.get("revision")
                if e_rev is None:
                    if stage == "complete":
                        add_error("missing_evidence_revision", f"{ev_loc}.revision", "Stage 'complete' requires evidence revision.")
                elif not isinstance(e_rev, str) or not e_rev.strip():
                    add_error("invalid_evidence_revision", f"{ev_loc}.revision", "Evidence revision must be a non-blank string.")
                elif result_revision is not None and e_rev != result_revision:
                    add_error("evidence_revision_mismatch", f"{ev_loc}.revision", "Evidence revision must equal result.revision.")

                if not isinstance(e_ref, str) or not e_ref.strip():
                    add_error("invalid_path", f"{ev_loc}.reference", "Evidence reference must be a non-blank string.")
                else:
                    # E1 durable check on every stage
                    if not is_durable_evidence_path(e_ref):
                        add_error("evidence_not_durable", f"{ev_loc}.reference", "Evidence reference is not a durable path.")
                    resolved_p, err = resolve_bounded_path(project_root, e_ref)
                    if err:
                        add_error("boundary_violation", f"{ev_loc}.reference", f"Evidence reference violates boundary: {err}")
                    elif resolved_p is None or not resolved_p.is_file():
                        add_error("file_not_found", f"{ev_loc}.reference", "Evidence file does not exist.")
                    elif isinstance(e_sha, str) and re.match(r"^[0-9a-f]{64}$", e_sha.lower()):
                        try:
                            actual_hash = compute_sha256(resolved_p)
                            if actual_hash != e_sha.lower():
                                add_error("evidence_hash_mismatch", f"{ev_loc}.sha256", "Evidence file content does not match recorded sha256.")
                        except OSError:
                            add_error("file_read_error", f"{ev_loc}.reference", "Failed to read evidence file.")
    return ev_data, seen_ev_criterion_ids


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
        "result",
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

    baseline_revision = _check_baseline(contract_data, project_root, stage, add_error, add_warning)
    _check_documents(contract_data, project_root, stage, add_error, add_warning)
    known_ac_ids = _check_acceptance_criteria(contract_data, project_root, stage, add_error, add_warning)
    op_risk, op_action, op_target, op_revision, op_scope = _check_operation(contract_data, project_root, stage, add_error, add_warning, baseline_revision)
    _check_approval(contract_data, project_root, stage, add_error, add_warning, op_risk, op_action, op_target, op_revision, op_scope)
    result_revision = _check_result(contract_data, project_root, stage, add_error, add_warning, baseline_revision)
    ev_data, seen_ev_criterion_ids = _check_evidence(contract_data, project_root, stage, add_error, add_warning, known_ac_ids, result_revision)

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
