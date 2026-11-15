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

    def _bump_source_version(self, source: Path) -> str:
        previous_version = (source / "VERSION").read_text(encoding="utf-8").strip()
        parts = previous_version.split(".")
        bumped = ".".join([*parts[:-1], str(int(parts[-1]) + 1)])
        (source / "VERSION").write_text(bumped + "\n", encoding="utf-8")
        skill = source / "SKILL.md"
        skill.write_text(
            skill.read_text(encoding="utf-8").replace(f'version: "{previous_version}"', f'version: "{bumped}"', 1),
            encoding="utf-8",
        )
        for rel in (
            ".claude-plugin/plugin.json",
            ".claude-plugin/marketplace.json",
            ".cursor-plugin/plugin.json",
            ".codex-plugin/plugin.json",
        ):
            manifest = source / rel
            if manifest.is_file():
                data = json.loads(manifest.read_text(encoding="utf-8"))
                if isinstance(data.get("version"), str):
                    data["version"] = bumped
                if isinstance(data.get("metadata"), dict) and isinstance(data["metadata"].get("version"), str):
                    data["metadata"]["version"] = bumped
                for plugin in data.get("plugins", []) if isinstance(data.get("plugins"), list) else []:
                    if isinstance(plugin, dict) and isinstance(plugin.get("version"), str):
                        plugin["version"] = bumped
                manifest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return bumped

    def test_upgrade_requires_update_flag_and_keeps_aliases(self):
        bundle = self.installed()
        source = self.source_copy()
        bumped = self._bump_source_version(source)
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
        mappings = {
            "codex": (".agents/skills", ".agents/skills"),
            "claude": (".claude/skills", ".claude/skills"),
            "gemini": (".gemini/skills", ".gemini/skills"),
            "cursor": (".cursor/skills", ".cursor/skills"),
            "copilot": (".github/skills", ".copilot/skills"),
            "opencode": (".opencode/skills", ".config/opencode/skills"),
            "antigravity": (".gemini/antigravity/skills", ".gemini/antigravity/skills"),
        }
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
        self._bump_source_version(source)
        result = self.cli("install", "--dry-run", source=source)
        self.assertEqual(result.returncode, 1)
        self.assertIn("--update", json.loads(result.stdout)["error"])

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
        for name in ("SKILL.md", "README.md", "AGENTS.md", "LICENSE", "VERSION", "CHANGELOG.md", "pyproject.toml", ".claude-plugin", "references", "templates", "skills", "docs", "tests", "tools"):
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
        for s in (Path(p).name for p in installer.package_layout.OPERATIONAL_SCRIPTS):
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

    def test_unchanged_install_and_update_short_circuit_without_staging(self):
        if not self.symlinks:
            self.skipTest("Directory symlinks unavailable")
        with mock.patch.object(installer, "staging_area", wraps=installer.staging_area) as stage_spy:
            first = installer.install(self.skills, update=False, no_aliases=False, dry_run=False)
            self.assertEqual(first["status"], "installed")
            self.assertEqual(stage_spy.call_count, 1)

            stage_spy.reset_mock()
            repeat = installer.install(self.skills, update=False, no_aliases=False, dry_run=False)
            self.assertEqual(repeat["status"], "unchanged")
            self.assertEqual(stage_spy.call_count, 0)

            repeat_update = installer.install(self.skills, update=True, no_aliases=False, dry_run=False)
            self.assertEqual(repeat_update["status"], "unchanged")
            self.assertEqual(stage_spy.call_count, 0)

        # Tamper detection still fires before any short-circuit.
        skill_md = self.skills / SUITE / "SKILL.md"
        original = skill_md.read_bytes()
        skill_md.write_bytes(b"tampered")
        with self.assertRaisesRegex(installer.InstallError, "Installed files were changed"):
            installer.install(self.skills, update=True, no_aliases=False, dry_run=False)
        skill_md.write_bytes(original)

        # Switching to --no-aliases does not short-circuit and runs staging.
        with mock.patch.object(installer, "staging_area", wraps=installer.staging_area) as stage_spy:
            updated = installer.install(self.skills, update=True, no_aliases=True, dry_run=False)
            self.assertEqual(updated["status"], "updated")
            self.assertEqual(stage_spy.call_count, 1)

    def test_agent_all_install_status_and_uninstall(self):
        if not self.symlinks:
            self.skipTest("Directory symlinks unavailable")
        project = self.base / "all-agents-proj"
        project.mkdir()

        # Status before install: all missing, exit 1
        st_before = self.cli("status", "--agent", "all", "--scope", "project", "--project-root", str(project), custom=False)
        self.assertEqual(st_before.returncode, 1)
        st_before_json = json.loads(st_before.stdout)
        self.assertEqual(st_before_json["status"], "missing")
        self.assertEqual(len(st_before_json["results"]), len(installer.SKILL_DIRS))

        # Install all presets
        inst = self.cli("install", "--agent", "all", "--scope", "project", "--project-root", str(project), custom=False)
        self.assertEqual(inst.returncode, 0, inst.stdout + inst.stderr)
        inst_json = json.loads(inst.stdout)
        self.assertEqual(inst_json["status"], "installed")
        self.assertEqual(inst_json["summary"]["installed"], len(installer.SKILL_DIRS))
        for agent, (local, _) in installer.SKILL_DIRS.items():
            self.assertTrue((project / local / SUITE / "SKILL.md").is_file(), agent)

        # Repeat install --agent all returns unchanged
        repeat = self.cli("install", "--agent", "all", "--scope", "project", "--project-root", str(project), custom=False)
        self.assertEqual(repeat.returncode, 0, repeat.stdout + repeat.stderr)
        self.assertEqual(json.loads(repeat.stdout)["status"], "unchanged")

        # Status after install (both JSON and text)
        st_after = self.cli("status", "--agent", "all", "--scope", "project", "--project-root", str(project), custom=False)
        self.assertEqual(st_after.returncode, 0, st_after.stdout + st_after.stderr)
        st_after_json = json.loads(st_after.stdout)
        self.assertEqual(st_after_json["status"], "ready")
        self.assertEqual(st_after_json["summary"]["ready"], len(installer.SKILL_DIRS))

        st_text = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "install.py"), "status", "--agent", "all", "--scope", "project", "--project-root", str(project)],
            cwd=self.base, env=self.env, capture_output=True, text=True,
        )
        self.assertEqual(st_text.returncode, 0, st_text.stderr)
        for agent in installer.SKILL_DIRS:
            self.assertIn(f"{agent}: ready", st_text.stdout)

        # Uninstall all
        uninst = self.cli("uninstall", "--agent", "all", "--scope", "project", "--project-root", str(project), custom=False)
        self.assertEqual(uninst.returncode, 0, uninst.stdout + uninst.stderr)
        self.assertEqual(json.loads(uninst.stdout)["status"], "removed")
        for _, (local, _) in installer.SKILL_DIRS.items():
            self.assertFalse((project / local / SUITE).exists())

    def test_agent_all_partial_collision_and_partial_uninstall(self):
        if not self.symlinks:
            self.skipTest("Directory symlinks unavailable")
        project = self.base / "partial-all-proj"
        conflict = project / ".claude" / "skills" / "daw-build"
        conflict.mkdir(parents=True)
        (conflict / "keep.txt").write_text("user skill", encoding="utf-8")

        inst = self.cli("install", "--agent", "all", "--scope", "project", "--project-root", str(project), custom=False)
        self.assertEqual(inst.returncode, 1)
        payload = json.loads(inst.stdout)
        self.assertEqual(payload["status"], "error")
        by_agent = {r["agent"]: r for r in payload["results"]}
        self.assertEqual(by_agent["claude"]["status"], "error")
        self.assertEqual(by_agent["codex"]["status"], "installed")
        self.assertEqual(by_agent["opencode"]["status"], "installed")
        self.assertEqual(by_agent["antigravity"]["status"], "installed")
        self.assertEqual((conflict / "keep.txt").read_text(encoding="utf-8"), "user skill")

        # Partial status reports partial and exits 1
        st = self.cli("status", "--agent", "all", "--scope", "project", "--project-root", str(project), custom=False)
        self.assertEqual(st.returncode, 1)
        self.assertEqual(json.loads(st.stdout)["status"], "partial")

        # Uninstall --agent all removes installed presets and treats absent ones as missing (exit 0)
        uninst = self.cli("uninstall", "--agent", "all", "--scope", "project", "--project-root", str(project), custom=False)
        self.assertEqual(uninst.returncode, 0, uninst.stdout + uninst.stderr)
        uninst_json = json.loads(uninst.stdout)
        self.assertEqual(uninst_json["status"], "removed")
        self.assertEqual(uninst_json["summary"]["removed"], len(installer.SKILL_DIRS) - 1)
        self.assertEqual(uninst_json["summary"]["missing"], 1)

        # --agent all cannot be combined with --skills-dir
        bad = self.cli("install", "--agent", "all")
        self.assertEqual(bad.returncode, 2)

    def test_doctor_checks_prerequisites_and_overlapping_installations(self):
        project = self.base / "doctor-proj"
        project.mkdir()

        # Clean project: read-only, exit 0, no directories created
        doc_clean = self.cli("doctor", "--scope", "project", "--project-root", str(project), custom=False)
        self.assertEqual(doc_clean.returncode, 0, doc_clean.stdout + doc_clean.stderr)
        clean_json = json.loads(doc_clean.stdout)
        self.assertEqual(clean_json["status"], "ok")
        self.assertTrue(clean_json["checks"]["python"]["ok"])
        self.assertTrue(clean_json["checks"]["git"]["ok"])
        self.assertEqual(clean_json["overlaps"], [])
        self.assertFalse((project / ".agents").exists())
        self.assertFalse((project / ".claude").exists())

        if not self.symlinks:
            self.skipTest("Directory symlinks unavailable")

        # Overlapping codex (.agents/skills) + claude (.claude/skills)
        for agent in ("codex", "claude"):
            res = self.cli("install", "--agent", agent, "--scope", "project", "--project-root", str(project), custom=False)
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        doc_overlap = self.cli("doctor", "--scope", "project", "--project-root", str(project), custom=False)
        self.assertEqual(doc_overlap.returncode, 0, doc_overlap.stdout + doc_overlap.stderr)
        overlap_json = json.loads(doc_overlap.stdout)
        self.assertEqual(overlap_json["status"], "warning")
        self.assertTrue(overlap_json["overlaps"])
        self.assertIn("codex", overlap_json["overlaps"][0]["agents"])
        self.assertIn("claude", overlap_json["overlaps"][0]["agents"])

        # Also test gemini + antigravity overlap
        for agent in ("codex", "claude"):
            self.cli("uninstall", "--agent", agent, "--scope", "project", "--project-root", str(project), custom=False)
        for agent in ("gemini", "antigravity"):
            res = self.cli("install", "--agent", agent, "--scope", "project", "--project-root", str(project), custom=False)
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        doc_gem = self.cli("doctor", "--scope", "project", "--project-root", str(project), custom=False)
        gem_json = json.loads(doc_gem.stdout)
        self.assertEqual(gem_json["status"], "warning")
        self.assertTrue(any(set(o["agents"]) == {"gemini", "antigravity"} for o in gem_json["overlaps"]))

        # Text output renders cleanly
        doc_text = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "install.py"), "doctor", "--scope", "project", "--project-root", str(project)],
            cwd=self.base, env=self.env, capture_output=True, text=True,
        )
        self.assertEqual(doc_text.returncode, 0, doc_text.stderr)
        self.assertIn("doctor (project): warning", doc_text.stdout)
        self.assertIn("gemini: ready", doc_text.stdout)

        # Tampered preset causes doctor error (exit 1)
        (project / ".gemini" / "skills" / SUITE / "SKILL.md").write_text("tampered", encoding="utf-8")
        doc_err = self.cli("doctor", "--scope", "project", "--project-root", str(project), custom=False)
        self.assertEqual(doc_err.returncode, 1)
        self.assertEqual(json.loads(doc_err.stdout)["status"], "error")

        # --dry-run is rejected on doctor
        bad_doc = self.cli("doctor", "--dry-run", custom=False)
        self.assertEqual(bad_doc.returncode, 2)

    def test_doctor_detects_missing_git_and_unsupported_symlinks(self):
        project = self.base / "doctor-env"
        project.mkdir()

        old_git = subprocess.CompletedProcess(args=["git", "--version"], returncode=0, stdout="git version 2.19.1\n", stderr="")
        with mock.patch.object(installer.subprocess, "run", return_value=old_git):
            payload, code = installer.doctor("project", project)
        self.assertEqual(code, 1)
        self.assertEqual(payload["status"], "error")
        self.assertFalse(payload["checks"]["git"]["ok"])

        with mock.patch.object(installer.subprocess, "run", side_effect=FileNotFoundError("no git")):
            payload_missing, code_missing = installer.doctor("project", project)
        self.assertEqual(code_missing, 1)
        self.assertFalse(payload_missing["checks"]["git"]["available"])

        with mock.patch.object(Path, "symlink_to", side_effect=OSError("no symlinks")):
            payload_sym, code_sym = installer.doctor("project", project)
        self.assertEqual(code_sym, 0)
        self.assertEqual(payload_sym["status"], "warning")
        self.assertFalse(payload_sym["checks"]["symlinks"]["supported"])

    def test_link_mode_install_status_live_edits_and_uninstall(self):
        if not self.symlinks:
            self.skipTest("Directory symlinks unavailable")
        source = self.source_copy()
        res = self.cli("install", "--link", source=source)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        payload = json.loads(res.stdout)
        self.assertEqual(payload["status"], "installed")
        self.assertEqual(payload["mode"], "link")
        self.assertEqual(Path(payload["target"]), source.resolve())

        bundle = self.skills / SUITE
        self.assertTrue(bundle.is_symlink())
        self.assertEqual(bundle.resolve(), source.resolve())
        link_receipt = self.skills / installer.LINK_RECEIPT
        self.assertTrue(link_receipt.is_file())
        # Never write receipts inside SOURCE checkout
        self.assertFalse((source / installer.RECEIPT).exists())
        self.assertFalse((source / installer.LINK_RECEIPT).exists())

        for m in MODULES:
            alias = self.skills / m
            self.assertTrue(alias.is_symlink())
            self.assertEqual(alias.resolve(), (source / "skills" / m).resolve())

        # Repeat install --link is unchanged without creating staging
        repeat = self.cli("install", "--link", source=source)
        self.assertEqual(repeat.returncode, 0, repeat.stdout + repeat.stderr)
        self.assertEqual(json.loads(repeat.stdout)["status"], "unchanged")

        # Live edits in SOURCE are allowed in link mode without tamper error
        (source / "references" / "dev-notes.md").write_text("# Live dev note\n", encoding="utf-8")
        st = self.cli("status", source=source)
        self.assertEqual(st.returncode, 0, st.stdout + st.stderr)
        st_json = json.loads(st.stdout)
        self.assertEqual(st_json["status"], "ready")
        self.assertEqual(st_json["mode"], "link")

        # Uninstall removes symlinks and link receipt while leaving SOURCE intact
        uninst = self.cli("uninstall", source=source)
        self.assertEqual(uninst.returncode, 0, uninst.stdout + uninst.stderr)
        self.assertEqual(json.loads(uninst.stdout)["status"], "removed")
        self.assertFalse(bundle.is_symlink())
        self.assertFalse(link_receipt.exists())
        for m in MODULES:
            self.assertFalse((self.skills / m).is_symlink())
        self.assertTrue((source / "SKILL.md").is_file())
        self.assertTrue((source / "references" / "dev-notes.md").is_file())

    def test_link_mode_safety_foreign_symlinks_and_mode_switching(self):
        if not self.symlinks:
            self.skipTest("Directory symlinks unavailable")
        source = self.source_copy()
        foreign = self.base / "foreign-suite"
        foreign.mkdir()

        # Unowned foreign symlink at bundle path is rejected by status/install/uninstall
        self.skills.mkdir(parents=True, exist_ok=True)
        (self.skills / SUITE).symlink_to(foreign, target_is_directory=True)
        for action, extra in (("status", ()), ("install", ("--link", "--update")), ("uninstall", ())):
            res = self.cli(action, *extra, source=source)
            self.assertEqual(res.returncode, 1)
            self.assertEqual((self.skills / SUITE).resolve(), foreign.resolve())
        (self.skills / SUITE).unlink()

        # Link install with --no-aliases, then tamper target symlink -> rejected
        res = self.cli("install", "--link", "--no-aliases", source=source)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertFalse((self.skills / "daw-build").exists())
        (self.skills / SUITE).unlink()
        (self.skills / SUITE).symlink_to(foreign, target_is_directory=True)
        self.assertEqual(self.cli("status", source=source).returncode, 1)
        self.assertEqual(self.cli("uninstall", source=source).returncode, 1)
        (self.skills / SUITE).unlink()
        (self.skills / SUITE).symlink_to(source.resolve(), target_is_directory=True)

        # Switching link -> copy requires --update, then succeeds with --update
        self.assertEqual(self.cli("install", source=source).returncode, 1)
        to_copy = self.cli("install", "--update", source=source)
        self.assertEqual(to_copy.returncode, 0, to_copy.stdout + to_copy.stderr)
        self.assertEqual(json.loads(to_copy.stdout)["status"], "updated")
        self.assertFalse((self.skills / SUITE).is_symlink())
        self.assertTrue((self.skills / SUITE).is_dir())
        self.assertFalse((self.skills / installer.LINK_RECEIPT).exists())

        # Switching copy -> link requires --update, then succeeds with --update
        self.assertEqual(self.cli("install", "--link", source=source).returncode, 1)
        to_link = self.cli("install", "--link", "--update", source=source)
        self.assertEqual(to_link.returncode, 0, to_link.stdout + to_link.stderr)
        self.assertEqual(json.loads(to_link.stdout)["status"], "updated")
        self.assertTrue((self.skills / SUITE).is_symlink())
        self.assertTrue((self.skills / installer.LINK_RECEIPT).is_file())

        # --link fails cleanly if directory symlinks are unavailable
        with mock.patch.object(Path, "symlink_to", side_effect=OSError("links disabled")):
            with self.assertRaisesRegex(installer.InstallError, "--link"):
                installer.install(self.base / "no-sym-skills", update=False, no_aliases=False, dry_run=False, link=True)

        # --link rejected on non-install actions
        self.assertEqual(self.cli("status", "--link").returncode, 2)

    def test_historical_profile_constants_remain_consistent(self):
        self.assertEqual(len(installer.HISTORICAL_8_MODULES), 8)
        self.assertEqual(len(installer.HISTORICAL_10_MODULES), 10)
        self.assertEqual(len(installer.HISTORICAL_11_MODULES), 11)
        self.assertEqual(len(installer.HISTORICAL_PROFILES), 3)
        self.assertEqual(set(installer.HISTORICAL_10_ROUTES["bootstrap"]["stages"]), {"daw-wizard", "daw-design", "daw-plan"})
        self.assertIn("setup", installer.HISTORICAL_10_ROUTES)
        self.assertIn("untangle", installer.HISTORICAL_11_ROUTES)

    def test_interactive_wizard_single_multi_and_project_config(self):
        alias_flag = [] if self.symlinks else ["--no-aliases"]
        (self.base / "home" / ".cursor").mkdir(parents=True, exist_ok=True)
        res_user = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "install.py"), "--interactive", *alias_flag],
            cwd=self.base,
            env=self.env,
            input="1\n\n",
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_user.returncode, 0, res_user.stderr + res_user.stdout)
        self.assertIn("[detected]", res_user.stdout)
        self.assertTrue((self.base / "home" / ".cursor" / "skills" / SUITE / "SKILL.md").is_file())
        self.assertFalse((self.base / "home" / ".agents" / "skills" / SUITE).exists())

        agents_list = tuple(installer.SKILL_DIRS.keys())
        project_one = self.base / "wizard-proj-one"
        project_one.mkdir(parents=True, exist_ok=True)
        res_multi = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "install.py"),
                "--interactive",
                "--project-root",
                str(project_one),
                *alias_flag,
            ],
            cwd=self.base,
            env=self.env,
            input="2\n1,2\ny\n",
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_multi.returncode, 0, res_multi.stderr + res_multi.stdout)
        for idx in (0, 1):
            local_rel = installer.SKILL_DIRS[agents_list[idx]][0]
            self.assertTrue((project_one / local_rel / SUITE / "SKILL.md").is_file())
        self.assertTrue((project_one / "AGENTS.md").is_file())
        self.assertIn("<!-- daw-config:start -->", (project_one / "AGENTS.md").read_text(encoding="utf-8"))
        val = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate.py"), "config", "AGENTS.md", "--project-root", str(project_one), "--format", "json"],
            cwd=self.base,
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(val.returncode, 0, val.stderr + val.stdout)
        self.assertTrue(json.loads(val.stdout)["valid"])

        project_all = self.base / "wizard-proj-all"
        project_all.mkdir(parents=True, exist_ok=True)
        res_all = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "install.py"),
                "--interactive",
                "--project-root",
                str(project_all),
                *alias_flag,
            ],
            cwd=self.base,
            env=self.env,
            input="2\na\nn\n",
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_all.returncode, 0, res_all.stderr + res_all.stdout)
        for agent, (local_rel, _) in installer.SKILL_DIRS.items():
            self.assertTrue((project_all / local_rel / SUITE / "SKILL.md").is_file(), agent)
        self.assertFalse((project_all / "AGENTS.md").exists())

    def test_init_config_creates_valid_daw_config_and_is_idempotent(self):
        alias_flag = [] if self.symlinks else ["--no-aliases"]
        project = self.base / "cfg-proj"
        project.mkdir(parents=True, exist_ok=True)

        dry = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "install.py"),
                "install",
                "--agent",
                "codex",
                "--scope",
                "project",
                "--project-root",
                str(project),
                "--init-config",
                "--dry-run",
                "--json",
            ],
            cwd=self.base,
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(dry.returncode, 0, dry.stderr + dry.stdout)
        dry_payload = json.loads(dry.stdout)
        self.assertEqual(dry_payload["status"], "planned")
        self.assertEqual(dry_payload["config"]["status"], "planned")
        self.assertFalse((project / "AGENTS.md").exists())
        self.assertFalse((project / "docs").exists())

        res = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "install.py"),
                "install",
                "--agent",
                "codex",
                "--scope",
                "project",
                "--project-root",
                str(project),
                "--init-config",
                *alias_flag,
                "--json",
            ],
            cwd=self.base,
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
        payload = json.loads(res.stdout)
        self.assertEqual(payload["config"]["status"], "created")
        self.assertTrue((project / "AGENTS.md").is_file())
        self.assertTrue((project / "docs" / "specs").is_dir())

        val = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate.py"), "config", "AGENTS.md", "--project-root", str(project), "--format", "json"],
            cwd=self.base,
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(val.returncode, 0, val.stderr + val.stdout)
        self.assertTrue(json.loads(val.stdout)["valid"])

        agents_before = (project / "AGENTS.md").read_text(encoding="utf-8")
        again = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "install.py"),
                "install",
                "--agent",
                "codex",
                "--scope",
                "project",
                "--project-root",
                str(project),
                "--update",
                "--init-config",
                *alias_flag,
                "--json",
            ],
            cwd=self.base,
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(again.returncode, 0, again.stderr + again.stdout)
        self.assertEqual(json.loads(again.stdout)["config"]["status"], "unchanged")
        self.assertEqual((project / "AGENTS.md").read_text(encoding="utf-8"), agents_before)

        claude_proj = self.base / "cfg-claude"
        claude_proj.mkdir(parents=True, exist_ok=True)
        (claude_proj / "CLAUDE.md").write_text("# CLAUDE\n\nExisting notes.\n", encoding="utf-8")
        res_claude = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "install.py"),
                "install",
                "--agent",
                "claude",
                "--scope",
                "project",
                "--project-root",
                str(claude_proj),
                "--init-config",
                *alias_flag,
                "--json",
            ],
            cwd=self.base,
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_claude.returncode, 0, res_claude.stderr + res_claude.stdout)
        self.assertEqual(json.loads(res_claude.stdout)["config"]["status"], "updated")
        self.assertFalse((claude_proj / "AGENTS.md").exists())
        claude_text = (claude_proj / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("Existing notes.", claude_text)
        self.assertIn("<!-- daw-config:start -->", claude_text)
        val_claude = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate.py"), "config", "CLAUDE.md", "--project-root", str(claude_proj), "--format", "json"],
            cwd=self.base,
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(val_claude.returncode, 0, val_claude.stderr + val_claude.stdout)
        self.assertTrue(json.loads(val_claude.stdout)["valid"])

        bad_scope = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "install.py"),
                "install",
                "--agent",
                "codex",
                "--scope",
                "user",
                "--init-config",
            ],
            cwd=self.base,
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(bad_scope.returncode, 0)

    @unittest.skipIf(os.name == "nt" or shutil.which("bash") is None, "POSIX bash required for install.sh")
    def test_install_sh_local_and_forwarded_args(self):
        alias_flag = [] if self.symlinks else ["--no-aliases"]
        env = dict(self.env, DAW_SOURCE_DIR=str(ROOT))
        res_cli = subprocess.run(
            ["bash", str(ROOT / "install.sh"), "install", "--skills-dir", str(self.skills), *alias_flag, "--json"],
            cwd=self.base,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_cli.returncode, 0, res_cli.stderr + res_cli.stdout)
        self.assertEqual(json.loads(res_cli.stdout)["status"], "installed")
        self.assertTrue((self.skills / SUITE / "SKILL.md").is_file())

        sh_proj = self.base / "sh-interactive-proj"
        sh_proj.mkdir(parents=True, exist_ok=True)
        res_wiz = subprocess.run(
            ["bash", str(ROOT / "install.sh"), "--interactive", "--project-root", str(sh_proj), *alias_flag],
            cwd=self.base,
            env=env,
            input="2\n1\ny\n",
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_wiz.returncode, 0, res_wiz.stderr + res_wiz.stdout)
        first_local = installer.SKILL_DIRS[tuple(installer.SKILL_DIRS.keys())[0]][0]
        self.assertTrue((sh_proj / first_local / SUITE / "SKILL.md").is_file())
        self.assertTrue((sh_proj / "AGENTS.md").is_file())


if __name__ == "__main__":
    unittest.main()
