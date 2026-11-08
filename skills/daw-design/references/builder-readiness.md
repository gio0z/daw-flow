# Builder-Readiness Assessment Protocol

This reference defines the builder-readiness assessment protocol for `daw-design`. It guides design agents in evaluating architectural specifications so downstream implementers (`daw-plan` and `daw-build`) receive complete, unambiguous, and executable boundaries without unresolved blocking seams.

_Reference Links:_

- [Shared Grilling Protocol](../../../references/grilling.md)
- [Domain Modeling Protocol](domain-modeling.md)
- [Parent Design Specification](../SKILL.md)
- [Shared Routing Reference](../../../references/routing.md)
- [Root Governance Specification](../../../SKILL.md)
- [Workflow Artifacts (Persistence, Ownership & Mockup Contract)](../../../references/workflow-artifacts.md)
- [Acceptance Criteria / EARS Semantic Source](../../../references/document-quality.md#acceptance-criteria-ears)

---

## 1. Core Principles

1. **Structural Soundness, Not Runtime Proof:**
   - Builder-readiness verifies that consumer boundaries, material contracts, and acceptance seams are well-defined.
   - It does NOT claim empirical test execution, deployment verification, or performance benchmarks (which belong to `daw-verify`).
   - A design `pass` verdict indicates specification completeness, not executed software.

2. **Proportional Inspection:**
   - Full seam inspection applies only to substantive designs (new services, modified data schemas, multi-module refactoring).
   - Minimal, routine, or localized changes skip formal builder-readiness assessment.

3. **No Recursive Dispatch:**
   - Loading this protocol grants no automated execution privileges. `daw-design` never dispatches sub-modules recursively.
   - If independent review is warranted for high-risk designs, recommend delegation to `daw-review` to the parent orchestrator via [Shared Routing](../../../references/routing.md).

---

## 2. Material Implementer Seam Inspection

For substantive designs, inspect consumer boundaries material to downstream implementation without prescribing internal helper mechanics:

### 1. Material Interface Boundaries

- **Check:** Are public ingress/egress payloads, schema changes, and external consumer contracts specified with concrete types and invariants?
- **Scope Rule:** Specify boundaries material to consumers; do NOT mandate specifying every internal private function signature or helper decomposition.

### 2. Relevant Error Topologies

- **Check:** When the design introduces network calls, external dependencies, or persistence mutations, are failure conditions and expected error responses documented?
- **Scope Rule:** Document failure modes where relevant to the architecture; do NOT mandate redundant retry or fallback mechanisms when requirements do not call for them.

### 3. State & Concurrency Invariants

- **Check:** If the design involves concurrent mutations, shared resources, or multi-step database writes, are atomic boundaries and consistency rules stated?
- **Scope Rule:** Address race conditions and transaction boundaries only when the problem domain or concurrency profile warrants it; do NOT mandate locks for single-threaded or stateless flows.

### 4. Verifiable Acceptance Seams

- **Check:** Are acceptance criteria defined as observable pass/fail checks linked to concrete outputs, paths, or response codes?
- **EARS Anchor:** Author acceptance criteria per the canonical [EARS Semantic Guidance](../../../references/document-quality.md#acceptance-criteria-ears) (observable condition/response/oracle; Given/When/Then equivalent). Do not invent competing local persistence/format rules.

### 5. Conditional ERD Readiness Seam

- **Check:** Is the ERD selection decision explicit in `details.erd_selection`: a selected ERD (`erd`, default `erd.md`) covering entities/identity, relationships/cardinality/optionality/ownership, and integrity/lifecycle/traceability — with physical PK/FK/index/deletion design only when storage choices warrant it — and linked from Blueprint/FRD/techstack; or a scoped skip/N/A with reason, or reuse of an adequate separate existing model?
- **Ownership Seam:** Blueprint owns boundaries, components, flows, and domain invariants and links the ERD; the ERD owns persistent entities/relationships; FRD retains behavior plus payload schema types/validation and links the ERD; techstack references the ERD for the storage model. No invented schema, migration authorization, or duplicated data authority.
- **Scoped Blocking:** An unresolved persistent-model gap blocks only data-dependent handoff. Projects without an applicable persistent model are not forced to produce an ERD; selection adds no new route or stage.

### 6. Mockup Readiness Seam (UI-Affecting Work Only)

For new or changed visual UI, additionally verify per [Workflow Artifacts §5](../../../references/workflow-artifacts.md#5-mockup-timing-proof--na):

- **Check:** Does an inspectable rendered mockup source or durable design reference plus a visual preview exist, derived from settled blueprint/domain/flow and the existing design source/tokens? Does it link relevant REQ/AC/screen IDs and cover relevant screens, behavior states, viewports, and focus/keyboard design? Was the preview produced with a real available tool (browser/design/export capability) — no vendor mandate?
- **Not Runtime Proof:** Mockup review covers design intent across states/viewports/focus/keyboard; it is not runtime implementation proof and not automatic human approval.
- **No Text Substitute:** Prose, ASCII, or wireframe-only descriptions do not satisfy the mockup requirement.
- **Scoped Blocking:** Missing direction or unavailable capability blocks only the affected UI scope; non-UI scopes proceed. Do not halt the whole workflow for a UI-only gap.
- **Explicit N/A:** Record `N/A` with scoped rationale when there is no UI or small nonvisual fixes reuse existing matching design without a redundant mockup.
- **Planning vs. Readiness:** Design may plan mockup creation within authoring; readiness then specifically blocks UI implementation absent a reviewed current mockup. This adds no new route and forces no full-catalog bundle or mandatory ERD.
- **Kind Placement:** The mockup remains a non-kind artifact: it lives as a section/reference inside an existing canonical kind or as the plan's design artifact. The ERD is the separate conditional 14th kind; it is not the mockup.

---

## 3. Decision Classification

Classify remaining open design items deterministically:

- **Blocking Unknown:** Missing business invariant, unverified security constraint, or unresolved contract ambiguity that prevents correct implementation.
  - _Action:_ Halt handoff, mark item `blocked` in handoff details, and resolve via [Shared Grilling Protocol](../../../references/grilling.md) or user escalation. Cannot declare design ready while a material blocker remains.
- **Safe Reversible Choice:** Implementation detail or default with low blast radius (e.g. internal data structure, standard timeout default).
  - _Action:_ Adopt a documented sensible default with rationale; proceed autonomously without interrupting the user.

---

## 4. Readiness Summary in Handoff Details

When builder-readiness is evaluated, record an optional summary under `details.builder_readiness` within the canonical suite handoff payload:

```json
"builder_readiness": {
  "substantive_design": true,
  "seams_checked": ["interfaces", "error_handling", "concurrency", "acceptance_criteria", "erd", "mockup"],
  "erd_selection": {"selected": false, "ref": null, "reason": "no persistent entities or relationships in scope", "reuse_existing": false},
  "blocking_unknowns": [],
  "safe_reversible_choices": [
    "Default HTTP client timeout set to 15 seconds"
  ],
  "mockup_readiness": {"required": false, "status": "na", "ref": null, "req_ac_screen_ids": [], "states_viewports_focus": "no UI in scope", "capability": null, "blocks_ui_only": false},
  "readiness_verdict": "ready_for_planning"
}
```

If material blockers exist, set `readiness_verdict: "blocked"` and `status: "blocked"`, documenting the specific blocking items in `details`. When only the UI-affecting scope is blocked (missing mockup direction/capability), set `mockup_readiness.status: "blocked"` with `blocks_ui_only: true` and keep non-UI readiness separate; do not halt the entire workflow for a UI-only gap. When only the persistent-model (ERD) scope is blocked, record the gap in `details.erd_selection` and keep other readiness separate; do not halt the entire workflow for a data-only gap. Details-level `details.erd_selection` mirrors this object; `details.builder_readiness.erd_selection` is optional duplication for local readability.
