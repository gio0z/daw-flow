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

- **Interactive Question Pacing:** Ask at most 5 focused questions per round, each with a recommended default. Never overwhelm the user with long interrogations.
- **No Redundant Questions:** Before each round, drop every candidate question already answered by the brief, an earlier answer, or a recorded default. Re-asking settled facts is the largest measured precision loss in clarification studies (CONTRA, arXiv 2610.01769).
- **Behavior-Changing Questions First:** Rank candidates by whether different plausible answers would change observable behavior (entry point and interface names, input/output formats, persistence location, validation and error behavior, ordering, limits). Ask those in the earliest rounds regardless of phase; LLM interviewers otherwise surface key questions late and miss over half of implicit requirements (ReqElicitGym, arXiv 2602.18306).
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
- **No Premature Implementation:** Does not implement production code or scaffold the project; produces specification artifacts only.

---

## 2. Inputs & Governance Loader Sequence

### Canonical Path Resolution & Governance Loading

1. **Physical Root Resolution:**
   - Resolve this `SKILL.md` to its canonical physical directory. The suite root is canonical `../..`.
   - Resolve all relative links (`../../references/...`, `../../templates/...`, `../../SKILL.md`) relative to the physical module directory.
2. **Mandatory Governance Loading:**
   - Before executing interview work, load root governance (`../../SKILL.md` §4 Safety & §6 Handoff Contract Schema) and canonical routing (`../../references/routing.md` §5 & §6).
   - Before writing specification files to disk, load `../../references/operations.md` §1 Preflight Safety & §2 High-Risk Approvals.
   - Respect repository spec conventions from DAW configuration if present (default: `docs/specs/`).

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

1. **Phase Elicitation:** For each phase, ask up to 5 high-leverage questions with suggested defaults, applying the redundancy filter and behavior-first ranking above. Accept `default` (adopt the proposal) or `skip` (record an Open Question). In Phase 4, handle visual style with the DESIGN.md rule (attach, or draft to the standard, or Open Question); headless projects skip wireframes and DESIGN.md but still get the output-style question.
2. **Document Set Confirmation:** After Phase 2, propose the proportional document set and confirm it before drafting.
3. **Drafting Specifications:** Create the confirmed documents in the spec directory (`spec_dir` from a `<!-- daw-config:start -->` block if present, else `docs/specs/`), following the canonical template structure. Every claim traces to an interview answer or a recorded default.
4. **Agent-Ready Checklist:** Before handoff, verify the document set jointly covers all 8 items an implementing agent needs: (1) goal, (2) in/out of scope, (3) inputs and outputs with types and exact names (entry points, commands, files), (4) data and persistence changes, (5) edge cases and error behavior, (6) executable acceptance criteria, (7) constraints (performance, security, compatibility), (8) no-change list. Any item the interview did not settle becomes an Open Question, not an invented value. Specs covering at least 6 of these items merged substantially more often in a 2026 spec-driven development benchmark (Uvik).
5. **Capture Open Questions:** Append an `## Open Questions` section to each generated document listing pending items, impact, owner, and resolution trigger.
6. **Handoff Formulation:** Hand off to `daw-design` (next bootstrap stage). Report the checklist coverage (`details.agent_ready_checklist`) and recommend `daw-setup` in `details.recommended_next_step` so the conventions decided in the interview (spec directory, stack commands) get recorded.

---

## 4. Output Contract

Every completion of `daw-wizard` delivers a structured handoff payload adhering to the canonical suite envelope:

```json
{
  "objective": "Complete greenfield project specification interview and generate baseline architectural specifications.",
  "input_paths": [],
  "output_paths": [
    "docs/specs/blueprint.md",
    "docs/specs/prd.md",
    "docs/specs/techstack.md",
    "docs/specs/security.md",
    "docs/specs/roadmap.md"
  ],
  "acceptance_criteria": [
    {
      "criterion": "Conducted 6-phase elicitation interview with proportional depth and at most 5 questions per round",
      "status": "pass"
    },
    {
      "criterion": "Generated baseline specifications adhering to canonical suite templates",
      "status": "pass"
    },
    {
      "criterion": "Recorded unresolved decisions in Open Questions appendix with owners and triggers",
      "status": "pass"
    }
  ],
  "evidence": [
    {
      "reference": "docs/specs/blueprint.md",
      "summary": "Authored foundational system architecture and component boundaries"
    },
    {
      "reference": "docs/specs/techstack.md",
      "summary": "Documented chosen stack, dependencies, and architectural invariants"
    }
  ],
  "status": "pass",
  "handoff_to": "daw-design",
  "details": {
    "project_name": "sample-service",
    "scale_classification": "medium application",
    "generated_specifications": [
      "docs/specs/blueprint.md",
      "docs/specs/prd.md",
      "docs/specs/techstack.md",
      "docs/specs/security.md",
      "docs/specs/roadmap.md"
    ],
    "open_questions_count": 2,
    "recommended_next_step": "Run daw-setup to record discovered build commands and project conventions in AGENTS.md"
  }
}
```
