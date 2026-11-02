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
- **Mandatory Governance Loading:**
  - Before executing any phase work, load root governance (`../../SKILL.md` §4 Safety & §6 Handoff Contract Schema) and canonical routing (`../../references/routing.md` §5 & §6). Reading governance documentation is not recursive router execution.
  - `daw-ask` is strictly conversational/advisory and read-only. It never performs file mutations or executes side-effect commands. Preflight evaluation confirms read-only scope without requiring production credentials or mutating authorizations.

## 3. Operational Steps

### Step 1: Context & Fact Discovery (Agent Work)

1. Inspect recorded evidence: read existing specifications, configuration files, and code.
2. Separate established codebase facts from open design uncertainties.
3. Distinguish facts the agent can inspect from decisions belonging exclusively to the user.

### Step 2: Build Decision Dependency Graph & Identify Frontier

1. Map upstream choices to downstream implications.
2. Focus questions strictly on the **decision frontier** (immediate unresolved items whose prerequisites are settled).
3. For factual, direct questions, answer directly; do not force artificial options or question checklists.

### Step 3: Recommendation-First Framing & Trade-Offs

1. **Direct Questions:** Provide a grounded, factual answer directly.
2. **Architectural / Strategic Decisions:** Provide a clear recommendation first, backed by recorded evidence. Present genuine alternatives only when meaningful divergence exists; do not manufacture strawmen.
3. Propose sensible, reversible defaults where low risk allows progress.
4. Note confidence level and uninspected assumptions.

### Step 4: Formulate Stage Handoff Suggestion

1. Record established facts, verified paths, and agreed principles.
2. Propose the next appropriate DAW module (`daw-design`, `daw-plan`, `daw-debug`, etc.) for user approval or orchestrator routing.

---

## 4. Output Contract

Every completion of `daw-ask` delivers a structured handoff payload adhering to the canonical suite envelope. Rich diagnostic summaries, recommendations, and frontier trade-offs are preserved under `details`:

```json
{
  "objective": "Answer user query regarding repository test runners and architectural patterns.",
  "input_paths": ["package.json", "docs/specs/blueprint.md"],
  "output_paths": [],
  "acceptance_criteria": [
    {
      "criterion": "Address user query accurately using recorded workspace facts",
      "status": "pass"
    },
    {
      "criterion": "Zero file modifications or state-mutating commands executed",
      "status": "pass"
    }
  ],
  "evidence": [
    {
      "reference": "package.json",
      "summary": "Inspected test scripts confirming vitest as configured test framework"
    }
  ],
  "status": "pass",
  "handoff_to": "daw-design",
  "details": {
    "core_intent": "Inquire regarding test runner setup and architectural patterns",
    "recommendation": "The repository uses vitest for unit tests and playwright for e2e tests. New unit tests should follow the *.test.ts convention in tests/.",
    "trade_offs": null,
    "frontier_questions": [],
    "confidence": "High",
    "unverified_assumptions": []
  }
}
```

_(Note: `status: "pass"` indicates that the advisory inquiry has been answered and read-only criteria satisfied; it does not indicate implementation or code mutation. Empty `output_paths` is standard for read-only advisory responses)._

---

## 5. Exit Criteria & Safety Invariants

- [ ] Addressed user inquiry using recorded workspace facts.
- [ ] Zero files mutated, zero side-effect commands or untrusted scripts executed.
- [ ] No artificial options manufactured for straightforward factual questions.
- [ ] Recommended next DAW module provided as an opt-in handoff.

---

## 6. Stop / Replan Triggers

- **Action Intent Expressed:** When the user decides to implement, halt advisory mode and output a handoff to `daw-design` or `daw-plan`. Do not run mutations inside `daw-ask`.
- **Fact Contradiction:** If discovered codebase facts invalidate user premises, present the contradiction immediately.

---

## 7. Handoff Protocol

- **To `daw-design`:** For architectural changes, new components, or multi-module contracts.
- **To `daw-plan`:** When architecture is settled and requires task decomposition.
- **To `daw-debug`:** For investigating reproducible bugs or failures.
- **To Orchestrator:** Return structured handoff payload; orchestrator executes downstream dispatch.

_Reference Link:_ See [Shared Routing Contract](../../references/routing.md) and [Parent Specification](../../SKILL.md).
