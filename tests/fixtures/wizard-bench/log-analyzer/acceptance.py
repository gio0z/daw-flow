#!/usr/bin/env python3
"""Acceptance test suite for log-analyzer scenario."""

import json
import subprocess
import sys
from pathlib import Path


def emit_result(check: str, status: str, detail: str) -> None:
    print(json.dumps({"check": check, "status": status, "detail": detail}))


def run_cli(entrypoint: Path, args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(entrypoint)] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=10,
    )


def main() -> int:
    if len(sys.argv) < 2:
        emit_result("setup", "fail", "Usage: acceptance.py <workspace>")
        return 1

    workspace = Path(sys.argv[1]).resolve()
    entrypoint = workspace / "logparser.py"

    all_checks = [
        "R1_entrypoint_exists",
        "R2_clf_parsing_and_skip",
        "R3_cli_arguments",
        "R4_min_status_filter_and_validation",
        "R5_text_output_format",
        "R6_json_output_format",
        "R7_missing_and_empty_file_handling",
    ]

    if not entrypoint.is_file():
        for check in all_checks:
            emit_result(check, "fail", f"Missing required entrypoint: {entrypoint.name}")
        return 1

    failures = 0

    # R7: Missing file and empty file handling
    missing_file = workspace / "nonexistent.log"
    empty_file = workspace / "empty.log"
    empty_file.write_text("", encoding="utf-8")

    try:
        proc_missing = run_cli(entrypoint, [str(missing_file)], cwd=workspace)
        proc_empty_txt = run_cli(entrypoint, [str(empty_file)], cwd=workspace)
        proc_empty_json = run_cli(entrypoint, [str(empty_file), "--json"], cwd=workspace)

        missing_ok = proc_missing.returncode == 1 and "Error: file not found" in proc_missing.stderr
        empty_txt_ok = (
            proc_empty_txt.returncode == 0
            and "Total Requests: 0" in proc_empty_txt.stdout
            and "Total Bytes: 0" in proc_empty_txt.stdout
            and "Error Rate: 0.0%" in proc_empty_txt.stdout
        )
        empty_json_ok = False
        if proc_empty_json.returncode == 0:
            try:
                ej = json.loads(proc_empty_json.stdout)
                if (
                    ej.get("total_requests") == 0
                    and ej.get("total_bytes") == 0
                    and ej.get("error_rate") == 0.0
                    and ej.get("top_paths") == []
                ):
                    empty_json_ok = True
            except Exception:
                pass

        if missing_ok and empty_txt_ok and empty_json_ok:
            emit_result("R7_missing_and_empty_file_handling", "pass", "Missing and empty logs handled cleanly")
        else:
            failures += 1
            emit_result(
                "R7_missing_and_empty_file_handling",
                "fail",
                f"missing_ok={missing_ok}, empty_txt_ok={empty_txt_ok}, empty_json_ok={empty_json_ok}",
            )
    except Exception as exc:
        failures += 1
        emit_result("R7_missing_and_empty_file_handling", "fail", str(exc))

    # R1: Entry point exists
    emit_result("R1_entrypoint_exists", "pass", "logparser.py exists in workspace")

    # Prepare sample log file with:
    # - 1 corrupt / non-CLF line (should be skipped)
    # - 1 line with '-' bytes
    # - multiple status codes (200, 301, 404, 500)
    #
    # Sample lines:
    # 127.0.0.1 - - [10/Oct/2026:13:55:36 +0000] "GET /home HTTP/1.1" 200 1200
    # 127.0.0.1 - - [10/Oct/2026:13:55:37 +0000] "GET /about HTTP/1.1" 200 450
    # THIS IS A CORRUPT UNPARSEABLE LINE
    # 192.168.1.5 - - [10/Oct/2026:13:55:38 +0000] "GET /home HTTP/1.1" 301 -
    # 10.0.0.1 - - [10/Oct/2026:13:55:39 +0000] "POST /api/login HTTP/1.1" 401 150
    # 10.0.0.2 - - [10/Oct/2026:13:55:40 +0000] "GET /home HTTP/1.1" 500 200
    # 10.0.0.3 - - [10/Oct/2026:13:55:41 +0000] "GET /contact HTTP/1.1" 200 300
    #
    # Valid lines: 5
    # Total requests: 5
    # Total bytes: 1200 + 450 + 0 + 150 + 200 + 300 = 2300 (wait: lines:
    # 1: /home 200 1200
    # 2: /about 200 450
    # 3: /home 301 - (0 bytes)
    # 4: /api/login 401 150
    # 5: /home 500 200
    # 6: /contact 200 300
    # Total valid lines: 6
    # Total bytes: 1200 + 450 + 0 + 150 + 200 + 300 = 2300
    # Error status >= 400: line 4 (401), line 5 (500) -> 2 out of 6 = 33.333% -> 33.3%
    # Paths count:
    # /home: 3
    # /about: 1
    # /api/login: 1
    # /contact: 1
    # Top 3 paths:
    # 1. /home: 3
    # 2. /about: 1
    # 3. /api/login: 1
    sample_log = workspace / "server.log"
    sample_log.write_text(
        '127.0.0.1 - - [10/Oct/2026:13:55:36 +0000] "GET /home HTTP/1.1" 200 1200\n'
        '127.0.0.1 - - [10/Oct/2026:13:55:37 +0000] "GET /about HTTP/1.1" 200 450\n'
        'THIS IS A CORRUPT UNPARSEABLE LINE\n'
        '192.168.1.5 - - [10/Oct/2026:13:55:38 +0000] "GET /home HTTP/1.1" 301 -\n'
        '10.0.0.1 - - [10/Oct/2026:13:55:39 +0000] "POST /api/login HTTP/1.1" 401 150\n'
        '10.0.0.2 - - [10/Oct/2026:13:55:40 +0000] "GET /home HTTP/1.1" 500 200\n'
        '10.0.0.3 - - [10/Oct/2026:13:55:41 +0000] "GET /contact HTTP/1.1" 200 300\n',
        encoding="utf-8",
    )

    # R2: CLF parsing and skip corrupt lines
    # R3: Basic CLI execution
    # R5: Text output format
    try:
        proc_txt = run_cli(entrypoint, [str(sample_log)], cwd=workspace)
        expected_txt = (
            "Total Requests: 6\n"
            "Total Bytes: 2300\n"
            "Error Rate: 33.3%\n"
            "Top Paths:\n"
            "  - /home: 3\n"
            "  - /about: 1\n"
            "  - /api/login: 1"
        )
        if proc_txt.returncode == 0:
            emit_result("R3_cli_arguments", "pass", "Executed logparser.py <file> with exit code 0")
            if (
                "Total Requests: 6" in proc_txt.stdout
                and "Total Bytes: 2300" in proc_txt.stdout
            ):
                emit_result("R2_clf_parsing_and_skip", "pass", "Parsed CLF lines, treated '-' as 0, skipped bad line")
            else:
                failures += 1
                emit_result(
                    "R2_clf_parsing_and_skip",
                    "fail",
                    f"Unexpected stdout summary: {proc_txt.stdout.strip()!r}",
                )

            lines_out = [l.rstrip() for l in proc_txt.stdout.strip().splitlines() if l.strip()]
            expected_lines = [l.rstrip() for l in expected_txt.splitlines()]
            if lines_out == expected_lines:
                emit_result("R5_text_output_format", "pass", "Plain text output strictly matches specification")
            else:
                failures += 1
                emit_result(
                    "R5_text_output_format",
                    "fail",
                    f"Got {lines_out!r}, expected {expected_lines!r}",
                )
        else:
            failures += 3
            emit_result("R3_cli_arguments", "fail", f"rc={proc_txt.returncode}, err={proc_txt.stderr.strip()!r}")
            emit_result("R2_clf_parsing_and_skip", "fail", "CLI failed")
            emit_result("R5_text_output_format", "fail", "CLI failed")
    except Exception as exc:
        failures += 3
        emit_result("R3_cli_arguments", "fail", str(exc))
        emit_result("R2_clf_parsing_and_skip", "fail", str(exc))
        emit_result("R5_text_output_format", "fail", str(exc))

    # R4: min-status filter & validation
    try:
        proc_bad_min = run_cli(entrypoint, [str(sample_log), "--min-status", "99"], cwd=workspace)
        proc_bad_alpha = run_cli(entrypoint, [str(sample_log), "--min-status", "abc"], cwd=workspace)
        # Filter for min-status 400: only 401 and 500 match!
        # Requests: 2
        # Total bytes: 150 + 200 = 350
        # Error rate: 100.0%
        # Paths: /api/login: 1, /home: 1
        proc_filter_400 = run_cli(entrypoint, [str(sample_log), "--min-status", "400", "--json"], cwd=workspace)

        val_err_ok = (
            proc_bad_min.returncode == 2
            and "Error: invalid min-status" in proc_bad_min.stderr
            and proc_bad_alpha.returncode == 2
            and "Error: invalid min-status" in proc_bad_alpha.stderr
        )
        filter_ok = False
        if proc_filter_400.returncode == 0:
            jf = json.loads(proc_filter_400.stdout)
            if (
                jf.get("total_requests") == 2
                and jf.get("total_bytes") == 350
                and jf.get("error_rate") == 100.0
            ):
                filter_ok = True

        if val_err_ok and filter_ok:
            emit_result("R4_min_status_filter_and_validation", "pass", "Validated min-status and filtered statistics")
        else:
            failures += 1
            emit_result(
                "R4_min_status_filter_and_validation",
                "fail",
                f"val_err_ok={val_err_ok}, filter_ok={filter_ok}, proc_filter_400={proc_filter_400.stdout.strip()!r}",
            )
    except Exception as exc:
        failures += 1
        emit_result("R4_min_status_filter_and_validation", "fail", str(exc))

    # R6: JSON output format
    try:
        proc_json = run_cli(entrypoint, [str(sample_log), "--json"], cwd=workspace)
        if proc_json.returncode == 0:
            parsed = json.loads(proc_json.stdout)
            expected_json = {
                "total_requests": 6,
                "total_bytes": 2300,
                "error_rate": 33.3,
                "top_paths": [
                    {"path": "/home", "count": 3},
                    {"path": "/about", "count": 1},
                    {"path": "/api/login", "count": 1},
                ],
            }
            if parsed == expected_json:
                emit_result("R6_json_output_format", "pass", "JSON output matches specification exactly")
            else:
                failures += 1
                emit_result("R6_json_output_format", "fail", f"Got {parsed!r}, expected {expected_json!r}")
        else:
            failures += 1
            emit_result("R6_json_output_format", "fail", f"rc={proc_json.returncode}, err={proc_json.stderr.strip()!r}")
    except Exception as exc:
        failures += 1
        emit_result("R6_json_output_format", "fail", str(exc))

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
