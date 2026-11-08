"""Unit tests for Document Quality workflow transition gate CLI and validation logic.

Verifies `python3 scripts/validate.py docs` subprocess behavior and `scripts.doc_quality`
against the contract:
- Five transition edges: intake-authoring, authoring-review, review-ready, review-rework, rework-review
- Exit codes: 0 (eligible/valid), 1 (rejected/ineligible), 2 (malformed JSON / CLI syntax)
- Zero-dependency Python stdlib isolated project fixtures
- Hostile path escapes, symlink traversal, non-UTF8, non-regular files
- Strict evidence line bounds, exact quote verification, hash integrity
- Rubric coverage (5 common DQ-01..DQ-05 + 3 kind criteria)
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

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATOR_SCRIPT = PROJECT_ROOT / "scripts" / "validate.py"
RUBRIC_FILE = PROJECT_ROOT / "references" / "document-quality-rubric.json"

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

COMMON_IDS = ["DQ-01", "DQ-02", "DQ-03", "DQ-04", "DQ-05"]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().lower()


class DocQualityTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.proj_root = pathlib.Path(self.temp_dir.name).resolve()

        # Create standard evidence source
        self.source_file = self.proj_root / "brief.txt"
        self.source_lines = [
            "Project Brief Line 1: Goal statement and background.",
            "Project Brief Line 2: Scope definitions and boundaries.",
            "Project Brief Line 3: Acceptance criteria and constraints.",
            "Project Brief Line 4: Security and compliance requirements.",
            "Project Brief Line 5: Operational telemetry and runbooks.",
        ]
        self.source_content = "\n".join(self.source_lines) + "\n"
        self.source_file.write_text(self.source_content, encoding="utf-8")
        self.source_sha = _sha256(self.source_file.read_bytes())

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_cli(
        self,
        args: list[str],
        cwd: pathlib.Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        cmd = [sys.executable, str(VALIDATOR_SCRIPT), "docs"] + args
        return subprocess.run(
            cmd,
            cwd=str(cwd or self.proj_root),
            capture_output=True,
            text=True,
        )

    def create_evidence(
        self,
        rel_path: str = "brief.txt",
        start_line: int = 1,
        end_line: int = 2,
        quote: str | None = None,
        sha256_hash: str | None = None,
    ) -> dict[str, object]:
        if quote is None:
            quote = "\n".join(self.source_lines[start_line - 1 : end_line])
        if sha256_hash is None:
            sha256_hash = self.source_sha
        return {
            "path": rel_path,
            "sha256": sha256_hash,
            "start_line": start_line,
            "end_line": end_line,
            "quote": quote,
        }

    def make_checks(
        self,
        kind: str,
        status: str = "pass",
        decision: str | None = None,
        rationale: str = "Verified against project charter.",
        evidence: list[dict[str, object]] | None = None,
    ) -> list[dict[str, object]]:
        if evidence is None:
            evidence = [self.create_evidence()]

        checks = []
        criterion_ids = COMMON_IDS + [f"{kind}-01", f"{kind}-02", f"{kind}-03"]
        for c_id in criterion_ids:
            chk: dict[str, object] = {
                "id": c_id,
                "status": status,
                "rationale": rationale,
                "evidence": evidence,
            }
            if decision is not None:
                chk["decision"] = decision
            checks.append(chk)
        return checks


class TestDocQualityCLIValidScenarios(DocQualityTestBase):
    """Verifies successful eligibility and exit 0 for valid workflow transitions."""

    def test_valid_intake_absent_target(self) -> None:
        """Intake allows target document that does not yet exist on disk."""
        target_rel = "docs/architecture/system-blueprint.md"
        rec = {
            "schema_version": 1,
            "transition": {"from": "intake", "to": "authoring"},
            "objective": "Define system architecture and communication bounds.",
            "scope": "Frontend, backend gateway, and event bus.",
            "documents": [
                {
                    "path": target_rel,
                    "kind": "blueprint",
                    "audience": "System architects and integration engineers",
                    "reader_task": "Review component boundaries and RPC contracts.",
                    "sources": [self.create_evidence()],
                }
            ],
        }
        rec_path = self.proj_root / "intake-record.json"
        rec_path.write_text(json.dumps(rec), encoding="utf-8")

        res = self.run_cli(
            [
                "intake-record.json",
                "--project-root",
                str(self.proj_root),
                "--transition",
                "intake-authoring",
                "--documents",
                target_rel,
                "--format",
                "json",
            ]
        )
        self.assertEqual(res.returncode, 0, msg=f"CLI failed: {res.stderr}\n{res.stdout}")
        data = json.loads(res.stdout)
        self.assertTrue(data.get("valid"))
        self.assertTrue(data.get("eligible"))
        self.assertEqual(data.get("transition"), "intake-authoring")
        self.assertEqual(len(data.get("findings", [])), 0)

    def test_valid_erd_intake_and_authoring_review(self) -> None:
        """ERD transitions require DQ-01..05 plus erd-01..03 and remain eligible."""
        target_rel = "docs/erd.md"
        rec = {
            "schema_version": 1,
            "transition": {"from": "intake", "to": "authoring"},
            "objective": "Model persisted entities and relationships.",
            "scope": "Order lifecycle only.",
            "documents": [
                {
                    "path": target_rel,
                    "kind": "erd",
                    "audience": "Data architects and backend engineers",
                    "reader_task": "Review logical data model.",
                    "sources": [self.create_evidence()],
                }
            ],
        }
        rec_path = self.proj_root / "erd-intake.json"
        rec_path.write_text(json.dumps(rec), encoding="utf-8")

        res = self.run_cli([
            "erd-intake.json",
            "--project-root",
            str(self.proj_root),
            "--transition",
            "intake-authoring",
            "--documents",
            target_rel,
            "--format",
            "json",
        ])
        self.assertEqual(res.returncode, 0, msg=f"CLI failed: {res.stderr}\n{res.stdout}")
        self.assertTrue(json.loads(res.stdout).get("eligible"))

        doc_path = self.proj_root / target_rel
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text("# ERD\nLogical entities and relationships.\n", encoding="utf-8")
        doc_sha = _sha256(doc_path.read_bytes())
        checks = self.make_checks("erd", status="pass")

        rec = {
            "schema_version": 1,
            "transition": {"from": "authoring", "to": "review"},
            "objective": "Model persisted entities and relationships.",
            "scope": "Order lifecycle only.",
            "documents": [
                {
                    "path": target_rel,
                    "kind": "erd",
                    "audience": "Data architects and backend engineers",
                    "reader_task": "Review logical data model.",
                    "sources": [self.create_evidence()],
                    "sha256": doc_sha,
                    "checks": checks,
                }
            ],
        }
        rec_path = self.proj_root / "erd-review.json"
        rec_path.write_text(json.dumps(rec), encoding="utf-8")

        res = self.run_cli([
            "erd-review.json",
            "--project-root",
            str(self.proj_root),
            "--transition",
            "authoring-review",
            "--documents",
            target_rel,
            "--format",
            "json",
        ])
        self.assertEqual(res.returncode, 0, msg=f"CLI failed: {res.stderr}\n{res.stdout}")
        self.assertTrue(json.loads(res.stdout).get("eligible"))

    def test_foreign_criterion_rejected_for_erd(self) -> None:
        """Criteria belonging to another kind are rejected on an ERD document."""
        doc_rel = "docs/erd.md"
        doc_path = self.proj_root / doc_rel
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text("# ERD\n", encoding="utf-8")
        doc_sha = _sha256(doc_path.read_bytes())

        checks = self.make_checks("erd", status="pass")
        checks.append({
            "id": "frd-01",
            "status": "pass",
            "rationale": "Foreign criterion must not substitute for an ERD criterion.",
            "evidence": [self.create_evidence()],
        })

        rec = {
            "schema_version": 1,
            "transition": {"from": "authoring", "to": "review"},
            "objective": "Model persisted entities.",
            "scope": "Order lifecycle only.",
            "documents": [
                {
                    "path": doc_rel,
                    "kind": "erd",
                    "audience": "Data architects",
                    "reader_task": "Review data model.",
                    "sources": [self.create_evidence()],
                    "sha256": doc_sha,
                    "checks": checks,
                }
            ],
        }
        rec_path = self.proj_root / "erd-foreign.json"
        rec_path.write_text(json.dumps(rec), encoding="utf-8")

        res = self.run_cli([
            "erd-foreign.json",
            "--project-root",
            str(self.proj_root),
            "--transition",
            "authoring-review",
            "--documents",
            doc_rel,
            "--format",
            "json",
        ])
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        self.assertFalse(data.get("valid"))
        codes = [f["code"] for f in data["findings"]]
        self.assertIn("check_id_unknown", codes)

    def test_erd_missing_criterion_rejected(self) -> None:
        """An ERD record missing one erd criterion is rejected with missing_checks."""
        doc_rel = "docs/erd.md"
        doc_path = self.proj_root / doc_rel
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text("# ERD\n", encoding="utf-8")
        doc_sha = _sha256(doc_path.read_bytes())

        checks = [c for c in self.make_checks("erd", status="pass") if c["id"] != "erd-03"]

        rec = {
            "schema_version": 1,
            "transition": {"from": "authoring", "to": "review"},
            "objective": "Model persisted entities.",
            "scope": "Order lifecycle only.",
            "documents": [
                {
                    "path": doc_rel,
                    "kind": "erd",
                    "audience": "Data architects",
                    "reader_task": "Review data model.",
                    "sources": [self.create_evidence()],
                    "sha256": doc_sha,
                    "checks": checks,
                }
            ],
        }
        rec_path = self.proj_root / "erd-missing.json"
        rec_path.write_text(json.dumps(rec), encoding="utf-8")

        res = self.run_cli([
            "erd-missing.json",
            "--project-root",
            str(self.proj_root),
            "--transition",
            "authoring-review",
            "--documents",
            doc_rel,
            "--format",
            "json",
        ])
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        self.assertFalse(data.get("valid"))
        codes = [f["code"] for f in data["findings"]]
        self.assertIn("missing_checks", codes)

    def test_valid_authoring_to_review_with_blocked_status(self) -> None:
        """Authoring-review transition permits grounded blocked criteria as legitimate coverage."""
        doc_rel = "specs/prd.md"
        doc_path = self.proj_root / doc_rel
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text("# Product Requirements\nFeature specifications.\n", encoding="utf-8")
        doc_sha = _sha256(doc_path.read_bytes())

        checks = self.make_checks("prd", status="pass")
        # Set one check to blocked with grounded rationale and evidence
        checks[-1]["status"] = "blocked"
        checks[-1]["rationale"] = "External billing API spec is pending vendor release."

        rec = {
            "schema_version": 1,
            "transition": {"from": "authoring", "to": "review"},
            "objective": "Complete core requirements specification.",
            "scope": "Core payment flow.",
            "documents": [
                {
                    "path": doc_rel,
                    "kind": "prd",
                    "audience": "Product managers and engineers",
                    "reader_task": "Implement payment flow.",
                    "sources": [self.create_evidence()],
                    "sha256": doc_sha,
                    "checks": checks,
                }
            ],
        }
        rec_path = self.proj_root / "authoring-review-record.json"
        rec_path.write_text(json.dumps(rec), encoding="utf-8")

        res = self.run_cli(
            [
                str(rec_path),
                "--project-root",
                str(self.proj_root),
                "--transition",
                "authoring-review",
                "--documents",
                doc_rel,
                "--format",
                "json",
            ]
        )
        self.assertEqual(res.returncode, 0, msg=f"CLI stderr: {res.stderr}")
        data = json.loads(res.stdout)
        self.assertTrue(data.get("valid"))
        self.assertTrue(data.get("eligible"))

    def test_valid_review_ready_with_alias_filename_and_not_applicable(self) -> None:
        """review-ready succeeds with non-canonical filename (alias) and not_applicable checks."""
        # Using alias filename 'overview.md' with kind 'blueprint'
        doc_rel = "docs/overview.md"
        doc_path = self.proj_root / doc_rel
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text("# Overview\nHigh-level system topology.\n", encoding="utf-8")
        doc_sha = _sha256(doc_path.read_bytes())

        checks = self.make_checks("blueprint", status="pass", decision="accepted")
        # One check is not_applicable with attested rationale and grounded evidence
        checks[1]["status"] = "not_applicable"
        checks[1]["rationale"] = "Standalone deployment has no cross-service RPC contracts."

        rec = {
            "schema_version": 1,
            "transition": {"from": "review", "to": "ready"},
            "reviewer": "Security and Architecture Gate Reviewer",
            "objective": "Verify architectural readiness.",
            "scope": "System overview.",
            "documents": [
                {
                    "path": doc_rel,
                    "kind": "blueprint",
                    "audience": "Deployment team",
                    "reader_task": "Verify target architecture.",
                    "sources": [self.create_evidence()],
                    "sha256": doc_sha,
                    "checks": checks,
                }
            ],
        }
        rec_path = self.proj_root / "review-ready-record.json"
        rec_path.write_text(json.dumps(rec), encoding="utf-8")

        res = self.run_cli(
            [
                str(rec_path),
                "--project-root",
                str(self.proj_root),
                "--transition",
                "review-ready",
                "--documents",
                doc_rel,
                "--format",
                "text",
            ]
        )
        self.assertEqual(res.returncode, 0, msg=f"CLI failed: {res.stderr}\n{res.stdout}")
        self.assertIn("[VALID]", res.stdout)
        self.assertIn("Check: docs", res.stdout)

    def test_valid_review_rework_transition(self) -> None:
        """review-rework requires reviewer and at least one rejected check."""
        doc_rel = "qa.md"
        doc_path = self.proj_root / doc_rel
        doc_path.write_text("# QA Plan\nTesting scenarios.\n", encoding="utf-8")
        doc_sha = _sha256(doc_path.read_bytes())

        checks = self.make_checks("qa", status="pass", decision="accepted")
        checks[0]["decision"] = "not_accepted"
        checks[0]["rationale"] = "Test matrix lacks performance regression bounds."

        rec = {
            "schema_version": 1,
            "transition": {"from": "review", "to": "rework"},
            "reviewer": "Lead QA Engineer",
            "objective": "Review QA test coverage.",
            "scope": "E2E automated suite.",
            "documents": [
                {
                    "path": doc_rel,
                    "kind": "qa",
                    "audience": "QA and test automation engineers",
                    "reader_task": "Execute regression test suite.",
                    "sources": [self.create_evidence()],
                    "sha256": doc_sha,
                    "checks": checks,
                }
            ],
        }
        rec_path = self.proj_root / "review-rework-record.json"
        rec_path.write_text(json.dumps(rec), encoding="utf-8")

        res = self.run_cli(
            [
                str(rec_path),
                "--project-root",
                str(self.proj_root),
                "--transition",
                "review-rework",
                "--documents",
                doc_rel,
                "--format",
                "json",
            ]
        )
        self.assertEqual(res.returncode, 0, msg=f"CLI stderr: {res.stderr}")
        data = json.loads(res.stdout)
        self.assertTrue(data.get("valid"))
        self.assertTrue(data.get("eligible"))


class TestDocQualityIneligibleScenarios(DocQualityTestBase):
    """Verifies that evidence, rubric, or schema invalidities return exit code 1."""

    def test_omission_expected_document_set(self) -> None:
        """Discrepancy between CLI --documents and record documents fails with document_set_mismatch."""
        rec = {
            "schema_version": 1,
            "transition": {"from": "intake", "to": "authoring"},
            "objective": "Test omission.",
            "scope": "Single doc.",
            "documents": [
                {
                    "path": "docs/doc1.md",
                    "kind": "brd",
                    "audience": "Business leaders",
                    "reader_task": "Review outcomes.",
                    "sources": [self.create_evidence()],
                }
            ],
        }
        rec_path = self.proj_root / "rec.json"
        rec_path.write_text(json.dumps(rec), encoding="utf-8")

        # Expecting docs/doc1.md AND docs/doc2.md
        res = self.run_cli(
            [
                str(rec_path),
                "--project-root",
                str(self.proj_root),
                "--transition",
                "intake-authoring",
                "--documents",
                "docs/doc1.md",
                "docs/doc2.md",
                "--format",
                "json",
            ]
        )
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        self.assertFalse(data["valid"])
        codes = [f["code"] for f in data["findings"]]
        self.assertIn("document_set_mismatch", codes)

    def test_missing_criteria_in_checks(self) -> None:
        """Handoff / review checks missing common or kind criteria must be rejected."""
        doc_rel = "sec.md"
        doc_path = self.proj_root / doc_rel
        doc_path.write_text("# Security Spec\n", encoding="utf-8")
        doc_sha = _sha256(doc_path.read_bytes())

        # Only include 3 kind criteria, omitting all 5 common criteria
        partial_checks = [
            {
                "id": f"security-0{i}",
                "status": "pass",
                "rationale": "Addressed threat vector.",
                "evidence": [self.create_evidence()],
            }
            for i in (1, 2, 3)
        ]

        rec = {
            "schema_version": 1,
            "transition": {"from": "authoring", "to": "review"},
            "objective": "Security evaluation.",
            "scope": "Auth layer.",
            "documents": [
                {
                    "path": doc_rel,
                    "kind": "security",
                    "audience": "AppSec",
                    "reader_task": "Audit threat model.",
                    "sources": [self.create_evidence()],
                    "sha256": doc_sha,
                    "checks": partial_checks,
                }
            ],
        }
        rec_path = self.proj_root / "rec.json"
        rec_path.write_text(json.dumps(rec), encoding="utf-8")

        res = self.run_cli(
            [
                str(rec_path),
                "--project-root",
                str(self.proj_root),
                "--transition",
                "authoring-review",
                "--documents",
                doc_rel,
                "--format",
                "json",
            ]
        )
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        codes = [f["code"] for f in data["findings"]]
        self.assertIn("missing_checks", codes)

    def test_duplicate_and_unknown_criteria_ids(self) -> None:
        """Duplicate criterion IDs or unknown IDs not in rubric must be rejected."""
        doc_rel = "runbook.md"
        doc_path = self.proj_root / doc_rel
        doc_path.write_text("# Runbook\n", encoding="utf-8")
        doc_sha = _sha256(doc_path.read_bytes())

        checks = self.make_checks("runbook", status="pass")
        # Add duplicate DQ-01 and an unknown criterion
        checks.append({
            "id": "DQ-01",
            "status": "pass",
            "rationale": "Duplicate entry.",
            "evidence": [self.create_evidence()],
        })
        checks.append({
            "id": "UNKNOWN-99",
            "status": "pass",
            "rationale": "Invented criterion.",
            "evidence": [self.create_evidence()],
        })

        rec = {
            "schema_version": 1,
            "transition": {"from": "authoring", "to": "review"},
            "objective": "Runbook check.",
            "scope": "Incident recovery.",
            "documents": [
                {
                    "path": doc_rel,
                    "kind": "runbook",
                    "audience": "SRE",
                    "reader_task": "Execute failover.",
                    "sources": [self.create_evidence()],
                    "sha256": doc_sha,
                    "checks": checks,
                }
            ],
        }
        rec_path = self.proj_root / "rec.json"
        rec_path.write_text(json.dumps(rec), encoding="utf-8")

        res = self.run_cli(
            [
                str(rec_path),
                "--project-root",
                str(self.proj_root),
                "--transition",
                "authoring-review",
                "--documents",
                doc_rel,
                "--format",
                "json",
            ]
        )
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        self.assertFalse(data.get("valid"))
        self.assertFalse(data.get("eligible"))
        finding_paths = [f.get("path", "") for f in data.get("findings", [])]
        self.assertTrue(any("checks" in p and "id" in p for p in finding_paths))

    def test_stale_document_and_source_hashes(self) -> None:
        """Mismatched document hash and stale source evidence hash must be flagged."""
        doc_rel = "deployment.md"
        doc_path = self.proj_root / doc_rel
        doc_path.write_text("# Deployment Guide\n", encoding="utf-8")

        checks = self.make_checks("deployment", status="pass")
        # Tamper evidence SHA
        checks[0]["evidence"] = [
            self.create_evidence(sha256_hash="0000000000000000000000000000000000000000000000000000000000000000")
        ]

        rec = {
            "schema_version": 1,
            "transition": {"from": "authoring", "to": "review"},
            "objective": "Deployment validation.",
            "scope": "Production deployment.",
            "documents": [
                {
                    "path": doc_rel,
                    "kind": "deployment",
                    "audience": "DevOps",
                    "reader_task": "Deploy cluster.",
                    "sources": [self.create_evidence()],
                    # Wrong document hash
                    "sha256": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
                    "checks": checks,
                }
            ],
        }
        rec_path = self.proj_root / "rec.json"
        rec_path.write_text(json.dumps(rec), encoding="utf-8")

        res = self.run_cli(
            [
                str(rec_path),
                "--project-root",
                str(self.proj_root),
                "--transition",
                "authoring-review",
                "--documents",
                doc_rel,
                "--format",
                "json",
            ]
        )
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        codes = [f["code"] for f in data["findings"]]
        self.assertIn("doc_sha256_mismatch", codes)
        self.assertIn("evidence_hash_mismatch", codes)

    def test_false_quote_and_line_bounds(self) -> None:
        """Evidence line out of bounds, start > end, and altered quotes must fail."""
        doc_rel = "design.md"
        doc_path = self.proj_root / doc_rel
        doc_path.write_text("# Design Document\n", encoding="utf-8")
        doc_sha = _sha256(doc_path.read_bytes())

        # Test quote mismatch
        bad_quote_ev = self.create_evidence(start_line=1, end_line=1, quote="This text does not exist in brief.")

        # Test inverted bounds
        bad_bounds_ev = {
            "path": "brief.txt",
            "sha256": self.source_sha,
            "start_line": 4,
            "end_line": 2,  # end < start
            "quote": "Invalid bounds",
        }

        # Test line exceeding file length
        overflow_bounds_ev = {
            "path": "brief.txt",
            "sha256": self.source_sha,
            "start_line": 1,
            "end_line": 9999,
            "quote": "Exceeds total lines",
        }

        checks = self.make_checks("design", status="pass")
        checks[0]["evidence"] = [bad_quote_ev]
        checks[1]["evidence"] = [bad_bounds_ev]
        checks[2]["evidence"] = [overflow_bounds_ev]

        rec = {
            "schema_version": 1,
            "transition": {"from": "authoring", "to": "review"},
            "objective": "Architecture check.",
            "scope": "Component boundaries.",
            "documents": [
                {
                    "path": doc_rel,
                    "kind": "design",
                    "audience": "Engineers",
                    "reader_task": "Build subsystems.",
                    "sources": [self.create_evidence()],
                    "sha256": doc_sha,
                    "checks": checks,
                }
            ],
        }
        rec_path = self.proj_root / "rec.json"
        rec_path.write_text(json.dumps(rec), encoding="utf-8")

        res = self.run_cli(
            [
                str(rec_path),
                "--project-root",
                str(self.proj_root),
                "--transition",
                "authoring-review",
                "--documents",
                doc_rel,
                "--format",
                "json",
            ]
        )
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        self.assertFalse(data.get("valid"))
        self.assertFalse(data.get("eligible"))
        finding_paths = [f.get("path", "") for f in data.get("findings", [])]
        self.assertTrue(any("checks[0].evidence" in p for p in finding_paths))
        self.assertTrue(any("checks[1].evidence" in p for p in finding_paths))
        self.assertTrue(any("checks[2].evidence" in p for p in finding_paths))

    def test_missing_rationale_or_empty_evidence(self) -> None:
        """Every check must supply non-empty rationale and non-empty grounded evidence."""
        doc_rel = "roadmap.md"
        doc_path = self.proj_root / doc_rel
        doc_path.write_text("# Roadmap\nMilestones.\n", encoding="utf-8")
        doc_sha = _sha256(doc_path.read_bytes())

        checks = self.make_checks("roadmap", status="pass")
        # Empty rationale
        checks[0]["rationale"] = "   "
        # Empty evidence array
        checks[1]["evidence"] = []

        rec = {
            "schema_version": 1,
            "transition": {"from": "authoring", "to": "review"},
            "objective": "Roadmap check.",
            "scope": "Phase 1 deliverables.",
            "documents": [
                {
                    "path": doc_rel,
                    "kind": "roadmap",
                    "audience": "Stakeholders",
                    "reader_task": "Track timeline.",
                    "sources": [self.create_evidence()],
                    "sha256": doc_sha,
                    "checks": checks,
                }
            ],
        }
        rec_path = self.proj_root / "rec.json"
        rec_path.write_text(json.dumps(rec), encoding="utf-8")

        res = self.run_cli(
            [
                str(rec_path),
                "--project-root",
                str(self.proj_root),
                "--transition",
                "authoring-review",
                "--documents",
                doc_rel,
                "--format",
                "json",
            ]
        )
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        self.assertFalse(data.get("valid"))
        self.assertFalse(data.get("eligible"))
        finding_paths = [f.get("path", "") for f in data.get("findings", [])]
        self.assertTrue(any("checks[0].rationale" in p for p in finding_paths))
        self.assertTrue(any("checks[1].evidence" in p for p in finding_paths))

    def test_type_invalidation_bool_line_numbers_and_scalars(self) -> None:
        """Bools masquerading as ints in line numbers or schema_version must be rejected."""
        rec = {
            # schema_version as bool
            "schema_version": True,
            "transition": {"from": "intake", "to": "authoring"},
            "objective": "Type test.",
            "scope": "Validation bounds.",
            "documents": [
                {
                    "path": "docs/techstack.md",
                    "kind": "techstack",
                    "audience": "Platform team",
                    "reader_task": "Select tooling.",
                    "sources": [
                        {
                            "path": "brief.txt",
                            "sha256": self.source_sha,
                            "start_line": True,  # bool instead of int
                            "end_line": 2,
                            "quote": self.source_lines[0] + "\n" + self.source_lines[1],
                        }
                    ],
                }
            ],
        }
        rec_path = self.proj_root / "rec.json"
        rec_path.write_text(json.dumps(rec), encoding="utf-8")

        res = self.run_cli(
            [
                str(rec_path),
                "--project-root",
                str(self.proj_root),
                "--transition",
                "intake-authoring",
                "--documents",
                "docs/techstack.md",
                "--format",
                "json",
            ]
        )
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        codes = [f["code"] for f in data["findings"]]
        self.assertIn("invalid_schema_version", codes)
        self.assertIn("evidence_start_line_invalid", codes)

    def test_file_escape_and_symlink_boundaries(self) -> None:
        """Path traversal outside project root and escaping symlinks must be blocked."""
        outside_file = self.temp_dir.name + "/../outside.txt"

        # Evidence escaping via traversal
        escape_ev = {
            "path": "../outside.txt",
            "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "start_line": 1,
            "end_line": 1,
            "quote": "outside",
        }

        # Create symlink pointing outside
        secret_file = pathlib.Path(tempfile.gettempdir()) / "secret.txt"
        secret_file.write_text("classified data\n", encoding="utf-8")
        symlink_path = self.proj_root / "symlink_outside.txt"
        try:
            symlink_path.symlink_to(secret_file)
            has_symlinks = True
        except (OSError, NotImplementedError):
            has_symlinks = False

        sources = [escape_ev]
        if has_symlinks:
            sources.append({
                "path": "symlink_outside.txt",
                "sha256": _sha256(secret_file.read_bytes()),
                "start_line": 1,
                "end_line": 1,
                "quote": "classified data",
            })

        rec = {
            "schema_version": 1,
            "transition": {"from": "intake", "to": "authoring"},
            "objective": "Security path traversal test.",
            "scope": "Path containment.",
            "documents": [
                {
                    "path": "docs/frd.md",
                    "kind": "frd",
                    "audience": "Backend engineers",
                    "reader_task": "Implement endpoints.",
                    "sources": sources,
                }
            ],
        }
        rec_path = self.proj_root / "rec.json"
        rec_path.write_text(json.dumps(rec), encoding="utf-8")

        res = self.run_cli(
            [
                str(rec_path),
                "--project-root",
                str(self.proj_root),
                "--transition",
                "intake-authoring",
                "--documents",
                "docs/frd.md",
                "--format",
                "json",
            ]
        )
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        codes = [f["code"] for f in data["findings"]]
        self.assertTrue(any("escapes" in c or "unsafe" in c for c in codes))

    def test_directory_and_non_utf8_evidence(self) -> None:
        """Directory path or binary / non-UTF8 evidence files must be rejected safely."""
        sub_dir = self.proj_root / "subdir"
        sub_dir.mkdir(exist_ok=True)

        binary_file = self.proj_root / "binary.bin"
        binary_file.write_bytes(b"\x80\x81\xff\xfe\x00\x01\x02")

        dir_ev = {
            "path": "subdir",
            "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "start_line": 1,
            "end_line": 1,
            "quote": "directory",
        }
        bin_ev = {
            "path": "binary.bin",
            "sha256": _sha256(binary_file.read_bytes()),
            "start_line": 1,
            "end_line": 1,
            "quote": "binary",
        }

        rec = {
            "schema_version": 1,
            "transition": {"from": "intake", "to": "authoring"},
            "objective": "Binary & directory test.",
            "scope": "Evidence encoding boundaries.",
            "documents": [
                {
                    "path": "docs/wireframe.md",
                    "kind": "wireframe",
                    "audience": "UI designers",
                    "reader_task": "Layout wireframes.",
                    "sources": [dir_ev, bin_ev],
                }
            ],
        }
        rec_path = self.proj_root / "rec.json"
        rec_path.write_text(json.dumps(rec), encoding="utf-8")

        res = self.run_cli(
            [
                str(rec_path),
                "--project-root",
                str(self.proj_root),
                "--transition",
                "intake-authoring",
                "--documents",
                "docs/wireframe.md",
                "--format",
                "json",
            ]
        )
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        self.assertFalse(data.get("valid"))
        self.assertFalse(data.get("eligible"))
        finding_paths = [f.get("path", "") for f in data.get("findings", [])]
        self.assertTrue(any("sources[0]" in p for p in finding_paths))
        self.assertTrue(any("sources[1]" in p for p in finding_paths))

    def test_transition_rules_and_reviewer_governance(self) -> None:
        """review-ready fails if reviewer is missing or any check is blocked or unaccepted."""
        doc_rel = "ui-ux.md"
        doc_path = self.proj_root / doc_rel
        doc_path.write_text("# UI/UX Guidelines\nDesign specs.\n", encoding="utf-8")
        doc_sha = _sha256(doc_path.read_bytes())

        # Checks marked pass but decision not_accepted
        checks = self.make_checks("ui-ux", status="pass", decision="not_accepted")

        rec = {
            "schema_version": 1,
            "transition": {"from": "review", "to": "ready"},
            # Reviewer missing!
            "objective": "UI/UX signoff.",
            "scope": "Component tokens.",
            "documents": [
                {
                    "path": doc_rel,
                    "kind": "ui-ux",
                    "audience": "Frontend designers",
                    "reader_task": "Implement color contrast tokens.",
                    "sources": [self.create_evidence()],
                    "sha256": doc_sha,
                    "checks": checks,
                }
            ],
        }
        rec_path = self.proj_root / "rec.json"
        rec_path.write_text(json.dumps(rec), encoding="utf-8")

        res = self.run_cli(
            [
                str(rec_path),
                "--project-root",
                str(self.proj_root),
                "--transition",
                "review-ready",
                "--documents",
                doc_rel,
                "--format",
                "json",
            ]
        )
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        self.assertFalse(data.get("valid"))
        self.assertFalse(data.get("eligible"))
        finding_paths = [f.get("path", "") for f in data.get("findings", [])]
        self.assertIn("reviewer", finding_paths)
        self.assertTrue(any("checks" in p for p in finding_paths))

    def test_unexpected_fields_rejected(self) -> None:
        """Extra or rogue fields on record, documents, checks, or evidence are rejected."""
        rec = {
            "schema_version": 1,
            "transition": {"from": "intake", "to": "authoring"},
            "objective": "Strict fields check.",
            "scope": "Boundary check.",
            "rogue_field": "disallowed",
            "documents": [
                {
                    "path": "docs/brd.md",
                    "kind": "brd",
                    "audience": "Leadership",
                    "reader_task": "Evaluate ROI.",
                    "extra_key": 123,
                    "sources": [
                        dict(self.create_evidence(), bonus_field="not_allowed")
                    ],
                }
            ],
        }
        rec_path = self.proj_root / "rec.json"
        rec_path.write_text(json.dumps(rec), encoding="utf-8")

        res = self.run_cli(
            [
                str(rec_path),
                "--project-root",
                str(self.proj_root),
                "--transition",
                "intake-authoring",
                "--documents",
                "docs/brd.md",
                "--format",
                "json",
            ]
        )
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        self.assertFalse(data.get("valid"))
        self.assertFalse(data.get("eligible"))
        finding_paths = [f.get("path", "") for f in data.get("findings", [])]
        self.assertIn("rogue_field", finding_paths)
        self.assertTrue(any("extra_key" in p for p in finding_paths))
        self.assertTrue(any("bonus_field" in p for p in finding_paths))


class TestDocQualityMalformedPayloads(DocQualityTestBase):
    """Verifies that unparseable JSON, duplicate keys, or unreadable files exit with code 2."""

    def test_malformed_json_syntax_exits_2(self) -> None:
        """Broken JSON syntax causes validate.py to terminate with exit code 2."""
        rec_path = self.proj_root / "malformed.json"
        rec_path.write_text("{ unquoted_key: 123, broken ...", encoding="utf-8")

        res = self.run_cli(
            [
                str(rec_path),
                "--project-root",
                str(self.proj_root),
                "--transition",
                "intake-authoring",
                "--documents",
                "doc.md",
            ]
        )
        self.assertEqual(res.returncode, 2)
        self.assertIn("Error parsing record JSON", res.stderr)

    def test_duplicate_json_keys_exits_2(self) -> None:
        """Duplicate keys in JSON trigger strict hook and terminate with exit code 2."""
        rec_path = self.proj_root / "duplicate_keys.json"
        rec_path.write_text(
            '{"schema_version": 1, "schema_version": 1, "transition": {"from": "intake", "to": "authoring"}}',
            encoding="utf-8",
        )

        res = self.run_cli(
            [
                str(rec_path),
                "--project-root",
                str(self.proj_root),
                "--transition",
                "intake-authoring",
                "--documents",
                "doc.md",
            ]
        )
        self.assertEqual(res.returncode, 2)
        self.assertIn("Error parsing record JSON", res.stderr)

    def test_nonexistent_record_file_exits_2(self) -> None:
        """Non-existent record path terminates with exit code 2."""
        res = self.run_cli(
            [
                "nonexistent-record.json",
                "--project-root",
                str(self.proj_root),
                "--transition",
                "intake-authoring",
                "--documents",
                "doc.md",
            ]
        )
        self.assertEqual(res.returncode, 2)

    def test_invalid_cli_arguments_exits_2(self) -> None:
        """Invalid transition choice or missing required arguments terminates with code 2."""
        res = self.run_cli(
            [
                "record.json",
                "--project-root",
                str(self.proj_root),
                "--transition",
                "invalid-transition-name",
                "--documents",
                "doc.md",
            ]
        )
        self.assertEqual(res.returncode, 2)


if __name__ == "__main__":
    unittest.main()
