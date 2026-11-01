# Task Contract Specification & Validator Reference

This document defines the CLI contract, JSON envelope, exit codes, and strict schema for the Deterministic Agentic Workflow validator (`scripts/validate.py`).

The validator is a read-only, stdlib Python (3.10+) utility. It performs structural and boundary checks on the skill package and project task contracts.

---

## 1. CLI Invocation

All paths to the script MUST resolve from the skill's actual location, never assuming the current working directory is the skill directory or the project root.

### Copyable Command Examples:

Set `SKILL_DIR` to the resolved skill directory and `PROJECT_DIR` to the target project directory:

```bash
SKILL_DIR="/path/to/skill"
PROJECT_DIR="/path/to/project"

# Validate package integrity
python3 "$SKILL_DIR/scripts/validate.py" package

# Validate package with explicit root and JSON output envelope
python3 "$SKILL_DIR/scripts/validate.py" package --root "$SKILL_DIR" --format json

# Validate project task contract at planning stage (project-relative contract file)
python3 "$SKILL_DIR/scripts/validate.py" contract task-contract.json --project-root "$PROJECT_DIR" --stage plan

# Validate project task contract with absolute contract file path
python3 "$SKILL_DIR/scripts/validate.py" contract "$PROJECT_DIR/task-contract.json" --project-root "$PROJECT_DIR" --stage execute

# Validate project task contract at completion stage
python3 "$SKILL_DIR/scripts/validate.py" contract task-contract.json --project-root "$PROJECT_DIR" --stage complete --format json
```

### Arguments & Defaults

- `package`:
  - `--root SKILL_DIR`: Optional. Defaults to the resolved parent directory of `scripts/` (the skill package root).
  - `--format text|json`: Output format (`text` or `json`). Defaults to `text`.
- `contract`:
  - `FILE`: Path to the JSON task contract file. May be specified as a project-root-relative path or an absolute path.
  - `--project-root DIR`: Required. Absolute or relative path to the target project root. All document paths, baseline files, and evidence references are bounded project-relative paths within this root.
  - `--stage plan|execute|complete`: Lifecycle stage. Defaults to `plan`.
  - `--format text|json`: Output format (`text` or `json`). Defaults to `text`.

### Exit Codes

| Exit Code | Meaning                      | Details                                                                                               |
| --------- | ---------------------------- | ----------------------------------------------------------------------------------------------------- |
| `0`       | **Valid**                    | All structural checks passed for the requested stage. Non-blocking warnings may be present.           |
| `1`       | **Validation Error**         | Schema violation, boundary escape, missing required field, hash mismatch, or stage gating failure.    |
| `2`       | **Input / Invocation Error** | Missing file, malformed JSON (including duplicate keys), invalid CLI arguments, or unreadable inputs. |

_Note: CLI syntax errors handled directly by `argparse` print standard error text to `stderr` and exit with code 2._

---

## 2. Invariants & Scope Limitations

The validator is deliberately bounded and **fail-closed**:

1. **Approval Presence vs. Runtime Authorization:** The validator verifies structural presence and field equality (`action`, `target`, `revision`, `scope`) of an opaque approval reference. It **never** authenticates human signatures, verifies external identity providers, or grants runtime execution permission.
2. **Hash Integrity vs. Live Git History:** Baseline file verification confirms that recorded SHA-256 digests match file contents on disk at validation time. Revision strings are treated as opaque identifiers; the validator does **not** query Git history, verify commit existence, or validate branch heads.
3. **Evidence Existence vs. Semantic Truth:** The validator confirms evidence reference files exist within `--project-root` and correspond to declared Acceptance Criteria IDs. It **never** executes evidence references, verifies command outputs, or proves test suite semantic truth.
4. **No Risk Inference:** The validator enforces schema requirements for declared `risk` (`"low"` or `"high"`), but does **not** classify or infer risk levels from code diffs or objectives.
5. **Read-Only Behavior:** The validator strictly reads files; it never writes files, never spawns subprocesses (no Git CLI or shell execution), and never connects to network endpoints.
6. **Project-Relative vs. Contract Path Resolution:** The contract `FILE` argument may be absolute or project-root-relative. All internal contract fields (`baseline.files[].path`, `documents[].path`, `evidence[].reference`) MUST be strict project-relative paths that resolve within `--project-root` without directory traversal (`..`) or symlink escapes.
7. **Supported Metadata Subset:** Frontmatter validation supports standard `name`, `description`, and `compatibility` string fields in the standard Agent Skills format. It is an explicit parser for this subset, not a generic full-YAML/multi-document parser.
8. **Markdown Link & Code Fence Integrity:** Markdown links (`[label](path)`) and reference definitions (`[label]: path`) must resolve within the package root (with URL percent-encoding supported). Proprietary host-specific URI schemes outside code fences are rejected.
9. **Diagnostic Safety:** Diagnostic messages and error outputs use static diagnostic codes and paths, never echoing raw file contents, credentials, tokens, or untrusted payload values.
10. **JSON Strictness:** Duplicate keys at any level (root or nested) are strictly rejected as invalid JSON (exit code 2). Python booleans (`True`/`False`) are not accepted in place of integers.

---

## 3. JSON Output Envelope

When `--format json` is specified, stdout contains a single JSON object adhering to this envelope:

```json
{
  "schema_version": 1,
  "check": "package",
  "valid": true,
  "findings": [
    {
      "severity": "warning",
      "code": "baseline_unverified",
      "path": "baseline.files",
      "message": "Baseline file list is empty; pre-execution state cannot be verified against file hashes."
    }
  ],
  "limitations": [
    "Structural verification only; does not authenticate evidence authenticity, runtime safety, or operational authorization."
  ]
}
```

### Envelope Fields

- `schema_version` (_integer_): Exactly `1`.
- `check` (_string_): Either `"package"` or `"contract"`.
- `valid` (_boolean_): `true` if there are zero `error` severity findings; `false` otherwise.
- `findings` (_array of objects_): List of diagnostic findings.
  - `severity` (_string_): `"error"` (fails validation, triggers exit 1) or `"warning"` (does not fail validation, allows exit 0).
  - `code` (_string_): Machine-readable diagnostic code (e.g., `baseline_changed`, `missing_approval`, `invalid_stage`).
  - `path` (_string_): Contract key path or package-relative file path associated with the finding.
  - `message` (_string_): Human-readable explanation.
- `limitations` (_array of strings_): Explicit statements of what the validator did NOT verify.

---

## 4. Package Validation Checks

When running `validate.py package`, the following checks are enforced:

1. **Required Files & Directories:**
   - `SKILL.md`
   - `references/routing.md`
   - `references/operations.md`
   - `references/validation.md`
   - `references/installation.md`
   - `references/task-contract.example.json`
   - `scripts/validate.py`
   - `tests/test_validate.py`
   - `templates/` containing exactly the 13 canonical document templates:
     `brd.md`, `prd.md`, `frd.md`, `techstack.md`, `blueprint.md`, `design.md`, `ui-ux.md`, `wireframe.md`, `roadmap.md`, `runbook.md`, `deployment.md`, `security.md`, `qa.md`. (Unrecognized extra Markdown files in `templates/` trigger validation errors).
2. **Frontmatter Validation:**
   - `name`: Must match the directory name (e.g., `deterministic-agentic-workflow`), non-empty, alphanumeric + hyphens, $\le 64$ characters.
   - `description`: Non-empty string, $\le 1024$ characters.
   - `compatibility`: Optional string, $\le 500$ characters.
   - Scalar parsing handles plain, single/double quoted, and multi-line literal/folded strings. (This validates required frontmatter fields, not universal YAML specifications).
3. **No Non-Portable References:**
   - Prohibits proprietary or host-specific skill URI schemes outside code blocks in instructions.
4. **Link & Code Fence Integrity:**
   - All internal Markdown links (`[label](path)`) must resolve to existing files within the package root. Remote (`http://`, `https://`, `mailto:`) and in-page anchor (`#...`) links are permitted. Links attempting traversal outside the package root are rejected.
   - Markdown code fences (` ``` ` or `~~~`) must be properly balanced.
5. **Routing Reference Structure:**
   - `references/routing.md` must contain 13 sections for the 13 document types, each including the mandatory structural labels: `Trigger`, `Inputs & Prerequisites`, `Primary Skill`, `Conditional Skills`, `Template Link`, `Output Contract`, `Exit Criterion`, `Downstream Handoff`, and `Stop / Replan Trigger`.

---

## 5. Task Contract Schema (Strict Specification)

Task contracts represent deterministic boundaries between planning and execution. All keys are strict; unrecognized keys are rejected to catch typos.

### Root Object

| Field                 | Type    | Required | Description                                                                                        |
| --------------------- | ------- | -------- | -------------------------------------------------------------------------------------------------- |
| `schema_version`      | integer | Yes      | Must be exactly `1`.                                                                               |
| `objective`           | string  | Yes      | Non-blank description of the task objective.                                                       |
| `baseline`            | object  | Yes      | Pre-task snapshot of relevant files and revision context.                                          |
| `documents`           | array   | Yes      | Array of 13-doc specification records (can be empty for routine patches).                          |
| `acceptance_criteria` | array   | Yes      | Non-empty array of verifiable criteria.                                                            |
| `operation`           | object  | Yes      | The planned state mutation operation.                                                              |
| `approval`            | object  | No       | Captured user approval reference (mandatory for high-risk operations at `execute` and `complete`). |
| `evidence`            | array   | No       | Verification records mapped to Acceptance Criteria (mandatory at `complete`).                      |

---

### Nested Schemas

#### 1. `baseline` (object)

Captures pre-mutation state.

- `revision` (_string, required_): Non-blank VCS commit hash, snapshot tag, or opaque working tree revision ID. (Used for context binding, not verified via Git).
- `files` (_array of objects, required_):
  - Each entry:
    - `path` (_string, required_): Project-root-relative path to an existing file. Must not escape root.
    - `sha256` (_string, required_): 64-character lowercase hexadecimal SHA-256 digest of the file contents.
  - Stage rules:
    - `plan`: Empty `files` array is permitted but triggers a `baseline_unverified` warning.
    - `execute` & `complete`: At least 1 file entry is required universally; an empty `files` array triggers a validation error.
  - Mismatch: If any file's current on-disk SHA-256 does not match, a `baseline_changed` error is emitted.

#### 2. `documents` (array of objects)

Tracks document-driven governance artifacts.

- Each entry:
  - `kind` (_string, required_): One of the 13 canonical document stems:
    `brd`, `prd`, `frd`, `techstack`, `blueprint`, `design`, `ui-ux`, `wireframe`, `roadmap`, `runbook`, `deployment`, `security`, `qa`.
  - `path` (_string, required_): Project-root-relative path to the document file. File must exist.
  - `status` (_string, required_): One of `"current"`, `"draft"`, `"stale"`, `"conflicting"`.
- Stage rules:
  - `stale` or `conflicting` status: Rejected with an error across **all** stages.
  - `draft` status: Permitted during `plan`; rejected with an error during `execute` and `complete`.
  - Zero documents permitted for small routine bug fixes or patches where acceptance criteria and baseline suffice.

#### 3. `acceptance_criteria` (array of objects)

- Array must be non-empty across all stages.
- Each entry:
  - `id` (_string, required_): Non-blank unique identifier (e.g., `"AC-1"`, `"AC-2"`).
  - `criterion` (_string, required_): Non-blank specification of observable result.

#### 4. `operation` (object)

Defines the exact action to be executed.

- `risk` (_string, required_): `"low"` or `"high"`.
- `action` (_string, required_): Non-blank action descriptor (e.g., `"refactor"`, `"delete"`, `"migrate"`, `"deploy"`).
- `target` (_string, required_): Non-blank target entity or component name.
- `revision` (_string, required_): Must match `baseline.revision` exactly.
- `scope` (_array of strings, required_): Non-empty list of unique non-blank strings defining target subsystems or files.

#### 5. `approval` (object, optional)

Records captured explicit user confirmation.

- `reference` (_string, required_): Non-blank opaque reference (e.g., ticket number, session interaction ID, PR review ID). **MUST NOT contain secrets, tokens, or credentials.**
- `action` (_string, required_): Must match `operation.action`.
- `target` (_string, required_): Must match `operation.target`.
- `revision` (_string, required_): Must match `operation.revision`.
- `scope` (_array of strings, required_): Must match `operation.scope` elements exactly (order-independent set equality).
- Stage rules:
  - If `operation.risk` is `"high"` and stage is `"execute"` or `"complete"`, `approval` is **mandatory**. Omission produces a `missing_approval` error.
  - If `approval` is provided at any stage (even for `"low"` risk), all binding fields (`action`, `target`, `revision`, `scope`) must match `operation` exactly. Mismatches produce a `binding_mismatch` error.

#### 6. `evidence` (array of objects, optional)

Records verifiable artifacts demonstrating AC satisfaction.

- Each entry:
  - `criterion_id` (_string, required_): Must match an `id` declared in `acceptance_criteria`.
  - `status` (_string, required_): One of `"passed"`, `"failed"`, `"blocked"`, `"unexercised"`.
  - `reference` (_string, required_): Project-root-relative path to an existing evidence artifact file (e.g., log file, test report, diff output). File must exist within project root.
  - `summary` (_string, required_): Non-blank description of observed output.
- Stage rules:
  - `plan`: Evidence array is optional; typically empty.
  - `execute`: Evidence may be partially populated. Any non-`passed` status is reported.
  - `complete`: Every declared acceptance criterion MUST have exactly one `evidence` entry with `status: "passed"`. Any missing, duplicate, or unpassed criterion produces an error.
