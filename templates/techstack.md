# Technology Stack & Architecture Decision: [Feature / Service]

> **Fill-in Guidance:** Fill this template using verified repository conventions and established libraries. Equivalent existing architecture decision records (ADRs) may be linked directly. Mark N/A with rationale if no new technical dependencies or architectural shifts are involved. Default rule: prefer existing repository stack; do not introduce new dependencies without evidence. Unresolved tech stack questions block only impacted technical dependencies.

> **Status:** Draft / Ready for Review / Approved / Superseded
> **Owner:** [Lead Architect / Principal Engineer]
> **Scope:** [Runtime stack, dependencies, framework choices, database additions]
> **Source Documents / Revision:** [FRD, RFC, or architecture spec@rev]
> **Assumptions:** [Deployment platform, existing library compatibility, runtime constraints]
> **Open Decisions:** [Material technical selections — block adding unapproved dependencies]
> **Acceptance Criteria IDs:** [TECH-01, TECH-02, ...]

---

## 1. Existing Stack Context & Constraints

_Default Rule: Prefer existing repository conventions and libraries. Do NOT introduce new dependencies without evidence._

- **Current Runtime & Language:** [e.g., Python 3.11, Node 20 LTS, Go 1.22]
- **Core Frameworks & Tools:** [Existing libraries currently maintained in repo]
- **Infrastructure Constraints:** [CPU/RAM limits, serverless timeouts, host environment constraints]

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
