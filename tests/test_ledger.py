#!/usr/bin/env python3
"""Unit tests for `python3 scripts/validate.py ledger` (C3)."""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATOR_SCRIPT = PROJECT_ROOT / "scripts" / "validate.py"

COMMON_IDS = ["DQ-01", "DQ-02", "DQ-03", "DQ-04", "DQ-05"]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().lower()


class LedgerTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.proj_root = pathlib.Path(self.temp_dir.name).resolve()
        self.source_lines = [
            "Line 1: background and goals.",
            "Line 2: scope and boundaries.",
        ]
        self.source_content = "\n".join(self.source_lines) + "\n"
        (self.proj_root / "brief.txt").write_text(self.source_content, encoding="utf-8")
        self.source_sha = _sha256(self.source_content.encode("utf-8"))

        self.doc_rel = "docs/specs/frd.md"
        doc_path = self.proj_root / self.doc_rel
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text("# FRD\nFunctional requirements.\n", encoding="utf-8")
        self.doc_sha = _sha256(doc_path.read_bytes())

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_cli(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        cmd = [sys.executable, str(VALIDATOR_SCRIPT), "ledger"] + args
        return subprocess.run(cmd, cwd=str(self.proj_root), capture_output=True, text=True)

    def evidence(self) -> dict[str, object]:
        return {
            "path": "brief.txt",
            "sha256": self.source_sha,
            "start_line": 1,
            "end_line": 2,
            "quote": "\n".join(self.source_lines),
        }

    def make_checks(self, kind: str = "frd") -> list[dict[str, object]]:
        checks = []
        for c_id in COMMON_IDS + [f"{kind}-01", f"{kind}-02", f"{kind}-03"]:
            checks.append(
                {
                    "id": c_id,
                    "status": "pass",
                    "decision": "accepted",
                    "rationale": "Verified against brief.",
                    "evidence": [self.evidence()],
                }
            )
        return checks

    def write_ready_record(self, overrides: dict | None = None) -> tuple[pathlib.Path, dict]:
        rec = {
            "schema_version": 1,
            "transition": {"from": "review", "to": "ready"},
            "reviewer": {"id": "reviewer-1", "kind": "human", "author_id": "author-1"},
            "objective": "Ship FRD.",
            "scope": "FRD only.",
            "documents": [
                {
                    "path": self.doc_rel,
                    "kind": "frd",
                    "audience": "Engineers",
                    "reader_task": "Implement FRD.",
                    "sources": [self.evidence()],
                    "sha256": self.doc_sha,
                    "checks": self.make_checks(),
                }
            ],
        }
        if overrides:
            rec.update(overrides)
        rec_path = self.proj_root / "docs/decisions/2026-11-06-frd-ready.json"
        rec_path.parent.mkdir(parents=True, exist_ok=True)
        rec_path.write_text(json.dumps(rec), encoding="utf-8")
        return rec_path, rec

    def write_ledger(self, documents: list[dict], schema_version: int = 1) -> pathlib.Path:
        ledger_path = self.proj_root / "docs/specs/ledger.json"
        payload = {"schema_version": schema_version, "documents": documents}
        ledger_path.write_text(json.dumps(payload), encoding="utf-8")
        return ledger_path

    def valid_entry(self) -> dict:
        return {
            "path": self.doc_rel,
            "state": "ready",
            "sha256": self.doc_sha,
            "record": "docs/decisions/2026-11-06-frd-ready.json",
        }

    def run_ledger(self, path: pathlib.Path) -> subprocess.CompletedProcess[str]:
        return self.run_cli(
            [str(path), "--project-root", str(self.proj_root), "--format", "json"]
        )


class TestLedgerValid(LedgerTestBase):
    def test_valid_ledger(self) -> None:
        self.write_ready_record()
        ledger_path = self.write_ledger([self.valid_entry()])
        res = self.run_ledger(ledger_path)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        data = json.loads(res.stdout)
        self.assertTrue(data["valid"])
        self.assertEqual(data["check"], "ledger")


class TestLedgerFindings(LedgerTestBase):
    def test_doc_drift(self) -> None:
        self.write_ready_record()
        entry = self.valid_entry()
        entry["sha256"] = "0" * 64
        ledger_path = self.write_ledger([entry])
        res = self.run_ledger(ledger_path)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        codes = [f["code"] for f in json.loads(res.stdout)["findings"]]
        self.assertIn("ledger_doc_drift", codes)

    def test_record_mismatch(self) -> None:
        self.write_ready_record()
        entry = self.valid_entry()
        entry["record"] = "docs/decisions/missing.json"
        ledger_path = self.write_ledger([entry])
        res = self.run_ledger(ledger_path)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        codes = [f["code"] for f in json.loads(res.stdout)["findings"]]
        self.assertIn("file_not_found", codes)

    def test_state_mismatch(self) -> None:
        self.write_ready_record()
        entry = self.valid_entry()
        entry["state"] = "review"
        ledger_path = self.write_ledger([entry])
        res = self.run_ledger(ledger_path)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        codes = [f["code"] for f in json.loads(res.stdout)["findings"]]
        self.assertIn("ledger_state_mismatch", codes)

    def test_duplicate_document(self) -> None:
        self.write_ready_record()
        entry = self.valid_entry()
        ledger_path = self.write_ledger([entry, dict(entry)])
        res = self.run_ledger(ledger_path)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        codes = [f["code"] for f in json.loads(res.stdout)["findings"]]
        self.assertIn("ledger_duplicate_document", codes)

    def test_tmp_record_path_rejected(self) -> None:
        self.write_ready_record()
        entry = self.valid_entry()
        entry["record"] = "tmp/2026-11-06-frd-ready.json"
        ledger_path = self.write_ledger([entry])
        res = self.run_ledger(ledger_path)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        codes = [f["code"] for f in json.loads(res.stdout)["findings"]]
        self.assertIn("evidence_not_durable", codes)

    def test_non_string_record_rejected(self) -> None:
        self.write_ready_record()
        entry = self.valid_entry()
        entry["record"] = 123
        ledger_path = self.write_ledger([entry])
        res = self.run_ledger(ledger_path)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        codes = [f["code"] for f in json.loads(res.stdout)["findings"]]
        self.assertIn("invalid_record", codes)

    def _write_two_doc_record(self) -> str:
        prd_rel = "docs/specs/prd.md"
        prd_path = self.proj_root / prd_rel
        prd_path.write_text("# PRD\nProduct requirements.\n", encoding="utf-8")
        _, rec = self.write_ready_record()
        rec["documents"].append(
            {
                "path": prd_rel,
                "kind": "prd",
                "audience": "Product",
                "reader_task": "Scope product.",
                "sources": [self.evidence()],
                "sha256": _sha256(prd_path.read_bytes()),
                "checks": self.make_checks("prd"),
            }
        )
        rec_path = self.proj_root / "docs/decisions/2026-11-06-frd-ready.json"
        rec_path.write_text(json.dumps(rec), encoding="utf-8")
        prd_path.write_text("# PRD\nEdited after review.\n", encoding="utf-8")
        return prd_rel

    def test_shared_record_isolates_sibling_drift(self) -> None:
        self._write_two_doc_record()
        res = self.run_ledger(self.write_ledger([self.valid_entry()]))
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_shared_record_reports_own_drift(self) -> None:
        prd_rel = self._write_two_doc_record()
        prd_entry = {
            "path": prd_rel,
            "state": "ready",
            "sha256": _sha256((self.proj_root / prd_rel).read_bytes()),
            "record": "docs/decisions/2026-11-06-frd-ready.json",
        }
        res = self.run_ledger(self.write_ledger([self.valid_entry(), prd_entry]))
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        findings = json.loads(res.stdout)["findings"]
        self.assertTrue(all(f["path"].startswith("documents[1]") for f in findings), findings)
        self.assertIn("ledger_record_mismatch", [f["code"] for f in findings])


if __name__ == "__main__":
    unittest.main()
