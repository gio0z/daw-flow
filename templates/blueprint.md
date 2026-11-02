# Master Blueprint: [Feature / System Name]

> **Fill-in Guidance:** Fill this template using verified repository terms and observable facts. Equivalent existing architecture or planning docs may be linked or referenced directly. The 13 specification types represent an available matrix, NOT a mandatory creation bundle. Mark N/A with rationale for unneeded documents. Do not fabricate architecture decisions, milestones, or approvals. Distinguish user requirements and observed source facts from author-proposed defaults using a concise provenance ledger or explicit labels. Unresolved items that represent material gaps block only impacted execution paths, not unrelated work.

> **Status:** Draft (default for new documents; set to Approved only with exact observed human/provider approval evidence)
> **Owner:** [Supplied/verified owner name or role; otherwise Unassigned — requires owner decision]
> **Scope:** [Bounded component, service, or repository area]
> **Source Documents / Revision:** [Actual observed commit SHA, file SHA-256, issue link, or relative path (marked unversioned if revision unobserved); never invent synthetic tags like @initial]
> **Assumptions:** [Explicit operational or technical assumptions]
> **Open Decisions:** [Material questions — block impacted execution paths until resolved]
> **Acceptance Criteria IDs:** [AC-01, AC-02, ...]

---

## 1. Executive Summary & Objective

- **Problem Statement:** [Concrete issue or requirement being addressed]
- **Target Outcome:** [Observable state after completion]
- **Explicit Non-Goals:** [What this effort will NOT do]

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

## 4. Execution Phases & Milestones

- [ ] **Phase 1: Contract Baseline** — Review required specs, resolve material gaps, establish preflight gates.
- [ ] **Phase 2: Scaffolding & Bounded Tools** — Reuse verified existing repo CLI/scripts; wrap only if absent.
- [ ] **Phase 3: Implementation** — Implement core changes against verified acceptance criteria.
- [ ] **Phase 4: Semantic Verification** — Run acceptance test matrix with concrete before/after evidence.
- [ ] **Phase 5: Release Hand-off** — Operational readiness verification per runbook.
