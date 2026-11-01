# Product Requirements Document (PRD)

## Deterministic Agentic Workflow

### 1. Product Overview & Purpose

Deterministic Agentic Workflow is an open-source, portable specification and verification utility for AI coding agents. It provides a formal contract between generative planning and deterministic execution, enforcing pre-code documentation, role specialization, fail-closed approval capturing, and stage-gated contract lifecycle verification.

### 2. User Personas

- **Developer / Human Operator:** Configures project rules, reviews task contracts, reviews destructive approval requests, and inspects validation output.
- **Autonomous Agent (Worker / Specialist):** Reads `SKILL.md` and reference routing, authors project specification documents, generates task contracts, executes bounded changes, and verifies contract state against `scripts/validate.py`.
- **Automated Quality Gate (CI / Harness):** Runs package and contract validation in headless pipelines, evaluating deterministic exit codes to allow or reject progression.

### 3. Functional Requirements & Acceptance Criteria

#### Category: Package Integrity (`PKG`)

- **REQ-PKG-01: Structure & Manifest Verification**
  - _Description:_ The validator must inspect the skill root and verify the presence of mandatory files: `SKILL.md`, `references/routing.md`, `references/operations.md`, `references/validation.md`, `references/installation.md`, `references/task-contract.example.json`, and all 13 canonical template files in `templates/`.
  - _AC-PKG-01.1:_ Running `validate.py package` returns exit code 0 when all 19 structural files exist and are readable.
  - _AC-PKG-01.2:_ When any required file is missing, the validator returns exit code 1 with finding code `PKG_FILE_MISSING` indicating the exact missing path.
- **REQ-PKG-02: Document Link Resolution**
  - _Description:_ The validator must parse markdown links in `SKILL.md` and reference files, resolving local file targets.
  - _AC-PKG-02.1:_ Broken internal markdown links generate finding code `PKG_LINK_BROKEN` with source file, link target, and line context.

#### Category: Task Contract Lifecycle (`CTR`)

- **REQ-CTR-01: JSON Envelope & Duplicate Key Detection**
  - _Description:_ Task contracts must be strictly formatted JSON with unique keys.
  - _AC-CTR-01.1:_ Contracts containing duplicate JSON keys must fail closed with finding code `CTR_DUPLICATE_KEY`.
  - _AC-CTR-01.2:_ Malformed JSON must fail closed with finding code `CTR_INVALID_JSON`.
- **REQ-CTR-02: Stage Semantics & Transitions**
  - _Description:_ The validator must support three distinct lifecycle stages: `plan`, `execute`, and `complete`.
  - _AC-CTR-02.1 (`plan`):_ Requires `schema_version`, `task_id`, `stage`, `title`, `author`, `planning_docs`, `specialist_roles`, `fail_closed_triggers`, and `acceptance_criteria`. Target files must not require post-execution fields.
  - _AC-CTR-02.2 (`execute`):_ Requires all `plan` fields plus declared `files_to_modify` with baseline SHA-256 hashes for existing files, planned actions (`create`, `modify`, `delete`), and rollback strategies.
  - _AC-CTR-02.3 (`complete`):_ Requires all `execute` fields plus `post_execution_hashes` for modified files, `evidence_references` mapping to existing disk files, and verification proof for every acceptance criterion.
- **REQ-CTR-03: Boundary Enforcement & Path Security**
  - _Description:_ All target paths, document paths, and evidence paths must remain strictly bounded within `--project-root`.
  - _AC-CTR-03.1:_ Path traversal patterns (`../`, absolute paths attempting to escape root) must trigger `CTR_BOUNDARY_VIOLATION` and exit code 1.
- **REQ-CTR-04: Approval Capturing vs Proof of Authorization**
  - _Description:_ The validator must capture and verify the structure of human approval records for destructive triggers.
  - _AC-CTR-04.1:_ If a contract declares a fail-closed trigger requiring approval (e.g., destructive file deletion or schema migration), `approvals_captured` must contain an object matching the trigger's `action`, `target`, and `scope`.
  - _AC-CTR-04.2:_ Structural validation of an approval object constitutes proof of captured intent, not proof of cryptographic identity or runtime authorization tokens.

#### Category: Specialist Role Routing (`RTE`)

- **REQ-RTE-01: 13-Document Matrix Routing**
  - _Description:_ The workflow must provide unambiguous routing rules defining required documents and specialist personas based on task impact tiers.
  - _AC-RTE-01.1:_ Minor scope edits (single-component, bug fix) require zero-docpatch mode or minimal contract (BRD + PRD + TRD).
  - _AC-RTE-01.2:_ Full feature additions require all core architectural documents before code modification begins.

### 4. Non-Functional Requirements

- **NFR-01: Standard Library Compatibility:** Must execute on Python 3.10, 3.11, 3.12, 3.13, and 3.14 using only the Python standard library.
- **NFR-02: Zero Network Access:** Must operate completely offline with no HTTP/HTTPS requests or external API dependencies.
- **NFR-03: Execution Performance:** Package validation must execute in under 200ms on standard developer hardware.
- **NFR-04: Deterministic Output:** Text and JSON envelopes must produce identical, sorted findings across repeated runs on identical inputs.

### 5. Scope & Non-Goals

- **In Scope:** Static structural validation, contract schema validation, hash matching against disk files, and path containment checking.
- **Non-Goals:**
  - Automated test execution (the validator verifies test evidence files, it does not invoke test runners).
  - Code linting, AST analysis, or syntax parsing of codebase files.
  - Git branch, commit, or push orchestration.
  - Runtime access control or identity federation.
