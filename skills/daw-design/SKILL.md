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
- Drafting or updating specifications across the 14-kind catalog (six baseline plus conditional ERD).
- Disambiguating domain models, resolving semantic overload, or recording architectural decisions (ADRs).

### Non-Goals & Invariants

- **No Approval Ceremony:** Proceed autonomously on routine engineering choices; gate only on consequential user decisions.
- **Proportional Documentation:** Do not author unnecessary documents for small changes. Use canonical root templates (`../../templates/`) when authoring or updating formal specifications. Trivial inline work (localized single-file tweaks, internal refactors, minor fixes) does not require a mandatory full-catalog bundle or document-quality JSON records.
- **Fact-Based Exploration & Grounded Reality:** Inspect existing files, dependencies, schemas, and constraints before proposing architecture. Never invent agreement or synthetic domain terminology; distinguish observed facts from legitimately proposed new concepts.
- **Workflow Transition Gate vs. Hook Claims:** Document-quality validation operates as an explicit deterministic workflow transition gate (`python3 scripts/validate.py docs RECORD --project-root ROOT --transition TRANSITION --documents PATH [PATH ...] --format text|json`) invoked by the orchestrator/parent. It does NOT claim or use automatic harness hook interception, daemon supervisors, or runtime monkeypatching. If Python 3 is unavailable, the gate must honestly halt with canonical `status: "blocked"` (never emit a fake pass).
- **Nonrecursive Dispatch & Downstream Handoff:** `daw-design` performs structural analysis, interactive elicitation, specification drafting, and readiness inspection; it never executes code, performs recursive module dispatch, or invokes sub-skills directly (`handoff_to: "daw-design"` is strictly forbidden; handoff proceeds downstream to `daw-plan` or returns to parent). Orchestration remains strictly with the parent router.
- **Scope Guard (Governance & Architecture vs. Implementation):** Classify every user input as either architecture/governance content or a separate non-governance intent. If input includes feature implementation, code generation, refactoring, building, or deployment requests, `daw-design` MUST NOT execute them. Extract them as deferred intents under `details.next_actions`. Do not create or modify application source code, feature routes, components, or test files during design or governance authoring.
- **Canonical Shared Procedural Contract:** Adhere to the shared delivery contract defined in [Canonical Document Quality & Workflow Transition Guide](../../references/document-quality.md#feature-delivery-contract) (specifically [Governance Alignment](../../references/document-quality.md#a-governance-and-authoring-alignment), [Clarification & Uncertainty Resolution](../../references/document-quality.md#b-clarification-and-technical-uncertainty-resolution), and [Feature Slicing & Behavioral Oracles](../../references/document-quality.md#c-feature-slicing-and-behavioral-contract-oracles)).
- **Canonical Workflow Artifacts Contract:** Adhere to [Workflow Artifacts](../../references/workflow-artifacts.md) for specification/plan/progress/mockup persistence, ownership, and binding. For multi-step work, a proportional authoritative specification MUST be persisted before tactical planning per [§1–§2](../../references/workflow-artifacts.md#1-artifact-set--proportionality), reusing a current adequate spec and preserving its IDs. Parent — not workers — records actual active design subphase/progress; workers propose updates only and never self-approve. Bootstrap starts from blueprint/domain/flow before UI/database design. The feature-delivery contract [§A.6](../../references/document-quality.md#a-governance-and-authoring-alignment) applies the same rule; in case of divergence, [Workflow Artifacts](../../references/workflow-artifacts.md) governs persistence/ownership and [Document Quality §9](../../references/document-quality.md#feature-delivery-contract) governs acceptance-criteria semantics.

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
  - Read [Canonical Document Quality & Workflow Transition Specification](../../references/document-quality.md) whenever authoring or updating formal specifications from the 14-kind catalog.
  - Read [Builder-Readiness Protocol](references/builder-readiness.md) ONLY before substantive design handoff (new services, modified data schemas, multi-module refactoring) to inspect material seams; skip for minimal, routine, or localized changes.
  - Read [Change Coupling & Structural Analysis Reference](../../references/change-coupling.md) ONLY when evaluating multi-module refactoring boundaries, decomposing tightly coupled components, or auditing proposed architecture for hidden links and surplus indirection; skip for routine or localized additions.
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
6. **Intake Workflow Transition Gate:** When formal specifications are planned, the parent/orchestrator establishes the objective, target audience, scope, empirical sources, and selects the expected target set (`--documents`). The orchestrator executes the intake transition check:
   `python3 scripts/validate.py docs <RECORD> --project-root <ROOT> --transition intake-authoring --documents <DOC_PATH> [<DOC_PATH> ...] --format text|json`
   Formal authoring begins only after intake transition eligibility is satisfied.

### Step 2: Formulate Invariants, Scope, and Non-Goals

1. State system invariants: functional boundaries, security rules, performance expectations, and data consistency boundaries.
2. Define explicit non-goals to prevent scope creep. Distinguish business what/why from technical how. Never invent policies, owners, approvals, or unobservable vanity metrics.
3. Identify integration touchpoints with existing modules or persistence layers.
4. Ground analysis strictly in verified facts versus user decisions; do not invent fictional constraints.
5. **Governance Change Impact & Sync:** When a principle or architectural foundation changes, do not silently override existing specifications or sneak in code edits. Identify affected downstream documents, tasks, and evidence, and produce a structured sync impact report (`details.sync_impact_report`):
   - Version change / revision bump
   - Modified principles or decisions (old title/concept -> new title/concept)
   - Added or removed constraints and sections
   - Downstream artifacts to sync (specifications, roadmaps, task lists, test suites, evidence ledgers).

### Step 3: On-Demand Shared Grilling (Interactive Clarification)

1. When requirements are ambiguous, trade-offs depend on unstated business priorities, or conflicting constraints arise, trigger the [Shared Grilling Protocol](../../references/grilling.md).
2. **Technical Research Before User Inquiries:** Before querying the operator about technical uncertainties, non-destructively research workspace code, dependencies, schemas, and official documentation. Record architectural decisions, technical rationale, alternatives considered, and authoritative citations directly in the appropriate existing specification section (e.g. `techstack.md`, ADR section in architecture doc, or `blueprint.md`) — no mandatory separate `research.md`.
3. Ground all fact-discoverable items through codebase inspection before asking the user.
4. Elicit in bounded rounds (maximum 5 prioritized questions per round) ordered by `impact × uncertainty`. Sequence dependent trade-offs **one at a time** along the active decision frontier; batch only independent choices up to 5 per round.
5. **Native Clarify Transport:** Follow [Native Interactive Clarification Transport (Canonical Rule)](../../references/grilling.md#native-interactive-clarification-transport-canonical-rule) for unresolved material user decisions only. Cancel/unanswered remains unresolved, never default consent; clarification does not replace required provider/security point-of-risk approval.
6. Frame questions with concrete agent recommendations and technical rationales when evaluating trade-offs; prompt for open user preferences when new business direction is required without forcing arbitrary assumptions. Avoid false dichotomies, answered questions, or internal naming queries.
7. Waive formal grilling for direct questions, routine engineering details, or small settled changes.
8. **Safe Answer Reinjection:** `daw-design` is the authorized specification write module. When receiving user answers from interactive grilling or read-only inquiry handoffs (from `daw-ask` or parent handoff via `details.elicitation_updates`), `daw-design` safely reinjects answers into the authoritative specifications, reconciles conflicting text, updates affected acceptance criteria, and marks remaining unknowns to block only dependent scope.
9. Conclude grilling when open decisions are resolved or deferred; preserve internal grilling classification under `details` (never use non-canonical values for top-level `status`). If a material blocker remains, exit with canonical `status: "blocked"`.

### Step 4: Alternatives, Trade-Offs & ADR Conjunctive Gating

1. Evaluate meaningful alternatives when genuine architectural choices exist (e.g. storage models, concurrency patterns).
2. Waive alternative evaluation when implementing a prescribed standard fix or straightforward extension to avoid strawman debates.
3. **ADR Conjunctive Gating:** Author an Architecture Decision Record (ADR) only when all three conjunctive conditions are met: (1) hard-to-reverse / high replacement cost, (2) non-obvious trade-offs requiring historical context, and (3) genuine architectural trade-offs across competing quality attributes per [Domain Modeling Protocol](references/domain-modeling.md). If any condition is absent, record material choices in an authorized existing specification (e.g. `blueprint.md`); trivial implementation choices require no record.
4. Track provenance explicitly: label items as `[Observed Fact]`, `[Human Decision]`, or `[Agent Recommendation]`. Agents may legitimately propose new domain concepts required by the design.
5. If past architectural decisions are modified, supersede the previous record with explicit linkage; NEVER rewrite or erase historical records.
6. **Change-Coupling & Deep Module Alignment:** When designing subsystem interfaces, apply the principles in `../../references/change-coupling.md`: ask "should these pieces change together?", favor deep modules with narrow interfaces over shallow pass-through abstractions, and preserve legitimate protocol retries, security wrappers, and transaction boundaries.

### Step 5: Proportional Specification Authoring

1. Govern specification authoring under the Authoritative Documentation Authoring Contract (`../../references/routing.md` §3). `daw-design` is the primary authoritative author, custodian, and adopter for specifications across the 14-kind catalog.
2. Before authoring or updating any specification, read its matching entry in `../../references/routing.md` §3 and the actual canonical template in `../../templates/<doc>.md`. Before declaring completion, explicitly satisfy the Output Contract, Exit Criterion, and builder-readiness seams.
3. **Hierarchy of Truth, Domain Math & Provenance:** User facts and existing repository realities (code, manifests, configs) outrank templates. Templates define structure, not evidence. Ground technical choices in observed repository manifests (`package.json`, `Cargo.toml`, etc.); cite exact paths and observed versions. Never fabricate citations or synthetic version numbers. Specification examples must preserve existing observed domain calculations, schemas, and invariants verbatim without inventing unsupplied math (such as physical vs. reserved inventory counts).
4. **Handling Missing Sources & Absence of Evidence:** Absence of supplied evidence is not evidence of absence; never invent negative facts (e.g. asserting "no auth configured" simply because none was supplied). If a decision cannot be grounded in verified sources or tools are unavailable, record it as `[UNVERIFIED]` or an Open Question. Unresolved interfaces, query parameters, path variants, or error codes (e.g. 404 defaults) must remain proposed `[Agent Recommendation]` awaiting acceptance, never silently entering binding Acceptance Criteria or claimed as settled. Block only impacted downstream paths; do not halt unaffected orthogonal work.
5. **Scoped Reader Questions & Fact Provenance:** Author specifications answering the scoped reader questions from [Canonical Document Quality & Workflow Transition Specification](../../references/document-quality.md) and `references/document-quality-rubric.json`: the 5 common criteria (DQ-01 to DQ-05: audience/task location, empirical fact vs proposal separation, domain terminology coherence, completeness of actionable contracts, absence of vanity padding) plus the 3 kind-specific criteria for each selected document. Ground factual assertions in empirical codebase citations with line numbers and exact quotes.
6. **Progressive Workflow Transitions:**
   - **Authoring to Review (`authoring-review`):** When drafting is complete, author emits the record with artifact citations and invokes:
     `python3 scripts/validate.py docs <RECORD> --project-root <ROOT> --transition authoring-review --documents <DOC_PATH> [<DOC_PATH> ...] --format text|json`
   - **Review to Ready (`review-ready`):** Downstream spec-dependent work requires parent/reviewer evaluation of semantic content and current evidence (author self-grading pass is rejected). Upon review acceptance (`decision: "accepted"` across all required criteria), parent executes:
     `python3 scripts/validate.py docs <RECORD> --project-root <ROOT> --transition review-ready --documents <DOC_PATH> [<DOC_PATH> ...] --format text|json`
   - **Review to Rework (`review-rework` / `rework-review`):** If any required criterion is rejected (`decision: "not_accepted"`), execute `review-rework`, perform targeted rework, and transition back via `rework-review`.
   - **Mutation Invalidation:** Any modification to specification text alters its SHA-256 hash and invalidates prior `review-ready` eligibility.
   - **QA Review Limitation:** Human comprehension remains unexercised without live people; automated review evaluates structural and evidence compliance only.
7. **Prioritized Feature Slicing & Measurable Oracles:** When authoring feature specifications (PRD, FRD, Blueprint):
   - Preserve existing stable story, requirement, and acceptance criteria IDs (`US-01`, `PRD-01`, `FRD-01`). If absent, generate scoped unique IDs and retain them.
   - Structure features into prioritized, independently demonstrable/testable behavior stories (P1, P2...) with acceptance criteria per the canonical [EARS Semantic Guidance](../../references/document-quality.md#acceptance-criteria-ears) (observable condition/response/oracle; Given/When/Then equivalent) — never restate competing persistence/format rules here.
   - Do not force deploy independence for inseparable safety or transaction invariants. Supporting infrastructure tasks can lack stories only with explicit prerequisite justification.
   - Distinguish business outcomes/KPIs from build/runtime acceptance criteria (a KPI cannot serve as runtime acceptance without an observable, testable measurement boundary).

8. Author or update only the relevant specifications for the scope (avoiding forced full-catalog churn).
9. **Conditional ERD Selection:** When persisted entities/relationships are introduced, materially changed, or adopted without an adequate existing model, select the separate ERD (`erd`, default `erd.md` under the spec convention) per [Workflow Artifacts §1A](../../references/workflow-artifacts.md#1a-conditional-erd-selection--ownership-seam): logical entities/identity, relationships/cardinality/optionality, integrity/ownership/lifecycle, traceability. Produce physical PK/FK/index/deletion design only when storage choices warrant it. Reuse an adequate separate existing model; otherwise record scoped skip/N/A with a reason in `details.erd_selection`. The Blueprint owns boundaries/components/flows/domain invariants and links the ERD; the ERD owns persistent entities/relationships; FRD retains behavior plus payload schema types/validation and links the ERD; techstack references the ERD for the storage model. Do not duplicate data authority, invent a schema, or authorize migrations. Selection adds no new route or stage, and not every project produces an ERD.
10. Accepted aliases (e.g., `api-contracts.md` for API specifications) are permitted where established, but do not invent uncoordinated template types.
11. **Persist Authoritative Spec Before Tactical Planning:** For multi-step work, persist the proportional authoritative specification (what/why/non-goals/acceptance criteria) before handing off to `daw-plan`, per [Workflow Artifacts §1–§2](../../references/workflow-artifacts.md#1-artifact-set--proportionality). Reuse a current adequate spec — do not duplicate it. If clear user requirements have no written source, the parent records their faithful bounded what/why/non-goals/AC in the chosen spec before planning; the planner cannot invent architecture or business choices. Ambiguity returns to the existing design/clarification route; no new design insertion is created for clear routes.
12. **Blueprint/Domain/Flow Before Physical/UI Design:** Settle Blueprint substance (system context/boundaries, components/responsibilities, primary interaction/data flows, domain invariants, failure/transaction boundaries), domain model, and data-flow/lifecycle — including the conditional ERD selection above — before physical (database/schema) or UI design. Physical design, UI mocks, and schema choices do not precede the domain/flow foundations unless the user supplies an explicit alternative direction.
13. Persist settled specifications, domain definitions, and ADRs strictly within authorized document scope.

### Step 6: Builder-Readiness Assessment & Seam Inspection

1. For substantive designs, inspect consumer boundaries material to downstream implementation per [Builder-Readiness Protocol](references/builder-readiness.md):
   - **Interface & Boundary Seams:** Material consumer contracts, ingress/egress payloads, and schema types (without requiring internal private function signatures).
   - **Relevant Error Topologies:** Explicit failure conditions and error contracts where relevant (without mandating unneeded retries or fallbacks).
   - **State & Concurrency Invariants:** Atomic boundaries, consistency rules, and race condition mitigations where concurrency or shared state warrants it.
   - **Verifiable Acceptance Seams:** Deterministic, observable pass/fail criteria with verifiable evidence hooks.
   - **Conditional ERD Readiness Seam:** Verify the ERD selection decision: a selected ERD is present with entities/identity, relationships/cardinality/optionality/ownership, and integrity/lifecycle/traceability (physical design only when storage choices warrant it) and is linked from Blueprint/FRD/techstack; or `details.erd_selection` records a scoped skip/N/A or reuse of an adequate existing model. An unresolved persistent-model gap blocks only data-dependent handoff; projects without an applicable persistent model are not forced to produce an ERD, and no new route or stage is added.
   - **Mockup Readiness Seam (UI-Affecting Work):** For new or changed visual UI, additionally verify per [Workflow Artifacts §5](../../references/workflow-artifacts.md#5-mockup-timing-proof--na): an inspectable rendered mockup source or durable design reference plus a visual preview exists, derived from settled domain/flow and the existing design source/tokens; the mockup links relevant REQ/AC/screen IDs and covers relevant screens, behavior states, viewports, and focus/keyboard design (design review coverage, not runtime proof); the preview was produced with a real available tool (browser/design/export capability) — no vendor mandate, and prose/ASCII/wireframe-only is not a substitute. Missing direction or available capability blocks only the affected UI scope; other non-UI scopes proceed. Record `N/A` with scoped rationale when there is no UI or small nonvisual fixes reuse existing matching design without a redundant mockup. Design may plan mockup creation within authoring; readiness then specifically blocks UI implementation absent a reviewed current mockup, without creating a new route or forcing a full-catalog bundle. The mockup ref is recorded as a section inside an existing canonical kind or as the plan's design artifact — the mockup remains a non-kind artifact; the separate ERD is the conditional 14th kind, not the mockup.
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

Use [routing §5: Canonical Module Handoff Contract](../../references/routing.md#5-canonical-module-handoff-contract) for the complete outer JSON schema and transport. Deliver the actual, inspectable envelope to the parent before any downstream transition; a concise direct-human report does not replace that handoff. Do not dump the envelope into normal user replies or create unrequested transport files.

### Design Details Contract

Preserve these module-specific fields under `details`, using empty collections or explicit not-applicable explanations for waived work rather than inventing findings:

- `architectural_summary`, `target_specifications`, `key_invariants`, and `explicit_non_goals`: grounded design, relevant artifact paths, boundaries, and exclusions.
- `erd_selection`: `{selected: bool, ref: "path or null", reason: "one-line scoped reason", reuse_existing: bool}` — `selected: false` records scoped skip/N/A (or reuse of an adequate separate existing model); `selected: true` links the separate ERD to Blueprint/FRD/techstack per [Workflow Artifacts §1A](../../references/workflow-artifacts.md#1a-conditional-erd-selection--ownership-seam).
- `evaluated_alternatives`: material choices with `chosen`, `alternative`, and `rationale`; empty when alternatives are waived.
- `domain_modeling`: `disambiguated_terms`, `adr_references`, and `convention_path`, respecting domain/ADR gates and repository conventions.
- `builder_readiness`: `substantive_design`, `seams_checked`, `blocking_unknowns`, `safe_reversible_choices`, `mockup_readiness`, and `readiness_verdict`; disclose waived inspection for localized work. `mockup_readiness` is `{required: bool, status: "reviewed"|"na"|"blocked", ref: "path or null", req_ac_screen_ids: [...], states_viewports_focus: "...", capability: "actual available tool or null", blocks_ui_only: bool}` — `required: false` with scoped rationale for no-UI/small nonvisual reuse; `blocked` only when the affected UI scope lacks direction/capability.
- `interface_contracts`: material consumer inputs/outputs and failure contracts, with provenance for unsettled proposals.
- `consequential_decisions`: `requires_user_approval` and `items`, kept separate from routine author decisions and operational authorization.
- `sync_impact_report`: `version_change`, `modified_principles`, `added_sections`, `removed_sections`, and `downstream_artifacts_to_sync` when governance or foundations change.
- `next_actions`: deferred implementation/non-governance intents; include `elicitation_updates` and decision state/open questions when answer reinjection or grilling applies.

Compact illustrative `details` (not a complete handoff):

```json
{
  "architectural_summary": "Rotate single-use refresh tokens in the existing session ledger.",
  "target_specifications": ["docs/specs/blueprint.md"],
  "key_invariants": [
    "Single-use refresh tokens",
    "No plaintext token persistence"
  ],
  "explicit_non_goals": ["Third-party OAuth providers"],
  "evaluated_alternatives": [
    {
      "chosen": "Session ledger",
      "alternative": "Stateless claims",
      "rationale": "Immediate revocation requires retained session state"
    }
  ],
  "domain_modeling": {
    "disambiguated_terms": ["RefreshToken", "SessionStore"],
    "adr_references": [],
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
    "safe_reversible_choices": [],
    "mockup_readiness": {
      "required": false,
      "status": "na",
      "ref": null,
      "req_ac_screen_ids": [],
      "states_viewports_focus": "no UI in scope",
      "capability": null,
      "blocks_ui_only": false
    },
    "readiness_verdict": "ready_for_planning"
  },
  "interface_contracts": "POST /api/v1/auth/refresh -> {access_token: string, refresh_token: string}",
  "consequential_decisions": { "requires_user_approval": false, "items": [] },
  "sync_impact_report": {
    "version_change": "1.0.0 -> 1.1.0",
    "modified_principles": [],
    "added_sections": ["Token refresh invariants"],
    "removed_sections": [],
    "downstream_artifacts_to_sync": [
      "docs/specs/roadmap.md",
      "docs/specs/qa.md"
    ]
  },
  "next_actions": []
}
```

`status: "pass"` proposes satisfaction of design-stage criteria only: specification completeness and applicable seam inspection, not parent acceptance, implementation, deployment, or runtime proof. Follow §7 for advisory routing; never self-dispatch.

---

## 5. Exit Criteria & Quality Checklist

Before finalizing handoff from `daw-design`, verify:

- [ ] Formal specs derived from canonical root templates (`../../templates/`).
- [ ] Domain vocabulary grounded in observable codebase facts; newly proposed concepts explicitly marked with recommendation provenance.
- [ ] Existing project specification and ADR path conventions respected (no forced generic paths).
- [ ] Consequential user decisions segregated from routine engineering decisions.
- [ ] For substantive designs, builder-readiness seams evaluated with zero unresolved blocking unknowns; ERD selection decision explicit in `details.erd_selection` (selected ERD linked per ownership seam, or scoped skip/N/A/reuse); mockup readiness seam evaluated for UI-affecting work (`reviewed` ref + preview, or scoped `N/A`, or UI-only `blocked`).
- [ ] Changed architectural decisions supersede rather than rewrite historical records.
- [ ] Input classified per Scope Guard; non-governance/implementation requests extracted to `next_actions` without source code mutations.
- [ ] Governance or principle changes include structured sync impact reporting with downstream artifacts flagged for synchronization.
- [ ] Feature requirements structured as prioritized, independently testable user journeys (P1, P2...) with EARS oracles per [EARS Semantic Guidance](../../references/document-quality.md#acceptance-criteria-ears); authoritative spec persisted before tactical planning per [Workflow Artifacts](../../references/workflow-artifacts.md).
- [ ] Canonical shared delivery contract (`references/document-quality.md#feature-delivery-contract` sections A, B, and C) satisfied.
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
