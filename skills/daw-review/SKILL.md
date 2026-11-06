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
- Auditing specification documents and evaluating workflow transitions (`review-ready`, `review-rework`) for selected canonical specifications.
- Conducting parent-requested proportional independent prebuild cross-artifact conformity review (readiness checkpoint) for spec-dependent or nontrivial features before build. (Prebuild readiness is a bounded review checkpoint, NOT a completed postbuild route `daw-review` or runtime proof. It does not advance the postbuild code review stage of the route, nor does it insert a new route stage into `../../references/routing.md` or cause module recursion; routine settled patches do not mandate an extra prebuild review stage).
- Conducting structural cohesion and change-coupling checks as part of Stage 2 review on modified diffs where applicable (feature and bugfix routes per `../../references/routing.md`).
  - **Reusing Accepted Current Review:** When the current matching scope and artifact revision have already been reviewed and accepted by the parent orchestrator, the parent reuses that accepted review evidence without triggering a duplicate review.
  - **Patch Route Proportionality:** Patch routes remain `build -> verify`; the parent orchestrator performs a bounded proportional diff check without mandating an extra `daw-review` stage or reviewer for routine patches or one-line fixes.
  - **Non-Code / Docs-Only Changes:** Tasks with no code or structural impact (documentation-only, comment-only, formatting) record an explicit inline N/A rationale rather than triggering a code review stage.

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
   - Before executing any phase work, ensure root governance (`../../SKILL.md` §4 Safety & §6 Handoff Contract Schema) and canonical routing (`../../references/routing.md` §5 & §6) are in context. If already loaded and active in the current session, reuse them directly without redundant re-reading.
   - `daw-review` is strictly read-only and never performs file mutations. Preflight evaluation confirms read-only scope without requiring production credentials or mutating authorizations.
   - The same independent read-only reviewer may be resumed for a corrected revision, but must inspect the current artifact; an earlier pass is invalid after affected edits. Existing retry and stop/replan rules still apply. Findings must be grounded in source proof or static verification of the current revision; independent review is strictly required only when the active route specifies it, and read-only review never forces unnecessary runtime execution when static proof is appropriate. Follow the [persistent worker graph contract](../../references/operations.md#persistent-worker-graphs-harness-native) and the [Parent Acceptance Checkpoint](../../references/operations.md#parent-acceptance-checkpoint) across [Checkpoint Boundaries](../../references/operations.md#checkpoint-boundaries). The parent authors acceptance decisions (optionally in a [Parent-Owned Acceptance Record](../../references/operations.md#parent-owned-acceptance-record)); reviewer findings serve as primary observations, not self-executing acceptance. Small tasks record reviews inline.

6. **Document Quality Reference & Review Invariants:**
   - Read [Canonical Document Quality & Workflow Transition Specification](../../references/document-quality.md#feature-delivery-contract) (§E, §F, §G) and `references/document-quality-rubric.json` when reviewing formal specifications.
   - **Independent Evaluation vs. Author Self-Grading:** The reviewer/parent evaluates semantic clarity, task accessibility for fresh readers/agents, and empirical evidence validity. Authors cannot self-grade unlock or grant themselves a pass; review exits require an independent `reviewer` identifier and explicit per-check `decision`: `accepted` | `not_accepted`.
   - **Requirements-Quality Checklist vs. Execution Task Checkboxes & Runtime Acceptance (§E):**
     - Requirements-quality checklists serve as "unit tests for requirements writing" — validating the completeness, clarity, consistency, verifiability, and coverage of requirements prose across domains.
     - **Reviewer-Owned Judgment:** Checklists and requirements reviews are strictly reviewer-owned artifacts. The author, builder, or implementation agent CANNOT tick reviewer criteria or checklist markers (`[x]`) to self-approve.
     - **No Generic Override:** Known blocking requirements or quality gate failures MUST NEVER be overridden with a generic user "proceed", "continue", or "LGTM" without satisfying the underlying criterion or formal documented scope revision. No request to relax tests, proofs, or review gates is permitted.
   - **Distinguishing Formal Document Rework Edges from Code-Only Evidence Invalidation:**
     - **Formal Document Rework Edges:** When an authoritative specification document (e.g. PRD, FRD, Blueprint, QA Matrix) is modified, its SHA-256 hash changes and invalidates prior `review-ready` eligibility. The document must transition through formal workflow edges: `review-rework` -> `rework-review` via `python3 scripts/validate.py docs` (or the direct Python stdlib fallback).
     - **Code-Only Evidence Invalidation:** When source code, environment, or configuration changes occur during build or fix iterations, affected Stage 1/Stage 2 review evidence and runtime test acceptance results are invalidated and must be rerun proportionally for affected paths, WITHOUT triggering formal document rework edges unless the authoritative specification itself was modified.
   - **Independent Reviewer Capability & Direct Fallback:**
     - Independent review is strictly required when the active route specifies it.
     - If an independent reviewer subagent capability is unavailable in the environment/harness, execute an explicit direct fallback under the parent orchestrator with documented evidence limits; never invent a fictitious reviewer persona or claim independent review where none occurred.
   - **Workflow Transition Gate vs. Hook Claims:** Review transitions are verified deterministically via:
     `python3 scripts/validate.py docs <RECORD> --project-root <ROOT> --transition review-ready|review-rework --documents <DOC_PATH> [<DOC_PATH> ...] --format text|json`
     This is a portable read-only CLI command, not an automatic harness interceptor hook or daemon supervisor.
   - **Transition Verdict Conditions:**
     - `review-ready`: Requires every decision to be `accepted` AND every author status to be `pass` or `not_applicable`. This unlocks downstream spec-dependent work.
     - `review-rework`: Triggered when at least one criterion is `not_accepted` (or blocked with `not_accepted`). Requires actionable repair rationale; routes back to authoring for rework, which subsequently transitions via `rework-review`.
   - **Mutation Invalidation:** Modifying any specification document changes its SHA-256 hash and immediately invalidates any prior `review-ready` eligibility.
   - **Proportionality & Python Fallback:** Trivial inline changes without formal specifications do not require document review transition records. If Python 3 is unavailable, halt with canonical `status: "blocked"` (never emit a fake pass).
   - **QA Review Limitation:** Document quality review verifies structural evidence eligibility, coverage, and citation presence. Human comprehension remains unexercised without live people (`[UNEXERCISED: NO HUMAN PARTICIPANTS]`).
7. **Structural Coupling Reference:** Consult [Change Coupling & Structural Analysis Reference](../../references/change-coupling.md) during Stage 2 technical audit when evaluating whether structural changes introduce hidden links, needless wrappers, or surplus taxonomy.
   7a. **Code Intelligence Capability Hierarchy:** Follow the canonical hierarchy in `../../skills/daw-untangle/SKILL.md` §2 for any code-intelligence lookups during review: real LSP for semantic definitions/references/callers/rename when available and language-supported; AST structural discovery when appropriate and authorized; graph only after coverage/freshness validation; scoped grep/glob fallback otherwise. Review is strictly read-only and never applies code actions, renames, or codemods (even when LSP/AST support them); cite the tier actually used and current revision in evidence; unavailable evidence is unexercised, never a pass. No global scans, fictitious tooling, mandatory external install, or static-as-runtime-proof claims.

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
5. **Structural Cohesion & Change-Coupling Audit (Parent Prefinal Check Alignment):**
   - Audit modified code against [Change Coupling Reference](../../references/change-coupling.md) and [Prefinal Coupling Checkpoint](../../references/change-coupling.md#prefinal-coupling-checkpoint): check for accidental co-change, circular dependencies, leaky abstractions, shotgun surgery risks, or surplus taxonomy (shallow wrappers, speculative interfaces) while preserving legitimate retries, security guards, and transaction boundaries.
   - **Finding Disposition:**
     - **Material Findings:** Direct correctness, security, invariant violations, broken encapsulation, or circular dependencies BLOCK review acceptance (`CHANGES_REQUESTED` or `status: "fail"`).
     - **Unrelated Improvements:** Observations regarding out-of-scope code or non-blocking cosmetic improvements must NOT be conflated with blocking findings or trigger unsolicited refactoring; report them separately as informational notes for parent consideration.
   - **Non-Code / Docs-Only Changes:** For documentation or non-code changes without structural impact, record an explicit inline N/A rationale.
   - **Escalation to `daw-untangle`:** If the structural check reveals deep, hidden, or unclear architectural entanglements across distant subsystems that cannot be settled from diff inspection alone, recommend that the parent escalate to `daw-untangle` (scoped strictly to the affected area, not the whole repository).
6. **Concrete Evidence vs. Subjective Taste:**
   - Every flagged issue must cite specific file paths, line numbers, and an objective technical reason or static code proof.
   - Reject subjective stylistic preferences that do not impact correctness, maintainability, or established project conventions.

### Prebuild Cross-Artifact Conformity Review (Readiness Checkpoint Mode)

When requested by the parent orchestrator prior to build dispatch, `daw-review` operates as an independent, read-only prebuild readiness checkpoint comparing proposed specifications, architecture, and task manifests per [Feature Delivery Contract §F](../../references/document-quality.md#feature-delivery-contract):

1. **Scope & Governance Alignment:**
   - Verify that proposed roadmap tasks and implementation plans align with foundational governance principles (`constitution.md`, `blueprint.md`, or project guidelines) without unrequested scope creep or policy violations.
2. **Bidirectional Traceability & Gap Analysis:**
   - Trace Requirements / Acceptance Criteria -> User Stories -> Task IDs -> Touchpoint File Paths.
   - Identify **Orphan Tasks** (tasks lacking requirement justification or prerequisite justification).
   - Identify **Unmapped Criteria** (requirements or acceptance scenarios lacking implementing tasks).
3. **Dependency & Parallel Safety:**
   - Verify that all task dependencies strictly precede dependent tasks in execution order.
   - Verify that parallel markers (`[P]`) are applied ONLY to tasks modifying disjoint file paths with zero shared mutable state or runtime dependencies.
   - Reject dependency cycles, unknown prerequisite IDs, and shared file ownership conflicts before dispatch.
4. **Source Freshness & Revision Alignment:**
   - Verify that all touchpoints cite currently verified repository paths and commit revisions, not stale assumptions or deprecated conventions.
5. **Requirements-Quality Evaluation:**
   - Audit requirements prose against the reviewer-owned quality rubric for ambiguity, untestable adjectives ("fast", "intuitive", "robust"), missing negative/edge scenarios, and ungrounded KPI claims.
6. **Structured Findings Format:**
   - Report findings using compact Markdown with:
     - `Finding ID`: Stable identifier (e.g., `PRE-01`).
     - `Severity`: `BLOCKER` (fails readiness; prevents build dispatch for affected scope), `HIGH`, `MEDIUM`, `LOW`.
     - `Location`: `artifact_path:line`.
     - `Consequence`: Concrete impact on build safety, requirements drift, or runtime ambiguity.
     - `Remediation`: Actionable repair instruction for the author or planner.
7. **Metrics Coverage Denominator Accounting:**
   - When reporting requirement coverage (e.g., tasks per requirement or test oracle definitions), the denominator MUST include all declared requirements and acceptance criteria.
   - Exclude ONLY justified non-buildable or out-of-scope criteria (such as post-launch business KPIs or external SLAs lacking test oracle boundaries, each with explicit written justification).
   - Unresolved gaps or missing mappings must NEVER be silently excluded from the denominator to artificially inflate coverage percentages. A missing mapping is an explicit gap, not an implicit N/A. No synthetic/fake 100% metrics.
8. **Readiness Checkpoint Gate:**
   - Blocking findings fail prebuild readiness (`status: "fail"`, `details.review_verdict: "CHANGES_REQUESTED"` or `"CONTRADICTION_HALT"`), preventing build dispatch for affected scope and routing back to authoring or planning.
   - Nonblocking findings are reported to the parent orchestrator, which retains sole authority over stage acceptance.
   - **Explicit Scope Boundary:** Passing a prebuild readiness review does NOT satisfy the postbuild code review requirement or claim runtime proof. Canonical postbuild code review remains required for feature and bugfix routes per active routing rules in `references/routing.md` (patch routes proceed directly from build to verification), and `daw-verify` remains required for runtime verification once code is implemented.

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

4. **Revision Invalidation & Route-Driven Corrections:**
   - Any code edits or fixes dispatched to address review findings invalidate prior affected review passes and runtime verification evidence for the modified artifacts.
   - The parent orchestrator routes authorized corrections through the existing `plan` -> `build` route before rechecking the current diff prior to final completion.
5. **Independent Reviewer Fallback Limitations:**
   - When an independent reviewer subagent is unavailable, state the explicit fallback limitations directly and do not pretend independent acceptance.

---

## 5. Output Contract

Every completion of `daw-review` delivers a structured handoff payload adhering to the canonical suite envelope as an internal module-to-orchestrator handoff. The canonical handoff payload MUST be delivered and observable BEFORE advancing to the next stage (`daw-verify`) per [User-Facing Reports & Handoff Transport](../../references/routing.md#user-facing-reports--handoff-transport) (via structured tool/subagent return or an explicit inline checkpoint fallback; read-only modules never create unasked files). Direct-user responses default to concise natural language rather than raw JSON. Rich audit findings, conformity status, and stage-gate verdicts are preserved under `details`.

- **Separate Stage 1 & Stage 2 Requirements:** `details` MUST contain explicit and separate verdicts and evidence for Stage 1 (`stage_1_conformity`) and Stage 2 (`stage_2_technical_audit`). Conflating both stages into a single unseparated verdict is invalid.
- **Review Mode Support:** `details.review_mode` explicitly distinguishes `"postbuild_code_review"` (default, evaluating implemented code diffs) from `"prebuild_readiness"` (evaluating proposed specifications, architecture, and task manifests for spec-dependent features). In `prebuild_readiness` mode, `review_verdict` evaluates cross-artifact readiness (`stage_1_conformity` reports requirements/story/task coverage and `stage_2_technical_audit` reports dependency/parallel safety). The orchestrator uses this checkpoint to gate build dispatch; postbuild code review (where required by the active route, e.g. feature and bugfix routes) and runtime verification remain strictly required after build completion.

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
5. For prebuild readiness reviews (scoped to spec-dependent and nontrivial features), cross-artifact traceability, orphan task detection, unmapped criteria, and dependency/parallel safety are fully recorded, with explicit notice that postbuild review remains required where mandated by the active route.
6. No automated or uncoordinated file modifications were performed by this skill.

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
  - Parent Acceptance Checkpoint: `../../references/operations.md#parent-acceptance-checkpoint`
  - Checkpoint Boundaries & Acceptance Records: `../../references/operations.md#checkpoint-boundaries` and `../../references/operations.md#parent-owned-acceptance-record`
