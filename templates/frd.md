# Functional Requirements Document (FRD): [Feature / Component]

> **Fill-in Guidance:** Fill this template using existing repository patterns and domain conventions. Equivalent existing technical contracts or schemas may be linked directly. Mark N/A with rationale if not applicable. Do not force generic REST or HTTP API schemas if implementing internal modules, CLI scripts, or data pipelines. Do not invent speculative schemas; expected input shape does not equal enforced schema (record missing validation explicitly). Distinguish user requirements and observed source facts from author-proposed engineering defaults using a concise provenance ledger or explicit labels. Unresolved technical questions block only impacted engineering components.

> **Status:** Draft (default for new documents; set to Approved only with exact observed human/provider approval evidence)
> **Owner:** [Supplied/verified owner name or role; otherwise Unassigned — requires owner decision]
> **Scope:** [Bounded modules, schema boundaries, CLI commands, or API endpoints]
> **Source Documents / Revision:** [Actual observed PRD, design doc, or relative path (marked unversioned if revision unobserved); never invent synthetic tags like @initial]
> **Assumptions:** [Runtime environment, language version, database engine capabilities]
> **Open Decisions:** [Material engineering trade-offs — block impacted execution paths until settled]
> **Acceptance Criteria IDs:** [FRD-01, FRD-02, ...]

---

## 1. Domain Entities & State Models

- **Entities & Types:** [Domain structures, DTOs, interfaces, or tables using repository naming conventions]
- **Lifecycle & Transitions:** [Valid state progressions, e.g., `Draft -> PendingApproval -> Active -> Archived`]
- **Forbidden Transitions:** [Transitions explicitly disallowed by business logic]

## 2. Behavioral Specifications & Contracts

_Describe interfaces, CLI arguments, or endpoints according to repo architecture. Do not force generic REST schemas if implementing internal modules or CLI tools._

- **Interface / Command / Endpoint:** `[Signature, CLI syntax, or Method]`
  - **Inputs & Constraints:** [Type constraints, required vs optional, validation rules]
  - **Outputs & Return Types:** [Structured response or return value]
  - **Error Handling & Failure Semantics:** [Specific error types, exit codes, or status payloads]

## 3. System Invariants

- **Always True:** [Conditions that MUST remain invariant before and after any execution]
- **Never True:** [Forbidden states that must trigger immediate rejection or rollback]
- **Concurrency & Idempotency:** [Locking semantics, optimistic concurrency, deduplication keys]

## 4. Side Effects & Integration Points

- **Database Operations:** [Reads, transactional writes, atomic batches]
- **Events & Messaging:** [Published domain events, webhook dispatches, async worker queues]
- **Filesystem / OS Interactions:** [File creation, temporary files, external process spawns]

## 5. Verification Mapping

- **FRD-01 -> Unit / Integration Test:** `[tests/path/test_case.ext]`
- **FRD-02 -> Unit / Integration Test:** `[tests/path/test_case.ext]`
