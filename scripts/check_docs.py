"""Documentation Quality and Workflow Transition Gate for Deterministic Agentic Workflows.

Zero-dependency Python stdlib read-only validation module.
Verifies document workflow transition fact records against rubric criteria and evidence sources.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
from typing import Any

try:
    from scripts.daw_common import (
        DuplicateKeyError,
        build_result,
        compute_sha256,
        has_errors,
        is_durable_evidence_path,
        is_safe_relative_path,
        make_error as _make_error,
        make_warning as _make_warning,
        parse_strict_json,
        resolve_bounded_path,
    )
except ImportError:
    from daw_common import (  # type: ignore[import-not-found]
        DuplicateKeyError,
        build_result,
        compute_sha256,
        has_errors,
        is_durable_evidence_path,
        is_safe_relative_path,
        make_error as _make_error,
        make_warning as _make_warning,
        parse_strict_json,
        resolve_bounded_path,
    )

SCHEMA_VERSION = 1

CANONICAL_KINDS = (
    "blueprint",
    "brd",
    "prd",
    "erd",
    "frd",
    "techstack",
    "design",
    "wireframe",
    "ui-ux",
    "security",
    "qa",
    "deployment",
    "runbook",
    "roadmap",
)

ALLOWED_TRANSITIONS = {
    "intake-authoring": ("intake", "authoring"),
    "authoring-review": ("authoring", "review"),
    "review-ready": ("review", "ready"),
    "review-rework": ("review", "rework"),
    "rework-review": ("rework", "review"),
}

COMMON_CRITERIA_IDS = ("DQ-01", "DQ-02", "DQ-03", "DQ-04", "DQ-05")

DOCS_LIMITATIONS = [
    "Evidence eligibility and structural verification only; does not certify semantic truth, completeness, or real-world operational accuracy.",
    "Source quote verification checks line-exact presence only at validation time; does not evaluate contextual meaning or prevent TOCTOU modifications.",
    "Reviewer and approval attestations capture opaque references only; independent human comprehension and authorization remain unexercised.",
    "Validator is read-only and does not persist state; parent workflow must verify transition provenance and record actual state changes.",
    "Durable-evidence check uses a deterministic path-segment denylist (tmp/temp/.tmp/scratch/.cache, __pycache__, and dot-prefixed segments except .github); the validator cannot call git, so it cannot detect gitignored paths that are not on this list.",
    "Validator never authenticates reviewer identity; reviewer independence is checked only by exact stripped casefold comparison of reviewer id against reviewer author_id, and agent-kind review attestation is flagged rather than certified.",
]


def _read_rubric_object(
    rubric_path: pathlib.Path, findings: list[dict[str, str]]
) -> dict[str, Any] | None:
    rubric_label = "references/document-quality-rubric.json"
    try:
        if not rubric_path.is_file():
            findings.append(
                _make_error("rubric_missing", rubric_label, "Rubric file does not exist or is not a regular file.")
            )
            return None
    except (OSError, RuntimeError):
        findings.append(
            _make_error("rubric_missing", rubric_label, "Rubric file cannot be accessed or is not a regular file.")
        )
        return None
    try:
        raw_text = rubric_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError, RuntimeError):
        findings.append(
            _make_error("rubric_unreadable", rubric_label, "Rubric file cannot be read or is not valid UTF-8.")
        )
        return None
    try:
        rubric = parse_strict_json(raw_text)
    except (json.JSONDecodeError, DuplicateKeyError, RecursionError, ValueError):
        findings.append(
            _make_error("rubric_malformed", rubric_label, "Rubric file contains malformed or non-strict JSON.")
        )
        return None
    if not isinstance(rubric, dict):
        findings.append(_make_error("rubric_invalid_type", rubric_label, "Rubric root must be a JSON object."))
        return None
    return rubric


def _validate_rubric_top_level(rubric: dict[str, Any], findings: list[dict[str, str]]) -> None:
    allowed_top_keys = {"schema_version", "common", "kinds"}
    actual_top_keys = set(rubric.keys())
    for k in sorted(actual_top_keys - allowed_top_keys):
        findings.append(_make_error("rubric_extra_key", k, f"Unexpected top-level key '{k}' in rubric registry."))
    for k in sorted(allowed_top_keys - actual_top_keys):
        findings.append(
            _make_error("rubric_missing_key", k, f"Missing required top-level key '{k}' in rubric registry.")
        )
    if "schema_version" in rubric:
        schema_ver = rubric["schema_version"]
        if isinstance(schema_ver, bool) or not isinstance(schema_ver, int) or schema_ver != SCHEMA_VERSION:
            findings.append(
                _make_error(
                    "rubric_invalid_schema_version",
                    "schema_version",
                    f"Rubric schema_version must be integer {SCHEMA_VERSION}.",
                )
            )


def _validate_rubric_criteria_list(
    items: Any,
    *,
    path_prefix: str,
    expected_count: int,
    expected_ids: set[str],
    is_common: bool,
    kind_name: str = "",
    findings: list[dict[str, str]],
) -> None:
    if is_common:
        missing_code = "rubric_missing_common"
        missing_msg = "Rubric must contain a 'common' criteria array."
        count_code = "rubric_common_count_invalid"
        count_msg = f"Common criteria must contain exactly {expected_count} items, found {{count}}."
        code_prefix = "rubric_common"
        item_label = "Common item"
        criterion_desc = "common criterion"
        mismatch_code = "rubric_common_mismatch"
        mismatch_msg = "Common criteria IDs do not match the expected set."
    else:
        missing_code = "rubric_kind_missing"
        missing_msg = f"Kind '{kind_name}' criteria must be an array."
        count_code = "rubric_kind_count_invalid"
        count_msg = f"Kind '{kind_name}' criteria must contain exactly {expected_count} items, found {{count}}."
        code_prefix = "rubric_kind"
        item_label = "Criterion item"
        criterion_desc = f"kind '{kind_name}' criterion"
        mismatch_code = "rubric_kind_ids_mismatch"
        mismatch_msg = f"Kind '{kind_name}' criteria IDs do not match expected criteria."

    if not isinstance(items, list):
        findings.append(_make_error(missing_code, path_prefix, missing_msg))
        return
    if len(items) != expected_count:
        findings.append(_make_error(count_code, path_prefix, count_msg.format(count=len(items))))

    found_ids: list[str] = []
    seen_ids: set[str] = set()
    for idx, item in enumerate(items):
        item_path = f"{path_prefix}[{idx}]"
        if not isinstance(item, dict):
            findings.append(_make_error(f"{code_prefix}_item_invalid", item_path, f"{item_label} must be an object."))
            continue
        item_keys = set(item.keys())
        for ek in sorted(item_keys - {"id", "question"}):
            findings.append(
                _make_error(
                    f"{code_prefix}_item_extra_key",
                    f"{item_path}.{ek}",
                    f"Unexpected key '{ek}' in {criterion_desc}.",
                )
            )
        for mk in sorted({"id", "question"} - item_keys):
            findings.append(
                _make_error(
                    f"{code_prefix}_item_missing_key",
                    f"{item_path}.{mk}",
                    f"Missing required key '{mk}' in {criterion_desc}.",
                )
            )
        if "id" in item:
            c_id = item["id"]
            if not isinstance(c_id, str):
                findings.append(
                    _make_error(f"{code_prefix}_id_invalid", f"{item_path}.id", f"{item_label} id must be a string.")
                )
            else:
                if c_id in seen_ids:
                    dup_msg = (
                        f"Duplicate common criterion ID '{c_id}'."
                        if is_common
                        else f"Duplicate criterion ID '{c_id}' in kind '{kind_name}'."
                    )
                    findings.append(_make_error(f"{code_prefix}_id_duplicate", f"{item_path}.id", dup_msg))
                seen_ids.add(c_id)
                found_ids.append(c_id)
        if "question" in item:
            c_q = item["question"]
            if not isinstance(c_q, str) or not c_q.strip():
                q_msg = (
                    "Common item question must be a non-empty string."
                    if is_common
                    else f"Criterion question in kind '{kind_name}' must be a non-empty string."
                )
                findings.append(_make_error(f"{code_prefix}_question_invalid", f"{item_path}.question", q_msg))

    if set(found_ids) != expected_ids:
        findings.append(_make_error(mismatch_code, path_prefix, mismatch_msg))


def _validate_rubric_kinds(kinds: Any, findings: list[dict[str, str]]) -> None:
    if not isinstance(kinds, dict):
        findings.append(_make_error("rubric_missing_kinds", "kinds", "Rubric must contain a 'kinds' object."))
        return
    actual_kind_keys = set(kinds.keys())
    expected_kind_keys = set(CANONICAL_KINDS)
    for ek in sorted(actual_kind_keys - expected_kind_keys):
        findings.append(_make_error("rubric_unknown_kind", f"kinds.{ek}", f"Unknown kind '{ek}' in rubric registry."))
    for mk in sorted(expected_kind_keys - actual_kind_keys):
        findings.append(
            _make_error("rubric_missing_kind", f"kinds.{mk}", f"Missing required kind '{mk}' in rubric registry.")
        )
    for k in CANONICAL_KINDS:
        if k not in kinds:
            continue
        _validate_rubric_criteria_list(
            kinds[k],
            path_prefix=f"kinds.{k}",
            expected_count=3,
            expected_ids={f"{k}-01", f"{k}-02", f"{k}-03"},
            is_common=False,
            kind_name=k,
            findings=findings,
        )


def load_rubric(rubric_path: pathlib.Path) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    """Load and validate the document quality rubric registry strictly from the package root.

    Returns (rubric_dict, findings).
    """
    findings: list[dict[str, str]] = []
    rubric = _read_rubric_object(rubric_path, findings)
    if rubric is None:
        return None, findings

    _validate_rubric_top_level(rubric, findings)
    if "common" in rubric:
        _validate_rubric_criteria_list(
            rubric["common"],
            path_prefix="common",
            expected_count=5,
            expected_ids=set(COMMON_CRITERIA_IDS),
            is_common=True,
            findings=findings,
        )
    if "kinds" in rubric:
        _validate_rubric_kinds(rubric["kinds"], findings)

    if findings:
        return None, findings
    return rubric, []

def _is_safe_doc_path(p: str) -> bool:
    if not isinstance(p, str) or not p.strip():
        return False
    if "\0" in p or ":" in p or "\\" in p:
        return False
    return is_safe_relative_path(p)



def _validate_evidence(
    ev: Any,
    ev_path_label: str,
    project_root: pathlib.Path,
    findings: list[dict[str, str]],
) -> None:
    if not isinstance(ev, dict):
        findings.append(_make_error("evidence_invalid_type", ev_path_label, "Evidence must be an object."))
        return

    allowed_keys = {"path", "sha256", "start_line", "end_line", "quote"}
    for k in ev:
        if k not in allowed_keys:
            findings.append(
                _make_error(
                    "unexpected_evidence_field",
                    f"{ev_path_label}.{k}",
                    "Unexpected field in evidence.",
                )
            )

    p_str = ev.get("path")
    if not isinstance(p_str, str) or not p_str.strip():
        findings.append(
            _make_error(
                "evidence_path_missing",
                f"{ev_path_label}.path",
                "Evidence path must be a non-empty string.",
            )
        )
        return

    if not _is_safe_doc_path(p_str):
        findings.append(
            _make_error(
                "evidence_path_unsafe",
                f"{ev_path_label}.path",
                "Evidence path is unsafe or absolute.",
            )
        )
        return

    if not is_durable_evidence_path(p_str):
        findings.append(
            _make_error(
                "evidence_not_durable",
                f"{ev_path_label}.path",
                "Evidence path is not durable (ephemeral, cache, or dot-prefixed segment).",
            )
        )
        return

    try:
        resolved_path, err = resolve_bounded_path(project_root, p_str)
    except (OSError, RuntimeError):
        resolved_path, err = None, "fs_error"
    if err or resolved_path is None:
        findings.append(
            _make_error(
                "evidence_path_escapes",
                f"{ev_path_label}.path",
                "Evidence path escapes project root or cannot be resolved.",
            )
        )
        return

    try:
        if not resolved_path.is_file():
            findings.append(
                _make_error(
                    "evidence_file_missing",
                    f"{ev_path_label}.path",
                    "Evidence file does not exist or is not a regular file.",
                )
            )
            return
    except (OSError, RuntimeError):
        findings.append(
            _make_error(
                "evidence_file_io_error",
                f"{ev_path_label}.path",
                "I/O error accessing evidence file.",
            )
        )
        return

    expected_hash = ev.get("sha256")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64 or not all(c in "0123456789abcdef" for c in expected_hash):
        findings.append(
            _make_error(
                "evidence_hash_invalid",
                f"{ev_path_label}.sha256",
                "Evidence sha256 must be a 64-character lowercase hex string.",
            )
        )
        return

    try:
        actual_hash = compute_sha256(resolved_path)
    except (OSError, RuntimeError):
        findings.append(
            _make_error(
                "evidence_hash_io_error",
                f"{ev_path_label}.sha256",
                "Failed to compute SHA256 for evidence file.",
            )
        )
        return

    if actual_hash != expected_hash:
        findings.append(
            _make_error(
                "evidence_hash_mismatch",
                f"{ev_path_label}.sha256",
                "Evidence SHA256 mismatch: expected hash does not match computed file hash.",
            )
        )
        return

    try:
        content = resolved_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError, RuntimeError):
        findings.append(
            _make_error(
                "evidence_utf8_error",
                f"{ev_path_label}.path",
                "Evidence file cannot be read as UTF-8.",
            )
        )
        return

    start_line = ev.get("start_line")
    end_line = ev.get("end_line")
    quote = ev.get("quote")

    if isinstance(start_line, bool) or not isinstance(start_line, int) or start_line < 1:
        findings.append(
            _make_error(
                "evidence_start_line_invalid",
                f"{ev_path_label}.start_line",
                "start_line must be a positive 1-based integer.",
            )
        )
        return

    if isinstance(end_line, bool) or not isinstance(end_line, int) or end_line < start_line:
        findings.append(
            _make_error(
                "evidence_end_line_invalid",
                f"{ev_path_label}.end_line",
                "end_line must be an integer >= start_line.",
            )
        )
        return

    if not isinstance(quote, str) or not quote.strip():
        findings.append(
            _make_error(
                "evidence_quote_invalid",
                f"{ev_path_label}.quote",
                "Evidence quote must be a non-blank string.",
            )
        )
        return

    file_lines = content.splitlines()
    total_lines = len(file_lines)

    if start_line > total_lines or end_line > total_lines:
        findings.append(
            _make_error(
                "evidence_lines_out_of_bounds",
                f"{ev_path_label}",
                "Evidence line range exceeds total file lines.",
            )
        )
        return

    expected_quote = "\n".join(file_lines[start_line - 1 : end_line])
    if quote != expected_quote:
        findings.append(
            _make_error(
                "evidence_quote_mismatch",
                f"{ev_path_label}.quote",
                "Evidence quote does not match exact content of file at specified lines.",
            )
        )


def _load_docs_inputs(
    record_path: pathlib.Path,
    project_root: pathlib.Path,
    transition: str,
    findings: list[dict[str, str]],
) -> tuple[pathlib.Path, dict[str, Any]] | None:
    try:
        resolved_proj_root = project_root.resolve()
        if not resolved_proj_root.is_dir():
            findings.append(_make_error("project_root_not_dir", str(project_root), "Project root is not a valid directory."))
            return None
    except (OSError, RuntimeError, ValueError):
        findings.append(_make_error("project_root_error", str(project_root), "Cannot resolve project root directory."))
        return None

    record_path_str = str(record_path)
    anchor = record_path.anchor if hasattr(record_path, "anchor") else pathlib.Path(record_path_str).anchor
    tail = record_path_str[len(anchor):] if record_path.is_absolute() else record_path_str
    if "\0" in record_path_str or ":" in tail or (not record_path.is_absolute() and "\\" in record_path_str):
        code = "record_path_outside_root" if record_path.is_absolute() else "record_path_escapes"
        findings.append(_make_error(code, record_path_str, "Record path escapes project root or is invalid."))
        return None

    if not record_path.is_absolute():
        try:
            rec_bound, rec_err = resolve_bounded_path(resolved_proj_root, str(record_path))
        except (OSError, RuntimeError):
            rec_bound, rec_err = None, "fs_error"
        if rec_err or rec_bound is None:
            findings.append(_make_error("record_path_escapes", str(record_path), "Record path escapes project root or is invalid."))
            return None
        resolved_rec_path = rec_bound
    else:
        try:
            resolved_rec_path = record_path.resolve()
            resolved_rec_path.relative_to(resolved_proj_root)
        except (ValueError, OSError, RuntimeError):
            findings.append(_make_error("record_path_outside_root", str(record_path), "Record path is outside project root."))
            return None

    try:
        if not resolved_rec_path.is_file():
            findings.append(_make_error("record_file_missing", str(record_path), "Record file does not exist or is not a file."))
            return None
    except (OSError, RuntimeError):
        findings.append(_make_error("record_file_missing", str(record_path), "Record file does not exist or is not a file."))
        return None

    try:
        raw_text = resolved_rec_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError, RuntimeError):
        findings.append(_make_error("record_unreadable", str(record_path), "Record file cannot be read or is not valid UTF-8."))
        return None

    try:
        record = parse_strict_json(raw_text)
    except (json.JSONDecodeError, DuplicateKeyError, RecursionError, ValueError):
        findings.append(_make_error("record_malformed_json", str(record_path), "Record file contains malformed JSON or duplicate keys."))
        return None

    if not isinstance(record, dict):
        findings.append(_make_error("record_not_object", "root", "Record root must be a JSON object."))
        return None

    if not isinstance(transition, str) or transition not in ALLOWED_TRANSITIONS:
        findings.append(
            _make_error(
                "invalid_cli_transition",
                "transition",
                f"CLI transition must be one of {sorted(ALLOWED_TRANSITIONS.keys())}.",
            )
        )
        return None

    return resolved_proj_root, record


def _validate_reviewer(reviewer: Any, transition: str, findings: list[dict[str, str]]) -> None:
    if isinstance(reviewer, str) or not isinstance(reviewer, dict):
        findings.append(
            _make_error(
                "invalid_reviewer",
                "reviewer",
                "reviewer must be an object with id, kind, and author_id for review exit transitions.",
            )
        )
        return

    allowed_reviewer_keys = {"id", "kind", "author_id"}
    for rk in reviewer:
        if rk not in allowed_reviewer_keys:
            findings.append(_make_error("unexpected_reviewer_field", f"reviewer.{rk}", "Unexpected field in reviewer object."))
    reviewer_id = reviewer.get("id")
    reviewer_kind = reviewer.get("kind")
    reviewer_author_id = reviewer.get("author_id")
    valid_reviewer_id = isinstance(reviewer_id, str) and bool(reviewer_id.strip())
    valid_author_id = isinstance(reviewer_author_id, str) and bool(reviewer_author_id.strip())
    if not valid_reviewer_id:
        findings.append(_make_error("invalid_reviewer", "reviewer.id", "reviewer.id must be a non-empty string."))
    if not valid_author_id:
        findings.append(_make_error("invalid_reviewer", "reviewer.author_id", "reviewer.author_id must be a non-empty string."))
    if reviewer_kind not in ("human", "agent"):
        findings.append(_make_error("invalid_reviewer", "reviewer.kind", "reviewer.kind must be 'human' or 'agent'."))
    if valid_reviewer_id and valid_author_id:
        if reviewer_id.strip().casefold() == reviewer_author_id.strip().casefold():
            findings.append(
                _make_error("reviewer_not_independent", "reviewer", "reviewer.id must differ from reviewer.author_id.")
            )
    if reviewer_kind == "agent" and transition == "review-ready":
        findings.append(
            _make_warning(
                "reviewer_agent_attestation",
                "reviewer",
                "reviewer.kind is 'agent' on review-ready; independent human review is recommended.",
            )
        )


def _validate_record_header(
    record: dict[str, Any], transition: str, findings: list[dict[str, str]]
) -> None:
    expected_edge = ALLOWED_TRANSITIONS[transition]
    is_review_exit = transition in ("review-ready", "review-rework")

    allowed_top_keys = {"schema_version", "transition", "objective", "scope", "documents"}
    if is_review_exit:
        allowed_top_keys.add("reviewer")

    for k in record:
        if k not in allowed_top_keys:
            findings.append(_make_error("unexpected_top_field", str(k), "Unexpected top-level field in record."))

    schema_ver = record.get("schema_version")
    if isinstance(schema_ver, bool) or not isinstance(schema_ver, int) or schema_ver != SCHEMA_VERSION:
        findings.append(_make_error("invalid_schema_version", "schema_version", f"schema_version must be integer {SCHEMA_VERSION}."))

    rec_trans = record.get("transition")
    if not isinstance(rec_trans, dict):
        findings.append(_make_error("invalid_transition_type", "transition", "transition must be an object with 'from' and 'to' fields."))
    else:
        for tk in rec_trans:
            if tk not in {"from", "to"}:
                findings.append(_make_error("unexpected_transition_field", f"transition.{tk}", "Unexpected field in transition object."))
        t_from = rec_trans.get("from")
        t_to = rec_trans.get("to")
        if not isinstance(t_from, str) or not isinstance(t_to, str) or (t_from, t_to) != expected_edge:
            findings.append(
                _make_error(
                    "transition_edge_mismatch",
                    "transition",
                    "Record transition edge does not match expected CLI transition edge.",
                )
            )

    obj = record.get("objective")
    if not isinstance(obj, str) or not obj.strip():
        findings.append(_make_error("invalid_objective", "objective", "objective must be a non-empty string."))

    scp = record.get("scope")
    if not isinstance(scp, str) or not scp.strip():
        findings.append(_make_error("invalid_scope", "scope", "scope must be a non-empty string."))

    if is_review_exit:
        _validate_reviewer(record.get("reviewer"), transition, findings)


def _resolve_expected_documents(
    expected_documents: list[str],
    resolved_proj_root: pathlib.Path,
    findings: list[dict[str, str]],
) -> set[str]:
    norm_expected: set[str] = set()
    if not isinstance(expected_documents, list) or not expected_documents:
        findings.append(_make_error("empty_expected_documents", "--documents", "Expected documents list must be non-empty."))
        return norm_expected
    for doc_arg in expected_documents:
        if not isinstance(doc_arg, str) or not doc_arg.strip():
            findings.append(_make_error("invalid_expected_document_path", "--documents", "Expected document path must be a non-empty string."))
            continue
        if not _is_safe_doc_path(doc_arg):
            findings.append(_make_error("unsafe_expected_document_path", "--documents", "Expected document path is unsafe or absolute."))
            continue
        norm_p = os.path.normpath(doc_arg).replace("\\", "/")
        if norm_p in norm_expected:
            findings.append(_make_error("duplicate_expected_documents", "--documents", "Duplicate expected document path."))
        norm_expected.add(norm_p)

        try:
            res_p, res_err = resolve_bounded_path(resolved_proj_root, doc_arg)
        except (OSError, RuntimeError):
            res_p, res_err = None, "fs_error"
        if res_err or res_p is None:
            findings.append(_make_error("expected_document_escapes", "--documents", "Expected document path escapes project root."))
    return norm_expected


def _validate_doc_target(
    doc: dict[str, Any],
    doc_label: str,
    resolved_target: pathlib.Path,
    resolved_proj_root: pathlib.Path,
    transition: str,
    findings: list[dict[str, str]],
) -> None:
    if transition == "intake-authoring":
        try:
            if resolved_target.exists() and not resolved_target.is_file():
                findings.append(_make_error("doc_target_not_regular_file", f"{doc_label}.path", "Intake document target exists but is not a regular file."))
            else:
                for parent in resolved_target.parents:
                    if parent == resolved_proj_root:
                        break
                    if parent.exists() and not parent.is_dir():
                        findings.append(_make_error("doc_target_not_regular_file", f"{doc_label}.path", "Intake document target parent is not a directory."))
                        break
        except (OSError, RuntimeError):
            findings.append(_make_error("doc_target_not_regular_file", f"{doc_label}.path", "Intake document target exists but is not a regular file."))
        return

    try:
        target_is_file = resolved_target.is_file()
    except (OSError, RuntimeError):
        target_is_file = False

    if not target_is_file:
        findings.append(_make_error("doc_target_missing", f"{doc_label}.path", "Document target file does not exist or is not a regular file."))
        return

    target_bytes: bytes | None = None
    try:
        target_bytes = resolved_target.read_bytes()
        target_bytes.decode("utf-8")
    except (OSError, UnicodeDecodeError, RuntimeError):
        target_bytes = None
        findings.append(_make_error("doc_target_unreadable_utf8", f"{doc_label}.path", "Document target cannot be read as UTF-8."))

    doc_sha256 = doc.get("sha256")
    if not isinstance(doc_sha256, str) or len(doc_sha256) != 64 or not all(c in "0123456789abcdef" for c in doc_sha256):
        findings.append(_make_error("doc_sha256_invalid", f"{doc_label}.sha256", "Document sha256 must be a 64-character lowercase hex string."))
    elif target_bytes is not None:
        actual_doc_sha = hashlib.sha256(target_bytes).hexdigest().lower()
        if actual_doc_sha != doc_sha256:
            findings.append(_make_error("doc_sha256_mismatch", f"{doc_label}.sha256", "Document SHA256 mismatch: expected hash does not match computed file hash."))


def _validate_single_check(
    chk: Any,
    chk_label: str,
    expected_criteria_ids: set[str],
    seen_criteria_ids: set[str],
    transition: str,
    is_review_exit: bool,
    resolved_proj_root: pathlib.Path,
    findings: list[dict[str, str]],
) -> bool:
    if not isinstance(chk, dict):
        findings.append(_make_error("check_not_object", chk_label, "Check must be an object."))
        return False

    allowed_chk_keys = {"id", "status", "rationale", "evidence"}
    if is_review_exit:
        allowed_chk_keys.add("decision")
    for k in chk:
        if k not in allowed_chk_keys:
            findings.append(_make_error("unexpected_check_field", f"{chk_label}.{k}", "Unexpected field in check."))

    c_id = chk.get("id")
    if not isinstance(c_id, str):
        findings.append(_make_error("check_id_invalid", f"{chk_label}.id", "Check id must be a string."))
        return False

    if c_id not in expected_criteria_ids:
        findings.append(_make_error("check_id_unknown", f"{chk_label}.id", f"Check id '{c_id}' is not in expected criteria set."))
    elif c_id in seen_criteria_ids:
        findings.append(_make_error("check_id_duplicate", f"{chk_label}.id", f"Duplicate check id '{c_id}' in checks."))
    seen_criteria_ids.add(c_id)

    status = chk.get("status")
    if not isinstance(status, str) or status not in ("pass", "not_applicable", "blocked"):
        findings.append(_make_error("check_status_invalid", f"{chk_label}.status", "Check status must be 'pass', 'not_applicable', or 'blocked'."))

    rationale = chk.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        findings.append(_make_error("check_rationale_empty", f"{chk_label}.rationale", f"Check rationale for '{c_id}' must be non-empty."))

    ev_list = chk.get("evidence")
    if not isinstance(ev_list, list) or len(ev_list) == 0:
        findings.append(_make_error("check_evidence_empty", f"{chk_label}.evidence", f"Check evidence for '{c_id}' must be a non-empty list of evidence items."))
    else:
        for e_idx, ev_item in enumerate(ev_list):
            _validate_evidence(ev_item, f"{chk_label}.evidence[{e_idx}]", resolved_proj_root, findings)

    if not is_review_exit:
        return False

    rejected = False
    decision = chk.get("decision")
    if not isinstance(decision, str) or decision not in ("accepted", "not_accepted"):
        findings.append(_make_error("check_decision_invalid", f"{chk_label}.decision", "Check decision must be 'accepted' or 'not_accepted'."))
        return False

    if decision == "not_accepted":
        rejected = True
    if status == "blocked" and decision == "accepted":
        findings.append(_make_error("blocked_check_accepted", f"{chk_label}", f"Criterion '{c_id}' has status 'blocked' and cannot be 'accepted'."))
    if transition == "review-ready":
        if decision != "accepted":
            findings.append(_make_error("review_ready_unaccepted_check", f"{chk_label}", f"review-ready transition requires all checks to be accepted, but '{c_id}' is '{decision}'."))
        if status == "blocked":
            findings.append(_make_error("review_ready_blocked_check", f"{chk_label}", f"review-ready transition requires all checks to be pass or not_applicable, but '{c_id}' is 'blocked'."))
    return rejected


def _validate_doc_checks(
    checks: Any,
    doc_label: str,
    kind: Any,
    transition: str,
    is_review_exit: bool,
    rubric: dict[str, Any] | None,
    resolved_proj_root: pathlib.Path,
    findings: list[dict[str, str]],
) -> bool:
    if not isinstance(checks, list):
        findings.append(_make_error("doc_checks_missing", f"{doc_label}.checks", "Document must have a 'checks' array."))
        return False
    if rubric is None or not isinstance(kind, str) or kind not in CANONICAL_KINDS:
        return False

    expected_criteria_ids = set(COMMON_CRITERIA_IDS) | {f"{kind}-01", f"{kind}-02", f"{kind}-03"}
    seen_criteria_ids: set[str] = set()
    has_rejected = False
    for c_idx, chk in enumerate(checks):
        if _validate_single_check(
            chk,
            f"{doc_label}.checks[{c_idx}]",
            expected_criteria_ids,
            seen_criteria_ids,
            transition,
            is_review_exit,
            resolved_proj_root,
            findings,
        ):
            has_rejected = True

    missing_criteria = expected_criteria_ids - seen_criteria_ids
    if missing_criteria:
        findings.append(_make_error("missing_checks", f"{doc_label}.checks", f"Missing checks for criteria: {sorted(missing_criteria)}."))
    return has_rejected


def _validate_record_documents(
    docs: list[Any],
    transition: str,
    rubric: dict[str, Any] | None,
    resolved_proj_root: pathlib.Path,
    norm_expected: set[str],
    findings: list[dict[str, str]],
) -> None:
    is_review_exit = transition in ("review-ready", "review-rework")
    allowed_doc_keys = (
        {"path", "kind", "audience", "reader_task", "sources"}
        if transition == "intake-authoring"
        else {"path", "kind", "audience", "reader_task", "sources", "sha256", "checks"}
    )
    record_doc_paths: set[str] = set()
    record_resolved_targets: set[pathlib.Path] = set()
    has_any_rejected_check = False

    for idx, doc in enumerate(docs):
        doc_label = f"documents[{idx}]"
        if not isinstance(doc, dict):
            findings.append(_make_error("doc_not_object", doc_label, "Document entry must be an object."))
            continue
        for k in doc:
            if k not in allowed_doc_keys:
                findings.append(_make_error("unexpected_doc_field", f"{doc_label}.{k}", "Unexpected field in document."))
        doc_path_str = doc.get("path")
        if not isinstance(doc_path_str, str) or not doc_path_str.strip():
            findings.append(_make_error("doc_path_missing", f"{doc_label}.path", "Document path must be a non-empty string."))
            continue
        if not _is_safe_doc_path(doc_path_str):
            findings.append(_make_error("doc_path_unsafe", f"{doc_label}.path", "Document path is unsafe or absolute."))
            continue

        norm_doc_path = os.path.normpath(doc_path_str).replace("\\", "/")
        if norm_doc_path in record_doc_paths:
            findings.append(_make_error("duplicate_doc_path", f"{doc_label}.path", "Duplicate document path in record."))
        record_doc_paths.add(norm_doc_path)

        try:
            resolved_target, target_err = resolve_bounded_path(resolved_proj_root, doc_path_str)
        except (OSError, RuntimeError):
            resolved_target, target_err = None, "fs_error"
        if target_err or resolved_target is None:
            findings.append(_make_error("doc_target_escapes", f"{doc_label}.path", "Document target path escapes project root."))
            continue
        if resolved_target in record_resolved_targets:
            findings.append(_make_error("doc_target_alias_collision", f"{doc_label}.path", "Document target resolves to an already used target."))
        record_resolved_targets.add(resolved_target)

        _validate_doc_target(doc, doc_label, resolved_target, resolved_proj_root, transition, findings)

        kind = doc.get("kind")
        if not isinstance(kind, str) or kind not in CANONICAL_KINDS:
            findings.append(_make_error("doc_kind_invalid", f"{doc_label}.kind", "Document kind must be one of canonical kinds."))
        aud = doc.get("audience")
        if not isinstance(aud, str) or not aud.strip():
            findings.append(_make_error("doc_audience_missing", f"{doc_label}.audience", "Document audience must be a non-empty string."))
        rt = doc.get("reader_task")
        if not isinstance(rt, str) or not rt.strip():
            findings.append(_make_error("doc_reader_task_missing", f"{doc_label}.reader_task", "Document reader_task must be a non-empty string."))

        sources = doc.get("sources")
        if not isinstance(sources, list) or len(sources) == 0:
            findings.append(_make_error("doc_sources_empty", f"{doc_label}.sources", "Document sources must be a non-empty list of evidence items."))
        else:
            for s_idx, src in enumerate(sources):
                _validate_evidence(src, f"{doc_label}.sources[{s_idx}]", resolved_proj_root, findings)

        if transition != "intake-authoring":
            if _validate_doc_checks(
                doc.get("checks"),
                doc_label,
                kind,
                transition,
                is_review_exit,
                rubric,
                resolved_proj_root,
                findings,
            ):
                has_any_rejected_check = True

    if transition == "review-rework" and not has_any_rejected_check:
        findings.append(_make_error("review_rework_no_rejected_checks", "documents", "review-rework transition requires at least one check with decision 'not_accepted'."))

    if norm_expected != record_doc_paths:
        diff_missing = sorted(norm_expected - record_doc_paths)
        diff_extra = sorted(record_doc_paths - norm_expected)
        msg_parts = []
        if diff_missing:
            msg_parts.append(f"missing expected documents: {diff_missing}")
        if diff_extra:
            msg_parts.append(f"unexpected record documents: {diff_extra}")
        findings.append(_make_error("document_set_mismatch", "documents", "; ".join(msg_parts)))


def validate_docs(
    record_path: pathlib.Path,
    project_root: pathlib.Path,
    transition: str,
    expected_documents: list[str],
) -> dict[str, Any]:
    """Validate a document quality workflow transition fact record against rubric criteria and evidence.

    Zero-dependency, read-only implementation.
    """
    transition_label = transition if isinstance(transition, str) else "unknown"
    findings: list[dict[str, str]] = []
    loaded = _load_docs_inputs(record_path, project_root, transition, findings)
    if loaded is not None:
        resolved_proj_root, record = loaded
        _validate_record_header(record, transition, findings)
        norm_expected = _resolve_expected_documents(expected_documents, resolved_proj_root, findings)

        pkg_root = pathlib.Path(__file__).resolve().parent.parent
        rubric, rubric_findings = load_rubric(pkg_root / "references" / "document-quality-rubric.json")
        if rubric_findings:
            findings.extend(rubric_findings)

        docs = record.get("documents")
        if not isinstance(docs, list) or not docs:
            findings.append(_make_error("invalid_documents_array", "documents", "documents must be a non-empty array."))
        else:
            _validate_record_documents(docs, transition, rubric, resolved_proj_root, norm_expected, findings)

    return build_result(
        "docs",
        findings,
        DOCS_LIMITATIONS,
        schema_version=SCHEMA_VERSION,
        extra={"eligible": not has_errors(findings), "transition": transition_label},
    )
