---
name: daw-wizard
description: "Interactive greenfield project specification interview: guides structured elicitation from problem statement to complete architectural specifications with proportional drafting and open question tracking."
compatibility: "Fully self-contained procedural skill; no external dependencies required."
---

# DAW Wizard (`daw-wizard`)

The wizard module conducts a structured, interactive specification interview for greenfield projects. It guides an operator from an initial idea through a progressive multi-phase elicitation, generating proportional specification documents grounded in the canonical 13-document matrix.

**Invariant:** Maintain rigorous interview discipline. Ask at most 5 focused questions per round, propose sensible defaults, adapt depth proportionally to project scale, and record unresolved items in an Open Questions appendix.

---

## 1. Trigger & Scope

### When to Invoke

- Bootstrap intent on a **blank** target directory (no source code and no existing specification documents). It is the first stage of the `bootstrap` route: `daw-wizard` -> `daw-design` -> `daw-plan`.
- Turning a loose concept or raw problem statement into the canonical specification documents through an interview.

### Refusal Conditions

- **Existing code or documents:** If the target contains source files or existing specifications, stop with `status: "blocked"` and hand off to the orchestrator for the `adopt` route (`daw-design`). The wizard never interviews over an existing codebase.
- **No brief at all:** The Phase 1 round is the single material question round. If the operator gives no answer to it, stop `blocked`; never draft documents from nothing.

### Non-Goals & Invariants

- **Interactive Question Pacing & Bounded Rounds:** Ask at most 5 focused questions per round, each with a recommended default. Never overwhelm the user with long interrogations.
- **Question Ranking by Impact × Uncertainty:** Rank candidate questions by multiplying observable impact on system boundaries, user journeys, contract definitions, security posture, or test design by factual uncertainty. Prioritize behavior-changing and contract-defining questions in early rounds regardless of phase.
- **Dependent Trade-Offs vs. Independent Batching:** When choices have causal dependencies, sequence dependent questions **one at a time** along the active decision frontier (upstream scope and architecture before downstream parameters). Independent orthogonal choices may be batched together up to the 5-question limit per round.
- **No Redundant Questions & Fact-First Discovery:** Before each round, inspect workspace evidence and drop every candidate question already answered by the brief, an earlier answer, or a recorded default. Re-asking settled facts is the largest measured precision loss in clarification studies (CONTRA, arXiv 2610.01769).
- **Native Clarify Transport:** Follow [Native Interactive Clarification Transport (Canonical Rule)](../../references/grilling.md#native-interactive-clarification-transport-canonical-rule) for unresolved material user decisions only. Cancel/unanswered remains an Open Question, never default consent; clarification does not replace required provider/security point-of-risk approval.
- **Distinguish Business What/Why from Technical How:** Separate business problems, user journeys, and functional outcomes from technical implementation how. Never invent policies, owners, approvals, or unobservable vanity metrics.
- **Safe Answer Reinjection:** Reinject operator answers directly into drafted specifications, reconcile conflicting requirements, update affected acceptance criteria, and mark remaining unknowns to block only dependent feature scope.
- **Prioritized Feature Slices & Measurable Oracles:** Preserve stable IDs (`US-01`, `PRD-01`, `FRD-01`). Feature requirements must specify prioritized independently demonstrable/testable user stories (P1, P2...) with Given/When/Then or equivalent exact input/output/error/state oracles. Do not force deploy independence for inseparable safety or transaction invariants.
- **Canonical Procedural Contract:** Adhere to the shared delivery contract defined in [Canonical Document Quality & Workflow Transition Guide](../../references/document-quality.md#feature-delivery-contract) (specifically [Governance Alignment](../../references/document-quality.md#a-governance-and-authoring-alignment), [Clarification & Uncertainty Resolution](../../references/document-quality.md#b-clarification-and-technical-uncertainty-resolution), and [Feature Slicing & Behavioral Oracles](../../references/document-quality.md#c-feature-slicing-and-behavioral-contract-oracles)).
- **Visual Style via DESIGN.md:** For projects with a visual UI, do not interview the user about colors, fonts, or spacing. Ask once whether they have a `DESIGN.md` (or an equivalent design system file) to attach.
  - _Attached:_ copy it verbatim to the project root as `DESIGN.md`, treat its tokens as normative, and reference it from the UI specs. Never rewrite or "improve" it.
  - _Declined:_ offer to draft one following the open [DESIGN.md format](https://github.com/google-labs-code/design.md/blob/main/docs/spec.md): YAML front-matter tokens (`colors`, `typography`, `rounded`, `spacing`, `components`) followed by the sections `## Overview`, `## Colors`, `## Typography`, `## Layout`, `## Elevation & Depth`, `## Shapes`, `## Components`, `## Do's and Don'ts` in that order, each section at most once. Derive it from at most 3 questions (brand mood/personality, light/dark and primary color preference, density and target devices) with proposed defaults; use WCAG 2.2 AA contrast unless the user specifies AAA. Present the draft for confirmation before writing it.
  - _Neither:_ record visual style as an Open Question; never invent a brand palette silently.
  - _Headless (CLI, library, API):_ skip DESIGN.md and instead ask once about output style (layout, message wording, formats, colors in terminals). Interviewers most often miss style requirements, so never skip this question.
- **Proportionality Rule:** Adjust document depth to project scale:
  - _Small utility / CLI tool:_ 1–2 pages total across core specs (`blueprint.md`, `techstack.md`).
  - _Medium application:_ 5–10 pages covering standard baseline specs (`blueprint.md`, `prd.md`, `frd.md`, `techstack.md`, `security.md`, `roadmap.md`).
  - _Large distributed platform:_ 10+ pages across full matrices including deployment, QA, and operational runbooks.
- **Open Questions Rule:** Anything unresolved during the interview goes into an explicit `## Open Questions` section with owner and trigger, never left as a hidden assumption. Material facts the operator did not supply are never invented; `skip` or no answer produces an Open Question, while `default` adopts the proposed default and records it as an assumption.
- **Confirmed Document Set:** After Phases 1–2, state which documents will be produced and which are skipped (with a one-line reason each), and obtain operator confirmation before drafting.
- **Creation-Only Mutation:** Writes only new files under the spec directory, plus the project-root `DESIGN.md` when the visual style rule applies. If a target file already exists, stop `blocked` rather than overwrite it.
- **No Premature Implementation & No Premature Spec-Ready:** Does not implement production code or scaffold the project; produces specification artifacts only. Never declares specifications ready if a material architectural blocker remains (`../../references/grilling.md` §1).
- **Workflow Transition Gate vs. Hook Claims:** Specification authoring and handoff follow explicit deterministic workflow transitions (`python3 scripts/validate.py docs RECORD --project-root ROOT --transition TRANSITION --documents PATH [PATH ...] --format text|json`) driven by the orchestrator. It does NOT claim or use automatic harness hook interception, daemon supervisors, or runtime monkeypatching. Trivial or minimal inline work does not require mandatory 13 documents or document-quality JSON records. If Python 3 is unavailable, report canonical `status: "blocked"` (never emit a fake pass).

---

## 2. Inputs & Governance Loader Sequence

### Canonical Path Resolution & Governance Loading

1. **Physical Root Resolution:**
   - Resolve this `SKILL.md` to its canonical physical directory. The suite root is canonical `../..`.
   - Resolve all relative links (`../../references/...`, `../../templates/...`, `../../SKILL.md`) relative to the physical module directory.
2. **Mandatory Governance Loading:**
   - Before executing interview work, load root governance (`../../SKILL.md` §4 Safety & §6 Handoff Contract Schema) and canonical routing (`../../references/routing.md` §5 & §6).
   - Load the canonical shared grilling protocol (`../../references/grilling.md`) for structured elicitation, bounded question rounds (<=5 questions/round), active decision frontier management, and blocker escalation. Loading protocol references grants no additional permissions or tools and spawns no background workers.
   - Before writing specification files to disk, load `../../references/operations.md` §1 Preflight Safety & §2 High-Risk Approvals.
   - Respect repository spec conventions from DAW configuration if present (default: `docs/specs/`).
   - Read [Canonical Document Quality & Workflow Transition Specification](../../references/document-quality.md) and adhere to its shared procedural contract (`references/document-quality.md#feature-delivery-contract`) whenever authoring formal specifications across the 13-document matrix.

---

## 3. Operational Steps: Interview Phases & Templates

The interview proceeds across 6 structured phases. Each phase corresponds to canonical templates located in `../../templates/`:

| Phase                                    | Focus Area                                                                                                                            | Canonical Specification Templates                                                                                                                                                     |
| :--------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **1. Problem & Scope**                   | Target users, core problem, non-goals, commercial objectives                                                                          | [brd.md](../../templates/brd.md), [prd.md](../../templates/prd.md)                                                                                                                    |
| **2. System Architecture**               | Domain model, invariants, component boundaries, data flow                                                                             | [blueprint.md](../../templates/blueprint.md), [frd.md](../../templates/frd.md)                                                                                                        |
| **3. Tech Stack & Invariants**           | Languages, frameworks, data stores, external APIs, hard constraints                                                                   | [techstack.md](../../templates/techstack.md)                                                                                                                                          |
| **4. UX & Visual Style** _(Conditional)_ | Interaction flows and wireframes; visual identity through the user's `DESIGN.md` or a drafted one; CLI/API output style when headless | [ui-ux.md](../../templates/ui-ux.md), [wireframe.md](../../templates/wireframe.md), root `DESIGN.md` ([format](https://github.com/google-labs-code/design.md/blob/main/docs/spec.md)) |
| **5. Security & Operations**             | Threat modeling, sensitive data, deployment topology, observability                                                                   | [security.md](../../templates/security.md), [deployment.md](../../templates/deployment.md), [runbook.md](../../templates/runbook.md)                                                  |
| **6. Verification & Phasing**            | Acceptance criteria, test strategy, milestones, release plan                                                                          | [qa.md](../../templates/qa.md), [roadmap.md](../../templates/roadmap.md)                                                                                                              |

_(Note: User-facing UI specifications in Phase 4 are omitted for headless CLI or pure API projects per suite omission rules)._

### Step-by-Step Procedure

1. **Phase Elicitation & Grilling Protocol:** For each phase, apply `../../references/grilling.md`: ask at most 5 high-leverage, behavior-changing questions with proposed defaults, applying the redundancy filter and behavior-first ranking above. Wait for operator response between rounds. Sequence questions along the active decision frontier (Phases 1–2 upstream scope and architecture before downstream operational details; delay prerequisite-dependent questions until upstream prerequisites are settled). Accept `default` (adopt the proposal) or `skip` (record an Open Question). In Phase 4, handle visual style with the DESIGN.md rule (attach, or draft to the standard, or Open Question); headless projects skip wireframes and DESIGN.md but still get the output-style question.
2. **Document Set Confirmation & Intake Gate:** After Phase 2, propose the proportional document set (avoiding fixed mandatory 13-document sets) and confirm it before drafting. The parent/orchestrator establishes the objective, audience, scope, empirical sources, and supplies the expected `--documents` list, executing the intake transition check:
   `python3 scripts/validate.py docs <RECORD> --project-root <ROOT> --transition intake-authoring --documents <DOC_PATH> [<DOC_PATH> ...] --format text|json`
   Formal drafting begins only when intake transition eligibility is satisfied.
3. **Drafting Specifications & Scoped Reader Questions:** Apply the Authoritative Documentation Authoring Contract (`../../references/routing.md` §3):
   - For each confirmed document, read its matching routing specification entry, canonical template at `../../templates/<doc>.md`, and the scoped reader questions from [Canonical Document Quality & Workflow Transition Specification](../../references/document-quality.md) and `references/document-quality-rubric.json` (DQ-01 to DQ-05 plus kind-specific criteria).
   - Ground all content in operator interview responses, confirmed scope, and explicit defaults. Templates define structural headings, not factual evidence; never invent synthetic data or unverified external claims.
   - Create the confirmed documents in the spec directory (`spec_dir` from a `<!-- daw-config:start -->` block if present, else `docs/specs/`).
   - When drafting finishes, author emits:
     `python3 scripts/validate.py docs <RECORD> --project-root <ROOT> --transition authoring-review --documents <DOC_PATH> [<DOC_PATH> ...] --format text|json`
4. **Review, Ready Transition & Agent-Ready Checklist:**
   - Downstream handoff to `daw-design` requires parent/reviewer evaluation of semantic content and evidence (author self-grading pass is rejected). Upon review acceptance (`decision: "accepted"` across all required criteria), execute:
     `python3 scripts/validate.py docs <RECORD> --project-root <ROOT> --transition review-ready --documents <DOC_PATH> [<DOC_PATH> ...] --format text|json`
   - If any required criterion is rejected, execute `review-rework`, update documents, and re-enter via `rework-review`.
   - Any modification to specification text alters its SHA-256 hash and invalidates prior `review-ready` eligibility.
   - QA review limitation: human comprehension testing remains unexercised without live people; automated review evaluates structural and evidence compliance only.
   - Jointly verify the document set covers all 8 agent-ready items: (1) goal, (2) in/out of scope, (3) inputs and outputs with types and exact names (entry points, commands, files), (4) data and persistence changes, (5) edge cases and error behavior, (6) executable acceptance criteria, (7) constraints (performance, security, compatibility), (8) no-change list. If material blockers or unresolvable contradictions remain, halt with `status: "blocked"` per `../../references/grilling.md` §1; never prematurely declare spec-ready. Any non-blocking item the interview did not settle becomes an Open Question, not an invented value.
5. **Capture Open Questions:** Append an `## Open Questions` section to each generated document listing pending items, impact, owner, and resolution trigger.
6. **Handoff Formulation:** Hand off to `daw-design` (next bootstrap stage). Report the checklist coverage (`details.agent_ready_checklist`) and recommend `daw-setup` in `details.recommended_next_step` so the conventions decided in the interview (spec directory, stack commands) get recorded.

---

## 4. Output Contract

Use [routing §5: Canonical Module Handoff Contract](../../references/routing.md#5-canonical-module-handoff-contract) for the complete outer JSON schema and transport. Deliver the actual, inspectable envelope to the parent before the next bootstrap stage; concise direct-human interview reports do not replace that handoff. Do not dump envelopes into normal user replies or create unrequested transport files.

### Wizard Details Contract

Preserve under `details`:

- `project_name`, `scale_classification`, and `generated_specifications`: interview identity, proportional depth, and actual created artifact paths.
- `open_questions_count` and `open_questions`: remaining decisions, affected scope, impact, owner, and resolution trigger, consistent with document appendices. Cancelled/skipped/unanswered material decisions remain unresolved and block only dependent scope.
- `agent_ready_checklist`: coverage of all 8 items in Step 4, with artifact references and any gaps; never replace evidence with a blanket readiness claim.
- `recommended_next_step`: recommend `daw-setup` to record conventions; this is distinct from the bootstrap handoff to `daw-design` and does not dispatch either module.

Compact illustrative `details` (not a complete handoff; checklist entries describe a hypothetical document set):

```json
{
  "project_name": "sample-service",
  "scale_classification": "small API utility",
  "generated_specifications": [
    "docs/specs/blueprint.md",
    "docs/specs/techstack.md"
  ],
  "open_questions_count": 0,
  "open_questions": [],
  "agent_ready_checklist": {
    "goal": "blueprint.md#goal",
    "scope": "blueprint.md#scope",
    "typed_inputs_outputs": "blueprint.md#contracts",
    "data_persistence": "blueprint.md#data",
    "edge_cases_errors": "blueprint.md#error-behavior",
    "executable_acceptance": "blueprint.md#acceptance-criteria",
    "constraints": "techstack.md#constraints",
    "no_change_list": "blueprint.md#non-goals"
  },
  "recommended_next_step": "Recommend daw-setup to record spec directory and stack commands after bootstrap design."
}
```

Set advisory `handoff_to: "daw-design"` only when the applicable interview, confirmed document set, agent-ready checklist, and document review/ready gates are satisfied; otherwise report the actual blocking conditions to the parent. A proposed `status: "pass"` certifies this specification interview stage only, not parent acceptance, application implementation, runtime verification, or operational authorization.
