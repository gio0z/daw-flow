# Engineering Delivery Roadmap: [Initiative Name]

> **Fill-in Guidance:** Fill this template using verified technical dependencies, milestone sequence, concrete task decomposition, and observable exit criteria. Comply with the canonical [Feature Delivery Contract](../references/document-quality.md#feature-delivery-contract) (§D Traceability, §F Prebuild Analysis, §G Convergence, §I Local Tooling).
>
> - **Traceability (Contract §D):** Every task must trace directly: `Requirement / AC ID -> User Story (where relevant) -> Task ID -> Target File Paths -> Dependencies -> Verification Command & Expected Outcome -> Current Observed Evidence / Status`.
> - **Supporting Infrastructure Justification (Contract §D):** Foundational or infrastructure tasks lacking a user story must state an explicit prerequisite justification explaining why downstream story slices depend on it.
> - **N/A Criteria Rule (Contract §D):** Mark criteria `N/A` ONLY with reasoned non-buildable or out-of-scope rationale; missing mappings are explicit gaps, never implicit `N/A`.
> - **Evidence vs. Command Distinction (Contract §D, §I):** Evidence references remain unexercised/empty until executed; commands alone or checked task boxes are NOT proof of completion.
> - **Dependency & Parallel Safety (Contract §D):** Dependencies precede story slices; parallel marker `[P]` requires strictly disjoint file writes AND zero shared runtime/data dependency. Reject cycles and unknown dependencies before dispatch.
> - **Prebuild Readiness (Contract §F):** Spec-dependent features require plan readiness self-check and parent-owned independent read-only conformity review (`daw-review` prebuild checkpoint or explicit direct fallback) before build dispatch; trivial inline patches do not.
> - **Convergence Reconciliation (Contract §G):** Classify items into `Implemented & Verified`, `Implemented (Unverified)`, `Missing`, `Contradicted`, or `Blocked`. Preserve existing IDs and history; do not duplicate pending tasks; append only genuine uncovered work inside accepted scope.
> - **Local Tooling (Contract §I):** Reuse project-local commands and test runners; exact verification commands must actually execute and be inspected; no automatic external issues, PRs, or deployments without operator authorization.

> **Status:** Draft (default for new documents; set to Approved only with exact observed human/provider approval evidence)
> **Owner:** [Supplied/verified owner name or role; otherwise Unassigned — requires owner decision]
> **Scope:** [Feature lifecycle, phasing, technical milestones, release gates]
> **Source Documents / Revision:** [Actual observed BRD, PRD, blueprint.md, or relative path (marked unversioned if revision unobserved); never invent synthetic tags like @initial]
> **Assumptions:** [Team availability, platform stability, upstream component releases]
> **Open Decisions:** [Material sequencing questions — block dependent milestones until resolved]
> **Acceptance Criteria IDs:** [ROAD-01, ROAD-02, ...]
> **Reader & Core Task:** [Engineering Lead / Delivery Coordinator / Implementation Agent] — Sequence delivery phases, verify dependency ordering and bounded milestone outcomes, and monitor stop/replan triggers without relying on invented calendar release dates.
> **Quality Reference:** Canonical rubric and transition gate criteria in [references/document-quality.md](../references/document-quality.md) (common `DQ-01`..`DQ-05`, `roadmap-01`..`03`, and [#feature-delivery-contract](../references/document-quality.md#feature-delivery-contract)).

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

## 2. Task Traceability & Work Breakdown Matrix (Contract §D)

_Compact traceability mapping linking every requirement and acceptance criterion to discrete implementation tasks, target files, dependencies, verification commands, and observed evidence. Mark N/A only with explicit reasoned justification for non-buildable or out-of-scope criteria._

| Task ID     | Story / Req / AC Ref | Prerequisite Justification (Infra)   | Target File Paths       | Dependencies | [P]?       | Exact Verification Command & Expected Outcome | Status      | Observed Evidence Ref |
| :---------- | :------------------- | :----------------------------------- | :---------------------- | :----------- | :--------- | :-------------------------------------------- | :---------- | :-------------------- |
| `[TASK-01]` | `[REQ-01 / AC-01]`   | `[Justification if infra; else N/A]` | `[exact/path/file.py]`  | `[]`         | `[Yes/No]` | `[pytest tests/test_task01.py (exit 0)]`      | `[Pending]` | `[Unexercised]`       |
| `[TASK-02]` | `[REQ-02 / AC-02]`   | `[N/A]`                              | `[exact/path/file2.py]` | `[TASK-01]`  | `[No]`     | `[pytest tests/test_task02.py (exit 0)]`      | `[Pending]` | `[Unexercised]`       |

> **Matrix Invariants:**
>
> - **Task Cardinality:** A task may cover multiple criteria; artificial 1-to-1 mapping is not required.
> - **Supporting Infrastructure Justification:** A foundational or infra task lacking a user story MUST state an explicit prerequisite justification explaining why downstream story slices depend on it.
> - **Evidence vs. Command:** The `Observed Evidence Ref` column remains `[Unexercised]` until the verification command actually executes against the built codebase; planned commands or task checkboxes are NOT proof of completion.
> - **Parallel Safety `[P]`:** Mark `[P]?` as `Yes` ONLY if target files are strictly disjoint AND no shared mutable runtime/data state exists.

## 3. Critical Path, Dependency Validation & Concurrency (Contract §D)

_The dependency graph must form a strict Directed Acyclic Graph (DAG). Reject cycles and unknown task dependencies before dispatch. Dependencies must strictly precede dependent story slices._

| Task / Milestone | Blocking Dependencies | Parallel With | File Isolation Verified?                    | Cycle / Dependency Check |
| :--------------- | :-------------------- | :------------ | :------------------------------------------ | :----------------------- |
| `[TASK-01]`      | `[]`                  | `[TASK-03]`   | `[Verified disjoint files: src/a vs src/b]` | `[Acyclic]`              |
| `[TASK-02]`      | `[TASK-01]`           | `[None]`      | `[Serialized consumer of TASK-01]`          | `[Acyclic]`              |

## 4. Prebuild Readiness & Conformity Review Checkpoint (Contract §F)

_Spec-dependent features require plan readiness self-check and parent-owned independent read-only conformity review (`daw-review` prebuild checkpoint or explicit direct fallback with documented evidence limits) before build dispatch; trivial inline patches do not require prebuild review._

- **Plan Readiness Self-Check:** `[Passed / Blocked — verified 100% criteria mapping, zero orphan tasks, zero cycles, disjoint parallel boundaries]`
- **Independent Prebuild Review Verdict:** `[Accepted / Findings Pending / Direct Fallback with Limits]`
- **Prebuild Review Findings Ledger:**

| Finding ID | Severity                    | Location                    | Consequence                       | Repair Proposal             |
| :--------- | :-------------------------- | :-------------------------- | :-------------------------------- | :-------------------------- |
| `[F-01]`   | `[Blocking / Non-Blocking]` | `[file.py:lines or doc.md]` | `[Direct consequence of finding]` | `[Exact corrective action]` |

## 5. Convergence Reconciliation Ledger (Contract §G)

_When re-planning or reconciling drift: inspect actual code, authoritative contracts, and current verification evidence. Classify items into Implemented & Verified, Implemented (Unverified), Missing, Contradicted, or Blocked. Preserve stable IDs and history; append only genuine uncovered work inside accepted scope._

| Item / Contract Ref | Classification             | Preserved Task ID | Current Observed Code / Evidence | Action / Appended Task        |
| :------------------ | :------------------------- | :---------------- | :------------------------------- | :---------------------------- |
| `[REQ-01 / AC-01]`  | `[Implemented & Verified]` | `[TASK-01]`       | `[tests/test_01.py passed]`      | `[None — preserved]`          |
| `[REQ-02 / AC-02]`  | `[Missing]`                | `[TASK-02]`       | `[Endpoint returns 404]`         | `[Appended TASK-03 in scope]` |

## 6. Scope Cut & De-scoping Protocol

_If unexpected blockers occur, de-scoping must be agreed upon explicitly rather than silently dropping acceptance criteria._

- **Non-Negotiable Core (Must Have):** [Core functionality required for safety and functionality]
- **Negotiable Secondary (Nice to Have):** [Performance micro-optimizations, auxiliary batch scripts]
- **Stop / Replan Triggers:** [Dependency cycle detected, unmapped criteria gap, prebuild review blocking finding, or unresolvable specification contradiction]

## 7. Document Quality & Review Checks

_Verify against canonical [Document Quality Rubric](../references/document-quality.md) and [Feature Delivery Contract](../references/document-quality.md#feature-delivery-contract) before workflow transitions. Mark N/A with rationale where proportional to scope._

- [ ] **roadmap-01 (Sequencing & Phasing):** Are delivery phases, milestones, and deliverables broken down into sequenced, dependency-ordered work units?
- [ ] **roadmap-02 (Critical Path & Dependencies):** Are critical path dependencies, integration risk choke-points, and technical debt mitigations explicitly identified with cycle checks?
- [ ] **roadmap-03 (Completion Gates & Decision Rules):** Are phase completion gates, release acceptance criteria, and go/no-go or stop/replan decision rules defined with observable signals without invented dates?
- [ ] **traceability-check (Contract §D):** Is every requirement/AC traced to task IDs, target files, dependencies, verification commands, and evidence status without implicit N/A?
- [ ] **prebuild-readiness (Contract §F):** Is plan readiness self-check complete and parent-directed prebuild review recorded for spec-dependent features?
- [ ] **convergence-integrity (Contract §G):** Are existing task IDs and history preserved during replanning, with genuine gaps appended inside accepted scope?
