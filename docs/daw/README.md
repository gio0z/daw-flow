# `docs/daw/` — where the suite's routes put their output

**The rule.** The **14 canonical document kinds** — `blueprint.md`, `brd.md`, `prd.md`, `frd.md`,
`erd.md`, `techstack.md`, `design.md`, `wireframe.md`, `ui-ux.md`, `security.md`, `roadmap.md`,
`deployment.md`, `qa.md`, `runbook.md` — keep their specification home in `docs/specs/`.
**Everything else a route generates goes under `docs/daw/`.**

| Output | Location |
| :--- | :--- |
| The 14 canonical document kinds | `docs/specs/<kind>.md` |
| Plan | `docs/daw/plans/<workflow-id>.md` |
| Progress record | `docs/daw/workflows/<workflow-id>.md` |
| Decision record | `docs/daw/decisions/<name>.md` |
| Evidence | `docs/daw/evidence/<task-id>/…` |
| Narrative document (design rationale, ADR, retrospective, review or verification record, coupling analysis) | `docs/daw/YYYY-MM-DD-<topic>.md` |

**This is a default, not an override.** When a project already has an established convention for
a document, that convention wins. The rule fills the gap where none exists, so a route's output
lands in one recognizable place instead of being scattered — or invented per project.

The normative statement is
[Workflow Artifacts §2A](../../references/workflow-artifacts.md#2a-the-docsdaw-home-where-the-suites-routes-put-their-output).

## Legacy locations still recognized

The four classes above have moved, and their readers moved with them. Because the rule is a
default rather than an override, a project that adopted an older location keeps it: every reader
accepts both, and a writer uses the project's existing directory when it has one.

| Class | Documented location | Also accepted |
| :--- | :--- | :--- |
| Plan | `docs/daw/plans/` | `docs/plans/` |
| Progress record | `docs/daw/workflows/` | `docs/workflows/` |
| Decision record | `docs/daw/decisions/` | `docs/decisions/` |
| Evidence | `docs/daw/evidence/` | `docs/evidence/` |

Removing the legacy directory makes the documented location the project's convention on the
next run — nothing is locked in.

## Conventions

- **Filename:** a narrative document is `YYYY-MM-DD-<topic>.md`, named for its authoring day. The
  class-scoped outputs keep their own naming (`<workflow-id>.md`, `<task-id>/`).
- **Marker:** a narrative document opens with `<!-- daw-doc -->`. The marker makes the folder
  machine-discoverable, so a future check can distinguish route-generated documents from
  client-project documents without relying on the path alone.
- **Status line:** a narrative document states its status (`proposed`, `approved`, `superseded`)
  so a reader never has to guess whether it is binding.
- **Naming the source:** a narrative document says which route produced it, in a `Produced by:`
  line. `docs/daw/` documents are produced by DAW's own routes; they are not imported from an
  external workflow framework.
- **Index:** this file lists every document in the folder, so a reader never has to glob it.

## Related reading

| | |
| :--- | :--- |
| **Canonical contract** | [`references/execution-runner.md`](../../references/execution-runner.md) — the runner's normative contract. Where the two disagree, the contract wins; this folder records the reasoning behind it. |
| **Change history** | [`CHANGELOG.md`](../../CHANGELOG.md) — what actually shipped, and the migration notes for newly enforced rules. |
| **Suite specifications** | [`docs/BRD.md`](../BRD.md), [`docs/PRD.md`](../PRD.md), [`docs/TRD.md`](../TRD.md), [`docs/UIRD.md`](../UIRD.md), [`docs/DESIGN.md`](../DESIGN.md) — what the suite is and how it is put together. |
| **Document quality** | [`references/document-quality.md`](../../references/document-quality.md#13-scope-proportionality) — the canonical document kinds and their acceptance criteria. |

## Reading order for a new contributor

1. [`SKILL.md`](../../SKILL.md) — what the suite is and how it routes.
2. [`references/operations.md`](../../references/operations.md) — the operational invariants.
3. The contract for the area you are changing — for the runner, that is
   [`references/execution-runner.md`](../../references/execution-runner.md).
4. The `docs/daw/` document for that area, if one exists — it explains *why* the contract reads
   the way it does.

## Documents

| Document | Status | What it covers |
|---|---|---|
| [`2026-11-14-parallel-batch-design.md`](2026-11-14-parallel-batch-design.md) | proposed | Composite batch execution: how a batch of independent tasks runs concurrently in isolated worktrees and is integrated as a combination that is verified as a whole. |
| [`2026-11-14-parallel-batch-implementation-plan.md`](2026-11-14-parallel-batch-implementation-plan.md) | proposed | The implementation plan for the design above: ten tasks across two commits, each with its own test cycle. |

Both are **narrative documents**, not runner-executable plans: a plan the deterministic runner can execute carries the `<!-- daw-task-manifest -->` task list and belongs in `docs/daw/plans/`. These two explain *why* the contract reads the way it does, so they sit here.
