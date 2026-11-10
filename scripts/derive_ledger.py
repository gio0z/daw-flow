#!/usr/bin/env python3
"""Derive a spec ledger from existing doc-transition records.

This is **not** the read-only validator: it is the suite's only writer. It emits
``<spec_dir>/ledger.json`` and nothing else, and only when ``--write`` is given.
``validate.py`` and ``route.py`` never invoke it.

Every ledger field is a projection of a record that already exists: ``state`` from
``transition.to``, ``sha256`` from a record whose declared hash still matches the
document's current bytes, ``record`` from that file, ``history`` from the rest of
the observed transition chain. A hash is never recomputed into the ledger, so an
edited document is reported as drift (``derive_doc_unmapped``) instead of being
silently re-pinned, and an ambiguous chain is reported (``derive_doc_conflict``)
instead of guessed from file mtimes.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from typing import Any

try:
    from scripts.check_config import parse_config_block
    from scripts.check_ledger import validate_ledger
    from scripts.daw_common import (
        SCHEMA_VERSION,
        DuplicateKeyError,
        compute_sha256,
        has_errors,
        is_durable_evidence_path,
        make_error,
        make_warning,
        parse_strict_json,
        resolve_bounded_path,
    )
except ImportError:
    from check_config import parse_config_block  # type: ignore[import-not-found]
    from check_ledger import validate_ledger  # type: ignore[import-not-found]
    from daw_common import (  # type: ignore[import-not-found]
        SCHEMA_VERSION,
        DuplicateKeyError,
        compute_sha256,
        has_errors,
        is_durable_evidence_path,
        make_error,
        make_warning,
        parse_strict_json,
        resolve_bounded_path,
    )

LEDGER_STATES = ("intake", "authoring", "review", "rework", "ready")
DEFAULT_RECORD_SOURCES = ("docs/decisions", "docs/specs/records", "docs/evidence")
DEFAULT_SPEC_DIR = "docs/specs"
LEDGER_FILENAME = "ledger.json"
MAX_INPUT_BYTES = 1024 * 1024
AGENT_FILES = ("AGENTS.md", "CLAUDE.md")
JSON_PARSE_ERRORS = (DuplicateKeyError, ValueError, RecursionError)

DERIVE_LIMITATIONS = [
    "Projects only what existing records declare; it never invents a state, a reviewer, or a hash.",
    "Requires at least one doc-transition record per document; a project with specs but no records stays underived.",
    "Oversize records (over 1 MiB) and non-UTF-8 files are reported unread rather than parsed partially.",
]


def _hex64(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _project_spec_dir(root: pathlib.Path, override: str | None) -> str:
    if override:
        return override
    for name in AGENT_FILES:
        agent = root / name
        if not agent.is_file():
            continue
        try:
            text = agent.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        spec_dir = parse_config_block(text).get("spec_dir")
        if isinstance(spec_dir, str) and spec_dir.strip():
            return spec_dir
        return DEFAULT_SPEC_DIR
    return DEFAULT_SPEC_DIR


def _record_roots(root: pathlib.Path, overrides: list[str]) -> list[pathlib.Path]:
    names = overrides if overrides else [d for d in DEFAULT_RECORD_SOURCES if (root / d).is_dir()]
    roots: list[pathlib.Path] = []
    for name in names:
        resolved, err = resolve_bounded_path(root, name)
        if err or resolved is None or not resolved.is_dir():
            continue
        roots.append(resolved)
    return roots


def _record_files(roots: list[pathlib.Path]) -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for base in roots:
        files.extend(sorted(base.glob("*.json")))
        files.extend(sorted(base.glob("*/*.json")))
    seen: set[pathlib.Path] = set()
    unique: list[pathlib.Path] = []
    for path in files:
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        unique.append(path)
    return unique


def _load_record(
    root: pathlib.Path, path: pathlib.Path, findings: list[dict[str, str]]
) -> dict[str, Any] | None:
    rel = path.relative_to(root).as_posix()
    try:
        if path.stat().st_size > MAX_INPUT_BYTES:
            findings.append(
                make_warning("derive_record_malformed", rel, "Record exceeds 1 MiB and was not read.")
            )
            return None
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        findings.append(
            make_warning("derive_record_malformed", rel, "Record cannot be read as UTF-8.")
        )
        return None
    try:
        data = parse_strict_json(text)
    except (OSError, *JSON_PARSE_ERRORS):
        findings.append(
            make_warning("derive_record_malformed", rel, "Record is not strict JSON or repeats a key.")
        )
        return None
    if not isinstance(data, dict):
        findings.append(make_warning("derive_record_malformed", rel, "Record root must be an object."))
        return None
    transition = data.get("transition")
    if not isinstance(transition, dict):
        # Not a doc-transition record (for example a task contract); skip it silently.
        return None
    state = transition.get("to")
    if not isinstance(state, str) or state not in LEDGER_STATES:
        findings.append(
            make_warning("derive_record_malformed", rel, "Record transition.to is missing or not a ledger state.")
        )
        return None
    if not isinstance(data.get("documents"), list):
        findings.append(
            make_warning("derive_record_malformed", rel, "Record documents must be an array.")
        )
        return None
    return data


def _record_declarations(
    data: dict[str, Any], findings: list[dict[str, str]], rel: str
) -> list[tuple[str, str]]:
    """Return usable (document path, declared sha256) pairs from one record."""
    pairs: list[tuple[str, str]] = []
    for entry in data.get("documents") or []:
        path = entry.get("path") if isinstance(entry, dict) else None
        sha = entry.get("sha256") if isinstance(entry, dict) else None
        if isinstance(path, str) and path.strip() and _hex64(sha):
            pairs.append((path, sha))
            continue
        findings.append(
            make_warning(
                "derive_record_malformed",
                rel,
                "Record documents[] entry must be an object with a string path and a 64-hex sha256.",
            )
        )
    return pairs


def _resolve_chain(
    path: str, candidates: list[dict[str, str]], findings: list[dict[str, str]]
) -> dict[str, Any] | None:
    by_to: dict[str, dict[str, str]] = {}
    for candidate in candidates:
        if candidate["to"] in by_to:
            findings.append(
                make_error(
                    "derive_doc_conflict",
                    path,
                    "Two records claim the same transition target "
                    f"'{candidate['to']}': {by_to[candidate['to']]['record']} and {candidate['record']}.",
                )
            )
            return None
        by_to[candidate["to"]] = candidate

    froms = {candidate["from"] for candidate in candidates if candidate.get("from")}
    terminal = [candidate for candidate in candidates if candidate["to"] not in froms]
    if len(terminal) != 1:
        pairs = ", ".join(f"{c.get('from') or '?'}->{c['to']}" for c in candidates)
        findings.append(
            make_error(
                "derive_doc_conflict",
                path,
                f"Transition chain has {len(terminal)} terminal records ({pairs}); expected exactly one.",
            )
        )
        return None
    winner = terminal[0]
    on_path: set[int] = set()
    current: dict[str, str] | None = winner
    while current is not None and id(current) not in on_path:
        on_path.add(id(current))
        current = by_to.get(current["from"]) if current.get("from") else None
    if current is not None or len(on_path) != len(candidates):
        pairs = ", ".join(f"{c.get('from') or '?'}->{c['to']}" for c in candidates)
        findings.append(
            make_error(
                "derive_doc_conflict",
                path,
                f"Transition chain is not one connected path ending at the terminal record ({pairs}).",
            )
        )
        return None
    entry: dict[str, Any] = {
        "path": path,
        "state": winner["to"],
        "sha256": winner["sha256"],
        "record": winner["record"],
    }
    history = sorted(c["record"] for c in candidates if c is not winner)  # winner is a distinct dict object
    if history:
        entry["history"] = history
    return entry


def derive_ledger(
    project_root: pathlib.Path,
    spec_dir: str | None,
    records_dirs: list[str],
    write: bool,
) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    try:
        root = pathlib.Path(project_root).resolve()
    except (OSError, RuntimeError, ValueError):
        return {
            "valid": False,
            "check": "derive_ledger",
            "schema_version": SCHEMA_VERSION,
            "spec_dir": spec_dir or DEFAULT_SPEC_DIR,
            "documents": 0,
            "unmapped": [],
            "written": None,
            "findings": [make_error("project_root_error", "$", "Cannot resolve project root.")],
            "limitations": DERIVE_LIMITATIONS,
        }

    resolved_spec_dir = _project_spec_dir(root, spec_dir)
    roots = _record_roots(root, records_dirs)
    if not roots:
        findings.append(
            make_warning(
                "derive_records_dir_missing",
                ",".join(DEFAULT_RECORD_SOURCES),
                "No records source exists; nothing can be derived without transition records.",
            )
        )

    candidates: dict[str, list[dict[str, str]]] = {}
    mentioned: set[str] = set()
    missing_reported: set[str] = set()
    for path in _record_files(roots):
        data = _load_record(root, path, findings)
        if data is None:
            continue
        rel = path.relative_to(root).as_posix()
        transition = data["transition"]
        from_state = transition.get("from") if isinstance(transition.get("from"), str) else None
        for doc_path, declared in _record_declarations(data, findings, rel):
            mentioned.add(doc_path)
            doc_resolved, err = resolve_bounded_path(root, doc_path)
            if err or doc_resolved is None:
                if doc_path not in missing_reported:
                    missing_reported.add(doc_path)
                    findings.append(
                        make_error(
                            "derive_doc_missing",
                            doc_path,
                            f"Record {rel} names a path that escapes the project root ({err}).",
                        )
                    )
                continue
            if not doc_resolved.is_file():
                if doc_path not in missing_reported:
                    missing_reported.add(doc_path)
                    findings.append(
                        make_warning("derive_doc_missing", doc_path, "Declared document does not exist on disk.")
                    )
                continue
            try:
                current = compute_sha256(doc_resolved)
            except (OSError, RuntimeError):
                continue
            if current != declared:
                continue
            candidates.setdefault(doc_path, []).append(
                {"record": rel, "from": from_state or "", "to": transition["to"], "sha256": declared}
            )

    entries: list[dict[str, Any]] = []
    unmapped: list[str] = []
    for doc_path in sorted(mentioned):
        if doc_path in missing_reported:
            continue
        group = candidates.get(doc_path)
        if not group:
            findings.append(
                make_warning(
                    "derive_doc_unmapped",
                    doc_path,
                    "every record's sha256 is stale for the current bytes — re-run the review transition",
                )
            )
            unmapped.append(doc_path)
            continue
        entry = _resolve_chain(doc_path, group, findings)
        if entry is not None:
            entries.append(entry)

    spec_dir_resolved, spec_dir_err = resolve_bounded_path(root, resolved_spec_dir)
    if spec_dir_err or spec_dir_resolved is None or not spec_dir_resolved.is_dir():
        spec_dir_resolved = None
    if spec_dir_resolved is not None:
        tracked = {os.path.normpath(p).replace("\\", "/") for p in mentioned}
        derived = {os.path.normpath(e["path"]).replace("\\", "/") for e in entries}
        for spec_path in sorted(spec_dir_resolved.glob("*.md")):
            if not spec_path.is_file() or spec_path.name == LEDGER_FILENAME:
                continue
            rel_spec = spec_path.relative_to(root).as_posix()
            norm_spec = os.path.normpath(rel_spec).replace("\\", "/")
            if norm_spec in tracked or norm_spec in derived:
                continue
            findings.append(
                make_error(
                    "derive_doc_untracked",
                    rel_spec,
                    "Spec document has no doc-transition record; the derived ledger would omit it.",
                )
            )
    for entry in entries:
        if not is_durable_evidence_path(entry["record"]):
            findings.append(
                make_warning("derive_record_not_durable", entry["record"], "Record path is not durable.")
            )

    payload = {"schema_version": 1, "documents": entries}
    for finding in validate_ledger(payload, root)["findings"]:
        if finding["severity"] != "error":
            continue
        findings.append(
            make_error(
                "derive_ledger_invalid",
                f"ledger:{finding['path']}",
                f"The derived ledger would fail ledger validation: {finding['message']}",
            )
        )

    written: str | None = None
    ledger_rel = f"{resolved_spec_dir.rstrip('/')}/{LEDGER_FILENAME}"
    if write:
        if has_errors(findings):
            findings.append(
                make_error("derive_write_refused", ledger_rel, "Refusing to write while error findings exist.")
            )
        else:
            ledger_path, err = resolve_bounded_path(root, ledger_rel)
            if err or ledger_path is None:
                findings.append(make_error("derive_write_refused", ledger_rel, f"Ledger path is unsafe ({err})."))
            else:
                if (root / ledger_rel).is_symlink():
                    findings.append(
                        make_error(
                            "derive_write_refused",
                            ledger_rel,
                            "Ledger path is a symlink; refusing to follow it.",
                        )
                    )
                else:
                    try:
                        ledger_path.parent.mkdir(parents=True, exist_ok=True)
                        ledger_path.write_text(
                            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
                        )
                    except OSError:
                        findings.append(make_error("derive_write_refused", ledger_rel, "Failed to write ledger."))
                    else:
                        written = ledger_rel

    return {
        "valid": not has_errors(findings),
        "check": "derive_ledger",
        "schema_version": SCHEMA_VERSION,
        "spec_dir": resolved_spec_dir,
        "documents": len(entries),
        "unmapped": sorted(unmapped),
        "written": written,
        "findings": findings,
        "limitations": DERIVE_LIMITATIONS,
    }


def _print_text(result: dict[str, Any]) -> None:
    status = "VALID" if result["valid"] else "INVALID"
    print(f"[{status}] Check: derive_ledger (schema_version: {result['schema_version']})")
    print(f"Spec dir: {result['spec_dir']}")
    print(f"Documents: {result['documents']}")
    print(f"Written: {result['written'] if result['written'] else '(nothing — pass --write to emit)'}")
    if result["unmapped"]:
        print("Unmapped:")
        for path in result["unmapped"]:
            print(f"  - {path}")
    if result["findings"]:
        print("\nFindings:")
        for finding in result["findings"]:
            print(f"  [{finding['severity'].upper()}] {finding['code']} @ {finding['path']}: {finding['message']}")
    if result["limitations"]:
        print("\nLimitations:")
        for limitation in result["limitations"]:
            print(f"  - {limitation}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Derive <spec_dir>/ledger.json from existing doc-transition records."
    )
    parser.add_argument("--project-root", required=True, help="Project root directory.")
    parser.add_argument("--spec-dir", default=None, help="Spec directory (default: daw-config spec_dir, else docs/specs).")
    parser.add_argument(
        "--records-dir",
        action="append",
        default=[],
        help="Record directory (repeatable). Default: docs/decisions, docs/specs/records, docs/evidence.",
    )
    parser.add_argument("--write", action="store_true", help="Write <spec_dir>/ledger.json.")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format.")
    args = parser.parse_args()

    try:
        root = pathlib.Path(args.project_root).resolve()
    except (OSError, RuntimeError, ValueError):
        sys.stderr.write("Error: Cannot resolve project root.\n")
        sys.exit(2)
    if not root.is_dir():
        sys.stderr.write("Error: Project root is not a directory.\n")
        sys.exit(2)

    try:
        result = derive_ledger(root, args.spec_dir, args.records_dir, args.write)
    except OSError:
        sys.stderr.write("Error: OS error while deriving the ledger.\n")
        sys.exit(2)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        _print_text(result)
    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
