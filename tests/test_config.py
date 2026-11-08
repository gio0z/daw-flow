#!/usr/bin/env python3
"""Unit tests for `python3 scripts/validate.py config` (C4)."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATOR_SCRIPT = PROJECT_ROOT / "scripts" / "validate.py"
INSTALLED_VERSION = (PROJECT_ROOT / "VERSION").read_text(encoding="utf-8").strip()


def _shift_version(delta: int) -> str:
    major, minor, patch = (int(p) for p in INSTALLED_VERSION.split("."))
    return f"{major}.{minor + delta}.{patch}" if minor + delta >= 0 else f"{major - 1}.99.0"


class ConfigTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.proj_root = pathlib.Path(self.temp_dir.name).resolve()
        (self.proj_root / "docs" / "specs").mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def valid_config(self, **overrides: str) -> dict[str, str]:
        config = {
            "schema": "1",
            "daw_version": INSTALLED_VERSION,
            "spec_dir": "docs/specs",
            "test_command": "python3 -m unittest",
            "lint_command": "none",
            "build_command": "none",
            "workspace": "in-place",
            "high_risk_paths": "none",
            "issue_tracker": "github",
            "default_branch": "main",
            "commit_convention": "conventional",
            "pr_template": "none",
            "ci_checks": "none",
            "release_process": "changelog+tags",
            "branch_pattern": "feature/*",
        }
        config.update(overrides)
        return config

    def write_agent_file(self, config: dict[str, str], extra_lines: list[str] | None = None, duplicate: bool = False) -> pathlib.Path:
        lines = ["<!-- daw-config:start -->", "", "## DAW Configuration", ""]
        for key, value in config.items():
            lines.append(f"- {key}: {value}")
        if extra_lines:
            lines.extend(extra_lines)
        lines.extend(["", "<!-- daw-config:end -->", ""])
        if duplicate:
            lines.extend(lines)
        path = self.proj_root / "AGENTS.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def run_cli(self, path: pathlib.Path) -> subprocess.CompletedProcess[str]:
        cmd = [sys.executable, str(VALIDATOR_SCRIPT), "config", str(path), "--project-root", str(self.proj_root), "--format", "json"]
        return subprocess.run(cmd, cwd=str(self.proj_root), capture_output=True, text=True)

    def codes(self, res: subprocess.CompletedProcess[str]) -> list[str]:
        return [f["code"] for f in json.loads(res.stdout)["findings"]]


class TestConfigValid(ConfigTestBase):
    def test_valid_config(self) -> None:
        path = self.write_agent_file(self.valid_config())
        res = self.run_cli(path)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        data = json.loads(res.stdout)
        self.assertTrue(data["valid"])
        self.assertEqual(data["check"], "config")


class TestConfigFindings(ConfigTestBase):
    def test_block_missing(self) -> None:
        path = self.proj_root / "AGENTS.md"
        path.write_text("# No config\n", encoding="utf-8")
        res = self.run_cli(path)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("config_block_missing", self.codes(res))

    def test_block_duplicate(self) -> None:
        path = self.write_agent_file(self.valid_config(), duplicate=True)
        res = self.run_cli(path)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("config_block_duplicate", self.codes(res))

    def test_missing_key(self) -> None:
        config = self.valid_config()
        del config["schema"]
        path = self.write_agent_file(config)
        res = self.run_cli(path)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("config_key_missing", self.codes(res))

    def test_duplicate_key(self) -> None:
        path = self.write_agent_file(self.valid_config(), extra_lines=["- schema: 1"])
        res = self.run_cli(path)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("config_key_duplicate", self.codes(res))

    def test_invalid_line(self) -> None:
        path = self.write_agent_file(self.valid_config(), extra_lines=["free-form text"])
        res = self.run_cli(path)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("config_line_invalid", self.codes(res))

    def test_bad_workspace(self) -> None:
        path = self.write_agent_file(self.valid_config(workspace="sideways"))
        res = self.run_cli(path)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("config_line_invalid", self.codes(res))

    def test_missing_path(self) -> None:
        path = self.write_agent_file(self.valid_config(spec_dir="docs/missing"))
        res = self.run_cli(path)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("config_path_missing", self.codes(res))

    def test_unresolved_command(self) -> None:
        path = self.write_agent_file(self.valid_config(test_command="definitely-not-a-real-command-xyz"))
        res = self.run_cli(path)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("config_command_unresolved", self.codes(res))


class TestConfigDawVersion(ConfigTestBase):
    def findings(self, res: subprocess.CompletedProcess[str]) -> list[dict[str, str]]:
        return json.loads(res.stdout)["findings"]

    def test_stale_version_warns_but_stays_valid(self) -> None:
        res = self.run_cli(self.write_agent_file(self.valid_config(daw_version=_shift_version(-1))))
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        stale = [f for f in self.findings(res) if f["code"] == "config_daw_version_stale"]
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0]["severity"], "warning")

    def test_ahead_version_is_error(self) -> None:
        res = self.run_cli(self.write_agent_file(self.valid_config(daw_version=_shift_version(1))))
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("config_daw_version_ahead", self.codes(res))

    def test_numeric_not_lexical_comparison(self) -> None:
        major, minor, patch = (int(p) for p in INSTALLED_VERSION.split("."))
        ahead = f"{major}.{minor}.{patch + 10}"
        res = self.run_cli(self.write_agent_file(self.valid_config(daw_version=ahead)))
        self.assertIn("config_daw_version_ahead", self.codes(res))

    def test_malformed_version_rejected(self) -> None:
        res = self.run_cli(self.write_agent_file(self.valid_config(daw_version="v0.3")))
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("config_line_invalid", self.codes(res))

    def test_missing_version_key(self) -> None:
        config = self.valid_config()
        del config["daw_version"]
        res = self.run_cli(self.write_agent_file(config))
        self.assertIn("config_key_missing", self.codes(res))


if __name__ == "__main__":
    unittest.main()
