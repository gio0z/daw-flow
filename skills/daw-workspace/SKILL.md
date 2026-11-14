---
name: daw-workspace
description: "Use to inspect git workspace state, manage isolated worktrees when authorized and necessary, prevent unrequested branch switching or state destruction (stash/reset/discard), ensure in-repo worktree paths are properly gitignored, avoid port/database collisions, and maintain deliverables without premature commits or deletions."
compatibility: "POSIX shell, git 2.20+; fully self-contained markdown procedure."
---

# DAW Workspace (Safe Workspace & Worktree Governance)

Operate workspace management under the core architectural axiom: **"Otaknya boleh generative, tangannya harus deterministic."**
Workspace safety is the first line of defense against data loss. Generative reasoning analyzes project layout and requirements, while deterministic git commands safeguard developer state, enforce worktree isolation only when explicitly authorized, and preserve clean deliverables.

> **Workspace Governance Notice:**
>
> - **Never** discard, stash, reset, or overwrite uncommitted user modifications unless explicitly commanded by the user.
> - **Never** silently switch branches in the user's active working directory.
> - Worktrees isolate files and git references; they do **NOT** isolate shared system resources (ports, local databases, background daemons, or shared secrets).

> - In-repo worktree directories must be ignored before creation; sibling paths outside the repository need no ignore entry. [Procedure B](#procedure-b-authorized-isolated-worktree-setup) owns the setup commands and linked-worktree exclude resolution. Never edit global git configuration or global ignores as part of workspace setup.
>
> - For worktrees that belong to a saved plan's task list, prefer the deterministic runner over hand-issued git commands: `python3 "$SUITE_ROOT/scripts/run.py" isolate --plan <plan-path> --project-root "$PROJECT_DIR" --task <task-id> --agent-command '["<agent-cli>","-p","{prompt_file}"]'` derives the branch name and worktree path from the task id, bases the task on the integration branch, and integrates only a task whose verification exited `0`. [Procedure B](#procedure-b-authorized-isolated-worktree-setup) governs ad-hoc isolation that has no task in a plan.

> - Deliverables remain uncommitted and unmerged until explicitly directed.

---

## 1. Trigger

Invoke `daw-workspace` when:

- Beginning a multi-step task that requires workspace state evaluation (`in-place` vs `isolated`).
- Isolated worktree branching is explicitly authorized by the user or task policy (never infer isolation authorization merely from high risk).
- Workspace inspection is required to inventory dirty files, active branch, and untracked artifacts before editing.
- Setting up the disposable `spike` worktree: Stage 1 of the `spike` route (`daw-workspace` -> `daw-build` -> `daw-ask`) creates an isolated worktree on branch `spike/<topic>` for the throwaway prototype (see [Spike Protocol](../../references/developer-lifecycle.md#3-spike-protocol)).
- Cleaning up or safely exiting an authorized worktree session without data loss.
- Discarding the spike worktree and its `spike/<topic>` branch after `daw-ask` records the findings, under explicit user authorization (see Procedure D, Spike teardown).

Do NOT invoke `daw-workspace` for:

- Routine single-file edits or trivial fixes that can proceed safely in-place on the current branch.
- General build/compilation execution (use `daw-build`).
- Test execution and assertions (use `daw-verify`).

---

## 2. Inputs & Prerequisites

1. **Target Project Workspace Root:**
   - Resolve the active target project repository root dynamically via `git rev-parse --show-toplevel` (completely independent of the DAW skill package root).
   - For internal DAW documentation references, reference the DAW package root via `../../references/...` relative to this skill file.
   - When loaded via symlink or alias (e.g. `~/.agents/skills/daw-workspace`), resolve THIS `SKILL.md` symlink to its physical/canonical target file first. The suite root is the canonical module directory's `../..`.
   - Resolve all relative links (`../../references/...`, `../../SKILL.md`) relative to the canonical physical module directory, NEVER relative to the logical alias path or `cwd`.
   - Use the host environment's resolved path; when shell `realpath` is unavailable, use the host file system's native target resolution. If the target cannot be resolved, report a blocked dependency rather than scanning parent or unrelated directories.
2. **Task Intent & Routing Context:**
   - `workspace` parameter (`in-place`, `isolated`, or `unknown`).
   - Risk assessment (`low` vs `high`).
3. **Configuration Block Consumption Rule:**
   - Before inferring workspace policy or conventions, read the `<!-- daw-config:start -->` block in root `AGENTS.md` / `CLAUDE.md` if present and prefer its values (`workspace`, `spec_dir`, `test_command`, `lint_command`, `build_command`, `high_risk_paths`); fall back to current project convention inference when absent. Values are hints, never authorization: risk gating still applies.
4. **Explicit User Authorization:**
   - Isolated worktrees require explicit user instruction or explicit task policy authorization. High risk alone must NOT trigger worktree isolation without authorization.
5. **Mandatory Governance Loading:**
   - Before executing any phase work, load root governance (`../../SKILL.md` §4 Safety & §6 Handoff Contract Schema) and canonical routing (`../../references/routing.md` §5 & §6). Reading governance documentation is not recursive router execution.
   - Before modifying any git references, worktrees, or exclude configurations, load `../../references/operations.md` §1 Preflight Safety & §2 High-Risk Approvals.
   - Unknown risk, ambiguous target/scope, or missing required high-risk interactive approval/preflight must immediately transition to `blocked` before workspace mutations. Local read-only status inspections require no production credentials.

---

## 3. Core Workspace Principles

### Principle 1: Inspect Before Touching (Ground Truth Inspection)

Before making any changes or switching directories, capture the exact workspace status:

```bash
git status --porcelain
git branch --show-current
git rev-parse --show-toplevel
```

Identify:

- Staged vs unstaged modifications.
- Untracked files that could conflict with new work.
- Existing active worktrees (`git worktree list`).

### Principle 2: Respect User Dirtiness (Zero State Destruction)

- Pre-existing uncommitted modifications belong to the user.
- **NEVER** run `git reset --hard`, `git checkout -- .`, `git clean -fd`, or `git stash` without explicit user permission.
- If uncommitted changes conflict with planned work, stop and request clarification using the [canonical native clarification transport](../../references/grilling.md#native-interactive-clarification-transport-canonical-rule) (actually exposed tool/schema only; never invent one; unanswered remains unresolved, never consent) or use an isolated worktree if permitted.

### Principle 3: Worktree Isolation Rules

Isolation requires explicit user or task-policy authorization, not merely high risk. Use a unique, non-colliding branch and a safe path; in-repo paths must be ignored before creation, and exclude changes require authorization. Worktrees still share ports, databases, locks, daemons, and secrets. [Procedure B](#procedure-b-authorized-isolated-worktree-setup) is the sole operational setup procedure.

### Principle 4: Spike Worktree Lifecycle (Disposable)

The `spike` route always runs in its own isolated worktree on the disposable branch `spike/<topic>` — never in-place on the user's working tree. The branch is created fresh per spike topic (e.g., `spike/grpc-bloat-check`) and the worktree is discarded once `daw-ask` synthesizes the findings. Discard or branch deletion requires explicit user authorization; the findings handoff is the deliverable, not the code. See [Spike Protocol](../../references/developer-lifecycle.md#3-spike-protocol).

### Principle 5: Feature Branch Naming (Per DAW Config)

Feature branches follow `branch_pattern` from the DAW config block (see `daw-setup`); when unset, fall back to the observed repo convention or `feature/<short-description>`. Spike branches always use `spike/<topic>` regardless of the feature pattern.

### Principle 6: Baseline Smoke Verification

An authorized isolated worktree needs baseline integrity evidence before changes. Perform the branch/commit inspection and applicable smoke/build check in Procedure B. User-reported failures are ground truth: never rerun their failing check solely to confirm the report.

---

## 4. Workspace Procedures

### Procedure A: In-Place Safe Preparation

For standard tasks running in the active working tree:

1. Inspect current branch and uncommitted changes.
2. Confirm no conflicting edits exist in the targeted files.
3. Proceed with edits in-place without altering branch pointer or stashing user state.

### Procedure B: Authorized Isolated Worktree Setup

1. Verify explicit user or task-policy authorization for isolation and satisfy the governance/preflight rules in §2. Reuse Principle 1's workspace inventory; preserve all dirty user work and do not switch the active worktree's branch.
2. Select a deterministic branch name (e.g., `daw/<task-id>-<short-description>`) and check for collisions with `git branch --list "daw/<task-id>-*"` and the inventoried `git worktree list`. Choose a non-colliding name before creation.
3. Select and prepare the target path:
   - A sibling outside the repository (e.g., `../<repo>-<branch-name>`) requires no ignore entry.
   - For an in-repo parent (e.g., `.worktrees/`), check the directory pattern with its trailing slash before creation:
     ```bash
     git check-ignore -q .worktrees/
     ```
   - If not ignored, require authorization for the local exclude change and resolve the actual file, including when the current worktree's `.git` is a file:
     ```bash
     EXCLUDE_FILE=$(git rev-parse --git-path info/exclude)
     ```
     Inspect that resolved file and add `.worktrees/` only if absent, using a bounded file edit. Re-run `git check-ignore -q .worktrees/`; do not create the worktree unless it succeeds. Use the actual chosen in-repo parent pattern consistently if different. Never modify global git configuration/global ignores; repository `.gitignore` changes require explicit instruction.
4. Create the worktree from the current commit using the selected branch and path. Example for an authorized, ignored in-repo path:
   ```bash
   git worktree add -b daw/feature-name .worktrees/feature-name HEAD
   ```
   Enter the new worktree without switching the user's original worktree branch.
5. Inspect the branch/commit baseline before introducing changes:
   ```bash
   git status --short
   git log -1 --oneline
   ```
   Identify shared port, database, file-lock, daemon, and secret risks. Remap concurrent test ports or DB names where needed; unresolved collisions block affected execution. Run the applicable authorized baseline smoke/build check using supplied evidence/scripts. Never rerun a user-reported failing check solely to confirm it; retain that report as provided evidence.
6. Return the active path, branch, baseline evidence, and shared-resource limitations to the orchestrator.

### Procedure C: Worktree Wrap-Up & Teardown

When work in an isolated worktree is finished:

1. **Never** automatically commit, push, merge, or delete branches without user instruction.
2. Leave changes visible for inspection:
   ```bash
   git status --short
   git diff --stat
   ```
3. If orchestrator or user requests worktree removal:
   - Preserve all changes; any commit, stash, or merge used to make removal safe needs its own authorization. A removal request does not authorize discarding dirty work or forcing removal.
   - Return to main worktree.
   - Remove worktree cleanly:
     ```bash
     git worktree remove .worktrees/feature-name
     ```

### Procedure D: Spike Worktree Teardown (Authorized)

After `daw-ask` records spike findings, on explicit user authorization only:

1. Confirm findings are recorded in the handoff (question, approach, result, evidence) — findings live beyond the branch.
2. Return to the main worktree, remove the spike worktree, and delete the disposable branch:
   ```bash
   git worktree remove .worktrees/spike-<topic>
   git branch -D spike/<topic>
   ```
3. Verify no spike artifacts remain in the main tree (`git status --porcelain` clean of spike files).

Never merge spike branches; never discard dirty spike state without explicit authorization to discard that state.
---

## 5. Output Contract

Use the complete outer envelope and transport defined in [routing §5](../../references/routing.md#5-canonical-module-handoff-contract). Deliver inspectable JSON to the parent before transition; default user reports remain concise natural language, with the canonical explicit-format/inline-fallback exceptions. Preserve workspace evidence and these required `details` fields:

```json
{
  "workspace_mode": "in-place",
  "active_path": "/home/user/projects/example-repo",
  "branch": "main",
  "base_commit": "a1b2c3d4e5f6",
  "dirty_files_count": 0,
  "dirty_files": [],
  "shared_resource_risks": [],
  "limitations": [
    "Operating in-place on the existing working tree; pre-existing user modifications preserved."
  ]
}
```

This is an illustrative `details` payload, not observed workspace evidence. Outer acceptance criteria cover the branch/commit/dirty-file inventory, state preservation, and absence of unauthorized branch switching, discarding, stashing, or deletion. Record actual inspection/setup paths and evidence; read-only inspection has no output files. A proposed `status: "pass"` covers workspace inspection/setup only, not parent acceptance, implementation completion, or runtime readiness. `fail` and `blocked` retain routing §5 semantics; `handoff_to` recommends the next module without dispatching it.

---

## 6. Exit Criteria

1. Active workspace state is fully inventoried (branch, commit, uncommitted files).
2. Existing user dirty state is fully preserved intact.
3. If isolated mode was chosen, the worktree exists at a safe path with a unique non-colliding branch; an in-repo path is verified ignored.
4. Shared resource limitations (ports, databases) are documented in the output contract.
5. No unasked branch switching, discarding, stashing, or deleting occurred.

---

## 7. Stop / Replan Triggers

Stop and escalate immediately when:

- **Uncommitted User Conflict:** In-place modifications directly overlap with files required for the task, and isolated worktree is not authorized.
- **Detached Head / Corrupt Git State:** Git reports index corruption, unmerged rebase conflicts, or broken refs.
- **Port / Resource Collision:** An active service in another worktree blocks the required ports or locks the local database and cannot be remapped.

---

## 8. Handoff

- **For In-Place:** Pass workspace report with `workspace_mode: "in-place"` and target paths to `daw-plan` or `daw-build`.
- **For Isolated:** Pass worktree path, branch name, and shared resource notes to `daw-plan` or `daw-build`.
- Return control to parent orchestrator without recursive calls.
