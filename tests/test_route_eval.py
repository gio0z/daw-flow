"""Route eval harness tests: suite selection, exit-code assertion, and failure reporting."""

import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tools" / "evaluation" / "route_eval_fixture.json"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.evaluation import route_eval  # noqa: E402


def run_harness(*argv: str) -> tuple[int, str]:
    """Run the harness in-process and capture its printed report."""
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        code = route_eval.main(list(argv))
    return code, stdout.getvalue()


class RouteEvalHarnessTests(unittest.TestCase):
    def test_repo_fixture_passes(self) -> None:
        code, output = run_harness(str(FIXTURE))
        self.assertEqual(code, 0, output)

    def test_run_route_returns_process_exit_code(self) -> None:
        request = {
            "schema_version": 1,
            "intent": "review",
            "requirements": "clear",
            "risk": "unknown",
            "workspace": "in-place",
        }
        exit_code, envelope = route_eval.run_route(request, REPO_ROOT)
        self.assertEqual(exit_code, 0)
        self.assertEqual(envelope["status"], "ready")

        bad_request = dict(request, schema_version=99)
        exit_code, envelope = route_eval.run_route(bad_request, REPO_ROOT)
        self.assertEqual(exit_code, 2)
        self.assertEqual(envelope["status"], "error")

    def test_wrong_expectation_fails_with_message(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        scenario = fixture["scenarios"][0]
        scenario["expected"]["status"] = "blocked"
        scenario["expected"]["exit_code"] = 1
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "fixture.json"
            path.write_text(json.dumps({"schema_version": 1, "scenarios": [scenario]}), encoding="utf-8")
            code, output = run_harness(str(path))
        self.assertEqual(code, 1, output)
        self.assertIn("expected status 'blocked'", output)

    def test_unknown_root_fails_instead_of_validating_wrong_suite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing_root = pathlib.Path(tmp) / "not-a-suite"
            code, output = run_harness(str(FIXTURE), "--root", str(missing_root))
        self.assertNotEqual(code, 0)
        self.assertIn("route.py not found under suite root", output)


if __name__ == "__main__":
    unittest.main()
