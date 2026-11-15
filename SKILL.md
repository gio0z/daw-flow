---
name: deterministic-agentic-workflow
description: "Use to route multi-step engineering tasks, bootstrap greenfield specifications, adopt documentation for existing codebases, or govern execution across the bundled DAW suite: provides router dispatch across 12 specialized execution modules (daw-design, daw-plan, daw-debug, daw-build, daw-review, daw-verify, daw-workspace, daw-ask, daw-setup, daw-wizard, daw-untangle, daw-ship), document-driven planning across the 14-doc specification matrix, capability routing, preflight checks, fail-closed risk gating, and verifiable evidence gates."
compatibility: "Python 3.10+ stdlib validator & route engine; core workflow instructions remain fully usable without Python."
license: MIT
metadata:
  version: "0.6.0"
---

# Deterministic Agentic Workflow

Core architectural axiom: **"Otaknya boleh generative, tangannya harus deterministic."**
Reserve generative reasoning for reading context, analyzing intent, designing specs, planning, and synthesis. Execute all state mutation, system modification, deployment, migration, and verification through deterministic scripts, bounded tools, and verifiable proof gates.

> **Instructional Contract & Scope:** Root router and governance entrypoint for the bundled 12-module DAW suite (`skills/daw-*/` and sibling symlinks). Does not install runtime hooks, daemon supervisors, interceptors, or external suites. Scripts never guarantee semantic truth — inspect observable runtime evidence against Acceptance Criteria. Docs alone never constitute running services or deploy authorization.
>
> **Native Interactive Clarification:** Every material operator decision uses [native interactive clarification transport](references/grilling.md#native-interactive-clarification-transport-canonical-rule): discover the exposed harness tool/schema first and call it; never invent a tool name/schema. Posing a material decision as chat text when a native question tool is exposed is a transport violation. Use bounded plain-text fallback (≤5 questions/round, frontier-ordered, recommendation-first, no synthesized "Other") only when no native tool is exposed; the explicit headless bench/oracle adapter is the sole file-transport exception. Cancellation/unanswered stay unresolved, never consent. Clarification never bypasses provider/security/point-of-risk controls, adds no gate to low-risk work, and never negates explicit authorization for its exact target/scope/action (§4).

Install via [the offline installer](references/installation.md) (Codex, Claude Code, Gemini CLI, Cursor, Copilot). Keep root and modules together; where directory symlinks are unsupported, load child modules by canonical paths from this root. Host tools, approvals, and client discovery stay environment-specific.

---

## 1. Suite Architecture & Bundled Module Delegation

DAW is a **complete 12-module bundle** requiring no external workflow frameworks (e.g. Superpowers) or third-party registries. All 12 internal modules are mandatory core dependencies.

Delivery flow is adopted, not invented: [Best Practice Flow](references/best-practice-flow.md) maps nine adopted steps (spec-kit, superpowers, Matt Pocock) to DAW rules, read by `validate.py flow` and the route flow gate.

| Module            | Canonical Path                                                 | Primary Responsibility                                                                                                                                            |
| :---------------- | :------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **daw-design**    | [skills/daw-design/SKILL.md](skills/daw-design/SKILL.md)       | Architecture, technical requirements, specification authoring, 14-doc matrix.                                                                                     |
| **daw-plan**      | [skills/daw-plan/SKILL.md](skills/daw-plan/SKILL.md)           | Structured task planning, phase breakdowns, risk assessment, task contracts.                                                                                      |
| **daw-debug**     | [skills/daw-debug/SKILL.md](skills/daw-debug/SKILL.md)         | Root cause analysis, minimal reproduction, failure diagnostics, regression isolation.                                                                             |
| **daw-build**     | [skills/daw-build/SKILL.md](skills/daw-build/SKILL.md)         | Implementation, code editing, minimal change construction, zero dead weight.                                                                                      |
| **daw-review**    | [skills/daw-review/SKILL.md](skills/daw-review/SKILL.md)       | Two-stage code review, architectural boundary compliance, security auditing.                                                                                      |
| **daw-verify**    | [skills/daw-verify/SKILL.md](skills/daw-verify/SKILL.md)       | Behavioral verification, test execution, regression proof, evidence checks.                                                                                       |
| **daw-workspace** | [skills/daw-workspace/SKILL.md](skills/daw-workspace/SKILL.md) | Isolated workspace/worktree setup, git worktree lifecycle, boundary containment.                                                                                  |
| **daw-ask**       | [skills/daw-ask/SKILL.md](skills/daw-ask/SKILL.md)             | Read-only architecture consultation, contextual guidance, decision frontier exploration.                                                                          |
| **daw-setup**     | [skills/daw-setup/SKILL.md](skills/daw-setup/SKILL.md)         | Interactive configuration setup, tool command discovery, and repo convention authoring.                                                                           |
| **daw-wizard**    | [skills/daw-wizard/SKILL.md](skills/daw-wizard/SKILL.md)       | Interactive greenfield requirements interview & initial specification document authoring.                                                                         |
| **daw-untangle**  | [skills/daw-untangle/SKILL.md](skills/daw-untangle/SKILL.md)   | Read-only structural analysis, change-coupling investigation, modular boundaries, zero mutation ([references/change-coupling.md](references/change-coupling.md)). |
| **daw-ship**      | [skills/daw-ship/SKILL.md](skills/daw-ship/SKILL.md)           | Integration & delivery: commit hygiene, pull requests, CI triage, review feedback, merge & release readiness.                                                     |

### Module Delegation Rules

1. **Delegation, Not Recursion:** Root router dispatches by classified intent and operational facts; modules execute their phase and return recommended next stages. Modules **NEVER** call the root router or invoke each other recursively.
2. **Missing Module Policy:** Missing any required internal module yields `blocked` (never shallow inline approximation). External domain skills are optional augmentations.
3. **Proportionality & Work Size (deterministic):**
   - **Tiny** iff ALL hold: 1 file (plus at most its own test), no new user-visible behavior, and no change to schema, migration, public API/interface, UI screen, config contract, or dependency. May go straight to build with no spec or plan doc.
   - **Multi-step** (everything else, or uncertain size): follows full route with a saved plan before any source edit. Auto-planned even under urgency wording ("cepat", "just do it"). Only an explicit user opt-out skips the plan (`Size: multi-step · plan skipped at user request`). Full 14-doc matrix stays reserved for `bootstrap`, `adopt`, or explicit requests.
4. **Workflow Artifacts (canonical):** Multi-step authorized work follows [Workflow Artifacts](references/workflow-artifacts.md):
   - Persist a proportional authoritative spec before tactical decomposition (reuse adequate specs; if clear user requirements have no file, parent records faithful bounded what/why/non-goals/AC before `daw-plan`; ambiguity returns to design/clarification with no `daw-design` insertion on clear routes).
   - Save the plan before build dispatch mapping stable requirement/AC IDs -> task IDs, exact target files, dependencies, parallel ownership, expected observations/checks, evidence, and separate parent acceptance with bound spec revisions.
   - Open a parent-owned durable progress record at intake naming the actual active module/stage and subphase (not just planned route), active task(s), completed accepted stages, scoped revisions, blockers/owner/question, next permitted action, primary evidence/handoff refs, and parent acceptance distinct from worker pass.
   - Produce a rendered visual mockup before UI build when UI-affecting.
   - Tiny, read-only, and bare-no-brief runs retain the zero-doc path; progress metadata is ignored when deciding blank `bootstrap` vs `adopt`.
5. **Canonical Relative Linking:** Modules link suite docs/templates relative to module location (`../../references/...`, `../../templates/...`).
6. **Harness-Native Worker Graphs:** At intake, discover harness capabilities and automatically retain same-role builders and independent reviewers when delegation, corrective rounds, and completed-worker continuation are warranted and supported (unless user opts out; no persistence keyword or prior setup needed). Keep tiny direct tasks direct; never add stages/workers just for retention. Follow [persistent worker graph contract](references/operations.md#persistent-worker-graphs-harness-native) (revision-scoped joins, evidence, stop/replan, explicit fresh-worker fallback; session-bounded, not durable crash recovery).
7. **Efficient Context Loading & Progressive Disclosure:**
   - **Load CURRENT stage only:** Load only the active `skills/daw-<stage>/SKILL.md` and needed templates; never load all 12 modules or all 14 templates at once.
   - **Progressive disclosure:** Read targeted sections/headings of `references/*` on demand, never entire reference files upfront.
   - **Honest direct fallback:** Execute directly when subagent/tool delegation is unavailable; never simulate tools or claim unexercised evidence.
   - **Cold factual advisory minimum:** Direct factual `daw-ask` with no material decision, parent handoff, or transition loads only the active module and root §4/§6 safety rules, deferring routing §5 and full grilling; permits no mutation, approval, or intake bypass.

---

## 2. Invocations & Observable Action Protocol

### Invocation Modes

1. **Explicit Bare Invocation** (e.g. `"Use deterministic-agentic-workflow"`):
   - Inspect target directory (`cwd`) only; do not scan parent directories unless directed.
   - If `cwd` has `## DAW Configuration` or any DAW artifact (spec dir, `ledger.json`, or `docs/daw/evidence/<task-id>/contract.json`): run `python3 "$SUITE_ROOT/scripts/validate.py" status --project-root <root>` first; report `summary`, advisory `recommended_route`, and `next_actions` (primary first), and propose that route before entering **Adopt**. `recommended_route` is advisory only — never enlarges scope, grants mutation authority, or dispatches an unauthorized route; continue the user's original route (except on an explicit status-only stop).
   - Else if existing code/partial docs exist -> **Adopt** (suggest Setup first if no `## DAW Configuration` block).
   - Else if empty with brief -> **Bootstrap** (starts with requirements interview).
   - Else if empty with **no brief** -> start interview phase 1 (project concept, scope, target users); halt `blocked` on unanswered material questions; never invent phantom product docs.
2. **Task-Specific Invocation** (e.g. `"fix the NPE in auth"` or `"review PR #12"`):
   - Not a bare invocation; extract explicit intent and dispatch directly.
   - **Intake line (required before first file write):** State one line in user's language: e.g. `Route: feature · Size: multi-step (new module + tests) → spec check, then saved plan before code`, or for tiny: `Size: tiny — one file, no new behavior`. Editing source before this line (or before saving the plan for multi-step) is a workflow violation -> stop and plan.
   - **Status preflight:** When DAW artifacts exist, run `python3 "$SUITE_ROOT/scripts/validate.py" status --project-root <root>` before dispatch. For mutating routes (`feature`, `bugfix`, `refactor`, `maintain`), also run `python3 "$SUITE_ROOT/scripts/route.py" REQUEST.json --project-root <root>` and report any `FLOW_GATE_*` blocker (`ready` without `--project-root` proves nothing about flow prerequisites).
   - **Advisory vs blocking:** `recommended_route` never enlarges scope or authorizes unrequested routes. An explicit status-only request is read-only & terminal: report `summary`, `recommended_route`, `next_actions` (primary first), and findings, then stop (no dispatch, no mutation, no extra consent gate). For ordinary tasks, status error findings block spec-dependent mutating routes (`feature`, `bugfix`, `refactor`, `maintain`) until resolved, never authorize dispatching `recommended_route` (`setup`, `upgrade-recheck`, `design-rework`, `verify`, `none`), and never block read-only routes (`ask`, `review`, `untangle`) or configuration setup. Ref: [`references/validation.md` §10](references/validation.md#10-status-aggregate-preflight-scriptsvalidatepy-status).

### Observable Action Protocol

Before authorized filesystem writes, output an observable planning table (never plan-only when an authorized mutation remains):

| Target File / Path        | Action (`create` \| `update` \| `reuse` \| `skip` \| `block`) | Rationale / Provenance                                  |
| :------------------------ | :------------------------------------------------------------ | :------------------------------------------------------ |
| `docs/specs/blueprint.md` | `create`                                                      | Initial system architecture based on operator brief.    |
| `src/auth.py`             | `update`                                                      | Surgical fix for null pointer exception.                |
| `docs/specs/wireframe.md` | `skip`                                                        | Backend-only change; UI contracts non-applicable (N/A). |

Report final results using exact statuses: `created`, `updated`, `reused`, `skipped`, or `blocked`.

---

## 3. Finite Intent Precedence & Routing

Route tasks by explicit finite intent precedence on operational facts, not open-ended keyword matching:

1. **Review (`review`):** Static analysis, code/diff review, or security boundary audit (`daw-review`). Strictly read-only; ignores unknown risk/workspace. Audit-and-fix requests are parent-composed: read-only review diagnosis first, then (only if warranted) an authorized correction route (`bugfix` for undiagnosed defect, `patch` for pre-diagnosed tiny clear scope, `feature` for new capability) with no new route/stage/schema; do not stop after review while authorized fixes remain.
2. **Untangle (`untangle`):** Explicit read-only structural/coupling analysis governed by [references/change-coupling.md](references/change-coupling.md) (`daw-untangle`). Strictly read-only; ignores unknown risk/workspace; no `daw-workspace`, approval execution, or mutation. Behavior-preserving restructuring routes to `refactor` (intent 10), not `untangle`; in code delivery, escalate from the prefinal coupling checkpoint only on demonstrated boundary obscurity.
3. **Ask (`ask`):** Read-only architectural consultation, Q&A, or trade-off analysis (`daw-ask`). Read-only intent wins; ignores unknown risk/workspace.
4. **Setup (`setup`):** Discover project commands/conventions, confirm with user, and write/update `<!-- daw-config:start -->` in `AGENTS.md`/`CLAUDE.md` (`daw-setup`). Suggest on first DAW use without a config block; with an existing config block, run `validate.py status` before spec-dependent work (`config_daw_version_stale` -> advisory `upgrade-recheck` only when user-authorized).
5. **Bootstrap (`bootstrap`):** Greenfield specs from a brief in an empty/new directory (`daw-wizard` -> `daw-design` -> `daw-plan`, docs-only).
6. **Adopt (`adopt`):** Reverse-engineer and author specs for existing undocumented code (`daw-design` -> `daw-plan`, docs-only, preserves code).
7. **Bugfix (`bugfix`):** Diagnose, reproduce, and fix defect/test failure (`daw-debug` -> `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify`; prepends `daw-workspace` if isolated).
8. **Patch (`patch`):** Minimal, pre-diagnosed **tiny** fix (§1 rule 3) with `requirements: "clear"` (`daw-build` -> `daw-verify`; prepends `daw-workspace` if isolated; unclear/unknown requirements -> `needs-input`). Multi-step pre-diagnosed changes route to `feature` or `bugfix`.
9. **Feature (`feature`):** Multi-step functional change or capability. Clear requirements: `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify`; unclear: `daw-design` -> `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify` (prepends `daw-workspace` if isolated). UI/visual design requests ("buat mockup", "redesign halaman", UI/UX polish) are UI-scoped `feature` work: `daw-design` settles flows and produces a rendered mockup per [Workflow Artifacts §5](references/workflow-artifacts.md#5-mockup-timing-proof--na) before UI `daw-plan` tasks; mockup-only requests stop after mockup review without build.
10. **Refactor (`refactor`):** Behavior-preserving structural restructuring (`daw-untangle` -> `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify`; prepends `daw-workspace` if isolated). Characterization tests precede edits; unknown requirements -> `needs-input`; see [refactor protocol](references/developer-lifecycle.md#4-behavior-preserving-refactor-protocol).
11. **Maintain (`maintain`):** Dependency/toolchain/platform upgrade, deprecation removal, migration (`daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify`; prepends `daw-workspace` if isolated).
12. **Spike (`spike`):** Time-boxed throwaway prototype resolving technical uncertainty (`daw-workspace` -> `daw-build` -> `daw-ask`, always isolated; unknown requirements allowed; output is throwaway only — production code re-enters `feature`/`refactor`, never merged). See [spike protocol](references/developer-lifecycle.md#3-spike-protocol).
13. **Ship (`ship`):** Integration & delivery of verified work: commit hygiene, PR, CI triage, review feedback, merge/release readiness (`daw-ship`). Unknown risk -> `needs-input`; high risk -> `interactive_approval_required`. Push to protected branches, merge, tag, publish, and deploy remain point-of-risk actions (§4). See [ship protocols](references/developer-lifecycle.md#8-pull-request--ci-protocol).

### Professional Delivery Lifecycle

Read-only intents (`review`, `untangle`, `ask`) hold top precedence. Choose mutating intents by observable character: `ship` (delivery of already-verified changes), `spike` (throwaway evidence for uncertainty), `refactor` (identical observable behavior), `maintain` (dependency/toolchain/deprecation), else `bugfix`/`patch`/`feature`. Split mixed behavior + restructuring requests into `refactor` first, then `feature`.

Flow: setup -> clarify/spike -> design -> plan -> build + inner loop -> review -> verify -> ship -> release -> retro feeding `AGENTS.md` (and optional consent-gated `daw feedback`). Reference: [Developer Lifecycle](references/developer-lifecycle.md) (inner loop §1, time-boxing §2, spike §3, refactor §4, maintenance §5, bisection §6, commit hygiene §7, PR/CI §8, review feedback §9, release §10, retro §11).

### Routing Execution API & Manifest Policy

Routing policy lives in `references/suite-manifest.json` (`schema_version` 1), evaluated via the read-only stdlib script:

```bash
python3 "$SUITE_ROOT/scripts/route.py" REQUEST.json [--format text|json] [--root SUITE_ROOT] \
  [--project-root PROJECT_ROOT]
```

Invoke via resolved `$SUITE_ROOT/scripts/route.py` (never assume `scripts/` exists in `cwd`). Always pass `--project-root` when routing a project so the [flow gate](references/best-practice-flow.md) downgrades `ready` to `blocked` (`FLOW_GATE_MISSING_ARTIFACT`, `FLOW_GATE_UNREADABLE`) when `flow_gate.affected_intents` lack required spec/plan artifacts.

Required request facts (`schema_version`, `intent`, `requirements`, `risk`, `workspace`):

- Returns `status: "needs-input"` with blockers when: `requirements` is unknown for `bootstrap`/`feature`/`refactor`/`maintain`, unknown/unclear for `patch`, `workspace` is unknown for mutating intents (`feature`/`bugfix`/`patch`/`refactor`/`maintain`), or `risk` is unknown for mutating intents (`feature`/`bugfix`/`patch`/`refactor`/`maintain`/`ship`). `spike` allows unknown requirements; `ship` flags unknown risk as `needs-input` and high risk as `interactive_approval_required`.
- In Python-less/shell-less environments, evaluate `references/suite-manifest.json` manually and disclose that the script was unexercised.

### Deterministic Execution Runner

Contract: [Deterministic Execution Runner](references/execution-runner.md); implementation: `scripts/run.py`.

```bash
# Validate a saved plan's task manifest (read-only).
python3 "$SUITE_ROOT/scripts/validate.py" tasks docs/daw/plans/<workflow-id>.md --project-root "$PROJECT_DIR"

# Compute the ready set, assemble one task's bounded context pack, run its verification command.
python3 "$SUITE_ROOT/scripts/run.py" next    --plan docs/daw/plans/<workflow-id>.md --project-root "$PROJECT_DIR"
python3 "$SUITE_ROOT/scripts/run.py" context --plan docs/daw/plans/<workflow-id>.md --project-root "$PROJECT_DIR" --task TASK-01
python3 "$SUITE_ROOT/scripts/run.py" verify  --plan docs/daw/plans/<workflow-id>.md --project-root "$PROJECT_DIR" --task TASK-01

# Run one task inside its own git worktree and integrate it only when it verifies green.
python3 "$SUITE_ROOT/scripts/run.py" isolate --plan docs/daw/plans/<workflow-id>.md \
  --project-root "$PROJECT_DIR" --task TASK-01 --agent-command '["claude","-p","{prompt_file}"]'
```

Runner rules:

- Explicitly invoked per unit of work — never a daemon, scheduler, or background service; never installs/discovers an agent command.
- Never pushes, tags, publishes, or deploys; never writes to a protected branch; never grants point-of-risk authorization (passing verification is evidence, not approval).
- Only `afk` tasks enter the ready set; `hitl` tasks always wait for a live human decision.
- Task list lives in the saved plan (`<!-- daw-task-manifest -->` JSON block) so prose and executable list stay synchronized.
- Verification commands run as argv without a shell; output captures to `docs/daw/evidence/<task-id>/`.
- Under per-task isolation, writes outside the task's worktree are detected and never integrated.

### Usage Feedback (`daw feedback`)

Opt-in, read-only, offline by default. It harvests structural finding codes from `docs/daw/evidence/`, prints a sanitized preview, and returns a 1-click GitHub Issue URL for `gio0z/daw-flow`.

```bash
# Local sanitized preview only; no network request, no subprocess.
python3 "$SUITE_ROOT/scripts/daw.py" feedback --project-root "$PROJECT_DIR" \
  --route <route> --module <module> --category friction --summary "<short sanitized summary>"
```

- Evidence scanning retains structural finding codes and environment metadata only.
- Operator free text (`--summary`, `--note`, `--client`) is redacted for absolute paths, git SHAs, task IDs, credential assignments, and opaque token runs; pasted source code cannot be detected mechanically, so the operator remains responsible for the summary's contents.
- `--submit` is the only path that reaches `gh issue create` and it requires explicit operator consent. Without `--submit` the tool never sends a network request and never spawns a subprocess.
- The `skill-feedback` issue form and label must exist in the target repository; a missing label fails closed with `feedback_label_missing`.
- Never invoke `--submit` without explicit user consent, and never paste source code or secrets into the summary.

---

## 4. Preflight Checks, Coexistence & High-Risk Gating

1. **Preservation of User Work (No Clean Tree Requirement):** Dirty trees are normal; preflight never requires a clean tree and never runs destructive `git reset --hard`, `git checkout .`, or `git clean -fd`. `daw-workspace` creates a separate `git worktree` only when authorized by intent or workspace preference.
2. **Context-Relevant Preflight Checks:** Cloud credentials, prod tags, and backup checks apply ONLY to high-risk infra/deploy operations — never to local docs or routine fixes. Read-only intake/inspection must not be blocked by preflight checks.
3. **Fail-Closed High-Risk Gating:**
   - High-risk operations (prod deploy, destructive migrations, security changes, remote state mutation) fail closed without exact interactive operator confirmation at the point of risk.
   - Structural refs, PR links, issue numbers, generic approval tokens, vague verbal assent, or passive context never authorize high-risk mutations.
   - Unknown risk, target environment, or mutation scope halts as `blocked` before mutation.
   - `route.py` sets `interactive_approval_required: true` and `authorization_granted: false` (always false); `status: "ready"` means the plan is ready, NOT that mutation is authorized.
4. **Suite Governance Loader Contract for Direct Invocations:** Direct module invocation must never bypass suite governance. Resolve canonical module directory and run:
   1. Reuse session-loaded root governance (§4/§6) and routing §5 handoff rules, else load them (cold factual `daw-ask` may defer routing §5 per §1 rule 7; root safety remains required).
   2. Before mutation, consult relevant `references/operations.md` preflight/approval headings if not already in context.
   3. Halt `blocked` on unknown risk/target or missing interactive approval before mutation; read-only intake remains permitted.
   - Apply [Operational Rule Diagnostics](references/operations.md#operational-rule-diagnostics) (trigger, observable tell, scoped fix, sufficient proof mapped to existing verdicts; no new stage/schema/artifact).
   - For multi-step authorized work, direct invocations also load [Workflow Artifacts](references/workflow-artifacts.md) before tactical planning or build dispatch (spec -> saved plan -> intake progress record -> rendered mockup if UI-affecting, keeping clear-feature route free of `daw-design` insertion and preserving §4 fail-closed gates).
5. **Feature Delivery Contract & Execution Governance:**
   - **Artifact & Revision Selection:** Use existing repo artifacts, current revisions, and stable IDs (`REQ-xxx`, `US-xxx`, `AC-xxx`); do not force `spec.md`/`tasks.md` over existing `prd.md`/`roadmap.md`.
   - **Workflow artifacts persistence:** Follow [Workflow Artifacts](references/workflow-artifacts.md) (§1–§5) — single-doc lean sections/default paths, no duplicate tracker authority (artifact ref in `details`), rendered visual mockup before UI build with scoped N/A for non-UI/nonvisual fixes.
   - **Three-Tier Verification Boundary:** (a) _Plan Self-Check_ (`daw-plan` checks AC coverage + acyclic DAG); (b) _Independent Prebuild Readiness Checkpoint_ (for spec-dependent builds, parent dispatches read-only `daw-review` on current spec + plan revisions before `daw-build`, no new stage/recursion); (c) _Route-Required Postbuild Review_ (`feature`/`bugfix` mandate `daw-review` after build; prebuild checkpoint never waives it; never insert `daw-review` into `patch`).
   - **Parent Prefinal Coupling Checkpoint:** Before final completion of code changes, apply [canonical proportional checkpoint](references/change-coupling.md#prefinal-coupling-checkpoint) (affected interfaces/deps, essential vs accidental co-change, current evidence or unresolved boundary; reuse matching review; inline N/A for clear nonstructural patches/docs; escalate to bounded read-only `daw-untangle` only on demonstrated boundary obscurity; material defects block, unrelated debt stays advisory). Preserve [parent-owned acceptance, scoped corrections, and evidence invalidation](references/operations.md#parent-prefinal-coupling-checkpoint).
   - **Scoped Pause/Resume with Canonical Statuses:** Internal labels (`blocked`, `in_progress`, `ready`, `completed`, `failed`) are neither canonical outer statuses (`pass`/`fail`/`blocked`, §6) nor parent acceptance (`accepted`/`not accepted`). When blocked, halt `blocked` and record reason, owner, question, next action, revisions, and evidence; resume revalidates prerequisites, scope, and approvals.
   - **Proportional Change Invalidation:** Code edits invalidate affected runtime evidence and postbuild reviews (not accepted specs). Formal spec edits require re-entry via the 5-edge gate (`review-rework` -> `rework-review` -> `review-ready`). Bound approvals invalidate only when action, target, revision, or scope changes.
   - **Scope Guard & Overrides:** Local templates/overrides/discovered commands never weaken safety gates or AC; no feature edits during governance-only edits.
   - **Authorized Command Execution:** Execute and inspect verification commands empirically; echoing commands, checkboxes, or file existence is not proof. See [Feature Delivery Contract](references/document-quality.md#feature-delivery-contract).

---

## 5. Specification Planning Matrix (The Canonical 14 Documents)

When specs are required (`bootstrap`, `adopt`, unclear `feature`), `daw-design` uses `templates/`:

1. [blueprint.md](templates/blueprint.md) — System Architecture & Foundational Design
2. [brd.md](templates/brd.md) — Business Requirements Document
3. [prd.md](templates/prd.md) — Product Requirements Document
4. [frd.md](templates/frd.md) — Functional Requirements Document
5. [techstack.md](templates/techstack.md) — Technology Stack & Infrastructure Specification
6. [design.md](templates/design.md) — Visual Design System & Component Library Specification
7. [wireframe.md](templates/wireframe.md) — Structural UI Wireframes & Layout Hierarchy
8. [ui-ux.md](templates/ui-ux.md) — Interactive Behaviors, Micro-interactions & Accessibility States
9. [security.md](templates/security.md) — Threat Modeling, Vulnerability Mitigation & Security Controls
10. [roadmap.md](templates/roadmap.md) — Milestone Planning, Phasing & Work Breakdown
11. [deployment.md](templates/deployment.md) — Infrastructure, Release Pipeline & Environment Configuration
12. [qa.md](templates/qa.md) — Quality Assurance, Test Strategy & Verification Plan
13. [runbook.md](templates/runbook.md) — Incident Response, Operational Procedures & Observability
14. [erd.md](templates/erd.md) — Entity-Relationship Diagram: entities, identity, relationships, cardinality/optionality, ownership, integrity/lifecycle, traceability, physical design

### Selection, Omission & Provenance Rules:

- **No Mandatory 14 Docs for Settled Features:** Routine bug fixes, isolated tasks, refactors, and settled features do not regenerate the 14 docs.
- **Default Baseline Subset (6 Core Docs):** `bootstrap` and `adopt` author `blueprint.md`, `prd.md`, `frd.md`, `techstack.md`, `security.md`, `roadmap.md`, plus conditional `erd.md` when persisted entities/relationships are introduced, changed, or adopted without an adequate existing model (otherwise mark ERD `skipped`/`N/A` with reason). Omit remaining docs in the planning table as `skipped` without empty files.
- **Explicit Full 14-Doc Suite:** On explicit operator request, satisfy all 14 contracts (reusing existing project docs/aliases; non-applicable docs get a meaningful `N/A` rationale).
- **Specification Directory:** Honor existing project conventions (e.g. `docs/` or root aliases); deterministic default is `docs/specs/`.
- **Artifact persistence ([Workflow Artifacts](references/workflow-artifacts.md)):** Default paths `docs/specs/<workflow-id>.md`, `docs/daw/plans/<workflow-id>.md`, `docs/daw/workflows/<workflow-id>.md` (lean single-doc sections preferred); rendered mockup before UI build (§5).
- **Standardized Document Metadata Block:** Every spec doc includes:
  ```markdown
  > **Status:** Draft / Ready for Review / Approved / Superseded
  > **Owner:** [Verified Operator Name / Role, or Unassigned]
  > **Scope:** [Bounded component, service, or repository area]
  > **Source Documents / Revision:** [Commit SHA, PR #, or path@rev, or unverified]
  ```
- **Document Workflow Gate:** Follow [Document Quality](references/document-quality.md). Parent owns expected doc set and state (`intake` -> `authoring` -> `review` -> `ready`, with `review` -> `rework` -> `review`). Invoke `validate.py docs --transition` before each edge. `<spec_dir>/ledger.json` (validated via `validate.py ledger`) is derived from existing transition records via `scripts/derive_ledger.py --write` — never hand-write hashes or hand-edit the ledger. Edits invalidate prior acceptance; the stateless gate checks prerequisites, evidence, coverage, and review records without certifying semantic truth or intercepting tools.

---

## 6. Canonical Module Handoff Contract

All module handoffs follow [routing §5](references/routing.md#5-canonical-module-handoff-contract). Required outer fields: `objective`, `input_paths`, `output_paths`, `acceptance_criteria`, `evidence`, `status`, `handoff_to`, `details`. (Cold factual `daw-ask` may defer schema detail per §1 rule 7, never safety/completion distinctions.)

### Envelope Invariants:

- **Observable Transition Checkpoints & Handoff Transport:** Deliver complete JSON envelopes BEFORE advancing stages. Transport hierarchy per [User-Facing Reports & Handoff Transport](references/routing.md#user-facing-reports--handoff-transport): tool/subagent return or native message channel -> authorized artifact reference -> clearly labeled inline JSON checkpoint fallback.
- **User-Facing Reports vs. Internal Handoffs:** Normal user replies MUST be concise natural language (unless JSON/CLI contract is requested): state outcome and artifact paths, report only exercised checks/limits (label supplied transcripts as historical, never rerun; keep transition names/outcomes verbatim), name unresolved decisions with scope and blocking impact, and give one concrete next action (command/invocation or artifact + expected result, at most two alternatives; name owner/action when blocked; state completion when done). Never dump full internal JSON envelopes or raw logs in normal replies.
- **Module-Specific Details & Outer Schema:** Stage facts live in `details` (e.g. `tasks` with `target_files` and `verification_command` in `daw-plan`, `stage_1_conformity`/`stage_2_technical_audit` in `daw-review`, `checks` in `daw-verify`); outer schema types and values are defined solely in [Canonical Handoff Schema](references/routing.md#canonical-handoff-schema). Outer `status` is `pass`, `fail`, or `blocked`.
- **Stage-Scoped Status & Completion Gate:** Outer `status: "pass"` proposes stage criteria satisfaction only — never end-to-end completion or authorization. Final completion requires `validate.py contract --stage complete` passing with a post-change `result` snapshot (`baseline` is pre-change; verify evidence binds to `result.revision`).
- **Correction Loop & Route Re-Entry:** On `not accepted`, parent re-dispatches to the earliest stage able to fix the failing artifact per [Correction Loop & Route Re-Entry](references/operations.md#correction-loop--route-re-entry) (unknown cause -> `daw-debug`; wrong fix -> `daw-build`; wrong tasks/order -> `daw-plan`; wrong requirement -> design/clarification or `spike`; `ship` CI/review failure -> build route via parent). Re-evaluate on the new revision; escalate after 3 non-progressing rounds; hard-stop at 3 escalation cycles as `blocked`.
- **Parent Acceptance Checkpoint & Ranked Triage:** Worker completion/`pass` != parent acceptance. Parent inspects primary evidence against current revision at [Parent Acceptance Checkpoint](references/operations.md#parent-acceptance-checkpoint) across [Checkpoint Boundaries](references/operations.md#checkpoint-boundaries) (including [Prefinal Coupling Checkpoint](references/operations.md#parent-prefinal-coupling-checkpoint)) and records `accepted`/`not accepted` with criterion reasons in [Parent-Owned Acceptance Record](references/operations.md#parent-owned-acceptance-record). Every worker result enters the parent-owned [Ranked Result Triage](references/operations.md#ranked-result-triage) queue in the plan/progress record; parent deduplicates, re-ranks, and gates dispatch (never auto-accept or auto-deploy).
- **Status Integrity, Advisory Handoff & Empty Paths:** `fail` = executed criteria failed/incomplete; `blocked` = missing prerequisites/context/approvals. `handoff_to` is advisory to the parent (pending downstream work precludes completion). `input_paths`/`output_paths` may be empty for read-only/no-file stages; evidence may cite tool logs/observations.
