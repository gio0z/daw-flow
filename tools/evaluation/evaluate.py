#!/usr/bin/env python3
"""Run small DAW task fixtures through an explicitly supplied agent command.

This opt-in runner writes retained evidence and executes local processes. It is
separate from the read-only route and contract validators, and is not a sandbox.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from scripts.package_layout import REQUIRED_DIRS, REQUIRED_FILES, operational_entries
except ImportError:
    from package_layout import REQUIRED_DIRS, REQUIRED_FILES, operational_entries

COPY_IGNORE_PATTERNS = (".git", "__pycache__", "*.pyc", ".pytest_cache", ".venv", ".DS_Store")
CASES = ("patch", "review", "cli", "status")
PATCH_SOURCE = '''import argparse


def add(left, right):
    return left - right


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("left", type=int)
    parser.add_argument("right", type=int)
    args = parser.parse_args()
    print(add(args.left, args.right))
'''
REVIEW_SOURCE = '''_cache = {}


def get_report(customer_id, compute):
    if "report" not in _cache:
        _cache["report"] = compute(customer_id)
    return _cache["report"]
'''
PATCH_BEHAVIOR_CHECK = '''import importlib.util
import sys

spec = importlib.util.spec_from_file_location("calculator", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
for left, right, expected in [(2, 3, 5), (-4, 1, -3), (0, 0, 0), (5, -7, -2)]:
    actual = module.add(left, right)
    if actual != expected:
        raise AssertionError(f"add({left}, {right}): expected {expected}, observed {actual}")
print("4 public add behavior checks passed")
'''
STATUS_CONFIG = """<!-- daw-config:start -->

## DAW Configuration

- schema: 1
- daw_version: 0.5.0
- spec_dir: docs/specs
- test_command: python3 -m unittest
- lint_command: daw-eval-missing-lint run
- build_command: none
- workspace: in-place
- high_risk_paths: none
- issue_tracker: none
- default_branch: main
- commit_convention: conventional
- pr_template: none
- ci_checks: none
- release_process: none
- branch_pattern: none

<!-- daw-config:end -->
"""


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def snapshot(root: Path) -> dict[str, Any]:
    """Record bytes, links, modes and mtimes without following directory links."""
    records: dict[str, Any] = {}
    for directory, directories, files in os.walk(root, followlinks=False):
        base = Path(directory)
        for path in [base, *(base / name for name in sorted(directories + files))]:
            key = path.relative_to(root).as_posix()
            if key in records:
                continue
            stat = path.lstat()
            entry: dict[str, Any] = {"mode": stat.st_mode, "mtime_ns": stat.st_mtime_ns}
            if path.is_symlink():
                entry.update(kind="symlink", target=os.readlink(path))
            elif path.is_dir():
                entry.update(kind="directory")
            else:
                entry.update(kind="file", sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            records[key] = entry
    return records


def changed_paths(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    return sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))


def stage_suite(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    ignored = shutil.ignore_patterns(*COPY_IGNORE_PATTERNS)
    for entry in operational_entries(source):
        if not entry.exists() and not entry.is_symlink():
            continue
        rel = entry.relative_to(source)
        target = destination / rel
        if entry.is_symlink():
            target.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(os.readlink(entry), target)
        elif entry.is_dir():
            shutil.copytree(entry, target, symlinks=True, ignore=ignored)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(entry, target, follow_symlinks=False)


def suite_identity(root: Path) -> dict[str, Any]:
    """Identify copied distributable bytes without depending on Git or mtimes."""
    records = {}
    ignored = shutil.ignore_patterns(*COPY_IGNORE_PATTERNS)
    for entry in operational_entries(root):
        if not entry.exists() and not entry.is_symlink():
            continue
        candidates = [entry]
        if entry.is_dir() and not entry.is_symlink():
            candidates = []
            for directory, directories, files in os.walk(entry, followlinks=False):
                excluded = ignored(directory, directories + files)
                directories[:] = sorted(item for item in directories if item not in excluded)
                candidates.extend(Path(directory) / item for item in sorted(files) if item not in excluded)
                candidates.extend(Path(directory) / item for item in sorted(directories) if (Path(directory) / item).is_symlink())
        for path in candidates:
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                records[relative] = {"symlink": os.readlink(path)}
            else:
                records[relative] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest_path = root / "references" / "suite-manifest.json"
    manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest() if manifest_path.is_file() else None
    return {"version": (root / "VERSION").read_text(encoding="utf-8").strip(),
            "manifest_sha256": manifest_sha,
            "payload_sha256": hashlib.sha256(encoded).hexdigest(), "file_count": len(records)}


def prepare_case(workspace: Path, case: str, mode: str, source: Path) -> tuple[str, Path | None]:
    workspace.mkdir()
    suite_root: Path | None = None
    if mode == "skill" or case in ("cli", "status"):
        location = ".agents/skills/deterministic-agentic-workflow" if mode == "skill" else "tools/daw"
        suite_root = workspace / location
        stage_suite(source, suite_root)
    if case == "patch":
        (workspace / "calculator.py").write_text(PATCH_SOURCE, encoding="utf-8")
        task = (
            "Fix calculator.py so add(left, right) computes addition. Supplied observation: "
            "add(2, 3) currently returns -1 instead of 5. Preserve the integer command line "
            "interface and handle negative operands. Add useful tests if needed, verify the "
            "public function and CLI, and report actual evidence. Do not create specification "
            "documents, add dependencies, or make commits."
        )
    elif case == "review":
        (workspace / "report.py").write_text(REVIEW_SOURCE, encoding="utf-8")
        (workspace / "README.md").write_text(
            "Reports for different customers must remain separate. Repeated requests for "
            "the same customer must reuse its report.\n", encoding="utf-8"
        )
        task = (
            "Review report.py against README.md. This is read-only: do not write files, "
            "run workspace scripts, or repair the code. Explain any concrete requirement "
            "violation and confidentiality impact with file/line evidence. Distinguish "
            "limited security triage from a completed full technical audit."
        )
    elif case == "status":
        (workspace / "AGENTS.md").write_text(STATUS_CONFIG, encoding="utf-8")
        (workspace / "docs" / "specs").mkdir(parents=True)
        task = "/skill:deterministic-agentic-workflow cek status dong"
    else:
        task = (
            f"Verify the CLI at {suite_root / 'scripts/route.py'}. Before running checks, "
            "state that missing arguments should exit 2 with a usage diagnostic and "
            "--check-suite should exit 0 with status ready. Run both commands using Python, "
            "report their actual outputs and exit codes, and decide whether each expectation "
            "passed. Do not modify the suite."
        )
    if mode == "skill" and case != "status":
        module = {"patch": "daw-build then daw-verify", "review": "daw-review", "cli": "daw-verify"}[case]
        task = (
            "Use the complete installed deterministic-agentic-workflow suite at "
            f"{suite_root / 'SKILL.md'}; select {module} for this task. " + task
        )
    return task + "\n", suite_root


def run_process(argv: list[str], cwd: Path, prefix: Path, timeout: float, stdin: bytes | None = None) -> dict[str, Any]:
    started = time.monotonic()
    result: dict[str, Any] = {"argv": argv, "cwd": str(cwd), "exit_code": None, "timed_out": False}
    stdout_path = prefix.with_suffix(".stdout.txt")
    stderr_path = prefix.with_suffix(".stderr.txt")
    result.update(stdout=str(stdout_path), stderr=str(stderr_path))
    try:
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            process = subprocess.Popen(
                argv, cwd=cwd, stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                stdout=stdout, stderr=stderr, shell=False, start_new_session=os.name == "posix",
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            try:
                process.communicate(input=stdin, timeout=timeout)
            except subprocess.TimeoutExpired:
                result["timed_out"] = True
                try:
                    if os.name == "posix":
                        os.killpg(process.pid, signal.SIGKILL)
                    else:
                        process.kill()
                except ProcessLookupError:
                    pass
                process.communicate()
            result["exit_code"] = process.returncode
    except OSError as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    result["duration_seconds"] = round(time.monotonic() - started, 3)
    return result


def observe_check(name: str, argv: list[str], workspace: Path, run_dir: Path,
                  expected_exit: int, stdout_contains: str | None = None,
                  stderr_contains: str | None = None, stdout_equals: str | None = None) -> dict[str, Any]:
    observed = run_process(argv, workspace, run_dir / name, timeout=10)
    stdout = Path(observed["stdout"]).read_text(encoding="utf-8", errors="replace")
    stderr = Path(observed["stderr"]).read_text(encoding="utf-8", errors="replace")
    passed = observed["exit_code"] == expected_exit and not observed["timed_out"] and "error" not in observed
    passed = passed and (stdout_contains is None or stdout_contains in stdout)
    passed = passed and (stderr_contains is None or stderr_contains in stderr)
    passed = passed and (stdout_equals is None or stdout == stdout_equals)
    return {"name": name, "observer": "grader", "expected_exit_code": expected_exit,
            "stdout_contains": stdout_contains, "stderr_contains": stderr_contains, "stdout_equals": stdout_equals,
            "status": "pass" if passed else "fail", "observed": observed}


def grade(case: str, workspace: Path, run_dir: Path, suite_root: Path | None,
          before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    changes = changed_paths(before, after)
    if case == "review":
        return [{"name": "read_only_workspace", "status": "pass" if not changes else "fail",
                 "changed_paths": changes, "observer": "grader"}]
    checks: list[dict[str, Any]] = []
    if case == "patch":
        unexpected = [path for path in changes if path != "." and path != "calculator.py"
                      and path not in ("tests", "__pycache__", ".pytest_cache")
                      and not path.startswith(("tests/", "__pycache__/", ".pytest_cache/"))]
        checks.append({"name": "bounded_patch_scope", "status": "pass" if not unexpected else "fail",
                       "unexpected_changed_paths": unexpected, "observer": "grader"})
        checks.append(observe_check(
            "public_add_behavior", [sys.executable, "-I", "-c", PATCH_BEHAVIOR_CHECK, str(workspace / "calculator.py")],
            workspace, run_dir, 0, stdout_contains="4 public add behavior checks passed",
        ))
        checks.append(observe_check(
            "calculator_cli", [sys.executable, "-I", str(workspace / "calculator.py"), "-4", "1"],
            workspace, run_dir, 0, stdout_equals="-3\n",
        ))
    elif case == "status":
        checks.append({"name": "unchanged_workspace", "status": "pass" if not changes else "fail",
                       "changed_paths": changes, "observer": "grader"})
        script = str(suite_root / "scripts/validate.py")
        observed = run_process([sys.executable, script, "status", "--project-root", ".", "--format", "json"],
                               workspace, run_dir / "status_structure", timeout=10)
        stdout = Path(observed["stdout"]).read_text(encoding="utf-8", errors="replace")
        try:
            envelope = json.loads(stdout)
        except json.JSONDecodeError:
            envelope = {}
        findings = envelope.get("findings") if isinstance(envelope, dict) else None
        structure_ok = (
            observed["exit_code"] == 1 and not observed["timed_out"] and "error" not in observed
            and envelope.get("check") == "status"
            and envelope.get("valid") is False
            and envelope.get("summary", {}).get("config") == "invalid"
            and envelope.get("recommended_route") == "setup"
            and isinstance(findings, list)
            and len(findings) == 1
            and findings[0].get("severity") == "error"
            and findings[0].get("code") == "config_command_unresolved"
            and findings[0].get("path") == "config:lint_command"
        )
        checks.append({"name": "status_structure", "observer": "grader", "expected_exit_code": 1,
                       "expected_summary_config": "invalid", "expected_recommended_route": "setup",
                       "expected_finding_code": "config_command_unresolved",
                       "expected_finding_path": "config:lint_command",
                       "status": "pass" if structure_ok else "fail", "observed": observed})
    else:
        checks.append({"name": "unmodified_suite", "status": "pass" if not changes else "fail",
                       "changed_paths": changes, "observer": "grader"})
        script = str(suite_root / "scripts/route.py")
        checks.append(observe_check(
            "cli_rejection", [sys.executable, script], workspace, run_dir, 2,
            stderr_contains="REQUEST filepath required unless --check-suite is specified.",
        ))
        checks.append(observe_check(
            "cli_suite_ready", [sys.executable, script, "--check-suite"], workspace, run_dir, 0,
            stdout_contains='"status": "ready"',
        ))
    return checks


def run_case(source: Path, output: Path, case: str, mode: str, repetition: int,
             command: list[str], timeout: float, agent_label: str) -> dict[str, Any]:
    run_dir = output / f"{case}-{mode}-{repetition:03d}"
    run_dir.mkdir()
    write_json(run_dir / "metadata.json", {
        "case": case, "mode": mode, "repetition": repetition, "agent_label": agent_label,
        "source_suite": str(source), "started_at": datetime.now(timezone.utc).isoformat(),
    })
    workspace = run_dir / "workspace"
    prompt, suite_root = prepare_case(workspace, case, mode, source)
    identity = suite_identity(suite_root if suite_root else source)
    write_json(run_dir / "metadata.json", {
        "case": case, "mode": mode, "repetition": repetition, "agent_label": agent_label,
        "source_suite": str(source), "suite_identity": identity,
        "identity_origin": "staged_bundle" if suite_root else "source_reference",
        "started_at": datetime.now(timezone.utc).isoformat(),
    })
    prompt_file = run_dir / "prompt.md"
    prompt_file.write_text(prompt, encoding="utf-8")
    substitutions = {"{workspace}": str(workspace), "{prompt_file}": str(prompt_file),
                     "{suite_root}": str(suite_root) if suite_root else ""}
    argv = [
        re.sub(r"\{(workspace|prompt_file|suite_root)\}", lambda m: substitutions[m.group(0)], argument)
        for argument in command
    ]
    before = snapshot(workspace)
    write_json(run_dir / "before.json", before)
    observed = run_process(argv, workspace, run_dir / "agent", timeout, prompt.encode("utf-8"))
    after = snapshot(workspace)
    write_json(run_dir / "after.json", after)
    try:
        checks = grade(case, workspace, run_dir, suite_root, before, after)
    except (OSError, ValueError) as exc:
        checks = [{"name": "grader", "status": "fail", "error": f"{type(exc).__name__}: {exc}"}]
    if observed["timed_out"]:
        status = "agent_timeout"
    elif observed["exit_code"] != 0:
        status = "agent_failed"
    elif not checks or any(check["status"] != "pass" for check in checks):
        status = "artifact_checks_failed"
    else:
        status = "artifact_checks_passed"
    result = {
        "schema_version": 1, "case": case, "mode": mode, "repetition": repetition,
        "status": status, "agent_label": agent_label, "source_suite": str(source),
        "suite_identity": identity,
        "workspace": str(workspace), "installed_suite": str(suite_root) if suite_root else None,
        "observed_agent_process": observed, "checks": checks,
        "human_review": {"status": "ungraded", "required": True,
                         "notes": "Inspect the transcript for reasoning, evidence and instruction adherence; grader checks do not prove the agent performed those checks."},
        "limitations": ["The runner is not a sandbox; host configuration, credentials and global skills are inherited.",
                        "Bare mode omits workspace-local DAW discovery, but global harness configuration can contaminate the control."],
    }
    write_json(run_dir / "result.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-command", required=True, help="JSON argv array; placeholders: {prompt_file}, {workspace}, {suite_root}. Prompt also arrives on stdin.")
    parser.add_argument("--output-dir", required=True, type=Path, help="New directory outside the source suite; evidence is retained.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="Suite root directory containing operational files (default: repository root)")
    parser.add_argument("--case", choices=("all", *CASES), default="all")
    parser.add_argument("--mode", choices=("skill", "bare", "both"), default="skill")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--agent-label", default="unspecified", help="Record the client, version, model and configuration used; not inferred.")
    args = parser.parse_args(argv)
    try:
        command = json.loads(args.agent_command)
    except json.JSONDecodeError:
        parser.error("--agent-command must be a JSON argv array")
    if not isinstance(command, list) or not command or any(not isinstance(part, str) or not part or "\x00" in part for part in command):
        parser.error("--agent-command must be a nonempty array of nonempty strings without NUL bytes")
    if not 1 <= args.runs <= 20 or not 0 < args.timeout <= 3600:
        parser.error("--runs must be 1..20 and --timeout must be greater than 0 and at most 3600 seconds")
    source = args.root.resolve()
    output = args.output_dir.resolve()
    if output == source or source in output.parents:
        parser.error("--output-dir must be outside the source suite")
    required = [source / f for f in REQUIRED_FILES] + [source / d for d in REQUIRED_DIRS]
    missing = [entry for entry in required if not entry.exists() and not entry.is_symlink()]
    if missing:
        parser.error(f"--root must contain the operational suite (missing: {', '.join(str(m.relative_to(source)) for m in missing)})")
    try:
        output.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        parser.error(f"cannot create a new output directory: {exc}")
    started = datetime.now(timezone.utc).isoformat()
    cases = CASES if args.case == "all" else (args.case,)
    modes = ("bare", "skill") if args.mode == "both" else (args.mode,)
    results = []
    for case in cases:
        for mode in modes:
            for repetition in range(1, args.runs + 1):
                try:
                    result = run_case(source, output, case, mode, repetition, command, args.timeout, args.agent_label)
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    result = {"schema_version": 1, "case": case, "mode": mode, "repetition": repetition,
                              "status": "runner_failed", "error": f"{type(exc).__name__}: {exc}",
                              "human_review": {"status": "ungraded", "required": True}}
                    write_json(output / f"{case}-{mode}-{repetition:03d}" / "result.json", result)
                results.append(result)
    summary = {"schema_version": 1, "started_at": started, "agent_label": args.agent_label,
               "configured_command": command, "results": results, "human_review_status": "ungraded",
               "status": "artifact_checks_passed" if all(result["status"] == "artifact_checks_passed" for result in results) else "artifact_checks_failed"}
    write_json(output / "summary.json", summary)
    print(json.dumps({"status": summary["status"], "summary": str(output / "summary.json"),
                      "runs": len(results), "human_review_status": "ungraded"}, indent=2))
    return 0 if summary["status"] == "artifact_checks_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
