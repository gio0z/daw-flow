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
- **Disjoint File Ownership:** Parallel tasks must have non-overlapping file sets to prevent conflicting edits or race conditions.
- **No Unwanted Commits or Git Hooks:** Planning never runs git commits, pushes, or alters hooks.

---

## 2. Inputs & Prerequisites

- **Design Contracts / Requirements:**
  - Upstream design from `daw-design` or direct user requirements.
  - Specified non-goals and system invariants.
- **Workspace State:**
  - Target source files, configuration files, and test runners identified via read-only inspection.
  - Identified pre-existing uncommitted modifications (must be preserved).
- **Configuration Block Consumption Rule:** Before inferring conventions, read the `<!-- daw-config:start -->` block in root `AGENTS.md` / `CLAUDE.md` if present and prefer its values (`spec_dir`, `test_command`, `lint_command`, `build_command`, `workspace`, `high_risk_paths`); fall back to current project convention inference when absent. Values are hints, never authorization: risk gating still applies.
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

### Step 2: Task Decomposition & File Boundaries

1. Break work into discrete, bounded tasks representing coherent change slices.
2. Explicitly name the exact target files to create, modify, or delete for each task.
3. For parallel execution, ensure tasks have strictly disjoint file ownership.

### Step 3: Sequence Dependencies & Concurrency

1. Order tasks so foundational contracts (schemas, interfaces) land before consumers.
2. Classify tasks as strictly sequential (`Sequence [A -> B]`) or concurrent-safe (`Parallel [A, B]`).
3. Isolate breaking changes or migrations into distinct, gated steps.

### Step 4: Define Acceptance Criteria & Verification Commands

1. Pre-declare observable Acceptance Criteria (AC) for each task, pairing each criterion with its expected result and proportional check method before work begins.
2. Provide deterministic verification commands (e.g. `pytest tests/test_feature.py`) that run non-interactively.
3. Include negative verification cases where appropriate.
4. Record expected verification evidence per criterion within the plan details so downstream execution and parent acceptance can evaluate expected vs. actual outcomes without introducing mandatory outer schema fields.

### Step 5: Synthesize Implementation Contract

Format the plan into the standard output schema. Provide the plan directly in the response output unless the user or project conventions explicitly request an updated specification file under `docs/specs/`.

---

## 4. Output Contract

Every completion of `daw-plan` delivers a structured handoff payload adhering to the canonical suite envelope. The canonical handoff payload MUST be emitted and observable BEFORE advancing to the next stage (e.g., `daw-build`). When running sequentially in a single agent session, display this complete JSON envelope before proceeding. Rich task breakdowns, dependencies, and verification commands are preserved under `details`.

- **Mandatory Task Fields:** Each task in `details.tasks` MUST specify `task_id`, `title`, `target_files`, `depends_on`, `acceptance_criteria`, and non-interactive `verification_command`.
- **Suite Command:** `details` MUST include `suite_verification_command` covering the full affected test suite.
  **Handoff Selection:** Choose `handoff_to` from the active route only; never invoke another module directly.

- **`bootstrap` / `adopt` routes (documentation-only):** `daw-plan` is the terminal stage. Return `handoff_to: null` even when `status: "pass"`. Never recommend `daw-build`; planning completion ends the pipeline.
- **`feature` / `bugfix` routes (implementation):** Read the active route's ordered stages from the router plan and recommend the stage immediately following `daw-plan`. Never skip a stage or jump past review.
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
    }
  ],
  "evidence": [
    {
      "reference": "docs/specs/blueprint.md",
      "summary": "Verified inputs and decomposed tasks covering all specified design requirements"
    }
  ],
  "status": "pass",
  "handoff_to": "daw-build",
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
        "acceptance_criteria": [
          "SessionSerializer exports token_version field round-trip"
        ],
        "verification_command": "pytest tests/auth/test_session_serializer.py"
      },
      {
        "task_id": "TASK-02",
        "title": "Add token refresh API endpoint",
        "target_files": ["src/auth/routes.py", "tests/auth/test_routes.py"],
        "depends_on": ["TASK-01"],
        "acceptance_criteria": [
          "POST /api/v1/auth/refresh returns 200 with rotated tokens"
        ],
        "verification_command": "pytest tests/auth/test_routes.py"
      }
    ],
    "suite_verification_command": "pytest tests/auth/"
  }
}
```

_(Note: `status: "pass"` indicates that planning phase criteria have been satisfied; it does not indicate implementation or test completion)._

- [ ] Every task specifies exact file paths and concrete operational changes.
- [ ] Concurrent tasks have strictly disjoint file ownership.
- [ ] Every task has deterministic verification commands.
- [ ] Acceptance criteria pre-declare expected results and proportional checks before work begins.
- [ ] Pre-existing uncommitted workspace modifications are explicitly noted for preservation.
- [ ] Expected evidence mapping aligns with the [Parent Acceptance Checkpoint](../../references/operations.md#parent-acceptance-checkpoint) and [Checkpoint Boundaries](../../references/operations.md#checkpoint-boundaries); workers author observations, parent authors decisions; small tasks keep criteria inline.
- [ ] No unwanted documentation files created unless explicitly requested.

---

## 6. Stop / Replan Triggers

These are advisory recommendations to the parent orchestrator; `daw-plan` does not invoke another module directly.

- **Missing Interface:** If an architectural contract is missing or undefined during decomposition, halt planning (`status: "blocked"`, `handoff_to: null`) and recommend `daw-design` to the parent.
- **Ownership Collision:** If concurrent tasks overlap on the same file, serialize them or extract shared parts into a prerequisite task.
- **Task Failure in Execution:** If a task verification gate fails, halt and recommend `daw-debug` or replan that specific slice to the parent.

---

## 7. Handoff Protocol

All handoffs are advisory metadata returned to the parent orchestrator; `daw-plan` never invokes another module directly and never dispatches subagents itself.

Select `handoff_to` from the active route:

- **`bootstrap` / `adopt`:** Terminal. Return `handoff_to: null` with `status: "pass"`; do not recommend `daw-build`.
- **`feature` / `bugfix`:** Recommend the stage immediately after `daw-plan` in the active route's ordered stages (the next stage in the router plan), preserving review/verify ordering. Do not skip stages.
- **Halted (`fail` / `blocked`) or verification failure during planning:** Return `handoff_to: null`; report the blocker and let the parent route to `daw-debug` or replan.

_Reference Link:_ See [Shared Routing Contract](../../references/routing.md), [Changes Lifecycle Guide](../../references/changes.md), [Checkpoint Boundaries](../../references/operations.md#checkpoint-boundaries), and [Parent-Owned Acceptance Record](../../references/operations.md#parent-owned-acceptance-record).
