# Document Routing, Intent Precedence & Suite Manifest Reference

This reference defines the routing engine policy, intent precedence hierarchy, execution pipeline dispatch, and handoff contracts for the Deterministic Agentic Workflow (DAW) suite.

Article Reference: Rama Digital — _Agentic Tapi Deterministic Workflow AI Agent_ (https://ramadigital.id/blog/agentic-tapi-deterministic-workflow-ai-agent).  
_Advice separation note:_ Core article principles (generative planning, deterministic mutation, document contracts, verification gates) establish the architectural foundation. Local operational additions in this reference define structured handoff schemas, lifecycle routing, and domain capability delegation for multi-agent CLI and workstation environments.

---

## 1. Intent Precedence & Routing Hierarchy

Routing in DAW is deterministic and requires classified input facts. The workflow does not rely on open-ended keyword heuristics. Incoming engineering tasks are mapped into one of 9 finite intents:

| Precedence | Intent      | Classification Criteria                                                                                 | Read-Only | Doc-Only | Stage Pipeline                                                                                                                                         |
| :--------: | :---------- | :------------------------------------------------------------------------------------------------------ | :-------: | :------: | :----------------------------------------------------------------------------------------------------------------------------------------------------- |
|   **1**    | `review`    | Diff review, security posture audit, boundary compliance check.                                         |    Yes    |    No    | `daw-review`                                                                                                                                           |
|   **2**    | `untangle`  | Explicit read-only structural analysis, coupling/cohesion assessment, modular boundary investigation.   |    Yes    |    No    | `daw-untangle`                                                                                                                                         |
|   **3**    | `ask`       | Conversational architecture guidance, Q&A, trade-off analysis.                                          |    Yes    |    No    | `daw-ask`                                                                                                                                              |
|   **4**    | `setup`     | Interactive configuration setup, tool command discovery, and repo convention block authoring.           |    No     |   Yes    | `daw-setup`                                                                                                                                            |
|   **5**    | `bootstrap` | Greenfield specification generation from a product brief in empty directory.                            |    No     |   Yes    | `daw-wizard` -> `daw-design` -> `daw-plan`                                                                                                             |
|   **6**    | `adopt`     | Reverse-engineering existing codebase to author missing specifications.                                 |    No     |   Yes    | `daw-design` -> `daw-plan`                                                                                                                             |
|   **7**    | `bugfix`    | Defect resolution requiring RCA, minimal fix, security review, regression verification.                 |    No     |    No    | `daw-debug` -> `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify`                                                                               |
|   **8**    | `patch`     | Pre-diagnosed minimal change or surgical fix with zero spec changes (requires `requirements: "clear"`). |    No     |    No    | `daw-build` -> `daw-verify`                                                                                                                            |
|   **9**    | `feature`   | New capability or functional evolution requiring plan, implementation, review, verification.            |    No     |    No    | Clear: `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify`<br>Unclear: `daw-design` -> `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify` |

### Precedence Rules & Invariants

- When user intent is evaluation, code audit, or PR review, `review` takes precedence.
- When user intent is explicit structural analysis, coupling investigation, modular boundary assessment, or change-coupling inspection, `untangle` takes precedence. Strictly read-only; ignores unknown risk or workspace preferences; no `daw-workspace`, approval execution, or mutation. Dispatches to `daw-untangle`. (Note: refactoring implementation requests themselves are NOT silently routed to untangle; mutating refactoring uses standard feature/patch routes after scope is accepted. Untangle is an explicit bounded investigation, never an extra mandatory stage on all requests or an unsolicited whole-codebase cleanup mandate). Governed by [references/change-coupling.md](change-coupling.md).
- When user intent is conversational Q&A, guidance, or trade-off evaluation, `ask` takes precedence.
- Read-only user intent always wins: `review`, `untangle`, and `ask` ignore risk and workspace preferences and never mutate code or specifications.

If `evaluates_workspace` is enabled in the manifest for mutating intents (`bugfix`, `patch`, `feature`):

- `workspace: "isolated"`: The router prepends `daw-workspace` to the stages pipeline.
- `workspace: "in-place"`: The router proceeds without prepending `daw-workspace`.
- `workspace: "unknown"`: The router sets status to `needs-input` with an explicit blocker.
- **Dirty Tree Invariant:** Preflight checks never require a clean git tree. User uncommitted changes are preserved.
- **Rollback & Credentials:** External cloud credentials or rollback targets are checked only for high-risk infrastructure/deployment actions.

---

## 2. Declarative Suite Manifest Policy & Route Engine

Routing policy is declared statically in [references/suite-manifest.json](suite-manifest.json) under `schema_version: 1`. The route engine validates requests against this fixed declarative schema and enforces canonical stage pipelines for all 9 intents. The policy is fixed and schema-governed rather than freely configurable at runtime; modifications to routing stages or capabilities require code/schema upgrades (schema enum additions remain additive within schema_version: 1).

### Strict Envelope Parsing & Limits

- **Payload Bounds:** Request and manifest JSON files enforce strict size limits (maximum 1 MiB for requests and manifests; maximum 256 KiB for module skill definitions).
- **Finite Types & Duplicate Rejection:** Parsing rejects non-finite numbers, malformed types, and duplicate dictionary keys, failing immediately with `status: "error"` and exit code 2.
- **Redacted Unknowns:** Error diagnostics redact unknown values to prevent credential and secret leakage.

### Declarative Intent Stage Mapping

| Intent              | Stage Pipeline                                                            | Constraints / Evaluation                                                               |
| :------------------ | :------------------------------------------------------------------------ | :------------------------------------------------------------------------------------- |
| `ask`               | `daw-ask`                                                                 | Read-only; ignores risk and workspace.                                                 |
| `review`            | `daw-review`                                                              | Read-only; ignores risk and workspace.                                                 |
| `untangle`          | `daw-untangle`                                                            | Read-only; ignores risk and workspace. Strictly non-mutating structural analysis.      |
| `setup`             | `daw-setup`                                                               | Documentation-only; allows unclear requirements.                                       |
| `bootstrap`         | `daw-wizard` -> `daw-design` -> `daw-plan`                                | Documentation-only; allows unclear requirements.                                       |
| `adopt`             | `daw-design` -> `daw-plan`                                                | Documentation-only; preserves user code.                                               |
| `bugfix`            | `daw-debug` -> `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify`  | Prepends `daw-workspace` if `workspace: "isolated"`.                                   |
| `patch`             | `daw-build` -> `daw-verify`                                               | Prepends `daw-workspace` if `workspace: "isolated"`. Requires `requirements: "clear"`. |
| `feature` (clear)   | `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify`                 | Prepends `daw-workspace` if `workspace: "isolated"`.                                   |
| `feature` (unclear) | `daw-design` -> `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify` | Requires requirements clarification or design intake.                                  |

### Requirements Clarity Gate

`patch` is pre-diagnosed by definition: its constraints are already well-defined, so requirements clarification is never part of the pipeline.

- `requirements: "unknown"` → `needs-input`, no stages, blocker `REQUIREMENTS_UNKNOWN` (exit code 1).
- `requirements: "unclear"` → `needs-input`, no stages, blocker `REQUIREMENTS_UNCLEAR` (exit code 1).
- `requirements: "clear"` → unchanged `daw-build` -> `daw-verify`.

`bugfix` keeps its investigation entry point (`daw-debug`) for `unknown`/`unclear` requirements; no other intent is gated on requirements clarity.

### Invocation Commands:

```bash
# Evaluate routing request using resolved suite script path
python3 "$SUITE_ROOT/scripts/route.py" request.json [--format text|json] [--root SUITE_ROOT]

# Check suite manifest and module availability
python3 "$SUITE_ROOT/scripts/route.py" --check-suite [--format text|json] [--root SUITE_ROOT]
```

### Request Envelope (Input)

All fields are mandatory. Unexpected keys or duplicate keys trigger an immediate error (status: `error`, exit code 2) with unknown values redacted to prevent secret leakage:

```json
{
  "schema_version": 1,
  "intent": "bugfix",
  "requirements": "clear",
  "risk": "low",
  "workspace": "in-place"
}
```

### Illustrative Response Envelope (Output Example)

```json
{
  "schema_version": 1,
  "status": "ready",
  "stages": ["daw-debug", "daw-plan", "daw-build", "daw-review", "daw-verify"],
  "reasons": [
    "Intent 'bugfix' resolved to canonical stages (illustrative reason text)."
  ],
  "blockers": [],
  "constraints": {
    "read_only": false,
    "documentation_only": false,
    "interactive_approval_required": false,
    "authorization_granted": false
  },
  "limitations": [
    "Workspace operations require operator authorization; no automated credential grants."
  ]
}
```

### Exit Codes:

- `0`: Route ready or `--check-suite` passed.
- `1`: `needs-input` or `blocked` (missing module, unclear requirements where disallowed, unknown workspace for mutating intent, unknown risk for mutating intent).
- `2`: Malformed input JSON, invalid enum value, or file read failure (`error`).

---

## 3. The 13 Document Routing Specifications

### Documentation Authoring Contract: Ownership, Provenance & Verification

To prevent document sprawl, speculative filler, and ambiguous responsibilities, all document authoring across the Deterministic Agentic Workflow suite is governed by this single authoritative contract:

> **Applicability Notice:** The 13-document matrix applies strictly to greenfield system creation (`bootstrap`), undocumented codebase onboarding (`adopt`), or when requirements are explicitly missing or requested. Routine bug fixes, isolated tasks, refactors, and settled features with clear requirements do NOT require generating or updating the 13 specification documents.

#### 1. Accountable Writers & Phase Ownership Matrix

| Document        | Accountable Author                           | Bootstrap Role (`daw-wizard`)                          | System Design / Adoption (`daw-design`)                 | Execution Planning (`daw-plan`)                              | Scope & Core Deliverable                                  |
| :-------------- | :------------------------------------------- | :----------------------------------------------------- | :------------------------------------------------------ | :----------------------------------------------------------- | :-------------------------------------------------------- |
| `blueprint.md`  | `daw-design`                                 | Drafts initial system brief & core invariants          | Authoritative author; enriches boundaries & seams       | Reads for architectural constraints & seams                  | High-level topology, module boundaries, system invariants |
| `brd.md`        | `daw-design`                                 | Drafts commercial & problem scope from brief           | Authoritative author; enriches business scope           | Reads for business boundaries & constraints                  | Business goals, OKRs/KPIs, budget/timeline constraints    |
| `prd.md`        | `daw-design`                                 | Drafts initial personas, user stories & AC             | Authoritative author; deepens stories & NFRs            | Reads for user stories & acceptance criteria                 | User personas, functional stories with verifiable AC      |
| `frd.md`        | `daw-design`                                 | Drafts core functional flows & transitions             | Authoritative author; formalizes state machines         | Reads for validation logic & state transitions               | State transitions, logic rules, validation matrices       |
| `techstack.md`  | `daw-design`                                 | Drafts proposed runtimes, stores & frameworks          | Authoritative author; grounds in code & ADRs            | Reads for runner commands, toolchains & versions             | Runtimes, libraries, DBs, toolchains, and ADR trade-offs  |
| `design.md`     | `daw-design`                                 | Drafts initial design tokens / UI inventory            | Authoritative author; enforces token scales             | Reads for UI component boundaries (if UI)                    | Design tokens, color contrast, component styling          |
| `wireframe.md`  | `daw-design`                                 | Drafts structural screen layouts (if UI)               | Authoritative author; responsive layout hierarchy       | Reads for layout structure (if UI)                           | ASCII/structural viewports, layout grids, screen blocks   |
| `ui-ux.md`      | `daw-design`                                 | Drafts core user interaction states (if UI)            | Authoritative author; interaction states & a11y         | Reads for interactive states (if UI)                         | Micro-interactions, keyboard navigation, a11y tree        |
| `security.md`   | `daw-design`                                 | Drafts initial threat boundaries & data flow           | Authoritative author; formal threat model & auth        | Reads for security invariants & test requirements            | Threat model, trust boundaries, auth rules, sanitization  |
| `roadmap.md`    | `daw-design` (strategy) / `daw-plan` (tasks) | Drafts high-level milestone strategy & delivery phases | Authoritative for strategic release phases & milestones | Owns task decomposition & milestone progress when authorized | Strategic milestone phasing vs tactical task breakdown    |
| `deployment.md` | `daw-design`                                 | Drafts deployment topology & target envs               | Authoritative author; release pipelines & rollback      | Reads for deployment targets & environment variables         | CI/CD pipeline, environments, containerization, rollback  |
| `qa.md`         | `daw-design`                                 | Drafts test strategy & verification gates              | Authoritative author; coverage gates & test plan        | Reads for test requirements & verification gates             | Test pyramid, automated test suites, quality gates        |
| `runbook.md`    | `daw-design`                                 | Drafts initial operational triage & alerts             | Authoritative author; operational procedures & triage   | Reads for operational constraints & commands                 | Service diagnostics, triage trees, incident remediation   |

#### 2. Module Phase Ownership Rules

- **`daw-wizard` (Bootstrap Greenfield Interview):** Conducts interactive elicitation for blank projects. Generates a _proportional bootstrap specification set_ grounded in interview answers and sensible defaults (typically baseline documents: `blueprint.md`, `prd.md`, `frd.md`, `techstack.md`, and high-level `roadmap.md` strategy). Hands off to `daw-design` for enrichment, boundary validation, and builder-readiness inspection.
- **`daw-design` (Authoritative System Architecture & Adoption):** The primary custodian and authoritative author for specifications across the 13-document matrix. Creates, updates, enriches, and adopts specifications (`adopt` route, or `requirements: "unclear"` `feature` / `bootstrap` design stage; read-only `review` recommends authorized follow-up, never writes). Assesses builder-readiness and verifies consumer seams before downstream handoff. Follows the active parent route; NEVER performs recursive self-invocation (`handoff_to: "daw-design"` is strictly forbidden; handoff proceeds downstream to `daw-plan` or returns to parent).
- **`daw-plan` (Deterministic Execution Task Decomposition):** Converts design specifications or direct change requests into concrete, ordered implementation tasks with disjoint file ownership, acceptance criteria, and verification commands. Returns the structured plan directly in its stage response payload by default. NEVER forces document sprawl or creates persistent tracking files (`tasks.md`, `tracker.md`) unless requested by the user or required by repository conventions. When an authorized persistent tracking document or `roadmap.md` task-level breakdown is required, `daw-plan` owns tactical task breakdown and milestone progress updates.
- **Consistency with Finite Routes:** Clear feature routes (`requirements: "clear"`) execute via `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify`. `daw-design` is NEVER forcibly inserted when requirements and interfaces are already clear. No new routes or mandatory stages are introduced.

#### 3. Mandatory Reference Read & Write Gate (Matrix Entry, Canonical Template & Exit Criteria)

Before authoring or mutating any specification document, the authoring module MUST:

1. Read the corresponding document specification entry in §3 below to confirm Trigger, Inputs, Required Capability, Output Contract, and Exit Criterion.
2. Read the actual canonical template file at `templates/<doc>.md` to load required structural headings, sections, and checklist items.
3. Explicitly satisfy the chosen document's Output Contract, Exit Criterion, and builder-readiness seams before declaring completion. Authoring specifications without first loading the matching routing specification and template, or failing to meet its defined exit criteria, is a contract violation.

#### 4. Source Inputs, Hierarchy of Truth & Provenance

- **Templates define structure, NOT evidence:** Canonical templates provide structural scaffolding, headings, and checklists; they do not supply factual claims, software versions, or repository evidence.
- **Hierarchy of Truth:**
  1. _User Facts & Direct Directives:_ The user's explicit instructions, business goals, and constraints are ground truth.
  2. _Repository Reality:_ Existing code, dependency manifests (`package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, etc.), and normative repository documentation outrank templates.
  3. _Templates:_ Structural guidelines only. Template placeholder text NEVER overrides observed repository facts.
- **Source-Quality, Version Grounding & Domain Integrity:**
  - Technical claims regarding existing stack components, libraries, APIs, security mechanisms, or deployment topologies MUST cite actual version-matched repository configuration/code files or verified vendor/standards documentation.
  - Authors must cite the exact file path and observed version (e.g. `Node.js 20.x per package.json#engines`, `PostgreSQL 16 per docker-compose.yml`).
  - Agents MUST NEVER fabricate source citations, synthetic version numbers, or unobserved API endpoints.
  - **Preserve Existing Domain Math & Invariants:** Specification examples and models MUST NOT invent domain calculations, math formulas, schemas, or domain invariants (e.g., inventing physical vs. reserved inventory counts when only existing stock math was supplied). Existing observed domain logic and math must be preserved verbatim.
  - **Permitted Design Proposals vs. Binding Acceptance:** For new features or architecture, agents MAY legitimately propose new domain concepts, libraries, or patterns, provided they are clearly labeled as `[Agent Recommendation]` or proposed choices awaiting acceptance, rather than misrepresenting them as pre-existing observed repository facts.

#### 5. Handling Missing Sources, Unresolved Interfaces & Absence of Evidence (Fail-Safe)

- **Absence of Supplied Evidence $\neq$ Evidence of Absence:** When an architectural element, auth flow, or cloud configuration is not mentioned in the brief or workspace, the agent MUST NOT invent negative facts (e.g. asserting "no auth/cloud configured" or "no security needed"). Instead, mark the area as `[Unspecified / Open Question]`.
- **Unresolved Interfaces & Error Topologies:** Unresolved query parameters, path equivalents, error response codes (e.g. inventing 404 defaults), or fallback mechanisms MUST remain explicitly labeled as `[Agent Recommendation]` or Open Decisions. They MUST NEVER silently enter binding Acceptance Criteria (AC) or be claimed as ready/settled requirements.
- **Blocking Scope:** If network access, tooling, or required source documents are unavailable, or if a design choice cannot be grounded in observed facts:
  - The agent MUST NOT invent plausible filler or speculative assumptions.
  - The agent MUST explicitly mark the claim as `[UNVERIFIED]` or record it in an `## Open Questions` section with owner, impact, and resolution trigger.
  - The agent blocks ONLY the impacted downstream commitments or execution paths; unaffected orthogonal paths proceed.

#### 6. Proportionality & Anti-Sprawl (No Forced 13 Documents)

- The 13-document matrix is an exhaustive reference catalog, NOT a mandatory checklist for every project.
- Author ONLY the documents justified by the project scope, trigger criteria, and user intent.
- For small scoped bug fixes, refactorings, or localized patches, zero persistent document churn or minimal updates to existing specs is the standard.

#### 7. Optional Specialist Capabilities

- Specialist capabilities (e.g., application security, backend architecture, database optimization, UX architecture) are optional domain augmentations.
- They are orchestrated strictly by the parent/orchestrator at the top level when available.
- They MUST NEVER be treated as hidden required dependencies or invoked recursively. The DAW suite executes completely and deterministically using its bundled modules and inline capabilities even when zero external specialist skills are installed.

#### 8. Documentation Quality Standards, Rubric & Transition Gate

All authored documentation must satisfy the quality criteria defined in the canonical reference [Document Quality Standards & Review Rubric](document-quality.md) and machine-readable rubric [document-quality-rubric.json](document-quality-rubric.json).

- **Deterministic Transition Gate (`scripts/validate.py docs`):** Documents advance through an explicit 5-edge state machine (`intake-authoring` -> `authoring-review` -> `review-ready` / `review-rework` -> `rework-review`).
- **Parent-Owned Scope & State:** The parent orchestrator specifies the exact selected document target set via `--documents` (normalized set equality; no mandatory 13-doc requirement) and persists actual workflow state. The validator is a stateless, read-only CLI check.
- **Evidence Grounding:** Authoring and review transitions require exact line-range quotes and SHA-256 digests matching UTF-8 source files in `--project-root`.
- **Mutation Invalidation:** Review verdicts (`review-ready`) are pinned to exact document and source file hashes. Any modification of an accepted formal document invalidates prior eligibility, requiring explicit re-entry through the existing five-edge gate (`review-rework` -> `rework-review` -> `review-ready`). Code-only changes invalidate affected runtime verification and postbuild reviews without forcing unchanged documents through doc quality gates. Approvals are invalidated only when their action, target, revision, or scope changes.
- **Explicit Command Gates:** The validator is invoked explicitly at workflow transition boundaries; it does not install background daemons, supervisors, or runtime pre-tool hooks.

#### 9. Feature Delivery Contract & Routing Integration

The lifecycle of feature delivery within DAW routes integrates the procedural requirements of [Feature Delivery Contract](document-quality.md#feature-delivery-contract):

1. **Artifact & Revision Selection:** Routing evaluates actual repository files and current commit/file revisions before dispatching stages. Pre-existing specifications and plans (`prd.md`, `roadmap.md`) satisfy matrix requirements; no synthetic filenames are mandated.
2. **Prebuild Readiness Checkpoint vs. Postbuild Review:**
   - _Prebuild Readiness Checkpoint:_ For feature/spec-dependent builds, the parent orchestrator dispatches read-only `daw-review` scoped strictly to current specification and plan revisions before `daw-build`. This evaluates cross-artifact consistency, orphan tasks, unmapped criteria, and parallel execution safety (`[P]` flag safety) without inserting synthetic stages into the manifest and without module recursion.
   - _Plan Self-Check:_ Planning (`daw-plan`) performs its own internal check for requirement coverage and acyclic dependencies before handoff.
   - _Route-Required Postbuild Review:_ For routes that explicitly include postbuild review (`feature`, `bugfix`), postbuild `daw-review` audits modified code, diffs, and fresh runtime evidence; a prebuild checkpoint cannot satisfy it. Do not insert `daw-review` into routes that do not require it (such as `patch`, which runs `daw-plan` -> `daw-build` -> `daw-verify`). Verification always runs per the active route pipeline.
3. **Scoped Pause/Resume with Canonical Statuses:** Execution halts use canonical handoff and acceptance statuses (`blocked`, `in_progress`, `ready`, `completed`, `failed`). When blocked on missing material decisions or ungranted approvals, the affected node halts as `blocked` and records reason, responsible party, question, next permitted action, revisions, and evidence in parent acceptance or handoff details. Resuming revalidates prerequisites, scope, and approvals.
4. **Governance & Template Override Scope Guard:** Discovered local scripts, commands, and template overrides cannot weaken core safety gates or acceptance criteria. No feature implementation during governance-only edits.
5. **Authorized Command Execution:** Verification commands must actually execute and be inspected empirically; echoing commands or checked task boxes do not constitute proof.

---

### 1. `blueprint.md` — System Architecture & Foundational Design

- **Trigger:** Greenfield system initiation, major platform rewrite, or introducing a core multi-service domain boundary.
- **Inputs & Prerequisites:** High-level project brief, business vision, core domain requirements (or relevant existing equivalent documentation).
- **Required Capability:** Explicit inline orchestrator (systems analysis, modular design, domain seams, AI-navigability).
- **Conditional Capabilities:**
  - Backend architecture capability — When distributed services, event buses, message queues, or high-throughput concurrency models are involved.
  - Codebase memory & graph mapping capability — When integrating into an existing multi-repo or complex enterprise codebase requiring caller/dependency graph mapping.
  - Codebase design & module structuring capability — Optional specialist capability for modular structure and deep interfaces.
- **Template Link:** [blueprint.md](../templates/blueprint.md)
- **Output Contract:** High-level topology, component relationships, module boundaries, cross-cutting architectural invariants, and directory structuring rules.
- **Exit Criterion:** Blueprint reviewed and validated against user constraints; module boundaries establish clean encapsulation without circular couplings.
- **Downstream Handoff:** Feeds into `brd.md`, `prd.md`, and `techstack.md` (or existing project architecture equivalents).
- **Stop / Replan Trigger:** Unresolved cross-system dependency cycles or undefined hardware/cloud platform constraints.

---

### 2. `brd.md` — Business Requirements Document

- **Trigger:** Strategic business initiatives, commercial client scopes, internal operational improvements, multi-stakeholder commercial goals, ROI-driven milestones.
- **Inputs & Prerequisites:** Stakeholder goals, executive brief, operational budgets (if available), market timing constraints, target KPIs (if defined; do not invent arbitrary numbers). Relevant existing equivalent documentation accepted.
- **Required Capability:** Explicit inline orchestrator (business requirements synthesis is driven by project context and user constraints; no single synthetic author skill overrides user business directives).
- **Conditional Capabilities:**
  - `competitive-landscape` — _Strictly conditional_: Only when user **explicitly requests SEO market leader analysis or organic positioning research**. Omit by default.
  - `competitor-analysis` — _Strictly conditional_: Only when user **explicitly requests organic competitor search research**; mere mention or provision of a competitor list does NOT grant permission to run SEO research tools.
- **Template Link:** [brd.md](../templates/brd.md)
- **Output Contract:** Business objectives, success metrics (OKRs/KPIs), stakeholder impact, budget/timeline constraints, cost/benefit boundary, and out-of-scope definitions.
- **Exit Criterion:** Measurable business metrics defined; clear delineation between business scope and technical execution.
- **Downstream Handoff:** Feeds into `prd.md` and `roadmap.md`.
- **Stop / Replan Trigger:** Conflicting stakeholder objectives or undefined business success criteria.

---

### 3. `prd.md` — Product Requirements Document

- **Trigger:** Definition of user-facing capabilities, feature epics, administrative tools, or backend product interfaces.
- **Inputs & Prerequisites:** `brd.md` (or relevant existing equivalent), project context, user problem statements.
- **Required Capability:** Explicit inline orchestrator (product definition and scope bounding; synthesizes requirements directly from user intent).
- **Conditional Capabilities:**
  - UX architecture capability — _Conditional_: When defining multi-step user workflows, navigational hierarchies, or complex user state interactions. Omit for backend-only PRDs.
  - API platform engineering capability — _Conditional_: When the product surface is primarily an API/platform for external integration.
- **Template Link:** [prd.md](../templates/prd.md)
- **Output Contract:** User personas, user stories with granular acceptance criteria (Given/When/Then), non-functional requirements (NFRs), and explicit edge cases.
- **Exit Criterion:** Every user story has verifiable acceptance criteria; non-goals clearly stated.
- **Downstream Handoff:** Feeds into `frd.md`, `roadmap.md`, and (for user-facing features only) `wireframe.md`, `design.md`, and `ui-ux.md`. (Backend-only features do not hand off to downstream UI specifications).
- **Stop / Replan Trigger:** Ambiguity in acceptance criteria or conflicting user story requirements.

---

### 4. `frd.md` — Functional Requirements Document

- **Trigger:** Engineering translation of product requirements into exact system mechanics, validations, state transitions, and business logic.
- **Inputs & Prerequisites:** `prd.md` (or relevant existing equivalent), domain data dictionary.
- **Required Capability:** Explicit inline orchestrator (systems analysis and technical requirement decomposition).
- **Conditional Capabilities:**
  - API platform engineering capability — When an actual external or internal API boundary, REST/OpenAPI contract, or endpoint schema is being defined.
  - Backend architecture capability — When transactions, concurrency locks, state machines, or distributed workflows must be specified.
  - `engineering-minimal-change-engineer` — When modifying existing complex functional logic to ensure minimal disruption to surrounding logic.
- **Template Link:** [frd.md](../templates/frd.md)
- **Output Contract:** Input validation matrices, state transition diagrams, internal data transformations, error response codes (where applicable to the interface), and idempotency guarantees (where state-mutating operations exist). Technical module and DB design are defined in `techstack.md` and `blueprint.md`; FRD remains non-technical where appropriate.
- **Exit Criterion:** Complete coverage of all PRD user stories with concrete functional definitions and state handling.
- **Downstream Handoff:** Feeds into `techstack.md`, `qa.md`, and direct implementation.
- **Stop / Replan Trigger:** Contradictory state transitions or unhandled error recovery paths.

---

### 5. `techstack.md` — Technology Stack & Infrastructure Specification

- **Trigger:** Selection or standardization of frameworks, databases, libraries, infrastructure runtimes, and external third-party SDKs.
- **Inputs & Prerequisites:** `blueprint.md`, `frd.md` (or relevant existing equivalents), hosting constraints, existing repository dependency manifests.
- **Required Capability:** Explicit inline orchestrator (evaluating repo tech constraints against requirements).
- **Conditional Capabilities:**
  - Backend architecture capability — When selecting persistence stores, messaging queues, or microservice fabrics.
  - `database-optimizer` — When choosing database engines, schema normalization, indexing, or migration frameworks.
  - API platform engineering capability — When deciding REST, gRPC, GraphQL, or OpenAPI standards.
- **Template Link:** [techstack.md](../templates/techstack.md)
- **Output Contract:** Selected languages, runtimes, database engines, external APIs, build tools, dependency versions, and architectural decision records (ADRs) explaining trade-offs.
- **Exit Criterion:** All stack components verified compatible; zero unvetted dependencies; license constraints checked.
- **Downstream Handoff:** Feeds into `security.md` and `deployment.md`.
- **Stop / Replan Trigger:** License incompatibilities, unmaintained dependencies, or environmental runtime constraints (e.g., unsupported OS or node/compiler versions).

---

### 6. `design.md` — Visual Design System & Component Library Specification

- **Trigger:** Authoring visual design systems, design tokens (colors, spacing, typography, elevation), shared component libraries, and UI themes. (Note: Low-level software/module design belongs in `blueprint.md`, `frd.md`, and `techstack.md`).
- **Inputs & Prerequisites:** `prd.md`, `wireframe.md` (or relevant existing equivalents), brand assets, style guidelines. A user-supplied or wizard-drafted root `DESIGN.md` in the open [DESIGN.md format](https://github.com/google-labs-code/design.md/blob/main/docs/spec.md) is the normative token source when present; this spec references its tokens instead of redefining them.
- **Required Capability:** Explicit inline orchestrator (visual layout, theme definitions, and component hierarchies).
- **Conditional Capabilities:**
  - UI design capability — Optional specialist capability when authoring a dedicated shared design system, token dictionary, or reusable component library.
  - Interface styling capability — Optional specialist capability for interface visual styling and refinement.
  - Accessibility & token contrast auditing capability — When auditing design token color systems and dark mode palette contrast compliance.
  - `antislop-ui` — When ensuring UI components avoid generic templates and maintain polished craft.
- **Template Link:** [design.md](../templates/design.md)
- **Output Contract:** Design token dictionary (CSS variables / theme definitions for colors, typography, spacing, border radii, shadows where relevant), component inventory of actual screens being built (no universal obligation to specify generic Button/Card components if not present on screen), and token contrast matrix.
- **Exit Criterion:** All primary UI components in scope mapped to explicit design tokens; contrast ratios meet the repository or user-required standard (defaulting to WCAG AA; never arbitrarily lowering or raising to AAA without requirement).
- **Downstream Handoff:** Feeds into `ui-ux.md` and frontend component implementation.
- **Stop / Replan Trigger:** Incompatible brand palettes failing accessibility contrast or undefined token scales.

---

### 7. `wireframe.md` — Structural UI Wireframes & Layout Hierarchy

- **Trigger:** User interface screen layout definition, structural content blocks, information hierarchy, and viewport layout grids.
- **Inputs & Prerequisites:** `prd.md` (or relevant existing equivalent), user journey maps.
- **Required Capability:** Explicit inline orchestrator (screen layout, informational hierarchy, structural ASCII/text layout).
- **Conditional Capabilities:**
  - UX architecture capability — Optional specialist capability for UX architecture, grid systems, and responsive layout hierarchies.
  - Frontend visual hierarchy capability — When defining landing pages, portfolios, or marketing layouts requiring distinctive visual hierarchy.
  - `antislop-layoutmobile` — When wireframing layouts that must reflow responsively across mobile breakpoints and desktop viewports.
- **Template Link:** [wireframe.md](../templates/wireframe.md)
- **Output Contract:** Structural ASCII/text layout blocks, viewport breakpoint rules (mobile, tablet, desktop), navigation hierarchy, and content region definitions.
- **Exit Criterion:** All primary screen regions mapped to layout containers; responsive reflow rules specified across target viewports.
- **Downstream Handoff:** Feeds into `design.md` and `ui-ux.md`.
- **Stop / Replan Trigger:** Complex navigational dead-ends or unresolvable screen real estate constraints.

---

### 8. `ui-ux.md` — Interactive Behaviors, Micro-interactions & Accessibility States

- **Trigger:** Interactive states (hover, active, disabled, focus-visible), micro-interactions, motion curves, keyboard navigation, and full accessibility trees. (Builds on visual tokens in `design.md` without duplicating them).
- **Inputs & Prerequisites:** `wireframe.md`, `design.md` (or relevant existing equivalents).
- **Required Capability:** Explicit inline orchestrator (interaction states, keyboard navigation, and accessibility semantics).
- **Conditional Capabilities:**
  - `antislop-human` — Optional specialist capability for accessibility, color contrast, keyboard navigation, and interactive UI states.
  - `mobile-native` — _Conditional_: When resolving mobile viewport constraints, touch gestures, mobile notch handling, or PWA offline sync known issues.
  - Micro-interaction & animation capability — For refined micro-interactions, spring curves, and delicate animation polish.
  - Native platform gestures & materials capability — _Strictly conditional_: Only when implementing native-feeling iOS/macOS web gestures, spring animations, sheets, or translucent materials.
- **Template Link:** [ui-ux.md](../templates/ui-ux.md)
- **Output Contract:** Component interaction state machine (loading, empty, error, active, disabled, focused), keyboard navigation traps/landmarks, ARIA role mappings, and transition timing specifications.
- **Exit Criterion:** Keyboard and focus invariants specified meeting the repository/user-required accessibility standard (default WCAG AA; no unsolicited deviation); interactive state transitions fully mapped.
- **Downstream Handoff:** Feeds into frontend implementation and `qa.md`.
- **Stop / Replan Trigger:** Inaccessible focus management or unresolvable layout overflow constraints.

---

### 9. `security.md` — Threat Modeling, Vulnerability Mitigation & Security Controls

- **Trigger:** Data persistence, authentication/authorization implementation, external network ingest, payment flows, or cryptographic handling.
- **Inputs & Prerequisites:** `blueprint.md`, `techstack.md` (or relevant existing equivalents).
- **Required Capability:** Explicit inline orchestrator (threat modeling, input validation matrices, authentication/authorization boundaries, and security controls).
- **Conditional Capabilities:**
  - Application security & threat modeling capability — Optional specialist capability for OWASP Top 10 auditing, threat modeling, input validation, and authentication hardening.
  - AppSec engineering & trust boundary capability — For formal threat modeling (STRIDE), SAST/DAST setup, and trust boundaries.
  - SecOps, CORS & secrets management capability — For secrets management, CORS configurations, rate limiting, and defensive headers.
- **Template Link:** [security.md](../templates/security.md)
- **Output Contract:** Threat model, data classification matrix, authentication & session handling specification, RBAC/ABAC rules, input sanitization rules, and encryption policies (at rest and in transit).
- **Exit Criterion:** Specified security controls and automated verification plan defined for all identified threats; zero hardcoded secrets. (Empirical proof occurs at execution verification gate).
- **Downstream Handoff:** Feeds into `deployment.md`, `qa.md`, and code implementation.
- **Stop / Replan Trigger:** Unresolvable security vulnerabilities or architectural violations of principle of least privilege.

---

### 10. `roadmap.md` — Milestone Planning, Phasing & Work Breakdown

- **Trigger:** Multi-phase project delivery, dependencies sequencing, team task breakdown, and sprint milestone definitions.
- **Inputs & Prerequisites:** `prd.md`, `techstack.md` (or relevant existing equivalents), stakeholder timeline expectations.
- **Required Capability:** Explicit inline orchestrator (translates overall specification into sequenced deliverables; notes: implementation planning skills are strictly for tactical code execution plans, not strategic roadmaps).
- **Conditional Capabilities:**
  - `writing-plans` — _Conditional_: When decomposing an individual milestone into a granular multi-step technical execution plan before touching code.
- **Template Link:** [roadmap.md](../templates/roadmap.md)
- **Output Contract:** Milestone definitions (Phase 0, 1, 2...), task dependency graphs, deliverable artifacts per phase, and critical path identification.
- **Exit Criterion:** Every task has clear upstream dependencies and distinct completion criteria; critical path identified.
- **Downstream Handoff:** Feeds into sprint execution, tracking, and `qa.md` phase milestones.
- **Stop / Replan Trigger:** Circular task dependencies or unmeetable hard deadline constraints.

---

### 11. `deployment.md` — Infrastructure, Release Pipeline & Environment Configuration

- **Trigger:** Deployment configuration, CI/CD pipeline automation, containerization, hosting topology, and rollback procedures.
- **Inputs & Prerequisites:** `techstack.md`, `security.md` (or relevant existing equivalents), environment secrets manifests (references and variable names ONLY, never secret values).
- **Required Capability:** Explicit inline orchestrator (environment configuration, containerization, CI/CD pipelines, and release rollback procedures).
- **Conditional Capabilities:**
  - DevOps & infrastructure automation capability — Optional specialist capability for Docker, compose, systemd, CI/CD workflows, and Linux networking.
  - CI/CD & pipeline automation capability — When constructing cloud infrastructure automation or GitHub Actions pipelines.
  - `vercel-deploy-github-flow` — _Strictly conditional_: Only when deploying web frontends to Vercel via GitHub flow.
  - `deploy-inventory30-hp-server` — _Strictly conditional_: Only when deploying inventory3.0 target to hp-server.
- **Template Link:** [deployment.md](../templates/deployment.md)
- **Output Contract:** Environment variables matrix, container build instructions, CI/CD pipeline definition, health check endpoints, and targeted rollback procedures specifying exact immutable release ID (Git SHA) and pre-change snapshot ID.
- **Exit Criterion:** Automated deploy and rollback steps specified deterministically with zero manual ambiguity.
- **Downstream Handoff:** Feeds into `runbook.md` and operations execution.
- **Stop / Replan Trigger:** Missing production credentials or unverified host environments.

---

### 12. `qa.md` — Quality Assurance, Test Strategy & Verification Plan

- **Trigger:** Test plan definition for feature verification, test pyramid allocation, performance baselines, and release sign-off.
- **Inputs & Prerequisites:** `prd.md`, `frd.md` (or relevant existing equivalents).
- **Required Capability:** Explicit inline orchestrator (defines comprehensive test matrix, acceptance verification steps, and regression checks directly against requirements).
- **Conditional Capabilities:**
  - `tdd` — _Conditional_: Strictly when actually implementing test-first features/bugfixes or uncertain logic requiring red-green-refactor isolation.
  - Test automation capability — For Playwright/Cypress end-to-end browser workflows and UI regression suites.
  - Performance benchmarking capability — _Conditional_: Only when explicit performance, load SLAs, latency targets, or memory profiling are scoped.
- **Template Link:** [qa.md](../templates/qa.md)
- **Output Contract:** Test pyramid coverage targets, specific test scenarios with expected outcomes, regression checklists, performance benchmarks, and synthetic test data sets.
- **Exit Criterion:** 100% of functional requirements mapped to test cases; automated test commands specified.
- **Downstream Handoff:** Guides code verification layer and release sign-off.
- **Stop / Replan Trigger:** Unverifiable acceptance criteria or untestable system architectures.

---

### 13. `runbook.md` — Incident Response, Operational Procedures & Observability

- **Trigger:** Production readiness, on-call operational handoff, disaster recovery planning, and service maintenance procedures.
- **Inputs & Prerequisites:** `blueprint.md`, `deployment.md`, `security.md` (or relevant existing equivalents).
- **Required Capability:** Explicit inline orchestrator (incident response runbooks, operational triage commands, diagnostic procedures, and service health checks).
- **Conditional Capabilities:**
  - DevOps & infrastructure automation capability — Optional specialist capability for systemd services, log inspection, process management, and networking diagnostics.
  - `diagnose-crash` — For handling segfaults, core dumps, memory panics, and unexpected fatal process exits.
  - Systematic debugging capability — For step-by-step triage procedures during complex distributed failures.
- **Template Link:** [runbook.md](../templates/runbook.md)
- **Output Contract:** Service architecture summary, health inspection commands, triage decision trees, step-by-step incident remediation runbooks, backup/restore procedures referencing immutable snapshot IDs, and escalation paths.
- **Exit Criterion:** All primary failure modes have actionable, copy-pasteable triage commands; operational procedures and evidence collection status documented. (Operational evidence status reflects actual collected facts; exit criteria never mandate executing live harmful recovery actions or destructive rollbacks during document drafting).
- **Downstream Handoff:** Handed to operational engineers and on-call teams.
- **Stop / Replan Trigger:** Undocumented critical dependencies, missing backup verification steps, or unresolved conflicts between user instructions and repo documentation (stop and flag material conflicts rather than making unilateral assumptions).

---

## 4. Exception Handling, Missing Skills & Conflict Resolution

1. **Missing or Unavailable Specialist Skills:**
   - Specialist skills are optional capability enhancements. If a designated specialist skill is not installed or available in the environment, the orchestrator authors the document inline using standard requirements engineering.
   - An orchestrator must never guess or hallucinate proprietary commands.
   - For specialized operational actions requiring external execution tools or host capabilities, the orchestrator cannot claim the capability is present if absent; report the exact blocker and complete reachable work.
   - If a specialist skill's prompt or instructions instruct behavior that conflicts with user explicit constraints, system limits, or repo conventions, **user constraints and repo conventions strictly override skill instructions**.
   - Never expand project scope based solely on generic suggestions in specialist skill files.
2. **No Recursive Routing & Progressive Disclosure of Supporting Resources:**
   - Under no circumstances may an agent reading `routing.md` invoke `deterministic-agentic-workflow` as a child task. Routing is a top-level deterministic mapping, executed once per planning stage.
   - **Reading Scoped Support Resources is NOT Module Invocation:** The suite maintains exactly 11 public execution modules (`skills/daw-*/`). Supporting resources (`references/change-coupling.md`, `references/grilling.md`, `skills/daw-design/references/domain-modeling.md`, `skills/daw-design/references/builder-readiness.md`) are documentation files for on-demand progressive disclosure. Reading these resources does not constitute module dispatch, child skill discovery, or sub-task execution.
   - Supporting references grant no new execution permissions or tools, and loading them does not spawn background workers.
   - **Targeted Reference Lookups:** When consulting reference manuals (`routing.md`, `operations.md`), agents MUST use progressive disclosure—querying or reading ONLY the specific section heading or line range needed rather than ingesting entire multi-thousand-line references upfront.
   - Parent agents retain full control over delegation. If an independent assessment of builder-readiness is warranted, the parent delegates to the existing `daw-review` module rather than recursively re-dispatching design or creating ad-hoc wrapper skills.
   - Handoff schema contracts remain fixed: any protocol-specific status or findings belong under the existing optional `details` object without introducing new required top-level JSON fields.

---

## 5. Canonical Module Handoff Contract

This section defines the canonical output envelope produced by all 11 internal execution modules (`daw-design`, `daw-plan`, `daw-debug`, `daw-build`, `daw-review`, `daw-verify`, `daw-workspace`, `daw-ask`, `daw-setup`, `daw-wizard`, `daw-untangle`).

> **Contract Scope Note:** This schema defines the **runtime module handoff contract** returned across module completion stages. It is distinct from the top-level route decision payload emitted by `scripts/route.py` and the task verification envelope checked by `scripts/validate.py`.

### Canonical Handoff Schema

> **Observable Transition Checkpoint Invariant:** Canonical output handoffs MUST be delivered and observable as complete JSON envelopes BEFORE advancing to the next stage, not deferred to final retrospective prose or remembered only in thoughts. Full actual JSON MUST be delivered and inspectable by the parent orchestrator via the preferred transport mechanism (or an explicit inline fallback checkpoint if no structured transport exists; see [User-Facing Reports & Handoff Transport](#user-facing-reports--handoff-transport)). The agent MUST NOT unconditionally dump full raw JSON into normal user-facing chat output unless explicitly requested. If subagent tools or external delegators are unavailable, execute directly via honest direct fallback in the current session.

Every execution module returns a JSON object adhering to this structure:

```json
{
  "objective": "Concise single-sentence summary of the executed stage.",
  "input_paths": ["docs/specs/blueprint.md", "src/service.py"],
  "output_paths": ["src/service.py", "tests/test_service.py"],
  "acceptance_criteria": [
    {
      "criterion": "Target null pointer exception reproduced with a failing unit test.",
      "status": "pass"
    },
    {
      "criterion": "Regression test suite passes without errors.",
      "status": "pass"
    }
  ],
  "evidence": [
    {
      "reference": "pytest tests/test_service.py::test_reproduce_npe",
      "summary": "Observed test pass output proving fix resolves root cause without regressions."
    }
  ],
  "status": "pass",
  "handoff_to": "daw-review",
  "details": {
    "module": "daw-build",
    "diff_summary": "Added defensive None check on payload header parsing.",
    "files_changed": 1
  }
}
```

### Field Definitions & Requirements

1. **`objective` (string, required):**
   - Nonblank single sentence stating the concrete achievement of this specific stage.
2. **`input_paths` (array of strings, required):**
   - Explicit file paths read, inspected, or evaluated. Empty array `[]` is permitted for read-only conversational stages, intake queries, or when operating strictly in-memory without disk dependencies.
3. **`output_paths` (array of strings, required):**
   - Explicit file paths created, modified, or written during this stage. Empty array `[]` is permitted for read-only evaluations (e.g. `daw-review`, `daw-ask`, diagnosis phases) or stages producing no disk artifacts.
4. **`acceptance_criteria` (array of objects, required):**
   - List of verifiable stage criteria evaluated. Each object must have:
     - `criterion` (string): Description of the condition.
     - `status` (`"pass"` | `"fail"` | `"blocked"`): Discrete outcome of this criterion.
5. **`evidence` (array of objects, required):**
   - Verifiable empirical proof of stage execution. Each object must have:
     - `reference` (string): Identifier of the observation, command run, diff reference, or tool log ID (does not need to be a new file on disk).
     - `summary` (string): Concise summary of what was observed.
6. **`status` (string, required):**
   - Discrete execution status: `"pass"`, `"fail"`, or `"blocked"`.
   - **Stage-Scoped & Proposed Pass Invariant:** `status: "pass"` is a module self-report certifying ONLY that the current module proposes its stage-specific criteria were satisfied. It is NEVER proof of parent acceptance, end-to-end task completion, full system implementation, production readiness, or operational authorization.
   - **Parent Acceptance vs. Proposed Pass:** As defined in the canonical [Parent Acceptance Checkpoint](operations.md#parent-acceptance-checkpoint), the parent orchestrator independently evaluates results across explicit [Checkpoint Boundaries](operations.md#checkpoint-boundaries) and records decisions via the [Parent-Owned Acceptance Record](operations.md#parent-owned-acceptance-record). Dispatch completion or a proposed worker `pass` does not equal parent stage acceptance (`accepted` / `not accepted`). Reported passes with missing, unexercised, or contradicted evidence are rejected as `not accepted`. Worker-supplied `details` are NOT parent decisions. Optional criterion-to-evidence mappings use existing parent `details` or plan artifacts without altering the outer schema.
   - `fail`: Executed criteria failed, produced errors, or were incomplete.
   - `blocked`: Execution could not proceed due to missing prerequisites, environment context, unverified risk, or missing exact interactive approval.
   - Rich findings inside `details` cannot override the outer `status`.
7. **`handoff_to` (string or null, required):**
   - Name of the recommended next canonical execution module (e.g., `"daw-verify"`, `"daw-review"`), or `null` if the pipeline has concluded or halted.
   - **Advisory Invariant:** `handoff_to` is purely advisory metadata returned to the parent orchestrator. Modules MUST NOT directly invoke child modules or recursively dispatch routing.
   - Parent-controlled corrective rounds may resume retained workers without changing the active route or allowing module recursion. See the [persistent worker graph contract](operations.md#persistent-worker-graphs-harness-native) and the [Parent Acceptance Checkpoint](operations.md#parent-acceptance-checkpoint): only accepted current-revision results satisfy dependencies via mandatory pre-dispatch joins, and a correction invalidates affected downstream passes. Canonical outer outcomes remain strictly `pass`, `fail`, and `blocked`; `not accepted` is solely the parent's evaluation decision label, never a new outer JSON envelope status. Downstream pending work strictly precludes declaring the final workflow complete.

8. **`details` (object, required):**
   - Module-specific domain payload (e.g. diagnostics, test summaries, review findings, workspace branches). Details preserve rich information defined by the current active module's output contract (such as `tasks` with `target_files` and `verification_command` in `daw-plan`, separate `stage_1_conformity` and `stage_2_technical_audit` in `daw-review`, and `checks` with runtime evidence in `daw-verify`), but remain subordinate to the outer `status`.

### User-Facing Reports & Handoff Transport

This section defines the canonical governance rules separating internal machine-readable handoffs from user-facing presentations across the DAW suite.

#### 1. Separation of Concerns & Internal Handoff Rigor

- **Internal Canonical Integrity:** Canonical output handoffs require the complete JSON envelope defined in [Canonical Handoff Schema](#canonical-handoff-schema). All outer fields (`objective`, `input_paths`, `output_paths`, `acceptance_criteria`, `evidence`, `status`, `handoff_to`, `details`) remain mandatory. The full actual JSON MUST be delivered and inspectable by the parent orchestrator before any downstream stage transition, not deferred to a final summary or remembered only in internal model thoughts.
- **User-Facing Separation:** Internal JSON handoffs are intended for deterministic workflow orchestration and parent acceptance. They MUST NOT be unconditionally dumped into conversational replies to human users.

#### 2. Transport Hierarchy & Preference Order

When executing module handoffs across stages, workers, or subagents, agents MUST adhere to this explicit transport preference hierarchy:

1. **Primary Transport (Preferred): Actual Module / Tool / Subagent Return:**
   - Deliver the canonical JSON envelope via the structured return value of the execution tool, subagent yield mechanism, or explicit harness-native message/checkpoint channel. The parent orchestrator inspects the structured return directly.
2. **Secondary Transport: Authorized Workflow Artifact:**
   - When authorized by the workflow or task contract, the canonical JSON handoff may be written to an explicitly designated artifact file on disk.
   - The exact artifact reference MUST be supplied in the completion notification and its content inspected by the parent orchestrator before transition.
   - _Strict Authorization & Read-Only Safety:_ Fabricated hidden channels are prohibited. There is NO implicit authorization to create disk files. Read-only modules (`daw-ask`, `daw-review`, `daw-untangle`, diagnostic audits) are strictly prohibited from writing unrequested transport files to disk and must use structured tool returns or inline fallbacks.
3. **Fallback Transport: Clearly Labeled Inline JSON Fallback Checkpoint:**
   - When no real non-chat transport exists and no authorized artifact is available (such as direct execution in a single chat session without subagent return structures), the agent MUST emit a complete, clearly labeled inline JSON checkpoint in the transcript BEFORE proceeding to downstream execution.
   - This checkpoint MUST be explicitly identified as an internal fallback checkpoint for observability (e.g. `### Internal Handoff Checkpoint (Observable Fallback)`), distinct from the user report. A natural-language summary NEVER replaces the required canonical handoff envelope.

#### 3. Default User-Facing Reports Contract

Default user-facing responses from orchestrators or directly invoked modules MUST be concise natural language in the user's language, structured into these four bounded parts:

1. **Result & Artifacts:** High-level summary of the stage outcome and relevant created/modified artifact paths.
2. **Exercised Verification & Limits:** Checks and tests actually exercised, observed empirical outcomes, and tool/session limits. Prior evidence or transcripts provided to the agent MUST be labeled as provided/retained, never rerun or claimed as fresh executions. Preserve reported transition names and outcomes (e.g., "review-ready eligible") exactly as supplied without relabeling them as earlier or later workflow states or certifying semantics.
3. **Unresolved Decisions & Scope:** Any pending ambiguities, open decisions, or blocked criteria, explicitly identifying their affected scope and whether they are blocking or non-blocking.
4. **Next Concrete Action:** Exactly one unambiguous, actionable next step.

_User-Facing Presentation Constraints:_

- Normal final replies MUST NOT duplicate the full JSON envelope or lengthy raw command logs.
- **Explicit Format Request Exception:** If the user explicitly requests JSON, machine-readable output, or exact CLI output (or when the module is invoked under an exact CLI output contract), preserve the requested format and CLI output contracts unchanged.
- When an inline JSON fallback checkpoint is required for observability under Fallback Transport, it must be clearly labeled as a fallback checkpoint and separated from the concise natural-language user report.

#### 4. Discrete State & Scope Distinctions

Agents and parent orchestrators MUST maintain clear semantic distinctions between five separate lifecycle states:

1. **Stage Pass:** The worker or module self-reports that its stage-specific criteria were satisfied (`status: "pass"`).
2. **Gate Eligibility:** Preflight, dependency joins, and prerequisite criteria are satisfied to enter an evaluation gate.
3. **Parent Acceptance:** The parent orchestrator independently inspects primary observable evidence against expected outcomes and accepts the stage (`accepted`).
4. **Workflow Completion:** All required route criteria are accepted, and zero required downstream, review, or verification tasks remain pending or blocked.
5. **Application / Runtime Readiness:** The system is compiled, packaged, deployed, or actively operating in its target runtime environment.

_Inference Guardrail:_ Structural documentation gates (such as completing specification drafts) do NOT imply semantic or business correctness, and do NOT certify global application or runtime readiness. Unresolved decisions or local failures block only their affected work scope, not automatically the entire project. When certainty cannot be established from empirical facts, report uncertainty truthfully rather than inventing blocker classifications.

## 6. Direct Module Invocation & Governance Loader Sequence

The DAW suite supports modular execution where individual modules may be invoked directly or discovered as top-level skills (e.g., via sibling symlinks). Direct module invocation MUST NOT bypass root suite governance.

### The Mandatory Governance Loader Sequence

Whenever any execution module (`skills/daw-*/SKILL.md`) is invoked directly, it must execute the following deterministic governance sequence before performing any work:

1. **Physical Root Resolution:**
   - Resolve the module's physical symlink target to locate the true canonical module directory.
   - Determine the suite root (`../..` relative to canonical module directory).
2. **Intake & Governance Loading:**
   - Read root `SKILL.md` §4 (Preflight Checks, Coexistence & High-Risk Gating) and §6 (Canonical Module Handoff Contract).
   - Read `references/routing.md` §5 (Canonical Module Handoff Contract).
   - Safe read-only intake, query processing, and contextual assessment proceed without requiring operational approvals or clean workspaces.
3. **Pre-Mutation Operational Evaluation:**
   - BEFORE executing any state mutation, command with side-effects, or disk modification, load relevant preflight and risk rules from `references/operations.md`.
   - Determine change risk level from observable facts:
     - **Low-Risk Local Edits:** Local code fixes, unit tests, and documentation are classified directly from facts without asking unnecessary confirmation.
     - **High-Risk Operations:** Production deployments, destructive migrations, cloud infrastructure changes, or external service modifications require **exact, interactive operator authorization at the point of risk**. Structural references (PR links, issue tags) do NOT grant authorization.
     - **Unknown Risk / Unknown Scope:** If risk, target environment, or mutation boundaries cannot be verified from facts, halt immediately with outer `status: "blocked"` before any mutation occurs.
4. **Deterministic Stage Completion:**
   - Execute stage tasks and produce empirical evidence.
   - Return output adhering strictly to the Canonical Module Handoff Contract (§5) to the caller.
