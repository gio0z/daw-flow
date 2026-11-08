# Functional Requirements Document (FRD): [Feature / Component]

> **Fill-in Guidance:** Fill this template using existing repository patterns and domain conventions adhering to the canonical shared procedural contract in [Canonical Document Quality & Workflow Transition Guide](../references/document-quality.md#feature-delivery-contract). Equivalent existing technical contracts or schemas may be linked directly. Mark N/A with rationale if not applicable. Do not force generic REST or HTTP API schemas if implementing internal modules, CLI scripts, or data pipelines. Do not invent speculative schemas; expected input shape does not equal enforced schema (record missing validation explicitly). Distinguish user requirements and observed source facts from author-proposed engineering defaults using a concise provenance ledger or explicit labels (`[User Requirement]`, `[Observed Fact]`, `[Proposed Default]`). Record proposed/default vs decided. Unresolved technical questions block only impacted engineering components. Persistent entities and their relationships are owned by the linked ERD; this FRD keeps behavioral payload types, validation, and state transitions, and links to the ERD for persistent identity and relationships — never restate its content here.

> **Status:** Draft (default for new documents; set to Approved only with exact observed human/provider approval evidence)
> **Owner:** [Supplied/verified owner name or role; otherwise Unassigned — requires owner decision]
> **Scope:** [Bounded modules, schema boundaries, CLI commands, or API endpoints]
> **Source Documents / Revision:** [Actual observed PRD, design doc, or relative path (marked unversioned if revision unobserved); never invent synthetic tags like @initial]
> **Assumptions:** [Runtime environment, language version, database engine capabilities]
> **Open Decisions:** [Material engineering trade-offs — block impacted execution paths until settled]
> **Acceptance Criteria IDs:** [FRD-01, FRD-02, ...]
> **Associated User Story IDs:** [US-01, US-02, ...]
> **Target Audience & Reader Task:** [Backend engineer, systems integrator, or test automation author: implement domain entities, verify deterministic state transitions, and enforce interface contracts and error invariants]
> **Quality Standards:** [Canonical Document Quality & Transition Guide](../references/document-quality.md#feature-delivery-contract) (specifically [Governance Alignment](../references/document-quality.md#a-governance-and-authoring-alignment) and [Feature Slicing & Behavioral Oracles](../references/document-quality.md#c-feature-slicing-and-behavioral-contract-oracles))

---

- **Entities & Types:** [Behavioral payload types, DTOs, interfaces, and value objects using repository naming conventions. Persistent entity identity and relationships: link the ERD document; do not duplicate its authority here]

- **Lifecycle & Transitions:** [Valid state progressions, e.g., `Draft -> PendingApproval -> Active -> Archived`]
- **Forbidden Transitions:** [Transitions explicitly disallowed by business logic]

## 2. Behavioral Specifications & Interface Contracts

_Describe interfaces, CLI arguments, or endpoints according to repo architecture. Provide exact input/output/error/state oracles. Do not force generic REST schemas if implementing internal modules or CLI tools._

### FRD-01: [Behavior Name] (Maps to US-01)

_Write the contract in EARS or Given/When/Then per [EARS Semantic Guidance](../references/document-quality.md#acceptance-criteria-ears). One behavior per criterion; split independently verifiable responses._

- **Criterion (EARS or GWT):** [WHEN/WHILE/WHERE/IF-THEN + THE SYSTEM SHALL + observable response, or Given/When/Then]
- **Condition / trigger or state:** [Trigger event, while-state, or precondition]
- **System response + observable oracle:** [Observable response and how a verifier proves it — return value, state readback, error code, file/DB read]
- **Negative / no-change (if meaningful):** [Observable error AND no-change side effect where one exists, or N/A]
- **Signature / Command Syntax:** `[Signature, CLI syntax, or Method]`
- **Inputs & Validation Rules:** [Type constraints, required vs optional, value limits, format validators]
- **Outputs & Return Types:** [Structured response payload, return object, or stdout format]
- **Provenance:** `[User Requirement]` / `[Observed Fact]` / `[Proposed Default]` / `[Open Question]` — no invented timeout/error policies; thresholds need a traceable source.

### FRD-02: [Negative / Error Behavior] (Maps to US-02)

- **Criterion (EARS or GWT):** [IF + unwanted condition, THEN THE SYSTEM SHALL + error response]
- **Condition / trigger or state:** [Invalid input or forbidden state]
- **System response + observable oracle:** [Error code/status/message and how a verifier reads it]
- **Negative / no-change (if meaningful):** [No rows persisted / no external call / input untouched, or N/A]
- **Signature / Command Syntax:** `[Signature, CLI syntax, or Method]`
- **Inputs & Constraints:** [Inputs and validation]
- **Outputs / Failure Oracle:** [Explicit expected error, exit code, or response]
- **Provenance:** `[User Requirement]` / `[Observed Fact]` / `[Proposed Default]` / `[Open Question]`

## 3. System Invariants & Inseparable Safety Boundaries

- **Always True:** [Conditions that MUST remain invariant before and after any execution]
- **Never True:** [Forbidden states that must trigger immediate rejection or rollback]
- **Inseparable Safety & Transaction Invariants:** [Transactional boundaries, ACID requirements, or security checks that MUST NOT be split across independent deployments. State rationale for unified deployment]
- **Concurrency & Idempotency:** [Locking semantics, optimistic concurrency, deduplication keys]

## 4. Supporting Infrastructure & Prerequisites

_Supporting infrastructure tasks (DB migrations, schema baselines, configuration seeds) can lack an independent user story ONLY with actual prerequisite justification documented here:_

- **Infra Prerequisite 1:** [e.g. Database migration for tokens table] — **Prerequisite Justification:** Required by FRD-01 before session refresh logic can execute.
- **Infra Prerequisite 2:** [e.g. Environment secret configuration] — **Prerequisite Justification:** Required for signing keys.

## 5. Side Effects & Integration Points

- **Database Operations:** [Reads, transactional writes, atomic batches]
- **Events & Messaging:** [Published domain events, webhook dispatches, async worker queues]
- **Filesystem / OS Interactions:** [File creation, temporary files, external process spawns]

## 6. Verification Mapping & Test Oracles

- **FRD-01 -> Test Target:** `[tests/path/test_case.ext::test_happy_path]` — **Assertion Oracle:** [Expected return type and database state change]
- **FRD-02 -> Test Target:** `[tests/path/test_case.ext::test_error_handling]` — **Assertion Oracle:** [Deterministic exception or error code returned]

## 7. Provenance Ledger & Open Decisions

| ID / Topic   | Classification       | Content / Decision                                       | Status   | Impacted Execution Path |
| :----------- | :------------------- | :------------------------------------------------------- | :------- | :---------------------- |
| `ENG-DEC-01` | `[Decided]`          | [Confirmed engineering pattern or schema contract]       | Settled  | All                     |
| `ENG-DEF-01` | `[Proposed Default]` | [Author-proposed configuration or timeout default]       | Proposed | Component B             |
| `ENG-OQ-01`  | `[Open Decision]`    | [Material architectural question; blocks dependent path] | Blocked  | Component C only        |

## 8. Document Quality & Review Checks

_Reviewers and authoring agents must verify the document against the canonical [Document Quality Specification](../references/document-quality.md) before workflow transitions:_

- [ ] **frd-01:** Are behavioral payload types and validation constraints defined with unambiguous types, with persistent entity identity and relationships linked to the ERD rather than duplicated?
- [ ] **frd-02:** Are system state transitions, event triggers, preconditions, and postconditions deterministically mapped?
- [ ] **frd-03:** Are edge cases, error handling contracts, and input boundary conditions specified with observable behavior?
