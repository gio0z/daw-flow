#!/usr/bin/env python3
"""Boundary and path safety regression tests for `scripts/validate.py docs`.

Tests:
1. Malformed JSON outside project root -> boundary rejection (exit 1), not parsed (not exit 2).
2. Traversal record path (../../escaped.json) -> boundary rejection (exit 1).
3. Absolute record inside root -> valid (exit 0) when valid.
4. Target or evidence with colon/ADS or backslash -> boundary rejection (exit 1), no crash.
5. Intake target path below an existing regular file -> rejected (exit 1), no crash.
6. Symlink loop record path -> safe rejection (exit 1 or 2), no unhandled traceback.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

VALID_INTAKE_RECORD = {
    "schema_version": 1,
    "transition": {
        "from": "intake",
        "to": "authoring",
    },
    "objective": "Define system architecture and communication bounds.",
    "scope": "Frontend, backend gateway, and event bus.",
    "documents": [
        {
            "path": "docs/architecture/system-blueprint.md",
            "kind": "blueprint",
            "audience": "System architects and integration engineers",
            "reader_task": "Review component boundaries and RPC contracts.",
            "sources": [
                {
                    "path": "evidence/source.md",
                    "sha256": "e88dfc324d0af82f9efeb9b5c1bb70d59515626f831b9fc30081b8287f75dc99",
                    "start_line": 1,
                    "end_line": 1,
                    "quote": "Valid evidence statement.",
                }
            ],
        }
    ],
}


class TestDocGateBoundary(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.proj_root = pathlib.Path(self.tmp_dir.name).resolve()

        # Create basic structure inside root
        (self.proj_root / "docs" / "architecture").mkdir(parents=True, exist_ok=True)
        (self.proj_root / "evidence").mkdir(parents=True, exist_ok=True)
        (self.proj_root / "evidence" / "source.md").write_text("Valid evidence statement.\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def run_cli(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        cmd = [sys.executable, "scripts/validate.py", "docs"] + args
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(pathlib.Path.cwd()),
        )

    def test_malformed_json_outside_project_root_is_boundary_rejected_not_parsed(self) -> None:
        """An escaped record containing malformed JSON must exit 1 (boundary rejected), NOT exit 2."""
        with tempfile.TemporaryDirectory() as outside_dir:
            outside_record = pathlib.Path(outside_dir) / "malformed.json"
            outside_record.write_text("{ unquoted_key: invalid json ...", encoding="utf-8")

            res = self.run_cli(
                [
                    str(outside_record),
                    "--project-root",
                    str(self.proj_root),
                    "--transition",
                    "intake-authoring",
                    "--documents",
                    "docs/architecture/system-blueprint.md",
                    "--format",
                    "json",
                ]
            )
            self.assertEqual(res.returncode, 1, msg=f"Stderr: {res.stderr}")
            payload = json.loads(res.stdout)
            self.assertFalse(payload["valid"])
            self.assertTrue(
                any(f["code"] in ("record_path_outside_root", "record_path_escapes") for f in payload["findings"])
            )

    def test_traversal_record_path_rejected_exit_1(self) -> None:
        """Relative traversal path for record file must exit 1 without crash or parsing."""
        res = self.run_cli(
            [
                "../../escaped_record.json",
                "--project-root",
                str(self.proj_root),
                "--transition",
                "intake-authoring",
                "--documents",
                "docs/architecture/system-blueprint.md",
                "--format",
                "json",
            ]
        )
        self.assertEqual(res.returncode, 1, msg=f"Stderr: {res.stderr}")
        payload = json.loads(res.stdout)
        self.assertFalse(payload["valid"])
        self.assertTrue(any(f["code"] == "record_path_escapes" for f in payload["findings"]))

    def test_absolute_record_inside_root_is_valid(self) -> None:
        """Absolute record path that resolves within project-root is allowed and succeeds."""
        rec_path = self.proj_root / "valid_record.json"
        rec_path.write_text(json.dumps(VALID_INTAKE_RECORD), encoding="utf-8")

        res = self.run_cli(
            [
                str(rec_path.resolve()),
                "--project-root",
                str(self.proj_root),
                "--transition",
                "intake-authoring",
                "--documents",
                "docs/architecture/system-blueprint.md",
                "--format",
                "json",
            ]
        )
        self.assertEqual(res.returncode, 0, msg=f"Stderr: {res.stderr}\nStdout: {res.stdout}")
        payload = json.loads(res.stdout)
        self.assertTrue(payload["valid"])
        self.assertTrue(payload["eligible"])

    def test_colon_in_target_path_rejected_exit_1(self) -> None:
        """Target document with colon or ADS must be rejected with exit 1."""
        rec_data = dict(VALID_INTAKE_RECORD)
        rec_data["documents"] = [
            {
                "path": "docs/architecture/system-blueprint.md:stream",
                "kind": "blueprint",
                "audience": "Engineers",
                "reader_task": "Review",
                "sources": VALID_INTAKE_RECORD["documents"][0]["sources"],
            }
        ]
        rec_path = self.proj_root / "colon_target.json"
        rec_path.write_text(json.dumps(rec_data), encoding="utf-8")

        res = self.run_cli(
            [
                str(rec_path),
                "--project-root",
                str(self.proj_root),
                "--transition",
                "intake-authoring",
                "--documents",
                "docs/architecture/system-blueprint.md:stream",
                "--format",
                "json",
            ]
        )
        self.assertEqual(res.returncode, 1, msg=f"Stderr: {res.stderr}")
        payload = json.loads(res.stdout)
        self.assertFalse(payload["valid"])
        self.assertTrue(any("unsafe" in f["code"] for f in payload["findings"]))

    def test_colon_in_evidence_path_rejected_exit_1(self) -> None:
        """Evidence path with colon must be rejected with exit 1."""
        rec_data = dict(VALID_INTAKE_RECORD)
        rec_data["documents"] = [
            {
                "path": "docs/architecture/system-blueprint.md",
                "kind": "blueprint",
                "audience": "Engineers",
                "reader_task": "Review",
                "sources": [
                    {
                        "path": "evidence/source.md:stream",
                        "sha256": "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
                        "start_line": 1,
                        "end_line": 1,
                        "quote": "Valid evidence statement.",
                    }
                ],
            }
        ]
        rec_path = self.proj_root / "colon_evidence.json"
        rec_path.write_text(json.dumps(rec_data), encoding="utf-8")

        res = self.run_cli(
            [
                str(rec_path),
                "--project-root",
                str(self.proj_root),
                "--transition",
                "intake-authoring",
                "--documents",
                "docs/architecture/system-blueprint.md",
                "--format",
                "json",
            ]
        )
        self.assertEqual(res.returncode, 1, msg=f"Stderr: {res.stderr}")
        payload = json.loads(res.stdout)
        self.assertFalse(payload["valid"])
        self.assertTrue(any("unsafe" in f["code"] for f in payload["findings"]))

    def test_intake_nonexistent_target_below_existing_file_rejected(self) -> None:
        """Intake target path whose parent is an existing regular file must be rejected."""
        (self.proj_root / "docs" / "existing_file").write_text("regular file", encoding="utf-8")

        rec_data = dict(VALID_INTAKE_RECORD)
        rec_data["documents"] = [
            {
                "path": "docs/existing_file/child.md",
                "kind": "blueprint",
                "audience": "Engineers",
                "reader_task": "Review",
                "sources": VALID_INTAKE_RECORD["documents"][0]["sources"],
            }
        ]
        rec_path = self.proj_root / "intake_bad_parent.json"
        rec_path.write_text(json.dumps(rec_data), encoding="utf-8")

        res = self.run_cli(
            [
                str(rec_path),
                "--project-root",
                str(self.proj_root),
                "--transition",
                "intake-authoring",
                "--documents",
                "docs/existing_file/child.md",
                "--format",
                "json",
            ]
        )
        self.assertEqual(res.returncode, 1, msg=f"Stderr: {res.stderr}")
        payload = json.loads(res.stdout)
        self.assertFalse(payload["valid"])
        self.assertTrue(any(f["code"] == "doc_target_not_regular_file" for f in payload["findings"]))

    def test_symlink_loop_record_path_no_unhandled_traceback(self) -> None:
        """A symlink loop record path should terminate gracefully without an uncaught traceback."""
        loop_link = self.proj_root / "loop_record.json"
        try:
            loop_link.symlink_to(loop_link)
        except OSError:
            self.skipTest("Symlinks not supported in environment")

        res = self.run_cli(
            [
                str(loop_link),
                "--project-root",
                str(self.proj_root),
                "--transition",
                "intake-authoring",
                "--documents",
                "docs/architecture/system-blueprint.md",
            ]
        )
        self.assertIn(res.returncode, (1, 2))
        self.assertNotIn("Traceback", res.stderr)


if __name__ == "__main__":
    unittest.main()
