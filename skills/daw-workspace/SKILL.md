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

- Worktree directories located inside the repository tree must be gitignored before creation. Use `git rev-parse --git-path info/exclude` to resolve the actual exclude file (especially inside linked worktrees where `.git` is a file). Do **not** modify global git configurations (`~/.gitconfig` or global ignore) silently. Sibling directories outside the repository tree do not require gitignore entries.

> - Deliverables remain uncommitted and unmerged until explicitly directed.

---

## 1. Trigger

Invoke `daw-workspace` when:

- Beginning a multi-step task that requires workspace state evaluation (`in-place` vs `isolated`).
- Isolated worktree branching is explicitly authorized by the user or task policy (never infer isolation authorization merely from high risk).
- Workspace inspection is required to inventory dirty files, active branch, and untracked artifacts before editing.
- Cleaning up or safely exiting an authorized worktree session without data loss.

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
3. **Explicit User Authorization:**
   - Isolated worktrees require explicit user instruction or explicit task policy authorization. High risk alone must NOT trigger worktree isolation without authorization.
4. **Mandatory Governance Loading:**
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
- If uncommitted changes conflict with planned work, stop and request clarification or use an isolated worktree if permitted.

### Principle 3: Worktree Isolation Rules

When an isolated worktree is authorized:

1. **Choose Directory Location & Ignore Policy:**
   - **Sibling Directory (Outside Repo Tree):** E.g., `../<repo>-<branch-name>`. Safe by default; does not pollute the target repository tree and does not require gitignore modifications.
   - **In-Repo Directory:** E.g., `.worktrees/<branch-name>`. MUST be verified as ignored before creation:
     ```bash
     # Check if already ignored
     git check-ignore -q .worktrees
     ```
     If not ignored and local exclude modification is authorized:
     ```bash
     # Resolve the actual exclude path (handles both standard git dirs and linked worktree git files)
     EXCLUDE_FILE=$(git rev-parse --git-path info/exclude)
     # Inspect and update exclude file if verified not ignored
     test -f "$EXCLUDE_FILE" && grep -qxF ".worktrees/" "$EXCLUDE_FILE" || echo ".worktrees/" >> "$EXCLUDE_FILE"
     # Verify it is now recognized as ignored
     git check-ignore -q .worktrees
     ```
     Do NOT modify global git configurations (`~/.gitconfig` or global ignores) or repository `.gitignore` without explicit instruction.
2. **Unique Branch Naming:**
   - Use deterministic, collision-resistant branch names (e.g., `daw/<task-id>-<short-description>`).
   - Ensure the branch does not already exist:
     ```bash
     git branch --list "daw/<task-id>-*"
     ```
3. **Shared Resource Awareness:**
   - Remember: Worktrees share local TCP ports (e.g., `localhost:3000`, `5432`), SQLite/Postgres databases, file locks, and environment variable secrets.
   - Adjust local test port configuration or test DB names if running concurrent instances.

### Principle 4: Baseline Smoke Verification

Upon creating and entering an isolated worktree, verify baseline integrity before introducing changes:

```bash
# Check branch and clean commit baseline
git status --short
git log -1 --oneline
```

Run the applicable baseline smoke test or build step using supplied evidence/scripts (e.g., executing the project test runner or CLI check).
**Ground Truth Rule:** If the task addresses a user-reported failure or bug, **NEVER** rerun the failing check solely to confirm what the user already observed and reported.

---

## 4. Workspace Procedures

### Procedure A: In-Place Safe Preparation

For standard tasks running in the active working tree:

1. Inspect current branch and uncommitted changes.
2. Confirm no conflicting edits exist in the targeted files.
3. Proceed with edits in-place without altering branch pointer or stashing user state.

### Procedure B: Authorized Isolated Worktree Setup

1. Verify explicit authorization for isolated worktree.
2. Determine target path:
   - If inside repository (e.g., `.worktrees/<name>`), verify it is ignored using `git check-ignore -q .worktrees`. If not ignored and authorized, add `.worktrees/` to `$(git rev-parse --git-path info/exclude)` and re-verify without error.
   - If outside repository (e.g., `../<repo>-<name>`), ignore check is not needed.
3. Create worktree off the current commit:
   ```bash
   git worktree add -b daw/feature-name .worktrees/feature-name HEAD
   ```
4. Navigate into the worktree directory.
5. Perform baseline smoke check (running applicable build/smoke test; never rerunning user-reported errors solely to confirm).
6. Notify orchestrator of active working path.

### Procedure C: Worktree Wrap-Up & Teardown

When work in an isolated worktree is finished:

1. **Never** automatically commit, push, merge, or delete branches without user instruction.
2. Leave changes visible for inspection:
   ```bash
   git status --short
   git diff --stat
   ```
3. If orchestrator or user requests worktree removal:
   - Ensure all changes are committed, stashed, or merged as authorized.
   - Return to main worktree.
   - Remove worktree cleanly:
     ```bash
     git worktree remove .worktrees/feature-name
     ```

---

## 5. Output Contract

Every completion of `daw-workspace` delivers a structured handoff payload adhering to the canonical suite envelope. Rich workspace state, branch configuration, and resource risks are preserved under `details`:

```json
{
  "objective": "Inspect git working tree state and configure in-place workspace mode.",
  "input_paths": [],
  "output_paths": [],
  "acceptance_criteria": [
    {
      "criterion": "Capture branch, commit SHA, and uncommitted modifications without state loss",
      "status": "pass"
    },
    {
      "criterion": "Confirm zero destructive git operations (no reset, stash, or clean)",
      "status": "pass"
    }
  ],
  "evidence": [
    {
      "reference": "git status --porcelain",
      "summary": "Verified working tree state: 0 untracked files, 0 conflicts"
    }
  ],
  "status": "pass",
  "handoff_to": "daw-plan",
  "details": {
    "workspace_mode": "in-place",
    "active_path": "/home/user/projects/example-repo",
    "branch": "main",
    "base_commit": "a1b2c3d4e5f6",
    "dirty_files_count": 0,
    "dirty_files": [],
    "shared_resource_risks": [],
    "limitations": [
      "Operating in-place on existing working tree; pre-existing user modifications preserved."
    ]
  }
}
```

_(Note: `status: "pass"` indicates that workspace setup or inspection criteria have been satisfied; it does not indicate implementation completion)._

---

## 6. Exit Criteria

1. Active workspace state is fully inventoried (branch, commit, uncommitted files).
2. Existing user dirty state is fully preserved intact.
3. If isolated mode was chosen, worktree exists at a safe, gitignored path with a unique non-colliding branch.
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
