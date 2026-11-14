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
    """Create a fully valid suite fixture with manifest and all 12 modules."""
    manifest_src = REPO_ROOT / "references" / "suite-manifest.json"
    manifest_dst = base_dir / "references" / "suite-manifest.json"
    manifest_dst.parent.mkdir(parents=True, exist_ok=True)
    manifest_dst.write_text(manifest_src.read_text(encoding="utf-8"), encoding="utf-8")
    flow_src = REPO_ROOT / "references" / "best-practice-flow.md"
    flow_dst = base_dir / "references" / "best-practice-flow.md"
    flow_dst.parent.mkdir(parents=True, exist_ok=True)
    flow_dst.write_text(flow_src.read_text(encoding="utf-8"), encoding="utf-8")

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
        # 10. Bootstrap (documentation only, starts with daw-wizard)
        req = make_request(intent="bootstrap", requirements="clear", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["stages"], ["daw-wizard", "daw-design", "daw-plan"])
        self.assertTrue(res["constraints"]["documentation_only"])
        # 11. Adopt (documentation only)
        req = make_request(intent="adopt", requirements="clear", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["stages"], ["daw-design", "daw-plan"])
        self.assertTrue(res["constraints"]["documentation_only"])


        # 12. Setup (documentation only, stages [daw-setup])
        req = make_request(intent="setup", requirements="clear", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["stages"], ["daw-setup"])
        self.assertTrue(res["constraints"]["documentation_only"])
        self.assertFalse(res["constraints"]["read_only"])

        # 13. Untangle (read-only structural analysis, stages [daw-untangle])
        req = make_request(intent="untangle", requirements="clear", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["stages"], ["daw-untangle"])
        self.assertTrue(res["constraints"]["read_only"])
        self.assertFalse(res["constraints"]["documentation_only"])
        self.assertFalse(res["constraints"]["interactive_approval_required"])
        self.assertFalse(res["constraints"]["authorization_granted"])
    def test_missing_stage_module_blocks_route(self):
        # Remove a core module (daw-workspace) even when requesting patch
        ws_file = self.suite_root / "skills" / "daw-workspace" / "SKILL.md"
        ws_file.unlink()
        req = make_request(intent="patch", requirements="clear", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "blocked")
        self.assertTrue(any(b["code"] == "MODULE_NOT_FOUND" for b in res["blockers"]))

    def test_check_suite_missing_wizard_module(self):
        wizard_file = self.suite_root / "skills" / "daw-wizard" / "SKILL.md"
        wizard_file.unlink()
        findings = route.check_suite(self.suite_root)
        self.assertTrue(any(f["code"] == "MODULE_NOT_FOUND" and "daw-wizard" in f["message"] for f in findings))

    def test_check_suite_missing_untangle_module(self):
        untangle_file = self.suite_root / "skills" / "daw-untangle" / "SKILL.md"
        untangle_file.unlink()
        findings = route.check_suite(self.suite_root)
        self.assertTrue(any(f["code"] == "MODULE_NOT_FOUND" and "daw-untangle" in f["message"] for f in findings))

    def test_untangle_route_behavior_and_flag_handling(self):
        # Requirements unknown -> proceeds without blocking, stages [daw-untangle]
        req = make_request(intent="untangle", requirements="unknown", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["stages"], ["daw-untangle"])
        self.assertTrue(any("Requirements unknown for untangle" in r for r in res["reasons"]))

        # Requirements unclear -> proceeds without blocking
        req = make_request(intent="untangle", requirements="unclear", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["stages"], ["daw-untangle"])

        # High or unknown risk ignored because untangle is read-only
        for r_risk in ("high", "unknown"):
            req = make_request(intent="untangle", requirements="clear", risk=r_risk, workspace="in-place")
            res = route.resolve_route(req, root=self.suite_root)
            self.assertEqual(res["status"], "ready")
            self.assertEqual(res["stages"], ["daw-untangle"])
            self.assertFalse(res["constraints"]["interactive_approval_required"])
            self.assertTrue(any("Read-only intent 'untangle' ignores risk classification" in r for r in res["reasons"]))

        # Workspace unknown or isolated does not prepend daw-workspace because untangle does not evaluate workspace
        for ws in ("unknown", "isolated"):
            req = make_request(intent="untangle", requirements="clear", risk="low", workspace=ws)
            res = route.resolve_route(req, root=self.suite_root)
            self.assertEqual(res["status"], "ready")
            self.assertEqual(res["stages"], ["daw-untangle"])
            self.assertTrue(any("Intent 'untangle' does not evaluate workspace isolation" in r for r in res["reasons"]))

    def test_untangle_manifest_tamper_and_invariants(self):
        manifest_file = self.suite_root / "references" / "suite-manifest.json"
        clean_manifest_text = (REPO_ROOT / "references" / "suite-manifest.json").read_text(encoding="utf-8")

        # 1. Missing daw-untangle module
        manifest_data = json.loads(clean_manifest_text)
        manifest_data["modules"].pop("daw-untangle", None)
        manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")
        findings = route.check_suite(self.suite_root)
        self.assertTrue(any(f["code"] == "MANIFEST_MISSING_MODULES" for f in findings))

        # 2. Missing untangle route
        manifest_data = json.loads(clean_manifest_text)
        manifest_data["routes"].pop("untangle", None)
        manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")
        findings = route.check_suite(self.suite_root)
        self.assertTrue(any(f["code"] == "MANIFEST_MISSING_ROUTES" for f in findings))

        # 3. Untangle route read_only false -> invariant violation
        manifest_data = json.loads(clean_manifest_text)
        manifest_data["routes"]["untangle"]["read_only"] = False
        manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")
        findings = route.check_suite(self.suite_root)
        self.assertTrue(any(f["code"] == "MANIFEST_ROUTE_INVARIANT_VIOLATION" for f in findings))

        # 4. Untangle route documentation_only true -> invariant violation
        manifest_data = json.loads(clean_manifest_text)
        manifest_data["routes"]["untangle"]["documentation_only"] = True
        manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")
        findings = route.check_suite(self.suite_root)
        self.assertTrue(any(f["code"] == "MANIFEST_ROUTE_INVARIANT_VIOLATION" for f in findings))

        # 5. Untangle route evaluates_workspace true -> invariant violation
        manifest_data = json.loads(clean_manifest_text)
        manifest_data["routes"]["untangle"]["evaluates_workspace"] = True
        manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")
        findings = route.check_suite(self.suite_root)
        self.assertTrue(any(f["code"] == "MANIFEST_ROUTE_INVARIANT_VIOLATION" for f in findings))

        # 6. Untangle route stages mutated
        manifest_data = json.loads(clean_manifest_text)
        manifest_data["routes"]["untangle"]["stages"] = ["daw-untangle", "daw-build"]
        manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")
        findings = route.check_suite(self.suite_root)
        self.assertTrue(any(f["code"] == "MANIFEST_ROUTE_INVARIANT_VIOLATION" for f in findings))

        # 7. Untangle route extra unexpected key -> shape invalid
        manifest_data = json.loads(clean_manifest_text)
        manifest_data["routes"]["untangle"]["unexpected_extra"] = True
        manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")
        findings = route.check_suite(self.suite_root)
        self.assertTrue(any(f["code"] == "MANIFEST_ROUTE_SHAPE_INVALID" for f in findings))

        # Restore clean manifest
        manifest_file.write_text(clean_manifest_text, encoding="utf-8")
    def test_lifecycle_intents_resolve_exact_stages(self):
        cases = [
            ("refactor", ["daw-untangle", "daw-plan", "daw-build", "daw-review", "daw-verify"]),
            ("maintain", ["daw-plan", "daw-build", "daw-review", "daw-verify"]),
            ("spike", ["daw-workspace", "daw-build", "daw-ask"]),
            ("ship", ["daw-ship"]),
        ]
        for intent, stages in cases:
            with self.subTest(intent=intent):
                req = make_request(intent=intent, requirements="clear", risk="low", workspace="in-place")
                res = route.resolve_route(req, root=self.suite_root)
                self.assertEqual(res["status"], "ready")
                self.assertEqual(res["stages"], stages)
                self.assertFalse(res["constraints"]["read_only"])
                self.assertFalse(res["constraints"]["documentation_only"])
                self.assertFalse(res["constraints"]["interactive_approval_required"])
                self.assertFalse(res["constraints"]["authorization_granted"])

    def test_refactor_maintain_workspace_isolation(self):
        for intent in ("refactor", "maintain"):
            with self.subTest(intent=intent):
                req = make_request(intent=intent, requirements="clear", risk="low", workspace="isolated")
                res = route.resolve_route(req, root=self.suite_root)
                self.assertEqual(res["status"], "ready")
                self.assertEqual(res["stages"][0], "daw-workspace")
                self.assertEqual(res["stages"].count("daw-workspace"), 1)
                req = make_request(intent=intent, requirements="clear", risk="low", workspace="unknown")
                res = route.resolve_route(req, root=self.suite_root)
                self.assertEqual(res["status"], "needs-input")
                self.assertEqual(res["stages"], [])

    def test_refactor_maintain_requirements_unknown_gate(self):
        for intent in ("refactor", "maintain"):
            with self.subTest(intent=intent):
                req = make_request(intent=intent, requirements="unknown", risk="low", workspace="in-place")
                res = route.resolve_route(req, root=self.suite_root)
                self.assertEqual(res["status"], "needs-input")
                self.assertEqual(res["stages"], [])
                self.assertTrue(any(b["code"] == "REQUIREMENTS_UNKNOWN" for b in res["blockers"]))

    def test_spike_allows_unknown_requirements_and_ignores_workspace(self):
        req = make_request(intent="spike", requirements="unknown", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["stages"], ["daw-workspace", "daw-build", "daw-ask"])
        self.assertTrue(any("throwaway" in r for r in res["reasons"]))
        for ws in ("unknown", "isolated"):
            with self.subTest(workspace=ws):
                req = make_request(intent="spike", requirements="unknown", risk="low", workspace=ws)
                res = route.resolve_route(req, root=self.suite_root)
                self.assertEqual(res["status"], "ready")
                self.assertEqual(res["stages"], ["daw-workspace", "daw-build", "daw-ask"])

    def test_ship_risk_gating(self):
        req = make_request(intent="ship", requirements="clear", risk="unknown", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "needs-input")
        self.assertEqual(res["stages"], [])
        self.assertTrue(any(b["code"] == "RISK_UNKNOWN" for b in res["blockers"]))
        req = make_request(intent="ship", requirements="clear", risk="high", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["stages"], ["daw-ship"])
        self.assertTrue(res["constraints"]["interactive_approval_required"])
        self.assertFalse(res["constraints"]["authorization_granted"])

    def test_check_suite_missing_ship_module(self):
        ship_file = self.suite_root / "skills" / "daw-ship" / "SKILL.md"
        ship_file.unlink()
        findings = route.check_suite(self.suite_root)
        self.assertTrue(any(f["code"] == "MODULE_NOT_FOUND" and "daw-ship" in f["message"] for f in findings))

    def test_lifecycle_manifest_invariants(self):
        manifest_file = self.suite_root / "references" / "suite-manifest.json"
        clean = json.loads((REPO_ROOT / "references" / "suite-manifest.json").read_text(encoding="utf-8"))
        for intent, bad in (("refactor", ["daw-plan", "daw-build"]), ("maintain", ["daw-build", "daw-verify"]), ("spike", ["daw-build", "daw-ask"]), ("ship", ["daw-build"])):
            data = json.loads(json.dumps(clean))
            data["routes"][intent]["stages"] = bad
            manifest_file.write_text(json.dumps(data), encoding="utf-8")
            findings = route.check_suite(self.suite_root)
            self.assertTrue(any(f["code"] == "MANIFEST_ROUTE_INVARIANT_VIOLATION" for f in findings), intent)
        for intent, ws in (("refactor", False), ("maintain", False), ("spike", True), ("ship", True)):
            data = json.loads(json.dumps(clean))
            data["routes"][intent]["evaluates_workspace"] = ws
            manifest_file.write_text(json.dumps(data), encoding="utf-8")
            findings = route.check_suite(self.suite_root)
            self.assertTrue(any(f["code"] == "MANIFEST_ROUTE_INVARIANT_VIOLATION" for f in findings), intent)
        data = json.loads(json.dumps(clean))
        data["routes"]["ship"]["read_only"] = True
        manifest_file.write_text(json.dumps(data), encoding="utf-8")
        self.assertTrue(any(f["code"] == "MANIFEST_ROUTE_INVARIANT_VIOLATION" for f in route.check_suite(self.suite_root)))
        manifest_file.write_text(json.dumps(clean), encoding="utf-8")
        self.assertEqual(route.check_suite(self.suite_root), [])
    def test_cli_rejects_unknown_flags(self):
        script_path = str(REPO_ROOT / "scripts" / "route.py")
        cmd = [sys.executable, script_path, "--unknown-flag", "--root", str(self.suite_root)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("unrecognized arguments", proc.stderr)

    def test_side_effect_free_dispatch_untangle(self):
        script_path = str(REPO_ROOT / "scripts" / "route.py")
        req_file = self.suite_root / "untangle-request.json"
        req_data = make_request(intent="untangle", requirements="clear", risk="low", workspace="in-place")
        req_file.write_text(json.dumps(req_data), encoding="utf-8")

        before_files = {
            p.relative_to(self.suite_root).as_posix(): p.stat().st_mtime_ns
            for p in self.suite_root.rglob("*")
            if p.is_file()
        }

        cmd = [sys.executable, script_path, str(req_file), "--root", str(self.suite_root)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertEqual(data["status"], "ready")
        self.assertEqual(data["stages"], ["daw-untangle"])
        self.assertTrue(data["constraints"]["read_only"])

        after_files = {
            p.relative_to(self.suite_root).as_posix(): p.stat().st_mtime_ns
            for p in self.suite_root.rglob("*")
            if p.is_file()
        }

        self.assertEqual(set(before_files.keys()), set(after_files.keys()))
        for path, mtime in before_files.items():
            self.assertEqual(mtime, after_files[path], f"File modified during dispatch: {path}")

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

    def test_patch_requires_clear_requirements(self):
        # Clear patch -> unchanged build/verify pipeline
        req = make_request(intent="patch", requirements="clear", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["stages"], ["daw-build", "daw-verify"])

        # Unknown patch requirements -> needs-input, no stages
        req = make_request(intent="patch", requirements="unknown", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "needs-input")
        self.assertEqual(res["stages"], [])
        self.assertEqual([b["code"] for b in res["blockers"]], ["REQUIREMENTS_UNKNOWN"])

        # Unclear patch requirements -> needs-input, no stages, distinct diagnostic
        req = make_request(intent="patch", requirements="unclear", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "needs-input")
        self.assertEqual(res["stages"], [])
        self.assertEqual([b["code"] for b in res["blockers"]], ["REQUIREMENTS_UNCLEAR"])

        # Bugfix keeps investigation for unknown/unclear requirements
        for clarity in ("unknown", "unclear"):
            req = make_request(intent="bugfix", requirements=clarity, risk="low", workspace="in-place")
            res = route.resolve_route(req, root=self.suite_root)
            self.assertEqual(res["status"], "ready")
            self.assertEqual(res["stages"][0], "daw-debug")

        # No generic gate: ask/bugfix unclear still route
        req = make_request(intent="ask", requirements="unclear", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")

    def test_cli_patch_requirements_gate_exit_codes(self):
        script_path = str(REPO_ROOT / "scripts" / "route.py")
        req_file = self.suite_root / "request.json"
        cmd = [sys.executable, script_path, str(req_file), "--root", str(self.suite_root)]

        req_file.write_text(
            json.dumps(make_request(intent="patch", requirements="unclear", risk="low", workspace="in-place")),
            encoding="utf-8",
        )
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        data = json.loads(proc.stdout)
        self.assertEqual(data["status"], "needs-input")
        self.assertEqual(data["stages"], [])
        self.assertEqual([b["code"] for b in data["blockers"]], ["REQUIREMENTS_UNCLEAR"])

        req_file.write_text(
            json.dumps(make_request(intent="patch", requirements="unknown", risk="low", workspace="in-place")),
            encoding="utf-8",
        )
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        data = json.loads(proc.stdout)
        self.assertEqual(data["status"], "needs-input")
        self.assertEqual([b["code"] for b in data["blockers"]], ["REQUIREMENTS_UNKNOWN"])

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

    def test_cli_preserves_suite_files_without_bytecode_environment_flags(self):
        scripts_dir = self.suite_root / "scripts"
        scripts_dir.mkdir()
        for name in ("route.py", "daw_common.py"):
            (scripts_dir / name).write_bytes((REPO_ROOT / "scripts" / name).read_bytes())
        request_path = self.suite_root / "request.json"
        request_path.write_text(json.dumps(make_request(intent="patch")), encoding="utf-8")
        before = {
            path.relative_to(self.suite_root).as_posix(): path.read_bytes() if path.is_file() else None
            for path in self.suite_root.rglob("*")
        }
        env = os.environ.copy()
        env.pop("PYTHONDONTWRITEBYTECODE", None)
        env.pop("PYTHONPYCACHEPREFIX", None)
        for arguments in (["--check-suite"], [str(request_path)]):
            with self.subTest(arguments=arguments):
                result = subprocess.run(
                    [sys.executable, str(scripts_dir / "route.py"), *arguments],
                    cwd=self.suite_root,
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout)["status"], "ready")
                after = {
                    path.relative_to(self.suite_root).as_posix(): path.read_bytes() if path.is_file() else None
                    for path in self.suite_root.rglob("*")
                }
                self.assertEqual(before.keys(), after.keys(), "Read-only routing created or removed filesystem entries")
                self.assertEqual(before, after, "Read-only routing changed file contents")

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

    def test_check_suite_accepts_flow_gate_manifest(self):
        script_path = str(REPO_ROOT / "scripts" / "route.py")
        cmd = [sys.executable, script_path, "--check-suite", "--root", str(self.suite_root)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertEqual(data["status"], "ready")

    def test_flow_gate_blocks_feature_on_empty_project(self):
        script_path = str(REPO_ROOT / "scripts" / "route.py")
        with tempfile.TemporaryDirectory() as tmp:
            project_root = pathlib.Path(tmp)
            req_file = self.suite_root / "request.json"
            req_data = make_request(intent="feature", requirements="clear", risk="low", workspace="in-place")
            req_file.write_text(json.dumps(req_data), encoding="utf-8")
            cmd = [sys.executable, script_path, str(req_file), "--root", str(self.suite_root), "--project-root", str(project_root)]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 1)
            data = json.loads(proc.stdout)
            self.assertEqual(data["status"], "blocked")
            self.assertTrue(any(b["code"] == "FLOW_GATE_MISSING_ARTIFACT" for b in data["blockers"]))

    def test_flow_gate_passes_with_artifacts(self):
        script_path = str(REPO_ROOT / "scripts" / "route.py")
        with tempfile.TemporaryDirectory() as tmp:
            project_root = pathlib.Path(tmp)
            (project_root / "docs" / "specs").mkdir(parents=True)
            (project_root / "docs" / "specs" / "prd.md").write_text("# PRD\nRequirements.\n", encoding="utf-8")
            (project_root / "docs" / "plans").mkdir(parents=True)
            (project_root / "docs" / "plans" / "p.md").write_text(
                "# Plan\nexpected: run tests\n<!-- daw-task-manifest -->\n", encoding="utf-8"
            )
            req_file = self.suite_root / "request.json"
            req_data = make_request(intent="feature", requirements="clear", risk="low", workspace="in-place")
            req_file.write_text(json.dumps(req_data), encoding="utf-8")
            cmd = [sys.executable, script_path, str(req_file), "--root", str(self.suite_root), "--project-root", str(project_root)]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0)
            data = json.loads(proc.stdout)
            self.assertEqual(data["status"], "ready")

    def test_flow_gate_skipped_without_project_root(self):
        script_path = str(REPO_ROOT / "scripts" / "route.py")
        req_file = self.suite_root / "request.json"
        req_data = make_request(intent="feature", requirements="clear", risk="low", workspace="in-place")
        req_file.write_text(json.dumps(req_data), encoding="utf-8")
        cmd = [sys.executable, script_path, str(req_file), "--root", str(self.suite_root)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertEqual(data["status"], "ready")

    def test_flow_gate_skips_ask_intent(self):
        script_path = str(REPO_ROOT / "scripts" / "route.py")
        with tempfile.TemporaryDirectory() as tmp:
            project_root = pathlib.Path(tmp)
            req_file = self.suite_root / "request.json"
            req_data = make_request(intent="ask", requirements="clear", risk="low", workspace="in-place")
            req_file.write_text(json.dumps(req_data), encoding="utf-8")
            cmd = [sys.executable, script_path, str(req_file), "--root", str(self.suite_root), "--project-root", str(project_root)]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0)
            data = json.loads(proc.stdout)
            self.assertEqual(data["status"], "ready")

    def _write_manifest(self, data: dict) -> None:
        manifest_file = self.suite_root / "references" / "suite-manifest.json"
        manifest_file.write_text(json.dumps(data), encoding="utf-8")

    def _clean_manifest(self) -> dict:
        return json.loads((REPO_ROOT / "references" / "suite-manifest.json").read_text(encoding="utf-8"))

    def _run_session_start(self, project_root: pathlib.Path, cwd=None):
        script_path = str(REPO_ROOT / "scripts" / "route.py")
        cmd = [sys.executable, script_path, "--session-start", "--root", str(self.suite_root), "--project-root", str(project_root)]
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_session_start_detects_project_artifacts(self):
        # Config block + plans -> feature; suggestion resolves without REQUEST_INVALID_INTENT.
        with tempfile.TemporaryDirectory() as tmp:
            project_root = pathlib.Path(tmp)
            (project_root / "AGENTS.md").write_text(
                "<!-- daw-config:start -->\n<!-- daw-config:end -->\n", encoding="utf-8"
            )
            plans = project_root / "docs" / "plans"
            plans.mkdir(parents=True)
            (plans / "plan.md").write_text("# Plan\n", encoding="utf-8")
            proc = self._run_session_start(project_root)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            data = json.loads(proc.stdout)
            self.assertEqual(data["status"], "ready")
            self.assertEqual(data["stages"], ["daw-plan", "daw-build", "daw-review", "daw-verify"])
            self.assertFalse(any(b["code"] == "REQUEST_INVALID_INTENT" for b in data["blockers"]))
            self.assertTrue(any("recommend feature" in r for r in data["reasons"]))

    def test_session_start_suggestion_mapping(self):
        script_path = str(REPO_ROOT / "scripts" / "route.py")
        cases = [
            ("evidence", {"AGENTS.md": "<!-- daw-config:start -->\n<!-- daw-config:end -->\n", "docs/evidence/e.md": "evidence\n"}, ["daw-ship"]),
            ("evidence-relocated", {"AGENTS.md": "<!-- daw-config:start -->\n<!-- daw-config:end -->\n", "docs/daw/evidence/e.md": "evidence\n"}, ["daw-ship"]),
            ("workflows", {"AGENTS.md": "<!-- daw-config:start -->\n<!-- daw-config:end -->\n", "docs/workflows/w.md": "# Workflow\n"}, ["daw-review"]),
            ("workflows-relocated", {"AGENTS.md": "<!-- daw-config:start -->\n<!-- daw-config:end -->\n", "docs/daw/workflows/w.md": "# Workflow\n"}, ["daw-review"]),
            ("specs", {"AGENTS.md": "<!-- daw-config:start -->\n<!-- daw-config:end -->\n", "docs/specs/prd.md": "# PRD\n"}, ["daw-plan", "daw-build", "daw-review", "daw-verify"]),
            ("bootstrap", {"AGENTS.md": "<!-- daw-config:start -->\n<!-- daw-config:end -->\n"}, ["daw-wizard", "daw-design", "daw-plan"]),
            ("setup", {}, ["daw-setup"]),
        ]
        for name, files, expected_stages in cases:
            with self.subTest(case=name):
                with tempfile.TemporaryDirectory() as tmp:
                    project_root = pathlib.Path(tmp)
                    for rel, content in files.items():
                        target = project_root / rel
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_text(content, encoding="utf-8")
                    cmd = [sys.executable, script_path, "--session-start", "--root", str(self.suite_root), "--project-root", str(project_root)]
                    proc = subprocess.run(cmd, capture_output=True, text=True)
                    self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
                    data = json.loads(proc.stdout)
                    self.assertEqual(data["status"], "ready")
                    self.assertEqual(data["stages"], expected_stages)
                    self.assertFalse(any(b["code"] == "REQUEST_INVALID_INTENT" for b in data["blockers"]))

    def test_session_start_uses_cwd_without_project_root_flag(self):
        script_path = str(REPO_ROOT / "scripts" / "route.py")
        with tempfile.TemporaryDirectory() as tmp:
            project_root = pathlib.Path(tmp)
            (project_root / "AGENTS.md").write_text(
                "<!-- daw-config:start -->\n<!-- daw-config:end -->\n", encoding="utf-8"
            )
            (project_root / "docs" / "workflows").mkdir(parents=True)
            (project_root / "docs" / "workflows" / "w.md").write_text("# Workflow\n", encoding="utf-8")
            cmd = [sys.executable, script_path, "--session-start", "--root", str(self.suite_root)]
            proc = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            data = json.loads(proc.stdout)
            self.assertEqual(data["status"], "ready")
            self.assertEqual(data["stages"], ["daw-review"])

    def test_feature_route_accepts_pre_enterprise_keys(self):
        clean = self._clean_manifest()
        data = json.loads(json.dumps(clean))
        feature = data["routes"]["feature"]
        for key in ("conditional_stages", "parallel_groups", "extension_hooks"):
            feature.pop(key, None)
        self._write_manifest(data)
        self.assertEqual(route.check_suite(self.suite_root), [])

        req = make_request(intent="feature", requirements="clear", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["stages"], ["daw-plan", "daw-build", "daw-review", "daw-verify"])

        # Unknown keys are still rejected.
        data["routes"]["feature"]["unexpected_extra"] = True
        self._write_manifest(data)
        findings = route.check_suite(self.suite_root)
        self.assertTrue(any(f["code"] == "MANIFEST_ROUTE_SHAPE_INVALID" for f in findings))

        # Missing canonical keys are still rejected.
        data = json.loads(json.dumps(clean))
        data["routes"]["feature"].pop("evaluates_workspace")
        self._write_manifest(data)
        findings = route.check_suite(self.suite_root)
        self.assertTrue(any(f["code"] == "MANIFEST_ROUTE_SHAPE_INVALID" for f in findings))

    def test_conditional_stage_placement_validation(self):
        clean = self._clean_manifest()
        cases = [
            ("insert_before_unknown", {"stage": "daw-review", "if": "risk == 'high'", "insert_before": "daw-nope"}),
            ("insert_after_unknown", {"stage": "daw-review", "if": "risk == 'high'", "insert_after": "daw-nope"}),
            ("both_placements", {"stage": "daw-review", "if": "risk == 'high'", "insert_before": "daw-build", "insert_after": "daw-verify"}),
            ("unknown_stage", {"stage": "daw-nope", "if": "risk == 'high'", "insert_before": "daw-build"}),
            ("insert_before_not_string", {"stage": "daw-review", "if": "risk == 'high'", "insert_before": ["daw-build"]}),
        ]
        for name, cs in cases:
            with self.subTest(case=name):
                data = json.loads(json.dumps(clean))
                data["routes"]["bugfix"]["conditional_stages"] = [cs]
                self._write_manifest(data)
                findings = route.check_suite(self.suite_root)
                self.assertTrue(any(f["code"] == "MANIFEST_ROUTE_CONDITIONAL_INVALID" for f in findings), name)

        # A well-formed conditional stage validates and resolves at runtime.
        data = json.loads(json.dumps(clean))
        data["routes"]["bugfix"]["conditional_stages"] = [
            {"stage": "daw-ask", "if": "risk == 'high'", "insert_before": "daw-verify"}
        ]
        self._write_manifest(data)
        self.assertEqual(route.check_suite(self.suite_root), [])
        req = make_request(intent="bugfix", requirements="clear", risk="high", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["stages"], ["daw-debug", "daw-plan", "daw-build", "daw-review", "daw-ask", "daw-verify"])
        req = make_request(intent="bugfix", requirements="clear", risk="low", workspace="in-place")
        res = route.resolve_route(req, root=self.suite_root)
        self.assertEqual(res["stages"], ["daw-debug", "daw-plan", "daw-build", "daw-review", "daw-verify"])

    def test_condition_expression_grammar_validation(self):
        clean = self._clean_manifest()
        cases = [
            ("risk == high", True),
            ("risk == 'high'", False),
            ("requirements == 'unclear' AND risk == 'high'", False),
            ("requirements == 'unclear' OR risk == 'high'", False),
            ("NOT risk == 'high'", False),
            ("(requirements == 'unclear') AND (risk == 'high')", False),
            ("risk != 'high'", False),
            ("intent == 'ship' AND risk > 1", False),
            ("risk == 'high' AND", True),
            ("risk == 'high' unknown_token", True),
            ("risk == ", True),
            ("(risk == 'high'", True),
            ("", True),
        ]
        for expr, should_fail in cases:
            with self.subTest(expr=expr):
                data = json.loads(json.dumps(clean))
                data["routes"]["bugfix"]["conditional_stages"] = [
                    {"stage": "daw-ask", "if": expr, "insert_before": "daw-verify"}
                ]
                self._write_manifest(data)
                findings = route.check_suite(self.suite_root)
                has_finding = any(
                    f["code"] == "MANIFEST_ROUTE_CONDITIONAL_INVALID" and "if" in f["message"]
                    for f in findings
                )
                self.assertEqual(has_finding, should_fail, expr)
        # The unquoted-literal failure names the unknown identifier.
        data = json.loads(json.dumps(clean))
        data["routes"]["bugfix"]["conditional_stages"] = [
            {"stage": "daw-ask", "if": "risk == high", "insert_before": "daw-verify"}
        ]
        self._write_manifest(data)
        findings = route.check_suite(self.suite_root)
        self.assertTrue(any("Unknown identifier 'high'" in f["message"] for f in findings))

    def test_parallel_groups_and_extension_hooks_validation(self):
        clean = self._clean_manifest()
        data = json.loads(json.dumps(clean))
        data["routes"]["bugfix"]["parallel_groups"] = [["daw-build", "daw-nope"]]
        self._write_manifest(data)
        self.assertTrue(any(f["code"] == "MANIFEST_ROUTE_PARALLEL_INVALID" for f in route.check_suite(self.suite_root)))

        data = json.loads(json.dumps(clean))
        data["routes"]["bugfix"]["parallel_groups"] = [["daw-build", 1]]
        self._write_manifest(data)
        self.assertTrue(any(f["code"] == "MANIFEST_ROUTE_PARALLEL_INVALID" for f in route.check_suite(self.suite_root)))

        data = json.loads(json.dumps(clean))
        data["routes"]["bugfix"]["extension_hooks"] = {"after_build": [1]}
        self._write_manifest(data)
        self.assertTrue(any(f["code"] == "MANIFEST_ROUTE_HOOKS_INVALID" for f in route.check_suite(self.suite_root)))

    def test_flow_gate_rejects_never_gated_intent(self):
        script_path = str(REPO_ROOT / "scripts" / "route.py")
        data = self._clean_manifest()
        data["flow_gate"]["affected_intents"] = ["feature", "review"]
        self._write_manifest(data)
        findings = route.check_suite(self.suite_root)
        self.assertTrue(any(f["code"] == "MANIFEST_FLOW_GATE_NEVER_GATED_INTENT" for f in findings))
        cmd = [sys.executable, script_path, "--check-suite", "--root", str(self.suite_root)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)

    def test_flow_gate_unreadable_on_deeply_nested_mapping(self):
        script_path = str(REPO_ROOT / "scripts" / "route.py")
        flow_file = self.suite_root / "references" / "best-practice-flow.md"
        deep_json = '{"steps": ' + "[" * 200000 + "]" * 200000 + "}"
        flow_file.write_text("```json\n" + deep_json + "\n```\n", encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            project_root = pathlib.Path(tmp)
            req_file = self.suite_root / "request.json"
            req_file.write_text(
                json.dumps(make_request(intent="feature", requirements="clear", risk="low", workspace="in-place")),
                encoding="utf-8",
            )
            cmd = [sys.executable, script_path, str(req_file), "--root", str(self.suite_root), "--project-root", str(project_root)]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotIn("Traceback", proc.stderr)
            self.assertEqual(proc.returncode, 1)
            data = json.loads(proc.stdout)
            self.assertEqual(data["status"], "blocked")
            self.assertTrue(any(b["code"] == "FLOW_GATE_UNREADABLE" for b in data["blockers"]))


if __name__ == "__main__":
    unittest.main()
