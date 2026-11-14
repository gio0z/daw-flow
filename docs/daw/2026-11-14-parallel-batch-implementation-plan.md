# Parallel Batch Execution — Implementation Plan

<!-- daw-doc -->

**Status:** proposed, awaiting review

**Produced by:** the DAW suite's own planning route, recorded under `docs/daw/` (see `docs/daw/README.md`).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the deterministic execution runner a cross-task parallel path: run a batch of independent tasks concurrently in isolated worktrees, integrate them as a composite that is verified as a whole, and migrate the AFK loop onto that path.

**Architecture:** A batch's members all branch from one fixed base commit `B0`, so they are siblings rather than a chain. Each member is verified alone in its own worktree; the green members are merged into a scratch composite branch, and the composite is then verified with *every* green member's verification command before the composite itself is merged into the integration branch. The integration gate therefore proves the **combination**, not just each part — the guarantee sequential mode only closes incidentally. A file lock serializes every operation that mutates the integration branch, so concurrent invocations are impossible rather than merely unlikely.

**Tech Stack:** Python 3.10+, standard library only (`argparse`, `concurrent.futures`, `hashlib`, `json`, `os`, `pathlib`, `re`, `shlex`, `subprocess`, `unittest`). Native `git` CLI for every worktree and merge operation. No third-party runtime dependency.

**Spec:** [`docs/daw/2026-11-14-parallel-batch-design.md`](2026-11-14-parallel-batch-design.md) — the design this plan implements. The spec travels with the plan: the spec's §§6.1–6.13 define the mechanism, §6.10 the failure matrix, §7 the decisions that must not be re-litigated, and §9 the test inventory.

---

## Global Constraints

These apply to every task. They are copied verbatim from the spec; a task's requirements implicitly include them.

- **Python 3.10+, standard library only.** No third-party runtime package dependency. Never add a dependency for what a few lines do.
- **The runner never pushes, tags, publishes, or deploys.** It never writes to a protected branch (`main`, `master`, `develop`, `trunk`, `release/*`). Merging the local integration branch into a working branch remains the ship route's job.
- **The runner never installs, discovers, or enables an agent command.** `--agent-command` is operator-supplied JSON argv.
- **Explicitly invoked per unit of work; never a daemon, scheduler, or background service.**
- **The merge gate lives inside the merge function**, not in its caller, so no entry point can bypass it.
- **The worktree container must be git-ignored.** `--add-ignore` appends to the repository-local exclude file only; never to the project's `.gitignore`, never to global git config.
- **Evidence lives under the project root** in one canonical location, regardless of which worktree produced it.
- **The runner writes only inside the project root**, and only the paths it is given.
- **A passing verification is evidence, never authorization.** It grants no permission to merge, push, or deploy.
- **Findings shape:** `{"severity": "error"|"warning", "code": str, "path": str, "message": str}`. A warning does not make the envelope invalid.
- **Finding codes used by this change** (one authority; the spec's §6.10 is the normative list): `integration_locked` (error), `integration_lock_stale` (warning), `batch_write_set_overlap` (warning), `batch_undeclared_write` (warning), `batch_accepted_unverified` (warning), `batch_task_not_ready` (error), `batch_stale_branch` (error), `batch_task_agent_failed` (error), `batch_task_verification_failed` (error), `batch_merge_conflict` (error), `batch_composite_verification_failed` (error), `batch_accepted_not_integrated` (error), `merge_batch_failed` (error), plus the pre-existing `merge_not_verified` and `worktree_escape_detected`.
- **Exit codes:** `0` = every selected member integrated; `1` = the batch ran and something failed; `2` = refused before any work (usage, environment, live lock, unmet precondition).
- **One artifact authority.** The composite record is written by the batch runner and validated by the composite merge gate; the log is the primary evidence and the record is an index over it.
- **Never commit without an explicit ask.** Stage explicit paths only — never `git add -A`. Inspect `git diff --cached` before every commit.

---

## Review Focus

The spec is a vision document: it says what the software must do, and its silence about an input is not permission for that input to break the program. These are the five failure modes most likely to bite a real operator, most likely first. Each has a test in the task that owns the code.

1. **An operator edits the main working tree while a batch runs.** The escape-detection window spans the whole batch, so the edit is indistinguishable from an agent escape and fails the batch. Expected: the batch is refused with `worktree_escape_detected`, the integration branch is untouched, and the operator can simply re-run. *Task 4, Task 6.*
2. **A task legitimately produces no changes** ("nothing to do" — the work was already done by a sibling). Expected: the member is **accepted**, does not fail the batch, and does not appear in the composite's merge history — because merging a branch with no new commit creates no merge commit and would otherwise fail the composite's completeness check. *Task 5, Task 6.*
3. **A member's agent writes into a sibling's worktree through an absolute path.** The escape check watches the *main* working tree, not sibling worktrees. Expected: the batch is not falsely reported as escaped; the corruption surfaces as a merge conflict or a red composite verification, and the integration branch stays untouched. *Task 6.*
4. **The plan marks two tasks `parallel_safe: true` whose `target_files` overlap.** Expected: the runner refuses to batch them, serializes them into separate batches, and reports `batch_write_set_overlap` as a warning — the plan's flag never talks the runner into a conflict. *Task 2, Task 6.*
5. **A member's verification command writes into the main tree through an absolute path during the composite phase.** The write lands after the members finished, so a per-worker window would have closed. Expected: the batch-level window still catches it and the batch is refused. *Task 4, Task 6.*

---

## File Structure

| File | Responsibility after this change |
|---|---|
| `scripts/batch.py` *(new)* | The batch mechanism: selection and grouping, prefix-aware write-set disjointness, the composite branch, the composite record, the composite merge gate, and the review dispatch package. Imports git primitives from `scripts/worktree.py`; never imports `scripts/run.py`. |
| `scripts/worktree.py` | Git-level primitives. Gains the integration lock, the content-hash tree snapshot, the per-member isolation-state records, the batch failure marker, and the `merge_batch_failed` check inside `merge_task_branch`. |
| `scripts/run.py` | The runner verbs. Gains the `batch` verb, the shared per-task execution helper, and the `run` migration onto batches. |
| `scripts/daw_common.py` | Gains `finding(severity, code, path, message)` — one authority for the finding shape shared by `worktree.py` and `batch.py`. |
| `scripts/package_layout.py` | Gains `scripts/batch.py` in `OPERATIONAL_SCRIPTS` so the new module ships. |
| `tests/test_batch.py` *(new)* | The batch mechanism's behavior tests. |
| `tests/test_worktree.py` | Gains lock, escape-snapshot, and state-marker tests. |
| `tests/test_isolation.py` | Gains the `isolate`-under-lock and hash-escape tests. |
| `references/execution-runner.md` | The runner's normative contract. Gains a batch section and an updated AFK-loop section. |
| `CHANGELOG.md` | Gains two entries with `### Project migration` subsections for the newly enforced rules. |

**Import direction (one-way, no cycles):** `run.py` → `batch.py` → `worktree.py` → `daw_common.py`.

---

## Commit Plan

Two commits, each independently green (`python3 -m unittest discover -s tests -p "test_*.py"`, `python3 scripts/validate.py package`, `python3 scripts/validate.py flow --project-root .`, `python3 scripts/route.py --check-suite --root .`):

1. `feat(runner): composite batch execution with whole-combination verification` — Tasks 1–8.
2. `feat(runner): run the AFK loop as isolated batches` — Tasks 9–10.

---

### Task 1: The integration lock

The first measured defect (M1) was two concurrent `isolate` runs racing on `refs/heads/daw/integration`: `fatal: cannot lock ref`. Separate worktrees do not fix that — the integration branch is the contention point. This task makes "one integration-touching operation at a time per repository" enforceable instead of aspirational.

**Files:**
- Modify: `scripts/daw_common.py` (add `finding`)
- Modify: `scripts/worktree.py` (add the lock section; wire into `command_prepare` and `command_merge`)
- Modify: `scripts/run.py` (acquire the lock in `verb_isolate`)
- Test: `tests/test_worktree.py`, `tests/test_isolation.py`

**Interfaces:**
- Consumes: nothing from later tasks.
- Produces:
  - `daw_common.finding(severity: str, code: str, path: str, message: str) -> dict[str, str]`
  - `worktree.DEFAULT_LOCK_PATH = "docs/daw/evidence/runner/integration.lock"` — the documented default; `worktree.lock_path(project_root)` resolves it through the project's evidence directory.
  - `worktree.lock_path(project_root: pathlib.Path, raw: str | None = None) -> pathlib.Path`
  - `worktree.process_start_time(pid: int) -> str | None` — field 22 of `/proc/<pid>/stat`, or `None` when it cannot be read.
  - `worktree.IntegrationLock(project_root, raw: str | None = None)` with `acquire() -> dict[str, Any]`, `release() -> None`, and the context-manager protocol (`__enter__` returns self, `__exit__` releases).
  - `IntegrationLock.acquire()` returns `{"path": str, "reentrant": bool, "stale_taken_over": bool}`. It raises `IsolationError` whose findings carry code `integration_locked` when a **live** holder owns the lock.
  - `worktree._error(code, path, message)` and `worktree._warning(code, path, message)` now delegate to `daw_common.finding`; their names and signatures are unchanged.

- [ ] **Step 1: Write the failing tests**

  In `tests/test_worktree.py`, add class `IntegrationLockTests(unittest.TestCase)` on the existing `IsolationRepoBase` (which already builds a real git repo in a temp dir). Add:

  - `test_a_live_holder_blocks_a_second_operation` — spawn a child process that acquires the lock and prints `held` on stdout, wait for that line, then assert `worktree.IntegrationLock(self.repo).acquire()` raises `IsolationError` with finding code `integration_locked`. Terminate the child in `addCleanup`. The child script inserts `PROJECT_ROOT/scripts` on `sys.path`, imports `worktree`, acquires the lock on the repo path given as `argv[1]`, prints `held`, and sleeps.
  - `test_a_lock_whose_holder_is_gone_is_taken_over` — write the lock file by hand with `{"pid": 999999, "start_time": "1"}`; assert `acquire()` succeeds and returns `stale_taken_over: True`.
  - `test_the_lock_is_reentrant_within_one_process` — acquire on two separate `IntegrationLock` instances in the same process; assert the second returns `reentrant: True` and that the lock file still exists after the first `release()`.
  - `test_releasing_the_outermost_holder_removes_the_lock_file` — assert the file is gone after the matching number of `release()` calls.
  - `test_worktree_merge_refuses_while_the_lock_is_held` — hold the lock in the test process, then run the `worktree.py merge` CLI; assert exit code `2` and finding code `integration_locked`.
  - `test_worktree_prepare_refuses_while_the_lock_is_held` — the same for `worktree.py prepare`.

  In `tests/test_isolation.py`, add to `IsolateTests`:

  - `test_isolate_refuses_while_the_lock_is_held` — write the lock file with the **test process's** pid and its real `process_start_time`, then run `run.py isolate`; assert exit code `2` and finding code `integration_locked`.

- [ ] **Step 2: Run the tests to verify they fail**

  Run: `python3 -m unittest discover -s tests -p "test_worktree.py" -v` and `python3 -m unittest discover -s tests -p "test_isolation.py" -v`

  Expected: FAIL with `AttributeError: module 'worktree' has no attribute 'IntegrationLock'`.

- [ ] **Step 3: Implement the lock in `scripts/worktree.py`**

  Add `DEFAULT_LOCK_PATH = "docs/daw/evidence/runner/integration.lock"` next to `DEFAULT_STATE_PATH`. Implement:

  - `lock_path(project_root, raw=None)` — with no explicit path, resolve the project's evidence directory through `daw_common.artifact_dir(project_root, "evidence")` and return `<evidence>/runner/integration.lock`, so the lock sits beside the evidence it protects in whichever location the project uses. With an explicit `raw`, resolve it through `resolve_bounded_path`; raise `IsolationError` when the path is not bounded by the project root.
  - `process_start_time(pid)` — read `/proc/<pid>/stat`, take the field after the last `)` (the comm field may contain spaces), split on whitespace, and return field index 19 (0-based, after `state`) — that is `/proc/<pid>/stat` field 22 overall. Return `None` on any `OSError` or when the file cannot be parsed. Guard `pid <= 0`.
  - `class IntegrationLock` — module-level `_LOCK_DEPTH: dict[str, int]` keyed by the resolved lock path string gives re-entrancy within a process.
    - `acquire()`:
      1. Resolve the path. If `_LOCK_DEPTH.get(key)` is truthy, increment it and return `{"path": ..., "reentrant": True, "stale_taken_over": False}`.
      2. Try `os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)`. On success, write the JSON payload `{"pid": os.getpid(), "start_time": process_start_time(os.getpid()), "acquired_at": <iso8601 utc>}` and set `_LOCK_DEPTH[key] = 1`; return `{"path": ..., "reentrant": False, "stale_taken_over": False}`.
      3. On `FileExistsError`, read the file and parse the JSON. The holder is **alive** when the recorded pid is alive **and** the recorded `start_time` matches that live process's current start time. A live holder raises `IsolationError` with finding code `integration_locked` and a message naming the holder pid.
      4. A holder that is **not** alive is stale: unlink the file, remember `stale_taken_over = True`, and retry step 2 exactly once. If the retry also fails with `FileExistsError`, raise `integration_locked` (another process won the race).
    - `release()` — decrement `_LOCK_DEPTH[key]`; when it reaches `0`, unlink the lock file **only if** it still records this process's pid, then delete the key.
    - `__enter__` acquires and returns self; `__exit__` releases.

  Pid liveness: use `os.kill(pid, 0)` — `ProcessLookupError` means dead, `PermissionError` means alive-but-not-ours (still alive).

- [ ] **Step 4: Wire the lock into the operations that mutate integration**

  - `scripts/worktree.py`: in `command_prepare` and `command_merge`, acquire the lock for the whole command and release it in a `finally`. The lock path comes from a new `--lock` CLI argument defaulting to `DEFAULT_LOCK_PATH`. When `acquire()` returns `stale_taken_over: True`, append a **warning** finding with code `integration_lock_stale` to the command's output payload (these two commands print a plain JSON payload today, so put the warnings under a `"findings"` key).
  - `scripts/run.py`: in `verb_isolate`, acquire the lock before `prepare_isolation` and release it in a `finally` covering the whole verb. On `IsolationError` from `acquire()`, raise `RunnerError(str(exc), exc.findings)` — the existing `main()` turns a `RunnerError` into exit code `2`.
  - `scripts/worktree.py`: change `_error` and `_warning` to delegate to `daw_common.finding`, and add `finding` to `scripts/daw_common.py`.

- [ ] **Step 5: Run the tests to verify they pass**

  Run: `python3 -m unittest discover -s tests -p "test_worktree.py" -v` then `python3 -m unittest discover -s tests -p "test_isolation.py" -v`

  Expected: PASS.

- [ ] **Step 6: Run the full suite and the gates**

  Run: `python3 -m unittest discover -s tests -p "test_*.py"` then `python3 scripts/validate.py package` then `python3 scripts/validate.py flow --project-root .` then `python3 scripts/route.py --check-suite --root .`

  Expected: all tests OK; package valid; flow reports 9 steps; `--check-suite` reports `ready`.

- [ ] **Step 7: Commit**

  ```bash
  git add scripts/daw_common.py scripts/worktree.py scripts/run.py tests/test_worktree.py tests/test_isolation.py
  git diff --cached
  git commit -m "feat(runner): serialize every integration-touching operation with a file lock" -m "Concurrent isolate runs raced on refs/heads/daw/integration (M1). The integration lock makes one integration-touching operation per repository enforceable rather than aspirational: worktree prepare and merge, and run.py isolate, all take it. Staleness requires the recorded pid to be dead AND its process start time to disagree, so a recycled pid cannot be mistaken for a live holder."
  ```

---

### Task 2: Write-set disjointness and batch selection

`daw-plan` can mark a task `parallel_safe: true`, and nothing consumed that flag. This task gives the runner a mechanical, deterministic answer to "which tasks may run together" that does not trust the plan's flag (anti-goal A2): the runner re-derives disjointness from the manifest itself.

**Files:**
- Create: `scripts/batch.py`
- Test: `tests/test_batch.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `batch.paths_overlap(left: str, right: str) -> bool` — prefix-aware. Normalize by stripping a leading `./` and trailing `/`; overlap when the strings are equal or one starts with the other followed by `/`.
  - `batch.write_sets_disjoint(left: Sequence[str], right: Sequence[str]) -> bool`
  - `batch.undeclared_paths(declared: Sequence[str], actual: Sequence[str]) -> list[str]` — the actual paths no declared path covers, using the same prefix rule.
  - `batch.select_batch_members(manifest: dict, ready: list[dict], pinned: Sequence[str] | None = None, max_concurrency: int | None = None, max_tasks: int | None = None) -> tuple[list[list[str]], list[dict[str, str]]]` — returns the groups (lists of task ids, in order) and warning findings.
    - `manifest` supplies each task's `target_files` and `parallel_safe`; `ready` supplies the deterministic order (dependency depth, then task id) and the `parallel_safe` flag.
    - `max_concurrency` caps the size of one group; `None` means unlimited.
    - `max_tasks` caps the **total** number of members across all groups; the budget is applied *during* grouping, so a group is never larger than the remaining budget. `None` means unlimited.
    - A task with `parallel_safe: false` forms a group of its own.
    - A task with `parallel_safe: true` joins the first group whose members' write sets are all disjoint from its own; otherwise it opens a new group.
    - When a task cannot join a group because of an overlap, a **warning** finding is appended: code `batch_write_set_overlap`, `path` = the task id, message naming both task ids and the overlapping path.

- [ ] **Step 1: Write the failing tests**

  Create `tests/test_batch.py` with a module-level helper `_manifest(tasks)` (reuse the shape from `tests/test_run.py`) and class `BatchSelectionTests(unittest.TestCase)`:

  - `test_disjoint_tasks_share_one_batch` — two tasks with `target_files` `["src/a.py"]` and `["src/b.py"]`, both `parallel_safe: true` → one group of two task ids.
  - `test_overlapping_target_files_are_not_batched_together` — `["src/app.py"]` and `["src/app.py"]` → two groups of one, and a warning with code `batch_write_set_overlap`.
  - `test_a_directory_target_file_overlaps_a_file_inside_it` — `["src/auth"]` and `["src/auth/x.py"]` → two groups of one (prefix-aware, not exact-string).
  - `test_a_task_that_is_not_parallel_safe_runs_alone` — one `parallel_safe: false` task and one `true` task with disjoint writes → the `false` task is in its own group.
  - `test_max_concurrency_caps_a_group` — three disjoint tasks with `max_concurrency=2` → groups of two then one.
  - `test_max_tasks_is_applied_during_grouping` — three disjoint tasks with `max_tasks=2` → the total number of members across all groups is exactly 2, and the selected members are the ones grouping chose (the first two in ready order).
  - `test_grouping_is_stable_across_manifest_order` — the same tasks declared in two different orders produce the same groups.
  - `test_pinned_tasks_with_overlapping_writes_are_serialized` — `pinned=["T-1","T-2"]` where the two overlap → two groups, plus the warning.

- [ ] **Step 2: Run the tests to verify they fail**

  Run: `python3 -m unittest discover -s tests -p "test_batch.py" -v`

  Expected: FAIL with `ModuleNotFoundError: No module named 'batch'`.

- [ ] **Step 3: Implement `scripts/batch.py`**

  Create the module with a docstring stating that it is the batch mechanism, that it never imports `scripts/run.py`, and that the merge gate for a composite lives in `merge_composite_branch` (added in Task 5). Add `from __future__ import annotations`, `import hashlib`, `import pathlib`, `from typing import Any, Sequence`, and the `try: from scripts.daw_common import ... except ImportError: from daw_common import ...` pattern used by the other modules.

  Implement `paths_overlap`, `write_sets_disjoint`, and `undeclared_paths` as pure functions.

  Implement `select_batch_members`:

  1. Build `tasks_by_id` from `manifest["tasks"]`.
  2. Filter `ready` to the pinned ids when `pinned` is given, preserving the ready order.
  3. Walk the filtered ready list in order, maintaining `groups: list[list[str]]`, `remaining = max_tasks` (`None` means unlimited), and `warnings`.
  4. For each candidate: stop when `remaining is not None and remaining <= 0`.
     - If the task is not `parallel_safe`, it forms a new group by itself.
     - Otherwise, find the first group the task can join: every member's `target_files` must be disjoint from the candidate's. Append it there.
     - If it fits no group, open a new group — and, if some existing group blocked it, emit the `batch_write_set_overlap` warning naming the blocking task and the first overlapping path.
     - Respect `max_concurrency`: a group that already holds `max_concurrency` members is skipped when looking for a home; the task then opens a new group.
  5. Decrement `remaining` by one per member added.

  The implementation must be deterministic: same manifest and ready set → same groups, every time.

- [ ] **Step 4: Run the tests to verify they pass**

  Run: `python3 -m unittest discover -s tests -p "test_batch.py" -v`

  Expected: PASS.

- [ ] **Step 5: Commit**

  ```bash
  git add scripts/batch.py tests/test_batch.py
  git diff --cached
  git commit -m "feat(runner): derive batch membership from the manifest, not the plan's flag" -m "A plan's parallel_safe flag is necessary but not sufficient: the runner re-derives write-set disjointness itself, prefix-aware so a directory target overlaps the files inside it. Grouping is greedy first-fit over the ready order, and the task budget is applied during grouping so a group never exceeds it."
  ```

---

### Task 3: Content-hash escape detection

The escape check compared the *set* of dirty paths before and after. A path that was already dirty before the batch and modified further by an agent appears in **both** sets, so the comparison could not see it (measured, M5). A content-hash comparison can. This task makes the check close that false negative — for `isolate` as well as for the batch.

**Files:**
- Modify: `scripts/worktree.py` (replace `snapshot_main_tree` with `snapshot_tree_state`)
- Modify: `scripts/run.py` (use the hash comparison in `verb_isolate`)
- Test: `tests/test_isolation.py`, `tests/test_worktree.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `worktree.snapshot_tree_state(repo: pathlib.Path) -> dict[str, str]` — every dirty path mapped to the SHA-256 of its current bytes. The value is the empty string for a path that does not exist (deleted). Uses `git status --porcelain -uall` so untracked directories are expanded into individual files rather than collapsed into one directory entry.
  - `worktree.escape_paths(before: dict[str, str], after: dict[str, str], owned_prefixes: Sequence[str] = (), owned_paths: Sequence[str] = ()) -> list[str]` — the sorted paths that changed or appeared, excluding runner-owned paths.
    - A path is an escape when it is absent from `before`, or when its hash differs.
    - `owned_prefixes` are repository-relative directory prefixes (a path under one is runner-owned); `owned_paths` are exact repository-relative paths.
  - `worktree.snapshot_main_tree` is **removed**; it had two call sites, both in `run.py`.

- [ ] **Step 1: Write the failing tests**

  In `tests/test_isolation.py`, add to `IsolateTests`:

  - `test_an_agent_modifying_an_already_dirty_path_is_detected` — make `app.py` dirty in the main tree *before* the run, run an agent that appends to `app.py` through an absolute path, and assert the run fails with finding code `worktree_escape_detected`. (The path-set comparison cannot see this; the hash comparison can.)
  - `test_the_runners_own_writes_are_not_mistaken_for_an_escape` already exists and must keep passing — the runner writes context packs, agent logs, and evidence under `docs/daw/evidence/`, and none of it may be reported as an escape.

  In `tests/test_worktree.py`, add class `TreeStateTests(unittest.TestCase)`:

  - `test_a_dirty_path_maps_to_its_content_hash` — write a file, modify it without committing, and assert `snapshot_tree_state` maps the path to the SHA-256 of the new bytes.
  - `test_an_untracked_directory_is_expanded_into_its_files` — create an untracked directory with one file and assert the snapshot names the file, not the directory.
  - `test_a_path_changed_between_snapshots_is_an_escape` — assert `escape_paths` reports a path whose hash changed.
  - `test_runner_owned_paths_are_not_escapes` — assert `escape_paths` skips paths under an owned prefix and paths named exactly.

- [ ] **Step 2: Run the tests to verify they fail**

  Run: `python3 -m unittest discover -s tests -p "test_isolation.py" -v` then `python3 -m unittest discover -s tests -p "test_worktree.py" -v`

  Expected: FAIL — `AttributeError: module 'worktree' has no attribute 'snapshot_tree_state'` and, in the isolation test, the escape is **not** detected (the old path-set comparison returns an empty difference).

- [ ] **Step 3: Implement the hash-based snapshot**

  In `scripts/worktree.py`, replace `snapshot_main_tree` with:

  ```python
  def snapshot_tree_state(repo: pathlib.Path) -> dict[str, str]:
      """Map every dirty path in the working tree to the SHA-256 of its bytes."""
  ```

  - Run `git status --porcelain -uall` in `repo` and parse the same way `dirty_paths` does (two status columns, then the path; ` -> ` for renames).
  - For each path, compute the SHA-256 of the file's bytes when it exists; use the empty string when it does not (a deleted file). Use `daw_common.compute_sha256` for the hashing and read the bytes directly for the missing case.
  - Return the mapping, sorted by path.

  Add `escape_paths(before, after, owned_prefixes=(), owned_paths=())` next to it.

- [ ] **Step 4: Use the hash comparison in `verb_isolate`**

  In `scripts/run.py`:

  - Replace `before_dirty = snapshot_main_tree(project_root)` with `before_state = snapshot_tree_state(project_root)`.
  - Replace the escape comparison with `escaped = escape_paths(before_state, snapshot_tree_state(project_root), owned_prefixes=[...], owned_paths=[...])`, where the owned prefixes are the **project's resolved evidence directory** (`daw_common.artifact_dir(project_root, "evidence")`, relative to the project root) plus the operator's `--work-dir` (default `<evidence>/runner`), and the owned exact paths are the lock file and the isolation state file as resolved by `worktree.lock_path` and `worktree.resolve_state_path`. Derive all three from the same resolver the writers use, so they cannot drift from where the runner actually writes.
  - Update the import list at the top of `run.py` (`snapshot_main_tree` → `snapshot_tree_state`, plus `escape_paths`).

- [ ] **Step 5: Run the tests to verify they pass**

  Run: `python3 -m unittest discover -s tests -p "test_isolation.py" -v` then `python3 -m unittest discover -s tests -p "test_worktree.py" -v`

  Expected: PASS.

- [ ] **Step 6: Commit**

  ```bash
  git add scripts/worktree.py scripts/run.py tests/test_isolation.py tests/test_worktree.py
  git diff --cached
  git commit -m "fix(runner): detect an escape by content hash, not by path set" -m "A path already dirty before the run and modified further by an agent appears in both path sets, so the path-set comparison could not see it. Comparing content hashes closes that false negative, and -uall expands untracked directories so a runner artifact is never mistaken for a new file."
  ```

---

### Task 4: Isolation state for every member, and the batch failure marker

`run.py` never persisted the isolation state at all, so `worktree.py list`'s "accepted" column was blind to runner-driven work and the merge gate had nothing to consult. This task gives the runner a state writer and gives the per-task merge gate a way to refuse a member of a batch whose *combination* was proven broken.

**Files:**
- Modify: `scripts/worktree.py` (state helpers; `merge_task_branch`; `remove --delete-branch`)
- Test: `tests/test_worktree.py`

**Interfaces:**
- Consumes: `daw_common.finding` (Task 1).
- Produces:
  - `worktree.record_task_entry(state_path: pathlib.Path, state: dict, task_id: str, entry: dict[str, Any]) -> None` — merge `entry` into `state["tasks"][task_id]` and save. Existing keys are preserved unless `entry` overwrites them.
  - `worktree.record_batch_failure(state_path: pathlib.Path, state: dict, task_id: str, marker: dict[str, Any]) -> None` — store `state["tasks"][task_id]["batch_failure"] = marker`.
  - `worktree.clear_batch_failure(state_path: pathlib.Path, state: dict, task_id: str) -> None` — remove the key if present.
  - `worktree.batch_failure_marker(state: dict, task_id: str) -> dict[str, Any] | None` — the marker for a task, or `None`.
  - `worktree.accepted_task_ids(state)` — now returns ids whose entry has `merged is True` **or** `accepted is True`. (Existing behavior for `merged` is unchanged.)
  - `worktree.merge_task_branch(repo, integration_worktree, task_branch, task_id, title, project_root=None, evidence=None, state_path=None)` — gains `state_path`. When `project_root` is given and the state file records a batch failure for `task_id`, the merge is refused with finding code `merge_batch_failed` and a message naming the batch id, the composite record path, and the exit codes. The check runs **before** the evidence gate, because a member's own green evidence is not sufficient evidence once the combination has been proven broken.
  - `worktree.remove_task_worktree(repo, worktree_rel, delete_branch: bool = False)` — when `delete_branch` is true, also delete the branch with `git branch -D`. The default keeps the branch (shipped behavior). `worktree.py remove` gains a `--delete-branch` flag.

- [ ] **Step 1: Write the failing tests**

  In `tests/test_worktree.py`, add class `StateMarkerTests(IsolationRepoBase)`:

  - `test_a_recorded_task_entry_survives_a_reload` — write an entry, reload the state, assert the fields are there.
  - `test_a_batch_failure_marker_is_readable_for_its_task` — record a marker and assert `batch_failure_marker(state, "TASK-01")` returns it and returns `None` for another task.
  - `test_a_no_op_member_counts_as_accepted` — an entry with `{"merged": False, "accepted": True}` is returned by `accepted_task_ids`; an entry with `{"merged": False}` is not.
  - `test_clearing_the_marker_removes_it`.
  - `test_merge_refuses_a_member_of_a_failed_batch` — prepare a task, give it green evidence at its commit, record a batch failure marker for it, and assert `merge_task_branch` raises `IsolationError` with finding code `merge_batch_failed` (not `merge_not_verified`).
  - `test_remove_can_delete_the_branch` — `remove_task_worktree(repo, rel, delete_branch=True)` removes the worktree **and** the branch; the default keeps the branch.

- [ ] **Step 2: Run the tests to verify they fail**

  Run: `python3 -m unittest discover -s tests -p "test_worktree.py" -v`

  Expected: FAIL with `AttributeError: module 'worktree' has no attribute 'record_task_entry'`.

- [ ] **Step 3: Implement the state helpers and the marker gate**

  In `scripts/worktree.py`:

  - Implement `record_task_entry`, `record_batch_failure`, `clear_batch_failure`, and `batch_failure_marker` next to `accepted_task_ids`.
  - Change `accepted_task_ids` to select ids where `entry.get("merged") is True or entry.get("accepted") is True`.
  - In `merge_task_branch`, add the `state_path` parameter. Resolve the state file as `state_path` when given, otherwise through `worktree.resolve_state_path(project_root, None)` when `project_root` is given — that resolves the project's own evidence directory, not a hard-coded path. Load it with `load_state` and, when `batch_failure_marker(state, task_id)` returns a marker, raise `IsolationError` with `_error("merge_batch_failed", task_id, reason)` where `reason` names the batch id, the composite record path, and the member's own and composite exit codes.
  - Change `remove_task_worktree` to take `delete_branch: bool = False` and, when true, run `git branch -D <branch>` for the branch that owns the worktree (resolve it with `worktree_for_branch` before removing the worktree, because removing the worktree unregisters the branch association).
  - In `command_remove`, add the `--delete-branch` flag and pass it through. In `command_merge`, resolve the state path from the existing `--state` argument and pass it to `merge_task_branch`.

- [ ] **Step 4: Run the tests to verify they pass**

  Run: `python3 -m unittest discover -s tests -p "test_worktree.py" -v`

  Expected: PASS.

- [ ] **Step 5: Commit**

  ```bash
  git add scripts/worktree.py tests/test_worktree.py
  git diff --cached
  git commit -m "feat(isolation): record every member's state and refuse a failed batch's members" -m "The runner persisted no isolation state, so the merge gate had nothing to consult. Members now get state entries, and a member of a batch whose combination was proven red is refused with merge_batch_failed even when its own evidence is green: individual greenness is not evidence for the combination."
  ```

---

### Task 5: The composite branch, the composite record, and the composite merge gate

This is the heart of the design. The composite's merge history is the authority on which members were merged — the record is checked against it, and the record's exit codes are re-derived from the logs the record points at. A composite whose record was edited by one byte still fails the gate.

**Files:**
- Create: `scripts/batch.py` (composite section)
- Modify: `scripts/worktree.py` (expose `merge_task_branch`'s git merge as a reusable primitive)
- Test: `tests/test_batch.py`

**Interfaces:**
- Consumes: `worktree.run_git`, `worktree.branch_commit`, `worktree.branch_exists`, `worktree.worktree_for_branch`, `worktree.IsolationError`.
- Produces:
  - `batch.batch_hash(base_commit: str, task_ids: Sequence[str]) -> str` — the first 10 hex characters of `sha256(base_commit + "|" + "|".join(sorted(task_ids)))`.
  - `batch.batch_id(base_commit: str, task_ids: Sequence[str]) -> str` — `"batch-" + batch_hash(...)`.
  - `batch.composite_branch_name(batch_id: str) -> str` — `"daw/batch/" + batch_id` with the `"batch-"` prefix stripped.
  - `batch.composite_worktree_rel(worktree_root: str) -> str` — `"<container>/_composite"`.
  - `batch.composite_record_schema_version = 1`
  - `batch.write_composite_record(path: pathlib.Path, record: dict[str, Any]) -> None` — writes JSON with `indent=2, sort_keys=True`.
  - `batch.read_composite_record(path: pathlib.Path) -> dict[str, Any] | None`
  - `batch.validate_composite_record(repo: pathlib.Path, record: dict[str, Any], composite_commit: str | None) -> tuple[bool, str]` — the four-axis gate:
    1. **Commit match** — `record["composite_commit"]` equals `composite_commit` (the composite branch's current tip).
    2. **Completeness** — the set of member commits in the record equals the set of merged commits reconstructed from the composite's own merge history. Reconstruct with `git rev-list --merges --parents <composite_commit> --not <base_commit>`; every line's **second parent** is a merged member commit. A member in the record with no matching merge fails; a merge with no matching record entry fails.
    3. **Uniform green** — every member's `exit_code` is `0`. There is no "newest log wins" rule.
    4. **Log cross-check** — for every member, the log file named by `log_path` (relative to the project root) exists, its SHA-256 equals the record's `log_sha256`, and the log's header `exit_code` equals the record's `exit_code`. The log's header must also carry `branch: <composite_branch>` and `commit: <composite_commit>`.
  - `batch.merge_composite_branch(repo, integration_worktree: str, composite_branch: str, batch_id: str, project_root: pathlib.Path, record_path: pathlib.Path) -> dict[str, Any]` — the gate's only entry point. Loads the record, calls `validate_composite_record`, and on failure raises `IsolationError` with finding code `merge_not_verified` and the reason. On success merges `composite_branch` into the integration worktree with `git merge --no-ff -m "merge(batch): <batch_id>"`; on conflict it runs `git merge --abort` and raises `IsolationError` with finding code `batch_merge_conflict`. Returns `{"merged": True, "merge_commit": <sha>, "batch_id": ..., "composite_commit": ...}`.
  - `batch.build_composite(repo, worktree_root: str, base_commit: str, batch_id: str, members: Sequence[dict[str, Any]]) -> dict[str, Any]` — creates (or recreates) the composite branch at `base_commit` in the composite worktree, then merges each member's branch into it with `git merge --no-ff -m "merge(task): <task_id> <title>"`, in task-id order. On conflict it aborts the merge and raises `IsolationError` with finding code `batch_merge_conflict`. Returns `{"branch": ..., "worktree_path": ..., "commit": <sha after the last merge>, "merged_task_ids": [...]}`.
    - Recreation: if the composite branch or its worktree already exists, remove the worktree (`git worktree remove --force`) and delete the branch (`git branch -D`) before recreating it at `base_commit`. A failed attempt must not contaminate the next one.

- [ ] **Step 1: Write the failing tests**

  In `tests/test_batch.py`, add class `CompositeGateTests(unittest.TestCase)`. Build a real repository (mirror the setup from `tests/test_worktree.py`: `git init`, one committed file, `.gitignore` containing `.worktrees/`), create two task branches off one base commit with divergent edits, merge them into a composite with `batch.build_composite`, and write a composite record plus a matching composite log per member.

  Tests:
  - `test_the_composite_holds_every_member` — the composite's tree contains both members' changes and its merge history has one merge commit per member.
  - `test_a_record_whose_commit_is_stale_is_refused` — change the record's `composite_commit` → `validate_composite_record` returns `False` and the reason mentions the commit.
  - `test_a_record_missing_a_member_is_refused` — drop one member from the record → refused.
  - `test_a_record_with_a_non_zero_exit_code_is_refused` — set one member's `exit_code` to `1` → refused.
  - `test_an_edited_exit_code_is_caught_by_the_log_cross_check` — the record says `0`, the log says `exit_code: 1` → refused (the log is the primary evidence).
  - `test_a_tampered_log_digest_is_refused` — the record's `log_sha256` no longer matches the log's bytes → refused.
  - `test_a_log_missing_the_composite_commit_is_refused` — the log header carries a different `commit:` → refused.
  - `test_merging_a_green_composite_lands_both_members` — `merge_composite_branch` merges into the integration worktree and the integration branch then holds both changes.
  - `test_a_conflicting_member_fails_the_build` — two members editing the same line → `build_composite` raises with finding code `batch_merge_conflict` and the composite branch holds no partial merge.

- [ ] **Step 2: Run the tests to verify they fail**

  Run: `python3 -m unittest discover -s tests -p "test_batch.py" -v`

  Expected: FAIL with `AttributeError: module 'batch' has no attribute 'build_composite'`.

- [ ] **Step 3: Implement the composite section of `scripts/batch.py`**

  Add the naming functions, the record read/write functions, `validate_composite_record`, `build_composite`, and `merge_composite_branch` exactly as specified in the Interfaces block.

  Notes that decide the implementation:

  - The composite log header format is the same one `run.py`'s `run_verification` writes: `$ <quoted argv>`, `exit_code: <n>`, `branch: <composite branch>`, `commit: <composite commit>`, `cwd: <composite worktree>`, a blank line, then the command output. `validate_composite_record` parses the header from the **first twelve lines** of the log, the same way `worktree.latest_verification` parses a task log.
  - `build_composite` must merge with `--no-ff` so each member leaves a merge commit. A member whose branch has no commit beyond the base produces **no** merge commit (git prints `Already up to date.`) — that member is a *no-op* and is simply not in the merged set; the record must not list it either.
  - `validate_composite_record` reads the merged set with `git rev-list --merges --parents <composite_commit> --not <base_commit>`; the `--not` bound is what keeps the base branch's own history out of the reconstruction.
  - The gate lives inside `merge_composite_branch` (design constraint C3): no caller can merge a composite without the record passing.

- [ ] **Step 4: Run the tests to verify they pass**

  Run: `python3 -m unittest discover -s tests -p "test_batch.py" -v`

  Expected: PASS.

- [ ] **Step 5: Commit**

  ```bash
  git add scripts/batch.py tests/test_batch.py
  git diff --cached
  git commit -m "feat(runner): gate the composite on a record cross-checked against its own logs" -m "The composite record is a derived summary, so the gate does not trust it: member membership is reconstructed from the composite's merge-history second parents, the record's commit must equal the composite tip, every member must be green, and every exit code is re-derived from the log the record names, whose digest must still match. Editing one byte of the record turns a red composite green without this cross-check."
  ```

---

### Task 6: The `batch` verb

The verb that ties the mechanism together: select a batch, prepare every member's worktree from one base commit, run the agents concurrently, verify each member alone, build the composite, verify the composite with every member's command, and integrate.

**Files:**
- Modify: `scripts/run.py`
- Test: `tests/test_batch.py`

**Interfaces:**
- Consumes: `batch.select_batch_members`, `batch.build_composite`, `batch.merge_composite_branch`, `batch.batch_id`, `batch.composite_branch_name`, `worktree.IntegrationLock`, `worktree.snapshot_tree_state`, `worktree.escape_paths`, `worktree.record_task_entry`, `worktree.record_batch_failure`, `worktree.clear_batch_failure`, `worktree.accepted_task_ids`.
- Produces:
  - `run.py batch` verb, with arguments: `--plan`, `--project-root`, `--agent-command`, `--tasks` (comma-separated task ids to consider), `--max-concurrency`, `--timeout`, `--agent-timeout`, `--accepted`, `--accepted-file`, `--work-dir`, `--worktree-root`, `--base-ref`, `--add-ignore`, `--dry-run`, `--format`.
    - `--max-concurrency` default: unlimited.
  - `run.run_agent_in_worktree(task, manifest, bodies, project_root, worktree_path, branch, argv_template, work_dir, agent_timeout, timeout_seconds) -> dict[str, Any]` — the per-task execution shared with `verb_isolate`:
    - assembles the context pack **from the worktree** and writes it to `<work_dir>/context-<task_id>.md`;
    - substitutes `{prompt_file}`, `{workspace}`, `{task_id}` and runs the agent with the worktree as its working directory, feeding the pack on stdin;
    - writes `<work_dir>/agent-<task_id>.log`;
    - when the agent exited `0`, commits the worktree with `worktree.commit_task_work`;
    - runs the task's verification command **inside the worktree** with `run_verification`, recording the branch and the commit.
    - Returns `{"task_id", "branch", "commit", "agent_exit_code", "agent_log", "committed", "verification": {...}, "category": "green"|"no-op"|"red", "changed_paths": [...], "undeclared_paths": [...]}`.
    - `category` is `green` when the agent exited `0`, the verification is green, and a commit was produced; `no-op` when the agent exited `0` and the verification is green but nothing was committed; `red` otherwise.
  - `run.execute_batch(manifest, bodies, project_root, member_ids, options) -> dict[str, Any]` — one batch end to end. Returns `{"batch_id", "base_commit", "members": [...], "integrated": bool, "composite": {...}|None, "findings": [...]}`.
  - The batch envelope (`check: "run:batch"`) carries: `workflow_id`, `batches` (one entry per group, each with `id`, `size`, `members`, `base_commit`, `composite_branch`, `composite_commit`, `integrated`, and `members_at_risk` — the number of green members that a red composite would discard), `accepted`, `failed`, `review_dispatch` (added in Task 7), and the standard `findings` / `limitations`.

- [ ] **Step 1: Write the failing tests**

  In `tests/test_batch.py`, add class `BatchExecutionTests(unittest.TestCase)` that builds a real repository with two disjoint source files and two agent scripts, then drives `run.py batch` through the CLI (the same shape as `tests/test_isolation.py`).

  Tests:
  - `test_two_disjoint_tasks_are_batched_and_integrated_as_one_composite` — assert exit `0`, the envelope names one batch of two members, the composite branch exists, and the integration branch holds both members' changes.
  - `test_each_member_runs_in_its_own_worktree` — assert the two agents wrote into different worktrees (each agent appends its task id to a file inside its own working directory; assert both files exist under `.worktrees/` and neither exists in the main tree).
  - `test_the_broken_combination_is_refused_and_the_integration_branch_is_untouched` — two individually-green members that break each other (each bumps the same constant) → exit `1`, finding code `batch_composite_verification_failed`, and the integration branch's tree is byte-identical to its pre-batch tip.
  - `test_a_red_member_is_excluded_and_its_sibling_still_integrates` — one member's agent exits `1` → exit `1`, the sibling is integrated, the red member is reported in `failed`.
  - `test_a_no_op_member_is_accepted_and_does_not_fail_the_batch` — a member whose agent changes nothing → the member is in `accepted`, the batch is green, and no merge commit for that member exists in the composite's history.
  - `test_a_conflicting_member_fails_the_batch_with_the_integration_untouched` — two members editing the same line → finding code `batch_merge_conflict`, integration unchanged.
  - `test_overlapping_declared_writes_are_serialized_and_reported` — two pinned tasks with overlapping `target_files` → two batches, warning code `batch_write_set_overlap`.
  - `test_a_pinned_task_that_is_not_ready_is_refused` — finding code `batch_task_not_ready`, exit `2`.
  - `test_a_stale_task_branch_is_refused` — pre-create the task branch with a commit, then run the batch → finding code `batch_stale_branch`, exit `2`, and the message names the branch, its actual tip, and the expected base.
  - `test_a_member_writing_into_the_main_tree_fails_the_batch` — an agent writing to an absolute path in the main tree → finding code `worktree_escape_detected`, integration untouched.
  - `test_a_member_writing_into_a_sibling_worktree_is_not_reported_as_an_escape` — an agent writes into another member's worktree through an absolute path → the batch is **not** reported as `worktree_escape_detected` (the escape check watches the main tree, not sibling worktrees), and the corruption surfaces as a merge conflict or a red composite, with the integration branch untouched.
  - `test_an_accepted_task_that_was_never_integrated_is_reported` — seed `--accepted` with a task id whose state entry names a commit that is not an ancestor of the batch's base → the batch reports `batch_accepted_not_integrated` instead of verifying a tree that does not contain that work.
  - `test_dry_run_creates_nothing` — assert no branch and no worktree exists afterwards.

- [ ] **Step 2: Run the tests to verify they fail**

  Run: `python3 -m unittest discover -s tests -p "test_batch.py" -v`

  Expected: FAIL — `run.py` has no `batch` subcommand (`argparse` exits `2` with an error).

- [ ] **Step 3: Implement the shared per-task execution**

  In `scripts/run.py`, add `run_agent_in_worktree` with the signature above and extract the corresponding block from `verb_isolate` so both verbs share one implementation. `verb_isolate` keeps its behavior (including its own escape check) and calls the shared helper.

  Extend `run_verification` with two optional parameters so the composite can write its logs elsewhere:

  ```python
  def run_verification(
      task, project_root, timeout_seconds=DEFAULT_VERIFY_TIMEOUT_SECONDS,
      work_dir=None, branch=None, commit=None,
      log_dir: pathlib.Path | None = None, log_prefix: str = "verify",
  ) -> dict[str, Any]:
  ```

  `log_dir` defaults to `evidence_dir(project_root, task["task_id"])`; `log_prefix` selects the file-name stem (`verify-<n>.log` today). Change `next_attempt_index(directory: pathlib.Path, log_prefix: str = "verify") -> int` to count files matching `<log_prefix>-<n>.log`, and pass `log_prefix` through.

- [ ] **Step 4: Implement `execute_batch` and the `batch` verb**

  `execute_batch` performs, in order:

  1. **Lock.** The verb acquires the integration lock once and holds it for every batch it runs.
  2. **Base.** Read `base_commit = worktree.branch_commit(repo, INTEGRATION_BRANCH)`. If the integration branch does not exist yet, prepare it first (`worktree.prepare_isolation` with no task) so there is a base to branch from. The base is read **once** per batch and every member branches from it, so the members are siblings rather than a chain.

  2b. **The accepted set must match the tree.** An accepted task id means "this task's work is already in the integration branch". Before selecting or verifying anything, check that claim against the branch's actual content: for every accepted id whose isolation-state entry records a `merge_commit`, verify that commit is an ancestor of `base_commit` (`git merge-base --is-ancestor <merge_commit> <base_commit>`). An accepted id whose merge commit is **not** an ancestor is an **error** finding with code `batch_accepted_not_integrated` — the composite would otherwise verify a tree that does not contain the work the plan says is already there. An accepted id with **no** state entry (seeded by the operator through `--accepted`) cannot be checked this way: emit a **warning** with code `batch_accepted_unverified` and continue.
  3. **Prepare members.** For each member, in task-id order, create or reuse its worktree **based at `base_commit`**:
     - the branch does not exist → create it at `base_commit`;
     - the branch exists and its tip **is exactly `base_commit`** → reuse it;
     - the branch exists at any other commit → refuse the whole batch with finding code `batch_stale_branch`, the message naming the branch, its actual tip, the expected base, and the operator's way out (`python3 scripts/worktree.py remove --project-root <root> --task <id> --delete-branch`).
     Implement this by extending `worktree.ensure_task_worktree` with an optional `require_tip: str | None = None` parameter that raises the refusal when the branch's tip differs.
  4. **Snapshot.** Take the main tree's hash snapshot (`worktree.snapshot_tree_state`) before the parallel phase. The escape check compares against this snapshot after the whole batch, including the composite phase.
  5. **Parallel phase.** Run every member's `run_agent_in_worktree` concurrently with `concurrent.futures.ThreadPoolExecutor(max_workers=len(members))`. Each member writes only inside its own worktree and its own evidence directory, so the members share nothing.
  6. **Categorize.** `green` = agent exit `0`, verification green, a commit was produced. `no-op` = agent exit `0`, verification green, no commit. `red` = anything else (finding code `batch_task_agent_failed` or `batch_task_verification_failed`).
  7. **Integrate:**
     - zero green members → nothing is integrated. The batch fails if any member was red, and succeeds (accepting every no-op) when every member was a no-op.
     - exactly one green member → merge that member's branch into the integration branch through `worktree.merge_task_branch`, gated by its own green evidence at its commit. No composite is built: there is no combination to verify.
     - two or more green members → `batch.build_composite` at `base_commit`, then run **every green member's** verification command in the composite worktree, sequentially, in task-id order, each writing `composite-<n>.log` into the batch's evidence directory — `daw_common.artifact_dir(project_root, "evidence") / batch_id`, the SAME directory `batch.composite_evidence_dir` bounds the gate against, not a hard-coded path; then write the composite record (which MUST carry `base_commit` = the batch's base commit, so the gate's cross-check against the independently derived base passes); then `batch.merge_composite_branch`.
       - A non-zero composite exit → finding code `batch_composite_verification_failed`; the batch fails and the integration branch is untouched.
       - A merge conflict → finding code `batch_merge_conflict`.
  8. **Record state.** For **every** member, write a state entry: `branch`, `worktree_path`, `worktree_rel`, `merged`, `accepted`, `batch_id`, `commit`, `merge_commit`, and `verified_commit` (the composite commit for a composited member, the member's own commit for the single-green fast path). A green member that was integrated gets `merged: True, accepted: True`. A no-op member gets `merged: False, accepted: True`. A red member gets `merged: False, accepted: False`.
  9. **Failure markers.** When the composite is red or a conflict occurred, call `worktree.record_batch_failure` for every member of the batch with the batch id, the composite branch and commit, the composite record path and its SHA-256, and each member's self-verification and composite exit codes. Clear a member's marker when it is prepared in a later batch (`worktree.clear_batch_failure`).
  10. **Changed paths.** For each member, compute the actual changed paths with `git diff --name-only <base_commit>..<member commit>` in the member's worktree and report them. When a member touched a path its declared `target_files` do not cover, emit a **warning** with code `batch_undeclared_write` (the member is still composited).

  `verb_batch` then:

  1. Loads the manifest, parses `--accepted` / `--accepted-file`, and computes the ready set with `compute_ready`.
  2. Validates `--tasks`: every pinned id must be in the ready set, or the run is refused with finding code `batch_task_not_ready` (exit `2`).
  3. Calls `batch.select_batch_members(manifest, ready, pinned, args.max_concurrency, None)` and extends the findings with the returned warnings.
  4. Runs each returned group as its own batch, in order, through `execute_batch`.
  5. Builds the envelope and returns `0` when every member of every group integrated, `1` when the batch ran and something failed, `2` when refused before any work.

  With `--dry-run`, report the planned groups, the branches that would be used, and the argv that would run — and create nothing.

- [ ] **Step 5: Run the tests to verify they pass**

  Run: `python3 -m unittest discover -s tests -p "test_batch.py" -v`

  Expected: PASS.

- [ ] **Step 6: Run the full suite and the gates**

  Run: `python3 -m unittest discover -s tests -p "test_*.py"` then `python3 scripts/validate.py package` then `python3 scripts/validate.py flow --project-root .` then `python3 scripts/route.py --check-suite --root .`

  Expected: all tests OK; package valid; flow 9 steps; suite ready.

- [ ] **Step 7: Commit**

  ```bash
  git add scripts/run.py scripts/batch.py scripts/worktree.py tests/test_batch.py
  git diff --cached
  git commit -m "feat(runner): composite batch execution with whole-combination verification" -m "Members of a batch all branch from one base commit, so they are siblings rather than a chain. The green members are merged into a scratch composite branch and the composite is verified with every member's command before it reaches the integration branch: the gate proves the combination, not just each part. A red member is excluded and its healthy siblings still integrate."
  ```

---

### Task 7: The review dispatch package

When a member fails, the runner already knows the facts a reviewer needs — but the reviewer must live outside the runner (a vetoing reviewer would un-determinize the gate) and in a **fresh context** (self-review must never be presented as independent review). The runner's contribution is therefore a dispatchable evidence package: facts only, no verdict.

**Files:**
- Modify: `scripts/batch.py`
- Modify: `scripts/run.py`
- Test: `tests/test_batch.py`

**Interfaces:**
- Consumes: everything from Task 6.
- Produces:
  - `batch.write_review_dispatch(project_root: pathlib.Path, task_id: str, facts: dict[str, Any]) -> pathlib.Path` — writes `review-dispatch.json` into the project's evidence directory (`daw_common.artifact_dir(project_root, "evidence") / task_id`) and returns its path.
  - The package's shape (schema version `1`):

    | Field | Content |
    |---|---|
    | `task_id`, `title` | the member |
    | `branch` | the member's branch |
    | `commit` | the member's commit, or `null` when the agent produced none |
    | `base_commit` | the batch's base commit |
    | `diff_range` | `"<base>..<commit>"`, or `""` when there is no commit |
    | `self_verification` | `{"exit_code", "log_path", "log_sha256"}` — `exit_code` may be `null` when the agent never ran |
    | `composite_verification` | `{"exit_code", "log_path", "log_sha256"}` or `null` when the member was never run on the composite |
    | `members` | one row per member of the batch: `{"task_id", "agent_exit_code", "self_verification_exit_code", "composite_exit_code"}` — `null` means *not measured*, and `null` is never `0` |
    | `combination_dependent_task_ids` | the ids whose composite exit differs from their self-verification exit — arithmetic, not judgment |
    | `declared_target_files` | the task's declared write set |
    | `actual_changed_paths` | the paths the member actually changed |
    | `undeclared_paths` | the changed paths the declared set does not cover |
    | `findings` | the finding codes that caused the exclusion |

- [ ] **Step 1: Write the failing tests**

  In `tests/test_batch.py`, add class `ReviewDispatchTests(unittest.TestCase)`:

  - `test_a_red_member_produces_a_package_with_its_evidence` — after a batch where one member's agent failed, assert `review-dispatch.json` exists in the project's evidence directory for that task and names the task id, its agent exit code, and the empty diff range.
  - `test_a_red_composite_produces_a_package_for_every_member` — after a red composite, assert a package exists for **every** member of the batch, not only the apparently guilty one.
  - `test_the_package_distinguishes_red_alone_from_red_only_on_the_composite` — assert the row for the member that is green alone and red on the composite carries a non-null composite exit code, and that its id appears in `combination_dependent_task_ids`.
  - `test_the_package_carries_no_verdict` — assert the JSON has no key whose name contains "verdict", "culprit", or "guilty", and that no value is a prose sentence about responsibility.
  - `test_the_package_names_its_own_path_in_the_envelope` — assert the batch envelope's `review_dispatch` lists the package path for each affected member.

- [ ] **Step 2: Run the tests to verify they fail**

  Run: `python3 -m unittest discover -s tests -p "test_batch.py" -v`

  Expected: FAIL — no package is written.

- [ ] **Step 3: Implement the package**

  In `scripts/batch.py`, add `write_review_dispatch` exactly as specified: build the dictionary from `facts`, write it with `json.dumps(..., indent=2, sort_keys=True)`, and return the path.

  In `scripts/run.py`, inside `execute_batch`:

  - After categorizing the members, decide who gets a package:
    - a **red** member always gets one (its own failure);
    - when the composite is red or a conflict occurred, **every green member** gets one as well, because the runner cannot know which member broke the combination and excluding one on a guess would discard correct work;
    - a member of a fully green batch gets none.
  - Build each package's facts from the member's own result plus the batch-level rows (`agent_exit_code`, `self_verification_exit_code`, `composite_exit_code`).
  - Collect the package paths into the envelope's `review_dispatch` list as `{"task_id": ..., "path": "<repo-relative path>"}`.

- [ ] **Step 4: Run the tests to verify they pass**

  Run: `python3 -m unittest discover -s tests -p "test_batch.py" -v`

  Expected: PASS.

- [ ] **Step 5: Commit**

  ```bash
  git add scripts/batch.py scripts/run.py tests/test_batch.py
  git diff --cached
  git commit -m "feat(runner): hand a failed member's facts to a fresh-context reviewer" -m "The runner computes which members' behavior depends on the combination, but it must not interpret that into a verdict: a reviewer that could veto would un-determinize the gate, and one sharing the worktree would not be an independent reviewer. The package carries recorded exit codes, paths, digests, and commits only; the parent dispatches the review."
  ```

---

### Task 8: The contract and the changelog

**Files:**
- Modify: `references/execution-runner.md`
- Modify: `CHANGELOG.md`
- Modify: `scripts/package_layout.py`

**Interfaces:**
- Consumes: everything from Tasks 1–7.
- Produces: the runner's normative contract for the batch verb, and the migration notes for the newly enforced rules.

- [ ] **Step 1: Ship the new module**

  Add `"scripts/batch.py"` to `OPERATIONAL_SCRIPTS` in `scripts/package_layout.py` (alphabetically it belongs after `"scripts/check_tasks.py"` and before `"scripts/derive_ledger.py"`). The installer copies `OPERATIONAL_SCRIPTS` into the bundle, so the new module must be listed or `batch` fails to import in an installed suite.

- [ ] **Step 2: Document the batch verb in `references/execution-runner.md`**

  Add a new section `## 8. Composite Batch Execution` after the current §7 (Per-Task Isolation) and renumber the following sections, or add it as `## 7A` to avoid renumbering. It must state, in the contract's own voice:

  - the selection rules (ready set, `parallel_safe`, prefix-aware write-set disjointness re-derived by the runner, `parallel_safe: false` runs alone, greedy first-fit, the `--max-concurrency` and `--max-tasks` bounds);
  - the fixed base commit and why the members are siblings;
  - the three member categories (green, no-op, red) and what each is worth;
  - the two gates — the per-task gate and the composite gate's four axes;
  - the composite branch's lifecycle (recreated per attempt at the base commit);
  - the integration lock, which operations take it, and the re-entrancy rule;
  - the escape check's content-hash basis and its batch-level window;
  - the failure matrix with each finding code and its exit code;
  - the review dispatch package: facts only, written by the runner, read by a reviewer the parent dispatches.

  Also add the `run.py batch` invocation to the `## Invocation Reference` code block.

- [ ] **Step 3: Write the changelog entries**

  In `CHANGELOG.md`, under the existing `## Unreleased` heading, add to the `### Added` list:

  - **Composite batch execution (`run.py batch`)** — the entry described above, naming the batch id, the composite branch, the record, the four gate axes, the three member categories, and the integration lock.

  Add a `### Project migration` subsection (the file's convention requires one for every newly enforced rule) with these bullets, each naming the artifact, the finding code or `manual`, and the fix route:

  - **Runner serialization (newly enforced)** — every operation that mutates the integration branch (`run.py isolate`, `run.py batch`, `run.py run`, `worktree.py prepare`, `worktree.py merge`) now takes a file lock at `docs/daw/evidence/runner/integration.lock`; a second operation is refused with `integration_locked` (manual: wait for the first to finish, or remove the lock file when its holder is gone — a stale lock is taken over with the `integration_lock_stale` warning); fix route: none.
  - **Batch write-set disjointness (newly enforced)** — the runner re-derives batch membership from the manifest and refuses to batch two tasks whose declared `target_files` overlap, prefix-aware; the plan's `parallel_safe` flag alone no longer puts tasks in one batch (manual: declare disjoint `target_files`, or serialize the tasks); fix route: `daw-plan`.
  - **Stale task branch (newly enforced)** — a batch member whose branch tip is not exactly the batch's base commit is refused with `batch_stale_branch` (manual: `python3 scripts/worktree.py remove --project-root <root> --task <id> --delete-branch` to start clean); fix route: none.
  - **Failed-batch members (newly enforced)** — after a composite is proven red, `worktree.py merge --task <id>` refuses that member with `merge_batch_failed` (manual: fix the member and merge the new commit — the refusal targets re-integrating the *old* evidence); fix route: none.

- [ ] **Step 4: Run the gates**

  Run: `python3 scripts/validate.py package` then `python3 scripts/validate.py flow --project-root .` then `python3 scripts/route.py --check-suite --root .` then `python3 -m unittest discover -s tests -p "test_*.py"`

  Expected: package valid; flow 9 steps; suite ready; all tests OK.

  Note: `docs/` is **not** shipped in the installed bundle (`tests/test_install.py` asserts the bundle has no `docs/` directory), so these documentation changes never affect an installed payload — but `check_package` link-checks every `.md` under the repository root, so every relative link must resolve. From `docs/daw/`, the repository's own `references/`, `CHANGELOG.md`, and `SKILL.md` are two levels up (`../../`), while the other files in `docs/` are one level up (`../`).

- [ ] **Step 5: Commit**

  ```bash
  git add scripts/package_layout.py references/execution-runner.md CHANGELOG.md
  git diff --cached
  git commit -m "docs(runner): document composite batch execution and its migration notes" -m "The runner's contract gains a batch section, and the changelog records the four newly enforced rules with the artifact, the finding code, and the fix route for each."
  ```

---

### Task 9: The AFK loop runs as isolated batches

`run.py run` currently executes agents with `cwd=project_root` — the user's working tree, with no isolation, no branch, and no commit. That contradicts the suite's isolation contract, and it is the reason the plan's declared parallelism has no execution path. This task migrates the loop.

**Files:**
- Modify: `scripts/run.py`
- Test: `tests/test_batch.py`, `tests/test_run.py`

**Interfaces:**
- Consumes: `run.execute_batch`, `batch.select_batch_members`, everything from Task 6.
- Produces:
  - `run.py run` gains `--max-concurrency` (default: unlimited) and keeps `--max-tasks` (default `1`) with its existing meaning: **the number of tasks the invocation processes**.
  - `verb_run` becomes a loop: compute the ready set → select the next group → execute it → mark accepted or failed → repeat, until no ready task remains or the task budget is spent.
  - The envelope carries `completed` (per-task results), `accepted`, `failed`, and `stopped` (one of `no_ready_task`, `max_tasks`, `all_failed`).

- [ ] **Step 1: Write the failing tests**

  In `tests/test_batch.py`, add class `RunMigrationTests(unittest.TestCase)`:

  - `test_run_works_in_an_isolated_worktree` — run `run.py run` and assert the agent's `cwd` was a worktree (the agent writes a marker file into its working directory; assert the marker is under `.worktrees/` and absent from the main tree).
  - `test_the_users_working_tree_is_never_modified` — assert the main tree's files are byte-identical before and after.
  - `test_run_marks_a_task_accepted_only_when_it_was_integrated` — assert the envelope's `accepted` lists the integrated task and not a red one.
  - `test_a_red_task_is_not_retried_and_the_others_still_proceed` — two ready tasks, one red; assert the red task appears in `failed`, is not attempted twice (the agent log for it records one run), and the green task is integrated.
  - `test_max_tasks_counts_tasks_not_batches` — three ready tasks with `--max-tasks 2` → exactly two tasks are processed.
  - `test_the_default_max_tasks_still_processes_one_task` — `--max-tasks` defaults to `1` → exactly one task is processed even when the tasks are disjoint and batchable.

  In `tests/test_run.py`, keep the existing tests passing: the `run` verb's envelope keys and exit codes must not change shape.

- [ ] **Step 2: Run the tests to verify they fail**

  Run: `python3 -m unittest discover -s tests -p "test_batch.py" -v`

  Expected: FAIL — `run.py run` executes the agent in the project root, so the marker file lands in the user's tree.

- [ ] **Step 3: Implement the migrated loop**

  In `scripts/run.py`, rewrite `verb_run`:

  1. Load the manifest, parse `--accepted` / `--accepted-file`, and read the accepted set from the isolation state file as well (the union). The state file path comes from a new `--state` argument; with no value it resolves through `worktree.resolve_state_path(project_root, None)`, so the runner reads the project's own evidence directory.
  2. Take the integration lock for the whole loop.
  3. Maintain `accepted: set[str]`, `failed: set[str]`, `processed = 0`, and `completed: list[dict]`.
  4. While `processed < args.max_tasks`:
     - compute the ready set with `compute_ready(manifest, accepted)` and drop the ids in `failed`;
     - if it is empty, stop with `stopped = "no_ready_task"`;
     - call `batch.select_batch_members(manifest, ready, None, args.max_concurrency, args.max_tasks - processed)` and take the first group;
     - if there is no group, stop;
     - execute the group with `execute_batch`;
     - for each member: add it to `accepted` when it was integrated or was a no-op; add it to `failed` otherwise;
     - `processed += len(group)`.
  5. Stop with `stopped = "max_tasks"` when the budget is spent. If every ready task ended in `failed`, stop with `stopped = "all_failed"`.
  6. The exit code is `0` when nothing failed, `1` when anything failed.

  The old code path that ran the agent in the project root is removed — `run` now uses `execute_batch`, which uses per-task worktrees. The `--dry-run` behavior is preserved: it reports the planned groups and the argv and creates nothing.

- [ ] **Step 4: Run the tests to verify they pass**

  Run: `python3 -m unittest discover -s tests -p "test_batch.py" -v` then `python3 -m unittest discover -s tests -p "test_run.py" -v`

  Expected: PASS.

- [ ] **Step 5: Run the full suite and the gates**

  Run: `python3 -m unittest discover -s tests -p "test_*.py"` then `python3 scripts/validate.py package` then `python3 scripts/validate.py flow --project-root .` then `python3 scripts/route.py --check-suite --root .`

  Expected: all tests OK; package valid; flow 9 steps; suite ready.

- [ ] **Step 6: Commit**

  ```bash
  git add scripts/run.py tests/test_batch.py tests/test_run.py
  git diff --cached
  git commit -m "feat(runner): run the AFK loop as isolated batches" -m "The loop executed agents in the user's working tree, with no isolation, no branch, and no commit, and it stopped at the first failure. It now drives batches: every task works in its own worktree, a red task is recorded in a failed set instead of aborting the loop, and --max-tasks still counts tasks with its default of 1."
  ```

---

### Task 10: The `run` migration, documented

**Files:**
- Modify: `references/execution-runner.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: everything from Task 9.
- Produces: the contract for the migrated loop, and the migration note for the boundary change.

- [ ] **Step 1: Update the contract's AFK-loop section**

  In `references/execution-runner.md`, rewrite `## 6. The AFK Loop`:

  - the loop now runs each task in its own worktree, through the batch mechanism, and integrates through the same gate;
  - `--max-tasks` counts tasks, default `1`; `--max-concurrency` bounds the group, default unlimited;
  - a failed task is recorded in a `failed` set, is not retried within the same invocation, and does not stop the other ready tasks;
  - the accepted set is the union of `--accepted` / `--accepted-file` and the merged ids in the isolation state file;
  - the `--dry-run` behavior is unchanged;
  - a passing verification is still evidence, never authorization.

- [ ] **Step 2: Write the changelog entry and its migration note**

  In `CHANGELOG.md`, under `### Changed`, add:

  - **The AFK loop is isolated (boundary change)** — `run.py run` executes each task in its own git worktree and integrates through the composite gate, instead of running the agent in the user's working tree.

  Add to the `### Project migration` subsection (Task 8 created it):

  - **The AFK loop no longer writes to the working tree (boundary change)** — `run.py run` now executes every agent in a per-task worktree and commits the result on the task branch, so a task's edits no longer land in the user's working tree (manual: if a workflow depended on the loop editing the working tree directly, run `run.py isolate` per task and merge the integration branch under the ship route); fix route: `daw-ship`.

- [ ] **Step 3: Run the gates**

  Run: `python3 scripts/validate.py package` then `python3 scripts/validate.py flow --project-root .` then `python3 scripts/route.py --check-suite --root .` then `python3 -m unittest discover -s tests -p "test_*.py"`

  Expected: package valid; flow 9 steps; suite ready; all tests OK.

- [ ] **Step 4: Commit**

  ```bash
  git add references/execution-runner.md CHANGELOG.md
  git diff --cached
  git commit -m "docs(runner): record the AFK loop's isolation boundary change" -m "run.py run no longer writes into the user's working tree, and the changelog names the artifact, the manual route, and the fix route for workflows that depended on the old behavior."
  ```

---

## Self-Review

**1. Spec coverage.** §6.1 vocabulary → the naming functions in Task 5 and the categories in Task 6. §6.2 selection → Task 2 and Task 6. §6.3 execution flow → Task 6. §6.4 the two gates → Task 5 (composite gate) and the existing per-task gate. §6.5 escape detection → Task 3. §6.6 evidence layout → Tasks 5, 6, 7. §6.7 the lock → Task 1. §6.8 CLI surface → Task 6 (including the accepted-set-must-match-the-tree check). §6.9 the `run` migration → Task 9. §6.10 the failure matrix → Tasks 1, 4, 5, 6, 7. §6.11 the write-set rule → Task 2. §6.12 branch lifecycle → Task 4 (`--delete-branch`) and Task 6 (`batch_stale_branch`). §6.13 review dispatch → Task 7, plus the `merge_batch_failed` guard in Task 4. §7's six decisions are all carried into the tasks: greedy first-fit (Task 2), unlimited default (Task 2, Task 6), exclusion of a red member (Task 6), sequential composite verification in task-id order (Task 6), composite recreated per attempt (Task 5), and the `run` migration as a second commit (Task 9).

**Three gaps found and closed during this self-review.** The first draft of the plan omitted the spec's "the accepted set must match the tree" check (§6.8, R7) — now step 2b of Task 6, with a test; it did not pin the `next_attempt_index` signature change that the composite's separate log stem requires — now stated in Task 6 step 3; and it had no test for a member writing into a **sibling** worktree, which the escape check deliberately does not watch — now `test_a_member_writing_into_a_sibling_worktree_is_not_reported_as_an_escape` in Task 6.

**2. Step scan.** Every step names either a test to write, a command to run with its expected output, a function to add with its signature, or a command to commit. No step says "handle errors" or "add appropriate validation".

**3. Type consistency.** `batch.select_batch_members` returns `(list[list[str]], list[dict[str, str]])` and Task 6 consumes it exactly that way. `batch.validate_composite_record` returns `(bool, str)` and Task 5's `merge_composite_branch` consumes it exactly that way. `run.execute_batch` returns a dict with the keys `batch_id`, `base_commit`, `members`, `integrated`, `composite`, `findings`; Task 9 reads `members` and each member's `integrated` flag — the category key is `category` in both. `IntegrationLock.acquire()` returns `{"path", "reentrant", "stale_taken_over"}` in both Task 1 and Task 6. `run_agent_in_worktree` returns `{"task_id", "branch", "commit", "agent_exit_code", "agent_log", "committed", "verification", "category", "changed_paths", "undeclared_paths"}` and Task 7 reads `category`, `agent_exit_code`, and `verification`.

**4. Review Focus.** All five lines have a test in the owning task: (1) and (5) → `test_a_member_writing_into_the_main_tree_fails_the_batch` and `test_an_agent_modifying_an_already_dirty_path_is_detected` (Tasks 3, 6); (2) → `test_a_no_op_member_is_accepted_and_does_not_fail_the_batch` (Task 6); (3) → `test_a_member_writing_into_a_sibling_worktree_is_not_reported_as_an_escape` plus `test_each_member_runs_in_its_own_worktree` (Task 6); (4) → `test_overlapping_declared_writes_are_serialized_and_reported` (Tasks 2, 6).

**5. Proportion.** The plan describes ten tasks' worth of behavior without transcribing the implementations: code blocks appear only where the shape is load-bearing (the finding shape, the package's field table, the `run_verification` signature, the member-category table).
