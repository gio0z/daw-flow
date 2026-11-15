---
name: daw-plan
description: "Deterministic implementation planning and task decomposition: maps concrete ordered tasks, explicit file ownership, dependencies, acceptance criteria, time-box estimates, and verification gates without unwanted document churn."
---

# DAW Plan (`daw-plan`)

Converts design specs, architectural requirements, or change requests into concrete, ordered, verifiable tasks with disjoint file ownership, dependency sequencing, Acceptance Criteria (AC), and verification commands.

**Invariant:** Keep plans actionable, bounded, and lean. Multi-step authorized work MUST save the plan before build dispatch per [Workflow Artifacts](../../references/workflow-artifacts.md) (chat/native todo alone is insufficient). Tiny settled patches stay inline. Never create plan sprawl or unwanted git commits.

---

## 1. Trigger & Scope

- Transitioning from design (`daw-design`) to implementation.
- Planning `refactor` (behavior-preserving structural steps + characterization oracles; see [Behavior-Preserving Refactor Protocol](../../references/developer-lifecycle.md#4-behavior-preserving-refactor-protocol)) or `maintain` (dependency groups with rollback; see [Dependency & Maintenance Upgrade Protocol](../../references/developer-lifecycle.md#5-dependency--maintenance-upgrade-protocol)).
- Decomposing a multi-step task/bugfix into execution slices or parallel subagent distributions.

### Non-Goals & Invariants

- **Authoring Boundary (`../../references/routing.md` §3):** `daw-plan` owns tactical decomposition, sequencing, file ownership, and tactical `roadmap.md` updates — never architecture specs or strategic phasing (`daw-design`/`daw-wizard`). Consume the persisted proportional spec ([Workflow Artifacts §1–§2](../../references/workflow-artifacts.md)); parent records clear no-file requirements first, while ambiguity returns to design/clarification with no invented stage.
- **Concrete Scope & Disjoint Ownership (Contract §D):** Every task names exact target files, operations, and verification commands. Concurrent `[P]` / `parallel_safe: true` tasks MUST have strictly non-overlapping write sets AND zero shared data/runtime dependencies; else serialize or extract prerequisites. Independent authorized work proceeds while blocked work halts.
- **DAG Integrity & Infrastructure Justification (Contract §D):** Tasks form a strict DAG (cycles or unknown IDs block planning); dependencies precede consumer slices. Storyless foundational/infra tasks require explicit `infrastructure_justification` showing downstream slice dependence.
- **Traceability & Evidence Distinction (Contract §D, §I):** Map `requirement/AC -> story (where relevant) -> task IDs -> file paths -> deps -> exact verification/expected -> observed evidence/status` with exact source refs/revisions and parent acceptance separate from worker outcomes. Map every buildable AC (many-to-one allowed); `N/A` requires explicit justification (non-buildable, post-launch KPI, out-of-scope); unmapped criteria stay explicit gaps. Evidence remains empty/null until executed — commands and checkboxes are not proof.
- **Saved Plan, Header & Vertical Slices (Contract §D):** Save multi-step plans before build dispatch (`details` carries plan/progress refs; outer schema unchanged; native todos complement, never replace). Fix `details.plan_header` (mirrored in `roadmap.md`) before tasks: Goal, Architecture (2–3 sentences), Tech Stack, Global Constraints (verbatim 1 line each from spec/config), File Map. Cut P1-first vertical slices (narrow end-to-end paths, independently demoable, 1 fresh context each; `What to build` + `Out of scope`; `P1 alone is demoable: <independent test>`; wide mechanical refactors use expand -> migrate batches -> contract). Forbid layer-only tasks ("create all tables", "all endpoints") and standalone "write tests for X" tasks.
- **Missing-Artifact Hard Stop & Autonomy:** Spec-dependent build without a saved plan (header, slices, ordered steps, commands) halts as `status: blocked` (milestone roadmap != plan; tiny carve-out unchanged). Every task/slice declares `autonomy: hitl|afk`; no `afk` task may depend on an open `hitl` decision.
- **UI Mockup Gate:** UI tasks MUST consume matching rendered mockup refs or mark UI scope blocked ([Workflow Artifacts §5](../../references/workflow-artifacts.md#5-mockup-timing-proof--na)); no silent text fallback.
- **Ranked Queue & Local Tooling Boundary (Contract §I):** Returned results feed parent-owned [Ranked Result Triage](../../references/operations.md#ranked-result-triage) (preserve stable IDs/retry history, merge duplicates, no auto-deploy). Reuse project-local templates, commands, and tracking without external skills/platforms. One-off tasks carry commands/tools, expected results, done criteria, and rollback where relevant. Real surface actions are permitted for UI checks (`verification_command` preserved where needed; no invented binary; printing a check != execution; local overrides cannot weaken safety/AC/test gates). Never create external issues/PRs or deploy without explicit authorization.
- **Readiness Self-Check & Prebuild Review (Contract §F):** Run internal self-check before submission. Spec-dependent workflows trigger parent-directed read-only `daw-review` prebuild conformity check before `daw-build` (or explicit direct fallback with documented limits; never an invented reviewer); does not replace postbuild audit.
- **Convergence Reconciliation (Contract §G):** On re-plan/drift, inspect code + contracts + evidence; classify items (`Implemented & Verified`, `Implemented (Unverified)`, `Missing`, `Contradicted`, `Blocked`). Preserve existing IDs/history, merge duplicates, append only genuine in-scope gaps (no scope expansion), invalidate affected review/runtime acceptance proportionally, and respect bounded retry limits.
- **No Unwanted Commits/Hooks & Transition Gate:** Never run git commits, pushes, or hook edits. Spec-dependent plans require upstream specs to pass `review-ready` (`python3 scripts/validate.py docs RECORD --project-root ROOT --transition review-ready --documents PATH [PATH ...] --format text|json`) — a deterministic CLI, not a hook/daemon; halt `status: "blocked"` if Python 3 is unavailable. Complies with [Feature Delivery Contract](../../references/document-quality.md#feature-delivery-contract).

---

## 2. Inputs & Prerequisites

- **Specs & Ledger:** Upstream design/user requirements, non-goals, invariants, and persisted proportional spec ([Workflow Artifacts §1–§2](../../references/workflow-artifacts.md)) with exact source refs/revisions (parent records clear no-file requirements first; ambiguity returns to design/clarification). For spec-dependent tasks, `python3 scripts/validate.py ledger <spec_dir>/ledger.json --project-root <ROOT>` must pass with dependent specs `ready` on current hashes (`ledger_doc_drift`, `ledger_record_mismatch`, `ledger_state_mismatch` -> rework/re-review before planning). Ref: [Document Quality](../../references/document-quality.md) and `references/document-quality-rubric.json`.
- **UI, Code & Workspace State:** UI tasks require matching rendered mockup refs ([Workflow Artifacts §5](../../references/workflow-artifacts.md#5-mockup-timing-proof--na)). For re-planning, inspect current code tree, prior plan/ledgers, and latest verification results. Read-only workspace check identifies target files, configs, test runners, and uncommitted changes to preserve.
- **Config & Coupling:** Prefer values from `<!-- daw-config:start -->` in `AGENTS.md`/`CLAUDE.md` (`spec_dir`, `test_command`, `lint_command`, `build_command`, `workspace`, `high_risk_paths`) before inferring conventions (hints only; risk gating applies). Read [Change Coupling](../../references/change-coupling.md) only for structural refactors or cross-module boundary shifts.
- **Canonical Root & Governance Loading:** Resolve THIS `SKILL.md` symlink to its physical file (`../..` = suite root; halt `blocked` if unresolvable, never scan parent dirs). Before phase work, load root governance (`../../SKILL.md` §4/§6) and routing (`../../references/routing.md` §5/§6); before writes, load `../../references/operations.md` §1/§2 (halt `blocked` on unknown risk/scope or missing high-risk approval; planning needs no prod credentials).
- **Worker Graphs & Native Tracker Binding:** Parent records role-to-worker IDs, mandatory deps, write ownership, rounds, and artifact revisions in the plan/handoff per [persistent worker graph contract](../../references/operations.md#persistent-worker-graphs-harness-native), [Parent Acceptance Checkpoint](../../references/operations.md#parent-acceptance-checkpoint), [Checkpoint Boundaries](../../references/operations.md#checkpoint-boundaries), and optional [Parent-Owned Acceptance Record](../../references/operations.md#parent-owned-acceptance-record) (auto-retain same-role workers when supported unless opted out, else explicit fresh-worker handoff). Discover harness tracker/scheduler per [Native Workflow Tracking & Scheduling](../../references/operations.md#native-workflow-tracking-and-scheduling) (bind task IDs for progress only; worker `done` != parent `accepted`; fallback to structured records without creating external issues).

---

## 3. Operational Steps

### Step 1: Workspace State & Blast Radius Inspection

1. Verify target source files, configs, and tests exist.
2. Record pre-existing uncommitted changes to preserve them.
3. Identify available test runners (`pytest`, `npm test`, etc.) and linters.

### Step 2: Requirements Inventory & Traceability Setup (Contract §D)

1. Consume and record exact source refs/revisions of the persisted proportional spec (parent records clear no-file requirements first; planner invents no design/business choices).
2. **Conditional ERD Traceability:** Consume design `details.erd_selection`. If `selected: true`, bind its ref + revision and map `erd-01..03` criteria (entities/identity/attributes; relationships/cardinality/ownership; integrity/lifecycle/traceability/physical design) under Step 2.3 without inventing schema/migrations (Blueprint/FRD/techstack links stay traceability edges). If `selected: false`, record the scoped skip/reuse ref — never leave unrecorded or force ERD tasks.
3. Extract stable IDs (`FR-###`, `AC-###`, `ROAD-###`, plus ERD criteria if selected); create scoped IDs only if absent.
4. Build bidirectional traceability: `Requirement / AC ID -> User Story (where relevant) -> Task ID(s) -> Target File Paths -> Dependencies -> Verification / Expected Outcome -> Current Observed Evidence / Status` (parent decision separate from worker status).
5. Enforce `N/A` rule: mark `N/A` only with explicit reasoned justification; UI tasks without matching rendered mockup refs block only UI scope; missing mappings remain explicit gaps.
6. Exclude post-launch business KPIs from build/runtime AC unless bounded by a measurable harness.

### Step 3: Task Decomposition, Slicing & Infrastructure Justification (Contract §D)

#### Step 3A: Lifecycle Route Entries (refactor / maintain)

- **Refactor:** One task per safe structural step (rename, extract, move, split) in `daw-untangle` order, each with a `behavior_preservation_oracle` (characterization suite/probe proving identical before/after behavior). Never bundle behavior changes; halt and return to parent if an oracle fails.
- **Maintain:** One dependency group per task/commit ordered by risk (patch -> minor -> major), starting with upstream changelog/breaking-change check and attaching per-group rollback (revert commit + lockfile).
- **Ship handoff & Time-box:** Every code-changing route recommends terminal `ship` to parent (never dispatch `daw-ship` or run git here). Assign each task a `timebox`; on expiry `daw-build` escalates per [Time-Boxing & Escalation Budgets](../../references/developer-lifecycle.md#2-time-boxing--escalation-budgets).

1. Cut P1-first vertical story slices (end-to-end `What to build` + `Out of scope`, independently demoable, 1 fresh context; `P1 alone is demoable: <independent test>`; wide mechanical refactors use expand -> migrate batches -> contract; tiny patches stay inline). Forbid layer-only tasks and standalone test tasks.
2. Name exact create/modify/delete target files per task (many-to-one criteria mapping allowed).
3. **Supporting Infrastructure Justification:** Storyless infra/scaffolding tasks require explicit `infrastructure_justification` explaining downstream slice dependency.
4. **Coupling & Cohesion Alignment:** For refactors, consult `../../references/change-coupling.md` to avoid pass-through wrappers or split domain invariants.
5. **Plan Header & File Map:** Fix `details.plan_header` before tasks (Goal, 2–3 sentence Architecture, Tech Stack, verbatim 1-line Global Constraints from spec/config, File Map).
6. **Ordered Execution Steps:** Inside each task, list single-action steps (baseline suite green -> write failing test -> run, expect named failure -> minimal change -> run, expect pass -> suite), each naming `file`, `run`, and `expected` (evidence stays `null` until run).
7. **Bounded Contract Preview:** Contract-bearing tasks (schema DDL, migration, API payload/envelope, public signature) carry exact intended text in `change_preview` (full bodies stay in `daw-build`); quote data-model constraints (nullability, enums, limits, money units) verbatim in `constraints_quoted`.
8. **Autonomy:** Declare `autonomy: hitl|afk` per task/slice; no `afk` task depends on an open human decision.
9. **Task List:** Saved plans carry the runner-consumable list (pick one form per workflow, never mix):
   - **Task files (preferred):** one Markdown file per task in `<!-- daw-task-sources: <dir> -->`, frontmatter carrying machine fields (`task_id`, `title`, `autonomy`, `depends_on`, `parallel_safe`, `target_files`, `acceptance_criteria`, `verification_command`, `expected_outcome`) and prose body stating `What to build`, `Out of scope`, and boundary reasoning for fresh workers. Derive the plan's JSON manifest after writing task files and validate (re-derive on `manifest_drift` rather than hand-editing):
     ```bash
     python3 "$SUITE_ROOT/scripts/derive_tasks.py" --plan <plan-path> \
       --project-root "$PROJECT_DIR" --write
     python3 "$SUITE_ROOT/scripts/validate.py" tasks <plan-path> \
       --project-root "$PROJECT_DIR"
     ```
   - **Embedded manifest:** one fenced ` ```json ` block immediately after `<!-- daw-task-manifest -->` with matching field names when no task files exist. Contract: [Deterministic Execution Runner](../../references/execution-runner.md).

### Step 4: Sequence Dependencies, Concurrency & Parallel Criteria [P] (Contract §D)

1. Form a strict DAG; land shared contracts/migrations/interfaces before consumers.
2. Sequence dependencies strictly before dependent slices.
3. Reject cycles or unknown task IDs (`status: "blocked"`); independent authorized tasks proceed.
4. Mark `[P]` / `parallel_safe: true` ONLY when BOTH hold: (a) strictly disjoint target file write sets, and (b) zero shared runtime/data/schema/cache dependencies.
5. Serialize or factor shared targets/state into a prerequisite task.

### Step 5: Define Acceptance Criteria, Verification Commands & Oracles (Contract §D, §I)

1. Pair every task AC with its expected result and check method upfront.
2. Use deterministic, non-interactive local verification (e.g. `pytest tests/test_feature.py`, `npm test`), exact invocations (no invented binary), and rollback where relevant for one-off tasks; real surface actions are permitted for UI checks (`verification_command` kept as ref/action).
3. Include negative verification cases where appropriate.
4. Keep `evidence: null` until executed; planned commands/expected outcomes/checkboxes are not proof.

### Step 6: Plan Readiness Self-Check (Contract §F)

Verify and record in `details.readiness_self_check`:
1. **Coverage Check:** 100% of requirement/AC IDs (and `erd-01..03` when ERD selected, or recorded skip/reuse) mapped or justified `N/A`.
2. **Orphan Task Check:** Every task links to an AC/story or has `infrastructure_justification`.
3. **Graph Integrity Check:** Zero dependency cycles or unknown IDs.
4. **Parallel Safety Check:** All `[P]` / `parallel_safe` tasks have disjoint write sets and zero runtime/data dependencies.
5. **Verification Coverage:** Every task has a non-interactive local command and expected oracle.
6. **Placeholder Scan:** Zero placeholders (`TBD`/`TODO`/`"add appropriate error handling"`/`"handle edge cases"`/`"write tests for the above"`/`"similar to TASK-n"`) and no prose-only `"tests pass"` gate without a command.
7. **Name/Type Consistency:** Every named entity, field, type, and function exists in the cited spec/ERD or an earlier task with identical spelling.
8. **Gate Concreteness:** Both `verification_command`/`expected_outcome` and every `steps` entry (`run` + `expected`) state decided outcomes — no hedged outcomes (`"fail or pass — record which"`, `"may fail"`); characterization tests on existing behavior expect PASS, red steps name the exact missing-behavior failure reason.
9. **Autonomy Check:** Every task has `autonomy: hitl|afk`; no `afk` task depends on an open human decision.

### Step 7: Convergence Reconciliation & Scope Preservation (Contract §G)

1. Inspect actual code, authoritative contracts, and current evidence.
2. Classify items: `Implemented & Verified`, `Implemented (Unverified)`, `Missing`, `Contradicted`, or `Blocked`.
3. Preserve existing task IDs and retry history; never renumber/delete pending or completed IDs; merge duplicate findings instead of repeating identical tasks.
4. Append new tasks ONLY for genuine uncovered in-scope gaps (never expand scope).
5. **Ranked Queue:** Feed results to parent-owned [Ranked Result Triage](../../references/operations.md#ranked-result-triage); parent selects eligible fixes without auto-dispatch/auto-deploy.
6. Record state in `details.convergence`.

### Step 8: Synthesize Implementation Contract & Prebuild Review Handoff (Contract §F)

1. For multi-step authorized work, save the plan per [Workflow Artifacts](../../references/workflow-artifacts.md) (`docs/daw/plans/<workflow-id>.md` or existing project doc/roadmap), including task files + derived manifest (Step 3 item 9), and record plan/progress refs in `details`. Native todos complement; tiny patches stay inline.
2. **Parent-Owned Independent Prebuild Readiness Review:** For spec-dependent workflows (`feature`, `bugfix`), recommend `handoff_to: "daw-review"` for proportional independent read-only conformity review before `daw-build`.

---

## 4. Output Contract

Deliver an observable JSON handoff per [routing §5](../../references/routing.md#5-canonical-module-handoff-contract) (with its transport hierarchy and labeled inline fallback; direct-user replies remain concise prose). `status: "pass"` proposes planning-stage readiness only, not prebuild/implementation/parent acceptance; cite current scope and revisions.

Required `details` fields:
- `tasks`: each entry MUST carry `task_id`, `title`, `target_files`, `depends_on`, `parallel_safe`, `autonomy` (`hitl|afk`), `acceptance_criteria`, `verification_command`, `expected_outcome`, `steps` (`[{action, file, run, expected}]`), `change_preview` (exact contract text for schema/API/signature tasks, else `null` with reason), `constraints_quoted` (verbatim data-model constraints), `interfaces` (`{consumes, produces}` — exact signatures/types neighboring tasks rely on, no duplicated code), plus `infrastructure_justification` if storyless, rendered mockup refs (or blocked UI scope) for UI checks, and lifecycle fields (`timebox`, `behavior_preservation_oracle` for `refactor`, dependency group / `lockfile_committed` / rollback for `maintain`, and recommended terminal `ship` route for code-changing routes).
- `saved_plan_ref` & `saved_progress_ref` (for multi-step work), `ranked_queue_ref`, `plan_header` (`goal`, `architecture` in 2–3 sentences, `tech_stack`, verbatim 1-line `global_constraints` from spec/config, and `file_map`, mirrored in `roadmap.md`; tiny patches stay inline with no header), `traceability` (consuming `details.erd_selection` verbatim), `readiness_self_check`, `convergence`, and `suite_verification_command`.

Illustrative `details` only (wrap in the canonical outer envelope):

```json
{
  "route": "feature",
  "execution_mode": "Sequential",
  "saved_plan_ref": "docs/daw/plans/<workflow-id>.md @ <revision>",
  "saved_progress_ref": "docs/daw/workflows/<workflow-id>.md @ <revision>",
  "spec_source_ref": "docs/specs/<workflow-id>.md @ <revision>",
  "ranked_queue_ref": "docs/daw/plans/<workflow-id>.md#ranked-result-triage",
  "plan_header": {
    "goal": "Rotate session tokens on refresh without invalidating unrelated sessions",
    "architecture": "SessionSerializer carries a token_version through refresh; the refresh route mints and validates the rotated pair.",
    "tech_stack": "Python 3, pytest",
    "global_constraints": ["pytest tests/auth/ — 0 exit code required"],
    "file_map": [
      {
        "path": "src/auth/serializer.py",
        "op": "modify",
        "responsibility": "SessionSerializer token_version round-trip"
      },
      {
        "path": "tests/auth/test_session_serializer.py",
        "op": "modify",
        "responsibility": "serializer regression tests"
      },
      {
        "path": "src/auth/routes.py",
        "op": "modify",
        "responsibility": "POST /api/v1/auth/refresh endpoint"
      },
      {
        "path": "tests/auth/test_routes.py",
        "op": "modify",
        "responsibility": "refresh endpoint tests"
      }
    ]
  },
  "tasks": [
    {
      "task_id": "TASK-01",
      "title": "Implement session version rotation in serializer",
      "target_files": [
        "src/auth/serializer.py",
        "tests/auth/test_session_serializer.py"
      ],
      "depends_on": [],
      "parallel_safe": false,
      "autonomy": "afk",
      "infrastructure_justification": null,
      "acceptance_criteria": [
        "SessionSerializer exports token_version field round-trip"
      ],
      "verification_command": "pytest tests/auth/test_session_serializer.py",
      "expected_outcome": "Tests pass with 0 exit code",
      "steps": [
        {
          "action": "Run baseline suite",
          "file": "tests/auth/test_session_serializer.py",
          "run": "pytest tests/auth/test_session_serializer.py",
          "expected": "0 failures on current revision"
        },
        {
          "action": "Write failing round-trip test for token_version",
          "file": "tests/auth/test_session_serializer.py",
          "run": "pytest tests/auth/test_session_serializer.py",
          "expected": "1 failure: token_version missing"
        },
        {
          "action": "Add token_version to SessionSerializer",
          "file": "src/auth/serializer.py",
          "run": "pytest tests/auth/test_session_serializer.py",
          "expected": "all pass, 0 exit code"
        }
      ],
      "change_preview": "class SessionSerializer: token_version: int",
      "constraints_quoted": []
    },
    {
      "task_id": "TASK-02",
      "title": "Add token refresh API endpoint",
      "target_files": ["src/auth/routes.py", "tests/auth/test_routes.py"],
      "depends_on": ["TASK-01"],
      "parallel_safe": false,
      "autonomy": "afk",
      "infrastructure_justification": null,
      "acceptance_criteria": [
        "POST /api/v1/auth/refresh returns 200 with rotated tokens"
      ],
      "verification_command": "pytest tests/auth/test_routes.py",
      "expected_outcome": "Endpoint tests pass with 200 OK on token refresh",
      "steps": [
        {
          "action": "Write failing refresh test",
          "file": "tests/auth/test_routes.py",
          "run": "pytest tests/auth/test_routes.py",
          "expected": "1 failure: POST /api/v1/auth/refresh 404"
        },
        {
          "action": "Add refresh route returning rotated tokens",
          "file": "src/auth/routes.py",
          "run": "pytest tests/auth/test_routes.py",
          "expected": "all pass, POST returns 200 with rotated tokens"
        }
      ],
      "change_preview": "POST /api/v1/auth/refresh -> 200 {access_token, refresh_token}",
      "constraints_quoted": []
    }
  ],
  "traceability": [
    {
      "requirement_id": "REQ-AUTH-01",
      "story_id": "US-01",
      "task_ids": ["TASK-01"],
      "target_files": [
        "src/auth/serializer.py",
        "tests/auth/test_session_serializer.py"
      ],
      "dependencies": [],
      "verification_command": "pytest tests/auth/test_session_serializer.py",
      "expected_outcome": "SessionSerializer exports token_version field",
      "status": "pending",
      "evidence": null,
      "parent_decision": null
    },
    {
      "requirement_id": "REQ-AUTH-02",
      "story_id": "US-02",
      "task_ids": ["TASK-02"],
      "target_files": ["src/auth/routes.py", "tests/auth/test_routes.py"],
      "dependencies": ["TASK-01"],
      "verification_command": "pytest tests/auth/test_routes.py",
      "expected_outcome": "POST /api/v1/auth/refresh returns 200",
      "status": "pending",
      "evidence": null,
      "parent_decision": null
    }
  ],
  "readiness_self_check": {
    "status": "pass",
    "unmapped_criteria": [],
    "orphan_tasks": [],
    "dependency_cycles": [],
    "parallel_violations": [],
    "findings": []
  },
  "convergence": {
    "mode": "initial",
    "appended_task_ids": [],
    "preserved_task_ids": ["TASK-01", "TASK-02"]
  },
  "suite_verification_command": "pytest tests/auth/"
}
```

---

## 5. Verification & Quality Invariants

- [ ] Exact target files and concrete operations specified for every task.
- [ ] Saved plan carries runner-consumable task files (`What to build` + `Out of scope`), manifest derived via `derive_tasks.py --write`, and `validate.py tasks` clean.
- [ ] Persisted proportional spec consumed with source refs/revisions; clear no-file requirements parent-recorded; no invented design/stage.
- [ ] `saved_plan_ref` and `saved_progress_ref` in `details` for multi-step work (tiny patches inline); no separate task tracker.
- [ ] Bidirectional traceability for every AC (and `erd-01..03` if selected, or reasoned ERD skip/reuse); parent decision separate from worker status.
- [ ] UI tasks carry matching rendered mockup refs or block only UI scope; real surface action permitted where shell checks are fake.
- [ ] Storyless infra tasks carry `infrastructure_justification` (Contract §D).
- [ ] Acyclic DAG verified; dependencies precede consumer slices; `[P]`/`parallel_safe` tasks have disjoint write sets and zero runtime/data dependencies (Contract §D).
- [ ] Non-interactive verification commands (no invented binary) and expected oracles on every task (`evidence: null` until run; one-off tasks include commands/tools, expected results, done criteria, rollback; Contract §D, §I).
- [ ] Results feed parent-owned [Ranked Result Triage](../../references/operations.md#ranked-result-triage); IDs/history preserved, duplicates merged, no auto-deploy.
- [ ] `details.readiness_self_check` recorded; no layer-only or standalone test tasks; slices state `What to build` + `Out of scope`; every task carries `autonomy: hitl|afk` with no `afk` depending on open `hitl` (Contract §F).
- [ ] Recommends parent-directed `daw-review` prebuild readiness review for spec-dependent builds (Contract §F).
- [ ] Convergence reconciliation preserves IDs/history, merges duplicates, and appends only genuine in-scope gaps (Contract §G); pre-existing uncommitted changes preserved; no unwanted docs created.
- [ ] Evidence mapping aligns with [Parent Acceptance Checkpoint](../../references/operations.md#parent-acceptance-checkpoint) and [Checkpoint Boundaries](../../references/operations.md#checkpoint-boundaries) (workers observe, parent decides).

---

## 6. Stop / Replan Triggers

Advisory triggers returned to parent (`daw-plan` never invokes modules directly):

- **Missing Interface / Spec Gap:** Halt (`status: "blocked"`, `handoff_to: null`) and recommend `daw-design`.
- **Dependency Cycle / Unknown ID:** Halt (`status: "blocked"`, `handoff_to: null`) and report cycle in `details.readiness_self_check`.
- **File Ownership / Data Collision:** Serialize overlapping tasks or extract shared parts into a prerequisite task.
- **Unmapped Criteria Gap:** Halt (`status: "blocked"`) and return gaps to parent.
- **Missing Plan Artifact:** Spec-dependent build without saved plan (header, slice checkpoints, ordered steps, run+expected gates) halts (`status: "blocked"`, `handoff_to: null`).
- **Downstream Execution Failure:** Halt failed slice and recommend `daw-debug` or slice replan.

---

## 7. Handoff Protocol

Advisory `handoff_to` for parent orchestrator (never invoke modules or subagents directly):

- **`bootstrap` / `adopt`:** Terminal (`handoff_to: null`, `status: "pass"`); do not recommend `daw-build`.
- **`patch`:** Direct (`handoff_to: "daw-build"`); tiny inline patches need no prebuild readiness review.
- **`feature` / `bugfix`:** Recommend `daw-review` for spec-dependent prebuild readiness review (or next active route stage), preserving review/verify ordering.
- **`refactor` / `maintain`:** After `daw-review` readiness checkpoint, recommend `daw-build` (`daw-build` -> `daw-review` -> `daw-verify`) and record terminal `ship` recommendation.

_Reference Link:_ [Feature Delivery Contract](../../references/document-quality.md#feature-delivery-contract), [Shared Routing Contract](../../references/routing.md), [Parent Acceptance Checkpoint](../../references/operations.md#parent-acceptance-checkpoint), [Checkpoint Boundaries](../../references/operations.md#checkpoint-boundaries), and [Parent-Owned Acceptance Record](../../references/operations.md#parent-owned-acceptance-record).
