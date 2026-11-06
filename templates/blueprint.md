# Master Blueprint: [Feature / System Name]

> **Fill-in Guidance:** Fill this template using verified repository terms and observable facts adhering to the canonical shared procedural contract in [Canonical Document Quality & Workflow Transition Guide](../references/document-quality.md#feature-delivery-contract). Equivalent existing architecture or planning docs may be linked or referenced directly. The 13 specification types represent an available matrix, NOT a mandatory creation bundle. Mark N/A with rationale for unneeded documents. Do not fabricate architecture decisions, milestones, or approvals. Distinguish user requirements and observed source facts from author-proposed defaults using a concise provenance ledger or explicit labels (`[User Requirement]`, `[Observed Fact]`, `[Proposed Default]`). Record proposed/default vs decided. Unresolved items that represent material gaps block only impacted execution paths, not unrelated work.

> **Status:** Draft (default for new documents; set to Approved only with exact observed human/provider approval evidence)
> **Owner:** [Supplied/verified owner name or role; otherwise Unassigned — requires owner decision]
> **Scope:** [Bounded component, service, or repository area]
> **Source Documents / Revision:** [Actual observed commit SHA, file SHA-256, issue link, or relative path (marked unversioned if revision unobserved); never invent synthetic tags like @initial]
> **Assumptions:** [Explicit operational or technical assumptions]
> **Open Decisions:** [Material questions — block impacted execution paths until resolved]
> **Acceptance Criteria IDs:** [AC-01, AC-02, ...]
> **Reader & Core Task:** [Systems Architect / Lead Engineer / Implementer] — Locate architectural boundaries, cross-specification routing, subsystem responsibilities, shared contracts, and decision risk boundaries without requiring ambient memory.
> **Quality Reference:** Canonical rubric and transition gate criteria in [references/document-quality.md](../references/document-quality.md) (common `DQ-01`..`DQ-05` and `blueprint-01`..`03`) and [Feature Delivery Contract](../references/document-quality.md#feature-delivery-contract) (specifically [Governance Alignment](../references/document-quality.md#a-governance-and-authoring-alignment), [Clarification](../references/document-quality.md#b-clarification-and-technical-uncertainty-resolution), and [Feature Slicing](../references/document-quality.md#c-feature-slicing-and-behavioral-contract-oracles)).

---

## 1. Executive Summary & Objective

- **Problem Statement:** [Concrete issue or requirement being addressed]
- **Target Outcome:** [Observable state after completion — focus on architectural outcomes]
- **Explicit Non-Goals & Scope Guard:** [What this effort will NOT do. Code generation and implementation tasks are deferred intents, not executed during blueprint authoring]

## 2. Document Routing & Artifact Map

_Mark existing repo docs, aliases, selected additions, or N/A with rationale._

| Document Contract | Status / Path                 | Notes / Justification                        |
| :---------------- | :---------------------------- | :------------------------------------------- |
| `blueprint.md`    | `[Path / This doc]`           | Master architecture & boundary map           |
| `brd.md`          | `[Selected / Existing / N/A]` | Business context & constraints               |
| `prd.md`          | `[Selected / Existing / N/A]` | User requirements & acceptance criteria      |
| `frd.md`          | `[Selected / Existing / N/A]` | Functional behavior & state invariants       |
| `techstack.md`    | `[Selected / Existing / N/A]` | Technology constraints & trade-offs          |
| `design.md`       | `[Selected / Existing / N/A]` | Visual tokens & component primitives         |
| `wireframe.md`    | `[Selected / Existing / N/A]` | Layout structure & screen states             |
| `ui-ux.md`        | `[Selected / Existing / N/A]` | Interaction behaviors & accessibility states |
| `security.md`     | `[Selected / Existing / N/A]` | Threat model & authorization boundaries      |
| `roadmap.md`      | `[Selected / Existing / N/A]` | Delivery phases & critical dependencies      |
| `deployment.md`   | `[Selected / Existing / N/A]` | Release mechanics & environment gates        |
| `qa.md`           | `[Selected / Existing / N/A]` | Semantic verification & test coverage        |
| `runbook.md`      | `[Selected / Existing / N/A]` | Operational procedures & recovery steps      |

## 3. Boundary & Approval Gates

- **Auto-Executable (Agent):** [Deterministic actions within verified local sandbox, e.g., local tests, lint, scoped edits]
- **Requires Explicit Human Approval:** [Schema migration, authentication/authorization changes, secret modifications, external API mutations, release deployment. Document approval provider, user identity, and bound revision; doc presence never substitutes for explicit approval.]
- **Inseparable Safety & Transaction Invariants:** [Core architectural transactions or safety invariants that cannot be split into independent deployments without compromising data integrity.]

## 4. Governance Sync & Provenance Ledger

### 4.1 Provenance & Decision State

| ID / Topic    | Classification       | Content / Decision                                  | Status   | Impacted Components |
| :------------ | :------------------- | :-------------------------------------------------- | :------- | :------------------ |
| `ARCH-DEC-01` | `[Decided]`          | [Confirmed architectural invariant or boundary]     | Settled  | All                 |
| `ARCH-DEF-01` | `[Proposed Default]` | [Author-proposed configuration or pattern default]  | Proposed | Component B         |
| `ARCH-OQ-01`  | `[Open Decision]`    | [Material architectural gap; blocks dependent path] | Blocked  | Component C only    |

### 4.2 Governance Sync Impact Report (Applicable on Principle / Architecture Amendments)

- **Revision / Version Change:** [e.g. 1.0.0 -> 1.1.0]
- **Modified Principles / Decisions:** [List modified principles: old concept -> new concept]
- **Added Sections / Constraints:** [New architectural boundaries or invariants]
- **Removed Sections / Constraints:** [Deprecated concepts or superseded rules]
- **Downstream Artifacts to Synchronize:** [List affected specifications, roadmaps, task lists, and tests]

## 5. Execution Phases & Prioritized Story Milestones

- [ ] **Phase 1: Contract Baseline & Infra Prerequisites** — Review required specs, resolve material gaps, establish preflight gates, execute prerequisite DB/schema baselines.
- [ ] **Phase 2: Core Behavior Slice (P1 MVP / US-01)** — Implement the foundational, independently testable user journey with exact input/output/error/state oracles.
- [ ] **Phase 3: Secondary Behavior Slices (P2 / US-02)** — Implement incremental user journeys and advanced options.
- [ ] **Phase 4: Semantic Verification & Boundary Tests** — Run acceptance test matrix against negative, edge, and non-functional criteria.
- [ ] **Phase 5: Release Hand-off** — Operational readiness verification per runbook.

## 6. Document Quality & Review Checks

_Verify against canonical [Document Quality Rubric](../references/document-quality.md) before workflow transitions. Mark N/A with rationale where proportional to scope._

- [ ] **blueprint-01:** Does the executive summary establish high-level system boundaries, core components, and primary architecture proportional to project scope?
- [ ] **blueprint-02:** Does the document routing map enumerate active specifications, their authoritative owners, and lifecycle stages without orphan links?
- [ ] **blueprint-03:** Are cross-cutting system contracts, communication conventions, and governance invariants explicitly stated?
