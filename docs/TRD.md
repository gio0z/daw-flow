# Technical Requirements Document (TRD)

## Deterministic Agentic Workflow

### CONTEXT-MAP

```
[Agent System / Caller / CI Runner]
               |
               v
 [scripts/validate.py CLI Entrypoint]
      |                        |
      v                        v
[check: package]         [check: contract]
      |                        |
      +---> Path Resolution    +---> Path Resolution (Project Root Boundary)
      +---> Symlink Escape     +---> Symlink Escape Verification
      +---> Frontmatter Subset +---> Strict JSON Parser (_strict_json_object_pairs_hook)
      +---> Markdown Link/URI  +---> Schema & Stage Enforcement (plan | execute | complete)
      +---> Template Inventory +---> Baseline File Hash (SHA-256) Check
                               +---> Operation / Approval Binding Verification
                               +---> Evidence Artifact Path Verification
                                       |
                                       v
                     [Structured Diagnostic Output]
                     (Exit 0: clean/warning, Exit 1: violation, Exit 2: usage/JSON syntax)
                     (Format: text stdout/stderr or JSON stdout envelope)
```

---

### 1. Architectural Overview & System Design

The Deterministic Agentic Workflow system is an offline, read-only, zero-dependency validation suite and documentation specification implemented in Python 3.10+ standard library. The core operational component is `scripts/validate.py`, which provides structural, boundary, and integrity verification for two independent operational surfaces:

1. **Agent Skill Package (`package` check):** Verifies the internal structural integrity of the workflow package itself, including YAML frontmatter scalar metadata, canonical template existence, routing table cross-references, URI schemes, and local markdown hyperlink targets.
2. **Task Contract (`contract` check):** Verifies machine-readable task execution contracts (`task-contract.json`) that bind operational planning, baseline file hashes, risk-tiered user approval references, and empirical evidence artifacts before, during, and after agent filesystem modifications.

The tool strictly avoids external package manager dependencies (e.g., PyPI packages, wheels, or virtualenvs), background daemons, network communication, and database engines.

---

### 2. Runtime Environment & Target Compatibility

- **Target Language Version:** Python 3.10+ standard library.
- **Verified Host Runtime:** Python 3.14.7 (Linux x86_64, kernel 7.2.5-3-omarchy).
- **Execution Constraints:**
  - Standard library modules only: `argparse`, `hashlib`, `json`, `os`, `pathlib`, `re`, `sys`, `urllib.parse`, `typing`.
  - Zero external dependencies: no `pyyaml`, `jsonschema`, `pydantic`, or binary compiled extensions.
  - Read-only execution: validator never creates, alters, or removes filesystem entities.

---

### 3. Command-Line Interface (CLI) Specification

The CLI interface exposes two distinct subcommands with deterministic exit codes and standard error reporting.

#### Subcommand 1: `package`

Validates skill package layout and content invariants.

```bash
python3 scripts/validate.py package [--root SKILL_DIR] [--format text|json]
```

- `--root SKILL_DIR`: Base directory of the skill package. Defaults to the resolved parent directory of `scripts/` (the repository root).
- `--format text|json`: Output serialization format. Defaults to `text`.

#### Subcommand 2: `contract`

Validates a task execution contract file against a target project workspace.

```bash
python3 scripts/validate.py contract FILE --project-root DIR [--stage plan|execute|complete] [--format text|json]
```

- `FILE`: Relative or absolute path to the task contract JSON file. If relative, resolved against `--project-root`.
- `--project-root DIR`: Target project directory against which contract baselines, scopes, and evidence paths are evaluated.
- `--stage plan|execute|complete`: Contract lifecycle validation stage. Defaults to `plan`.
- `--format text|json`: Output serialization format. Defaults to `text`.

#### Exit Codes & Contracts

- **Exit 0 (Success):** Validation succeeded. In JSON mode, `valid: true`. Warnings may be present in `findings` but do not block progression.
- **Exit 1 (Validation Error):** Validation failed due to one or more structural, boundary, schema, or invariant violations. In JSON mode, `valid: false`.
- **Exit 2 (CLI / JSON Syntax Error):** Execution halted prior to domain validation due to invalid CLI argument usage, missing mandatory flags, unreadable input files, malformed JSON, or duplicate JSON keys.

---

### 4. Security Architecture & Boundary Verification

#### 4.1 Root Boundary Containment & Symlink Defense

All file path parameters (contracts, baseline files, markdown link targets, evidence files) are validated through strict directory containment checks implemented in `resolve_contained_path`:

1. Targets are fully canonicalized via `pathlib.Path.resolve()`.
2. Target paths must be proven descendants of the specified root (`root_dir.resolve()`) using `relative_to(root_dir)`.
3. Symlinks pointing to paths outside the root boundary trigger immediate containment violations (`symlink_escapes_root` or `path_escapes_root`).
4. Boundary checks are executed strictly **before** opening or reading any file contents, preventing symlink traversal attacks, circular symlink deadlocks, and arbitrary file disclosure.

#### 4.2 Untrusted Evidence Artifacts

Evidence references recorded under `evidence[].reference` in task contracts point to project-local log files, test output dumps, or diffs. The validator verifies path containment and physical file existence on disk, but treats file contents as strictly unparsed, untrusted data. The validator never executes scripts or evals payloads found within evidence artifacts.

#### 4.3 Opaque Approval References

Approval data recorded under `approval` captures an opaque reference string (`reference`) alongside matching operation descriptors (`action`, `target`, `revision`, `scope`).

- Approval references represent external human or ticket confirmations (e.g., issue numbers, session tokens, audit hashes).
- Approval captures contain no authentication credentials, API keys, or operational permissions.
- The validator ensures binding consistency between `operation` and `approval`, but does not verify third-party authorization infrastructure.

#### 4.4 Diagnostic Redaction & Information Safety

Diagnostics emitted to stdout or stderr are bounded to static error codes, schema field locations, and relative file paths. Diagnostic messages never echo file contents, environment variables, or potential secret payloads.

---

### 5. Data Formats & Parsing Invariants

#### 5.1 YAML Frontmatter Scalar Parser

The validator includes a custom, strict YAML frontmatter parser for `SKILL.md` designed specifically for the standard Agent Skills metadata subset (`name`, `description`, `compatibility`):

- **Delimiter Integrity:** Frontmatter must start with `---` on line 1 and close with `---`.
- **Scalar Subset:** Supports single-line string scalars, quoted strings (single or double), and multi-line literal/folded block scalars (`>`, `|`, `>-`, `|-`).
- **No Arbitrary Deserialization:** Does not execute Python code, does not load arbitrary YAML objects/tags, and does not parse nested mappings or arbitrary structures.

#### 5.2 Strict Duplicate-Key JSON Parsing

All task contracts parsed by the validator utilize a custom `object_pairs_hook` (`_strict_json_object_pairs_hook`). Duplicate JSON keys at any nesting level raise `DuplicateKeyError`, immediately aborting execution with Exit Code 2.

#### 5.3 Markdown Link & Code Fence Integrity

The package validator scans markdown documents (`SKILL.md`, `references/*.md`, `templates/*.md`) for internal and external links:

- Local file links must resolve to existing files within the package boundary.
- External URLs must use standard public schemes (`http`, `https`, `mailto`).
- Host-specific skill activation URIs are not portable instructions and are rejected outside fenced examples. Inline code spans are ignored for Markdown link extraction, but do not exempt host-specific activation URIs from this check.

---

### 6. Contract Lifecycle Stages & Validation Rules

A task contract (`task-contract.json`) progresses through three distinct lifecycle stages:

| Rule / Field                  | `plan` Stage          | `execute` Stage       | `complete` Stage                |
| :---------------------------- | :-------------------- | :-------------------- | :------------------------------ |
| `task_id`, `version`, `title` | Mandatory             | Mandatory             | Mandatory                       |
| `acceptance_criteria`         | Mandatory (non-empty) | Mandatory (non-empty) | Mandatory (non-empty)           |
| `baseline.revision`           | Mandatory             | Mandatory             | Mandatory                       |
| `baseline.files[].sha256`     | Verified if present   | Verified if present   | Verified if present             |
| `operation` descriptors       | Mandatory             | Mandatory             | Mandatory                       |
| `approval` for `risk: high`   | Optional              | **Mandatory**         | **Mandatory**                   |
| `approval` for `risk: low`    | Optional              | Optional              | Optional                        |
| `evidence` artifact records   | Optional              | Optional              | **Mandatory** (All ACs covered) |
| `evidence` physical files     | Verified if present   | Verified if present   | **Mandatory** (Must exist)      |
| `evidence[].status`           | Any valid status      | Any valid status      | **Must be `"passed"`**          |

---

### 7. Regression Strategy & Verification Suite

The repository contains an automated regression suite in `tests/test_validate.py` consisting of 56 unit tests executed via standard Python `unittest`.

#### Test Coverage Categories

1. **CLI Execution & Exit Codes:** Verifies exit codes 0, 1, and 2 across all subcommands, invalid flag invocations, and non-existent file inputs.
2. **Package Structural Checks:** Verifies frontmatter parsing, missing template detection, broken link handling, code fence exemption logic, and canonical template mapping.
3. **Contract Schema & Type Validation:** Validates required fields, type restrictions, rejection of booleans for integer fields, and duplicate key rejection.
4. **Boundary & Path Resolution:** Exercises directory traversal prevention (`../` sequences), escaping symlinks, broken symlinks, and absolute path containment across project roots.
5. **Approval Binding Invariants:** Verifies exact order-independent scope match, action match, target match, revision match, and risk-tier enforcement across stages.
6. **Baseline Hash Verification:** Tests SHA-256 calculation against target project files, handling missing files, modified contents, and empty baseline arrays.
7. **Evidence & Completion Verification:** Verifies complete 1:1 acceptance criteria mapping, status validation (`passed`, `failed`, `blocked`, `unexercised`), and missing evidence file detection.

---

### 8. Known Limitations & Non-Guarantees

1. **No Concurrency / TOCTOU Protection:** The validator is a point-in-time check. It does not lock target files or prevent concurrent filesystem modifications occurring between validation and task execution.
2. **No Semantic Verification:** Validates syntactic structure, reference consistency, and hash matches; does not evaluate the qualitative correctness or semantic intent of code changes or prompt instructions.
3. **Self-Declared Baseline Revisions:** The validator does not query VCS (git) history to verify whether `baseline.revision` corresponds to a genuine remote or local git commit hash.
4. **No Sandbox Execution:** The validator does not isolate or execute code; test suite invocation is governed by external CI runners or developer commands.

---

### BLOCKERS

- None. The technical architecture is fully realized in `scripts/validate.py` with zero external dependencies and 100% test passing rate across the 56-test regression suite under Python 3.14.7.
