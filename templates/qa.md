# Quality Assurance & Semantic Verification Matrix: [Feature / System]

> **Fill-in Guidance:** Fill this template using verified test cases, executable reproduction steps, and observable semantic evidence. Equivalent existing test suites or test reports may be linked directly. Routine bugfixes and minor patches do NOT require a full new `qa.md`; routine changes can reuse existing test suites, reproduction scripts, or an inline verification record. Mark N/A with rationale when covered by existing test suites. Define an independent observable test oracle boundary distinguishing unexercised capabilities from empirical passes. Negative verification must prove semantic denial and zero data leakage appropriate to the actual interface (e.g. exit code, permission exception, or HTTP status per system design). Do not fabricate test passes, empirical screen-reader compatibility claims, or mock output traces. Unresolved test criteria block only impacted verification sign-off. Never include secret values or credentials in templates. Preserve exact risk point confirmation and never invent commands.

> **Status:** Draft (default for new documents; set to Approved only with exact observed human/provider approval evidence)
> **Owner:** [Supplied/verified owner name or role; otherwise Unassigned — requires owner decision]
> **Scope:** [Semantic verification, negative testing, cross-tenant isolation, regression tests]
> **Target Reader Role:** [QA engineer, test automation reviewer, or fresh verification subagent executing acceptance suites]
> **Core Reader Task:** [Execute independent verification with observable pass/fail test oracle boundaries, distinguishing unexercised checks from passes without assuming ambient state]
> **Source Documents / Revision:** [Actual observed PRD, FRD, git commit SHA, or relative path (marked unversioned if revision unobserved); never invent synthetic tags like @initial]
> **Assumptions:** [Test database isolation, deterministic seed data, sandbox credentials]
> **Open Decisions:** [Material test coverage gaps — block verification sign-off until resolved]
> **Acceptance Criteria IDs:** [QA-01, QA-02, ...]
> **Quality Reference:** Canonical rubric and transition gate criteria in [references/document-quality.md](../references/document-quality.md) (common `DQ-01`..`DQ-05`, `qa-01`..`qa-03`).

---

## 1. Scope & Verification Strategy

_Routine bugfixes do NOT require a full new `qa.md`. Existing test suites or inline reproduction records are preferred for routine work._

- **Target Surface:** [API endpoints, CLI arguments, UI workflows, or background worker jobs]
- **Verification Environment:** [Local isolated container, Staging, CI pipeline]
- **Test Data Strategy:** [Deterministic fixtures, generated test seeds, clean teardown]

## 2. Semantic Acceptance Matrix

_Every acceptance criterion must map to an observable semantic check, NOT merely a generic success indicator or HTTP 200._

| AC ID   | Scenario & Input State                 | Expected Observable State / Output                        | Test Case / Script                | Verification Evidence                      |
| :------ | :------------------------------------- | :-------------------------------------------------------- | :-------------------------------- | :----------------------------------------- |
| `QA-01` | [Valid creation payload with tenant A] | [Entity persisted with tenant_id=A, audit record emitted] | `tests/path/test_create.ext`      | `[Sanitized log output / DB row evidence]` |
| `QA-02` | [Duplicate idempotency key submitted]  | [Original entity returned, no duplicate entity created]   | `tests/path/test_idempotency.ext` | `[Persistence count == 1 evidence]`        |

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

## 6. Document Quality & Review Checks

_Verify against canonical [Document Quality Rubric](../references/document-quality.md) before workflow transitions. Mark N/A with rationale where proportional to scope._

- [ ] **qa-01:** Is the test strategy partitioned across appropriate testing levels (e.g. unit, integration, system) with concrete testing boundaries?
- [ ] **qa-02:** Are test environments, fixtures, synthetic data, and isolation strategies specified proportional to system architecture?
- [ ] **qa-03:** Are exit criteria, defect severity classifications, flakiness policies, and regression gating rules explicitly defined?
