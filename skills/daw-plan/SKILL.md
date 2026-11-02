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

- **No Document Sprawl:** Do not force creation of persistent `tasks.md` or tracker files unless requested. Outputting the structured plan in the handoff response is sufficient for standard tasks.
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
- **Relative Reference Base & Canonical Path Resolution:**
  - When loaded via symlink or alias (e.g. `~/.agents/skills/daw-plan`), resolve THIS `SKILL.md` symlink to its physical/canonical target file first.
  - The suite root is the canonical module directory's `../..`.
  - Use the host environment's resolved path; when shell `realpath` is unavailable, use the host file system's native target resolution. If the target cannot be resolved, report a blocked dependency rather than scanning parent or unrelated directories.
- **Mandatory Governance Loading:**
  - Before executing any phase work, load root governance (`../../SKILL.md` §4 Safety & §6 Handoff Contract Schema) and canonical routing (`../../references/routing.md` §5 & §6). Reading governance documentation is not recursive router execution.
  - Before performing any state mutations or file writes, load `../../references/operations.md` §1 Preflight Safety & §2 High-Risk Approvals.
  - Unknown risk, ambiguous target/scope, or missing required high-risk interactive approval/preflight must immediately transition to `blocked` before mutating files. Planning and task decomposition require no production credentials.

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

1. Define observable Acceptance Criteria (AC) for each task.
2. Provide deterministic verification commands (e.g. `pytest tests/test_feature.py`) that run non-interactively.
3. Include negative verification cases where appropriate.

### Step 5: Synthesize Implementation Contract

Format the plan into the standard output schema. Provide the plan directly in the response output unless the user or project conventions explicitly request an updated specification file under `docs/specs/`.

---

## 4. Output Contract

Every completion of `daw-plan` delivers a structured handoff payload adhering to the canonical suite envelope. Rich task breakdowns, dependencies, and verification commands are preserved under `details`:

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
- [ ] Pre-existing uncommitted workspace modifications are explicitly noted for preservation.
- [ ] No unwanted documentation files created unless explicitly requested.

---

## 6. Stop / Replan Triggers

- **Missing Interface:** If an architectural contract is missing or undefined during decomposition, halt planning and route back to `daw-design`.
- **Ownership Collision:** If concurrent tasks overlap on the same file, serialize them or extract shared parts into a prerequisite task.
- **Task Failure in Execution:** If a task verification gate fails, route to `daw-debug` or replan that specific slice.

---

## 7. Handoff Protocol

- **To Execution Agents (`daw-build` / Task Subagents):** Dispatch tasks in dependency order with file ownership and AC.
- **To `daw-review`:** Hand off for two-stage specification compliance and code review after implementation verification passes.
- **To `daw-debug`:** Route when task verification fails during implementation.
- **To Orchestrator:** Return structured plan payload; orchestrator executes subagent dispatch.

_Reference Link:_ See [Shared Routing Contract](../../references/routing.md) and [Changes Lifecycle Guide](../../references/changes.md).
