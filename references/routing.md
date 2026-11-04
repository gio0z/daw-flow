# Document Routing, Intent Precedence & Suite Manifest Reference

This reference defines the routing engine policy, intent precedence hierarchy, execution pipeline dispatch, and handoff contracts for the Deterministic Agentic Workflow (DAW) suite.

Article Reference: Rama Digital — _Agentic Tapi Deterministic Workflow AI Agent_ (https://ramadigital.id/blog/agentic-tapi-deterministic-workflow-ai-agent).  
_Advice separation note:_ Core article principles (generative planning, deterministic mutation, document contracts, verification gates) establish the architectural foundation. Local operational additions in this reference define structured handoff schemas, lifecycle routing, and domain capability delegation for multi-agent CLI and workstation environments.

---

## 1. Intent Precedence & Routing Hierarchy

Routing in DAW is deterministic and requires classified input facts. The workflow does not rely on open-ended keyword heuristics. Incoming engineering tasks are mapped into one of 8 finite intents:

| Precedence | Intent      | Classification Criteria                                                                                 | Read-Only | Doc-Only | Stage Pipeline                                                                                                                                         |
| :--------: | :---------- | :------------------------------------------------------------------------------------------------------ | :-------: | :------: | :----------------------------------------------------------------------------------------------------------------------------------------------------- |
|   **1**    | `review`    | Diff review, security posture audit, boundary compliance check.                                         |    Yes    |    No    | `daw-review`                                                                                                                                           |
|   **2**    | `ask`       | Conversational architecture guidance, Q&A, trade-off analysis.                                          |    Yes    |    No    | `daw-ask`                                                                                                                                              |
|   **3**    | `setup`     | Interactive configuration setup, tool command discovery, and repo convention block authoring.           |    No     |   Yes    | `daw-setup`                                                                                                                                            |
|   **4**    | `bootstrap` | Greenfield specification generation from a product brief in empty directory.                            |    No     |   Yes    | `daw-wizard` -> `daw-design` -> `daw-plan`                                                                                                             |
|   **5**    | `adopt`     | Reverse-engineering existing codebase to author missing specifications.                                 |    No     |   Yes    | `daw-design` -> `daw-plan`                                                                                                                             |
|   **6**    | `bugfix`    | Defect resolution requiring RCA, minimal fix, and regression test.                                      |    No     |    No    | `daw-debug` -> `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify`                                                                               |
|   **7**    | `patch`     | Pre-diagnosed minimal change or surgical fix with zero spec changes (requires `requirements: "clear"`). |    No     |    No    | `daw-build` -> `daw-verify`                                                                                                                            |
|   **8**    | `feature`   | New capability or functional evolution requiring plan, build, review, and verification.                 |    No     |    No    | Clear: `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify`<br>Unclear: `daw-design` -> `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify` |

- When user intent is evaluation, code audit, or PR review, `review` takes precedence.
- When user intent is conversational Q&A, guidance, or trade-off evaluation, `ask` takes precedence.
- Read-only user intent always wins: `review` and `ask` ignore risk and workspace preferences and never mutate code or specifications.
- **Read-Only `daw-ask` vs. Authorized `daw-design` Docs Handoff:** `daw-ask` is strictly read-only. It answers queries, explores trade-offs, and inspects the decision frontier, but it **never** writes or modifies workspace documents or specs. When conversational guidance reveals that new or modified specification documents are required, the workflow transitions to an explicitly authorized `daw-design` stage (e.g., under `bootstrap`, `adopt`, or `feature` intents). Direct questions and small settled changes do not trigger the structured grilling ceremony.

### Workspace Isolation & Preflight Invariants

If `evaluates_workspace` is enabled in the manifest for mutating intents (`bugfix`, `patch`, `feature`):

- `workspace: "isolated"`: The router prepends `daw-workspace` to the stages pipeline.
- `workspace: "in-place"`: The router proceeds without prepending `daw-workspace`.
- `workspace: "unknown"`: The router sets status to `needs-input` with an explicit blocker.
- **Dirty Tree Invariant:** Preflight checks never require a clean git tree. User uncommitted changes are preserved.
- **Rollback & Credentials:** External cloud credentials or rollback targets are checked only for high-risk infrastructure/deployment actions.

---

## 2. Declarative Suite Manifest Policy & Route Engine

Routing policy is declared statically in [references/suite-manifest.json](suite-manifest.json) under `schema_version: 1`. The route engine validates requests against this fixed declarative schema and enforces canonical stage pipelines for all 8 intents. The policy is fixed and schema-governed rather than freely configurable at runtime; modifications to routing stages or capabilities require code/schema upgrades.

### Strict Envelope Parsing & Limits

- **Payload Bounds:** Request and manifest JSON files enforce strict size limits (maximum 1 MiB for requests and manifests; maximum 256 KiB for module skill definitions).
- **Finite Types & Duplicate Rejection:** Parsing rejects non-finite numbers, malformed types, and duplicate dictionary keys, failing immediately with `status: "error"` and exit code 2.
- **Redacted Unknowns:** Error diagnostics redact unknown values to prevent credential and secret leakage.

### Declarative Intent Stage Mapping

| Intent              | Stage Pipeline                                                            | Constraints / Evaluation                                                               |
| :------------------ | :------------------------------------------------------------------------ | :------------------------------------------------------------------------------------- |
| `ask`               | `daw-ask`                                                                 | Read-only; ignores risk and workspace.                                                 |
| `review`            | `daw-review`                                                              | Read-only; ignores risk and workspace.                                                 |
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
   - **Reading Scoped Support Resources is NOT Module Invocation:** The suite maintains exactly 10 public execution modules (`skills/daw-*/`). Supporting resources (`references/grilling.md`, `skills/daw-design/references/domain-modeling.md`, `skills/daw-design/references/builder-readiness.md`) are documentation files for on-demand progressive disclosure. Reading these resources does not constitute module dispatch, child skill discovery, or sub-task execution.
   - Supporting references grant no new execution permissions or tools, and loading them does not spawn background workers.
   - Parent agents retain full control over delegation. If an independent assessment of builder-readiness is warranted, the parent delegates to the existing `daw-review` module rather than recursively re-dispatching design or creating ad-hoc wrapper skills.
   - Handoff schema contracts remain fixed: any protocol-specific status or findings belong under the existing optional `details` object without introducing new required top-level JSON fields.

---

## 5. Canonical Module Handoff Contract

This section defines the canonical output envelope produced by all 10 internal execution modules (`daw-design`, `daw-plan`, `daw-debug`, `daw-build`, `daw-review`, `daw-verify`, `daw-workspace`, `daw-ask`, `daw-setup`, `daw-wizard`).

> **Contract Scope Note:** This schema defines the **runtime module handoff contract** returned across module completion stages. It is distinct from the top-level route decision payload emitted by `scripts/route.py` and the task verification envelope checked by `scripts/validate.py`.

### Canonical Handoff Schema

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
   - **Stage-Scoped Invariant:** `status: "pass"` certifies ONLY that the current module's stage-specific criteria were satisfied. It is NEVER proof of end-to-end task completion, full system implementation, production readiness, or operational authorization.
   - `fail`: Executed criteria failed, produced errors, or were incomplete.
   - `blocked`: Execution could not proceed due to missing prerequisites, environment context, unverified risk, or missing exact interactive approval.
   - Rich findings inside `details` cannot override the outer `status`.
7. **`handoff_to` (string or null, required):**
   - Name of the recommended next canonical execution module (e.g., `"daw-verify"`, `"daw-review"`), or `null` if the pipeline has concluded or halted.
   - **Advisory Invariant:** `handoff_to` is purely advisory metadata returned to the parent orchestrator. Modules MUST NOT directly invoke child modules or recursively dispatch routing.
   - Parent-controlled corrective rounds may resume retained workers without changing the active route or allowing module recursion. See the [persistent worker graph contract](operations.md#persistent-worker-graphs-harness-native): only accepted current-revision results satisfy dependencies, and a correction invalidates affected downstream passes. Canonical outer outcomes remain `pass`, `fail`, and `blocked`; graph bookkeeping belongs in existing plan artifacts or optional `details`, not new outer statuses.

8. **`details` (object, required):**
   - Module-specific domain payload (e.g. diagnostics, test summaries, review findings, workspace branches). Details preserve rich information but remain subordinate to the outer `status`.

---

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
