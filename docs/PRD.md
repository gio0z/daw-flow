# Product Requirements Document (PRD)

## Deterministic Agentic Workflow

### 1. Product Overview & Purpose

Deterministic Agentic Workflow is an open-source, portable specification, suite router, and verification utility for AI coding agents. It provides a formal contract between generative planning and deterministic execution, enforcing pre-code documentation, role specialization across deep modular skills (`skills/daw-*`), declarative route resolution (`scripts/route.py`), fail-closed approval capturing, and stage-gated contract lifecycle verification (`scripts/validate.py`).

### 2. User Personas

- **Developer / Human Operator:** Configures project rules, reviews task contracts, reviews destructive approval requests, inspects routing plans, and evaluates validation output.
- **Autonomous Agent (Suite Router / Orchestrator):** Reads `SKILL.md`, executes declarative routing requests against `scripts/route.py`, evaluates the execution pipeline, and coordinates specialized module skills.
- **Specialized Module Worker (Agent):** Executes deep, bounded procedures (`daw-design`, `daw-plan`, `daw-debug`, `daw-build`, `daw-review`, `daw-verify`, `daw-workspace`, `daw-ask`, `daw-setup`, `daw-wizard`, `daw-untangle`), authoring specifications, executing code changes, performing read-only advisory, or conducting structural change-coupling investigation without persona impersonation, and returning clean handoffs without recursive router invocation.
- **Automated Quality Gate (CI / Harness):** Runs package, suite structure (`route.py --check-suite`), and contract validation in headless pipelines, evaluating deterministic exit codes to allow or reject progression.

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
  - _AC-CTR-02.1 (`plan`):_ Requires canonical schema fields (`schema_version: 1`, `objective`, `baseline`, `documents`, `acceptance_criteria`, `operation`). Preflight baseline file checks verify that referenced files exist within `--project-root` and match their recorded SHA-256 digests on disk (warns if empty).
  - _AC-CTR-02.2 (`execute`):_ Requires all `plan` fields with non-empty `baseline.files`. Preflight baseline verification confirms on-disk existence and SHA-256 digest match for all baseline files before mutations begin. High-risk operations require an approval object.
  - _AC-CTR-02.3 (`complete`):_ Requires all structural `execute` fields with non-empty `baseline.files`, but does not re-verify live on-disk existence or hash equality against baseline files (allowing legitimate modifications, renames, and deletions). Requires mandatory `evidence` array mapping to existing disk files covering all acceptance criteria with status `"passed"`.
- **REQ-CTR-03: Boundary Enforcement & Path Security**
  - _Description:_ All target paths, document paths, and evidence paths must remain strictly bounded within `--project-root`.
  - _AC-CTR-03.1:_ Path traversal patterns (`../`, absolute paths attempting to escape root) must trigger `CTR_BOUNDARY_VIOLATION` and exit code 1.
- **REQ-CTR-04: Approval Capturing vs Proof of Authorization**
  - _Description:_ The validator must capture and verify the structure of human approval records for destructive triggers.
  - _AC-CTR-04.1:_ For operations with `risk: "high"`, `approval` must be provided in stages `execute` and `complete` as an opaque reference object whose `action`, `target`, `revision`, and `scope` fields strictly bind to `operation`.
  - _AC-CTR-04.2:_ Structural validation of an approval object constitutes proof of captured intent, not proof of cryptographic identity or runtime authorization tokens.

#### Category: Capability & Document Routing (`RTE`)

- **REQ-RTE-01: 13-Document Matrix Routing**
  - _Description:_ The workflow must provide unambiguous routing rules defining required documents and technical capabilities based on task impact tiers.
  - _AC-RTE-01.1:_ Small scoped fixes (single-line or localized bug fixes, typos) operate in zero-doc patch mode with an explicit documented reason (e.g., localized bug fix, bounded scope) rather than forcing synthetic specification bundles.
  - _AC-RTE-01.2:_ Full feature additions require all core architectural documents before code modification begins.
  - _AC-RTE-01.3:_ Required capabilities may be fulfilled directly by the current agent or delegated to a qualified subagent without requiring external skill registry lookups or named external skill dependencies.

#### Category: Lifecycle Invocation & Mode Precedence (`MOD`)

- **REQ-MOD-01: Execution Mode Resolution & Precedence**
  - _Description:_ The agent must resolve operating mode according to strict precedence rules: explicit review/audit (read-only) > explicit feature/fix (change) > explicit existing-project setup (adopt) > explicit new setup (bootstrap) > bare invocation (inspect target; enter adopt if implementation exists else bootstrap).
  - _AC-MOD-01.1:_ When an explicit mode is instructed, it supersedes heuristics or target state. Explicit review mode strictly forbids file creation or state mutations.
  - _AC-MOD-01.2:_ In bare invocation on an empty workspace without a product brief, the agent must inspect the workspace and ask exactly one clarifying question regarding product intent, rather than inventing synthetic features or phantom requirements.
- **REQ-MOD-02: Observable Document Action Transparency**
  - _Description:_ The agent must announce its operating mode, resolve target scope from user context or `cwd`, and output a structured document action table: planned actions (`create`, `update`, `reuse`, `skip`, `blocked` with path and reason) prior to execution, and final completed actions (`created`, `updated`, `reused`, `skipped`, `blocked` with path and reason) upon completion.
  - _AC-MOD-02.1:_ The agent must clearly distinguish planned document actions from final completed actions.
  - _AC-MOD-02.2:_ During adoption of an existing codebase, the agent must inspect actual code, dependencies, and docs, authoring missing baseline specifications from observed facts while preserving existing code and user-authored documents.
  - _AC-MOD-02.3:_ When an explicit full 13-document suite is requested, the agent must honor all requested documents with substantive scoped content or document explicit blockers/applicability limits, never silently shrinking the suite.

#### Category: Suite Routing & Module Execution (`RTE`)

- **REQ-RTE-01: Declarative Route Manifest & Policy**
  - _Description:_ Suite routing must be governed declaratively by `references/suite-manifest.json` via `scripts/route.py REQUEST`.
  - _AC-RTE-01.1:_ Input request schema requires strict JSON keys: `schema_version` (integer 1), `intent` (`bootstrap` | `adopt` | `feature` | `bugfix` | `patch` | `review` | `untangle` | `ask` | `setup`), `requirements` (`clear` | `unclear` | `unknown`), `risk` (`low` | `high` | `unknown`), and `workspace` (`in-place` | `isolated` | `unknown`). Rejects unknown keys, duplicate keys, or nonstandard constants.
  - _AC-RTE-01.2:_ Output response schema guarantees deterministic keys: `schema_version`, `status` (`ready` | `needs-input` | `blocked`), `stages` (ordered list of module names), `reasons` (list of strings), `blockers` (list of code/message objects), `constraints` (`read_only`, `documentation_only`, `interactive_approval_required`, `authorization_granted: false`), and `limitations` (list of strings).
  - _AC-RTE-01.3:_ Route execution exit codes: `0` (route ready), `1` (needs-input or incomplete modules), `2` (malformed input, manifest violation, or CLI usage error).
- **REQ-RTE-02: Policy Routing Logic & Workspace Selection**
  - _Description:_ Route calculation honors declared matrix:
    - `bootstrap` -> `[daw-wizard, daw-design, daw-plan]` (`documentation_only: true`).
    - `adopt` -> `[daw-design, daw-plan]` (`documentation_only: true`).
    - `setup` -> `[daw-setup]` (`documentation_only: true`).
    - `feature` with clear requirements -> `[daw-plan, daw-build, daw-review, daw-verify]`.
    - `feature` with unclear requirements -> `[daw-design, daw-plan, daw-build, daw-review, daw-verify]`.
    - `bugfix` -> `[daw-debug, daw-plan, daw-build, daw-review, daw-verify]`.
    - `patch` -> `[daw-build, daw-verify]`.
    - `review` -> `[daw-review]` (`read_only: true`).
    - `ask` -> `[daw-ask]` (`read_only: true`).
    - `untangle` -> `[daw-untangle]` (`read_only: true`).
  - _AC-RTE-02.1:_ For mutating intents (`feature`, `bugfix`, `patch`), when `workspace` is `isolated`, `daw-workspace` is prepended to the stage list. When `workspace` is `in-place`, execution proceeds normal. When `workspace` is `unknown`, status is `needs-input`.
  - _AC-RTE-02.2:_ Read-only intents (`ask`, `review`, `untangle`) ignore unknown risk and unknown workspace.
  - _AC-RTE-02.3:_ When `risk` is `high`, `constraints.interactive_approval_required` is set to `true`, and `constraints.authorization_granted` is permanently `false`.
- **REQ-RTE-03: Structural Suite Verification (`--check-suite`)**
  - _Description:_ `scripts/route.py --check-suite [--root ROOT]` validates structural consistency of the suite manifest and bundled modules without modifying existing validator contracts.
  - _AC-RTE-03.1:_ Validates all 11 declared module paths exist within the root boundary, checks frontmatter scalar integrity, and verifies route mapping soundness.
  - _AC-RTE-03.2:_ Returns exit code 0 when the suite is complete and sound; returns exit code 1 if any module or route definition is broken or missing.

### 4. Non-Functional Requirements

- **NFR-01: Standard Library Compatibility:** Must execute on Python 3.10, 3.11, 3.12, 3.13, and 3.14 using only the Python standard library.
- **NFR-02: Zero Network Access:** Must operate completely offline with no HTTP/HTTPS requests, socket creation, or external API dependencies.
- **NFR-03: Execution Performance:** Package validation and suite routing checks must execute in under 200ms on standard developer hardware.
- **NFR-04: Deterministic Output:** Text and JSON envelopes must produce identical, sorted findings across repeated runs on identical inputs.
- **NFR-05: Deep Module Independence & Distribution:** Modules are bundled under `skills/daw-*` with relative links to suite root. In installed environments, sibling symlinks point to bundled modules. Standalone unbundled distribution is unsupported.

### 5. Scope & Non-Goals

- **In Scope:**
  - Suite router and 11 specialized modular skills (`daw-design`, `daw-plan`, `daw-debug`, `daw-build`, `daw-review`, `daw-verify`, `daw-workspace`, `daw-ask`, `daw-setup`, `daw-wizard`, `daw-untangle`).
  - Declarative route policy engine and structural check (`scripts/route.py`, `references/suite-manifest.json`).
  - Static structural validation of skill packages and task contract schemas via `scripts/validate.py`.
  - Hash matching against disk files and root path containment verification.
- **Non-Goals:**
  - Automated code execution, shell hook enforcement, or background daemons inside the route engine or validator.
  - Persona impersonation or external identity spoofing in advisory skills (`daw-ask`).
  - Runtime credential validation or cryptographic authorization tokens.
  - Standalone unbundled distribution of child modules without the suite root.
  - Git branch, commit, or push orchestration.
