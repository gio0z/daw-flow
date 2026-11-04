# Shared Grilling & Structured Elicitation Protocol

This reference defines the canonical shared grilling protocol for Deterministic Agentic Workflow (DAW). It governs how agent modules (`daw-ask`, `daw-wizard`, and `daw-design`) conduct bounded, hypothesis-driven elicitation, uncover ambiguities, distinguish factual codebase reality from user decisions, track the decision frontier, and resolve material blockers without gratuitous ceremony.

---

## 1. Core Principles & Invariants

1. **Agent Investigation vs. User Decisions:**
   - The agent MUST inspect recorded workspace evidence (reading source files, configurations, existing specifications, and schemas) to discover factual information before asking questions.
   - Questions directed to the operator MUST be reserved strictly for material business requirements, external/consumer contracts, architectural trade-offs, preferences, or domain constraints that cannot be discovered from workspace evidence.
   - **No Internal Implementation / Naming Inquiries:** NEVER query the operator about internal refactoring, variable/field naming (e.g. renaming an internal collection like `self.holds`), or private helper structure absent consumer consequence. Those are autonomous implementation decisions for the builder.
   - Distinguish repo facts (verified from files/configs) from user decisions/preferences (intent, trade-offs) and agent defaults.
   - **Anti-Pattern:** Asking the operator what framework, database library, or directory structure is used when those facts exist in the workspace files.

2. **Bounded Rounds, Question Budgeting & Pacing:**
   - Elicitation proceeds in bounded rounds.
   - Each round MUST contain at most **5 focused questions**.
   - Wait for operator response between rounds.
   - Prioritize questions by impact on observable behavior and contracts.
   - Direct questions, factual consultations, or small settled changes do NOT trigger multi-round grilling ceremony; answer or confirm directly.

3. **Active Decision Dependency Frontier:**
   - Decisions form a directed dependency graph where downstream choices depend on upstream choices.
   - Questions MUST target only the current **frontier**: unresolved material trade-offs whose prerequisites are settled.
   - Delay downstream detail questions until upstream architectural prerequisites are resolved.
   - **No Premature Downstream Defaults:** Downstream numeric parameters, thresholds, or timeouts (e.g. hold expiration duration) MUST NOT be selected or recommended as fixed defaults before the prerequisite upstream decision (e.g. exclusive vs. non-exclusive) is resolved. Downstream defaults must wait, or be presented only as conditional alternatives tied to specific upstream branches.

4. **Reopen Dependent Decisions When Inputs Change:**
   - When upstream inputs, requirements, or verified facts change, downstream decisions and assumptions dependent on them are invalidated.
   - The agent MUST explicitly reopen invalidated decisions and bring them back onto the active decision frontier.

5. **Recommendation-First Framing & Sensible Defaults:**
   - Every question or decision point presented SHOULD lead with a concrete, grounded recommendation backed by recorded evidence or standard patterns.
   - For low-risk, reversible choices, the agent may adopt and label sensible agent defaults without requiring operator confirmation for every trivial detail.
   - Present genuine alternatives with honest trade-offs; NEVER manufacture artificial strawman choices to force agreement.
   - **No Invented Technical Guarantees:** Recommendation rationales cannot claim technical guarantees from a product label (e.g. asserting a pattern eliminates race conditions or guarantees determinism without proof). Distinguish desired behavioral intent from implementation proof, and preserve user-specified requirements across branches rather than dismissing them as unnecessary.
   - NEVER fabricate user agreement or claim an operator made a choice they did not make.

6. **Exit State & Stage-Scoped Blocker Invariant:**
   - Grilling concludes with an internal decision state recorded under `details.decision_state`: `settled`, `deferred`, or `blocked`.
   - The suite handoff envelope status remains standard (`pass`, `fail`, `blocked`).
   - Never report core path as clear (`deferred`) while foundational upstream choices or exclusions remain unresolved.
   - If a material architectural blocker, contradictory constraint, or missing foundational input prevents the current stage from completing, exit with `status: "blocked"`.
   - Stage-scoped evaluation applies: an advisory module (`daw-ask`) can pass its stage (`status: "pass"`) while tracking a material downstream implementation blocker under `details.decision_state: "blocked"` and `details.downstream_blocker`.
   - Non-blocking unknowns are recorded under `details.open_questions` (or in an `## Open Questions` section of generated documents) with owner and resolution trigger.

---

## 2. Operational Protocol Steps

### Step 1: Pre-Question Fact Discovery (Agent Groundwork)

Before framing any questions:

1. Non-destructively inspect relevant workspace files: specs, code, dependencies, build configs, and schemas.
2. Compile verified codebase facts. If an answer exists in workspace files, perform the lookup directly; do not query the operator.

### Step 2: Build the Decision Graph & Identify Frontier

1. Map prerequisite relationships between remaining decisions.
2. Isolate the active frontier: unresolved material trade-offs whose prerequisites are settled. Filter out internal implementation details.
3. Delay downstream parameter or tuning questions until upstream architectural choices are decided. Do not prematurely lock downstream numeric defaults.

### Step 3: Question Formulation & Interactive Round (Budget <= 5)

1. Select at most 5 questions from the active frontier, ordered by behavioral impact.
2. State the recommended choice and rationale. Where low risk permits, state the proposed agent default.
3. **Pre-Send Response Check:** Before transmitting the formulated response to the operator, execute a mandatory pre-send check against the draft:
   - **(1) Fact Sources:** Are any factual questions asked that could be resolved by reading workspace files?
   - **(2) Frontier Material Only:** Are all inquiries focused strictly on unsettled material trade-offs, excluding internal implementation/refactoring naming?
   - **(3) No Premature Parameters:** Are downstream numeric parameters, timeouts, or intervals held back until upstream prerequisite decisions resolve?
   - **(4) No Invented Guarantees:** Does the rationale avoid claiming absolute technical guarantees (e.g. "eliminates race conditions", "guarantees determinism") from mere product patterns without proof? Qualify claims when support is bounded.
   - **(5) Preserve Requirements:** Are user-specified requirements preserved across branches rather than assumed away?
     Correct any detected violations in the draft before sending.
4. Wait for the operator's response before proceeding to downstream questions.

### Step 4: Evaluate Answers & Invalidation Check

1. Update decision state from operator choices and accepted defaults.
2. If the operator's decision contradicts or alters an earlier premise, invalidate dependent downstream nodes and return them to the active frontier.

### Step 5: Exit Classification & Handoff

1. Determine `details.decision_state`:
   - `settled`: Required decisions resolved; proceed to authoring or handoff.
   - `deferred`: Core path clear; non-blocking unknowns captured in open questions. Never use `deferred` if foundational upstream choices remain unresolved.
   - `blocked`: Material blocker halts the current stage.
2. Emit the standard handoff payload with canonical status (`pass`, `fail`, or `blocked`) and decision metadata in `details`.

---

## 3. Concrete Worked Example (Hypothetical Seat Hold)

### Step A: Fact Discovery (Agent Groundwork)

- _Scenario:_ Adding hold expiration to a hypothetical reservation service.
- _Agent Lookup:_ Agent reads existing configuration (`config/reservation.json`) to inspect background cleanup worker intervals.
- _Fact Separation:_ Polling frequency is an existing codebase fact; the agent inspects it directly and avoids querying the operator.

### Step B: Decision Frontier & Question Formulation

- _Upstream Decision (Frontier):_ Does a provisional hold exclusively block other users from selecting the seat, or can multiple users hold the seat until payment?
- _Downstream Dependent Decision (Delayed):_ Hold expiration window. Delay asking or recommending any fixed expiration length until the hold model is settled. Distinguish behavioral requirements from implementation proofs; do not assume expiration is unnecessary or invent technical guarantees from product labels.
- _Round 1:_ Agent asks exclusively about hold exclusivity semantics, presenting trade-offs without assuming checkout funnels or fixing premature numeric timeouts.

### Step C: Answer Evaluation & Downstream Progression

- _Operator Response:_ Operator confirms holds must be exclusive.
- _Frontier Advance:_ Exclusivity is settled, unlocking the expiration duration decision on the frontier.
- _Next Question / Default:_ Only now does the agent evaluate expiration duration, recommending a duration compatible with the inspected cleanup interval.

### Step D: Material Uncertainty Blocker Encountered

- If an external ticketing provider webhook contract is required but entirely undefined in workspace documentation or code:
  - In `daw-design`: Halts specification drafting with canonical `status: "blocked"` until the external contract is provided.
  - In `daw-ask`: Completes advisory review (`status: "pass"`), but records `details.decision_state: "blocked"` and notes the unresolved external API dependency in `details.downstream_blocker`.

---

## 4. Integration Contract with DAW Modules

| Module       | Usage Mode                                            | Constraints                                                                                                                                                                                                                                                                                |
| :----------- | :---------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `daw-ask`    | Conversational advisor, read-only Socratic front door | Evaluates decisions, recommendations, and trade-offs. Strictly read-only; no file mutations. Simple questions answer immediately without multi-round ceremony. May return `status: "pass"` while noting downstream implementation blockers in `details`.                                   |
| `daw-wizard` | Greenfield interactive specification interview        | Applies grilling protocol across 6 greenfield phases. Max 5 questions/round with wait between rounds. Refuses existing codebases (`blocked` -> `daw-design`). Retains DESIGN.md visual style rule and 8-item agent-ready checklist. Cannot declare spec-ready if material blockers remain. |
| `daw-design` | Deep architectural modeling & spec generation         | Applies grilling during architectural trade-offs and domain boundary definition. Evaluates builder-readiness gate before handoff.                                                                                                                                                          |
