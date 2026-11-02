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

1. **Task Contract / Specification:** Explicit objective, list of files in scope, and acceptance criteria.
2. **Behavioral Invariants & Interface Signatures:** Function signatures, input/output contracts, or API schemas to implement or maintain.
3. **Diagnostic Report (for Bug Fixes):** Root cause mechanism, failing signature, and regression test requirement from `daw-debug`.
4. **Clean File Ownership Assignment:** If running in a parallel multi-agent session, verify that the assigned target files do not overlap with any active sibling subagent.
5. **Configuration Block Consumption Rule:** Before inferring conventions, read the `<!-- daw-config:start -->` block in root `AGENTS.md` / `CLAUDE.md` if present and prefer its values (`spec_dir`, `test_command`, `lint_command`, `build_command`, `workspace`, `high_risk_paths`); fall back to current project convention inference when absent. Values are hints, never authorization: risk gating still applies.
6. **Relative Reference Base & Canonical Path Resolution:**
   - The suite root is the canonical module directory's `../..`.
   - Resolve all relative links (`../../references/...`, `../../SKILL.md`) relative to the canonical physical module directory, NEVER relative to the logical alias path or `cwd`.
   - Use the host environment's resolved path; when shell `realpath` is unavailable, use the host file system's native target resolution. If the target cannot be resolved, report a blocked dependency rather than scanning parent or unrelated directories.
7. **Mandatory Governance Loading:**
   - Before executing any phase work, load root governance (`../../SKILL.md` §4 Safety & §6 Handoff Contract Schema) and canonical routing (`../../references/routing.md` §5 & §6). Reading governance documentation is not recursive router execution.
   - Before mutating any files or writing code, load `../../references/operations.md` §1 Preflight Safety & §2 High-Risk Approvals.
   - Unknown risk, ambiguous target/scope, or missing required high-risk interactive approval/preflight must immediately transition to `blocked` before mutating files. Standard local file construction requires no production credentials.

---

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

### Step 4: Subagent & Parallel Task Isolation

When the orchestrator delegates tasks across multiple subagents:

- **Disjoint File Ownership:** Each subagent must own a completely distinct set of files. Never assign the same file to concurrent workers.
- **Explicit Interface Contracts:** Any shared types, interfaces, or protocol boundaries between subagent tasks must be pre-defined in the shared plan context before subagent execution begins.
- **Fresh Context:** Each subagent starts with clear, self-contained requirements, target files, non-goals, and acceptance criteria.
- **No Mid-Flight Verification Storms:** Subagents skip running full test suites or lint passes mid-flight; the parent orchestrator runs end-to-end integration verification once after all subagents yield.

---

## 4. Output Contract

Every completion of `daw-build` delivers a structured handoff payload adhering to the canonical suite envelope. Rich build facts, test strategies, and clean cutover status are preserved under `details`:

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

## 5. Exit Criteria

1. Target files and implementation meet all specified acceptance criteria and contract specifications.
2. Behavioral test strategy appropriate to the change type was executed and documented.
3. Code changes represent minimal-viable diffs without dead code, speculative features, or unrelated file changes.
4. Exported interfaces, callers, and dependencies remain consistent with repository conventions.
5. In parallel execution, no file collision or concurrent overwrite occurred across sibling tasks.

---

## 6. Stop / Replan Protocols

Immediately halt construction and escalate to the parent orchestrator if:

- **Interface Mismatch / Missing Dependency:** An expected upstream interface, type definition, or internal service contract is missing, ambiguous, or incompatible with the build plan.
- **File Ownership Conflict:** Implementing the required change requires modifying a file currently assigned to or locked by a concurrent sibling agent.
- **Red Phase Non-Reproducibility:** The failing behavioral test passes without code changes (flaky or invalid test specification), or fails due to an intractable environment error outside the build scope.
- **Scope Creep / Missing Architectural Guidance:** Meeting the acceptance criteria requires modifying core database schemas, changing public API contracts, or refactoring unassigned subsystems.

---

## 7. Handoff

Upon exit:

- Yield the Build Handoff report to the parent orchestrator for end-to-end integration verification and dispatch to `daw-review`.
- References:
  - Root contract: `../../SKILL.md`
  - Specifications and routing: `../../references/routing.md`
