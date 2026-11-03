---
name: daw-review
description: "Deterministic two-stage code review gate: evaluates changes across Stage 1 (Requirements Conformity) and Stage 2 (Correctness, Security, Performance, Maintainability). Operates strictly read-only, grounds findings on concrete evidence or static proofs rather than subjective taste, enforces bounded fix-and-rereview loops with hypothesis-driven replanning, and halts when changes contradict specifications."
compatibility: "Fully self-contained procedural skill; no external dependencies required."
---

# DAW Review: Deterministic Two-Stage Code Review Gate

Read-only code review gate auditing changes against explicit requirements and empirical evidence or static code proofs.

---

## 1. Trigger & When to Use

Invoke `daw-review` when:

- Evaluating completed features, bug fixes, or refactors before integration, branch merging, or user sign-off.
- Conducting intermediate stage-gate evaluations during multi-step engineering plans.
- Re-evaluating previously flagged review findings after an orchestrator-directed fix cycle.
- Auditing security, input validation, error handling, or performance regression risks in modified code.

**Do NOT use `daw-review` for:**

- Writing implementation code, tests, or hotfixes (use `daw-build`).
- Root cause diagnosis of unexplained system crashes or bug reproduction (use `daw-debug`).
- Verifying deployment infrastructure, live URLs, or external smoke endpoints (use `daw-verify`).

---

## 2. Inputs & Prerequisites

Before conducting a code review:

1. **Target Diff / Scope:** The list of changed files, commits, or git diff relative to the base branch.
2. **Authoritative Specification / Requirements Contract:** The user prompt, acceptance criteria, BRD/PRD, plan document, or task contract specifying what was requested.
3. **Evidence Artifacts:** Test execution results, benchmark outputs, static analysis proofs, or diagnostic logs produced during build or verification.
   - **Ground Truth Evidence vs. Agent Self-Report:** Trust only actual command outputs, tool logs, observable test results, or verifiable static path proofs. Never accept an agent's self-reported "all tests pass" or "code is clean" without examining concrete verification evidence.
4. **Relative Reference Base & Canonical Path Resolution:**
   - When loaded via symlink or alias (e.g. `~/.agents/skills/daw-review`), resolve THIS `SKILL.md` symlink to its physical/canonical target file first.
   - The suite root is the canonical module directory's `../..`.
   - Resolve all relative links (`../../references/...`, `../../SKILL.md`) relative to the canonical physical module directory, NEVER relative to the logical alias path or `cwd`.
   - Use the host environment's resolved path; when shell `realpath` is unavailable, use the host file system's native target resolution. If the target cannot be resolved, report a blocked dependency rather than scanning parent or unrelated directories.
5. **Mandatory Governance Loading:**
   - Before executing any phase work, load root governance (`../../SKILL.md` §4 Safety & §6 Handoff Contract Schema) and canonical routing (`../../references/routing.md` §5 & §6). Reading governance documentation is not recursive router execution.
   - `daw-review` is strictly read-only and never performs file mutations. Preflight evaluation confirms read-only scope without requiring production credentials or mutating authorizations.

---

## 3. Step-by-Step Procedure

### Stage 1: Requirements Conformity Gate

_Stage 1 determines whether a full Stage 2 audit is useful. A failed conformity gate still produces a complete review report; evident security or data-loss risks must remain visible._

1. **Scope & Goal Alignment:**
   - Verify every item in the task contract or user request has a corresponding implementation.
   - Flag any missing acceptance criteria, omitted edge cases, or dropped requirements.
   - Check for unrequested scope creep: flag features, abstractions, or configuration knobs added without user authorization.
2. **Behavioral Invariant Check:**
   - Verify that the core requested behavior actually exists and is exercised in the diff.
   - Ensure the implementation solves the real problem requested, not a simplified or familiar substitute.
3. **Stage 1 Decision Gate:**
   - If requirements conformity fails: Record `Stage 1: FAILED`, outer `status: "fail"`, and `details.review_verdict: "CHANGES_REQUESTED"`. Skip the full Stage 2 audit, but perform bounded static triage of evident confidentiality, authorization, or data-loss risks in the inspected paths. Record Stage 2 as `LIMITED_SECURITY_TRIAGE` when such triage is performed, or `SKIPPED` otherwise; neither status claims a full technical audit passed.
   - If requirements conformity passes: Proceed to Stage 2.

### Stage 2: Technical Correctness, Security, Performance & Maintainability Gate

1. **Correctness & Robustness:**
   - Check error handling, edge cases, null/undefined safety, off-by-one errors, and boundary conditions.
   - Verify that tests are non-tautological, test real outcomes, and adequately cover failure branches.
   - Verify that no bugs or error states are suppressed (e.g., empty `catch` blocks, silent fallbacks, or fake mocks).
2. **Security & Vulnerability Audit:**
   - Audit for injection risks (SQLi, command injection, path traversal, template injection).
   - Check authentication/authorization boundaries, token handling, and secret leakage.
   - Audit input validation, deserialization, and untrusted payload handling.
   - **Static Path Proofs Valid:** For security findings, an empirical live exploit run is not required; a verifiable static data-flow proof (tracing unvalidated input from source to sink) constitutes valid evidence.
3. **Performance & Resource Hygiene:**
   - In compiled or hot execution paths, check for avoidable memory allocations, deep object copies, and redundant loops.
   - Check for potential memory leaks, unclosed file descriptors, orphaned sockets, or database connection pool leaks.
   - Identify unindexed database queries or N+1 query patterns.
4. **Maintainability & Boring Design:**
   - Prefer boring, clear, readable design over clever or needless abstractions.
   - Delete dead weight: ensure deprecated shims, obsolete comments, and unused functions were removed (clean cutover).
   - Reject arbitrary code restyling or formatting churn on untouched lines.
5. **Concrete Evidence vs. Subjective Taste:**
   - Every flagged issue must cite specific file paths, line numbers, and an objective technical reason or static code proof.
   - Reject subjective stylistic preferences that do not impact correctness, maintainability, or established project conventions.

---

## 4. Fix-and-Rereview Loop Protocol

To ensure review loops remain deterministic and avoid both premature halts and endless thrashing:

1. **Recurrence-Driven Replanning (No Arbitrary Cycle Caps):**
   - Do not halt solely on an arbitrary iteration number if progress is being made.
   - Instead, track finding recurrence: if the **same failure recurs** after a targeted correction, halt the loop and trigger a root-cause replan.
   - **Hypothesis-Bounded Retries:** When a proposed fix fails review, allow exactly one retry under a revised hypothesis. If that retry fails or produces the same recurrence, stop the cycle and change the approach or escalate.
2. **Strictly Read-Only Standalone Execution:**
   - `daw-review` NEVER applies edits or fixes directly.
   - All findings are reported back to the parent orchestrator, which coordinates requested implementation fixes with worker agents.
3. **Stop When Contradicting Requirements:**
   - If resolving a technical or quality finding would directly contradict an explicit user requirement or acceptance criterion:
     1. Do not engage in speculative trade-off guessing.
     2. Immediately stop the review loop.
     3. Surface the explicit conflict to the parent orchestrator / user for a binding decision.

---

## 5. Output Contract

Every completion of `daw-review` delivers a structured handoff payload adhering to the canonical suite envelope. Rich audit findings, conformity status, and stage-gate verdicts are preserved under `details`:

```json
{
  "objective": "Perform two-stage code review of authentication session version rotation.",
  "input_paths": [
    "src/auth/serializer.py",
    "src/auth/session.py",
    "tests/auth/test_session_serializer.py"
  ],
  "output_paths": [],
  "acceptance_criteria": [
    {
      "criterion": "Stage 1: All authoritative requirements satisfied without omissions or unrequested creep",
      "status": "pass"
    },
    {
      "criterion": "Stage 2: Code passes technical audit for correctness, security, performance, and maintainability",
      "status": "pass"
    }
  ],
  "evidence": [
    {
      "reference": "pytest tests/auth/test_session_serializer.py",
      "summary": "pytest tests/auth/test_session_serializer.py exited 0 (2 passed)"
    }
  ],
  "status": "pass",
  "handoff_to": "daw-verify",
  "details": {
    "review_verdict": "PASSED",
    "stage_1_conformity": {
      "status": "PASSED",
      "requirements_checked": [
        {
          "requirement": "Add JWT token rotation with token_version tracking",
          "status": "SATISFIED",
          "evidence_file": "src/auth/serializer.py:42"
        }
      ],
      "omissions_or_creep": []
    },
    "stage_2_technical_audit": {
      "status": "PASSED",
      "findings": []
    },
    "review_loop_state": {
      "iteration_count": 1,
      "recurrence_detected": false,
      "remaining_blockers": 0
    },
    "recommendation_for_orchestrator": "Proceed to integration verification."
  }
}
```

_(Note: `status: "pass"` indicates that the review phase evaluation criteria have been satisfied; it does not indicate deployment or runtime verification). No competing top-level verdict exists outside `details`._

---

## 6. Exit Criteria

The review phase is complete when:

1. Stage 1 Requirements Conformity has been explicitly evaluated against authoritative requirements.
2. If Stage 1 passed, Stage 2 has examined correctness, security, performance, and maintainability. If Stage 1 failed, the report records Stage 2 as `SKIPPED` or `LIMITED_SECURITY_TRIAGE`, states the unexamined scope, and includes any evident security or data-loss findings. A failed conformity review is complete with outer `status: "fail"`; it never receives a passing verdict.
3. Every finding includes an objective technical rationale and evidence (no subjective taste or unsourced assertions).
4. Detailed review verdict is recorded under `details.review_verdict` (`PASSED`, `CHANGES_REQUESTED`, `CONTRADICTION_HALT`, or `REPLAN_REQUIRED`).
5. No automated or uncoordinated file modifications were performed by this skill.

---

## 7. Stop / Replan Protocols

Immediately halt the review and return control to the parent orchestrator if:

- **Missing Requirements Baseline:** The user request, acceptance criteria, or specification is completely absent or self-contradictory.
- **Specification Contradiction:** A proposed technical remediation directly contradicts a core user-specified requirement.
- **Recurrent Failure After Targeted Correction:** A fix attempt resulted in the same recurring failure signature, indicating an invalid root cause hypothesis.
- **Unverified Agent Claims:** Critical changes lack objective test output, verifiable runtime proof, or clear static code proofs.

---

## 8. Handoff

Upon exit:

- Deliver the structured Review Report to the parent orchestrator.
- If changes are requested: Orchestrator routes specific findings to `daw-build` or `daw-debug`.
- If passed: Orchestrator routes to `daw-verify` or final delivery.
- References:
  - Root contract: `../../SKILL.md`
  - Specifications and routing: `../../references/routing.md`
