#!/usr/bin/env python3
"""Tests for `scripts/feedback.py` and `daw feedback` subcommand."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import urllib.parse

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import feedback, package_layout  # noqa: E402


class FeedbackTests(unittest.TestCase):
    def _run_daw_feedback(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "daw.py"), "feedback", *args],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_operational_scripts_and_issue_template_present(self) -> None:
        self.assertIn("scripts/feedback.py", package_layout.OPERATIONAL_SCRIPTS)
        tpl = REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "skill-feedback.yml"
        self.assertTrue(tpl.is_file())
        tpl_text = tpl.read_text(encoding="utf-8")
        self.assertIn('labels: ["skill-feedback"]', tpl_text)
        for cat in feedback.VALID_CATEGORIES:
            self.assertIn(cat, tpl_text)

    def test_valid_json_and_text_output(self) -> None:
        res_json = self._run_daw_feedback(
            "--route",
            "feature",
            "--module",
            "daw-plan",
            "--category",
            "friction",
            "--client",
            "claude-code",
            "--finding",
            "manifest_drift",
            "--summary",
            "Plan needed re-derive after edit",
            "--json",
        )
        self.assertEqual(res_json.returncode, 0, res_json.stderr)
        payload = json.loads(res_json.stdout)
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["check"], "feedback")
        self.assertFalse(payload["submitted"])
        self.assertIsNone(payload["submitted_url"])

        report = payload["report"]
        expected_version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual(report["daw_version"], expected_version)
        self.assertEqual(report["route"], "feature")
        self.assertEqual(report["module"], "daw-plan")
        self.assertEqual(report["category"], "friction")
        self.assertEqual(report["client"], "claude-code")
        self.assertEqual(report["finding_codes"], ["manifest_drift"])
        self.assertEqual(report["finding_counts"], {"manifest_drift": 1})
        self.assertEqual(report["recurring_findings"], [])

        url = payload["issue_url"]
        self.assertTrue(url.startswith("https://github.com/gio0z/daw-flow/issues/new?"))
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        self.assertEqual(params["template"], ["skill-feedback.yml"])
        self.assertEqual(params["labels"], ["skill-feedback"])
        self.assertIn("manifest_drift", params["title"][0])
        # The target is an issue form: query keys are the form's field ids.
        self.assertNotIn("body", params)
        self.assertEqual(params["daw_version"], [expected_version])
        self.assertIn("Python", params["environment"][0])
        self.assertIn("feature", params["route_module"][0])
        self.assertEqual(params["category"], ["friction"])
        self.assertIn("manifest_drift", params["finding_codes"][0])
        self.assertEqual(params["summary"], ["Plan needed re-derive after edit"])

        res_text = self._run_daw_feedback(
            "--route",
            "feature",
            "--module",
            "daw-plan",
            "--category",
            "friction",
            "--finding",
            "manifest_drift",
            "--summary",
            "Plan needed re-derive after edit",
        )
        self.assertEqual(res_text.returncode, 0, res_text.stderr)
        self.assertIn("[VALID] Check: feedback", res_text.stdout)
        self.assertIn("Issue URL: https://github.com/gio0z/daw-flow/issues/new?", res_text.stdout)
        self.assertIn("GH CLI: gh issue create --repo gio0z/daw-flow", res_text.stdout)

    def test_evidence_scanning_counts_recurring_and_strips_sensitive_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = pathlib.Path(tmpdir)
            ev = root / "docs" / "daw" / "evidence"
            (ev / "TASK-SECRET-99").mkdir(parents=True)
            (ev / "TASK-SECRET-100").mkdir(parents=True)
            (ev / "runner").mkdir(parents=True)

            secret_token = "SECRET_PRIVATE_KEY_DO_NOT_LEAK"
            secret_path = "src/internal/payroll_secret_engine.py"
            secret_title = "Confidential Payroll Secret Task"

            (ev / "TASK-SECRET-99" / "review-dispatch.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "task_id": "TASK-SECRET-99",
                        "title": secret_title,
                        "declared_target_files": [secret_path],
                        "actual_changed_paths": [secret_path],
                        "findings": [
                            "batch_task_verification_failed",
                            {"code": "manifest_drift", "message": secret_token},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (ev / "TASK-SECRET-100" / "review-dispatch.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "task_id": "TASK-SECRET-100",
                        "title": secret_title,
                        "findings": ["batch_task_verification_failed"],
                    }
                ),
                encoding="utf-8",
            )
            (ev / "runner" / "isolation.json").write_text(
                json.dumps(
                    {
                        "tasks": {
                            "TASK-SECRET-99": {
                                "branch": "daw/TASK-SECRET-99-secret",
                                "worktree_path": f"/tmp/{secret_token}",
                                "batch_failure": "batch_merge_conflict",
                                "status": "escaped",
                            },
                            "TASK-SECRET-100": {
                                "batch_failure": {"batch_id": "batch-1234", "member_exit_code": 1},
                                "status": "failed",
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )

            res = self._run_daw_feedback(
                "--project-root",
                str(root),
                "--route",
                "feature",
                "--category",
                "bug",
                "--json",
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            payload = json.loads(res.stdout)
            report = payload["report"]
            self.assertEqual(
                report["finding_counts"],
                {
                    "batch_failure": 1,
                    "batch_merge_conflict": 1,
                    "batch_task_verification_failed": 2,
                    "escaped": 1,
                    "failed": 1,
                    "manifest_drift": 1,
                },
            )
            self.assertEqual(report["recurring_findings"], ["batch_task_verification_failed"])

            serialized = json.dumps(payload)
            for forbidden in (
                secret_token,
                secret_path,
                secret_title,
                "TASK-SECRET-99",
                "TASK-SECRET-100",
                "batch-1234",
            ):
                self.assertNotIn(forbidden, serialized)

    def test_validation_errors_and_bad_project_root(self) -> None:
        bad_root = self._run_daw_feedback("--project-root", "/definitely/missing/daw-root-xyz")
        self.assertEqual(bad_root.returncode, 2)

        for flag, bad_val, expected_code in (
            ("--finding", "../secret", "invalid_finding_code"),
            ("--finding", "spaces not allowed", "invalid_finding_code"),
            ("--route", "nonexistent-route", "invalid_route"),
            ("--module", "daw-nonexistent", "invalid_module"),
            ("--category", "invalid-cat", "invalid_category"),
        ):
            res = self._run_daw_feedback(flag, bad_val, "--json")
            self.assertEqual(res.returncode, 1, f"{flag}={bad_val}: {res.stdout}")
            data = json.loads(res.stdout)
            self.assertFalse(data["valid"])
            self.assertIn(expected_code, {f["code"] for f in data["findings"]})

    def test_submit_flag_success_and_missing_gh(self) -> None:
        with mock.patch("scripts.feedback.shutil.which", return_value=None):
            with mock.patch("builtins.print") as mocked_print:
                rc = feedback.main(["--route", "patch", "--category", "bug", "--submit", "--json"])
            self.assertEqual(rc, 1)
            emitted = json.loads(mocked_print.call_args[0][0])
            self.assertFalse(emitted["valid"])
            self.assertFalse(emitted["submitted"])
            self.assertIn("feedback_submit_failed", {f["code"] for f in emitted["findings"]})

        fake_proc = subprocess.CompletedProcess(
            args=["gh"],
            returncode=0,
            stdout="https://github.com/gio0z/daw-flow/issues/42\n",
            stderr="",
        )
        with (
            mock.patch("scripts.feedback.shutil.which", return_value="/usr/bin/gh"),
            mock.patch("scripts.feedback.subprocess.run", return_value=fake_proc) as mocked_run,
        ):
            with mock.patch("builtins.print") as mocked_print:
                rc = feedback.main(["--route", "patch", "--category", "bug", "--submit", "--json"])
            self.assertEqual(rc, 0)
            mocked_run.assert_called_once()
            cmd_passed = mocked_run.call_args[0][0]
            self.assertEqual(cmd_passed[:5], ["gh", "issue", "create", "--repo", "gio0z/daw-flow"])
            emitted = json.loads(mocked_print.call_args[0][0])
            self.assertTrue(emitted["valid"])
            self.assertTrue(emitted["submitted"])
            self.assertEqual(emitted["submitted_url"], "https://github.com/gio0z/daw-flow/issues/42")

    def test_operator_free_text_is_redacted(self) -> None:
        secret_path = "src/internal/payroll_secret_engine.py"
        secret_sha = "abc123def4567890abcdef1234567890abcdef12"
        secret_task = "TASK-42"
        secret_token = "Zx91qwertyuiopASDFGHJKL0987654321"
        summary = (
            f"failed at /home/regio/projects/foo/{secret_path} "
            f"task {secret_task} with commit {secret_sha} and token={secret_token}"
        )
        note = f"see C:\\Users\\bob\\notes.txt and https://example.com/leak and T-99"

        res = self._run_daw_feedback("--summary", summary, "--note", note, "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        payload = json.loads(res.stdout)
        report = payload["report"]
        serialized = json.dumps(payload)

        for forbidden in (
            "/home/regio/projects/foo",
            secret_path,
            secret_task,
            secret_sha,
            secret_token,
            "C:\\Users\\bob",
            "example.com/leak",
            "T-99",
        ):
            self.assertNotIn(forbidden, serialized, f"leaked: {forbidden}")

        self.assertIn("[PATH]", report["summary"])
        self.assertIn("[TASK-ID]", report["summary"])
        self.assertIn("[SHA]", report["summary"])
        self.assertIn("[REDACTED]", report["summary"])
        self.assertIn("[PATH]", report["note"])
        self.assertIn("[URL]", report["note"])
        self.assertIn("[TASK-ID]", report["note"])

        # The redacted text is what reaches the body and the URL.
        self.assertNotIn(secret_sha, payload["issue_body"])
        self.assertNotIn(secret_sha, payload["issue_url"])
        self.assertNotIn(secret_task, payload["issue_url"])
        self.assertIn("%5BPATH%5D", payload["issue_url"])

    def test_issue_url_stays_under_length_cap(self) -> None:
        for note in ("x " * 2000, "\u65e5\u672c\u8a9e " * 1000, "A1b2C3d4E5f6G7h8" * 400):
            with self.subTest(note_len=len(note)):
                res = self._run_daw_feedback("--note", note, "--json")
                self.assertEqual(res.returncode, 0, res.stderr)
                payload = json.loads(res.stdout)
                self.assertLessEqual(
                    len(payload["issue_url"]),
                    feedback.MAX_ISSUE_URL_LENGTH,
                )

    def test_missing_upstream_label_is_actionable(self) -> None:
        fake_proc = subprocess.CompletedProcess(
            args=["gh"],
            returncode=1,
            stdout="",
            stderr="could not add label: 'skill-feedback' not found\n",
        )
        with (
            mock.patch("scripts.feedback.shutil.which", return_value="/usr/bin/gh"),
            mock.patch("scripts.feedback.subprocess.run", return_value=fake_proc),
        ):
            with mock.patch("builtins.print") as mocked_print:
                rc = feedback.main(["--route", "patch", "--category", "bug", "--submit", "--json"])
        self.assertEqual(rc, 1)
        emitted = json.loads(mocked_print.call_args[0][0])
        self.assertFalse(emitted["valid"])
        self.assertFalse(emitted["submitted"])
        codes = {f["code"] for f in emitted["findings"]}
        self.assertIn("feedback_label_missing", codes)
        self.assertNotIn("feedback_submit_failed", codes)
        message = next(f["message"] for f in emitted["findings"] if f["code"] == "feedback_label_missing")
        self.assertIn("skill-feedback", message)
        self.assertIn("gh label create", message)

    def test_evidence_symlink_escape_skipped_with_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = pathlib.Path(tmpdir)
            outside = tmp_path / "outside"
            outside.mkdir()
            (outside / "review-dispatch.json").write_text(
                json.dumps({"findings": ["should_not_count"]}),
                encoding="utf-8",
            )
            root = tmp_path / "project"
            ev = root / "docs" / "daw" / "evidence"
            ev.mkdir(parents=True)
            link = ev / "TASK-1"
            try:
                os.symlink(outside, link)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks unavailable on this platform")

            counts, warnings = feedback.scan_evidence_findings(root)
            self.assertEqual(counts, {})
            self.assertTrue(any(w["code"] == "evidence_unsafe_path" for w in warnings))


if __name__ == "__main__":
    unittest.main()
