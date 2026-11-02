"""Tests for daw-wizard interview benchmark runner and reference oracle.

These tests exercise the runner and oracle plumbing using isolated fake agents
and a self-contained temporary fixture scenario. They do not depend on external
network access, LLM APIs, or scenarios under references/wizard-bench/.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER = REPO_ROOT / "scripts/wizard_bench.py"
ORACLE = REPO_ROOT / "scripts/wizard_oracle.py"

FAKE_AGENT_CODE = """import sys
from pathlib import Path

prompt_file = Path(sys.argv[1])
workspace = Path(sys.argv[2])
action = sys.argv[3] if len(sys.argv) > 3 else "normal"
prompt = prompt_file.read_text(encoding="utf-8")

if "Use daw-wizard" in prompt:
    # Interview phase
    if action == "always_ask":
        q_dir = workspace / ".daw-interview"
        q_dir.mkdir(parents=True, exist_ok=True)
        (q_dir / "questions.md").write_text("1. What should we build?\\n")
    else:
        # Check if oracle's answer was provided in transcript
        if "The program must be entry.py and printing SUCCESS." in prompt:
            # Turn 2: write specs without questions
            specs_dir = workspace / "docs" / "specs"
            specs_dir.mkdir(parents=True, exist_ok=True)
            (specs_dir / "requirements.md").write_text("Spec: entrypoint is entry.py, output is SUCCESS\\n")
        else:
            # Turn 1: ask questions
            q_dir = workspace / ".daw-interview"
            q_dir.mkdir(parents=True, exist_ok=True)
            (q_dir / "questions.md").write_text("1. What is the entrypoint file and output?\\n")
else:
    # Build phase
    specs_file = workspace / "docs" / "specs" / "requirements.md"
    suite_staged = (workspace / ".agents").exists()
    if suite_staged:
        (workspace / "suite_found.txt").write_text("Error: suite should not be staged in build workspace\\n")
    if specs_file.is_file() and "entrypoint is entry.py" in specs_file.read_text(encoding="utf-8"):
        # Implements from specs
        (workspace / "entry.py").write_text("print('SUCCESS')\\n")
    else:
        # Brief arm or missing specs: guesses wrongly
        (workspace / "wrong_app.py").write_text("print('UNKNOWN')\\n")
"""

FAKE_JUDGE_CODE = """import json
import sys

scenario_file, transcript_file, specs_dir, mode = sys.argv[1:5]
if mode == "valid":
    print(json.dumps({
        "elicited_requirement_ids": ["R1"],
        "redundant_question_count": 0,
        "total_question_count": 1,
        "checklist": {
            "goal": True, "scope": True, "inputs_outputs": True, "data_changes": True,
            "edge_cases": True, "acceptance_tests": True, "constraints": True, "no_change_list": True
        },
        "unsupported_claims": []
    }))
elif mode == "partial":
    print(json.dumps({
        "elicited_requirement_ids": [],
        "redundant_question_count": 2,
        "total_question_count": 4,
        "checklist": {
            "goal": True, "scope": False, "inputs_outputs": False, "data_changes": False,
            "edge_cases": False, "acceptance_tests": False, "constraints": True, "no_change_list": False
        },
        "unsupported_claims": ["unsupported feature X"]
    }))
elif mode == "malformed":
    print("{this is not valid json")
"""

FIXTURE_ACCEPTANCE_CODE = """#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

workspace = Path(sys.argv[1]).resolve()
entry = workspace / "entry.py"

if not entry.is_file():
    print(json.dumps({"check": "entry_exists", "status": "fail", "detail": "Missing entry.py"}))
    sys.exit(1)

print(json.dumps({"check": "entry_exists", "status": "pass", "detail": "entry.py exists"}))
res = subprocess.run([sys.executable, str(entry)], cwd=str(workspace), capture_output=True, text=True)
if res.returncode == 0 and "SUCCESS" in res.stdout:
    print(json.dumps({"check": "prints_success", "status": "pass", "detail": "Printed SUCCESS"}))
    sys.exit(0)
else:
    print(json.dumps({"check": "prints_success", "status": "fail", "detail": f"Output: {res.stdout}"}))
    sys.exit(1)
"""

FIXTURE_SCENARIO_JSON = {
    "schema_version": 1,
    "id": "fixture-scenario",
    "brief": "Create a tool in Python.",
    "hidden_requirements": [
        {
            "id": "R1",
            "category": "constraint",
            "text": "The entrypoint must be entry.py and print SUCCESS.",
            "answer": "The program must be entry.py and printing SUCCESS.",
        }
    ],
    "out_of_scope_answer": "That is out of scope for this tool.",
}


class WizardBenchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

        # Set up fixture scenario
        self.scenarios_dir = self.root / "scenarios"
        self.scenario_dir = self.scenarios_dir / "fixture-scenario"
        self.scenario_dir.mkdir(parents=True)
        (self.scenario_dir / "scenario.json").write_text(
            json.dumps(FIXTURE_SCENARIO_JSON, indent=2), encoding="utf-8"
        )
        acceptance_path = self.scenario_dir / "acceptance.py"
        acceptance_path.write_text(FIXTURE_ACCEPTANCE_CODE, encoding="utf-8")
        acceptance_path.chmod(0o755)

        # Set up fake agent script
        self.agent_script = self.root / "fake_agent.py"
        self.agent_script.write_text(FAKE_AGENT_CODE, encoding="utf-8")

        # Set up fake judge script
        self.judge_script = self.root / "fake_judge.py"
        self.judge_script.write_text(FAKE_JUDGE_CODE, encoding="utf-8")

    def run_bench(
        self,
        output_dir: Path,
        arm: str = "both",
        action: str = "normal",
        judge_mode: str | None = None,
        max_turns: int = 4,
        runs: int = 1,
        timeout: float = 10.0,
    ) -> tuple[subprocess.CompletedProcess[str], dict | None]:
        agent_cmd = [sys.executable, str(self.agent_script), "{prompt_file}", "{workspace}", action]
        oracle_cmd = [
            sys.executable,
            str(ORACLE),
            "--scenario",
            "{scenario_file}",
            "--questions",
            "{questions_file}",
        ]

        cmd = [
            sys.executable,
            str(RUNNER),
            "--agent-command",
            json.dumps(agent_cmd),
            "--oracle-command",
            json.dumps(oracle_cmd),
            "--scenarios-dir",
            str(self.scenarios_dir),
            "--output-dir",
            str(output_dir),
            "--arm",
            arm,
            "--runs",
            str(runs),
            "--max-turns",
            str(max_turns),
            "--timeout",
            str(timeout),
        ]

        if judge_mode:
            judge_cmd = [
                sys.executable,
                str(self.judge_script),
                "{scenario_file}",
                "{transcript_file}",
                "{specs_dir}",
                judge_mode,
            ]
            cmd.extend(["--judge-command", json.dumps(judge_cmd)])

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        summary = None
        summary_file = output_dir / "summary.json"
        if summary_file.is_file():
            summary = json.loads(summary_file.read_text(encoding="utf-8"))
        return proc, summary

    def test_wizard_arm_two_turns_oracle_reaches_second_prompt_pass_rate_one(self) -> None:
        """Fake agent that asks once then writes docs; fake builder implements from docs."""
        output = self.root / "out_wizard"
        proc, summary = self.run_bench(output, arm="wizard", action="normal")
        self.assertEqual(proc.returncode, 0, f"Benchmark runner failed:\n{proc.stderr}")

        self.assertIsNotNone(summary)
        self.assertEqual(summary["arms"]["wizard"]["mean_pass_rate"], 1.0)
        self.assertEqual(summary["arms"]["wizard"]["mean_turns"], 2.0)

        run_dir = output / "fixture-scenario-wizard-001"
        self.assertTrue(run_dir.is_dir())

        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["turns_used"], 2)
        self.assertEqual(result["pass_rate"], 1.0)

        # Verify oracle answer reaches the second prompt transcript
        turn2_prompt = (run_dir / "turn_2_prompt.md").read_text(encoding="utf-8")
        self.assertIn("The program must be entry.py and printing SUCCESS.", turn2_prompt)

        # Verify evidence retention
        self.assertTrue((run_dir / "transcript.md").is_file())
        self.assertTrue((run_dir / "turn_1_questions.md").is_file())
        self.assertTrue((run_dir / "turn_1_answer.md").is_file())
        self.assertTrue((run_dir / "docs/requirements.md").is_file())
        self.assertTrue((run_dir / "build_workspace/entry.py").is_file())
        self.assertTrue((run_dir / "acceptance.stdout.txt").is_file())

    def test_brief_arm_workspace_has_no_specs_no_suite_and_acceptance_fails(self) -> None:
        """Brief arm: build workspace contains no docs/specs and no suite; acceptance fails => pass_rate < 1."""
        output = self.root / "out_brief"
        proc, summary = self.run_bench(output, arm="brief", action="normal")
        self.assertEqual(proc.returncode, 0, f"Benchmark runner failed:\n{proc.stderr}")

        self.assertIsNotNone(summary)
        self.assertLess(summary["arms"]["brief"]["mean_pass_rate"], 1.0)

        run_dir = output / "fixture-scenario-brief-001"
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        self.assertLess(result["pass_rate"], 1.0)

        build_ws = run_dir / "build_workspace"
        self.assertTrue(build_ws.is_dir())
        # Must contain no docs/specs and no suite
        self.assertFalse((build_ws / "docs/specs").exists())
        self.assertFalse((build_ws / ".agents").exists())
        self.assertFalse((build_ws / "suite_found.txt").exists())

    def test_turn_limit_agent_that_always_asks(self) -> None:
        """Turn limit: agent that always asks => status interview_turn_limit."""
        output = self.root / "out_turn_limit"
        proc, summary = self.run_bench(output, arm="wizard", action="always_ask", max_turns=3)
        self.assertEqual(proc.returncode, 0, f"Benchmark runner failed:\n{proc.stderr}")

        run_dir = output / "fixture-scenario-wizard-001"
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "interview_turn_limit")
        self.assertEqual(result["turns_used"], 3)

    def test_judge_valid_malformed_and_ungraded(self) -> None:
        """Judge: valid judge JSON => IRE and checklist score computed; malformed => error, not crashed; no judge => ungraded."""
        # 1. Valid judge
        output_valid = self.root / "out_judge_valid"
        proc_v, summary_v = self.run_bench(output_valid, arm="wizard", action="normal", judge_mode="valid")
        self.assertEqual(proc_v.returncode, 0)
        res_v = json.loads((output_valid / "fixture-scenario-wizard-001" / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(res_v["judge"]["status"], "graded")
        self.assertEqual(res_v["judge"]["ire"], 1.0)
        self.assertEqual(res_v["judge"]["checklist_score"], 8)
        self.assertEqual(res_v["judge"]["redundancy_ratio"], 0.0)

        # 2. Malformed judge
        output_mal = self.root / "out_judge_malformed"
        proc_m, summary_m = self.run_bench(output_mal, arm="wizard", action="normal", judge_mode="malformed")
        # Run must not crash (exit 0)
        self.assertEqual(proc_m.returncode, 0)
        res_m = json.loads((output_mal / "fixture-scenario-wizard-001" / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(res_m["judge"]["status"], "error")
        self.assertIn("JSONDecodeError", res_m["judge"]["error"])

        # 3. No judge => ungraded
        output_none = self.root / "out_judge_none"
        proc_n, summary_n = self.run_bench(output_none, arm="wizard", action="normal", judge_mode=None)
        self.assertEqual(proc_n.returncode, 0)
        res_n = json.loads((output_none / "fixture-scenario-wizard-001" / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(res_n["judge"], "ungraded")

    def test_reference_oracle_keyword_matching_and_out_of_scope(self) -> None:
        """Reference oracle: question mentioning requirement keywords gets answer; unrelated question gets out_of_scope_answer."""
        scenario_file = self.scenario_dir / "scenario.json"

        # Question mentioning keywords
        proc_match = subprocess.run(
            [sys.executable, str(ORACLE), "--scenario", str(scenario_file)],
            input="What is the entrypoint file and expected output?",
            text=True,
            capture_output=True,
        )
        self.assertEqual(proc_match.returncode, 0)
        self.assertEqual(
            proc_match.stdout.strip(),
            "The program must be entry.py and printing SUCCESS.",
        )

        # Unrelated question
        proc_unrelated = subprocess.run(
            [sys.executable, str(ORACLE), "--scenario", str(scenario_file)],
            input="What is the weather in Berlin?",
            text=True,
            capture_output=True,
        )
        self.assertEqual(proc_unrelated.returncode, 0)
        self.assertEqual(
            proc_unrelated.stdout.strip(),
            "That is out of scope for this tool.",
        )


if __name__ == "__main__":
    unittest.main()
