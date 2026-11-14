#!/usr/bin/env python3
"""Tests for the derive pattern: Markdown task files are the source, the plan's
JSON manifest is the derived projection."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATE = PROJECT_ROOT / "scripts" / "validate.py"
DERIVE = PROJECT_ROOT / "scripts" / "derive_tasks.py"
RUNNER = PROJECT_ROOT / "scripts" / "run.py"

SOURCES_MARKER = "<!-- daw-task-sources: docs/daw/plans/wf.tasks -->"


def _task_file(
    task_id: str,
    *,
    title: str | None = None,
    autonomy: str = "afk",
    depends_on: list[str] | None = None,
    body: str = "## What to build\n\nThe behavior.\n",
) -> str:
    deps = "\n".join(f"  - {d}" for d in (depends_on or []))
    deps_block = f"depends_on:\n{deps}\n" if depends_on else "depends_on: []\n"
    return (
        "---\n"
        f"task_id: {task_id}\n"
        f"title: {title or f'Task {task_id}'}\n"
        f"autonomy: {autonomy}\n"
        f"{deps_block}"
        "parallel_safe: false\n"
        "target_files:\n  - src/app.py\n"
        "acceptance_criteria:\n  - the behavior works\n"
        'verification_command: python3 -c "print(\'ok\')"\n'
        "expected_outcome: 0 exit code\n"
        "---\n\n"
        f"{body}"
    )


class DerivePatternTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = pathlib.Path(self.temp_dir.name).resolve()
        (self.root / "src").mkdir()
        (self.root / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        self.tasks_dir = self.root / "docs" / "daw" / "plans" / "wf.tasks"
        self.tasks_dir.mkdir(parents=True)
        self.plan = self.root / "docs" / "daw" / "plans" / "wf.md"

    def write_plan(self, body: str) -> None:
        self.plan.write_text(body, encoding="utf-8")

    def write_sources(self, body: str) -> None:
        self.write_plan(f"# Plan\n\n{SOURCES_MARKER}\n")
        (self.tasks_dir / "TASK-01.md").write_text(body, encoding="utf-8")

    def derive(self, *args: str) -> tuple[int, str]:
        proc = subprocess.run(
            [sys.executable, str(DERIVE), "--plan", str(self.plan), "--project-root", str(self.root), *args],
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode, proc.stdout

    def validate_tasks(self) -> tuple[int, dict]:
        proc = subprocess.run(
            [sys.executable, str(VALIDATE), "tasks", str(self.plan), "--project-root", str(self.root), "--format", "json"],
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode, json.loads(proc.stdout)


class TaskFileParsingTests(DerivePatternTestBase):
    def test_task_file_without_frontmatter_is_rejected(self) -> None:
        self.write_sources("# Just prose, no frontmatter\n")
        code, output = self.derive()
        self.assertEqual(code, 1)
        self.assertIn("task_file_frontmatter_missing", output)

    def test_unknown_frontmatter_key_is_rejected(self) -> None:
        self.write_sources(_task_file("TASK-01").replace("autonomy: afk", "autonomy: afk\ncolour: blue"))
        code, output = self.derive()
        self.assertEqual(code, 1)
        self.assertIn("task_unknown_field", output)

    def test_duplicate_frontmatter_key_is_rejected(self) -> None:
        self.write_sources(_task_file("TASK-01").replace("title: Task TASK-01", "title: One\ntitle: Two"))
        code, output = self.derive()
        self.assertEqual(code, 1)
        self.assertIn("task_file_field_duplicate", output)

    def test_missing_required_field_is_rejected(self) -> None:
        body = _task_file("TASK-01")
        body = "\n".join(line for line in body.splitlines() if not line.startswith("expected_outcome"))
        self.write_sources(body)
        code, output = self.derive()
        self.assertEqual(code, 1)
        self.assertIn("task_missing_field", output)

    def test_inline_json_list_is_accepted(self) -> None:
        body = _task_file("TASK-01").replace(
            "target_files:\n  - src/app.py", 'target_files: ["src/app.py"]'
        )
        self.write_sources(body)
        code, _ = self.derive()
        self.assertEqual(code, 0)

    def test_quoted_scalar_is_unquoted(self) -> None:
        body = _task_file("TASK-01").replace(
            "expected_outcome: 0 exit code", 'expected_outcome: "0 exit code, 3 tests pass"'
        )
        self.write_sources(body)
        code, _ = self.derive()
        self.assertEqual(code, 0)

    def test_prose_body_is_not_a_manifest_field(self) -> None:
        self.write_sources(_task_file("TASK-01", body="## What to build\n\nSome prose.\n"))
        code, output = self.derive()
        self.assertEqual(code, 0, output)
        self.assertNotIn("body", output)


class DeriveTests(DerivePatternTestBase):
    def test_dry_run_writes_nothing(self) -> None:
        self.write_sources(_task_file("TASK-01"))
        before = self.plan.read_text(encoding="utf-8")
        code, output = self.derive()
        self.assertEqual(code, 0)
        self.assertEqual(self.plan.read_text(encoding="utf-8"), before)
        self.assertIn('"task_id": "TASK-01"', output)

    def test_write_produces_a_manifest_the_validator_accepts(self) -> None:
        self.write_sources(_task_file("TASK-01"))
        code, _ = self.derive("--write")
        self.assertEqual(code, 0)
        code, payload = self.validate_tasks()
        self.assertEqual(code, 0, payload)
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["task_count"], 1)

    def test_write_is_idempotent(self) -> None:
        self.write_sources(_task_file("TASK-01"))
        self.derive("--write")
        once = self.plan.read_text(encoding="utf-8")
        code, _ = self.derive("--write")
        self.assertEqual(code, 0)
        self.assertEqual(self.plan.read_text(encoding="utf-8"), once)

    def test_write_replaces_a_stale_block(self) -> None:
        self.write_sources(_task_file("TASK-01"))
        self.derive("--write")
        stale = self.plan.read_text(encoding="utf-8").replace('"expected_outcome": "0 exit code"', '"expected_outcome": "stale"')
        self.plan.write_text(stale, encoding="utf-8")
        self.derive("--write")
        self.assertNotIn("stale", self.plan.read_text(encoding="utf-8"))

    def test_plan_without_sources_marker_is_refused(self) -> None:
        self.write_plan("# Plan\n\nNo marker here.\n")
        code, output = self.derive("--write")
        self.assertEqual(code, 1)
        self.assertIn("task_sources_undeclared", output)

    def test_missing_source_directory_is_refused(self) -> None:
        self.write_plan("# Plan\n\n<!-- daw-task-sources: docs/daw/plans/nope -->\n")
        code, output = self.derive("--write")
        self.assertEqual(code, 1)
        self.assertIn("task_source_missing", output)

    def test_source_path_escaping_the_root_is_refused(self) -> None:
        self.write_plan("# Plan\n\n<!-- daw-task-sources: ../outside -->\n")
        code, output = self.derive("--write")
        self.assertEqual(code, 1)
        self.assertIn("task_sources_unsafe", output)


class DriftDetectionTests(DerivePatternTestBase):
    def test_edited_task_file_is_reported_as_drift(self) -> None:
        self.write_sources(_task_file("TASK-01"))
        self.derive("--write")
        edited = (self.tasks_dir / "TASK-01.md").read_text(encoding="utf-8").replace(
            "expected_outcome: 0 exit code", "expected_outcome: 0 exit code, 3 tests pass"
        )
        (self.tasks_dir / "TASK-01.md").write_text(edited, encoding="utf-8")
        code, payload = self.validate_tasks()
        self.assertEqual(code, 1)
        codes = [f["code"] for f in payload["findings"]]
        self.assertIn("manifest_drift", codes)
        message = " ".join(f["message"] for f in payload["findings"])
        self.assertIn("expected_outcome", message)

    def test_added_task_file_is_reported_as_drift(self) -> None:
        self.write_sources(_task_file("TASK-01"))
        self.derive("--write")
        (self.tasks_dir / "TASK-02.md").write_text(_task_file("TASK-02"), encoding="utf-8")
        code, payload = self.validate_tasks()
        self.assertEqual(code, 1)
        self.assertIn("manifest_drift", [f["code"] for f in payload["findings"]])

    def test_removed_task_file_is_reported_as_drift(self) -> None:
        self.write_sources(_task_file("TASK-01"))
        (self.tasks_dir / "TASK-02.md").write_text(_task_file("TASK-02"), encoding="utf-8")
        self.derive("--write")
        (self.tasks_dir / "TASK-02.md").unlink()
        code, payload = self.validate_tasks()
        self.assertEqual(code, 1)
        self.assertIn("manifest_drift", [f["code"] for f in payload["findings"]])

    def test_re_deriving_clears_the_drift(self) -> None:
        self.write_sources(_task_file("TASK-01"))
        self.derive("--write")
        (self.tasks_dir / "TASK-02.md").write_text(_task_file("TASK-02"), encoding="utf-8")
        self.assertEqual(self.validate_tasks()[0], 1)
        code, _ = self.derive("--write")
        self.assertEqual(code, 0)
        code, payload = self.validate_tasks()
        self.assertEqual(code, 0, payload)


class RunnerReadsTaskFilesTests(DerivePatternTestBase):
    def test_runner_uses_the_task_files_as_the_source(self) -> None:
        self.write_sources(_task_file("TASK-01"))
        self.derive("--write")
        proc = subprocess.run(
            [sys.executable, str(RUNNER), "next", "--plan", str(self.plan), "--project-root", str(self.root), "--format", "json"],
            capture_output=True,
            text=True,
            check=False,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(proc.returncode, 0, payload)
        self.assertEqual(payload["next_task_id"], "TASK-01")

    def test_runner_refuses_to_run_on_drift(self) -> None:
        self.write_sources(_task_file("TASK-01"))
        self.derive("--write")
        edited = (self.tasks_dir / "TASK-01.md").read_text(encoding="utf-8").replace(
            "expected_outcome: 0 exit code", "expected_outcome: changed"
        )
        (self.tasks_dir / "TASK-01.md").write_text(edited, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(RUNNER), "next", "--plan", str(self.plan), "--project-root", str(self.root), "--format", "json"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 2)
        payload = json.loads(proc.stdout)
        self.assertIn("manifest_drift", [f["code"] for f in payload["findings"]])

    def test_context_pack_includes_the_prose_brief(self) -> None:
        self.write_sources(
            _task_file("TASK-01", body="## What to build\n\nRotate the token_version.\n")
        )
        self.derive("--write")
        proc = subprocess.run(
            [sys.executable, str(RUNNER), "context", "--plan", str(self.plan), "--project-root", str(self.root), "--task", "TASK-01"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("## Task brief", proc.stdout)
        self.assertIn("Rotate the token_version.", proc.stdout)


class EmbeddedManifestModeTests(DerivePatternTestBase):
    def test_plan_without_sources_keeps_its_embedded_manifest(self) -> None:
        payload = {
            "schema_version": 1,
            "workflow_id": "wf",
            "tasks": [
                {
                    "task_id": "TASK-01",
                    "title": "Task TASK-01",
                    "autonomy": "afk",
                    "depends_on": [],
                    "parallel_safe": False,
                    "target_files": ["src/app.py"],
                    "acceptance_criteria": ["it works"],
                    "verification_command": "python3 -c \"print('ok')\"",
                    "expected_outcome": "0 exit code",
                }
            ],
        }
        self.write_plan(
            "# Plan\n\n<!-- daw-task-manifest -->\n```json\n"
            + json.dumps(payload, indent=2)
            + "\n```\n"
        )
        code, envelope = self.validate_tasks()
        self.assertEqual(code, 0, envelope)
        self.assertTrue(envelope["valid"])


if __name__ == "__main__":
    unittest.main()
