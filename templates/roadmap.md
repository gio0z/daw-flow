# Engineering Delivery Roadmap: [Initiative Name]

> **Fill-in Guidance:** Fill this template using verified technical dependencies, milestone sequence, and observable exit criteria. Equivalent existing tracking issues or project boards may be referenced directly. Mark N/A with rationale for single-iteration bugfixes or routine patches. Milestones are domain-neutral; do not assume every initiative involves database migrations or backend systems. Base milestones strictly on completion of verified gates, not fabricated calendar release dates. Distinguish user-requested delivery targets from author-proposed phasing using a concise provenance ledger or explicit labels. Unresolved sequencing questions block dependent delivery phases only. Never record secret values or credentials in templates.

> **Status:** Draft (default for new documents; set to Approved only with exact observed human/provider approval evidence)
> **Owner:** [Supplied/verified owner name or role; otherwise Unassigned — requires owner decision]
> **Scope:** [Feature lifecycle, phasing, technical milestones, release gates]
> **Source Documents / Revision:** [Actual observed BRD, PRD, blueprint.md, or relative path (marked unversioned if revision unobserved); never invent synthetic tags like @initial]
> **Assumptions:** [Team availability, platform stability, upstream component releases]
> **Open Decisions:** [Material sequencing questions — block dependent milestones until resolved]
> **Acceptance Criteria IDs:** [ROAD-01, ROAD-02, ...]
> **Reader & Core Task:** [Engineering Lead / Delivery Coordinator / Implementation Agent] — Sequence delivery phases, verify dependency ordering and bounded milestone outcomes, and monitor stop/replan triggers without relying on invented calendar release dates.
> **Quality Reference:** Canonical rubric and transition gate criteria in [references/document-quality.md](../references/document-quality.md) (common `DQ-01`..`DQ-05` and `roadmap-01`..`03`).

---

## 1. Milestone Sequencing & Phasing

_Base phases strictly on milestone completion, technical dependencies, and concrete exit criteria. Adapt milestones to actual domain._

### Phase 1: Specifications & Preflight Contracts

- **Focus:** Complete blueprint routing, resolve material open questions, baseline acceptance criteria.
- **Prerequisites:** Approved PRD/FRD or equivalent baseline contracts.
- **Exit Criteria:** Material design questions resolved; preflight verification gates established.

### Phase 2: Core Foundation & Tooling

- **Focus:** [Initial structural changes, core domain models, internal interfaces, or verified tooling]
- **Prerequisites:** Phase 1 contract sign-off.
- **Exit Criteria:** [Unit test baseline green, foundational contracts passing in local/sandbox]

### Phase 3: Implementation & Integration

- **Focus:** [Feature logic, integration points, user or API surface implementation]
- **Prerequisites:** Phase 2 foundation in place.
- **Exit Criteria:** End-to-end integration tests passing across all supported paths.

### Phase 4: Semantic Verification & Pre-Release Readiness

- **Focus:** Full acceptance test matrix, security negative verification, performance validation.
- **Prerequisites:** Phase 3 implementation complete.
- **Exit Criteria:** QA verification matrix signed off with evidence logs; operational readiness verified.

## 2. Critical Path & Blocking Dependencies

| Milestone   | Blocking Dependency                                                    | Dependent Deliverable | Risk / Mitigation                            |
| :---------- | :--------------------------------------------------------------------- | :-------------------- | :------------------------------------------- |
| `[Phase X]` | `[Specific dependency, e.g. third-party API / architectural sign-off]` | `[Dependent feature]` | `[Concrete risk mitigation / mock fallback]` |
| `[Phase Y]` | `[Specific dependency]`                                                | `[Dependent feature]` | `[Concrete risk mitigation]`                 |

## 3. Scope Cut & De-scoping Protocol

_If unexpected blockers occur, de-scoping must be agreed upon explicitly rather than silently dropping acceptance criteria._

- **Non-Negotiable Core (Must Have):** [Core functionality required for safety and functionality]
- **Negotiable Secondary (Nice to Have):** [Performance micro-optimizations, auxiliary batch scripts]
- **Stop / Replan Triggers:** [Explicit conditions that halt delivery execution and require replanning rather than pushing broken state downstream]

## 4. Document Quality & Review Checks

_Verify against canonical [Document Quality Rubric](../references/document-quality.md) before workflow transitions. Mark N/A with rationale where proportional to scope._

- [ ] **roadmap-01 (Sequencing & Phasing):** Are delivery phases, milestones, and deliverables broken down into sequenced, dependency-ordered work units?
- [ ] **roadmap-02 (Critical Path & Dependencies):** Are critical path dependencies, integration risk choke-points, and technical debt mitigations explicitly identified?
- [ ] **roadmap-03 (Completion Gates & Decision Rules):** Are phase completion gates, release acceptance criteria, and go/no-go or stop/replan decision rules defined with observable signals without invented dates?
