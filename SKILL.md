---
name: deterministic-agentic-workflow
description: "Use to route multi-step engineering tasks, bootstrap greenfield specifications, adopt documentation for existing codebases, or govern execution across the bundled DAW suite: provides router dispatch across 12 specialized execution modules (daw-design, daw-plan, daw-debug, daw-build, daw-review, daw-verify, daw-workspace, daw-ask, daw-setup, daw-wizard, daw-untangle, daw-ship), document-driven planning across the 14-doc specification matrix, capability routing, preflight checks, fail-closed risk gating, and verifiable evidence gates."
compatibility: "Python 3.10+ stdlib validator & route engine; core workflow instructions remain fully usable without Python."
license: MIT
metadata:
  version: "0.2.0"
---

# Deterministic Agentic Workflow

Operate AI agents using the core architectural axiom: **"Otaknya boleh generative, tangannya harus deterministic."**
Generative cognitive capabilities are reserved for reading context, analyzing intent, designing specifications, planning execution, and synthesizing solutions. All state mutation, system modification, deployment, migration, and verification must execute through deterministic scripts, bounded tools, and verifiable proof gates.

> **Instructional Contract & Scope Notice:** This skill acts as the root router and governance entrypoint for the complete bundled Deterministic Agentic Workflow suite. It directs execution to 12 dedicated, bundled modules in `skills/daw-*/` (and their canonical sibling symlinks). It does not install runtime system hooks, daemon supervisors, automated enforcement interceptors, or external tool suites. Deterministic execution tools and scripts do not automatically guarantee semantic success; truthful verification requires inspecting observable runtime evidence against Acceptance Criteria. Documents alone never constitute running background services or deployment authorization.
> **Native Interactive Clarification (all decision workflows):** Ask only material unknowns not resolvable from evidence, using the [canonical native interactive clarification transport](references/grilling.md#native-interactive-clarification-transport-canonical-rule). Discover the actual tool/schema; never invent one. Cancellation or unanswered questions remain unresolved, never consent. Text fallback is allowed only when native transport is absent or unavailable; the explicit headless bench/oracle adapter is the sole file-transport exception. Preference clarification never bypasses provider/security/point-of-risk controls, adds no approval gate to low-risk work, and does not negate explicit authorization for its exact target/scope/action (§4).

Install the complete suite using [the offline installer](references/installation.md). It targets documented skill locations for Codex, Claude Code, Gemini CLI, Cursor, and Copilot. Keep the root and all modules together; on hosts without directory symlinks, load child modules by their canonical paths from this root. Host tools, approval mechanisms, and client discovery remain environment-specific.

Article Reference: Rama Digital — _Agentic Tapi Deterministic Workflow AI Agent_ (https://ramadigital.id/blog/agentic-tapi-deterministic-workflow-ai-agent).  
_Advice separation note:_ Core article principles (generative planning, deterministic mutation, document contracts, verification gates) establish the architectural foundation. Local operational additions in this skill and references define the 12-module suite architecture, declarative manifest routing, two-stage review loops, and isolated workspace controls for multi-agent CLI and workstation environments.

---

## 1. Suite Architecture & Bundled Module Delegation

The DAW suite is **self-contained as a complete 12-module bundle**. It requires **no external workflow frameworks (e.g. Superpowers) or third-party registries**. However, all 12 bundled internal execution modules are **mandatory core dependencies** for complete suite execution:

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

1. **Delegation, Not Recursion:** The root router dispatches to modules based on classified intent and operational facts. Modules perform their specific phase and yield back to the orchestrator with recommended next stages. Modules **NEVER** recursively call the root router or invoke each other in circular loops.
2. **Missing Module Policy:** All 12 modules are required core components. If any required internal module is missing from the suite, the workflow is **blocked**; it does not silently degrade into shallow inline approximations. External specialist domain skills remain optional augmentations.
3. **Proportionality:** Small, single-line patches or isolated fixes do not trigger the full 14-document matrix. Planning overhead scales proportionally with risk and blast radius.
4. **Workflow Artifacts (canonical):** For multi-step authorized work, specification, saved plan, parent-owned progress record, and rendered visual mockup (where UI-affecting) follow the canonical contract in [Workflow Artifacts](references/workflow-artifacts.md): a proportional authoritative specification is persisted before tactical decomposition (reuse an adequate spec; if clear user requirements have no written source the authorized parent records the faithful bounded what/why/non-goals/AC before `daw-plan`; ambiguity returns to the existing design/clarification route with no new `daw-design` insertion for clear routes); the plan is saved before build dispatch and maps stable requirement/AC IDs to task IDs, exact target files, dependencies, parallel ownership, expected observations/checks, evidence, and separate parent acceptance with bound spec revisions; a required parent-owned durable progress record opens at intake naming the actual active module/stage and subphase (not only the planned route), active task(s), completed accepted stages, current scoped revisions, blockers/owner/question, next permitted action, primary evidence/handoff refs, and parent acceptance distinct from worker pass; tiny/read-only/bare-no-brief runs retain the zero-document path, and workflow-owned progress metadata is ignored when deciding blank bootstrap vs adopt (it is a state record, not a requirements source).
5. **Canonical Relative Linking:** Modules reference suite documentation and templates using root-relative paths resolved from their location (`../../references/...` or `../../templates/...`).

6. **Harness-Native Worker Graphs:** At workflow intake, discover harness capabilities and automatically retain same-role builders and independent reviewers when the task already warrants delegation and corrective rounds and completed-worker continuation is supported, unless the user opts out. No persistence keyword or prior setup invocation is required. Small direct tasks stay direct; do not add route stages or workers to enable retention. Follow the [persistent worker graph contract](references/operations.md#persistent-worker-graphs-harness-native) for revision-scoped joins, evidence, stop/replan and explicit fresh-worker fallback when optional continuation is unavailable. Retention is session-bounded, not durable crash recovery.
7. **Efficient Context Loading & Progressive Disclosure:**
   - **Load CURRENT stage only:** When executing any stage, load ONLY the skill file corresponding to the active stage (`skills/daw-<stage>/SKILL.md`) and required domain templates. Do NOT read the entire 12-module suite, all module instructions, or all 14 document templates into active prompt context simultaneously.
   - **Progressive disclosure for references:** Reference files (`references/routing.md`, `references/operations.md`, etc.) are large references consulted on-demand for exact section headings only (using targeted section/line ranges), NEVER read in their entirety upfront.
   - **Honest direct fallback:** If tools or subagent delegation are unavailable, execute directly via honest direct fallback in the current session; never simulate tool execution or claim unexercised evidence.
   - **Cold factual advisory minimum:** A direct `daw-ask` factual answer with no material decision, parent handoff, or downstream transition loads the active module and root §4/§6 safety rules only. It may defer routing §5 schema/transport detail and the full grilling protocol until a material decision or actual handoff requires them. This exception permits no mutation, execution approval, or bypass of safe intake and route selection.

---

## 2. Invocations & Observable Action Protocol

### Invocation Modes

1. **Explicit Bare Invocation:**
   - When invoked bare without a task (e.g. `"Use deterministic-agentic-workflow"`):
     - The agent immediately inspects the target directory (`cwd`). It does not scan parent directories unless explicitly directed.
     - If existing code or partial documentation is found -> enters **Adopt** mode (suggest **Setup** first if no `## DAW Configuration` block exists).
     - If the target directory is empty and a brief is provided -> enters **Bootstrap** mode (starts with `daw-wizard` interview).
     - If the target directory is empty and **no brief** is provided -> starts `daw-wizard` interview phase 1; the wizard's phase 1 round acts as the material question round to establish project concept, scope, and target users. It halts blocked on unanswered material questions and **never invents phantom product documents**.
2. **Task-Specific Invocation:**
   - When loaded alongside an explicit user task (e.g. `"Use deterministic-agentic-workflow to fix the NPE in auth"` or `"Use deterministic-agentic-workflow to review PR #12"`):
     - This is **not** a bare invocation. The agent does not halt for empty briefs; it extracts the explicit intent and proceeds directly to dispatch.

### Observable Action Protocol

To ensure transparency before making filesystem modifications, the agent must output an observable planning table before performing writes (never plan-only without execution):

| Target File / Path        | Action (`create` \| `update` \| `reuse` \| `skip` \| `block`) | Rationale / Provenance                                  |
| :------------------------ | :------------------------------------------------------------ | :------------------------------------------------------ |
| `docs/specs/blueprint.md` | `create`                                                      | Initial system architecture based on operator brief.    |
| `src/auth.py`             | `update`                                                      | Surgical fix for null pointer exception.                |
| `docs/specs/wireframe.md` | `skip`                                                        | Backend-only change; UI contracts non-applicable (N/A). |

Upon phase completion, report final results using exact statuses: `created`, `updated`, `reused`, `skipped`, or `blocked`.

---

## 3. Finite Intent Precedence & Routing

The workflow routes incoming tasks using an explicit finite intent decision hierarchy based on operational facts, not open-ended keyword matching:

1. **Review (`review`):** Static analysis, code review, diff audit, or security boundary assessment on existing code or PRs. When the user's primary intent is evaluation/audit of code or diffs, `review` takes precedence. Evaluation-only review remains strictly read-only: `daw-review` never mutates and ignores unknown risk or workspace preferences. An explicit audit-and-fix request is parent-composed as a read-only review diagnosis followed, only when findings warrant it, by an authorized correction route selected from those findings — `bugfix` for an undiagnosed defect, `patch` only for a pre-diagnosed clear scope, or `feature` for a new capability — adding no new route enum, stage, or schema; the parent must not end the workflow after the initial review while authorized fixes remain. Dispatches to `daw-review`.
2. **Untangle (`untangle`):** Explicit read-only structural analysis, coupling/cohesion assessment, modular boundary investigation, and change-coupling analysis governed by [references/change-coupling.md](references/change-coupling.md). Strictly read-only; ignores unknown risk or workspace preferences; no daw-workspace, approval execution, or mutation. Dispatches to `daw-untangle`. (Note: refactoring implementation requests themselves are NOT silently routed to untangle; mutating behavior-preserving restructuring uses the `refactor` route (intent 10) after scope is accepted. Untangle is an explicit bounded investigation, never an extra mandatory stage on all requests or an unsolicited whole-repo mandate; in code delivery, escalation from the prefinal coupling checkpoint occurs only on demonstrated boundary obscurity for an authorized scope).
3. **Ask (`ask`):** Purely conversational, read-only architectural consultation, codebase Q&A, or decision trade-off analysis. Read-only user intent always wins. Ignores unknown risk or workspace preferences. Dispatches to `daw-ask`.
4. **Setup (`setup`):** Interactive project configuration discovery and repo convention block authoring. Explores repository commands and context files, confirms settings with the user, and writes/updates `<!-- daw-config:start -->` in `AGENTS.md` (or `CLAUDE.md`). Dispatches to `daw-setup`. Suggest this on first DAW use in a repository with no existing DAW configuration block.
5. **Bootstrap (`bootstrap`):** Greenfield project specification from a brief or prompt in an empty or new directory. Begins with an interactive requirements interview via `daw-wizard`, then generates core specification documents and planning breakdown. Dispatches to `daw-wizard` -> `daw-design` -> `daw-plan` (documentation-only).
6. **Adopt (`adopt`):** Reverse-engineering and specification authoring for an existing codebase with missing or partial documentation. Dispatches to `daw-design` -> `daw-plan` (documentation-only; preserves user code).
7. **Bugfix (`bugfix`):** Diagnosing, reproducing, and resolving an existing defect or test failure. Dispatches to `daw-debug` -> `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify`. Prepends `daw-workspace` if workspace is isolated.
8. **Patch (`patch`):** Minimal, pre-diagnosed fix or surgical change with well-defined constraints. Requires `requirements: "clear"`; unknown or unclear requirements yield `needs-input` with no stages. Dispatches to `daw-build` -> `daw-verify`. Prepends `daw-workspace` if workspace is isolated.
9. **Feature (`feature`):** Multi-step functional change or new capability. If requirements are clear: `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify`. If requirements are unclear: `daw-design` -> `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify`. Prepends `daw-workspace` if workspace is isolated.
10. **Refactor (`refactor`):** Behavior-preserving structural restructuring (rename, extract, re-layer, dead-code removal) whose observable behavior must be unchanged. Characterization tests precede structural edits; unknown requirements yield `needs-input` with no stages. Dispatches to `daw-untangle` -> `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify`. Prepends `daw-workspace` if workspace is isolated. See [refactor protocol](references/developer-lifecycle.md#4-behavior-preserving-refactor-protocol).
11. **Maintain (`maintain`):** Dependency, toolchain, or platform upgrade; deprecation removal; version migration. Dispatches to `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify`. Prepends `daw-workspace` if workspace is isolated.
12. **Spike (`spike`):** Time-boxed throwaway prototype to resolve technical uncertainty. Always isolated: dispatch is fixed as `daw-workspace` -> `daw-build` -> `daw-ask` regardless of the workspace flag; unknown requirements are allowed (the spike exists to resolve them). Output is throwaway only — findings return via `daw-ask`; production code re-enters `feature`/`refactor` and is never merged from the spike. See [spike protocol](references/developer-lifecycle.md#3-spike-protocol).
13. **Ship (`ship`):** Integration and delivery of verified work: commit hygiene, pull request, CI triage, review feedback, merge and release readiness. Dispatches to `daw-ship`. Unknown risk yields `needs-input`; high risk requires interactive approval. Push to protected branches, merge, tag, publish, and deploy remain point-of-risk actions needing exact interactive authorization (§4). See [ship protocols](references/developer-lifecycle.md#8-pull-request--ci-protocol).

### Professional Delivery Lifecycle

Read-only intents (`review`, `untangle`, `ask`) keep top precedence. Among mutating intents, select by the observable character of the work, not keywords: `ship` when the work is integration/delivery of already-verified changes (no product-code edits needed); `spike` when the blocker is technical uncertainty and the output is throwaway evidence; `refactor` when observable behavior must stay identical; `maintain` when the change is driven by a dependency, toolchain, platform, or deprecation; `bugfix`/`patch`/`feature` otherwise. A request mixing behavior change with restructuring splits into separate `refactor` and `feature` workflows (structure first), never one mixed diff.

End-to-end professional flow: setup -> clarify/spike -> design -> plan -> build with inner loop (run the app while building, smoke early) -> review -> verify -> ship (commit / PR / CI / review-feedback loop) -> release -> retro feeding `AGENTS.md`. Exact commands, time-boxes, and escalation budgets live in [Developer Lifecycle](references/developer-lifecycle.md) (inner loop §1, time-boxing §2, spike §3, refactor §4, maintenance §5, bisection §6, commit hygiene §7, PR/CI §8, review feedback §9, release §10, retro §11).

### Routing Execution API & Manifest Policy

Automated and programmatic routing decisions are governed by `references/suite-manifest.json` (schema_version 1) and evaluated via the read-only stdlib script:

```bash
python3 "$SUITE_ROOT/scripts/route.py" REQUEST.json [--format text|json] [--root SUITE_ROOT]
```

_(Always invoke using the explicitly resolved script path `$SUITE_ROOT/scripts/route.py`, never assuming `scripts/` exists in the target project's `cwd`)._

The request requires classified input facts (`schema_version`, `intent`, `requirements`, `risk`, `workspace`):

- If requirements are unknown for `bootstrap`, `feature`, `refactor`, or `maintain`, requirements are unknown or unclear for `patch`, or if workspace is unknown for mutating intents (`feature`, `bugfix`, `patch`, `refactor`, `maintain`), or if risk is unknown for mutating intents (`feature`, `bugfix`, `patch`, `refactor`, `maintain`, `ship`), the engine returns `status: "needs-input"` with explicit blockers. `spike` allows unknown requirements; `ship` uses unknown risk as a `needs-input` blocker and high risk as `interactive_approval_required`.
- In shell-less or Python-less environments, agents may evaluate `references/suite-manifest.json` manually, but must explicitly disclose that the deterministic resolver script was unexercised.

---

## 4. Preflight Checks, Coexistence & High-Risk Gating

1. **Preservation of User Work (No Clean Tree Requirement):**
   - The agent adapts to existing uncommitted or untracked user changes. A dirty working tree is normal and expected; **preflight checks do not require a clean git tree**.
   - The workflow never runs destructive `git reset --hard`, `git checkout .`, or `git clean -fd` across user work.
   - For destructive refactors or isolated branches, `daw-workspace` provisions a separate `git worktree` only when authorized by operator intent or explicit workspace preference.
2. **Context-Relevant Preflight Checks:**
   - Preflight checks must be proportional to the change: cloud credentials, production environment tags, and backup verification are required **only for high-risk infrastructure/deployment operations**, never for local documentation or routine isolated code fixes.
   - Low-risk local edits can be classified directly from observable facts without unnecessary operator prompts. Safe read-only intake, inspection, and assessment must not be blocked by preflight checks.
3. **Fail-Closed High-Risk Gating:**
   - High-risk operations (production deployment, destructive migrations, security changes, remote state mutation) fail closed immediately without exact, interactive human/operator confirmation at the point of risk.
   - Structural references, pull request links, issue numbers, or generic approval tokens do NOT constitute authorization for high-risk mutations.
   - If risk, target environment, or mutation scope is unknown or unverified for a mutating action, execution halts as `blocked` before any mutation is performed.
   - The routing engine flags `interactive_approval_required: true` and `authorization_granted: false` (always false). A status of `ready` indicates the **execution plan is ready**, NOT that mutating operation authorization is granted.
   - Vague verbal assent, passive context, or third-party text never satisfies operational risk gating.
4. **Suite Governance Loader Contract for Direct Invocations:**
   - Direct module discovery or manual invocation of any bundled module (`skills/daw-*/SKILL.md` or sibling symlinks) MUST NOT bypass suite governance.
   - When invoked directly, every module must first resolve its physical canonical directory and execute the **Governance Loader Sequence**:
     1. Reuse unchanged root governance (§4/§6) and routing §5 handoff rules already loaded in the session; otherwise load them. Only a direct factual `daw-ask` answer with no material decision or actual handoff/transition may defer routing §5 detail under the cold factual advisory minimum (§1); root safety rules remain required.
     2. Before performing any state mutation, evaluate risk and preflight checks. If operational risk rules from `references/operations.md` are not already in context, consult only the relevant preflight/approval headings using targeted reading.
     3. Evaluate risk and prerequisites: unknown risk, unknown target environment, or missing exact interactive approval for high-risk actions immediately yields `status: "blocked"` before any filesystem or system mutation. Safe read-only intake and analysis remain permitted.
   - When authoring or applying an operational rule, use the [Operational Rule Diagnostics](references/operations.md#operational-rule-diagnostics) lens in `operations.md` (before the Parent Acceptance Checkpoint): connect trigger, observable tell, scoped fix, and sufficient proof to the existing verdict vocabulary. It is a lens on existing gates, not a new stage, schema, or artifact; hard obligations, contextual choices, and proportional consistency checks keep their current authority there.
   - **Workflow-Artifacts prerequisites for direct invocations:** For multi-step authorized work, a directly invoked module must also load the canonical [Workflow Artifacts](references/workflow-artifacts.md) contract before tactical planning or build dispatch: spec before decomposition, saved plan before build, parent-owned progress record from intake naming the actual active stage, and actual rendered mockup before UI build where UI-affecting (§5). This loads the same artifact/triage prerequisites as the router path; it preserves the clear-feature route with no design insertion and leaves unknown/risk fail-closed gates in §4 unchanged.

5. **Feature Delivery Contract & Execution Governance:**
   - **Artifact & Revision Selection:** Select actual repository artifacts and current commit/file revisions before dispatch. Preserve existing stable requirement/story/AC IDs (`REQ-xxx`, `US-xxx`, `AC-xxx`); do not mandate artificial new filenames (`spec.md`, `tasks.md`) when existing specifications (`prd.md`, `roadmap.md`) exist.
   - **Workflow artifacts persistence:** Spec/plan/progress/mockup persistence, paths, and ownership follow [Workflow Artifacts](references/workflow-artifacts.md) (§1–§5): single-document spec/plan/progress sections or default paths when lean; no duplicate task-tracker authority (artifact ref in handoff `details`, outer schema unchanged); UI-affecting work requires an actual inspectable rendered visual mockup (not prose/ASCII/wireframe-only) from settled domain/flow before UI build, reused only when matching existing, with scoped N/A for no-UI and small nonvisual fixes.
   - **Three-Tier Verification Boundary:**
     - _Plan Self-Check:_ Planning agent (`daw-plan`) verifies requirement coverage and acyclic task graphs before submission.
     - _Independent Prebuild Readiness Checkpoint:_ For feature/spec-dependent builds, parent orchestrator dispatches read-only `daw-review` scoped strictly to current specification and plan revisions before `daw-build`. This bounded checkpoint evaluates cross-artifact consistency without inserting new routing stages or invoking module recursion.
     - _Route-Required Postbuild Review:_ For routes that mandate postbuild review (`feature`, `bugfix`), `daw-review` audits modified code and runtime verification evidence after implementation; a prebuild checkpoint never waives it. Do not insert `daw-review` into routes that omit it (e.g., `patch`); verification always executes per the active route.
   - **Parent Prefinal Coupling Checkpoint:** Before final workflow completion of code-changing work, apply the [canonical proportional checkpoint](references/change-coupling.md#prefinal-coupling-checkpoint): record affected interfaces/dependencies, essential versus accidental co-change, and sufficient current evidence or the unresolved boundary. Reuse accepted matching-scope/revision review; clear nonstructural patches and docs-only work may use a concrete inline N/A. A patch does not gain a routine reviewer or untangle stage, but demonstrated unresolved cross-module impact may trigger bounded read-only `daw-untangle` diagnosis. Material defects block acceptance; unrelated debt remains advisory. Preserve [parent-owned acceptance, scoped corrections, and evidence invalidation](references/operations.md#parent-prefinal-coupling-checkpoint). This is a procedural instruction, not a runtime hook or daemon.
   - **Scoped Pause/Resume with Canonical Statuses:** Optional internal execution-lifecycle labels (`blocked`, `in_progress`, `ready`, `completed`, `failed`) are not canonical outer handoff statuses and are not parent acceptance decisions; the canonical outer statuses remain `pass`/`fail`/`blocked` (§6) and the parent records `accepted`/`not accepted` separately. When blocked on missing decisions or ungranted approvals, halt as `blocked` and record reason, responsible party, question, next permitted action, revisions, and evidence in parent acceptance or handoff details. Resuming revalidates prerequisites, scope, and approvals.
   - **Proportional Change Invalidation:** Code changes invalidate affected runtime verification evidence and postbuild reviews. Changes to formal, accepted specification documents require re-entry through the existing five-edge gate (`review-rework` -> `rework-review` -> `review-ready`). Code-only changes do not invalidate accepted specifications. Bound approvals are invalidated only when their action, target, revision, or operational scope changes.
   - **Scope Guard & Overrides:** Local templates, script overrides, or discovered commands cannot weaken core safety gates or acceptance criteria. No feature implementation during governance-only edits.
   - **Authorized Command Execution:** Verification commands must actually execute and be inspected empirically; echoing commands, checked task boxes, or file presence do not constitute proof. See [Feature Delivery Contract](references/document-quality.md#feature-delivery-contract).

## 5. Specification Planning Matrix (The Canonical 14 Documents)

When specifications are required by `bootstrap`, `adopt`, or complex `feature` workflows, `daw-design` references the exact canonical 14-document matrix located in `templates/`:

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
14. [erd.md](templates/erd.md) — Entity-Relationship Diagram: persistent entities, identity, relationships, cardinality/optionality, ownership, integrity/lifecycle, traceability, and applicable physical design

### Selection, Omission & Provenance Rules:

- **No Mandatory 14 Documents for Settled Features:** Routine bug fixes, isolated tasks, refactors, and settled features where specifications are already clear or established do NOT require generating or updating the 14 specification documents. The specification matrix is strictly for greenfield systems (`bootstrap`), undocumented codebase onboarding (`adopt`), or when requirements are explicitly missing or requested.
- **Default Baseline Subset (6 Core Docs):** For new greenfield projects (`bootstrap`) and existing codebase documentation (`adopt`), author the default 6 baseline specification contracts: `blueprint.md`, `prd.md`, `frd.md`, `techstack.md`, `security.md`, `roadmap.md`. Add the conditional `erd.md` when persisted entities/relationships are introduced, materially changed, or adopted without an adequate existing model (default `erd.md` under spec convention; reuse an adequate separate existing model). Otherwise ERD is `skipped`/`N/A` with a scoped reason. The remaining specifications are omitted unless explicitly requested; in the planning table, state omitted documents as `skipped` without generating empty files.
- **Explicit Full 14-Doc Suite:** When an operator explicitly requests the full 14-document suite, all 14 document contracts must be satisfied. Existing architecture documents, filenames, or established project aliases count toward satisfying contracts; do not force duplicate new files when existing project specifications already satisfy the contract. Any contract not applicable to the architecture (e.g., UI wireframes for a headless backend CLI) must contain an explicit, meaningful `N/A` section with rationale, rather than being omitted.
- **Specification Directory Determination:** Always check the target project's established conventions first (e.g. existing `docs/` or root aliases). If no established directory exists, **the deterministic default is `docs/specs/`**.
- **Artifact persistence (canonical [Workflow Artifacts](references/workflow-artifacts.md)):** Where specs are required and multi-step work is authorized, authoring follows the proportional-spec → saved-plan → intake-opened progress-record sequence there (default `docs/specs/<workflow-id>.md`, `docs/plans/<workflow-id>.md`, `docs/workflows/<workflow-id>.md` when no convention exists; lean single-document spec/plan/progress sections preferred). UI-affecting entries require an actual rendered visual mockup before UI build (§5); wireframe-only or prose does not satisfy it. The matrix above remains the catalog of canonical kinds — no mandatory full 14-doc generation for settled/tiny/read-only work.
- **Standardized Document Metadata Block:** Every specification document must include the standard template metadata block:
  ```markdown
  > **Status:** Draft / Ready for Review / Approved / Superseded
  > **Owner:** [Verified Operator Name / Role, or Unassigned]
  > **Scope:** [Bounded component, service, or repository area]
  > **Source Documents / Revision:** [Commit SHA, PR #, or path@rev, or unverified]
  ```
- **Document Workflow Gate:** For selected formal specifications, use the audience tasks and per-document criteria in [Document Quality](references/document-quality.md). The parent owns the expected document set and actual workflow state: intake → authoring → review → ready, with review → rework → review. Invoke the read-only `validate.py docs --transition` gate before each edge; advance only when that transition is eligible. Document or source changes invalidate prior acceptance. The gate checks transition prerequisites, current evidence, coverage, and recorded review decisions; it does not persist workflow state, authenticate reviewers, decide semantic truth, prove human comprehension, or intercept tools. Keep trivial inline work proportional and never require all 14 documents merely to satisfy the gate.

---

## 6. Canonical Module Handoff Contract

All module handoffs use the sole full outer schema and transport authority in [routing §5](references/routing.md#5-canonical-module-handoff-contract). Required fields are `objective`, `input_paths`, `output_paths`, `acceptance_criteria`, `evidence`, `status`, `handoff_to`, and `details`; retain the active module's required details. A direct factual `daw-ask` answer without a material decision or actual handoff/transition may defer schema detail, not these safety and completion distinctions.

### Envelope Invariants:

- **Observable Transition Checkpoints & Handoff Transport:** Canonical output handoffs MUST be delivered and inspectable as complete JSON envelopes (`objective`, `input_paths`, `output_paths`, `acceptance_criteria`, `evidence`, `status`, `handoff_to`, `details`) BEFORE advancing to the next stage, not deferred to final retrospective prose or remembered only in thoughts. Transport follows the hierarchy in [User-Facing Reports & Handoff Transport](references/routing.md#user-facing-reports--handoff-transport): deliver via actual module/tool/subagent return or harness-native message channel; if writing an authorized workflow artifact, supply its exact reference in the handoff. If no non-chat transport or authorized artifact exists, emit a clearly labeled complete inline JSON checkpoint as an explicit fallback before stage transition.
- **User-Facing Reports vs. Internal Handoffs:** Internal canonical JSON is an execution envelope for parent orchestration and downstream transitions, NOT a template for normal user responses. Unless the user explicitly requests JSON/machine-readable format or CLI output contracts mandate exact CLI output, user-facing reports MUST be concise natural language in the user's language: state the outcome and relevant artifact paths, report only actually exercised checks and limits (truthfully labeling provided transcripts as historical, never rerun; preserving reported transition names and outcomes without relabeling them as earlier/later workflow states or certifying semantics), identify unresolved decisions with affected scope and blocking/nonblocking impact, and give exactly one concrete next action. Do NOT duplicate full internal JSON envelopes or lengthy raw command logs in normal replies.
- **Module-Specific Details:** The `details` object carries rich stage-specific facts defined by the CURRENT active module's output contract (e.g. `tasks` with `target_files` and `verification_command` in `daw-plan`, separate `stage_1_conformity` and `stage_2_technical_audit` in `daw-review`, `checks` with runtime evidence in `daw-verify`). Modules define their own internal details payload; root governance enforces the outer envelope and observable stage boundaries.
- **Outer Schema Authority:** Field types, criterion/evidence entries, and permitted values are defined only in [Canonical Handoff Schema and Field Definitions](references/routing.md#canonical-handoff-schema). Outer `status` remains `pass`, `fail`, or `blocked`; module-specific findings belong in `details`.
- **Stage-Scoped Status & Proposed Pass:** Outer `status: "pass"` certifies ONLY that the worker proposes that its stage-specific criteria were satisfied. It is NEVER proof of end-to-end implementation, deployment, or authorization.
- **Correction Loop & Route Re-Entry:** When a stage is `not accepted`, the parent re-dispatches into the earliest stage that can change the failing artifact, following the canonical [Correction Loop & Route Re-Entry](references/operations.md#correction-loop--route-re-entry) table (wrong behavior with unknown cause -> `daw-debug`; wrong fix -> `daw-build`; wrong tasks/order -> `daw-plan`; wrong requirement -> design/clarification or `spike`; CI/review failure on `ship` -> a build route via the parent). Each round is re-evaluated on the new revision, and the loop escalates after 3 non-progressing rounds and hard-stops at 3 escalation cycles as `blocked`.
- **Parent Acceptance Checkpoint:** Dispatch completion and a proposed worker `pass` do NOT equal parent acceptance. The parent orchestrator independently evaluates results at the canonical [Parent Acceptance Checkpoint](references/operations.md#parent-acceptance-checkpoint) across explicit [Checkpoint Boundaries](references/operations.md#checkpoint-boundaries) (including the proportional [Prefinal Coupling Checkpoint](references/operations.md#parent-prefinal-coupling-checkpoint)) and records decisions via the [Parent-Owned Acceptance Record](references/operations.md#parent-owned-acceptance-record). The parent records `accepted` or `not accepted` with a criterion-specific reason separate from the outer status. Reported passes with missing, unexercised, or contradicting evidence MUST be rejected as `not accepted`. Optional check/evidence mappings use existing envelope `details` or plan artifacts without altering the outer schema.
- **Ranked result triage (canonical [operations.md#ranked-result-triage](references/operations.md#ranked-result-triage)):** Every completed worker result is dispositioned and ranked by the parent before acceptance or corrective dispatch; every worker proposes ranked evidence-backed findings or an explicit no-actionable-finding statement. The parent inspects primary evidence against the current revision, deduplicates, re-ranks, and gates every result — a worker `pass` or child rank is never accepted blindly and never auto-deploys. The compact queue lives in the durable plan/progress record ([Workflow Artifacts](references/workflow-artifacts.md)); real external deployment still requires exact target/scope permission at the point of risk.
- **Status Integrity:** `fail` means executed criteria failed or are incomplete; `blocked` means missing prerequisites, environment context, or required interactive approvals. Rich domain findings in `details` cannot override the outer status.
- **Advisory Handoff:** `handoff_to` is an advisory recommendation for the parent orchestrator, never a directive for recursive module-to-module self-execution. Downstream pending work strictly precludes declaring the final workflow complete.
- **Empty Paths Permitted:** `input_paths` and `output_paths` may be empty for read-only evaluations or stages producing no disk artifacts. Evidence references can identify tool logs or observations rather than new files.
