"""Behavioral regression tests for bookmark-manager acceptance.py R4 and R6."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parent.parent
ACCEPTANCE_SCRIPT = REPO_ROOT / "references" / "wizard-bench" / "bookmark-manager" / "acceptance.py"

EXPECTED_ALL_PASS = {
    "R1_entrypoint_exists": "pass",
    "R2_json_persistence": "pass",
    "R3_add_command": "pass",
    "R4_validation_and_update": "pass",
    "R5_search_tag_and_query": "pass",
    "R6_search_output_formatting": "pass",
    "R7_missing_file_handling": "pass",
}

PERFECT_BOOKMARKS_CLI = '''#!/usr/bin/env python3
import json
import sys
from pathlib import Path

data_file = Path("bookmarks.json")

def load_data():
    if not data_file.exists():
        return []
    try:
        return json.loads(data_file.read_text(encoding="utf-8"))
    except Exception:
        return []

def save_data(data):
    data_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

def parse_tags(tags_str):
    if not tags_str:
        return []
    seen = set()
    result = []
    for raw in tags_str.split(","):
        tag = raw.strip().lower()
        if tag and tag not in seen:
            seen.add(tag)
            result.append(tag)
    return result

def main():
    args = sys.argv[1:]
    if not args:
        return 0
    cmd = args[0]
    if cmd == "search":
        if not data_file.exists():
            print("No bookmarks found.")
            return 0
        data = load_data()
        tag_filter = None
        query_filter = None
        i = 1
        while i < len(args):
            if args[i] == "--tag" and i + 1 < len(args):
                tag_filter = args[i + 1].strip().lower()
                i += 2
            elif args[i] == "--query" and i + 1 < len(args):
                query_filter = args[i + 1].strip().lower()
                i += 2
            else:
                i += 1
        matches = []
        for b in data:
            if tag_filter and tag_filter not in [t.lower() for t in b.get("tags", [])]:
                continue
            if query_filter:
                title_matches = query_filter in b.get("title", "").lower()
                url_matches = query_filter in b.get("url", "").lower()
                if not (title_matches or url_matches):
                    continue
            matches.append(b)
        if not matches:
            print("No bookmarks found.")
            return 0
        matches.sort(key=lambda x: x.get("title", ""))
        for b in matches:
            sorted_tags = sorted(b.get("tags", []))
            tags_str = ", ".join(sorted_tags)
            print(f"[{tags_str}] {b.get('title', '')} - {b.get('url', '')}")
        return 0

    elif cmd == "add":
        url = None
        title = None
        tags_str = ""
        i = 1
        while i < len(args):
            if args[i] == "--url" and i + 1 < len(args):
                url = args[i + 1]
                i += 2
            elif args[i] == "--title" and i + 1 < len(args):
                title = args[i + 1]
                i += 2
            elif args[i] == "--tags" and i + 1 < len(args):
                tags_str = args[i + 1]
                i += 2
            else:
                i += 1

        if not url or not (url.startswith("http://") or url.startswith("https://")):
            sys.stderr.write("Error: invalid URL scheme\\n")
            return 1
        data = load_data()
        tags = parse_tags(tags_str)
        existing = next((b for b in data if b.get("url") == url), None)
        if existing is not None:
            existing["title"] = title
            existing["tags"] = tags
            save_data(data)
            print(f"Updated bookmark: {title}")
            return 0
        else:
            data.append({"url": url, "title": title, "tags": tags})
            save_data(data)
            print(f"Saved bookmark: {title}")
            return 0
    return 0

if __name__ == "__main__":
    sys.exit(main())
'''

FAULTY_BOOKMARKS_CLI_INVALID_URL_EXIT_2 = PERFECT_BOOKMARKS_CLI.replace(
    'sys.stderr.write("Error: invalid URL scheme\\n")\n            return 1',
    'sys.stderr.write("Error: invalid URL scheme\\n")\n            return 2',
)

FAULTY_BOOKMARKS_CLI_WRONG_SORT = PERFECT_BOOKMARKS_CLI.replace(
    'matches.sort(key=lambda x: x.get("title", ""))',
    'matches.sort(key=lambda x: x.get("title", ""), reverse=True)',
)

FAULTY_BOOKMARKS_CLI_WRONG_FORMAT = PERFECT_BOOKMARKS_CLI.replace(
    'print(f"[{tags_str}] {b.get(\'title\', \'\')} - {b.get(\'url\', \'\')}")',
    'print(f"{b.get(\'title\', \'\')} [{tags_str}] - {b.get(\'url\', \'\')}")',
)
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



class BookmarkAcceptanceBehavioralRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="bookmark-behavior-")
        self.addCleanup(self.temp_dir.cleanup)
        self.workspace = Path(self.temp_dir.name)

    def _init_workspace(self, cli_code: str) -> None:
        entrypoint = self.workspace / "bookmarks.py"
        entrypoint.write_text(cli_code, encoding="utf-8")

    def _run_acceptance(self, expected_returncode: int = 0) -> dict[str, dict]:
        res = subprocess.run(
            [sys.executable, str(ACCEPTANCE_SCRIPT), str(self.workspace)],
            cwd=str(self.workspace),
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            res.returncode,
            expected_returncode,
            f"acceptance.py exited with {res.returncode}; stdout={res.stdout!r}, stderr={res.stderr!r}",
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

    def test_all_seven_checks_pass_on_correct_implementation(self):
        self._init_workspace(PERFECT_BOOKMARKS_CLI)
        results = self._run_acceptance(expected_returncode=0)
        for check, expected_status in EXPECTED_ALL_PASS.items():
            self.assertIn(check, results, f"Check {check} missing from results")
            self.assertEqual(results[check]["status"], expected_status, f"{check} status mismatch")

    def test_invalid_url_defect_fails_r4_only_while_r6_passes(self):
        self._init_workspace(FAULTY_BOOKMARKS_CLI_INVALID_URL_EXIT_2)
        results = self._run_acceptance(expected_returncode=1)
        self.assertEqual(results["R4_validation_and_update"]["status"], "fail")
        self.assertIn("Invalid URL check failed", results["R4_validation_and_update"]["detail"])
        self.assertEqual(results["R6_search_output_formatting"]["status"], "pass")
        # Other independent checks pass
        self.assertEqual(results["R1_entrypoint_exists"]["status"], "pass")
        self.assertEqual(results["R2_json_persistence"]["status"], "pass")
        self.assertEqual(results["R3_add_command"]["status"], "pass")
        self.assertEqual(results["R5_search_tag_and_query"]["status"], "pass")
        self.assertEqual(results["R7_missing_file_handling"]["status"], "pass")

    def test_wrong_sort_fails_r6_while_r4_passes(self):
        self._init_workspace(FAULTY_BOOKMARKS_CLI_WRONG_SORT)
        results = self._run_acceptance(expected_returncode=1)
        self.assertEqual(results["R4_validation_and_update"]["status"], "pass")
        self.assertEqual(results["R6_search_output_formatting"]["status"], "fail")

    def test_wrong_format_fails_r6_while_r4_passes(self):
        self._init_workspace(FAULTY_BOOKMARKS_CLI_WRONG_FORMAT)
        results = self._run_acceptance(expected_returncode=1)
        self.assertEqual(results["R4_validation_and_update"]["status"], "pass")
        self.assertEqual(results["R6_search_output_formatting"]["status"], "fail")
if __name__ == "__main__":
    unittest.main()
