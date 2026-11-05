#!/usr/bin/env python3
"""Windows and cross-platform boundary regression tests for `scripts/validate.py docs`.

Tests:
1. Cross-platform host-native absolute record path inside project root succeeds (exit 0).
2. Windows-specific absolute drive path (e.g. C:\\...\\record.json) inside root succeeds on Windows;
   skipped cleanly on non-Windows platforms.
3. Colon in record tail / Alternate Data Streams (ADS) and colon in relative target/evidence rejected (exit 1).
4. Symlink loop in project root directory safely rejected with exit 2 and no traceback (if symlinks supported).
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


class TestDocGateWindows(unittest.TestCase):
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

    def test_hostnative_absolute_record_inside_root_succeeds(self) -> None:
        """Absolute record path on the host native filesystem within project root exits 0."""
        rec_path = (self.proj_root / "record.json").resolve()
        rec_path.write_text(json.dumps(VALID_INTAKE_RECORD), encoding="utf-8")

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
        self.assertEqual(res.returncode, 0, msg=f"Stderr: {res.stderr}\nStdout: {res.stdout}")
        payload = json.loads(res.stdout)
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["findings"], [])

    def test_windows_drive_absolute_record_inside_root(self) -> None:
        """On Windows, absolute path with drive letter (e.g. C:\\path\\record.json) succeeds."""
        if sys.platform != "win32":
            self.skipTest("Windows drive letter path test requires Windows platform")

        rec_path = (self.proj_root / "record.json").resolve()
        rec_path.write_text(json.dumps(VALID_INTAKE_RECORD), encoding="utf-8")

        # Ensure path format has drive letter on Windows
        win_path_str = str(rec_path)
        self.assertRegex(win_path_str, r"^[a-zA-Z]:[\\/]")

        res = self.run_cli(
            [
                win_path_str,
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
        self.assertEqual(payload["findings"], [])

    def test_colon_in_record_tail_or_ads_rejected_exit_1(self) -> None:
        """Colon in record path tail (e.g. stream/ADS or invalid segment) rejected with exit 1."""
        rec_path = (self.proj_root / "record.json").resolve()
        rec_path.write_text(json.dumps(VALID_INTAKE_RECORD), encoding="utf-8")

        # Tail with ADS stream
        bad_record_str = f"{rec_path}:hidden_stream"

        res = self.run_cli(
            [
                bad_record_str,
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
        self.assertEqual(res.returncode, 1, msg=f"Stderr: {res.stderr}\nStdout: {res.stdout}")
        payload = json.loads(res.stdout)
        self.assertFalse(payload["valid"])
        self.assertTrue(any("record_path" in f["code"] or "unsafe" in f["code"] for f in payload["findings"]))

    def test_colon_in_relative_target_and_evidence_rejected_exit_1(self) -> None:
        """Colon / ADS in document target and evidence paths rejected with exit 1."""
        # 1. Target with colon
        rec_data = dict(VALID_INTAKE_RECORD)
        rec_path = self.proj_root / "colon_target.json"
        rec_path.write_text(json.dumps(rec_data), encoding="utf-8")

        res_target = self.run_cli(
            [
                str(rec_path),
                "--project-root",
                str(self.proj_root),
                "--transition",
                "intake-authoring",
                "--documents",
                "docs/architecture/system-blueprint.md:ads",
                "--format",
                "json",
            ]
        )
        self.assertEqual(res_target.returncode, 1, msg=f"Stderr: {res_target.stderr}")
        payload_target = json.loads(res_target.stdout)
        self.assertFalse(payload_target["valid"])
        self.assertTrue(any("unsafe" in f["code"] for f in payload_target["findings"]))

        # 2. Evidence with colon
        rec_data_ev = dict(VALID_INTAKE_RECORD)
        rec_data_ev["documents"] = [
            {
                "path": "docs/architecture/system-blueprint.md",
                "kind": "blueprint",
                "audience": "Engineers",
                "reader_task": "Review",
                "sources": [
                    {
                        "path": "evidence/source.md:stream",
                        "sha256": "e88dfc324d0af82f9efeb9b5c1bb70d59515626f831b9fc30081b8287f75dc99",
                        "start_line": 1,
                        "end_line": 1,
                        "quote": "Valid evidence statement.",
                    }
                ],
            }
        ]
        rec_path_ev = self.proj_root / "colon_ev.json"
        rec_path_ev.write_text(json.dumps(rec_data_ev), encoding="utf-8")

        res_ev = self.run_cli(
            [
                str(rec_path_ev),
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
        self.assertEqual(res_ev.returncode, 1, msg=f"Stderr: {res_ev.stderr}")
        payload_ev = json.loads(res_ev.stdout)
        self.assertFalse(payload_ev["valid"])
        self.assertTrue(any("unsafe" in f["code"] for f in payload_ev["findings"]))

    def test_symlink_loop_project_root_safely_exit_2_no_traceback(self) -> None:
        """Symlink loop pointing project root to itself exits 2 cleanly with no traceback."""
        loop_dir = self.proj_root / "loop_root"
        try:
            loop_dir.symlink_to(loop_dir)
        except (OSError, NotImplementedError, AttributeError):
            self.skipTest("Symlinks not supported on this platform/filesystem")

        rec_path = self.proj_root / "record.json"
        rec_path.write_text(json.dumps(VALID_INTAKE_RECORD), encoding="utf-8")

        res = self.run_cli(
            [
                str(rec_path),
                "--project-root",
                str(loop_dir),
                "--transition",
                "intake-authoring",
                "--documents",
                "docs/architecture/system-blueprint.md",
                "--format",
                "json",
            ]
        )
        self.assertEqual(res.returncode, 2, msg=f"Stderr: {res.stderr}\nStdout: {res.stdout}")
        self.assertNotIn("Traceback", res.stderr)


if __name__ == "__main__":
    unittest.main()
