# Deterministic Agentic Workflow (DAW) Suite

A portable, document-driven planning, execution, and verification suite for AI coding agents.

> **"Otaknya boleh generative, tangannya harus deterministic."**  
> _(Generative cognitive reasoning for context and planning; deterministic execution and verification for system state)._

Based on the architectural principles articulated in Rama Digital's [_Agentic Tapi Deterministic Workflow AI Agent_](https://ramadigital.id/blog/agentic-tapi-deterministic-workflow-ai-agent), this package provides a comprehensive, self-contained engineering workflow suite combining root router dispatch, an explicit 8-module execution architecture (`skills/daw-*/`), the canonical 13-document specification matrix, capability-based risk gating, and verifiable evidence proof gates.

---

## 1. Quickstart & Invocation

Invoke the workflow using natural conversational prompts across any agent harness or via client skill mentions (e.g. `@deterministic-agentic-workflow`).

### Common Invocations & Routing Behavior

1. **Explicit Bare Invocation (Inspect & Resolve):**
   - _Prompt:_ `"Use deterministic-agentic-workflow"`
   - _Behavior:_ The agent immediately inspects the target directory (`cwd`).
     - If existing code or specs are found -> enters **Adopt** mode.
     - If the target directory is empty and a brief is provided -> enters **Bootstrap** mode.
     - If the target directory is empty and **no brief** is provided -> halts and asks **ONE concrete material question** to establish requirements. It never fabricates phantom product documents.

2. **Bugfix (Diagnose, Plan, Build, Review, Verify):**
   - _Prompt:_ `"Use deterministic-agentic-workflow to fix the null pointer exception when parsing JSON payloads in auth controller."`
   - _Routing:_ Dispatches through `daw-debug` (reproduce & RCA) -> `daw-plan` (patch plan) -> `daw-build` (minimal diff) -> `daw-review` (security & boundary audit) -> `daw-verify` (failing-to-passing test evidence). Prepends `daw-workspace` if isolated workspace is requested.

3. **Feature (Plan, Build, Review, Verify):**
   - _Prompt:_ `"Use deterministic-agentic-workflow to add a rate-limiting middleware to the payment service."`
   - _Routing:_ If requirements are clear, dispatches to `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify`. If requirements are unclear, routes first to `daw-design` for specification authoring. Prepends `daw-workspace` if isolated workspace is requested.

4. **Read-Only Consultation / Ask:**
   - _Prompt:_ `"Use deterministic-agentic-workflow to explain the database connection lifecycle and recommend connection pooling strategies."`
   - _Routing:_ Strictly read-only; dispatches to `daw-ask`. Evaluates context and surfaces trade-offs on the decision frontier without modifying workspace files or drafting phantom documents. Ignores risk and workspace preferences.

5. **Greenfield Bootstrap (New Project Specification):**
   - _Prompt:_ `"Use deterministic-agentic-workflow to bootstrap specifications for a multi-tenant metrics ingestion engine in Go."`
   - _Routing:_ Dispatches to `daw-design` -> `daw-plan` (documentation-only). Selects proportional specification templates from `templates/` and generates initial architecture documents.

6. **Codebase Adoption (Reverse-Engineering & Spec Alignment):**
   - _Prompt:_ `"Use deterministic-agentic-workflow to document this existing repository and identify missing specification coverage."`
   - _Routing:_ Dispatches to `daw-design` -> `daw-plan` (documentation-only). Analyzes existing code and creates specs without modifying application source code.

---

## 2. Suite Architecture & Bundled Modules

The DAW suite is **self-contained as a complete 8-module bundle**. It does not depend on external workflow frameworks (like Superpowers or external registries). However, all 8 bundled internal execution modules are **mandatory core dependencies** for complete suite execution:

| Module            | Location                        | Role                                                                  |
| :---------------- | :------------------------------ | :-------------------------------------------------------------------- |
| **daw-design**    | `skills/daw-design/SKILL.md`    | Specification authoring, technical requirements, 13-doc matrix.       |
| **daw-plan**      | `skills/daw-plan/SKILL.md`      | Task decomposition, execution sequencing, task contracts, risk flags. |
| **daw-debug**     | `skills/daw-debug/SKILL.md`     | Root cause analysis, minimal reproduction, failure diagnostics.       |
| **daw-build**     | `skills/daw-build/SKILL.md`     | Minimal code construction, surgical edits, no dead weight.            |
| **daw-review**    | `skills/daw-review/SKILL.md`    | Two-stage code review, architectural boundaries, security checks.     |
| **daw-verify**    | `skills/daw-verify/SKILL.md`    | Semantic test verification, regression proof, evidence capture.       |
| **daw-workspace** | `skills/daw-workspace/SKILL.md` | Isolated git worktree lifecycle and directory isolation.              |
| **daw-ask**       | `skills/daw-ask/SKILL.md`       | Read-only architecture advisory, contextual trade-offs, Q&A.          |

> **Missing Module Policy:** All 8 modules are strictly required. If any required internal module is missing from the suite, execution is **blocked**. The workflow does not silently fall back to shallow inline approximations. External specialist skills remain optional domain augmentations.

---

## 3. Finite Intent Precedence & Route Engine API

Automated routing is governed deterministically by `references/suite-manifest.json` (schema_version 1) and evaluated via `scripts/route.py`:

```bash
# Evaluate routing request
python3 scripts/route.py request.json [--format text|json] [--root SUITE_ROOT]

# Verify suite integrity (manifest + 8 bundled modules)
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

- `intent`: enum `bootstrap` | `adopt` | `feature` | `bugfix` | `patch` | `review` | `ask`
- `requirements`: enum `clear` | `unclear` | `unknown`
- `risk`: enum `low` | `high` | `unknown`
- `workspace`: enum `in-place` | `isolated` | `unknown`

### Intent Dispatch Hierarchy

1. `ask` -> `daw-ask` (read-only, workspace unaffected)
2. `review` -> `daw-review` (read-only, workspace unaffected)
3. `bootstrap` -> `daw-design`, `daw-plan` (documentation-only)
4. `adopt` -> `daw-design`, `daw-plan` (documentation-only, preserves code)
5. `bugfix` -> `daw-debug`, `daw-plan`, `daw-build`, `daw-review`, `daw-verify` (workspace prepended if `isolated`)
6. `patch` -> `daw-build`, `daw-verify` (workspace prepended if `isolated`)
7. `feature` -> `daw-plan`, `daw-build`, `daw-review`, `daw-verify` (or starts with `daw-design` if requirements are `unclear`; workspace prepended if `isolated`)

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
   - Verifies all 8 bundled module `SKILL.md` files exist within the suite root and prevents symlink path escapes.
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

---

## 6. References & Documentation Links

- **`references/routing.md`**: Complete routing policy, intent precedence, handoff schemas, and manifest specifications.
- **`references/installation.md`**: Distribution models, nested bundle layout, and portable sibling symlink discovery.
- **`references/validation.md`**: Detailed validator contracts for `route.py --check-suite` and `validate.py`.
- **`references/changes.md`**: Suite change history and architecture evolution log.
- **`tests/behavior-scenarios.md`**: Reusable behavior test scenarios for verifying agent compliance.
