"""Behavioral regression test for bookmark-manager acceptance.py R2 persistence."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parent.parent
ACCEPTANCE_SCRIPT = REPO_ROOT / "references" / "wizard-bench" / "bookmark-manager" / "acceptance.py"

TOY_BOOKMARKS_TEMPLATE = '''#!/usr/bin/env python3
import json
import sys
from pathlib import Path

data_file = Path("bookmarks.json")

def main():
    args = sys.argv[1:]
    if not args:
        return 0
    cmd = args[0]
    if cmd == "search":
        if not data_file.exists():
            print("No bookmarks found.")
            return 0
        print("Found bookmarks.")
        return 0
    elif cmd == "add":
        if "--url" in args:
            url_idx = args.index("--url") + 1
            url = args[url_idx]
            if url.startswith("ftp://"):
                sys.stderr.write("Error: invalid URL scheme\\n")
                return 1
        # Populate initial test state on add
        if not data_file.exists():
            data = __INITIAL_DATA__
            data_file.write_text(json.dumps(data), encoding="utf-8")
        print("Saved bookmark: Python Official")
        return 0
    return 0

if __name__ == "__main__":
    sys.exit(main())
'''


class BookmarkAcceptanceR2Tests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="bookmark-test-")
        self.addCleanup(self.temp_dir.cleanup)
        self.workspace = Path(self.temp_dir.name)

    def _setup_toy_workspace(self, initial_data: list | dict) -> Path:
        code = TOY_BOOKMARKS_TEMPLATE.replace("__INITIAL_DATA__", json.dumps(initial_data))
        entrypoint = self.workspace / "bookmarks.py"
        entrypoint.write_text(code, encoding="utf-8")
        return entrypoint

    def _run_acceptance(self) -> dict[str, dict]:
        res = subprocess.run(
            [sys.executable, str(ACCEPTANCE_SCRIPT), str(self.workspace)],
            cwd=str(self.workspace),
            capture_output=True,
            text=True,
        )
        checks = {}
        for line in res.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if "check" in record:
                    checks[record["check"]] = record
            except json.JSONDecodeError:
                pass
        return checks

    def test_r2_passes_canonical_tag_order(self):
        self._setup_toy_workspace([
            {
                "url": "https://python.org",
                "title": "Python Official",
                "tags": ["python", "programming"],
            }
        ])
        results = self._run_acceptance()
        self.assertIn("R2_json_persistence", results)
        self.assertEqual(results["R2_json_persistence"]["status"], "pass")

    def test_r2_passes_reversed_tag_order(self):
        self._setup_toy_workspace([
            {
                "url": "https://python.org",
                "title": "Python Official",
                "tags": ["programming", "python"],
            }
        ])
        results = self._run_acceptance()
        self.assertIn("R2_json_persistence", results)
        self.assertEqual(results["R2_json_persistence"]["status"], "pass")

    def test_r2_fails_corrupted_url_with_reversed_tags(self):
        self._setup_toy_workspace([
            {
                "url": "https://evil.org",
                "title": "Python Official",
                "tags": ["programming", "python"],
            }
        ])
        results = self._run_acceptance()
        self.assertIn("R2_json_persistence", results)
        self.assertEqual(results["R2_json_persistence"]["status"], "fail")

    def test_r2_fails_corrupted_title_with_reversed_tags(self):
        self._setup_toy_workspace([
            {
                "url": "https://python.org",
                "title": "Wrong Title",
                "tags": ["programming", "python"],
            }
        ])
        results = self._run_acceptance()
        self.assertIn("R2_json_persistence", results)
        self.assertEqual(results["R2_json_persistence"]["status"], "fail")

    def test_r2_fails_extra_rows_with_reversed_tags(self):
        self._setup_toy_workspace([
            {
                "url": "https://python.org",
                "title": "Python Official",
                "tags": ["programming", "python"],
            },
            {
                "url": "https://extra.org",
                "title": "Extra Record",
                "tags": ["extra"],
            },
        ])
        results = self._run_acceptance()
        self.assertIn("R2_json_persistence", results)
        self.assertEqual(results["R2_json_persistence"]["status"], "fail")


if __name__ == "__main__":
    unittest.main()
