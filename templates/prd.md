# Product Requirements Document (PRD): [Feature Name]

> **Fill-in Guidance:** Fill this template using verified product outcomes and observable acceptance criteria adhering to the canonical shared procedural contract in [Canonical Document Quality & Workflow Transition Guide](../references/document-quality.md#feature-delivery-contract). Equivalent existing specs or feature briefs may be reused directly. Mark N/A with rationale if not applicable (e.g. pure refactors or internal bugfixes). Do not invent user personas, market stats, UI flows for non-UI features, or speculative acceptance criteria. Non-UI features (CLI, backend, workers) must focus on programmatic actors and operational outcomes. Distinguish user requirements and observed source facts from author-proposed defaults using a concise provenance ledger or explicit labels (`[User Requirement]`, `[Observed Fact]`, `[Proposed Default]`). Record proposed/default vs decided. Unresolved questions block only impacted feature paths. Detail ceiling: PRD prose carries WHAT/WHY only — no DDL, function bodies, migrations, file paths, or code blocks implementing behavior; entity identity/relationships belong in `erd.md`, interface shapes in the FRD interface table. A decision-rich shape may be quoted only when prose cannot express it, labeled as a decision. Priorities MUST be distributed (not everything P1/Must) with a Why-this-priority and Independent Test per story; P1 alone must be a viable demoable slice. At most 3 material unresolved decisions remain as `[Open Question]` with owner/trigger; every other assumption is a labeled `[Proposed Default]` in the provenance ledger.

> **Status:** Draft (default for new documents; set to Approved only with exact observed human/provider approval evidence)
> **Owner:** [Supplied/verified owner name or role; otherwise Unassigned — requires owner decision]
> **Scope:** [Product surface: CLI, API, Service, or User Interface]
> **Source Documents / Revision:** [Actual observed source issue, BRD, or relative path (marked unversioned if revision unobserved); never invent synthetic tags like @initial]
> **Assumptions:** [User capability, data availability, or platform baseline]
> **Open Decisions:** [Material product questions — block impacted feature paths until settled]
> **Acceptance Criteria IDs:** [PRD-01, PRD-02, ...]
> **User Story IDs:** [US-01, US-02, ...]
> **Target Audience & Reader Task:** [Product engineer, system designer, or QA reviewer: understand target actor problem scenarios, verify user journey priorities, and implement observable acceptance criteria]
> **Quality Standards:** [Canonical Document Quality & Transition Guide](../references/document-quality.md#feature-delivery-contract) (specifically [Governance Alignment](../references/document-quality.md#a-governance-and-authoring-alignment) and [Feature Slicing & Behavioral Oracles](../references/document-quality.md#c-feature-slicing-and-behavioral-contract-oracles))

---

## 1. Problem Statement & Target Actor

- **Target Actor:** [API client, system administrator, internal operator, or end user]
- **Core Problem:** [Concrete workflow breakdown or unmet need with observed evidence]
- **Context of Use:** [Circumstances under which the actor encounters this problem]

## 2. Product Objectives & Observable Outcomes

- **Desired Behavior:** [What the actor or consuming system can accomplish after completion — focus on business what/why, not technical how]
- **Key Tenets:** [Simplicity, determinism, transparency, or zero-latency overhead]
- **Explicit Out-of-Scope / Non-Goals:** [Adjoining features, integrations, or workflows explicitly excluded from this iteration to prevent scope creep]
- **Business Outcomes & KPIs:** [Target business metrics or operational goals. Note: High-level KPIs cannot serve as build/runtime acceptance criteria without a justified, measurable runtime observation boundary]

## 3. Prioritized User Stories & Scenarios

<!--
  IMPORTANT: User stories are PRIORITIZED user journeys ordered by importance (P1, P2, P3...).
  Each user story MUST be INDEPENDENTLY TESTABLE and DEMONSTRABLE — implementing just P1 delivers a viable MVP.
  Exception: Inseparable safety or transaction invariants (e.g. atomic financial transfers or auth checks) do NOT require artificial deploy independence if separation breaks data integrity.
  Applicable to UI screens, CLI commands, or programmatic backend consumers. Do not force UI flows for backend or CLI features.
-->

### US-01: [Brief Title] (Priority: P1)

- **User Journey / Description:** [Describe what the actor does and experiences in plain language]
- **Why This Priority:** [Concrete value delivered; why this is P1 critical vs subsequent increments]
- **Independent Test / Value Oracle:** [How this slice can be demonstrated and verified independently before P2/P3 work begins]
- **Acceptance Scenarios:**
  - **Scenario 1 (Primary / Happy Path):** Given [initial state / preconditions], When [action taken], Then [observable state change / response].
  - **Scenario 2 (Negative / Edge Case):** Given [invalid state or input], When [action attempted], Then [deterministic error or rejection with code/message].

### US-02: [Brief Title] (Priority: P2)

- **User Journey / Description:** [Describe the secondary journey, operational enhancement, or advanced option]
- **Why This Priority:** [Incremental value over P1; why it can be deferred if P1 is constrained]
- **Independent Test / Value Oracle:** [How this can be tested and demonstrated independently]
- **Acceptance Scenarios:**
  - **Scenario 1:** Given [preconditions], When [action], Then [observable outcome].

## 4. Acceptance Criteria Matrix

_Express each criterion in EARS or Given/When/Then form per [EARS Semantic Guidance](../references/document-quality.md#acceptance-criteria-ears). The pattern choice is free; what matters is the condition, response, and oracle. Do not force all five patterns._

| ID       | Criterion (EARS or GWT — one form per criterion)                                                               | Condition / trigger or state                                               | System response + observable oracle                                                                            | Negative / no-change (if meaningful)                             | Provenance                                                                                                                               |
| :------- | :------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------- |
| `PRD-01` | WHEN [trigger event] THE SYSTEM SHALL [observable response]                                                    | [Trigger or while-state]                                                   | [Response and how a verifier proves it]                                                                        | [Error + no-change, or N/A]                                      | `[User Requirement]` / `[Observed Fact]` / `[Proposed Default]` / `[Open Question]`                                                      |
| `PRD-02` | IF [unwanted condition / invalid input], THEN THE SYSTEM SHALL [error response]                                | [Invalid state or input]                                                   | [Error code/status/message and state readback]                                                                 | [No rows persisted / no external call / input untouched, or N/A] | `[User Requirement]` / `[Observed Fact]` / `[Proposed Default]` / `[Open Question]`                                                      |
| `PRD-03` | [Given/When/Then: Given precondition, When action, Then observable outcome]                                    | [Precondition / trigger]                                                   | [Observable outcome + durable oracle]                                                                          | [Safe rejection + no-change, or N/A]                             | `[User Requirement]` / `[Observed Fact]` / `[Proposed Default]` / `[Open Question]`                                                      |
| `PRD-04` | [Non-functional / boundary: measured under verified load, e.g. response time / throughput / concurrency limit] | [Load / concurrency condition and source-proposed-or-unknown target value] | [Observed measurement oracle: p95 duration or throughput read from the test run output on the pinned revision] | N/A                                                              | `[Proposed Default]` / `[Open Question]` / `[Observed Fact]` (target provenance required; no numeric default without a traceable source) |

_Provenance note:_ Numeric thresholds (latency, counts, timeouts) appear only with a traceable source; otherwise record as `[Open Question]` or `[Proposed Default]`, never as a silent SHALL. Artifact placement and progress binding per [Workflow Artifacts](../references/workflow-artifacts.md).

## 5. Provenance Ledger & Open Questions

| ID / Topic | Classification       | Content / Decision                                          | Status   | Impacted Paths |
| :--------- | :------------------- | :---------------------------------------------------------- | :------- | :------------- |
| `DEC-01`   | `[Decided]`          | [Confirmed product requirement or scope boundary]           | Settled  | All            |
| `DEF-01`   | `[Proposed Default]` | [Author-proposed sensible default awaiting feedback]        | Proposed | Feature path B |
| `OQ-01`    | `[Open Question]`    | [Material unresolved trade-off; blocks dependent path only] | Blocked  | Path C only    |

## 6. Dependencies & Non-Functional Expectations

- **Cross-Service Dependencies:** [Upstream services, external APIs, shared libraries]
- **Supporting Infrastructure Tasks:** [Prerequisite DB migrations, schema setups, or config baselines required by P1]
- **Performance Expectations:** [Target response latency or throughput within known system constraints]
- **Telemetry & Logging:** [Required user action events or audit milestones]

## 7. Document Quality & Review Checks

_Reviewers and authoring agents must verify the document against the canonical [Document Quality Specification](../references/document-quality.md) before workflow transitions:_

- [ ] **prd-01:** Are primary actors, target users, or consuming systems and their specific problem scenarios concretely defined?
- [ ] **prd-02:** Are product capabilities, user or system interaction flows, and usage priorities mapped directly to target outcomes?
- [ ] **prd-03:** Are functional and experiential success conditions, feature-level acceptance criteria, and explicit out-of-scope boundaries defined?
- [ ] **prd-gates:** Every success/verification claim names an exact command and its expected observable, not prose like "tests pass".
- [ ] **prd-oracles:** Each AC states its oracle source (spec literal or worked example), with at least one negative/no-change case per AC.
