# Deterministic Execution Runner

The suite's execution layer. It exists because a plan is a document, not a process: without a machine-readable task list and a program that consumes it, the *order* in which work happens, the *context* each worker receives, and the *evidence* each task produces are all decided by a model at runtime. The runner moves those three decisions into deterministic code and leaves the judgment (what to build, whether the result is right) where it belongs.

This document is the canonical contract. The implementation is `scripts/run.py`; the manifest's structural rules live in `scripts/check_tasks.py` and are also reachable read-only through `validate.py tasks`.

## 1. Scope & Boundaries

- **Explicitly invoked, per unit of work.** Every invocation performs one bounded action and exits. There is no daemon, no background service, no scheduler, and no automatic recovery after process loss.
- **Never a writer of project intent.** The runner reads a plan, derives state, and produces evidence. It never edits a specification, never rewrites a plan, and never records parent acceptance.
- **Never pushes, tags, publishes, or deploys, and never writes to a protected branch.** Task branches and the local integration branch are branches the runner created. Delivery — merging into a working branch, opening a PR, releasing — remains the `ship` route with its own approval gates.
- **Never installs, discovers, or enables an agent command.** The AFK loop takes the agent command from the operator on the command line.
- **Never trusts a model claim.** A task is complete only when its own prescribed verification command actually exited `0` in this session and the output was captured to disk.

## 2. The Task List

The task list has one hand-authored source per workflow, and the machine manifest is a *projection* of it. Two modes exist, and they never mix.

### 2A. Task files as the source (preferred)

Each task is one Markdown file in a directory the plan names. The frontmatter carries the machine fields; the body is free prose — the "what and why" a human writes and a machine never has to guess.

```
docs/daw/plans/wf-session-rotation.tasks/TASK-01.md
```

```markdown
---
task_id: TASK-01
title: Rotate token_version in the serializer
autonomy: afk
depends_on: []
parallel_safe: false
target_files:
  - src/auth/serializer.py
acceptance_criteria:
  - SessionSerializer round-trips token_version
verification_command: python3 -m pytest tests/test_serializer.py -q
expected_outcome: 0 exit code, all cases pass
---

## What to build

The serializer emits a `token_version` and reads it back on every load.

## Out of scope

The refresh route — that is TASK-02.
```

Frontmatter values accept three forms: a plain scalar, an inline JSON value (`["a", "b"]`), or an indented `- item` list. Unknown keys, duplicate keys, and missing required fields are rejected — never silently ignored.

The plan declares where its task files live:

```markdown
<!-- daw-task-sources: docs/daw/plans/wf-session-rotation.tasks -->
```

`scripts/derive_tasks.py` projects those files into the plan's manifest block:

```bash
# Print what would be written; nothing is modified.
python3 scripts/derive_tasks.py --plan docs/daw/plans/wf-session-rotation.md --project-root .

# Write it.
python3 scripts/derive_tasks.py --plan docs/daw/plans/wf-session-rotation.md --project-root . --write
```

This is the same discipline as `derive_ledger.py`: the Markdown files stay the only hand-authored source, the manifest is a verified projection, and the writer never invents a field.

**Drift is refused, not tolerated.** `validate.py tasks` and every runner verb recompute the projection and compare it with the manifest in the plan. Any difference — an edited field, an added task, a removed task — is reported as `manifest_drift` naming the exact task and field, and the runner refuses to execute until the manifest is re-derived. A plan whose prose and task files disagree cannot run.

### 2B. The embedded manifest as the source

A plan that declares no task-source directory carries the task list directly, as one fenced ` ```json ` block immediately after the `<!-- daw-task-manifest -->` marker. The marker makes the block unambiguous inside a plan that may contain other JSON examples, and it is the literal token the route flow gate looks for (see [Best Practice Flow](best-practice-flow.md) BPF-9).

```markdown
<!-- daw-task-manifest -->
```json
{
  "schema_version": 1,
  "workflow_id": "wf-session-rotation",
  "tasks": [
    {
      "task_id": "TASK-01",
      "title": "Rotate token_version in the serializer",
      "autonomy": "afk",
      "depends_on": [],
      "parallel_safe": false,
      "target_files": ["src/auth/serializer.py"],
      "acceptance_criteria": ["SessionSerializer round-trips token_version"],
      "verification_command": "python3 -m pytest tests/test_serializer.py -q",
      "expected_outcome": "0 exit code, all cases pass"
    }
  ]
}
```
```

### Field vocabulary

Both modes use the same field names, so a task file and an embedded manifest describe a task identically. They mirror the planning module's task contract (`daw-plan`'s `details.tasks[]`), so the plan prose and the executable task list cannot drift into different vocabularies.

| Field | Meaning |
| :--- | :--- |
| `task_id` | Stable, unique within the workflow. Used for dependency joins and evidence paths. |
| `title` | One-line human description. |
| `autonomy` | `afk` (delegable without a live human) or `hitl` (needs a human decision). |
| `depends_on` | Task ids that must be accepted before this task is ready. Must form a DAG. |
| `parallel_safe` | Whether the task may run beside a disjoint sibling. |
| `target_files` | Project-relative paths the task owns. Must be safe relative paths. |
| `acceptance_criteria` | Observable conditions the task must satisfy. |
| `verification_command` | The exact command whose `0` exit code is the task's proof. |
| `expected_outcome` | What a passing command is expected to show. |

Optional: `steps` (ordered `action`/`file`/`run`/`expected` entries), `interfaces` (`consumes`/`produces`), `context_files` (extra files for the context pack), `notes`. A task file's prose body is human context and never becomes a machine field.

### Structural rules

`validate.py tasks` (read-only) and the runner both reject: a missing or duplicated marker, a malformed or non-strict-JSON block, an unknown manifest or task field, a missing required field, a duplicate `task_id`, an unknown dependency, a dependency cycle, an invalid `autonomy`, an empty `target_files` or `acceptance_criteria`, a blank command/expected outcome, and an unsafe or absolute `target_files` path. The rules are structural only; they never evaluate whether a task is semantically correct.

## 3. The Ready Set

`run.py next` computes what may run now, with no model in the loop:

1. A task is **ready** when every id in `depends_on` is in the accepted set, and the task itself is `autonomy: afk`.
2. A `hitl` task is never ready. It is reported under `requires_human` with the pending dependencies, because a live decision is exactly what a script cannot supply.
3. A task with unaccepted dependencies is **blocked**, naming the dependencies it waits on.
4. Ready tasks are ordered by dependency depth, then by task id. The order is a pure function of the manifest and the accepted set, so two runs on the same inputs produce the same list.

Acceptance is supplied by the caller (`--accepted` / `--accepted-file`) because parent acceptance is the parent's decision, not the runner's.

## 4. The Context Pack

`run.py context` assembles the bounded context a worker receives — the "smart zone" discipline: each task gets a fresh, deliberately small context instead of an ever-growing conversation.

Sections are emitted in fixed order: task header (goal, autonomy, dependencies, verification command, expected outcome), acceptance criteria, steps, interfaces, notes, the task's prose brief (when the task came from a task file), the suite constitution excerpt, the project's own configured commands, then the target files.

- The pack is **byte-bounded** (`--budget-chars`, default 100 000). Truncation is explicit and recorded per file, never silent.
- Every included file carries its **SHA-256** in the pack, so the consumer can prove which bytes it received.
- Files are read from the project root only, through the same bounded-path resolver the validators use. A path that escapes the root is refused, not sanitized.
- Files that do not exist yet are recorded as skipped with a reason instead of failing the assembly.

The pack is written to `--out` or printed to stdout. It is an input artifact for a worker; it is not evidence.

## 5. Verification & Evidence

`run.py verify` executes a task's prescribed command and captures what actually happened:

- The command is split with `shlex` and executed as an argv **without a shell**, so plan text cannot inject shell syntax.
- Output and the exit code are written to `docs/daw/evidence/<task-id>/verify-<n>.log`, with the attempt number incrementing per run.
- The result reports `exit_code`, `passed`, the evidence path, and the evidence file's SHA-256.
- A missing binary is exit `127`; a timeout is exit `124`. Neither is a pass.

The evidence file is the artifact a task contract's `evidence[]` entry points at, so the existing `validate.py contract --stage complete` gate consumes runner output without any new schema.

## 6. The AFK Loop

`run.py run` is the unattended path: take the next ready task, hand it its context pack to an operator-supplied agent command, then verify it.

- `--agent-command` is a JSON argv array. The runner substitutes `{prompt_file}`, `{workspace}`, and `{task_id}`; the prompt also arrives on stdin. The runner never discovers or enables an agent.
- `--dry-run` prints the argv without executing it.
- The loop stops at the first task whose agent or verification fails, and at `--max-tasks`.
- A task is added to the accepted set only when both the agent and the verification succeeded.

A passing verification is **evidence, not authorization**. It says the prescribed command exited `0` on this revision. It does not certify semantic correctness, and it grants no permission to merge, push, or deploy.

## 7. Per-Task Isolation

`run.py isolate` runs one task inside its own git worktree and integrates the result only when the task's own verification proves it.

The order is fixed and mechanical:

1. **Prepare.** Create the local integration branch (`daw/integration`) and its worktree, then a task branch named `daw/<task-id>-<title-slug>` with its own worktree. The task branch is based on the integration branch, so a task sees the work already integrated by the tasks before it.
2. **Hand over.** Assemble the context pack from the *worktree*, not the project root, so the worker reads the state its own branch will merge.
3. **Work.** Run the operator's agent command with the worktree as its working directory.
4. **Verify.** Run the task's verification command *inside the worktree*, so the command observes the isolated code. The evidence records the branch and the commit it was produced at.
5. **Commit.** Commit the worktree's contents on the task branch.
6. **Integrate.** Merge the task branch into the integration branch — only when the recorded evidence is green *at that exact commit*.

### What the tool refuses

- A worktree container git would track. The container must be ignored; `--add-ignore` appends the pattern to the **repository-local** exclude file (`git rev-parse --git-path info/exclude`). The project's own `.gitignore` and global git configuration are never modified.
- A merge without green evidence, or with evidence produced on a different branch or at a different commit.
- A merge into a protected branch (`main`, `master`, `develop`, `release/*`).
- A task whose agent wrote into the project's main working tree. The main working tree is snapshotted before the agent runs and compared after; any new dirty path there is reported as `worktree_escape_detected` and the task is not merged.

### What isolation does and does not guarantee

The worktree is a **working directory**, not a sandbox. It changes where a relative path lands; it does not confine the process.

- **Relative paths stay inside.** The working directory is inherited by the whole process tree, so a worker that spawns its own subagents keeps them inside the worktree too. A swarm launched under the worktree does not escape it by spawning.
- **Absolute paths bypass it.** A worker that writes to an absolute path outside the worktree lands outside it. The runner detects writes that land inside the project's main working tree — the case that would corrupt the user's work — and refuses to integrate the task. Writes to locations entirely outside the project root are not detected: bounding those would require filesystem monitoring, and the isolation contract is about the repository, not the machine.

The consequence for an agent command: run it with the worktree as its working directory and let it use relative paths, or give it no write access outside the worktree at all.

### Why native git, not the harness's worktree API

The isolation layer is `git worktree` driven, on purpose:

- **Harness-agnostic.** The runner is a CLI invoked with `python3 scripts/run.py`. It runs the same way under Codex, Claude Code, OpenCode, or in CI, with or without a harness-native worktree feature.
- **Deterministic naming.** Branch and worktree names are derived from the task id and the integration base. A harness-native API does not accept a base ref, so "this task builds on the work already integrated by the tasks before it" could not be guaranteed.
- **Many worktrees at once.** A harness-native session worktree is session-scoped. The AFK loop needs one worktree per task, each with a different base.

A harness-native worktree remains useful for an *interactive* session (the agent stays inside it with its context intact). That is a different shape of work: interactive session continuity versus deterministic batch isolation. The runner does not depend on it.

`scripts/worktree.py` exposes the same primitives for manual use:

```bash
# Prepare the isolation worktrees for one task.
python3 scripts/worktree.py prepare --project-root "$PROJECT_DIR" \
  --task TASK-01 --title "Rotate token_version"

# Commit the work inside the task's worktree.
python3 scripts/worktree.py commit --project-root "$PROJECT_DIR" --task TASK-01

# Merge the verified task branch into the integration branch.
python3 scripts/worktree.py merge --project-root "$PROJECT_DIR" --task TASK-01

# Report the isolation state.
python3 scripts/worktree.py list --project-root "$PROJECT_DIR"
```

The runner never pushes, tags, publishes, or deploys, and never writes to a protected branch. Merging the local integration branch into a working branch remains the ship route's job.

## 8. Invocation Reference

```bash
# Validate a plan's task list (read-only); detects drift against the task files.
python3 "$SKILL_DIR/scripts/validate.py" tasks docs/daw/plans/<workflow-id>.md \
  --project-root "$PROJECT_DIR"

# Re-derive the plan's manifest from its task files.
python3 "$SKILL_DIR/scripts/derive_tasks.py" --plan docs/daw/plans/<workflow-id>.md \
  --project-root "$PROJECT_DIR" --write

# What may run right now?
python3 "$SKILL_DIR/scripts/run.py" next \
  --plan docs/daw/plans/<workflow-id>.md --project-root "$PROJECT_DIR"

# Assemble one task's bounded context pack.
python3 "$SKILL_DIR/scripts/run.py" context \
  --plan docs/daw/plans/<workflow-id>.md --project-root "$PROJECT_DIR" \
  --task TASK-01 --budget-chars 100000 --out docs/daw/evidence/runner/context-TASK-01.md

# Run one task's verification command and capture evidence.
python3 "$SKILL_DIR/scripts/run.py" verify \
  --plan docs/daw/plans/<workflow-id>.md --project-root "$PROJECT_DIR" --task TASK-01

# Run one task inside its own git worktree and integrate it when it verifies green.
python3 "$SKILL_DIR/scripts/run.py" isolate \
  --plan docs/daw/plans/<workflow-id>.md --project-root "$PROJECT_DIR" --task TASK-01 \
  --agent-command '["claude","-p","{prompt_file}"]'

# Unattended loop over ready tasks with an operator-supplied agent.
python3 "$SKILL_DIR/scripts/run.py" run \
  --plan docs/daw/plans/<workflow-id>.md --project-root "$PROJECT_DIR" \
  --agent-command '["claude","-p","{prompt_file}"]' --max-tasks 5
```

Every verb prints a JSON envelope with `findings` and `limitations`, and exits `0` on success, `1` on findings or a failed verification, `2` on a usage or environment error.

## 9. Why This Exists

Without this layer the suite's own axiom — "the brain may be generative, the hands must be deterministic" — is only half implemented. The validators are deterministic, but the *execution* of a plan was a sequence of model decisions: which task next, what the worker could see, whether the task actually passed. The runner makes those three decisions mechanical and reproducible, and leaves the generative work (design, code, judgment about quality) untouched.
