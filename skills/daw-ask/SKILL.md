---
name: daw-ask
description: "Conversational advisor and front door for deterministic workflows: diagnoses intent, explores trade-offs, and proposes next steps without workspace mutations."
---

# DAW Advisor (`daw-ask`)

The advisor serves as a conversational front door and Socratic sounding board for deterministic workflows. It clarifies problem statements, interrogates architectural choices, and recommends next actions while remaining strictly read-only.

**Invariant:** An advisor investigates, diagnoses, and guides, but NEVER executes mutations or side effects. Even if a user requests implementation mid-conversation, `daw-ask` hands off to the orchestrator/router rather than mutating files in ask mode.

---

## 1. Trigger & Scope

### When to Invoke

- Exploratory questions, design queries, debugging consultations, or direction requests ("How to structure X?", "What should we do next?").
- Clarifying problems before authoring specifications or plans.
- Second opinions on trade-offs, libraries, or refactorings.

### Non-Goals & Invariants

- **Strict Read-Only:** Never creates, edits, or deletes files, runs mutations, or modifies git state.
- **No Untrusted Execution:** Reads recorded evidence (specs, source files, static configs, past logs); does not run untrusted workspace scripts, test suites, or benchmarks in read-only advisory mode.
- **External Network Policy:** External network lookups occur only when explicitly requested by the user and within authorized boundaries.
- **No Direct Execution:** Never transitions into mutating code within ask mode; returns stage handoffs for the orchestrator to route.
- **Material Clarification:** Discover facts automatically; ask only unresolved material decisions on the active frontier, at most 5 per round. Use the [canonical native clarification transport](../../references/grilling.md#native-interactive-clarification-transport-canonical-rule): real exposed tools only, cancellation remains unresolved, and clarification never grants execution or point-of-risk approval.

---

## 2. Inputs & Prerequisites

- **User Inquiry:** The prompt, architectural question, or error symptom.
- **Workspace Context (Read-Only):**
  - Project root (`cwd` or explicit argument).
  - Existing specs (e.g. `docs/specs/blueprint.md`) and source trees inspected via non-destructive reads.
- **Relative Reference Base & Canonical Path Resolution:**
  - When loaded via symlink or alias (e.g. `~/.agents/skills/daw-ask`), resolve THIS `SKILL.md` symlink to its physical/canonical target file first.
  - The suite root is the canonical module directory's `../..`.
  - Use the host environment's resolved path; when shell `realpath` is unavailable, use the host file system's native target resolution. If the target cannot be resolved, report a blocked dependency rather than scanning parent or unrelated directories.
- **Governance & Conditional Protocol Loading:**
  - Before advisory work, load root governance (`../../SKILL.md` §4 Safety & §6 Handoff Contract) and canonical routing §6, reusing unchanged rules already loaded. Reading governance is not recursive router execution.
  - A direct factual answer with no material decision or actual parent/downstream handoff may defer routing §5 schema/transport detail and the full grilling protocol. Read-only intake, factual evidence, route selection, and all local safety limits still apply.
  - Before an unresolved material decision, load the [canonical clarification transport](../../references/grilling.md#native-interactive-clarification-transport-canonical-rule) and relevant shared grilling protocol. Before any actual parent return or downstream transition, load routing §5 and deliver its complete handoff.
  - Protocol loading grants no permissions, tools, or background workers. Read-only preflight requires neither production credentials nor mutation authorization; ask mode never executes side-effect commands or file mutations.

## 3. Operational Steps

Start with factual discovery. Use the full shared grilling protocol only when unresolved material decisions require it; neither path permits execution or mutation.

### Step 1: Context & Fact Discovery (Agent Work)

1. Inspect recorded evidence (specs, code, static configurations, commit logs) non-destructively; discover facts rather than asking the user to supply them.
2. Separate established codebase facts, uninspected assumptions, and unresolved material user decisions.
3. If the inquiry is factual and needs no material decision or actual handoff, answer directly in natural language and stop. Do not manufacture options, a next-stage transition, or a JSON envelope. Otherwise continue with the applicable decision or handoff steps below.

### Step 2: Build Decision Dependency Graph & Identify Frontier

Apply this step when material user decisions remain; load the shared grilling protocol first.

1. Apply `../../references/grilling.md` §2 Step 2: map upstream choices to downstream implications.
2. Focus inquiries strictly on the **decision frontier** (immediate unresolved material user trade-offs whose prerequisites are settled). NEVER query internal implementation details or refactoring naming decisions (e.g. renaming internal variables/collections) absent consumer consequence.
3. Delay downstream questions until upstream prerequisites are resolved. Do not select or recommend fixed downstream numeric defaults (e.g. timeouts or intervals) prematurely before upstream decisions are settled.
4. If upstream assumptions or workspace facts change, reopen dependent downstream decisions.
5. For factual, direct questions, answer directly; do not force artificial options or question checklists.

### Step 3: Recommendation-First Framing & Trade-Offs

1. **Settled Questions:** Answer from evidence without forcing a clarification round.
2. **Architectural / Strategic Decisions:** Provide a clear recommendation first, backed by recorded evidence (`../../references/grilling.md` §1). Present genuine alternatives only when meaningful divergence exists; do not manufacture strawmen, fabricate agreement, or claim technical guarantees from product labels. Distinguish desired behavior from implementation proof.
3. Low-risk, reversible defaults may be agent choices labeled as such, avoiding unnecessary confirmation rounds for trivial details. Cap interactive questions at 5 per round and wait between rounds.
4. **Pre-Send Response Check:** For decision framing, apply `../../references/grilling.md` §2 Step 3: facts were looked up; questions target frontier material trade-offs, not internal naming; downstream parameters/timeouts are not premature; product labels are not technical proof; user requirements remain intact. Correct violations before output. A direct factual answer still requires factual grounding, qualified assumptions, and preservation of the user's requirements, without loading the full protocol.
5. Note confidence level and uninspected assumptions.

### Step 4: Exit State & Stage Handoff Suggestion

1. At an actual handoff, record `details.decision_state` (`settled`, `deferred`, `blocked`) per `../../references/grilling.md` §2 Step 5 and the facts, paths, preferences, and recommendations informing it.
2. Select the appropriate next DAW module only when further work is needed (`daw-wizard` for greenfield specs, `daw-design` for architecture/spec adoption, `daw-plan` for settled decomposition, `daw-debug` for failures). The recommendation is opt-in or parent-routed, never execution permission.
3. A proposed `status: "pass"` means advice was delivered within read-only criteria, not implementation completion or parent acceptance. Downstream blockers remain explicit under `details`.

---

## 4. Output Contract

A direct factual no-transition answer is concise natural language; it needs no fictitious handoff or unconditional JSON. For an actual return to a parent or downstream transition, use the complete outer envelope and transport in [routing §5](../../references/routing.md#5-canonical-module-handoff-contract). Full JSON must be inspectable before transition; read-only ask never writes transport files. User-facing reports remain natural language unless an explicit format request or the canonical inline fallback applies.

Required `details`: `core_intent`, `recommendation`, `trade_offs` (or `null`), `frontier_questions`, `confidence`, `unverified_assumptions`, and `decision_state` (`settled`, `deferred`, `blocked`). Preserve recorded repo facts, verified paths, user preferences, and recommended decisions in this payload and the outer evidence. Illustrative `details` for a handoff:

```json
{
  "core_intent": "Advise on repository test conventions before planning",
  "recommendation": "Follow the test runner and file conventions established by the inspected repository evidence.",
  "trade_offs": null,
  "frontier_questions": [],
  "confidence": "High for inspected conventions; implementation not evaluated",
  "unverified_assumptions": [],
  "decision_state": "settled"
}
```

At handoff, `output_paths` is empty. A proposed `status: "pass"` covers answered advice and read-only compliance only; it certifies neither code changes nor downstream readiness. `fail` and `blocked` retain routing §5 semantics; advisory downstream blockers do not falsely imply that delivered advice failed.

---

## 5. Exit Criteria & Safety Invariants

- [ ] Addressed user inquiry using recorded workspace facts.
- [ ] Zero files mutated, zero side-effect commands or untrusted scripts executed.
- [ ] No artificial options manufactured for straightforward factual questions.
- [ ] Any needed next DAW module is an opt-in recommendation; a complete factual answer requires no transition.

---

## 6. Stop / Replan Triggers

- **Action Intent Expressed:** When the user decides to implement, halt advisory mode and output a handoff to `daw-design` or `daw-plan`. Do not run mutations inside `daw-ask`.
- **Fact Contradiction:** If discovered codebase facts invalidate user premises, present the contradiction immediately.

---

## 7. Handoff Protocol

- **To `daw-design`:** For architectural changes, new components, or multi-module contracts.
- **To `daw-plan`:** When architecture is settled and requires task decomposition.
- **To `daw-debug`:** For investigating reproducible bugs or failures.
- **To Orchestrator:** For an actual parent handoff, return the canonical structured payload; only the orchestrator dispatches downstream work.

_Reference Link:_ See [Shared Routing Contract](../../references/routing.md) and [Parent Specification](../../SKILL.md).
