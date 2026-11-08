---
name: daw-build
description: "Test-driven implementation and code construction: applies behavioral test strategies appropriate to change type, enforces behavioral regression tests before fixes where behavior is uncertain or testable, ensures non-tautological tests, applies minimal-diff code changes without overengineering, isolates parallel subagents into disjoint file boundaries, and executes refactor/maintain/spike lifecycle modes (behavior-preserving structural edits, dependency upgrades with lockfile fidelity, throwaway spike prototypes in isolated worktrees)."
compatibility: "Fully self-contained procedural skill; no external dependencies required."
---

# DAW Build: Test-Driven Code Construction

Implementation and code construction enforcing appropriate behavioral testing, minimal diffs, and clean multi-agent isolation.

---

## 1. Trigger & When to Use

Invoke `daw-build` when:

- Implementing planned engineering tasks, features, components, or API endpoints defined in a specification or plan.
- Applying bug fixes and remediations backed by a diagnosed root cause and reproduction contract (from `daw-debug`).
- Executing the `refactor` route: behavior-preserving structural changes only, with characterization oracles first and no behavior change (see [Behavior-Preserving Refactor Protocol](../../references/developer-lifecycle.md#4-behavior-preserving-refactor-protocol)).
- Executing the `maintain` route: dependency/toolchain upgrades, deprecation removal, and version migrations, one dependency group at a time with the lockfile committed (see [Dependency & Maintenance Upgrade Protocol](../../references/developer-lifecycle.md#5-dependency--maintenance-upgrade-protocol)).
- Executing the `spike` route: throwaway prototypes in an isolated worktree to resolve technical uncertainty; never merged (see [Spike Protocol](../../references/developer-lifecycle.md#3-spike-protocol)).
- Executing multi-task implementation plans decomposed across parallel or sequential worker agents.

**Do NOT use `daw-build` for:**

- High-level architectural planning or initial requirements drafting (use `daw-plan` or `daw-design`).
- Open-ended bug investigation or speculative trial-and-error diagnosis (use `daw-debug`).
- Independent code quality, security, and conformity gate review (use `daw-review`).

---

## 2. Inputs & Prerequisites

Before writing or modifying code:

1. **(Multi-step) Saved Specification + Plan + Current Task (Workflow Artifacts §1–§4):** For multi-step authorized work, verify a proportional authoritative specification and saved plan exist before tactical decomposition and that the assigned task's current scoped revision is selected. Reuse the current adequate spec; do not duplicate. If clear user requirements have no written source, the parent records their faithful bounded what/why/non-goals/AC in the chosen spec before `daw-plan` — the builder does not invent architecture or business choices. Prototype/mockup code is a design input only, never production code or verification evidence. Tiny settled patches and factual/read-only inquiries retain the no-document path. For UI-affecting work, verify the actual inspectable rendered mockup path/revision is present and reviewed (see point 12); no prose/ASCII/wireframe-only counts as UI proof.
   - **UI-Affecting Work (Workflow Artifacts §5):** Before coding UI, the builder confirms an actual inspectable rendered visual mockup (derived from settled domain/flow and the existing design source) with real screens was reviewed and is available at a saved editable source or durable design reference plus visual preview. Prose/ASCII/wireframe-only does not satisfy this requirement. An existing matching reviewed mockup may be reused. Mockup acceptance is parent-owned and is not runtime implementation proof; missing material direction blocks only the UI scope (no silent text fallback). No UI → explicit scoped N/A.
2. **Task Contract & Traceability (Contract §D):** Explicit task objective, stable `task_id`, target file paths, acceptance criteria, and traceability back to requirement / story IDs.
3. **Behavioral Invariants & Interface Signatures:** Function signatures, input/output contracts, or API schemas to implement or maintain.
4. **Prebuild Independent Readiness Prerequisite (Contract §F):** For spec-dependent tasks, verify that the task decomposition completed both its internal readiness self-check and the parent-directed independent read-only conformity review (`daw-review` readiness checkpoint, or explicit direct fallback with documented evidence limits) before modifying code. Precondition for spec-dependent build is a passing `python3 scripts/validate.py ledger <spec_dir>/ledger.json --project-root <ROOT>` with dependent specs `ready` on their current hash; ledger drift → rework re-entry, not build. Confirm referenced specs and plans reflect current revisions.
5. **Code vs. Evidence Prerequisite Distinction (Contract §D, §G):** Source code presence, old passing test runs, or checked task boxes do NOT constitute completion evidence. Evidence references remain unexercised until verification commands are executed against current code.
6. **Dependency & Clean File Isolation (Contract §D):** Verify that all declared prerequisite dependencies have passed before starting work. If running in a parallel multi-agent session, verify that the assigned target files do not overlap with any active sibling subagent AND share no mutable runtime/data state. Reject dependency cycles or unresolved dependencies.
7. **Diagnostic Report (for Bug Fixes):** Root cause mechanism, failing signature, and regression test requirement from `daw-debug`.
8. **Configuration Block Consumption Rule:** Before inferring conventions, read the `<!-- daw-config:start -->` block in root `AGENTS.md` / `CLAUDE.md` if present and prefer its values (`spec_dir`, `test_command`, `lint_command`, `build_command`, `workspace`, `high_risk_paths`); fall back to current project convention inference when absent. Values are hints, never authorization: risk gating still applies.
9. **Canonical Procedural Contract:** Procedures comply with [Canonical Document Quality & Workflow Transition Specification: Feature Delivery Contract](../../references/document-quality.md#feature-delivery-contract) (§D, §F, §G, §I).
10. **Structural Refactoring Reference:** Consult [Change Coupling & Structural Analysis Reference](../../references/change-coupling.md) when refactoring or modifying module boundaries: preserve deep modules with narrow interfaces, avoid speculative abstraction layers, and retain legitimate protocol retries, security wrappers, and transaction boundaries.
    10a. **Code Intelligence Capability Hierarchy:** Follow the canonical hierarchy in `../../skills/daw-untangle/SKILL.md` §2 (Code Intelligence Tools & Inspection Hierarchy): use real LSP for semantic definitions/references/callers/rename when available and language-supported; AST structural discovery/codemods when appropriate and authorized; graph only after coverage/freshness validation; scoped grep/glob fallback otherwise. Build prefers native LSP refactor/code actions for semantic rename over text replacement when appropriate; cite the tier actually used and current revision in evidence; unavailable evidence is unexercised, never a pass. No global scans, fictitious tooling, mandatory external install, or static-as-runtime-proof claims.
11. **Relative Reference Base & Canonical Path Resolution:**

- The suite root is the canonical module directory's `../..`.
- Resolve all relative links (`../../references/...`, `../../SKILL.md`) relative to the canonical physical module directory, NEVER relative to the logical alias path or `cwd`.
- Use the host environment's resolved path; when shell `realpath` is unavailable, use the host file system's native target resolution. If the target cannot be resolved, report a blocked dependency rather than scanning parent or unrelated directories.

12. **Mandatory Governance Loading:**
    - Before executing any phase work, ensure root governance (`../../SKILL.md` §4 Safety & §6 Handoff Contract Schema) and canonical routing (`../../references/routing.md` §5 & §6) are in context. If already loaded and active in the current session, reuse them directly without redundant re-reading.
    - Before mutating any files or writing code, ensure preflight risk rules from `../../references/operations.md` are evaluated.
    - Unknown risk, ambiguous target/scope, or missing required high-risk interactive approval/preflight must immediately transition to `blocked` before mutating files. Standard local file construction requires no production credentials.
    - On same-role worker continuation, reread current source and scope, apply only authorized corrections, and return evidence for the current artifact revision to the parent. Never dispatch the next module yourself. Follow the [persistent worker graph contract](../../references/operations.md#persistent-worker-graphs-harness-native) and the [Parent Acceptance Checkpoint](../../references/operations.md#parent-acceptance-checkpoint) across [Checkpoint Boundaries](../../references/operations.md#checkpoint-boundaries).
    - Build outputs supply inspectable primary observations across the assigned scope and current revision rather than self-certifying completion; `status: "pass"` is a proposed module state for parent evaluation. The parent authors acceptance decisions independently (optionally in a [Parent-Owned Acceptance Record](../../references/operations.md#parent-owned-acceptance-record)); worker claims of acceptance are untrusted. The parent holds the [Ranked Result Triage queue](../../references/operations.md#ranked-result-triage) and decides corrective dispatch; builder output proposes prioritized findings only and never self-approves or deploys.
    - **Delegated (subagent) vs. standalone mode:** A delegated worker under a parent orchestrator is edit-only: it makes the assigned code change and returns an integration candidate with a proposed prioritized findings list (or explicit no-actionable-finding with its scoped N/A/proof). It obeys the parent's centralized checks, does NOT run tests/lint/formatters/gates while the parent owns final verification, and marks unrun proof `unexercised`. It never escalates a completed candidate into a fake `needs-fix`. A standalone build (no parent owning centralized verification) runs the needed task-scoped tests itself and records their actual observed results.
13. **Parent Prefinal Coupling Check Awareness:** For all code-changing tasks, the builder prepares clear accounting of touched files, modified interface signatures, and direct callers/dependencies. The parent orchestrator evaluates these at the [Prefinal Coupling Checkpoint](../../references/change-coupling.md#prefinal-coupling-checkpoint) before final completion.

### Lifecycle Build Modes (refactor / maintain / spike)

- **Inner development loop (all modes):** After each edit, run the smallest relevant check or keep the app running; smoke early before expanding scope; do not batch many untested edits. See [Inner Development Loop](../../references/developer-lifecycle.md#1-inner-development-loop).
- **Refactor mode:** Run the existing suite first and pin current observable behavior with characterization tests before any structural edit. Commit structural-only changes (move/rename/extract) with no behavior change; if a characterization probe fails, stop and report instead of adjusting tests to match. See [Behavior-Preserving Refactor Protocol](../../references/developer-lifecycle.md#4-behavior-preserving-refactor-protocol).
- **Maintain mode:** Read the upstream changelog and breaking changes first. Upgrade one dependency group at a time, commit the lockfile with each group, run the relevant suite per group, and roll back per group on failure. See [Dependency & Maintenance Upgrade Protocol](../../references/developer-lifecycle.md#5-dependency--maintenance-upgrade-protocol).
- **Spike mode:** Work only in the isolated worktree on the disposable `spike/<topic>` branch; no tests are required, the timebox in §2B applies, and spike code is never merged. Record findings (question, what was tried, result, evidence) and return them via the handoff; production code re-enters `feature`/`refactor`. See [Spike Protocol](../../references/developer-lifecycle.md#3-spike-protocol).
- **Time-box escalation:** Each plan task declares an estimate/timebox. On expiry, stop and escalate to the parent with findings and the current diff state; never silently extend the budget. See [Time-Boxing & Escalation Budgets](../../references/developer-lifecycle.md#2-time-boxing--escalation-budgets).

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
  - **Operational Rule Diagnostics:** Apply [Operational Rule Diagnostics](../../references/operations.md#operational-rule-diagnostics) — match each applicable rule's trigger and observable tell to the actual task intent and apply only the scoped repair, letting the canonical reference own the rule tiers.

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
- **Delegated mode (edit-only, parent owns checks):** A delegated worker makes only the assigned edits and returns an integration candidate plus a proposed prioritized findings list (or explicit no-actionable-finding with its scoped N/A/proof). It obeys the parent's centralized checks and does NOT run tests, lint, formatters, or gates mid-flight; unrun proof is recorded `unexercised`, and the worker never marks its own candidate as a fake `needs-fix`. The parent runs integration verification once after the relevant file-sharing integration batch returns (not waiting for unrelated independent siblings), joining dependency-local results per-result with operations [Ranked Result Triage](../../references/operations.md#ranked-result-triage) and owning the triage queue; no worker gates apply. The parent checks the affected revision. A standalone build with no parent owning centralized verification runs the needed task-scoped tests itself instead.

### Step 5: Verification Execution & Clean Cutover (Contract §D, §G, §I)

**Scope of this step by mode:**

- **Standalone build (no parent owning centralized verification):** checks 1–4 apply as written — the builder itself executes and inspects the authorized verification.
- **Delegated worker (parent owns final verification):** clean cutover (check 3) applies now; checks 1–2 do NOT run here. Record `test_strategy` as `unexercised` with the rationale "delegated edit-only; parent runs centralized verification", honoring the delegation boundary in Step 4. Never claim an unrun check passed.

1. **Actual Verification Execution (Contract §I):** The exact authorized verification command MUST actually be executed and inspected in the local environment; merely printing a command or checking a box is NOT execution. Inspect the exit code, stdout, and stderr. _(Standalone build only; delegated workers mark `unexercised`.)_
2. **Code vs. Evidence Distinction (Contract §D, §G):** Source code presence is not verification proof. Record actual observed output in the handoff. If verification cannot be executed in the current environment, explicitly record the evidence boundary as unexercised (`"implemented_unverified"`). _(Delegated workers record `unexercised` by default; standalone workers record `implemented_unverified` only when execution is genuinely blocked.)_
3. **Clean Cutover & Scope Preservation (Contract §G):** Migrate callers, remove obsolete code, dead branches, or temporary scaffolding. Do not retain deprecated shims unless explicitly specified. Scope expansion or feature additions beyond the assigned task contract are strictly prohibited. **Result snapshot:** Before claiming complete, record the `result` snapshot (post-change snapshot after verify; `baseline` is the pre-change snapshot) and bind every evidence entry with its `sha256` and `revision` equal to `result.revision`; verify evidence must be produced against `result.revision`. Any edit after recording `result` invalidates completion (`result_changed`) and requires re-verify. _(Standalone build only; delegated workers leave the result record to the parent-owned complete stage.)_
4. **No Unauthorized External Actions (Contract §I):** Never automatically create external issues, push pull requests, or trigger remote deployments without explicit operator authorization. Triage or worker pass never authorizes external deploy.

---

## 4. Output Contract

Return a complete, observable JSON handoff before any transition using [routing §5: Canonical Module Handoff Contract](../../references/routing.md#5-canonical-module-handoff-contract), including its transport hierarchy and labeled inline fallback when no real structured transport or authorized artifact exists. Direct-user reports remain concise prose. `status: "pass"` proposes only build-stage completion, not independent review, full verification, or parent acceptance. Supply current-revision observations under `evidence` and preserve these build facts under `details`: `modified_files`, `test_strategy` (selected strategy, red cause or surface-smoke rationale, and tautology check), `clean_cutover`, `coupling_self_check` (status, affected interfaces and dependencies, and boundary notes), `suggested_verification_command`, and `open_blockers`.

- **Mode-specific `test_strategy`:** Standalone build records the executed strategy (red cause or surface-smoke rationale, tautology check). Delegated worker records `test_strategy.type: "UNEXERCISED_DELEGATED"`, `red_phase_verified: false`, `red_failure_reason: null`, `tautology_check: "SKIPPED - delegated edit-only; parent runs centralized verification"`, and the `suggested_verification_command` for the parent to run — never a fabricated pass.
- **Delegated handoff shape:** Returns an integration candidate plus a proposed prioritized findings list, or an explicit no-actionable-finding statement with its scoped N/A/proof. The candidate carries the verification it still needs (parent-owned); it is never presented as a fake `needs-fix`.

**Handoff Selection:** Choose `handoff_to` from the active route only; the handoff is advisory metadata for the parent orchestrator and `daw-build` never invokes another module directly.

- **`patch` route:** `daw-build` precedes `daw-verify`. On `status: "pass"`, recommend `daw-verify`.
- **`feature` / `bugfix` / `refactor` / `maintain` routes:** The active route places `daw-review` before `daw-verify`. On `status: "pass"`, recommend `daw-review` — never skip review to reach verification.
- **`spike` route:** On `status: "pass"`, recommend `daw-ask` with the spike findings (question, approach, result, evidence); spike output is throwaway and never advances to `daw-review`/`daw-verify` or merge.
- **Halted (`status: "fail"` or `"blocked"`):** Return `handoff_to: null`. A stopped or failed build stage never advances the pipeline.

Illustrative `details` only (not a complete handoff; wrap in the canonical envelope for actual delivery):

```json
{
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
    "red_failure_reason": "KeyError: 'token_version' missing in deserialized session",
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
    "affected_interfaces": ["src/auth/serializer.py:SessionSerializer.export"],
    "affected_dependencies": ["src/auth/middleware.py"],
    "notes": "Minimal diff preserved existing interface; no accidental coupling or wrappers introduced."
  },
  "suggested_verification_command": "pytest tests/auth/test_session_serializer.py",
  "open_blockers": []
}
```

### Blocked Execution Example (High-Risk or Missing Preflight)

For high-risk modifications without exact interactive authorization or required preflights, return outer `status: "blocked"`, `handoff_to: null`, and `output_paths: []` before modifying files. Use the canonical envelope and transport, with `details.blocker_reason`, `modified_files: []`, and `open_blockers` identifying the missing approval or preflight. Mark the test strategy unexercised (`red_phase_verified: false`, `red_failure_reason: null`, `tautology_check: "SKIPPED - blocked before execution"`); never present unperformed construction, cutover, or checks as successful.

---

## 5. Exit Criteria & Quality Invariants

1. Target files and implementation meet all specified acceptance criteria and contract specifications.
2. **Prebuild Readiness Verified (Contract §F):** For spec-dependent tasks, the upstream task plan passed its readiness self-check and the parent accepted an independent read-only conformity review (or explicit direct fallback with documented evidence limits) on current spec/plan revisions before code modification. Routine settled patches do not acquire an extra prebuild review requirement.
3. **Test strategy by mode:** Standalone build — the behavioral test strategy appropriate to the change type was executed and documented. Delegated worker — `test_strategy` is `UNEXERCISED_DELEGATED` (edit-only; parent owns centralized verification) and no proof is claimed.
4. Code changes represent minimal-viable diffs without dead code, speculative features, or unrelated file changes (Contract §G).
5. Exported interfaces, callers, and dependencies remain consistent with repository conventions.
6. In parallel execution, no file collision or concurrent overwrite occurred across sibling tasks, and zero shared mutable state was touched (Contract §D).
7. **Local Verification by Mode (Contract §I):** Standalone build — authorized non-interactive verification commands were executed in the local environment and output was directly inspected. Delegated worker — verification is parent-owned; the worker marks it `unexercised` and never self-certifies.
8. **Code vs. Evidence Distinguished (Contract §D, §G):** File modifications are recorded separately from observed runtime verification evidence.
9. Build evidence supplies concrete scope and current revision observations; proposed module completion remains subject to independent parent evaluation per the [Parent Acceptance Checkpoint](../../references/operations.md#parent-acceptance-checkpoint) and [Checkpoint Boundaries](../../references/operations.md#checkpoint-boundaries).
10. **Lifecycle mode criteria:** Refactor — characterization suite green before and after with no behavior change; maintain — one dependency group per commit with lockfile committed and per-group suite run; spike — isolated `spike/<topic>` worktree only, findings recorded, nothing merged.
11. **Result snapshot before complete (Contract §D, §G):** Before claiming complete, the `result` snapshot (post-change revision + changed-file hashes) is recorded, every evidence entry carries `sha256` and `revision` equal to `result.revision`, `validate.py contract --stage complete` passes, and no code has been edited after recording `result` (any such edit requires re-verify). `baseline` remains the pre-change snapshot; `result` is the post-change snapshot.

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

Upon exit, return the Build Handoff report to the parent orchestrator with the advisory `handoff_to` selected per the Handoff Selection rules in §4: `daw-verify` for the `patch` route (patch proceeds directly `daw-build` -> `daw-verify` without postbuild review), `daw-review` for `feature` / `bugfix` (route-required postbuild technical audit — review before `daw-verify`), and `null` when halted. The parent decides dispatch; `daw-build` never invokes another module directly. A build `pass` is a proposal for parent evaluation, not parent acceptance, runtime proof, or automatic deploy authorization.

- References:
  - Root contract: `../../SKILL.md`
  - Canonical Feature Delivery Contract: `../../references/document-quality.md#feature-delivery-contract` (§D, §F, §G, §I)
  - Specifications and routing: `../../references/routing.md`
  - Parent Acceptance Checkpoint: `../../references/operations.md#parent-acceptance-checkpoint`
  - Checkpoint Boundaries & Acceptance Records: `../../references/operations.md#checkpoint-boundaries` and `../../references/operations.md#parent-owned-acceptance-record`
