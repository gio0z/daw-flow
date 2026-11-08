# Developer Lifecycle Reference

Shared lifecycle guidance for the DAW suite: when a lifecycle practice applies, which route/module owns it, concrete commands, and decision rules with numeric thresholds. The voice follows the suite standard: deterministic hands / generative brain, fail-closed high-risk gating, canonical handoff envelope. New guidance adds no runtime dependencies.

High-risk authorization, preflight checks, rollback, and approval-invalidation rules are defined in [operations.md](operations.md) and are not duplicated here. Read [operations.md](operations.md) §1 Preflight Safety and §2 Fail-Closed Approval Boundaries before any mutating lifecycle action. Parent-owned stage acceptance and ranked triage are defined in [operations.md](operations.md#parent-acceptance-checkpoint) and [operations.md](operations.md#parent-owned-acceptance-record).

---

## 1. Inner Development Loop

**When it applies:** During any mutating build route (`feature`, `bugfix`, `patch`, `refactor`, `maintain`, `spike`) while code is actively being edited.

**Owner route/module:** `daw-build` owns code mutation; `daw-verify` owns terminal proof. This loop is the discipline `daw-build` follows between edits and the smoke proof `daw-verify` later formalizes.

**Concrete steps/commands:**

```bash
# 1. Run the smallest relevant check after each edit
pytest tests/<touched_module>/ -q          # or the suite's configured test command
npm test -- <touched_module>               # JS/TS equivalents per AGENTS.md test_command

# 2. Smoke the running surface early (first runnable artifact only)
./bin/my-tool --help                       # CLI
curl -sS http://127.0.0.1:8080/health    # API (local authorized instance)
# UI: open the running page in the discovered browser tool and exercise the changed view

# 3. Rerun on a fixed cadence, not just at the end
git status --short && git diff --stat
```

**Decision rules with numeric thresholds:**

- After **every** edit, run the smallest relevant check (unit/targeted integration for the touched module) before the next edit. Never accumulate more than **1 untested edit** before a check.
- First smoke proof is due within **15 minutes** of the first runnable artifact existing; if no runnable artifact exists yet, run the nearest syntax/build check instead.
- If a single targeted check exceeds **60 seconds**, split it into per-module commands and run the failing subset first.
- A full-suite run is due at stage end (not mid-loop) unless a targeted check fails twice on the same symptom, which forces an immediate full-suite run to distinguish local breakage from cross-module regression.
- Stop the loop when the same check fails **3 times** without a new hypothesis; return to `daw-plan` or `daw-debug` rather than iterating blindly (see [§2 Time-Boxing & Escalation Budgets](#2-time-boxing--escalation-budgets)).

---

## 2. Time-Boxing & Escalation Budgets

**When it applies:** Any route where investigation, debugging, design, or building could otherwise consume unbounded effort.

**Owner route/module:** `daw-plan` sets the budget; `daw-debug`, `daw-design`, and `daw-build` consume it; `daw-ask` records the escalation question and answer.

**Concrete steps/commands:**

```bash
# Record the budget in the plan/durable progress record before starting:
#   Budget: started <ISO time> | timebox <N> min | max hypotheses <K> | escalate via daw-ask
# No shell timer is required; the bound is the count and the clock recorded in the plan.
```

**Decision rules with numeric thresholds:**

- **Spike time-box (see [§3 Spike Protocol](#3-spike-protocol)):** default **90 minutes**; after **2 failed hypotheses**, stop hypothesizing and escalate via `daw-ask` with both negative results attached.
- **Debug budget:** at most **3 distinct hypotheses** per failing symptom; after the **3rd** failed falsification, stop and re-plan with `daw-plan` (or escalate to the user if the blocker is external).
- **Research/design budget:** at most **60 minutes** of open-ended exploration before a decision is recorded; record the decision or the explicit unknown that blocks it.
- **No-progress rule:** if **45 minutes** pass with no new observable evidence (no new failing output, no narrowed search space), stop and escalate rather than continuing the same action.
- **Build iteration cap:** at most **5 edit-verify cycles** per acceptance criterion; on the **6th** cycle, re-open planning with the failing evidence instead of patching again.
- Any budget expiry returns to the parent with `status: "blocked"` naming the exact question, the elapsed evidence, and the next permitted action. Never silently extend a budget.
- **Workflow-level loop:** these module budgets bound a single stage. When a failing acceptance criterion keeps looping across stages, the outer edge, round definition, progress test, and escalation caps live in the canonical [Correction Loop & Route Re-Entry](operations.md#correction-loop--route-re-entry); whichever cap is reached first governs.

---

## 3. Spike Protocol

**When it applies:** Technical uncertainty blocks a `feature`, `patch`, or `refactor` decision and a throwaway experiment is the cheapest way to answer one concrete question.

**Owner route/module:** `spike` intent: `daw-workspace` -> `daw-build` -> `daw-ask`. The output is throwaway findings via `daw-ask`; production code re-enters `feature`/`refactor` and is **never merged**.

**Concrete steps/commands:**

```bash
# 1. Create a throwaway branch/worktree (never spike on the delivery branch)
git branch --show-current
git worktree list

# 2. State one spike question and a pass/fail rule before coding:
#   Question: <single binary or bounded answer>
#   Pass rule: <observable outcome that settles it>

# 3. Time-box: default 90 min; announce expiry in the progress record.

# 4. Return findings; do not merge spike code:
#   daw-ask output records: verdict, evidence, cost, recommendation for the real route.
```

**Decision rules with numeric thresholds:**

- Time-box default **90 minutes**; scale is allowed in the plan (for example **30 minutes** for a lookup-only spike, **180 minutes** maximum for a build spike) but must be recorded before starting.
- After **2 failed hypotheses**, escalate via `daw-ask` with the negative evidence; do not start a **3rd** hypothesis inside the spike.
- A spike answers **exactly 1 question**; a second question requires a new spike or moves to `daw-design`.
- Spike code is never merged: on expiry or verdict, leave the throwaway branch unmerged and route the production implementation through `feature`/`refactor` fresh.
- If the spike exceeds its time-box without a verdict, return `status: "blocked"` with elapsed time and partial evidence; the parent decides: extend once (max **+90 minutes**), convert to design/build, or drop.

---

## 4. Behavior-Preserving Refactor Protocol

**When it applies:** Structural change (rename, extract, move, decompose, pattern migration) where observable behavior must not change.

**Owner route/module:** `refactor` intent: `daw-untangle` -> `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify`. If a behavior change is needed mid-refactor, stop this protocol and route to `feature`/`patch` as separate work.

**Concrete steps/commands:**

```bash
# 1. Characterization tests BEFORE structural edits
pytest tests/<touched_packages>/ -q
git status --short

# 2. Structural edits in small steps; after each step rerun the characterization set
git diff --stat

# 3. Verify no observable drift against the baseline suite
pytest tests/<affected_surface>/ -q
# Reviewers diff-check: no test expectation, fixture, or behavior may change with the refactor.
```

**Decision rules with numeric thresholds:**

- Characterization coverage first: **100%** of currently exercised acceptance criteria for the touched surface must have a passing test (or recorded probe) **before** the first structural edit.
- If characterization reveals **0** passing tests for the surface, block the refactor and write tests first; do not proceed on static reasoning alone.
- Any observed behavior change (new failing test that passed at baseline, changed CLI output, changed API schema) is a **must-fix**: revert that step and split behavior work into a separate `feature`/`patch` task.
- Refactor diffs above **400 changed lines** require re-splitting into reviewable steps before `daw-review`.
- `daw-verify` must re-run the characterization set on the current revision; a stale baseline pass is not proof.

---

## 5. Dependency & Maintenance Upgrade Protocol

**When it applies:** Dependency, toolchain, framework, or library upgrades; deprecation removal; version migrations (including language/runtime bumps).

**Owner route/module:** `maintain` intent: `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify`. `daw-ship` owns commit/PR packaging afterwards.

**Concrete steps/commands:**

```bash
# 1. Read the upstream changelog for breaking changes before upgrading
# 2. Upgrade ONE dependency/toolchain per change set
npm update <pkg> && npm test                      # or: pip install -U <pkg> && pytest
# 3. Lockfile/digest discipline
git diff --stat package-lock.json Pipfile.lock poetry.lock
# 4. Deprecation sweep before the breaking version lands
grep -r "deprecated\|TODO.*upgrade" --include="*.py" src/
git log --oneline -5
```

**Decision rules with numeric thresholds:**

- One upgrade per commit; never bundle a version bump with a behavior change (split into `maintain` + `feature`/`patch` if both are needed).
- If the upstream reports **2 or more breaking changes** affecting the repo, upgrade incrementally (one minor at a time) rather than jumping major versions.
- Deprecation removal: remove usages within the same change set; unresolved deprecated call sites must be **0** before the breaking version is installed.
- Pin or lock only if the repo already does; never introduce lockfile churn beyond the single package change (lockfile diff limited to that package and its transitive subtree).
- Rollback for a bad upgrade is a revert of the upgrade commit, verified by `daw-verify` rerunning the suite on the reverted revision. Never "fix forward" a breaking upgrade with unrelated code.

---

## 6. Regression Bisection Protocol

**When it applies:** A regression is reproducible and the introducing change is unknown among many candidate commits (for example nightly failures, a "worked last week" report, post-release breakage).

**Owner route/module:** `daw-debug` owns diagnosis; `daw-build` owns the fix afterwards. Bisection evidence feeds the debug handoff.

**Concrete steps/commands:**

```bash
# 1. Identify a known GOOD (passing) and BAD (failing) revision
git log --oneline -20
# 2. Start bisection (BAD and GOOD are commit SHAs, not floating tags)
git bisect start <BAD_SHA> <GOOD_SHA>
# 3. Mark each revision (run the deterministic repro each time)
git bisect good   # observed pass
git bisect bad    # observed fail
# 4. Automate when the repro is scriptable
git bisect run <deterministic-repro-command>
#    The run command must exit 0 for pass, 1 for fail, and 125 for SKIP
#    (for example a commit that cannot build at all):
git bisect run bash scripts/repro.sh
# 5. ALWAYS reset bisection state before continuing work
git bisect reset
git status --short
```

**Decision rules with numeric thresholds:**

- Bisect only with a **deterministic, scriptable repro** (same command, same exit code semantics). A flaky repro (fails intermittently more than **1 time in 5 runs** on the same revision) must be quarantined first per [§8 Pull Request & CI Protocol](#8-pull-request--ci-protocol) before bisection.
- GOOD must be verified passing on its revision and BAD verified failing on its revision before starting; never bisect on assumed states.
- Exit code **125** from `git bisect run` means SKIP (for example unbuildable intermediate commits); count SKIP revisions separately and report them in the handoff.
- Always terminate with `git bisect reset`, even on failure; a repository left in bisection state blocks all follow-up work.
- If bisection converges on a merge or a commit outside the suspect range, record the root-cause candidate and route the fix to `daw-build`/`bugfix` instead of continuing to bisect.

---

## 7. Commit Hygiene

**When it applies:** Packaging verified work for review, release, or handoff. Owned by `daw-ship` commit shaping, but the discipline also governs any local commit a build route makes with authorization.

**Owner route/module:** `daw-ship` for commit shaping on the `ship` intent; build routes make local commits only within their authorized scope.

**Concrete steps/commands:**

```bash
git status --short
git diff --stat
git diff --cached --stat
# Atomic, conventional subject + why-body (one commit, one logical change)
git add <explicit_paths_only>
git commit -m "feat(auth): add session token_version passthrough" \
  -m "Why: serializer dropped token_version on round-trip; clients could replay stale sessions."
git log -3 --oneline
git show --stat HEAD
```

**Decision rules with numeric thresholds:**

- **Atomic:** one commit = one logical change. Never mix a behavior change with a refactor in one commit; split into 2 commits (`feat/fix` + `refactor`) even when small.
- **Conventional subject:** `type(scope): subject`, where `type` is one of `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `build`, `ci`, `perf`, `style`; subject is imperative, **<= 72 characters**, no trailing period.
- **Why-body:** every commit body states **why** (the reason, trade-off, or link), not just **what**; regenerating the diff from the message must still explain the intent.
- **Size:** commits above **400 changed lines** should be split before opening a PR; if splitting is impossible, the PR description must justify why the change is inseparable.
- **Secrets:** never commit secrets, tokens, private keys, or `.env` files. Before committing, run a secret scan appropriate to the repo and inspect the staged diff; any detected secret is **0 tolerated** and blocks the commit until removed and history-checked.
- Local commits on a feature branch within authorized scope need no extra prompt; see [operations.md](operations.md) §2 for the exact protected-branch gate. Never commit with unexamined staged content: `git diff --cached` is mandatory before every commit.

---

## 8. Pull Request & CI Protocol

**When it applies:** Every change set that leaves the local branch for human review, integration, or release.

**Owner route/module:** `daw-ship` authors drafts and triages CI; `daw-build`/`patch`/`feature`/`bugfix` route corrections back via the parent.

**Concrete steps/commands:**

```bash
# 1. Draft first; never open a ready PR without green CI on the current revision
git log --oneline base..HEAD
git diff --stat base...HEAD

# 2. PR description (required template, fill every field):
#   ## What: <one-paragraph outcome>
#   ## Why: <problem / motivation / linked issue>
#   ## How tested: <exact commands + observed results>
#   ## Risk: <blast radius, high-risk paths touched>
#   ## Rollback: <exact revert or redeploy step>
# 3. Open via the harness PR tool (only with authorization) or leave a local draft file.
```

**Decision rules with numeric thresholds:**

- **Small PRs:** guidance target is **< 400 changed lines** (excluding generated/lockfiles). PRs above **400** must be split or must justify inseparability in the description; above **1,000** lines, split is mandatory unless the reviewer explicitly accepts the batch.
- **Draft first:** every PR opens as draft until CI is green on the current revision and the description template is complete; marking ready is a deliberate step, never automatic.
- **CI triage taxonomy (classify every failure, never bulk-retry):**
  - **Real failure:** deterministic, reproducible on the current revision (`git bisect` if the bisection protocol in [§6](#6-regression-bisection-protocol) applies). Fix on a new commit; rerun affected checks.
  - **Flaky:** passes on re-run without code change, with intermittent evidence (same command, same revision, different outcome). See quarantine rule below.
  - **Infra:** environment/toolchain/cloud failure (network, runner, credential, service outage) with no code signal. Escalate as infrastructure; never edit product code to satisfy infra noise.
- **Quarantine rule (never silent retry-until-green):** flaky jobs are quarantined once they flake **3 times in 10 runs** (track / flag / disable with a linked issue and owner). Silent re-running until green is forbidden: every rerun must be recorded in `details.ci` with the classification.
- Any CI failure whose classification is `real failure` blocks merge readiness; `flaky` blocks until quarantined or proven stable (**10/10 pass** on the current revision over the next 10 runs); `infra` blocks until the infra cause is resolved or a waiver is recorded by the parent.

---

## 9. Review Feedback Protocol

**When it applies:** A PR exists and human (or reviewer-agent) comments arrive, whether on a `ship` round or on feature/bugfix PRs.

**Owner route/module:** `daw-ship` runs the intake loop and records dispositions; corrections route back via the parent to `patch`/`feature`/`bugfix`/`maintain`/`refactor`. `daw-ship` never edits product code itself.

**Concrete steps/commands:**

```bash
# 1. Classify EVERY comment before touching code (see dispositions below).
# 2. Record disposition per thread in details.review_threads.
# 3. Apply must-fix via the parent-dispatched correction route, then rerun affected checks:
pytest tests/<affected_surface>/ -q
# 4. Reply per thread explaining what changed (or why not).
```

**Decision rules with numeric thresholds:**

- Every comment gets exactly one disposition:
  - **must-fix:** correct and required; route to the correction module the same day; rerun the affected checks before re-requesting review.
  - **should:** accepted with scope; schedule in the current PR if the diff stays **< 400 lines**, otherwise file a follow-up and complete the thread with the link.
  - **nit:** cosmetic; fix only if it does not expand the diff beyond **5 lines** total, otherwise defer.
  - **question:** answer with evidence or a check; never guess.
  - **disagree:** reply with a rationale and evidence, keep the thread open for reviewer concurrence; never resolve a `disagree` thread unilaterally.
- **Never resolve reviewer threads on their behalf.** `daw-ship` replies and proposes; only the reviewer marks resolved after the fix lands and checks pass.
- Review cycles: after **3 rounds** without convergence on the same thread, escalate to the parent for a scope decision (split, defer, or accept the reviewer's direction) instead of iterating further.
- Any fixup commit invalidates prior CI evidence: rerun the affected checks and refresh `daw-verify` evidence on the new revision before re-requesting review.

---

## 10. Release Readiness

**When it applies:** A merged change set is being prepared for a versioned release, package publish, container image, or deployment artifact.

**Owner route/module:** `daw-ship` prepares release readiness (version bump proposal, changelog); tag, publish, and deploy remain point-of-risk actions authorized only per [operations.md](operations.md) §2.

**Concrete steps/commands:**

```bash
# 1. Semver decision (record in the plan before mutating version files)
#    major: breaking API/contract change | minor: backward-compatible feature | patch: backward-compatible fix
# 2. Bump exactly ONE place (single source of truth for the version)
grep -rn "VERSION\|version" pyproject.toml package.json VERSION 2>/dev/null
# 3. Changelog from commits (no hand-written fiction)
git log <last_tag>..HEAD --oneline
# 4. Verify on the release candidate revision
pytest -q
```

**Decision rules with numeric thresholds:**

- **Semver:** any breaking change (removed endpoint, changed payload schema, dropped support) forces at least **major**; any backward-compatible feature forces at least **minor**; fixes, docs, and refactors are **patch**. When in doubt between two levels, choose the higher one.
- Changelog entries come from the commit log (`git log <last_tag>..HEAD`); every entry must map to a merged commit SHA, and every merged commit must appear exactly once.
- Tag and publish are point-of-risk: `git tag`, package registry publish, and deploy each require exact interactive authorization naming the version, artifact digest, and target environment; a prior release approval never covers a new version.
- Release candidate evidence: `daw-verify` on the exact release revision is mandatory; a pass on an earlier revision does not cover the tagged revision.
- Post-merge cleanup handoff (feature branch deletion, worktree removal) happens only after merge and is itself authorized per [operations.md](operations.md) §2; never auto-delete branches or worktrees.

---

## 11. Retrospective & Convention Feedback

**When it applies:** After a route completes (or fails) and a repeatable lesson exists: a defect pattern, a missing convention, another occurrence of the same friction.

**Owner route/module:** Parent owns the retrospective; `daw-ask` records the lesson; `daw-setup` writes AGENTS.md DAW config rules when a convention changes; `daw-build` + `daw-verify` add regression tests when a defect pattern is found.

**Concrete steps/commands:**

```bash
# Record the lesson in the retrospective note (blameless, evidence-first):
#   What happened | Evidence (revision, command, output) | Lesson | Converted to
# Converted artifacts:
#   - AGENTS.md / CLAUDE.md <!-- daw-config:start --> block  (convention rule via daw-setup)
#   - tests/regression/test_<pattern>.py                     (regression test via daw-build)
#   - references/developer-lifecycle.md                       (checklist/threshold update)
```

**Decision rules with numeric thresholds:**

- **Blameless:** retrospectives describe system conditions and evidence, never individuals; a retrospective that names a person is rejected and rewritten.
- **Convert or drop:** every recorded lesson must either (a) convert to an AGENTS.md DAW config rule (via `daw-setup`), (b) convert to a regression test (via `daw-build` -> `daw-verify`), or (c) be explicitly dropped with a reason. Lessons with no conversion path are not recorded as conventions.
- **Recurrence threshold:** a friction or defect observed **twice** must be converted (config rule or regression test); a single observation may stay as a noted lesson only.
- Convention rules land in the `<!-- daw-config:start -->` block so every module consumes them; a convention that never reaches AGENTS.md, a test, or this reference is not a convention.
- Retrospective input is due within **1 week** of route completion; stale retrospectives must be re-derived from evidence, not memory.
