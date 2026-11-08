# Engineering Delivery Roadmap: [Initiative Name]

> **Fill-in Guidance:** Fill this template using verified technical dependencies, milestone sequence, concrete task decomposition, and observable exit criteria. Comply with the canonical [Feature Delivery Contract](../references/document-quality.md#feature-delivery-contract) (§D Traceability, §F Prebuild Analysis, §G Convergence, §I Local Tooling) and [Workflow Artifacts](../references/workflow-artifacts.md).
>
> - **Spec-First Consumption:** Consume the current persisted proportional spec before tactical decomposition with exact source refs + revisions. If clear requirements have no file, the authorized parent records them first; planner invents no design or new stage. Ambiguity returns to the existing design/clarification route.
> - **Traceability (Contract §D):** Every task must trace bidirectionally: `Requirement / AC ID -> User Story (where relevant) -> Task ID -> Target File Paths -> Dependencies -> Verification / Expected Outcome -> Current Observed Evidence / Status`, with separate parent decision distinct from worker status.
> - **Supporting Infrastructure Justification (Contract §D):** Foundational or infrastructure tasks lacking a user story must state an explicit prerequisite justification explaining why downstream story slices depend on it.
> - **N/A Criteria Rule (Contract §D):** Mark criteria `N/A` ONLY with reasoned non-buildable or out-of-scope rationale; missing mappings are explicit gaps, never implicit `N/A`. A UI task without a matching rendered mockup ref marks only UI scope blocked.
> - **Evidence vs. Command Distinction (Contract §D, §I):** Evidence references remain unexercised/empty until executed; commands alone or checked task boxes are NOT proof of completion. Exact invocation uses no invented binary; a real surface action is permitted for UI checks while legacy `verification_command` is preserved only as a reference/action where needed.
> - **Dependency & Parallel Safety (Contract §D):** Dependencies precede story slices; parallel marker `[P]` requires strictly disjoint file writes AND zero shared runtime/data dependency. Reject cycles and unknown dependencies before dispatch.
> - **Prebuild Readiness (Contract §F):** Spec-dependent features require plan readiness self-check and parent-owned independent read-only conformity review (`daw-review` prebuild checkpoint or explicit direct fallback) before build dispatch; trivial inline patches do not.
> - **Convergence Reconciliation (Contract §G):** Classify items into `Implemented & Verified`, `Implemented (Unverified)`, `Missing`, `Contradicted`, or `Blocked`. Preserve stable IDs and retry history; merge duplicates; do not duplicate pending tasks; append only genuine uncovered work inside accepted scope.
> - **Ranked Queue (operations#ranked-result-triage):** Returned results enter the parent-owned ranked queue — parent picks eligible fixes by urgency/impact/deps and accepted joins; no automatic external deploy from worker pass.
> - **Local Tooling (Contract §I):** Reuse project-local commands and test runners; exact verification must actually execute and be inspected; no automatic external issues, PRs, or deployments without operator authorization. Native todos complement durable artifacts; no separate task tracker is created.

> **Status:** Draft (default for new documents; set to Approved only with exact observed human/provider approval evidence)
> **Owner:** [Supplied/verified owner name or role; otherwise Unassigned — requires owner decision]
> **Scope:** [Feature lifecycle, phasing, technical milestones, release gates]
> **Source Documents / Revision:** [Actual observed BRD, PRD, blueprint.md, or relative path (marked unversioned if revision unobserved); never invent synthetic tags like @initial]
> **Spec Source Revisions:** [Exact spec paths and revisions consumed before planning; if clear requirements had no file, the parent-recorded spec ref and revision]
> **Current Phase / Progress Ref:** [Current phase, progress record ref, saved plan ref and revision; current-phase reference only — no mandated strategic rewrite each task]
> **Source / Mockups Trace:** [Source → rendered mockup refs for UI tasks, or explicit scoped N/A; UI task without matching mockup ref is blocked for UI scope only]
> **Ranked Queue Ref:** [Parent-owned ranked result triage record in this durable plan/progress; no automatic external deploy from worker pass]
> **Assumptions:** [Team availability, platform stability, upstream component releases]
> **Reader & Core Task:** [Engineering Lead / Delivery Coordinator / Implementation Agent] — Sequence delivery phases, verify dependency ordering and bounded milestone outcomes, and monitor stop/replan triggers without relying on invented calendar release dates.
> **Quality Reference:** Canonical rubric and transition gate criteria in [references/document-quality.md](../references/document-quality.md) (common `DQ-01`..`DQ-05`, `roadmap-01`..`03`, and [#feature-delivery-contract](../references/document-quality.md#feature-delivery-contract)).
> **Goal:** [One-sentence delivery goal]
> **Architecture:** [2-3 sentences: key shape, layering, non-obvious decisions]
> **Tech Stack:** [Language, runtime, framework, test runner]
> **Global Constraints (verbatim from spec/config):** [Configured test command, e.g. `pytest tests/auth/ — 0 exit code required`; integer-money rule, etc. — one line each, copied verbatim]
> **File Map:** [`src/...` (create/modify) — one-line responsibility; `tests/...` — corresponding tests]

---

## 1. Foundation & Vertical Story Slices

_Structure is foundation → vertical story slices (P1 first) → release-readiness. Do NOT use horizontal layer phases (spec/foundation/implementation/verification) — a milestone-only roadmap without task IDs, steps, and commands is not a plan. Tiny settled patches stay inline without slices._

### Foundation / Prefactor (only with infrastructure justification)

- **Justification:** [Why downstream slices depend on this; N/A if none — foundation tasks are forbidden without it]
- **Goal:** [Shared capability the slices consume]
- **Independent Test:** [Observable check, e.g. exact command + expected output]
- **Tasks:** TASK-00 [exact file paths; ordered steps with run+expected]

### Slice P1: [Story title]

- **What to build:** [End-to-end behavior, not a layer list]
- **Out of scope:** [Explicit non-goals for this slice]
- **Goal:** [Narrow behavior this slice delivers]
- **Independent Test:** [Observable oracle; e.g. `pytest tests/test_slice.py` → all pass]
- **Checkpoint:** P1 alone is demoable: [independent test]
- **Autonomy:** [hitl|afk — hitl needs a live human decision; only afk is delegable unsteered]
- **Tasks:** TASK-01, TASK-02 [each with target files, depends_on, ordered steps `action/file/run/expected`, contract preview, constraints quoted]

### Slice P2: [Story title]

- **What to build:** [End-to-end behavior not covered by P1]
- **Out of scope:** [Explicit non-goals]
- **Goal:** [Behavior delivered]
- **Independent Test:** [Observable oracle]
- **Checkpoint:** P2 alone is demoable: [independent test]
- **Autonomy:** [hitl|afk]
- **Tasks:** [TASK-03, ... with ordered steps run+expected]

### Release-readiness

- **Scope:** [Full-suite gate, security negative verification, operational checks]
- **Exit Criteria:** [Exact suite command + expected observable; QA matrix signed off with evidence logs]

## 2. Task Traceability & Work Breakdown Matrix (Contract §D)

_Compact traceability mapping linking every requirement and acceptance criterion to discrete implementation tasks, target files, dependencies, verification commands, and observed evidence. Mark N/A only with explicit reasoned justification for non-buildable or out-of-scope criteria._

| Task ID     | Slice  | Story / Req / AC Ref | Source Ref + Revision    | Prerequisite Justification (Infra)   | Target File Paths       | Dependencies | [P]?       | Autonomy | Verification / Expected Outcome          | Status      | Observed Evidence Ref | Parent Decision    |
| :---------- | :----- | :------------------- | :----------------------- | :----------------------------------- | :---------------------- | :----------- | :--------- | :------- | :--------------------------------------- | :---------- | :-------------------- | :----------------- |
| `[TASK-01]` | `[P1]` | `[REQ-01 / AC-01]`   | `[docs/specs/... @ rev]` | `[Justification if infra; else N/A]` | `[exact/path/file.py]`  | `[]`         | `[Yes/No]` | `[afk]`  | `[pytest tests/test_task01.py (exit 0)]` | `[Pending]` | `[Unexercised]`       | `[Pending parent]` |
| `[TASK-02]` | `[P1]` | `[REQ-02 / AC-02]`   | `[docs/specs/... @ rev]` | `[N/A]`                              | `[exact/path/file2.py]` | `[TASK-01]`  | `[No]`     | `[afk]`  | `[pytest tests/test_task02.py (exit 0)]` | `[Pending]` | `[Unexercised]`       | `[Pending parent]` |

> **Execution Steps (per task; do not compress to a single command):** each task lists ordered single-action steps — write failing test → run, expect fail with named reason → minimal change → run, expect pass → suite. Each step names its file and an exact `run` + `expected` observable. Baseline step first (current revision, suite green before edits). Steps are plan text; evidence stays null until executed. Contract-bearing tasks carry the exact intended contract text (`change_preview`) and verbatim data-model constraints (`constraints_quoted`); non-contract tasks set `change_preview: null` with reason. No layer-only tasks ("create all tables", "all endpoints") and no standalone "write tests for X" tasks — tests land inside the slice introducing the behavior.

_Task block shape (illustrative; replace every value with real paths, names and commands from the spec and config):_

```markdown
#### TASK-01 — Reject a duplicate for the same key (Slice P1, AC-01, afk)

- Files: modify `src/store.py`; test `tests/test_store.py`
- Contract preview: `class DuplicateError(Exception)`; `Store.add(item) -> None` raises `DuplicateError`
- Constraints quoted: "quantity is an integer; no float conversion" (spec §4)

1. Baseline — run `pytest tests/` → expected: all existing tests pass
2. Write failing test `test_add_rejects_duplicate` in `tests/test_store.py` (add once, add again, assert `DuplicateError` and stored count stays 1)
3. Run `pytest tests/test_store.py::test_add_rejects_duplicate` → expected: FAIL, `DuplicateError` not defined
4. Minimal change in `src/store.py`: define `DuplicateError`, raise it on a repeated key
5. Run `pytest tests/test_store.py::test_add_rejects_duplicate` → expected: PASS
6. Run `pytest tests/` → expected: all tests pass, exit 0
```

> **Matrix Invariants:**
>
> - **Task Cardinality:** A task may cover multiple criteria; artificial 1-to-1 mapping is not required.
> - **Supporting Infrastructure Justification:** A foundational or infra task lacking a user story MUST state an explicit prerequisite justification explaining why downstream story slices depend on it.
> - **Evidence vs. Command:** The `Observed Evidence Ref` column remains `[Unexercised]` until the verification actually executes against the built codebase; planned commands or task checkboxes are NOT proof of completion. Exact invocation uses no invented binary; a real surface action is permitted for UI checks while legacy `verification_command` is preserved only as a reference/action where needed.
> - **Parallel Safety `[P]`:** Mark `[P]?` as `Yes` ONLY if target files are strictly disjoint AND no shared mutable runtime/data state exists.
> - **Parent Decision:** Worker status and parent acceptance are separate columns; worker `pass` never equals parent `accepted`.
> - **UI Mockup Gate:** A UI-affecting task MUST consume matching rendered mockup refs or mark only UI scope blocked; no silent text fallback for material missing direction.

## 3. Critical Path, Dependency Validation & Concurrency (Contract §D)

_The dependency graph must form a strict Directed Acyclic Graph (DAG). Reject cycles and unknown task dependencies before dispatch. Dependencies must strictly precede dependent story slices._

| Task / Milestone | Blocking Dependencies | Parallel With | File Isolation Verified?                    | Cycle / Dependency Check |
| :--------------- | :-------------------- | :------------ | :------------------------------------------ | :----------------------- |
| `[TASK-01]`      | `[]`                  | `[TASK-03]`   | `[Verified disjoint files: src/a vs src/b]` | `[Acyclic]`              |
| `[TASK-02]`      | `[TASK-01]`           | `[None]`      | `[Serialized consumer of TASK-01]`          | `[Acyclic]`              |

## 4. Prebuild Readiness & Conformity Review Checkpoint (Contract §F)

_Spec-dependent features require plan readiness self-check and parent-owned independent read-only conformity review (`daw-review` prebuild checkpoint or explicit direct fallback with documented evidence limits) before build dispatch; trivial inline patches do not require prebuild review._

- **Plan Readiness Self-Check:** `[Passed / Blocked — verified 100% criteria mapping, zero orphan tasks, zero cycles, disjoint parallel boundaries]`
- **Independent Prebuild Review Verdict:** `[Accepted / Findings Pending / Direct Fallback with Limits]`
- **Prebuild Review Findings Ledger:**

| Finding ID | Severity                    | Location                    | Consequence                       | Repair Proposal             |
| :--------- | :-------------------------- | :-------------------------- | :-------------------------------- | :-------------------------- |
| `[F-01]`   | `[Blocking / Non-Blocking]` | `[file.py:lines or doc.md]` | `[Direct consequence of finding]` | `[Exact corrective action]` |

## 5. Convergence Reconciliation Ledger (Contract §G)

_When re-planning or reconciling drift: inspect actual code, authoritative contracts, and current verification evidence. Classify items into Implemented & Verified, Implemented (Unverified), Missing, Contradicted, or Blocked. Preserve stable IDs and history; append only genuine uncovered work inside accepted scope._

| Item / Contract Ref | Classification             | Preserved Task ID | Current Observed Code / Evidence | Action / Appended Task        |
| :------------------ | :------------------------- | :---------------- | :------------------------------- | :---------------------------- |
| `[REQ-01 / AC-01]`  | `[Implemented & Verified]` | `[TASK-01]`       | `[tests/test_01.py passed]`      | `[None — preserved]`          |
| `[REQ-02 / AC-02]`  | `[Missing]`                | `[TASK-02]`       | `[Endpoint returns 404]`         | `[Appended TASK-03 in scope]` |

## 6. Scope Cut & De-scoping Protocol

_If unexpected blockers occur, de-scoping must be agreed upon explicitly rather than silently dropping acceptance criteria. One-off execution includes commands/tools, expected results, done criteria, and rollback only where relevant; discover/reuse bounded repeat tooling, no unsolicited automation._

- **Non-Negotiable Core (Must Have):** [Core functionality required for safety and functionality]
- **Negotiable Secondary (Nice to Have):** [Performance micro-optimizations, auxiliary batch scripts]
- **Stop / Replan Triggers:** [Dependency cycle detected, unmapped criteria gap, prebuild review blocking finding, or unresolvable specification contradiction]
- **Ranked Queue Ref:** [Parent-owned ranked result triage record: parent picks eligible fixes by urgency/impact/deps and accepted joins; no automatic external deploy from worker pass]

## 7. Document Quality & Review Checks

_Verify against canonical [Document Quality Rubric](../references/document-quality.md) and [Feature Delivery Contract](../references/document-quality.md#feature-delivery-contract) before workflow transitions. Mark N/A with rationale where proportional to scope._

- [ ] **roadmap-01 (Sequencing & Phasing):** Are delivery phases, milestones, and deliverables broken down into sequenced, dependency-ordered work units?
- [ ] **roadmap-02 (Critical Path & Dependencies):** Are critical path dependencies, integration risk choke-points, and technical debt mitigations explicitly identified with cycle checks?
- [ ] **roadmap-03 (Completion Gates & Decision Rules):** Are phase completion gates, release acceptance criteria, and go/no-go or stop/replan decision rules defined with observable signals without invented dates?
- [ ] **traceability-check (Contract §D):** Is every requirement/AC traced bidirectionally to task IDs, target files, dependencies, verification, evidence status, source refs/revisions, and separate parent decision without implicit N/A?
- [ ] **prebuild-readiness (Contract §F):** Is plan readiness self-check complete and parent-directed prebuild review recorded for spec-dependent features?
- [ ] **convergence-integrity (Contract §G):** Are existing task IDs and history preserved during replanning, with genuine gaps appended inside accepted scope?
- [ ] **saved-plan-check:** Is the saved plan + progress ref current, native todos complementary (no separate tracker), UI mockup refs matched or UI scope blocked, and ranked queue current?
- [ ] **placeholder-scan:** No TBD/TODO/"add appropriate error handling"/"handle edge cases"/"write tests for the above"/"similar to TASK-n" and no prose-only gate like "tests pass" without a command.
- [ ] **name-consistency:** Every entity, field, type, and function named in any task exists in the cited spec/ERD or is produced by an earlier task with the same spelling.
- [ ] **gate-concreteness:** Every verification names an exact command and its expected observable, including every step's `run` + `expected`.
- [ ] **autonomy-check:** Every task carries `autonomy: hitl|afk`; no `afk` task depends on an open human decision.
- [ ] **slice-scope-check:** Each slice states What to build (end-to-end behavior) and an explicit Out of scope line; no layer-only or standalone-test tasks.
