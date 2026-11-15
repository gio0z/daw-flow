# Deterministic Agentic Workflow (DAW) Suite

A portable planning, execution, and verification suite for AI coding agents. Python 3.10+, no third-party runtime dependencies, MIT licensed.

> **"Otaknya boleh generative, tangannya harus deterministic."**
> _(Generative cognitive reasoning for context and planning; deterministic execution and verification for system state)._

This package provides a self-contained engineering workflow suite combining root router dispatch, an explicit 12-module execution architecture (`skills/daw-*/`), the canonical 14-document specification matrix, capability-based risk gating, and verifiable evidence proof gates.

> **Professional delivery lifecycle:** End-to-end flow — setup -> clarify/spike -> design -> plan -> build with inner loop -> review -> verify -> ship (commit / PR / CI / review-feedback loop) -> release -> retro feeding `AGENTS.md`. Protocols in [Developer Lifecycle](references/developer-lifecycle.md); new intents `refactor`, `maintain`, `spike`, and `ship` (via `daw-ship`) are first-class routes (13 intents, 12 modules total).

> **Instructional Contract & Scope Notice:** This suite provides instructional workflow guidance for coding agents. It directs execution across 12 bundled modules (`skills/daw-*/`). It does not install daemon supervisors, background services, runtime interceptors, or automated enforcement mechanisms. Route evaluation (`scripts/route.py`) and package validation (`scripts/validate.py`) are read-only structural checks, not automated dispatchers or semantic proofs of correctness. Deterministic scripts and specifications do not guarantee semantic success; truthful verification requires inspecting observable runtime evidence against Acceptance Criteria.

---

## 1. Quickstart & Invocation

### Interactive Installer (Recommended)

Choose the interactive setup wizard — it detects installed agents on your machine, asks for scope (`user` vs `project`) and target agent(s), and can initialize a valid `<!-- daw-config -->` block in your project's `AGENTS.md` or `CLAUDE.md`:

- **One-liner (no manual clone; fetches into a temp directory and runs the stdlib installer):**
  ```bash
  curl -fsSL https://raw.githubusercontent.com/gio0z/daw-flow/main/install.sh | bash
  ```
- **Zero-clone via `uvx` (`uv`) or `pipx`:**
  ```bash
  uvx --from git+https://github.com/gio0z/daw-flow daw install
  ```
- **From a local checkout:**
  ```bash
  git clone https://github.com/gio0z/daw-flow.git
  cd daw-flow
  python3 scripts/install.py    # launches interactive wizard in a TTY (or pass --interactive)
  ```

### Native Agent Plugins

The suite ships native plugin manifests at `.claude-plugin/`, `.cursor-plugin/`, and `.codex-plugin/`:

- **Claude Code:**
  ```text
  /plugin marketplace add https://github.com/gio0z/daw-flow
  /plugin install deterministic-agentic-workflow@deterministic-agentic-workflow
  ```
  Or load a local checkout directly: `claude --plugin-dir /path/to/daw-flow`.
- **Cursor:**
  ```text
  /agent plugin marketplace add https://github.com/gio0z/daw-flow
  ```
- **Codex CLI:**
  ```bash
  codex plugin marketplace add gio0z/daw-flow
  codex plugin add deterministic-agentic-workflow@deterministic-agentic-workflow
  ```
- **Antigravity CLI:**
  ```bash
  agy plugin install https://github.com/gio0z/daw-flow
  ```

### Non-Interactive CLI & Project Setup

Install directly with flags (non-TTY safe, deterministic, zero network access from `scripts/install.py`):

```bash
python3 scripts/install.py install --agent codex --scope user
python3 scripts/install.py install --agent claude --scope project --project-root /path/to/project --init-config
```

Choose `codex`, `claude`, `gemini`, `cursor`, `copilot`, `opencode`, `antigravity`, or `all` (`--agent all` applies `install`, `status`, or `uninstall` across every preset agent for the selected `--scope`). Add `--init-config` on `--scope project` installs to append a validated `<!-- daw-config:start -->` block to `AGENTS.md` (or `CLAUDE.md` if present without `AGENTS.md`). On Windows, use `python` if that is your Python 3 command. If directory symlinks are unavailable, add `--no-aliases`; the complete root skill still loads its bundled modules by path.

Restart or reload skills in your agent, then ask:

```text
Use deterministic-agentic-workflow to fix this bug and verify the result.
```

Codex also supports `$deterministic-agentic-workflow`; Claude Code exposes `/deterministic-agentic-workflow`. Other clients provide their own skill menus and invocation syntax. Native discovery depends on client version and settings.

Inspect, diagnose, link for local development, update from a refreshed checkout, or remove the same installation:

```bash
python3 scripts/install.py doctor --scope user --json
python3 scripts/install.py status --agent codex --scope user
python3 scripts/install.py install --agent codex --scope user --link
python3 scripts/install.py install --agent codex --scope user --update
python3 scripts/install.py uninstall --agent codex --scope user
```

- **`doctor`**: Read-only environment and installation check verifying Python >= 3.10, `git` >= 2.20, symlink support, preset status, and overlapping/duplicate installations at the same scope.
- **`--link`**: Developer mode that symlinks `<skills_dir>/deterministic-agentic-workflow` (and sibling aliases unless `--no-aliases`) directly to the source checkout so local edits take effect immediately without copying, recording its link receipt inside the target skills directory rather than inside the checkout.
- **`--dry-run`**: Previews an action without writing. Updates and removal refuse changed files, extra files, and unrelated skills. The installer installs the self-contained operational skill package (`SKILL.md`, `LICENSE`, `VERSION`, `.claude-plugin/`, `.cursor-plugin/`, `.codex-plugin/`, `skills/`, `templates/`, operational `references/`, and operational `scripts/`), so removing a copied source checkout does not break a copied installation. Developer tooling, tests, fixtures, and documentation remain in the source repository. It never modifies agent configuration or Git hooks, or installs agent CLIs. (`install.sh` is an optional bootstrap wrapper that clones the repository only when run outside a checkout.)

### Unified `daw` CLI & `pyproject.toml`

The repository includes a zero-dependency PEP 621 `pyproject.toml` (`requires-python = ">=3.10"`) and `setup.py` bundling the operational suite under `share/deterministic-agentic-workflow/`, exposing the unified `daw` console script (`scripts.daw:main`) for `pip`, `pipx`, `uv tool`, and `uvx` installs, or runnable directly without installation via `python3 scripts/daw.py`:

```bash
pip install -e .        # or: pipx install . / uv tool install . / uvx --from git+https://github.com/gio0z/daw-flow daw install
daw --version
daw --help
daw install
daw route --check-suite
daw validate package --root .
daw install doctor --scope user
```

`daw <subcommand> [args...]` dispatches to `route`, `validate`, `run`, `worktree`, `install`, `derive-ledger`, and `derive-tasks` while preserving their arguments and exit codes.

See [installation and compatibility](references/installation.md) for exact paths, platform limits, and custom directories. `status` checks files and module aliases; confirm client discovery in your agent's skill list after installation.

### Common Invocations & Routing Behavior

1. **Explicit Bare Invocation (Inspect & Resolve):**
   - _Prompt:_ `"Use deterministic-agentic-workflow"`
   - _Behavior:_ The agent inspects `cwd`. If existing code or specs are found, enters **Adopt** (suggesting **Setup** first if no `## DAW Configuration` block exists). If the target directory is empty and a brief is provided, enters **Bootstrap** (`daw-wizard` -> `daw-design` -> `daw-plan`). If empty without a brief, begins `daw-wizard` phase 1 questioning to establish concept and scope, halting on unanswered material questions without inventing phantom documents.

2. **Interactive Configuration Setup (`setup`):**
   - _Prompt:_ `"Use deterministic-agentic-workflow to set up DAW conventions for this repo."`
   - _Routing:_ Dispatches to `daw-setup` (documentation-only). Explores existing project context (`git remote`, context files, test/lint/build runners, CI workflows, spec directory), confirms settings with the user, and writes/updates `<!-- daw-config:start -->` in `AGENTS.md` (or `CLAUDE.md`).

3. **Greenfield Wizard & Bootstrap (`bootstrap`):**
   - _Prompt:_ `"Use deterministic-agentic-workflow to bootstrap a real-time multiplayer whiteboard web app from scratch."`
   - _Routing:_ Dispatches to `daw-wizard` -> `daw-design` -> `daw-plan` (documentation-only). Conducts a structured interactive interview across problem concept, scope, system components, tech stack, and ops/roadmap, authoring initial proportional specifications into `docs/specs/`.

4. **Codebase Adoption (`adopt`):**
   - _Prompt:_ `"Use deterministic-agentic-workflow to document this existing repository and identify missing specification coverage."`
   - _Routing:_ Dispatches to `daw-design` -> `daw-plan` (documentation-only). Analyzes existing code and creates specifications without modifying application source code.

5. **Feature Implementation (`feature`):**
   - _Prompt:_ `"Use deterministic-agentic-workflow to add a rate-limiting middleware to the payment service."`
   - _Routing:_ If requirements are clear, dispatches to `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify`. If requirements are unclear, routes first to `daw-design` for specification authoring. Prepends `daw-workspace` if an isolated workspace is requested.

6. **Bugfix Investigation & Repair (`bugfix`):**
   - _Prompt:_ `"Use deterministic-agentic-workflow to fix the null pointer exception when parsing JSON payloads in auth controller."`
   - _Routing:_ Dispatches through `daw-debug` (reproduce & RCA) -> `daw-plan` (patch plan) -> `daw-build` (minimal diff) -> `daw-review` (security & boundary audit) -> `daw-verify` (failing-to-passing test evidence). Prepends `daw-workspace` if an isolated workspace is requested.

7. **Targeted Patch (`patch`):**
   - _Prompt:_ `"Use deterministic-agentic-workflow to patch the typo in config validator and verify tests."`
   - _Routing:_ Dispatches directly through `daw-build` -> `daw-verify` for small, self-contained fixes. Prepends `daw-workspace` if an isolated workspace is requested.

8. **Independent Code Review (`review`):**
   - _Prompt:_ `"Use deterministic-agentic-workflow to review the open pull request for security and architectural boundary violations."`
   - _Routing:_ Strictly read-only; dispatches to `daw-review` (stage 1 specification and boundary compliance, stage 2 security audit). Workspace unaffected.

9. **Structural Coupling Analysis (`untangle`):**
   - _Prompt:_ `"Use deterministic-agentic-workflow to analyze the coupling between the payment gateway and order processor modules."`
   - _Routing:_ Strictly read-only; dispatches to `daw-untangle`. Inspects code references, dependency topology, and call chains without modifying workspace files or executing test suites. Answers _"Should these pieces change together?"_ and proposes modular boundaries and refactoring targets governed by [`references/change-coupling.md`](references/change-coupling.md). Workspace unaffected.

10. **Read-Only Consultation (`ask`):**

- _Prompt:_ `"Use deterministic-agentic-workflow to explain the database connection lifecycle and recommend connection pooling strategies."`
- _Routing:_ Strictly read-only; dispatches to `daw-ask`. Evaluates context and surfaces trade-offs on the decision frontier without modifying workspace files or drafting phantom documents. Workspace unaffected.

---

## 2. Suite Architecture & Bundled Modules

The DAW suite is self-contained as a complete 12-module bundle. It does not depend on external workflow frameworks. All 12 bundled modules in `skills/daw-*/` are core dependencies:

| Module            | Location                        | Role                                                                     |
| :---------------- | :------------------------------ | :----------------------------------------------------------------------- |
| **daw-design**    | `skills/daw-design/SKILL.md`    | System architecture, requirements authoring, 14-doc specification.       |
| **daw-plan**      | `skills/daw-plan/SKILL.md`      | Phase decomposition, task contracts, atomic task boundaries.             |
| **daw-debug**     | `skills/daw-debug/SKILL.md`     | Root cause analysis, minimal reproduction, failure diagnostics.          |
| **daw-build**     | `skills/daw-build/SKILL.md`     | Minimal code construction, surgical edits, no dead weight.               |
| **daw-review**    | `skills/daw-review/SKILL.md`    | Two-stage code review, architectural boundaries, security checks.        |
| **daw-verify**    | `skills/daw-verify/SKILL.md`    | Semantic test verification, regression proof, evidence capture.          |
| **daw-workspace** | `skills/daw-workspace/SKILL.md` | Isolated git worktree lifecycle and directory isolation.                 |
| **daw-ask**       | `skills/daw-ask/SKILL.md`       | Read-only architectural guidance & decision frontier exploration.        |
| **daw-setup**     | `skills/daw-setup/SKILL.md`     | Interactive configuration setup, tool command discovery & conventions.   |
| **daw-wizard**    | `skills/daw-wizard/SKILL.md`    | Greenfield requirements interview & initial specification authoring.     |
| **daw-untangle**  | `skills/daw-untangle/SKILL.md`  | Read-only structural analysis, change-coupling & boundary investigation. |
| **daw-ship**      | `skills/daw-ship/SKILL.md`      | Integration & delivery: commits, PRs, CI triage, review feedback, merge. |

> **Missing Module Policy:** All 12 modules are required. If any bundled module is missing from the suite, execution is blocked. The workflow does not silently fall back to shallow inline approximations. External specialist skills (such as application security auditors, database optimizers, or frontend engineers) are optional orchestrator augmentations, not mandatory bundled dependencies.

### Progressive-Disclosure Supporting Protocols

The 12 public modules are the only standalone discoverable and executable workflow units. Supporting protocols are scoped reference markdown files, not separate sub-skills, registered routes, child commands, or runtime layers:

- **Shared Grilling Protocol (`references/grilling.md`):** Canonical bounded-round elicitation protocol used by `daw-wizard`, `daw-ask`, and `daw-design`. Enforces structured question rounds, separates repo facts from user decisions, tracks the active decision dependency frontier, offers grounded recommendations rather than fabricated consensus, and halts on material blockers without demanding ceremony for trivial changes.
- **Domain Modeling Resource (`skills/daw-design/references/domain-modeling.md`):** Design-owned guidance on ubiquitous language, bounded contexts, domain invariants, and entities to deepen `blueprint.md` and related specs.
- **Builder-Readiness Gate (`skills/daw-design/references/builder-readiness.md`):** Design-owned preflight qualification ensuring requirements, interface contracts, and invariants are concrete and unblocked before handoff to `daw-plan` and `daw-build`.
- **Change Coupling & Boundary Analysis (`references/change-coupling.md`):** Canonical principles, inspection taxonomy, and boundary criteria for change coupling, hidden links, needless links, and non-destructive refactoring proposals used primarily by `daw-untangle`, as a light reference by `daw-design`, `daw-plan`, `daw-build`, and `daw-review`, and as the standard for the prefinal coupling checkpoint ([`references/change-coupling.md#prefinal-coupling-checkpoint`](references/change-coupling.md#prefinal-coupling-checkpoint)).

### Harness-Native Persistent Worker Graphs

Worker retention is session-bounded and harness-dependent:

- When the hosting agent harness supports continuing completed workers with preserved identity and conversation state, worker reuse is preferred for tasks requiring multi-round correction (retaining the builder and independent reviewer across rounds).
- Worker retention is harness-dependent and not a universal or guaranteed behavior across all agents. It is not a persistent daemon, background scheduler, or crash recovery system.
- Optional worker retention is distinct from the durable-artifact contract below: for multi-step authorized work the parent-owned progress record is **required** regardless of retention availability (see [Workflow Artifacts](references/workflow-artifacts.md)). Worker continuation itself remains optional unless explicitly required, in which case required-but-unavailable retention fails closed as `blocked`.
- If continuation is unavailable and retention is optional, use an explicit fresh-worker handoff; if delegation itself is unavailable, execute directly and report that limitation. Required retention fails closed as `blocked`. Never simulate continuity or hide worker replacement. See the [execution contract](references/operations.md#persistent-worker-graphs-harness-native) and [behavioral pilot protocol](docs/evaluation/guide.md#persistent-worker-graph-pilot).

### Saved Workflow Artifacts & Actual Phase

For multi-step authorized work, the canonical artifact contract is [Workflow Artifacts](references/workflow-artifacts.md) (spec / saved plan / parent-owned progress / mockup handoff). Tiny settled patches and factual/read-only inquiries keep the no-document path.

- **Specification before decomposition:** A proportional authoritative spec (what/why/non-goals/AC) is persisted before tactical decomposition — reuse an adequate existing spec; if clear requirements have no written source, the authorized parent records their faithful bounded what/why/non-goals/AC in the chosen spec before `daw-plan`. The planner cannot invent architecture or business choices. Acceptance criteria follow the canonical semantic guidance in [EARS](references/document-quality.md#acceptance-criteria-ears): five forms with composition allowed, observable condition/response/oracle, normal/error separation, no keyword parser as truth, no invented policies/numbers, no forced five-pattern use; Given/When/Then remains valid.
- **Saved plan before build dispatch:** The plan mapping stable requirement/AC IDs to task IDs, exact target files, dependencies, parallel ownership, expected observations/checks, evidence slots, and separate parent acceptance must be **saved** — reusing an existing roadmap/issue-export/project doc section when sufficient, otherwise defaulting to `docs/daw/plans/<workflow-id>.md`. A chat payload or native todo alone is insufficient. The artifact reference rides in existing handoff `details` without changing the outer JSON schema; there is one artifact authority — no duplicate task-tracker authority.
- **Required parent-owned progress record:** Opened at intake (default `docs/daw/workflows/<workflow-id>.md`, reusing the established project location when one exists), it names the **actual active module/stage and subphase** (not merely the planned route), active tasks, completed accepted stages, pending acceptance, spec/plan refs with scoped revisions, blockers/owner/question, `next_permitted_action`, and primary evidence refs with parent acceptance distinct from worker pass. Intake refs that do not yet exist must say explicitly **not-yet-created**, never imaginary files. The parent updates it only on real phase entry/acceptance, correction, block/resume, relevant revision change, stop, or final; workers return proposals only. See [Workflow Artifacts §3–§4](references/workflow-artifacts.md#3-required-progress-record) and [Workflow Resume & Durable Progress Checkpoint](references/operations.md#workflow-resume--durable-progress-checkpoint).
- **Rendered mockup before UI implementation:** UI-affecting work requires an actual inspectable rendered visual mockup (not prose/ASCII/wireframe-only) from settled domain/flow and existing design source before UI work — an existing matching mockup may be reused. Save the editable source or durable design reference plus a visual preview with the actual available design/export/browser capability; no vendor mandate and no external publish/account/asset actions without permission. Material missing capability blocks only the UI scope; there is no silent text fallback. Mockup acceptance is not runtime proof or automatic human approval. No UI → explicit scoped N/A. See [Workflow Artifacts §5](references/workflow-artifacts.md#5-mockup-timing-proof--na).
- **Ranked result triage:** Every completed worker result is inspected, dispositioned, and ranked by the parent before any corrective dispatch or acceptance — never automatically applied or deployed from worker pass. The compact queue (result ID, source worker, scope/revision + evidence, severity/impact, urgency justification, dependency/unblock relation, relative rank, disposition/next action, integration target + verification ref) lives in the durable plan/progress record; no new schema, stage, or scheduler. Safety/correctness/material acceptance blockers rank first, then urgency and dependency unblocking; severity stays distinct from executable order (a prerequisite may execute before a higher-impact dependent fix). See [Ranked Result Triage](references/operations.md#ranked-result-triage).

### Internal Module Handoffs vs. User-Facing Reports

DAW strictly separates internal orchestration handoffs from conversational human reporting:

- **Internal Canonical Envelope:** Module handoffs between execution stages require a full canonical JSON envelope (`objective`, `input_paths`, `output_paths`, `acceptance_criteria`, `evidence`, `status`, `handoff_to`, `details`). This payload must be delivered via structured transport (module/subagent return, harness checkpoint, or authorized artifact) and inspected by the parent orchestrator before any downstream transition. An inline fallback checkpoint is used only when no structured transport exists.
- **Default User-Facing Report:** User responses use concise natural language in the user's language, summarizing the outcome, relevant artifact paths, actually exercised checks (clearly distinguishing provided transcripts from rerun verifications), unresolved decisions and their bounded scope, and one concrete next action. Full raw JSON is omitted from normal conversational responses.
- **Explicit Machine-Readable Exception:** Raw JSON is emitted only when the user explicitly requests machine-readable or JSON output, or when operating direct CLI tools with structured output contracts (`--format json`). See [User-Facing Reports & Handoff Transport](references/routing.md#user-facing-reports--handoff-transport).

---

## 3. Finite Intent Precedence & Route Engine API

Automated routing is governed deterministically by `references/suite-manifest.json` (schema_version 1) and evaluated via `scripts/route.py`:

```bash
# Evaluate routing request against an input JSON payload
python3 scripts/route.py references/route-request.example.json

# Verify suite integrity (manifest + 12 bundled modules)
python3 scripts/route.py --check-suite
```

Optional flags include `--format text|json` for machine-readable output and `--root <suite_root>` to target a custom suite directory.

### Request Structure

Routing requires classified input facts rather than arbitrary keyword matching:

```json
{
  "schema_version": 1,
  "intent": "bugfix",
  "requirements": "clear",
  "risk": "low",
  "workspace": "in-place"
}
```

- `intent`: enum `bootstrap` | `adopt` | `feature` | `bugfix` | `patch` | `review` | `untangle` | `ask` | `setup` | `refactor` | `maintain` | `spike` | `ship`
- `requirements`: enum `clear` | `unclear` | `unknown`
- `risk`: enum `low` | `high` | `unknown`
- `workspace`: enum `in-place` | `isolated` | `unknown`

### Intent Dispatch Hierarchy

1. `ask` -> `daw-ask` (read-only, workspace unaffected)
2. `review` -> `daw-review` (read-only, workspace unaffected)
3. `setup` -> `daw-setup` (documentation-only, workspace unaffected)
4. `bootstrap` -> `daw-wizard`, `daw-design`, `daw-plan` (documentation-only)
5. `adopt` -> `daw-design`, `daw-plan` (documentation-only, preserves code)
6. `bugfix` -> `daw-debug`, `daw-plan`, `daw-build`, `daw-review`, `daw-verify` (workspace prepended if `isolated`)
7. `patch` -> `daw-build`, `daw-verify` (workspace prepended if `isolated`)
8. `feature` -> `daw-plan`, `daw-build`, `daw-review`, `daw-verify` (or starts with `daw-design` if requirements are `unclear`; workspace prepended if `isolated`)
9. `refactor` -> `daw-untangle`, `daw-plan`, `daw-build`, `daw-review`, `daw-verify` (behavior-preserving; workspace prepended if `isolated`)
10. `maintain` -> `daw-plan`, `daw-build`, `daw-review`, `daw-verify` (workspace prepended if `isolated`)
11. `spike` -> `daw-workspace`, `daw-build`, `daw-ask` (always isolated; throwaway output only)
12. `ship` -> `daw-ship` (integration-only; unknown risk -> `needs-input`, high risk -> interactive approval)

### High-Risk Gating & Preflight Rules

- **Preflight Coexistence:** Working tree is not required to be clean. The workflow respects existing uncommitted user edits and never executes destructive wipe commands (`git checkout .`, `git reset --hard`).
- **Relevant Checks Only:** Cloud credentials and external rollback targets are evaluated only for high-risk deployment or infrastructure tasks, never for local file edits.
- **Fail-Closed Approval:** High-risk mutating routes flag `interactive_approval_required: true` and `authorization_granted: false` (always false). A status of `ready` means the route is resolved, not that execution is authorized. Exact interactive operator confirmation is required at the point of risk; documents never grant authorization.
- **Parent Acceptance:** A completed worker or proposed stage `pass` does not unlock downstream stages. The parent or independent evaluator independently inspects evidence and evaluates transitions (pre-dispatch eligibility, stage result acceptance, and final workflow completion) with optional structured recording in a [parent-owned acceptance record](references/operations.md#parent-owned-acceptance-record). Small or inline tasks record acceptance decisions inline in parent plans and handoffs without mandatory JSON files. Acceptance does not grant high-risk operational authorization. This is an instructional contract, not a runtime interceptor. See the [research basis and evaluation limits](docs/evaluation/guide.md#research-basis-and-limits) and [acceptance decision evaluation](docs/evaluation/guide.md#acceptance-decision-evaluation).

### Parent Prefinal Coupling Checkpoint & Proportional Delivery

Before final delivery of any code-changing workflow, the parent orchestrator executes a proportional structural coupling and boundary check against the changed diff and adjacent interfaces/dependencies:

- **Proportional Route Coverage:**
  - `feature` and `bugfix`: Reuses current accepted `daw-review` stage structural findings without duplicate review passes if the matching scope and revision were already accepted.
  - `patch`: Retains the `build -> verify` route; the parent performs a bounded, proportional diff check without mandating an extra reviewer stage or escalating to untangle for a one-line or localized patch.
  - Documentation-only / non-code: Records an explicit inline N/A rationale within existing plan/handoff/checkpoint details (`coupling_check: N/A - documentation-only changes with no codebase structural or interface effects`).
- **Bounded Escalation to `daw-untangle`:** The parent escalates to `daw-untangle` only upon demonstrated hidden/unclear boundary impact or dependency obscurity requiring deeper source tracing. Escalation is strictly scoped to the affected area or subsystem, never an unsolicited whole-codebase scan. `daw-untangle` executes read-only analysis without workspace mutation; its output pass denotes completed structural analysis, not runtime proof.
- **Finding Disposition & Evidence Invalidation:**
  - Material correctness, security, or domain invariant findings block final acceptance.
  - Out-of-scope improvements or speculative cleanup are reported separately as non-blocking suggestions, rejecting unsolicited refactoring.
  - Authorized corrections route via existing `daw-plan`/`daw-build` workflows; any code revision invalidates prior affected review and runtime verification evidence, requiring fresh verification of the current diff before final completion.
- **Instructional Rule & Observability:** This is an instructional procedural skill rule governing agent cognitive reasoning and parent checkpoints, NOT a Stop hook, background daemon, or automated runtime interceptor. Observability uses existing plan/handoff/checkpoint records (`scope`, `revision`, `evidence`, `disposition`/`reason`) without mandatory new files or schemas. Default user-facing reporting remains concise natural language; canonical JSON envelopes are internal to orchestrator handoffs.

---

## 4. Verification & Structural Validation

The suite includes two read-only Python 3.10+ standard library diagnostic utilities, one companion generator, and one explicitly invoked execution runner. The diagnostics perform structural inspection and schema validation; they do not automatically dispatch agents, enforce runtime policies, or provide semantic proof of code correctness. The generator writes exactly one artifact and only on explicit request. The runner writes only the evidence logs and context packs it is asked for, inside the project root, and is never invoked by the diagnostics:

1. **Suite Integrity Check (`route.py --check-suite`):**
   - Validates that `references/suite-manifest.json` conforms to schema 1.
   - Verifies all 12 bundled module `SKILL.md` files exist within the suite root and prevents symlink path escapes.
   - Exits `0` on pass (`ready`), `1` on missing modules/blockers (`blocked`), `2` on malformed manifest (`error`).

2. **Package & Task Contract Validator (`validate.py`):**
   - `python3 scripts/validate.py package`: Verifies directory structure, templates, and baseline files.
   - `python3 scripts/validate.py contract <file> --stage <stage>`: Validates structured project task contracts against the phase schema (`plan`, `execute`, `complete`).
   - `python3 scripts/validate.py docs <record> --project-root <dir> --transition <edge> --documents <docs...>`: Validates documentation workflow transition eligibility across 5 lifecycle edges (`intake-authoring`, `authoring-review`, `review-ready`, `review-rework`, `rework-review`) against the [Document Quality Standards & Review Rubric](references/document-quality.md). Checks criterion coverage, SHA-256 digests, and grounded line-slice source quotes. Operates as a passive, read-only CLI check invoked explicitly by the parent orchestrator; it installs no daemons or hooks, and checks structural evidence eligibility without certifying semantic truth or human comprehension.
     Truthful verification requires inspecting observable runtime evidence (exit codes, test runner reports, diff checks) against defined Acceptance Criteria. Structural validity checks ensure the repository adheres to contract conventions; they are not substitutes for functional testing.

3. **Ledger Derivation (`derive_ledger.py`, the suite's only writer):**
   - `python3 scripts/derive_ledger.py --project-root <dir> [--write]`: projects `<spec_dir>/ledger.json` from the doc-transition records already under `docs/daw/decisions/`, `docs/specs/records/`, or `docs/daw/evidence/`, so specifications stay the only hand-authored artifact.
   - Every field is copied from a record: `state` from `transition.to`, `sha256` from the record that still matches the document's current bytes, `record` from the file itself, `history` from the rest of the transition chain. An edited document is reported as `derive_doc_unmapped` (drift) rather than silently re-pinned, and a conflicted chain is reported as `derive_doc_conflict` — `--write` refuses instead of guessing. Without `--write` it prints the ledger it would write and touches nothing.

4. **Deterministic Execution Runner (`run.py`):**
   - `python3 scripts/run.py next|context|verify|run --plan <plan> --project-root <dir>`: consumes the task list carried by a saved plan and makes three decisions mechanically — which task may run next, what bounded context a worker receives, and whether the task's verification command actually passed.
   - The task list has one hand-authored source per workflow: either one Markdown file per task (frontmatter carries the machine fields, the body carries the prose) named by a `<!-- daw-task-sources: <dir> -->` marker, or the manifest embedded directly after a `<!-- daw-task-manifest -->` marker. `derive_tasks.py` projects the task files into the plan's manifest; `validate.py tasks` reports any drift between them and refuses a plan whose two halves disagree.
   - `context` assembles a byte-bounded context pack ("smart zone") with per-file SHA-256, explicit truncation, and the task's prose brief; `verify` runs a task's prescribed command as argv without a shell and captures the exit code and output to `docs/daw/evidence/<task-id>/verify-<n>.log`; `isolate` runs one task inside its own git worktree (branch `daw/<task-id>-<slug>`, based on the local integration branch) and merges it only when that verification exited `0` at the merged commit; `run` drives the unattended loop using an operator-supplied agent command.
   - It is explicitly invoked per unit of work — never a daemon, scheduler, or background service — never pushes/merges/tags/deploys, never installs or discovers an agent command, and never grants point-of-risk authorization. A passing verification is evidence, not approval. Full contract: [Deterministic Execution Runner](references/execution-runner.md).

---

## 5. The Canonical 14 Specification Documents

The suite includes standard Markdown templates in `templates/` for the complete 14-doc specification matrix:

1. `blueprint.md` (System Architecture)
2. `brd.md` (Business Requirements)
3. `prd.md` (Product Requirements)
4. `frd.md` (Functional Requirements)
5. `erd.md` (Entity-Relationship Diagram: persistent entities, identity, sourced attributes, relationships, cardinality/optionality/ownership, integrity/lifecycle/traceability, applicable physical design)
6. `techstack.md` (Technology Stack)
7. `design.md` (Visual Design System)
8. `wireframe.md` (UI Wireframes)
9. `ui-ux.md` (Micro-interactions & UX)
10. `security.md` (Threat Modeling & Controls)
11. `roadmap.md` (Phasing & Milestones)
12. `deployment.md` (Infrastructure & Release)
13. `qa.md` (Test Strategy & Matrix)
14. `runbook.md` (Operations & Observability)

Default greenfield projects author a proportional core set (typically 6 core documents: `blueprint`, `prd`, `frd`, `techstack`, `security`, `roadmap`) plus conditional ERD when persisted entities/relationships are introduced, materially changed, or adopted without an adequate existing model (default `erd.md`; reuse an adequate existing model; otherwise `skipped`/`N/A` with a scoped reason). Non-applicable domains are marked with explicit `N/A` rationales rather than generating speculative filler. Small changes and bugfixes require minimal or zero spec edits.

### Documentation Authoring Contract & Accountability

Specification authoring is governed by the Authoritative Documentation Authoring Contract (`references/routing.md` §3):

- **Ownership by Phase:**
  - `daw-wizard` conducts requirements elicitation interviews and drafts initial proportional specifications.
  - `daw-design` is the authoritative author, custodian, and adopter across all 14 specifications.
  - `daw-plan` owns task decomposition and persists the saved plan mapping stable requirement/AC IDs to task IDs, exact target files, dependencies, parallel ownership, expected observations/checks, and evidence slots before build dispatch (reusing an existing roadmap/issue-export/project doc section when sufficient, otherwise `docs/daw/plans/<workflow-id>.md`; no forced `tasks.md` files; updates `roadmap.md` only when authorized). A chat payload alone does not satisfy the saved-plan requirement for multi-step work — see [Workflow Artifacts](references/workflow-artifacts.md).
- **Mandatory Reference Reads:** Writers must read the matching matrix entry in `references/routing.md` §3 and the canonical template in `templates/` before writing.
- **Hierarchy of Truth & Provenance:** User facts and repository files (`package.json`, source configs) outrank templates. Templates define structure, not evidence. Technical claims must cite exact paths and observed versions; missing facts become `[UNVERIFIED]` or Open Questions blocking only impacted commitments, never speculative filler.
- **Proportional Scope & External Specialists:** Never force 14 documents on routine tasks. External domain specialists (such as security auditors or database optimizers) are optional orchestrator augmentations, not mandatory recursive dependencies.

### Feature Delivery Contract & Specification-Driven Delivery

DAW incorporates specification-driven execution semantics governed by the canonical shared procedural contract in [`references/document-quality.md#feature-delivery-contract`](references/document-quality.md#feature-delivery-contract). Rather than introducing new modules or runtime daemons, these semantics are embedded directly into existing execution modules and standard document templates:

- **A. Governance & Authoring Alignment:** Authoring modules (`daw-wizard`, `daw-design`) consume real project principles and explicit source provenance, cleanly separating business what/why from technical how. Principles and architectural decisions distinguish proposed defaults from approved decisions; updating an authoritative decision syncs affected tasks and acceptance criteria without silent overrides or covert feature execution.
- **B. Clarification & Technical Uncertainty Resolution:** When requirements contain material gaps, agents first inspect repository facts to resolve discoverable context. Unresolved questions are ranked by `impact * uncertainty`. Dependent trade-offs are asked sequentially one at a time, while independent choices are batched up to 5 per round. Read-only inquiry (`daw-ask`) proposes exact updates to authoring via the parent orchestrator without file writes.
- **C. Feature Slicing & Behavioral Oracles:** Feature specifications (`prd.md`, `frd.md`) structure deliverables into prioritized, demonstrable user stories with Given/When/Then or equivalent exact input/output/error/state oracles and stable requirement IDs. Inseparable safety or transaction invariants are not artificially fragmented.
- **D. Traceability, Task Graph & Parallel Safety:** Planning decomposes work into a compact traceability mapping: `Requirement/AC ID -> Story ID -> Task ID -> Target File Paths -> Dependencies -> Exact Verification -> Current Evidence`. The `[P]` parallel execution marker is permitted only when tasks have disjoint file writes and zero shared data or runtime dependencies. Dependency cycles and unknown dependencies fail closed before dispatch.
- **E. Requirements-Quality Checklist Separation:** A reviewer-owned quality checklist evaluates prose completeness, clarity, consistency, and verifiability. This qualitative review is strictly decoupled from the builder's task completion checkboxes and empirical runtime test passes. Builders cannot self-approve reviewer rubrics, and generic user "proceed" prompts cannot waive blocking quality gates.
- **F. Prebuild Cross-Artifact Analysis:** Before writing code for feature- or spec-dependent tasks, the parent orchestrator requires an independent read-only conformity review (`daw-review` as a bounded readiness checkpoint). Reviewers compare scope, governance, requirements, design, and task graphs, reporting structured findings with ID, severity, location, consequence, and repair recommendations without declaring a completed code audit. Downstream postbuild verification preserves active route contracts: feature and bugfix routes mandate independent review, while trivial settled patch routes verify directly without requiring additional `daw-review` ceremony.
- **G. Convergence Drift Analysis & Scoped Invalidation:** Multi-round verification inspects actual code, authoritative specs, and current runtime evidence, categorizing deliverables into `implemented-verified`, `implemented-unverified`, `missing`, `contradicted`, or `blocked`. When gaps are detected, parent-authorized plan updates append genuine uncovered work within accepted scope without duplicating pending tasks or expanding scope. Modifying requirements or code invalidates affected prior evidence and review passes proportionally.
- **H. Scoped Pause/Resume & Canonical Block State:** When material decisions, missing credentials, or review blockers halt progress, the orchestrator transitions the affected scope to a canonical `blocked` state, recording the reason, owner, pending question, and permitted next action. Non-interactive execution without user response is never treated as consent. On resumption, scope, revisions, prerequisites, and authorizations are rechecked before re-dispatch.
- **I. Local Toolchain Integration & Reusable Verification:** Workflows discover and execute actual project scripts, local test commands, and linters directly from the workspace. Automated verification commands must actually execute and return observable output; simulated check logs are prohibited. Local configurations may strengthen but never weaken canonical safety or acceptance criteria.

### Adopted Flow & Enforcement Gates

The delivery flow is adopted rather than invented, and it is enforced rather than merely described. [Best Practice Flow](references/best-practice-flow.md) records the eight steps — constitution first, clarify then specify, vertical-slice plans with one-action steps, acceptance plus an exact verification command per task, small test-first diffs, independent review, run-it-to-prove-it verification, and commit/PR hygiene as its own route — each tagged with its source (`spec-kit`, `superpowers`, `pocock`) and an anchor to the DAW rule that already implements it.

Two gates keep that mapping honest:

| Gate                | Command                                                          | Fails / blocks when                                                                                                                                                                                                                                                 |
| :------------------ | :--------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Static mapping gate | `python3 scripts/validate.py flow --project-root .`              | A step, its source tag, its DAW anchor, the cross-links from `SKILL.md` / `references/routing.md`, or the manifest `flow_gate` entry is missing or inconsistent.                                                                                                    |
| Route flow gate     | `python3 scripts/route.py REQUEST.json --project-root <project>` | An affected intent (`feature`, `bugfix`, `refactor`, `maintain`) is dispatched while a required artifact step (spec, plan, plan carrying verification `expected` markers) is unsatisfied; status drops from `ready` to `blocked` with `FLOW_GATE_MISSING_ARTIFACT`. |

Both gates are read-only and advisory about authority: passing them never authorizes a mutation, a deployment, or any action beyond the operator's explicit request.

### GitHub Spec Kit Adoption Matrix

The table below summarizes the alignment between upstream GitHub Spec Kit mechanisms (pinned to commit [`3ca735b846afcbcf3304d571f296ec542464e08c`](https://github.com/github/spec-kit/tree/3ca735b846afcbcf3304d571f296ec542464e08c)) and the DAW architecture. DAW adopts all high-value specification-driven mechanisms into its existing 12-module pipeline, while intentionally excluding external daemons, rigid file naming mandates, embedded markdown scripts, and ungrounded efficacy claims:

| Upstream Spec Kit Mechanism                           | Pinned Upstream Source                                        | DAW Architecture Alignment                                                                                                     | Status & Architectural Rationale                                                                                                                                                                                                                                                                                  |
| :---------------------------------------------------- | :------------------------------------------------------------ | :----------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Governance & Principles**                           | `templates/commands/constitution.md`, `spec-driven.md`        | Consumed in `daw-wizard`, `daw-design`, and `templates/blueprint.md` / `prd.md` via Contract §A                                | **Adopted:** Project principles and governance recorded with source provenance; distinguishes proposed vs. decided; syncs affected tasks without silent overrides.                                                                                                                                                |
| **Interactive Clarification**                         | `templates/commands/clarify.md`                               | Handled via `references/grilling.md`, `skills/daw-ask/`, and `skills/daw-wizard/` via Contract §B                              | **Adopted:** Ranks questions by `impact * uncertainty`; prioritizes repo fact discovery before asking; asks 1 question at a time for dependent choices, batches up to 5 independent; read-only inquiry returns proposed updates.                                                                                  |
| **Feature Story Slicing**                             | `templates/commands/specify.md`, `spec-driven.md`             | Integrated into `templates/prd.md`, `templates/frd.md`, and `skills/daw-design/` via Contract §C                               | **Adopted:** Prioritizes independently demonstrable user stories with stable IDs and Given/When/Then oracles; explicit out-of-scope and measurable criteria.                                                                                                                                                      |
| **Traceability & Dependency Graph**                   | `templates/commands/tasks.md`                                 | Enforced in `skills/daw-plan/` and `templates/roadmap.md` via Contract §D                                                      | **Adopted:** Compact bidirectional traceability mapping (`req/AC -> story -> task -> paths -> deps -> verification -> evidence`); `[P]` marker strictly requires disjoint writes AND no shared data/runtime deps; cycle rejection.                                                                                |
| **Requirements Quality Checklist**                    | `templates/commands/checklist.md`                             | Reviewer-owned quality checklist in `skills/daw-review/` and `templates/qa.md` via Contract §E                                 | **Adopted:** Strictly separates reviewer prose quality rubric from builder task checkboxes and runtime tests; builder cannot self-approve; no generic "proceed" bypass.                                                                                                                                           |
| **Cross-Artifact Consistency Analysis**               | `templates/commands/analyze.md`                               | Independent prebuild readiness checkpoint in `skills/daw-review/` via Contract §F                                              | **Adopted:** Read-only conformity check before feature build; inspects governance, spec, design, and plan consistency; emits structured findings (ID/severity/location/consequence/repair) with explicit coverage denominators.                                                                                   |
| **Brownfield Codebase Convergence**                   | `templates/commands/converge.md`                              | Drift analysis in `skills/daw-verify/` and `skills/daw-design/` via Contract §G                                                | **Adopted:** Classifies code/contracts as implemented-verified, unverified, missing, contradicted, or blocked; appends genuine uncovered work without duplicating tasks or expanding scope; invalidates stale evidence upon contract mutation.                                                                    |
| **Scoped Pause & Resume**                             | `spec-driven.md`, `templates/commands/implement.md`           | Managed via parent orchestrator handoff states and fail-closed block contracts (§H)                                            | **Adopted:** Material missing decisions pause affected nodes as canonical `blocked`; non-interactive silence is not consent; state, revisions, and approval re-verified upon resume.                                                                                                                              |
| **Local Toolchain Integration & Template Overrides**  | `.specify/extensions.yml`, `workflows/speckit/workflow.yml`   | Discovered workspace scripts and local template overrides executed via Contract §I                                             | **Adopted with Invariant:** Reuses local workspace commands and custom templates; local overrides and custom templates may strengthen but can NEVER weaken canonical safety gates, acceptance criteria, or verification evidence requirements. Verification commands must actually execute (no simulated output). |
| **Capability-Based Risk Gating**                      | Implicit in command execution                                 | Explicitly codified in `references/operations.md` and `references/routing.md`                                                  | **Already Covered:** DAW natively classifies operations into low/medium/high/critical risk tiers with deterministic human approval gates.                                                                                                                                                                         |
| **14-Document Specification Matrix**                  | Ad-hoc markdown documents (`spec.md`, `plan.md`)              | Canonical 14-document matrix (`templates/`, incl. conditional ERD) with dual-audience review rubric                            | **Already Covered:** Comprehensive architectural, functional, security, QA, data-model, and operational specifications with formal state transitions.                                                                                                                                                             |
| **Structured Machine Handoff Envelopes**              | Implicit markdown frontmatter / conversational state          | Strict JSON handoff schema (`references/routing.md#5-canonical-module-handoff-contract`)                                       | **Already Covered:** Rigorous, observable JSON envelope emitted across all 12 module transitions, separating machine handoff from human reporting.                                                                                                                                                                |
| **Read-Only Standard Library Validation**             | Ad-hoc npm/bash scripts                                       | Native Python stdlib utilities (`scripts/validate.py` CLI, backed by `scripts/daw_common.py` and `scripts/check_*.py` modules) | **Already Covered:** Zero-dependency, portable structural linting and schema validation.                                                                                                                                                                                                                          |
| **Daemon Supervisors & Runtime Interceptors**         | Suggested background watchers / daemons                       | Intentionally omitted: DAW uses instructional agent skill execution                                                            | **Intentionally Excluded:** Violates DAW's zero-dependency portable design; agent workflows operate through prompt and tool guidance, not background daemon listeners.                                                                                                                                            |
| **Mandated Rigid Single-File Schemas**                | Hardcoded `spec.md`, `plan.md`, `tasks.md`, `constitution.md` | Proportional documentation tailored to project scale (6-doc core or inline mappings)                                           | **Intentionally Excluded:** Avoids bureaucratic file duplication; small bug fixes and patches keep mappings inline without forcing ceremonial file creation.                                                                                                                                                      |
| **Embedded Markdown Shell Script Bindings**           | Executable bash/powershell code blocks inside templates       | External stdlib utilities and discovered repository scripts                                                                    | **Intentionally Excluded:** Prevents arbitrary, uninspected command execution from markdown text; preserves clean separation between documentation and execution tools.                                                                                                                                           |
| **Automated External Git / Issue / Deploy Mutations** | Automatic branch push, PR creation, issue closing             | Strict fail-closed user authorization required for external side-effects                                                       | **Intentionally Excluded:** External environment changes, VCS mutations, and deployment actions strictly require explicit human approval.                                                                                                                                                                         |
| **Upstream Tests-Optional Default**                   | `spec-driven.md`, `templates/commands/plan.md`                | Primary verification evidence required per Contract §D, §I                                                                     | **Intentionally Excluded:** Upstream Spec Kit treats testing as optional or deferred by default; DAW strictly rejects tests-optional defaults for behavioral acceptance. Tasks require observable runtime proof against Acceptance Criteria before completion.                                                    |
| **Generic Checklist Override Default**                | `templates/commands/checklist.md`                             | Reviewer-owned quality checklist separation per Contract §E                                                                    | **Intentionally Excluded:** Upstream Spec Kit permits proceeding despite unchecked quality items or via generic user overrides; DAW strictly prohibits generic user 'proceed' prompts from bypassing blocking requirements gates or self-approving reviewer rubrics.                                              |
| **Unverified "Zero Hallucination" Claims**            | Marketing guarantees of 100% precision                        | Honest disclosure of prompt engineering limits, manual review necessity, and empirical costs                                   | **Intentionally Excluded:** LLM outputs are inherently probabilistic; contracts structure verification but cannot certify semantic correctness. Transparent honesty rules and negative control protocols in `docs/evaluation/guide.md`.                                                                           |

---

## 6. References & Documentation

- [Best Practice Flow (`references/best-practice-flow.md`)](references/best-practice-flow.md): The nine adopted delivery steps (spec-kit, superpowers, Matt Pocock) mapped to the DAW rule that implements each, with the machine mapping read by both enforcement gates.
- [Grilling Protocol (`references/grilling.md`)](references/grilling.md): Canonical bounded-round elicitation protocol used by `daw-wizard`, `daw-ask`, and `daw-design`.
- [Routing & Specification Manifest (`references/routing.md`)](references/routing.md): Detailed intent precedence, 14-doc authoring rules, and stage pipeline handoffs.
- [Developer Lifecycle (`references/developer-lifecycle.md`)](references/developer-lifecycle.md): Inner loop, time-boxing, spike, refactor, maintenance, bisection, commit hygiene, PR/CI, review feedback, release, and retro protocols.
- [Installation & Compatibility Guide (`references/installation.md`)](references/installation.md): Supported agent paths, symlink aliasing, and OS compatibility.
- [Validation & Verification Policy (`references/validation.md`)](references/validation.md): Package validation rules, structural contracts, and validation diagnostics.
- [Operations & Execution Manual (`references/operations.md`)](references/operations.md): Preflight gates, fail-closed approvals, rollback mechanics, and persistent worker graph contracts.
- [Evaluation Guide (`docs/evaluation/guide.md`)](docs/evaluation/guide.md): Reproducible task evaluations, oracle benchmarking, acceptance evaluation dimensions, research basis, and evaluation protocols.
- [Evaluation Observations (`docs/evaluation/observations.md`)](docs/evaluation/observations.md): Observed empirical probe and benchmark records, failure findings, token measurements, and execution limits.
- [Changelog & Architecture Decisions (`CHANGELOG.md`)](CHANGELOG.md): Suite design history, contract hardening, and historical notes.
- [Document Quality Standards & Review Rubric (`references/document-quality.md`)](references/document-quality.md): Canonical 14-doc quality rubric, dual human and fresh-agent reader criteria, grounded evidence rules, and workflow transition gate.
- [Canonical Feature Delivery Contract (`references/document-quality.md#feature-delivery-contract`)](references/document-quality.md#feature-delivery-contract): Canonical specification-driven procedural contract covering governance, clarification, story slicing, task traceability, prebuild readiness, convergence, and scoped pause/resume.
- [Behavioral Verification Scenarios (`tests/behavior-scenarios.md`)](tests/behavior-scenarios.md): Test scenarios and regression verification cases.
- [Parent Prefinal Coupling Checkpoint (`references/change-coupling.md#prefinal-coupling-checkpoint`)](references/change-coupling.md#prefinal-coupling-checkpoint): Proportional parent-owned structural check before final delivery, review reuse, patch proportionality, and read-only escalation rules.

---

## 7. Development & Empirical Evaluation

Run the local test suite and quality gates:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/validate.py package
python3 scripts/route.py --check-suite
```

CI configures these checks across Linux, macOS, and Windows with Python 3.10 and 3.14. A local passing run verifies package structure and route mechanics, not hosted CI matrix execution.

### Empirical Evaluation & Realistic Limits

The repository includes an opt-in evaluation harness (`tools/evaluation/evaluate.py`) that tests agent commands against isolated task fixtures without bypassing approvals or forcing paid calls.

Empirical evaluation records (detailed in [`docs/evaluation/observations.md`](docs/evaluation/observations.md)) establish that DAW does not automatically reduce token costs or guarantee canonical compliance:

- **Round 1 (3 Small CLI Tasks):** Both the baseline (no-DAW) and DAW passed all 39 functional acceptance checks (14/14, 11/11, 14/14). However, DAW used **175% more tokens** (414,659 vs. 150,868 baseline) and all 3 DAW runs failed required canonical checkpoints because the agent emitted stage narrative prose rather than structured handoffs and review gates.
- **Round 2 (Multi-Step Goal Tasks):** Execution was blocked and remains incomplete after an unmetered upstream HTTP 429 rate limit halted dispatch under the frozen protocol.

DAW makes no claim of universal cost reduction or turnkey quality improvement. Explicit multi-stage planning and verification introduce significant token overhead. Achieving structured handoff compliance requires deliberate harness integration and verification, not merely loading skill instructions.

---

The suite follows the [Agent Skills format](https://agentskills.io/specification). Directory layouts and symlink discovery rules are detailed in [installation and compatibility](references/installation.md).

Licensed under the [MIT License](LICENSE). See [VERSION](VERSION) for the current package version.
