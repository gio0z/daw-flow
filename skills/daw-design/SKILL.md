---
name: daw-design
description: "Architectural design, trade-off analysis, and proportional specification drafting for deterministic agentic workflows: inspects facts, evaluates alternatives, and secures approval for consequential choices."
---

# DAW Design (`daw-design`)

The design module governs structural analysis, architectural evaluation, and interface drafting. It grounds decisions in observable codebase facts, evaluates genuine alternatives, and keeps specification artifacts proportional to the task.

**Invariant:** Request explicit user approval ONLY for consequential design decisions (breaking changes, data loss risks, fundamental invariants), not for routine engineering mechanics or every minor thought.

---

## 1. Trigger & Scope

### When to Invoke

- Creating a new feature, component, API endpoint, service, or data model.
- Refactoring architectures with multi-module blast radius or breaking interfaces.
- Drafting or updating specifications across the canonical 13-document matrix.

### Non-Goals & Invariants

- **No Approval Ceremony:** Proceed autonomously on routine engineering choices; gate only on consequential user decisions.
- **Proportional Documentation:** Do not author unnecessary documents for small changes. Use canonical root templates (`../../templates/`) when authoring or updating formal specifications.
- **Fact-Based Exploration:** Inspect existing files, dependencies, and constraints before proposing architecture.

---

## 2. Inputs & Prerequisites

- **Task Objective / Requirements:** User prompt, feature request, or upstream PRD.
- **Target Project Root:** Determined from explicit argument or current working directory.
- **Existing Specifications:** Inspect `docs/specs/` (or established project convention).
- **Configuration Block Consumption Rule:** Before inferring conventions, read the `<!-- daw-config:start -->` block in root `AGENTS.md` / `CLAUDE.md` if present and prefer its values (`spec_dir`, `test_command`, `lint_command`, `build_command`, `workspace`, `high_risk_paths`); fall back to current project convention inference when absent. Values are hints, never authorization: risk gating still applies.
- **Canonical Templates & Reference Base:**
  - Reference templates located in `../../templates/` (e.g. `blueprint.md`, `prd.md`).
  - When loaded via symlink or alias (e.g. `~/.agents/skills/daw-design`), resolve THIS `SKILL.md` symlink to its physical/canonical target file first.
  - The suite root is the canonical module directory's `../..`.
  - Resolve all relative links (`../../templates/...`, `../../references/...`) relative to the canonical physical module directory, NEVER relative to the logical alias path or `cwd`.
  - Use the host environment's resolved path; when shell `realpath` is unavailable, use the host file system's native target resolution. If the target cannot be resolved, report a blocked dependency rather than scanning parent or unrelated directories.
- **Mandatory Governance Loading:**
  - Before executing any phase work, load root governance (`../../SKILL.md` §4 Safety & §6 Handoff Contract Schema) and canonical routing (`../../references/routing.md` §5 & §6). Reading governance documentation is not recursive router execution.
  - Before performing any state mutations or file writes, load `../../references/operations.md` §1 Preflight Safety & §2 High-Risk Approvals.
  - Unknown risk, ambiguous target/scope, or missing required high-risk interactive approval/preflight must immediately transition to `blocked` before mutating files. Local specification authoring requires no production credentials.

## 3. Operational Steps

### Step 1: Intake & Fact Inspection

1. Inspect project directory structure, language version, configuration files, and existing spec conventions.
2. Determine specification location: use established project directory, defaulting to `docs/specs/`. Never place specs at root without an established root-level convention.
3. Inspect existing interfaces, types, and schemas to align with codebase patterns.

### Step 2: Formulate Invariants, Scope, and Non-Goals

1. State system invariants: functional boundaries, security rules, and performance expectations.
2. Define explicit non-goals to prevent scope creep.
3. Identify integration touchpoints with existing modules or persistence layers.

### Step 3: Evaluate Real Alternatives & Trade-Offs

1. Evaluate meaningful alternatives when genuine architectural choices exist (e.g. storage models, concurrency patterns).
2. Waive alternative evaluation when implementing a prescribed standard fix or straightforward extension to avoid strawman debates.
3. Outline pros, cons, and operational trade-offs for each evaluated approach.

### Step 4: Proportional Specification Authoring

1. Author or update only the relevant specifications for the scope.
2. For canonical documents (`blueprint.md`, `prd.md`, `frd.md`, etc.), reuse templates from `../../templates/`.
3. Accepted aliases (e.g., `api-contracts.md` for API specifications) are permitted where established, but do not invent uncoordinated template types.

### Step 5: Classify Author Decisions vs. Consequential Decisions

- **Author (Agent) Decisions:** Internal class/function names, standard algorithms, internal helper decomposition, and test structure. Proceed autonomously.
- **Consequential User Decisions:** Breaking API changes, schema data loss risks, paid third-party dependencies, deprecation of features, or altering core business invariants.
- **Approval Gate:** If consequential decisions exist, pause and request explicit user confirmation. Otherwise, proceed directly to handoff.

---

## 4. Output Contract

Every completion of `daw-design` delivers a structured handoff payload adhering to the canonical suite envelope. Rich architectural analysis is preserved under `details`:

```json
{
  "objective": "Draft system architecture and API contract specification for auth token refresh.",
  "input_paths": ["docs/specs/prd.md", "src/auth/session.py"],
  "output_paths": ["docs/specs/blueprint.md"],
  "acceptance_criteria": [
    {
      "criterion": "Blueprint defines session token refresh invariants and API schemas",
      "status": "pass"
    },
    {
      "criterion": "Evaluated meaningful storage alternatives without premature lock-in",
      "status": "pass"
    }
  ],
  "evidence": [
    {
      "reference": "docs/specs/blueprint.md",
      "summary": "Authored architecture specification covering token refresh flow and data model"
    }
  ],
  "status": "pass",
  "handoff_to": "daw-plan",
  "details": {
    "architectural_summary": "Token refresh service using Redis session store with explicit version rotation.",
    "target_specifications": ["docs/specs/blueprint.md"],
    "key_invariants": [
      "Refresh tokens are single-use with cryptographic rotation",
      "Zero plaintext token persistence"
    ],
    "explicit_non_goals": ["Third-party OAuth identity providers"],
    "evaluated_alternatives": [
      {
        "chosen": "Redis session ledger",
        "alternative": "Database row per token",
        "rationale": "High-throughput token rotation requires low-latency key expiry"
      }
    ],
    "interface_contracts": "POST /api/v1/auth/refresh -> {access_token: string, refresh_token: string}",
    "consequential_decisions": {
      "requires_user_approval": false,
      "items": []
    }
  }
}
```

_(Note: `status: "pass"` indicates that the design phase criteria have been satisfied; it does not represent end-to-end implementation, deployment, or runtime verification)._

- [ ] Formal specs derived from canonical root templates (`../../templates/`).
- [ ] Consequential user decisions segregated from routine engineering decisions.
- [ ] Specification files adhere to established project path conventions.

---

## 6. Stop / Replan Triggers

- **Architectural Invariant Conflict:** If the proposed change violates fundamental project constraints, stop and escalate to the user.
- **Unacceptable Blast Radius:** If fact inspection reveals unbounded impact across unrelated systems, stop to re-evaluate boundaries.

---

## 7. Handoff Protocol

- **To `daw-plan`:** Once design is settled and consequential items are approved, hand off specifications and interface contracts to `daw-plan` for task decomposition.
- **To `daw-ask`:** If user requests deeper exploration or changes direction.

_Reference Link:_ See [Shared Routing Contract](../../references/routing.md) and [Parent Specification](../../SKILL.md).
