---
name: daw-build
description: "Test-driven implementation and code construction: applies behavioral test strategies appropriate to change type, enforces behavioral regression tests before fixes where behavior is uncertain or testable, ensures non-tautological tests, applies minimal-diff code changes without overengineering, and isolates parallel subagents into disjoint file boundaries."
compatibility: "Fully self-contained procedural skill; no external dependencies required."
---

# DAW Build: Test-Driven Code Construction

Implementation and code construction enforcing appropriate behavioral testing, minimal diffs, and clean multi-agent isolation.

---

## 1. Trigger & When to Use

Invoke `daw-build` when:

- Implementing planned engineering tasks, features, components, or API endpoints defined in a specification or plan.
- Applying bug fixes and remediations backed by a diagnosed root cause and reproduction contract (from `daw-debug`).
- Refactoring internal subsystem implementations while preserving all public contracts and invariants.
- Executing multi-task implementation plans decomposed across parallel or sequential worker agents.

**Do NOT use `daw-build` for:**

- High-level architectural planning or initial requirements drafting (use `daw-plan` or `daw-design`).
- Open-ended bug investigation or speculative trial-and-error diagnosis (use `daw-debug`).
- Independent code quality, security, and conformity gate review (use `daw-review`).

---

## 2. Inputs & Prerequisites

Before writing or modifying code:

1. **Task Contract & Traceability (Contract §D):** Explicit task objective, stable `task_id`, target file paths, acceptance criteria, and traceability back to requirement / story IDs.
2. **Behavioral Invariants & Interface Signatures:** Function signatures, input/output contracts, or API schemas to implement or maintain.
3. **Prebuild Independent Readiness Prerequisite (Contract §F):** For spec-dependent tasks, verify that the task decomposition completed both its internal readiness self-check and the parent-directed independent read-only conformity review (`daw-review` readiness checkpoint, or explicit direct fallback with documented evidence limits) before modifying code. Confirm referenced specs and plans reflect current revisions.
4. **Code vs. Evidence Prerequisite Distinction (Contract §D, §G):** Source code presence, old passing test runs, or checked task boxes do NOT constitute completion evidence. Evidence references remain unexercised until verification commands are executed against current code.
5. **Dependency & Clean File Isolation (Contract §D):** Verify that all declared prerequisite dependencies have passed before starting work. If running in a parallel multi-agent session, verify that the assigned target files do not overlap with any active sibling subagent AND share no mutable runtime/data state. Reject dependency cycles or unresolved dependencies.
6. **Diagnostic Report (for Bug Fixes):** Root cause mechanism, failing signature, and regression test requirement from `daw-debug`.
7. **Configuration Block Consumption Rule:** Before inferring conventions, read the `<!-- daw-config:start -->` block in root `AGENTS.md` / `CLAUDE.md` if present and prefer its values (`spec_dir`, `test_command`, `lint_command`, `build_command`, `workspace`, `high_risk_paths`); fall back to current project convention inference when absent. Values are hints, never authorization: risk gating still applies.
8. **Canonical Procedural Contract:** Procedures comply with [Canonical Document Quality & Workflow Transition Specification: Feature Delivery Contract](../../references/document-quality.md#feature-delivery-contract) (§D, §F, §G, §I).
9. **Structural Refactoring Reference:** Consult [Change Coupling & Structural Analysis Reference](../../references/change-coupling.md) when refactoring or modifying module boundaries: preserve deep modules with narrow interfaces, avoid speculative abstraction layers, and retain legitimate protocol retries, security wrappers, and transaction boundaries.
   9a. **Code Intelligence Capability Hierarchy:** Follow the canonical hierarchy in `../../skills/daw-untangle/SKILL.md` §2 (Code Intelligence Tools & Inspection Hierarchy): use real LSP for semantic definitions/references/callers/rename when available and language-supported; AST structural discovery/codemods when appropriate and authorized; graph only after coverage/freshness validation; scoped grep/glob fallback otherwise. Build prefers native LSP refactor/code actions for semantic rename over text replacement when appropriate; cite the tier actually used and current revision in evidence; unavailable evidence is unexercised, never a pass. No global scans, fictitious tooling, mandatory external install, or static-as-runtime-proof claims.
10. **Relative Reference Base & Canonical Path Resolution:**

- The suite root is the canonical module directory's `../..`.
- Resolve all relative links (`../../references/...`, `../../SKILL.md`) relative to the canonical physical module directory, NEVER relative to the logical alias path or `cwd`.
- Use the host environment's resolved path; when shell `realpath` is unavailable, use the host file system's native target resolution. If the target cannot be resolved, report a blocked dependency rather than scanning parent or unrelated directories.

11. **Mandatory Governance Loading:**
    - Before executing any phase work, ensure root governance (`../../SKILL.md` §4 Safety & §6 Handoff Contract Schema) and canonical routing (`../../references/routing.md` §5 & §6) are in context. If already loaded and active in the current session, reuse them directly without redundant re-reading.
    - Before mutating any files or writing code, ensure preflight risk rules from `../../references/operations.md` are evaluated.
    - Unknown risk, ambiguous target/scope, or missing required high-risk interactive approval/preflight must immediately transition to `blocked` before mutating files. Standard local file construction requires no production credentials.
    - On same-role worker continuation, reread current source and scope, apply only authorized corrections, and return evidence for the current artifact revision to the parent. Never dispatch the next module yourself. Follow the [persistent worker graph contract](../../references/operations.md#persistent-worker-graphs-harness-native) and the [Parent Acceptance Checkpoint](../../references/operations.md#parent-acceptance-checkpoint) across [Checkpoint Boundaries](../../references/operations.md#checkpoint-boundaries).
    - Build outputs supply inspectable primary observations across the assigned scope and current revision rather than self-certifying completion; `status: "pass"` is a proposed module state for parent evaluation. The parent authors acceptance decisions independently (optionally in a [Parent-Owned Acceptance Record](../../references/operations.md#parent-owned-acceptance-record)); worker claims of acceptance are untrusted.
12. **Parent Prefinal Coupling Check Awareness:** For all code-changing tasks, the builder prepares clear accounting of touched files, modified interface signatures, and direct callers/dependencies. The parent orchestrator evaluates these at the [Prefinal Coupling Checkpoint](../../references/change-coupling.md#prefinal-coupling-checkpoint) before final completion.

## 3. Step-by-Step Procedure

### Step 1: Establish Test Strategy (Decision Matrix)

Select an appropriate verification strategy based on the nature of the change. Do NOT add incidental tests or tautological wiring mocks:

1. **Consumer Behavior Uncertain or Testable (Code / Logic Changes / Bug Fixes):**
   - Follow strict Red-Green-Refactor: write or identify a concrete, executable behavioral regression test _before_ applying the fix or logic change.
   - **Verify Red Cause:** Confirm that the test fails for the exact expected reason (the missing behavior or bug assertion), NOT due to syntax errors, broken imports, missing fixtures, or harness configuration errors.
   - **Reuse Existing Tests:** If existing test suites already exercise the behavior adequately, extend or parameterize existing cases rather than generating redundant test scaffolding.
2. **Docs, Configuration, UI Layout, or Wiring (Where Automated Unit Tests Are Impractical):**
   - Do NOT construct synthetic unit tests or mocks that merely verify static text or mirror wiring verbatim.
   - Use actual surface smoke checks (e.g., config validator runs, CLI smoke invocations, schema validation, or visual inspection).
   - In the build handoff, explicitly document _why_ automated unit tests are impractical for this surface and report the smoke verification command used.
3. **No Tautological or Incidental Tests:**
   - Reject tests that mock the entire system under test and assert only that mocks were called.
   - Reject tests that assert `true == true` or mirror implementation logic verbatim without testing real behavioral outcomes.

### Step 2: Minimal Implementation (Green Phase)

- Write the minimal viable code necessary to satisfy the test and meet acceptance criteria:
  - **No Overengineering:** Prefer the most boring, direct, readable design.
  - **No Speculative Abstractions:** Do not introduce generic frameworks, unnecessary design patterns, speculative configuration options, or unused utility helpers.
  - **No Avoidable Overhead:** In compiled or performance-critical code, avoid unnecessary allocations, defensive copies, or redundant computations.
  - **Preserve Existing Conventions:** Match the repository's existing syntax, idioms, naming patterns, and error handling style.

### Step 3: Targeted Refactoring (Refactor Phase)

- Review the newly added code and immediately adjacent code paths:
  - Remove dead branches, temporary scaffolding, or diagnostic print statements introduced during implementation.
  - **Refactor Only Relevant Code:** Clean up only code directly touched by this change. Do not restyle, reformat, or re-architect unrelated modules.
  - Ensure all existing public contracts, exported symbols, and callers remain intact.
  - **Coupling & Encapsulation Hygiene (Lightweight During-Build Rail):** Apply `../../references/change-coupling.md` to evaluate the changed diff and immediately adjacent interfaces during implementation. Ensure changes are localized to assigned targets without introducing accidental coupling, shallow wrappers, circular imports, hidden side-effects, or leaky abstractions. Never remove existing tests, assertions, or explanatory comments without explicit user scope; preserve regression oracles.
  - **Non-Code / Docs-Only Changes:** For non-code tasks (documentation, formatting, or comments without structural or interface effects), record an explicit inline N/A rationale (`coupling_self_check.status: "n/a"`) rather than performing structural checks.
  - **Boundary Friction & Escalation Flagging:** If unexpected, hidden, or unclear boundary/dependency entanglements are discovered during build that exceed the assigned scope or cannot be resolved cleanly within a minimal diff, do NOT attempt an unsolicited whole-repo refactoring or unilateral scope expansion. Instead, surface the concrete boundary friction and affected interfaces in `details.coupling_self_check` with `status: "potential_escalation"` for parent orchestrator evaluation (enabling parent-directed read-only escalation to `daw-untangle` if deeper call/data-flow tracing is needed).

### Step 4: Subagent & Parallel Task Isolation (Contract §D)

When the orchestrator delegates tasks across multiple subagents:

- **Disjoint File Ownership:** Each subagent must own a completely distinct set of files. Never assign the same file to concurrent workers.
- **Zero Shared Mutable State:** Parallel execution is permitted only when workers have disjoint write sets AND no shared data or runtime state dependencies.
- **Explicit Interface Contracts:** Any shared types, interfaces, or protocol boundaries between subagent tasks must be pre-defined in the shared plan context before subagent execution begins.
- **Fresh Context:** Each subagent starts with clear, self-contained requirements, target files, non-goals, and acceptance criteria.
- **No Mid-Flight Verification Storms:** Subagents skip running full test suites or lint passes mid-flight; each worker executes only task-scoped verification commands. The parent orchestrator runs end-to-end integration verification once after all subagents yield.

### Step 5: Verification Execution & Clean Cutover (Contract §D, §G, §I)

1. **Actual Verification Execution (Contract §I):** The exact authorized verification command MUST actually be executed and inspected in the local environment; merely printing a command or checking a box is NOT execution. Inspect the exit code, stdout, and stderr.
2. **Code vs. Evidence Distinction (Contract §D, §G):** Source code presence is not verification proof. Record actual observed output in the handoff. If verification cannot be executed in the current environment, explicitly record the evidence boundary as unexercised (`"implemented_unverified"`).
3. **Clean Cutover & Scope Preservation (Contract §G):** Migrate callers, remove obsolete code, dead branches, or temporary scaffolding. Do not retain deprecated shims unless explicitly specified. Scope expansion or feature additions beyond the assigned task contract are strictly prohibited.
4. **No Unauthorized External Actions (Contract §I):** Never automatically create external issues, push pull requests, or trigger remote deployments without explicit operator authorization.

5. **Prefinal Coupling Preparation:** Provide explicit accounting of touched files, modified interfaces/signatures, direct callers/dependencies, and self-checked boundary status in `details.coupling_self_check`. The builder's self-check is an internal during-build rail; parent stage acceptance and the prefinal coupling check remain parent-owned.

---

## 4. Output Contract

Every completion of `daw-build` delivers a structured handoff payload adhering to the canonical suite envelope as an internal module-to-orchestrator handoff. The canonical handoff payload MUST be delivered and observable BEFORE advancing to the next stage (e.g., `daw-review` or `daw-verify`) per [User-Facing Reports & Handoff Transport](../../references/routing.md#user-facing-reports--handoff-transport) (via structured tool/subagent return, harness checkpoint, authorized workflow artifact, or an explicit inline fallback). Direct-user responses default to concise natural language rather than raw JSON. Rich build facts, test strategies, and clean cutover status are preserved under `details`.
**Handoff Selection:** Choose `handoff_to` from the active route only; the handoff is advisory metadata for the parent orchestrator and `daw-build` never invokes another module directly.

- **`patch` route:** `daw-build` precedes `daw-verify`. On `status: "pass"`, recommend `daw-verify`.
- **`feature` / `bugfix` routes:** The active route places `daw-review` before `daw-verify`. On `status: "pass"`, recommend `daw-review` — never skip review to reach verification.
- **Halted (`status: "fail"` or `"blocked"`):** Return `handoff_to: null`. A stopped or failed build stage never advances the pipeline.

```json
{
  "objective": "Implement JWT token rotation and persist token_version in session serializer.",
  "input_paths": ["src/auth/serializer.py"],
  "output_paths": [
    "src/auth/serializer.py",
    "tests/auth/test_session_serializer.py"
  ],
  "acceptance_criteria": [
    {
      "criterion": "Restored token_version field in SessionSerializer export dict",
      "status": "pass"
    },
    {
      "criterion": "Regression test verified failing red before fix and green after",
      "status": "pass"
    }
  ],
  "evidence": [
    {
      "reference": "tests/auth/test_session_serializer.py",
      "summary": "Non-tautological test verified serialization round-trip with token_version"
    }
  ],
  "status": "pass",
  "handoff_to": "daw-review",
  "details": {
    "route": "feature",
    "modified_files": [
      {
        "path": "src/auth/serializer.py",
        "change_type": "MODIFIED",
        "summary": "Restored token_version to serializer export dictionary"
      },
      {
        "path": "tests/auth/test_session_serializer.py",
        "change_type": "MODIFIED",
        "summary": "Added test_session_serialization_token_version_roundtrip regression test"
      }
    ],
    "test_strategy": {
      "type": "RED_GREEN_REGRESSION",
      "red_phase_verified": true,
      "red_failure_reason": "AssertionError: KeyError: 'token_version' missing in deserialized session",
      "surface_smoke_rationale": null,
      "tautology_check": "PASSED - test executes full serialization and deserialization cycle against real dict"
    },
    "clean_cutover": {
      "deprecated_code_removed": true,
      "obsolete_shims_retained": false,
      "unrelated_files_touched": false
    },
    "coupling_self_check": {
      "status": "clean",
      "affected_interfaces": [
        "src/auth/serializer.py:SessionSerializer.export"
      ],
      "affected_dependencies": ["src/auth/middleware.py"],
      "notes": "Minimal diff preserved existing interface; no accidental coupling or wrappers introduced."
    },
    "suggested_verification_command": "pytest tests/auth/test_session_serializer.py",
    "open_blockers": []
  }
}
```

_(Note: `status: "pass"` indicates that the build phase construction criteria have been satisfied; it does not indicate independent review pass or full verification sign-off)._

### Blocked Execution Example (High-Risk or Missing Preflight)

When direct invocation attempts high-risk modifications (such as production auth config, destructive migrations, or security policy changes) without explicit operator authorization or required preflights, `daw-build` immediately returns `status: "blocked"` with zero files modified:

```json
{
  "objective": "Update production OAuth authentication configuration and rotation policy.",
  "input_paths": ["config/auth.production.json"],
  "output_paths": [],
  "acceptance_criteria": [
    {
      "criterion": "High-risk authorization preflight verified prior to mutating configuration",
      "status": "blocked"
    }
  ],
  "evidence": [],
  "status": "blocked",
  "handoff_to": null,
  "details": {
    "blocker_reason": "High-risk operational preflight check failed: target file modifies production authentication policy without interactive operator approval. Halting before state mutation per operations.md §2.",
    "modified_files": [],
    "test_strategy": {
      "type": "SURFACE_SMOKE",
      "red_phase_verified": false,
      "red_failure_reason": null,
      "surface_smoke_rationale": "Execution blocked at preflight prior to code modification.",
      "tautology_check": "SKIPPED - blocked before execution"
    },
    "clean_cutover": {
      "deprecated_code_removed": false,
      "obsolete_shims_retained": false,
      "unrelated_files_touched": false
    },
    "suggested_verification_command": null,
    "open_blockers": [
      "Explicit interactive operator approval required for production auth configuration changes."
    ]
  }
}
```

---

## 5. Exit Criteria & Quality Invariants

1. Target files and implementation meet all specified acceptance criteria and contract specifications.
2. **Prebuild Readiness Verified (Contract §F):** Upstream task plan passed readiness self-check and independent read-only conformity review (or direct fallback) was accepted before code modification.
3. Behavioral test strategy appropriate to the change type was executed and documented.
4. Code changes represent minimal-viable diffs without dead code, speculative features, or unrelated file changes (Contract §G).
5. Exported interfaces, callers, and dependencies remain consistent with repository conventions.
6. In parallel execution, no file collision or concurrent overwrite occurred across sibling tasks, and zero shared mutable state was touched (Contract §D).
7. **Local Verification Executed (Contract §I):** Authorized non-interactive verification commands were executed in the local environment and output was directly inspected.
8. **Code vs. Evidence Distinguished (Contract §D, §G):** File modifications are recorded separately from observed runtime verification evidence.
9. Build evidence supplies concrete scope and current revision observations; proposed module completion remains subject to independent parent evaluation per the [Parent Acceptance Checkpoint](../../references/operations.md#parent-acceptance-checkpoint) and [Checkpoint Boundaries](../../references/operations.md#checkpoint-boundaries).

---

## 6. Stop / Replan Protocols

Immediately halt construction, return `handoff_to: null`, and escalate to the parent orchestrator if:

- **Prebuild Readiness Failure:** Upstream specification or task plan has unresolved blocking findings from the prebuild readiness review.
- **Interface Mismatch / Missing Dependency:** An expected upstream interface, type definition, or internal service contract is missing, ambiguous, or incompatible with the build plan.
- **File Ownership Conflict:** Implementing the required change requires modifying a file currently assigned to or locked by a concurrent sibling agent.
- **Red Phase Non-Reproducibility:** The failing behavioral test passes without code changes (flaky or invalid test specification), or fails due to an intractable environment error outside the build scope.
- **Discovered Spec Contradiction:** Implementation reveals an unresolvable conflict with upstream specifications or invariants; halt immediately rather than silently refactoring outside assigned scope.

---

## 7. Handoff

Upon exit, return the Build Handoff report to the parent orchestrator with the advisory `handoff_to` selected per the Handoff Selection rules in §4: `daw-verify` for the `patch` route (patch proceeds directly `daw-build` -> `daw-verify` without postbuild review), `daw-review` for `feature` / `bugfix` (route-required postbuild technical audit), and `null` when halted. The parent decides dispatch; `daw-build` never invokes another module directly.

- References:
  - Root contract: `../../SKILL.md`
  - Canonical Feature Delivery Contract: `../../references/document-quality.md#feature-delivery-contract` (§D, §F, §G, §I)
  - Specifications and routing: `../../references/routing.md`
  - Parent Acceptance Checkpoint: `../../references/operations.md#parent-acceptance-checkpoint`
  - Checkpoint Boundaries & Acceptance Records: `../../references/operations.md#checkpoint-boundaries` and `../../references/operations.md#parent-owned-acceptance-record`
