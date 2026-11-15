#!/usr/bin/env python3
"""Generate or submit sanitized DAW skill usage feedback.

Read-only and offline by default: harvests structural finding codes (never
file paths, task IDs, commit SHAs, prompts, or source code), prints a sanitized
preview and a 1-click GitHub Issue URL for `gio0z/daw-flow`, and invokes `gh`
only when `--submit` is explicitly passed.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import os
import pathlib
import platform
import re
import shlex
import shutil
import subprocess
import sys
from typing import Any
import urllib.parse

try:
    from scripts.daw_common import (
        SCHEMA_VERSION,
        DuplicateKeyError,
        artifact_dirs,
        build_result,
        make_error,
        make_warning,
        parse_strict_json,
        resolve_bounded_path,
    )
except ImportError:
    from daw_common import (  # type: ignore[import-not-found]
        SCHEMA_VERSION,
        DuplicateKeyError,
        artifact_dirs,
        build_result,
        make_error,
        make_warning,
        parse_strict_json,
        resolve_bounded_path,
    )

FEEDBACK_REPO = "gio0z/daw-flow"
FEEDBACK_ISSUES_URL = f"https://github.com/{FEEDBACK_REPO}/issues/new"
FEEDBACK_TEMPLATE = "skill-feedback.yml"
FEEDBACK_LABEL = "skill-feedback"
VALID_CATEGORIES = (
    "friction",
    "bug",
    "false-block",
    "token-bloat",
    "routing-mismatch",
    "other",
)
FINDING_CODE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
MAX_EVIDENCE_BYTES = 1024 * 1024  # 1 MiB
MAX_ISSUE_URL_LENGTH = 6000  # GitHub answers with 414 URI Too Long past its server limit
MAX_SUMMARY_LEN = 500
MAX_NOTE_LEN = 4000
MAX_CLIENT_LEN = 120
_JSON_PARSE_ERRORS = (json.JSONDecodeError, DuplicateKeyError, RecursionError, ValueError)

# Redaction pipeline, applied in order to operator-provided free text.
_URL_RE = re.compile(r"https?://\S+")
_WINDOWS_PATH_RE = re.compile(r"[A-Za-z]:\\[^\s]+")
# Absolute POSIX path: known root segment, three or more segments, or a file extension.
_POSIX_PATH_RE = re.compile(
    r"(?<![\w])/(?:"
    r"(?:etc|usr|var|home|root|opt|tmp|proc|sys|dev|srv|mnt|Users|Library)/"
    r"|(?:[\w.\-]+/){2,}"
    r"|(?:[\w.\-]+/)*[\w.\-]+\.[A-Za-z0-9]{1,8}\b"
    r")[\w.\-/]*"
)
# Relative path that names a file with an extension (e.g. src/main.py).
_RELATIVE_PATH_RE = re.compile(r"(?<![\w./\-])[\w.\-]+/[\w.\-/]*[\w\-]+\.[A-Za-z0-9]{1,8}\b")
# A git SHA: 12+ hex chars containing a digit, or any 40+ hex run.
_SHA_RE = re.compile(r"\b(?=[0-9a-f]{12,64}\b)(?=[0-9a-f]*\d)[0-9a-f]{12,64}\b", re.IGNORECASE)
_LONG_HEX_RE = re.compile(r"\b[0-9a-f]{40,64}\b", re.IGNORECASE)
_TASK_ID_RES = (
    re.compile(r"\bTASK[-_][A-Za-z0-9._-]+"),
    re.compile(r"\bT-\d+\b"),
    re.compile(r"\bISSUE[-_#]\d+\b", re.IGNORECASE),
    re.compile(r"\bpr-\d+\b", re.IGNORECASE),
)
_CREDENTIAL_RE = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|token|pass(?:word|wd)|secret"
    r"|private[_-]?key|authorization)\b(\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|\S+)"
)
_BEARER_RE = re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._\-+/=]{8,}")
# Opaque token runs: 32+ contiguous token characters.
_OPAQUE_TOKEN_RE = re.compile(r"[A-Za-z0-9+/=_-]{32,}")
# A run that is only lowercase letters and separators reads as prose, not a secret.
_OPAQUE_PROSE_RE = re.compile(r"\A[a-z0-9_-]+\Z")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MISSING_LABEL_RE = re.compile(r"could not add label: '([^']+)' not found")
# Harness-style secret placeholders (e.g. {{API_KEY_...}}) and bare secret literals.
_KNOWN_TOKEN_RE = re.compile(
    r"\{\{[A-Za-z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD)[A-Za-z0-9_]*\}\}"
    r"|(?i:\b(?:sk|pk|ghp|gho|xox[baprs])[-_][A-Za-z0-9\-]{16,})"
)

FEEDBACK_LIMITATIONS = [
    "Read-only and offline by default: never mutates project files or sends network requests unless --submit is passed.",
    "Evidence scanning retains structural finding codes and environment metadata only; no paths, task IDs, prompts, or source are collected from project files.",
    "Operator free text (--summary, --note, --client) is redacted for absolute paths, git SHAs, task IDs, credential assignments, and opaque token runs.",
    "Pasted source code cannot be detected mechanically: the operator remains responsible for the contents of the summary.",
    "With --submit, delegates issue creation to the local authenticated `gh` CLI; requires explicit operator consent.",
]


def _suite_root() -> pathlib.Path:
    parent = pathlib.Path(__file__).resolve().parents[1]
    if (parent / "SKILL.md").is_file() and (parent / "VERSION").is_file():
        return parent
    shared = pathlib.Path(sys.prefix).resolve() / "share" / "deterministic-agentic-workflow"
    if (shared / "SKILL.md").is_file() and (shared / "VERSION").is_file():
        return shared
    return parent


def _read_daw_version(suite_root: pathlib.Path) -> str:
    version_file = suite_root / "VERSION"
    if version_file.is_file():
        try:
            text = version_file.read_text(encoding="utf-8").strip()
            if text:
                return text
        except (OSError, UnicodeDecodeError):
            pass
    return "unknown"


def _load_manifest_sets(suite_root: pathlib.Path) -> tuple[set[str], set[str]]:
    manifest_path = suite_root / "references" / "suite-manifest.json"
    if not manifest_path.is_file():
        return set(), set()
    try:
        data = parse_strict_json(manifest_path.read_text(encoding="utf-8"))
    except (*_JSON_PARSE_ERRORS, OSError, UnicodeDecodeError):
        return set(), set()
    if not isinstance(data, dict):
        return set(), set()
    routes = data.get("routes")
    modules = data.get("modules")
    route_names = set(routes.keys()) if isinstance(routes, dict) else set()
    module_names = set(modules.keys()) if isinstance(modules, dict) else set()
    return route_names, module_names


def _read_bounded_json(
    project_root: pathlib.Path,
    rel_path: str,
    warnings: list[dict[str, str]],
    seen_files: set[pathlib.Path],
) -> dict[str, Any] | None:
    resolved, err = resolve_bounded_path(project_root, rel_path)
    if err or resolved is None:
        warnings.append(
            make_warning(
                "evidence_unsafe_path",
                "evidence",
                "Skipped an evidence file whose path escapes the project root.",
            )
        )
        return None
    if resolved in seen_files or not resolved.is_file():
        return None
    seen_files.add(resolved)
    try:
        if resolved.stat().st_size > MAX_EVIDENCE_BYTES:
            warnings.append(
                make_warning(
                    "evidence_oversize",
                    "evidence",
                    f"Skipped an evidence file exceeding {MAX_EVIDENCE_BYTES} bytes.",
                )
            )
            return None
        raw = resolved.read_text(encoding="utf-8")
        data = parse_strict_json(raw)
    except (*_JSON_PARSE_ERRORS, OSError, UnicodeDecodeError):
        warnings.append(
            make_warning(
                "evidence_unreadable",
                "evidence",
                "Skipped an unreadable or malformed JSON evidence file.",
            )
        )
        return None
    if not isinstance(data, dict):
        warnings.append(
            make_warning(
                "evidence_malformed",
                "evidence",
                "Skipped a non-object JSON evidence file.",
            )
        )
        return None
    return data


def _extract_dispatch_findings(data: dict[str, Any], counts: Counter[str]) -> None:
    raw_findings = data.get("findings")
    if not isinstance(raw_findings, list):
        return
    for item in raw_findings:
        code = item if isinstance(item, str) else item.get("code") if isinstance(item, dict) else None
        if isinstance(code, str) and FINDING_CODE_RE.match(code):
            counts[code] += 1


def _extract_isolation_findings(data: dict[str, Any], counts: Counter[str]) -> None:
    tasks = data.get("tasks")
    if not isinstance(tasks, dict):
        return
    for entry in tasks.values():
        if not isinstance(entry, dict):
            continue
        bf = entry.get("batch_failure")
        if isinstance(bf, str) and FINDING_CODE_RE.match(bf):
            counts[bf] += 1
        elif isinstance(bf, dict) and bf:
            bf_code = bf.get("code")
            if isinstance(bf_code, str) and FINDING_CODE_RE.match(bf_code):
                counts[bf_code] += 1
            else:
                counts["batch_failure"] += 1
        status = entry.get("status")
        if isinstance(status, str) and status in ("failed", "escaped"):
            counts[status] += 1


def scan_evidence_findings(
    project_root: pathlib.Path,
) -> tuple[dict[str, int], list[dict[str, str]]]:
    """Scan evidence directories for finding codes without retaining paths or IDs."""
    root = pathlib.Path(project_root).resolve()
    counts: Counter[str] = Counter()
    warnings: list[dict[str, str]] = []
    seen_files: set[pathlib.Path] = set()

    for ev_dir in artifact_dirs(root, "evidence"):
        try:
            rel_dir = ev_dir.relative_to(root).as_posix()
        except ValueError:
            continue
        resolved_ev, err = resolve_bounded_path(root, rel_dir)
        if err or resolved_ev is None:
            if ev_dir.exists() or ev_dir.is_symlink():
                warnings.append(
                    make_warning(
                        "evidence_unsafe_path",
                        "evidence",
                        "Skipped an evidence directory outside the project root.",
                    )
                )
            continue
        if not resolved_ev.is_dir():
            continue

        for cur_root, dirs, files in os.walk(resolved_ev, followlinks=False):
            cur_path = pathlib.Path(cur_root)
            safe_dirs: list[str] = []
            for dname in sorted(dirs):
                d_rel = (cur_path / dname).relative_to(root).as_posix()
                _, d_err = resolve_bounded_path(root, d_rel)
                if d_err is None:
                    safe_dirs.append(dname)
                else:
                    warnings.append(
                        make_warning(
                            "evidence_unsafe_path",
                            "evidence",
                            "Skipped a nested evidence symlink escaping the project root.",
                        )
                    )
            dirs[:] = safe_dirs

            if "review-dispatch.json" in files:
                rel_dispatch = (cur_path / "review-dispatch.json").relative_to(root).as_posix()
                dispatch_data = _read_bounded_json(root, rel_dispatch, warnings, seen_files)
                if dispatch_data is not None:
                    _extract_dispatch_findings(dispatch_data, counts)

        iso_candidate = resolved_ev / "runner" / "isolation.json"
        if iso_candidate.exists() or iso_candidate.is_symlink():
            rel_iso = f"{rel_dir}/runner/isolation.json"
            iso_data = _read_bounded_json(root, rel_iso, warnings, seen_files)
            if iso_data is not None:
                _extract_isolation_findings(iso_data, counts)

    sorted_counts = {code: counts[code] for code in sorted(counts)}
    return sorted_counts, warnings


def _single_line(text: str, max_len: int | None = None) -> str:
    cleaned = " ".join(text.split())
    if max_len is not None and len(cleaned) > max_len:
        return cleaned[: max_len - 3].rstrip() + "..."
    return cleaned


def _clean_multiline(text: str, max_len: int = 4000) -> str:
    cleaned = text.strip()
    if len(cleaned) > max_len:
        return cleaned[: max_len - 3].rstrip() + "..."
    return cleaned

def _redact_opaque_tokens(text: str) -> str:
    """Mask long opaque token runs, leaving lowercase prose alone."""
    def replace(match: re.Match[str]) -> str:
        run = match.group(0)
        if _OPAQUE_PROSE_RE.match(run):
            return run
        return "[REDACTED]"

    return _OPAQUE_TOKEN_RE.sub(replace, text)

def _redact_free_text(text: str) -> str:
    """Remove paths, SHAs, task IDs, credentials, and token runs from operator text.

    The pipeline is ordered so the most specific patterns claim their span first:
    a URL is masked before its path segments can be matched separately.
    """
    if not text:
        return ""
    redacted = _URL_RE.sub("[URL]", text)
    redacted = _WINDOWS_PATH_RE.sub("[PATH]", redacted)
    redacted = _POSIX_PATH_RE.sub("[PATH]", redacted)
    redacted = _RELATIVE_PATH_RE.sub("[PATH]", redacted)
    redacted = _LONG_HEX_RE.sub("[SHA]", redacted)
    redacted = _SHA_RE.sub("[SHA]", redacted)
    for task_re in _TASK_ID_RES:
        redacted = task_re.sub("[TASK-ID]", redacted)
    redacted = _BEARER_RE.sub(lambda m: f"{m.group(1)} [REDACTED]", redacted)
    redacted = _CREDENTIAL_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", redacted)
    redacted = _KNOWN_TOKEN_RE.sub("[REDACTED]", redacted)
    redacted = _redact_opaque_tokens(redacted)
    return _CONTROL_CHARS_RE.sub("", redacted)

def _build_issue_url(fields: dict[str, str]) -> str:
    """Assemble the 1-click issue URL, bounded under the GitHub URL length limit.

    The target is an issue *form*, so the query keys are the form's field ids.
    When the encoded URL would exceed the limit, the summary shrinks first,
    then the finding codes are dropped.
    """
    params = dict(fields)

    def encode(current: dict[str, str]) -> str:
        query = urllib.parse.urlencode(current, quote_via=urllib.parse.quote)
        return f"{FEEDBACK_ISSUES_URL}?{query}"

    url = encode(params)
    if len(url) <= MAX_ISSUE_URL_LENGTH:
        return url

    summary = params.get("summary", "")
    for size in range(len(summary), -1, -1):
        candidate = summary[:size]
        if size < len(summary):
            candidate = candidate.rstrip() + "..."
        trimmed = dict(params)
        trimmed["summary"] = candidate
        url = encode(trimmed)
        if len(url) <= MAX_ISSUE_URL_LENGTH:
            return url

    trimmed = dict(params)
    trimmed.pop("summary", None)
    url = encode(trimmed)
    if len(url) <= MAX_ISSUE_URL_LENGTH:
        return url

    trimmed.pop("finding_codes", None)
    return encode(trimmed)


def _build_issue_title(
    route: str,
    module: str,
    category: str,
    finding_counts: dict[str, int],
    recurring_findings: list[str],
    summary: str,
) -> str:
    if route != "unspecified" and module != "unspecified":
        target = f"{route}/{module}"
    elif module != "unspecified":
        target = module
    elif route != "unspecified":
        target = route
    else:
        target = "suite"

    if recurring_findings:
        detail = min(recurring_findings, key=lambda c: (-finding_counts[c], c))
    elif finding_counts:
        detail = min(finding_counts, key=lambda c: (-finding_counts[c], c))
    elif summary:
        detail = summary
    else:
        detail = "report"

    return _single_line(f"[feedback] {target}: {category} ({detail})", max_len=120)


def _build_issue_body(report: dict[str, Any]) -> str:
    counts: dict[str, int] = report["finding_counts"]
    recurring: list[str] = report["recurring_findings"]
    codes_text = (
        ", ".join(f"{code} ({counts[code]}x)" for code in report["finding_codes"])
        if report["finding_codes"]
        else "none"
    )
    recurring_line = (
        f"\nRecurring (>= 2): {', '.join(recurring)}" if recurring else ""
    )
    summary_text = report["summary"] or "(none provided)"
    note_block = f"\n\n{report['note']}" if report["note"] else ""

    return (
        f"### DAW Version\n{report['daw_version']}\n\n"
        f"### Environment\nPython {report['python_version']} | {report['os']} | Client: {report['client']}\n\n"
        f"### Route / Module\nroute: {report['route']} | module: {report['module']}\n\n"
        f"### Category\n{report['category']}\n\n"
        f"### Finding Codes\n{codes_text}{recurring_line}\n\n"
        f"### Summary / Notes\n{summary_text}{note_block}"
    )


def build_feedback_report(
    *,
    route: str = "unspecified",
    module: str = "unspecified",
    category: str = "friction",
    client: str = "unspecified",
    findings_input: list[str] | None = None,
    summary: str = "",
    note: str = "",
    project_root: pathlib.Path | None = None,
    suite_root: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Build and validate a sanitized feedback report and GitHub Issue payload."""
    resolved_suite = (suite_root or _suite_root()).resolve()
    valid_routes, valid_modules = _load_manifest_sets(resolved_suite)
    findings: list[dict[str, str]] = []

    if category not in VALID_CATEGORIES:
        findings.append(
            make_error(
                "invalid_category",
                "category",
                f"Category {category!r} must be one of {list(VALID_CATEGORIES)}.",
            )
        )
    if route != "unspecified" and route not in valid_routes:
        findings.append(
            make_error(
                "invalid_route",
                "route",
                f"Unknown route {route!r}; expected 'unspecified' or a manifest route.",
            )
        )
    if module != "unspecified" and module not in valid_modules:
        findings.append(
            make_error(
                "invalid_module",
                "module",
                f"Unknown module {module!r}; expected 'unspecified' or a manifest module.",
            )
        )

    counts: Counter[str] = Counter()
    for code in findings_input or []:
        if not isinstance(code, str) or not FINDING_CODE_RE.match(code):
            findings.append(
                make_error(
                    "invalid_finding_code",
                    "finding",
                    f"Finding code {code!r} must match {FINDING_CODE_RE.pattern}.",
                )
            )
        else:
            counts[code] += 1

    if project_root is not None:
        scanned_counts, scan_warnings = scan_evidence_findings(project_root)
        counts.update(scanned_counts)
        findings.extend(scan_warnings)

    finding_codes = sorted(counts.keys())
    finding_counts = {code: counts[code] for code in finding_codes}
    recurring_findings = [code for code in finding_codes if counts[code] >= 2]

    clean_client = _single_line(_redact_free_text(client), max_len=MAX_CLIENT_LEN) or "unspecified"
    clean_summary = _single_line(_redact_free_text(summary), max_len=MAX_SUMMARY_LEN)
    clean_note = _clean_multiline(_redact_free_text(note), max_len=MAX_NOTE_LEN)

    report_obj: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "daw_version": _read_daw_version(resolved_suite),
        "python_version": platform.python_version(),
        "os": f"{platform.system()} ({platform.machine()})",
        "client": clean_client,
        "route": route,
        "module": module,
        "category": category,
        "finding_codes": finding_codes,
        "finding_counts": finding_counts,
        "recurring_findings": recurring_findings,
        "summary": clean_summary,
        "note": clean_note,
    }

    issue_title = _build_issue_title(
        route, module, category, finding_counts, recurring_findings, clean_summary
    )
    issue_body = _build_issue_body(report_obj)
    codes_text = (
        ", ".join(f"{code} ({finding_counts[code]}x)" for code in finding_codes)
        if finding_codes
        else "none"
    )
    issue_url = _build_issue_url(
        {
            "template": FEEDBACK_TEMPLATE,
            "labels": FEEDBACK_LABEL,
            "title": issue_title,
            "daw_version": report_obj["daw_version"],
            "environment": (
                f"Python {report_obj['python_version']} | {report_obj['os']}"
                f" | Client: {report_obj['client']}"
            ),
            "route_module": f"route: {route} | module: {module}",
            "category": category,
            "finding_codes": codes_text,
            "summary": clean_summary or "(none provided)",
        }
    )
    gh_command = [
        "gh",
        "issue",
        "create",
        "--repo",
        FEEDBACK_REPO,
        "--label",
        FEEDBACK_LABEL,
        "--title",
        issue_title,
        "--body",
        issue_body,
    ]

    return build_result(
        "feedback",
        findings,
        FEEDBACK_LIMITATIONS,
        extra={
            "report": report_obj,
            "issue_title": issue_title,
            "issue_body": issue_body,
            "issue_url": issue_url,
            "gh_command": gh_command,
            "submitted": False,
            "submitted_url": None,
        },
    )


def submit_via_gh(gh_command: list[str]) -> tuple[bool, str, str | None]:
    """Invoke `gh issue create` cleanly without shell expansion.

    Returns `(ok, detail, error_code)`. `error_code` is `feedback_label_missing`
    when the target repository has no `skill-feedback` label, otherwise None.
    """
    if shutil.which("gh") is None:
        return (
            False,
            "GitHub CLI ('gh') not found on PATH; open issue_url in a browser instead.",
            None,
        )
    try:
        proc = subprocess.run(
            gh_command,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except OSError as exc:
        return False, f"Failed to execute gh: {exc}", None
    except subprocess.TimeoutExpired:
        return False, "gh issue create timed out after 30 seconds.", None

    if proc.returncode == 0:
        return True, proc.stdout.strip(), None
    detail = proc.stderr.strip() or proc.stdout.strip() or f"gh exited {proc.returncode}"
    if _MISSING_LABEL_RE.search(detail):
        return (
            False,
            detail,
            "feedback_label_missing",
        )
    return False, detail, None


def _print_text_output(result: dict[str, Any]) -> None:
    status_str = "VALID" if result["valid"] else "INVALID"
    print(f"[{status_str}] Check: {result['check']} (schema_version: {result['schema_version']})")

    report = result["report"]
    print("\nSanitized Report Preview:")
    print(f"  DAW Version : {report['daw_version']}")
    print(f"  Environment : Python {report['python_version']} | {report['os']} | Client: {report['client']}")
    print(f"  Target      : route={report['route']} | module={report['module']} | category={report['category']}")
    codes_display = (
        ", ".join(f"{c} ({report['finding_counts'][c]}x)" for c in report["finding_codes"])
        if report["finding_codes"]
        else "none"
    )
    print(f"  Findings    : {codes_display}")
    if report["recurring_findings"]:
        print(f"  Recurring   : {', '.join(report['recurring_findings'])}")
    if report["summary"]:
        print(f"  Summary     : {report['summary']}")

    if result["findings"]:
        print("\nValidation Findings:")
        for f in result["findings"]:
            print(f"  [{f['severity'].upper()}] {f['code']} @ {f['path']}: {f['message']}")

    if result["valid"]:
        print(f"\nIssue Title: {result['issue_title']}")
        print(f"Issue URL: {result['issue_url']}")
        print(f"GH CLI: {shlex.join(result['gh_command'])}")
        if result["submitted"]:
            print(f"Submitted URL: {result['submitted_url'] or '(created)'}")

    if result["limitations"]:
        print("\nLimitations:")
        for lim in result["limitations"]:
            print(f"  - {lim}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate or submit sanitized DAW skill usage feedback for gio0z/daw-flow."
    )
    parser.add_argument("--route", default="unspecified", help="DAW route name (e.g. feature, bugfix, patch).")
    parser.add_argument("--module", default="unspecified", help="DAW module name (e.g. daw-plan, daw-build).")
    parser.add_argument(
        "--category",
        default="friction",
        help=f"Feedback category ({', '.join(VALID_CATEGORIES)}).",
    )
    parser.add_argument("--client", default="unspecified", help="Agent client/model label (e.g. claude-code).")
    parser.add_argument(
        "--finding",
        action="append",
        default=[],
        help="Sanitized finding code to include (repeatable).",
    )
    parser.add_argument("--summary", default="", help="Short sanitized summary (never paste secrets/code).")
    parser.add_argument("--note", default="", help="Optional sanitized details or reproduction note.")
    parser.add_argument(
        "--project-root",
        default=None,
        help="Optional project root to scan docs/daw/evidence/ for finding codes.",
    )
    parser.add_argument(
        "--submit",
        action="store_true",
        help="Create the issue directly with `gh issue create` (requires operator consent).",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format: text or json.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output (shorthand for --format json).",
    )
    args = parser.parse_args(argv)

    project_root: pathlib.Path | None = None
    if args.project_root is not None:
        candidate = pathlib.Path(args.project_root).resolve()
        if not candidate.is_dir():
            sys.stderr.write("Error: Project root is not a directory.\n")
            return 2
        project_root = candidate

    result = build_feedback_report(
        route=args.route,
        module=args.module,
        category=args.category,
        client=args.client,
        findings_input=args.finding,
        summary=args.summary,
        note=args.note,
        project_root=project_root,
    )

    if args.submit and result["valid"]:
        ok, detail, error_code = submit_via_gh(result["gh_command"])
        if ok:
            result["submitted"] = True
            result["submitted_url"] = detail or None
        elif error_code == "feedback_label_missing":
            result["findings"].append(
                make_error(
                    "feedback_label_missing",
                    "gh",
                    f"{detail}. Create the label first: "
                    f"gh label create {FEEDBACK_LABEL} --repo {FEEDBACK_REPO} "
                    f"--description \"DAW skill usage feedback\".",
                )
            )
            result["valid"] = False
        else:
            result["findings"].append(
                make_error("feedback_submit_failed", "gh", detail)
            )
            result["valid"] = False

    fmt = "json" if args.json else args.format
    if fmt == "json":
        print(json.dumps(result, indent=2))
    else:
        _print_text_output(result)

    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
