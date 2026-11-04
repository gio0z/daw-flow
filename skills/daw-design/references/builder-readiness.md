# Builder-Readiness Assessment Protocol

This reference defines the builder-readiness assessment protocol for `daw-design`. It guides design agents in evaluating architectural specifications so downstream implementers (`daw-plan` and `daw-build`) receive complete, unambiguous, and executable boundaries without unresolved blocking seams.

_Reference Links:_

- [Shared Grilling Protocol](../../../references/grilling.md)
- [Domain Modeling Protocol](domain-modeling.md)
- [Parent Design Specification](../SKILL.md)
- [Shared Routing Reference](../../../references/routing.md)
- [Root Governance Specification](../../../SKILL.md)

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
  "seams_checked": ["interfaces", "error_handling", "concurrency", "acceptance_criteria"],
  "blocking_unknowns": [],
  "safe_reversible_choices": [
    "Default HTTP client timeout set to 15 seconds"
  ],
  "readiness_verdict": "ready_for_planning"
}
```

If material blockers exist, set `readiness_verdict: "blocked"` and `status: "blocked"`, documenting the specific blocking items in `details`.
