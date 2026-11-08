"""Exercise installation ownership and complete bundles through the real CLI."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import install as installer
SUITE = "deterministic-agentic-workflow"
MODULES = installer.MODULES


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="daw-install-test-")
        self.addCleanup(self.temp.cleanup)
        raw_base = Path(self.temp.name)
        real_base = raw_base / "real"
        real_base.mkdir()
        logical_base = raw_base / "logical"
        try:
            logical_base.symlink_to(real_base, target_is_directory=True)
            self.base = logical_base
            self.symlinks = True
        except OSError:
            self.base = raw_base
            self.symlinks = False
        self.skills = self.base / "project" / ".agents" / "skills"
        self.env = dict(os.environ, HOME=str(self.base / "home"), USERPROFILE=str(self.base / "home"), PYTHONDONTWRITEBYTECODE="1")

    def cli(self, action="install", *extra, source=ROOT, custom=True):
        argv = [sys.executable, str(source / "scripts" / "install.py"), action]
        if custom:
            argv += ["--skills-dir", str(self.skills)]
        result = subprocess.run(argv + list(extra) + ["--json"], cwd=self.base, env=self.env, capture_output=True, text=True)
        self.assertNotIn("Traceback", result.stderr)
        return result

    def installed(self):
        if not self.symlinks:
            self.skipTest("Directory symlinks unavailable; root-only installation is tested separately")
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return self.skills / SUITE

    def source_copy(self):
        target = self.base / "source" / SUITE
        shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns(".git", ".agents", ".codex", "__pycache__", ".venv", ".pytest_cache"))
        return target

    def test_installs_whole_bundle_and_resolves_all_module_aliases(self):
        bundle = self.installed()
        for module in MODULES:
            alias = self.skills / module
            self.assertTrue(alias.is_symlink())
            self.assertEqual(alias.resolve(), (bundle / "skills" / module).resolve())
            self.assertTrue((alias.resolve().parents[1] / "references" / "operations.md").is_file())
        self.assertTrue((bundle / "templates" / "security.md").is_file())
        self.assertTrue((bundle / "LICENSE").is_file())
        self.assertTrue((bundle / "VERSION").is_file())
        self.assertTrue((bundle / "SKILL.md").is_file())
        self.assertTrue((bundle / "scripts" / "package_layout.py").is_file())
        self.assertFalse((bundle / ".git").exists())
        self.assertFalse((bundle / "tests").exists())
        self.assertFalse((bundle / "docs").exists())
        self.assertFalse((bundle / "tools").exists())
        self.assertFalse((bundle / "README.md").exists())
        self.assertFalse((bundle / "AGENTS.md").exists())
        self.assertFalse((bundle / "scripts" / "evaluate.py").exists())
        self.assertFalse((bundle / "scripts" / "wizard_bench.py").exists())
        for cmd in (["scripts/route.py", "--check-suite"], ["scripts/validate.py", "package"]):
            result = subprocess.run([sys.executable, str(bundle / cmd[0]), *cmd[1:]], cwd=self.base, env=self.env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_dry_run_and_missing_status_do_not_create_destination(self):
        result = self.cli("install", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.skills.parent.exists())
        status = self.cli("status")
        self.assertEqual(status.returncode, 1)
        self.assertEqual(json.loads(status.stdout)["status"], "missing")
        self.assertFalse(self.skills.parent.exists())

    def test_repeat_install_is_unchanged_and_status_checks_aliases(self):
        bundle = self.installed()
        before = (bundle / "SKILL.md").stat().st_mtime_ns
        again = self.cli()
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        self.assertEqual(json.loads(again.stdout)["status"], "unchanged")
        self.assertEqual((bundle / "SKILL.md").stat().st_mtime_ns, before)
        self.assertEqual(self.cli("status").returncode, 0)
        (self.skills / "daw-build").unlink()
        self.assertEqual(self.cli("status").returncode, 1)

    def test_unrelated_skill_collision_aborts_before_bundle_creation(self):
        conflict = self.skills / "daw-build"
        conflict.mkdir(parents=True)
        sentinel = conflict / "user.txt"
        sentinel.write_text("keep me")
        result = self.cli()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(sentinel.read_text(), "keep me")
        self.assertFalse((self.skills / SUITE).exists())

    def test_unowned_bundle_is_never_replaced_or_removed(self):
        bundle = self.skills / SUITE
        bundle.mkdir(parents=True)
        (bundle / "user.txt").write_text("keep")
        for action, extra in (("install", ("--update",)), ("uninstall", ())):
            result = self.cli(action, *extra)
            self.assertEqual(result.returncode, 1)
            self.assertEqual((bundle / "user.txt").read_text(), "keep")

    def test_changed_files_or_extra_files_prevent_update_and_uninstall(self):
        bundle = self.installed()
        original = (bundle / "SKILL.md").read_bytes()
        for path, content in ((bundle / "SKILL.md", b"user edits"), (bundle / "extra.txt", b"user file")):
            with self.subTest(path=path.name):
                path.write_bytes(content)
                for action, extra in (("install", ("--update",)), ("uninstall", ())):
                    result = self.cli(action, *extra)
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(path.read_bytes(), content)
                if path.name == "SKILL.md":
                    path.write_bytes(original)
                else:
                    path.unlink()

    def test_upgrade_requires_update_flag_and_keeps_aliases(self):
        bundle = self.installed()
        source = self.source_copy()
        previous_version = (source / "VERSION").read_text().strip()
        parts = previous_version.split(".")
        bumped = ".".join([*parts[:-1], str(int(parts[-1]) + 1)])
        (source / "VERSION").write_text(bumped + "\n")
        skill = source / "SKILL.md"
        skill.write_text(skill.read_text().replace(
            f'version: "{previous_version}"', f'version: "{bumped}"', 1
        ))
        result = self.cli(source=source)
        self.assertEqual(result.returncode, 1)
        self.assertNotEqual((bundle / "VERSION").read_text(), bumped + "\n")
        result = self.cli("install", "--update", source=source)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((bundle / "VERSION").read_text(), bumped + "\n")
        self.assertEqual((self.skills / "daw-build").resolve(), (bundle / "skills" / "daw-build").resolve())
        self.assertEqual(self.cli("status").returncode, 0)

    def test_uninstall_removes_only_owned_installation(self):
        self.installed()
        unrelated = self.skills / "other-skill"
        unrelated.mkdir()
        (unrelated / "SKILL.md").write_text("user content")
        result = self.cli("uninstall", "--dry-run")
        self.assertEqual(result.returncode, 0)
        self.assertTrue((self.skills / SUITE).exists())
        result = self.cli("uninstall")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((unrelated / "SKILL.md").read_text(), "user content")
        self.assertFalse((self.skills / SUITE).exists())
        for module in MODULES:
            self.assertFalse((self.skills / module).is_symlink())

    def test_foreign_alias_target_prevents_uninstall(self):
        bundle = self.installed()
        foreign = self.base / "user-skill"
        foreign.mkdir()
        alias = self.skills / "daw-build"
        alias.unlink()
        alias.symlink_to(foreign, target_is_directory=True)
        result = self.cli("uninstall")
        self.assertEqual(result.returncode, 1)
        self.assertTrue(bundle.is_dir())
        self.assertEqual(alias.resolve(), foreign.resolve())

    def test_no_aliases_preserves_complete_root_dispatch(self):
        result = self.cli("install", "--no-aliases")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        bundle = self.skills / SUITE
        self.assertTrue((bundle / "skills" / "daw-build" / "SKILL.md").is_file())
        self.assertFalse((self.skills / "daw-build").exists())
        self.assertEqual(self.cli("status").returncode, 0)
        self.assertEqual(self.cli("uninstall").returncode, 0)

    def test_agent_presets_target_documented_project_and_user_locations(self):
        project = self.base / "target"
        mappings = {"codex": (".agents/skills", ".agents/skills"), "claude": (".claude/skills", ".claude/skills"), "gemini": (".gemini/skills", ".gemini/skills"), "cursor": (".cursor/skills", ".cursor/skills"), "copilot": (".github/skills", ".copilot/skills")}
        for agent, (local, personal) in mappings.items():
            for scope, expected in (("project", project / local), ("user", Path(self.env["HOME"]) / personal)):
                with self.subTest(agent=agent, scope=scope):
                    result = self.cli("install", "--agent", agent, "--scope", scope, "--project-root", str(project), "--dry-run", custom=False)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(Path(json.loads(result.stdout)["skills_dir"]), expected.resolve())
        self.assertFalse(project.exists())

    def test_invalid_source_aborts_without_destination_writes(self):
        source = self.source_copy()
        shutil.rmtree(source / "skills" / "daw-debug")
        result = self.cli(source=source)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.skills.exists())

    def test_source_symlink_is_rejected_without_copying_external_bytes(self):
        if not self.symlinks:
            self.skipTest("Symlinks unavailable")
        source = self.source_copy()
        external = self.base / "private.txt"
        external.write_text("private fixture")
        (source / "references" / "external.txt").symlink_to(external)
        result = self.cli(source=source)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.skills.exists())

    def test_source_optional_agents_symlink_is_rejected(self):
        if not self.symlinks:
            self.skipTest("Symlinks unavailable")
        source = self.source_copy()
        external_agents = self.base / "external-agents"
        external_agents.mkdir()
        (external_agents / "metadata.txt").write_text("secret metadata")
        agents_path = source / "agents"
        if agents_path.is_dir() and not agents_path.is_symlink():
            shutil.rmtree(agents_path)
        elif agents_path.exists() or agents_path.is_symlink():
            agents_path.unlink()
        agents_path.symlink_to(external_agents, target_is_directory=True)
        result = self.cli(source=source)
        self.assertEqual(result.returncode, 1)
        self.assertIn("symlink", result.stdout + result.stderr)
        self.assertFalse(self.skills.exists())

    def test_install_into_source_resources_is_rejected(self):
        source = self.source_copy()
        self.skills = source / "references" / "recursive"
        result = self.cli(source=source)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.skills.exists())

    def test_dry_run_rejects_changes_without_update_just_like_real_install(self):
        self.installed()
        result = self.cli("install", "--no-aliases", "--dry-run")
        self.assertEqual(result.returncode, 1)
        source = self.source_copy()
        previous_version = (source / "VERSION").read_text().strip()
        parts = previous_version.split(".")
        bumped = ".".join([*parts[:-1], str(int(parts[-1]) + 1)])
        (source / "VERSION").write_text(bumped + "\n")
        skill = source / "SKILL.md"
        skill.write_text(skill.read_text().replace(
            f'version: "{previous_version}"', f'version: "{bumped}"', 1
        ))
        result = self.cli("install", "--dry-run", source=source)
        self.assertEqual(result.returncode, 1)

    def test_failed_update_or_uninstall_keeps_backup_when_restore_fails(self):
        real_rename = Path.rename
        real_unlink = Path.unlink

        def fail_restore(path, target):
            if path.name == "previous":
                raise PermissionError("restore failure")
            return real_rename(path, target)

        def fail_alias_removal(path, *args, **kwargs):
            if path.parent.resolve() == self.skills.resolve() and path.name == "daw-ask":
                raise PermissionError("alias removal failure")
            return real_unlink(path, *args, **kwargs)

        for action in ("update", "uninstall"):
            with self.subTest(action=action):
                self.skills = self.base / action / "skills"
                bundle = self.installed()
                old_bytes = (bundle / "SKILL.md").read_bytes()
                with mock.patch.object(Path, "rename", fail_restore), mock.patch.object(Path, "unlink", fail_alias_removal):
                    with self.assertRaises((OSError, installer.InstallError)):
                        if action == "update":
                            installer.install(self.skills, update=True, no_aliases=True, dry_run=False)
                        else:
                            installer.uninstall(self.skills, dry_run=False)
                backups = list(self.skills.glob(".daw-*/previous/SKILL.md"))
                self.assertEqual(len(backups), 1, "The only recoverable bundle must survive a failed restore")
                self.assertEqual(backups[0].read_bytes(), old_bytes)
                if bundle.exists():
                    shutil.rmtree(bundle)
                backups[0].parent.rename(bundle)
                shutil.rmtree(backups[0].parent.parent)

    def test_symlink_creation_failure_does_not_apply_bundle(self):
        with mock.patch.object(Path, "symlink_to", side_effect=OSError("links disabled")):
            with self.assertRaisesRegex(installer.InstallError, "--no-aliases"):
                installer.install(self.skills, update=False, no_aliases=False, dry_run=False)
        self.assertFalse((self.skills / SUITE).exists())

    def test_status_and_uninstall_ignore_bytecode_caches(self):
        bundle = self.installed()
        pycache1 = bundle / "scripts" / "__pycache__"
        pycache1.mkdir(parents=True, exist_ok=True)
        (pycache1 / "x.cpython.pyc").write_bytes(b"dummy")
        pycache2 = bundle / "skills" / "daw-build" / "__pycache__"
        pycache2.mkdir(parents=True, exist_ok=True)
        (pycache2 / "y.pyc").write_bytes(b"dummy")

        status = self.cli("status")
        self.assertEqual(status.returncode, 0, status.stderr + status.stdout)
        payload = json.loads(status.stdout)
        self.assertEqual(payload.get("status"), "ready")

        uninstall = self.cli("uninstall")
        self.assertEqual(uninstall.returncode, 0, uninstall.stderr + uninstall.stdout)
        self.assertFalse(bundle.exists())

    def test_existing_lockfile_error_contains_lock_path(self):
        self.skills.mkdir(parents=True, exist_ok=True)
        lock = self.skills / ".daw-install.lock"
        lock.write_text("locked", encoding="utf-8")
        result = self.cli("install")
        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertIn(str(lock.resolve()), payload.get("error", ""))
        self.assertIn("delete that file and retry", payload.get("error", ""))
        non_json = subprocess.run([sys.executable, str(ROOT / "scripts" / "install.py"), "install", "--skills-dir", str(self.skills)], cwd=self.base, env=self.env, capture_output=True, text=True)
        self.assertNotEqual(non_json.returncode, 0)
        self.assertIn(str(lock.resolve()), non_json.stderr)
    def setup_true_historical_eight_payload(self, manifest_module_override=None):
        if not self.symlinks:
            self.skipTest("Directory symlinks unavailable; root-only installation is tested separately")
        entries = installer.source_entries()
        bundle = self.skills / SUITE
        bundle.mkdir(parents=True)
        for entry in entries:
            rel = entry.relative_to(installer.SOURCE)
            target = bundle / rel
            if entry.is_dir():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(entry, target, ignore=installer.ignore_copy)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(entry, target)

        manifest_path = bundle / "references" / "suite-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for mod in ("daw-setup", "daw-wizard", "daw-untangle", "daw-ship"):
            manifest["modules"].pop(mod, None)
            shutil.rmtree(bundle / "skills" / mod, ignore_errors=True)
        for route_name in ("setup", "untangle", "refactor", "maintain", "spike", "ship"):
            manifest["routes"].pop(route_name, None)
        manifest["routes"]["bootstrap"]["stages"] = ["daw-design", "daw-plan"]
        if manifest_module_override:
            mod_name, new_path = manifest_module_override
            manifest["modules"][mod_name]["path"] = new_path
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        for f_name in ("SKILL.md", "AGENTS.md"):
            f_path = bundle / f_name
            if not f_path.is_file():
                continue
            lines = f_path.read_text().splitlines(keepends=True)
            out = []
            fm_count = 0
            for l in lines:
                if l.strip() == "---" and fm_count < 2:
                    fm_count += 1
                    out.append(l)
                    continue
                if fm_count == 1:
                    out.append(l)
                    continue
                if "daw-setup" in l or "daw-wizard" in l or "daw-untangle" in l or "daw-ship" in l:
                    continue
                out.append(l)
            f_path.write_text("".join(out))

        eight_modules = [m for m in MODULES if m not in ("daw-setup", "daw-wizard", "daw-untangle", "daw-ship")]
        for m in eight_modules:
            alias = self.skills / m
            alias.symlink_to(installer.alias_path(m), target_is_directory=True)

        receipt = {
            "schema_version": 1,
            "suite": SUITE,
            "version": "0.1.0",
            "aliases": eight_modules,
            "files": installer.inventory(bundle),
        }
        (bundle / installer.RECEIPT).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        return bundle, eight_modules

    def test_historical_eight_module_payload_status_update_and_uninstall(self):
        bundle, eight_modules = self.setup_true_historical_eight_payload()

        status = self.cli("status")
        self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
        self.assertEqual(json.loads(status.stdout)["status"], "ready")

        update = self.cli("install", "--update")
        self.assertEqual(update.returncode, 0, update.stdout + update.stderr)
        self.assertEqual(json.loads(update.stdout)["status"], "updated")
        for m in MODULES:
            self.assertTrue((self.skills / m).is_symlink())

        status_after = self.cli("status")
        self.assertEqual(status_after.returncode, 0, status_after.stdout + status_after.stderr)
        self.assertEqual(json.loads(status_after.stdout)["status"], "ready")

        uninst = self.cli("uninstall")
        self.assertEqual(uninst.returncode, 0, uninst.stdout + uninst.stderr)
        self.assertFalse(bundle.exists())
        for m in MODULES:
            self.assertFalse((self.skills / m).exists())


    def test_historical_suite_rejects_external_manifest_module_paths(self):
        outside_file = self.base / "external-skill.md"
        outside_content = "# External Skill\nContent\n"
        outside_file.write_text(outside_content, encoding="utf-8")

        rel_escape = os.path.relpath(outside_file, self.skills / SUITE)
        for escape_path in (str(outside_file.resolve()), rel_escape):
            with self.subTest(escape_path=escape_path):
                if self.skills.exists():
                    shutil.rmtree(self.skills)
                bundle, eight_modules = self.setup_true_historical_eight_payload(
                    manifest_module_override=("daw-build", escape_path)
                )

                receipt = json.loads((bundle / installer.RECEIPT).read_text(encoding="utf-8"))
                self.assertEqual(receipt["files"], installer.inventory(bundle))

                status = self.cli("status")
                self.assertNotEqual(status.returncode, 0, status.stdout + status.stderr)
                payload = json.loads(status.stdout)
                self.assertEqual(payload.get("status"), "error")
                self.assertIn("error", payload)
                self.assertEqual(outside_file.read_text(encoding="utf-8"), outside_content)
                self.assertTrue(outside_file.is_file())
                self.assertTrue(bundle.exists())
                for m in eight_modules:
                    self.assertTrue((self.skills / m).is_symlink())
    def test_historical_eight_alias_receipt_status_update_and_uninstall(self):
        bundle = self.installed()
        eight_modules = [m for m in MODULES if m not in ("daw-setup", "daw-wizard", "daw-untangle", "daw-ship")]
        self.assertEqual(len(eight_modules), 8)
        receipt_file = bundle / ".daw-install.json"
        receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
        receipt["aliases"] = eight_modules
        receipt_file.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        for added in ("daw-setup", "daw-wizard", "daw-untangle", "daw-ship"):
            (self.skills / added).unlink()

        # Status is ready
        status = self.cli("status")
        self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
        self.assertEqual(json.loads(status.stdout)["status"], "ready")

        # Collisions protect new aliases during update
        conflict = self.skills / "daw-setup"
        conflict.mkdir(parents=True)
        (conflict / "user.txt").write_text("keep me")
        colliding_update = self.cli("install", "--update")
        self.assertEqual(colliding_update.returncode, 1)
        self.assertIn("already used by another skill", colliding_update.stdout + colliding_update.stderr)
        shutil.rmtree(conflict)

        # Tampered files preserve existing suite
        original_content = (bundle / "SKILL.md").read_bytes()
        (bundle / "SKILL.md").write_bytes(b"tampered")
        tampered_update = self.cli("install", "--update")
        self.assertEqual(tampered_update.returncode, 1)
        (bundle / "SKILL.md").write_bytes(original_content)

        # Tampered alias symlink preserves existing suite
        alias_to_tamper = self.skills / "daw-build"
        alias_to_tamper.unlink()
        alias_to_tamper.symlink_to(self.base, target_is_directory=True)
        tampered_alias = self.cli("status")
        self.assertEqual(tampered_alias.returncode, 1)
        alias_to_tamper.unlink()
        alias_to_tamper.symlink_to(installer.alias_path("daw-build"), target_is_directory=True)

        # Malformed alias shape tests fail JSON cleanly without tracebacks
        malformed_cases = [
            "non-list",
            {"invalid": "type"},
            [123],
            [{}],
            ["daw-build", 123],
            ["daw-build", "daw-build"],
            ["daw-unknown"],
            ["../daw-build"],
            ["skills/daw-build"],
        ]
        for malformed in malformed_cases:
            with self.subTest(malformed=malformed):
                receipt["aliases"] = malformed
                receipt_file.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
                malformed_res = self.cli("status")
                self.assertEqual(malformed_res.returncode, 1)
                payload = json.loads(malformed_res.stdout)
                self.assertEqual(payload["status"], "error")
                self.assertIn("Invalid installer receipt", payload["error"])

        # Restore valid 8-alias receipt for update
        receipt["aliases"] = eight_modules
        receipt_file.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

        # Actual update adds the 4 missing aliases and updates receipt to 12 modules
        update = self.cli("install", "--update")
        self.assertEqual(update.returncode, 0, update.stdout + update.stderr)
        self.assertEqual(json.loads(update.stdout)["status"], "updated")
        for m in MODULES:
            self.assertTrue((self.skills / m).is_symlink())
        updated_receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
        self.assertEqual(updated_receipt["aliases"], list(MODULES))

        # Uninstall after legacy migration succeeds
        # Also verify uninstalling directly from 8-alias legacy state
        receipt["aliases"] = eight_modules
        receipt_file.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        for added in ("daw-setup", "daw-wizard", "daw-untangle", "daw-ship"):
            (self.skills / added).unlink()
        uninst = self.cli("uninstall")
        self.assertEqual(uninst.returncode, 0, uninst.stdout + uninst.stderr)
        self.assertFalse(bundle.exists())
        for m in eight_modules:
            self.assertFalse((self.skills / m).exists())


    def setup_true_historical_ten_payload(self):
        if not self.symlinks:
            self.skipTest("Directory symlinks unavailable; root-only installation is tested separately")
        entries = installer.source_entries()
        bundle = self.skills / SUITE
        bundle.mkdir(parents=True)
        for entry in entries:
            rel = entry.relative_to(installer.SOURCE)
            target = bundle / rel
            if entry.is_dir():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(entry, target, ignore=installer.ignore_copy)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(entry, target)

        manifest_path = bundle / "references" / "suite-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["modules"].pop("daw-untangle", None)
        manifest["modules"].pop("daw-ship", None)
        shutil.rmtree(bundle / "skills" / "daw-untangle", ignore_errors=True)
        shutil.rmtree(bundle / "skills" / "daw-ship", ignore_errors=True)
        for route_name in ("untangle", "refactor", "maintain", "spike", "ship"):
            manifest["routes"].pop(route_name, None)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        for f_name in ("SKILL.md", "AGENTS.md"):
            f_path = bundle / f_name
            if not f_path.is_file():
                continue
            lines = f_path.read_text().splitlines(keepends=True)
            out = []
            fm_count = 0
            for l in lines:
                if l.strip() == "---" and fm_count < 2:
                    fm_count += 1
                    out.append(l)
                    continue
                if fm_count == 1:
                    out.append(l)
                    continue
                if "daw-untangle" in l or "daw-ship" in l:
                    continue
                out.append(l)
            f_path.write_text("".join(out))

        ten_modules = [m for m in MODULES if m not in ("daw-untangle", "daw-ship")]
        self.assertEqual(len(ten_modules), 10)
        for m in ten_modules:
            alias = self.skills / m
            alias.symlink_to(installer.alias_path(m), target_is_directory=True)

        receipt = {
            "schema_version": 1,
            "suite": SUITE,
            "version": "0.1.0",
            "aliases": ten_modules,
            "files": installer.inventory(bundle),
        }
        (bundle / installer.RECEIPT).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        return bundle, ten_modules

    def test_historical_ten_module_status(self):
        bundle, ten_modules = self.setup_true_historical_ten_payload()
        status = self.cli("status")
        self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
        self.assertEqual(json.loads(status.stdout)["status"], "ready")
        for m in ten_modules:
            self.assertTrue((self.skills / m).is_symlink())
        self.assertFalse((self.skills / "daw-untangle").exists())

    def test_historical_ten_module_update(self):
        bundle, ten_modules = self.setup_true_historical_ten_payload()
        update = self.cli("install", "--update")
        self.assertEqual(update.returncode, 0, update.stdout + update.stderr)
        self.assertEqual(json.loads(update.stdout)["status"], "updated")
        for m in MODULES:
            self.assertTrue((self.skills / m).is_symlink())
        self.assertTrue((self.skills / "daw-untangle").is_symlink())
        status_after = self.cli("status")
        self.assertEqual(status_after.returncode, 0, status_after.stdout + status_after.stderr)
        self.assertEqual(json.loads(status_after.stdout)["status"], "ready")

    def test_historical_ten_module_uninstall(self):
        bundle, ten_modules = self.setup_true_historical_ten_payload()
        uninst = self.cli("uninstall")
        self.assertEqual(uninst.returncode, 0, uninst.stdout + uninst.stderr)
        self.assertFalse(bundle.exists())
        for m in ten_modules:
            self.assertFalse((self.skills / m).exists())

    def test_foreign_untangle_alias_collision_pre_mutation_on_update(self):
        bundle, ten_modules = self.setup_true_historical_ten_payload()
        conflict = self.skills / "daw-untangle"
        conflict.mkdir(parents=True)
        (conflict / "custom_tool.py").write_text("# user owned tool\n", encoding="utf-8")

        colliding_update = self.cli("install", "--update")
        self.assertEqual(colliding_update.returncode, 1)
        self.assertIn("already used by another skill", colliding_update.stdout + colliding_update.stderr)

        # Pre-mutation guarantee: conflict file preserved, bundle intact, existing aliases intact
        self.assertTrue((conflict / "custom_tool.py").is_file())
        self.assertEqual((conflict / "custom_tool.py").read_text(encoding="utf-8"), "# user owned tool\n")
        self.assertTrue(bundle.is_dir())
        for m in ten_modules:
            self.assertTrue((self.skills / m).is_symlink())

    def test_foreign_untangle_alias_collision_on_fresh_install(self):
        self.skills.mkdir(parents=True, exist_ok=True)
        conflict = self.skills / "daw-untangle"
        conflict.write_text("existing unmanaged content", encoding="utf-8")

        fresh_install = self.cli("install")
        self.assertEqual(fresh_install.returncode, 1)
        self.assertIn("already used by another skill", fresh_install.stdout + fresh_install.stderr)
        self.assertEqual(conflict.read_text(encoding="utf-8"), "existing unmanaged content")
        self.assertFalse((self.skills / SUITE).exists())

    def test_historical_ten_module_tampered_preserves_suite(self):
        bundle, ten_modules = self.setup_true_historical_ten_payload()
        (bundle / "SKILL.md").write_text("tampered content", encoding="utf-8")

        tampered_update = self.cli("install", "--update")
        self.assertEqual(tampered_update.returncode, 1)
        self.assertIn("Installed files were changed", tampered_update.stdout + tampered_update.stderr)

        tampered_status = self.cli("status")
        self.assertEqual(tampered_status.returncode, 1)

        tampered_uninstall = self.cli("uninstall")
        self.assertEqual(tampered_uninstall.returncode, 1)
        self.assertTrue(bundle.is_dir())

    def test_installed_bundle_can_reinstall_from_itself(self):
        bundle = self.installed()
        second_skills = self.base / "second-project" / ".agents" / "skills"
        result = self.cli("install", "--skills-dir", str(second_skills), source=bundle, custom=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        second_bundle = second_skills / SUITE
        self.assertTrue((second_bundle / "SKILL.md").is_file())
        self.assertFalse((second_bundle / "tests").exists())
        self.assertFalse((second_bundle / "docs").exists())
        self.assertTrue((second_bundle / "scripts" / "package_layout.py").is_file())
        status = self.cli("status", "--skills-dir", str(second_skills), source=second_bundle, custom=False)
        self.assertEqual(status.returncode, 0, status.stdout + status.stderr)

    def setup_true_historical_eleven_payload(self):
        if not self.symlinks:
            self.skipTest("Directory symlinks unavailable; root-only installation is tested separately")
        entries = installer.source_entries()
        bundle = self.skills / SUITE
        bundle.mkdir(parents=True)
        for entry in entries:
            rel = entry.relative_to(installer.SOURCE)
            target = bundle / rel
            if entry.is_dir():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(entry, target, ignore=installer.ignore_copy)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(entry, target)
        manifest_path = bundle / "references" / "suite-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["modules"].pop("daw-ship", None)
        shutil.rmtree(bundle / "skills" / "daw-ship", ignore_errors=True)
        for route_name in ("refactor", "maintain", "spike", "ship"):
            manifest["routes"].pop(route_name, None)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        for f_name in ("SKILL.md", "AGENTS.md"):
            f_path = bundle / f_name
            if not f_path.is_file():
                continue
            lines = f_path.read_text().splitlines(keepends=True)
            out = []
            fm_count = 0
            for l in lines:
                if l.strip() == "---" and fm_count < 2:
                    fm_count += 1
                    out.append(l)
                    continue
                if fm_count == 1:
                    out.append(l)
                    continue
                if "daw-ship" in l:
                    continue
                out.append(l)
            f_path.write_text("".join(out))
        eleven_modules = [m for m in MODULES if m != "daw-ship"]
        self.assertEqual(len(eleven_modules), 11)
        for m in eleven_modules:
            alias = self.skills / m
            alias.symlink_to(installer.alias_path(m), target_is_directory=True)
        receipt = {
            "schema_version": 1,
            "suite": SUITE,
            "version": "0.1.0",
            "aliases": eleven_modules,
            "files": installer.inventory(bundle),
        }
        (bundle / installer.RECEIPT).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        return bundle, eleven_modules

    def test_historical_eleven_module_status_update_and_uninstall(self):
        bundle, eleven_modules = self.setup_true_historical_eleven_payload()
        status = self.cli("status")
        self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
        self.assertEqual(json.loads(status.stdout)["status"], "ready")
        self.assertFalse((self.skills / "daw-ship").exists())
        update = self.cli("install", "--update")
        self.assertEqual(update.returncode, 0, update.stdout + update.stderr)
        self.assertEqual(json.loads(update.stdout)["status"], "updated")
        for m in MODULES:
            self.assertTrue((self.skills / m).is_symlink())
        self.assertTrue((bundle / "skills" / "daw-ship" / "SKILL.md").is_file())
        status_after = self.cli("status")
        self.assertEqual(status_after.returncode, 0, status_after.stdout + status_after.stderr)
        self.assertEqual(json.loads(status_after.stdout)["status"], "ready")
        uninst = self.cli("uninstall")
        self.assertEqual(uninst.returncode, 0, uninst.stdout + uninst.stderr)
        self.assertFalse(bundle.exists())
        for m in MODULES:
            self.assertFalse((self.skills / m).exists())

    def test_legacy_full_eleven_migration_and_tamper_protection(self):
        if not self.symlinks:
            self.skipTest("Directory symlinks unavailable; root-only installation is tested separately")
        bundle = self.skills / SUITE
        bundle.mkdir(parents=True)
        for name in ("SKILL.md", "README.md", "AGENTS.md", "LICENSE", "VERSION", "CHANGELOG.md", "references", "templates", "skills", "docs", "tests", "tools"):
            src = ROOT / name
            if not src.exists():
                continue
            dst = bundle / name
            if src.is_dir():
                shutil.copytree(src, dst, ignore=installer.ignore_copy)
            else:
                shutil.copy2(src, dst)
        scripts_dir = bundle / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        for s in ("install.py", "route.py", "validate.py", "doc_quality.py", "package_layout.py"):
            if (ROOT / "scripts" / s).exists():
                shutil.copy2(ROOT / "scripts" / s, scripts_dir / s)
        for m in MODULES:
            alias = self.skills / m
            alias.symlink_to(installer.alias_path(m), target_is_directory=True)
        inv = installer.inventory(bundle)
        receipt = {
            "schema_version": 1,
            "suite": SUITE,
            "version": (bundle / "VERSION").read_text(encoding="utf-8").strip(),
            "aliases": list(MODULES),
            "files": inv,
        }
        (bundle / installer.RECEIPT).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

        # 1. Status passes on legacy full 11
        status = self.cli("status")
        self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
        payload = json.loads(status.stdout)
        self.assertEqual(payload["status"], "ready")

        # 2. Tampering with any file in legacy bundle (even docs/tests) prevents update
        test_file = bundle / "docs" / "tamper_test.txt"
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text("user edits", encoding="utf-8")
        failed_update = self.cli("install", "--update")
        self.assertEqual(failed_update.returncode, 1)
        self.assertIn("preserving local work", failed_update.stdout + failed_update.stderr)
        test_file.unlink()

        # 3. Clean update migrates legacy bundle to new minimal bundle
        update = self.cli("install", "--update")
        self.assertEqual(update.returncode, 0, update.stdout + update.stderr)
        self.assertEqual(json.loads(update.stdout)["status"], "updated")

        # 4. In minimal bundle, dev files are absent and package_layout is present
        self.assertFalse((bundle / "tests").exists())
        self.assertFalse((bundle / "docs").exists())
        self.assertFalse((bundle / "README.md").exists())
        self.assertFalse((bundle / "AGENTS.md").exists())
        self.assertTrue((bundle / "scripts" / "package_layout.py").is_file())
        for m in MODULES:
            self.assertTrue((self.skills / m).is_symlink())

        # 5. Status passes after migration
        status_after = self.cli("status")
        self.assertEqual(status_after.returncode, 0, status_after.stdout + status_after.stderr)

if __name__ == "__main__":
    unittest.main()
