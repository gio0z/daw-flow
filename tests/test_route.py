import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

# Ensure scripts can be imported
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import route


def make_request(
    schema_version=1,
    intent="feature",
    requirements="clear",
    risk="low",
    workspace="in-place",
    **extra
):
    req = {
        "schema_version": schema_version,
        "intent": intent,
        "requirements": requirements,
        "risk": risk,
        "workspace": workspace,
    }
    req.update(extra)
    return req


def setup_suite_fixture(base_dir: pathlib.Path) -> pathlib.Path:
    """Create a fully valid suite fixture with manifest and all 8 modules."""
    manifest_src = REPO_ROOT / "references" / "suite-manifest.json"
    manifest_dst = base_dir / "references" / "suite-manifest.json"
    manifest_dst.parent.mkdir(parents=True, exist_ok=True)
    manifest_dst.write_text(manifest_src.read_text(encoding="utf-8"), encoding="utf-8")

    manifest_data = json.loads(manifest_dst.read_text(encoding="utf-8"))
    for mod_name, mod_info in manifest_data["modules"].items():
        mod_file = base_dir / mod_info["path"]
        mod_file.parent.mkdir(parents=True, exist_ok=True)
        mod_file.write_text(
            f"---\nname: {mod_name}\ndescription: {mod_info['description']}\n---\n# {mod_name}\n\nProcedure body.\n",
            encoding="utf-8",
        )
    return base_dir


class TestRouteSuite(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.suite_root = pathlib.Path(self.tmp_dir.name)
        setup_suite_fixture(self.suite_root)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_check_suite_valid(self):
        findings = route.check_suite(self.suite_root)
        self.assertEqual(findings, [])

    def test_check_suite_missing_module(self):
        # Remove daw-debug module
        debug_file = self.suite_root / "skills" / "daw-debug" / "SKILL.md"
        debug_file.unlink()
        findings = route.check_suite(self.suite_root)
        self.assertTrue(any(f["code"] == "MODULE_NOT_FOUND" for f in findings))

    def test_check_suite_mismatched_frontmatter(self):
        # Valid frontmatter structure with description, but mismatched name
        design_file = self.suite_root / "skills" / "daw-design" / "SKILL.md"
        design_file.write_text(
            "---\nname: wrong-name\ndescription: Design module description\n---\n# Content\n",
            encoding="utf-8",
        )
        findings = route.check_suite(self.suite_root)
        self.assertTrue(any(f["code"] == "MODULE_NAME_MISMATCH" for f in findings))

    def test_all_intent_routes(self):
        # 1. Feature with clear requirements, in-place
        req = make_request(intent="feature", requirements="clear", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["stages"], ["daw-plan", "daw-build", "daw-review", "daw-verify"])
        self.assertFalse(res["constraints"]["read_only"])
        self.assertFalse(res["constraints"]["documentation_only"])
        self.assertFalse(res["constraints"]["interactive_approval_required"])
        self.assertFalse(res["constraints"]["authorization_granted"])

        # 2. Feature with unclear requirements -> prepends daw-design
        req = make_request(intent="feature", requirements="unclear", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["stages"], ["daw-design", "daw-plan", "daw-build", "daw-review", "daw-verify"])

        # 3. Feature isolated -> prepends daw-workspace
        req = make_request(intent="feature", requirements="clear", risk="low", workspace="isolated")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["stages"], ["daw-workspace", "daw-plan", "daw-build", "daw-review", "daw-verify"])

        # 4. Feature unclear + isolated
        req = make_request(intent="feature", requirements="unclear", risk="low", workspace="isolated")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["stages"], ["daw-workspace", "daw-design", "daw-plan", "daw-build", "daw-review", "daw-verify"])

        # 5. Bugfix
        req = make_request(intent="bugfix", requirements="clear", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["stages"], ["daw-debug", "daw-plan", "daw-build", "daw-review", "daw-verify"])

        # 6. Bugfix isolated
        req = make_request(intent="bugfix", requirements="clear", risk="low", workspace="isolated")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["stages"], ["daw-workspace", "daw-debug", "daw-plan", "daw-build", "daw-review", "daw-verify"])

        # 7. Patch
        req = make_request(intent="patch", requirements="clear", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["stages"], ["daw-build", "daw-verify"])

        # 8. Review (read-only)
        req = make_request(intent="review", requirements="clear", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["stages"], ["daw-review"])
        self.assertTrue(res["constraints"]["read_only"])

        # 9. Ask (read-only)
        req = make_request(intent="ask", requirements="clear", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["stages"], ["daw-ask"])
        self.assertTrue(res["constraints"]["read_only"])

        # 10. Bootstrap (documentation only)
        req = make_request(intent="bootstrap", requirements="clear", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["stages"], ["daw-design", "daw-plan"])
        self.assertTrue(res["constraints"]["documentation_only"])

        # 11. Adopt (documentation only)
        req = make_request(intent="adopt", requirements="clear", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["stages"], ["daw-design", "daw-plan"])
        self.assertTrue(res["constraints"]["documentation_only"])

    def test_missing_stage_module_blocks_route(self):
        # Remove a core module (daw-workspace) even when requesting patch
        ws_file = self.suite_root / "skills" / "daw-workspace" / "SKILL.md"
        ws_file.unlink()
        req = make_request(intent="patch", requirements="clear", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "blocked")
        self.assertTrue(any(b["code"] == "MODULE_NOT_FOUND" for b in res["blockers"]))

    def test_requirements_and_workspace_handling(self):
        # Unknown requirements for feature -> needs-input, stages empty
        req = make_request(intent="feature", requirements="unknown", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "needs-input")
        self.assertEqual(res["stages"], [])

        # Unknown requirements for bootstrap -> needs-input, stages empty
        req = make_request(intent="bootstrap", requirements="unknown", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "needs-input")
        self.assertEqual(res["stages"], [])

        # Adopt with unknown requirements -> can inspect observed source and proceed
        req = make_request(intent="adopt", requirements="unknown", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["stages"], ["daw-design", "daw-plan"])

        # Mutating intent with unknown workspace -> needs-input
        req = make_request(intent="feature", requirements="clear", risk="low", workspace="unknown")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "needs-input")

        # Readonly or bootstrap ignores unknown workspace
        req = make_request(intent="ask", requirements="clear", risk="low", workspace="unknown")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")

        req = make_request(intent="bootstrap", requirements="clear", risk="low", workspace="unknown")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")

    def test_risk_and_approval_invariants(self):
        # Read-only intent with unknown risk -> ignored
        req = make_request(intent="review", requirements="clear", risk="unknown", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")

        # Mutating intent with unknown risk -> needs-input
        req = make_request(intent="feature", requirements="clear", risk="unknown", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "needs-input")

        # High risk -> interactive_approval_required: True, authorization_granted: False ALWAYS
        req = make_request(intent="feature", requirements="clear", risk="high", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")
        self.assertTrue(res["constraints"]["interactive_approval_required"])
        self.assertFalse(res["constraints"]["authorization_granted"])

    def test_strict_types_and_no_secret_leakage(self):
        secret_token = "SECRET_TOKEN_DO_NOT_LEAK_12345"

        # 1. Unknown unexpected key with secret value
        req = make_request()
        req[secret_token] = "SECRET_PAYLOAD"
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "error")
        serialized = json.dumps(res)
        self.assertNotIn(secret_token, serialized)
        self.assertNotIn("SECRET_PAYLOAD", serialized)

        # 2. Duplicate key in raw JSON containing secret
        raw_json = f'{{"schema_version": 1, "intent": "feature", "{secret_token}": 1, "{secret_token}": 2, "requirements": "clear", "risk": "low", "workspace": "in-place"}}'
        parsed, err = route.parse_strict_json(raw_json)
        self.assertIsNone(parsed)
        self.assertIsNotNone(err)
        self.assertNotIn(secret_token, err)

        # 3. Non-finite JSON numbers (NaN / Infinity)
        raw_nan = '{"schema_version": NaN, "intent": "feature", "requirements": "clear", "risk": "low", "workspace": "in-place"}'
        parsed, err = route.parse_strict_json(raw_nan)
        self.assertIsNone(parsed)
        self.assertIn("Non-standard", err)

        # 4. Strict types: schema_version as boolean True or float 1.0 or string "1"
        for bad_ver in [True, False, 1.0, "1", [1], {"ver": 1}]:
            req = make_request(schema_version=bad_ver)
            res = route.resolve_route(req, root=self.suite_root)
            self.assertEqual(res["status"], "error")
            self.assertTrue(any(b["code"] == "REQUEST_INVALID_SCHEMA_VERSION" for b in res["blockers"]))

        # 5. Invalid enum types (unhashable list / dict / integer / bool)
        for bad_intent in [["feature"], {"intent": "feature"}, 123, None, True, False]:
            req = make_request(intent=bad_intent)
            res = route.resolve_route(req, root=self.suite_root)
            self.assertEqual(res["status"], "error")
            self.assertTrue(any(b["code"] == "REQUEST_INVALID_INTENT" for b in res["blockers"]))

        for bad_req in [["clear"], {"r": "clear"}, 123, None, True]:
            req = make_request(requirements=bad_req)
            res = route.resolve_route(req, root=self.suite_root)
            self.assertEqual(res["status"], "error")
            self.assertTrue(any(b["code"] == "REQUEST_INVALID_REQUIREMENTS" for b in res["blockers"]))

        for bad_risk in [["low"], {"r": "low"}, 123, None, True]:
            req = make_request(risk=bad_risk)
            res = route.resolve_route(req, root=self.suite_root)
            self.assertEqual(res["status"], "error")
            self.assertTrue(any(b["code"] == "REQUEST_INVALID_RISK" for b in res["blockers"]))

        for bad_ws in [["in-place"], {"w": "in-place"}, 123, None, True]:
            req = make_request(workspace=bad_ws)
            res = route.resolve_route(req, root=self.suite_root)
            self.assertEqual(res["status"], "error")
            self.assertTrue(any(b["code"] == "REQUEST_INVALID_WORKSPACE" for b in res["blockers"]))

    def test_manifest_semantic_invariants(self):
        bad_manifest_path = self.suite_root / "references" / "suite-manifest.json"
        manifest_data = json.loads(bad_manifest_path.read_text(encoding="utf-8"))

        # Ask with mutating stage
        manifest_data["routes"]["ask"]["stages"] = ["daw-build"]
        bad_manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")
        findings = route.check_suite(self.suite_root)
        self.assertTrue(any(f["code"] == "MANIFEST_ROUTE_INVARIANT_VIOLATION" for f in findings))

        # Ask with read_only: false
        manifest_data = json.loads(bad_manifest_path.read_text(encoding="utf-8"))
        manifest_data["routes"]["ask"]["stages"] = ["daw-ask"]
        manifest_data["routes"]["ask"]["read_only"] = False
        bad_manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")
        findings = route.check_suite(self.suite_root)
        self.assertTrue(any(f["code"] == "MANIFEST_ROUTE_INVARIANT_VIOLATION" for f in findings))

        # Documentation-only on mutating route (e.g. bugfix)
        manifest_data = json.loads(bad_manifest_path.read_text(encoding="utf-8"))
        manifest_data["routes"]["ask"]["read_only"] = True
        manifest_data["routes"]["bugfix"]["documentation_only"] = True
        bad_manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")
        findings = route.check_suite(self.suite_root)
        self.assertTrue(any(f["code"] == "MANIFEST_ROUTE_INVARIANT_VIOLATION" for f in findings))

        # Empty stages list -> rejected as invariant violation and error status on route resolution
        manifest_data = json.loads(bad_manifest_path.read_text(encoding="utf-8"))
        manifest_data["routes"]["bugfix"]["documentation_only"] = False
        manifest_data["routes"]["bugfix"]["stages"] = []
        bad_manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")
        findings = route.check_suite(self.suite_root)
        self.assertTrue(any(f["code"] == "MANIFEST_ROUTE_INVARIANT_VIOLATION" for f in findings))
        # Consumer resolve_route behavior: status error, stages empty
        req = make_request(intent="bugfix", requirements="clear", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["stages"], [])

        # Duplicate stage in list -> rejected as invariant violation
        manifest_data = json.loads(bad_manifest_path.read_text(encoding="utf-8"))
        manifest_data["routes"]["bugfix"]["stages"] = ["daw-debug", "daw-debug"]
        bad_manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")
        findings = route.check_suite(self.suite_root)
        self.assertTrue(any(f["code"] == "MANIFEST_ROUTE_INVARIANT_VIOLATION" for f in findings))
        # Non-boolean evaluates_workspace (e.g. string "true")
        manifest_data = json.loads(bad_manifest_path.read_text(encoding="utf-8"))
        manifest_data["routes"]["bugfix"]["evaluates_workspace"] = "true"
        bad_manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")
        findings = route.check_suite(self.suite_root)
        self.assertTrue(any(f["code"] == "MANIFEST_ROUTE_INVARIANT_VIOLATION" for f in findings))

        # Extra unknown module in modules map containing secret name
        manifest_data = json.loads(bad_manifest_path.read_text(encoding="utf-8"))
        manifest_data["modules"]["SECRET_ATTACKER_MODULE"] = {"path": "skills/secret/SKILL.md", "description": "bad"}
        bad_manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")
        findings = route.check_suite(self.suite_root)
        self.assertTrue(any(f["code"] == "MANIFEST_EXTRA_MODULES" for f in findings))
        serialized_findings = json.dumps(findings)
        self.assertNotIn("SECRET_ATTACKER_MODULE", serialized_findings)

    def test_path_boundary_and_symlink_escapes(self):
        manifest_file = self.suite_root / "references" / "suite-manifest.json"
        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
        manifest_data["modules"]["daw-design"]["path"] = "../../etc/passwd"
        manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

        findings = route.check_suite(self.suite_root)
        self.assertTrue(any("ESCAPE" in f["code"] or "NON_CANONICAL" in f["code"] for f in findings))

    def test_cli_execution_modes(self):
        script_path = str(REPO_ROOT / "scripts" / "route.py")

        # 1. Valid check-suite CLI -> exit code 0
        cmd = [sys.executable, script_path, "--check-suite", "--root", str(self.suite_root)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertEqual(data["status"], "ready")

        # 2. Missing module on disk check-suite CLI -> exit code 1 (blocked)
        debug_file = self.suite_root / "skills" / "daw-debug" / "SKILL.md"
        debug_file.unlink()
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        data = json.loads(proc.stdout)
        self.assertEqual(data["status"], "blocked")

        # 3. Malformed manifest check-suite CLI -> exit code 2 (error)
        manifest_file = self.suite_root / "references" / "suite-manifest.json"
        manifest_file.write_text("NOT_VALID_JSON", encoding="utf-8")
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        data = json.loads(proc.stdout)
        self.assertEqual(data["status"], "error")

        # 4. Route request CLI -> exit code 0 on valid request
        setup_suite_fixture(self.suite_root)
        req_file = self.suite_root / "request.json"
        req_data = make_request(intent="patch", requirements="clear", risk="low", workspace="in-place")
        req_file.write_text(json.dumps(req_data), encoding="utf-8")

        cmd_req = [sys.executable, script_path, str(req_file), "--root", str(self.suite_root)]
        proc = subprocess.run(cmd_req, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertEqual(data["status"], "ready")
        self.assertEqual(data["stages"], ["daw-build", "daw-verify"])


if __name__ == "__main__":
    unittest.main()
