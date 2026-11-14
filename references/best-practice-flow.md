# Best Practice Flow: Adopted Sources & Enforcement Points

The DAW suite does not invent its delivery flow. Each step below is adopted from an existing, working workflow — GitHub **spec-kit**, **superpowers**, or **Matt Pocock**'s agent workflow — and bound to an existing DAW rule that already implements it. This document is the single authority for that mapping: the prose states what is borrowed, and the machine mapping at the end is what `validate.py flow` and the `route.py` flow gate read.

Two rules govern edits here:

1. **No untagged step.** Every step carries a `source` and a resolvable anchor into this repository. A step whose rule cannot be located in the suite is not a real step, and the validator rejects it.
2. **Anchor before prose.** Changing a rule's location requires updating the matching `anchor` in the machine mapping in the same revision; a dangling anchor fails the gate rather than silently documenting a rule that no longer exists.

## The Nine Steps

### BPF-1 — Constitution and principles come first

Borrowed from **spec-kit**'s constitution step: project principles are written before features, and every later phase is evaluated against them.

DAW realization: `references/constitution.md` is loaded in mandatory governance, and `daw-design` exits `blocked` when a design contradicts it.

### BPF-2 — Clarify and specify before planning

Borrowed from **superpowers**' brainstorming-to-plan discipline and **spec-kit**'s `/specify`: the agent interviews for the material decisions and writes a spec before any decomposition.

DAW realization: `references/grilling.md` fixes the question protocol (native clarification transport, frontier ordering, at most five questions per round), and multi-step authorized work persists a proportional specification per `references/workflow-artifacts.md` before `daw-plan` runs.

### BPF-3 — Plan as vertical slices with one-action steps

Borrowed from **Matt Pocock**'s small-step agent workflow and **superpowers**' plan authoring: work is cut into vertical, independently shippable slices, and each task step names one action, one file, and an expected result.

DAW realization: `skills/daw-plan/SKILL.md` requires a plan header fixed before tasks, vertical story slices, and per-task ordered `steps` (`action`, `file`, `run`, `expected`); horizontal layer tasks and standalone "write tests" tasks are rejected.

### BPF-4 — Every task carries acceptance and an exact verification command

Borrowed from **spec-kit**'s `/tasks`: a task is not a task unless an observable acceptance criterion and the exact command that proves it are attached.

DAW realization: `references/validation.md` defines the task contract schema whose acceptance criteria and evidence entries are validated structurally, and the completion gate refuses `complete` without `passed` evidence produced against `result.revision`.

### BPF-5 — Small diffs, test-first, refactor after green

Borrowed from **superpowers**' TDD loop: red, green, refactor — the smallest failing test first, minimal implementation, cleanup only once green.

DAW realization: `skills/daw-build/SKILL.md` fixes the test-strategy matrix, the minimal implementation phase, and the targeted refactoring phase, with the lifecycle inner loop in `references/developer-lifecycle.md` running the smallest relevant check after each edit.

### BPF-6 — Independent review, never self-review

Borrowed from **superpowers**' review subagent pattern: the author never certifies its own work.

DAW realization: `references/operations.md` requires the parent to inspect primary evidence at the Parent Acceptance Checkpoint, and `references/validation.md` rejects a `review-ready` record whose reviewer id equals the author id.

### BPF-7 — Verify by running the thing

Borrowed from **superpowers**' "verification before completion": no completion claim without fresh observed output from the real surface.

DAW realization: `skills/daw-verify/SKILL.md` fixes the claim → check → actual triad and rejects dry-runs, mock-based victory, and reused transcripts as proof; the root handoff contract's completion claim gate requires a passing `validate.py contract --stage complete`.

### BPF-8 — Commit and integration hygiene as its own route

Borrowed from **Matt Pocock**'s commit-sized workflow and **spec-kit**'s explicit implementation handoff: delivery steps are a route with their own checks, not a tail appended to coding.

DAW realization: `skills/daw-ship/SKILL.md` owns pre-ship inventory, commit shaping, PR drafting, CI triage, review-feedback intake, and merge/release readiness; push, merge, tag, and deploy stay point-of-risk actions.

### BPF-9 — A machine-readable task list drives execution

Borrowed from **Matt Pocock**'s PRD-to-issues workflow and his unattended agent loop: a plan is decomposed into independently grabbable task files, the next task is chosen by a program rather than by a model's runtime judgment, and each task runs against a fixed context and a fixed verification command.

DAW realization: the saved plan carries a task manifest (a fenced JSON block after the `<!-- daw-task-manifest -->` marker) whose field names match the planning module's task contract. [`scripts/run.py`](../scripts/run.py) computes the ready set from the dependency DAG, assembles a byte-bounded context pack per task, and runs each task's prescribed verification command, capturing output and exit code as durable evidence; `scripts/check_tasks.py` validates the manifest's structure read-only. The runner is explicitly invoked, never a daemon, and never pushes, merges, or deploys. Full contract: [Deterministic Execution Runner](execution-runner.md).

## Enforcement

- **Static gate:** `python3 scripts/validate.py flow --project-root <suite root>` verifies the machine mapping below — step count, ids, sources, anchors (file and heading), the required cross-links from `SKILL.md` and `references/routing.md`, and consistency with `flow_gate` in `references/suite-manifest.json`.
- **Route gate:** `python3 scripts/route.py REQUEST.json --project-root <project root>` downgrades `status: ready` to `blocked` for the intents named in the manifest's `flow_gate.affected_intents` when a required artifact step is unsatisfied.

Both gates are advisory about _authority_: passing them never authorizes a mutation, a deployment, or any action beyond what the operator asked for.

## Machine Mapping

The fenced block below is parsed by `validate.py flow` and by the route gate. Fields:

| Field                           | Meaning                                                                                                   |
| :------------------------------ | :-------------------------------------------------------------------------------------------------------- |
| `flow_schema_version`           | Integer schema version; currently `1`.                                                                    |
| `cross_links`                   | Files that must link this document.                                                                       |
| `steps[]`                       | The eight adopted steps, in flow order.                                                                   |
| `steps[].id`                    | Stable id `BPF-1`…`BPF-8`.                                                                                |
| `steps[].source`                | One of `spec-kit`, `superpowers`, `pocock`, `original`.                                                   |
| `steps[].anchor`                | Repository path with optional `#heading-slug` that must resolve.                                          |
| `artifact_steps[]`              | Steps with a file-checkable prerequisite, used only by the route gate.                                    |
| `artifact_steps[].patterns`     | Bounded project-relative globs; `{spec_dir}` resolves from the project's `daw-config`, else `docs/specs`. |
| `artifact_steps[].require_text` | Literal token the matched file must contain, or `null`.                                                   |

```json
{
  "flow_schema_version": 1,
  "cross_links": ["SKILL.md", "references/routing.md"],
  "steps": [
    {
      "id": "BPF-1",
      "name": "Constitution and principles come first",
      "source": "spec-kit",
      "anchor": "references/constitution.md#evaluation-gate",
      "mandatory": true
    },
    {
      "id": "BPF-2",
      "name": "Clarify and specify before planning",
      "source": "superpowers",
      "anchor": "references/grilling.md#2-operational-protocol-steps",
      "mandatory": true
    },
    {
      "id": "BPF-3",
      "name": "Plan as vertical slices with one-action steps",
      "source": "pocock",
      "anchor": "skills/daw-plan/SKILL.md#3-operational-steps",
      "mandatory": true
    },
    {
      "id": "BPF-4",
      "name": "Every task carries acceptance and an exact verification command",
      "source": "spec-kit",
      "anchor": "references/validation.md#5-task-contract-schema-strict-specification",
      "mandatory": true
    },
    {
      "id": "BPF-5",
      "name": "Small diffs, test-first, refactor after green",
      "source": "superpowers",
      "anchor": "skills/daw-build/SKILL.md#3-step-by-step-procedure",
      "mandatory": true
    },
    {
      "id": "BPF-6",
      "name": "Independent review, never self-review",
      "source": "superpowers",
      "anchor": "references/operations.md#parent-acceptance-checkpoint",
      "mandatory": true
    },
    {
      "id": "BPF-7",
      "name": "Verify by running the thing",
      "source": "superpowers",
      "anchor": "skills/daw-verify/SKILL.md#3-core-verification-rules",
      "mandatory": true
    },
    {
      "id": "BPF-8",
      "name": "Commit and integration hygiene as its own route",
      "source": "pocock",
      "anchor": "skills/daw-ship/SKILL.md#3-ship-procedures",
      "mandatory": true
    },
    {
      "id": "BPF-9",
      "name": "A machine-readable task list drives execution",
      "source": "pocock",
      "anchor": "references/execution-runner.md#2-the-task-list",
      "mandatory": true
    }
  ],
  "artifact_steps": [
    { "step": "BPF-2", "patterns": ["{spec_dir}/*.md"], "require_text": null },
    { "step": "BPF-3", "patterns": ["docs/plans/*.md"], "require_text": null },
    {
      "step": "BPF-4",
      "patterns": ["docs/plans/*.md"],
      "require_text": "expected"
    },
    {
      "step": "BPF-9",
      "patterns": ["docs/plans/*.md"],
      "require_text": "<!-- daw-task-manifest -->"
    }
  ]
}
```
