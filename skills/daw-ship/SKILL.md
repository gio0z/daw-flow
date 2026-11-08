---
name: daw-ship
description: "Use for integration & delivery after daw-verify evidence exists: commit shaping, branch naming, PR draft authoring, CI result triage, review-feedback intake loop, merge readiness, release readiness, and post-merge cleanup handoff. Enforces the pre-ship gate (parent acceptance and daw-verify evidence on the current revision), fail-closed authorization for protected pushes, merge, tag, publish and deploy, and never edits product code."
compatibility: "POSIX shell, git 2.20+, hosting harness PR/CI tools when authorized; fully self-contained markdown procedure."
---

# DAW Ship (Integration & Delivery)

Operate integration and delivery under the core architectural axiom: **"Otaknya boleh generative, tangannya harus deterministic."**
Generative reasoning assembles commits, PR narratives, and triage classifications, but every claim about integration state is established exclusively via deterministic git and CI evidence on the current revision.

> **Ship Contract Notice:**
>
> - **Pre-ship gate is non-negotiable:** `daw-ship` runs only after parent stage acceptance AND `daw-verify` evidence on the **current** revision. Any revision drift invalidates both (see [operations.md §2 Approval Invalidation Rules](../../references/operations.md)).
> - **`daw-ship` never edits product code.** Review feedback and CI `real failure` fixes route back via the parent to `patch`, `feature`, `bugfix`, `maintain`, or `refactor`.
> - **Local commits on a feature branch within authorized scope are allowed.** Pushes to protected branches (`main`, `master`, `release/*`), merge, tag, publish, and deploy require exact interactive authorization at the point of risk per [operations.md §2](../../references/operations.md#2-fail-closed-approval-boundaries).
> - A `daw-ship` `pass` proposes merge/release readiness only; it never authorizes merge, tag, publish, deploy, or post-release closure.

---

## 1. Trigger

Invoke `daw-ship` when:

- Intent is `ship`: integration and delivery of already-verified work (commit hygiene, PR, CI triage, review feedback, merge and release readiness).
- Parent acceptance on prior stages and `daw-verify` evidence for the current revision are present and current.
- Commit shaping is needed before opening a PR (atomic splits, conventional messages).
- A PR draft, CI triage, or review-feedback intake loop is needed.
- Merge readiness or release readiness (version bump proposal, changelog) is being prepared.

Do NOT invoke `daw-ship` for:

- Writing or fixing product code, tests, or specifications (route corrections back via the parent to `patch`, `feature`, `bugfix`, `maintain`, or `refactor`; `daw-ship` never edits product code).
- Verification without runtime evidence (use `daw-verify`).
- Structural analysis or coupling investigation (use `daw-untangle` or `daw-review`).
- Workspace/worktree setup or branch switching without authorization (use `daw-workspace`).
- Spikes, dependency upgrades, or refactor implementation (use `spike`, `maintain`, or `refactor` intents).
- Merge, tag, publish, or deploy without exact interactive authorization (fail closed, see §6 Stop Conditions).

---

## 2. Inputs & Prerequisites

1. **Intent & Route Context:**
   - `intent: "ship"`, stages `["daw-ship"]` (mutating: local commits/branch/PR drafts; does not evaluate the workspace flag).
   - Risk assessment: risk `unknown` -> `needs-input` before any mutation; risk `high` -> interactive approval before any mutation (see contract).
2. **Pre-Ship Gate (blocking, checked before any mutation):**
   - Parent stage acceptance record for prior stages on the current revision (see [Parent Acceptance Checkpoint](../../references/operations.md#parent-acceptance-checkpoint)).
   - `daw-verify` evidence (`details.pre_ship_evidence`, falling back to `details.checks`, convergence, coverage) whose revision matches the current commit (`git rev-parse HEAD`, `git status --short`). Consume it as-is; do not rerun the suite to re-prove it. For multi-session or multi-commit work the task contract and `daw-verify` evidence MUST be persisted in the repo under `docs/evidence/<task-id>/` (or the contract's evidence paths) before commit; inline-only acceptance is limited to single-session trivial/patch work.
   - If either is missing, stale, or bound to an older revision: halt `blocked` naming the missing item. `daw-ship` never manufactures verification or acceptance.
3. **Target Workspace Root:**
   - Resolve the active target repository root via `git rev-parse --show-toplevel` (independent of the DAW skill package root).
   - When loaded via symlink or alias (for example `~/.agents/skills/daw-ship`), resolve THIS `SKILL.md` symlink to its physical/canonical target file first. The suite root is the canonical module directory's `../..`.
   - Resolve all relative links (`../../references/...`, `../../SKILL.md`) relative to the canonical physical module directory, NEVER relative to the logical alias path or `cwd`.
   - Use the host environment's resolved path; when shell `realpath` is unavailable, use the host file system's native target resolution. If the target cannot be resolved, report a blocked dependency rather than scanning parent or unrelated directories.
4. **Configuration Block Consumption Rule:**
   - Before inferring branch, commit, or PR conventions, read the `<!-- daw-config:start -->` block in root `AGENTS.md` / `CLAUDE.md` if present and prefer its values (`test_command`, `lint_command`, `build_command`, `high_risk_paths`, and the delivery keys `commit_convention`, `pr_template`, `ci_checks`, `release_process`, `branch_pattern`); fall back to current project convention inference when absent or `none`. Values are hints, never authorization.
5. **Mandatory Governance Loading:**
   - Before executing any phase work, ensure root governance (`../../SKILL.md` §4 Safety & §6 Handoff Contract Schema) and canonical routing (`../../references/routing.md` §5 & §6) are in context. If already loaded and active in the current session, reuse them directly without redundant re-reading.
   - Before any git mutation, PR action, or remote push, load `../../references/operations.md` §1 Preflight Safety and §2 Fail-Closed Approval Boundaries. Unknown risk, ambiguous target/scope, or missing required high-risk interactive approval/preflight must immediately transition to `blocked` before mutations.

---

## 3. Ship Procedures

### Procedure A: Pre-Ship Gate & Inventory

```bash
git status --short
git branch --show-current
git rev-parse HEAD
git log --oneline -10
```

1. Confirm parent acceptance and current-revision `daw-verify` evidence (§2, item 2). Record the verified revision SHA in `details.commits.base_revision`.
2. Inventory dirty files, untracked artifacts, and worktrees (`git worktree list`). Preserve all pre-existing user state; never stash, reset, or discard user work without explicit instruction (see `daw-workspace` principles).
3. Stop `blocked` if the tree contains unrelated uncommitted work that overlaps the ship scope.

### Procedure B: Branch Naming

- Ship operates on the existing feature branch. New branches are created only when absent, following config `branch_pattern`; when unset, use the observed repo convention, else `daw/<task-id>-<short-description>` (kebab-case, max 50 characters, no spaces).
- Check collisions before creation (for example `git branch --list "daw/<task-id>-*"`).
- Never silently switch branches in the user's active working directory; branch creation requires the governed authorization in §2.

### Procedure C: Commit Shaping

Follow [Commit Hygiene](../../references/developer-lifecycle.md#7-commit-hygiene) in full:

```bash
git status --short
git diff --stat
git diff --cached --stat
git log -3 --oneline
```

1. One commit = one logical change; never mix behavior with refactor. Split commits above **400 changed lines** unless inseparability is justified in the commit/PR body.
2. Conventional subject `type(scope): subject` (imperative, **<= 72 characters**, no trailing period) with a why-body stating the reason, not only the diff.
3. Stage explicit paths only (`git add <paths>`); never `git add -A`/`git add .`. Inspect `git diff --cached` before every commit.
4. Secret scan before committing; **0 tolerated** secret hits (block, remove, and check history).
5. Local commits on a feature branch within authorized scope proceed without redundant prompts; this does not authorize any protected-branch push.

### Procedure D: PR Draft Authoring

Follow [Pull Request & CI Protocol](../../references/developer-lifecycle.md#8-pull-request--ci-protocol) in full.

1. Open draft first via the harness PR tool **only when explicitly authorized**, or write a local draft file (for example `pr-draft.md`, uncommitted unless instructed) otherwise. Never open a ready PR without green CI on the current revision and a complete description.
2. Use the repository PR template (config `pr_template`) when one exists, ensuring it still covers: `What`, `Why`, `How tested` (exact commands + observed results), `Risk` (blast radius, high-risk paths), `Rollback` (exact revert/redeploy step). Base and head revisions are explicit SHAs.
3. PR size guidance: **< 400 changed lines** target; above **1,000** lines split is mandatory unless a reviewer explicitly accepts the batch.

### Procedure E: CI Result Triage

Follow the triage taxonomy and quarantine rules in [Pull Request & CI Protocol](../../references/developer-lifecycle.md#8-pull-request--ci-protocol).

1. Record every run in `details.ci` with its classification: `real failure`, `flaky`, or `infra`. Silent retry-until-green is forbidden.
2. `real failure` -> route correction via parent to the owning build route; refresh `daw-verify` evidence on the new revision.
3. `flaky` -> quarantine once it flakes **3 times in 10 runs** (linked issue + owner); merge readiness requires **10/10 pass** on the current revision or the quarantine in place.
4. `infra` -> escalate as infrastructure; never edit product code to satisfy infra noise.

### Procedure F: Review-Feedback Intake Loop

Follow [Review Feedback Protocol](../../references/developer-lifecycle.md#9-review-feedback-protocol) in full.

1. Classify **every** comment into exactly one disposition (`must-fix` / `should` / `nit` / `question` / `disagree`) and record it in `details.review_threads` with the response and resulting action.
2. Dispositions route corrections back **via the parent** to `patch`/`feature`/`bugfix`/`maintain`/`refactor`. `daw-ship` replies per thread, proposes fixes, and reruns affected checks after landing; `daw-ship` never edits product code.
3. Never resolve reviewer threads on their behalf: reply, propose, refresh evidence; only the reviewer resolves.
4. After **3 review rounds** without convergence on a thread, escalate to the parent for a scope decision instead of iterating further.

### Procedure G: Merge & Release Readiness

Follow [Release Readiness](../../references/developer-lifecycle.md#10-release-readiness) in full.

1. **Merge readiness checklist (all must hold):**
   - Pre-ship gate still valid on the current revision (no unrecorded drift).
   - CI: no unresolved `real failure`; `flaky` quarantined or **10/10 pass**; `infra` resolved or parent-recorded waiver.
   - Review: every thread classified; no unanswered `must-fix`; no unresolved `disagree` blocked on ship alone.
   - Description template complete with exact `How tested` evidence.
2. **Release readiness:** semver decision recorded (breaking -> major, feature -> minor, fix -> patch; choose higher when in doubt); version bump in exactly one source of truth; changelog generated from `git log <last_tag>..HEAD` with every merged commit mapped once; `daw-verify` evidence on the release-candidate revision.
3. **Point-of-risk actions (each needs its own exact interactive authorization):** merge, protected-branch push, `git tag`, publish, deploy. A prior approval never covers a new revision or version. On any drift, halt and request fresh confirmation.
4. **Post-merge cleanup handoff:** after an authorized merge, propose branch deletion and worktree removal to the parent; never auto-delete branches, worktrees, or local artifacts. Hand the parent the cleanup inventory (`git branch -d`, `git worktree remove` targets) for authorized execution.
5. **Retrospective trigger:** when the ship cycle surfaced a reusable lesson (a `real failure` CI class, a `must-fix` review pattern, a quarantined flaky test, a rework round, or an exceeded time-box), record it in `details.retro_candidates` with its evidence and proposed conversion (DAW config rule via `daw-setup` or regression test via `daw-build`/`daw-verify`) per [Retrospective & Convention Feedback](../../references/developer-lifecycle.md#11-retrospective--convention-feedback). Empty is valid; the parent decides conversion.

---

## 4. Ship Invariants

1. **Integration-only.** `daw-ship` authors git/commit/PR/CI/release artifacts; it never mutates product code, tests, or specifications.
2. **Current-revision truth.** Every `details` claim binds to the revision inspected (`git rev-parse HEAD` recorded). Evidence from older revisions is reported as stale, never reused as current.
3. **No fabricated green.** CI passes, review approvals, and release readiness are recorded only from observed harness or git evidence; unavailable evidence is `blocked`/`unexercised`.
4. **Secrets redacted.** Commands, PR bodies, and audit records record key names only (for example `AUTH_TOKEN=[REDACTED]`), never credential values (see [operations.md §5](../../references/operations.md#5-semantic-verification-audit-records--secret-redaction)).

---

## 5. Output Contract

Use the complete outer envelope and transport defined in [routing §5](../../references/routing.md#5-canonical-module-handoff-contract). Deliver inspectable JSON to the parent before transition; default user reports remain concise natural language, with the canonical explicit-format/inline-fallback exceptions. Preserve ship evidence and these required `details` fields:

```json
{
  "commits": {
    "base_revision": "a1b2c3d4e5f6",
    "head_revision": "b2c3d4e5f6a1",
    "branch": "daw/<task-id>-<short-description>",
    "commits": [
      {
        "sha": "b2c3d4e5f6a1",
        "subject": "feat(auth): add session token_version passthrough",
        "changed_lines": 42
      }
    ],
    "shaping_notes": "Atomic split applied; refactor separated from behavior change."
  },
  "pr": {
    "status": "draft",
    "url_or_path": null,
    "draft_path": "pr-draft.md",
    "description_complete": true,
    "changed_lines": 42
  },
  "ci": [
    {
      "run_id": "ci-123",
      "revision": "b2c3d4e5f6a1",
      "classification": "flaky",
      "evidence": "passed on rerun without code change; 3 flakes in 10 runs, quarantined",
      "quarantine": { "issue": "ISSUE-7", "owner": "platform" }
    }
  ],
  "review_threads": [
    {
      "thread_id": "t1",
      "disposition": "must-fix",
      "response": "Fixed via patch route on new revision; reran affected checks.",
      "routed_to": "patch",
      "resolved_by_reviewer": false
    }
  ],
  "release": {
    "semver_decision": "minor",
    "version_source": "pyproject.toml",
    "changelog_from": "v1.2.0",
    "tag": null,
    "publish": null,
    "deploy": null
  },
  "retro_candidates": [
    {
      "lesson": "Integration tests depended on wall-clock time and flaked in CI.",
      "evidence": "ci-123 classification flaky, 3 flakes in 10 runs",
      "proposed_conversion": "regression test with injected clock via daw-build/daw-verify"
    }
  ],
  "limitations": ["Merge and tag pending exact interactive authorization."]
}
```

This is an illustrative `details` payload, not observed ship evidence. Outer acceptance criteria cover the pre-ship gate validity, commit hygiene, PR template completeness, CI triage classifications, review-thread dispositions, and release-changelog mapping. Record actual revision SHAs, PR identifiers, and CI observations. A proposed `status: "pass"` covers ship readiness only, not parent acceptance, merge authorization, or release completion. `fail` and `blocked` retain routing §5 semantics; `handoff_to` recommends the next module (for example `patch`, `feature`, `bugfix`, or the parent) without dispatching it.

---

## 6. Exit Criteria

1. Pre-ship gate held: parent acceptance and current-revision `daw-verify` evidence recorded in `details.commits` before any mutation.
2. Commits are atomic, conventional (`type(scope): subject`, **<= 72 characters**), why-bodied, secret-scanned, and inspected via `git diff --cached`.
3. PR (or local draft) exists with a complete `What`/`Why`/`How tested`/`Risk`/`Rollback` description; `details.pr` reflects its draft status.
4. Every CI run is classified (`real failure` / `flaky` / `infra`) with recorded evidence; no silent retry-until-green.
5. Every review thread has exactly one disposition; corrections routed via the parent; no reviewer thread resolved by `daw-ship`.
6. Merge readiness checklist and release semver/changelog mapping are recorded; tag/publish/deploy remain unexecuted pending authorization.
7. Post-merge cleanup handoff inventory is recorded for the parent.

---

## 7. Stop / Replan Triggers

Stop and escalate immediately when:

- **Pre-Ship Gate Failure:** Parent acceptance or current-revision `daw-verify` evidence is missing or stale (revision drift). Halt `blocked`; never self-approve.
- **Protected-Branch / Point-of-Risk Demand:** Any request to push to a protected branch, merge, tag, publish, or deploy without exact interactive authorization naming target, revision/version, and scope. Halt `blocked` per [operations.md §2](../../references/operations.md#2-fail-closed-approval-boundaries).
- **CI Real Failure:** Classification is `real failure` and cannot be resolved by triage alone. Halt and route via parent to the owning build route with the failing evidence.
- **Unconverged Review:** **3 rounds** without convergence on a thread. Halt and request a parent scope decision.
- **Scope Collision:** The dirty tree contains unrelated user work overlapping the ship scope, or the branch is on a protected ref. Halt `blocked` without stashing or discarding.

---

## 8. Handoff

- **If Envelope Status is "pass":** Hand off the ship readiness report (commits, PR, CI, review threads, release) to the parent for final acceptance and authorized merge/release dispatch. A `daw-ship` `pass` is a proposal only.
- **If Envelope Status is "fail":** Hand off structured ship failure evidence (commit/PR/CI diagnostics) to the parent, naming the owning correction route (`patch`, `feature`, `bugfix`, `maintain`, `refactor`).
- **If Envelope Status is "blocked":** Return blocked status with the unmet gate (acceptance, evidence, authorization, or env) to the parent.
- No recursive invocation of the router or sibling modules; no product-code edits; no merge/tag/publish/deploy without authorization.

---

## 9. References

- Root contract: `../../SKILL.md`
- Specifications and routing: `../../references/routing.md`
- Parent Acceptance Checkpoint: `../../references/operations.md#parent-acceptance-checkpoint`
- Checkpoint Boundaries & Acceptance Records: `../../references/operations.md#checkpoint-boundaries` and `../../references/operations.md#parent-owned-acceptance-record`
- Secret redaction & audit records: `../../references/operations.md#5-semantic-verification-audit-records--secret-redaction`
- Developer lifecycle (inner loop, time-boxing, spike, refactor, maintenance, bisection, commit hygiene, PR & CI, review feedback, release, retrospective): `../../references/developer-lifecycle.md`
- Commit hygiene detail: `../../references/developer-lifecycle.md#7-commit-hygiene`
- Pull request & CI detail: `../../references/developer-lifecycle.md#8-pull-request--ci-protocol`
- Review feedback intake detail: `../../references/developer-lifecycle.md#9-review-feedback-protocol`
- Release readiness detail: `../../references/developer-lifecycle.md#10-release-readiness`
