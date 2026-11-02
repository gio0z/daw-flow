#!/usr/bin/env python3
"""Acceptance test suite for bookmark-manager scenario."""

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
    entrypoint = workspace / "bookmarks.py"

    all_checks = [
        "R1_entrypoint_exists",
        "R2_json_persistence",
        "R3_add_command",
        "R4_validation_and_update",
        "R5_search_tag_and_query",
        "R6_search_output_formatting",
        "R7_missing_file_handling",
    ]

    if not entrypoint.is_file():
        for check in all_checks:
            emit_result(check, "fail", f"Missing required entrypoint: {entrypoint.name}")
        return 1

    failures = 0
    data_file = workspace / "bookmarks.json"

    # R7: Missing file handling prior to creation
    try:
        proc_empty = run_cli(entrypoint, ["search", "--query", "anything"], cwd=workspace)
        if proc_empty.returncode == 0 and "No bookmarks found." in proc_empty.stdout and not data_file.exists():
            emit_result("R7_missing_file_handling", "pass", "Handled missing bookmarks.json cleanly without creating it")
        else:
            failures += 1
            emit_result(
                "R7_missing_file_handling",
                "fail",
                f"rc={proc_empty.returncode}, out={proc_empty.stdout.strip()!r}, file_created={data_file.exists()}",
            )
    except Exception as exc:
        failures += 1
        emit_result("R7_missing_file_handling", "fail", str(exc))

    # R1: Entry point exists
    emit_result("R1_entrypoint_exists", "pass", "bookmarks.py exists in workspace")

    # R4 part 1: URL validation error
    try:
        proc_bad_url = run_cli(
            entrypoint,
            ["add", "--url", "ftp://example.org/files", "--title", "FTP Site"],
            cwd=workspace,
        )
        if proc_bad_url.returncode == 1 and "Error: invalid URL scheme" in proc_bad_url.stderr:
            url_val_ok = True
        else:
            url_val_ok = False
            failures += 1
            emit_result(
                "R4_validation_and_update",
                "fail",
                f"Invalid URL check failed: rc={proc_bad_url.returncode}, stderr={proc_bad_url.stderr.strip()!r}",
            )
    except Exception as exc:
        url_val_ok = False
        failures += 1
        emit_result("R4_validation_and_update", "fail", str(exc))

    # R3: Add command basic functionality & tag normalization
    try:
        proc_add1 = run_cli(
            entrypoint,
            [
                "add",
                "--url",
                "https://python.org",
                "--title",
                "Python Official",
                "--tags",
                " Python, programming , python ",
            ],
            cwd=workspace,
        )
        if proc_add1.returncode == 0 and "Saved bookmark: Python Official" in proc_add1.stdout:
            emit_result("R3_add_command", "pass", "Added bookmark with normalized deduplicated tags")
        else:
            failures += 1
            emit_result(
                "R3_add_command",
                "fail",
                f"rc={proc_add1.returncode}, out={proc_add1.stdout.strip()!r}, err={proc_add1.stderr.strip()!r}",
            )
    except Exception as exc:
        failures += 1
        emit_result("R3_add_command", "fail", str(exc))

    # R2: JSON persistence check
    try:
        if data_file.is_file():
            data = json.loads(data_file.read_text(encoding="utf-8"))
            if (
                isinstance(data, list)
                and len(data) == 1
                and data[0].get("url") == "https://python.org"
                and data[0].get("title") == "Python Official"
                and data[0].get("tags") == ["python", "programming"] or data[0].get("tags") == ["programming", "python"]
            ):
                emit_result("R2_json_persistence", "pass", "bookmarks.json structure and contents verified")
            else:
                failures += 1
                emit_result("R2_json_persistence", "fail", f"Unexpected content in JSON: {data}")
        else:
            failures += 1
            emit_result("R2_json_persistence", "fail", "bookmarks.json does not exist")
    except Exception as exc:
        failures += 1
        emit_result("R2_json_persistence", "fail", str(exc))

    # R4 part 2: Duplicate URL updates existing bookmark
    if url_val_ok:
        try:
            proc_update = run_cli(
                entrypoint,
                [
                    "add",
                    "--url",
                    "https://python.org",
                    "--title",
                    "Python Language",
                    "--tags",
                    "python, core",
                ],
                cwd=workspace,
            )
            if proc_update.returncode == 0 and "Updated bookmark: Python Language" in proc_update.stdout:
                # check file updated in place
                data = json.loads(data_file.read_text(encoding="utf-8"))
                if len(data) == 1 and data[0]["title"] == "Python Language":
                    emit_result("R4_validation_and_update", "pass", "Validation and in-place URL update verified")
                else:
                    failures += 1
                    emit_result("R4_validation_and_update", "fail", f"Data not updated in place: {data}")
            else:
                failures += 1
                emit_result(
                    "R4_validation_and_update",
                    "fail",
                    f"Update failed: rc={proc_update.returncode}, out={proc_update.stdout.strip()!r}",
                )
        except Exception as exc:
            failures += 1
            emit_result("R4_validation_and_update", "fail", str(exc))

    # Add more bookmarks for search tests:
    # 1. Django Docs - https://docs.djangoproject.com - tags: web, python
    # 2. Rust Lang - https://rust-lang.org - tags: systems, programming
    # 3. Plain Link - http://example.com - no tags
    run_cli(
        entrypoint,
        ["add", "--url", "https://docs.djangoproject.com", "--title", "Django Docs", "--tags", "web, python"],
        cwd=workspace,
    )
    run_cli(
        entrypoint,
        ["add", "--url", "https://rust-lang.org", "--title", "Rust Lang", "--tags", "systems, programming"],
        cwd=workspace,
    )
    run_cli(
        entrypoint,
        ["add", "--url", "http://example.com", "--title", "Example Site"],
        cwd=workspace,
    )

    # R5: Search command with tag and query (AND condition)
    try:
        # Search by tag=python and query=django -> should match only Django Docs
        proc_s1 = run_cli(entrypoint, ["search", "--tag", "PYTHON", "--query", "django"], cwd=workspace)
        # Search by tag=python and query=rust -> should match nothing (No bookmarks found.)
        proc_s2 = run_cli(entrypoint, ["search", "--tag", "python", "--query", "rust"], cwd=workspace)
        if (
            proc_s1.returncode == 0
            and "Django Docs" in proc_s1.stdout
            and "Python Language" not in proc_s1.stdout
            and proc_s2.returncode == 0
            and "No bookmarks found." in proc_s2.stdout
        ):
            emit_result("R5_search_tag_and_query", "pass", "Search filters by tag and query with AND semantics")
        else:
            failures += 1
            emit_result(
                "R5_search_tag_and_query",
                "fail",
                f"s1 out={proc_s1.stdout.strip()!r}, s2 out={proc_s2.stdout.strip()!r}",
            )
    except Exception as exc:
        failures += 1
        emit_result("R5_search_tag_and_query", "fail", str(exc))

    # R6: Search output formatting and alphabetical sorting by title
    # When searching with no filters (or matching multiple):
    # Total items now:
    # - Django Docs (tags: python, web)
    # - Example Site (tags: none)
    # - Python Language (tags: core, python)
    # - Rust Lang (tags: programming, systems)
    #
    # Expected title sort order:
    # 1. Django Docs: [python, web] Django Docs - https://docs.djangoproject.com
    # 2. Example Site: [] Example Site - http://example.com
    # 3. Python Language: [core, python] Python Language - https://python.org
    # 4. Rust Lang: [programming, systems] Rust Lang - https://rust-lang.org
    try:
        proc_all = run_cli(entrypoint, ["search"], cwd=workspace)
        expected_lines = [
            "[python, web] Django Docs - https://docs.djangoproject.com",
            "[] Example Site - http://example.com",
            "[core, python] Python Language - https://python.org",
            "[programming, systems] Rust Lang - https://rust-lang.org",
        ]
        out_lines = [l.strip() for l in proc_all.stdout.strip().splitlines() if l.strip()]
        if proc_all.returncode == 0 and out_lines == expected_lines:
            emit_result("R6_search_output_formatting", "pass", "Search output formatted and sorted correctly")
        else:
            failures += 1
            emit_result(
                "R6_search_output_formatting",
                "fail",
                f"rc={proc_all.returncode}, got={out_lines!r}, expected={expected_lines!r}",
            )
    except Exception as exc:
        failures += 1
        emit_result("R6_search_output_formatting", "fail", str(exc))

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
