---
name: daw-design
description: "Architectural design, trade-off analysis, domain modeling, and proportional specification drafting for deterministic agentic workflows: grounds decisions in observable facts, resolves trade-offs via bounded grilling, inspects builder-readiness, and secures approval for consequential choices."
---

# DAW Design (`daw-design`)

The design module governs structural analysis, architectural evaluation, domain modeling, and interface drafting. It grounds decisions in observable codebase facts, evaluates genuine alternatives, keeps specification artifacts proportional to the task, and assesses builder-readiness before downstream handoff.

**Invariant:** Request explicit user approval ONLY for consequential design decisions (breaking changes, data loss risks, fundamental invariants), not for routine engineering mechanics or every minor thought.

---

## 1. Trigger & Scope

### When to Invoke

- Creating a new feature, component, API endpoint, service, or data model.
- Refactoring architectures with multi-module blast radius or breaking interfaces.
- Drafting or updating specifications across the canonical 13-document matrix.
- Disambiguating domain models, resolving semantic overload, or recording architectural decisions (ADRs).

### Non-Goals & Invariants

- **No Approval Ceremony:** Proceed autonomously on routine engineering choices; gate only on consequential user decisions.
- **Proportional Documentation:** Do not author unnecessary documents for small changes. Use canonical root templates (`../../templates/`) when authoring or updating formal specifications.
- **Fact-Based Exploration & Grounded Reality:** Inspect existing files, dependencies, schemas, and constraints before proposing architecture. Never invent agreement or synthetic domain terminology; distinguish observed facts from legitimately proposed new concepts.
- **Nonrecursive Dispatch:** `daw-design` performs structural analysis, interactive elicitation, specification drafting, and readiness inspection; it never executes code, performs recursive module dispatch, or invokes sub-skills directly. Orchestration remains strictly with the parent router.

---

## 2. Inputs & Prerequisites

- **Task Objective / Requirements:** User prompt, feature request, or upstream PRD.
- **Target Project Root:** Determined from explicit argument or current working directory.
- **Existing Specifications & Conventions:** Inspect `docs/specs/` (or established project convention), existing ADR folders (`docs/adr/`, `doc/decisions/`), and schema definitions.
- **Configuration Block Consumption Rule:** Before inferring conventions, read the `<!-- daw-config:start -->` block in root `AGENTS.md` / `CLAUDE.md` if present and prefer its values (`spec_dir`, `test_command`, `lint_command`, `build_command`, `workspace`, `high_risk_paths`); fall back to current project convention inference when absent. Values are hints, never authorization: risk gating still applies.
- **Canonical Templates & Reference Base:**
  - Reference templates located in `../../templates/` (e.g. `blueprint.md`, `prd.md`, `techstack.md`).
  - When loaded via symlink or alias (e.g. `~/.agents/skills/daw-design`), resolve THIS `SKILL.md` symlink to its physical/canonical target file first.
  - The suite root is the canonical module directory's `../..`.
  - Resolve all relative links (`../../templates/...`, `../../references/...`, `references/...`) relative to the canonical physical module directory, NEVER relative to the logical alias path or `cwd`.
  - Use the host environment's resolved path; when shell `realpath` is unavailable, use the host file system's native target resolution. If the target cannot be resolved, report a blocked dependency rather than scanning parent or unrelated directories.
- **Conditional Supporting References (Load On-Demand Only):**
  - Read [Shared Grilling Protocol](../../references/grilling.md) ONLY when requirements are ambiguous, trade-offs depend on unstated business priorities, or conflicting constraints arise; skip for routine tasks.
  - Read [Domain Modeling Protocol](references/domain-modeling.md) ONLY when domain terminology is overloaded, ambiguous across modules, or ADR gating applies; skip for standard extensions with established vocabulary.
  - Read [Builder-Readiness Protocol](references/builder-readiness.md) ONLY before substantive design handoff (new services, modified data schemas, multi-module refactoring) to inspect material seams; skip for minimal, routine, or localized changes.
- **Mandatory Governance Loading:**
  - Before executing any phase work, load root governance (`../../SKILL.md` §4 Safety & §6 Handoff Contract Schema) and canonical routing (`../../references/routing.md` §5 & §6). Reading governance documentation is not recursive router execution.
  - Before performing any state mutations or file writes, load `../../references/operations.md` §1 Preflight Safety & §2 High-Risk Approvals.
  - Unknown risk, ambiguous target/scope, or missing required high-risk interactive approval/preflight must immediately transition to `blocked` before mutating files. Local specification authoring requires no production credentials.

---

## 3. Operational Steps

### Step 1: Intake, Fact Inspection & Domain Grounding

1. Inspect project directory structure, language version, configuration files, and existing spec conventions.
2. Determine specification location: use established project directory, defaulting to `docs/specs/`. Never place specs at root without an established root-level convention.
3. Inspect existing domain vocabulary, entity models, database schemas, and ADR conventions (e.g. `docs/adr/`, `doc/decisions/`, `docs/specs/`, `architecture/`).
4. Avoid forcing generic `GLOSSARY.md` or arbitrary ADR paths onto an existing codebase; conform to existing repo conventions.
5. If overloaded domain terms appear across modules, resolve them via concrete operational scenarios and bounded contexts per [Domain Modeling Protocol](references/domain-modeling.md).

### Step 2: Formulate Invariants, Scope, and Non-Goals

1. State system invariants: functional boundaries, security rules, performance expectations, and data consistency boundaries.
2. Define explicit non-goals to prevent scope creep.
3. Identify integration touchpoints with existing modules or persistence layers.
4. Ground analysis strictly in verified facts versus user decisions; do not invent fictional constraints.

### Step 3: On-Demand Shared Grilling (Interactive Clarification)

1. When requirements are ambiguous, trade-offs depend on unstated business priorities, or conflicting constraints arise, trigger the [Shared Grilling Protocol](../../references/grilling.md).
2. Ground all fact-discoverable items through codebase inspection before asking the user.
3. Elicit in bounded rounds (maximum 5 prioritized questions per round) ordered by the decision dependency frontier.
4. Frame questions with concrete agent recommendations and technical rationales when evaluating trade-offs; prompt for open user preferences when new business direction is required without forcing arbitrary assumptions.
5. Waive formal grilling for direct questions, routine engineering details, or small settled changes.
6. Conclude grilling when open decisions are resolved or deferred; preserve internal grilling classification under `details` (never use non-canonical values for top-level `status`). If a material blocker remains, exit with canonical `status: "blocked"`.

### Step 4: Alternatives, Trade-Offs & ADR Conjunctive Gating

1. Evaluate meaningful alternatives when genuine architectural choices exist (e.g. storage models, concurrency patterns).
2. Waive alternative evaluation when implementing a prescribed standard fix or straightforward extension to avoid strawman debates.
3. **ADR Conjunctive Gating:** Author an Architecture Decision Record (ADR) only when all three conjunctive conditions are met: (1) hard-to-reverse / high replacement cost, (2) non-obvious trade-offs requiring historical context, and (3) genuine architectural trade-offs across competing quality attributes per [Domain Modeling Protocol](references/domain-modeling.md). If any condition is absent, record material choices in an authorized existing specification (e.g. `blueprint.md`); trivial implementation choices require no record.
4. Track provenance explicitly: label items as `[Observed Fact]`, `[Human Decision]`, or `[Agent Recommendation]`. Agents may legitimately propose new domain concepts required by the design.
5. If past architectural decisions are modified, supersede the previous record with explicit linkage; NEVER rewrite or erase historical records.

### Step 5: Proportional Specification Authoring

1. Author or update only the relevant specifications for the scope across the canonical 13-document matrix.
2. For canonical documents (`blueprint.md`, `prd.md`, `frd.md`, `techstack.md`, etc.), reuse templates from `../../templates/`.
3. Accepted aliases (e.g., `api-contracts.md` for API specifications) are permitted where established, but do not invent uncoordinated template types.
4. Persist settled specifications, domain definitions, and ADRs strictly within authorized document scope.

### Step 6: Builder-Readiness Assessment & Seam Inspection

1. For substantive designs, inspect consumer boundaries material to downstream implementation per [Builder-Readiness Protocol](references/builder-readiness.md):
   - **Interface & Boundary Seams:** Material consumer contracts, ingress/egress payloads, and schema types (without requiring internal private function signatures).
   - **Relevant Error Topologies:** Explicit failure conditions and error contracts where relevant (without mandating unneeded retries or fallbacks).
   - **State & Concurrency Invariants:** Atomic boundaries, consistency rules, and race condition mitigations where concurrency or shared state warrants it.
   - **Verifiable Acceptance Seams:** Deterministic, observable pass/fail criteria with verifiable evidence hooks.
2. Waive formal builder-readiness inspection for minimal, routine, or localized changes.
3. Classify open items into **Blocking Unknowns** (halt handoff; resolve or escalate) versus **Safe Reversible Choices** (document sensible default with rationale; proceed autonomously).
4. Report structural readiness, not runtime proof: design status `pass` validates specification completeness, never runtime execution or deployment.
5. If independent review is warranted for high-risk designs, recommend delegation to `daw-review` via the parent router; NEVER invoke other modules recursively.

### Step 7: Classify Author Decisions vs. Consequential Decisions

- **Author (Agent) Decisions:** Internal class/helper decomposition, algorithms, local variable naming, sensible configuration defaults, and test structure. Proceed autonomously without requiring user approval.
- **Consequential User Decisions:** Breaking external API contracts, schema migrations with data loss risk, introducing paid third-party dependencies, deprecating public features, or altering core business invariants.
- **Approval Gate:** If consequential decisions exist, pause and request explicit user confirmation. Safe reversible defaults do not require interactive approval.

---

## 4. Output Contract

Every completion of `daw-design` delivers a structured handoff payload adhering to the canonical suite envelope. Rich architectural analysis, domain modeling, and builder-readiness facts are preserved under `details`:

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
      "criterion": "Builder-readiness seam inspection confirms zero blocking unknowns",
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
    "architectural_summary": "Token refresh service using dedicated session store with cryptographic rotation.",
    "target_specifications": ["docs/specs/blueprint.md"],
    "key_invariants": [
      "Refresh tokens are single-use with cryptographic rotation",
      "Zero plaintext token persistence"
    ],
    "explicit_non_goals": ["Third-party OAuth identity providers"],
    "evaluated_alternatives": [
      {
        "chosen": "Dedicated session ledger table",
        "alternative": "Stateless HMAC-signed token claims",
        "rationale": "Immediate revocation requirement precludes stateless token claims"
      }
    ],
    "domain_modeling": {
      "disambiguated_terms": ["RefreshToken", "SessionStore"],
      "adr_references": ["docs/specs/blueprint.md#adr-token-storage"],
      "convention_path": "docs/specs/"
    },
    "builder_readiness": {
      "substantive_design": true,
      "seams_checked": [
        "interfaces",
        "error_handling",
        "concurrency",
        "acceptance_criteria"
      ],
      "blocking_unknowns": [],
      "safe_reversible_choices": [
        "Default HTTP client timeout set to 15 seconds"
      ],
      "readiness_verdict": "ready_for_planning"
    },
    "interface_contracts": "POST /api/v1/auth/refresh -> {access_token: string, refresh_token: string}",
    "consequential_decisions": {
      "requires_user_approval": false,
      "items": []
    }
  }
}
```

_(Note: `status: "pass"` indicates that the design phase criteria have been satisfied; it does not represent end-to-end implementation, deployment, or runtime verification)._

---

## 5. Exit Criteria & Quality Checklist

Before finalizing handoff from `daw-design`, verify:

- [ ] Formal specs derived from canonical root templates (`../../templates/`).
- [ ] Domain vocabulary grounded in observable codebase facts; newly proposed concepts explicitly marked with recommendation provenance.
- [ ] Existing project specification and ADR path conventions respected (no forced generic paths).
- [ ] Consequential user decisions segregated from routine engineering decisions.
- [ ] For substantive designs, builder-readiness seams evaluated with zero unresolved blocking unknowns.
- [ ] Changed architectural decisions supersede rather than rewrite historical records.
- [ ] No recursive module dispatch attempted; independent review recommendations directed to parent router.

---

## 6. Stop / Replan Triggers

- **Architectural Invariant Conflict:** If the proposed change violates fundamental project constraints, stop and escalate to the user.
- **Unacceptable Blast Radius:** If fact inspection reveals unbounded impact across unrelated systems, stop to re-evaluate boundaries.
- **Material Blocker Encountered:** If a blocking unknown or fundamental constraint conflict cannot be resolved via grilling, exit with `status: "blocked"`.
- **Preflight or Risk Violation:** If high-risk file mutation occurs without required authorization, halt immediately per `../../references/operations.md`.

---

## 7. Handoff Protocol

- **To `daw-plan`:** Once design is settled, builder-readiness is verified, and consequential items are approved, hand off specifications and interface contracts to `daw-plan` for deterministic task decomposition.
- **To `daw-ask`:** If user requests deeper conversational exploration or shifts direction.
- **Independent Review Delegation:** When architectural risk or blast radius warrants independent auditing, recommend `daw-review` to the parent router in handoff notes. `daw-design` NEVER dispatches modules recursively.

_Reference Links:_

- [Shared Grilling Protocol](../../references/grilling.md)
- [Domain Modeling Protocol](references/domain-modeling.md)
- [Builder-Readiness Protocol](references/builder-readiness.md)
- [Shared Routing Contract](../../references/routing.md)
- [Parent Specification](../../SKILL.md)
