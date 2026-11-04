# Deterministic Agentic Workflow (DAW) Suite

A portable planning, execution, and verification suite for AI coding agents. Python 3.10+, no third-party runtime dependencies, MIT licensed.

> **"Otaknya boleh generative, tangannya harus deterministic."**  
> _(Generative cognitive reasoning for context and planning; deterministic execution and verification for system state)._

Based on the architectural principles articulated in Rama Digital's [_Agentic Tapi Deterministic Workflow AI Agent_](https://ramadigital.id/blog/agentic-tapi-deterministic-workflow-ai-agent), this package provides a comprehensive, self-contained engineering workflow suite combining root router dispatch, an explicit 10-module execution architecture (`skills/daw-*/`), the canonical 13-document specification matrix, capability-based risk gating, and verifiable evidence proof gates.

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
   - _Behavior:_ The agent immediately inspects the target directory (`cwd`).
     - If existing code or specs are found -> enters **Adopt** mode (suggests **Setup** first if no `## DAW Configuration` block exists).
     - If the target directory is empty and a brief is provided -> enters **Bootstrap** mode (starts with `daw-wizard` interview).
     - If the target directory is empty and **no brief** is provided -> starts `daw-wizard` interview phase 1; the wizard's phase 1 round acts as the material question round to establish project concept, scope, and target users. It halts blocked on unanswered material questions and **never invents phantom product documents**.

2. **Interactive Configuration Setup:**
   - _Prompt:_ `"Use deterministic-agentic-workflow to set up DAW conventions for this repo."`
   - _Routing:_ Dispatches to `daw-setup`. Explores existing project context (`git remote`, context files, test/lint/build runners, CI workflows, spec directory), confirms settings with the user, and writes/updates `<!-- daw-config:start -->` in `AGENTS.md` (or `CLAUDE.md`).

3. **Greenfield Wizard & Bootstrap:**
   - _Prompt:_ `"Use deterministic-agentic-workflow to build a real-time multiplayer whiteboard web app from scratch."`
   - _Routing:_ Dispatches to `daw-wizard` -> `daw-design` -> `daw-plan` (documentation-only). Conducts a structured interactive interview across problem concept, scope, system components, tech stack, and ops/roadmap, authoring initial specifications into `docs/specs/`.

4. **Bugfix (Diagnose, Plan, Build, Review, Verify):**
   - _Prompt:_ `"Use deterministic-agentic-workflow to fix the null pointer exception when parsing JSON payloads in auth controller."`
   - _Routing:_ Dispatches through `daw-debug` (reproduce & RCA) -> `daw-plan` (patch plan) -> `daw-build` (minimal diff) -> `daw-review` (security & boundary audit) -> `daw-verify` (failing-to-passing test evidence). Prepends `daw-workspace` if isolated workspace is requested.

5. **Feature (Plan, Build, Review, Verify):**
   - _Prompt:_ `"Use deterministic-agentic-workflow to add a rate-limiting middleware to the payment service."`
   - _Routing:_ If requirements are clear, dispatches to `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify`. If requirements are unclear, routes first to `daw-design` for specification authoring. Prepends `daw-workspace` if isolated workspace is requested.

6. **Read-Only Consultation / Ask:**
   - _Prompt:_ `"Use deterministic-agentic-workflow to explain the database connection lifecycle and recommend connection pooling strategies."`
   - _Routing:_ Strictly read-only; dispatches to `daw-ask`. Evaluates context and surfaces trade-offs on the decision frontier without modifying workspace files or drafting phantom documents. Ignores risk and workspace preferences.

7. **Greenfield Bootstrap (New Project Specification):**
   - _Prompt:_ `"Use deterministic-agentic-workflow to bootstrap specifications for a multi-tenant metrics ingestion engine in Go."`
   - _Routing:_ Dispatches to `daw-design` -> `daw-plan` (documentation-only). Selects proportional specification templates from `templates/` and generates initial architecture documents.

8. **Codebase Adoption (Reverse-Engineering & Spec Alignment):**
   - _Prompt:_ `"Use deterministic-agentic-workflow to document this existing repository and identify missing specification coverage."`
   - _Routing:_ Dispatches to `daw-design` -> `daw-plan` (documentation-only). Analyzes existing code and creates specs without modifying application source code.

---

## 2. Suite Architecture & Bundled Modules

The DAW suite is **self-contained as a complete 10-module bundle**. It does not depend on external workflow frameworks (like Superpowers or external registries). However, all 10 bundled internal execution modules are **mandatory core dependencies** for complete suite execution:

### Progressive-Disclosure Supporting Protocols

The 10 public modules remain the only standalone discoverable and executable workflow units. Supporting protocols are scoped reference resources (`.md`), **not** separate sub-skills, registered routes, child commands, or runtime layers:

- **Shared Grilling Protocol (`references/grilling.md`):** A canonical bounded-round elicitation protocol used by `daw-wizard`, `daw-ask`, and `daw-design`. It enforces structured question rounds, distinguishes agent-researched repo facts from user decisions, tracks the active decision dependency frontier, offers grounded recommendations rather than fabricated consensus, and halts on material blockers without demanding ceremony for direct questions or minor changes.
- **Domain Modeling Resource (`skills/daw-design/references/domain-modeling.md`):** Design-owned guidance on ubiquitous language, bounded contexts, domain invariants, and entities to deepen `blueprint.md` and related specs.
- **Builder-Readiness Gate (`skills/daw-design/references/builder-readiness.md`):** Design-owned preflight qualification ensuring requirements, interface contracts, and invariants are concrete and unblocked before handing off to `daw-plan` and `daw-build`.

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

> **Missing Module Policy:** All 10 modules are strictly required. If any required internal module is missing from the suite, execution is **blocked**. The workflow does not silently fall back to shallow inline approximations. External specialist skills remain optional domain augmentations.

### Harness-Native Persistent Worker Graphs

Worker reuse is automatic for tasks that already need delegated corrective rounds when
the harness supports completed-worker continuation, unless you opt out. No special
keyword or setup invocation is needed; small direct tasks stay direct. The same builder
and independent reviewer are retained across corrective rounds. DAW defines graph
dependencies, revision-scoped evidence, and stop/replan rules; the harness supplies worker
lifecycle and execution. Worker retention is session-bounded, not a durable scheduler or
automatic crash recovery. Unsupported retention is reported explicitly, never simulated
by silently replacing workers. See the [execution contract](references/operations.md#persistent-worker-graphs-harness-native)
and [behavioral pilot protocol](references/evaluation.md#persistent-worker-graph-pilot).

---

## 3. Finite Intent Precedence & Route Engine API

Automated routing is governed deterministically by `references/suite-manifest.json` (schema_version 1) and evaluated via `scripts/route.py`:

```bash
# Evaluate routing request
python3 scripts/route.py request.json [--format text|json] [--root SUITE_ROOT]

# Verify suite integrity (manifest + 10 bundled modules)
python3 scripts/route.py --check-suite [--format text|json] [--root SUITE_ROOT]
```

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
- **Relevant Checks Only:** Cloud credentials and external rollback targets are validated only for high-risk infrastructure/deployment actions, never for routine local edits or documentation.
- **Fail-Closed Approval:** High-risk tasks flag `interactive_approval_required: true` and `authorization_granted: false` (always false). A status of `ready` indicates the route plan is ready, NOT that mutating execution is pre-authorized. Exact interactive confirmation is required at the point of risk; structural references do not grant operational authorization. Unknown risk or scope blocks execution prior to mutation.
- **Direct Module Governance:** Direct discovery or invocation of child modules (`skills/daw-*/SKILL.md`) executes the Governance Loader Sequence (loading root §4/§6, `references/routing.md` §5, and pre-mutation operations checks) rather than bypassing governance.
- **Canonical Module Handoff:** All modules produce a standardized JSON envelope (`objective`, `input_paths`, `output_paths`, `acceptance_criteria`, `evidence`, `status`, `handoff_to`, `details`). Status is stage-scoped (`pass` verifies only the current phase criteria, never end-to-end completion).

## 4. Verification & Structural Validation

The suite includes two read-only Python 3.10+ standard library diagnostic utilities:

1. **Suite Integrity Check (`route.py --check-suite`):**
   - Validates that `references/suite-manifest.json` conforms to schema 1.
   - Verifies all 10 bundled module `SKILL.md` files exist within the suite root and prevents symlink path escapes.
   - Exits `0` on pass (`ready`), `1` on missing modules/blockers (`blocked`), `2` on malformed manifest (`error`).

2. **Package & Task Contract Validator (`validate.py`):**
   - `python3 scripts/validate.py package`: Verifies directory structure, templates, and baseline files.
   - `python3 scripts/validate.py contract <file> --stage <stage>`: Validates structured project task contracts against the phase schema (`plan`, `execute`, `complete`).

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

Default greenfield projects author the 6-doc core set (`blueprint`, `prd`, `frd`, `techstack`, `security`, `roadmap`). Non-applicable domains are marked with explicit `N/A` rationales.

### Documentation Authoring Contract & Accountability

Specification authoring is governed by the Authoritative Documentation Authoring Contract (`references/routing.md` §3):

- **Ownership by Phase:** `daw-wizard` conducts interviews and drafts proportional bootstrap specs; `daw-design` is the authoritative author, custodian, and adopter across all 13 specs; `daw-plan` owns task decomposition and returns plans in the stage payload (no forced `tasks.md` files; updates `roadmap.md` only when authorized).
- **Mandatory Reference Reads:** Writers must read the matching matrix entry in `references/routing.md` §3 and the canonical template in `templates/` before writing.
- **Hierarchy of Truth & Provenance:** User facts and repository files (`package.json`, source configs) outrank templates. Templates define structure, not evidence. Technical claims must cite exact paths and observed versions; missing facts become `[UNVERIFIED]` or Open Questions blocking only impacted commitments, never speculative filler.
- **No Forced 13 Documents:** Small changes require zero or minimal spec updates; specialists are optional orchestrator augmentations, not recursive dependencies.

---

## 6. References & Documentation Links

- **`references/grilling.md`**: Canonical shared grilling and elicitation protocol (bounded rounds, decision frontier, fact vs. decision separation).
- **`references/routing.md`**: Complete routing policy, intent precedence, handoff schemas, and manifest specifications.
- **`references/installation.md`**: Distribution models, nested bundle layout, and portable sibling symlink discovery.
- **`references/validation.md`**: Detailed validator contracts for `route.py --check-suite` and `validate.py`.
- **`references/operations.md`**: Preflight safety, fail-closed approvals, rollback, verification/audit rules, and the harness-native persistent worker graph contract.
- **`references/evaluation.md`**: Reproducible task evaluation, the wizard benchmark, the manual persistent worker graph pilot, and supporting protocol evaluation guidance.
- **`references/changes.md`**: Suite change history and architecture evolution log.
- **`tests/behavior-scenarios.md`**: Reusable behavior test scenarios for verifying agent compliance.

---

## 7. Development & Behavioral Evaluation

Run the local quality gate:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/validate.py package
python3 scripts/route.py --check-suite
```

CI configures these checks across Linux, macOS, and Windows with Python 3.10 and 3.14. A local passing run does not imply that the hosted matrix has run.

The [behavioral evaluation runner](references/evaluation.md) executes an explicitly supplied agent command against fresh fixtures, retains transcripts and timing, and supports repeated comparisons with and without a workspace-local skill. It does not select a model, disable approvals, or treat harness tests as evidence of agent quality. Review the retained evidence and any ungraded criteria before claiming workflow compliance.

The suite follows the [Agent Skills format](https://agentskills.io/specification). Its supported directory layouts are documented in the installation guide; cross-client behavioral parity requires actual client runs.

Licensed under the [MIT License](LICENSE). See [VERSION](VERSION) for the current package version.
