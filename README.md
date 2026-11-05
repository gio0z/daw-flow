# Deterministic Agentic Workflow (DAW) Suite

A portable planning, execution, and verification suite for AI coding agents. Python 3.10+, no third-party runtime dependencies, MIT licensed.

> **"Otaknya boleh generative, tangannya harus deterministic."**
> _(Generative cognitive reasoning for context and planning; deterministic execution and verification for system state)._

Based on the architectural principles articulated in Rama Digital's [_Agentic Tapi Deterministic Workflow AI Agent_](https://ramadigital.id/blog/agentic-tapi-deterministic-workflow-ai-agent), this package provides a self-contained engineering workflow suite combining root router dispatch, an explicit 10-module execution architecture (`skills/daw-*/`), the canonical 13-document specification matrix, capability-based risk gating, and verifiable evidence proof gates.

> **Instructional Contract & Scope Notice:** This suite provides instructional workflow guidance for coding agents. It directs execution across 10 bundled modules (`skills/daw-*/`). It does not install daemon supervisors, background services, runtime interceptors, or automated enforcement mechanisms. Route evaluation (`scripts/route.py`) and package validation (`scripts/validate.py`) are read-only structural checks, not automated dispatchers or semantic proofs of correctness. Deterministic scripts and specifications do not guarantee semantic success; truthful verification requires inspecting observable runtime evidence against Acceptance Criteria.

---

## 1. Quickstart & Invocation

Clone or download the complete repository, then install it into your agent's user skill directory:

```bash
git clone https://github.com/gio0z/deterministic-agentic-workflow.git
cd deterministic-agentic-workflow
python3 scripts/install.py install --agent codex --scope user
```

Choose `codex`, `claude`, `gemini`, `cursor`, or `copilot`. For a project installation, use `--scope project --project-root /path/to/project`. On Windows, use `python` if that is your Python 3 command. If directory symlinks are unavailable, add `--no-aliases`; the complete root skill still loads its bundled modules by path.

Restart or reload skills in your agent, then ask:

```text
Use deterministic-agentic-workflow to fix this bug and verify the result.
```

Codex also supports `$deterministic-agentic-workflow`; Claude Code exposes `/deterministic-agentic-workflow`. Other clients provide their own skill menus and invocation syntax. Native discovery depends on client version and settings.

Inspect, update from a refreshed checkout, or remove the same installation:

```bash
python3 scripts/install.py status --agent codex --scope user
python3 scripts/install.py install --agent codex --scope user --update
python3 scripts/install.py uninstall --agent codex --scope user
```

`--dry-run` previews an action without writing. Updates and removal refuse changed files, extra files, and unrelated skills. The installer copies the full suite, so removing the source checkout does not break it. It never modifies agent configuration or Git hooks, downloads packages, or installs agent CLIs.

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

9. **Read-Only Consultation (`ask`):**
   - _Prompt:_ `"Use deterministic-agentic-workflow to explain the database connection lifecycle and recommend connection pooling strategies."`
   - _Routing:_ Strictly read-only; dispatches to `daw-ask`. Evaluates context and surfaces trade-offs on the decision frontier without modifying workspace files or drafting phantom documents. Workspace unaffected.

---

## 2. Suite Architecture & Bundled Modules

The DAW suite is self-contained as a complete 10-module bundle. It does not depend on external workflow frameworks. All 10 bundled modules in `skills/daw-*/` are core dependencies:

| Module            | Location                        | Role                                                                   |
| :---------------- | :------------------------------ | :--------------------------------------------------------------------- |
| **daw-design**    | `skills/daw-design/SKILL.md`    | System architecture, requirements authoring, 13-doc specification.     |
| **daw-plan**      | `skills/daw-plan/SKILL.md`      | Phase decomposition, task contracts, atomic task boundaries.           |
| **daw-debug**     | `skills/daw-debug/SKILL.md`     | Root cause analysis, minimal reproduction, failure diagnostics.        |
| **daw-build**     | `skills/daw-build/SKILL.md`     | Minimal code construction, surgical edits, no dead weight.             |
| **daw-review**    | `skills/daw-review/SKILL.md`    | Two-stage code review, architectural boundaries, security checks.      |
| **daw-verify**    | `skills/daw-verify/SKILL.md`    | Semantic test verification, regression proof, evidence capture.        |
| **daw-workspace** | `skills/daw-workspace/SKILL.md` | Isolated git worktree lifecycle and directory isolation.               |
| **daw-ask**       | `skills/daw-ask/SKILL.md`       | Read-only architectural guidance & decision frontier exploration.      |
| **daw-setup**     | `skills/daw-setup/SKILL.md`     | Interactive configuration setup, tool command discovery & conventions. |
| **daw-wizard**    | `skills/daw-wizard/SKILL.md`    | Greenfield requirements interview & initial specification authoring.   |

> **Missing Module Policy:** All 10 modules are required. If any bundled module is missing from the suite, execution is blocked. The workflow does not silently fall back to shallow inline approximations. External specialist skills (such as application security auditors, database optimizers, or frontend engineers) are optional orchestrator augmentations, not mandatory bundled dependencies.

### Progressive-Disclosure Supporting Protocols

The 10 public modules are the only standalone discoverable and executable workflow units. Supporting protocols are scoped reference markdown files, not separate sub-skills, registered routes, child commands, or runtime layers:

- **Shared Grilling Protocol (`references/grilling.md`):** Canonical bounded-round elicitation protocol used by `daw-wizard`, `daw-ask`, and `daw-design`. Enforces structured question rounds, separates repo facts from user decisions, tracks the active decision dependency frontier, offers grounded recommendations rather than fabricated consensus, and halts on material blockers without demanding ceremony for trivial changes.
- **Domain Modeling Resource (`skills/daw-design/references/domain-modeling.md`):** Design-owned guidance on ubiquitous language, bounded contexts, domain invariants, and entities to deepen `blueprint.md` and related specs.
- **Builder-Readiness Gate (`skills/daw-design/references/builder-readiness.md`):** Design-owned preflight qualification ensuring requirements, interface contracts, and invariants are concrete and unblocked before handoff to `daw-plan` and `daw-build`.

### Harness-Native Persistent Worker Graphs

Worker retention is session-bounded and harness-dependent:

- When the hosting agent harness supports continuing completed workers with preserved identity and conversation state, worker reuse is preferred for tasks requiring multi-round correction (retaining the builder and independent reviewer across rounds).
- Worker retention is harness-dependent and not a universal or guaranteed behavior across all agents. It is not a persistent daemon, background scheduler, or crash recovery system.
- If continuation is unavailable and retention is optional, use an explicit fresh-worker handoff; if delegation itself is unavailable, execute directly and report that limitation. Required retention fails closed as `blocked`. Never simulate continuity or hide worker replacement. See the [execution contract](references/operations.md#persistent-worker-graphs-harness-native) and [behavioral pilot protocol](references/evaluation.md#persistent-worker-graph-pilot).

---

## 3. Finite Intent Precedence & Route Engine API

Automated routing is governed deterministically by `references/suite-manifest.json` (schema_version 1) and evaluated via `scripts/route.py`:

```bash
# Evaluate routing request against an input JSON payload
python3 scripts/route.py references/route-request.example.json

# Verify suite integrity (manifest + 10 bundled modules)
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

- `intent`: enum `bootstrap` | `adopt` | `feature` | `bugfix` | `patch` | `review` | `ask` | `setup`
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

### High-Risk Gating & Preflight Rules

- **Preflight Coexistence:** Working tree is not required to be clean. The workflow respects existing uncommitted user edits and never executes destructive wipe commands (`git checkout .`, `git reset --hard`).
- **Relevant Checks Only:** Cloud credentials and external rollback targets are evaluated only for high-risk deployment or infrastructure tasks, never for local file edits.
- **Fail-Closed Approval:** High-risk mutating routes flag `interactive_approval_required: true` and `authorization_granted: false` (always false). A status of `ready` means the route is resolved, not that execution is authorized. Exact interactive operator confirmation is required at the point of risk; documents never grant authorization.
- **Parent Acceptance:** A completed worker or proposed stage `pass` does not unlock downstream stages. The parent or independent evaluator independently inspects evidence and evaluates transitions (pre-dispatch eligibility, stage result acceptance, and final workflow completion) with optional structured recording in a [parent-owned acceptance record](references/operations.md#parent-owned-acceptance-record). Small or inline tasks record acceptance decisions inline in parent plans and handoffs without mandatory JSON files. Acceptance does not grant high-risk operational authorization. This is an instructional contract, not a runtime interceptor. See the [research basis and evaluation limits](references/evaluation.md#research-basis-and-limits) and [acceptance decision evaluation](references/evaluation.md#acceptance-decision-evaluation).

---

## 4. Verification & Structural Validation

The suite includes two read-only Python 3.10+ standard library diagnostic utilities. These scripts perform structural inspection and schema validation; they do not automatically dispatch agents, enforce runtime policies, or provide semantic proof of code correctness:

1. **Suite Integrity Check (`route.py --check-suite`):**
   - Validates that `references/suite-manifest.json` conforms to schema 1.
   - Verifies all 10 bundled module `SKILL.md` files exist within the suite root and prevents symlink path escapes.
   - Exits `0` on pass (`ready`), `1` on missing modules/blockers (`blocked`), `2` on malformed manifest (`error`).

2. **Package & Task Contract Validator (`validate.py`):**
   - `python3 scripts/validate.py package`: Verifies directory structure, templates, and baseline files.
   - `python3 scripts/validate.py contract <file> --stage <stage>`: Validates structured project task contracts against the phase schema (`plan`, `execute`, `complete`).
   - `python3 scripts/validate.py docs <record> --project-root <dir> --transition <edge> --documents <docs...>`: Validates documentation workflow transition eligibility across 5 lifecycle edges (`intake-authoring`, `authoring-review`, `review-ready`, `review-rework`, `rework-review`) against the [Document Quality Standards & Review Rubric](references/document-quality.md). Checks criterion coverage, SHA-256 digests, and grounded line-slice source quotes. Operates as a passive, read-only CLI check invoked explicitly by the parent orchestrator; it installs no daemons or hooks, and checks structural evidence eligibility without certifying semantic truth or human comprehension.
     Truthful verification requires inspecting observable runtime evidence (exit codes, test runner reports, diff checks) against defined Acceptance Criteria. Structural validity checks ensure the repository adheres to contract conventions; they are not substitutes for functional testing.

---

## 5. The Canonical 13 Specification Documents

The suite includes standard Markdown templates in `templates/` for the complete 13-doc specification matrix:

1. `blueprint.md` (System Architecture)
2. `brd.md` (Business Requirements)
3. `prd.md` (Product Requirements)
4. `frd.md` (Functional Requirements)
5. `techstack.md` (Technology Stack)
6. `design.md` (Visual Design System)
7. `wireframe.md` (UI Wireframes)
8. `ui-ux.md` (Micro-interactions & UX)
9. `security.md` (Threat Modeling & Controls)
10. `roadmap.md` (Phasing & Milestones)
11. `deployment.md` (Infrastructure & Release)
12. `qa.md` (Test Strategy & Matrix)
13. `runbook.md` (Operations & Observability)

Default greenfield projects author a proportional core set (typically 6 core documents: `blueprint`, `prd`, `frd`, `techstack`, `security`, `roadmap`). Non-applicable domains are marked with explicit `N/A` rationales rather than generating speculative filler. Small changes and bugfixes require minimal or zero spec edits.

### Documentation Authoring Contract & Accountability

Specification authoring is governed by the Authoritative Documentation Authoring Contract (`references/routing.md` §3):

- **Ownership by Phase:**
  - `daw-wizard` conducts requirements elicitation interviews and drafts initial proportional specifications.
  - `daw-design` is the authoritative author, custodian, and adopter across all 13 specifications.
  - `daw-plan` owns task decomposition and returns plans in the stage payload (no forced `tasks.md` files; updates `roadmap.md` only when authorized).
- **Mandatory Reference Reads:** Writers must read the matching matrix entry in `references/routing.md` §3 and the canonical template in `templates/` before writing.
- **Hierarchy of Truth & Provenance:** User facts and repository files (`package.json`, source configs) outrank templates. Templates define structure, not evidence. Technical claims must cite exact paths and observed versions; missing facts become `[UNVERIFIED]` or Open Questions blocking only impacted commitments, never speculative filler.
- **Proportional Scope & External Specialists:** Never force 13 documents on routine tasks. External domain specialists (such as security auditors or database optimizers) are optional orchestrator augmentations, not mandatory recursive dependencies.

---

## 6. References & Documentation

- [Grilling Protocol (`references/grilling.md`)](references/grilling.md): Canonical bounded-round elicitation protocol used by `daw-wizard`, `daw-ask`, and `daw-design`.
- [Routing & Specification Manifest (`references/routing.md`)](references/routing.md): Detailed intent precedence, 13-doc authoring rules, and stage pipeline handoffs.
- [Installation & Compatibility Guide (`references/installation.md`)](references/installation.md): Supported agent paths, symlink aliasing, and OS compatibility.
- [Validation & Verification Policy (`references/validation.md`)](references/validation.md): Package validation rules, structural contracts, and validation diagnostics.
- [Operations & Execution Manual (`references/operations.md`)](references/operations.md): Preflight gates, fail-closed approvals, rollback mechanics, and persistent worker graph contracts.
- [Evaluation Harness & Benchmark Guide (`references/evaluation.md`)](references/evaluation.md): Reproducible task evaluations, oracle benchmarking, acceptance evaluation dimensions, and empirical baseline findings.
- [Changelog & Architecture Decisions (`references/changes.md`)](references/changes.md): Suite design history, contract hardening, and historical notes.
- [Document Quality Standards & Review Rubric (`references/document-quality.md`)](references/document-quality.md): Canonical 13-doc quality rubric, dual human and fresh-agent reader criteria, grounded evidence rules, and workflow transition gate.
- [Behavioral Verification Scenarios (`tests/behavior-scenarios.md`)](tests/behavior-scenarios.md): Test scenarios and regression verification cases.

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

The suite includes an opt-in evaluation harness (`scripts/evaluate.py`) that tests agent commands against isolated task fixtures without bypassing approvals or forcing paid calls.

Empirical evaluation records (detailed in [`references/evaluation.md`](references/evaluation.md)) establish that DAW does not automatically reduce token costs or guarantee canonical compliance:

- **Round 1 (3 Small CLI Tasks):** Both the baseline (no-DAW) and DAW passed all 39 functional acceptance checks (14/14, 11/11, 14/14). However, DAW used **175% more tokens** (414,659 vs. 150,868 baseline) and all 3 DAW runs failed required canonical checkpoints because the agent emitted stage narrative prose rather than structured handoffs and review gates.
- **Round 2 (Multi-Step Goal Tasks):** Execution was blocked and remains incomplete after an unmetered upstream HTTP 429 rate limit halted dispatch under the frozen protocol.

DAW makes no claim of universal cost reduction or turnkey quality improvement. Explicit multi-stage planning and verification introduce significant token overhead. Achieving structured handoff compliance requires deliberate harness integration and verification, not merely loading skill instructions.

---

The suite follows the [Agent Skills format](https://agentskills.io/specification). Directory layouts and symlink discovery rules are detailed in [installation and compatibility](references/installation.md).

Licensed under the [MIT License](LICENSE). See [VERSION](VERSION) for the current package version.
