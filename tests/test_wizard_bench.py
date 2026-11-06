"""Tests for daw-wizard interview benchmark runner and reference oracle.

These tests exercise the runner and oracle plumbing using isolated fake agents
and a self-contained temporary fixture scenario. They do not depend on external
network access or LLM APIs. One oracle test runs the real reference oracle
against the bundled scenarios under tests/fixtures/wizard-bench/ to check that
off-topic questions disclose no hidden requirement.
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
RUNNER = REPO_ROOT / "tools/evaluation/wizard_bench.py"
ORACLE = REPO_ROOT / "tools/evaluation/wizard_oracle.py"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.evaluation.wizard_bench import aggregate_summary, evaluate_judge, run_scenario

FAKE_AGENT_CODE = """import json
import sys
from pathlib import Path

prompt_file = Path(sys.argv[1])
workspace = Path(sys.argv[2])
action = sys.argv[3] if len(sys.argv) > 3 else "normal"
prompt = prompt_file.read_text(encoding="utf-8")

if "Use daw-wizard" in prompt:
    # Interview phase
    if action == "no_answer":
        # Do nothing: neither questions nor specs produced
        pass
    elif action == "always_ask":
        q_dir = workspace / ".daw-interview"
        q_dir.mkdir(parents=True, exist_ok=True)
        (q_dir / "questions.md").write_text("1. What should we build?\\n")
    elif action == "history_two_rounds":
        if prompt.count("## Turn") >= 4:
            # Turn 3: two completed rounds seen, write specs without asking.
            specs_dir = workspace / "docs" / "specs"
            specs_dir.mkdir(parents=True, exist_ok=True)
            (specs_dir / "requirements.md").write_text("Spec: entrypoint is entry.py, output is SUCCESS\\n")
        else:
            q_dir = workspace / ".daw-interview"
            q_dir.mkdir(parents=True, exist_ok=True)
            if "## Turn" in prompt:
                # Turn 2: first answer seen, ask a second distinct question.
                (q_dir / "questions.md").write_text("2. Which output string confirms success?\\n")
            else:
                # Turn 1: ask first question.
                (q_dir / "questions.md").write_text("1. What is the entrypoint file and output?\\n")
    else:
        if action == "secret_check":
            staged_suite = workspace / ".agents/skills/deterministic-agentic-workflow"
            leak_report = {
                "wizard_bench_exists": (staged_suite / "references/wizard-bench").exists() or (staged_suite / "tests/fixtures/wizard-bench").exists(),
                "scenario_json_count": len(list(staged_suite.rglob("scenario.json"))),
                "acceptance_py_count": len(list(staged_suite.rglob("acceptance.py"))),
                "eval_test_exists": (staged_suite / "tests/test_wizard_bench.py").exists(),
                "skill_md_exists": (staged_suite / "skills/daw-wizard/SKILL.md").exists(),
                "routing_md_exists": (staged_suite / "references/routing.md").exists(),
            }
            (workspace / "secret_findings.json").write_text(json.dumps(leak_report), encoding="utf-8")

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

HISTORY_READING_ORACLE_CODE = """import json
import sys
from pathlib import Path

scenario_file, questions_file, transcript_file, state_file = sys.argv[1:5]
transcript = Path(transcript_file)
if not transcript.is_file():
    raise FileNotFoundError(f"transcript missing on oracle invocation: {transcript_file}")
history = transcript.read_text(encoding="utf-8")
state_path = Path(state_file)
turn = int(state_path.read_text(encoding="utf-8")) if state_path.is_file() else 1
state_path.write_text(str(turn + 1), encoding="utf-8")
question = "What is the entrypoint file and output?"
answer = "The program must be entry.py and printing SUCCESS."
if turn == 1:
    if history.strip():
        sys.stderr.write(f"Expected empty transcript on first oracle call, got: {history!r}\\n")
        sys.exit(3)
elif turn == 2:
    if question not in history or answer not in history:
        sys.stderr.write(f"Expected turn 1 question and answer in transcript, got: {history!r}\\n")
        sys.exit(4)
scenario = json.loads(Path(scenario_file).read_text(encoding="utf-8"))
questions = Path(questions_file).read_text(encoding="utf-8")
for requirement in scenario.get("hidden_requirements", []):
    keywords = [w for w in requirement["text"].lower().split() if len(w) > 3]
    if any(w in questions.lower() for w in keywords):
        print(requirement["answer"])
        break
else:
    print(scenario.get("out_of_scope_answer", "Out of scope."))
"""

FAKE_JUDGE_CODE = """import json
import sys
from pathlib import Path

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
elif mode == "mixed":
    # Uses state file to succeed once then fail
    state_file = Path(specs_dir).parent.parent / "judge_state.txt"
    if not state_file.is_file():
        state_file.write_text("called")
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
    else:
        print("{malformed json on second run")
"""

CRASHED_ACCEPTANCE_CODE = """#!/usr/bin/env python3
import json
import sys
print(json.dumps({"check": "R1_passes", "status": "pass"}))
sys.stdout.flush()
raise RuntimeError("Grader crashed after R1 passes")
"""

TIMEOUT_ACCEPTANCE_CODE = """#!/usr/bin/env python3
import time
time.sleep(10)
"""

MALFORMED_ACCEPTANCE_CODE = """#!/usr/bin/env python3
print("not valid json at all")
"""

DUPLICATE_ACCEPTANCE_CODE = """#!/usr/bin/env python3
import json
print(json.dumps({"check": "R1", "status": "pass"}))
print(json.dumps({"check": "R1", "status": "pass"}))
"""

ORDINARY_FAIL_ACCEPTANCE_CODE = """#!/usr/bin/env python3
import json
import sys
print(json.dumps({"check": "R1_passes", "status": "pass"}))
print(json.dumps({"check": "R2_fails", "status": "fail", "detail": "intentional check failure"}))
sys.exit(1)
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
        scenario: str = "all",
        oracle_cmd: list[str] | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict | None]:
        agent_cmd = [sys.executable, str(self.agent_script), "{prompt_file}", "{workspace}", action]
        if oracle_cmd is None:
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
        if scenario != "all":
            cmd.extend(["--scenario", scenario])

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

    def test_history_reading_oracle_gets_empty_then_prior_turn_transcript(self) -> None:
        """Two-round interview with an oracle reading {transcript_file} each call: first empty, then turn 1 Q/A."""
        oracle_script = self.root / "history_oracle.py"
        oracle_script.write_text(HISTORY_READING_ORACLE_CODE, encoding="utf-8")
        state_file = self.root / "oracle_calls.txt"
        oracle_cmd = [
            sys.executable,
            str(oracle_script),
            "{scenario_file}",
            "{questions_file}",
            "{transcript_file}",
            str(state_file),
        ]

        output = self.root / "out_history_oracle"
        proc, summary = self.run_bench(
            output, arm="wizard", action="history_two_rounds", oracle_cmd=oracle_cmd
        )
        self.assertEqual(proc.returncode, 0, f"Benchmark runner failed:\n{proc.stderr}")
        self.assertIsNotNone(summary)

        # Exactly two oracle invocations, both observing the expected history.
        self.assertEqual(state_file.read_text(encoding="utf-8"), "3")

        run_dir = output / "fixture-scenario-wizard-001"
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["turns_used"], 3)
        self.assertEqual(result["question_count"], 2)
        self.assertEqual(result["pass_rate"], 1.0)
        checks = {c["check"]: c["status"] for c in result["checks"]}
        self.assertEqual(checks, {"entry_exists": "pass", "prints_success": "pass"})


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
        """Turn limit: agent that always asks => status interview_turn_limit and nonzero exit."""
        output = self.root / "out_turn_limit"
        proc, summary = self.run_bench(output, arm="wizard", action="always_ask", max_turns=3)
        self.assertEqual(proc.returncode, 1, f"Expected nonzero exit on turn limit:\n{proc.stderr}")

        self.assertIsNotNone(summary)
        self.assertEqual(summary["arms"]["wizard"]["agent_failures"], 1)

        run_dir = output / "fixture-scenario-wizard-001"
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "interview_turn_limit")
        self.assertEqual(result["turns_used"], 3)

    def test_no_answer_agent_interview_failed(self) -> None:
        """No-answer agent: produces neither questions nor specs => status interview_failed and nonzero exit."""
        output = self.root / "out_no_answer"
        proc, summary = self.run_bench(output, arm="wizard", action="no_answer", max_turns=3)
        self.assertEqual(proc.returncode, 1, f"Expected nonzero exit on no-answer interview failure:\n{proc.stderr}")

        self.assertIsNotNone(summary)
        self.assertEqual(summary["arms"]["wizard"]["agent_failures"], 1)

        run_dir = output / "fixture-scenario-wizard-001"
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "interview_failed")

    def test_evaluate_judge_rejects_invalid_counts_and_unknown_ids(self) -> None:
        """Judge validation: negative/excess/bool counts and unknown elicited IDs raise ValueError."""
        scenario = {
            "hidden_requirements": [{"id": "R1"}, {"id": "R2"}],
        }
        base = {
            "elicited_requirement_ids": ["R1"],
            "redundant_question_count": 0,
            "total_question_count": 1,
            "checklist": {
                "goal": True, "scope": True, "inputs_outputs": True, "data_changes": True,
                "edge_cases": True, "acceptance_tests": True, "constraints": True, "no_change_list": True,
            },
            "unsupported_claims": [],
        }
        for changes in [
            {"redundant_question_count": -1},
            {"total_question_count": -1},
            {"redundant_question_count": 5, "total_question_count": 1},
            {"redundant_question_count": True},
            {"total_question_count": False},
            {"elicited_requirement_ids": ["R1", "INVENTED"]},
        ]:
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    evaluate_judge({**base, **changes}, scenario)

    def test_evaluate_judge_valid_boundaries_and_partial_ids(self) -> None:
        """Judge validation: zero/zero and partial known IDs grade with unchanged formulas."""
        scenario = {
            "hidden_requirements": [{"id": "R1"}, {"id": "R2"}],
        }
        result = evaluate_judge(
            {
                "elicited_requirement_ids": ["R2"],
                "redundant_question_count": 0,
                "total_question_count": 0,
                "checklist": {
                    "goal": True, "scope": False, "inputs_outputs": False, "data_changes": False,
                    "edge_cases": False, "acceptance_tests": False, "constraints": True, "no_change_list": False,
                },
                "unsupported_claims": ["claim"],
            },
            scenario,
        )
        self.assertEqual(result["status"], "graded")
        self.assertEqual(result["ire"], 0.5)
        self.assertEqual(result["checklist_score"], 2)
        self.assertEqual(result["redundancy_ratio"], 0.0)
        self.assertEqual(result["fabrication_count"], 1)
        self.assertEqual(result["elicited_requirement_ids"], ["R2"])

    def test_judge_valid_malformed_and_ungraded(self) -> None:
        """Judge: valid judge JSON => IRE computed; malformed => error and nonzero CLI exit; no judge => ungraded and exit 0."""
        # 1. Valid judge
        output_valid = self.root / "out_judge_valid"
        proc_v, summary_v = self.run_bench(output_valid, arm="wizard", action="normal", judge_mode="valid")
        self.assertEqual(proc_v.returncode, 0)
        self.assertIsNotNone(summary_v)
        self.assertEqual(summary_v["arms"]["wizard"]["judge"]["status"], "graded")
        self.assertEqual(summary_v["arms"]["wizard"]["judge"]["graded_count"], 1)
        self.assertEqual(summary_v["arms"]["wizard"]["judge"]["error_count"], 0)
        res_v = json.loads((output_valid / "fixture-scenario-wizard-001" / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(res_v["judge"]["status"], "graded")
        self.assertEqual(res_v["judge"]["ire"], 1.0)
        self.assertEqual(res_v["judge"]["checklist_score"], 8)
        self.assertEqual(res_v["judge"]["redundancy_ratio"], 0.0)

        # 2. Malformed judge => failure propagated by CLI
        output_mal = self.root / "out_judge_malformed"
        proc_m, summary_m = self.run_bench(output_mal, arm="wizard", action="normal", judge_mode="malformed")
        self.assertEqual(proc_m.returncode, 1, "Expected nonzero exit when judge fails")
        self.assertIsNotNone(summary_m)
        self.assertEqual(summary_m["arms"]["wizard"]["judge"]["status"], "error")
        self.assertEqual(summary_m["arms"]["wizard"]["judge"]["graded_count"], 0)
        self.assertEqual(summary_m["arms"]["wizard"]["judge"]["error_count"], 1)
        res_m = json.loads((output_mal / "fixture-scenario-wizard-001" / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(res_m["judge"]["status"], "error")
        self.assertIn("JSONDecodeError", res_m["judge"]["error"])

        # 3. No judge => ungraded and exit 0
        output_none = self.root / "out_judge_none"
        proc_n, summary_n = self.run_bench(output_none, arm="wizard", action="normal", judge_mode=None)
        self.assertEqual(proc_n.returncode, 0)
        self.assertIsNotNone(summary_n)
        self.assertEqual(summary_n["arms"]["wizard"]["judge"], "ungraded")
        res_n = json.loads((output_none / "fixture-scenario-wizard-001" / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(res_n["judge"], "ungraded")

    def test_mixed_judge_graded_and_error(self) -> None:
        """Judge partial error: mixed graded and error runs visible with counts, means over graded, and CLI exit 1."""
        output = self.root / "out_judge_mixed"
        proc, summary = self.run_bench(output, arm="wizard", action="normal", judge_mode="mixed", runs=2)
        self.assertEqual(proc.returncode, 1, "Expected nonzero exit on mixed judge failure")
        self.assertIsNotNone(summary)
        judge_data = summary["arms"]["wizard"]["judge"]
        self.assertEqual(judge_data["status"], "partial_error")
        self.assertEqual(judge_data["graded_count"], 1)
        self.assertEqual(judge_data["error_count"], 1)
        self.assertEqual(judge_data["mean_ire"], 1.0)

    def test_acceptance_crashed_after_passes_fails_closed(self) -> None:
        """Acceptance crash: script prints pass then raises exception => status grading_failed, pass_rate 0, exit 1."""
        scenario_crashed = self.scenarios_dir / "crashed-scenario"
        scenario_crashed.mkdir(parents=True)
        crashed_json = dict(FIXTURE_SCENARIO_JSON, id="crashed-scenario")
        (scenario_crashed / "scenario.json").write_text(json.dumps(crashed_json), encoding="utf-8")
        (scenario_crashed / "acceptance.py").write_text(CRASHED_ACCEPTANCE_CODE, encoding="utf-8")

        output = self.root / "out_crashed"
        proc, summary = self.run_bench(output, arm="wizard", action="normal", scenario="crashed-scenario")
        self.assertEqual(proc.returncode, 1, "Expected nonzero exit when acceptance crashes")
        self.assertIsNotNone(summary)
        self.assertEqual(summary["arms"]["wizard"]["infrastructure_failures"], 1)

        run_dir = output / "crashed-scenario-wizard-001"
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "grading_failed")
        self.assertEqual(result["pass_rate"], 0.0)
        self.assertEqual(len(result["checks"]), 1)
        self.assertEqual(result["checks"][0]["check"], "R1_passes")

    def test_acceptance_simulated_timeout_fails_closed(self) -> None:
        """Acceptance timeout: runner enforces deadline fail-closed without 60s wait."""
        scenario_timeout = self.scenarios_dir / "timeout-scenario"
        scenario_timeout.mkdir(parents=True)
        timeout_json = dict(FIXTURE_SCENARIO_JSON, id="timeout-scenario")
        (scenario_timeout / "scenario.json").write_text(json.dumps(timeout_json), encoding="utf-8")
        (scenario_timeout / "acceptance.py").write_text(TIMEOUT_ACCEPTANCE_CODE, encoding="utf-8")

        output = self.root / "out_timeout"
        run_dir = output / "timeout-scenario-wizard-001"
        run_dir.mkdir(parents=True)
        agent_cmd = [sys.executable, str(self.agent_script), "{prompt_file}", "{workspace}", "normal"]
        oracle_cmd = [
            sys.executable,
            str(ORACLE),
            "--scenario",
            "{scenario_file}",
            "--questions",
            "{questions_file}",
        ]
        result = run_scenario(
            source=REPO_ROOT,
            run_dir=run_dir,
            scenario_dir=scenario_timeout,
            scenario_data=timeout_json,
            arm="wizard",
            repetition=1,
            agent_command=agent_cmd,
            oracle_command=oracle_cmd,
            judge_command=None,
            timeout=10.0,
            max_turns=4,
            agent_label="test",
            acceptance_timeout=0.1,
        )
        self.assertEqual(result["status"], "grading_failed")
        self.assertEqual(result["pass_rate"], 0.0)
        self.assertEqual(result["error"], "Acceptance test timed out")
        self.assertEqual(result["checks"], [])

        summary = aggregate_summary([result], ["timeout-scenario"])
        self.assertEqual(summary["arms"]["wizard"]["infrastructure_failures"], 1)

        saved = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["status"], "grading_failed")
        self.assertEqual(saved["pass_rate"], 0.0)
    def test_acceptance_malformed_and_duplicate_checks_fail_closed(self) -> None:
        """Acceptance malformed/duplicate checks fail closed."""
        # 1. Malformed
        scenario_mal = self.scenarios_dir / "mal-scenario"
        scenario_mal.mkdir(parents=True)
        mal_json = dict(FIXTURE_SCENARIO_JSON, id="mal-scenario")
        (scenario_mal / "scenario.json").write_text(json.dumps(mal_json), encoding="utf-8")
        (scenario_mal / "acceptance.py").write_text(MALFORMED_ACCEPTANCE_CODE, encoding="utf-8")

        output_mal = self.root / "out_acceptance_mal"
        proc_mal, summary_mal = self.run_bench(output_mal, arm="wizard", action="normal", scenario="mal-scenario")
        self.assertEqual(proc_mal.returncode, 1)
        self.assertIsNotNone(summary_mal)
        self.assertEqual(summary_mal["arms"]["wizard"]["infrastructure_failures"], 1)
        res_mal = json.loads((output_mal / "mal-scenario-wizard-001" / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(res_mal["status"], "grading_failed")
        self.assertEqual(res_mal["pass_rate"], 0.0)

        # 2. Duplicate
        scenario_dup = self.scenarios_dir / "dup-scenario"
        scenario_dup.mkdir(parents=True)
        dup_json = dict(FIXTURE_SCENARIO_JSON, id="dup-scenario")
        (scenario_dup / "scenario.json").write_text(json.dumps(dup_json), encoding="utf-8")
        (scenario_dup / "acceptance.py").write_text(DUPLICATE_ACCEPTANCE_CODE, encoding="utf-8")

        output_dup = self.root / "out_acceptance_dup"
        proc_dup, summary_dup = self.run_bench(output_dup, arm="wizard", action="normal", scenario="dup-scenario")
        self.assertEqual(proc_dup.returncode, 1)
        self.assertIsNotNone(summary_dup)
        self.assertEqual(summary_dup["arms"]["wizard"]["infrastructure_failures"], 1)
        res_dup = json.loads((output_dup / "dup-scenario-wizard-001" / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(res_dup["status"], "grading_failed")
        self.assertEqual(res_dup["pass_rate"], 0.0)

    def test_acceptance_ordinary_failure_scored_fractionally(self) -> None:
        """Ordinary acceptance failure: exit 1 with check failures preserves completed status and fractional score."""
        scenario_ord = self.scenarios_dir / "ordinary-fail-scenario"
        scenario_ord.mkdir(parents=True)
        ord_json = dict(FIXTURE_SCENARIO_JSON, id="ordinary-fail-scenario")
        (scenario_ord / "scenario.json").write_text(json.dumps(ord_json), encoding="utf-8")
        (scenario_ord / "acceptance.py").write_text(ORDINARY_FAIL_ACCEPTANCE_CODE, encoding="utf-8")

        output = self.root / "out_ordinary_fail"
        proc, summary = self.run_bench(output, arm="wizard", action="normal", scenario="ordinary-fail-scenario")
        self.assertEqual(proc.returncode, 0, f"Ordinary failure should not cause runner failure:\n{proc.stderr}")
        self.assertIsNotNone(summary)
        self.assertEqual(summary["arms"]["wizard"]["completed"], 1)
        self.assertEqual(summary["arms"]["wizard"]["infrastructure_failures"], 0)
        self.assertEqual(summary["arms"]["wizard"]["agent_failures"], 0)
        self.assertEqual(summary["arms"]["wizard"]["mean_pass_rate"], 0.5)

        run_dir = output / "ordinary-fail-scenario-wizard-001"
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["pass_rate"], 0.5)

    def test_staged_suite_sanitization_and_source_intact(self) -> None:
        """Staged suite is sanitized of hidden evaluation assets while source remains intact and skills functional."""
        output = self.root / "out_secret_check"
        proc, summary = self.run_bench(output, arm="wizard", action="secret_check")
        self.assertEqual(proc.returncode, 0, f"Runner failed:\n{proc.stderr}")

        run_dir = output / "fixture-scenario-wizard-001"
        report_file = run_dir / "interview_workspace" / "secret_findings.json"
        self.assertTrue(report_file.is_file())
        report = json.loads(report_file.read_text(encoding="utf-8"))
        self.assertFalse(report["wizard_bench_exists"])
        self.assertEqual(report["scenario_json_count"], 0)
        self.assertEqual(report["acceptance_py_count"], 0)
        self.assertFalse(report["eval_test_exists"])
        self.assertTrue(report["skill_md_exists"])
        self.assertTrue(report["routing_md_exists"])

        # Source suite at REPO_ROOT remains completely intact
        self.assertTrue((REPO_ROOT / "tests/fixtures/wizard-bench").is_dir())
        self.assertTrue((REPO_ROOT / "tests/test_wizard_bench.py").is_file())

        # Fingerprint in result records the source suite identity
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        self.assertIn("suite_identity", result)
        self.assertTrue(len(result["suite_identity"]) > 0)
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

    def test_reference_oracle_off_topic_discloses_no_hidden_requirement(self) -> None:
        """Real reference oracle: off-topic question leaks no hidden artifact, option, or subcommand."""
        cases = [
            ("bookmark-manager", "What is the entrypoint file name?", "python3 bookmarks.py", ["bookmarks.json", "add", "search"]),
            ("expense-tracker", "What is the entrypoint script called?", "python3 expenses.py", ["expenses.csv", "summary"]),
            ("log-analyzer", "What entrypoint filename is required?", "python3 logparser.py", ["--min-status", "--json", "Common Log Format"]),
        ]
        for scenario_id, on_topic, expected_entrypoint, leaked in cases:
            scenario_file = REPO_ROOT / "tests/fixtures/wizard-bench" / scenario_id / "scenario.json"
            cmd = [sys.executable, str(ORACLE), "--scenario", str(scenario_file)]

            on_topic_reply = subprocess.run(cmd, input=on_topic, text=True, capture_output=True).stdout
            self.assertIn(expected_entrypoint, on_topic_reply)

            off_topic_reply = subprocess.run(cmd, input="quantum banana zebra?", text=True, capture_output=True).stdout
            for leak in leaked:
                self.assertNotIn(leak, off_topic_reply, f"{scenario_id}: off-topic reply leaked {leak!r}")


    def test_wizard_bench_cli_help_works_from_arbitrary_cwd(self) -> None:
        res = subprocess.run(
            [sys.executable, str(RUNNER), "--help"],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("--agent-command", res.stdout)
        self.assertIn("--scenarios-dir", res.stdout)

if __name__ == "__main__":
    unittest.main()
