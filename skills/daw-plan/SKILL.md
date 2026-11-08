---
name: daw-plan
description: "Deterministic implementation planning and task decomposition: maps concrete ordered tasks, explicit file ownership, dependencies, acceptance criteria, time-box estimates, and verification gates without unwanted document churn."
---

# DAW Plan (`daw-plan`)

The planning module converts design specifications, architectural requirements, or direct change requests into concrete, ordered, and verifiable implementation tasks. It defines strict file ownership boundaries, sequences dependencies, and attaches measurable Acceptance Criteria (AC) and verification commands to every task.

**Invariant:** Keep plans actionable, bounded, and lean. For multi-step authorized work, the plan MUST be saved before build dispatch per [Workflow Artifacts: Specification, Plan, Progress & Mockup Contract](../../references/workflow-artifacts.md); a chat payload or native todo alone is insufficient. Tiny settled patches retain the proportional no-document path. Do not create plan sprawl or unwanted git commits.

---

## 1. Trigger & Scope

- Transitioning from design (`daw-design`) to implementation.
- Planning the `refactor` route: sequence behavior-preserving structural steps with their characterization oracles (see [Behavior-Preserving Refactor Protocol](../../references/developer-lifecycle.md#4-behavior-preserving-refactor-protocol)).
- Planning the `maintain` route: dependency upgrade order (one dependency group at a time) with per-group rollback steps (see [Dependency & Maintenance Upgrade Protocol](../../references/developer-lifecycle.md#5-dependency--maintenance-upgrade-protocol)).
- Decomposing a multi-step engineering task, refactoring, or bug fix into execution slices.
- Structuring subagent task distributions for sequential or staged parallel execution.

### Non-Goals & Invariants

- **No Document Sprawl & Authoring Boundaries:** Apply the Documentation Authoring Contract (`../../references/routing.md` §3). `daw-plan` owns tactical task decomposition, sequencing, disjoint file boundaries, and verification commands. It does not author architecture specifications. Before tactical decomposition, consume the current persisted proportional specification per [Workflow Artifacts §1–§2](../../references/workflow-artifacts.md). If clear requirements have no file, the authorized parent records them first; the planner MUST NOT invent design or insert a new stage. Ambiguity returns to the existing design/clarification route. When updating persistent tracking, `daw-plan` owns tactical task updates and milestone progress in `roadmap.md` while strategic phasing remains authored by `daw-design`/`daw-wizard`.
- **Concrete Scope:** Every task must specify exact file paths, operations, and verification commands.
- **Disjoint File Ownership & Parallel Criteria (Contract §D):** Concurrent tasks must have strictly non-overlapping file write sets AND no shared data or runtime dependency. Parallel marker `[P]` (or `parallel_safe: true`) is permitted only when both conditions hold. Shared files or runtime state must be serialized or factored into prerequisite tasks. Independent authorized work continues while blocked work halts.
- **Dependency Graph Integrity (Contract §D):** The plan forms a strict Directed Acyclic Graph (DAG). Dependency cycles or references to unknown task IDs are fatal planning errors. All dependencies must precede consumer story slices.
- **Traceability & Task Contract (Contract §D):** Every task must maintain explicit traceability: `requirement/AC -> story (where relevant) -> task IDs -> file paths -> deps -> exact verification/expected outcomes -> current observed evidence/status`, with exact source refs and source revisions, and stable IDs mapped bidirectionally to tasks/files/deps/verification. Parent acceptance is recorded separately from worker outcomes. Every buildable criterion must be mapped; unmapped criteria are explicit gaps, never assumed as implicit N/A. `N/A` is valid only with explicit reasoned justification (e.g., non-buildable outcome, post-launch metric, or documented out-of-scope). A task may cover multiple criteria without artificial 1-to-1 mapping.
- **Supporting Infrastructure Justification (Contract §D):** A foundational or infra task lacking a user story is permitted ONLY when accompanied by an explicit, verified prerequisite justification explaining why downstream story slices depend on it.
- **Evidence vs. Command Distinction (Contract §D, §I):** Evidence references remain empty or unexercised until verification commands run and outcomes are observed. Planned verification commands or task checkboxes are NOT proof of completion.
- **Saved Plan & Artifact Reference:** Multi-step plans are saved per [Workflow Artifacts](../../references/workflow-artifacts.md) before build dispatch. Include saved plan/progress refs in existing `details` without changing the outer JSON schema. Native todos complement durable artifacts; no separate task tracker is created. Tiny settled patches stay inline.
- **UI Task Mockup Gate:** A UI task MUST consume matching rendered mockup refs or mark UI scope blocked. No silent text fallback for material missing direction; see [Workflow Artifacts §5](../../references/workflow-artifacts.md#5-mockup-timing-proof--na).
- **Ranked Queue & Local Tooling Boundary (Contract §I):** Recovered results enter the parent-owned [Ranked Result Triage](../../references/operations.md#ranked-result-triage) queue — parent picks eligible fixes by urgency/impact/deps and accepted joins. Planner preserves stable IDs/retry history and merges duplicates. No automatic external deploy occurs from worker pass. For one-off execution include commands/tools, expected results, done criteria, and rollback only where relevant. Discover and reuse bounded repeat tooling; no unsolicited automation. A real surface action is permitted for UI checks; legacy `verification_command` is preserved only as a reference/action where needed. Exact invocation uses no invented binary. Local overrides cannot weaken canonical safety, acceptance, or test gates.
- **Plan Readiness Self-Check (Contract §F):** Before finalizing the plan, `daw-plan` performs an internal readiness self-check verifying task completeness, cycle-free dependencies, disjoint parallel boundaries, justified infrastructure tasks, and executable local commands.
- **Parent-Owned Independent Prebuild Conformity Review (Contract §F):** In feature or spec-dependent workflows, plan delivery triggers a parent-owned independent read-only conformity review (using `daw-review` under parent orchestration as a bounded prebuild checkpoint without declaring code audit or completed route stage, and without module recursion) before `daw-build` is dispatched. If no independent review capability is available, an explicit direct fallback with documented evidence limits must be used (never an invented reviewer). This prebuild check verifies cross-artifact consistency (scope, governance, requirements, stories, design, plan, tasks) and does NOT replace mandatory postbuild technical audit.
- **Convergence Reconciliation & Scope Preservation (Contract §G):** When re-planning or reconciling drift (e.g. re-entering from review/verify or during code adoption): inspect actual code + authoritative contracts + current evidence. Classify items into `Implemented & Verified`, `Implemented (Unverified)`, `Missing`, `Contradicted`, or `Blocked`. Source existence, passing old tests, or task checkboxes alone are NEVER completion proof. Plan updates preserve existing stable IDs and history; never duplicate pending tasks or repeat identical missing work; append only genuine uncovered work inside accepted scope (no scope expansion). Changes to specs, code, or environment invalidate affected prior review/runtime acceptance; rerun proportionally. Bound repair rounds by existing retry rules to prevent endless loops.
- **Local Tooling & Integration Boundary (Contract §I):** Planning reuses project-local templates, tracking issues, discovered commands, and capabilities without requiring external skills or proprietary platforms. A real surface action is permitted for UI checks while legacy `verification_command` is preserved only as a reference/action where needed; exact invocation uses no invented binary. Merely printing a hook/check command is not execution. Local overrides cannot weaken canonical safety, acceptance, or test gates. No automatic external issue creation, PR generation, or deployment without explicit user authorization.
- **No Unwanted Commits or Git Hooks:** Planning never runs git commits, pushes, or alters hooks.
- **Workflow Transition Gate vs. Hook Claims:** Spec-dependent planning tasks require upstream specifications to have passed the `review-ready` workflow transition gate (`python3 scripts/validate.py docs RECORD --project-root ROOT --transition review-ready --documents PATH [PATH ...] --format text|json`). The gate is a deterministic CLI utility, not an automatic daemon or harness hook interceptor. Trivial inline tasks or bug fixes do not require a mandatory full-catalog bundle or document-quality JSON records. If Python 3 is unavailable, halt with canonical `status: "blocked"` (never emit a fake pass).
- **Canonical Procedural Contract:** Procedures comply with [Canonical Document Quality & Workflow Transition Specification: Feature Delivery Contract](../../references/document-quality.md#feature-delivery-contract).

---

## 2. Inputs & Prerequisites

- **Design Contracts / Requirements:**
  - Upstream design from `daw-design` or direct user requirements.
  - Specified non-goals and system invariants.
  - Current persisted proportional specification per [Workflow Artifacts §1–§2](../../references/workflow-artifacts.md), with exact source refs and revisions. If clear requirements have no file, parent records them first; planner does not invent architecture or business choices. Ambiguity returns to design/clarification.
  - Upstream specification workflow transition verification: For spec-dependent tasks, verify that the required upstream specifications passed the `review-ready` transition on their current revision. If specifications were modified after review, the cached verdict is invalid due to SHA-256 mismatch, requiring rework re-entry and review re-evaluation before planning commences.
  - UI tasks consume matching rendered mockup refs where required; missing material direction blocks only UI scope. See [Workflow Artifacts §5](../../references/workflow-artifacts.md#5-mockup-timing-proof--na).
  - Reference [Canonical Document Quality & Workflow Transition Specification](../../references/document-quality.md) and `references/document-quality-rubric.json` for document quality standards.
- **Code & Contract Prerequisites vs. Runtime Evidence:**
  - Upstream requirements, user stories, acceptance criteria IDs, schemas, and blueprint interfaces are design-time contract specifications.
  - Runtime verification evidence is strictly unexercised at planning time; planned commands, expected outcomes, and task checkboxes do not constitute evidence until executed.
- **Convergence Context (for Re-planning / Drift Reconciliation):**
  - When re-planning or reconciling drift, inspect the current code tree, previous plan/task ledgers, and latest verification results. Reconcile differences against authoritative contracts.
- **Workspace State:**
  - Target source files, configuration files, and test runners identified via read-only inspection.
  - Identified pre-existing uncommitted modifications (must be preserved).
- **Configuration Block Consumption Rule:** Before inferring conventions, read the `<!-- daw-config:start -->` block in root `AGENTS.md` / `CLAUDE.md` if present and prefer its values (`spec_dir`, `test_command`, `lint_command`, `build_command`, `workspace`, `high_risk_paths`); fall back to current project convention inference when absent. Values are hints, never authorization: risk gating still applies.
- **Structural Boundary Reference:** Read [Change Coupling & Structural Analysis Reference](../../references/change-coupling.md) ONLY when planning structural refactoring or cross-module boundary shifts to ensure task slices align with genuine change boundaries.
- **Relative Reference Base & Canonical Path Resolution:**
  - When loaded via symlink or alias (e.g. `~/.agents/skills/daw-plan`), resolve THIS `SKILL.md` symlink to its physical/canonical target file first.
  - The suite root is the canonical module directory's `../..`.
  - Use the host environment's resolved path; when shell `realpath` is unavailable, use the host file system's native target resolution. If the target cannot be resolved, report a blocked dependency rather than scanning parent or unrelated directories.
- **Mandatory Governance Loading:**
  - Before executing any phase work, load root governance (`../../SKILL.md` §4 Safety & §6 Handoff Contract Schema) and canonical routing (`../../references/routing.md` §5 & §6). Reading governance documentation is not recursive router execution.
  - Before performing any state mutations or file writes, load `../../references/operations.md` §1 Preflight Safety & §2 High-Risk Approvals.
  - Unknown risk, ambiguous target/scope, or missing required high-risk interactive approval/preflight must immediately transition to `blocked` before mutating files. Planning and task decomposition require no production credentials.
- For worker graphs, the parent records role-to-worker IDs, mandatory dependencies, write ownership, rounds and artifact revisions in the existing plan/handoff. Reuse is same-role only and introduces no required configuration keys. Follow the [persistent worker graph contract](../../references/operations.md#persistent-worker-graphs-harness-native) and the [Parent Acceptance Checkpoint](../../references/operations.md#parent-acceptance-checkpoint) across [Checkpoint Boundaries](../../references/operations.md#checkpoint-boundaries), optionally using a [Parent-Owned Acceptance Record](../../references/operations.md#parent-owned-acceptance-record). Parent authors acceptance decisions independently; workers supply observations. Small tasks track criteria inline without ceremony.
  - **Native Tracker/Scheduler Binding:** At intake, discover the actual harness-native task/todo tracker (or scheduler) from exposed tools/documentation and follow the canonical [Native Workflow Tracking & Scheduling](../../references/operations.md#native-workflow-tracking-and-scheduling) contract: bind stable plan task IDs to native refs for execution progress only; native todos complement durable artifacts and never replace the saved plan; parent acceptance remains authoritative in the structured plan/handoff per the [Parent Acceptance Checkpoint](../../references/operations.md#parent-acceptance-checkpoint); worker `done` is never parent `accepted`; when no tracker exists, use the structured-records fallback with no mandatory file. Planning does not create external issues or reset state.
  - Select retained workers automatically for already-justified delegated corrective rounds when the harness supports completed-worker continuation, unless the user opts out. Do not add delegation or review stages for retention; unsupported optional retention uses an explicit fresh-worker handoff, not a blocker.

## 3. Operational Steps

### Step 1: Workspace State & Blast Radius Inspection

1. Verify target source files, configs, and test files exist at expected locations.
2. Inspect and record pre-existing uncommitted changes to ensure they are preserved.
3. Identify existing test runners (`pytest`, `npm test`, etc.) and linters for verification gates.

### Step 2: Requirements Inventory & Traceability Setup (Contract §D)

1. Consume the current persisted proportional specification, reuse it when adequate, and record exact source refs and source revisions. If clear requirements have no file, the authorized parent records them first; planner invents no architecture or business choices.
2. **Conditional ERD Traceability:** Consume the design handoff's `details.erd_selection`. When an ERD was selected (`selected: true`), treat its ref + revision as a consumed source: include erd-01..03 criteria (entities/identity and sourced attributes; relationships/cardinality/optionality and ownership; integrity/lifecycle/traceability and applicable physical design) in the inventory and traceability map under Step 2.3, mapping each buildable criterion to task IDs/files/deps/verification — without inventing schema or migrations, and keeping Blueprint/FRD/techstack links as traceability edges, not duplicated authority. When ERD was skipped/reused (`selected: false`), the scoped reason/reuse ref is the mapping disposition — never leave it unrecorded and never force ERD tasks onto projects without an applicable persistent model.
3. Extract stable requirement and acceptance criteria identifiers (`FR-###`, `AC-###`, `ROAD-###`, plus erd criteria where selected) from upstream specifications or design contracts. Retain existing stable IDs; create scoped unique IDs only if absent.
4. Establish a compact bidirectional traceability mapping:
   `Requirement / AC ID -> User Story (where relevant) -> Task ID(s) -> Target File Paths -> Dependencies -> Verification / Expected Outcome -> Current Observed Evidence / Status`, with separate parent decision distinct from worker status.
5. Enforce the `N/A` rule: Mark an acceptance criterion `N/A` ONLY with an explicit, reasoned justification for non-buildable or documented out-of-scope criteria. A UI task without a matching rendered mockup ref marks only UI scope blocked. Missing mappings remain explicit gaps, NEVER implicit `N/A`.
6. Differentiate business outcomes/KPIs from build/runtime acceptance criteria: Exclude post-launch outcome metrics and business KPIs from build/runtime criteria unless bounded by a justified, measurable observation harness.

### Step 3: Task Decomposition, Slicing & Infrastructure Justification (Contract §D)

#### Step 3A: Lifecycle Route Entries (refactor / maintain)

- **Refactor entries:** One task per safe structural step (rename, extract, move, split) in the order produced by `daw-untangle`, each carrying a behavior-preservation oracle: the characterization suite or probe that proves identical observable behavior before and after. No step may bundle a behavior change; if an oracle fails mid-sequence, the plan halts at that step and returns to the parent.
- **Maintain entries:** Group upgrades by dependency (one group per task/commit), order groups by risk (patch-only first, then minor, then major), and attach per-group rollback steps (revert the group commit and lockfile) plus the upstream changelog/breaking-change check as the first task of each group.
- **Ship handoff:** Every code-changing route (`feature`, `bugfix`, `patch`, `refactor`, `maintain`) ends by recommending the `ship` route to the parent for commit hygiene, PR, and release readiness; `daw-plan` never dispatches `daw-ship` itself and never performs git operations.
- **Time-box:** Each task carries an estimate/timebox; on expiry `daw-build` escalates per [Time-Boxing & Escalation Budgets](../../references/developer-lifecycle.md#2-time-boxing--escalation-budgets) rather than extending silently.

1. Break work into discrete, bounded tasks representing independently demonstrable or testable behavior slices.
2. Explicitly name the exact target files to create, modify, or delete for each task. A task may satisfy several criteria; artificial one-to-one mapping is not required.
3. **Supporting Infrastructure Justification:** A foundational or infrastructure task (e.g., scaffolding, schema migrations, test harness setup) that lacks an associated user story is permitted ONLY when accompanied by an explicit prerequisite justification explaining why downstream story slices depend on it.

4. **Coupling & Cohesion Alignment:** When planning refactoring tasks, consult `../../references/change-coupling.md`: ensure task boundaries do not introduce needless pass-through wrappers or split cohesive domain invariants across arbitrary files; preserve existing behavioral invariants.

### Step 4: Sequence Dependencies, Concurrency & Parallel Criteria [P] (Contract §D)

1. Structure tasks into a strict Directed Acyclic Graph (DAG). Foundational contracts, migrations, and shared interfaces must land before consumers.
2. **Dependency Sequencing Rule:** Dependencies must strictly precede dependent story slices.
3. **Dependency Cycle & Unknown ID Rejection:** Detect and reject cyclic dependencies or references to unknown task IDs before dispatch. If a cycle or unknown dependency is detected, halt planning (`status: "blocked"`). Independent authorized tasks can proceed while blocked tasks wait.
4. **Parallelism Criteria `[P]`:** Mark tasks as parallel-safe (`[P]` or `parallel_safe: true`) ONLY when BOTH conditions are verified:
   - **Disjoint Write Sets:** Target files between parallel tasks must not overlap.
   - **Zero Shared Runtime/Data Dependencies:** Neither task depends on runtime state, schema modifications, or in-memory caches produced by the other.
5. If tasks share write targets or data dependencies, serialize them or extract shared components into a prerequisite task.

### Step 5: Define Acceptance Criteria, Verification Commands & Oracles (Contract §D, §I)

1. Pre-declare observable Acceptance Criteria (AC) for each task, pairing each criterion with its expected result and proportional check method before work begins.
2. Provide deterministic verification (e.g. `pytest tests/test_feature.py`, `npm test`) that runs non-interactively in the local environment. For one-off execution include commands/tools, expected results, done criteria, and rollback only where relevant. A real surface action is permitted for UI checks; legacy `verification_command` is preserved only as a reference/action where needed. Exact invocation uses no invented binary.
3. Include negative verification cases where appropriate.
4. **Evidence vs. Command Distinction:** Evidence references in the plan remain empty or null (`evidence: null`) until executed during build/verification. Planned commands, expected outcomes, or task checkboxes are NOT proof of completion.

### Step 6: Plan Readiness Self-Check (Contract §F)

Before finalizing the plan, perform an internal cross-artifact readiness self-check:

1. **Coverage Check:** Verify 100% of requirement / AC IDs are mapped to tasks (or explicitly justified as `N/A`). When an ERD was selected, its erd-01..03 criteria map to tasks or carry a reasoned non-mapping; an ERD skip/reuse disposition is recorded, never an unexamined gap.
2. **Orphan Task Check:** Verify every task links to an AC/story or carries an explicit infrastructure prerequisite justification.
3. **Graph Integrity Check:** Verify no dependency cycles and no dangling or unknown task dependencies exist.
4. **Parallel Safety Check:** Verify all tasks marked `[P]` / `parallel_safe` have strictly disjoint write sets and zero data/runtime dependencies.
5. **Verification Coverage:** Verify every task defines a non-interactive, executable local command and expected oracle.
   Record the self-check result in `details.readiness_self_check`.

### Step 7: Convergence Reconciliation & Scope Preservation (Contract §G)

When invoked to re-plan or reconcile gaps identified during execution, review, or verification:

1. Inspect the actual codebase, authoritative contracts, and current verification evidence.
2. Classify items into `Implemented & Verified`, `Implemented (Unverified)`, `Missing`, `Contradicted`, or `Blocked`.
3. **Preserve Existing IDs, Retry History & Merge Duplicates:** Do not renumber, delete, or rewrite completed or pending task IDs; preserve stable IDs and retry history; merge duplicate findings rather than creating duplicate pending tasks or repeating identical missing work.
4. **Append Only Genuine Gaps Inside Scope:** Append new tasks only for genuine uncovered work within accepted scope. Scope expansion or feature creep is strictly prohibited.
5. **Ranked Queue:** Returned results enter the parent-owned [Ranked Result Triage](../../references/operations.md#ranked-result-triage) queue; parent picks eligible fixes by urgency/impact/deps and accepted joins; planner does not auto-dispatch or auto-deploy from worker pass.
6. Record convergence state in `details.convergence`.

### Step 8: Synthesize Implementation Contract & Prebuild Review Handoff (Contract §F)

1. Format the plan into the standard output schema. For multi-step authorized work, save the plan before build dispatch per [Workflow Artifacts](../../references/workflow-artifacts.md) (existing roadmap/issue-export/project doc section if sufficient, otherwise `docs/plans/<workflow-id>.md`). Include saved plan/progress refs in existing `details` and keep examples consistent with the saved form. Native todos complement durable artifacts; no separate task tracker is created. Tiny settled patches stay inline.
2. **Parent-Owned Independent Prebuild Readiness Review:** For spec-dependent implementation workflows (`feature`, `bugfix`), `daw-plan` self-checks the plan and recommends `handoff_to: "daw-review"` (or parent readiness checkpoint) for a proportional independent read-only conformity review before `daw-build` execution begins.

---

## 4. Output Contract

Return a complete, observable JSON handoff before any transition using [routing §5: Canonical Module Handoff Contract](../../references/routing.md#5-canonical-module-handoff-contract), including its transport hierarchy and labeled inline fallback when no real structured transport or authorized artifact exists. Direct-user reports remain concise prose. `status: "pass"` proposes only planning-stage criteria and the internal readiness self-check, not independent prebuild acceptance, implementation/test completion, or parent acceptance; observations must identify current scope and revisions. Keep the planning payload under `details` as defined below.

- **Mandatory Task Fields:** Each task in `details.tasks` MUST specify `task_id`, `title`, `target_files`, `depends_on`, `parallel_safe`, `acceptance_criteria`, non-interactive `verification_command`, and `expected_outcome`. Legacy `verification_command` is a reference/action field; real surface action may serve the same check where a command would be fake. If a task checks the UI, it MUST carry matching rendered mockup refs or mark UI scope blocked. If a task lacks a user story, it must include `infrastructure_justification`.
- **Lifecycle fields (refactor / maintain):** Tasks carry `timebox` and, for refactor, the `behavior_preservation_oracle`; for maintain, the dependency group, `lockfile_committed`, and rollback step. Code-changing routes record the recommended terminal `ship` route for the parent.
- **Saved Plan & Progress Refs:** `details` MUST include `saved_plan_ref` and `saved_progress_ref` for multi-step work under [Workflow Artifacts](../../references/workflow-artifacts.md). Native todos complement durable artifacts; no separate task tracker is created. Tiny settled patches stay inline.
- **Traceability Mapping:** `details.traceability` records exact source refs and revisions with the compact bidirectional mapping from requirement/AC ID to user story, task IDs, target files, dependencies, verification/expected outcomes, status, evidence reference, and separate parent decision. It consumes the design `details.erd_selection` disposition verbatim: a selected ERD's ref + revision and erd-01..03 coverage, or the reasoned skip/N/A/reuse disposition — never invented schema or migrations.
- **Ranked Queue Ref:** `details` references the parent-owned [Ranked Result Triage](../../references/operations.md#ranked-result-triage) queue in the durable plan/progress record; planner does not auto-deploy from worker pass.
- **Readiness Self-Check:** `details.readiness_self_check` records the internal validation verdict (`pass` or `fail`), unmapped criteria, orphan tasks, dependency cycles, and parallel violations.
- **Convergence Metadata:** `details.convergence` records whether the plan is an initial decomposition or a convergence reconciliation, listing preserved task IDs and appended task IDs.
- **Suite Command:** `details` MUST include `suite_verification_command` covering the full affected test suite.

Illustrative `details` only (not a complete handoff; wrap in the canonical envelope for actual delivery):

```json
{
  "route": "feature",
  "execution_mode": "Sequential",
  "saved_plan_ref": "docs/plans/<workflow-id>.md @ <revision>",
  "saved_progress_ref": "docs/workflows/<workflow-id>.md @ <revision>",
  "spec_source_ref": "docs/specs/<workflow-id>.md @ <revision>",
  "ranked_queue_ref": "docs/plans/<workflow-id>.md#ranked-result-triage",
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
      "infrastructure_justification": null,
      "acceptance_criteria": [
        "SessionSerializer exports token_version field round-trip"
      ],
      "verification_command": "pytest tests/auth/test_session_serializer.py",
      "expected_outcome": "Tests pass with 0 exit code"
    },
    {
      "task_id": "TASK-02",
      "title": "Add token refresh API endpoint",
      "target_files": ["src/auth/routes.py", "tests/auth/test_routes.py"],
      "depends_on": ["TASK-01"],
      "parallel_safe": false,
      "infrastructure_justification": null,
      "acceptance_criteria": [
        "POST /api/v1/auth/refresh returns 200 with rotated tokens"
      ],
      "verification_command": "pytest tests/auth/test_routes.py",
      "expected_outcome": "Endpoint tests pass with 200 OK on token refresh"
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

Before completing `daw-plan`, verify:

- [ ] Every task specifies exact file paths and concrete operational changes.
- [ ] Current persisted proportional spec was consumed with exact source refs and revisions; clear no-file requirements were parent-recorded, with no invented design or new stage.
- [ ] Saved plan + progress refs are present in `details` for multi-step work; native todos complement durable artifacts with no separate task tracker; tiny patches stay inline.
- [ ] Full bidirectional traceability: Every requirement and acceptance criterion maps to task(s)/files/deps/verification/evidence/status or carries explicit, reasoned `N/A` justification; parent decision is separate from worker status. Where a conditional ERD was selected, its erd-01..03 criteria and traceability links map to tasks without inventing schema or migrations; a scoped ERD skip/N/A is a reasoned non-mapping, never an implicit pass.
- [ ] UI tasks consume matching rendered mockup refs or mark only UI scope blocked; real surface action is permitted where a fake shell check would be dishonest.
- [ ] Supporting infrastructure tasks lacking user stories have explicit prerequisite justifications (Contract §D).
- [ ] Dependency DAG verified: No dependency cycles and no references to unknown task IDs; dependencies strictly precede dependent story slices (Contract §D).
- [ ] Parallel execution criteria verified: Tasks marked `[P]` / `parallel_safe` have strictly disjoint write file paths AND zero shared runtime/data dependencies (Contract §D).
- [ ] Deterministic, non-interactive verification with exact invocation (no invented binary) and expected oracles specified for every task; evidence fields remain unexercised/null until run. One-off entries include commands/tools, expected results, done criteria, and rollback only where relevant (Contract §D, §I).
- [ ] Ranked queue: returned results feed the parent-owned [Ranked Result Triage](../../references/operations.md#ranked-result-triage); stable IDs/retry history preserved, duplicates merged, no automatic external deploy from worker pass.
- [ ] Plan readiness self-check completed and recorded in `details.readiness_self_check` (Contract §F).
- [ ] Recommends parent-directed independent readiness review (`daw-review`) for spec-dependent builds prior to `daw-build` (Contract §F).
- [ ] Convergence reconciliation preserves existing task IDs and history, does not duplicate pending tasks, and appends only genuine gaps inside accepted scope (Contract §G).
- [ ] Pre-existing uncommitted workspace modifications are explicitly noted for preservation.
- [ ] Expected evidence mapping aligns with the [Parent Acceptance Checkpoint](../../references/operations.md#parent-acceptance-checkpoint) and [Checkpoint Boundaries](../../references/operations.md#checkpoint-boundaries); workers author observations, parent authors decisions; small tasks keep criteria inline.
- [ ] No unwanted documentation files created unless explicitly requested.

---

## 6. Stop / Replan Triggers

These are advisory recommendations to the parent orchestrator; `daw-plan` does not invoke another module directly.

- **Missing Interface / Specification Gap:** If an architectural contract is missing or undefined during decomposition, halt planning (`status: "blocked"`, `handoff_to: null`) and recommend `daw-design` to the parent.
- **Dependency Cycle or Unknown Dependency:** If a cyclic dependency or unknown task dependency is detected, halt planning (`status: "blocked"`, `handoff_to: null`) and report the cycle in `details.readiness_self_check`.
- **File Ownership / Data Collision:** If concurrent tasks overlap on the same file or share mutable runtime state, serialize them or extract shared parts into a prerequisite task.
- **Unmapped Criteria Gap:** If buildable requirements cannot be decomposed within current scope, halt (`status: "blocked"`) and return gaps to the parent.
- **Task Failure in Execution:** If a task verification gate fails downstream, halt and recommend `daw-debug` or replan that specific slice to the parent.

---

## 7. Handoff Protocol

All handoffs are advisory metadata returned to the parent orchestrator; `daw-plan` never invokes another module directly and never dispatches subagents itself.

Select `handoff_to` from the active route:

- **`bootstrap` / `adopt`:** Terminal. Return `handoff_to: null` with `status: "pass"`; do not recommend `daw-build`.
- **`patch`:** Precedes `daw-build` directly. Trivial inline patches do not require independent prebuild readiness review. Return `handoff_to: "daw-build"`.
- **`feature` / `bugfix`:** For spec-dependent features, recommend `daw-review` for parent-directed independent prebuild readiness review (or the stage immediately following `daw-plan` in the active route plan), preserving review/verify ordering. Do not skip stages.
- **`refactor` / `maintain`:** After the readiness checkpoint under `daw-review`, recommend `daw-build` (the active route continues `daw-build` -> `daw-review` -> `daw-verify`); record the terminal `ship` recommendation for the parent.

_Reference Link:_ See [Canonical Feature Delivery Contract](../../references/document-quality.md#feature-delivery-contract), [Shared Routing Contract](../../references/routing.md), [Changes Lifecycle Guide](../../references/operations.md#parent-acceptance-checkpoint), [Checkpoint Boundaries](../../references/operations.md#checkpoint-boundaries), and [Parent-Owned Acceptance Record](../../references/operations.md#parent-owned-acceptance-record).
