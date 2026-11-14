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
- A task whose agent wrote into the project's main working tree. The main working tree is snapshotted before the agent runs and compared after; a path that appears, whose content hash changes, or that was dirty before the run and is gone afterwards is reported as `worktree_escape_detected` and the task is not merged.

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

## 8. Composite Batch Execution

`run.py batch` (backed by `scripts/batch.py`, consumed one-way by `scripts/run.py`) runs independent ready tasks concurrently in sibling worktrees, verifies their combined result on a scratch composite branch, and integrates the composite into `daw/integration` only when the composite record passes the composite merge gate.

### Selection & grouping

1. **Ready order.** `compute_ready` computes the ready tasks (every id in `depends_on` is accepted and `autonomy == "afk"`), sorted deterministically by `(depth, task_id)`.
2. **Accepted-set consistency.** The accepted set is the union of `--accepted` / `--accepted-file` and tasks recorded as `merged` or `accepted` in the isolation state file (`docs/daw/evidence/runner/isolation.json` by default). Before any batch runs, every accepted task with a recorded `merge_commit` must have that commit as an ancestor of the base commit (`git merge-base --is-ancestor`); otherwise the runner refuses before work with `batch_accepted_not_integrated` (exit `2`). An accepted id with no entry in `isolation.json` emits a `batch_accepted_unverified` warning.
3. **Write-set disjointness.** A plan's `parallel_safe: true` is necessary but not sufficient. The runner re-derives pairwise write-set disjointness directly from the manifest's declared `target_files`. Comparison is **prefix-aware** by path segment (after stripping leading `./` and trailing `/`): `src/auth` overlaps `src/auth/x.py` but not `src/authz/x.py`. A task with `parallel_safe: false` always runs alone in its own single-member batch.
4. **Greedy first-fit & bounds.** Candidates are scanned in ready order (filtered to `--tasks` when pinned, preserving ready order; any pinned task that is not ready is refused before work with `batch_task_not_ready`, exit `2`). Each candidate joins the first existing group whose members are all `parallel_safe: true`, have fewer than `--max-concurrency` members (default: unlimited), and have write sets disjoint from its own; otherwise it opens a new group. When two candidates' declared `target_files` overlap, they are serialized into separate groups and reported as `batch_write_set_overlap` (warning), never refused. When `--max-tasks` bounds a run, the budget is spent *during* grouping so the selected members match what grouping chose.
5. **Declared vs. actual writes.** After member execution, the runner computes `git diff --name-only <base_commit>..<commit>` per member and emits `batch_undeclared_write` (warning) for any changed path not covered (prefix-aware) by `target_files` without blocking composition; true git merge conflicts fail with `batch_merge_conflict`. Residual limit: cross-member interference that no member's `verification_command` exercises cannot be detected from the manifest alone.

### Fixed base commit & sibling branches

- **One base commit (`B0`).** Each batch pins `B0` to the tip of `daw/integration` at batch start (initialized from `--base-ref`, default `HEAD`, when `daw/integration` does not yet exist; refused with `batch_no_base_commit`, exit `2`, if `daw/integration` has no commit). Every member branches from that exact `B0` into `daw/<task-id>-<title-slug>` inside `<worktree-root>/<task-id>`. Because all members start from `B0`, they are **siblings**, never a chain.
- **Pre-existing branch tip check.** If a member's task branch already exists, its tip must be **exactly** `B0`. Any branch at a different commit is refused before any work starts with `batch_stale_branch` (exit `2`), preserving the prior attempt; start clean explicitly with `python3 scripts/worktree.py remove --project-root <root> --task <id> --delete-branch`.
- **Batch identity.** `batch_id` is `batch-<hash>`, where `<hash>` is the first 10 hex characters of `sha256(base_commit + "|" + "|".join(sorted(task_ids)))`. The composite branch is `daw/batch/<hash>`, its worktree is `<worktree-root>/_composite`, and its evidence directory is `docs/daw/evidence/<batch-id>/` (resolved under the project's evidence directory).

### Member categories & integration fast paths

Each member runs concurrently in its own worktree (`run_agent_in_worktree`) and falls into one of three categories:

| Category | Agent exit | Self-verification | Commit produced | Treatment |
| :--- | :--- | :--- | :--- | :--- |
| **`green`** | `0` | `0` | yes | Composited; gates integration of the batch. |
| **`no-op`** | `0` | `0` | no | Not composited (no commit beyond `B0`); **accepted** unless `worktree_escape_detected` fired, since verification passed and the end state already holds. |
| **`red`** | non-zero or verification non-zero | — | — | Excluded from the composite and never accepted (`batch_task_agent_failed` or `batch_task_verification_failed`); healthy siblings still proceed. |

Integration depends on the count of `green` members (provided no `worktree_escape_detected` occurred):
- **`0` green:** nothing to integrate (`integrated` is `True` only when there are no `red` members).
- **`1` green:** no combination exists, so no composite is built; the lone `green` member integrates directly via `merge_task_branch` on its own per-task evidence.
- **`>= 2` green:** all `green` members are merged (`--no-ff`, sorted by `task_id`) into `daw/batch/<hash>`, each green member's `verification_command` runs sequentially in `task_id` order inside `<worktree-root>/_composite`, logs are written as `docs/daw/evidence/<batch-id>/composite-<n>.log`, and the summary record is written to `docs/daw/evidence/<batch-id>/composite-1.json`.

### The two merge gates

- **Per-task gate (`worktree.merge_task_branch`).** Refuses any task carrying a `batch_failure` marker in `isolation.json` with `merge_batch_failed`, then requires green `verify-*.log` evidence on that exact branch and exact tip commit (`merge_not_verified`).
- **Composite gate (`batch.merge_composite_branch`).** Merges `daw/batch/<hash>` into `daw/integration` only when `composite-1.json` passes all four axes of `validate_composite_record`:
  1. **Completeness.** Reconstructs the merged member commits from the composite's own merge history (`git rev-list --merges --parents <composite_commit> --not <base_commit>` second parents), deriving `base_commit` from `git merge-base <composite_commit> daw/integration` (never read on trust from the record) and requiring `record.base_commit` to match it. The reconstructed commit set must equal `record.members[].commit` exactly.
  2. **Commit match.** `record.composite_commit` must equal the current tip of `daw/batch/<hash>`, and `record.composite_branch` and `record.batch_id` must match the target branch and batch.
  3. **Uniform green.** Every entry in `record.members` must have `exit_code == 0`.
  4. **Log cross-check.** Every member's `log_path` must resolve inside that batch's own evidence directory, its file SHA-256 must match `record.members[].log_sha256`, and the log header's `exit_code`, `branch`, and `commit` must match `0`, the composite branch, and the composite commit.

When a composite fails verification or conflicts (`batch_merge_conflict`, `batch_composite_verification_failed`, or `merge_not_verified`), `daw/integration` is left untouched and a `batch_failure` marker is written per member into `isolation.json`. Manual `worktree.py merge --task <id>` refuses any marked member with `merge_batch_failed` until a subsequent batch run clears the marker or a new commit is verified.

### Composite branch lifecycle

`build_composite` recreates `daw/batch/<hash>` and `<worktree-root>/_composite` fresh from `B0` on every attempt so a prior attempt never leaks into a retry. If merging a member into the composite conflicts, `_composite` is reset (`git reset --hard <base_commit>`) and `batch_merge_conflict` is reported. On a red composite verification, the composite branch and its evidence (`composite-<n>.log`, `composite-1.json`) remain on disk for inspection; task branches are never automatically deleted by the runner.

### Integration lock & re-entrancy

Every operation that can mutate `daw/integration` acquires the file lock at `docs/daw/evidence/runner/integration.lock` (under the project's evidence directory): `run.py isolate`, `run.py batch`, `worktree.py prepare`, and `worktree.py merge` (and `run.py run` once migrated); `worktree.py commit`, `list`, and `remove` do not touch `daw/integration` and do not acquire it.

- Acquired atomically via `os.open(..., os.O_CREAT | os.O_EXCL)` recording `pid`, `start_time` (from `/proc/<pid>/stat`), and `acquired_at`.
- If a live process holds the lock (`pid` alive and `start_time` matching), the second operation refuses immediately before doing work with `integration_locked` (exit `2`).
- If the holder process is gone, the stale lock is taken over (`integration_lock_stale` warning in `worktree.py`).
- Re-entrant within a process via `_LOCK_DEPTH` keyed by lock path so `run.py` can hold the lock for the whole batch while calling `worktree.py` helpers; released in `finally` only when the outermost holder exits.

### Content-hash escape check & batch-level window

`snapshot_tree_state` hashes every dirty path (`git status --porcelain=v1 -z -uall`) in the main working tree (`""` for deleted or non-file paths) before the parallel phase and checks again across a **batch-level window** spanning both member execution and composite verification (`_integrate_composite`). Runner-owned paths are subtracted: the project's `evidence` directory prefix, `--work-dir` prefix, `integration.lock`, and `isolation.json`.

Any non-owned path that appears, disappears (for example, reverting a user's uncommitted edit), or changes content hash triggers `worktree_escape_detected` (error, exit `1`), leaving `daw/integration` untouched and preventing any member (including `no-op` siblings in `run.py batch`) from being marked accepted. Because attribution is batch-level under concurrency, the operator must not edit the main working tree while a batch is running.

### Failure matrix

Exit codes for `run.py batch`: `0` = every selected member integrated (or was a `no-op` with no errors); `1` = the batch ran and failed (partial or total); `2` = refused before work (usage, lock, or precondition error; `worktree.py` CLI also exits `2` on `IsolationError`).

| Condition | Finding code | Severity | Exit | Effect |
| :--- | :--- | :--- | :--- | :--- |
| Live integration lock held | `integration_locked` | `error` | `2` | Refused before any work |
| Stale integration lock taken over (`worktree.py`) | `integration_lock_stale` | `warning` | `0` | Lock taken over; operation proceeds |
| Pinned `--tasks` member not ready | `batch_task_not_ready` | `error` | `2` | Refused before any work |
| Accepted task not ancestor of base commit | `batch_accepted_not_integrated` | `error` | `2` | Refused before any work |
| Accepted task missing from `isolation.json` | `batch_accepted_unverified` | `warning` | `0` | Reported; batch proceeds |
| Integration branch has no commit | `batch_no_base_commit` | `error` | `2` | Refused before any work |
| Pre-existing task branch tip != `B0` | `batch_stale_branch` | `error` | `2` | Refused before any work |
| Worktree container not git-ignored | `worktree_root_not_ignored` | `error` | `2` | Refused before any work |
| Two tasks declare overlapping `target_files` | `batch_write_set_overlap` | `warning` | `0` | Serialized into separate batches |
| Member modifies path outside `target_files` | `batch_undeclared_write` | `warning` | `0` | Reported; member still composited |
| Member's agent exits non-zero | `batch_task_agent_failed` | `error` | `1` | Member excluded; siblings proceed; dispatch written |
| Member's self-verification exits non-zero | `batch_task_verification_failed` | `error` | `1` | Member excluded; siblings proceed; dispatch written |
| Merge conflict on composite or integration | `batch_merge_conflict` | `error` | `1` | Batch fails; integration untouched; failure marker & dispatch written |
| Composite verification exits non-zero | `batch_composite_verification_failed` | `error` | `1` | Batch fails; integration untouched; composite kept; failure marker & dispatch written |
| Per-task or composite gate rejects merge | `merge_not_verified` | `error` | `1` | Merge refused; integration untouched |
| Manual `worktree.py merge` on failed-batch member | `merge_batch_failed` | `error` | `2` (`1` in batch) | Refused; individual greenness does not prove combination |
| Agent or composite modified main working tree | `worktree_escape_detected` | `error` | `1` | Batch refused; nothing integrated or accepted |

### Review dispatch package

When a batch excludes a `red` member, fails composite verification, or hits a merge conflict, the runner writes `docs/daw/evidence/<task-id>/review-dispatch.json` (`schema_version: 1`) via `batch.write_review_dispatch` for every `red` member — and, when the composite is red or a conflict occurred, for every `green` member as well (none are written for a clean batch). Every written path is listed explicitly in the batch JSON envelope's `review_dispatch` array (`[{"task_id": ..., "path": "<repo-relative path>"}]`).

The package carries **facts only** — never a verdict, culprit, or prose summary:

- `task_id`, `title`, `branch`, `commit` (`null` when no new commit beyond `base_commit`), `base_commit`, and `diff_range` (`"<base_commit>..<commit>"` or `""` when `commit` is `null`).
- `self_verification` (`exit_code`, `log_path`, `log_sha256`) and `composite_verification` (same shape, or `null` when the task did not run on a composite — `null` means *not measured*, never `0`).
- `members[]`: per-member `{task_id, agent_exit_code, self_verification_exit_code, composite_exit_code}`.
- `combination_dependent_task_ids`: arithmetic list of task ids whose non-null `composite_exit_code` differs from their non-null `self_verification_exit_code`.
- `declared_target_files`, `actual_changed_paths`, `undeclared_paths`, and `findings` (error finding codes).

The parent orchestrator dispatches an independent reviewer (`daw-review` or a fresh-context reviewer) against this package and owns triage; the runner never auto-repairs failed members and never lets a generative reviewer veto a mechanical gate.

## 9. Invocation Reference

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

# Run independent ready tasks concurrently in sibling worktrees and integrate the composite.
python3 "$SKILL_DIR/scripts/run.py" batch \
  --plan docs/daw/plans/<workflow-id>.md --project-root "$PROJECT_DIR" \
  --agent-command '["claude","-p","{prompt_file}"]' --max-concurrency 4

# Unattended loop over ready tasks with an operator-supplied agent.
python3 "$SKILL_DIR/scripts/run.py" run \
  --plan docs/daw/plans/<workflow-id>.md --project-root "$PROJECT_DIR" \
  --agent-command '["claude","-p","{prompt_file}"]' --max-tasks 5
```

Every verb prints a JSON envelope with `findings` and `limitations`, and exits `0` on success, `1` on findings or a failed verification, `2` on a usage or environment error.

## 10. Why This Exists

Without this layer the suite's own axiom — "the brain may be generative, the hands must be deterministic" — is only half implemented. The validators are deterministic, but the *execution* of a plan was a sequence of model decisions: which task next, what the worker could see, whether the task actually passed. The runner makes those three decisions mechanical and reproducible, and leaves the generative work (design, code, judgment about quality) untouched.
