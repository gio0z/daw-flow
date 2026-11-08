"""Exercise runner plumbing with fake agents; these are not agent efficacy results."""

import json
import hashlib
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
RUNNER = REPO_ROOT / "tools/evaluation/evaluate.py"
MODULE_COUNT = len(json.loads((REPO_ROOT / "references/suite-manifest.json").read_text())["modules"])
FAKE_AGENT = '''import pathlib
import sys
import time

prompt_file, workspace, action, *extra = sys.argv[1:]
prompt = pathlib.Path(prompt_file).read_text()
if sys.stdin.read() != prompt:
    raise RuntimeError("stdin differs from retained prompt")
root = pathlib.Path(workspace)
if action in ("patch", "noisy-patch"):
    source = root / "calculator.py"
    source.write_text(source.read_text().replace("return left - right", "return left + right"))
    if action == "noisy-patch":
        source.write_text('print("debug noise")\\n' + source.read_text())
elif action == "bad-patch":
    (root / "calculator.py").write_text("def add(:\\n")
elif action == "mutate":
    (root / "unauthorized.txt").write_text("review must not write this")
elif action == "fail":
    print("retained partial output", flush=True)
    print("fake agent failure", file=sys.stderr, flush=True)
    sys.exit(7)
elif action == "timeout":
    print("retained before timeout", flush=True)
    time.sleep(10)
if extra:
    print(extra[0])
print("fake agent; reasoning is deliberately ungraded")
'''


class EvaluateRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.adapter = self.root / "fake_agent.py"
        self.adapter.write_text(FAKE_AGENT, encoding="utf-8")

    def evaluate(self, action, case="patch", mode="skill", extra=None, timeout=5, output=None):
        output = output or self.root / "evidence"
        command = [sys.executable, str(self.adapter), "{prompt_file}", "{workspace}", action]
        if extra:
            command.append(extra)
        result = subprocess.run(
            [sys.executable, str(RUNNER), "--agent-command", json.dumps(command),
             "--output-dir", str(output), "--case", case, "--mode", mode,
             "--timeout", str(timeout), "--agent-label", "unit-test fake harness; no efficacy claim"],
            text=True, capture_output=True, timeout=20,
        )
        summary = json.loads((output / "summary.json").read_text()) if (output / "summary.json").exists() else None
        return result, summary, output

    def test_patch_runs_real_public_checks_and_stages_complete_bundle(self):
        result, summary, output = self.evaluate("patch")
        self.assertEqual(result.returncode, 0, result.stderr)
        run = summary["results"][0]
        self.assertEqual(run["status"], "artifact_checks_passed")
        self.assertEqual(run["human_review"]["status"], "ungraded")
        installed = pathlib.Path(run["installed_suite"])
        self.assertTrue((installed / "scripts/route.py").is_file())
        self.assertTrue((installed / "references/suite-manifest.json").is_file())
        self.assertEqual(len(list((installed / "skills").glob("daw-*/SKILL.md"))), MODULE_COUNT)
        self.assertEqual(len(list((installed / "templates").glob("*.md"))), 14)
        observed = run["checks"][1]["observed"]
        self.assertIn("4 public add behavior checks passed", pathlib.Path(observed["stdout"]).read_text())
        self.assertTrue((output / "patch-skill-001/before.json").is_file())
        self.assertTrue((output / "patch-skill-001/after.json").is_file())

    def test_bare_control_has_no_workspace_local_skill_and_keeps_separate_runs(self):
        result, summary, _ = self.evaluate("patch", mode="both")
        self.assertEqual(result.returncode, 0, result.stderr)
        bare, skill = summary["results"]
        self.assertIsNone(bare["installed_suite"])
        self.assertFalse((pathlib.Path(bare["workspace"]) / ".agents").exists())
        self.assertNotEqual(bare["workspace"], skill["workspace"])
        self.assertIn("contaminate", bare["limitations"][1])

    def test_staged_distribution_passes_its_package_validator_with_license(self):
        result, summary, _ = self.evaluate("noop", case="review")
        self.assertEqual(result.returncode, 0, result.stderr)
        installed = pathlib.Path(summary["results"][0]["installed_suite"])
        validation = subprocess.run(
            [sys.executable, str(installed / "scripts/validate.py"), "package", "--format", "json"],
            cwd=installed, text=True, capture_output=True, timeout=10,
        )
        self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)
        self.assertIn("MIT License", (installed / "LICENSE").read_text())
        self.assertTrue((installed / "VERSION").is_file())
        self.assertTrue((installed / "agents/openai.yaml").is_file())
        self.assertFalse((installed / "tests").exists())
        self.assertFalse((installed / "docs").exists())
        self.assertFalse((installed / "README.md").exists())
        self.assertFalse((installed / "AGENTS.md").exists())
        self.assertFalse((installed / "tools").exists())
        identity = summary["results"][0]["suite_identity"]
        self.assertEqual(identity["version"], (installed / "VERSION").read_text().strip())
        self.assertEqual(identity["manifest_sha256"], hashlib.sha256((installed / "references/suite-manifest.json").read_bytes()).hexdigest())

    def test_suite_identity_ignores_timestamps_and_caches_but_tracks_changed_bytes(self):
        result, summary, _ = self.evaluate("noop", case="review")
        self.assertEqual(result.returncode, 0, result.stderr)
        installed = pathlib.Path(summary["results"][0]["installed_suite"])
        from tools.evaluation import evaluate
        original = evaluate.suite_identity(installed)
        os.utime(installed / "SKILL.md", ns=(1, 1))
        cache = installed / "scripts/__pycache__"
        cache.mkdir()
        (cache / "transient.pyc").write_bytes(b"cache only")
        self.assertEqual(original, evaluate.suite_identity(installed))
        with (installed / "SKILL.md").open("a") as document:
            document.write("\nChanged instruction bytes.\n")
        changed = evaluate.suite_identity(installed)
        self.assertNotEqual(original["payload_sha256"], changed["payload_sha256"])
        self.assertEqual(original["manifest_sha256"], changed["manifest_sha256"])

    def test_review_mutation_fails_snapshot_check(self):
        result, summary, _ = self.evaluate("mutate", case="review")
        self.assertEqual(result.returncode, 1)
        run = summary["results"][0]
        self.assertEqual(run["status"], "artifact_checks_failed")
        self.assertIn("unauthorized.txt", run["checks"][0]["changed_paths"])

    def test_broken_patch_fails_runtime_grading_with_retained_diagnostics(self):
        result, summary, _ = self.evaluate("bad-patch")
        self.assertEqual(result.returncode, 1)
        check = summary["results"][0]["checks"][1]
        self.assertEqual(check["status"], "fail")
        self.assertIn("SyntaxError", pathlib.Path(check["observed"]["stderr"]).read_text())

    def test_cli_output_must_match_including_unrequested_noise(self):
        result, summary, _ = self.evaluate("noisy-patch")
        self.assertEqual(result.returncode, 1)
        check = summary["results"][0]["checks"][2]
        self.assertEqual(check["status"], "fail")
        self.assertEqual(check["observed"]["exit_code"], 0)
        self.assertEqual(check["stdout_equals"], "-3\n")

    def test_agent_nonzero_exit_retains_output_and_reports_failure(self):
        result, summary, _ = self.evaluate("fail", case="review")
        self.assertEqual(result.returncode, 1)
        run = summary["results"][0]
        self.assertEqual(run["status"], "agent_failed")
        self.assertEqual(run["observed_agent_process"]["exit_code"], 7)
        self.assertIn("retained partial output", pathlib.Path(run["observed_agent_process"]["stdout"]).read_text())
        self.assertIn("fake agent failure", pathlib.Path(run["observed_agent_process"]["stderr"]).read_text())

    def test_timeout_retains_partial_output_and_never_defaults_to_pass(self):
        result, summary, _ = self.evaluate("timeout", case="review", timeout=0.2)
        self.assertEqual(result.returncode, 1)
        run = summary["results"][0]
        self.assertEqual(run["status"], "agent_timeout")
        self.assertTrue(run["observed_agent_process"]["timed_out"])
        self.assertIn("retained before timeout", pathlib.Path(run["observed_agent_process"]["stdout"]).read_text())

    def test_argv_shell_syntax_is_literal(self):
        target = self.root / "shell-must-not-create-this"
        literal = f"$(touch {target})"
        result, summary, _ = self.evaluate("noop", case="review", extra=literal)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(target.exists())
        output = pathlib.Path(summary["results"][0]["observed_agent_process"]["stdout"]).read_text()
        self.assertIn(literal, output)

    def test_substituted_values_are_not_resubstituted(self):
        output = self.root / "{suite_root}" / "evidence"
        result, summary, _ = self.evaluate("noop", case="review", mode="bare", extra="{workspace}", output=output)
        self.assertEqual(result.returncode, 0, result.stderr)
        argv = summary["results"][0]["observed_agent_process"]["argv"]
        expected = str((output / "review-bare-001" / "workspace").resolve())
        self.assertEqual(argv[-1], expected)

    def test_existing_output_directory_is_not_overwritten(self):
        output = self.root / "evidence"
        output.mkdir()
        sentinel = output / "keep.txt"
        sentinel.write_text("previous evidence")
        result, summary, _ = self.evaluate("patch", output=output)
        self.assertEqual(result.returncode, 2)
        self.assertIsNone(summary)
        self.assertEqual(sentinel.read_text(), "previous evidence")
        self.assertFalse((output / "patch-skill-001").exists())

    def test_cli_grader_accepts_expected_nonzero_and_labels_human_review_ungraded(self):
        result, summary, _ = self.evaluate("noop", case="cli")
        self.assertEqual(result.returncode, 0, result.stderr)
        run = summary["results"][0]
        check = run["checks"][1]
        self.assertEqual(check["expected_exit_code"], 2)
        self.assertEqual(check["observed"]["exit_code"], 2)
        self.assertEqual(check["status"], "pass")
        self.assertEqual(check["observer"], "grader")
        self.assertEqual(run["human_review"]["status"], "ungraded")

    def test_runner_cli_help_works_from_arbitrary_cwd(self):
        res = subprocess.run(
            [sys.executable, str(RUNNER), "--help"],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("--agent-command", res.stdout)
        self.assertIn("--output-dir", res.stdout)

if __name__ == "__main__":
    unittest.main()
