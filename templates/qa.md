# Quality Assurance & Semantic Verification Matrix: [Feature / System]

> **Fill-in Guidance:** Fill this template using verified test cases, executable reproduction steps, and observable semantic evidence per [Feature Delivery Contract §E, §F, §G](../references/document-quality.md#feature-delivery-contract). Equivalent existing test suites or test reports may be linked directly. Routine bugfixes and minor patches do NOT require a full new `qa.md`; routine changes can reuse existing test suites, reproduction scripts, or an inline verification record. Mark N/A with rationale when covered by existing test suites. Define an independent observable test oracle boundary distinguishing unexercised capabilities from empirical passes. Negative verification must prove semantic denial and zero data leakage appropriate to the actual interface (e.g. exit code, permission exception, or HTTP status per system design). Do not fabricate test passes, empirical screen-reader compatibility claims, or mock output traces. Unresolved test criteria block only impacted verification sign-off. Never include secret values or credentials in templates. Preserve exact risk point confirmation and never invent commands.
>
> **Requirements-Quality Checklist vs. Runtime Test Acceptance (§E):**
>
> - The requirements-quality checklist below is a reviewer-owned judgment artifact ("unit tests for requirements writing"). It validates prose completeness, clarity, consistency, and verifiability.
> - A builder or implementation author CANNOT tick reviewer criteria (`[x]`) to self-approve.
> - Known blocking requirements, failing test suites, or gate failures MUST NEVER be overridden with generic user "proceed" or requests to relax tests/proofs.
>
> **Distinguishing Formal Document Rework Edges from Code-Only Evidence Invalidation:**
>
> - **Formal Document Rework:** Modifying authoritative specification documents changes their SHA-256 and invalidates prior transition eligibility, requiring formal transition (`review-rework` -> `rework-review` via `python3 scripts/validate.py docs`).
> - **Code-Only Evidence Invalidation:** Modifying application code, configuration, or environment invalidates prior test execution evidence and acceptance verdicts for affected paths. Fresh deterministic tests must be rerun proportionally without modifying document transition records unless specifications changed.
>
> **Verification Non-Implementation Boundary (§G):**
>
> - Verification identifies missing, unverified, or contradicted behavior and returns findings to the parent orchestrator. The verifier has NO implementation role and NEVER edits source code to fix defects.
>
> **Status:** Draft (default for new documents; set to Approved only with exact observed human/provider approval evidence)
> **Owner:** [Supplied/verified owner name or role; otherwise Unassigned — requires owner decision]
> **Scope:** [Semantic verification, negative testing, cross-tenant isolation, regression tests]
> **Target Reader Role:** [QA engineer, test automation reviewer, or fresh verification subagent executing acceptance suites]
> **Core Reader Task:** [Execute independent verification with observable pass/fail test oracle boundaries, distinguishing unexercised checks from passes without assuming ambient state]
> **Source Documents / Revision:** [Actual observed PRD, FRD, git commit SHA, or relative path (marked unversioned if revision unobserved); never invent synthetic tags like @initial]
> **Assumptions:** [Test database isolation, deterministic seed data, sandbox credentials]
> **Open Decisions:** [Material test coverage gaps — block verification sign-off until resolved]
> **Acceptance Criteria IDs:** [QA-01, QA-02, ...]
> **Quality Reference:** Canonical rubric and transition gate criteria in [references/document-quality.md](../references/document-quality.md#feature-delivery-contract) (common `DQ-01`..`DQ-05`, `qa-01`..`qa-03`, §E, §F, §G).

---

## 1. Scope & Verification Strategy

_Routine bugfixes do NOT require a full new `qa.md`. Existing test suites or inline reproduction records are preferred for routine work._

- **Target Surface:** [API endpoints, CLI arguments, UI workflows, or background worker jobs]
- **Verification Environment:** [Local isolated container, Staging, CI pipeline]
- **Test Data Strategy:** [Deterministic fixtures, generated test seeds, clean teardown]

## 2. Requirements-to-Test Traceability & Convergence Matrix

_Map each requirement/acceptance criterion to its implementing story, task, target source paths, and deterministic verification command per [EARS Semantic Guidance](../references/document-quality.md#acceptance-criteria-ears) and [Feature Delivery Contract §D, §G](../references/document-quality.md#feature-delivery-contract). Source existence, passing old tests, or task checkboxes are never completion alone._

_Coverage rule:_ normal-path criteria and IF/THEN error-path criteria are checked separately. For each mapped criterion, the verifier runs the check that proves the stated **system response + observable oracle**, and records evidence as `passed` only when the oracle matches; otherwise `failed`, `blocked`, `missing`, or `contradicted` — or `unexercised` until the verification command actually runs. Never infer a pass from the PRD/FRD text alone._

### 2.1 Coverage Denominator Accounting

- **Total Declared Criteria (N):** [Count of all declared requirements and ACs in scope]
- **Justified Non-Buildable / Out-of-Scope (M):** [Count of criteria excluded from buildable denominator with explicit rationale, e.g. post-launch business KPIs without test oracles]
- **Unresolved Gaps (K):** [Count of unmapped or unresolved criteria — strictly retained in denominator, NEVER silently excluded]
- **Effective Buildable Denominator (N - M):** [N minus M]
- **Empirically Verified Passing (P):** [Count of criteria with fresh passing runtime evidence]
- **Actual Verified Coverage Ratio:** `P / (N - M)` [Report exact fraction; no synthetic 100% metrics]

### 2.2 Traceability & Verification Status

| AC / Req ID | Criterion (condition → response + oracle)                                                            | User Story | Task ID(s) | Touchpoint Source Paths | Verification Command / Expected Oracle                                       | Observed Status | Evidence Ref / Commit SHA          |
| :---------- | :--------------------------------------------------------------------------------------------------- | :--------- | :--------- | :---------------------- | :--------------------------------------------------------------------------- | :-------------- | :--------------------------------- |
| `QA-01`     | WHEN [normal trigger] THE SYSTEM SHALL [normal response]; oracle: [state readback / command output]  | `US-01`    | `TASK-01`  | `src/auth/session.py`   | `pytest tests/auth/test_session.py` → expect [normal oracle]                 | `Unexercised`   | `[awaiting fresh test run output]` |
| `QA-02`     | IF [invalid input], THEN THE SYSTEM SHALL [error response]; oracle: [error code + no persisted rows] | `US-01`    | `TASK-02`  | `src/auth/token.py`     | `pytest tests/auth/test_token.py` → expect [error code + no-change readback] | `Unexercised`   | `[awaiting fresh test run]`        |

_(Observed Status must be one of: `Passed` (implemented/verified), `Failing`, `Blocked`, `Unexercised` (implemented-unverified), `Missing`, or `Contradicted`). Evidence stays `unexercised` until the command runs._

## 3. Negative & Boundary Testing

_Explicitly verify that invalid, out-of-order, or malicious actions fail safely and deterministically._

- **Cross-Tenant Isolation (Negative):** Request tenant A's resource with tenant B's authenticated context -> Expect semantic denial and zero data leakage appropriate to the interface (e.g., forbidden error, not found, or access exception per system convention; no tenant A data leaked).
- **Malformed & Boundary Inputs:** Null bytes, max-length overflow, negative quantities -> Expect deterministic validation error with structured error representation.
- **Concurrent Mutations:** Two simultaneous updates with conflicting versions -> Expect conflict error with retry recommendation or safe deterministic rejection.

## 4. Non-Functional & Resilience Verification

- **Performance / Latency Proof:** [p95 response time or execution duration under verified test load]
- **Failure Recovery:** [Service behavior when dependency or secondary storage becomes unavailable]

## 5. Verification Sign-off & Evidence Log

- [ ] Unit tests pass: `[N] passed, 0 failed`
- [ ] Integration & negative tests pass: `[N] passed, 0 failed`
- [ ] Concrete evidence artifacts linked (test runner output, CLI logs, sanitized response traces — NO credentials or secrets).

## 6. Convergence Gap & Invalidation Ledger

### 6.1 Change Invalidation & Rerun Tracking

| Invalidation Event | Modified Files / Revisions | Affected Test Cases / ACs | Rerun Command                       | Fresh Result / Evidence |
| :----------------- | :------------------------- | :------------------------ | :---------------------------------- | :---------------------- |
| Code modification  | `src/auth/session.py`      | `QA-01`                   | `pytest tests/auth/test_session.py` | `Passed (exited 0)`     |

### 6.2 Convergence Defect & Remediation Routing (§G)

_Record gaps discovered during verification. The verifier NEVER implements fixes directly; all items route via parent orchestrator to `daw-plan` or `daw-build`._

| Finding ID | Source Ref | Gap Type (`missing` / `partial` / `contradicts` / `unrequested`) | Severity (`BLOCKER` / `HIGH` / `MEDIUM` / `LOW`) | Observed Evidence                                 | Recommended Parent Routing                           |
| :--------- | :--------- | :--------------------------------------------------------------- | :----------------------------------------------- | :------------------------------------------------ | :--------------------------------------------------- |
| `GAP-01`   | `QA-02`    | `partial`                                                        | `HIGH`                                           | Token expiration check missing edge case handling | Route to `daw-build` to implement boundary condition |

## 7. Document Quality & Review Checks

_Verify against canonical [Document Quality Rubric](../references/document-quality.md) before workflow transitions. Mark N/A with rationale where proportional to scope._

- [ ] **qa-01:** Is the test strategy partitioned across appropriate testing levels (e.g. unit, integration, system) with concrete testing boundaries?
- [ ] **qa-02:** Are test environments, fixtures, synthetic data, and isolation strategies specified proportional to system architecture?
- [ ] **qa-03:** Are exit criteria, defect severity classifications, flakiness policies, and regression gating rules explicitly defined?
