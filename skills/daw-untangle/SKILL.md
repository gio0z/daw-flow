---
name: daw-untangle
description: "Read-only structural analysis and change-coupling investigation: maps hidden dependencies, needless wrappers, and shotgun surgery risks to propose clean module boundaries without workspace mutations."
---

# DAW Untangle (`daw-untangle`)

The untangle module performs deterministic, read-only structural analysis and change-coupling diagnostics. It investigates code friction, answers the question _"Should these pieces change together?"_, identifies architectural entanglement (hidden links, needless links, and surplus taxonomy), and formulates bounded refactoring proposals and deep module boundaries without mutating files or running test suites.

**Invariant:** `daw-untangle` is strictly read-only. It investigates, diagnoses, and formulates structural boundaries with grounded codebase evidence, but NEVER mutates workspace files, runs builds/tests, or executes code modifications. Direct refactoring execution is handled by downstream implementation stages (`daw-plan` / `daw-build`) under explicit operator authorization.

---

## 1. Trigger & Scope

### When to Invoke

- **Explicit Structural Investigation:** Answering inquiries regarding coupling, circular dependencies, shotgun surgery risks, or architectural boundary friction.
- **Change-Coupling Diagnosis:** Investigating whether two or more subsystems or modules should change together or be decoupled.
- **Pre-Refactoring Scoping:** Preparing for structural refactoring by diagnosing coupling roots, hidden dependencies, and invariant requirements before authoring implementation plans or mutating code.
- **First Stage of the `refactor` Route:** On the `refactor` route, `daw-untangle` is Stage 1: it outputs the target structure and the safe step sequence for `daw-plan` (see [Behavior-Preserving Refactor Protocol](../../references/developer-lifecycle.md#4-behavior-preserving-refactor-protocol)). It remains strictly read-only — the sequence is a proposal, never executed here.
- **Subsystem Boundary Audits:** Auditing an authorized named component or subsystem for leaky abstractions, mega-context passing, or shallow module layering.

### Precedence in Suite Pipeline

`daw-untangle` occupies a distinct position in the suite routing hierarchy:

1. `review` (Stage 1 & 2 diff review of proposed/implemented changes).
2. `untangle` (Explicit read-only structural coupling & boundary analysis).
3. `ask` (General read-only conversational advice & Socratic sounding board).
4. `setup` / `bootstrap` / `adopt` / `feature` / `patch` / `fix` (Execution & lifecycle pipelines).

### Non-Goals & Invariants

- **Strictly Read-Only Execution:** Never creates, edits, or deletes files. Zero modifications to source code, specifications, configuration, comments, tests, or git state.
- **No Test / Build / Benchmark Execution:** Does not run test suites, build tools, performance benchmarks, or mutating scripts. Evaluates static code structure and recorded evidence only.
- **Bounded Investigation vs. Unsolicited Repo Cleanup:** Investigates ONLY the authorized named area, subsystem, or demonstrated boundary friction. When escalated from a parent prefinal coupling check, analysis is strictly scoped to the affected diff and directly adjacent interfaces—NEVER expanding into an unsolicited whole-codebase scan or cleanup wave.
- **Pass Analysis is NOT Runtime Proof:** A `status: "pass"` indicates that the bounded structural analysis was successfully completed and grounded in observable codebase evidence. It does NOT provide proof of runtime execution, system correctness, or test passing (which require `daw-verify`).
- **Finding Disposition & No Unsolicited Refactoring:** Material correctness, security, or domain invariant-breaking coupling findings block parent final acceptance until addressed. Unrelated structural improvements or pre-existing architectural debt outside the authorized scope must be reported separately as informational observations; they MUST NOT trigger an unsolicited refactoring campaign.
- **Correction Routing & Evidence Invalidation:** `daw-untangle` never mutates code or executes fixes directly. Authorized structural corrections must be routed through standard planning and build modules (`daw-plan` -> `daw-build`). Any resulting code modifications invalidate affected prior review and runtime evidence, requiring the parent to re-evaluate the current diff before final completion.
- **Refactoring Implementation is NOT Read-Only Untangle:** If a user directly requests code refactoring or implementation, that request routes through the standard execution pipeline (`daw-plan` -> `daw-build` -> `daw-verify` or `daw-design`), NOT silently hijacked into read-only `daw-untangle`. `daw-untangle` is chosen when structural analysis is explicitly requested.
- **No Preflight Approval Ceremony:** Because `daw-untangle` is strictly read-only and performs zero mutations, it does NOT require clean git trees, production credentials, or high-risk confirmation. Preflight confirms read-only scope and proceeds immediately.
- **Negative Evidence Discipline:** "No callers observed in repository" does NOT constitute absolute proof of dead code. Inspected coverage and potential dynamic entrypoints must be explicitly disclosed.
- **Preserve Legitimate Architectural Resilience:** Never flag legitimate protocol retries, security wrappers, transaction boundaries, or seam error translations as surplus taxonomy.
- **No Speculative Abstraction:** Recommends deep modules with narrow interfaces and boring, maintainable designs. Avoids recommending speculative abstractions or intermediate layers that incur memory allocation or runtime performance penalties.
- **Advisory Handoffs Only:** Sets `handoff_to: null` by default. Advisory handoffs to `daw-design` (for unsettled architecture) or `daw-plan` (for settled concrete task decomposition) never invoke downstream modules directly or grant mutation authority.

---

## 2. Inputs & Prerequisites

1. **Target Scope / Inquiry:**
   - Authorized named subsystem, directory, file list, or explicitly requested repository scope.
   - Specific architectural question, coupling concern, or refactoring intent.
2. **Workspace Context (Read-Only):**
   - Repository source files, package manifests, build definitions, and configuration files.
   - Existing specifications, architectural decision records (`docs/specs/`, `docs/adr/`), and domain models.
   - Git log and change history (to evaluate historical co-change patterns where relevant).
3. **Relative Reference Base & Canonical Path Resolution:**
   - When loaded via symlink or alias (e.g. `~/.agents/skills/daw-untangle`), resolve THIS `SKILL.md` symlink to its physical/canonical target file first.
   - The suite root is the canonical module directory's `../..`.
   - Resolve all relative links (`../../references/...`, `../../SKILL.md`) relative to the canonical physical module directory, NEVER relative to the logical alias path or `cwd`.
   - Use the host environment's resolved path; when shell `realpath` is unavailable, use the host file system's native target resolution. If the target cannot be resolved, report a blocked dependency rather than scanning parent or unrelated directories.
4. **Mandatory Governance Loading:**
   - Before executing structural analysis, ensure root governance (`../../SKILL.md` §4 Safety & §6 Handoff Contract Schema) and canonical routing (`../../references/routing.md` §5 & §6) are in context. If already active in the current session, reuse them directly without redundant re-reading.
   - `daw-untangle` is strictly read-only. Preflight evaluation confirms read-only scope. Dirty git working trees are explicitly accepted; no clean tree is required.
5. **Code Intelligence Tools & Inspection Hierarchy:**

   ### Code Intelligence Capability Hierarchy
   - **Language Server Protocol (LSP) First (Semantic):** Prefer real LSP `definitions`, `type_definitions`, `references`, `implementations`, and callers for semantic definitions, references, callers, and rename when LSP is configured, active, and supports the target language. Verify results against current-revision source reads; an unavailable/unsupported LSP is an honest fallback trigger, never a pass.
   - **AST Structural Discovery / Codemods:** Use AST-aware structural search and codemods (e.g. AST grep/edit patterns) for structural discovery and authorized mechanical codemods when pattern shape — not just literal text — defines the target. Do not invent AST tooling; fall back when unavailable.
   - **Graph Coverage / Freshness Validation:** When graph tools are available, validate index coverage and freshness (timestamps/revision) before trusting edges; verify every cited symbol against current-revision source. Stale or incomplete graph evidence is scoped as fallback, not proof.
   - **Literal / Coverage Fallback:** Use scoped `grep`/`glob` literal search plus targeted line-range `read` for literal text, coverage-gap checks, and when higher tiers are unavailable or unsupported. Scope stays within the authorized area; no global scans.
   - **Read-Only Mutation Ban:** `daw-untangle` never applies code actions, renames, codemods, or any mutation — even when LSP/AST support them. It only proposes boundaries/invariants for `daw-plan`/`daw-build`. No fictitious tooling, no mandatory external install, and no static result claims runtime proof.

6. **Canonical Supporting Reference:**
   - Read [Change Coupling & Structural Analysis Reference](../../references/change-coupling.md) for the canonical coupling taxonomy, legitimate pattern catalog, and deep module principles.

---

## 3. Step-by-Step Procedure

```
┌────────────────────────────────────────────────────────────────────────┐
│                        daw-untangle Procedure                          │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Intake, Scope Boundary & Read-Only Preflight                        │
│    • Validate authorized scope (named area vs. explicit repo)          │
│    • Confirm read-only operation (zero mutations, zero script runs)     │
│    • Identify available code intelligence (LSP / graph / static grep)  │
├────────────────────────────────────────────────────────────────────────┤
│ 2. Dependency Mapping & Change-Coupling Diagnostics                    │
│    • Ask: "Should these pieces change together?"                       │
│    • Trace actual callers, references, shared state, and imports       │
│    • Apply Taxonomy: Hidden Links | Needless Links | Surplus Taxonomy  │
│    • Preserve legitimate retries, security wrappers, and transactions  │
│    • Disclose inspected coverage; protect dynamic/public entrypoints   │
├────────────────────────────────────────────────────────────────────────┤
│ 3. Synthesis, Trade-offs & Solution Formulation                        │
│    • Design deep modules with narrow interfaces (Ousterhout)           │
│    • Formulate behavioral invariants & verification proposals          │
│    • Evaluate trade-offs (allocations, complexity, maintainability)    │
│    • Rank genuine impact (no vanity counts); log decisions             │
├────────────────────────────────────────────────────────────────────────┤
│ 4. Downstream Readiness & Handoff Preparation                          │
│    • If blocked by material external unknowns, flag status "blocked"   │
│    • Set handoff_to: null (advisory daw-design or daw-plan optional)   │
│    • Deliver canonical JSON envelope + clean human report              │
└────────────────────────────────────────────────────────────────────────┘
```

### Step 1: Intake, Scope Boundary & Read-Only Preflight

1. **Scope Boundary Enforcement:**
   - Restrict analysis strictly to the authorized target area (e.g., `src/auth/`, `services/billing/`, or explicit whole-repo scope).
   - If the request is ambiguous, inspect the target files first; clarify only material external boundaries or trade-offs that cannot be discovered from code facts.
2. **Read-Only Preflight Confirmation:**
   - Confirm that no files will be written, edited, or deleted.
   - Confirm that no test runners, compilers, linters, or workspace mutation commands will be executed.
   - Dirty or uncommitted working trees are preserved as-is.
3. **Code Intelligence Selection:**
   - Check if language servers or graph indexes are available. If not, establish a targeted static search plan using `glob`, `grep`, and `read`.

### Step 2: Dependency Mapping & Change-Coupling Diagnostics

1. **The Core Question:**
   - Evaluate each boundary with: _"Should these pieces change together?"_
   - Distinguish essential co-change (shared domain invariants, protocol synchronization) from accidental co-change (leaky implementation details, shared untyped dictionary bags).
2. **Taxonomy Classification:**
   - **Hidden Links:**
     - _Temporal Environment Coupling:_ Order-dependent `os.environ` mutations where Module A must load or set keys before Module B can read them.
     - _Duplicate Business Logic / Pricing Logic:_ Duplicating business formulas (e.g. pricing calculations, discount logic, tax rules) across multiple callers rather than centralizing a single authoritative domain engine.
     - _Shared Mutable State:_ Global mutable dictionaries or module singletons accessed across subsystems.
   - **Needless Links:** Mega-context objects passed where single fields suffice, tight coupling to concrete database cursors or internal ORM models, and circular import cycles.
   - **Surplus Taxonomy:** Shallow modules where interfaces are larger than implementations, single-use speculative interfaces, and gratuitous pass-through layers (`Controller -> Facade -> Service -> Manager -> Handler`).
3. **Preserve Legitimate Resilience Patterns (Explicit Non-Findings):**
   - Explicitly verify that identified wrappers or layers are not legitimate patterns:
     - _Protocol retries & exponential backoff:_ E.g., handling HTTP 429 Too Many Requests, rate limits, or transient connection drops. Standard retry decorators or backoff wrappers are essential resilience mechanisms and MUST NOT be flagged as surplus taxonomy or needless wrappers.
     - _Security & authentication guards:_ E.g., `@require_permission("orders:write")`, JWT verification, or CSRF middleware. These represent critical perimeter security boundaries and MUST NOT be flattened or flagged as unnecessary indirection.
     - _Transaction boundaries:_ Atomic commit/rollback blocks and resource lifecycles must be protected.
     - _Seam error translation:_ Catching library exceptions and re-raising typed domain exceptions at subsystem boundaries is correct encapsulation.
4. **Negative Evidence & Dynamic Entrypoint Protection:**
   - If a symbol appears to have zero callers in the repository, state inspected search boundaries explicitly (e.g., "Grep search for `TokenRevocationService` across `src/` yielded 0 call sites").
   - Explicitly protect dynamic entrypoints: plugins or handlers dynamically loaded via configuration strings or `importlib.import_module()` (e.g. plugin registries) have zero static call sites in application code but are actively used; never classify them as dead code from lack of direct static callers alone.

### Step 3: Synthesis, Trade-offs & Solution Formulation

1. **Deep Module Design:**
   - Formulate proposed refactoring boundaries favoring deep modules: simple, minimal interfaces that encapsulate substantial internal complexity.
   - Eliminate shallow intermediate wrappers rather than adding new ones.
2. **Behavior Invariants & Regression Safety:**
   - Identify explicit behavioral invariants that must remain unchanged downstream.
   - Formulate concrete verification proposals (suggested test commands or behavioral scenarios) for downstream execution.
   - Invariant: Never propose deleting test suites or assertions. Regression oracles must remain intact.
3. **Trade-Off & Performance Evaluation:**
   - Evaluate allocation impact: avoid proposing designs that introduce object allocations, defensive copies, or serialization overhead in hot paths.
   - Prefer boring, direct code over complex meta-programming.
4. **Impact Ranking & Decision Logging:**
   - Rank findings by genuine architectural impact and maintenance risk; avoid manufactured "vanity counts."
   - Record architectural trade-offs in `details.decision_log` within the structured return payload (no file writes).
5. **Valid "No Findings" Pass:**
   - If the target subsystem is already well-decoupled, modular, and possesses clean boundaries, return `status: "pass"` with verified coverage details. A clean pass with zero findings is completely valid; never manufacture artificial refactoring issues.

6. **Zero Target Execution & No Automatic Transformation:**
   - Structural analysis evaluates static code structure and recorded evidence without executing target code, running test suites, or applying automatic code rewrites.
   - All proposals articulate boundary designs, behavioral invariants, and fix trade-offs for downstream execution by `daw-plan`/`daw-build`.

### Step 4: Downstream Readiness & Handoff Preparation

1. **Readiness Evaluation & Pass Semantics:**
   - `status: "pass"` indicates a successfully completed, bounded structural analysis grounded in codebase evidence, even if unresolved downstream design choices or proposal trade-offs remain open for subsequent planning.
   - Scoped trade-offs, design alternatives, and open questions belong in `details.decision_log` and `details.unknowns`, NOT blanket `status: "blocked"`. Ordinary proposal uncertainty does not block a completed analysis.
   - Reserve `status: "blocked"` strictly for situations where missing essential repository facts or inaccessible scope prevent completing the requested analysis itself.
2. **Advisory Stage Suggestion:**
   - Set `handoff_to: null` by default.
   - If recommending next steps for operator consideration:
     - Suggest `daw-design` if high-level architectural trade-offs, breaking public contracts, or multi-subsystem boundaries remain unsettled.
     - Suggest `daw-plan` if the proposed module boundary is settled, bounded, and ready for concrete implementation task decomposition.
3. **Output Delivery Separation & Human Output Policy:**
   - When directly answering a user with no downstream stage transition, provide a concise, grounded human report in natural language only. Do NOT append raw JSON envelopes, schema examples, or extra status lines to conversational user replies.
   - Complete canonical JSON handoffs are delivered on actual module-to-parent tool/subagent returns.
   - Inline JSON fallback checkpoints are used ONLY when real pre-transition observability across workflow stages is needed, never on every user-facing response.

---

## 4. Output Contract

Use [routing §5: Canonical Module Handoff Contract](../../references/routing.md#5-canonical-module-handoff-contract) for the complete outer JSON schema and transport. Deliver the actual, inspectable envelope on module-to-parent returns and before downstream transitions. With no downstream transition, answer a direct user in concise grounded natural language only; use an inline checkpoint only for real pre-transition observability, never unrequested transport files.

### Canonical Envelope Schema

The outer schema is defined only in routing §5. Preserve the following module-specific contract under `details`; empty findings are valid when supported by disclosed coverage:

- `inspected_scope`: `authorized_target`, `coverage`, and actual `tools_used`, including inspected boundaries and dynamic/public entrypoint limits.
- `findings`: each includes `id`, `title`, `category` (`hidden_link`, `needless_link`, or `surplus_taxonomy`), `locations`, `observed_relationship`, `consequence`, `proposed_boundary`, `tradeoffs`, `behavior_invariants`, `verification_proposal`, and `confidence`.
- `decision_log`: `topic`, `rationale`, and `alternatives_considered`, including legitimate resilience patterns checked and preserved as non-findings.
- `dependencies`, `invariants`, and `non_goals`: scoped external/cross-subsystem links, required behavior, and exclusions.
- `proposed_change`: `summary`, `boundary`, and affected files/consumers in `impact`; proposals grant no execution authority.
- `target_structure` (refactor route): the proposed module boundary — modules created/merged/split, new public interfaces, and invariants preserved.
- `safe_step_sequence` (refactor route): ordered structural-only steps (rename, extract, move, split) for `daw-plan`, each with files touched, the behavior-preservation oracle (characterization probe) expected before/after, and the rollback point. Each step changes structure only; no step bundles a behavior change.
- `verification_plan.suggested_checks`: checks for downstream execution, never represented as exercised by untangle.
- `unknowns`: unresolved facts, downstream design choices, and qualified negative evidence; distinguish analysis-blocking gaps from ordinary proposal uncertainty.

### Important Status & Boundary Rules

- **`status: "pass"`:** Indicates that the bounded structural analysis was successfully completed and grounded in observable codebase evidence. Ordinary proposal uncertainty, trade-offs, or open downstream design choices do not block a pass; they are recorded under `details.unknowns` or `details.decision_log`. It does NOT imply that code was refactored, that tests passed, that runtime behavior was verified, or that the parent orchestrator has accepted the proposal.
- **No Competing Status:** The top-level `status` field is the sole authoritative verdict. Do not include duplicate or competing status fields (such as `analysis_verdict`) inside `details`.
- **`output_paths: []`:** Because `daw-untangle` is strictly read-only, `output_paths` is ALWAYS empty.
- **`handoff_to`:** Defaults to `null`. May include an advisory string (`"daw-design"` or `"daw-plan"`) to indicate the recommended subsequent stage for the orchestrator, but never directly invokes that stage or grants mutation authority.

### Concrete Production Example

Compact hypothetical `details` only (not a complete handoff or evidence of an actual inspection):

```json
{
  "inspected_scope": {
    "authorized_target": "src/auth and src/user",
    "coverage": "Inspected session.py, tokens.py, middleware.py, user/service.py, and their references. Checked configured middleware bindings; third-party consumers remain outside coverage.",
    "tools_used": ["grep", "read"]
  },
  "findings": [
    {
      "id": "COUP-001",
      "title": "Shared mutable session dictionary bypasses lifecycle validation",
      "category": "hidden_link",
      "locations": ["src/auth/session.py:12-25", "src/user/service.py:88-102"],
      "observed_relationship": "UserService directly mutates GLOBAL_SESSION_STORE owned by session.py.",
      "consequence": "Session lifecycle validation is bypassed during user deactivation.",
      "proposed_boundary": "Expose revoke_user_sessions(user_id) through SessionManager; keep its dictionary private.",
      "tradeoffs": "Adds one domain method and migrates callers; removes direct state sharing.",
      "behavior_invariants": [
        "Immediately revoke active refresh tokens",
        "Preserve transaction and concurrency boundaries"
      ],
      "verification_proposal": "pytest tests/auth/test_session_lifecycle.py tests/user/test_user_service.py",
      "confidence": "high"
    }
  ],
  "decision_log": [
    {
      "topic": "Retain AuthMiddleware error translation",
      "rationale": "Observed PyJWTError-to-401 translation is a legitimate seam boundary, not surplus taxonomy.",
      "alternatives_considered": "Removing it would leak library exceptions to clients."
    }
  ],
  "dependencies": ["PyJWT", "FastAPI middleware bindings"],
  "invariants": [
    "Expired tokens still produce HTTP 401",
    "Public login schema remains unchanged"
  ],
  "proposed_change": {
    "summary": "Decouple UserService from session storage internals.",
    "boundary": "SessionManager owns session mutation behind a user_id-based API.",
    "impact": "src/auth/session.py and src/user/service.py and their consumers"
  },
  "verification_plan": {
    "suggested_checks": ["pytest tests/auth/ tests/user/"]
  },
  "non_goals": ["Redis migration", "User database model refactoring"],
  "unknowns": [
    "No direct external callers observed within inspected repository scope; third-party usage is not disproven."
  ]
}
```

---

## 5. Exit Criteria & Safety Invariants

Before finalizing an untangle run, verify the following exit criteria:

- [ ] **Strict Read-Only Verification:** Zero files created, modified, or deleted in the workspace.
- [ ] **No Execution Mutations:** Zero test suites, compilers, benchmarks, or mutating scripts executed.
- [ ] **Grounded Evidence:** All findings cite exact file paths, line ranges, and observed dependency relationships.
- [ ] **Taxonomy Applied:** Findings are categorized into `hidden_link`, `needless_link`, or `surplus_taxonomy`.
- [ ] **Resilience Patterns Preserved:** Protocol retries, security wrappers, transaction boundaries, and seam error translations are preserved.
- [ ] **Negative Evidence Qualified:** Inspected coverage disclosed; no unqualified "dead code" assertions made for potential dynamic entrypoints.
- [ ] **Deep Modules Favored:** Proposed boundaries prioritize deep modules with narrow interfaces over speculative abstraction layers.
- [ ] **Canonical Envelope Delivered:** Complete JSON envelope delivered via primary tool/subagent return.
- [ ] **Clean Human Presentation:** Direct-user response delivered in professional natural language without robotic JSON dumps.

---

## 6. Stop / Replan Triggers

- **Action / Implementation Intent Expressed:** If the operator requests immediate code refactoring during an untangle consultation, halt read-only mode and output an advisory handoff to `daw-plan` or `daw-design`. Do not begin editing files inside `daw-untangle`.
- **Scope Ambiguity / Unbounded Workspace:** If the requested boundary is completely undefined and cannot be inferred, ask one focused scoping question to establish the authorized target area using the [canonical native clarification transport](../../references/grilling.md#native-interactive-clarification-transport-canonical-rule): use the actually exposed harness tool/schema; never invent one; cancellation or an unanswered question remains unresolved, never consent; plain-text fallback is permitted only when no native interactive question tool is exposed or available.
- **Uninspected External Consumers:** If code intelligence reveals that a target subsystem is exposed as an external library API with unknown third-party callers, record the boundary as an explicit unknown under `details.unknowns` and mark `status: "blocked"` if safe refactoring cannot be formulated without external requirements.

---

## 7. Handoff Protocol

- **To `daw-design`:** When the proposed restructuring involves high-level architectural trade-offs, breaking API changes, or cross-subsystem contracts requiring formal specification updates or operator decision gating.
- **To `daw-plan`:** When the structural diagnosis is complete, module boundaries are settled, and the task is ready for concrete, ordered file-by-file implementation task decomposition.
- **To `daw-plan` (refactor route):** When `daw-untangle` is Stage 1 of the `refactor` route, hand off `target_structure` and `safe_step_sequence` to `daw-plan` for decomposition into behavior-preserving tasks. The handoff stays advisory and read-only; `daw-untangle` never executes steps or grants mutation authority.
- **To Orchestrator / Operator:** Return the canonical handoff envelope with `handoff_to: null`. The orchestrator or operator evaluates the findings and explicitly authorizes downstream execution.

_Reference Link:_ See [Change Coupling Reference](../../references/change-coupling.md), [Shared Routing Contract](../../references/routing.md), and [Parent Specification](../../SKILL.md).
