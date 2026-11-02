#!/usr/bin/env python3
"""Run daw-wizard requirements interview and downstream build benchmarks.

This opt-in runner evaluates agents on greenfield requirements elicitation
and subsequent specification-driven implementation. It runs two arms:
1. 'wizard': Multi-turn interview where the agent may ask questions via
   .daw-interview/questions.md, answered by an oracle, producing specs in docs/specs/,
   followed by a downstream builder implementing the project from docs/specs/.
2. 'brief' (baseline): Downstream builder implements the project directly from the
   underspecified brief, without interview or specs.

All prompts, workspaces, transcripts, questions, answers, and evaluation checks are
retained in the output directory.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluate import (
    REQUIRED_PARTS,
    run_process,
    snapshot,
    stage_suite,
    suite_identity,
    write_json,
)

CHECKLIST_KEYS = (
    "goal",
    "scope",
    "inputs_outputs",
    "data_changes",
    "edge_cases",
    "acceptance_tests",
    "constraints",
    "no_change_list",
)

QUESTION_REGEX = re.compile(r"^\s*(?:\d+[\.\)]|[-*+])\s+")


def substitute_argv(argv: list[str], mapping: dict[str, str]) -> list[str]:
    pattern = re.compile(r"\{(" + "|".join(re.escape(k.strip("{}")) for k in mapping) + r")\}")
    return [pattern.sub(lambda m: mapping.get("{" + m.group(1) + "}", m.group(0)), arg) for arg in argv]


def count_questions(questions_text: str) -> int:
    lines = questions_text.splitlines()
    count = sum(1 for line in lines if QUESTION_REGEX.match(line))
    if count == 0 and questions_text.strip():
        # Fall back to counting non-empty lines that aren't headings
        count = sum(1 for line in lines if line.strip() and not line.strip().startswith("#"))
    return count if count > 0 else (1 if questions_text.strip() else 0)


def evaluate_judge(judge_data: Any, scenario: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(judge_data, dict):
        raise ValueError("Judge output must be a JSON object")
    if "elicited_requirement_ids" not in judge_data or not isinstance(judge_data["elicited_requirement_ids"], list):
        raise ValueError("Judge output missing 'elicited_requirement_ids' list")
    if any(not isinstance(x, str) for x in judge_data["elicited_requirement_ids"]):
        raise ValueError("'elicited_requirement_ids' items must be strings")
    if "redundant_question_count" not in judge_data or not isinstance(judge_data["redundant_question_count"], int):
        raise ValueError("Judge output missing integer 'redundant_question_count'")
    if "total_question_count" not in judge_data or not isinstance(judge_data["total_question_count"], int):
        raise ValueError("Judge output missing integer 'total_question_count'")
    if "checklist" not in judge_data or not isinstance(judge_data["checklist"], dict):
        raise ValueError("Judge output missing 'checklist' object")
    for key in CHECKLIST_KEYS:
        if key not in judge_data["checklist"] or not isinstance(judge_data["checklist"][key], bool):
            raise ValueError(f"Judge checklist missing or non-boolean key '{key}'")
    if "unsupported_claims" not in judge_data or not isinstance(judge_data["unsupported_claims"], list):
        raise ValueError("Judge output missing 'unsupported_claims' list")

    hidden_reqs = scenario.get("hidden_requirements", [])
    hidden_ids = {r["id"] for r in hidden_reqs if isinstance(r, dict) and "id" in r}
    elicited_set = set(judge_data["elicited_requirement_ids"])

    ire = len(elicited_set & hidden_ids) / len(hidden_ids) if hidden_ids else 0.0
    total_q = judge_data["total_question_count"]
    redundant_q = judge_data["redundant_question_count"]
    redundancy_ratio = redundant_q / total_q if total_q > 0 else 0.0
    checklist_score = sum(1 for key in CHECKLIST_KEYS if judge_data["checklist"][key] is True)
    fabrication_count = len(judge_data["unsupported_claims"])

    return {
        "status": "graded",
        "ire": round(ire, 4),
        "checklist_score": checklist_score,
        "redundancy_ratio": round(redundancy_ratio, 4),
        "fabrication_count": fabrication_count,
        "elicited_requirement_ids": sorted(list(elicited_set)),
        "raw": judge_data,
    }


def parse_acceptance_output(stdout_path: Path) -> tuple[list[dict[str, Any]], float]:
    if not stdout_path.is_file():
        return [], 0.0
    text = stdout_path.read_text(encoding="utf-8")
    checks = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            if isinstance(data, dict) and "check" in data:
                checks.append(data)
        except json.JSONDecodeError:
            continue
    if not checks:
        return [], 0.0
    passed = sum(1 for c in checks if c.get("status") == "pass")
    return checks, round(passed / len(checks), 4)


def run_scenario(
    source: Path,
    run_dir: Path,
    scenario_dir: Path,
    scenario_data: dict[str, Any],
    arm: str,
    repetition: int,
    agent_command: list[str],
    oracle_command: list[str] | None,
    judge_command: list[str] | None,
    timeout: float,
    max_turns: int,
    agent_label: str,
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc).isoformat()
    t_start = time.monotonic()
    scenario_id = scenario_data.get("id", scenario_dir.name)
    brief = scenario_data.get("brief", "")

    interview_duration = 0.0
    build_duration = 0.0
    grade_duration = 0.0
    judge_duration = 0.0

    turns_used = 0
    question_count = 0
    docs_produced: list[str] = []
    all_questions_text: list[str] = []

    status = "completed"
    error: str | None = None

    transcript_file = run_dir / "transcript.md"
    transcript = ""

    # Phase 1: Interview (wizard arm only)
    if arm == "wizard":
        interview_workspace = run_dir / "interview_workspace"
        interview_workspace.mkdir(parents=True, exist_ok=True)
        suite_root = interview_workspace / ".agents/skills/deterministic-agentic-workflow"
        stage_suite(source, suite_root)

        turn = 1
        while turn <= max_turns:
            turns_used = turn
            turn_prompt = (
                f"# Project Brief\n{brief}\n\n"
                f"# Transcript\n{transcript.strip() if transcript.strip() else '(No interview history yet.)'}\n\n"
                "# Protocol\n"
                "Use daw-wizard. If you need answers, write your questions as a numbered markdown list "
                "to `.daw-interview/questions.md` and stop. When done, write the specification documents "
                "under `docs/specs/` and do NOT write questions.md.\n"
            )
            prompt_file = run_dir / f"turn_{turn}_prompt.md"
            prompt_file.write_text(turn_prompt, encoding="utf-8")

            subs = {
                "{prompt_file}": str(prompt_file),
                "{workspace}": str(interview_workspace),
                "{suite_root}": str(suite_root),
            }
            argv = substitute_argv(agent_command, subs)

            t0 = time.monotonic()
            agent_res = run_process(
                argv,
                interview_workspace,
                run_dir / f"turn_{turn}_agent",
                timeout=timeout,
                stdin=turn_prompt.encode("utf-8"),
            )
            interview_duration += time.monotonic() - t0

            if agent_res.get("timed_out"):
                status = "agent_timeout"
                error = f"Agent timed out on interview turn {turn}"
                break
            if agent_res.get("exit_code") != 0:
                status = "agent_failed"
                error = f"Agent exited with code {agent_res.get('exit_code')} on interview turn {turn}"
                break

            questions_path = interview_workspace / ".daw-interview/questions.md"
            if questions_path.is_file():
                q_text = questions_path.read_text(encoding="utf-8")
                (run_dir / f"turn_{turn}_questions.md").write_text(q_text, encoding="utf-8")
                question_count += count_questions(q_text)
                all_questions_text.append(q_text)
                questions_path.unlink()

                daw_dir = interview_workspace / ".daw-interview"
                if daw_dir.is_dir():
                    try:
                        daw_dir.rmdir()
                    except OSError:
                        pass

                if not oracle_command:
                    status = "runner_failed"
                    error = "Missing oracle command for wizard arm interview"
                    break

                oracle_subs = {
                    "{questions_file}": str(run_dir / f"turn_{turn}_questions.md"),
                    "{scenario_file}": str(scenario_dir / "scenario.json"),
                    "{transcript_file}": str(transcript_file),
                }
                oracle_argv = substitute_argv(oracle_command, oracle_subs)
                oracle_res = run_process(
                    oracle_argv,
                    interview_workspace,
                    run_dir / f"turn_{turn}_oracle",
                    timeout=60,
                    stdin=q_text.encode("utf-8"),
                )

                if oracle_res.get("timed_out") or oracle_res.get("exit_code") != 0:
                    status = "runner_failed"
                    error = f"Oracle failed on turn {turn}: exit {oracle_res.get('exit_code')}"
                    break

                oracle_stdout_file = Path(oracle_res["stdout"])
                oracle_answer = (
                    oracle_stdout_file.read_text(encoding="utf-8").strip() if oracle_stdout_file.is_file() else ""
                )
                (run_dir / f"turn_{turn}_answer.md").write_text(oracle_answer, encoding="utf-8")

                transcript += (
                    f"\n\n## Turn {turn} Questions\n{q_text.strip()}\n\n## Turn {turn} Answers\n{oracle_answer.strip()}\n"
                )
                transcript_file.write_text(transcript.strip() + "\n", encoding="utf-8")

                if turn == max_turns:
                    status = "interview_turn_limit"
                    break
                turn += 1
                continue
            else:
                specs_dir = interview_workspace / "docs/specs"
                specs = [p for p in specs_dir.rglob("*") if p.is_file()] if specs_dir.is_dir() else []
                if specs:
                    dest_docs = run_dir / "docs"
                    shutil.copytree(specs_dir, dest_docs)
                    docs_produced = sorted([p.relative_to(dest_docs).as_posix() for p in dest_docs.rglob("*") if p.is_file()])
                    break
                else:
                    status = "interview_failed"
                    error = "Agent stopped without producing questions or docs/specs"
                    break

        transcript_file.write_text(transcript.strip() + "\n", encoding="utf-8")

    # If interview did not succeed, do not run build
    if status in ("agent_timeout", "agent_failed", "runner_failed", "interview_turn_limit", "interview_failed"):
        completed_at = datetime.now(timezone.utc).isoformat()
        total_duration = time.monotonic() - t_start
        result: dict[str, Any] = {
            "schema_version": 1,
            "scenario": scenario_id,
            "arm": arm,
            "repetition": repetition,
            "agent_label": agent_label,
            "status": status,
            "turns_used": turns_used,
            "question_count": question_count,
            "docs_produced": docs_produced,
            "pass_rate": 0.0,
            "checks": [],
            "judge": "ungraded",
            "timing": {
                "interview_seconds": round(interview_duration, 3),
                "build_seconds": 0.0,
                "grading_seconds": 0.0,
                "total_seconds": round(total_duration, 3),
            },
            "suite_identity": suite_identity(source),
            "started_at": started_at,
            "completed_at": completed_at,
        }
        if error:
            result["error"] = error
        write_json(run_dir / "result.json", result)
        return result

    # Phase 2: Build (both arms)
    build_workspace = run_dir / "build_workspace"
    build_workspace.mkdir(parents=True, exist_ok=True)

    if arm == "wizard":
        dest_specs = build_workspace / "docs/specs"
        if (run_dir / "docs").is_dir():
            shutil.copytree(run_dir / "docs", dest_specs)
        build_prompt = (
            "Implement the project described in docs/specs/. "
            "Put the implementation in the workspace root. Do not ask questions.\n"
        )
    else:
        build_prompt = (
            f"Implement the project described in this brief:\n\n{brief}\n\n"
            "Put the implementation in the workspace root. Do not ask questions.\n"
        )

    build_prompt_file = run_dir / "build_prompt.md"
    build_prompt_file.write_text(build_prompt, encoding="utf-8")

    build_subs = {
        "{prompt_file}": str(build_prompt_file),
        "{workspace}": str(build_workspace),
        "{suite_root}": "",
    }
    build_argv = substitute_argv(agent_command, build_subs)

    t0 = time.monotonic()
    build_res = run_process(
        build_argv,
        build_workspace,
        run_dir / "builder",
        timeout=timeout,
        stdin=build_prompt.encode("utf-8"),
    )
    build_duration = time.monotonic() - t0

    if build_res.get("timed_out"):
        status = "agent_timeout"
        error = "Builder agent timed out"
    elif build_res.get("exit_code") != 0:
        status = "agent_failed"
        error = f"Builder agent exited with code {build_res.get('exit_code')}"

    # Phase 3: Grade (acceptance.py)
    acceptance_script = scenario_dir / "acceptance.py"
    t0 = time.monotonic()
    grade_res = run_process(
        [sys.executable, str(acceptance_script), str(build_workspace)],
        build_workspace,
        run_dir / "acceptance",
        timeout=60,
    )
    grade_duration = time.monotonic() - t0

    checks, pass_rate = parse_acceptance_output(Path(grade_res["stdout"]))

    # Phase 4: Optional judge
    judge_data: Any = "ungraded"
    if judge_command and arm == "wizard":
        specs_dir = run_dir / "docs"
        specs_dir.mkdir(parents=True, exist_ok=True)
        if not transcript_file.is_file():
            transcript_file.write_text("", encoding="utf-8")

        judge_subs = {
            "{scenario_file}": str(scenario_dir / "scenario.json"),
            "{transcript_file}": str(transcript_file),
            "{specs_dir}": str(specs_dir),
        }
        judge_argv = substitute_argv(judge_command, judge_subs)

        t0 = time.monotonic()
        judge_res = run_process(judge_argv, run_dir, run_dir / "judge", timeout=timeout)
        judge_duration = time.monotonic() - t0

        if judge_res.get("timed_out") or judge_res.get("exit_code") != 0:
            judge_data = {
                "status": "error",
                "error": f"Judge process exited with code {judge_res.get('exit_code')} (timed_out={judge_res.get('timed_out')})",
            }
        else:
            j_stdout_file = Path(judge_res["stdout"])
            j_raw_text = j_stdout_file.read_text(encoding="utf-8").strip() if j_stdout_file.is_file() else ""
            try:
                parsed_judge = json.loads(j_raw_text)
                judge_data = evaluate_judge(parsed_judge, scenario_data)
            except Exception as exc:
                judge_data = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

    total_duration = time.monotonic() - t_start
    completed_at = datetime.now(timezone.utc).isoformat()

    result = {
        "schema_version": 1,
        "scenario": scenario_id,
        "arm": arm,
        "repetition": repetition,
        "agent_label": agent_label,
        "status": status,
        "turns_used": turns_used,
        "question_count": question_count,
        "docs_produced": docs_produced,
        "pass_rate": pass_rate,
        "checks": checks,
        "judge": judge_data,
        "timing": {
            "interview_seconds": round(interview_duration, 3),
            "build_seconds": round(build_duration, 3),
            "grading_seconds": round(grade_duration, 3),
            "judge_seconds": round(judge_duration, 3),
            "total_seconds": round(total_duration, 3),
        },
        "suite_identity": suite_identity(source),
        "started_at": started_at,
        "completed_at": completed_at,
    }
    if error:
        result["error"] = error
    write_json(run_dir / "result.json", result)
    return result


def aggregate_summary(results: list[dict[str, Any]], scenarios: list[str]) -> dict[str, Any]:
    arms_data: dict[str, Any] = {}
    for arm in ("wizard", "brief"):
        arm_results = [r for r in results if r.get("arm") == arm]
        if not arm_results:
            continue
        pass_rates = [r.get("pass_rate", 0.0) for r in arm_results]
        mean_pass_rate = round(sum(pass_rates) / len(pass_rates), 4) if pass_rates else 0.0
        turns = [r.get("turns_used", 0) for r in arm_results]
        mean_turns = round(sum(turns) / len(turns), 2) if turns else 0.0
        questions = [r.get("question_count", 0) for r in arm_results]
        mean_questions = round(sum(questions) / len(questions), 2) if questions else 0.0

        # Judge metrics aggregation
        graded_judges = [r["judge"] for r in arm_results if isinstance(r.get("judge"), dict) and r["judge"].get("status") == "graded"]
        judge_errors = [r["judge"] for r in arm_results if isinstance(r.get("judge"), dict) and r["judge"].get("status") == "error"]

        judge_summary: Any
        if graded_judges:
            judge_summary = {
                "status": "graded",
                "mean_ire": round(sum(j["ire"] for j in graded_judges) / len(graded_judges), 4),
                "mean_checklist_score": round(sum(j["checklist_score"] for j in graded_judges) / len(graded_judges), 2),
                "mean_redundancy_ratio": round(sum(j["redundancy_ratio"] for j in graded_judges) / len(graded_judges), 4),
                "mean_fabrication_count": round(sum(j["fabrication_count"] for j in graded_judges) / len(graded_judges), 2),
            }
        elif judge_errors:
            judge_summary = {"status": "error", "error": judge_errors[0].get("error", "Judge error")}
        else:
            judge_summary = "ungraded"

        arms_data[arm] = {
            "runs": len(arm_results),
            "mean_pass_rate": mean_pass_rate,
            "mean_turns": mean_turns,
            "mean_questions": mean_questions,
            "judge": judge_summary,
        }

    return {
        "schema_version": 1,
        "scenarios": scenarios,
        "arms": arms_data,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="DAW wizard interview benchmark runner")
    parser.add_argument("--agent-command", required=True, help="Agent command as JSON argv array")
    parser.add_argument("--oracle-command", help="Oracle command as JSON argv array (required for wizard arm)")
    parser.add_argument("--judge-command", help="Judge command as JSON argv array (optional)")
    parser.add_argument("--output-dir", required=True, type=Path, help="New directory for retained evidence")
    parser.add_argument("--scenario", default="all", help="Scenario ID or 'all' (default: all)")
    parser.add_argument(
        "--scenarios-dir",
        default="references/wizard-bench",
        type=Path,
        help="Path to scenarios directory (default: references/wizard-bench)",
    )
    parser.add_argument("--arm", choices=["wizard", "brief", "both"], default="both", help="Evaluation arm")
    parser.add_argument("--runs", type=int, default=1, help="Repetitions per scenario arm (1..10)")
    parser.add_argument("--timeout", type=float, default=300.0, help="Timeout in seconds per agent invocation (1..3600)")
    parser.add_argument("--max-turns", type=int, default=6, help="Max interview turns (1..12)")
    parser.add_argument("--agent-label", default="unlabeled-agent", help="Label for agent configuration")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="Suite root directory")

    args = parser.parse_args()

    # Validate agent command
    try:
        agent_command = json.loads(args.agent_command)
    except json.JSONDecodeError:
        parser.error("--agent-command must be a JSON argv array")
    if (
        not isinstance(agent_command, list)
        or not agent_command
        or any(not isinstance(p, str) or not p or "\x00" in p for p in agent_command)
    ):
        parser.error("--agent-command must be a nonempty array of nonempty strings without NUL bytes")

    # Validate arm and oracle command
    oracle_command: list[str] | None = None
    if args.arm in ("wizard", "both"):
        if not args.oracle_command:
            parser.error("--oracle-command is required for wizard arm")
        try:
            oracle_command = json.loads(args.oracle_command)
        except json.JSONDecodeError:
            parser.error("--oracle-command must be a JSON argv array")
        if (
            not isinstance(oracle_command, list)
            or not oracle_command
            or any(not isinstance(p, str) or not p or "\x00" in p for p in oracle_command)
        ):
            parser.error("--oracle-command must be a nonempty array of nonempty strings without NUL bytes")

    # Validate judge command
    judge_command: list[str] | None = None
    if args.judge_command:
        try:
            judge_command = json.loads(args.judge_command)
        except json.JSONDecodeError:
            parser.error("--judge-command must be a JSON argv array")
        if (
            not isinstance(judge_command, list)
            or not judge_command
            or any(not isinstance(p, str) or not p or "\x00" in p for p in judge_command)
        ):
            parser.error("--judge-command must be a nonempty array of nonempty strings without NUL bytes")

    if not (1 <= args.runs <= 10):
        parser.error("--runs must be between 1 and 10")
    if not (0 < args.timeout <= 3600):
        parser.error("--timeout must be between 1 and 3600 seconds")
    if not (1 <= args.max_turns <= 12):
        parser.error("--max-turns must be between 1 and 12")

    source = args.root.resolve()
    output = args.output_dir.resolve()

    if output == source or source in output.parents:
        parser.error("--output-dir must be outside the source suite")
    if any(not (source / part).exists() for part in REQUIRED_PARTS):
        parser.error("--root must contain the complete distributable suite")

    try:
        output.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        parser.error(f"cannot create a new output directory: {exc}")

    scenarios_base = args.scenarios_dir if args.scenarios_dir.is_absolute() else (source / args.scenarios_dir)
    scenarios_base = scenarios_base.resolve()
    if not scenarios_base.is_dir():
        parser.error(f"--scenarios-dir '{scenarios_base}' does not exist or is not a directory")

    discovered: list[tuple[Path, dict[str, Any]]] = []
    for entry in sorted(scenarios_base.iterdir()):
        if entry.is_dir() and (entry / "scenario.json").is_file() and (entry / "acceptance.py").is_file():
            try:
                sc_data = json.loads((entry / "scenario.json").read_text(encoding="utf-8"))
                discovered.append((entry, sc_data))
            except Exception:
                pass

    if args.scenario != "all":
        discovered = [
            (d, s) for (d, s) in discovered if s.get("id") == args.scenario or d.name == args.scenario
        ]
        if not discovered:
            parser.error(f"scenario '{args.scenario}' not found in {scenarios_base}")

    if not discovered:
        parser.error(f"no valid scenarios found in {scenarios_base}")

    arms = ["wizard", "brief"] if args.arm == "both" else [args.arm]
    results: list[dict[str, Any]] = []

    for sc_dir, sc_data in discovered:
        for arm in arms:
            for repetition in range(1, args.runs + 1):
                sc_id = sc_data.get("id", sc_dir.name)
                run_dir = output / f"{sc_id}-{arm}-{repetition:03d}"
                run_dir.mkdir(parents=True, exist_ok=False)
                try:
                    res = run_scenario(
                        source=source,
                        run_dir=run_dir,
                        scenario_dir=sc_dir,
                        scenario_data=sc_data,
                        arm=arm,
                        repetition=repetition,
                        agent_command=agent_command,
                        oracle_command=oracle_command,
                        judge_command=judge_command,
                        timeout=args.timeout,
                        max_turns=args.max_turns,
                        agent_label=args.agent_label,
                    )
                except Exception as exc:
                    res = {
                        "schema_version": 1,
                        "scenario": sc_id,
                        "arm": arm,
                        "repetition": repetition,
                        "agent_label": args.agent_label,
                        "status": "runner_failed",
                        "error": f"{type(exc).__name__}: {exc}",
                        "pass_rate": 0.0,
                        "judge": "ungraded",
                    }
                    write_json(run_dir / "result.json", res)
                results.append(res)

    summary = aggregate_summary(results, [s.get("id", d.name) for d, s in discovered])
    write_json(output / "summary.json", summary)

    # Print compact JSON summary
    compact = {
        "scenarios": summary["scenarios"],
        "arms": {
            arm: {
                "runs": data["runs"],
                "mean_pass_rate": data["mean_pass_rate"],
                "mean_turns": data["mean_turns"],
                "judge": data["judge"],
            }
            for arm, data in summary["arms"].items()
        },
    }
    sys.stdout.write(json.dumps(compact, indent=2) + "\n")

    failures = sum(1 for r in results if r.get("status") in ("runner_failed", "agent_failed", "agent_timeout"))
    return 1 if failures > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
