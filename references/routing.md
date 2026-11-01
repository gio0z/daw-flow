# Document Routing & Delegation Reference

This reference defines the document-driven engineering contract for the 13 document types in the deterministic agentic workflow (1 system blueprint + 12 derivative specifications), along with handoff protocols, skill routing, and impact-based scope selection.

Article Reference: Rama Digital — _Agentic Tapi Deterministic Workflow AI Agent_ (https://ramadigital.id/blog/agentic-tapi-deterministic-workflow-ai-agent).
Advice separation note: Core article principles (generative planning, deterministic mutation, document contracts, verification gates) establish the architectural foundation. Local operational additions in this reference define structured handoff schemas, lifecycle routing, and domain specialist delegation for multi-agent CLI and workstation environments.
---

## 1. Shared Handoff & Validation Schema

Every transition between orchestrator, specialist skill, and document artifact must satisfy the standard handoff schema:

| Field                  | Type                | Description                                                                                                                                                                                                                      |
| ---------------------- | ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `objective`            | string              | Exact single-sentence goal of the phase or document artifact.                                                                                                                                                                    |
| `input_paths`          | list[string]        | Array of repository-relative paths to upstream documents or reference specs (relevant existing equivalents accepted).                                                                                                            |
| `input_revisions`      | map[string, string] | Key-value mapping of file path to Git commit SHA or file content hash (enforces baseline freshness).                                                                                                                             |
| `decisions`            | list[string]        | Architectural, product, or technical decisions already settled and closed to re-litigation.                                                                                                                                      |
| `open_issues`          | list[string]        | Unresolved edge cases, explicit blockers, or trade-offs awaiting user input.                                                                                                                                                     |
| `required_output_path` | string              | Specific target path where the generated specification must be stored.                                                                                                                                                           |
| `verification_checks`  | list[string]        | Concrete, automated or evidence-based criteria to confirm the output satisfies the contract.                                                                                                                                     |
| `approval_boundaries`  | list[string]        | Explicit operational boundaries requiring authorized user / provider sign-off prior to mutation. Neither orchestrator nor document contracts grant human permissions; delegated coordinators cannot authorize high-risk actions. |

### Handoff Contract Template (YAML Map Example)

_(Illustrative schema only; decisions, paths, and verification checks reflect approved repo-defined invariants rather than hardcoded security mechanisms or universal defaults)_

```yaml
contract_handoff:
  objective: "Specify domain validation rules and persistence interfaces for billing subsystem"
  input_paths:
    - "docs/specs/prd.md"
  input_revisions:
    "docs/specs/prd.md": "a3f81c9d24e7"
  decisions:
    - "Reuse existing repository database client patterns without introducing alternative ORMs"
    - "State modifications enforce transactional boundaries at the service layer"
  open_issues: []
  required_output_path: "docs/specs/frd.md"
  verification_checks:
    - "All input validation boundaries mapped directly to acceptance criteria in PRD"
    - "Failure states declare specific domain error types rather than generic exceptions"
  approval_boundaries:
    - "Authorized user confirmation required before running any database schema migrations"
```

---

## 2. Document Selection Matrix (Illustrative Impact Selection)

The 13 document types are an **available menu of contracts**, never a compulsory 13-doc bundle for every task. Select documents by actual blast radius, subsystem impact, and domain risk:

| Impact Scope                              | Typical Document Contracts Needed                                                                             | Omit Unless Justified                                                   |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| **New System / Greenfield Project**       | `blueprint.md`, `prd.md`, `frd.md`, `techstack.md`, `security.md`, `roadmap.md`                               | `runbook.md`, `qa.md` (drafted during implementation)                   |
| **Major Architectural Revision**          | `blueprint.md` (or system delta), `techstack.md`, `security.md`, `deployment.md`                              | `brd.md`, `wireframe.md`                                                |
| **New User-Facing Feature**               | `prd.md`, `frd.md`, `wireframe.md`, `design.md`, `ui-ux.md`, `qa.md`                                          | `blueprint.md`, `runbook.md`                                            |
| **Backend-Only API / Data Flow**          | `prd.md` (backend scope), `frd.md`, `techstack.md`, `security.md`                                             | `wireframe.md`, `design.md`, `ui-ux.md` (NO frontend/UI skills invoked) |
| **Frontend Feature with Security Impact** | `prd.md`, `wireframe.md`, `design.md`, `ui-ux.md`, `security.md` (input sanitization, auth tokens, XSS, CORS) | `blueprint.md`, `runbook.md`                                            |
| **Infrastructure / DevOps Cutover**       | `techstack.md`, `deployment.md`, `runbook.md`, `security.md`                                                  | `brd.md`, `wireframe.md`, `design.md`, `ui-ux.md`                       |
| **Routine Bugfix / Isolated Patch**       | Minimal verification record (issue / test plan / test file diff)                                              | All new planning docs (reuse existing specs, NO forced qa.md)           |

### Precedence, Aliases, Staleness & Safety Invariants

1. **Existing vs. New Docs & Equivalents:** If a project already uses `docs/architecture.md`, `docs/spec.md`, or README architecture sections, **reuse and respect existing paths, casing, and naming**. Relevant existing equivalents satisfy input prerequisites; never force standard filenames or duplicate existing specs.
2. **Routine Patches:** Routine bugfixes or isolated patches do NOT require authoring new planning documents or a forced `qa.md`. Existing issues, test diffs, and test suite execution serve as the concise verification record.
3. **Backend PRD Strict Boundary:** Backend-only or internal API PRDs must NOT invoke UI/UX or design specialists (`design`, `design-ui-designer`, `antislop-ui`, `design-ux-architect`) or generate UI wireframes or design tokens.
4. **Frontend Security Impact:** Frontend changes involving auth token handling, form sanitization, iframe sandboxing, CORS, or local storage MUST invoke application security expertise (`application-security`) or compile `security.md` regardless of whether the change is primarily visual.
5. **Staleness & Conflicting Contracts:** Upstream contracts must be validated for revision matches. If `input_revisions` mismatch or upstream contracts conflict, pause downstream execution immediately to resolve material gaps before proceeding.
6. **Approval Invalidation & Fail-Closed Gates:** Prior human or provider approvals are strictly invalidated if underlying inputs, specifications, revision hashes, target scope, or tenant boundaries change. Neither the orchestrator nor any document contract grants human permission. If an approval UI/confirmation mechanism is unavailable (e.g. headless/subagent context), execution must **fail-closed** and stop—never assume silent approval.
7. **Safe Rollback Target Selection:** Automated rollback must NEVER blindly target `HEAD~1` or an unverified git commit (which risks rolling back unrelated concurrent work). Application rollback requires an **exact immutable release ID or artifact digest/version-resolved Git commit SHA**. If and only if stateful data recovery is part of the selected rollback plan, an **exact pre-change database snapshot ID** must also be specified, with schema compatibility and writes that occurred after the snapshot explicitly accounted for. Stateless application rollbacks do not mandate database snapshot restores or backups. Never conflate application Git commit SHAs with database snapshot identifiers.
8. **Maintenance Layer Inactive During Planning:** The presence of `runbook.md` or maintenance documentation does NOT mean active operational monitoring, continuous polling, or daemon tasks are running; operations are triggered only during explicit live execution.
9. **Semantic & Cross-Tenant Verification:** Verification must check actual domain semantics, authorization boundaries, and business assertions (e.g., verifying user isolation, multi-tenant boundaries, or idempotency keys). For frontend security checks, select semantically appropriate permission responses (e.g. verifying that an unauthorized route redirects to login or returns 404 to conceal resource existence, rather than forcing an artificial HTTP 403 when the API intentionally masks endpoints).
10. **Planning Gates vs Execution Proof:** Document gates require specified controls and an actionable verification plan. Avoid claiming absolute runtime compliance (e.g. "zero threats guaranteed") from planning documentation alone; empirical proof occurs at the execution verification gate.
11. **Proportional Handoff Contracts:** Handoff contracts do not force every artifact into rigid JSON files or require full content hashes of every doc for a tiny patch; a proportional baseline commit SHA or clear content identity is sufficient. Automatic creation of all 13 docs is prohibited.
12. **No Recursive Delegation:** Subagents and skills invoked for a document contract must never re-invoke routing skills or spawn unbounded meta-workflows.
13. **No Unilateral Scope Expansion:** Specialist skills (e.g., SEO, security, UX) operate strictly within requested boundaries. A skill instructions file cannot silently authorize out-of-scope work (e.g., automated SEO rewrites during a backend PRD phase). Always read target skills before relying on them.

---

## 3. The 13 Document Routing Specifications

### 1. `blueprint.md` — System Architecture & Foundational Design

- **Trigger:** Greenfield system initiation, major platform rewrite, or introducing a core multi-service domain boundary.
- **Inputs & Prerequisites:** High-level project brief, business vision, core domain requirements (or relevant existing equivalent documentation).
- **Primary Skill:** Explicit inline orchestrator (systems analysis, modular design, domain seams, AI-navigability).
- **Conditional Skills:**
  - `backend-architect` — When distributed services, event buses, message queues, or high-throughput concurrency models are involved.
  - `codebase-memory` — When integrating into an existing multi-repo or complex enterprise codebase requiring caller/dependency graph mapping.
  - `codebase-design` — Optional specialist capability for modular structure and deep interfaces.
- **Template Link:** [blueprint.md](../templates/blueprint.md)
- **Output Contract:** High-level topology, component relationships, module boundaries, cross-cutting architectural invariants, and directory structuring rules.
- **Exit Criterion:** Blueprint reviewed and validated against user constraints; module boundaries establish clean encapsulation without circular couplings.
- **Downstream Handoff:** Feeds into `brd.md`, `prd.md`, and `techstack.md` (or existing project architecture equivalents).
- **Stop / Replan Trigger:** Unresolved cross-system dependency cycles or undefined hardware/cloud platform constraints.

---

### 2. `brd.md` — Business Requirements Document

- **Trigger:** Strategic business initiatives, commercial client scopes, internal operational improvements, multi-stakeholder commercial goals, ROI-driven milestones.
- **Inputs & Prerequisites:** Stakeholder goals, executive brief, operational budgets (if available), market timing constraints, target KPIs (if defined; do not invent arbitrary numbers). Relevant existing equivalent documentation accepted.
- **Primary Skill:** Explicit inline orchestrator (business requirements synthesis is driven by project context and user constraints; no single synthetic author skill overrides user business directives).
- **Conditional Skills:**
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
- **Primary Skill:** Explicit inline orchestrator (product definition and scope bounding; synthesizes requirements directly from user intent).
- **Conditional Skills:**
  - `design-ux-architect` — _Conditional_: When defining multi-step user workflows, navigational hierarchies, or complex user state interactions. Omit for backend-only PRDs.
  - `api-platform-engineer` — _Conditional_: When the product surface is primarily an API/platform for external integration.
- **Template Link:** [prd.md](../templates/prd.md)
- **Output Contract:** User personas, user stories with granular acceptance criteria (Given/When/Then), non-functional requirements (NFRs), and explicit edge cases.
- **Exit Criterion:** Every user story has verifiable acceptance criteria; non-goals clearly stated.
- **Downstream Handoff:** Feeds into `frd.md`, `roadmap.md`, and (for user-facing features only) `wireframe.md`, `design.md`, and `ui-ux.md`. (Backend-only features do not hand off to downstream UI specifications).
- **Stop / Replan Trigger:** Ambiguity in acceptance criteria or conflicting user story requirements.

---

### 4. `frd.md` — Functional Requirements Document

- **Trigger:** Engineering translation of product requirements into exact system mechanics, validations, state transitions, and business logic.
- **Inputs & Prerequisites:** `prd.md` (or relevant existing equivalent), domain data dictionary.
- **Primary Skill:** Explicit inline orchestrator (systems analysis and technical requirement decomposition).
- **Conditional Skills:**
  - `api-platform-engineer` — When an actual external or internal API boundary, REST/OpenAPI contract, or endpoint schema is being defined.
  - `backend-architect` — When transactions, concurrency locks, state machines, or distributed workflows must be specified.
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
- **Primary Skill:** Explicit inline orchestrator (evaluating repo tech constraints against requirements).
- **Conditional Skills:**
  - `backend-architect` — When selecting persistence stores, messaging queues, or microservice fabrics.
  - `database-optimizer` — When choosing database engines, schema normalization, indexing, or migration frameworks.
  - `engineering-api-platform-engineer` — When deciding REST, gRPC, GraphQL, or OpenAPI standards.
- **Template Link:** [techstack.md](../templates/techstack.md)
- **Output Contract:** Selected languages, runtimes, database engines, external APIs, build tools, dependency versions, and architectural decision records (ADRs) explaining trade-offs.
- **Exit Criterion:** All stack components verified compatible; zero unvetted dependencies; license constraints checked.
- **Downstream Handoff:** Feeds into `security.md` and `deployment.md`.
- **Stop / Replan Trigger:** License incompatibilities, unmaintained dependencies, or environmental runtime constraints (e.g., unsupported OS or node/compiler versions).

---

### 6. `design.md` — Visual Design System & Component Library Specification

- **Trigger:** Authoring visual design systems, design tokens (colors, spacing, typography, elevation), shared component libraries, and UI themes. (Note: Low-level software/module design belongs in `blueprint.md`, `frd.md`, and `techstack.md`).
- **Inputs & Prerequisites:** `prd.md`, `wireframe.md` (or relevant existing equivalents), brand assets, style guidelines.
- **Primary Skill:** Explicit inline orchestrator (visual layout, theme definitions, and component hierarchies).
- **Conditional Skills:**
  - `design-ui-designer` — Optional specialist capability when authoring a dedicated shared design system, token dictionary, or reusable component library.
  - `design` — Optional specialist capability for interface visual styling and refinement.
  - `wcag-token-contrast-audit` — When auditing design token color systems and dark mode palette contrast compliance.
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
- **Primary Skill:** Explicit inline orchestrator (screen layout, informational hierarchy, structural ASCII/text layout).
- **Conditional Skills:**
  - `design-ux-architect` — Optional specialist capability for UX architecture, grid systems, and responsive layout hierarchies.
  - `design-taste-frontend` — When defining landing pages, portfolios, or marketing layouts requiring distinctive visual hierarchy.
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
- **Primary Skill:** Explicit inline orchestrator (interaction states, keyboard navigation, and accessibility semantics).
- **Conditional Skills:**
  - `antislop-human` — Optional specialist capability for accessibility, color contrast, keyboard navigation, and interactive UI states.
  - `mobile-native` — _Conditional_: When resolving mobile viewport constraints, touch gestures, mobile notch handling, or PWA offline sync known issues.
  - `emil-design-eng` — For refined micro-interactions, spring curves, and delicate animation polish.
  - `apple-design` — _Strictly conditional_: Only when implementing native-feeling iOS/macOS web gestures, spring animations, sheets, or translucent materials.
- **Template Link:** [ui-ux.md](../templates/ui-ux.md)
- **Output Contract:** Component interaction state machine (loading, empty, error, active, disabled, focused), keyboard navigation traps/landmarks, ARIA role mappings, and transition timing specifications.
- **Exit Criterion:** Keyboard and focus invariants specified meeting the repository/user-required accessibility standard (default WCAG AA; no unsolicited deviation); interactive state transitions fully mapped.
- **Downstream Handoff:** Feeds into frontend implementation and `qa.md`.
- **Stop / Replan Trigger:** Inaccessible focus management or unresolvable layout overflow constraints.

---

### 9. `security.md` — Threat Modeling, Vulnerability Mitigation & Security Controls

- **Trigger:** Data persistence, authentication/authorization implementation, external network ingest, payment flows, or cryptographic handling.
- **Inputs & Prerequisites:** `blueprint.md`, `techstack.md` (or relevant existing equivalents).
- **Primary Skill:** Explicit inline orchestrator (threat modeling, input validation matrices, authentication/authorization boundaries, and security controls).
- **Conditional Skills:**
  - `application-security` — Optional specialist capability for OWASP Top 10 auditing, threat modeling, input validation, and authentication hardening.
  - `security-appsec-engineer` — For formal threat modeling (STRIDE), SAST/DAST setup, and trust boundaries.
  - `security-senior-secops` — For secrets management, CORS configurations, rate limiting, and defensive headers.
- **Template Link:** [security.md](../templates/security.md)
- **Output Contract:** Threat model, data classification matrix, authentication & session handling specification, RBAC/ABAC rules, input sanitization rules, and encryption policies (at rest and in transit).
- **Exit Criterion:** Specified security controls and automated verification plan defined for all identified threats; zero hardcoded secrets. (Empirical proof occurs at execution verification gate).
- **Downstream Handoff:** Feeds into `deployment.md`, `qa.md`, and code implementation.
- **Stop / Replan Trigger:** Unresolvable security vulnerabilities or architectural violations of principle of least privilege.

---

### 10. `roadmap.md` — Milestone Planning, Phasing & Work Breakdown

- **Trigger:** Multi-phase project delivery, dependencies sequencing, team task breakdown, and sprint milestone definitions.
- **Inputs & Prerequisites:** `prd.md`, `techstack.md` (or relevant existing equivalents), stakeholder timeline expectations.
- **Primary Skill:** Explicit inline orchestrator (translates overall specification into sequenced deliverables; notes: implementation planning skills are strictly for tactical code execution plans, not strategic roadmaps).
- **Conditional Skills:**
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
- **Primary Skill:** Explicit inline orchestrator (environment configuration, containerization, CI/CD pipelines, and release rollback procedures).
- **Conditional Skills:**
  - `devops-infrastructure` — Optional specialist capability for Docker, compose, systemd, CI/CD workflows, and Linux networking.
  - `engineering-devops-automator` — When constructing cloud infrastructure automation or GitHub Actions pipelines.
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
- **Primary Skill:** Explicit inline orchestrator (defines comprehensive test matrix, acceptance verification steps, and regression checks directly against requirements).
- **Conditional Skills:**
  - `tdd` — _Conditional_: Strictly when actually implementing test-first features/bugfixes or uncertain logic requiring red-green-refactor isolation.
  - `testing-test-automation-engineer` — For Playwright/Cypress end-to-end browser workflows and UI regression suites.
  - `testing-performance-benchmarker` — _Conditional_: Only when explicit performance, load SLAs, latency targets, or memory profiling are scoped.
- **Template Link:** [qa.md](../templates/qa.md)
- **Output Contract:** Test pyramid coverage targets, specific test scenarios with expected outcomes, regression checklists, performance benchmarks, and synthetic test data sets.
- **Exit Criterion:** 100% of functional requirements mapped to test cases; automated test commands specified.
- **Downstream Handoff:** Guides code verification layer and release sign-off.
- **Stop / Replan Trigger:** Unverifiable acceptance criteria or untestable system architectures.

---

### 13. `runbook.md` — Incident Response, Operational Procedures & Observability

- **Trigger:** Production readiness, on-call operational handoff, disaster recovery planning, and service maintenance procedures.
- **Inputs & Prerequisites:** `blueprint.md`, `deployment.md`, `security.md` (or relevant existing equivalents).
- **Primary Skill:** Explicit inline orchestrator (incident response runbooks, operational triage commands, diagnostic procedures, and service health checks).
- **Conditional Skills:**
  - `devops-infrastructure` — Optional specialist capability for systemd services, log inspection, process management, and networking diagnostics.
  - `diagnose-crash` — For handling segfaults, core dumps, memory panics, and unexpected fatal process exits.
  - `systematic-debugging` — For step-by-step triage procedures during complex distributed failures.
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
2. **No Recursive Routing:**
   - Under no circumstances may an agent reading `routing.md` invoke `deterministic-agentic-workflow` as a child task. Routing is a top-level deterministic mapping, executed once per planning stage.
