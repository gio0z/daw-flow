# Task Contract Specification & Validator Reference

This document defines the CLI contract, JSON envelope, exit codes, and strict schema for the Deterministic Agentic Workflow validator (`scripts/validate.py`).

The validator is a read-only, stdlib Python (3.10+) utility. It performs structural and boundary checks on the skill package and project task contracts.
The validator remains **stateless**: it never persists workflow state, decides parent acceptance, ranks worker findings, or writes spec/plan/progress/mockup artifacts. Artifact selection and persistence for multi-step authorized work follow the canonical [Workflow Artifacts](workflow-artifacts.md) contract; parent triage/acceptance follows [Ranked Result Triage](operations.md#ranked-result-triage). No Python or schema change is made by those references.

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

# Run the read-only aggregate status preflight (config + ledger + task contracts)
python3 "$SKILL_DIR/scripts/validate.py" status --project-root "$PROJECT_DIR" --format json
```

```bash
# Validate documentation workflow transition (intake to authoring)
python3 "$SKILL_DIR/scripts/validate.py" docs doc-transition.json \
  --project-root "$PROJECT_DIR" \
  --transition intake-authoring \
  --documents docs/prd.md docs/architecture.md

# Validate authoring to review transition with JSON output envelope
python3 "$SKILL_DIR/scripts/validate.py" docs doc-transition.json \
  --project-root "$PROJECT_DIR" \
  --transition authoring-review \
  --documents docs/prd.md docs/architecture.md \
  --format json

# Validate review to ready downstream transition
python3 "$SKILL_DIR/scripts/validate.py" docs doc-transition.json \
  --project-root "$PROJECT_DIR" \
  --transition review-ready \
  --documents docs/prd.md docs/architecture.md

# Validate review to rework transition
python3 "$SKILL_DIR/scripts/validate.py" docs doc-transition.json \
  --project-root "$PROJECT_DIR" \
  --transition review-rework \
  --documents docs/prd.md docs/architecture.md

# Validate rework to review transition
python3 "$SKILL_DIR/scripts/validate.py" docs doc-transition.json \
  --project-root "$PROJECT_DIR" \
  --transition rework-review \
  --documents docs/prd.md docs/architecture.md
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

- `docs`:
  - `RECORD`: Path to the JSON documentation transition record file. May be specified as a project-root-relative path or an absolute path within `--project-root`.
  - `--project-root DIR`: Required. Absolute or relative path to the target project root. All target document paths and quoted source evidence files are bounded project-relative paths within this root.
  - `--transition intake-authoring|authoring-review|review-ready|review-rework|rework-review`: Required. Explicit workflow transition edge to validate.
  - `--documents PATH [PATH ...]`: Required. Parent-owned expected target document set (strict project-relative paths). Normalized set equality against the record's declared `documents` is strictly enforced; duplicate targets and alias collisions are rejected. There is no mandatory 14-document requirement; only selected actual documents for the current task.
  - `--format text|json`: Output format (`text` or `json`). Defaults to `text`.

- `ledger`, `config`, `status` (see §8–§10):
  - `ledger FILE` / `config FILE`: the target file (`ledger.json` / agent file); both require `--project-root DIR`.
  - `status`: no `FILE` argument. `--project-root ROOT` (required), optional `--agent-file PATH` (defaults to `AGENTS.md`, else `CLAUDE.md`, under the root), `--format text|json` (defaults to `text`). Exit `2` when the root is not a directory.

### Exit Codes

| Exit Code | Meaning                      | Details                                                                                                                     |
| --------- | ---------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `0`       | **Valid**                    | All structural checks passed for requested stage or transition. Non-blocking warnings may be present.                       |
| `1`       | **Validation Error**         | Schema violation, boundary escape, missing field, hash mismatch, criterion coverage failure, or transition edge violation.  |
| `2`       | **Input / Invocation Error** | Missing file, malformed JSON (including duplicate keys), invalid CLI arguments, unreadable inputs, or invalid project root. |

_Note: CLI syntax errors handled directly by `argparse` print standard error text to `stderr` and exit with code 2._

---

## 2. Invariants & Scope Limitations

The validator is deliberately bounded and **fail-closed**:

1. **Approval Presence vs. Runtime Authorization:** The validator verifies structural presence and field equality (`action`, `target`, `revision`, `scope`) of an opaque approval reference. It **never** authenticates human signatures, verifies external identity providers, or grants runtime execution permission.
2. **Hash Integrity vs. Live Git History:** Baseline file verification confirms that recorded SHA-256 digests match file contents on disk at preflight validation time (`plan` and `execute` stages). At `complete`, the validator enforces historical baseline structure, field schema, and project boundary containment without requiring historical baseline files to remain unchanged or exist on disk (permitting legitimate modifications, renames, and deletions). Revision strings are treated as opaque identifiers; the validator does **not** query Git history, verify commit existence, or validate branch heads.
3. **Evidence Existence vs. Semantic Truth:** The validator confirms evidence reference files exist within `--project-root`, are durable (not under an ephemeral segment), correspond to declared Acceptance Criteria IDs, carry a matching SHA-256 content hash and a revision binding to `result.revision` at `complete`. It **never** executes evidence references, verifies command outputs, proves test suite semantic truth, or evaluates the semantic truth of evidence contents. The parent must open the evidence — the validator never evaluates semantic truth of evidence; the parent must open the evidence to confirm it actually proves the claimed criteria.
4. **No Risk Inference:** The validator enforces schema requirements for declared `risk` (`"low"` or `"high"`), but does **not** classify or infer risk levels from code diffs or objectives.
5. **Read-Only Behavior:** The validator strictly reads files; it never writes files, never spawns subprocesses (no Git CLI or shell execution), and never connects to network endpoints.
6. **Project-Relative vs. Contract Path Resolution:** The contract `FILE` argument may be absolute or project-root-relative. All internal contract fields (`baseline.files[].path`, `documents[].path`, `evidence[].reference`, `result.files[].path`) MUST be strict project-relative paths that resolve within `--project-root` without directory traversal (`..`) or symlink escapes.
7. **Supported Metadata Subset:** Frontmatter validation supports standard Scalar values (strings, numbers, booleans) and lists of strings. Custom tags or complex types trigger validation errors.
8. **Markdown Link & Code Fence Integrity:** Markdown links (`[label](path)`) and reference definitions (`[label]: path`) must resolve within the package root (with URL percent-encoding supported). Proprietary host-specific URI schemes outside code fences are rejected.
9. **Diagnostic Safety:** Diagnostic messages and error outputs use static diagnostic codes and paths, never echoing raw file contents, credentials, tokens, or untrusted payload values.
10. **JSON Strictness:** Duplicate keys at any level (root or nested) are strictly rejected as invalid JSON (exit code 2). Python booleans (`True`/`False`) are not accepted in place of integers.
11. **Explicit Command Gates Not Hooks (`docs`):** The documentation transition validator is a passive, read-only CLI command invoked explicitly by the parent orchestrator. It installs no daemon supervisors, background services, pre-tool hooks, or automated interception mechanisms. The parent orchestrator holds actual workflow state and decides when to execute validation.
12. **Structural Evidence Eligibility vs. Semantic Truth (`docs`):** A `valid: true` (or `eligible: true`) result certifies only that the transition record strictly satisfies schema, path boundary containment, rubric criterion coverage, regular UTF-8 document and source file existence, SHA-256 byte digests, and exact line-range quote matches against decoded text splitlines. It does NOT certify semantic prose truth, technical correctness, design suitability, or runtime success.
13. **Parent-Owned Workflow State & History (`docs`):** The validator is strictly read-only and does not persist state across invocations. The parent orchestrator maintains actual workflow state in task contracts or handoff records. The parent MUST verify that the record's `transition.from` matches the actual accepted current state before recording state advancement.
14. **Opacity of Reviewer (`docs`):** Review exit transitions (`review-ready` and `review-rework`) validate `reviewer` as an object `{"id": "<non-empty string>", "kind": "human" | "agent", "author_id": "<non-empty string>"}`. A bare string `reviewer` is rejected with `invalid_reviewer`. If `reviewer.id` equals `reviewer.author_id` (exact after strip and casefold), validation fails with `reviewer_not_independent`. On `review-ready`, `kind: "agent"` emits warning `reviewer_agent_attestation` but does not flip `valid`. The validator never authenticates human signatures, verifies external identity providers, or certifies reviewer independence beyond this string comparison.
15. **Non-Applicable (N/A) Evidence Attestation (`docs`):** Criteria marked `not_applicable` require non-empty rationale and grounded source evidence objects demonstrating why the criterion does not apply. N/A is an explicit reviewer/author attestation backed by inspectable evidence, not an automated bypass.
16. **Artifact Mutation Invalidates Verdict (`docs`):** Review verdicts (`review-ready`) are cryptographically pinned to document and source SHA-256 byte hashes. Any file modification invalidates prior eligibility, requiring re-entry via `rework`, `rework-review`, and fresh `review-ready` validation. Decision `"accepted"` with status `"blocked"` is invalid across all edges. On `review-rework`, at least one check must have `decision: "not_accepted"`.
17. **No Workflow-Artifact or Triage Semantics:** The validator does not create or rank spec/plan/progress/mockup artifacts, does not persist parent workflow state or the ranked result queue, and does not decide parent acceptance. Those procedural duties live in [Workflow Artifacts](workflow-artifacts.md) and [Ranked Result Triage](operations.md#ranked-result-triage); the validator only checks the structural transition/record it is explicitly invoked on.
18. **Durable Evidence Denylist Limitation (`docs`):** Evidence paths (`sources[].path` and `checks[].evidence[].path`) are rejected with `evidence_not_durable` when the first path segment is `tmp`, `temp`, `.tmp`, `scratch`, or `.cache`, any segment is `__pycache__`, or any segment starts with `.` except `.github`. The validator cannot call git, so this is a deterministic path-segment denylist; it cannot detect gitignored paths that are not on this list.
19. **Result Snapshot Semantics (`contract`):** `baseline` is the pre-change snapshot; `result` is the post-change snapshot recorded after verify. Verify evidence must be produced against `result.revision`. Any edit after recording `result` invalidates completion and requires re-verify. The validator never evaluates the semantic truth of evidence; the parent must open the evidence.

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
- `check` (_string_): One of `"package"`, `"contract"`, `"docs"`, `"ledger"`, `"config"`, or `"status"`.
- `valid` (_boolean_): `true` if there are zero `error` severity findings; `false` otherwise. For `docs`, this indicates eligibility for the requested transition edge.
- `transition` (_string, docs check only_): The requested transition string (e.g., `"review-ready"`).
- `eligible` (_boolean, docs check only_): Identical to `valid`, explicitly naming transition eligibility.
- `summary` (_object, status check only_): `{ "config", "ledger", "tasks": { "complete_valid", "complete_invalid", "in_progress" } }` (see §10).
- `recommended_route` (_string, status check only_): One of `"setup"`, `"upgrade-recheck"`, `"design-rework"`, `"verify"`, `"none"` (see §10).
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
   - `templates/` containing exactly the 14 canonical document templates:
     `brd.md`, `prd.md`, `frd.md`, `techstack.md`, `blueprint.md`, `design.md`, `ui-ux.md`, `wireframe.md`, `roadmap.md`, `runbook.md`, `deployment.md`, `security.md`, `qa.md`, `erd.md`. (Unrecognized extra Markdown files in `templates/` trigger validation errors). Escaping paths or symlinks yield `symlink_escapes_package` (for symlink escapes) or `path_escapes_package` (for non-symlink/traversal boundary escapes).
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
   - `references/routing.md` must contain 14 sections for the 14 document types, each including the mandatory structural labels: `Trigger`, `Inputs & Prerequisites`, `Required Capability`, `Conditional Capabilities`, `Template Link`, `Output Contract`, `Exit Criterion`, `Downstream Handoff`, and `Stop / Replan Trigger`.

6. **Version Consistency:**
   - When `VERSION` exists at the package root, and `SKILL.md` frontmatter defines `metadata.version`, both values must match exactly (`VERSION` stripped; metadata value unquoted). If `VERSION` exists but `metadata.version` is missing or mismatched, a `version_mismatch` error is raised. If `VERSION` is absent, the check is skipped.

---

## 5. Task Contract Schema (Strict Specification)

Task contracts represent deterministic boundaries between planning and execution. All keys are strict; unrecognized keys are rejected to catch typos.

### Root Object

| Field                 | Type    | Required | Description                                                                                                                                        |
| --------------------- | ------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `schema_version`      | integer | Yes      | Must be exactly `1`.                                                                                                                               |
| `objective`           | string  | Yes      | Non-blank description of the task objective.                                                                                                       |
| `baseline`            | object  | Yes      | Pre-change snapshot (`baseline` = pre-change snapshot) of relevant files and revision context.                                                     |
| `documents`           | array   | Yes      | Array of 14-doc specification records (can be empty for routine patches).                                                                          |
| `acceptance_criteria` | array   | Yes      | Non-empty array of verifiable criteria.                                                                                                            |
| `operation`           | object  | Yes      | The planned state mutation operation.                                                                                                              |
| `approval`            | object  | No       | Captured user approval reference (mandatory for high-risk operations at `execute` and `complete`).                                                 |
| `evidence`            | array   | No       | Verification records mapped to Acceptance Criteria (mandatory at `complete`).                                                                      |
| `result`              | object  | No       | Post-change snapshot (`result` = post-change snapshot), recorded after verify: forbidden at `plan`, optional at `execute`, required at `complete`. |

---

### Nested Schemas

`baseline` captures the pre-change snapshot (the snapshot recorded before mutating any file). `result` captures the post-change snapshot recorded after verify. Verify evidence must be produced against `result.revision`; any edit after recording `result` invalidates completion and requires re-verify.

#### 1. `baseline` (object)

- `revision` (_string, required_): Non-blank VCS commit hash, snapshot tag, or opaque working tree revision ID. (Used for context binding, not verified via Git).
- `files` (_array of objects, required_):
  - Each entry:
    - `path` (_string, required_): Project-root-relative path to a baseline file. Must not escape project root.
    - `sha256` (_string, required_): 64-character lowercase hexadecimal SHA-256 digest of the file contents.
  - Stage rules:
    - `plan`: Empty `files` array is permitted but triggers a `baseline_unverified` warning. If present, every referenced file must exist within `--project-root` and match its recorded SHA-256 digest.
    - `execute`: At least 1 file entry is required universally; an empty `files` array triggers a validation error (`empty_baseline_files`). Every referenced file must exist within `--project-root` and match its recorded SHA-256 digest on disk. If any file's current on-disk SHA-256 does not match or a file is missing, a `baseline_changed` or `baseline_file_missing` error is emitted.
    - `complete`: At least 1 file entry is required universally; an empty `files` array triggers a validation error (`empty_baseline_files`). Baseline entries must be structurally valid (valid syntax, 64-char lowercase hex digest, non-escaping bounded path). However, live on-disk existence and hash equality are **not** re-checked at completion, allowing legitimate mutations, renames, or deletions of pre-mutation files. (Completion validity is established by passed evidence artifacts covering all acceptance criteria).
  - Mismatch: During `plan` and `execute`, if any file's current on-disk SHA-256 does not match, a `baseline_changed` error is emitted.

#### 2. `documents` (array of objects)

Tracks document-driven governance artifacts.

- Each entry:
  - `kind` (_string, required_): One of the 14 canonical document stems:
    `brd`, `prd`, `frd`, `techstack`, `blueprint`, `design`, `ui-ux`, `wireframe`, `roadmap`, `runbook`, `deployment`, `security`, `qa`, `erd`.
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
- `scope` (_array of strings, required_): Non-empty array of unique non-blank strings defining target subsystems or files.

#### 5. `approval` (object, conditionally required)

Records user authorization for high-risk mutations before execution and completion.

- Structure:
  - `action` (_string, required_): Must match `operation.action`.
  - `target` (_string, required_): Must match `operation.target`.
  - `revision` (_string, required_): Must match `baseline.revision`.
  - `scope` (_array of strings, required_): Non-empty array of non-blank unique strings, evaluated regardless of operation scope validity. Must exactly match the set of paths in `operation.scope` with no duplicates.
  - `reference` (_string, required_): Opaque non-blank token (e.g., issue/PR link, signed token, or human approval log reference). **MUST NOT contain secrets, tokens, or credentials.**
- Stage rules:
  - If `operation.risk` is `"high"` and stage is `"execute"` or `"complete"`, `approval` is **mandatory**. Omission produces a `missing_approval` error.
  - If `approval` is provided at any stage (even for `"low"` risk), all binding fields (`action`, `target`, `revision`, `scope`) must match `operation` exactly. Mismatches produce a `binding_mismatch` error.

#### 6. `evidence` (array of objects, optional)

Records verifiable artifacts demonstrating AC satisfaction.

- Each entry:
  - `criterion_id` (_string, required_): Must match an `id` declared in `acceptance_criteria`.
  - `status` (_string, required_): One of `"passed"`, `"failed"`, `"blocked"`, `"unexercised"`.
  - `reference` (_string, required_): Project-root-relative path to an existing evidence artifact file (e.g., log file, test report, diff output). File must exist within project root. On **every stage**, the path must pass the durable-path denylist (`is_durable_evidence_path`): under an ephemeral segment (`tmp`, `temp`, `.tmp`, `scratch`, `.cache`), any `__pycache__` segment, or any dot-prefixed segment except `.github` fails with `evidence_not_durable` at `evidence[i].reference`. The denylist cannot detect gitignored paths not on this list.
  - `summary` (_string, required_): Non-blank description of observed output.
  - `sha256` (_string, conditionally required_): 64 lowercase hex SHA-256 digest of the evidence file bytes. Required at `complete` (`missing_evidence_sha256` when absent). Optional at `plan`/`execute`; if present at any stage it must be valid hex (`invalid_sha256`) and equal the file's current SHA-256 (`evidence_hash_mismatch`).
  - `revision` (_string, conditionally required_): Revision the evidence was produced against. Required at `complete` (`missing_evidence_revision` when absent). Must equal `result.revision` (`evidence_revision_mismatch`). Optional earlier; if present at `execute` with a `result` present, the same equality check applies.
- Stage rules:
  - `plan` & `execute`: `evidence` array is optional. If present, entries may have any valid status (`"passed"`, `"failed"`, `"blocked"`, `"unexercised"`), and referenced files must exist on disk and be durable (`evidence_not_durable` on every stage). `sha256`/`revision` are optional but validated when present.
- `complete`: `evidence` array is **mandatory**. Every declared acceptance criterion MUST have exactly one `evidence` entry with `status: "passed"`; all referenced files must exist on disk, be durable (`evidence_not_durable`), carry `sha256` (`missing_evidence_sha256`, `invalid_sha256`, `evidence_hash_mismatch`) and `revision` (`missing_evidence_revision`, `evidence_revision_mismatch`). Verify evidence must be produced against `result.revision`. Any missing, duplicate, unpassed criterion (including `"unexercised"`, `"failed"`, or `"blocked"`), non-array evidence payload, or non-string/unhashable `criterion_id` produces deterministic validation error findings without runtime traceback.

#### 7. `result` (object, conditionally required)

Records the post-change snapshot of the changed files, captured after verify. `baseline` is the pre-change snapshot; `result` is the post-change snapshot.

- `revision` (_string, required_): Non-blank revision ID of the post-change state (e.g. commit SHA or worktree ID). Blank → `invalid_result_revision`. At `complete` it must differ from `baseline.revision` (`result_revision_unchanged`).
- `files` (_array of objects, required_): Snapshot of changed files after verify. Each entry `{"path": "src/x.py", "sha256": "<hex>"}`: `path` is a bounded project-relative path (same boundary checks as `baseline.files[].path`); `sha256` is 64 lowercase hex. Unknown keys → `unknown_field`. Empty `files` at `complete` → `empty_result_files`.
- Stage rules:
  - `plan`: `result` is forbidden; presence → `result_not_allowed`.
  - `execute`: Optional. If present, every `result` file must exist and its current SHA-256 must equal the recorded value, else `result_changed` (code changed after verification).
  - `complete`: Required; absence → `missing_result`. Every recorded file must exist and match its current SHA-256, else `result_changed`. `result.revision` must not equal `baseline.revision` (`result_revision_unchanged`).

---

## 6. Documentation Workflow Transition Schema (`scripts/validate.py docs`)

The documentation workflow transition validator enforces deterministic state-transition rules and evidence requirements across the document lifecycle:

```text
intake ----[ intake-authoring ]----> authoring ----[ authoring-review ]----> review
                                                                               |  |
                                       review-ready (downstream unlocked) <----+  |
                                                                                  |
rework <----------------------------------[ review-rework ]-----------------------+
  |
  +-----[ rework-review ]----> review
```

### Allowed Transition Edges

| Transition Edge    | From State  | To State    | Purpose & Requirements                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| :----------------- | :---------- | :---------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `intake-authoring` | `intake`    | `authoring` | Base document intake: validates objective, scope, audience, reader task, sources, and safe path containment. Document need not exist yet on disk; checks and sha256 are forbidden. Source evidence items must exist as regular UTF-8 files.                                                                                                                                                                                                                                                                                                                                     |
| `authoring-review` | `authoring` | `review`    | Author submits draft for review: target document must exist as a regular UTF-8 file; doc sha256, source hashes/quotes, and all 8 rubric criteria (5 common + 3 kind) must be present. Status `blocked` is permitted (exposing unresolved criteria to reviewer). Field `reviewer` and check `decision` are forbidden.                                                                                                                                                                                                                                                            |
| `review-ready`     | `review`    | `ready`     | Reviewer approves document for downstream consumption: `reviewer` object `{"id": "<non-empty string>", "kind": "human" \| "agent", "author_id": "<non-empty string>"}` required. `reviewer.id == reviewer.author_id` (stripped casefold) fails with `reviewer_not_independent`; `kind: "agent"` emits warning `reviewer_agent_attestation` while staying valid. Every check must have `decision: "accepted"` and status `pass` or `not_applicable`. Any `blocked` check or `not_accepted` decision fails validation. Decision `"accepted"` with status `"blocked"` is rejected. |
| `review-rework`    | `review`    | `rework`    | Reviewer rejects document, requiring revisions: same `reviewer` object required (string form rejected with `invalid_reviewer`). At least one check must have `decision: "not_accepted"` (or `status: "blocked"` with `decision: "not_accepted"`). Check `decision` values are required on all checks. Decision `"accepted"` with status `"blocked"` is rejected.                                                                                                                                                                                                                |
| `rework-review`    | `rework`    | `review`    | Author resubmits revised document: document must exist as a regular UTF-8 file; updated sha256 and source evidence; all 8 rubric criteria present. Field `reviewer` and check `decision` are forbidden.                                                                                                                                                                                                                                                                                                                                                                         |

### Schematic Record Excerpt

The following JSON shows the structural layout of a transition record. It is an explicitly incomplete structural schematic (showing 1 check excerpt; a production record requires all 8 criteria: 5 common `DQ-01`..`DQ-05` plus 3 kind-specific criteria):

```json
{
  "schema_version": 1,
  "transition": {
    "from": "review",
    "to": "ready"
  },
  "objective": "Define architectural boundaries and interfaces for payment processing",
  "scope": "Payment processing service and webhook listeners",
  "reviewer": {
    "id": "arch-reviewer-1",
    "kind": "human",
    "author_id": "doc-author-1"
  },
  "documents": [
    {
      "path": "docs/blueprint.md",
      "kind": "blueprint",
      "audience": "Backend engineering team and security reviewers",
      "reader_task": "Implement webhook verification and idempotency handlers",
      "sources": [
        {
          "path": "src/config.py",
          "sha256": "1111111111111111111111111111111111111111111111111111111111111111",
          "start_line": 1,
          "end_line": 2,
          "quote": "WEBHOOK_SECRET = \"test-secret\"\nTIMEOUT_SECONDS = 30"
        }
      ],
      "sha256": "2222222222222222222222222222222222222222222222222222222222222222",
      "checks": [
        {
          "id": "DQ-01",
          "status": "pass",
          "decision": "accepted",
          "rationale": "Audience, operational scope, and core reader tasks are defined in Section 1.",
          "evidence": [
            {
              "path": "src/config.py",
              "sha256": "1111111111111111111111111111111111111111111111111111111111111111",
              "start_line": 1,
              "end_line": 2,
              "quote": "WEBHOOK_SECRET = \"test-secret\"\nTIMEOUT_SECONDS = 30"
            }
          ]
        }
      ]
    }
  ]
}
```

### Detailed Schema Rules

1. **Top-Level Fields:**
   - `schema_version` (_integer, required_): Must be exactly `1`.
   - `transition` (_object, required_): Must contain `from` and `to` strings matching the CLI `--transition` edge.
   - `objective` (_string, required_): Non-blank description of documentation goal.
   - `scope` (_string, required_): Non-blank description of in-scope boundaries.
   - `reviewer` (_object_): Required on `review-ready` and `review-rework` as `{"id": "<non-empty string>", "kind": "human" | "agent", "author_id": "<non-empty string>"}`. A string form is rejected with `invalid_reviewer`. `reviewer.id` equal to `reviewer.author_id` (stripped casefold) fails with `reviewer_not_independent`. On `review-ready`, `kind: "agent"` emits warning `reviewer_agent_attestation` without invalidating. Strictly forbidden on `intake-authoring`, `authoring-review`, and `rework-review` (unknown fields rejected).
   - `documents` (_array of objects, required_): Non-empty array of document objects. Set of document `path` values must match CLI `--documents` exactly (normalized set equality; no duplicates or alias collisions).

2. **Per-Document Base Fields (All Transitions):**
   - `path` (_string, required_): Bounded, strict project-relative path. Traversal (`..`), absolute paths, and symlink escapes are rejected. For `intake-authoring`, the file need not exist yet, but its parent directory must be safe. For all other transitions, the file must exist as a regular UTF-8 file.
   - `kind` (_string, required_): Must be one of the 14 canonical document kinds (`blueprint`, `brd`, `prd`, `frd`, `techstack`, `design`, `wireframe`, `ui-ux`, `security`, `qa`, `deployment`, `runbook`, `roadmap`, `erd`).
   - `audience` (_string, required_): Non-blank description of target human or agent reader.
   - `reader_task` (_string, required_): Non-blank description of task reader must execute.
   - `sources` (_array of objects, required_): Non-empty list of source evidence objects grounding prerequisites and factual context in existing regular UTF-8 files within `--project-root`.

3. **Per-Document Lifecycle Fields (`authoring-review`, `review-ready`, `review-rework`, `rework-review`):**
   - `sha256` (_string, required_): 64 lowercase hexadecimal SHA-256 digest of the current document file on disk. Forbidden on `intake-authoring`.
   - `checks` (_array of objects, required_): Must contain exactly 8 criteria: the 5 common criteria (`DQ-01` through `DQ-05`) plus the 3 kind-specific criteria from `references/document-quality-rubric.json`. Missing, duplicate, or unknown criteria IDs fail validation. Forbidden on `intake-authoring`.

4. **Check Object Schema:**
   - `id` (_string, required_): Rubric criterion ID.
   - `status` (_string, required_): One of `"pass"`, `"not_applicable"`, `"blocked"`. On `review-ready`, all statuses must be `"pass"` or `"not_applicable"`. Status `"blocked"` with decision `"accepted"` is invalid across all transition edges.
   - `rationale` (_string, required_): Non-blank justification explaining how evidence satisfies the criterion, why it is not applicable, or why it is blocked.
   - `evidence` (_array of objects, required_): Non-empty array of source evidence objects.
   - `decision` (_string_): Required on `review-ready` and `review-rework` (`"accepted"` or `"not_accepted"`). Strictly forbidden on `authoring-review` and `rework-review`. On `review-ready`, all decisions must be `"accepted"`. On `review-rework`, at least one check must have `decision: "not_accepted"`.

5. **Source Evidence Object Schema:**
   - `path` (_string, required_): Strict project-relative path to a regular UTF-8 file within `--project-root`. Binary files, directories, unreadable encodings, and symlink escapes are rejected.
   - `sha256` (_string, required_): 64 lowercase hexadecimal SHA-256 digest binding the raw file bytes on disk.
   - `start_line` (_integer, required_): Positive 1-indexed start line number (boolean values rejected).
   - `end_line` (_integer, required_): Integer greater than or equal to `start_line`.
   - `quote` (_string, required_): Exact non-blank full line slice from source file without trailing newline (`"\n".join(file_lines[start_line-1:end_line])` where `file_lines = content.splitlines()` on UTF-8 decoded text). Must match decoded lines exactly.

---

## 7. Suite Integrity Check (`scripts/route.py --check-suite`)

Complementary to `validate.py package` (which performs purely structural validation of package assets and templates), `scripts/route.py --check-suite` validates the declarative suite manifest (`references/suite-manifest.json`) and verifies that all 12 bundled internal execution modules exist within the suite root without path traversal escapes.

### CLI Invocation Examples

```bash
SUITE_DIR="/path/to/suite"

# Human-readable text format (default)
python3 "$SUITE_DIR/scripts/route.py" --check-suite

# Structured JSON output envelope
python3 "$SUITE_DIR/scripts/route.py" --check-suite --format json

# Explicit suite root
python3 "$SUITE_DIR/scripts/route.py" --check-suite --root "$SUITE_DIR" --format json
```

### Exit Codes

- `0`: Suite manifest valid and all 12 bundled modules present (`status: "ready"`).
- `1`: One or more required modules missing or corrupted (`status: "blocked"`).
- `2`: Manifest malformed, unparseable JSON, or schema violation (`status: "error"`).

### Payload Bounds & Parsing Invariants

- **Size Bounds:** Enforces 1 MiB limit on request and manifest payloads; 256 KiB limit on module definitions.
- **Strict Types:** Rejects non-finite numbers (`NaN`, `Infinity`), boolean substitutions for integers, and duplicate keys with exit code 2.
- **Secret Redaction:** Diagnostics redact unexpected values to prevent credential leakage.

### Illustrative JSON Output Envelope (Actual CLI Output)

```json
{
  "schema_version": 1,
  "status": "ready",
  "stages": [],
  "reasons": [
    "Suite manifest and all declared modules exist and are structurally valid."
  ],
  "blockers": [],
  "constraints": {
    "read_only": false,
    "documentation_only": false,
    "interactive_approval_required": false,
    "authorization_granted": false
  },
  "limitations": [
    "Routing resolution is deterministic based on declared manifest policy.",
    "Resolution does not grant runtime authorization for high-risk operations."
  ]
}
```

### Illustrative JSON Output Envelope (Blocked - Missing Module)

```json
{
  "schema_version": 1,
  "status": "blocked",
  "stages": [],
  "reasons": ["One or more declared modules are missing or invalid."],
  "blockers": [
    {
      "code": "MODULE_MISSING",
      "message": "Module file not found: skills/daw-plan/SKILL.md"
    }
  ],
  "constraints": {
    "read_only": false,
    "documentation_only": false,
    "interactive_approval_required": false,
    "authorization_granted": false
  },
  "limitations": [
    "Routing resolution is deterministic based on declared manifest policy.",
    "Resolution does not grant runtime authorization for high-risk operations."
  ]
}
```

---

## 8. Ledger Validation (`scripts/validate.py ledger`)

Validates the spec index that records, per document, its workflow state, current SHA-256, and current transition record (C3).

### CLI Invocation

```bash
python3 "$SKILL_DIR/scripts/validate.py" ledger docs/specs/ledger.json --project-root "$PROJECT_DIR" --format json
```

Arguments:

- `FILE`: Path to the ledger JSON file. May be project-root-relative or absolute.
- `--project-root DIR`: Required. Bounds all document and record paths.
- `--format text|json`: Output format. Defaults to `text`.

Exit codes match the shared table in §1 (`0` valid, `1` findings, `2` usage/IO error).

### Schema

Root object:

- `schema_version` (_integer, required_): Exactly `1`.
- `documents` (_array of objects, required_): One entry per tracked document.

Each document entry:

- `path` (_string, required_): Project-relative path to the spec document.
- `state` (_string, required_): One of `intake`, `authoring`, `review`, `rework`, `ready`.
- `sha256` (_string, required_): 64 lowercase hex digest of the current document bytes.
- `record` (_string, required_): Project-relative path of the current transition record. Must be durable (see C1: path-segment denylist over `tmp`, `temp`, `.tmp`, `scratch`, `.cache`, `__pycache__`, dot-segments except `.github`). The denylist cannot detect gitignored paths.
- `history` (_array of strings, optional_): Superseded record paths; each must exist, be bounded, and be durable.

Unknown keys at root or per-entry are rejected. Duplicate document paths are rejected (`ledger_duplicate_document`).

### Checks

- Document file exists and its current SHA-256 equals `sha256` (else `ledger_doc_drift`).
- `record` exists, parses as strict JSON (duplicate keys rejected), and contains an entry for that doc path whose `sha256` equals the ledger `sha256` (else `ledger_record_mismatch`).
- Record `transition.to` equals ledger `state` (else `ledger_state_mismatch`).
- For `state: ready`, the existing `review-ready` docs validation (`scripts/check_docs.py` `validate_docs`) additionally runs on the whole record; only record-level findings and findings for that document's own entry propagate (path prefix `documents[i].record:`). Drift in a sibling document sharing the record does not fail this entry; that sibling's own ledger entry reports it.

### Output Envelope

Same shape as `docs`: `{ "valid", "check": "ledger", "schema_version": 1, "findings", "limitations" }`. `valid` is `true` iff no `error`-severity findings.

---

## 9. Config Validation (`scripts/validate.py config`)

Validates the single `<!-- daw-config:start -->`…`<!-- daw-config:end -->` block in an agent file (`AGENTS.md` or `CLAUDE.md`) as written by `daw-setup` (C4).

### CLI Invocation

```bash
python3 "$SKILL_DIR/scripts/validate.py" config AGENTS.md --project-root "$PROJECT_DIR" --format json
```

Arguments:

- `FILE`: Path to the agent file. May be project-root-relative or absolute.
- `--project-root DIR`: Required. Bounds path checks and command resolution.
- `--format text|json`: Output format. Defaults to `text`.

Exit codes match the shared table in §1 (`0` valid, `1` findings, `2` usage/IO error).

### Block Rules

- Exactly one block must exist: zero → `config_block_missing`; more than one → `config_block_duplicate`.
- The `## DAW Configuration` heading must be present (else `config_heading_missing`). After it, every non-blank line must be `- key: value`. Anything else → `config_line_invalid`, reported by file line number (`line N`).
- Required keys, exactly as in `skills/daw-setup/SKILL.md` Step 3: `schema`, `daw_version`, `spec_dir`, `test_command`, `lint_command`, `build_command`, `workspace`, `high_risk_paths`, `issue_tracker`, `default_branch`, `commit_convention`, `pr_template`, `ci_checks`, `release_process`, `branch_pattern`. Missing → `config_key_missing`; duplicate → `config_key_duplicate`; unknown key → `config_line_invalid`.
- `schema` must be `1`. `workspace` must be `in-place` or `isolated` (else `config_line_invalid`).
- `daw_version` MUST be semver X.Y.Z (else `config_line_invalid`). The installed suite `VERSION` is read read-only from the validator's own package root (`scripts/check_config.py`, whose package root is the parent of `scripts/`). Comparison: project < installed → warning `config_daw_version_stale` (`valid` stays `true`, routes to `daw-setup` Upgrade Re-check); project > installed → error `config_daw_version_ahead`; installed `VERSION` unreadable or non-semver → warning `config_daw_version_unverified`.

### Path and Command Checks (read-only)

- `spec_dir` must exist as a directory under root (else `config_path_missing`).
- `pr_template` must exist unless `none` (else `config_path_missing`).
- Each comma-separated `high_risk_paths` entry must exist unless the whole value is `none` (else `config_path_missing`).
- For `test_command`, `lint_command`, `build_command` not `none`: the first token (after stripping leading `VAR=val` env assignments) must be an existing project-relative file or resolvable via `shutil.which`, else `config_command_unresolved` (severity `error`).

### Output Envelope

Same envelope shape with `"check": "config"`. `limitations` states that the validator never executes commands and only checks lookup resolvability.

---

## 10. Status Aggregate Preflight (`scripts/validate.py status`)

The read-only aggregate preflight composes the existing checks (`config`, `ledger`, `contract`) for one project root and answers a single routing question: what should happen before spec-dependent work? It is implemented in `scripts/check_status.py` and composes the other `check_*` modules; it owns no validation rules of its own.

### CLI Invocation

```bash
python3 "$SKILL_DIR/scripts/validate.py" status --project-root "$PROJECT_DIR" --format json
python3 "$SKILL_DIR/scripts/validate.py" status --project-root "$PROJECT_DIR" --agent-file AGENTS.md --format text
```

Arguments: `--project-root ROOT` (required, must be a directory, else exit `2`), optional `--agent-file PATH`, `--format text|json` (default `text`). Exit codes match §1 (`0` no error findings, `1` error findings, `2` usage/IO error).

### Agent-file & Config Discovery

- Agent file: `--agent-file` if given, else `AGENTS.md` under the root, else `CLAUDE.md` under the root. If neither exists or it cannot be read, `summary.config` is `missing` with error `status_config_missing` (path `config`). If the file exists but carries no `<!-- daw-config:start -->` block, `summary.config` is `missing` and the config check's own `config_block_missing` error is propagated.
- The config check (§9) runs against that file. `summary.config` is `ok` (no config findings), `stale` (only the warning `config_daw_version_stale`), `invalid` (any error-severity config finding), or `missing`.

### Ledger Discovery

If the config parsed a `spec_dir`: when `<spec_dir>/ledger.json` exists the ledger check (§8) runs and `summary.ledger` is `ok` or `invalid`; a ledger that is not strict JSON is `invalid` with error `ledger_malformed` (path `ledger:$`). When it is absent but the spec dir contains any `*.md` other than a ledger file, `summary.ledger` is `missing` with one warning `status_ledger_missing` (path `ledger`). Otherwise (empty spec dir with no Markdown) `summary.ledger` is `not_applicable`. If no `spec_dir` is known, `summary.ledger` is `not_applicable`.

### Task-Contract Discovery

Task contracts follow the convention path `docs/evidence/<task-id>/contract.json` (globbed one level under the root):

- A contract carrying a `result` key is validated at stage `complete` and counted `complete_valid` (no error findings) or `complete_invalid` (any error finding).
- A contract without a `result` key is `in_progress`: it is not validated; each emits one warning `status_task_in_progress` (path = the contract path).
- A contract that is not strict JSON counts as `complete_invalid` with error `contract_malformed` (path `contract[<relpath>]:$`).

### Finding Path Prefixes

Sub-findings propagate with the owning check prefixed to `path`: `config:`, `ledger:`, or `contract[<relpath>]:` (e.g. `contract[docs/evidence/t1/contract.json]:result.files[0].path`).

### Summary & recommended_route Precedence

`summary.tasks` counts are `{ "complete_valid", "complete_invalid", "in_progress" }`. `recommended_route` resolves in this precedence order:

1. `config` is `missing` or `invalid` => `setup`.
2. `config` is `stale` => `upgrade-recheck`.
3. `ledger` is `invalid` or `missing` => `design-rework`.
4. Any `complete_invalid` task => `verify`.
5. Otherwise => `none`.

### Output Envelope

```json
{
  "valid": true,
  "check": "status",
  "schema_version": 1,
  "summary": {
    "config": "ok",
    "ledger": "ok",
    "tasks": { "complete_valid": 1, "complete_invalid": 0, "in_progress": 1 }
  },
  "recommended_route": "none",
  "findings": [],
  "limitations": [
    "Read-only aggregate: never runs tests, evidence commands, or builds, and never writes files.",
    "Task discovery is limited to the convention path docs/evidence/<task-id>/contract.json; contracts stored elsewhere are not checked.",
    "Inherits every composed check's limitations (config, ledger, docs, contract); semantic truth of evidence is never evaluated."
  ]
}
```

`valid` is `true` iff there are zero error-severity findings. Text output prints the summary and `recommended_route` in addition to findings.

### Limitations

- Read-only; does not run tests or evidence commands (command resolvability only, per §9).
- Task discovery is limited to the convention path `docs/evidence/<task-id>/contract.json`, globbed one level; contracts stored elsewhere are not seen.
- Inherits each composed check's limitations (§2, §8–§9).
