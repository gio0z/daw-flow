#!/usr/bin/env python3
"""Tests for unified `daw` CLI, `.claude-plugin` validation, `package_layout`, and `pyproject.toml`."""

from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import setup  # noqa: E402
from scripts import check_package, daw, daw_common, install as installer, package_layout  # noqa: E402


def _parse_pyproject(path: pathlib.Path) -> dict:
    """Parse pyproject.toml using tomllib on Python 3.11+ with a minimal stdlib fallback for 3.10."""
    raw = path.read_text(encoding="utf-8")
    try:
        import tomllib  # type: ignore[import-not-found]

        return tomllib.loads(raw)
    except ModuleNotFoundError:
        project: dict[str, object] = {}
        scripts: dict[str, str] = {}
        section = ""
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("[") and stripped.endswith("]"):
                section = stripped[1:-1].strip()
                continue
            m = re.match(r'^([A-Za-z0-9_-]+)\s*=\s*"([^"]*)"$', stripped)
            if m:
                key, val = m.group(1), m.group(2)
                if section == "project":
                    project[key] = val
                elif section == "project.scripts":
                    scripts[key] = val
            elif section == "project" and re.match(r"^dependencies\s*=\s*\[\s*\]$", stripped):
                project["dependencies"] = []
        return {"project": project, "scripts": scripts}


def _copy_minimal_suite(dest_parent: pathlib.Path) -> pathlib.Path:
    """Copy a minimal suite directory named `deterministic-agentic-workflow` without `.claude-plugin`."""
    pkg = dest_parent / "deterministic-agentic-workflow"
    pkg.mkdir(parents=True, exist_ok=True)
    for fname in ("SKILL.md", "VERSION", "LICENSE"):
        shutil.copy2(REPO_ROOT / fname, pkg / fname)
    for dname in ("references", "templates", "skills", "scripts"):
        shutil.copytree(
            REPO_ROOT / dname,
            pkg / dname,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    return pkg


class DawCliTests(unittest.TestCase):
    def _run_daw(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "daw.py"), *args],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_dont_write_bytecode_enabled(self) -> None:
        self.assertTrue(daw.sys.dont_write_bytecode)

    def test_help_and_version(self) -> None:
        expected_version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
        for flag in ("--version", "-V"):
            res = self._run_daw(flag)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertEqual(res.stdout.strip(), f"daw {expected_version}")

        for flag in ("--help", "-h"):
            res = self._run_daw(flag)
            self.assertEqual(res.returncode, 0, res.stderr)
            for cmd in (
                "route",
                "validate",
                "run",
                "worktree",
                "install",
                "derive-ledger",
                "derive-tasks",
                "feedback",
            ):
                self.assertIn(cmd, res.stdout)

    def test_no_args_and_unknown_subcommand_exit_two(self) -> None:
        empty = self._run_daw()
        self.assertEqual(empty.returncode, 2)
        self.assertIn("usage: daw", empty.stderr)

        unknown = self._run_daw("does-not-exist")
        self.assertEqual(unknown.returncode, 2)
        self.assertIn("unknown subcommand", unknown.stderr)

    def test_subcommand_help_passthrough_and_exit_codes(self) -> None:
        for cmd in (
            "route",
            "validate",
            "run",
            "worktree",
            "install",
            "derive-ledger",
            "derive-tasks",
            "feedback",
        ):
            res = self._run_daw(cmd, "--help")
            self.assertEqual(res.returncode, 0, f"{cmd} --help failed: {res.stderr}")
            self.assertIn("usage:", res.stdout.lower())

        ok_route = self._run_daw("route", "--check-suite", "--format", "json")
        self.assertEqual(ok_route.returncode, 0, ok_route.stderr)
        self.assertEqual(json.loads(ok_route.stdout)["status"], "ready")

        err_route = self._run_daw("route", str(REPO_ROOT / "does-not-exist.json"))
        self.assertEqual(err_route.returncode, 2)

        with tempfile.TemporaryDirectory() as tmpdir:
            bad_pkg = self._run_daw("validate", "package", "--root", tmpdir, "--format", "json")
            self.assertEqual(bad_pkg.returncode, 1)
            self.assertFalse(json.loads(bad_pkg.stdout)["valid"])


class PluginAndPackagingTests(unittest.TestCase):
    def test_package_layout_exports(self) -> None:
        self.assertIn("scripts/daw.py", package_layout.OPERATIONAL_SCRIPTS)
        self.assertIn(".claude-plugin", package_layout.OPTIONAL_DIRS)
        self.assertIn(".cursor-plugin", package_layout.OPTIONAL_DIRS)
        self.assertIn(".codex-plugin", package_layout.OPTIONAL_DIRS)
        for attr in ("OPERATIONAL_SCRIPTS", "REQUIRED_FILES", "REQUIRED_DIRS", "OPTIONAL_DIRS", "operational_entries"):
            self.assertTrue(hasattr(package_layout, attr))

    def test_repo_plugin_manifests_valid_and_synced_with_version(self) -> None:
        version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
        for rel in (".claude-plugin/plugin.json", ".cursor-plugin/plugin.json", ".codex-plugin/plugin.json"):
            plugin_path = REPO_ROOT / rel
            self.assertTrue(plugin_path.is_file(), rel)
            plugin = daw_common.parse_strict_json(plugin_path.read_text(encoding="utf-8"))
            self.assertEqual(plugin["name"], "deterministic-agentic-workflow", rel)
            self.assertEqual(plugin["version"], version, rel)

        marketplace_path = REPO_ROOT / ".claude-plugin" / "marketplace.json"
        self.assertTrue(marketplace_path.is_file())
        marketplace = daw_common.parse_strict_json(marketplace_path.read_text(encoding="utf-8"))
        self.assertEqual(marketplace["name"], "deterministic-agentic-workflow")
        self.assertEqual(marketplace["plugins"][0]["name"], "deterministic-agentic-workflow")
        self.assertEqual(marketplace["plugins"][0]["version"], version)

    def test_pyproject_metadata_and_version_sync(self) -> None:
        version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
        data = _parse_pyproject(REPO_ROOT / "pyproject.toml")
        project = data["project"]
        self.assertEqual(project["name"], "deterministic-agentic-workflow")
        self.assertEqual(project["version"], version)
        self.assertEqual(project["requires-python"], ">=3.10")
        self.assertEqual(project["dependencies"], [])
        scripts = project.get("scripts") or data.get("scripts")
        self.assertEqual(scripts["daw"], "scripts.daw:main")

    def test_check_package_claude_plugin_validation(self) -> None:
        version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg = _copy_minimal_suite(pathlib.Path(tmpdir))

            # 1. Without .claude-plugin -> passes cleanly
            res_no_plugin = check_package.validate_package(pkg)
            self.assertTrue(res_no_plugin["valid"], res_no_plugin["findings"])

            # 2. Valid .claude-plugin/plugin.json -> passes
            plugin_dir = pkg / ".claude-plugin"
            plugin_dir.mkdir()
            plugin_file = plugin_dir / "plugin.json"
            plugin_file.write_text(
                json.dumps(
                    {
                        "name": "deterministic-agentic-workflow",
                        "version": version,
                        "skills": ["./", "./skills"],
                    }
                ),
                encoding="utf-8",
            )
            res_valid = check_package.validate_package(pkg)
            self.assertTrue(res_valid["valid"], res_valid["findings"])

            # 3. Malformed JSON -> invalid_plugin_json
            plugin_file.write_text("{malformed", encoding="utf-8")
            res_bad_json = check_package.validate_package(pkg)
            self.assertFalse(res_bad_json["valid"])
            self.assertIn("invalid_plugin_json", {f["code"] for f in res_bad_json["findings"]})

            # 4. Duplicate JSON key -> invalid_plugin_json
            plugin_file.write_text(
                f'{{"name": "deterministic-agentic-workflow", "name": "deterministic-agentic-workflow", "version": "{version}"}}',
                encoding="utf-8",
            )
            res_dup = check_package.validate_package(pkg)
            self.assertFalse(res_dup["valid"])
            self.assertIn("invalid_plugin_json", {f["code"] for f in res_dup["findings"]})

            # 5. Version mismatch -> plugin_version_mismatch
            plugin_file.write_text(
                json.dumps({"name": "deterministic-agentic-workflow", "version": "0.0.1"}),
                encoding="utf-8",
            )
            res_ver = check_package.validate_package(pkg)
            self.assertFalse(res_ver["valid"])
            self.assertIn("plugin_version_mismatch", {f["code"] for f in res_ver["findings"]})

            # 6. Name mismatch -> plugin_name_mismatch
            plugin_file.write_text(
                json.dumps({"name": "wrong-plugin", "version": version}),
                encoding="utf-8",
            )
            res_name = check_package.validate_package(pkg)
            self.assertFalse(res_name["valid"])
            self.assertIn("plugin_name_mismatch", {f["code"] for f in res_name["findings"]})

            # 7. Path traversal in skills -> path_escapes_package
            plugin_file.write_text(
                json.dumps(
                    {
                        "name": "deterministic-agentic-workflow",
                        "version": version,
                        "skills": ["../outside"],
                    }
                ),
                encoding="utf-8",
            )
            res_escape = check_package.validate_package(pkg)
            self.assertFalse(res_escape["valid"])
            self.assertIn("path_escapes_package", {f["code"] for f in res_escape["findings"]})

            # 8. Symlink escape on plugin.json -> symlink_escapes_package
            outside = pathlib.Path(tmpdir) / "outside.json"
            outside.write_text(
                json.dumps({"name": "deterministic-agentic-workflow", "version": version}),
                encoding="utf-8",
            )
            plugin_file.unlink()
            try:
                os.symlink(outside, plugin_file)
            except (OSError, NotImplementedError):
                return
            res_sym = check_package.validate_package(pkg)
            self.assertFalse(res_sym["valid"])
            self.assertIn("symlink_escapes_package", {f["code"] for f in res_sym["findings"]})

    def test_cursor_and_codex_plugin_manifests_validated_and_daw_flow_root_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            pkg = _copy_minimal_suite(tmp_path)
            version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
            for plugin_dir in (".cursor-plugin", ".codex-plugin"):
                shutil.copytree(REPO_ROOT / plugin_dir, pkg / plugin_dir)

            ok = check_package.validate_package(pkg)
            self.assertTrue(ok["valid"], ok)

            cursor_manifest = pkg / ".cursor-plugin" / "plugin.json"
            cursor_data = json.loads(cursor_manifest.read_text(encoding="utf-8"))
            cursor_manifest.write_text(json.dumps({**cursor_data, "version": "9.9.9"}), encoding="utf-8")
            bad_cursor = check_package.validate_package(pkg)
            self.assertFalse(bad_cursor["valid"])
            self.assertIn(
                ("plugin_version_mismatch", ".cursor-plugin/plugin.json"),
                {(f["code"], f["path"]) for f in bad_cursor["findings"]},
            )
            cursor_manifest.write_text(json.dumps({**cursor_data, "version": version}), encoding="utf-8")

            codex_manifest = pkg / ".codex-plugin" / "plugin.json"
            codex_data = json.loads(codex_manifest.read_text(encoding="utf-8"))
            codex_manifest.write_text(json.dumps({**codex_data, "name": "wrong-name"}), encoding="utf-8")
            bad_codex = check_package.validate_package(pkg)
            self.assertFalse(bad_codex["valid"])
            self.assertIn(
                ("plugin_name_mismatch", ".codex-plugin/plugin.json"),
                {(f["code"], f["path"]) for f in bad_codex["findings"]},
            )
            codex_manifest.write_text(json.dumps({**codex_data, "name": "deterministic-agentic-workflow"}), encoding="utf-8")

            daw_flow_pkg = tmp_path / "daw-flow"
            pkg.rename(daw_flow_pkg)
            ok_renamed = check_package.validate_package(daw_flow_pkg)
            self.assertTrue(ok_renamed["valid"], ok_renamed)

    def test_setup_collect_data_files_and_shared_prefix_resolution(self) -> None:
        grouped = dict(setup.collect_data_files(REPO_ROOT))
        root_files = set(grouped.get("share/deterministic-agentic-workflow", []))
        self.assertTrue({"SKILL.md", "VERSION", "LICENSE"}.issubset(root_files))
        self.assertNotIn("README.md", root_files)
        self.assertIn("scripts/install.py", grouped.get("share/deterministic-agentic-workflow/scripts", []))
        self.assertIn("scripts/daw.py", grouped.get("share/deterministic-agentic-workflow/scripts", []))
        self.assertIn(
            ".cursor-plugin/plugin.json",
            grouped.get("share/deterministic-agentic-workflow/.cursor-plugin", []),
        )
        self.assertIn(
            ".codex-plugin/plugin.json",
            grouped.get("share/deterministic-agentic-workflow/.codex-plugin", []),
        )
        self.assertFalse(any(target.startswith("share/deterministic-agentic-workflow/tests") for target in grouped))

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            fake_site = tmp_path / "site-packages"
            (fake_site / "scripts").mkdir(parents=True, exist_ok=True)
            (fake_site / "scripts" / "daw.py").write_text("", encoding="utf-8")
            (fake_site / "scripts" / "install.py").write_text("", encoding="utf-8")

            fake_prefix = tmp_path / "prefix"
            shared_suite = fake_prefix / "share" / "deterministic-agentic-workflow"
            shared_suite.mkdir(parents=True, exist_ok=True)
            (shared_suite / "SKILL.md").write_text("---\nname: deterministic-agentic-workflow\n---\n", encoding="utf-8")
            (shared_suite / "VERSION").write_text("0.5.0\n", encoding="utf-8")

            with (
                mock.patch.object(sys, "prefix", str(fake_prefix)),
                mock.patch.object(daw, "__file__", str(fake_site / "scripts" / "daw.py")),
                mock.patch.object(installer, "__file__", str(fake_site / "scripts" / "install.py")),
            ):
                self.assertEqual(daw._suite_root(), shared_suite.resolve())
                self.assertEqual(installer._resolve_source_root(), shared_suite.resolve())


if __name__ == "__main__":
    unittest.main()
