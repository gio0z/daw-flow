# Parallel Batch Execution — Composite Verification Design

<!-- daw-doc -->

**Date:** 2026-11-14
**Status:** proposed, awaiting approval
**Scope:** `scripts/run.py`, `scripts/worktree.py`, `references/execution-runner.md`, suite docs, tests

**Produced by:** the DAW suite's own design route (`daw-design`), recorded under `docs/daw/`. This is a suite-development document — it changes the suite itself, so it is not one of the 14 canonical project document kinds in `references/document-quality.md`, and it is not a client-project artifact.

---

## 1. Intent and why

The suite's execution layer is deterministic in isolation: `next` computes the ready set, `context` assembles a bounded pack, `verify` runs a prescribed command, `isolate` runs one task in its own worktree and merges it only on green evidence. What it cannot yet do is run **several tasks at once**.

Today, parallel work is either impossible or unsafe. An operator who wants three independent tasks done at once has three options, and all three are bad:

1. Run them sequentially — correct, but slow, and the plan's parallelism is unrealized.
2. Run three `isolate` invocations concurrently — **raced**. Measured: `fatal: cannot lock ref 'refs/heads/daw/integration'` and `cannot lock ref 'HEAD'`.
3. Run one `run.py run` AFK loop — correct but sequential, and (as of today) it executes in the shared working tree with no isolation at all.

The gap is not "the runner is slow". It is that **a plan's declared parallelism has no deterministic execution path**. `daw-plan` can mark a task `parallel_safe: true`, and nothing consumes that flag.

This design adds that path: a **batch** of independent tasks executed concurrently in separate worktrees, integrated as a **composite** that is verified as a whole before it reaches the integration branch.

## 2. Goals, non-goals, anti-goals

### Goals

- **G1.** Execute a set of mutually independent ready tasks concurrently, each in its own git worktree, in one runner invocation.
- **G2.** Integrate a batch only as a unit, and only after the **combination** is verified green — not merely each member separately.
- **G3.** Make the batch's selection, ordering, and pass/fail decision mechanical. No model judgment at runtime.
- **G4.** Preserve every existing boundary: no daemon, no auto-merge into a working branch, no protected-branch writes, no pushes, no agent-command discovery, read-only where it was read-only.
- **G5.** Make concurrent *runner invocations* impossible rather than merely unlikely, so the measured race cannot recur.

### Non-goals

- **N1.** Not a scheduler, daemon, or background service. Every invocation does bounded work and exits.
- **N2.** Not a task scheduler with priorities, retries, backoff, or crash recovery.
- **N3.** Not a token-modeled context budget (the current budget is character-based; that stays).
- **N4.** Not a conflict resolver. A conflict inside a composite fails the batch; it is not auto-resolved.
- **N5.** Not a new manifest format. No new task fields, no manifest schema change, no `derive_tasks.py` change.
- **N6.** Not a new adopted-flow step. Composite verification produces no artifact, so it earns no BPF entry; the flow stays at nine steps.

### Anti-goals (outcomes that would make this a failure even if it "worked")

- **A1.** Integrating a composite whose *combination* was never verified, even if every member was individually green. This is the specific failure sequential mode hides and parallel mode would expose.
- **A2.** Letting a plan's `parallel_safe` flag be the *only* evidence that two tasks may run together. The runner must re-derive disjointness mechanically.
- **A3.** Leaving the runner's own artifacts (evidence, context packs, lock file) readable as an agent escaping its worktree.
- **A4.** A batch that succeeds by luck of timing — the integration branch must be provably untouched when a batch fails.
- **A5.** A composite gate that reads "the newest log" and therefore accepts a composite whose last member passed while an earlier one failed. A false green is strictly worse than the race this design set out to kill.

## 3. Constraints

- **C1.** Python 3.10+, standard library only. No third-party runtime dependency.
- **C2.** The runner stays read-only with respect to project intent: it reads a plan, derives state, produces evidence.
- **C3.** The merge gate lives *inside* the merge function, not in its caller, so no entry point can bypass it.
- **C4.** Isolation is git-driven, not harness-driven: the runner behaves identically under any harness or in CI.
- **C5.** The worktree container must be git-ignored; the tool never edits `.gitignore` or global git config.
- **C6.** Evidence lives under the project root in one canonical location, regardless of which worktree produced it.
- **C7.** A batch's success is a property of the *committed tree*, not of the agent's exit code alone.

## 4. Approaches considered

Three approaches were laid out and measured. All three were tested against real git repositories before choosing.

### A. Merge queue — rebase each task onto the integration tip, re-verify, then merge

Guarantee identical to sequential mode: each task is verified against the cumulative state.

Costs, all measured:
- **Rebase changes the commit SHA.** Old verification evidence becomes stale, so the existing merge gate correctly refuses it (`merge_not_verified`). Every task needs a second verification round.
- **Serial merge from a common base can conflict.** Two branches editing the same file produce `CONFLICT (content)` and leave the integration worktree at `UU`.
- Verification cost roughly doubles.

Strong guarantee, high cost, no parallelism benefit beyond wall-clock of the agent itself.

### B. Composite batch — merge the batch into a scratch composite branch, verify the composite, then merge the composite into integration

All task branches are created from **one** base commit. Each member is verified in its own worktree. The green members are merged into a composite branch; the composite is then verified with **every member's** verification command; only then is the composite merged into the integration branch.

Properties:
- **Stronger than sequential.** Sequential verifies task N against `base + task 1..N` only for the last task; a combination break is caught only if a later task's command exercises it. The composite runs *all* members' commands against the *whole* tree, so any cross-member interference surfaces.
- One extra verification round (the composite), not one per task.
- A conflict blocks the whole batch, not one task.

### C. B plus a serial merge-queue fallback

Strongest, most work: on composite failure, fall back to merging tasks one at a time so healthy tasks still land.

Rejected for now. It adds a second integration path (and therefore a second way to bypass the merge gate) to solve a case the operator can solve by re-running with a smaller batch. Recorded here as a possible later increment, not as part of this change.

### Chosen: **B**

The deciding argument is A1. Parallel execution widens a gap that sequential mode closes only incidentally: per-branch green proves `base + this task`, never `base + A + B`. Introducing parallelism without closing that gap would trade a real guarantee for speed nobody asked for. B closes it and is net-cheaper than A's per-task re-verification.

## 5. Measurements that shaped the design

All five were reproduced against real repositories, not assumed.

| # | Finding | Consequence for the design |
|---|---|---|
| M1 | Two concurrent `isolate` runs race on the integration branch: `fatal: cannot lock ref 'refs/heads/daw/integration'`; on merge, `fatal: cannot lock ref 'HEAD': is at 3a293b3...` | Separate worktrees are not sufficient. The integration branch is the contention point. → §7 lock model: every integration-touching operation takes one lock; parallelism lives *inside* one invocation. |
| M2 | Rebase changes the commit SHA, so prior evidence goes stale and the merge gate correctly refuses it (`merge_not_verified`) | "Rebase then integrate" requires re-verification. → rejected approach A; the composite is built from a single fixed base, so no rebase ever happens. |
| M3 | Serial merge from a common base can conflict: `CONFLICT (content)`, integration worktree left at `UU` | A conflict must abort cleanly and leave integration untouched. → §6.10, `batch_merge_conflict`. |
| M4 | Two individually-green tasks can produce a broken composite: each branch bumps the same constant; each passes alone; merged, they conflict | Per-branch green is not sufficient evidence for integration. → composite verification is the integration gate (§6.4). |
| M5 | A path already dirty before the batch, modified further by an agent, appears in *both* before/after path sets → a path-set diff cannot see it. A content-hash diff can. | The escape check must compare content hashes, not path sets. → §6.5. |
| M6 | Merging an **ancestor** into the composite with `--no-ff` prints `Already up to date.`, exits `0`, and creates **no merge commit**. | A member that produced no commit leaves no trace in the composite's history → the completeness check (§6.4) would fail the whole batch over a task that changed nothing. → §6.4, §6.10. |
| M7 | A branch based at the *same* B0 but carrying a prior attempt's commit **passes** `git merge-base --is-ancestor B0 <branch>`. | The staleness rule as first written did not detect the risk it claimed to detect. The correct predicate is "branch tip is exactly B0", not "B0 is an ancestor". → §6.11. |

M5, M6 and M7 were found by the builder checks and are genuine false negatives and false positives in rules the first draft asserted. M7 in particular means the first draft's `batch_stale_branch` rule was wrong in the direction that mattered: it passed the case it was written to catch, and failed the case that must work (a retry after a sibling integrated).

## 6. The design

### 6.1 Vocabulary

- **Ready task** — as today: every dependency accepted, autonomy `afk`.
- **Batch** — a set of ready tasks selected for one composite integration.
- **Base commit (B0)** — the integration branch tip, read **once**, before any task worktree is created. Every task branch in the batch starts at B0, so the branches are siblings and the composite is a merge of siblings, not a chain.
- **Composite branch** — `daw/batch/<hash>`, a scratch branch created at B0 in a scratch worktree, into which the green task branches are merged.
- **Self-verification** — a task's own `verification_command` run in that task's own worktree, at that task's commit.
- **Composite verification** — every green member's `verification_command` run in the composite worktree, at the composite commit.
- **Composite record** — one JSON evidence file describing the composite verification: branch, commit, and every member's command, exit code, and log digest.
- **Integration lock** — an advisory file lock that makes "one integration-touching operation at a time per repository" enforceable rather than aspirational.

### 6.2 Batch selection (deterministic)

Selection reads only the manifest and the accepted set.

1. Start from the ready set (`compute_ready`): dependencies accepted, autonomy `afk`. Ready tasks are mutually independent by construction — a task depending on another ready task would itself be blocked — so no extra dependency check is needed.
2. A task may join a **parallel** batch only if `parallel_safe` is `true`.
3. Two tasks may share a batch only if their `target_files` sets are **pairwise disjoint**. This is re-derived mechanically by the runner from the manifest; the plan's `parallel_safe` flag is a necessary but not sufficient condition (A2).
4. A task with `parallel_safe: false` runs **alone** — its own batch of one. Conservative by construction: the flag exists precisely to say "this task may not run beside another".
5. Grouping is greedy first-fit over the ready order (dependency depth, then task id). Deterministic given the manifest and the accepted set.

   `--max-concurrency` caps the batch size. **Its default is unlimited** — every mutually-disjoint, parallel-safe ready task joins one batch. The cap exists for operators who want to bound resource use on a large plan; it is not the default because the operator already declared the tasks parallel-safe and ready, and because an artificial default silently serializes work the plan asked to run together.

   `--max-tasks` bounds how many tasks the **invocation** processes. The budget is applied **during** grouping, not by truncating the grouped result: the runner walks the ready set in order and stops adding members once the budget is spent, so the selected members are exactly the ones grouping chose, and the batch never exceeds the budget.

   **The blast radius of unlimited concurrency, stated plainly.** A batch of N members creates N task worktrees plus one composite worktree, runs N agents concurrently, and holds the integration lock for the whole batch. If the composite verification fails, **all N members' work is discarded from the integration branch** — not because the members are wrong, but because the combination was proven broken and §6.13 explains why no member can be exonerated mechanically. This is the price of the stronger guarantee, and it is why the batch envelope reports its size and loss exposure before integrating, and why `--max-concurrency` and `--max-tasks` exist as the operator's bounds. Under unlimited concurrency the operator has chosen to accept that blast radius; the runner's job is to make it visible, not to soften it silently.

   The shared working tree is not at risk: every agent works in its own worktree. But the escape-detection window spans the whole batch (§6.5), so an operator editing the main tree during a long batch fails it — a likelihood that scales with N, and one more reason the batch is one operator-bounded operation rather than a background service.

Consequence: a plan that wrongly marks two overlapping tasks `parallel_safe` does **not** get them batched. The runner declines and reports the overlap. The plan's flag cannot talk the runner into a conflict.

### 6.3 Execution flow

```
acquire integration lock
  read B0 = integration tip
  prepare N task worktrees, all based at B0
  snapshot main working tree (escape baseline: path -> content hash)

  parallel phase, N workers, each in its own worktree:
      assemble context pack from that worktree
      run the operator's agent command there
      commit on the task branch
      run the task's self-verification there -> evidence

  green members = agent exited 0, self-verification exited 0, produced a commit
  no-op members = agent exited 0, self-verification exited 0, produced NO commit
                  (nothing to merge; accepted; not composited)
  red members   = the rest (excluded, reported)

  if len(green members) == 0:
      outcome "failed" if there were red members, else "accepted" (all no-op);
      nothing integrated
  elif len(green members) == 1:
      (no combination to verify) merge that branch into integration,
      gated by its own green self-verification at its commit
  else:
      create composite branch daw/batch/<hash> at B0 in a scratch worktree
      merge each green member's branch into the composite (--no-ff, task id order)
        -> conflict => abort, batch fails, integration untouched
      run EVERY green member's verification_command in the composite worktree
      write the composite record (branch, commit, per-member exit codes)
        -> any non-zero => batch fails, integration untouched
      merge the composite into integration, gated by the composite record
        green at the exact composite commit

  snapshot main working tree again (escape check over the whole batch window)
  release lock
```

**Why the base is fixed (B0).** If each task branched from a moving integration tip, the composite would be a chain rather than a set of siblings, and "merge of siblings" would become "rebase and hope". Pinning B0 makes the composite a pure combination of independent changes, which is exactly the property worth verifying.

**Why the fast path keys off green-member count, not batch size.** The composite exists to verify a *combination*. A lone green member has no combination, so building a composite for it would be ceremony. Counting green members (not batch size) also avoids building a pointless composite when a 3-task batch ends with 2 red members and 1 green — the remaining member integrates on its own green evidence, which is exactly the guarantee `isolate` gives today.

**Why one extra verification round.** Self-verification proves each member is sound alone; composite verification proves the members are sound *together*. Both are needed: self-verification localizes a broken member (and excludes it), composite verification is what the integration gate consumes.

**Why the composite branch exists at all.** Merging members directly into the integration branch and verifying afterwards would leave a broken integration branch behind on failure — exactly the "integration worktree left at `UU`" state measured in M3. The composite branch is where failures are allowed to happen.

### 6.4 The two merge gates

Both gates are enforced inside merge functions in `worktree.py`.

**Per-task gate (unchanged).** A task branch reaches the composite only if its self-verification is green **at the exact commit** being merged — the existing `verification_supports_merge` rule.

**Composite gate.** The composite reaches the integration branch only if the composite record says every member was green **at the exact composite commit**. `merge_composite_branch` validates three things, and refuses if any fails:

1. **Completeness** — the record's member set equals the set of task branches actually merged into the composite. The member set is not taken on trust: it is read from the composite branch's own merge history. `git rev-list --merges --parents` exposes each merge commit's **second parent**, which is the exact member commit that was merged. The gate reconstructs the merged set from those second parents and compares it to the record's set — a branch merged without a record entry fails the gate, and a record entry with no matching merge fails it too. (Measured: the second parent is the merged member's commit, so the reconstruction is mechanical and does not parse commit messages.)
2. **Commit match** — the record's commit equals the composite branch's current tip. Anything that changes the composite after verification invalidates the record, exactly as a stale commit invalidates a task's evidence.
3. **Uniform green** — every member entry has exit code `0`. There is no "newest log wins" rule anywhere in this path: the record is the unit of evidence, and a single non-zero member fails the whole gate (A5).
4. **Log cross-check** — every per-member exit code in the record is **re-derived from the member's composite log**, and the record's stored SHA-256 for that log must match the log's actual bytes.

Clause 4 exists because the record alone is not trustworthy evidence. The record is a *derived summary*, it is mutable, and it lives under `docs/daw/evidence/` — which §6.5 deliberately subtracts from escape detection, so editing it raises no alarm. Without the cross-check, changing one byte in the record turns a red composite green and no check notices. The log is the primary evidence; the record is an index over it, and the gate verifies the index against the evidence it points at. The composite log header also carries the composite branch and commit, so "green at the exact composite commit" is attested in the log itself and not only in the record.

**A member that produced no commit.** A member whose agent exited `0` and changed nothing is a legitimate outcome ("nothing to do"). Measured: merging such a member's branch into the composite prints `Already up to date.`, exits `0`, and creates **no merge commit** (M6) — so the member leaves no trace in the composite's history, and a naive completeness check would fail the entire batch over a task that correctly changed nothing. Such a member is therefore a **third category**, distinct from green and red:

| Category | Agent exit | Self-verification | Produced a commit | Treatment |
|---|---|---|---|---|
| **Green** | 0 | green | yes | composited; gates the batch |
| **No-op** | 0 | green | no | not composited (nothing to merge); **accepted**, since its verification passed and the intended end state already holds |
| **Red** | non-zero or verification red | — | — | excluded; reported; not accepted |

A no-op member is accepted but contributes nothing to the composite, so it does not appear in the composite's merge history and does not appear in the record's member set. The completeness check therefore compares the record's set against the merged set, and both exclude no-op members consistently. Under unlimited concurrency this matters a great deal: without this rule, one no-op task among thirty would discard thirty tasks' work.

### 6.5 Escape detection

In batch mode the runner writes evidence, context packs, and the lock file into the project root while agents are running. Those are runner-owned paths and must not be mistaken for an agent escaping its worktree.

The check is:

- snapshot the main working tree as a map of **path -> content hash** for every dirty path (tracked-modified and untracked), before the parallel phase and again after the whole batch completes;
- subtract runner-owned paths (the evidence directory, the work directory, the lock file, the isolation state file) from both sides;
- report an escape when a path is **new** in the after-map, **or** when a path present in both maps has a **different hash**.

The second clause is M5. A path-set diff cannot distinguish "the agent left this path dirty" from "the agent modified this path the user had already modified"; only a hash comparison can. It closes a false negative that would otherwise let an agent quietly overwrite a user's uncommitted work in the main tree.

The window covers the **whole batch**, including the composite phase: a verification command that writes into the main tree through an absolute path is still an escape, and it would otherwise land after the window closed.

This is deliberately batch-level rather than per-worker: under concurrency, per-worker attribution is unreliable (a sibling's in-flight write falls inside another worker's window), and a false negative — missing an escape — is the dangerous direction. A batch-level before/after diff has no false negatives.

The fail-closed consequence is documented: an operator editing the main tree *while a batch runs* is indistinguishable from an escape and will fail the batch. The lock already requires the operator not to run a second integration-touching command at the same time; this extends the same expectation to file edits. The operator can re-run.

### 6.6 Evidence layout

| Artifact | Location | Carries |
|---|---|---|
| Self-verification | `docs/daw/evidence/<task-id>/verify-<n>.log` | command, exit code, branch, commit, cwd (task worktree) |
| Composite verification (per member) | `docs/daw/evidence/<batch-id>/composite-<n>.log` | command, exit code, cwd (composite worktree) |
| **Composite record (the gate's input)** | `docs/daw/evidence/<batch-id>/composite-<n>.json` | composite branch, composite commit, per-member task id, command, exit code, log path + SHA-256 |
| Context pack | `docs/daw/evidence/runner/context-<task-id>.md` | bounded pack, per-file SHA-256 |
| Agent log | `docs/daw/evidence/runner/agent-<task-id>.log` | agent stdout/stderr |
| Isolation state | `docs/daw/evidence/runner/isolation.json` | branch/worktree/merged per task, accepted set |
| Review dispatch package | `docs/daw/evidence/<task-id>/review-dispatch.json` | diff range, evidence digests, per-member sensitivity table, causing findings (§6.12) |
| Integration lock | `docs/daw/evidence/runner/integration.lock` | pid of the holder |

`batch-id` is `batch-<hash>` where `hash` is the first 10 hex characters of `sha256(base commit + sorted task ids)`. It is a function of inputs, so the same batch on the same base gets the same id — the composite branch name and evidence directory are derived from it.

The composite branch and its worktree are scratch artifacts of this tool: each attempt recreates them at B0. Task branches are **not** removed — consistent with the existing rule that branch deletion is not this tool's job.

### 6.7 Integration lock

A file lock at `docs/daw/evidence/runner/integration.lock`, acquired with `O_CREAT|O_EXCL` (atomic on POSIX).

- If the lock is held by a **live** process, the operation refuses immediately with `integration_locked` and does no work.
- If the recorded holder is **gone**, the lock is stale: it is taken over and a warning finding `integration_lock_stale` is emitted. "Gone" means the recorded pid is not alive **and** the recorded process start time does not match a live process with that pid. Pid liveness alone is not sufficient: a pid from another pid namespace, or a recycled pid, makes a live holder look dead — and taking over a live lock's file is exactly the concurrent-integration failure G5 exists to prevent. The lock file therefore records the pid *and* the process start time, and both must agree before the lock is considered stale.
- The lock is released in a `finally` block, so a crash inside a batch still releases it.

**Which operations take it.** Every operation that can mutate the integration branch or its ref:

| Operation | Takes the lock | Why |
|---|---|---|
| `run.py isolate` | yes | merges a task branch into integration; creates the integration worktree |
| `run.py batch` | yes | same, plus creates the composite |
| `run.py run` | yes | drives batches |
| `worktree.py prepare` | yes | creates the integration branch and worktree — this is exactly the ref-lock race measured in M1 |
| `worktree.py merge` | yes | merges into integration; a manual CLI a human can run at the same time |
| `worktree.py commit`, `worktree.py list`, `worktree.py remove` | no | do not touch the integration branch |

Without this, the measured failure mode survives through `worktree.py merge`, and G5 ("impossible, not merely unlikely") would be false.

**Re-entrancy.** `run.py` verbs hold the lock for their whole duration and call into `worktree.py`'s library functions. The lock is therefore re-entrant within a process: acquiring it when the lock file already records *our own* pid succeeds and increments a depth counter; the file is removed only when the outermost holder exits.

**Lock lifetime.** Held for the entire operation that can mutate integration, including the agent run and the composite verification. This is deliberate: releasing it between batches would let a second `run` invocation interleave, and the second invocation's accepted set — derived from the shared state file — would go stale. Fail-closed and simple beats fine-grained and racy.

### 6.8 CLI surface

```
run.py batch --plan <plan> --project-root <root> --agent-command '<json argv>'
             [--tasks id,id,...] [--max-concurrency N] [--timeout S]
             [--agent-timeout S] [--accepted id] [--accepted-file FILE]
             [--work-dir DIR] [--worktree-root DIR]
             [--base-ref REF] [--add-ignore] [--dry-run] [--format json|text]

run.py run   ... [--max-concurrency N]      # existing verb, now batch-driven
```

`--tasks` selects *which* tasks to consider; it does not override the grouping rules (see §6.2 rule 3 and §6.10). A pinned task that is not ready is refused with `batch_task_not_ready` (error) — running it would violate the dependency contract. Two pinned tasks with overlapping write sets are **serialized into separate batches**, not refused, and the split is reported as a warning. The operator's pin expresses "these tasks, now"; the write-set rule expresses safety; honoring both means serializing, not refusing.

`--accepted` / `--accepted-file` mirror `run`. The accepted set is the **union** of those seeds and the task ids the isolation state file already records as merged. This requires the runner to record integrations into the state file — today `run.py` never writes that file at all, so `worktree.py list`'s "accepted" column is blind to runner-driven work. Without this, a task whose dependency was accepted by a human could never be batched, and `run` and `batch` could not compose.

**The accepted set must match the tree.** An accepted task id means "this task's work is already in the integration branch". If an operator seeds `--accepted TASK-X` whose work was never merged into `daw/integration`, the batch's tree does not contain X — and the composite verification then runs against a tree that is not the tree the plan describes. That is a false red at best, and a false green for a plan that assumed X was present. So the runner checks the accepted set against the integration branch's actual content before batching, and reports a mismatch rather than verifying the wrong tree. The check is mechanical: for each accepted task id, the runner resolves the commit it was merged at (from the state file) and verifies that commit is an ancestor of B0.

`--dry-run` reports the planned batches, branches, and commands and creates nothing.

The agent command is operator-supplied and never discovered. Per-task substitutions (`{prompt_file}`, `{workspace}`, `{task_id}`) continue to work: each task gets its own workspace and its own prompt file.

### 6.9 `run` migration

`run.py run` currently executes agents with `cwd=project_root` — the user's working tree, with no isolation, no branch, and no commit. That is inconsistent with the suite's isolation contract and is a prerequisite for parallel dispatch, so `run` is migrated as part of this work:

- `run` becomes a loop over batches: select batch → execute → mark accepted → repeat, until no ready tasks remain or `--max-tasks` is reached.
- **`--max-tasks` keeps counting tasks, with its current default of 1.** The semantics do not change; only the grouping does. Today `--max-tasks 8` runs 8 tasks sequentially; after the change it runs them in batches of up to `--max-concurrency` concurrently. Same count, more concurrency — the existing default keeps its exact meaning, so `run` with no flags still does exactly one task.
- **A failed task does not abort the loop.** Red members are recorded in a `failed` set and excluded from re-selection, so a red task is not retried in the same invocation (which would burn `--agent-timeout` again on work that just failed) while the remaining ready tasks still proceed. The batch semantics already say siblings proceed; the loop mirrors that. The envelope reports `failed` alongside `accepted`, and the exit code is non-zero if anything failed.
- The accepted set is the union of the isolation state's merged tasks and any `--accepted`/`--accepted-file` seeds (§6.8).

This is a deliberate boundary change and is recorded as such in `CHANGELOG.md` under "Project migration": after this change, `run` no longer writes to the user's working tree.

### 6.10 Failure matrix

Severity is stated explicitly rather than left to the envelope's default. Exit codes: `0` = every selected member integrated; `1` = the batch ran but something failed (partial or total); `2` = usage or environment error.

| Condition | Code | Severity | Exit | Effect |
|---|---|---|---|---|
| Second operation while the lock is live | `integration_locked` | error | 2 | Refused before any work |
| Stale lock (holder pid not alive) | `integration_lock_stale` | warning | — | Lock taken over, work proceeds |
| Member's agent exits non-zero | `batch_task_agent_failed` | error | 1 | Member excluded; siblings proceed |
| Member's self-verification exits non-zero | `batch_task_verification_failed` | error | 1 | Member excluded; siblings proceed |
| Member produced no commit (nothing to do) | — | none | — | Not composited; **accepted**; no failure (§6.4) |
| Merge of a member into the composite conflicts | `batch_merge_conflict` | error | 1 | Batch fails; integration untouched |
| Any composite verification exits non-zero | `batch_composite_verification_failed` | error | 1 | Batch fails; integration untouched; composite branch kept; failure marker written |
| Composite record incomplete / stale / not all green / log digest mismatch | `merge_not_verified` | error | 1 | Composite refused; integration untouched |
| A member of a failed batch is merged manually | `merge_batch_failed` | error | 1 | Refused; the combination was proven red (§6.13) |
| Agent wrote outside its worktree | `worktree_escape_detected` | error | 1 | Batch refused; integration untouched |
| A task branch exists at a commit other than B0 | `batch_stale_branch` | error | 2 | Batch refused (§6.12) |
| A member is excluded or the composite is red | (per member) | error | 1 | A `review-dispatch.json` package is written for each affected member (§6.13) |
| Pinned task is not ready | `batch_task_not_ready` | error | 2 | Task refused; batch refused |
| Two batch tasks declare overlapping `target_files` | `batch_write_set_overlap` | warning | — | The two are not batched together; reported |
| A member changed a file outside its declared `target_files` | `batch_undeclared_write` | warning | — | Reported; the member is still composited (§6.11) |

In every failure row, the integration branch is left exactly as it was (A4).

**Exit codes.** `0` = every selected member integrated. `1` = the batch ran and something failed — partial integration, a red composite, a conflict, an escape, or a refused manual merge of a failed batch's member. `2` = the operation was refused *before any work*: the lock was live, the batch's preconditions were not met (a pinned task that is not ready, a stale branch). The distinction is "did work happen", which is what a CI gate needs in order to decide between "the code is broken" and "the invocation was not permitted". This follows the shipped convention: `RunnerError` → 2, error findings → 1.

**The envelope names the packages.** The `review-dispatch.json` paths are listed explicitly in the batch envelope, per member. The parent must not have to glob `docs/daw/evidence/*/review-dispatch.json` to discover them: a discovery step the runner does not own is a step the parent can silently miss, and the package is the entire delivery mechanism of §6.13.

### 6.11 What the write-set rule does and does not cover

Declared `target_files` govern **batch formation** (which tasks may run beside which). The runner also computes each member's **actual** changed paths (`git diff --name-only B0..<member commit>`) and reports them in the batch envelope and in the composite record, flagging `batch_undeclared_write` when a member touched a path it did not declare.

Sibling overlap in *actual* writes is reported but is **not** a hard refusal. Two members appending to different sections of one shared file is legitimate work that git merges cleanly; refusing it would reject valid work. Where actual overlap is a true conflict, git's merge detects it and the batch fails with `batch_merge_conflict` (§6.10).

The residual limit is stated plainly rather than papered over: **cross-member interference that no member's verification command exercises is not detectable by any mechanical rule here.** It is caught only if some command fails on the composite. The protections against it are the plan's `parallel_safe` declaration, the declared write-set disjointness, and the composite verification. A plan that marks two tasks parallel-safe while they secretly share runtime state has mis-declared its contract, and no runner can detect that from the manifest alone. The suite's answer to that is the planner's discipline (`daw-plan`'s Parallelism Criteria), not a stronger runner.

**Directory-shaped `target_files`.** `is_safe_relative_path` (`scripts/daw_common.py:61`) accepts a directory (`src/auth`) as well as a file (`src/auth/x.py`). Exact-string disjointness would treat those two as disjoint while they overlap in reality. So the comparison is **prefix-aware**: a declared path that is a directory prefix of another member's path is an overlap. The same prefix rule applies to the declared-vs-actual comparison, where actual paths are files and declared ones may be directories.

### 6.12 Branch and worktree lifecycle for batch members

The first draft of this design got this wrong, and the builder check caught it. The original rule was "refuse if B0 is not an ancestor of the branch tip". Measured (M7): a branch based at the *same* B0 but carrying a prior attempt's commit **passes** that check, so the rule did not detect the case it was written for. It also failed the case that must work: after any sibling integrates, B0 moves, so the failed member's branch is no longer a descendant — and the rule refused it, meaning one red task poisoned every later batch that included it. That directly contradicts §6.12's promise that a failed member stays re-runnable against a fresh base.

**The correct predicate is: the branch tip is exactly B0.** A branch at exactly B0 carries no prior attempt and is safe to reuse. A branch at anything else carries prior work.

**What to do with a branch that is not at B0.** Three options, and the choice is forced:

| Option | Why it fails |
|---|---|
| Reset the branch to B0 | Destroys the prior attempt's commit — and §6.12's dispatch package points its diff range at `B0..<commit>`, so the reviewer's evidence would dangle. The runner does not delete work. |
| Reuse it as-is | `commit_task_work` runs `git add -A` in a worktree that is never cleaned, so the next attempt would commit the previous attempt's uncommitted leftovers into the branch — unverified content entering the composite. It also turns the "merge of siblings" into a chain, and leaves stale self-verification evidence pointing at a non-tip commit. |
| **Refuse, and say exactly why** | The prior attempt is preserved for review; the operator chooses. |

So the rule is: **a batch member whose branch tip is not exactly B0 is refused with `batch_stale_branch`**, and the finding names the branch, its actual tip, and the expected B0.

**But refusing is only correct if a retry can succeed.** It can, because the batch's base is not the integration tip but *the integration tip at batch start*. On a later invocation, B0 is re-read; if nothing else has integrated since, the failed member's branch is still not at B0 and is still refused. That is the right outcome — the operator must decide whether to keep the prior attempt or start clean — but it must be *decidable*, not accidental. So the runner provides the explicit, non-destructive way to start clean: **`worktree.py remove --task <id>`** drops the worktree and branch, and a subsequent batch then finds no branch and creates one at B0.

The lifecycle in full:

```
batch starts
  B0 = integration tip
  for each member:
      if branch tip == B0 exactly:
          reuse the worktree (it is clean by construction: nothing to commit)
      elif branch does not exist:
          create it at B0
      else:
          refuse: batch_stale_branch, naming branch / actual tip / expected B0
```

**Every batch member's branch must be a descendant of B0, and B0 is fixed for the whole batch.** The composite's completeness check (§6.4) reconstructs the merged set from the composite's merge-history second parents; if a member's branch were not a descendant of B0, that reconstruction could not distinguish "merged" from "inherited", and the gate could not prove what it verified.

### 6.13 Review dispatch: what the runner hands a fresh reviewer

A reviewer is a good idea and a bad idea at the same time, and the distinction matters more than the feature itself.

**Why a fresh-context reviewer is the right instrument.** `daw-review` is explicitly read-only (`skills/daw-review/SKILL.md`: *"Operates strictly read-only"*, *"never performs file mutations"*), and it reviews *changes* against requirements and evidence. The suite's operating rules require an independent perspective — `references/operations.md` §Persistent Worker Graphs: *"self-review must never be presented as independent review."* A reviewer sharing the builder's context has the builder's blind spots; the whole point of the fresh context is that it does not. So when a batch member fails, a reviewer in a fresh context is genuinely the right next step, and the runner should make that possible.

**Why the reviewer must not live inside the runner, and must not gate integration.** Three reasons, in order of force:

1. **A vetoing reviewer would un-determinize the gate.** The runner exists because the pass/fail decision was made by a model at runtime. If a reviewer can reject a member, that decision is generative again — and it would be worse than the original problem, because it would be a *second* model judgment layered on top of the mechanical one. The integration gate stays the composite verification.
2. **A reviewer diagnoses; it does not repair.** `daw-review` never mutates files. So an in-runner reviewer would produce a verdict the runner could not act on, leaving the member stuck: the runner has no mechanism to route findings back to a builder, and inventing one would make the runner a scheduler (N2).
3. **A reviewer sharing the worktree is not an independent reviewer.** `operations.md` is explicit that self-review must never be presented as independent review. The runner's review would run in the same worktree, over the same diff, with the same context — that is a second opinion, not an independent one.

**What the runner does instead: it produces the dispatchable evidence.** The runner already computes, mechanically, the single most useful fact for root-causing a failed member — *which* member's command went red, and *under which combination*. The package carries **facts only, no interpretation**:

| Member | Agent exit | Self-verification exit | Composite exit | Commit |
|---|---|---|---|---|
| A | 0 | 0 | 1 | `abc123` |
| B | 0 | 0 | 0 | `def456` |
| C | 1 | — | — | none |

The runner states one derived fact, because it is arithmetic rather than judgment: **the set of members whose composite exit differs from their self-verification exit is the set whose behavior depends on the combination.** It does not name a culprit, and it does not say who broke whom. If A broke B, then B's row is the one that differs — but "B depends on the combination" is not "B is at fault", and a package that reads as an accusation aims the parent's corrective dispatch at the wrong task. The package says what was observed; the reviewer decides what it means.

The runner also does not interpret its own observations into prose in the package: the parent triages from the raw facts and the findings, not from a runner-authored summary of them. Every package field is either a recorded exit code, a recorded path, a recorded digest, or a recorded commit.

Three shape cases the package must handle, all of which the first draft left undefined:

- **The single-green fast path** (§6.3) has no composite, so the composite-exit column is *null* for every member — not `0`, not "green". The runner reports the agent exit and the self-verification exit only.
- **A member excluded for agent failure** has no commit, so its diff range `B0..<commit>` is empty. The package records the agent exit and the empty range, not a fabricated range.
- **A member excluded for a self-verification failure** has a commit but was never run on the composite, so its composite exit is likewise *null*.

Only a member that was actually composited and actually run on the composite has a non-null composite exit. The null-versus-zero distinction is load-bearing: a null composite exit means "not measured", and a reviewer must not read it as "passed".

**The dispatch package.** When a batch fails, the runner writes one package per failed or excluded member:

```
docs/daw/evidence/<task-id>/review-dispatch.json
```

containing: the task id and title, the branch and commit, the diff range (`B0..<commit>`), the self-verification log path and SHA-256, the composite record's per-member exit codes, the **sensitivity table above**, the declared `target_files` versus the actually changed paths, and the finding codes that caused the exclusion.

The package is written by the runner and read by a reviewer. It is not a verdict, and it is not accepted by anything. The parent orchestrator dispatches the review — `daw-review` or a harness-native fresh reviewer (`references/operations.md` §Persistent Worker Graphs) — and owns the resulting triage, per *"Control feedback at the parent"* and *"The parent holds the Ranked Result Triage queue and decides corrective dispatch."*

**What the runner still does, and does not, do with a failed member.** It excludes the member from the composite and reports it (§6.10). It does not attempt to repair it, does not ask a reviewer to approve it, and does not re-dispatch it. A member excluded for a self-verification failure stays excluded and stays un-accepted; it is re-runnable on the next invocation against a fresh base.

**The manual merge path must not reopen a red composite.** This is the sharpest edge in the whole design, and the builder check found it. `worktree.py merge --task <member>` calls `merge_task_branch`, whose gate reads `latest_verification` → `docs/daw/evidence/<task-id>/verify-*.log`. The composite's logs live under `docs/daw/evidence/<batch-id>/` and are invisible to that reader. So after a red composite, the obvious operator move — *"exclude the suspect, integrate the other one"* — would go straight through `worktree.py merge`, merging one member into the integration branch with nothing checking that the combination had been proven red. That is exactly A1 re-entering through the side door, and it would make §6.13's dispatch package decorative: the parent would be handed a "decide who is guilty" package while the mechanical path already allowed it to pick a winner and merge it.

So the runner writes a **batch failure marker** into the isolation state, and the per-task merge gate consults it:

- On a red composite, the runner records, per member: the batch id, the composite branch and commit, the composite record path and digest, and each member's self-verification and composite exit codes.
- `merge_task_branch` refuses any member whose batch is marked failed, with `merge_batch_failed` — regardless of that member's own green self-verification. The member's individual greenness is not sufficient evidence for integration once the combination has been proven broken; that is the entire point of the composite.
- The marker is cleared when the member is re-run in a later batch, so a legitimate retry is not blocked forever.

**This also settles what the runner writes into the state file.** The runner must write a per-member state entry for every batch member — branch, worktree, `merged: false`, batch id, and the failure marker — not only for integrations. Today `run.py` never persists isolation state at all (`grep record_prepared_task scripts/run.py` → nothing), so the state file is written only by the `worktree.py` CLI. Batch members must appear in it, or the gate has nothing to consult and the manual path stays open.

**The legitimate manual route.** An operator who fixes a member by hand and then wants it merged is not blocked: fixing the member means a new commit, and the merge is gated on green evidence at that new commit. What the gate refuses is specifically *re-integrating a member of a proven-red batch on the strength of its pre-existing evidence*. The finding message names the batch, the composite record, and the exit codes, so the operator can see exactly what was proven red and decide deliberately.

**A note on why a composite failure cannot be repaired by exclusion.** When the composite is red, the runner cannot know which member is guilty: A's command may be red because B broke it. Excluding A on that evidence would discard correct work and leave the batch broken. This is precisely why approach C's serial fallback was rejected — a fallback that guesses the culprit is worse than no fallback. The composite failure is reported whole, with the sensitivity table, and the parent decides.

## 7. Decisions the builder must not re-litigate

1. **Batch grouping algorithm.** Greedy first-fit over ready order, capped by `--max-concurrency`. Alternative: a graph coloring that maximizes group count. Chosen: greedy — deterministic, explainable, and the cap dominates in practice.
2. **Default concurrency.** Unlimited. The operator chose this over a finite default: the plan already declared its tasks parallel-safe and ready, so an artificial cap silently serializes work the plan asked to run together. `--max-concurrency` remains available as an explicit operator bound on resource use.
3. **Self-red member handling.** Excluded from the composite; healthy siblings still integrate. Alternative: fail the whole batch. Chosen: exclusion — a broken sibling should not destroy correct work, and the exclusion is reported loudly.
4. **Composite verification order.** Sequential, in task-id order, in the composite worktree. Alternative: parallel. Chosen: sequential — the members' commands may share caches or fixtures inside the composite tree, and a deterministic evidence order is worth more than the seconds. Two members with an identical `verification_command` are run separately; deduplicating them would make the composite record's per-member mapping ambiguous.
5. **Composite branch lifecycle.** Recreated per attempt at B0. Alternative: kept and reused. Chosen: recreate — a failed attempt's composite must not contaminate the next one.
6. **`run` migration in the same change.** Yes, as a second commit. It is a prerequisite for useful parallel dispatch and cannot be deferred without leaving `run` inconsistent with the isolation contract.

## 8. Builder-check resolutions

Ten questions were raised by a fresh builder reading this document against the existing implementation. Each is answered and, where it changed the design, the change is in the document.

| # | Question | Resolution | Where it landed |
|---|---|---|---|
| Q1 | What does the `run` loop do with a self-red member, and what does `--max-tasks` count? | `--max-tasks` keeps counting tasks, default 1, semantics unchanged. A red member is recorded in a `failed` set, excluded from re-selection, and the loop continues. | §6.9 |
| Q2 | Is the write-set check on declared `target_files` only, or also on actual changes? | Declared sets govern batch formation; actual changed paths are computed, reported, and flagged when undeclared. Actual sibling overlap is reported, not refused. The residual limit is stated explicitly. | §6.10, §6.11 |
| Q3 | Does the lock cover `isolate` and `worktree.py merge`, and how long is it held? | Yes — every operation that can mutate integration takes it, including `worktree.py prepare` and `worktree.py merge`. Held for the whole operation, re-entrant within a process. | §6.7 |
| Q4 | What does the composite gate actually read? | A single composite record (JSON) validated on three axes: completeness against the composite's own merge history, commit match against the composite tip, and uniform green. No "newest log" rule. | §6.4, §6.6 |
| Q5 | Exit code, envelope validity, and severity for a partial batch? | Severity is stated per row; exit `0` only when every selected member integrated, `1` when the batch ran but something failed, `2` for usage. `batch_write_set_overlap` is a warning. | §6.10 |
| Q6 | What happens to a task branch that already exists at a commit other than B0? | Refuse with `batch_stale_branch`. Measured: merging a non-descendant of the current B0 silently reintroduces the prior attempt's changes into the composite — exactly the unverified state the design exists to prevent. The check is `git merge-base --is-ancestor B0 <branch>`. | §6.10, §6.11 |
| Q7 | Does the single-member fast path key off batch size or green-member count? | Green-member count. Zero green → nothing integrated. One green → no composite; integrate on that member's own green evidence. | §6.3 |
| Q8 | Where does `batch`'s accepted set come from? | Union of `--accepted`/`--accepted-file` and the isolation state's merged ids — which requires the runner to start recording integrations into the state file (it does not today). | §6.8 |
| Q9 | Does `--tasks` override the selection rules? | It selects which tasks to consider, not how they group. Overlapping pinned tasks are serialized into separate batches and reported; a pinned task that is not ready is refused. | §6.8, §6.10 |
| Q10 | Is the escape check a path-set diff or a content diff, and does the window cover the composite phase? | Content-hash diff (M5 closes a real false negative), over a window spanning the whole batch including the composite phase. | §6.5 |

### Second builder check — seven findings, all confirmed and folded in

The second check focused on §6.13 (review dispatch), the unlimited-concurrency decision, and the failure matrix. It found seven numbered issues and five secondary ones. Every one was verified against real git and real code before being accepted; three of them overturned rules the first draft had asserted.

| # | Finding | Resolution | Where |
|---|---|---|---|
| R1 | The `batch_stale_branch` predicate (`merge-base --is-ancestor`) **passes** a branch carrying a prior attempt based at the same B0, and **fails** a legitimate retry after a sibling integrated (M7). | Corrected predicate: the branch tip must be **exactly B0**. A branch elsewhere is refused with the branch, its actual tip, and the expected B0 named. Retries work because `worktree.py remove --task <id>` gives the operator a non-destructive way to start clean. | §6.12 |
| R2 | The composite gate trusts the JSON record, which is a derived, mutable summary living under `docs/daw/evidence/` — a directory §6.5 subtracts from escape detection. Editing one byte turns a red composite green. | The gate re-derives every exit code from the member's composite log and checks the record's stored digest against the log's bytes. The composite log header now carries the composite branch and commit. | §6.4 |
| R3 | After a red composite, `worktree.py merge --task <member>` bypasses the whole-combination guarantee — the per-task gate reads only that task's own log, and the composite's logs live elsewhere. A1 would re-enter through the side door. | The runner writes a per-member **batch failure marker** into the isolation state; `merge_task_branch` consults it and refuses with `merge_batch_failed`. The runner now writes per-member state entries for **all** batch members, not only integrations — today `run.py` persists no state at all. | §6.13 |
| R4 | The sensitivity table's prose column is an interpretation and can read as an accusation against the wrong task; it also had no row for agent failure, and was undefined in the single-green fast path. | The package carries **facts only** — recorded exit codes, paths, digests, commits — with the null-versus-zero distinction made load-bearing. The one derived fact stated is the set of members whose composite exit differs from their self-verification exit, which is arithmetic. | §6.13 |
| R5 | A member that produces no commit leaves no merge commit in the composite (M6), so the completeness check would fail the entire batch over a task that correctly changed nothing — catastrophic under unlimited concurrency. | A third category: **no-op** members are not composited and not in the record's member set, but are **accepted**, since their verification passed and the intended end state already holds. | §6.4, §6.3 |
| R6 | Unlimited concurrency's blast radius was never stated: N+2 worktrees, N concurrent agents, and one cross-member interference discarding all N. | The consequences are stated explicitly; the batch reports its size and loss exposure before integrating; `--max-concurrency` and `--max-tasks` are the operator's bounds; §6.13 explains why a composite failure cannot be repaired by exclusion. | §6.2, §6.13, §6.10 |
| R7 | An accepted task seeded with `--accepted` whose work was never merged into the integration branch makes the composite verify against a tree missing that work. | The runner checks the accepted set against the integration branch's actual content and reports a mismatch rather than verifying a tree that is not the one the plan describes. | §6.8 |
| S1 | Exit codes were stated globally, not per row; the "refused before any work" rows fit neither bucket. | Per-row exit codes: `2` = refused before any work, `1` = the batch ran and something failed, `0` = all integrated. | §6.10 |
| S2 | The parent would have to glob `docs/daw/evidence/*/review-dispatch.json` to find packages — a discovery step the runner does not own, and one the parent can silently miss. | The envelope names every package path explicitly. | §6.10, §6.13 |
| S3 | `target_files` may be directories (`src/auth`), so exact-string disjointness treats overlapping paths as disjoint. | Disjointness is **prefix-aware**, for both declared-vs-declared and declared-vs-actual. | §6.11 |
| S4 | `--max-tasks 3` with five disjoint ready tasks — is the batch three, truncated after grouping, or is the budget applied during grouping? | The budget is applied **during** grouping, so the selected members are the same set the grouping chose; the batch never exceeds the budget. | §6.2 |
| S5 | Pid-liveness alone can mistake a live holder for a dead one across pid namespaces or after pid reuse. | The lock file records the holder's pid **and** its process start time; staleness requires both to match. | §6.7 |

Two scope notes the builder deliberately did not raise, recorded so they are visibly decided rather than silently assumed: concurrency mechanics (threads vs. processes, concurrent `git commit` in sibling worktrees) and the CLI flag names are decidable from the existing code and are left to the implementation.

## 9. Test plan

New file `tests/test_batch.py`, plus additions to `tests/test_isolation.py` and `tests/test_worktree.py`.

**Selection**
- disjoint tasks batch together; overlapping `target_files` do not
- `parallel_safe: false` runs alone
- grouping is stable across runs and independent of manifest order
- `--max-concurrency` caps the batch
- `--tasks` pinning: overlapping pins serialize; a not-ready pin is refused

**Execution**
- agents run concurrently in separate worktrees, each `cwd` is its own worktree
- each member's branch starts at B0 (all siblings share one base)

**Gates**
- a green member + a red member → only the green member is composited
- **the key test:** two individually-green members whose combination is broken → composite verification fails and the integration branch is **byte-identical** to B0
- a conflict inside the composite → `batch_merge_conflict`, integration untouched
- a composite record missing a member → gate refuses
- a composite record whose commit is stale → `merge_not_verified`, refused
- a composite record where one member is non-zero → gate refuses (no "newest log wins")
- **a record whose exit code was edited to 0 → the gate re-derives from the log and refuses**
- **a record whose log digest does not match the log's bytes → the gate refuses**
- a member with green evidence at the wrong commit is refused
- a member that produced no commit → not composited, **accepted**, and does not fail the batch
- **after a red composite, `worktree.py merge --task <member>` → `merge_batch_failed`**
- the failure marker is cleared when the member is re-run in a later batch

**Isolation**
- an agent writing into the main tree → `worktree_escape_detected`, batch refused
- an agent modifying a path that was **already dirty** → detected by the hash diff
- runner-owned artifacts (evidence, context packs, lock file) do **not** trigger escape detection

**Locking**
- a second operation while the lock is live → `integration_locked`, no work done
- a lock whose pid is dead → taken over with a warning
- `worktree.py merge` refuses while the lock is held
- the lock is re-entrant within one process

**Review dispatch**
- a failed member produces a `review-dispatch.json` naming its diff range, evidence digest, and per-member sensitivity table
- the sensitivity table distinguishes "red alone" from "red only on the composite"
- a composite failure produces a package for every member, not only the apparently guilty one
- the package contains no verdict and is read by nothing in the runner

**`run` migration**
- `run --max-concurrency 1` isolates: the agent's `cwd` is a worktree, the user's working tree is unchanged afterwards
- `run` marks tasks accepted only when they were integrated
- a red task is not retried in the same invocation; other ready tasks still proceed

## 10. Commit plan

This document lives at `docs/daw/2026-11-14-parallel-batch-design.md` — the suite's own
development-document folder, not a client-project artifact (see `docs/daw/README.md`).

Two commits, each independently green (full suite + package + flow + `--check-suite`):

1. **`feat(runner): composite batch execution with whole-combination verification`** — `worktree.py` composite support and lock, `run.py batch`, findings, tests, docs.
2. **`feat(runner): run the AFK loop as isolated batches`** — `run.py run` migration to per-task worktrees and batch driving, tests, docs.

`references/execution-runner.md` gains a batch section; `CHANGELOG.md` gains entries with a "Project migration" subsection for the newly enforced rules (runner serialization, `run` no longer writing to the working tree, batch write-set disjointness re-derived by the runner, stale-branch refusal). The adopted flow stays at nine steps — composite verification produces no artifact, so it earns no BPF entry (N6).

## 11. Operator decisions

Resolved with the operator:

1. **A self-red member is excluded; healthy siblings still integrate.** Chosen by the operator over failing the whole batch.
2. **Default concurrency is unlimited.** Chosen by the operator over a finite default; `--max-concurrency` remains an explicit operator bound (§7.2).
3. **`run`'s migration lands in the same change**, as a second commit (§10).
4. **A failed member is reviewed in a fresh context — by a reviewer dispatched by the parent, not by the runner.** The operator asked whether a sub-reviewer should run on failure; the answer is yes, with the reviewer outside the runner and outside the integration gate. The runner's contribution is the mechanical sensitivity table and the dispatch package that makes such a review possible (§6.12).
