---
name: deterministic-agentic-workflow
description: "Use to route multi-step engineering tasks, bootstrap greenfield specifications, adopt documentation for existing codebases, or govern execution across the bundled DAW suite: provides router dispatch across 8 specialized execution modules (daw-design, daw-plan, daw-debug, daw-build, daw-review, daw-verify, daw-workspace, daw-ask), document-driven planning across the 13-doc specification matrix, capability routing, preflight checks, fail-closed risk gating, and verifiable evidence gates."
compatibility: "Python 3.10+ stdlib validator & route engine; core workflow instructions remain fully usable without Python."
license: MIT
metadata:
  version: "0.1.0"
---

# Deterministic Agentic Workflow

Operate AI agents using the core architectural axiom: **"Otaknya boleh generative, tangannya harus deterministic."**
Generative cognitive capabilities are reserved for reading context, analyzing intent, designing specifications, planning execution, and synthesizing solutions. All state mutation, system modification, deployment, migration, and verification must execute through deterministic scripts, bounded tools, and verifiable proof gates.

> **Instructional Contract & Scope Notice:** This skill acts as the root router and governance entrypoint for the complete bundled Deterministic Agentic Workflow suite. It directs execution to 8 dedicated, bundled modules in `skills/daw-*/` (and their canonical sibling symlinks). It does not install runtime system hooks, daemon supervisors, automated enforcement interceptors, or external tool suites. Deterministic execution tools and scripts do not automatically guarantee semantic success; truthful verification requires inspecting observable runtime evidence against Acceptance Criteria. Documents alone never constitute running background services or deployment authorization.

Install the complete suite using [the offline installer](references/installation.md). It targets documented skill locations for Codex, Claude Code, Gemini CLI, Cursor, and Copilot. Keep the root and all modules together; on hosts without directory symlinks, load child modules by their canonical paths from this root. Host tools, approval mechanisms, and client discovery remain environment-specific.

Article Reference: Rama Digital — _Agentic Tapi Deterministic Workflow AI Agent_ (https://ramadigital.id/blog/agentic-tapi-deterministic-workflow-ai-agent).  
_Advice separation note:_ Core article principles (generative planning, deterministic mutation, document contracts, verification gates) establish the architectural foundation. Local operational additions in this skill and references define the 8-module suite architecture, declarative manifest routing, two-stage review loops, and isolated workspace controls for multi-agent CLI and workstation environments.

---

## 1. Suite Architecture & Bundled Module Delegation

The DAW suite is **self-contained as a complete 8-module bundle**. It requires **no external workflow frameworks (e.g. Superpowers) or third-party registries**. However, all 8 bundled internal execution modules are **mandatory core dependencies** for complete suite execution:

| Module            | Canonical Path                                                 | Primary Responsibility                                                                   |
| :---------------- | :------------------------------------------------------------- | :--------------------------------------------------------------------------------------- |
| **daw-design**    | [skills/daw-design/SKILL.md](skills/daw-design/SKILL.md)       | Architecture, technical requirements, specification authoring, 13-doc matrix.            |
| **daw-plan**      | [skills/daw-plan/SKILL.md](skills/daw-plan/SKILL.md)           | Structured task planning, phase breakdowns, risk assessment, task contracts.             |
| **daw-debug**     | [skills/daw-debug/SKILL.md](skills/daw-debug/SKILL.md)         | Root cause analysis, minimal reproduction, failure diagnostics, regression isolation.    |
| **daw-build**     | [skills/daw-build/SKILL.md](skills/daw-build/SKILL.md)         | Implementation, code editing, minimal change construction, zero dead weight.             |
| **daw-review**    | [skills/daw-review/SKILL.md](skills/daw-review/SKILL.md)       | Two-stage code review, architectural boundary compliance, security auditing.             |
| **daw-verify**    | [skills/daw-verify/SKILL.md](skills/daw-verify/SKILL.md)       | Behavioral verification, test execution, regression proof, evidence checks.              |
| **daw-workspace** | [skills/daw-workspace/SKILL.md](skills/daw-workspace/SKILL.md) | Isolated workspace/worktree setup, git worktree lifecycle, boundary containment.         |
| **daw-ask**       | [skills/daw-ask/SKILL.md](skills/daw-ask/SKILL.md)             | Read-only architecture consultation, contextual guidance, decision frontier exploration. |

### Module Delegation Rules

1. **Delegation, Not Recursion:** The root router dispatches to modules based on classified intent and operational facts. Modules perform their specific phase and yield back to the orchestrator with recommended next stages. Modules **NEVER** recursively call the root router or invoke each other in circular loops.
2. **Missing Module Policy:** All 8 modules are required core components. If any required internal module is missing from the suite, the workflow is **blocked**; it does not silently degrade into shallow inline approximations. External specialist domain skills remain optional augmentations.
3. **Proportionality:** Small, single-line patches or isolated fixes do not trigger the full 13-document matrix. Planning overhead scales proportionally with risk and blast radius.
4. **Canonical Relative Linking:** Modules reference suite documentation and templates using root-relative paths resolved from their location (`../../references/...` or `../../templates/...`).

---

## 2. Invocations & Observable Action Protocol

### Invocation Modes

1. **Explicit Bare Invocation:**
   - When invoked bare without a task (e.g. `"Use deterministic-agentic-workflow"`):
     - The agent immediately inspects the target directory (`cwd`). It does not scan parent directories unless explicitly directed.
     - If existing code or partial documentation is found -> enters **Adopt** mode.
     - If the target directory is empty and a brief is provided -> enters **Bootstrap** mode.
     - If the target directory is empty and **no brief** is provided -> halts and asks **ONE concrete material question** to establish scope. It halts blocked and **never invents phantom product documents**.
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

1. **Review (`review`):** Static analysis, code review, diff audit, or security boundary assessment on existing code or PRs. When the user's primary intent is evaluation/audit of code or diffs, `review` takes precedence. Strictly read-only; ignores unknown risk or workspace preferences. Dispatches to `daw-review`.
2. **Ask (`ask`):** Purely conversational, read-only architectural consultation, codebase Q&A, or decision trade-off analysis. Read-only user intent always wins. Ignores unknown risk or workspace preferences. Dispatches to `daw-ask`.
3. **Bootstrap (`bootstrap`):** Greenfield project specification from a brief or prompt in an empty or new directory. Generates core specification documents. Dispatches to `daw-design` -> `daw-plan` (documentation-only).
4. **Adopt (`adopt`):** Reverse-engineering and specification authoring for an existing codebase with missing or partial documentation. Dispatches to `daw-design` -> `daw-plan` (documentation-only; preserves user code).
5. **Bugfix (`bugfix`):** Diagnosing, reproducing, and resolving an existing defect or test failure. Dispatches to `daw-debug` -> `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify`. Prepends `daw-workspace` if workspace is isolated.
6. **Patch (`patch`):** Minimal, pre-diagnosed fix or surgical change with well-defined constraints. Dispatches to `daw-build` -> `daw-verify`. Prepends `daw-workspace` if workspace is isolated.
7. **Feature (`feature`):** Multi-step functional change or new capability. If requirements are clear: `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify`. If requirements are unclear: `daw-design` -> `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify`. Prepends `daw-workspace` if workspace is isolated.

### Routing Execution API & Manifest Policy

Automated and programmatic routing decisions are governed by `references/suite-manifest.json` (schema_version 1) and evaluated via the read-only stdlib script:

```bash
python3 "$SUITE_ROOT/scripts/route.py" REQUEST.json [--format text|json] [--root SUITE_ROOT]
```

_(Always invoke using the explicitly resolved script path `$SUITE_ROOT/scripts/route.py`, never assuming `scripts/` exists in the target project's `cwd`)._

The request requires classified input facts (`schema_version`, `intent`, `requirements`, `risk`, `workspace`):

- If requirements are unknown for `bootstrap` or `feature`, or if workspace is unknown for mutating intents (`feature`, `bugfix`, `patch`), or if risk is unknown for mutating intents (`feature`, `bugfix`, `patch`), the engine returns `status: "needs-input"` with explicit blockers.
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
     1. Load root governance rules (this section §4 and §6) and the canonical module handoff specification in `references/routing.md`.
     2. Before performing any state mutation, load the relevant preflight and approval rules from `references/operations.md`.
     3. Evaluate risk and prerequisites: unknown risk, unknown target environment, or missing exact interactive approval for high-risk actions immediately yields `status: "blocked"` before any filesystem or system mutation. Safe read-only intake and analysis remain permitted.

## 5. Specification Planning Matrix (The Canonical 13 Documents)

When specifications are required by `bootstrap`, `adopt`, or complex `feature` workflows, `daw-design` references the exact canonical 13-document matrix located in `templates/`:

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

### Selection, Omission & Provenance Rules:

- **Default Baseline Subset (6 Core Docs):** For new greenfield projects (`bootstrap`) and existing codebase documentation (`adopt`), author the default 6 baseline specification contracts: `blueprint.md`, `prd.md`, `frd.md`, `techstack.md`, `security.md`, `roadmap.md`. The remaining specifications are omitted unless explicitly requested; in the planning table, state omitted documents as `skipped` without generating empty files.
- **Explicit Full 13-Doc Suite:** When an operator explicitly requests the full 13-document suite, all 13 document contracts must be satisfied. Existing architecture documents, filenames, or established project aliases count toward satisfying contracts; do not force duplicate new files when existing project specifications already satisfy the contract. Any contract not applicable to the architecture (e.g., UI wireframes for a headless backend CLI) must contain an explicit, meaningful `N/A` section with rationale, rather than being omitted.
- **Specification Directory Determination:** Always check the target project's established conventions first (e.g. existing `docs/` or root aliases). If no established directory exists, **the deterministic default is `docs/specs/`**.
- **Standardized Document Metadata Block:** Every specification document must include the standard template metadata block:
  ```markdown
  > **Status:** Draft / Ready for Review / Approved / Superseded
  > **Owner:** [Verified Operator Name / Role, or Unassigned]
  > **Scope:** [Bounded component, service, or repository area]
  > **Source Documents / Revision:** [Commit SHA, PR #, or path@rev, or unverified]
  ```
- **Truthful Decision Provenance:** Capture decisions in a concise human-readable provenance table with clear labels: `user_directed`, `observed_from_source`, or `agent_proposed`.

---

## 6. Canonical Module Handoff Contract

All module completions produce a structured handoff payload adhering to the canonical contract defined in `references/routing.md#5-canonical-module-handoff-contract`.

Every bundled execution module returns a JSON object with this exact outer envelope:

```json
{
  "objective": "Single-sentence concise summary of the executed stage.",
  "input_paths": ["paths/read/or/evaluated.ext"],
  "output_paths": ["paths/created/or/modified.ext"],
  "acceptance_criteria": [
    {
      "criterion": "Verifiable condition evaluated during this stage.",
      "status": "pass"
    }
  ],
  "evidence": [
    {
      "reference": "Command, test output, or tool observation identifier.",
      "summary": "Concrete empirical proof of the outcome."
    }
  ],
  "status": "pass",
  "handoff_to": "daw-verify",
  "details": {
    "module_specific_field": "values"
  }
}
```

### Envelope Invariants:

- **Outer Fields:** `objective` (nonblank string), `input_paths` (array of strings), `output_paths` (array of strings), `acceptance_criteria` (array of `{criterion: string, status: "pass"|"fail"|"blocked"}`), `evidence` (array of `{reference: string, summary: string}`), `status` (`"pass"` | `"fail"` | `"blocked"`), `handoff_to` (canonical `daw-*` name or `null`), `details` (object containing rich module-specific findings).
- **Stage-Scoped Status:** Outer `status: "pass"` certifies ONLY that the current module's stage-specific criteria were satisfied. It is NEVER proof of end-to-end implementation, deployment, or authorization.
- **Status Integrity:** `fail` means executed criteria failed or are incomplete; `blocked` means missing prerequisites, environment context, or required interactive approvals. Rich domain findings in `details` cannot override the outer status.
- **Advisory Handoff:** `handoff_to` is an advisory recommendation for the parent orchestrator, never a directive for recursive module-to-module self-execution.
- **Empty Paths Permitted:** `input_paths` and `output_paths` may be empty for read-only evaluations or stages producing no disk artifacts. Evidence references can identify tool logs or observations rather than new files.
