---
name: daw-plan
description: "Deterministic implementation planning and task decomposition: maps concrete ordered tasks, explicit file ownership, dependencies, acceptance criteria, and verification gates without unwanted document churn."
---

# DAW Plan (`daw-plan`)

The planning module converts design specifications, architectural requirements, or direct change requests into concrete, ordered, and verifiable implementation tasks. It defines strict file ownership boundaries, sequences dependencies, and attaches measurable Acceptance Criteria (AC) and verification commands to every task.

**Invariant:** Keep plans actionable, bounded, and lean. Author persistent planning documentation ONLY when requested or structurally necessary; do not create plan sprawl or unwanted git commits.

---

## 1. Trigger & Scope

### When to Invoke

- Transitioning from design (`daw-design`) to implementation.
- Decomposing a multi-step engineering task, refactoring, or bug fix into execution slices.
- Structuring subagent task distributions for sequential or staged parallel execution.

### Non-Goals & Invariants

- **No Document Sprawl & Authoring Boundaries:** Apply the Documentation Authoring Contract (`../../references/routing.md` §3). `daw-plan` owns tactical task decomposition, sequencing, disjoint file boundaries, and verification commands. It does not author architecture specifications. Do not force creation of persistent `tasks.md` or tracker files; returning the structured plan in the stage payload is sufficient for standard tasks. When authorized by repository conventions or explicit user request to maintain persistent tracking, `daw-plan` owns tactical task updates and milestone progress tracking in `roadmap.md` (while high-level strategic roadmap phasing remains authored by `daw-design`/`daw-wizard`).
- **Concrete Scope:** Every task must specify exact file paths, operations, and verification commands.
- **Disjoint File Ownership & Parallel Criteria (Contract §D):** Concurrent tasks must have strictly non-overlapping file write sets AND no shared data or runtime dependency. Parallel marker `[P]` (or `parallel_safe: true`) is permitted only when both conditions hold. Shared files or runtime state must be serialized or factored into prerequisite tasks. Independent authorized work continues while blocked work halts.
- **Dependency Graph Integrity (Contract §D):** The plan forms a strict Directed Acyclic Graph (DAG). Dependency cycles or references to unknown task IDs are fatal planning errors. All dependencies must precede consumer story slices.
- **Traceability & Task Contract (Contract §D):** Every task must maintain explicit traceability: `requirement/AC -> story (where relevant) -> task IDs -> file paths -> deps -> exact verification/expected outcomes -> current observed evidence/status`. Every buildable criterion must be mapped; unmapped criteria are explicit gaps, never assumed as implicit N/A. `N/A` is valid only with explicit reasoned justification (e.g., non-buildable outcome, post-launch metric, or documented out-of-scope). A task may cover multiple criteria without artificial 1-to-1 mapping.
- **Supporting Infrastructure Justification (Contract §D):** A foundational or infra task lacking a user story is permitted ONLY when accompanied by an explicit, verified prerequisite justification explaining why downstream story slices depend on it.
- **Evidence vs. Command Distinction (Contract §D, §I):** Evidence references remain empty or unexercised until verification commands run and outcomes are observed. Planned verification commands or task checkboxes are NOT proof of completion.
- **Plan Readiness Self-Check (Contract §F):** Before finalizing the plan, `daw-plan` performs an internal readiness self-check verifying task completeness, cycle-free dependencies, disjoint parallel boundaries, justified infrastructure tasks, and executable local commands.
- **Parent-Owned Independent Prebuild Conformity Review (Contract §F):** In feature or spec-dependent workflows, plan delivery triggers a parent-owned independent read-only conformity review (using `daw-review` under parent orchestration as a bounded prebuild checkpoint without declaring code audit or completed route stage, and without module recursion) before `daw-build` is dispatched. If no independent review capability is available, an explicit direct fallback with documented evidence limits must be used (never an invented reviewer). This prebuild check verifies cross-artifact consistency (scope, governance, requirements, stories, design, plan, tasks) and does NOT replace mandatory postbuild technical audit.
- **Convergence Reconciliation & Scope Preservation (Contract §G):** When re-planning or reconciling drift (e.g. re-entering from review/verify or during code adoption): inspect actual code + authoritative contracts + current evidence. Classify items into `Implemented & Verified`, `Implemented (Unverified)`, `Missing`, `Contradicted`, or `Blocked`. Source existence, passing old tests, or task checkboxes alone are NEVER completion proof. Plan updates preserve existing stable IDs and history; never duplicate pending tasks or repeat identical missing work; append only genuine uncovered work inside accepted scope (no scope expansion). Changes to specs, code, or environment invalidate affected prior review/runtime acceptance; rerun proportionally. Bound repair rounds by existing retry rules to prevent endless loops.
- **Local Tooling & Integration Boundary (Contract §I):** Planning reuses project-local templates, tracking issues, discovered commands, and capabilities without requiring external skills or proprietary platforms. All verification commands must be concrete, non-interactive, and locally executable; merely printing a hook/check command is not execution. Local overrides cannot weaken canonical safety, acceptance, or test gates. No automatic external issue creation, PR generation, or deployment without explicit user authorization.
- **No Unwanted Commits or Git Hooks:** Planning never runs git commits, pushes, or alters hooks.
- **Workflow Transition Gate vs. Hook Claims:** Spec-dependent planning tasks require upstream specifications to have passed the `review-ready` workflow transition gate (`python3 scripts/validate.py docs RECORD --project-root ROOT --transition review-ready --documents PATH [PATH ...] --format text|json`). The gate is a deterministic CLI utility, not an automatic daemon or harness hook interceptor. Trivial inline tasks or bug fixes do not require mandatory 13 documents or document-quality JSON records. If Python 3 is unavailable, halt with canonical `status: "blocked"` (never emit a fake pass).
- **Canonical Procedural Contract:** Procedures comply with [Canonical Document Quality & Workflow Transition Specification: Feature Delivery Contract](../../references/document-quality.md#feature-delivery-contract).

---

## 2. Inputs & Prerequisites

- **Design Contracts / Requirements:**
  - Upstream design from `daw-design` or direct user requirements.
  - Specified non-goals and system invariants.
  - Upstream specification workflow transition verification: For spec-dependent tasks, verify that the required upstream specifications passed the `review-ready` transition on their current revision. If specifications were modified after review, the cached verdict is invalid due to SHA-256 mismatch, requiring rework re-entry and review re-evaluation before planning commences.
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
  - Select retained workers automatically for already-justified delegated corrective rounds when the harness supports completed-worker continuation, unless the user opts out. Do not add delegation or review stages for retention; unsupported optional retention uses an explicit fresh-worker handoff, not a blocker.

## 3. Operational Steps

### Step 1: Workspace State & Blast Radius Inspection

1. Verify target source files, configs, and test files exist at expected locations.
2. Inspect and record pre-existing uncommitted changes to ensure they are preserved.
3. Identify existing test runners (`pytest`, `npm test`, etc.) and linters for verification gates.

### Step 2: Requirements Inventory & Traceability Setup (Contract §D)

1. Extract stable requirement and acceptance criteria identifiers (`FR-###`, `AC-###`, `ROAD-###`) from upstream specifications or design contracts. Retain existing stable IDs; create scoped unique IDs only if absent.
2. Establish a compact traceability mapping:
   `Requirement / AC ID -> User Story (where relevant) -> Task ID(s) -> Target File Paths -> Dependencies -> Verification Command & Expected Outcome -> Current Observed Evidence / Status`.
3. Enforce the `N/A` rule: Mark an acceptance criterion `N/A` ONLY with an explicit, reasoned justification for non-buildable or documented out-of-scope criteria. Missing mappings remain explicit gaps, NEVER implicit `N/A`.
4. Differentiate business outcomes/KPIs from build/runtime acceptance criteria: Exclude post-launch outcome metrics and business KPIs from build/runtime criteria unless bounded by a justified, measurable observation harness.

### Step 3: Task Decomposition, Slicing & Infrastructure Justification (Contract §D)

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
2. Provide deterministic verification commands (e.g. `pytest tests/test_feature.py`, `npm test`) that run non-interactively in the local environment.
3. Include negative verification cases where appropriate.
4. **Evidence vs. Command Distinction:** Evidence references in the plan remain empty or null (`evidence: null`) until executed during build/verification. Planned commands, expected outcomes, or task checkboxes are NOT proof of completion.

### Step 6: Plan Readiness Self-Check (Contract §F)

Before finalizing the plan, perform an internal cross-artifact readiness self-check:

1. **Coverage Check:** Verify 100% of requirement / AC IDs are mapped to tasks (or explicitly justified as `N/A`).
2. **Orphan Task Check:** Verify every task links to an AC/story or carries an explicit infrastructure prerequisite justification.
3. **Graph Integrity Check:** Verify no dependency cycles and no dangling or unknown task dependencies exist.
4. **Parallel Safety Check:** Verify all tasks marked `[P]` / `parallel_safe` have strictly disjoint write sets and zero data/runtime dependencies.
5. **Verification Coverage:** Verify every task defines a non-interactive, executable local command and expected oracle.
   Record the self-check result in `details.readiness_self_check`.

### Step 7: Convergence Reconciliation & Scope Preservation (Contract §G)

When invoked to re-plan or reconcile gaps identified during execution, review, or verification:

1. Inspect the actual codebase, authoritative contracts, and current verification evidence.
2. Classify items into `Implemented & Verified`, `Implemented (Unverified)`, `Missing`, `Contradicted`, or `Blocked`.
3. **Preserve Existing IDs & History:** Do not renumber, delete, or rewrite completed or pending task IDs.
4. **No Duplicate Pending Tasks:** Do not re-append tasks that are already pending or repeat identical missing work.
5. **Append Only Genuine Gaps Inside Scope:** Append new tasks only for genuine uncovered work within accepted scope. Scope expansion or feature creep is strictly prohibited.
6. Record convergence state in `details.convergence`.

### Step 8: Synthesize Implementation Contract & Prebuild Review Handoff (Contract §F)

1. Format the plan into the standard output schema. Provide the plan directly in the response output unless the user or project conventions explicitly request an updated specification file under `docs/specs/` or `roadmap.md`.
2. **Parent-Owned Independent Prebuild Readiness Review:** For spec-dependent implementation workflows (`feature`, `bugfix`), `daw-plan` self-checks the plan and recommends `handoff_to: "daw-review"` (or parent readiness checkpoint) for a proportional independent read-only conformity review before `daw-build` execution begins.

---

## 4. Output Contract

Every completion of `daw-plan` delivers a structured handoff payload adhering to the canonical suite envelope as an internal module-to-orchestrator handoff. The canonical handoff payload MUST be delivered and observable BEFORE advancing to the next stage (e.g., `daw-review` or `daw-build`) per [User-Facing Reports & Handoff Transport](../../references/routing.md#user-facing-reports--handoff-transport) (via structured tool/subagent return, harness checkpoint, authorized workflow artifact, or an explicit inline fallback). Direct-user responses default to concise natural language rather than raw JSON. Rich task breakdowns, dependencies, and verification commands are preserved under `details`.

- **Mandatory Task Fields:** Each task in `details.tasks` MUST specify `task_id`, `title`, `target_files`, `depends_on`, `parallel_safe`, `acceptance_criteria`, non-interactive `verification_command`, and `expected_outcome`. If a task lacks a user story, it must include `infrastructure_justification`.
- **Traceability Mapping:** `details.traceability` records the compact mapping from requirement/AC ID to user story, task IDs, target files, dependencies, verification command, status, and evidence reference.
- **Readiness Self-Check:** `details.readiness_self_check` records the internal validation verdict (`pass` or `fail`), unmapped criteria, orphan tasks, dependency cycles, and parallel violations.
- **Convergence Metadata:** `details.convergence` records whether the plan is an initial decomposition or a convergence reconciliation, listing preserved task IDs and appended task IDs.
- **Suite Command:** `details` MUST include `suite_verification_command` covering the full affected test suite.

**Handoff Selection:** Choose `handoff_to` from the active route only; never invoke another module directly:

- **`bootstrap` / `adopt` routes (documentation-only):** `daw-plan` is the terminal stage. Return `handoff_to: null` even when `status: "pass"`. Never recommend `daw-build`; planning completion ends the pipeline.
- **`feature` / `bugfix` routes (implementation):** Recommend `daw-review` (for the parent-directed prebuild independent readiness conformity checkpoint) or the next ordered stage in the router plan.
- **Halted (`status: "fail"` or `"blocked"`):** Return `handoff_to: null`; the parent decides replan or routing.

```json
{
  "objective": "Decompose authentication token refresh implementation into sequential tasks.",
  "input_paths": ["docs/specs/blueprint.md"],
  "output_paths": [],
  "acceptance_criteria": [
    {
      "criterion": "All implementation tasks specify exact file paths and disjoint ownership",
      "status": "pass"
    },
    {
      "criterion": "Every task has explicit non-interactive verification commands",
      "status": "pass"
    },
    {
      "criterion": "Plan readiness self-check passes with 100% criteria mapping and acyclic dependencies",
      "status": "pass"
    }
  ],
  "evidence": [
    {
      "reference": "docs/specs/blueprint.md",
      "summary": "Verified inputs and decomposed tasks covering all specified design requirements"
    }
  ],
  "status": "pass",
  "handoff_to": "daw-review",
  "details": {
    "route": "feature",
    "execution_mode": "Sequential",
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
        "evidence": null
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
        "evidence": null
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
}
```

_(Note: `status: "pass"` indicates that planning phase criteria and internal readiness self-check have been satisfied; it does not indicate implementation or test completion)._

---

## 5. Verification & Quality Invariants

Before completing `daw-plan`, verify:

- [ ] Every task specifies exact file paths and concrete operational changes.
- [ ] Full traceability: Every requirement and acceptance criterion maps to task(s) or carries explicit, reasoned `N/A` justification (Contract §D).
- [ ] Supporting infrastructure tasks lacking user stories have explicit prerequisite justifications (Contract §D).
- [ ] Dependency DAG verified: No dependency cycles and no references to unknown task IDs; dependencies strictly precede dependent story slices (Contract §D).
- [ ] Parallel execution criteria verified: Tasks marked `[P]` / `parallel_safe` have strictly disjoint write file paths AND zero shared runtime/data dependencies (Contract §D).
- [ ] Deterministic, non-interactive local verification commands and expected oracles specified for every task; evidence fields remain unexercised/null until run (Contract §D, §I).
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
- **Halted (`fail` / `blocked`) or verification failure during planning:** Return `handoff_to: null`; report the blocker and let the parent route to `daw-debug` or replan.

_Reference Link:_ See [Canonical Feature Delivery Contract](../../references/document-quality.md#feature-delivery-contract), [Shared Routing Contract](../../references/routing.md), [Changes Lifecycle Guide](../../references/operations.md#parent-acceptance-checkpoint), [Checkpoint Boundaries](../../references/operations.md#checkpoint-boundaries), and [Parent-Owned Acceptance Record](../../references/operations.md#parent-owned-acceptance-record).
