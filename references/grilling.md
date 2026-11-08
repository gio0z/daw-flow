# Shared Grilling & Structured Elicitation Protocol

This reference defines the canonical shared grilling protocol for Deterministic Agentic Workflow (DAW). It governs how agent modules (`daw-ask`, `daw-wizard`, and `daw-design`) conduct bounded, hypothesis-driven elicitation, uncover ambiguities, distinguish factual codebase reality from user decisions, track the decision frontier, and resolve material blockers without gratuitous ceremony.

This reference is the **canonical native interactive clarification transport** for all DAW decision workflows. Whenever any DAW module must ask the operator a material question — interview, design decision, setup confirmation, unclear-route intake, or any other decision frontier — it MUST use this transport. It applies beyond the three interview modules named below; do not duplicate a separate questionnaire alongside the same tool call.

**Progressive loading for factual advice:** A direct factual `daw-ask` answer with no material decision or actual handoff/transition need not load the full protocol. Answer from evidence under root `SKILL.md` §4/§6 and the module's read-only/intake rules. Before a material question, load the canonical transport below and the relevant decision-frontier steps; before any actual handoff, load [routing §5](routing.md#5-canonical-module-handoff-contract). No clarification, approval, or mutation authority is implied by this loading exception.

### Native Interactive Clarification Transport (Canonical Rule)

1. **Capability discovery, never assumption:** At the start of a session (or when the harness/toolset changes), the parent MUST discover which interactive question tool the harness actually exposes. Use the tool's real name and real schema as exposed — e.g. a native `clarify` tool when present, or the harness's equivalent `ask` / `question` / `AskUserQuestion` tool under its actual name and fields. NEVER invent, hardcode, or hallucinate a tool name, parameter, or schema; NEVER presume a tool exists because another harness has it. If no interactive question tool is exposed, that is the "native absent" case below.
2. **Ask only material unknowns:** Use the discovered tool ONLY for questions that are (a) material to scope, contracts, architecture, or risk, and (b) not resolvable from workspace evidence. NEVER use it for redundant confirmations, trivial defaults, or facts already established. Keep it to genuinely unresolved decisions.
3. **Pre-tool context (concise, no duplication):** Before the blocking tool call, emit only material decision context that is NOT already visible inside the tool: what is being decided, why it is material, verified facts, and the recommended option/rationale. Do NOT repeat the full alternatives prose, option descriptions, or rationale already shown in the tool (one-form idea — context in chat OR in the tool, never both). The tool call still MUST NOT be the first thing the operator sees.
4. **Bounded, dependency-frontier questions:** At most **5 independent questions per round**; obey any tighter cap the actual tool schema imposes (e.g. a lower per-call limit) — the tighter cap wins. Dependent questions are asked **one at a time** along the active decision frontier (see §1 principle 3); NEVER batch a downstream question whose upstream prerequisite is still unresolved. Wait for the response before the next dependent round.
5. **Tool semantics, not synthesized schema:** Use whatever semantics the actual tool supplies — recommendation/preferred-option highlighting, custom answer, free-text, and multiselect where supported. NEVER synthesize an "Other" option or hardcode a schema when the tool already provides those affordances. Present genuine alternatives with honest trade-offs; no false dichotomies.
6. **Cancellation / no-approval is unresolved, never consent:** If the tool is cancelled, dismissed, skipped, or returned unanswered, treat the question as **unresolved** — NEVER as default consent, NEVER as a "yes," and NEVER as authorization to proceed on that decision. Record it in `details.decision_state` / `details.open_questions` (blocked if material) and continue only with work that does not depend on it.
7. **Approval-bypass prohibition (narrow):** Ordinary preference/selection clarification NEVER bypasses required provider, security, or point-of-risk native controls — those controls still apply where they are required by root `SKILL.md` §4 fail-closed gating. This rule imposes NO new approval gate on low-risk local writes or routine work that required no such control before. Conversely, an explicit user authorization naming the target/scope/action still stands as authorization for that exact action; a preference selection is not blanket approval for actions beyond its scope.
8. **Fallback when native is absent or unavailable:** If no interactive question tool is exposed, or it errors/unavailable mid-session, fall back to concise plain-text questions in chat (still bounded: ≤5, frontier-ordered, recommendation-first, no redundant confirmation). This fallback is the ONLY permitted text-only path; it does not change any other rule above.
9. **Benchmark / file-oracle exception (explicit adapter context only):** The headless `tools/evaluation/wizard_bench.py` runner drives the interview through its file-based oracle transport (`.daw-interview/questions.md` → oracle → `transcript.md`). That transport is a legitimate **non-interactive evaluation adapter** for reproducible measurement and MUST remain intact — it is the sole exception to the native-tool rule, and it applies ONLY when running under that explicitly configured bench/oracle adapter context. It NEVER authorizes replacing native clarification with files in ordinary interactive DAW work.

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
   - **Question Ranking by Impact × Uncertainty:** Rank candidate questions by multiplying the question's observable impact on system boundaries, user journeys, contract definitions, security posture, or test design by the degree of factual uncertainty (unresolvable from codebase inspection). Highest `impact × uncertainty` questions are addressed first.
   - **Dependent Trade-Offs vs. Independent Batching:** When choices have causal dependencies, sequence dependent questions **one at a time** along the active dependency frontier (never query downstream parameters before the upstream prerequisite fork is decided). Independent orthogonal choices may be batched together up to the **5-question limit** per round.
   - Direct questions, factual consultations, or small settled changes do NOT trigger multi-round grilling ceremony; answer or confirm directly.
   - **No False Dichotomies:** Present genuine, viable architectural alternatives with transparent trade-offs. Avoid strawman options designed to force a predetermined conclusion.

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

6. **Safe Answer Reinjection & Read-Only Inquiry Handoff:**
   - Read-only inquiry modules (`daw-ask` or interactive clarification sessions) MUST NOT perform direct specification file writes or mutations.
   - Read-only inquiries capture resolved answers, structured user choices, and proposed exact specification updates in their handoff payload (under `details.elicitation_updates` or canonical handoff).
   - The authoritative authoring module (`daw-wizard` or `daw-design`) is the sole authorized writer. It safely reinjects user answers into authoritative specifications, reconciles conflicting text, updates affected acceptance criteria, cleans up superseded assumptions, and marks remaining unknowns to block only dependent feature paths.

7. **Technical Research Before User Inquiries:**
   - Before asking the operator questions about technical uncertainties, the agent MUST research workspace facts, dependencies, schemas, and official framework patterns.
   - Ground technical choices before querying the user. Record architectural decisions, rationale, alternatives considered, and authoritative citations directly in the appropriate existing specification section (e.g., `techstack.md`, ADR section in architecture docs, or `blueprint.md`) — no mandatory separate `research.md`.
   - Adhere to the canonical shared procedural contract in [Canonical Document Quality & Workflow Transition Guide](document-quality.md#feature-delivery-contract) (specifically [Clarification & Uncertainty Resolution](document-quality.md#b-clarification-and-technical-uncertainty-resolution)).

8. **Exit State & Stage-Scoped Blocker Invariant:**
   - Grilling concludes with an internal decision state recorded under `details.decision_state`: `settled`, `deferred`, or `blocked`.
   - The suite handoff envelope status remains standard (`pass`, `fail`, `blocked`).
   - Never report core path as clear (`deferred`) while foundational upstream choices or exclusions remain unresolved.
   - If a material architectural blocker, contradictory constraint, or missing foundational input prevents the current stage from completing, exit with `status: "blocked"`.
   - Stage-scoped evaluation applies: an advisory module (`daw-ask`) can pass its stage (`status: "pass"`) while tracking a material downstream implementation blocker under `details.decision_state: "blocked"` and `details.downstream_blocker`.
   - Non-blocking unknowns are recorded under `details.open_questions` (or in an `## Open Questions` section of generated documents) with owner and resolution trigger. Ambiguity budget: at most 3 material unresolved decisions per document remain as `[Open Question]` with owner/trigger; everything else is a labeled `[Proposed Default]` assumption in an Assumptions subsection of the provenance ledger.

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
   - **(6) No False Dichotomies:** Are choices genuinely distinct and mutually exclusive with honest trade-offs rather than manufactured strawmen?
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

| Module       | Usage Mode                                            | Constraints                                                                                                                                                                                                                                                                                                                                                                                                              |
| :----------- | :---------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `daw-ask`    | Conversational advisor, read-only Socratic front door | Evaluates decisions, recommendations, and trade-offs. Strictly read-only; no file mutations. Simple questions answer immediately without multi-round ceremony. Returns proposed specification deltas under `details.elicitation_updates` to parent for safe reinjection by authoring modules. May return `status: "pass"` while noting downstream implementation blockers in `details`.                                  |
| `daw-wizard` | Greenfield interactive specification interview        | Applies grilling protocol across 6 greenfield phases. Max 5 questions/round with wait between rounds. Sequences dependent trade-offs 1 at a time; batches independent up to 5. Refuses existing codebases (`blocked` -> `daw-design`). Retains DESIGN.md visual style rule and 8-item agent-ready checklist. Reinjects answers directly into authoritative specs; cannot declare spec-ready if material blockers remain. |
| `daw-design` | Deep architectural modeling & spec generation         | Applies grilling during architectural trade-offs, governance impact sync, and domain boundary definition. Researches technical uncertainties before querying user. Safe reinjection target for answers from `daw-ask` or parent handoff. Evaluates builder-readiness gate before handoff.                                                                                                                                |
