#!/usr/bin/env python3
"""Behavior tests for `python3 scripts/derive_ledger.py`."""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
DERIVE_SCRIPT = PROJECT_ROOT / "scripts" / "derive_ledger.py"
VALIDATOR_SCRIPT = PROJECT_ROOT / "scripts" / "validate.py"


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DeriveLedgerTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name).resolve()
        (self.root / "docs" / "specs").mkdir(parents=True)
        (self.root / "docs" / "decisions").mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_doc(self, rel: str, text: str = "# Spec\n\nBody.\n") -> pathlib.Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def write_record(
        self,
        name: str,
        *,
        to: str,
        from_state: str = "rework",
        docs: list[tuple[str, str]] | None = None,
    ) -> pathlib.Path:
        payload = {
            "schema_version": 1,
            "transition": {"from": from_state, "to": to},
            "objective": "test transition",
            "scope": "test",
            "reviewer": {"id": "reviewer-1", "kind": "agent", "author_id": "author-1"},
            "documents": [
                {"path": path, "kind": "spec", "sha256": sha} for path, sha in (docs or [])
            ],
        }
        path = self.root / "docs" / "decisions" / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def run_derive(self, *args: str) -> tuple[int, dict]:
        res = subprocess.run(
            [sys.executable, str(DERIVE_SCRIPT), "--project-root", str(self.root), "--format", "json", *args],
            capture_output=True,
            text=True,
        )
        return res.returncode, json.loads(res.stdout or "{}")

    def ledger(self) -> dict:
        return json.loads((self.root / "docs" / "specs" / "ledger.json").read_text(encoding="utf-8"))


class TestDeriveLedger(DeriveLedgerTestBase):
    def test_round_trip_ledger_passes_existing_validator(self) -> None:
        doc = self.write_doc("docs/specs/prd.md")
        self.write_record(
            "r1.json", to="review", from_state="rework", docs=[("docs/specs/prd.md", _sha(doc))]
        )

        code, result = self.run_derive("--write")

        self.assertEqual(code, 0, result)
        self.assertEqual(result["written"], "docs/specs/ledger.json")
        self.assertEqual(result["documents"], 1)
        ledger = self.ledger()
        self.assertEqual(ledger["schema_version"], 1)
        self.assertEqual(ledger["documents"][0]["state"], "review")
        self.assertEqual(ledger["documents"][0]["record"], "docs/decisions/r1.json")

        check = subprocess.run(
            [
                sys.executable,
                str(VALIDATOR_SCRIPT),
                "ledger",
                "docs/specs/ledger.json",
                "--project-root",
                str(self.root),
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(check.returncode, 0, check.stdout)

    def test_chain_picks_terminal_and_records_history(self) -> None:
        doc = self.write_doc("docs/specs/frd.md")
        current = _sha(doc)
        self.write_record(
            "a-intake.json", to="authoring", from_state="intake", docs=[("docs/specs/frd.md", current)]
        )
        self.write_record(
            "b-review.json", to="review", from_state="authoring", docs=[("docs/specs/frd.md", current)]
        )
        self.write_record(
            "c-rework.json", to="rework", from_state="review", docs=[("docs/specs/frd.md", "0" * 64)]
        )

        code, result = self.run_derive("--write")

        self.assertEqual(code, 0, result)
        entry = self.ledger()["documents"][0]
        self.assertEqual(entry["state"], "review")
        self.assertEqual(entry["record"], "docs/decisions/b-review.json")
        self.assertEqual(entry["sha256"], current)
        self.assertEqual(entry["history"], ["docs/decisions/a-intake.json"])

    def test_same_target_conflict_refuses_write(self) -> None:
        doc = self.write_doc("docs/specs/prd.md")
        current = _sha(doc)
        self.write_record("x.json", to="review", from_state="rework", docs=[("docs/specs/prd.md", current)])
        self.write_record("y.json", to="review", from_state="intake", docs=[("docs/specs/prd.md", current)])

        code, result = self.run_derive("--write")

        self.assertEqual(code, 1)
        codes = [f["code"] for f in result["findings"]]
        self.assertIn("derive_doc_conflict", codes)
        self.assertIn("derive_write_refused", codes)
        self.assertIsNone(result["written"])
        self.assertFalse((self.root / "docs" / "specs" / "ledger.json").exists())

    def test_disconnected_chain_conflicts(self) -> None:
        doc = self.write_doc("docs/specs/prd.md")
        current = _sha(doc)
        self.write_record("a.json", to="authoring", from_state="intake", docs=[("docs/specs/prd.md", current)])
        self.write_record("b.json", to="review", from_state="rework", docs=[("docs/specs/prd.md", current)])

        code, result = self.run_derive()

        self.assertEqual(code, 1)
        self.assertIn("derive_doc_conflict", [f["code"] for f in result["findings"]])

    def test_dry_run_writes_nothing(self) -> None:
        doc = self.write_doc("docs/specs/prd.md")
        self.write_record("r1.json", to="review", docs=[("docs/specs/prd.md", _sha(doc))])

        code, result = self.run_derive()

        self.assertEqual(code, 0, result)
        self.assertIsNone(result["written"])
        self.assertFalse((self.root / "docs" / "specs" / "ledger.json").exists())

    def test_edited_document_is_reported_not_repinned(self) -> None:
        doc = self.write_doc("docs/specs/prd.md")
        stale = _sha(doc)
        self.write_record("prd.json", to="review", docs=[("docs/specs/prd.md", stale)])
        doc.write_text("# Spec\n\nEdited after review.\n", encoding="utf-8")

        other = self.write_doc("docs/specs/frd.md")
        self.write_record("frd.json", to="review", docs=[("docs/specs/frd.md", _sha(other))])

        code, result = self.run_derive("--write")

        self.assertEqual(code, 0, result)
        self.assertEqual(result["unmapped"], ["docs/specs/prd.md"])
        self.assertIn("derive_doc_unmapped", [f["code"] for f in result["findings"]])
        paths = [entry["path"] for entry in self.ledger()["documents"]]
        self.assertEqual(paths, ["docs/specs/frd.md"])

    def test_malformed_record_does_not_block_other_documents(self) -> None:
        doc = self.write_doc("docs/specs/prd.md")
        self.write_record("good.json", to="review", docs=[("docs/specs/prd.md", _sha(doc))])
        (self.root / "docs" / "decisions" / "broken.json").write_text("{not json", encoding="utf-8")

        code, result = self.run_derive("--write")

        self.assertEqual(code, 0, result)
        self.assertIn("derive_record_malformed", [f["code"] for f in result["findings"]])
        self.assertEqual(result["documents"], 1)

    def test_path_escaping_root_is_never_read(self) -> None:
        outside = self.root.parent / "outside-secret.md"
        outside.write_text("secret\n", encoding="utf-8")
        try:
            self.write_record(
                "escape.json", to="review", docs=[("../../outside-secret.md", _sha(outside))]
            )
            code, result = self.run_derive()

            self.assertEqual(code, 1)
            self.assertIn("derive_doc_missing", [f["code"] for f in result["findings"]])
            self.assertEqual(result["documents"], 0)
        finally:
            outside.unlink(missing_ok=True)

    def test_stale_record_shape_refuses_write(self) -> None:
        doc = self.write_doc("docs/specs/prd.md")
        payload = {
            "schema_version": 1,
            "transition": {"from": "review", "to": "ready"},
            "objective": "old-format record",
            "scope": "test",
            "reviewer": "Regio (Product Owner)",
            "documents": [{"path": "docs/specs/prd.md", "kind": "prd", "sha256": _sha(doc)}],
        }
        (self.root / "docs" / "decisions" / "old.json").write_text(json.dumps(payload), encoding="utf-8")

        code, result = self.run_derive("--write")

        self.assertEqual(code, 1)
        codes = [finding["code"] for finding in result["findings"]]
        self.assertIn("derive_ledger_invalid", codes)
        self.assertIn("derive_write_refused", codes)
        self.assertFalse((self.root / "docs" / "specs" / "ledger.json").exists())

    def test_missing_project_root_exits_two(self) -> None:
        res = subprocess.run(
            [sys.executable, str(DERIVE_SCRIPT), "--project-root", str(self.root / "nope")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 2)


if __name__ == "__main__":
    unittest.main()
