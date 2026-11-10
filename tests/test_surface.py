#!/usr/bin/env python3
"""Behavior tests for surface-session validation (`validate.py verify`) and the
completion gate that consumes it."""

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


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def valid_session() -> dict:
    return {
        "role": "PETUGAS_TPS",
        "viewports": [
            {"width": 390, "height": 844},
            {"width": 1440, "height": 900},
        ],
        "legs": [
            {
                "kind": "write",
                "name": "create deposit for today",
                "interaction": "fill ID/date/volume/fat/SNF, click Simpan setoran",
                "wire": "POST /api/v1/deposits -> 201",
                "message": "Setoran berhasil disimpan.",
                "status": "passed",
            },
            {
                "kind": "read_back",
                "name": "reopen the deposits screen",
                "interaction": "reload and read the saved row",
                "wire": "GET /api/v1/deposits?date=2026-11-09 -> 200",
                "message": "1 setoran hari ini",
                "status": "passed",
            },
        ],
    }


class SurfaceTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name).resolve()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_session(self, data: dict) -> pathlib.Path:
        path = self.root / "surface-session.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def run_verify(self, *args: str) -> tuple[int, dict]:
        res = subprocess.run(
            [
                sys.executable,
                str(VALIDATOR_SCRIPT),
                "verify",
                *args,
                "--project-root",
                str(self.root),
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
        )
        return res.returncode, json.loads(res.stdout or "{}")


class TestVerifyCLI(SurfaceTestBase):
    def test_complete_session_passes(self) -> None:
        self.write_session(valid_session())
        code, payload = self.run_verify("surface-session.json")

        self.assertEqual(code, 0, payload)
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["check"], "verify")

    def test_missing_read_back_leg_fails(self) -> None:
        session = valid_session()
        session["legs"] = [session["legs"][0]]
        self.write_session(session)

        code, payload = self.run_verify("surface-session.json")

        self.assertEqual(code, 1)
        self.assertIn("surface_leg_kind_missing", [f["code"] for f in payload["findings"]])

    def test_single_viewport_fails(self) -> None:
        session = valid_session()
        session["viewports"] = [{"width": 1440, "height": 900}]
        self.write_session(session)

        code, payload = self.run_verify("surface-session.json")

        self.assertEqual(code, 1)
        self.assertIn("surface_viewport_missing", [f["code"] for f in payload["findings"]])

    def test_phone_only_fails_pair_check(self) -> None:
        session = valid_session()
        session["viewports"] = [
            {"width": 390, "height": 844},
            {"width": 480, "height": 800},
        ]
        self.write_session(session)

        code, payload = self.run_verify("surface-session.json")

        self.assertEqual(code, 1)
        self.assertIn("surface_viewport_pair_missing", [f["code"] for f in payload["findings"]])

    def test_wire_without_outcome_fails(self) -> None:
        session = valid_session()
        session["legs"][0]["wire"] = "POST /api/v1/deposits"
        self.write_session(session)

        code, payload = self.run_verify("surface-session.json")

        self.assertEqual(code, 1)
        self.assertIn("surface_leg_wire_undetermined", [f["code"] for f in payload["findings"]])

    def test_bare_number_is_not_a_wire_outcome(self) -> None:
        session = valid_session()
        session["legs"][0]["wire"] = "viewport 390"
        self.write_session(session)

        code, payload = self.run_verify("surface-session.json")

        self.assertEqual(code, 1)
        self.assertIn("surface_leg_wire_undetermined", [f["code"] for f in payload["findings"]])

    def test_wire_accepts_method_and_exit_outcomes(self) -> None:
        for wire in ("POST /x -> 201", "POST /x 201", "exit 0"):
            with self.subTest(wire=wire):
                session = valid_session()
                session["legs"][0]["wire"] = wire
                self.write_session(session)

                code, payload = self.run_verify("surface-session.json")

                self.assertEqual(code, 0, payload)

    def test_blank_message_fails(self) -> None:
        session = valid_session()
        session["legs"][1]["message"] = "   "
        self.write_session(session)

        code, payload = self.run_verify("surface-session.json")

        self.assertEqual(code, 1)
        self.assertIn("surface_leg_field_missing", [f["code"] for f in payload["findings"]])

    def test_unexercised_leg_passes_in_flight_but_not_at_completion(self) -> None:
        session = valid_session()
        session["legs"][1]["status"] = "unexercised"
        self.write_session(session)

        in_flight, _ = self.run_verify("surface-session.json", "--stage", "execute")
        complete, payload = self.run_verify("surface-session.json", "--stage", "complete")

        self.assertEqual(in_flight, 0)
        self.assertEqual(complete, 1)
        self.assertIn("surface_leg_not_passed", [f["code"] for f in payload["findings"]])

    def test_malformed_session_is_usage_error(self) -> None:
        (self.root / "broken.json").write_text("{not json", encoding="utf-8")
        res = subprocess.run(
            [
                sys.executable,
                str(VALIDATOR_SCRIPT),
                "verify",
                "broken.json",
                "--project-root",
                str(self.root),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 2)


class TestContractCompletionGate(SurfaceTestBase):
    def build_contract(self, session: dict | None) -> dict:
        src = self.root / "src" / "app.py"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("print('ok')\n", encoding="utf-8")
        evidence = self.root / "evidence" / "ac-1.log"
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text("observed pass\n", encoding="utf-8")

        result = {
            "revision": "rev-2",
            "files": [{"path": "src/app.py", "sha256": _sha(src)}],
        }
        if session is not None:
            result["surface_session"] = session
        return {
            "schema_version": 1,
            "objective": "Ship the deposits screen change",
            "surface": "ui",
            "baseline": {
                "revision": "rev-1",
                "files": [{"path": "src/app.py", "sha256": "0" * 64}],
            },
            "documents": [],
            "acceptance_criteria": [{"id": "AC-1", "criterion": "Operator can record a deposit today."}],
            "operation": {
                "risk": "low",
                "action": "edit",
                "target": "deposits screen",
                "revision": "rev-1",
                "scope": ["frontend/src/components"],
            },
            "evidence": [
                {
                    "criterion_id": "AC-1",
                    "status": "passed",
                    "reference": "evidence/ac-1.log",
                    "summary": "Deposit saved and visible after reload.",
                    "sha256": _sha(evidence),
                    "revision": "rev-2",
                }
            ],
            "result": result,
        }

    def run_contract(self, contract: dict, stage: str = "complete") -> tuple[int, dict]:
        path = self.root / "contract.json"
        path.write_text(json.dumps(contract), encoding="utf-8")
        res = subprocess.run(
            [
                sys.executable,
                str(VALIDATOR_SCRIPT),
                "contract",
                "contract.json",
                "--project-root",
                str(self.root),
                "--stage",
                stage,
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
        )
        return res.returncode, json.loads(res.stdout or "{}")

    def test_complete_contract_with_full_session_is_valid(self) -> None:
        code, payload = self.run_contract(self.build_contract(valid_session()))

        self.assertEqual(code, 0, payload)
        self.assertTrue(payload["valid"], payload["findings"])

    def test_complete_contract_without_session_is_rejected(self) -> None:
        code, payload = self.run_contract(self.build_contract(None))

        self.assertEqual(code, 1)
        self.assertIn("surface_session_missing", [f["code"] for f in payload["findings"]])

    def test_complete_contract_with_unwalked_leg_is_rejected(self) -> None:
        session = valid_session()
        session["legs"][0]["status"] = "unexercised"
        code, payload = self.run_contract(self.build_contract(session))

        self.assertEqual(code, 1)
        self.assertIn("surface_leg_not_passed", [f["code"] for f in payload["findings"]])

    def test_ui_scope_without_surface_declaration_warns(self) -> None:
        contract = self.build_contract(valid_session())
        contract.pop("surface")
        code, payload = self.run_contract(contract)

        self.assertEqual(code, 0, payload)
        self.assertIn("surface_declaration_inferred", [f["code"] for f in payload["findings"]])
        self.assertIn("surface_session_ignored", [f["code"] for f in payload["findings"]])
        self.assertNotIn("surface_declaration_mismatch", [f["code"] for f in payload["findings"]])

    def test_non_ui_declaration_over_ui_scope_is_rejected(self) -> None:
        contract = self.build_contract(None)
        contract["surface"] = "non-ui"
        code, payload = self.run_contract(contract)

        self.assertEqual(code, 1)
        self.assertIn("surface_declaration_mismatch", [f["code"] for f in payload["findings"]])

    def test_non_ui_declaration_over_non_ui_scope_passes(self) -> None:
        contract = self.build_contract(None)
        contract["surface"] = "non-ui"
        contract["operation"]["scope"] = ["scripts/foo.py"]
        code, payload = self.run_contract(contract)

        self.assertEqual(code, 0, payload)
        self.assertNotIn("surface_declaration_mismatch", [f["code"] for f in payload["findings"]])

    def test_invalid_surface_value_is_rejected(self) -> None:
        contract = self.build_contract(valid_session())
        contract["surface"] = "webby"
        code, payload = self.run_contract(contract)

        self.assertEqual(code, 1)
        self.assertIn("surface_declaration_invalid", [f["code"] for f in payload["findings"]])


if __name__ == "__main__":
    unittest.main()
