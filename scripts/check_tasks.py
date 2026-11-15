"""Task manifest validation (`validate.py tasks`) and task-file sourcing.

The task list has one authoritative source per workflow, and the machine
manifest is a *projection* of it:

- **Hand-authored source:** one Markdown file per task, each with a structured
  frontmatter block and a free-prose body. Frontmatter values may be a scalar,
  an inline JSON value, or an indented ``- item`` list. This is what a human
  edits.
- **Derived projection:** a fenced ```json block directly after the
  ``<!-- daw-task-manifest -->`` marker in the plan. It is generated from the
  task files by ``scripts/derive_tasks.py --write`` and is never hand-edited.

A plan that declares no task-source directory keeps the embedded block as its
own hand-authored manifest; the two modes never mix.

This module owns the structural rules for both forms. It is read-only: it
never writes files, never executes commands, and never decides acceptance.
"""

from __future__ import annotations

import pathlib
import re
from typing import Any

try:
    from scripts.daw_common import (
        build_result,
        is_safe_relative_path,
        make_error,
        parse_strict_json,
    )
except ImportError:
    from daw_common import (  # type: ignore[import-not-found]
        build_result,
        is_safe_relative_path,
        make_error,
        parse_strict_json,
    )

TASK_LIMITATIONS = [
    "Structural validation only; never executes a task, never accepts a task, and never evaluates semantic truth.",
    "The manifest is validated as a self-contained DAG: dependency, uniqueness, autonomy, and path safety only.",
    "Evidence referenced by a task is not verified here; verification evidence is produced by the runner's verify step.",
    "Drift detection compares the embedded manifest against the derived projection of the task files; it never re-derives a task field.",
]

MANIFEST_MARKER = "<!-- daw-task-manifest -->"
MANIFEST_SCHEMA_VERSION = 1

#: Plan marker naming the directory holding this workflow's hand-authored task
#: files. Its value is a project-relative directory path.
SOURCES_MARKER_RE = re.compile(r"<!--\s*daw-task-sources:\s*(?P<path>[^>]+?)\s*-->")

ALLOWED_MANIFEST_FIELDS = {"schema_version", "workflow_id", "tasks"}
ALLOWED_TASK_FIELDS = {
    "task_id",
    "title",
    "autonomy",
    "depends_on",
    "parallel_safe",
    "target_files",
    "acceptance_criteria",
    "verification_command",
    "expected_outcome",
    "steps",
    "interfaces",
    "context_files",
    "notes",
}
REQUIRED_TASK_FIELDS = (
    "task_id",
    "title",
    "autonomy",
    "depends_on",
    "parallel_safe",
    "target_files",
    "acceptance_criteria",
    "verification_command",
    "expected_outcome",
)

_JSON_PARSE_ERRORS = (ValueError, RecursionError)


def extract_manifest(plan_text: str) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    """Return the task manifest carried by a plan document.

    The manifest is the fenced ```json block that directly follows the
    ``<!-- daw-task-manifest -->`` marker. The marker makes the block
    unambiguous inside a plan that may contain other JSON examples, and it is
    the literal token the route flow gate looks for. Exactly one marker and one
    parsable block are required; zero or several is an ambiguity error, never a
    guess.
    """
    findings: list[dict[str, str]] = []
    markers = [m.start() for m in re.finditer(re.escape(MANIFEST_MARKER), plan_text)]
    if not markers:
        findings.append(
            make_error(
                "manifest_missing",
                "plan",
                f"Plan contains no {MANIFEST_MARKER} marker; the task manifest is absent.",
            )
        )
        return None, findings
    if len(markers) > 1:
        findings.append(
            make_error(
                "manifest_ambiguous",
                "plan",
                f"Plan contains {len(markers)} {MANIFEST_MARKER} markers; exactly one is required.",
            )
        )
        return None, findings
    tail = plan_text[markers[0] + len(MANIFEST_MARKER) :]
    match = re.search(r"```json\s*\n(.*?)\n```", tail, re.DOTALL)
    if match is None:
        findings.append(
            make_error(
                "manifest_missing",
                "plan",
                f"No fenced ```json block follows the {MANIFEST_MARKER} marker.",
            )
        )
        return None, findings
    try:
        parsed = parse_strict_json(match.group(1))
    except _JSON_PARSE_ERRORS as exc:
        findings.append(
            make_error("manifest_malformed", "plan", f"Task manifest is not strict JSON: {exc}.")
        )
        return None, findings
    if not isinstance(parsed, dict) or not isinstance(parsed.get("tasks"), list):
        findings.append(
            make_error(
                "manifest_malformed",
                "plan",
                "Task manifest must be an object with a 'tasks' array.",
            )
        )
        return None, findings
    return parsed, findings


def validate_task_fields(task: dict[str, Any], label: str) -> list[dict[str, str]]:
    """Validate one task's own fields, without looking at other tasks.

    Cross-task rules (duplicate ids, unknown dependencies, cycles) belong to
    `validate_manifest`, so a single task file can be checked on its own.
    """
    findings: list[dict[str, str]] = []
    unknown = sorted(set(task) - ALLOWED_TASK_FIELDS)
    if unknown:
        findings.append(make_error("task_unknown_field", label, f"Unknown task field(s): {', '.join(unknown)}."))
    missing = [f for f in REQUIRED_TASK_FIELDS if f not in task]
    if missing:
        findings.append(
            make_error("task_missing_field", label, f"Missing required task field(s): {', '.join(missing)}.")
        )
        return findings
    task_id = task["task_id"]
    if not isinstance(task_id, str) or not task_id.strip():
        findings.append(make_error("task_id_invalid", f"{label}.task_id", "task_id must be a non-blank string."))
        return findings
    if task["autonomy"] not in ("afk", "hitl"):
        findings.append(make_error("task_autonomy_invalid", f"{label}.autonomy", "autonomy must be 'afk' or 'hitl'."))
    depends_on = task["depends_on"]
    if not isinstance(depends_on, list) or not all(isinstance(d, str) and d.strip() for d in depends_on):
        findings.append(
            make_error("task_depends_on_invalid", f"{label}.depends_on", "depends_on must be an array of task ids.")
        )
    for field in ("target_files", "acceptance_criteria"):
        value = task[field]
        if not isinstance(value, list) or not value or not all(isinstance(v, str) and v.strip() for v in value):
            findings.append(
                make_error(f"task_{field}_invalid", f"{label}.{field}", f"{field} must be a non-empty array of strings.")
            )
    for field in ("verification_command", "expected_outcome", "title"):
        if not isinstance(task[field], str) or not task[field].strip():
            findings.append(
                make_error(f"task_{field}_invalid", f"{label}.{field}", f"{field} must be a non-blank string.")
            )
    if not isinstance(task["parallel_safe"], bool):
        findings.append(
            make_error("task_parallel_safe_invalid", f"{label}.parallel_safe", "parallel_safe must be a boolean.")
        )
    for path in task["target_files"] if isinstance(task["target_files"], list) else []:
        if isinstance(path, str) and not is_safe_relative_path(path):
            findings.append(
                make_error("task_target_file_unsafe", f"{label}.target_files", f"Unsafe or absolute path {path!r}.")
            )
    return findings


def validate_manifest(manifest: dict[str, Any]) -> list[dict[str, str]]:
    """Structurally validate a task manifest. Empty findings means valid."""
    findings: list[dict[str, str]] = []
    unknown_manifest = sorted(set(manifest) - ALLOWED_MANIFEST_FIELDS)
    if unknown_manifest:
        findings.append(
            make_error(
                "manifest_unknown_field",
                "manifest",
                f"Unknown manifest field(s): {', '.join(unknown_manifest)}.",
            )
        )
    version = manifest.get("schema_version")
    if isinstance(version, bool) or not isinstance(version, int) or version != MANIFEST_SCHEMA_VERSION:
        findings.append(
            make_error(
                "manifest_schema_version_invalid",
                "manifest.schema_version",
                f"schema_version must be integer {MANIFEST_SCHEMA_VERSION}.",
            )
        )
    tasks = manifest.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        findings.append(make_error("manifest_tasks_invalid", "manifest.tasks", "tasks must be a non-empty array."))
        return findings
    seen: set[str] = set()
    for index, task in enumerate(tasks):
        label = f"manifest.tasks[{index}]"
        if not isinstance(task, dict):
            findings.append(make_error("task_invalid", label, "Each task must be an object."))
            continue
        findings.extend(validate_task_fields(task, label))
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or not task_id.strip():
            continue
        if task_id in seen:
            findings.append(make_error("task_id_duplicate", f"{label}.task_id", f"Duplicate task_id {task_id!r}."))
        seen.add(task_id)
    known = {t.get("task_id") for t in tasks if isinstance(t, dict) and isinstance(t.get("task_id"), str)}
    for index, task in enumerate(tasks):
        if not isinstance(task, dict) or not isinstance(task.get("depends_on"), list):
            continue
        for dep in task["depends_on"]:
            if isinstance(dep, str) and dep not in known:
                findings.append(
                    make_error(
                        "task_dependency_unknown",
                        f"manifest.tasks[{index}].depends_on",
                        f"Dependency {dep!r} is not declared in the manifest.",
                    )
                )
    findings.extend(detect_cycles(tasks))
    return findings


def detect_cycles(tasks: list[Any]) -> list[dict[str, str]]:
    """Report dependency cycles deterministically.

    Uses Kahn's algorithm: any task still holding unresolved dependencies after
    the graph is exhausted participates in a cycle. The reported set is sorted,
    so the same manifest always yields the same finding.
    """
    graph: dict[str, list[str]] = {}
    for task in tasks:
        if isinstance(task, dict) and isinstance(task.get("task_id"), str):
            deps = task.get("depends_on")
            graph[task["task_id"]] = [d for d in deps if isinstance(d, str)] if isinstance(deps, list) else []
    indegree = {node: 0 for node in graph}
    dependents: dict[str, list[str]] = {node: [] for node in graph}
    for node, deps in graph.items():
        for dep in deps:
            if dep in graph:
                indegree[node] += 1
                dependents[dep].append(node)
    queue = sorted(node for node, degree in indegree.items() if degree == 0)
    processed = 0
    while queue:
        node = queue.pop(0)
        processed += 1
        for child in sorted(dependents[node]):
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
                queue.sort()
    if processed == len(graph):
        return []
    involved = sorted(node for node, degree in indegree.items() if degree > 0)
    return [
        make_error(
            "task_dependency_cycle",
            "manifest.tasks",
            "Dependency cycle among task(s): " + ", ".join(involved),
        )
    ]


def topological_depth(tasks: list[dict[str, Any]]) -> dict[str, int]:
    """Return each task's depth in the dependency DAG (0 for roots).

    Independent of declaration order and never recurses; cycles are rejected
    earlier by manifest validation.
    """
    ids = {t["task_id"] for t in tasks if isinstance(t, dict) and isinstance(t.get("task_id"), str)}
    indegree = {task_id: 0 for task_id in ids}
    dependents: dict[str, list[str]] = {task_id: [] for task_id in ids}
    for task in tasks:
        if not isinstance(task, dict) or not isinstance(task.get("task_id"), str):
            continue
        for dep in task.get("depends_on", []) or []:
            if dep in ids:
                indegree[task["task_id"]] += 1
                dependents[dep].append(task["task_id"])
    depth = {task_id: 0 for task_id in ids}
    queue = sorted(task_id for task_id, degree in indegree.items() if degree == 0)
    while queue:
        node = queue.pop(0)
        for child in sorted(dependents[node]):
            depth[child] = max(depth[child], depth[node] + 1)
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
                queue.sort()
    return depth


def validate_plan_manifest(
    plan_path: pathlib.Path, project_root: pathlib.Path | None = None
) -> dict[str, Any]:
    """Validate the task manifest carried by one plan document.

    When the plan declares a task-source directory, the embedded manifest is
    compared against the projection of those task files and any difference is
    reported as drift. The task files stay the hand-authored source; the
    embedded block is its derived form.
    """
    findings: list[dict[str, str]] = []
    manifest: dict[str, Any] | None = None
    try:
        text = plan_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        findings.append(
            makemake_error("manifest_unreadable", str(plan_path), "Plan cannot be read as UTF-8 text.")
        )
    else:
        manifest, extract_findings = extract_manifest(text)
        findings.extend(extract_findings)
        if manifest is not None:
            findings.extend(validate_manifest(manifest))
            sources = extract_sources(text)
            if sources and project_root is not None:
                findings.extend(check_source_drift(sources, manifest, project_root, plan_path))
    tasks = manifest.get("tasks") if isinstance(manifest, dict) else None
    return build_result(
        "tasks",
        findings,
        TASK_LIMITATIONS,
        extra={
            "task_count": len(tasks) if isinstance(tasks, list) else 0,
            "workflow_id": manifest.get("workflow_id") if isinstance(manifest, dict) else None,
        },
    )


# ---------------------------------------------------------------------------
# Hand-authored task files (the source of truth)
# ---------------------------------------------------------------------------


def extract_sources(plan_text: str) -> str | None:
    """Return the declared task-source directory, or None when the plan has none."""
    match = SOURCES_MARKER_RE.search(plan_text)
    if match is None:
        return None
    return match.group("path")


def _parse_scalar(raw: str) -> Any:
    """Parse a frontmatter value: JSON literal when it looks like one, else text."""
    text = raw.strip()
    if text.startswith(("[", "{")) or text in ("true", "false", "null"):
        try:
            return parse_strict_json(text)
        except (ValueError, RecursionError):
            return text
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1]
    return text


def parse_task_file(
    text: str, label: str
) -> tuple[dict[str, Any] | None, str, list[dict[str, str]]]:
    """Parse one task file: a frontmatter block plus a free-prose body.

    Frontmatter values accept three forms: a plain scalar, an inline JSON
    value, or an indented ``- item`` list. Unknown keys and unparsable blocks
    are findings, never silent omissions. The prose body is returned
    separately: it is human context, not a machine field.
    """
    findings: list[dict[str, str]] = []
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        findings.append(
            make_error("task_file_frontmatter_missing", label, "Task file must start with a '---' frontmatter block.")
        )
        return None, "", findings
    end = -1
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    if end == -1:
        findings.append(
            make_error("task_file_frontmatter_missing", label, "Task file frontmatter block is not closed with '---'.")
        )
        return None, "", findings

    fields: dict[str, Any] = {}
    current_key: str | None = None
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indented = raw[:1] in (" ", "\t")
        if indented and current_key is not None:
            item = raw.strip()
            if not item.startswith("- "):
                findings.append(
                    make_error("task_file_field_invalid", f"{label}.{current_key}", "Indented lines must be '- item' list entries.")
                )
                continue
            value = _parse_scalar(item[2:])
            if not isinstance(fields.get(current_key), list):
                fields[current_key] = []
            fields[current_key].append(value)
            continue
        match = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", raw)
        if match is None:
            findings.append(
                make_error("task_file_field_invalid", label, f"Unparsable frontmatter line: {raw.strip()!r}.")
            )
            continue
        key = match.group(1)
        if key in fields:
            findings.append(
                make_error("task_file_field_duplicate", f"{label}.{key}", f"Duplicate frontmatter key {key!r}.")
            )
            continue
        raw_value = match.group(2).strip()
        current_key = key
        if raw_value == "":
            fields[key] = []
        else:
            fields[key] = _parse_scalar(raw_value)

    unknown = sorted(set(fields) - ALLOWED_TASK_FIELDS)
    if unknown:
        findings.append(
            make_error("task_unknown_field", label, f"Unknown task field(s): {', '.join(unknown)}.")
        )
    missing = [f for f in REQUIRED_TASK_FIELDS if f not in fields]
    if missing:
        findings.append(
            make_error("task_missing_field", label, f"Missing required task field(s): {', '.join(missing)}.")
        )
        return None, "", findings

    body = "\n".join(lines[end + 1 :]).strip()
    task = {key: fields[key] for key in fields}
    findings.extend(validate_task_fields(task, label))
    return task, body, findings


def load_task_files(
    directory: pathlib.Path,
) -> tuple[list[dict[str, Any]], dict[str, str], list[dict[str, str]]]:
    """Load and validate every task file in a directory, sorted by file name.

    Returns (tasks, bodies, findings) where ``bodies`` maps task id to the
    file's prose body.
    """
    findings: list[dict[str, str]] = []
    tasks: list[dict[str, Any]] = []
    bodies: dict[str, str] = {}
    if not directory.is_dir():
        findings.append(
            make_error("task_source_missing", str(directory), "Declared task-source directory does not exist.")
        )
        return tasks, bodies, findings
    for path in sorted(directory.glob("*.md")):
        rel = path.name
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            findings.append(
                make_error("task_file_unreadable", rel, "Task file cannot be read as UTF-8 text.")
            )
            continue
        task, body, task_findings = parse_task_file(text, rel)
        findings.extend(task_findings)
        if task is not None:
            tasks.append(task)
            if body:
                bodies[str(task.get("task_id", ""))] = body
    if not tasks and not findings:
        findings.append(
            make_error("task_source_empty", str(directory), "Task-source directory contains no Markdown task file.")
        )
    findings.extend(validate_manifest({"schema_version": MANIFEST_SCHEMA_VERSION, "tasks": tasks}))
    return tasks, bodies, findings


def derive_manifest(tasks: list[dict[str, Any]], workflow_id: str | None = None) -> dict[str, Any]:
    """Project task files into the machine manifest.

    Only the fields the manifest defines are copied; the prose body of a task
    file is not part of the machine form.
    """
    projected: list[dict[str, Any]] = []
    for task in sorted(tasks, key=lambda t: str(t.get("task_id", ""))):
        entry = {key: task[key] for key in REQUIRED_TASK_FIELDS if key in task}
        for optional in ("steps", "interfaces", "context_files", "notes"):
            if optional in task:
                entry[optional] = task[optional]
        projected.append(entry)
    manifest: dict[str, Any] = {"schema_version": MANIFEST_SCHEMA_VERSION, "tasks": projected}
    if workflow_id:
        manifest["workflow_id"] = workflow_id
    return manifest


def compare_manifests(
    embedded: dict[str, Any],
    derived: dict[str, Any],
    plan_path: pathlib.Path,
    sources: str,
) -> list[dict[str, str]]:
    """Report the field-level difference between two manifests of the same task set."""
    if embedded == derived:
        return []
    embedded_by_id = {t.get("task_id"): t for t in embedded.get("tasks", []) if isinstance(t, dict)}
    derived_by_id = {t.get("task_id"): t for t in derived.get("tasks", []) if isinstance(t, dict)}
    differences: list[str] = []
    for task_id in sorted(set(embedded_by_id) | set(derived_by_id)):
        left = derived_by_id.get(task_id)
        right = embedded_by_id.get(task_id)
        if left is None:
            differences.append(f"{task_id}: present in the plan manifest but not in the task files")
        elif right is None:
            differences.append(f"{task_id}: present in the task files but not in the plan manifest")
        elif left != right:
            differing = sorted(k for k in set(left) | set(right) if left.get(k) != right.get(k))
            differences.append(f"{task_id}: differs in {', '.join(differing)}")
    return [
        make_error(
            "manifest_drift",
            str(plan_path),
            "Plan manifest does not match the task files in "
            f"{sources}. Re-derive it: python3 scripts/derive_tasks.py --plan <plan> --write. "
            + "; ".join(differences),
        )
    ]


def check_source_drift(
    sources: str,
    embedded: dict[str, Any],
    project_root: pathlib.Path,
    plan_path: pathlib.Path,
) -> list[dict[str, str]]:
    """Compare the embedded manifest against the projection of the task files."""
    findings: list[dict[str, str]] = []
    directory = project_root / sources
    tasks, _bodies, load_findings = load_task_files(directory)
    if load_findings:
        return load_findings
    workflow_id = embedded.get("workflow_id")
    derived = derive_manifest(tasks, workflow_id if isinstance(workflow_id, str) else None)
    return compare_manifests(embedded, derived, plan_path, sources)
