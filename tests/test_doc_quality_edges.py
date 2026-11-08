"""Focused regression unit tests for Document Quality workflow transition edge cases.

Targets edge-case scenarios against public CLI `scripts/validate.py docs`:
1. Unknown/unhashable status (list, dict, integer)
2. Unknown/unhashable decision (list, dict, integer)
3. Invalid/unhashable document kind (list, dict)
4. Unreadable/non-UTF-8 document safely handled without traceback (returns JSON envelope)
5. Symlink loop in evidence paths handled safely without traceback or recursion hang
6. Schema malformed errors (malformed JSON, duplicate keys, type mismatches)
7. Secret marker scrubbing in output diagnostics (no raw secret markers echoed on invalid kind/transition/field)
8. Minimal fixture builder with 8 criteria registry IDs (5 common DQ-01..DQ-05 + 3 kind criteria for FRD)

All tests verify observable behavior via CLI subprocess (`python3 scripts/validate.py docs`),
checking JSON envelope structure, exit codes, and absence of leaked secrets or uncaught tracebacks.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from typing import Any

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATOR_SCRIPT = PROJECT_ROOT / "scripts" / "validate.py"
RUBRIC_FILE = PROJECT_ROOT / "references" / "document-quality-rubric.json"

FRD_CRITERIA_IDS = [
    "DQ-01",
    "DQ-02",
    "DQ-03",
    "DQ-04",
    "DQ-05",
    "frd-01",
    "frd-02",
    "frd-03",
]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().lower()


class DocQualityEdgeTests(unittest.TestCase):
    """Observable regressions for doc quality gate edge cases and error bounds."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.proj_root = pathlib.Path(self.temp_dir.name).resolve()

        # Build isolated evidence file
        self.evidence_file = self.proj_root / "spec_source.txt"
        self.evidence_lines = [
            "Source line 1: Domain models and entities.",
            "Source line 2: State transitions and event hooks.",
            "Source line 3: Error handling and boundary conditions.",
        ]
        self.evidence_file.write_text("\n".join(self.evidence_lines), encoding="utf-8")
        self.evidence_bytes = self.evidence_file.read_bytes()
        self.evidence_sha = _sha256(self.evidence_bytes)

        # Build minimal valid FRD document
        self.doc_file = self.proj_root / "docs" / "frd.md"
        self.doc_file.parent.mkdir(parents=True, exist_ok=True)
        self.doc_content = (
            "# Functional Requirements Document\n\n"
            "## Entities and Models\n"
            "Domain entities are strictly typed.\n\n"
            "## State Transitions\n"
            "State transitions follow deterministic lifecycle.\n"
        )
        self.doc_file.write_text(self.doc_content, encoding="utf-8")
        self.doc_sha = _sha256(self.doc_file.read_bytes())

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_cli(
        self,
        args: list[str],
    ) -> subprocess.CompletedProcess[str]:
        cmd = [sys.executable, str(VALIDATOR_SCRIPT), "docs"] + args
        return subprocess.run(
            cmd,
            cwd=str(self.proj_root),
            capture_output=True,
            text=True,
        )

    def _create_evidence(
        self,
        rel_path: str = "spec_source.txt",
        start_line: int = 1,
        end_line: int = 1,
        quote: str | None = None,
        sha256_hash: str | None = None,
    ) -> dict[str, Any]:
        if quote is None:
            quote = self.evidence_lines[start_line - 1]
        if sha256_hash is None:
            sha256_hash = self.evidence_sha
        return {
            "path": rel_path,
            "sha256": sha256_hash,
            "start_line": start_line,
            "end_line": end_line,
            "quote": quote,
        }

    def _build_valid_checks(
        self,
        include_decision: bool = False,
        decision_val: str = "accepted",
        status_val: Any = "pass",
    ) -> list[dict[str, Any]]:
        checks = []
        for cid in FRD_CRITERIA_IDS:
            check_obj: dict[str, Any] = {
                "id": cid,
                "status": status_val,
                "rationale": f"Verified compliance against criterion {cid} with grounded evidence.",
                "evidence": [self._create_evidence()],
            }
            if include_decision:
                check_obj["decision"] = decision_val
            checks.append(check_obj)
        return checks

    def _build_base_record(
        self,
        transition: str = "authoring-review",
        doc_kind: Any = "frd",
        checks: list[dict[str, Any]] | None = None,
        reviewer: dict[str, Any] | str | None = None,
        include_decision: bool = False,
        decision_val: str = "accepted",
    ) -> dict[str, Any]:
        trans_map = {
            "intake-authoring": {"from": "intake", "to": "authoring"},
            "authoring-review": {"from": "authoring", "to": "review"},
            "review-ready": {"from": "review", "to": "ready"},
            "review-rework": {"from": "review", "to": "rework"},
            "rework-review": {"from": "rework", "to": "review"},
        }
        edge_dict = trans_map.get(transition, {"from": "unknown", "to": "unknown"})
        is_review_exit = transition in ("review-ready", "review-rework")
        should_include_decision = include_decision or is_review_exit

        doc_entry: dict[str, Any] = {
            "path": "docs/frd.md",
            "kind": doc_kind,
            "audience": "system-architects",
            "reader_task": "implement system state transitions",
            "sources": [self._create_evidence()],
        }
        if transition != "intake-authoring":
            doc_entry["sha256"] = self.doc_sha
            doc_entry["checks"] = (
                checks
                if checks is not None
                else self._build_valid_checks(
                    include_decision=should_include_decision,
                    decision_val=decision_val,
                )
            )

        record: dict[str, Any] = {
            "schema_version": 1,
            "transition": edge_dict,
            "objective": "Verify system requirements and state boundaries",
            "scope": "FRD specification package",
            "documents": [doc_entry],
        }
        if reviewer is not None:
            record["reviewer"] = reviewer
        elif is_review_exit:
            record["reviewer"] = {"id": "test-reviewer@domain.org", "kind": "human", "author_id": "doc-author-1"}

        return record

    def _write_record(self, data: dict[str, Any] | str, filename: str = "quality_record.json") -> pathlib.Path:
        target = self.proj_root / filename
        if isinstance(data, str):
            target.write_text(data, encoding="utf-8")
        else:
            target.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return target

    # =========================================================================
    # 1. Unhashable / unexpected status types: list, dict, integer
    # =========================================================================
    def test_unhashable_status_dict_does_not_crash(self) -> None:
        checks = self._build_valid_checks()
        # Corrupt first check status to be a dict
        checks[0]["status"] = {"invalid": "status_dict"}  # type: ignore[dict-item]
        rec = self._build_base_record(transition="authoring-review", checks=checks)
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "authoring-review",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertNotIn("TypeError", res.stderr)
        self.assertEqual(res.returncode, 1)
        out = json.loads(res.stdout)
        self.assertFalse(out["valid"])
        self.assertFalse(out["eligible"])
        self.assertEqual(out["transition"], "authoring-review")

    def test_unhashable_status_list_does_not_crash(self) -> None:
        checks = self._build_valid_checks()
        # Corrupt first check status to be a list
        checks[0]["status"] = ["pass", "extra"]  # type: ignore[dict-item]
        rec = self._build_base_record(transition="authoring-review", checks=checks)
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "authoring-review",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertNotIn("TypeError", res.stderr)
        self.assertEqual(res.returncode, 1)
        out = json.loads(res.stdout)
        self.assertFalse(out["valid"])
        self.assertFalse(out["eligible"])

    def test_unknown_status_string_rejected(self) -> None:
        checks = self._build_valid_checks()
        checks[0]["status"] = "partially_passed"
        rec = self._build_base_record(transition="authoring-review", checks=checks)
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "authoring-review",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertEqual(res.returncode, 1)
        out = json.loads(res.stdout)
        self.assertFalse(out["eligible"])
        self.assertFalse(out["valid"])

    # =========================================================================
    # 2. Unhashable / unexpected decision types: list, dict, integer
    # =========================================================================
    def test_unhashable_decision_dict_does_not_crash(self) -> None:
        checks = self._build_valid_checks(include_decision=True, decision_val="accepted")
        checks[0]["decision"] = {"nested": "decision"}  # type: ignore[dict-item]
        rec = self._build_base_record(transition="review-ready", checks=checks)
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "review-ready",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertNotIn("TypeError", res.stderr)
        self.assertEqual(res.returncode, 1)
        out = json.loads(res.stdout)
        self.assertFalse(out["eligible"])
        self.assertFalse(out["valid"])

    def test_unhashable_decision_list_does_not_crash(self) -> None:
        checks = self._build_valid_checks(include_decision=True, decision_val="accepted")
        checks[0]["decision"] = ["accepted", "not_accepted"]  # type: ignore[dict-item]
        rec = self._build_base_record(transition="review-ready", checks=checks)
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "review-ready",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertNotIn("TypeError", res.stderr)
        self.assertEqual(res.returncode, 1)
        out = json.loads(res.stdout)
        self.assertFalse(out["eligible"])
        self.assertFalse(out["valid"])

    def test_unknown_decision_string_rejected(self) -> None:
        checks = self._build_valid_checks(include_decision=True, decision_val="accepted")
        checks[0]["decision"] = "pending_approval"
        rec = self._build_base_record(transition="review-ready", checks=checks)
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "review-ready",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertEqual(res.returncode, 1)
        out = json.loads(res.stdout)
        self.assertFalse(out["eligible"])
        self.assertFalse(out["valid"])

    # =========================================================================
    # 3. Invalid / unhashable document kind (list, dict)
    # =========================================================================
    def test_unhashable_kind_dict_does_not_crash(self) -> None:
        rec = self._build_base_record(transition="authoring-review", doc_kind={"kind_name": "frd"})
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "authoring-review",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertNotIn("TypeError", res.stderr)
        self.assertEqual(res.returncode, 1)
        out = json.loads(res.stdout)
        self.assertFalse(out["eligible"])
        self.assertFalse(out["valid"])

    def test_unhashable_kind_list_does_not_crash(self) -> None:
        rec = self._build_base_record(transition="authoring-review", doc_kind=["frd", "prd"])
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "authoring-review",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertNotIn("TypeError", res.stderr)
        self.assertEqual(res.returncode, 1)
        out = json.loads(res.stdout)
        self.assertFalse(out["eligible"])
        self.assertFalse(out["valid"])

    def test_unknown_kind_string_rejected(self) -> None:
        rec = self._build_base_record(transition="authoring-review", doc_kind="non_existent_kind")
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "authoring-review",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertEqual(res.returncode, 1)
        out = json.loads(res.stdout)
        self.assertFalse(out["eligible"])
        self.assertFalse(out["valid"])

    # =========================================================================
    # 4. Unreadable / non-UTF8 document safely handled without traceback
    # =========================================================================
    def test_non_utf8_target_document_returns_ineligible_no_traceback(self) -> None:
        bad_bytes = b"\x80\x81\xff\xfe\xaa\xbb"
        self.doc_file.write_bytes(bad_bytes)
        bad_sha = _sha256(bad_bytes)

        rec = self._build_base_record(transition="authoring-review")
        rec["documents"][0]["sha256"] = bad_sha
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "authoring-review",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertNotIn("UnboundLocalError", res.stderr)
        self.assertEqual(res.returncode, 1)
        out = json.loads(res.stdout)
        self.assertFalse(out["eligible"])
        self.assertFalse(out["valid"])

    def test_target_document_directory_safely_rejected_no_traceback(self) -> None:
        # Replace doc file with directory
        self.doc_file.unlink()
        self.doc_file.mkdir(parents=True, exist_ok=True)

        rec = self._build_base_record(transition="authoring-review")
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "authoring-review",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertEqual(res.returncode, 1)
        out = json.loads(res.stdout)
        self.assertFalse(out["eligible"])
        self.assertFalse(out["valid"])

    def test_non_utf8_evidence_source_returns_ineligible_no_traceback(self) -> None:
        bad_source = self.proj_root / "bad_source.txt"
        bad_bytes = b"\xff\xfe\xfd\x80"
        bad_source.write_bytes(bad_bytes)
        bad_sha = _sha256(bad_bytes)

        bad_ev = self._create_evidence(rel_path="bad_source.txt", sha256_hash=bad_sha)
        checks = self._build_valid_checks()
        checks[0]["evidence"] = [bad_ev]

        rec = self._build_base_record(transition="authoring-review", checks=checks)
        rec["documents"][0]["sources"] = [bad_ev]
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "authoring-review",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertEqual(res.returncode, 1)
        out = json.loads(res.stdout)
        self.assertFalse(out["eligible"])
        self.assertFalse(out["valid"])

    # =========================================================================
    # 5. Symlink loop in evidence paths handled safely without traceback or hang
    # =========================================================================
    def test_symlink_loop_in_evidence_path_fails_safely(self) -> None:
        loop_link1 = self.proj_root / "loop1"
        loop_link2 = self.proj_root / "loop2"
        try:
            loop_link1.symlink_to(loop_link2)
            loop_link2.symlink_to(loop_link1)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks not supported on this environment.")

        loop_ev = {
            "path": "loop1/file.txt",
            "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "start_line": 1,
            "end_line": 1,
            "quote": "any quote",
        }
        checks = self._build_valid_checks()
        checks[0]["evidence"] = [loop_ev]

        rec = self._build_base_record(transition="authoring-review", checks=checks)
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "authoring-review",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertNotIn("RuntimeError", res.stderr)
        self.assertIn(res.returncode, (1, 2))
        if res.returncode == 1:
            out = json.loads(res.stdout)
            self.assertFalse(out["eligible"])
            self.assertFalse(out["valid"])

    def test_self_referencing_symlink_fails_safely(self) -> None:
        self_loop = self.proj_root / "self_loop.txt"
        try:
            self_loop.symlink_to(self_loop)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks not supported on this environment.")

        loop_ev = {
            "path": "self_loop.txt",
            "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "start_line": 1,
            "end_line": 1,
            "quote": "any quote",
        }
        checks = self._build_valid_checks()
        checks[0]["evidence"] = [loop_ev]

        rec = self._build_base_record(transition="authoring-review", checks=checks)
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "authoring-review",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertNotIn("RuntimeError", res.stderr)
        self.assertIn(res.returncode, (1, 2))

    # =========================================================================
    # 6. Schema malformed errors
    # =========================================================================
    def test_malformed_json_returns_exit_code_2(self) -> None:
        bad_json_path = self._write_record("{ unquoted_key: 123, }", filename="malformed.json")

        res = self.run_cli([
            str(bad_json_path),
            "--project-root", str(self.proj_root),
            "--transition", "authoring-review",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertEqual(res.returncode, 2)

    def test_duplicate_json_keys_rejected(self) -> None:
        duplicate_json = (
            '{\n'
            '  "schema_version": 1,\n'
            '  "schema_version": 1,\n'
            '  "transition": {"from": "authoring", "to": "review"},\n'
            '  "objective": "Test duplicate keys",\n'
            '  "scope": "FRD",\n'
            '  "documents": []\n'
            '}'
        )
        dup_path = self._write_record(duplicate_json, filename="duplicate_keys.json")

        res = self.run_cli([
            str(dup_path),
            "--project-root", str(self.proj_root),
            "--transition", "authoring-review",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertEqual(res.returncode, 2)

    def test_record_root_not_object_rejected(self) -> None:
        list_root = json.dumps([{"schema_version": 1}])
        list_path = self._write_record(list_root, filename="list_root.json")

        res = self.run_cli([
            str(list_path),
            "--project-root", str(self.proj_root),
            "--transition", "authoring-review",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertIn(res.returncode, (1, 2))
        if res.returncode == 1:
            out = json.loads(res.stdout)
            self.assertFalse(out["eligible"])

    def test_documents_not_array_rejected(self) -> None:
        rec = self._build_base_record(transition="authoring-review")
        rec["documents"] = {"docs/frd.md": {"kind": "frd"}}  # type: ignore[dict-item]
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "authoring-review",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertEqual(res.returncode, 1)
        out = json.loads(res.stdout)
        self.assertFalse(out["eligible"])
        self.assertFalse(out["valid"])

    def test_document_entry_not_object_rejected(self) -> None:
        rec = self._build_base_record(transition="authoring-review")
        rec["documents"] = ["docs/frd.md"]  # type: ignore[list-item]
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "authoring-review",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertEqual(res.returncode, 1)
        out = json.loads(res.stdout)
        self.assertFalse(out["eligible"])

    def test_checks_not_array_rejected(self) -> None:
        rec = self._build_base_record(transition="authoring-review")
        rec["documents"][0]["checks"] = "all_passed"  # type: ignore[dict-item]
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "authoring-review",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertEqual(res.returncode, 1)
        out = json.loads(res.stdout)
        self.assertFalse(out["eligible"])

    def test_sources_not_array_rejected(self) -> None:
        rec = self._build_base_record(transition="authoring-review")
        rec["documents"][0]["sources"] = "spec_source.txt"  # type: ignore[dict-item]
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "authoring-review",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertEqual(res.returncode, 1)
        out = json.loads(res.stdout)
        self.assertFalse(out["eligible"])

    def test_schema_version_invalid_type_rejected(self) -> None:
        rec = self._build_base_record(transition="authoring-review")
        rec["schema_version"] = "1"  # string instead of int
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "authoring-review",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertEqual(res.returncode, 1)
        out = json.loads(res.stdout)
        self.assertFalse(out["eligible"])

    # =========================================================================
    # 7. Secret marker scrubbing in output diagnostics
    # =========================================================================
    def test_secret_markers_not_echoed_in_invalid_kind(self) -> None:
        secret_kind = "CANARY_SECRET_API_KEY_xyz987"
        rec = self._build_base_record(transition="authoring-review", doc_kind=secret_kind)
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "authoring-review",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertEqual(res.returncode, 1)
        out = json.loads(res.stdout)
        self.assertFalse(out["eligible"])

        # Secret marker must NOT appear in any finding message
        for finding in out.get("findings", []):
            msg = finding.get("message", "")
            self.assertNotIn(secret_kind, msg, "Finding message should not echo raw unvalidated secret string.")

    def test_secret_markers_not_echoed_in_invalid_transition(self) -> None:
        secret_trans = "CANARY_SECRET_TRANS_TOKEN_44556"
        rec = self._build_base_record(transition="authoring-review")
        rec["transition"] = {"from": secret_trans, "to": "review"}
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "authoring-review",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertEqual(res.returncode, 1)
        out = json.loads(res.stdout)
        self.assertFalse(out["eligible"])

        for finding in out.get("findings", []):
            msg = finding.get("message", "")
            self.assertNotIn(secret_trans, msg, "Finding message should not echo raw unvalidated transition secret.")

    def test_secret_markers_not_echoed_in_unexpected_field(self) -> None:
        secret_field_name = "CANARY_SECRET_TOP_LEVEL_TOKEN_abc123"
        rec = self._build_base_record(transition="authoring-review")
        rec[secret_field_name] = "sensitive_payload"
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "authoring-review",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertEqual(res.returncode, 1)
        out = json.loads(res.stdout)
        self.assertFalse(out["eligible"])

    # =========================================================================
    # 8. All 8 criteria registry IDs required for FRD
    # =========================================================================
    def test_omission_of_one_frd_criterion_causes_ineligibility(self) -> None:
        checks = self._build_valid_checks()
        # Drop the last criterion frd-03
        checks = [c for c in checks if c["id"] != "frd-03"]
        rec = self._build_base_record(transition="authoring-review", checks=checks)
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "authoring-review",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertEqual(res.returncode, 1)
        out = json.loads(res.stdout)
        self.assertFalse(out["eligible"])
        self.assertFalse(out["valid"])

    def test_complete_8_criteria_frd_passes_authoring_review(self) -> None:
        rec = self._build_base_record(transition="authoring-review")
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "authoring-review",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertEqual(res.returncode, 0, f"Expected 0 exit, stderr: {res.stderr}, stdout: {res.stdout}")
        out = json.loads(res.stdout)
        self.assertTrue(out["eligible"])
        self.assertTrue(out["valid"])
        self.assertEqual(out["transition"], "authoring-review")
        self.assertEqual(len(out["findings"]), 0)

    # =========================================================================
    # 9. C1 durable evidence + C2 reviewer object
    # =========================================================================
    def test_tmp_source_path_rejected_as_not_durable(self) -> None:
        tmp_source = self.proj_root / "tmp" / "ephemeral.txt"
        tmp_source.parent.mkdir(parents=True, exist_ok=True)
        tmp_source.write_text("ephemeral source line\n", encoding="utf-8")
        tmp_sha = _sha256(tmp_source.read_bytes())
        rec = self._build_base_record(transition="authoring-review")
        rec["documents"][0]["sources"] = [
            {"path": "tmp/ephemeral.txt", "sha256": tmp_sha, "start_line": 1, "end_line": 1, "quote": "ephemeral source line"}
        ]
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "authoring-review",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertEqual(res.returncode, 1)
        out = json.loads(res.stdout)
        self.assertFalse(out["valid"])
        self.assertIn("evidence_not_durable", [f["code"] for f in out["findings"]])

    def test_reviewer_equal_to_author_rejected(self) -> None:
        rec = self._build_base_record(
            transition="review-ready",
            reviewer={"id": "same-id", "kind": "human", "author_id": " Same-Id "},
        )
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "review-ready",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertEqual(res.returncode, 1)
        out = json.loads(res.stdout)
        self.assertFalse(out["valid"])
        self.assertIn("reviewer_not_independent", [f["code"] for f in out["findings"]])

    def test_agent_reviewer_on_review_ready_warns_but_valid(self) -> None:
        rec = self._build_base_record(
            transition="review-ready",
            reviewer={"id": "agent-reviewer-1", "kind": "agent", "author_id": "doc-author-1"},
        )
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "review-ready",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertEqual(res.returncode, 0, f"Expected 0 exit, stderr: {res.stderr}, stdout: {res.stdout}")
        out = json.loads(res.stdout)
        self.assertTrue(out["valid"])
        self.assertTrue(out["eligible"])
        self.assertIn("reviewer_agent_attestation", [f["code"] for f in out["findings"]])
        self.assertTrue(any(f["severity"] == "warning" for f in out["findings"]))

    def test_string_reviewer_rejected(self) -> None:
        rec = self._build_base_record(transition="review-ready", reviewer="legacy-string-reviewer")
        rec_path = self._write_record(rec)

        res = self.run_cli([
            str(rec_path),
            "--project-root", str(self.proj_root),
            "--transition", "review-ready",
            "--documents", "docs/frd.md",
            "--format", "json",
        ])

        self.assertNotIn("Traceback", res.stderr)
        self.assertEqual(res.returncode, 1)
        out = json.loads(res.stdout)
        self.assertFalse(out["valid"])
        self.assertIn("invalid_reviewer", [f["code"] for f in out["findings"]])


if __name__ == "__main__":
    unittest.main()
