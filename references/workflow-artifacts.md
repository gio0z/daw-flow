# Workflow Artifacts: Specification, Plan, Progress & Mockup Contract

This reference is the canonical procedural authority for artifact selection, persistence, and state in DAW. It adds no new route, module, runtime, dependency, or service. Tiny settled patches and factual/read-only inquiries retain the no-document path; this contract governs multi-step authorized work only.

Acceptance-criteria authoring (EARS patterns, observable response/oracle, normal/error separation) is owned by [Acceptance criteria / EARS](document-quality.md#acceptance-criteria-ears). This reference governs only where those criteria live, how they bind to tasks, and how progress is recorded.

---

## 1. Artifact Set & Proportionality

- **Specification (authoritative what/why/non-goals/AC):** Proportional authoritative specification is persisted before tactical decomposition. Reuse a current adequate spec; do not duplicate. If clear user requirements have no written source, the authorized parent records their faithful bounded what/why/non-goals/AC in the chosen spec before `daw-plan`. The planner cannot invent architecture or business choices. Ambiguity returns to the existing design/clarification route; no new design insertion is created for clear routes. Domain/flow settle before physical/UI design: bootstrap starts from blueprint/domain/flow before UI/data design. Conditional ERD selection belongs here (§1A): select a separate ERD (`erd`, default `erd.md` under the spec convention) only when persisted entities/relationships are introduced, materially changed, or adopted without an adequate existing model; otherwise record a scoped skip/N/A with reason, and reuse an adequate separate existing model when one exists. Workflow-owned progress/queue metadata is a state record, not a requirements source: do not feed it back into `daw-wizard`/`daw-design` (or adopt-mode re-spec) as if it were authoritative direction; re-derive requirements from user-stated goals plus the bound spec.
- **Plan (how, mapped):** A saved plan maps stable requirement/AC IDs to task IDs, exact target files, dependencies, parallel ownership, expected observations/checks, evidence slots, and separate parent acceptance. Supporting infra tasks require an explicit justified prerequisite dependency.
- **Progress record (actual state):** A required parent-owned durable project progress document/section, opened at intake, records real progress distinct from planned work (see §3).
- **Mockup (UI proof):** Visual mockup handoff where required (see §5). No UI → explicit scoped N/A.
- Single document with separate spec/plan/progress sections is allowed and preferred when lean.

### 1A. Conditional ERD Selection & Ownership Seam

- **Selection:** Select a separate ERD (`erd`, default `erd.md` under the spec convention) only when persisted entities/relationships are introduced, materially changed, or adopted without an adequate existing model. Otherwise record scoped skip/N/A with a one-line reason; reuse an adequate separate existing model when one exists. Selection needs no new route or stage, and not every project produces an ERD.
- **Ownership seam:** Blueprint owns boundaries, components, flows, and domain invariants and links the ERD; the ERD owns persistent entities/relationships; FRD retains behavior plus payload schema types/validation and links the ERD for persistent identity/relationships; techstack references the ERD for the storage model. Detailed relationships reference the separate ERD — no invented schema, migration authorization, or duplicated data authority.
- **Rubric:** An ERD is judged on DQ-01..05 plus erd-01 (entities/identity and sourced attributes), erd-02 (relationships, cardinality, optionality and ownership), and erd-03 (integrity/lifecycle/traceability and applicable physical design).

Proportionality rule: artifacts must be no larger than the work warrants. Trivial settled patches stay inline; do not expand tiny fixes into multi-document ceremony.

---

## 2. Canonical Paths & Ownership

Reuse established project conventions first. Only when no convention exists, use these defaults:

| Artifact        | Established location                              | Default when none                 |
| :-------------- | :------------------------------------------------ | :-------------------------------- |
| Specification   | Existing adequate spec path                       | `docs/specs/<workflow-id>.md`     |
| Plan            | Existing roadmap/issue-export/project doc section | `docs/plans/<workflow-id>.md`     |
| Progress record | Established project doc location                  | `docs/workflows/<workflow-id>.md` |

Single-document alternative: one file with separate spec/plan/progress sections is allowed and preferred when lean.

Ownership:

- **Spec:** Authoring modules (`daw-design`/`daw-wizard` or parent-directed drafting) own content; parent binds it before planning.
- **Plan:** `daw-plan` (or current planning stage) writes task decomposition; parent owns acceptance.
- **Progress:** Parent is sole owner. Workers return proposals only; read-only roles never write. Update the progress record only from observed transitions (see §4).
- **Handoff details:** Include the artifact reference (spec/plan/progress path + revision) in existing handoff `details`. This does not change the outer JSON schema. One artifact authority only: no duplicate task-tracker authority. Native trackers reference plan task IDs; they never duplicate acceptance status (see [Native Workflow Tracking & Scheduling](operations.md#native-workflow-tracking--scheduling)).

`<workflow-id>` is the parent-chosen stable workflow identifier recorded in the progress record. It is reused across spec, plan, and progress for that workflow.

**Result triage queue location:** The parent's [Ranked Result Triage](operations.md#ranked-result-triage) compact queue lives in this durable plan/progress record for multi-step work (finding/result ID, source worker, evidence/revision, rank, dependencies, disposition/next action, integration verification ref). Workers propose priority; the parent validates/re-ranks and gates every result before acceptance or next dispatch. No child rank is trusted blindly and no separate scheduler is introduced.

---

## 3. Required Progress Record

### Contents

A fresh agent reading only the saved progress record must be able to determine the active phase and next action. The record names:

- Workflow ID, objective/scope, active route (planned route list alone is not active state).
- **Actual active module/stage and subphase** — not merely the full planned route.
- Active task(s) for parallel work, and completed **accepted** stages.
- Pending acceptance: stages with worker-proposed `pass` but no parent `accepted` yet.
- Spec and plan refs with current scoped revisions; when a spec/plan artifact does not yet exist, record the ref as explicitly not-yet-created (named planned path + intended owner/creation stage) rather than implying an existing file. Do not record imaginary or phantom files; `unexercised` is not evidence of existence.
- Blockers: owner, question/decision, affected scope.
- `next_permitted_action` (e.g. `parent_acceptance_review`, `dispatch_correction`, `blocked`).
- Primary evidence/handoff refs; parent acceptance distinct from worker pass.
- Correction/retry state where relevant.

Keep history compact. No fake percentages, approvals, or invented observations. Planned commands/checkboxes are not evidence; evidence stays empty or explicitly `unexercised` until the check runs.

### Worked example (illustrative, not an execution)

The following is the canonical inline example. It shows actual active phase vs. planned route, pending acceptance, spec/plan refs and revisions, active tasks, blockers/next action, and evidence:

```markdown
## Workflow Progress: wf-signed-sum-402

- Objective/scope: signed-sum CLI fix; planned route: daw-plan -> daw-build -> daw-review -> daw-verify
- Actual active phase: daw-build (round 2, corrective) — daw-review and daw-verify not yet entered
- Completed accepted stages: daw-plan (accepted, rev b1)
- Pending acceptance: daw-build round 2 worker outcome `pass` claim, parent acceptance not yet recorded
- Spec ref: docs/specs/wf-signed-sum-402.md @ snapshot:docs/specs/wf-signed-sum-402.md#rev-s1
- Plan ref: docs/plans/wf-signed-sum-402.md @ snapshot:docs/plans/wf-signed-sum-402.md#rev-p2
- Progress record: docs/workflows/wf-signed-sum-402.md (parent-owned)
- Active tasks: task-402-signed-sum (builder daw-build-worker-1, round 2)
- Blockers: none
- Next permitted action: parent_acceptance_review (inspect obs-run-signed-sum-r2 vs AC-1 before acceptance)
- Parent acceptance: daw-plan accepted; daw-build round 2 pending
- Evidence refs: obs-run-signed-sum-r2 (exit 0, stdout "-5\n") vs AC-1; canonical handoff task-402 round 2
```

---

## 4. Binding, Update Triggers & Resume

### Scope + revision binding

- Each plan task binds: requirement/AC IDs, exact target files, dependencies, parallel ownership, expected check/observation, and evidence slot.
- Spec source revisions are pinned; approvals bind to specific action, target, revision, and scope. A relevant revision change invalidates affected evidence and approvals (see [Approval Invalidation](operations.md#approval-invalidation-rules) and [Evidence Reuse & Invalidation Rule](operations.md#evidence-reuse--invalidation-rule)).
- Modifying accepted specification documents re-enters the existing five-edge document transition gate (`review-rework` -> `rework-review` -> `review-ready`) per [document-quality](document-quality.md#42-document-mutation--verdict-invalidation). Code-only changes do not invalidate accepted specs.

### Update triggers (parent only)

Parent opens the progress record at intake and updates it at: real phase entry, parent stage acceptance, correction dispatch, block/resume, relevant revision change, stop, and final completion. Not after every tool call, and never from a worker claim alone. Bare no-brief / read-only / tiny-patch runs that have no multi-step workflow do not gain a phantom progress document to fill; the durable record is required only once multi-step authorized work exists.

### Resume / revalidation

On resume, the parent reloads the progress record and revalidates current references before dispatch:

1. Verify blocking condition resolved and revisions still current per scope.
2. Reconstruct mandatory predecessor joins from accepted inputs (see [Mandatory Pre-Dispatch Dependency Joins](operations.md#mandatory-pre-dispatch-dependency-joins)).
3. Preserve retry state; invalidate only affected scope on revision change.
4. Resume never restores a stale approval, assumes prior worker IDs remain valid, or invents missing evidence.
5. Missing or stale evidence is treated as unverified, not as an accepted prerequisite.

Read-only modules and reviewers never write progress records and never gain write authority from them.

---

## 5. Mockup Timing, Proof & N/A

### When required

UI-affecting work requires an actual inspectable rendered visual mockup before UI implementation, derived from settled domain/flow and the existing design source. Prose, ASCII, or wireframe-only descriptions do not satisfy this requirement. An existing matching mockup may be reused. Mockup selection is an optional capability step inside the existing UI/design stage, not a new workflow stage; UI implementation follows visual review.

### Capability discovery & tool selection

At the mockup step, discover which design capabilities are actually accessible to the agent in this session (callable tools, not merely installed software or vendor availability). No installation, account, or vendor dependency is mandated or prompted.

- Prefer an existing relevant accessible project design source. If both Figma and FigCraft are accessible, follow the project's source; do not impose arbitrary vendor priority.
- If Figma/FigCraft is accessible, reuse the relevant file/frame via read/export/preview; no canvas interaction beyond that is required.
- If neither is accessible, use renderable local HTML/SVG or an existing matching mockup, with an actual rendered preview via an already-available browser/render capability. The fallback requires no new tool, installation, or account prompt.
- No external publish, account, or asset actions without permission.

### Real visual inspection & persistence

Review must be based on rendered screenshot/preview inspection of every required screen and state, not layer-tree, props, or JSON inspection alone. Review covers relevant screens, behavior states, viewports, keyboard/focus, and requirement/AC/screen-ID links. Persist the editable source or durable design reference plus the visual preview, and record in the existing plan/progress artifact: design file/frame reference, source revision or snapshot, preview reference, and review coverage. Claim Figma/FigCraft visual review only when its rendered output was actually inspected. A preview never proves runtime behavior; mockup acceptance is not runtime implementation proof or automatic human approval. A relevant source revision/snapshot change invalidates affected preview evidence (see §4). Material missing capability/direction blocks only the UI scope; there is no silent text fallback. When UI direction is uncertain, the mockup step states the question, offers 2–3 structurally different variants (layout/hierarchy/primary action, not recolors), and records the chosen verdict + rationale beside the existing mockup refs; mockup output is a design input, never verification evidence. Field additions only — no new stage.

### Explicit N/A

Record `N/A` with scoped rationale when there is no UI, or when small nonvisual fixes reuse existing matching design without generating a redundant mockup.

### Canonical kinds

Preserve the default six baseline docs (blueprint, prd, frd, techstack, security, roadmap) within the 14-kind catalog in [document-quality](document-quality.md#13-scope--proportionality), plus conditional ERD (§1A) when applicable. Add UI sections where needed; do not change the outer handoff schema. The mockup remains a non-kind artifact — a section/reference inside an existing kind or the plan's design artifact — never a canonical kind. The conditional ERD is the 14th kind, not the mockup.

---

## 6. Boundaries

- No new tools, runtime, storage daemon, crash recovery, or background enforcement. This is a procedural persistence contract; the parent holds workflow state.
- Optional worker retention (continued completed-worker identity in the owning session) remains distinct from this durable-artifact contract. See [Persistent Worker Graphs](operations.md#persistent-worker-graphs-harness-native). This reference is required for multi-step work regardless of retention availability.
- Chat payloads, native todo lists, or session memory alone cannot substitute for the saved plan or progress record for multi-step work.
