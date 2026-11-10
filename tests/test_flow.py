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


    def test_step_id_unhashable_no_traceback(self) -> None:
        self._rewrite_mapping(lambda d: d["steps"][0].update(id={"a": 1}))
        proc = subprocess.run(
            [sys.executable, str(VALIDATE), "flow", "--project-root", str(self.root), "--format", "json"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertNotIn("Traceback", proc.stderr)
        env = json.loads(proc.stdout)
        self.assertFalse(env["valid"])
        self.assertIn("flow_step_id_invalid", _codes(env))

    def test_source_unhashable_no_crash(self) -> None:
        self._rewrite_mapping(lambda d: d["steps"][0].update(source=["x"]))
        code, env = _run_flow(self.root)
        self.assertEqual(code, 1)
        self.assertIn("flow_source_invalid", _codes(env))

    def test_manifest_entry_unhashable_no_crash(self) -> None:
        self._rewrite_manifest(
            lambda d: d["flow_gate"].update(required_steps=[{"a": 1}], affected_intents=[{"b": 2}])
        )
        code, env = _run_flow(self.root)
        self.assertEqual(code, 1)
        self.assertIn("flow_gate_step_unknown", _codes(env))
        self.assertIn("flow_gate_intent_unknown", _codes(env))

    def test_flow_schema_version_requires_int(self) -> None:
        for value in (True, 1.0, "1"):
            with self.subTest(value=value):
                self._rewrite_mapping(lambda d, v=value: d.update(flow_schema_version=v))
                code, env = _run_flow(self.root)
                self.assertEqual(code, 1)
                self.assertIn("flow_schema_version_invalid", _codes(env))

    def test_artifact_step_unknown(self) -> None:
        self._rewrite_mapping(
            lambda d: d["artifact_steps"].append({"step": "BPF-9", "patterns": ["x"], "require_text": None})
        )
        code, env = _run_flow(self.root)
        self.assertEqual(code, 1)
        self.assertIn("flow_artifact_step_unknown", _codes(env))

    def test_artifact_step_malformed(self) -> None:
        for entry in (
            "not-an-object",
            {"step": "BPF-2", "patterns": [], "require_text": None},
            {"step": "BPF-2", "patterns": ["ok", 3], "require_text": None},
            {"step": "BPF-2", "patterns": ["ok"], "require_text": "  "},
        ):
            with self.subTest(entry=entry):
                self._rewrite_mapping(lambda d, e=entry: d.update(artifact_steps=[e]))
                code, env = _run_flow(self.root)
                self.assertEqual(code, 1)
                self.assertIn("flow_artifact_step_invalid", _codes(env))

    def test_required_step_without_artifact_check(self) -> None:
        self._rewrite_mapping(
            lambda d: d.update(artifact_steps=[e for e in d["artifact_steps"] if e["step"] != "BPF-2"])
        )
        code, env = _run_flow(self.root)
        self.assertEqual(code, 1)
        self.assertIn("flow_artifact_step_missing", _codes(env))

    def test_flow_gate_document_redirect(self) -> None:
        self._rewrite_manifest(lambda d: d["flow_gate"].update(document="references/other-flow.md"))
        code, env = _run_flow(self.root)
        self.assertEqual(code, 1)
        self.assertIn("flow_gate_document_mismatch", _codes(env))

    def test_cross_links_required(self) -> None:
        for links in ([], ["SKILL.md"], ["references/routing.md"], ["SKILL.md", "unrelated.md"]):
            with self.subTest(cross_links=links):
                self._rewrite_mapping(lambda d, l=links: d.update(cross_links=l))
                code, env = _run_flow(self.root)
                self.assertEqual(code, 1)
                self.assertIn("flow_missing_link", _codes(env))


if __name__ == "__main__":
    unittest.main()
