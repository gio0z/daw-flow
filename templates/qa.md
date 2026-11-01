# Quality Assurance & Semantic Verification Matrix: [Feature / System]

> **Fill-in Guidance:** Fill this template using verified test cases, executable reproduction steps, and observable semantic evidence. Equivalent existing test suites or test reports may be linked directly. Routine bugfixes and minor patches do NOT require a full new `qa.md`; routine changes can reuse existing test suites, reproduction scripts, or an inline verification record. Mark N/A with rationale when covered by existing test suites. Negative verification must prove semantic denial and zero data leakage appropriate to the actual interface (e.g. exit code, permission exception, or HTTP status per system design). Do not fabricate test passes or mock output traces. Unresolved test criteria block only impacted verification sign-off. Never include secret values or credentials in test logs or templates.

> **Status:** Draft / Ready for Review / Approved / Superseded
> **Owner:** [QA Engineer / Test Lead]
> **Scope:** [Semantic verification, negative testing, cross-tenant isolation, regression tests]
> **Source Documents / Revision:** [PRD, FRD, git commit SHA]
> **Assumptions:** [Test database isolation, deterministic seed data, sandbox credentials]
> **Open Decisions:** [Material test coverage gaps — block verification sign-off until resolved]
> **Acceptance Criteria IDs:** [QA-01, QA-02, ...]

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
