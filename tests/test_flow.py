"""Tests for `validate.py flow` (scripts/check_flow.py)."""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
VALIDATE = REPO_ROOT / "scripts" / "validate.py"


def _run_flow(root: pathlib.Path) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(VALIDATE), "flow", "--project-root", str(root), "--format", "json"],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, json.loads(proc.stdout)


def _codes(envelope: dict) -> list[str]:
    return [f["code"] for f in envelope["findings"]]


class FlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = pathlib.Path(self._tmp.name)
        for sub in ("references", "skills"):
            shutil.copytree(REPO_ROOT / sub, self.root / sub)
        shutil.copy2(REPO_ROOT / "SKILL.md", self.root / "SKILL.md")

    def _mapping(self) -> dict:
        text = (self.root / "references" / "best-practice-flow.md").read_text(encoding="utf-8")
        start = text.find("```json") + len("```json")
        end = text.find("```", start)
        return json.loads(text[start:end])

    def _rewrite_mapping(self, mutate) -> None:
        doc = self.root / "references" / "best-practice-flow.md"
        text = doc.read_text(encoding="utf-8")
        start = text.find("```json") + len("```json")
        end = text.find("```", start)
        data = json.loads(text[start:end])
        mutate(data)
        doc.write_text(text[:start] + "\n" + json.dumps(data, indent=2) + "\n" + text[end:], encoding="utf-8")

    def _rewrite_manifest(self, mutate) -> None:
        path = self.root / "references" / "suite-manifest.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        mutate(data)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    def test_happy_path_real_repo(self) -> None:
        code, env = _run_flow(REPO_ROOT)
        self.assertEqual(code, 0)
        self.assertTrue(env["valid"])
        self.assertEqual(env["check"], "flow")
        self.assertEqual(env["schema_version"], 1)
        self.assertEqual(env["steps"], 8)
        self.assertEqual(env["findings"], [])

    def test_happy_path_temp_copy(self) -> None:
        code, env = _run_flow(self.root)
        self.assertEqual(code, 0)
        self.assertTrue(env["valid"])
        self.assertEqual(env["steps"], 8)

    def test_step_count(self) -> None:
        self._rewrite_mapping(lambda d: d.update(steps=d["steps"][:-1]))
        code, env = _run_flow(self.root)
        self.assertEqual(code, 1)
        self.assertIn("flow_step_count", _codes(env))

    def test_source_invalid(self) -> None:
        self._rewrite_mapping(lambda d: d["steps"][0].update(source="unknown"))
        code, env = _run_flow(self.root)
        self.assertEqual(code, 1)
        self.assertIn("flow_source_invalid", _codes(env))

    def test_anchor_missing_file(self) -> None:
        self._rewrite_mapping(lambda d: d["steps"][0].update(anchor="references/does-not-exist.md#x"))
        code, env = _run_flow(self.root)
        self.assertEqual(code, 1)
        self.assertIn("flow_anchor_unresolved", _codes(env))

    def test_anchor_bogus_fragment(self) -> None:
        self._rewrite_mapping(
            lambda d: d["steps"][0].update(anchor="references/constitution.md#no-such-heading")
        )
        code, env = _run_flow(self.root)
        self.assertEqual(code, 1)
        self.assertIn("flow_anchor_unresolved", _codes(env))

    def test_manifest_gate_missing(self) -> None:
        self._rewrite_manifest(lambda d: d.pop("flow_gate"))
        code, env = _run_flow(self.root)
        self.assertEqual(code, 1)
        self.assertIn("flow_manifest_gate_missing", _codes(env))

    def test_manifest_gate_step_unknown(self) -> None:
        self._rewrite_manifest(lambda d: d["flow_gate"].update(required_steps=["BPF-9"]))
        code, env = _run_flow(self.root)
        self.assertEqual(code, 1)
        self.assertIn("flow_gate_step_unknown", _codes(env))

    def test_cross_link_missing(self) -> None:
        skill = self.root / "SKILL.md"
        skill.write_text(skill.read_text(encoding="utf-8").replace("best-practice-flow.md", "removed-link"), encoding="utf-8")
        code, env = _run_flow(self.root)
        self.assertEqual(code, 1)
        self.assertIn("flow_missing_link", _codes(env))


if __name__ == "__main__":
    unittest.main()
