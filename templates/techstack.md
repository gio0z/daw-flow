# Technology Stack & Architecture Decision: [Feature / Service]

> **Fill-in Guidance:** Fill this template using verified repository conventions and established libraries. Equivalent existing architecture decision records (ADRs) may be linked directly. Mark N/A with rationale if no new technical dependencies or architectural shifts are involved. Default rule: prefer existing repository stack; do not introduce new dependencies without evidence. Distinguish observed stack facts from author-proposed dependencies or defaults using a concise provenance ledger or explicit labels. Unresolved tech stack questions block only impacted technical dependencies.

> **Status:** Draft (default for new documents; set to Approved only with exact observed human/provider approval evidence)
> **Owner:** [Supplied/verified owner name or role; otherwise Unassigned — requires owner decision]
> **Scope:** [Runtime stack, dependencies, framework choices, database additions]
> **Source Documents / Revision:** [Actual observed FRD, RFC, or relative path (marked unversioned if revision unobserved); never invent synthetic tags like @initial]
> **Assumptions:** [Deployment platform, existing library compatibility, runtime constraints]
> **Open Decisions:** [Material technical selections — block adding unapproved dependencies]
> **Acceptance Criteria IDs:** [TECH-01, TECH-02, ...]
> **Reader & Core Task:** [Software Architect / Backend Engineer / Platform Lead] — Evaluate existing runtime conventions against proposed technical additions, inspect architectural decision trade-offs, and verify lifecycle/dependency constraints without introducing avoidable dependencies.
> **Quality Reference:** Canonical rubric and transition gate criteria in [references/document-quality.md](../references/document-quality.md) (common `DQ-01`..`DQ-05` and `techstack-01`..`03`).

---

## 1. Existing Stack Context & Constraints

_Default Rule: Prefer existing repository conventions and libraries. Do NOT introduce new dependencies without evidence._

- **Current Runtime & Language:** [e.g., Python 3.11, Node 20 LTS, Go 1.22]
- **Core Frameworks & Tools:** [Existing libraries currently maintained in repo]
- **Storage Model:** [Existing storage engine and model conventions; persistent-entity and relationship authority lives in the linked `erd.md` — reference it here, do not duplicate its content]

## 2. Proposed Technology Additions (if any)

| Candidate Library / Tool | Version    | Purpose                                | Dependency Impact (Size / Transitive) |
| :----------------------- | :--------- | :------------------------------------- | :------------------------------------ |
| `[package-name]`         | `[semver]` | [Specific technical capability needed] | [Estimated size, maintenance health]  |

## 3. Alternative Solutions Evaluated

_Document evaluated alternatives to prevent bikeshedding and ensure boring, maintainable design._

- **Option A (Chosen):** [Description and why it meets criteria with minimal maintenance drag]
- **Option B (Rejected):** [Description and reason for rejection, e.g., bloat, complex abstractions]
- **Option C (Existing Native):** [Why existing repository tooling could or could not be reused]

## 4. Operational & Long-Term Maintainability Impact

- **Observability Support:** [Tracing, logging, telemetry integration]
- **Upgrade Cadence:** [Release stability, LTS support status, breaking change history]
- **Failure Modes:** [Memory leaks, connection exhaustion, deadlocks, serialization overhead]

## 5. Document Quality & Review Checks

_Verify against canonical [Document Quality Rubric](../references/document-quality.md) before workflow transitions. Mark N/A with rationale where proportional to scope._

- [ ] **techstack-01:** Are programming languages, runtimes, frameworks, and storage systems specified with explicit versions and architectural rationales?
- [ ] **techstack-02:** Are key architectural decisions and technical trade-offs recorded with context, decision rationale, and consequences?
- [ ] **techstack-03:** Are third-party dependencies, license constraints, and integration boundaries documented?
