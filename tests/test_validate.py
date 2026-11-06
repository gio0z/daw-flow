"""Unit tests for standalone Agent Skills package and task contract validator CLI.

These tests invoke the CLI via subprocess against temporary synthetic
packages and project workspaces, verifying standard CLI behavior, JSON output
envelopes, exit codes, and security invariants.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import shutil
import tempfile
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATOR_SCRIPT = PROJECT_ROOT / "scripts" / "validate.py"

CANONICAL_TEMPLATES = (
    "blueprint.md",
    "brd.md",
    "deployment.md",
    "design.md",
    "frd.md",
    "prd.md",
    "qa.md",
    "roadmap.md",
    "runbook.md",
    "security.md",
    "techstack.md",
    "ui-ux.md",
    "wireframe.md",
)


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class TestValidateCLI(unittest.TestCase):
    def run_cli(
        self,
        args: list[str],
        cwd: pathlib.Path | None = None,
        script_path: pathlib.Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        target_script = script_path or VALIDATOR_SCRIPT
        cmd = [sys.executable, str(target_script)] + args
        return subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
        )

    def create_minimal_package_fixture(
        self,
        base_dir: pathlib.Path,
        pkg_name: str = "deterministic-agentic-workflow",
        colon_inside_bold: bool = False,
    ) -> pathlib.Path:
        pkg_root = base_dir / pkg_name
        pkg_root.mkdir(parents=True, exist_ok=True)

        skill_md = (
            "---\n"
            f"name: {pkg_name}\n"
            "description: Deterministic agentic workflow standard.\n"
            "compatibility: Python 3.10+\n"
            "---\n\n"
            "# Deterministic Agentic Workflow\n\n"
            "See [routing](references/routing.md) and [operations](references/operations.md).\n"
            "Templates are available in [templates](templates/blueprint.md).\n"
            "Read [validation](references/validation.md) and [installation](references/installation.md).\n"
        )
        (pkg_root / "SKILL.md").write_text(skill_md, encoding="utf-8")

        refs = pkg_root / "references"
        refs.mkdir(exist_ok=True)
        (refs / "operations.md").write_text("# Operations Reference\n", encoding="utf-8")
        (refs / "validation.md").write_text("# Validation Guide\n", encoding="utf-8")
        (refs / "installation.md").write_text("# Installation Reference\n", encoding="utf-8")

        routing_content = ["# Routing Reference\n"]
        for idx, tpl in enumerate(CANONICAL_TEMPLATES, start=1):
            if colon_inside_bold:
                routing_content.append(
                    f"### {idx}. `{tpl}`\n\n"
                    "- **Trigger:** Initial scoping.\n"
                    "- **Inputs & Prerequisites:** Clean baseline.\n"
                    "- **Required Capability:** System Architecture & Planning.\n"
                    "- **Conditional Capabilities:** None.\n"
                    f"- **Template Link:** [template](../templates/{tpl})\n"
                    "- **Output Contract:** Canonical specification.\n"
                    "- **Exit Criterion:** Acceptance agreed.\n"
                    "- **Downstream Handoff:** Next phase.\n"
                    "- **Stop / Replan Trigger:** Scope drift.\n"
                )
            else:
                routing_content.append(
                    f"### {idx}. `{tpl}`\n\n"
                    "- **Trigger**: Initial scoping.\n"
                    "- **Inputs & Prerequisites**: Clean baseline.\n"
                    "- **Required Capability**: System Architecture & Planning.\n"
                    "- **Conditional Capabilities**: None.\n"
                    f"- **Template Link**: [template](../templates/{tpl})\n"
                    "- **Output Contract**: Canonical specification.\n"
                    "- **Exit Criterion**: Acceptance agreed.\n"
                    "- **Downstream Handoff**: Next phase.\n"
                    "- **Stop / Replan Trigger**: Scope drift.\n"
                )
        (refs / "routing.md").write_text("\n".join(routing_content), encoding="utf-8")

        (refs / "task-contract.example.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "objective": "Example task",
                    "baseline": {"revision": "rev-1", "files": []},
                    "documents": [],
                    "acceptance_criteria": [{"id": "AC-1", "criterion": "Done"}],
                    "operation": {
                        "risk": "low",
                        "action": "noop",
                        "target": "target",
                        "revision": "rev-1",
                        "scope": ["src/"],
                    },
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        templates_dir = pkg_root / "templates"
        templates_dir.mkdir(exist_ok=True)
        for tpl in CANONICAL_TEMPLATES:
            (templates_dir / tpl).write_text(f"# Template {tpl}\n", encoding="utf-8")

        scripts_dir = pkg_root / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        if VALIDATOR_SCRIPT.exists():
            (scripts_dir / "validate.py").write_text(
                VALIDATOR_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8"
            )
        else:
            (scripts_dir / "validate.py").write_text(
                "# Validator script placeholder\n", encoding="utf-8"
            )

        tests_dir = pkg_root / "tests"
        tests_dir.mkdir(exist_ok=True)
        (tests_dir / "test_validate.py").write_text("# Tests stub\n", encoding="utf-8")

        return pkg_root

    def create_minimal_project_fixture(
        self,
        base_dir: pathlib.Path,
        files: dict[str, str] | None = None,
    ) -> tuple[pathlib.Path, list[dict[str, str]]]:
        proj_dir = base_dir / "project"
        proj_dir.mkdir(parents=True, exist_ok=True)

        if files is None:
            files = {"src/app.py": "print('hello world')\n"}

        baseline_entries = []
        for rel_path, content in files.items():
            full_path = proj_dir / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            encoded = content.encode("utf-8")
            full_path.write_bytes(encoded)
            baseline_entries.append({"path": rel_path, "sha256": _sha256(encoded)})

        return proj_dir, baseline_entries

    def create_contract_dict(
        self,
        revision: str = "rev-001",
        baseline_files: list[dict[str, str]] | None = None,
        risk: str = "low",
        scope: list[str] | None = None,
        documents: list[dict[str, str]] | None = None,
        acceptance_criteria: list[dict[str, str]] | None = None,
        approval: dict | None = None,
        evidence: list[dict] | None = None,
    ) -> dict:
        if baseline_files is None:
            baseline_files = []
        if scope is None:
            scope = ["src/"]
        if documents is None:
            documents = []
        if acceptance_criteria is None:
            acceptance_criteria = [{"id": "AC-1", "criterion": "Core functionality works"}]

        contract: dict = {
            "schema_version": 1,
            "objective": "Execute safe deterministic change",
            "baseline": {
                "revision": revision,
                "files": baseline_files,
            },
            "documents": documents,
            "acceptance_criteria": acceptance_criteria,
            "operation": {
                "risk": risk,
                "action": "refactor",
                "target": "core_module",
                "revision": revision,
                "scope": scope,
            },
        }
        if approval is not None:
            contract["approval"] = approval
        if evidence is not None:
            contract["evidence"] = evidence
        return contract

    # -------------------------------------------------------------------------
    # Package validation tests
    # -------------------------------------------------------------------------

    def test_package_valid_synthetic_bundle_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_root = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
            res = self.run_cli(["package", "--root", str(pkg_root), "--format", "json"])
            self.assertEqual(res.returncode, 0, msg=f"CLI failed: {res.stderr}\n{res.stdout}")
            payload = json.loads(res.stdout)
            self.assertEqual(payload.get("schema_version"), 1)
            self.assertEqual(payload.get("check"), "package")
            self.assertTrue(payload.get("valid"))
            self.assertIsInstance(payload.get("findings"), list)
            self.assertIsInstance(payload.get("limitations"), list)

    def test_package_valid_colon_inside_bold_labels(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_root = self.create_minimal_package_fixture(
                pathlib.Path(tmpdir), colon_inside_bold=True
            )
            res = self.run_cli(["package", "--root", str(pkg_root), "--format", "json"])
            self.assertEqual(res.returncode, 0, msg=f"CLI failed: {res.stderr}\n{res.stdout}")
            payload = json.loads(res.stdout)
            self.assertTrue(payload.get("valid"))

    def test_package_text_format_output_meaningful(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_root = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
            res = self.run_cli(["package", "--root", str(pkg_root), "--format", "text"])
            self.assertEqual(res.returncode, 0, msg=f"CLI failed: {res.stderr}\n{res.stdout}")
            self.assertTrue(len(res.stdout.strip()) > 0)
            self.assertIn("valid", res.stdout.lower())

    def test_package_root_independent_of_cwd(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = pathlib.Path(tmpdir)
            pkg_root = self.create_minimal_package_fixture(tmp_path)
            copied_script = pkg_root / "scripts" / "validate.py"
            other_dir = tmp_path / "somewhere_else"
            other_dir.mkdir()

            res = self.run_cli(
                ["package", "--format", "json"],
                cwd=other_dir,
                script_path=copied_script,
            )
            self.assertEqual(res.returncode, 0, msg=f"CLI failed: {res.stderr}\n{res.stdout}")
            payload = json.loads(res.stdout)
            self.assertTrue(payload.get("valid"))

    def test_package_missing_required_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_root = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
            (pkg_root / "references" / "operations.md").unlink()

            res = self.run_cli(["package", "--root", str(pkg_root), "--format", "json"])
            self.assertEqual(res.returncode, 1)
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))
            errors = [f for f in payload["findings"] if f.get("severity") == "error"]
            self.assertTrue(any("operations.md" in f.get("path", "") or "operations.md" in f.get("message", "") for f in errors))

    def test_package_without_tests_directory_validates_successfully(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_root = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
            shutil.rmtree(pkg_root / "tests", ignore_errors=True)

            res = self.run_cli(["package", "--root", str(pkg_root), "--format", "json"])
            self.assertEqual(res.returncode, 0, msg=f"Validation failed: {res.stderr}\n{res.stdout}")
            payload = json.loads(res.stdout)
            self.assertTrue(payload.get("valid"))
            errors = [f for f in payload["findings"] if f.get("severity") == "error"]
            self.assertEqual(errors, [])

    def test_package_missing_validator_script(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_root = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
            (pkg_root / "scripts" / "validate.py").unlink()

            res = self.run_cli(["package", "--root", str(pkg_root), "--format", "json"])
            self.assertEqual(res.returncode, 1)
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))
            errors = [f for f in payload["findings"] if f.get("severity") == "error"]
            self.assertTrue(any("validate.py" in f.get("path", "") for f in errors))
    def test_package_unrelated_templates_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_root = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
            (pkg_root / "templates" / "extra_unknown.md").write_text("# Extra\n", encoding="utf-8")

            res = self.run_cli(["package", "--root", str(pkg_root), "--format", "json"])
            self.assertEqual(res.returncode, 1)
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))

    def test_package_broken_local_markdown_link(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_root = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
            with open(pkg_root / "SKILL.md", "a", encoding="utf-8") as f:
                f.write("\nSee [missing docs](references/nonexistent.md)\n")

            res = self.run_cli(["package", "--root", str(pkg_root), "--format", "json"])
            self.assertEqual(res.returncode, 1)
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))

    def test_package_rejects_skill_uri(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_root = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
            with open(pkg_root / "references" / "operations.md", "a", encoding="utf-8") as f:
                f.write("\nInvoke skill://some-managed-tool directly.\n")

            res = self.run_cli(["package", "--root", str(pkg_root), "--format", "json"])
            self.assertEqual(res.returncode, 1)
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))

    def test_package_unbalanced_code_fence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_root = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
            with open(pkg_root / "references" / "validation.md", "a", encoding="utf-8") as f:
                f.write("\n```bash\nUnclosed code block\n")

            res = self.run_cli(["package", "--root", str(pkg_root), "--format", "json"])
            self.assertEqual(res.returncode, 1)
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))

    def test_package_traversal_escape_link_blocked(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_root = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
            with open(pkg_root / "SKILL.md", "a", encoding="utf-8") as f:
                f.write("\n[escape link](../../etc/passwd)\n")

            res = self.run_cli(["package", "--root", str(pkg_root), "--format", "json"])
            self.assertEqual(res.returncode, 1)
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))

    def test_package_frontmatter_metadata_validation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_root = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
            long_desc = "x" * 1050
            (pkg_root / "SKILL.md").write_text(
                f"---\nname: deterministic-agentic-workflow\ndescription: >-\n  {long_desc}\n---\n# Title\n",
                encoding="utf-8",
            )
            res = self.run_cli(["package", "--root", str(pkg_root), "--format", "json"])
            self.assertEqual(res.returncode, 1)
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))

    def test_package_routing_missing_required_labels(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_root = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
            routing_text = (pkg_root / "references" / "routing.md").read_text(encoding="utf-8")
            routing_text = routing_text.replace("- **Exit Criterion**: Acceptance agreed.\n", "")
            (pkg_root / "references" / "routing.md").write_text(routing_text, encoding="utf-8")

            res = self.run_cli(["package", "--root", str(pkg_root), "--format", "json"])
            self.assertEqual(res.returncode, 1)
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))

    def test_package_routing_missing_required_capability_field(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_root = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
            routing_text = (pkg_root / "references" / "routing.md").read_text(encoding="utf-8")
            routing_text = routing_text.replace("- **Required Capability**: System Architecture & Planning.\n", "")
            (pkg_root / "references" / "routing.md").write_text(routing_text, encoding="utf-8")

            res = self.run_cli(["package", "--root", str(pkg_root), "--format", "json"])
            self.assertEqual(res.returncode, 1)
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))
            self.assertTrue(any(f.get("code") == "routing_field_missing" and "Required Capability" in f.get("message", "") for f in payload.get("findings", [])))

    # -------------------------------------------------------------------------
    # Contract validation tests (Plan, Execute, Complete)
    # -------------------------------------------------------------------------

    def test_contract_plan_valid_tiny_patch_zero_docs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, _ = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            contract_data = self.create_contract_dict(documents=[])
            contract_file = proj_dir / "contract.json"
            contract_file.write_text(json.dumps(contract_data), encoding="utf-8")

            res = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "plan",
                "--format", "json",
            ])
            self.assertEqual(res.returncode, 0, msg=f"CLI failed: {res.stderr}\n{res.stdout}")
            payload = json.loads(res.stdout)
            self.assertTrue(payload.get("valid"))
            warnings = [f for f in payload.get("findings", []) if f.get("severity") == "warning"]
            self.assertTrue(any("baseline" in f.get("code", "").lower() for f in warnings))

    def test_contract_text_format_output_meaningful(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, _ = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            contract_data = self.create_contract_dict(documents=[])
            contract_file = proj_dir / "contract.json"
            contract_file.write_text(json.dumps(contract_data), encoding="utf-8")

            res = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "plan",
                "--format", "text",
            ])
            self.assertEqual(res.returncode, 0, msg=f"CLI failed: {res.stderr}\n{res.stdout}")
            self.assertTrue(len(res.stdout.strip()) > 0)
            self.assertIn("valid", res.stdout.lower())

    def test_contract_draft_allowed_in_plan_rejected_in_execute(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, baseline = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            doc_path = proj_dir / "docs" / "frd.md"
            doc_path.parent.mkdir(parents=True, exist_ok=True)
            doc_path.write_text("# FRD Draft\n", encoding="utf-8")

            contract_data = self.create_contract_dict(
                baseline_files=baseline,
                documents=[{"kind": "frd", "path": "docs/frd.md", "status": "draft"}],
            )
            contract_file = proj_dir / "contract.json"
            contract_file.write_text(json.dumps(contract_data), encoding="utf-8")

            res_plan = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "plan",
                "--format", "json",
            ])
            self.assertEqual(res_plan.returncode, 0, msg=f"Plan failed: {res_plan.stderr}\n{res_plan.stdout}")
            self.assertTrue(json.loads(res_plan.stdout).get("valid"))

            res_exec = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "execute",
                "--format", "json",
            ])
            self.assertEqual(res_exec.returncode, 1)
            self.assertFalse(json.loads(res_exec.stdout).get("valid"))

            res_comp = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "complete",
                "--format", "json",
            ])
            self.assertEqual(res_comp.returncode, 1)
            self.assertFalse(json.loads(res_comp.stdout).get("valid"))

    def test_contract_stale_or_conflicting_doc_rejected_in_all_stages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, baseline = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            doc_path = proj_dir / "docs" / "techstack.md"
            doc_path.parent.mkdir(parents=True, exist_ok=True)
            doc_path.write_text("# Techstack\n", encoding="utf-8")

            for bad_status in ("stale", "conflicting"):
                contract_data = self.create_contract_dict(
                    baseline_files=baseline,
                    documents=[{"kind": "techstack", "path": "docs/techstack.md", "status": bad_status}],
                )
                contract_file = proj_dir / "contract.json"
                contract_file.write_text(json.dumps(contract_data), encoding="utf-8")

                for stage in ("plan", "execute", "complete"):
                    res = self.run_cli([
                        "contract", str(contract_file),
                        "--project-root", str(proj_dir),
                        "--stage", stage,
                        "--format", "json",
                    ])
                    self.assertEqual(
                        res.returncode,
                        1,
                        msg=f"Stage {stage} should reject status {bad_status}",
                    )
                    self.assertFalse(json.loads(res.stdout).get("valid"))

    def test_contract_existing_doc_alias_path_accepted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, baseline = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            doc_path = proj_dir / "specs" / "design-system.md"
            doc_path.parent.mkdir(parents=True, exist_ok=True)
            doc_path.write_text("# Design Spec\n", encoding="utf-8")

            contract_data = self.create_contract_dict(
                baseline_files=baseline,
                documents=[{"kind": "design", "path": "specs/design-system.md", "status": "current"}],
            )
            contract_file = proj_dir / "contract.json"
            contract_file.write_text(json.dumps(contract_data), encoding="utf-8")

            res = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "execute",
                "--format", "json",
            ])
            self.assertEqual(res.returncode, 0, msg=f"CLI failed: {res.stderr}\n{res.stdout}")
            self.assertTrue(json.loads(res.stdout).get("valid"))

    def test_contract_baseline_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, baseline = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            corrupt_baseline = [{"path": baseline[0]["path"], "sha256": "0" * 64}]

            contract_data = self.create_contract_dict(baseline_files=corrupt_baseline)
            contract_file = proj_dir / "contract.json"
            contract_file.write_text(json.dumps(contract_data), encoding="utf-8")

            res = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "execute",
                "--format", "json",
            ])
            self.assertEqual(res.returncode, 1)
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))
            errors = [f for f in payload.get("findings", []) if f.get("severity") == "error"]
            self.assertTrue(any("baseline" in f.get("code", "").lower() for f in errors))

    def test_contract_execute_requires_at_least_one_baseline_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, _ = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            contract_data = self.create_contract_dict(baseline_files=[])
            contract_file = proj_dir / "contract.json"
            contract_file.write_text(json.dumps(contract_data), encoding="utf-8")

            res = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "execute",
                "--format", "json",
            ])
            self.assertEqual(res.returncode, 1)
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))

    def test_contract_scope_empty_or_duplicate_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, baseline = self.create_minimal_project_fixture(pathlib.Path(tmpdir))

            # Empty scope
            contract_empty = self.create_contract_dict(baseline_files=baseline, scope=[])
            cfile_empty = proj_dir / "contract_empty.json"
            cfile_empty.write_text(json.dumps(contract_empty), encoding="utf-8")
            res = self.run_cli([
                "contract", str(cfile_empty),
                "--project-root", str(proj_dir),
                "--stage", "plan",
                "--format", "json",
            ])
            self.assertEqual(res.returncode, 1)
            self.assertFalse(json.loads(res.stdout).get("valid"))

            # Duplicate scope items
            contract_dup = self.create_contract_dict(
                baseline_files=baseline, scope=["src/app.py", "src/app.py"]
            )
            cfile_dup = proj_dir / "contract_dup.json"
            cfile_dup.write_text(json.dumps(contract_dup), encoding="utf-8")
            res_dup = self.run_cli([
                "contract", str(cfile_dup),
                "--project-root", str(proj_dir),
                "--stage", "plan",
                "--format", "json",
            ])
            self.assertEqual(res_dup.returncode, 1)
            self.assertFalse(json.loads(res_dup.stdout).get("valid"))

    def test_contract_duplicate_acceptance_criteria_id_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, baseline = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            contract_data = self.create_contract_dict(
                baseline_files=baseline,
                acceptance_criteria=[
                    {"id": "AC-1", "criterion": "Passes test A"},
                    {"id": "AC-1", "criterion": "Passes test B"},
                ],
            )
            contract_file = proj_dir / "contract.json"
            contract_file.write_text(json.dumps(contract_data), encoding="utf-8")

            res = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "plan",
                "--format", "json",
            ])
            self.assertEqual(res.returncode, 1)
            self.assertFalse(json.loads(res.stdout).get("valid"))

    def test_contract_high_risk_missing_approval_at_execute(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, baseline = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            contract_data = self.create_contract_dict(
                baseline_files=baseline,
                risk="high",
                approval=None,
            )
            contract_file = proj_dir / "contract.json"
            contract_file.write_text(json.dumps(contract_data), encoding="utf-8")

            res = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "execute",
                "--format", "json",
            ])
            self.assertEqual(res.returncode, 1)
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))

    def test_contract_approval_binding_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, baseline = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            contract_data = self.create_contract_dict(
                baseline_files=baseline,
                risk="high",
                scope=["src/app.py"],
                approval={
                    "reference": "approval-ticket-42",
                    "action": "refactor",
                    "target": "core_module",
                    "revision": "rev-001",
                    "scope": ["src/other.py"],
                },
            )
            contract_file = proj_dir / "contract.json"
            contract_file.write_text(json.dumps(contract_data), encoding="utf-8")

            res = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "execute",
                "--format", "json",
            ])
            self.assertEqual(res.returncode, 1)
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))

    def test_contract_valid_high_risk_with_matching_approval(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, baseline = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            scope = ["src/app.py"]
            contract_data = self.create_contract_dict(
                baseline_files=baseline,
                risk="high",
                scope=scope,
                approval={
                    "reference": "RFC-789",
                    "action": "refactor",
                    "target": "core_module",
                    "revision": "rev-001",
                    "scope": scope,
                },
            )
            contract_file = proj_dir / "contract.json"
            contract_file.write_text(json.dumps(contract_data), encoding="utf-8")

            res = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "execute",
                "--format", "json",
            ])
            self.assertEqual(res.returncode, 0, msg=f"CLI failed: {res.stderr}\n{res.stdout}")
            payload = json.loads(res.stdout)
            self.assertTrue(payload.get("valid"))

    def test_contract_complete_stage_requires_all_passed_evidence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, baseline = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            ev_file = proj_dir / "test-evidence.log"
            ev_file.write_text("All tests pass\n", encoding="utf-8")

            acs = [
                {"id": "AC-1", "criterion": "Passes unit tests"},
                {"id": "AC-2", "criterion": "Passes integration tests"},
            ]

            incomplete_evidence = [
                {
                    "criterion_id": "AC-1",
                    "status": "passed",
                    "reference": "test-evidence.log",
                    "summary": "Unit tests executed successfully",
                }
            ]
            contract_data = self.create_contract_dict(
                baseline_files=baseline,
                acceptance_criteria=acs,
                evidence=incomplete_evidence,
            )
            contract_file = proj_dir / "contract.json"
            contract_file.write_text(json.dumps(contract_data), encoding="utf-8")

            res_incomplete = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "complete",
                "--format", "json",
            ])
            self.assertEqual(res_incomplete.returncode, 1)
            self.assertFalse(json.loads(res_incomplete.stdout).get("valid"))

            complete_evidence = [
                {
                    "criterion_id": "AC-1",
                    "status": "passed",
                    "reference": "test-evidence.log",
                    "summary": "Unit tests passed",
                },
                {
                    "criterion_id": "AC-2",
                    "status": "passed",
                    "reference": "test-evidence.log",
                    "summary": "Integration tests passed",
                },
            ]
            contract_data["evidence"] = complete_evidence
            contract_file.write_text(json.dumps(contract_data), encoding="utf-8")

            res_complete = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "complete",
                "--format", "json",
            ])
            self.assertEqual(res_complete.returncode, 0, msg=f"Complete failed: {res_complete.stderr}\n{res_complete.stdout}")
            self.assertTrue(json.loads(res_complete.stdout).get("valid"))

    def test_contract_duplicate_evidence_criterion_id_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, baseline = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            ev_file = proj_dir / "test-evidence.log"
            ev_file.write_text("Evidence\n", encoding="utf-8")

            contract_data = self.create_contract_dict(
                baseline_files=baseline,
                evidence=[
                    {
                        "criterion_id": "AC-1",
                        "status": "passed",
                        "reference": "test-evidence.log",
                        "summary": "Run 1",
                    },
                    {
                        "criterion_id": "AC-1",
                        "status": "passed",
                        "reference": "test-evidence.log",
                        "summary": "Run 2 duplicate",
                    },
                ],
            )
            contract_file = proj_dir / "contract.json"
            contract_file.write_text(json.dumps(contract_data), encoding="utf-8")

            res = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "complete",
                "--format", "json",
            ])
            self.assertEqual(res.returncode, 1)
            self.assertFalse(json.loads(res.stdout).get("valid"))

    def test_contract_evidence_unknown_ac_id_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, baseline = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            ev_file = proj_dir / "report.txt"
            ev_file.write_text("Report\n", encoding="utf-8")

            contract_data = self.create_contract_dict(
                baseline_files=baseline,
                evidence=[{
                    "criterion_id": "NON-EXISTENT",
                    "status": "passed",
                    "reference": "report.txt",
                    "summary": "Unknown ref",
                }],
            )
            contract_file = proj_dir / "contract.json"
            contract_file.write_text(json.dumps(contract_data), encoding="utf-8")

            res = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "plan",
                "--format", "json",
            ])
            self.assertEqual(res.returncode, 1)
            self.assertFalse(json.loads(res.stdout).get("valid"))

    def test_contract_evidence_scalar_or_bool_rejected_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, baseline = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            for bad_evidence in (42, True):
                contract_data = self.create_contract_dict(
                    baseline_files=baseline,
                    evidence=bad_evidence,
                )
                contract_file = proj_dir / "contract.json"
                contract_file.write_text(json.dumps(contract_data), encoding="utf-8")

                res = self.run_cli([
                    "contract", str(contract_file),
                    "--project-root", str(proj_dir),
                    "--stage", "complete",
                    "--format", "json",
                ])
                self.assertEqual(res.returncode, 1)
                self.assertNotIn("Traceback", res.stderr)
                payload = json.loads(res.stdout)
                self.assertFalse(payload.get("valid"))
                error_codes = [f.get("code") for f in payload.get("findings", [])]
                self.assertIn("invalid_evidence", error_codes)
                self.assertIn("missing_complete_evidence", error_codes)

    def test_contract_evidence_unhashable_criterion_id_rejected_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, baseline = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            ev_file = proj_dir / "smoke.log"
            ev_file.write_text("observed output\n", encoding="utf-8")
            for bad_id in (["AC-1"], {"id": "AC-1"}):
                contract_data = self.create_contract_dict(
                    baseline_files=baseline,
                    evidence=[{
                        "criterion_id": bad_id,
                        "status": "passed",
                        "reference": "smoke.log",
                        "summary": "observed",
                    }],
                )
                contract_file = proj_dir / "contract.json"
                contract_file.write_text(json.dumps(contract_data), encoding="utf-8")

                res = self.run_cli([
                    "contract", str(contract_file),
                    "--project-root", str(proj_dir),
                    "--stage", "complete",
                    "--format", "json",
                ])
                self.assertEqual(res.returncode, 1)
                self.assertNotIn("Traceback", res.stderr)
                payload = json.loads(res.stdout)
                self.assertFalse(payload.get("valid"))
                error_codes = [f.get("code") for f in payload.get("findings", [])]
                self.assertIn("invalid_evidence_criterion_id", error_codes)
                self.assertIn("incomplete_evidence_coverage", error_codes)
    # -------------------------------------------------------------------------
    # Schema integrity, types, duplicate keys, and bounds checks
    # -------------------------------------------------------------------------

    def test_contract_rejects_bool_for_integer_schema_version(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, baseline = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            raw_json = (
                '{\n'
                '  "schema_version": true,\n'
                '  "objective": "Test bool rejected",\n'
                '  "baseline": {"revision": "rev-1", "files": []},\n'
                '  "documents": [],\n'
                '  "acceptance_criteria": [{"id": "AC-1", "criterion": "Pass"}],\n'
                '  "operation": {"risk": "low", "action": "test", "target": "t", "revision": "rev-1", "scope": ["s"]}\n'
                '}'
            )
            contract_file = proj_dir / "contract.json"
            contract_file.write_text(raw_json, encoding="utf-8")

            res = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "plan",
                "--format", "json",
            ])
            self.assertEqual(res.returncode, 1)
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))

    def test_contract_rejects_bool_in_string_arrays(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, baseline = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            raw_json = (
                '{\n'
                '  "schema_version": 1,\n'
                '  "objective": "Test bool in string array rejected",\n'
                '  "baseline": {"revision": "rev-1", "files": []},\n'
                '  "documents": [],\n'
                '  "acceptance_criteria": [{"id": "AC-1", "criterion": "Pass"}],\n'
                '  "operation": {"risk": "low", "action": "test", "target": "t", "revision": "rev-1", "scope": [true]}\n'
                '}'
            )
            contract_file = proj_dir / "contract.json"
            contract_file.write_text(raw_json, encoding="utf-8")

            res = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "plan",
                "--format", "json",
            ])
            self.assertEqual(res.returncode, 1)
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))

    def test_contract_rejects_unknown_top_level_and_nested_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, _ = self.create_minimal_project_fixture(pathlib.Path(tmpdir))

            # Top level unknown
            contract_top = self.create_contract_dict()
            contract_top["unexpected_field"] = "should_fail"
            cfile_top = proj_dir / "contract_top.json"
            cfile_top.write_text(json.dumps(contract_top), encoding="utf-8")

            res_top = self.run_cli([
                "contract", str(cfile_top),
                "--project-root", str(proj_dir),
                "--stage", "plan",
                "--format", "json",
            ])
            self.assertEqual(res_top.returncode, 1)
            self.assertFalse(json.loads(res_top.stdout).get("valid"))

            # Nested unknown field in operation
            contract_nested = self.create_contract_dict()
            contract_nested["operation"]["extra_op_key"] = "forbidden"
            cfile_nested = proj_dir / "contract_nested.json"
            cfile_nested.write_text(json.dumps(contract_nested), encoding="utf-8")

            res_nested = self.run_cli([
                "contract", str(cfile_nested),
                "--project-root", str(proj_dir),
                "--stage", "plan",
                "--format", "json",
            ])
            self.assertEqual(res_nested.returncode, 1)
            self.assertFalse(json.loads(res_nested.stdout).get("valid"))

    def test_contract_rejects_duplicate_json_keys_top_and_nested(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, _ = self.create_minimal_project_fixture(pathlib.Path(tmpdir))

            # Top-level duplicate key
            dup_top = (
                '{\n'
                '  "schema_version": 1,\n'
                '  "objective": "First",\n'
                '  "objective": "Duplicate Second",\n'
                '  "baseline": {"revision": "r", "files": []},\n'
                '  "documents": [],\n'
                '  "acceptance_criteria": [{"id": "AC-1", "criterion": "Pass"}],\n'
                '  "operation": {"risk": "low", "action": "a", "target": "t", "revision": "r", "scope": ["s"]}\n'
                '}'
            )
            cfile_top = proj_dir / "dup_top.json"
            cfile_top.write_text(dup_top, encoding="utf-8")

            res_top = self.run_cli([
                "contract", str(cfile_top),
                "--project-root", str(proj_dir),
                "--stage", "plan",
                "--format", "json",
            ])
            self.assertEqual(res_top.returncode, 2, msg="Duplicate key must yield exact exit 2")

            # Nested duplicate key in operation
            dup_nested = (
                '{\n'
                '  "schema_version": 1,\n'
                '  "objective": "Check nested dup",\n'
                '  "baseline": {"revision": "r", "files": []},\n'
                '  "documents": [],\n'
                '  "acceptance_criteria": [{"id": "AC-1", "criterion": "Pass"}],\n'
                '  "operation": {\n'
                '    "risk": "low",\n'
                '    "action": "first_action",\n'
                '    "action": "second_action",\n'
                '    "target": "t",\n'
                '    "revision": "r",\n'
                '    "scope": ["s"]\n'
                '  }\n'
                '}'
            )
            cfile_nested = proj_dir / "dup_nested.json"
            cfile_nested.write_text(dup_nested, encoding="utf-8")

            res_nested = self.run_cli([
                "contract", str(cfile_nested),
                "--project-root", str(proj_dir),
                "--stage", "plan",
                "--format", "json",
            ])
            self.assertEqual(res_nested.returncode, 2, msg="Nested duplicate key must yield exact exit 2")

    def test_contract_malformed_json_syntax(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, _ = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            contract_file = proj_dir / "broken.json"
            contract_file.write_text("{ this is not json }", encoding="utf-8")

            res = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--format", "json",
            ])
            self.assertEqual(res.returncode, 2)

    def test_contract_unreadable_non_utf8_input(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, _ = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            contract_file = proj_dir / "invalid_utf8.json"
            contract_file.write_bytes(b"\x80\x81\xff\xfe\x00\x01")

            res = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--format", "json",
            ])
            self.assertEqual(res.returncode, 2)
            self.assertNotIn("traceback", res.stderr.lower())

    def test_contract_missing_file_argument(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            res = self.run_cli([
                "contract", str(pathlib.Path(tmpdir) / "nonexistent.json"),
                "--project-root", tmpdir,
                "--format", "json",
            ])
            self.assertEqual(res.returncode, 2)

    # -------------------------------------------------------------------------
    # Security and isolation tests: Escapes, command execution, secret leaks
    # -------------------------------------------------------------------------

    def test_contract_path_traversal_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, baseline = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            contract_data = self.create_contract_dict(
                baseline_files=[{"path": "../outside.txt", "sha256": "a" * 64}],
            )
            contract_file = proj_dir / "contract.json"
            contract_file.write_text(json.dumps(contract_data), encoding="utf-8")

            res = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "plan",
                "--format", "json",
            ])
            self.assertEqual(res.returncode, 1)
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))

    def test_contract_absolute_file_path_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = pathlib.Path(tmpdir)
            proj_dir, _ = self.create_minimal_project_fixture(tmp_path)
            outside_abs = tmp_path / "outside_target.txt"
            outside_abs.write_text("outside", encoding="utf-8")

            contract_data = self.create_contract_dict(
                baseline_files=[{"path": str(outside_abs), "sha256": "a" * 64}],
            )
            contract_file = proj_dir / "contract.json"
            contract_file.write_text(json.dumps(contract_data), encoding="utf-8")

            res = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "plan",
                "--format", "json",
            ])
            self.assertEqual(res.returncode, 1)
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))

    def test_contract_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = pathlib.Path(tmpdir)
            outside_file = tmp_path / "secret.txt"
            outside_file.write_text("super-secret\n", encoding="utf-8")

            proj_dir, _ = self.create_minimal_project_fixture(tmp_path)
            link_path = proj_dir / "link_to_secret.txt"
            try:
                os.symlink(outside_file, link_path)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks not permitted in this environment")

            contract_data = self.create_contract_dict(
                baseline_files=[{"path": "link_to_secret.txt", "sha256": _sha256(b"super-secret\n")}],
            )
            contract_file = proj_dir / "contract.json"
            contract_file.write_text(json.dumps(contract_data), encoding="utf-8")

            res = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "plan",
                "--format", "json",
            ])
            self.assertEqual(res.returncode, 1)
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))

    def test_payload_command_like_text_never_executed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, baseline = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            marker_file = proj_dir / "RCE_EXECUTED"

            evil_command = f"touch {marker_file}"
            contract_data = self.create_contract_dict(
                baseline_files=baseline,
                acceptance_criteria=[{"id": "AC-1", "criterion": f"; {evil_command} ;"}],
            )
            contract_data["operation"]["action"] = f"$( {evil_command} )"
            contract_file = proj_dir / "contract.json"
            contract_file.write_text(json.dumps(contract_data), encoding="utf-8")

            res = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "plan",
                "--format", "json",
            ])
            self.assertEqual(res.returncode, 0, msg=f"Valid contract with command strings should pass: {res.stderr}")
            self.assertFalse(marker_file.exists(), "Command payload was unexpectedly executed!")

    def test_no_secret_leak_on_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, _ = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            secret_value = "SUPER_SECRET_TOKEN_DO_NOT_LEAK_XYZ123"

            bad_json = (
                '{\n'
                '  "schema_version": 1,\n'
                '  "objective": "Check no leaks",\n'
                f'  "baseline": "{secret_value}",\n'
                '  "documents": [],\n'
                '  "acceptance_criteria": [{"id": "AC-1", "criterion": "Pass"}],\n'
                '  "operation": {"risk": "low", "action": "test", "target": "t", "revision": "r", "scope": ["s"]}\n'
                '}'
            )
            contract_file = proj_dir / "contract.json"
            contract_file.write_text(bad_json, encoding="utf-8")

            res = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "plan",
                "--format", "json",
            ])
            self.assertEqual(res.returncode, 1, msg="Invalid field type must yield exit 1")
            combined_output = res.stdout + res.stderr
            self.assertNotIn(
                secret_value,
                combined_output,
                "Secret payload echoed in error output!",
            )

    def test_read_only_inputs_remain_unmodified(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, baseline = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            contract_data = self.create_contract_dict(baseline_files=baseline)
            contract_file = proj_dir / "contract.json"
            contract_content = json.dumps(contract_data, indent=2)
            contract_file.write_text(contract_content, encoding="utf-8")

            app_file = proj_dir / "src" / "app.py"
            app_before = app_file.read_bytes()

            res = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "plan",
                "--format", "json",
            ])
            self.assertEqual(res.returncode, 0, msg=f"Contract validation failed: {res.stderr}")

            self.assertEqual(contract_file.read_text(encoding="utf-8"), contract_content)
            self.assertEqual(app_file.read_bytes(), app_before)

    def test_package_skill_md_symlink_outside_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = pathlib.Path(tmpdir)
            outside_dir = tmp_path / "outside"
            outside_dir.mkdir()
            outside_skill = outside_dir / "SKILL.md"
            outside_skill.write_bytes(b"\xff\xfe\x00\x00invalid_utf8_binary")

            pkg_dir = self.create_minimal_package_fixture(tmp_path / "pkg")
            skill_link = pkg_dir / "SKILL.md"
            skill_link.unlink()
            try:
                os.symlink(outside_skill, skill_link)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks not permitted in this environment")

            res = self.run_cli(["package", "--root", str(pkg_dir), "--format", "json"])
            self.assertEqual(res.returncode, 1)
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))
            self.assertIsInstance(payload.get("findings"), list)
            error_findings = [f for f in payload["findings"] if f.get("severity") == "error"]
            self.assertTrue(len(error_findings) > 0, "Expected error findings for escaping SKILL.md symlink")
            self.assertNotIn("UnicodeDecodeError", res.stderr + res.stdout)

    def test_package_template_symlink_outside_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = pathlib.Path(tmpdir)
            outside_file = tmp_path / "outside_blueprint.md"
            outside_file.write_bytes(b"\xff\xfe\x00\x00invalid_utf8")

            pkg_dir = self.create_minimal_package_fixture(tmp_path / "pkg")
            tpl_file = pkg_dir / "templates" / "blueprint.md"
            tpl_file.unlink()
            try:
                os.symlink(outside_file, tpl_file)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks not permitted in this environment")

            res = self.run_cli(["package", "--root", str(pkg_dir), "--format", "json"])
            self.assertEqual(res.returncode, 1)
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))
            self.assertIsInstance(payload.get("findings"), list)
            error_findings = [f for f in payload["findings"] if f.get("severity") == "error"]
            self.assertTrue(len(error_findings) > 0, "Expected error findings for escaping template symlink")
            self.assertNotIn("UnicodeDecodeError", res.stderr + res.stdout)

    def test_package_references_symlink_outside_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = pathlib.Path(tmpdir)
            outside_file = tmp_path / "outside_routing.md"
            outside_file.write_bytes(b"\xff\xfe\x00\x00invalid_utf8")

            pkg_dir = self.create_minimal_package_fixture(tmp_path / "pkg")
            routing_file = pkg_dir / "references" / "routing.md"
            routing_file.unlink()
            try:
                os.symlink(outside_file, routing_file)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks not permitted in this environment")

            res = self.run_cli(["package", "--root", str(pkg_dir), "--format", "json"])
            self.assertEqual(res.returncode, 1)
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))
            self.assertIsInstance(payload.get("findings"), list)
            error_findings = [f for f in payload["findings"] if f.get("severity") == "error"]
            self.assertTrue(len(error_findings) > 0, "Expected error findings for escaping reference symlink")
            self.assertNotIn("UnicodeDecodeError", res.stderr + res.stdout)

    def test_package_directory_symlink_outside_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = pathlib.Path(tmpdir)
            outside_dir = tmp_path / "outside_templates"
            outside_dir.mkdir()
            for tpl in CANONICAL_TEMPLATES:
                (outside_dir / tpl).write_text(f"# {tpl}\n", encoding="utf-8")

            pkg_dir = self.create_minimal_package_fixture(tmp_path / "pkg")
            tpl_dir = pkg_dir / "templates"
            for child in tpl_dir.iterdir():
                child.unlink()
            tpl_dir.rmdir()

            try:
                os.symlink(outside_dir, tpl_dir)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks not permitted in this environment")

            res = self.run_cli(["package", "--root", str(pkg_dir), "--format", "json"])
            self.assertEqual(res.returncode, 1)
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))
            self.assertIsInstance(payload.get("findings"), list)
            error_findings = [f for f in payload["findings"] if f.get("severity") == "error"]
            self.assertTrue(len(error_findings) > 0, "Expected error findings for escaping directory symlink")

    def test_package_parent_directory_symlink_escape_rejected(self):
        for directory in ("references", "scripts", "tests", "extras"):
            with self.subTest(directory=directory), tempfile.TemporaryDirectory() as tmpdir:
                base_dir = pathlib.Path(tmpdir)
                pkg_dir = self.create_minimal_package_fixture(base_dir)
                # No links in SKILL.md: required-file containment must stand alone.
                (pkg_dir / "SKILL.md").write_text(
                    "---\nname: deterministic-agentic-workflow\ndescription: Valid package\n---\n",
                    encoding="utf-8",
                )
                source_dir = pkg_dir / directory
                if not source_dir.exists():
                    source_dir.mkdir()
                external_dir = base_dir / "outside"
                source_dir.rename(external_dir)
                source_dir.symlink_to(external_dir, target_is_directory=True)
                res = self.run_cli(["package", "--root", str(pkg_dir), "--format", "json"])
                self.assertEqual(res.returncode, 1, msg=res.stdout)
                codes = {f["code"] for f in json.loads(res.stdout)["findings"]}
                self.assertIn("symlink_escapes_package", codes)

    def test_package_external_directory_contents_are_not_read(self):
        for directory, filename in (("references", "routing.md"), ("templates", "blueprint.md")):
            with self.subTest(directory=directory), tempfile.TemporaryDirectory() as tmpdir:
                base_dir = pathlib.Path(tmpdir)
                pkg_dir = self.create_minimal_package_fixture(base_dir)
                external_dir = base_dir / "outside"
                (pkg_dir / directory).rename(external_dir)
                (external_dir / filename).write_bytes(b"\xff")
                (pkg_dir / directory).symlink_to(external_dir, target_is_directory=True)
                res = self.run_cli(["package", "--root", str(pkg_dir), "--format", "json"])
                self.assertEqual(res.returncode, 1, msg=res.stdout)
                codes = {f["code"] for f in json.loads(res.stdout)["findings"]}
                self.assertIn("symlink_escapes_package", codes)
                self.assertNotIn("utf8_decode_error", codes, "Escaping files must not be opened")

    def test_package_markdown_windows_absolute_link_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_dir = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
            ops_md = pkg_dir / "references" / "operations.md"
            ops_md.write_text("# Ops\n\nSee [bad win link](C:\\Windows\\System32\\cmd.exe)\n", encoding="utf-8")

            res = self.run_cli(["package", "--root", str(pkg_dir), "--format", "json"])
            self.assertEqual(res.returncode, 1)
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))
            error_findings = [f for f in payload.get("findings", []) if f.get("severity") == "error"]
            self.assertTrue(len(error_findings) > 0, "Expected error finding for Windows absolute link")

    def test_package_markdown_percent_encoded_space_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_dir = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
            target_file = pkg_dir / "references" / "extra guide.md"
            target_file.write_text("# Extra Guide\n", encoding="utf-8")

            ops_md = pkg_dir / "references" / "operations.md"
            ops_md.write_text("# Ops\n\nSee [extra](extra%20guide.md)\n", encoding="utf-8")

            res = self.run_cli(["package", "--root", str(pkg_dir), "--format", "json"])
            self.assertEqual(res.returncode, 0, msg=f"Valid percent-encoded space link should pass: {res.stdout}")
            payload = json.loads(res.stdout)
            self.assertTrue(payload.get("valid"))

    def test_package_markdown_percent_encoded_traversal_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_dir = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
            ops_md = pkg_dir / "references" / "operations.md"
            ops_md.write_text("# Ops\n\nSee [escape](%2e%2e/%2e%2e/outside.md)\n", encoding="utf-8")

            res = self.run_cli(["package", "--root", str(pkg_dir), "--format", "json"])
            self.assertEqual(res.returncode, 1)
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))
            error_findings = [f for f in payload.get("findings", []) if f.get("severity") == "error"]
            self.assertTrue(len(error_findings) > 0, "Expected error finding for percent-encoded traversal escape")

    def test_package_markdown_reference_style_broken_link_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_dir = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
            ops_md = pkg_dir / "references" / "operations.md"
            ops_md.write_text(
                "# Ops\n\nCheck [ref guide][ref_key].\n\n[ref_key]: nonexistent_guide.md\n",
                encoding="utf-8",
            )

            res = self.run_cli(["package", "--root", str(pkg_dir), "--format", "json"])
            self.assertEqual(res.returncode, 1)
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))
            error_findings = [f for f in payload.get("findings", []) if f.get("severity") == "error"]
            self.assertTrue(len(error_findings) > 0, "Expected error finding for broken reference link")

    def test_package_metadata_malformed_names_rejected(self):
        malformed_names = [
            "Deterministic-Workflow",
            "deterministic_workflow",
            "-deterministic-workflow",
            "deterministic-workflow-",
            "deterministic--workflow",
        ]
        for bad_name in malformed_names:
            with tempfile.TemporaryDirectory() as tmpdir:
                pkg_dir = self.create_minimal_package_fixture(pathlib.Path(tmpdir), pkg_name=bad_name)
                res = self.run_cli(["package", "--root", str(pkg_dir), "--format", "json"])
                self.assertEqual(res.returncode, 1, msg=f"Malformed metadata name '{bad_name}' must fail")
                payload = json.loads(res.stdout)
                self.assertFalse(payload.get("valid"))
                error_findings = [f for f in payload.get("findings", []) if f.get("severity") == "error"]
                self.assertTrue(len(error_findings) > 0, f"Expected error finding for bad name '{bad_name}'")

    def test_package_metadata_nonscalar_and_unclosed_quotes_rejected(self):
        test_cases = [
            (
                "unclosed_quote",
                "---\nname: valid-workflow-name\ndescription: \"Unclosed quoted description\n---\n# Doc\n",
            ),
            (
                "description_map",
                "---\nname: valid-workflow-name\ndescription:\n  nested: value\n---\n# Doc\n",
            ),
            (
                "description_list",
                "---\nname: valid-workflow-name\ndescription:\n  - item 1\n  - item 2\n---\n# Doc\n",
            ),
            (
                "unterminated_frontmatter",
                "---\nname: valid-workflow-name\ndescription: A description\n# Doc without closing fence\n",
            ),
        ]
        for label, frontmatter in test_cases:
            with tempfile.TemporaryDirectory() as tmpdir:
                pkg_dir = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
                (pkg_dir / "SKILL.md").write_text(frontmatter, encoding="utf-8")
                res = self.run_cli(["package", "--root", str(pkg_dir), "--format", "json"])
                self.assertEqual(res.returncode, 1, msg=f"Malformed frontmatter ({label}) must fail")
                payload = json.loads(res.stdout)
                self.assertFalse(payload.get("valid"))
                error_findings = [f for f in payload.get("findings", []) if f.get("severity") == "error"]
                self.assertTrue(len(error_findings) > 0, f"Expected error finding for {label}")

    def test_package_metadata_nonstring_plain_values_rejected(self):
        values = ("[one, two]", "{key: value}", "true", "FALSE", "null", "~", "123", "1.25", ".inf", "2026-11-02", "*alias", "!!str 123")
        for field in ("description", "compatibility"):
            for value in values:
                with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as tmpdir:
                    pkg_dir = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
                    skill_file = pkg_dir / "SKILL.md"
                    text = skill_file.read_text(encoding="utf-8")
                    old = "description: Deterministic agentic workflow standard." if field == "description" else "compatibility: Python 3.10+"
                    skill_file.write_text(text.replace(old, f"{field}: {value}"), encoding="utf-8")
                    res = self.run_cli(["package", "--root", str(pkg_dir), "--format", "json"])
                    self.assertEqual(res.returncode, 1, msg=res.stdout)
                    codes = {f["code"] for f in json.loads(res.stdout)["findings"]}
                    self.assertIn("invalid_frontmatter", codes)

    def test_package_metadata_quoted_nonstring_looking_values_allowed(self):
        for value in ('"[one, two]"', "'true'", '"123"', '"null"'):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as tmpdir:
                pkg_dir = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
                skill_file = pkg_dir / "SKILL.md"
                text = skill_file.read_text(encoding="utf-8")
                skill_file.write_text(text.replace("description: Deterministic agentic workflow standard.", f"description: {value}"), encoding="utf-8")
                res = self.run_cli(["package", "--root", str(pkg_dir), "--format", "json"])
                self.assertEqual(res.returncode, 0, msg=res.stdout)

    def test_package_metadata_unknown_maps_allowed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_dir = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
            skill_md = (
                "---\n"
                "name: deterministic-agentic-workflow\n"
                "description: Deterministic agentic workflow standard.\n"
                "compatibility: Python 3.10+\n"
                "metadata:\n"
                "  nested_key: nested_value\n"
                "  version: 1.0.0\n"
                "---\n\n"
                "# Deterministic Agentic Workflow\n\n"
                "See [routing](references/routing.md) and [operations](references/operations.md).\n"
                "Templates are available in [templates](templates/blueprint.md).\n"
                "Read [validation](references/validation.md) and [installation](references/installation.md).\n"
            )
            (pkg_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
            res = self.run_cli(["package", "--root", str(pkg_dir), "--format", "json"])
            self.assertEqual(res.returncode, 0, msg=f"Unknown metadata map should be allowed: {res.stdout}")
            payload = json.loads(res.stdout)
            self.assertTrue(payload.get("valid"))

    def test_package_nested_fence_length_tracking(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_dir = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
            ops_md = pkg_dir / "references" / "operations.md"
            content = (
                "# Operations Reference\n\n"
                "Here is an example showing markdown syntax:\n\n"
                "````markdown\n"
                "```bash\n"
                "echo 'Inside inner fence'\n"
                "See [inner bad link](nonexistent_inner.md) and `skill://forbidden-skill`\n"
                "```\n"
                "More text still inside the 4-backtick fence: [another inner](bad_link.md)\n"
                "````\n\n"
                "Outside code fence now.\n"
            )
            ops_md.write_text(content, encoding="utf-8")
            res = self.run_cli(["package", "--root", str(pkg_dir), "--format", "json"])
            self.assertEqual(
                res.returncode, 0,
                msg=f"Inner 3-backtick fence must not close 4-backtick fence prematurely: {res.stdout}",
            )
            payload = json.loads(res.stdout)
            self.assertTrue(payload.get("valid"))

    def test_package_nested_fence_tilde_variants(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_dir = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
            ops_md = pkg_dir / "references" / "operations.md"
            content = (
                "# Operations Reference\n\n"
                "Here is an example with tildes:\n\n"
                "~~~~\n"
                "```\n"
                "echo 'inner backticks inside outer tildes'\n"
                "See [bad](bad_link.md)\n"
                "```\n"
                "~~~~\n\n"
                "Outside.\n"
            )
            ops_md.write_text(content, encoding="utf-8")
            res = self.run_cli(["package", "--root", str(pkg_dir), "--format", "json"])
            self.assertEqual(
                res.returncode, 0,
                msg=f"Tilde fence enclosing backtick fence must be parsed properly: {res.stdout}",
            )
            payload = json.loads(res.stdout)
            self.assertTrue(payload.get("valid"))

    def test_package_fence_indentation_up_to_3_spaces_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_dir = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
            ops_md = pkg_dir / "references" / "operations.md"
            content = (
                "# Operations Reference\n\n"
                "   ```bash\n"
                "   [link inside 3-space indented fence](nonexistent_nested.md)\n"
                "   ```\n\n"
                "Outside.\n"
            )
            ops_md.write_text(content, encoding="utf-8")
            res = self.run_cli(["package", "--root", str(pkg_dir), "--format", "json"])
            self.assertEqual(
                res.returncode, 0,
                msg=f"Fence with <=3 spaces indentation should be recognized: {res.stdout}",
            )
            payload = json.loads(res.stdout)
            self.assertTrue(payload.get("valid"))

    def test_package_inline_code_fake_markdown_link_ignored(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_dir = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
            ops_md = pkg_dir / "references" / "operations.md"
            content = (
                "# Operations Reference\n\n"
                "Refer to `[fake link](nonexistent_inline.md)` in the instructions.\n"
            )
            ops_md.write_text(content, encoding="utf-8")
            res = self.run_cli(["package", "--root", str(pkg_dir), "--format", "json"])
            self.assertEqual(
                res.returncode, 0,
                msg=f"Inline code containing link-like syntax must not be validated as a file link: {res.stdout}",
            )
            payload = json.loads(res.stdout)
            self.assertTrue(payload.get("valid"))

    def test_unknown_json_key_secret_marker_not_leaked(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, baseline = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            secret_marker = "SUPER_SECRET_KEY_NAME_NEVER_LEAK_999888"
            nested_secret_marker = "ANOTHER_SECRET_NESTED_KEY_444555"

            contract_data = self.create_contract_dict(baseline_files=baseline)
            contract_data[secret_marker] = "secret_value"
            contract_data["operation"][nested_secret_marker] = "nested_secret_value"

            contract_file = proj_dir / "contract.json"
            contract_file.write_text(json.dumps(contract_data), encoding="utf-8")

            res = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "plan",
                "--format", "json",
            ])
            self.assertEqual(res.returncode, 1, msg="Unknown keys in contract must reject with exit 1")
            combined_output = res.stdout + res.stderr
            self.assertNotIn(secret_marker, combined_output, "Top-level secret key name was leaked in CLI output!")
            self.assertNotIn(nested_secret_marker, combined_output, "Nested secret key name was leaked in CLI output!")
            payload = json.loads(res.stdout)
            self.assertFalse(payload.get("valid"))
            error_findings = [f for f in payload.get("findings", []) if f.get("severity") == "error"]
            self.assertTrue(len(error_findings) > 0, "Expected error findings for unknown contract keys")

    def test_contract_diagnostic_payload_values_redacted(self):
        marker = "SYNTHETIC_SECRET_DO_NOT_ECHO"
        cases = ("duplicate_key", "document_kind", "document_status", "baseline_path", "document_path", "evidence_path", "criterion_id", "missing_contract")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmpdir:
                base_dir = pathlib.Path(tmpdir)
                proj_dir, baseline = self.create_minimal_project_fixture(base_dir)
                contract = self.create_contract_dict(baseline_files=baseline)
                if case == "document_kind":
                    contract["documents"] = [{"kind": marker, "status": "current", "path": "src/app.py"}]
                elif case == "document_status":
                    contract["documents"] = [{"kind": "prd", "status": {"secret": marker}, "path": "src/app.py"}]
                elif case == "baseline_path":
                    contract["baseline"]["files"][0]["path"] = marker
                elif case == "document_path":
                    contract["documents"] = [{"kind": "prd", "status": "current", "path": marker}]
                elif case == "evidence_path":
                    contract["evidence"] = [{"criterion_id": "AC-1", "status": "passed", "reference": marker, "summary": "Observed"}]
                elif case == "criterion_id":
                    criterion = {"id": marker, "criterion": "Pass"}
                    contract["acceptance_criteria"] = [criterion, criterion]
                contract_file = proj_dir / "contract.json"
                raw = f'{{"{marker}": 1, "{marker}": 2}}' if case == "duplicate_key" else json.dumps(contract)
                contract_file.write_text(raw, encoding="utf-8")
                input_file = proj_dir / marker if case == "missing_contract" else contract_file
                res = self.run_cli(["contract", str(input_file), "--project-root", str(proj_dir), "--format", "json"])
                self.assertIn(res.returncode, (1, 2))
                self.assertNotIn(marker, res.stdout + res.stderr)

    def test_package_diagnostic_payload_values_redacted(self):
        marker = "synthetic-secret-do-not-echo"
        for case in ("frontmatter_name", "frontmatter_key", "markdown_target", "routing_section"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmpdir:
                pkg_dir = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
                skill_file = pkg_dir / "SKILL.md"
                text = skill_file.read_text(encoding="utf-8")
                if case == "frontmatter_name":
                    text = text.replace("name: deterministic-agentic-workflow", f"name: {marker}")
                elif case == "frontmatter_key":
                    text = text.replace("---\n\n", f'{marker}: "unclosed\n---\n\n', 1)
                elif case == "markdown_target":
                    text += f"\n[broken]({marker})\n"
                else:
                    routing_file = pkg_dir / "references" / "routing.md"
                    routing_file.write_text(f"### 1. `{marker}`\n", encoding="utf-8")
                skill_file.write_text(text, encoding="utf-8")
                res = self.run_cli(["package", "--root", str(pkg_dir), "--format", "json"])
                self.assertEqual(res.returncode, 1, msg=res.stdout)
                self.assertNotIn(marker, res.stdout + res.stderr)

    # -------------------------------------------------------------------------
    # Baseline completion, approval scope, and evidence status regression tests
    # -------------------------------------------------------------------------

    def test_contract_complete_stage_accepts_edited_and_deleted_baseline_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, baseline = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            ev_file = proj_dir / "test-evidence.log"
            ev_file.write_text("All tests pass\n", encoding="utf-8")
            deleted_path = proj_dir / "obsolete.txt"
            deleted_path.write_text("pre-mutation content\n", encoding="utf-8")
            baseline.append({
                "path": "obsolete.txt",
                "sha256": _sha256(deleted_path.read_bytes()),
            })

            # Mutate workspace: edit one baseline file and delete another
            edited_path = proj_dir / baseline[0]["path"]
            edited_path.write_text("modified content after baseline\n", encoding="utf-8")
            deleted_path.unlink()

            contract_data = self.create_contract_dict(
                baseline_files=baseline,
                acceptance_criteria=[{"id": "AC-1", "criterion": "Passes tests"}],
                evidence=[{
                    "criterion_id": "AC-1",
                    "status": "passed",
                    "reference": "test-evidence.log",
                    "summary": "Verified post-mutation behavior",
                }],
            )
            contract_file = proj_dir / "contract.json"
            contract_file.write_text(json.dumps(contract_data), encoding="utf-8")

            # Complete stage must accept legitimate mutations without baseline drift errors
            res_comp = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "complete",
                "--format", "json",
            ])
            self.assertEqual(res_comp.returncode, 0, msg=f"Complete rejected valid mutated baseline: {res_comp.stdout}")
            payload_comp = json.loads(res_comp.stdout)
            self.assertTrue(payload_comp.get("valid"))

            # Execute stage still rejects the workspace drift and missing file
            res_exec = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "execute",
                "--format", "json",
            ])
            self.assertEqual(res_exec.returncode, 1, msg=f"Execute should have rejected baseline drift: {res_exec.stdout}")
            payload_exec = json.loads(res_exec.stdout)
            self.assertFalse(payload_exec.get("valid"))
            error_codes = [f.get("code") for f in payload_exec.get("findings", []) if f.get("severity") == "error"]
            self.assertIn("baseline_changed", error_codes)
            self.assertIn("file_not_found", error_codes)

    def test_contract_complete_stage_still_rejects_malformed_baseline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, baseline = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            ev_file = proj_dir / "test-evidence.log"
            ev_file.write_text("pass\n", encoding="utf-8")
            valid_ev = [{
                "criterion_id": "AC-1",
                "status": "passed",
                "reference": "test-evidence.log",
                "summary": "pass",
            }]

            cases = [
                ("bad_digest", [{"path": "nonexistent.py", "sha256": "not-a-valid-sha256-hex"}], "invalid_sha256"),
                ("traversal_escape", [{"path": "../outside.py", "sha256": "0" * 64}], "boundary_violation"),
                ("duplicate_path", [
                    {"path": "src/app.py", "sha256": "0" * 64},
                    {"path": "src/app.py", "sha256": "1" * 64},
                ], "duplicate_baseline_path"),
            ]
            for label, test_baseline, expected_code in cases:
                with self.subTest(case=label):
                    contract_data = self.create_contract_dict(
                        baseline_files=test_baseline,
                        evidence=valid_ev,
                    )
                    contract_file = proj_dir / f"contract_{label}.json"
                    contract_file.write_text(json.dumps(contract_data), encoding="utf-8")

                    res = self.run_cli([
                        "contract", str(contract_file),
                        "--project-root", str(proj_dir),
                        "--stage", "complete",
                        "--format", "json",
                    ])
                    self.assertEqual(res.returncode, 1, msg=f"Case {label} did not fail complete: {res.stdout}")
                    payload = json.loads(res.stdout)
                    self.assertFalse(payload.get("valid"))
                    codes = [f.get("code") for f in payload.get("findings", []) if f.get("severity") == "error"]
                    self.assertIn(expected_code, codes, f"Expected {expected_code} in {codes}")

    def test_contract_approval_scope_variations_and_crash_resilience(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, baseline = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            scope = ["src/app.py", "src/util.py"]
            base_approval = {
                "reference": "APP-123",
                "action": "refactor",
                "target": "core_module",
                "revision": "rev-001",
            }

            # Reordered scope: valid match
            reordered_app = dict(base_approval, scope=["src/util.py", "src/app.py"])
            contract_data = self.create_contract_dict(
                baseline_files=baseline,
                risk="high",
                scope=scope,
                approval=reordered_app,
            )
            contract_file = proj_dir / "contract_reordered.json"
            contract_file.write_text(json.dumps(contract_data), encoding="utf-8")
            res = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "execute",
                "--format", "json",
            ])
            self.assertEqual(res.returncode, 0, msg=f"Reordered scope failed: {res.stdout}")
            self.assertTrue(json.loads(res.stdout).get("valid"))

            # Invalid approval scope types / contents must cleanly reject without crash
            invalid_scope_cases = [
                ("dict", {"nested": "dict"}, "invalid_approval_scope"),
                ("nested_dict_in_list", [{"a": 1}], "invalid_approval_scope_item"),
                ("nested_list_in_list", [["nested"]], "invalid_approval_scope_item"),
                ("number_in_list", [123], "invalid_approval_scope_item"),
                ("blank_string_in_list", ["   "], "invalid_approval_scope_item"),
                ("empty_list", [], "invalid_approval_scope"),
                ("duplicate_items", ["src/app.py", "src/app.py"], "duplicate_approval_scope"),
            ]
            for label, bad_app_scope, expected_code in invalid_scope_cases:
                with self.subTest(case=label):
                    bad_app = dict(base_approval, scope=bad_app_scope)
                    cdata = self.create_contract_dict(
                        baseline_files=baseline,
                        risk="high",
                        scope=scope,
                        approval=bad_app,
                    )
                    cfile = proj_dir / f"contract_bad_scope_{label}.json"
                    cfile.write_text(json.dumps(cdata), encoding="utf-8")
                    res = self.run_cli([
                        "contract", str(cfile),
                        "--project-root", str(proj_dir),
                        "--stage", "execute",
                        "--format", "json",
                    ])
                    self.assertEqual(res.returncode, 1, msg=f"Case {label} did not exit 1: {res.stdout}")
                    self.assertNotIn("traceback", res.stderr.lower())
                    payload = json.loads(res.stdout)
                    self.assertFalse(payload.get("valid"))
                    codes = [f.get("code") for f in payload.get("findings", []) if f.get("severity") == "error"]
                    self.assertIn(expected_code, codes, f"Expected {expected_code} in {codes}")

            # When operation.scope itself is invalid (e.g. dict or list of dicts), approval scope check must not crash
            cdata_bad_op = self.create_contract_dict(
                baseline_files=baseline,
                risk="high",
                approval=dict(base_approval, scope=["src/app.py"]),
            )
            cdata_bad_op["operation"]["scope"] = [{"not": "a_string"}]
            cfile_bad_op = proj_dir / "contract_bad_op_scope.json"
            cfile_bad_op.write_text(json.dumps(cdata_bad_op), encoding="utf-8")
            res_bad_op = self.run_cli([
                "contract", str(cfile_bad_op),
                "--project-root", str(proj_dir),
                "--stage", "execute",
                "--format", "json",
            ])
            self.assertEqual(res_bad_op.returncode, 1)
            self.assertNotIn("traceback", res_bad_op.stderr.lower())
            payload_bad_op = json.loads(res_bad_op.stdout)
            self.assertFalse(payload_bad_op.get("valid"))

    def test_contract_evidence_unexercised_status_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir, baseline = self.create_minimal_project_fixture(pathlib.Path(tmpdir))
            ev_file = proj_dir / "evidence.txt"
            ev_file.write_text("Evidence note\n", encoding="utf-8")

            contract_data = self.create_contract_dict(
                baseline_files=baseline,
                acceptance_criteria=[{"id": "AC-1", "criterion": "Passes"}],
                evidence=[{
                    "criterion_id": "AC-1",
                    "status": "unexercised",
                    "reference": "evidence.txt",
                    "summary": "Pending verification in subsequent run",
                }],
            )
            contract_file = proj_dir / "contract.json"
            contract_file.write_text(json.dumps(contract_data), encoding="utf-8")

            # Allowed in plan
            res_plan = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "plan",
                "--format", "json",
            ])
            self.assertEqual(res_plan.returncode, 0, msg=f"Plan should accept unexercised evidence: {res_plan.stdout}")
            self.assertTrue(json.loads(res_plan.stdout).get("valid"))

            # Allowed in execute
            res_exec = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "execute",
                "--format", "json",
            ])
            self.assertEqual(res_exec.returncode, 0, msg=f"Execute should accept unexercised evidence: {res_exec.stdout}")
            self.assertTrue(json.loads(res_exec.stdout).get("valid"))

            # Rejected in complete
            res_comp = self.run_cli([
                "contract", str(contract_file),
                "--project-root", str(proj_dir),
                "--stage", "complete",
                "--format", "json",
            ])
            self.assertEqual(res_comp.returncode, 1, msg=f"Complete must reject unexercised evidence: {res_comp.stdout}")
            payload_comp = json.loads(res_comp.stdout)
            self.assertFalse(payload_comp.get("valid"))
            codes = [f.get("code") for f in payload_comp.get("findings", []) if f.get("severity") == "error"]
            self.assertIn("unpassed_evidence_at_complete", codes)

    def test_package_required_file_traversal_yields_path_escapes_package(self):
        sys_path = sys.path[:]
        try:
            sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
            import validate
            with tempfile.TemporaryDirectory() as tmpdir:
                pkg_dir = self.create_minimal_package_fixture(pathlib.Path(tmpdir))
                orig_rf = validate.validate_package.__globals__["resolve_bounded_path"]
                try:
                    # 1. Non-symlink boundary escape yields path_escapes_package
                    def mock_resolve_traversal(root, rel):
                        if rel == "templates":
                            return None, "absolute_or_traversal_path"
                        return orig_rf(root, rel)
                    validate.validate_package.__globals__["resolve_bounded_path"] = mock_resolve_traversal
                    result = validate.validate_package(pkg_dir)
                    codes = {f["code"] for f in result["findings"]}
                    self.assertIn("path_escapes_package", codes)
                    self.assertNotIn("symlink_escapes_package", codes)

                    # 2. Symlink boundary escape yields symlink_escapes_package
                    def mock_resolve_symlink(root, rel):
                        if rel == "templates":
                            return None, "symlink_escapes_root"
                        return orig_rf(root, rel)
                    validate.validate_package.__globals__["resolve_bounded_path"] = mock_resolve_symlink
                    result_sym = validate.validate_package(pkg_dir)
                    codes_sym = {f["code"] for f in result_sym["findings"]}
                    self.assertIn("symlink_escapes_package", codes_sym)
                    self.assertNotIn("path_escapes_package", codes_sym)
                finally:
                    validate.validate_package.__globals__["resolve_bounded_path"] = orig_rf
        finally:
            sys.path = sys_path

    def test_package_accessed_via_symlinked_ancestor(self):
        sys_path = sys.path[:]
        try:
            sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
            import validate
            with tempfile.TemporaryDirectory() as tmpdir:
                base_path = pathlib.Path(tmpdir)
                real_parent = base_path / "real"
                real_parent.mkdir()
                pkg_dir = self.create_minimal_package_fixture(real_parent)
                link_parent = base_path / "linked"
                try:
                    os.symlink(real_parent, link_parent, target_is_directory=True)
                except (OSError, NotImplementedError):
                    self.skipTest("Symlinks not permitted in this environment")
                aliased_pkg = link_parent / pkg_dir.name
                res = validate.validate_package(aliased_pkg)
                error_codes = {f["code"] for f in res["findings"] if f.get("severity") == "error"}
                self.assertEqual(error_codes, set(), f"Unexpected errors for aliased package: {error_codes}")
                self.assertTrue(res["valid"])
        finally:
            sys.path = sys_path

    def test_package_version_consistency(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_dir = self.create_minimal_package_fixture(pathlib.Path(tmpdir))

            # 1. No VERSION file -> passes (skipped)
            res = self.run_cli(["package", "--root", str(pkg_dir), "--format", "json"])
            self.assertEqual(res.returncode, 0, msg=res.stdout)

            # 2. VERSION file exists and matches SKILL.md metadata.version -> passes
            (pkg_dir / "VERSION").write_text("0.1.0\n", encoding="utf-8")
            skill_md = (
                "---\n"
                "name: deterministic-agentic-workflow\n"
                "description: Deterministic agentic workflow standard.\n"
                "compatibility: Python 3.10+\n"
                "license: MIT\n"
                "metadata:\n"
                '  version: "0.1.0"\n'
                "---\n\n"
                "# Deterministic Agentic Workflow\n\n"
                "See [routing](references/routing.md) and [operations](references/operations.md).\n"
                "Templates are available in [templates](templates/blueprint.md).\n"
                "Read [validation](references/validation.md) and [installation](references/installation.md).\n"
            )
            (pkg_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
            res = self.run_cli(["package", "--root", str(pkg_dir), "--format", "json"])
            self.assertEqual(res.returncode, 0, msg=res.stdout)

            # 3. VERSION file exists but metadata.version is mismatched -> version_mismatch
            (pkg_dir / "VERSION").write_text("0.2.0\n", encoding="utf-8")
            res = self.run_cli(["package", "--root", str(pkg_dir), "--format", "json"])
            self.assertEqual(res.returncode, 1, msg=res.stdout)
            codes = {f["code"] for f in json.loads(res.stdout)["findings"]}
            self.assertIn("version_mismatch", codes)

            # 4. VERSION file exists but metadata.version is absent -> version_mismatch
            skill_no_ver = (
                "---\n"
                "name: deterministic-agentic-workflow\n"
                "description: Deterministic agentic workflow standard.\n"
                "compatibility: Python 3.10+\n"
                "---\n\n"
                "# Deterministic Agentic Workflow\n\n"
                "See [routing](references/routing.md) and [operations](references/operations.md).\n"
                "Templates are available in [templates](templates/blueprint.md).\n"
                "Read [validation](references/validation.md) and [installation](references/installation.md).\n"
            )
            (pkg_dir / "SKILL.md").write_text(skill_no_ver, encoding="utf-8")
            res = self.run_cli(["package", "--root", str(pkg_dir), "--format", "json"])
            self.assertEqual(res.returncode, 1, msg=res.stdout)
            codes = {f["code"] for f in json.loads(res.stdout)["findings"]}
            self.assertIn("version_mismatch", codes)
if __name__ == "__main__":
    unittest.main()
