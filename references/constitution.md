# DAW Constitution — Project Principles

Establishes the binding principles every later phase (specify, clarify, plan, build, review, verify, converge) is evaluated against. Run `daw-design` once up front to record or confirm them, and update them whenever a foundational principle changes. Every specification, plan, and task must argue from this constitution; a phase that contradicts it is a `blocked` finding, not a judgment call.

## Core Axiom

**"Otaknya boleh generative, tangannya harus deterministic."**
Generative cognitive capabilities are reserved for reading context, analyzing intent, designing specifications, planning execution, and synthesizing solutions. All state mutation, system modification, deployment, migration, and verification execute through deterministic scripts, bounded tools, and verifiable proof gates. Documents alone never constitute running background services or deployment authorization.

## Hard Rules

1. **Standard library exclusivity.** `scripts/validate.py` and `scripts/route.py` use the Python standard library only. No third-party runtime dependencies.
2. **Read-only inspection engine.** The validator and route engine never write files, mutate filesystem nodes, or execute subprocesses.
3. **Fail-closed high-risk gating.** High-risk operations (production deployment, destructive migrations, security changes, remote state mutation) halt immediately without exact, interactive human confirmation at the point of risk. Structural references, PR links, issue numbers, or generic approval tokens do not constitute authorization.
4. **No automatic enforcement hooks.** No global git hooks, configuration daemons, or environment security policies are installed or modified to bypass gates. The transition gate is a stateless, read-only CLI utility invoked explicitly at workflow boundaries.
5. **Evidence before claims.** No completion, pass, or success claim without fresh verification evidence actually run and observed in the current session. "Should pass," "looks correct," and agent self-reports are not evidence.
6. **Proportionality.** Artifacts (spec, plan, progress, mockup) are no larger than the work warrants. Tiny settled patches stay inline; multi-step work gets a saved plan before source edits without the user asking.
7. **No document sprawl.** Author only the documents justified by scope, trigger criteria, and user intent. Do not force artificial `spec.md`, `plan.md`, `tasks.md`, or `constitution.md` filenames when equivalent canonical documents already exist.
8. **Grounded facts only.** User facts and observable repository reality outrank templates. Never fabricate citations, synthetic version numbers, or unobserved API endpoints. Absence of evidence is not evidence of absence; mark it `[UNVERIFIED]` or an Open Question.
9. **One workflow at a time.** Modules do not recursively call the root router or each other. Each stage finishes with a clean handoff to the parent orchestrator.
10. **Parent owns acceptance.** A worker `pass` proposes stage criteria only; the parent independently records `accepted`/`not accepted` at the Parent Acceptance Checkpoint.

## Consequences of Change

When a foundational principle or architectural decision is modified:

- Record the old title/concept → new title/concept.
- Enumerate every affected document, task, and acceptance evidence.
- Synchronize authorized artifacts; never silently override established principles or sneak implementation into governance-only edits.
- Supersede, never rewrite, historical records.

## Evaluation Gate

Before any phase reports `pass`, the authoring module must state which constitutional rules the phase touches and confirm none are violated. A violated rule yields `status: "blocked"` with the rule name and the conflicting artifact.
