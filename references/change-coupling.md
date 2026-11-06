# Change Coupling, Structural Cohesion & Boundary Analysis Reference

This reference defines the canonical principles, inspection taxonomy, and evaluation standards for structural dependency analysis and change coupling in the Deterministic Agentic Workflow (DAW) suite.

It is used as the primary foundation by `daw-untangle` and as a light, on-demand reference by `daw-design`, `daw-plan`, `daw-build`, and `daw-review` during structural boundary definition, refactoring planning, implementation, and architectural audits.

---

## 1. Core Guiding Principle & Scope Boundary

### The Core Guiding Question

> **"Should these pieces change together?"**

Structural analysis does not exist to satisfy aesthetic symmetry or subjective dogma. It exists to minimize friction across software evolution. The central inquiry evaluates whether two units of code share an essential conceptual lifecycle or whether they have been accidentally coupled by convenience, historical accretion, or premature abstractions:

1. **Essential Co-Change:** Components that model the exact same domain invariant, protocol, or state machine and _must_ change synchronously when that invariant evolves.
2. **Accidental Co-Change:** Components that change together due to leaky abstraction boundaries, shared untyped data blobs, implicit side-effects, or cross-cutting structural entanglements.
3. **Temporal vs. Semantic Coupling:** Components required to run in a specific sequence (temporal ordering) should not force structural coupling across distant layers.

### Scope & Proportionality Invariant

Structural analysis must remain strictly proportional to authorized scope:

- **Authorized Boundary:** Analysis investigates **only** the authorized named area, subsystem, or explicitly requested full repository. It NEVER expands into an unsolicited whole-codebase cleanup campaign or cosmetic refactoring wave.
- **Proportional Depth:** Routine localized feature additions, isolated bug fixes, or single-file edits DO NOT require change-coupling analysis or untangle passes.
- **Primacy of Working Code:** Working, well-tested code that does not actively incur change friction should remain untouched. "Boring" and proven code is preferable to novel abstractions.

---

## 2. Grounded Evidence & Code Intelligence

Architectural claims must be substantiated with concrete code evidence. Speculative coupling claims or vibe-based diagnoses are strictly invalid.

### Inspection Hierarchy & Tooling Discipline

When analyzing dependencies and call graphs, apply this tool preference order:

1. **Language Server Protocol (LSP) First:**
   - If an LSP server is configured and active in the host environment, use language intelligence (`definitions`, `references`, `implementations`, `type_definitions`) for exact cross-file symbol resolution.
2. **Graph Intelligence with Freshness Verification:**
   - If codebase graph tooling is available (e.g., indexed knowledge graphs, call-path indexes), verify index freshness against current file timestamps before trusting edges. Always verify cited nodes with targeted source reads.
3. **Targeted Static Code Analysis:**
   - When language servers or graph indexes are absent or incomplete, use deterministic static tools (`grep`, `glob`, AST patterns, and targeted file reads) to trace imports, caller sites, type signatures, and configuration bindings.

### Negative Evidence Discipline (No Absolute "Dead Code" Claims)

A common failure mode in structural analysis is asserting that a function, class, or module is "unused" or "dead code" simply because no explicit static call site was found in immediate application code.

- **Explicit Coverage Disclosure:** Any negative claim (e.g., "no callers found") MUST state the exact search boundary and tools inspected (e.g., "Inspected `src/` via symbol reference search; no internal callers detected").
- **Dynamic Entrypoint Protection:** Never label code dead without considering:
  1. _Dynamic Dispatch & Reflection:_ Event buses, string-based dispatch tables, metaprogramming.
  2. _Plugin & Extension Registries:_ Plugins or handlers dynamically resolved via configuration strings, entry points, or `importlib.import_module(plugin_path)` (e.g. `plugins.auth_oidc`). These have zero static call sites in application code but are actively used; flagging them as dead code is a false positive.
  3. _Configuration & Serialization:_ Data classes, models, or schema handlers instantiated dynamically from JSON/YAML or database rows.
  4. _Public / Library Surfaces:_ Exported symbols intended for external consumers, CLI runners, or third-party integrations.

---

## 3. The Change-Coupling Taxonomy

When evaluating code friction, classify findings into three canonical categories:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Change-Coupling Taxonomy                        │
├───────────────────────┬───────────────────────┬────────────────────────┤
│     Hidden Links      │     Needless Links    │    Surplus Taxonomy    │
│  (Implicit Coupling)  │ (Artificial Coupling) │  (Over-Abstraction)    │
├───────────────────────┼───────────────────────┼────────────────────────┤
│ • Shared mutable state│ • Pass-through blobs  │ • 1-line pass-throughs │
│ • Global singletons   │ • Mega-context props  │ • Single-impl interfaces│
│ • Magic strings/keys  │ • Internal type leaks │ • Premature frameworks │
│ • Unwritten sequences │ • Inappropriate detail│ • Gratuitous layering  │
└───────────────────────┴───────────────────────┴────────────────────────┘
```

### 1. Hidden Links (Implicit Coupling)

Hidden links occur when components depend on each other without an explicit, type-checked, or syntactic contract. Changes to one component break another without compile-time or static warnings.

- **Shared Mutable State / Global Singletons:** Multiple modules reading from and writing to shared global dictionaries, module-level variables, or uncoordinated cache instances.
- **Convention-Based Side Effects:** Component A relies on Component B having been executed earlier in the request lifecycle without explicit parameter passing or dependency injection.
- **Untyped Config Bags / Magic String Coupling:** Passing raw dictionaries where keys like `"auth_v2_enabled"` or `"session_timeout"` are read across disparate files without centralized constant or schema definitions.
- **Environment Variable Initialization Ordering (Temporal Env Coupling):** Multiple modules reading and mutating `os.environ` with implicit assumptions that Module A executed `.load_env()` or initialized specific keys before Module B runs, creating invisible temporal coupling.
- **Pricing & Domain Calculation Duplication:** Duplicating business formulas (e.g. pricing calculations, discount rules, tax tiers) across disparate modules instead of sharing a canonical domain engine, forcing shotgun surgery whenever business rules evolve.
- **Database Trigger & Action-at-a-Distance Coupling:** Application logic relying on database triggers, hidden stored procedures, or implicit cascading side effects that bypass application validation.

### 2. Needless Links (Artificial & Leaky Coupling)

Needless links occur when modules are tightly bound together despite having conceptually independent responsibilities.

- **Context Bag & Mega-Object Passing:** Passing an entire 30-field `ApplicationContext` or `Request` object into a helper function that only needs a single `user_id` string.
- **Internal Type & Implementation Leakage:** Exposing internal ORM models, database cursor handles, or private helper classes across public subsystem boundaries, forcing downstream consumers to understand internal storage mechanics.
- **Inappropriate Intimacy:** Module A directly accessing private or underscore-prefixed properties of Module B, bypassing Module B's interface.
- **Circular Dependencies:** Module A importing Module B while Module B imports Module A, often patched over with deferred inline imports that obscure architectural tangling.

### 3. Surplus Taxonomy (Over-Abstraction & Shallow Modules)

Surplus taxonomy occurs when developers introduce layers of indirection, abstractions, or classifications that add cognitive load without providing simplification or isolation.

- **Shallow Modules (Ousterhout):** Modules where the interface is as complex as, or more complex than, the implementation. A class with five methods that each forward directly to another single method without transformation or invariant enforcement.
- **Single-Implementation Speculative Interfaces:** Interfaces (`IUserService`, `IOrderProcessor`) introduced "in case we need another implementation later" when only one concrete implementation exists and no testing boundary requires abstraction.
- **Pass-Through Pipelines (Gratuitous Layering):** A call chain traversing `Controller -> Facade -> Service -> Manager -> Handler -> Repository` where intermediate layers do nothing but forward arguments.
- **Premature Generic Frameworks:** Replacing three straightforward, clear functions with an intricate meta-programmed generic pipeline that requires mental decompression to trace.

---

## 4. Preserving Legitimate Architectural Patterns

A critical invariant in structural analysis: **NOT every layer, wrapper, retry, or exception translation is unnecessary coupling.**

The analysis MUST actively distinguish between accidental coupling and legitimate, necessary software resilience patterns. Preserving these patterns is an absolute requirement:

```
┌────────────────────────────────────────────────────────────────────────┐
│              Preserved Legitimate Architectural Patterns               │
├──────────────────────────┬─────────────────────────────────────────────┤
│ Pattern                  │ Justification & Legitimacy Criteria         │
├──────────────────────────┼─────────────────────────────────────────────┤
│ Protocol Retries         │ Exponential backoff, transient network      │
│                          │ fault tolerance, idempotency token handling │
├──────────────────────────┼─────────────────────────────────────────────┤
│ Security & Auth Wrappers │ Perimeter authentication, JWT validation,   │
│                          │ CSRF guards, role checks, input sanitizers  │
├──────────────────────────┼─────────────────────────────────────────────┤
│ Transaction Boundaries   │ Database transactions, atomic units-of-work,│
│                          │ commit/rollback lifecycles, resource cleanups│
├──────────────────────────┼─────────────────────────────────────────────┤
│ Seam Error Translation   │ Catching low-level transport errors         │
│                          │ (e.g. SQLite/HTTP) and re-raising typed     │
│                          │ domain errors at public subsystem boundaries│
├──────────────────────────┼─────────────────────────────────────────────┤
│ Bounded Context Seams    │ Maintaining explicit boundaries between     │
│                          │ distinct domain bounded contexts or teams   │
└──────────────────────────┴─────────────────────────────────────────────┘
```

1. **Protocol Retries & Backoff (Explicit Non-Finding):** Legitimate network and distributed system communication requires retry loops, jitter, and circuit breakers (e.g., handling HTTP 429 Too Many Requests, exponential backoff for rate limits, or transient connection drops). Standard retry decorators or backoff wrappers are essential resilience mechanisms and MUST NOT be flagged as surplus taxonomy or needless wrappers.
2. **Security & Authentication Guards (Explicit Non-Finding):** Middleware, decorators (e.g., `@require_permission("orders:write")`), or wrappers enforcing authentication, authorization, rate limiting, or input sanitization protect system integrity. They represent vital defense-in-depth boundaries and MUST NOT be flattened into business logic or flagged as unnecessary indirection.
3. **Clean Module Valid Pass:** When inspecting a well-structured, cohesive module that exhibits clean boundaries and no pathological coupling, returning zero findings with `status: "pass"` and explicit inspected coverage is the expected valid outcome. Never manufacture artificial findings or forced refactorings.
4. **Transaction Boundaries & Unit of Work:** Context managers or wrappers managing database commit/rollback blocks, distributed locks, or file locks provide atomicity invariants and must be preserved.
5. **Seam Error Translation:** Transforming low-level driver exceptions (e.g., `psycopg2.OperationalError`) into domain-level exceptions (e.g., `DatabaseUnavailableError`) at subsystem boundaries decouples calling code from third-party vendor libraries. This is sound encapsulation, not surplus taxonomy.
6. **Legitimate Facades:** A facade that aggregates 15 underlying subsystem calls into 2 simple operations is a _deep_ module and represents exemplary software design.

---

## 5. Architectural Principles for Decoupling

When formulating refactoring proposals or boundaries, adhere to these fundamental principles:

### 1. Deep Modules with Narrow Interfaces (Ousterhout's Principle)

- The best modules are **deep**: they provide powerful, comprehensive functionality through a simple, minimal, and obvious interface.
- The worst modules are **shallow**: they expose large, intricate interfaces while doing very little real work under the hood.
- When decoupling subsystems, design deep interfaces that hide internal decisions (data representations, parsing details, caching) completely from callers.

### 2. Behavioral Invariants Retained

- Structural refactoring MUST preserve 100% of functional behavior, public contracts, and system invariants.
- If an architectural shift requires breaking changes to public contracts, the proposal must explicitly classify the change as breaking, enumerate affected consumers, and require operator authorization through `daw-design`.

### 3. Avoid Avoidable Allocations & Performance Regressions

- Never introduce speculative wrappers, intermediate object copies, defensive dictionary clones, or dynamic serialization layers in hot loops or performance-sensitive paths.
- Prefer boring, direct code over clever abstractions that allocate unnecessary objects.

### 4. Regression Oracle & Test Integrity

- **Tests and Comments Preservation:** Never remove existing tests, assertions, or explanatory comments during a structural untangling pass. The regression oracle must not be weakened.
- If existing tests are tightly coupled to private implementation details (mocking internal methods), mark the issue as an observation. Updating tests requires separate, explicit planning during the implementation phase (`daw-plan` / `daw-build`).

---

## 6. Structure of an Untangle Finding

When documenting structural findings, structure each observation using this deterministic template:

| Field                         | Description                                                                         |
| :---------------------------- | :---------------------------------------------------------------------------------- |
| **Finding ID & Title**        | Unique identifier (e.g., `COUP-001`) and concise descriptive name.                  |
| **Coupling Category**         | `hidden_link`, `needless_link`, or `surplus_taxonomy`.                              |
| **Locations**                 | Specific file paths and line ranges (`src/core/router.py:45-82`).                   |
| **Observed Relationship**     | Concrete evidence of the coupling (call chain, shared state, import cycle).         |
| **Consequence**               | Concrete impact on change friction, testability, blast radius, or cognitive load.   |
| **Proposed Boundary / Fix**   | Recommended structural remedy (e.g., extract deep module, narrow interface).        |
| **Alternatives & Trade-offs** | What is gained vs. lost (e.g., extra indirection vs. test isolation).               |
| **Behavior Invariants**       | Specific behavior, edge cases, and public contracts that must be preserved.         |
| **Verification Proposal**     | Specific test commands or behavioral assertions that will verify the fix.           |
| **Confidence & Coverage**     | Confidence level (`high`, `medium`, `low`) and explicit inspected scope disclosure. |

---

## 7. Downstream Module Integration

How other DAW modules interact with this reference:

- **`daw-untangle` (Primary User):** Executes read-only analysis using this taxonomy, produces structured findings, and proposes boundaries without mutating workspace files.
- **`daw-design` (Architectural Governance):** Reads this reference when evaluating subsystem boundaries, domain modeling, or resolving high-blast-radius dependencies.
- **`daw-plan` (Task Decomposition):** Consults this reference to ensure task boundaries follow genuine change seams, avoiding plans that create artificial intermediate layers or split tightly-coupled units across disjoint subagents.
- **`daw-build` (Implementation):** Follows deep module principles and minimal-diff invariants when refactoring; never removes comments or tests unasked.
- **`daw-review` (Stage 2 Technical Audit):** Audits code changes against the taxonomy to reject newly introduced surplus taxonomy, leaky abstractions, or hidden coupling before verification.
- **Parent Orchestrator (Prefinal Coupling Checkpoint):** Enforces proportional structural verification before final delivery ([§8](#prefinal-coupling-checkpoint)), reusing accepted `daw-review` passes, performing bounded patch checks, and escalating to `daw-untangle` only when boundary impact is genuinely obscure.

---

<a id="prefinal-coupling-checkpoint"></a>

## 8. Parent Prefinal Coupling Checkpoint & Proportional Governance

The parent orchestrator enforces a proportional structural coupling and boundary check **before final delivery** of any code-changing workflow. This check ensures that changes do not introduce hidden side effects, leaky abstractions, or accidental co-change entanglements across modules.

This is an **instructional procedural skill rule governing agent reasoning**, NOT a deterministic semantic enforcement hook, runtime daemon supervisor, or Claude Code Stop listener.

### 1. Proportional Scope & Route Alignment

Structural verification depth must match the risk and route of the delivered change:

- **Feature & Bugfix Routes:** Existing route-required `daw-review` already executes Stage 2 structural boundary and architectural audits. The parent orchestrator **reuses the existing accepted `daw-review` result** for the current matching artifact revision and scope. It MUST NOT execute a redundant or duplicate review pass if an accepted review already covers the current diff.
- **Patch Route:** The patch route remains strictly streamlined (`daw-build` -> `daw-verify`). The parent orchestrator performs a bounded, proportional inspection of the changed diff and directly affected interfaces. It MUST NOT mandate a new intermediate reviewer stage or invoke `daw-untangle` for localized, low-risk, or single-file fixes. If operating without an independent review stage, the parent explicitly notes the single-perspective verification fallback limitation in its acceptance record rather than claiming simulated independent acceptance.
- **Documentation & Non-Code Routes:** Tasks with zero structural code changes (docs-only, configuration descriptions, comments) record an explicit inline N/A rationale (e.g., `coupling_check: "N/A - documentation-only, no structural code changes"`) without structural analysis overhead.
- **Implementation Rail:** During construction, `daw-build` applies lightweight change-coupling self-checks (minimal diff, avoiding accidental co-change, preserving public contracts) and notes observations inline in its handoff details.

### 2. Threshold for Escalation to `daw-untangle`

Escalation to `daw-untangle` is strictly an exception, not a routine pipeline stage:

- **Escalation Criteria:** Escalate ONLY when the parent or reviewer observes **demonstrated hidden, unclear, or circular dependency impacts** across modules that cannot be reliably resolved through direct inspection of the diff and local call sites.
- **Strictly Bounded Scope:** Any escalation MUST target solely the specific affected boundary, component, or subsystem. An untangle escalation NEVER authorizes a whole-codebase scan, unsolicited architectural audit, or broad repository cleanup.
- **Read-Only Analysis Contract:** `daw-untangle` returns bounded, evidence-backed read-only analysis to the parent orchestrator. It receives NO mutation authority. An untangle output status of `pass` indicates completion of structural diagnosis, NEVER proof of runtime behavioral correctness or operational fix.

### 3. Finding Disposition, Invalidation & Authorized Corrections

When structural issues are identified:

- **Blocking vs. Out-of-Scope:**
  - **Material Structural Blockers:** Changes that break architectural boundaries, introduce circular dependencies, or violate subsystem encapsulation directly affecting the correctness, security, or stability of the change block parent final acceptance.
  - **Out-of-Scope Architectural Debt:** Pre-existing coupling, incidental refactoring opportunities, or stylistic boundary improvements are documented separately as advisory backlog observations. They MUST NOT trigger unsolicited refactoring or block acceptance of the immediate scoped fix.
- **Authorized Correction Routing:** When structural corrections are required, the parent orchestrator routes them through standard planning and implementation modules (`daw-plan` / `daw-build`) under an explicit, bounded correction scope.
- **Evidence Invalidation on Revision:** Any code modification made during correction **invalidates all affected review and runtime verification evidence** for prior revisions. The parent orchestrator must re-verify behavioral correctness and recheck the revised diff before final acceptance.
- **Applicable Route Retry & Stop Rules:** Corrective iterations follow existing applicable route retry and stop rules without inventing new fixed caps. Executed criteria that fail retain status `fail`; unexercised prerequisites or missing approvals become `blocked`.

### 4. Observability & Parent Acceptance Record

Coupling verification is recorded directly within the existing plan, handoff, or parent checkpoint records. It requires NO mandatory new files, custom schemas, or hidden storage.

- **Record Fields:** Uses existing structures, populating inline:
  - `scope`: The target paths, interfaces, and dependencies evaluated.
  - `revision`: Specific snapshot or commit identifiers inspected (e.g., `snapshot:src/auth/service.py#rev-b2`).
  - `evidence`: Concrete references (accepted `daw-review` ref, parent diff inspection summary, or `daw-untangle` finding IDs).
  - `disposition`: `accepted`, `not accepted`, or `N/A` with clear rationale.
- **Output Presentation:** Default human reporting remains concise and action-first; comprehensive JSON records remain internal to the parent orchestrator.
