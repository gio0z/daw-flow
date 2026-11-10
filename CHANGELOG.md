# Suite Change History & Architecture Log

Convention: every entry with breaking or newly-enforced rules MUST include a `### Project migration` subsection (artifact, finding code or `manual`, fix route).

## Unreleased — Enterprise Router, Native Clarification & Component Source

### Added

- `references/constitution.md`: project principles every later phase is evaluated against. `daw-design` loads it in mandatory governance and exits `blocked` on a contradiction; its exit criteria include constitution compliance.
- Router (`scripts/route.py` + `references/suite-manifest.json`): routes now support `conditional_stages` (condition-guarded stage insertion with `insert_before`/`insert_after`/`duplicate_allowed`), `parallel_groups` (declared concurrent pairs), and `extension_hooks` (declared hook points), all validated declaratively. Modules carry `maturity` (`stable|beta|deprecated|experimental`) and `bucket`; a `deprecated` module in an active route blocks it, an `experimental` one warns.
- Router `--session-start`: bare invocation analyzes project artifacts (config block, specs, plans, workflows, evidence) and proposes an entry route (`setup`/`ship`/`verify`/`build`/`plan`/`bootstrap`).
- `tools/evaluation/route_eval.py` + `route_eval_fixture.json`: stdlib route-eval harness asserting expected status/stages/constraints across scenarios.
- `workflow-artifacts.md` §7–§10: spec quality checklist ("unit tests for requirements"), read-only analyze step, append-only converge step, and feature-directory convention.
- `daw-wizard` / `daw-design`: optional **component source** question (own design system vs. actually-available MCP design components vs. recommend-after-inspection), asked via the native clarification transport and recorded in `details.component_source`.
- `validate.py status` now emits a machine-readable `next_actions` array in the status envelope (primary first, each entry `{action, kind: author|run|decide, command, why, blocking}` with `$SKILL_DIR`/`$PROJECT_DIR` placeholders, advisory only) and prints a `Next actions:` block in text output; user-facing reports must end with a concrete next action naming an exact command (at most two alternatives after it, or say the workflow is complete or name the unblocking action and its owner when blocked).
- `references/best-practice-flow.md` + `validate.py flow`: the delivery flow is now documented as eight adopted steps (spec-kit, superpowers, Matt Pocock) each tagged with its source and a resolving DAW anchor, backed by a machine mapping that the new read-only `flow` check validates (step count/ids, source enum, anchor file _and_ heading slug, required cross-links from `SKILL.md`/`references/routing.md`, and consistency with the manifest `flow_gate`).
- `scripts/derive_ledger.py`: `<spec_dir>/ledger.json` can now be **derived** from existing doc-transition records instead of hand-written, removing the state/hash duplication that made every spec-only project report `status_ledger_missing` → `design-rework`. It is the suite's only writer (never invoked by `validate.py`/`route.py`), writes only on `--write`, and copies a `sha256` only from a record that declares it _and_ whose document bytes still match — an edited document is reported as `derive_doc_unmapped` rather than silently re-pinned. `status` `design-rework` `next_actions` now leads with `design-derive` whenever a records source (`docs/decisions`, `docs/specs/records`, `docs/evidence`) exists.

### Changed

- `validate.py verify` + `scripts/check_surface.py`: the mechanical half of `daw-verify` Rule 8. A recorded role-based session must name its role, carry a phone (≤480 px) and desktop (≥1024 px) viewport, contain a `write` and a `read_back` leg, and give every leg a wire outcome with a concrete HTTP status/exit plus the operator-visible message; `--stage complete` additionally requires `passed` on every leg. Task contracts gain an optional `surface: "ui" | "non-ui"` field: declaring `ui` makes the session mandatory at `contract --stage complete` (`surface_session_missing`, `surface_leg_not_passed`), an absent declaration over a UI-shaped `operation.scope` warns `surface_declaration_inferred`, and a session recorded without the declaration warns `surface_session_ignored`.

- `daw-verify` Rule 8: a UI-affecting change cannot be marked `passed` without one executed role-based session on the running product, recording per leg the interaction, the wire outcome (HTTP status or exit code) and the operator-visible message, covering the write leg, the read-back leg, the non-staff surface when one exists, and both phone (~390 px) and desktop (~1440 px) viewports when layout or navigation changed. Recorded as `details.surface_session`; an unwalked leg is `unexercised` and blocks acceptance. This closes the gap found while delivering kud-business, where every structural gate was green while the UI rejected today's date, itemized no deductions, and leaked English errors.

- `route.py --session-start` fixed to analyze project artifacts against the project root (or cwd) while loading the manifest from the suite root, to suggest only valid intents (`setup`/`ship`/`review`/`feature`/`bootstrap`), and to treat a feature route's enterprise keys as optional with a distinct message when absent. `conditional_stages` entries now validate their `stage`/`insert_before`/`insert_after`, and `if` expressions enforce the `AND`/`OR`/`NOT` grammar; a deeply nested flow mapping yields `FLOW_GATE_UNREADABLE` instead of an uncaught `RecursionError`. `references/suite-manifest.json` drops the unreachable `daw-design` conditional-stage entry.
- `validate.py flow` (`scripts/check_flow.py`) guards against unhashable JSON values in `_validate_steps`/`_validate_manifest` (`flow_step_id_invalid`/`flow_source_invalid`/`flow_gate_step_unknown`/`flow_gate_intent_unknown`) instead of crashing; `flow_schema_version` must be an actual int (not bool/float); `artifact_steps` entries are validated (`flow_artifact_step_invalid`, `flow_artifact_step_unknown`) and every `required_steps` step must have at least one artifact check (`flow_artifact_step_missing`); `flow_gate.document` must be exactly `references/best-practice-flow.md` (`flow_gate_document_mismatch`); `cross_links` must include both `SKILL.md` and `references/routing.md` (`flow_missing_link` fires for each missing one). A `validate.py flow --format json` run on malformed input always emits a JSON envelope, never a traceback.
- `validate.py verify` bounds the session file path to the project root (exit 2 with an error message on `../../` paths), and `scripts/check_surface.py` errors `surface_declaration_mismatch` when `surface: "non-ui"` is declared over a UI-shaped scope, with the session still enforced only when declared `"ui"`; the wire-outcome regex now accepts a status only following an HTTP method, `-> N`, or `exit N`.
- `validate.py status` (`scripts/check_status.py`): `summary.plans` is `ok` only when a regular `docs/plans/*.md` file contains the literal token `expected` (a `docs/plans/dir.md` directory no longer counts), and `next_actions[0].blocking` is `true` for a missing config, matching `references/validation.md`.
- Ledger derivation (`scripts/derive_ledger.py`/`scripts/check_ledger.py`): `_resolve_chain` rejects disconnected chains (`derive_doc_conflict`); `--write` refuses when the ledger path is a symlink (`derive_write_refused`); untracked spec docs error `derive_doc_untracked` and refuse the write; task contracts are skipped silently; malformed `documents[]` entries warn `derive_record_malformed`; and `validate_ledger` errors on a non-string `record` (`invalid_record`).
- Eval tooling (`tools/evaluation/`): `route_eval` passes `--root` through to `route.py`, exit codes are asserted in the fixture (`expected.exit_code`), the status grader degrades non-dict envelopes, and plan-file detection matches a `plans/` component or a stem token.

- `route.py` accepts `--project-root`: for the intents named in `references/suite-manifest.json` `flow_gate.affected_intents` (`feature`, `bugfix`, `refactor`, `maintain`) a `ready` resolution is downgraded to `blocked` with `FLOW_GATE_MISSING_ARTIFACT` when a required flow step's artifact is absent (spec file, plan file, plan carrying `expected` markers). Without `--project-root` route resolution is unchanged; an unreadable mapping fails closed as `FLOW_GATE_UNREADABLE`. `flow_gate` is optional in the manifest, so older manifests stay valid.
- Native interactive clarification is enforced across the suite: when a harness exposes a native question tool, posing a material decision only as plain chat text is a transport violation (root `SKILL.md`, `daw-ask`, `daw-wizard`, `daw-design`, `daw-setup`, `daw-untangle`, `daw-workspace`, and `operations.md` §2 fail-closed approval).
- `daw-plan` tasks carry an `interfaces` block (`consumes`/`produces` exact signatures).

### Project migration

For projects that last passed 0.5.0 (`daw_version: 0.5.0`):

- Clarification — agents must use the harness's native question/approval tool when one is exposed; plain-chat material questions are no longer valid (manual: rerun the decision through the native tool); fix route: none.
- Routes — new optional manifest keys (`conditional_stages`, `parallel_groups`, `extension_hooks`, module `maturity`/`bucket`) are additive; existing manifests remain valid (manual: none); fix route: none.
- Constitution — a project may add `references/constitution.md`; a phase that contradicts it now blocks (manual: reconcile the offending artifact first); fix route: `daw-design`.

## Unreleased — Executable Specs & Plans, Status Advisory, Setup Command Preservation

### Changed

- Root §2/§3: `status` `recommended_route` is advisory only; an explicit status-only request is read-only and terminal, while an ordinary task continues on its own authorized route with no extra consent gate for already-authorized mutations.
- `daw-setup`: preserves existing configured commands verbatim (including locally unresolved ones, reported as `config_command_unresolved`), defaults only absent fields to `none`, treats format-only normalization as lossless, and shows every semantic delta in the confirmed setup diff. `valid` config means structural/resolvability only, not readiness.
- `daw-plan` + `templates/roadmap.md`: plans are now executable. Every multi-step plan opens with a header (Goal, Architecture, Tech Stack, verbatim Global Constraints, File Map) fixed before tasks; work is cut into vertical story slices (P1 first, each with What to build, Out of scope, and a P1 checkpoint) instead of horizontal phases; each task carries ordered single-action `steps` (`action`, `file`, `run`, `expected`) starting from a baseline step, a bounded `change_preview` for contract-bearing surfaces, verbatim `constraints_quoted`, and `autonomy: hitl|afk`. Layer-only tasks and standalone "write tests" tasks are forbidden. Wide mechanical refactors use expand → migrate → contract.
- `daw-plan` readiness self-check adds a placeholder scan, entity/type name consistency, gate concreteness (exact command + expected observable), and an autonomy check. A spec-dependent build without a persisted plan (header, slices, steps, commands) is `blocked`; a milestone roadmap is not a plan.
- `daw-design` + PRD/FRD templates: a detail ceiling keeps DDL, function bodies, migrations, and file paths out of spec prose (entities → `erd.md`, shapes → FRD interface table); priorities must be distributed with an Independent Test per story; acceptance criteria are scenarios with an observable, independently sourced oracle and a negative case; at most 3 material `[Open Question]`s per document, the rest become labeled `[Proposed Default]`s; test seams are chosen at design time; consequential seams record two real alternatives; a bounded spec self-review runs before the transition gate.
- Domain modeling: glossary terms carry an `Avoid:` alias list; cross-document entity/type spelling is checked. Cross-artifact analysis (`document-quality.md` §F) adds named passes including entity-set diff. Rubric questions sharpened in place (same IDs and counts).
- `daw-review` prebuild mode adds a buildability dimension with no-nitpick calibration. Mockups with uncertain direction offer 2–3 structural variants and record the verdict; mockup/prototype code is design input, never production code or verification evidence (`workflow-artifacts.md` §5, `daw-build` §2).
- Root §1 rule 3: "tiny" now has one deterministic definition (one file plus its own test, no new user-visible behavior, no schema/migration/public interface/UI screen/config contract/dependency change). Everything else is multi-step and gets a saved plan before source edits automatically; the user never has to ask for a plan. Urgency wording does not reclassify work; only an explicit per-task opt-out skips the plan and is recorded. Uncertain size counts as multi-step. `patch` is restricted to tiny work.
- Root §2: a one-line intake classification (`Route · Size → next step`) is required before the first file write, so a skipped route is visible immediately.
- Root §3 `feature`: visual design and mockup requests route through `feature` with UI scope (`daw-design` mockup with variants and verdict before UI tasks; mockup-only requests stop after review) instead of running as unrouted direct work.
- `tools/evaluation/evaluate.py`: new `feature` case whose prompt never mentions planning; it passes only when a saved plan exists, and fails if code changes without one.

### Project migration

For projects that last passed 0.5.0 (`daw_version: 0.5.0`):

- Status callers — treat `recommended_route` as advisory; explicit status-only requests report and stop with no dispatched route (manual: adopt advisory-only handling); fix route: none.
- Config block — manually confirm any preserved-but-unresolvable command with `validate.py config` (`config_command_unresolved`); do not erase it to pass; fix route: `daw-setup` write only when the user authorizes the command change.
- Saved plans — a milestone-only roadmap is no longer accepted as a plan for spec-dependent builds (manual: re-plan into header + vertical slices + steps with `run`/`expected`); fix route: `daw-plan`.
- PRD/FRD with DDL or function bodies in prose — manual: move entity model to `erd.md` and shapes to the FRD interface table; fix route: `daw-design` rework through the document gate.
- Work classification — agents that previously treated multi-step work as "small" now plan first (manual: expect an intake line and a saved plan before code on multi-step requests); fix route: none.

## 0.5.0 (2026-11-08) — Validator Split and Project Status Preflight

### Added

- `validate.py status --project-root ROOT`: one read-only preflight that composes `config`, `ledger`, and `contract --stage complete` (for task contracts at `docs/evidence/<task-id>/contract.json` that carry a `result`), returns a summary (`config`, `ledger`, `tasks`) and a `recommended_route` (`setup`, `upgrade-recheck`, `design-rework`, `verify`, or `none`). New warnings `status_ledger_missing` and `status_task_in_progress`.
- Router: a bare invocation in a repo with DAW artifacts runs `status` first and proposes its recommended route before Adopt; a task invocation runs `status` as preflight, and error findings block spec-dependent mutating routes until resolved. Read-only routes and setup are never blocked.

### Changed

- `scripts/validate.py` is now CLI only. Checks live in flat modules: `daw_common.py` (shared parsing, paths, hashing, findings, output), `check_package.py`, `check_contract.py` (split per contract section), `check_docs.py` (was `doc_quality.py`), `check_ledger.py` and `check_config.py` (were `ledger_config.py`), and `check_status.py`. No check module imports `validate.py`; the former circular import is gone. Subcommand behavior, exit codes, finding codes, and output are unchanged.
- `VERSION` and root `SKILL.md` `metadata.version` bumped to `0.5.0`.

### Project migration

For projects that last passed 0.4.0 (`daw_version: 0.4.0`):

- Task contracts — store them at `docs/evidence/<task-id>/contract.json` so `status` can discover them; contracts elsewhere are not checked by `status` (manual: move or keep checking with `validate.py contract`); fix route: `daw-verify`.
- Code importing DAW internals — replace `scripts.doc_quality` with `scripts.check_docs` and `scripts.ledger_config` with `scripts.check_ledger` / `scripts.check_config` (manual; the CLI is unchanged).
- Config block — bump `daw_version` to `0.5.0` after `validate.py status` reports no errors; fix route: `daw-setup` Upgrade Re-check.

## 0.4.0 (2026-11-08) — Completion Claims Bound to Durable, Revision-Pinned Evidence

Closes early "done" claims that `validate.py contract --stage complete` still accepted: stale logs from an earlier revision, evidence in ephemeral paths, and code edited after verification.

### Added

- Task contract `result` object (`revision`, `files[]` with `sha256`): the post-change snapshot recorded after verification. Forbidden at `plan`, optional at `execute`, required at `complete`.
- Evidence entries gain `sha256` and `revision`, both required at `complete`.

### Changed

- Breaking: `complete` now fails with `missing_result`, `result_changed` (result file edited after recording), `result_revision_unchanged` (result revision equals baseline), `missing_evidence_sha256`, `evidence_hash_mismatch`, `missing_evidence_revision`, `evidence_revision_mismatch` (evidence not produced for `result.revision`), and `evidence_not_durable` (evidence under `tmp/`, scratch, or dot-directories; applies on every stage).
- `VERSION` and root `SKILL.md` `metadata.version` bumped to `0.4.0`.
- Unchanged limitation: the validator never evaluates the semantic truth of evidence contents; the parent still opens the evidence before accepting.

### Project migration

For projects that last passed 0.3.0 (`daw_version: 0.3.0`):

- Task contracts already at `complete` — add `result` and evidence `sha256`/`revision`, regenerating evidence against the current revision where the old log no longer matches (`missing_result`, `missing_evidence_sha256`, `missing_evidence_revision`, `evidence_revision_mismatch`); fix route: `daw-verify`.
- Task contracts with evidence under `tmp/` or other ephemeral paths — move evidence into committed paths such as `docs/evidence/<task-id>/` (`evidence_not_durable`); fix route: `daw-verify`.
- In-flight contracts at `plan`/`execute` — no change required until `complete`; remove any `result` from `plan`-stage contracts (`result_not_allowed`).
- Config block — bump `daw_version` to `0.4.0` only after the re-check above is clean; fix route: `daw-setup` Upgrade Re-check.

## 0.3.0 (2026-11-08) — Persisted Workflow State & Gate Hardening

Motivated by a downstream audit (kud-business) where every transition record failed revalidation: specs drifted after `review-ready`, evidence pointed at an uncommitted `tmp/` file, an agent persona signed as reviewer, the `daw-config` block was free-form with unresolvable commands, and plan/review/verify left no repo evidence across commits.

### Added

- `validate.py ledger`: validates `<spec_dir>/ledger.json`, the persisted per-document workflow state (current state, hash, current transition record, superseded history). Detects spec drift, record/state mismatch, and revalidates `ready` records.
- `validate.py config`: validates the `daw-config` block (exact key set, values, existing paths, resolvable commands; commands are never executed).
- `daw_version` key (semver X.Y.Z) in the `daw-config` block, placed right after `schema`, recording the last version the project passed re-check against; `validate.py config` compares it read-only against the installed `VERSION` (`config_daw_version_stale` warning, `config_daw_version_ahead` error, `config_daw_version_unverified` warning, non-semver `config_line_invalid`).
- `daw-setup` Upgrade Re-check (read-only diagnosis) triggered by `config_daw_version_stale` or a suite update: collects `### Project migration` items between versions, runs `config`/`ledger`/`docs` validators, lists manual checks, reports findings by artifact with fix route, and bumps `daw_version` only after errors resolve and the user confirms.

### Changed

- Doc gate rejects non-durable evidence paths (`tmp/`, scratch, dot-directories) with `evidence_not_durable`; gitignored paths remain undetectable without Git.
- Breaking: `reviewer` on `review-ready`/`review-rework` is now `{id, kind: human|agent, author_id}`; self-review fails with `reviewer_not_independent`; agent review on `review-ready` emits warning `reviewer_agent_attestation`. Identity is still never authenticated.
- Workflow rules: spec-dependent plan/build require a passing ledger with dependent specs `ready`; multi-session or multi-commit work persists the task contract and verify evidence under `docs/evidence/<task-id>/` before commit; `daw-setup` runs `validate.py config` after writing the block.
- `VERSION` and root `SKILL.md` `metadata.version` bumped to `0.3.0`; text output of `validate.py` now lists findings for every check, not only `docs`.

### Project migration

For projects that last passed 0.2.0 or earlier (no `daw_version` recorded), run the `daw-setup` Upgrade Re-check before spec-dependent work:

- Config block (`AGENTS.md`/`CLAUDE.md`) — add `daw_version` right after `schema` and convert the block to the exact key format (`config_key_missing`/`config_line_invalid`); fix route: `daw-setup` write.
- Transition records — convert `reviewer` strings to `{id, kind, author_id}` and re-record review exits (`invalid_reviewer`); fix route: `daw-design` rework.
- Evidence paths — move evidence out of `tmp/` etc. into committed paths (`evidence_not_durable`); fix route: `daw-design` rework.
- Spec index — create `<spec_dir>/ledger.json` (`validate.py ledger`); fix route: `daw-design` rework.
- Manual check (no validator): ERD needed when persisted entities exist (since 0.1.2); persist the task contract plus verify evidence under `docs/evidence/<task-id>/` for multi-commit work; fix route: `daw-design` rework / `daw-plan`.

## 0.2.0 (2026-11-08) — Professional Developer Lifecycle

### Added

- New module `daw-ship` (`skills/daw-ship/SKILL.md`): integration & delivery — commit hygiene, pull requests, CI triage, review feedback, merge & release readiness. The suite is now **12 modules**.
- New shared reference `references/developer-lifecycle.md`: inner dev loop, time-boxing & escalation budgets, spike protocol, behavior-preserving refactor protocol, dependency/maintenance upgrade protocol, regression bisection, commit hygiene, PR/CI protocol, review feedback protocol, release readiness, retro fed back into `AGENTS.md`.
- Four new intents (total **13**: bootstrap, adopt, feature, bugfix, patch, review, untangle, ask, setup, refactor, maintain, spike, ship). `refactor` (`daw-untangle -> daw-plan -> daw-build -> daw-review -> daw-verify`), `maintain`, `spike` (`daw-workspace -> daw-build -> daw-ask`, always isolated, throwaway), and `ship` (`daw-ship`).

### Changed

- Module count 11 -> 12 and intent count 9 -> 13 across router, routing, `README.md`, `AGENTS.md`, `docs/PRD.md`, `docs/TRD.md`, `docs/DESIGN.md`, `docs/WORKFLOW.md`, and references.
- `VERSION` and root `SKILL.md` `metadata.version` bumped to `0.2.0`.
- Installer update now creates the `daw-ship` alias.

## 0.1.2 (2026-11-08)

- Version bump for the 2026-11-08 corrections below: optional Figma/FigCraft-first mockup review, workflow artifact governance, separate conditional ERD kind (14-kind catalog), substantive Blueprint, and post-release feedback/incident closure loop. `VERSION` and `SKILL.md` `metadata.version` updated together.

## 2026-11-08: ERD and Application Lifecycle Correction (Matrix Docs)

- Catalog is now 14 kinds including conditional `erd.md` (`templates/erd.md`, default project file `erd.md` under spec convention). Baseline remains six (`blueprint`, `prd`, `frd`, `techstack`, `security`, `roadmap`) plus conditional ERD when persisted entities/relationships are introduced, materially changed, or adopted without an adequate existing model; otherwise ERD is skipped/N/A with a scoped reason. Reuse an adequate separate existing model. Full-suite explicit requests cover all 14. Mockup remains a non-kind artifact.
- ERD selection and rubric: erd-01 entities/identity and sourced attributes; erd-02 relationships, cardinality, optionality, and ownership; erd-03 integrity/lifecycle/traceability and applicable physical design (PK/FK/index/deletion only when storage choices warrant them). DQ-01..05 unchanged. No invented schema or migration authorization.
- Ownership: Blueprint = boundaries/components/flows/domain invariants linking ERD; ERD = persistent entities/relationships; FRD retains behavior and payload validation linked to ERD for identity/relationships; techstack references ERD for the storage model.
- Maintain loop: authorized post-release feedback/incident intake records source/release/evidence, impact, and owner; classifies bug, new requirement, operational incident, or no-change/deferred via existing routes and approvals. Closure requires disposition, linked REQ/AC/task when actioned, parent-observed scoped verification, and post-release evidence only if actually deployed. Local proof never means production resolved; no auto publish/monitor; opt-in maintenance stays opt-in.
- Historical changelog and evaluation observations remain historical; this entry records only the dated correction. Truthful status: no runtime or test pass results are claimed by this entry.

## 2026-11-08: Optional Figma/FigCraft-First Visual Mockup Review

- Align `templates/wireframe.md` mockup record with canonical `references/workflow-artifacts.md` §5: optional existing matching mockup, Figma/FigCraft frame, or renderable local HTML/SVG source when actually accessible; capture file/frame reference, revision/snapshot, visual preview, and actual capability exercised (`unexercised`/`unavailable` when not exercised, never a claimed vendor use).
- No new workflow stage, mandatory vendor dependency, installation/account prompt, or canonical kind; domain/flow still precedes mockups and UI implementation follows visual review; actual rendered preview remains required with runtime verification distinct and UI-only blocking when no viable capability.
- Truthful status: no runtime or test pass results are claimed by this entry.

## 2026-11-08: Seven Workflow Corrections Integration (Documentation & Scenarios)

- Integrate the seven authorized corrections into procedural prose and manual scenarios only (no code, schema, route, module, runtime, dependency, service, or 14th template): canonical semantic EARS guidance with observable oracle and normal/error separation (no keyword parser as truth, no invented policies/numbers, no forced five-pattern use; Given/When/Then remains valid); persisted authoritative spec before tactical decomposition with reuse of adequate specs and the existing design/clarification route for ambiguity (tiny settled patches and read-only inquiries keep the no-document path); saved plan binding stable requirement/AC IDs to task IDs, exact files, dependencies, parallel ownership, expected observations, evidence, and separate parent acceptance; REQUIRED parent-owned durable progress record from intake naming the actual active phase with explicit not-yet-created refs; rendered visual mockup (not prose/ASCII/wireframe-only) before UI work with reuse and scoped N/A; and ranked subagent-result triage with no automatic apply/deploy from worker pass.
- README now links the canonical contracts ([Workflow Artifacts](references/workflow-artifacts.md), [EARS](references/document-quality.md#acceptance-criteria-ears), [Ranked Result Triage](references/operations.md#ranked-result-triage)) and states the required progress record distinctly from optional worker retention; the payload-only planner claim is replaced by the saved-plan requirement.
- Scenarios: existing `SCN-R-*` resume and `SCN-H-02` tracker-absent assumptions are updated to the durable multi-step record model while tiny/read-only controls remain zero new files; new `SCN-WF-*` manual matrix covers semantic AC rejection, written spec → saved plan / current phase, fresh-session resume with scoped revisions, rendered mockup vs text/block/noUI reuse, and every-worker-output ranking with parent dedup / stale / unsupported / safety + urgency / dependency order / no automatic deploy. Empty-bootstrap owner-progress owner is clarified: it is not an existing product.
- Truthful status: no runtime or test pass results are claimed by this entry; scenario outcomes remain unexecuted manual expectations until separately exercised.

## 2026-11-07: Agent Readiness Audit Corrections

- Clarify explicit audit-and-fix requests as parent-composed read-only diagnosis followed by an authorized existing correction route; review-only requests and review modules retain zero mutation authority.
- Separate optional execution-lifecycle labels from canonical outer handoff `pass`/`fail`/`blocked` and parent `accepted`/`not accepted` decisions.
- Correct requirements-clarity reference prose to match the existing resolver: unknown requirements block bootstrap, feature, and patch; unclear requirements block patch, while feature enters design and bootstrap enters its interview.
- Preserve deterministic engine behavior, approval boundaries, module count, and schemas. Verification observations distinguish structural/package checks, bounded supervised agent smoke, transport failures, and the initial parent-confounded patch probe; no cross-client or autonomous reliability certification is claimed.

## 2026-11-07: SCN-C-04 Conditional Diagnosis Decision

- In `tests/behavior-scenarios.md`, replace SCN-C-04's unconditional `daw-build` remediation with one mutually exclusive branch from fresh diagnosis in existing scope/revision/evidence/disposition fields: sufficient legitimate coupling accepted structurally only; missing/conflicting/stale ownership-or-invariant evidence held as not accepted/unexercised on only the affected criterion with no build dispatch; proven concrete defect not accepted/failed with bounded correction, affected-evidence invalidation, and re-verification. Add three given-observation manual controls C04-A/B/C; diagnostic pass is not runtime/production proof or mutation authorization. Limits: docs/scenarios only; no code, schema, route, or new files; zero writes by untangle preserved.

## 2026-11-07: Prefinal Coupling Checkpoint Three-Answer Record

- Refine the canonical coupling checkpoint in `references/change-coupling.md` and its root/operations pointers: require three concise, evidence-backed answers, retain factual N/A for confirmed nonstructural scope, and escalate only demonstrated unresolved cross-module impact. Trigger patterns prompt inspection rather than automatic defect claims; existing accepted reviews are reused without new artifacts or verdict values.
- Extend `SCN-C-01` (legitimate transaction co-change accepted), `SCN-C-02` (clear local patch one-line N/A), and `SCN-C-04` (unresolved hidden-order/shared-state escalation bounded) to require the three short answers in existing scope/revision/evidence/disposition records; add `SCN-C-08` requiring a concrete three-answer record over bare PASS and retaining wrappers with actual security/protocol purpose. Docs/scenarios only; no new runtime code, schema, route, or hook.

## 2026-11-07: Operational Rule Diagnostics Adoption and Manual Scenarios

- Adopt a practical diagnostic lens in `references/operations.md#operational-rule-diagnostics` (no new schema, stage, checklist, or mandatory artifact): each applicable rule connects trigger, observable tell/consequence, scoped corrective action, and sufficient proof, reusing the existing `passed`/`failed`/`blocked`/`unexercised` and parent `accepted`/`not accepted` vocabulary.
- Adopted from pinned upstream inspiration (no external dependency): the trigger/tell/fix/proof framing and observable-tell discipline; scoped tiers distinguish non-negotiable hard obligations (safety gates, accepted contracts, point-of-risk approvals), contextual choices judged against actual requirement and purpose (subjective style defects are not gate violations), and consistency checks proportional to changed scope.
- Evidence scope is tiered: static proof suffices for documentation and read-only review where it directly establishes the claim; runtime claims require execution on the actual surface by a non-read-only actor; missing required evidence blocks only the affected completion, with scoped repair under the existing retry protocol and no forced giant audit. Limits: instruction structure only; no runtime promise, dependency, schema, route, or gate stage; no universal quality claim and no behavior beyond the described manual scenarios.
- Add five manual scenarios (`SCN-DIAG-01` to `SCN-DIAG-05`): valid static documentation proof accepted without forced tests; expected negative CLI exit accepted as valid proof; stated-purpose style choice not a defect while the real invariant's evidence is inspected; missing required runtime proof rejected with a specific scoped corrective action; tiny settled patch proceeding without extra documents or broad cleanup. No probe results are claimed; existing scenario IDs are preserved.

## 2026-11-07: Instruction Density and Consistency

- Make the prebuild review gate conditional on changed scope and route triggers rather than applying it uniformly.
- Load advisory context progressively, limited to the current question and relevant headings.
- Treat clarification transport and the outer handoff envelope as canonical throughout, retaining domain details in their owning modules.
- Consolidate worktree setup into one procedure.

## 2026-11-07: Animation Performance Reference Adoption

- Add optional shared `references/animation-performance.md`, linked from `daw-review` Stage 2 Performance and `daw-verify` Web UI surface. Covers stack-neutral conditional trigger, bounded inventory, static cost checklist, reproducible baseline/after frame traces with refresh-rate-aware budgets, runtime reduced-motion and cleanup checks, evidence statuses, metric limits, and exact WCAG 2.2.2/2.3.3 applicability with flashing separate. No new module, route, generator, or runtime dependency; reviewer/verifier roles remain read-only.

## 2026-11-06: Capability-First Harness Integration

- Bind plan task IDs to available native tracker references and use native scheduling without treating worker completion as parent acceptance or bypassing dependency joins. Preserve structured fallback without new mandatory files.
- Prefer supported LSP and AST capabilities for semantic navigation and authorized refactors, with current-source validation and read-only review boundaries.
- Prefer bounded native debugger observations when appropriate and authorized; retain logging/tracing fallback and hypothesis-driven evidence.
- Match verification to the actual surface: browser, native desktop, CLI, or API. Unavailable required evidence remains unexercised rather than a fabricated pass.
- Add manual capability scenarios covering tracking, dependency gates, code intelligence, debugging, UI evidence, and fallback behavior.

## 2026-11-06: Native Interactive Clarification Transport

- Route material interview and choice questions through the harness's exposed native clarification tool, using its actual schema and limits; retain concise text fallback only when the tool is absent or unavailable.
- Apply the shared protocol to wizard, advisory, design, setup, and other DAW decision flows without redundant questions, duplicate questionnaires, or new approval gates. Cancellation remains unresolved and cannot authorize dependent work.
- Preserve the explicit headless benchmark oracle adapter and add manual transport scenarios covering native tools, equivalent tools, fallback, cancellation, and adapter compatibility.

## 2026-11-06: Optional Parent-Owned Workflow Resume Checkpoint

- Define an optional Markdown resume summary in the operations reference, reusing authorized artifacts or durable harness records without introducing a mandatory file, logger, database, or runtime.
- Preserve workflow identity, scope revisions, parent acceptance, canonical handoff/evidence references, unresolved findings, and correction state across resume. Revalidate predecessor inputs before success-dependent dispatch; scoped corrections still use validated failure findings under existing limits.
- Link the summary from handoff transport without treating it as a new transport or replacement envelope, and add manual unchanged-revision, scoped-invalidation, and fresh-session scenarios.

## 2026-11-06: Patch Routing Consistency and Wizard Metric Validation

- Align patch pipeline references with the canonical `daw-build` -> `daw-verify` route.
- Replace the illustrative repair-attempt cap with a link to the existing review retry protocol; retry policy is unchanged.
- Reject negative or boolean judge question counts, redundant counts exceeding total counts, and elicited requirement IDs absent from the scenario. Preserve valid zero-count boundaries and existing score formulas, with behavioral regression coverage.

## 2026-11-06: Repository Structural Separation and Operational Packaging

- **Operational Package Separation:** Formally separate the self-contained installed operational runtime package from developer tooling, tests, fixtures, and repository documentation.
- **Canonical Package Layout Definition:** Introduce `scripts/package_layout.py` as the canonical source of truth defining the exact, minimal operational payload (`SKILL.md`, `LICENSE`, `VERSION`, `skills/`, `templates/`, operational `references/`, and operational `scripts/`), preserving relative paths without flattening nested directories and without copying dev tools or tests.
- **Documentation Migration & Split:**
  - Relocate suite change history and architectural decision logs from `references/changes.md` to repository root `CHANGELOG.md`.
  - Split evaluation documentation from `references/evaluation.md` into `docs/evaluation/guide.md` (runner invocation, evaluation protocols, research basis, and criteria) and `docs/evaluation/observations.md` (dated empirical probe and benchmark observations, failure records, and execution limits).
  - Retain all factual research citations, empirical failure findings, and token measurement caveats without fabrication or duplicate sections.
- **Developer Tooling & Fixture Relocation:** Relocate development and evaluation tools (`evaluate.py`, `wizard_bench.py`, `wizard_oracle.py`, `autoresearch_bench.py`) from `scripts/` to `tools/evaluation/` and wizard evaluation fixtures from `references/wizard-bench/` to `tests/fixtures/wizard-bench/`.
- **Operational Self-Containment:** Installed skills run, validate, route, status, update, and uninstall independently from installed paths without requiring source checkout, repository tests, documentation, or network access.

## 2026-11-06: Parent-Owned Proportional Pre-Delivery Coupling Checkpoint

- **Parent-Owned Pre-Delivery Verification:** Formalize parent-owned structural coupling verification enforced before final delivery of any code-changing workflow ([`references/change-coupling.md#prefinal-coupling-checkpoint`](references/change-coupling.md#prefinal-coupling-checkpoint)), evaluating the changed diff and directly affected interfaces/dependencies.
- **Proportional Route Governance:**
  - `feature` and `bugfix`: Reuses current accepted `daw-review` stage structural audit without redundant, duplicate review passes when scope and revision match.
  - `patch`: Retains the canonical minimal `daw-build -> daw-verify` pipeline with bounded parent diff check; introduces no mandatory extra reviewer stage or untangle pass for localized or one-line patches.
  - Documentation-only / non-code: Records an explicit inline N/A rationale within existing plan/handoff/checkpoint structures (`coupling_check: N/A - documentation-only changes with no codebase structural or interface effects`).
- **Escalation to `daw-untangle`:** Escalates to `daw-untangle` only upon demonstrated hidden or unclear dependency/boundary impact requiring deeper source tracing; strictly scoped to the affected area or subsystem, never an unsolicited whole-codebase scan. `daw-untangle` executes strictly read-only analysis without workspace mutation; its output pass denotes completed structural analysis, not runtime proof.
- **Finding Disposition & Evidence Invalidation:** Material correctness, security, or domain invariant findings block final acceptance; unrelated out-of-scope improvements or speculative cleanup are reported separately as follow-up candidates, rejecting unsolicited refactoring. Authorized corrections route via existing `daw-plan`/`daw-build` workflows; any code revision invalidates prior affected review and runtime verification evidence, requiring fresh verification of the current diff before final completion.
- **Instructional Contract & Zero Runtime Hooks:** Strictly an instructional procedural skill rule governing agent cognitive reasoning and parent checkpoints, NOT a Stop hook, background daemon, or automated runtime interceptor. Observability uses existing plan/handoff/checkpoint records (`scope`, `revision`, `evidence`, `disposition`/`reason`) without mandatory new files or schemas. Default user-facing reporting remains concise natural language; canonical JSON envelopes are internal to orchestrator handoffs.

## 2026-11-06: Read-Only Structural Analysis & daw-untangle Subskill Addition

- **Bundled Subskill Addition (`daw-untangle`):** Introduce `daw-untangle` as the 11th bundled execution module in `skills/daw-untangle/SKILL.md` (and canonical sibling symlinks), expanding the suite to 11 execution modules.
- **Dedicated Read-Only Intent (`untangle`):** Add `untangle` as the 9th finite routing intent in `references/suite-manifest.json` under `schema_version: 1` (additive enum), routing strictly to `daw-untangle` with `read_only: true`, `documentation_only: false`, and `evaluates_workspace: false`.
- **Intent Precedence Hierarchy:** Position `untangle` at precedence 2, immediately following `review` (requested diff audit) and preceding `ask` (generic Q&A) and `setup`. Read-only user intent always wins; ignores unknown risk or workspace preferences (no `daw-workspace`, approval execution, or file mutation). Implementation or refactoring requests are never silently routed to `untangle`; they use standard feature/patch pipelines after scope is accepted. Untangle is an explicit, bounded structural investigation, never an unsolicited whole-codebase mandate.
- **Shared Canonical Reference (`references/change-coupling.md`):** Establish canonical principles, inspection taxonomy, and boundary criteria for change coupling. Centers on the core guiding question _"Should these pieces change together?"_ and categorizes structural friction across hidden links (temporal coupling, implicit side effects, shared untyped state), needless links (shallow pass-through layers, speculative abstractions, premature generalization), and surplus taxonomy (trivial boilerplate, redundant DTO mapping). Legitimate protocol retries, security boundaries, and transaction wrappers are explicitly preserved.
- **Read-Only Invariant & Zero-Mutation Boundary:** `daw-untangle` is strictly non-mutating: no source/doc/comment/test edits, no builds/tests/target code execution, and no unapproved command execution. Inspects recorded code, configuration, specifications, and native code intelligence. Returns full canonical internal envelope with scoped findings (location, observed relationship, consequence, proposed boundary, tradeoffs, invariants, verification proposals), decision log, and dependencies. Emits concise user report per shared reporting policy.
- **Installer Historical Compatibility:** Support status inspection, update staging, and clean removal across historical 8-module/7-intent and 10-module/8-intent installations, verifying existing alias symlinks and file inventories, safely linking `daw-untangle` on update, and aborting if collisions with foreign skills exist.

## 2026-11-06: Specification-Driven Development & Spec Kit Mechanism Adoption

- **Comprehensive Specification-Driven Mechanism Adoption:** Coherently adopt high-value specification-driven development mechanisms from GitHub Spec Kit (pinned upstream commit [`3ca735b846afcbcf3304d571f296ec542464e08c`](https://github.com/github/spec-kit/tree/3ca735b846afcbcf3304d571f296ec542464e08c)) across the existing 10 bundled modules (`skills/daw-*/`), 13 specification templates (`templates/`), and canonical procedural standards.
- **Zero Architectural Bloat Invariant:** Implement complete adoption without adding new modules, route intents, workflow stages, execution daemons, background supervisors, hook registries, JSON envelope schema mutations, script changes, runtime dependencies, or package version bumps.
- **Canonical Shared Procedural Contract:** Anchor execution semantics in [`document-quality.md#feature-delivery-contract`](references/document-quality.md#feature-delivery-contract), structured across nine disciplined subsections (A–I):
  - **A. Governance & Authoring Alignment:** Authoring modules (`daw-wizard`, `daw-design`) ingest real project principles and record source provenance, cleanly separating business what/why from technical how. Explicitly track proposed defaults versus decided rules; updating an architectural principle triggers automated synchronization of affected tasks, docs, and acceptance criteria without silent overrides or covert implementation.
  - **B. Clarification & Technical Uncertainty Resolution:** Agents inspect repository facts before querying users. Unresolved questions are ranked by `impact * uncertainty`. Dependent trade-offs are asked sequentially one at a time; independent choices are batched up to 5 per round. Read-only inquiry (`daw-ask`) proposes exact updates via parent orchestration without unauthorized file writes; technical uncertainties are researched before consulting users.
  - **C. Feature Slicing & Behavioral Contract Oracles:** Feature specifications (`prd.md`, `frd.md`) structure deliverables into prioritized user stories with stable IDs and Given/When/Then or equivalent exact input/output/error/state oracles. Inseparable safety or transaction invariants are kept intact; supporting infrastructure tasks require explicit prerequisite justification; business KPIs are not conflated with runtime code acceptance.
  - **D. Traceability, Dependency Graph & Parallel Safety:** Planning enforces an end-to-end traceability mapping (`Requirement/AC ID -> Story ID -> Task ID -> Target File Paths -> Dependencies -> Exact Verification -> Current Evidence`). The `[P]` parallel execution marker strictly requires disjoint file writes and zero shared data or runtime dependencies. Dependency cycles and unknown dependencies fail closed before dispatch.
  - **E. Requirements-Quality Checklist Separation:** Reviewer-owned quality rubrics evaluate prose completeness, clarity, consistency, and verifiability. This qualitative evaluation is strictly decoupled from builder task checkboxes and runtime test execution. Builders cannot self-approve reviewer rubrics, and generic user "proceed" prompts cannot waive blocking quality gates.
  - **F. Prebuild Cross-Artifact Analysis & Readiness Checkpoint:** Plan readiness self-checks are complemented by proportional independent read-only conformity reviews (`daw-review` prebuild readiness checkpoint under parent orchestration) prior to feature-dependent implementation. Reviewers compare scope, governance, requirements, design, and plan consistency, returning structured findings (ID, severity, location, consequence, repair) with explicit coverage denominators; downstream review stages remain strictly governed by the active route (feature and bugfix routes require independent review; trivial settled patch routes proceed directly to verification without additional `daw-review` ceremony).
  - **G. Convergence, Drift Analysis & Scoped Invalidation:** Multi-round verification inspects actual code, authoritative specs, and current runtime evidence, classifying components as `implemented-verified`, `implemented-unverified`, `missing`, `contradicted`, or `blocked`. Detected gaps append genuine uncovered work within accepted scope without duplicate tasks or scope expansion; mutating requirements or code invalidates affected prior evidence and review passes proportionally.
  - **H. Scoped Pause/Resume & Canonical Block State:** Unresolved material decisions, missing credentials, or review blockers pause affected scopes in a canonical `blocked` state with recorded reasons, owners, questions, revisions, and dependencies. Non-interactive silence is not treated as approval. On resumption, scope, revisions, prerequisites, and authorizations are verified before re-dispatch.
  - **I. Local Toolchain Integration & Reusable Verification:** Workflows discover and execute actual project scripts, local test commands, and linters directly from the workspace. Automated verification commands must actually execute and return observable output; simulated check logs are prohibited. Local configurations may strengthen but never weaken canonical safety or acceptance criteria.
- **Explicit Intentional Exclusions:**
  - Omit mandatory single-file schemas (`spec.md`, `plan.md`, `tasks.md`, `constitution.md`, `research.md`); DAW retains its canonical 13-document matrix and inline stage payloads.
  - Omit external daemon supervisors, background services, and pre-tool hooks to preserve Python stdlib zero-dependency portability.
  - Omit unearned builder self-approvals, generic checklist bypasses, and automated unapproved VCS or deployment mutations.
  - Explicitly reject universal efficacy claims: formal specifications and checklists provide cognitive structure and auditability, but software correctness requires empirical execution and verification against domain oracles.

## 2026-11-05: User-Facing Reporting & Handoff Transport Decoupling

- **Separation of Internal Envelope & User Report:** Decouple internal machine-readable canonical handoff JSON envelopes from default conversational user reports (`references/routing.md#user-facing-reports--handoff-transport`). Internal full JSON envelopes remain strictly required for inter-module transitions and parent acceptance, but are no longer unconditionally dumped into human-facing chats.
- **Transport Preference Order:** Formalize handoff delivery hierarchy: (1) structured module/subagent returns or harness-native messages, (2) authorized workflow artifacts whose paths are provided and inspected, and (3) labeled inline fallback checkpoints (`### Internal Handoff Checkpoint (Observable Fallback)`) for observability only when no structured transport exists. Prohibit creating unauthorized throwaway disk files during read-only stages.
- **Default 4-Part User Report:** Standardize default user-facing reports in the user's language containing: (1) outcome & relevant artifact paths, (2) actually exercised checks and limits (clearly identifying provided transcripts as retained without rerunning), (3) unresolved decisions with affected scopes and blocking classifications, and (4) one concrete next action.
- **Explicit Machine-Readable Exception:** Raw, clean JSON output without markdown fences or conversational preamble is emitted when explicitly requested by the user, preserving machine-readable CLI contracts unchanged.
- **Discrete State & Scope Isolation:** Explicitly distinguish five lifecycle states: stage pass, gate eligibility, parent acceptance, workflow completion, and application/runtime readiness. Structural document gate pass does not imply global implementation readiness; unresolved business decisions block only affected modules.

## 2026-11-05: Version 0.1.1 Release

- Implement documentation quality standards, research-informed rubric (`references/document-quality.md`, `references/document-quality-rubric.json`), and deterministic workflow transition gate (`scripts/validate.py docs`).
- Enforce an explicit 5-edge state machine (`intake-authoring`, `authoring-review`, `review-ready`, `review-rework`, `rework-review`) governing document intake, drafting, review, rework, and downstream readiness.
- Require parent-owned expected document target sets (`--documents`) with strict normalized set equality against records, rejecting duplicate targets and alias collisions without mandating all 13 documents.
- Validate grounded source evidence: exact line-range slice quotes and SHA-256 digests verified against regular UTF-8 source files in `--project-root`.
- Require non-empty rationale and grounded source evidence for non-applicable (`not_applicable`) criterion attestations; N/A is an explicit author/reviewer attestation, not an automated bypass.
- Enforce that review verdicts (`review-ready`) require an opaque `reviewer` reference and per-check `decision: "accepted"`. Any subsequent mutation of document or source artifacts invalidates prior eligibility, requiring re-entry via `rework`.
- Implement as a read-only, zero-dependency Python 3.10+ standard library validator without daemon supervisors, background services, or harness pre-tool hooks.
- Establish fresh-agent blind comprehension evaluation protocols and human peer review guidelines, noting that human comprehension remains formally unexercised without live participants.
- Document structural evidence eligibility vs. semantic truth: the validator verifies schema conformity, bounds, hashes, and quotes without certifying semantic prose correctness or making empirical efficacy claims.
- Define parent-owned acceptance boundaries and current runtime evidence requirements across multi-agent workflows.
- Require observable stage transition checkpoints, canonical handoff JSON envelopes, and verified CLI execution outputs before advancing phases.
- Standardize progressive context loading (stage-scoped skill resolution and exact heading lookups) to prevent premature context saturation.
- Align README usage limits and documentation with actual shipped suite capabilities, excluding synthetic benchmark claims and automated daemon supervisor assumptions.

## 2026-11-04: Efficient Context Loading & Observable Transition Checkpoints

- Instruct stage-scoped context loading (load CURRENT stage skill only, never all 10 modules upfront).
- Enforce governance reuse in single-session sequential runs; avoid reloading unchanged root rules.
- Add progressive disclosure for reference documents (consult exact headings only).
- Clarify that the 13-document matrix is not mandatory for settled features or routine bug fixes.
- Enforce emission and display of observable canonical handoff JSON envelopes before stage advancement.
- Emphasize observable contract compliance across plan (expected output + command), review (separate Stage 1 and Stage 2 verdicts/evidence), and verify (latest CLI runtime evidence); illustrative transition envelopes were omitted from the suite at integration.
- Retain observed benchmark evidence from local test rounds: Round 1 (three completed CLI task pairs) and Round 2 (multi-step project goals). Neither established lower token cost or verified canonical handoffs; Round 2 is blocked and incomplete after an unmetered upstream rate-limit failure halted dispatch under the frozen protocol.
- Document honest direct fallback when subagent delegation tools are unavailable.
- Present context reuse as instruction guidance, not as demonstrated compliance or proven token cost reduction.

## 2026-11-04: Parent-Owned Records and Current Evidence

- Add pre-dispatch, result-acceptance, and final-completion boundaries, plus an
  optional criterion/evidence/decision record authored by the parent. Preserve outer
  handoff statuses, inline small-task records, and approval boundaries.
- Integrate verified 2026 journal, conference, and preprint sources with bounded
  implications, including counterevidence that process verification is not reliably
  beneficial. Add acceptance error metrics, independent oracle accounting, and
  explicit handling of missing, duplicate, or fabricated case IDs.
- Extend manual scenarios for forged acceptance, context invalidation, negative-exit
  and source-proof positive controls, pending later stages, and scoped correction.
- Actual local comparisons did not establish reliability improvement: complete runs
  retained false rejections, one checkpoint run fabricated/omitted case IDs, and a
  focused follow-up still conflated stage acceptance with final completion. Record
  these failures and control confounders in the evaluation reference; stop repeated
  prompt retries rather than claiming success.
- Final unified verification: 149 unit tests passed, package validation had no
  findings, suite inspection returned ready, and the optional JSON example parsed.
  No installed-skill update, commit, push, executor, or runtime interceptor was added.

## 2026-11-04: Parent Acceptance Checkpoint

- Separate completed dispatch, proposed module pass, parent acceptance, and workflow
  completion. Require criterion-linked expected/actual observations, current identity
  and revisions, and mandatory dependency joins in existing plan/handoff records.
- Keep validated failure findings usable for explicitly scoped correction without
  counting them as successful stage evidence. Preserve existing outer statuses and
  harness-native instructional scope; add no scheduler, interceptor, or schema.
- Link root governance, canonical handoffs, plan/build/review/verify, and README to the
  checkpoint. Add four manual acceptance scenarios and bounded research rationale
  distinguishing three journal references from two conference papers.
- A single real-harness decision smoke matched four predeclared decisions: reject
  contradicted success, stale/incomplete input, and failed/unexercised verification;
  accept matching current evidence. CLI observations came from disposable signed-add
  artifacts. This is not a controlled efficacy or cross-harness reliability result.
- Unified checks: 149 unit tests passed, package validation had no findings, and suite
  inspection returned ready. No installed-skill update, commit, or push was performed.

## 2026-11-04: Independent Grading and Source-Grounded Documentation

- Separate bookmark validation/update checks from the search-format fixture so an
  invalid-URL defect fails its own criterion without contaminating search grading.
- Derive expense list expectations from date and numeric ID instead of assuming the
  current UTC date follows the fixed January fixtures; retain strict format checks.
- Define accountable documentation authors and mandatory matrix/template reads in
  routing §3. Require observed sources, explicit proposed decisions, and the selected
  document's output and exit criteria without forcing all thirteen documents.
- Add behavioral regressions for grading independence, date boundaries, incorrect
  ordering and formatting. Direct CLI probes exercised the corrected grading paths.
- A documentation behavior probe initially invented domain math and interface details;
  strengthen the source rules and record unresolved commitments explicitly. A corrected
  probe preserved supplied facts and blocked only unsupported commitments. These
  observations are not a guarantee of model reliability.
- Final Linux verification: 149 unit tests passed, package validation reported no
  findings, and suite inspection returned ready. Temporary install/status/package
  validation/uninstall shipped the updated authoring references successfully.

## 2026-11-04: On-Demand Interview and Design Protocols

- Share bounded grilling through one supporting reference used directly by ask, wizard,
  and design; retain ten public modules and nonrecursive, parent-controlled dispatch.
- Add design-owned domain-modeling and builder-readiness references with explicit write
  scope, vocabulary provenance, conjunctive ADR qualification, and material blocker checks.
- Add six manual behavioral scenarios and evaluation guidance. Structural gates and real
  temporary installation confirmed all three resources ship without new module aliases.
- Behavioral probes exercised direct factual answers, authorized updates to an existing
  vocabulary file, and blocked design readiness. Advisory probes exposed premature expiry
  choices and unsupported concurrency guarantees; the protocol now includes a pre-send
  response check. Prompt instructions are not enforcement or a model reliability guarantee.

## 2026-11-04: Canonical Package and Installer Roots

- Resolve package and installation roots before containment, ownership, and alias-target
  comparisons so symlinked ancestors and platform path aliases use the same identity.
- Exercise installer transactions through a symlinked temporary ancestor and add a
  package-validation regression for that layout. Preserve traversal rejection, rollback
  backups, and ownership checks; compare canonical destinations in platform fixtures.
- Verified 141 unit tests, package integrity with zero findings, suite inspection, and
  real install/status/package-validation/update/uninstall CLI operations through an aliased
  temporary root on Linux. Native macOS and Windows verification remains pending CI.

## 2026-11-03: Automatic Conditional Worker Retention

- Make completed-worker retention the intake default for tasks that already warrant
  delegated corrective rounds when the harness supports it, unless the user opts out.
  No persistence keyword or prior setup invocation is required; small direct tasks and
  existing route stages remain unchanged. Unsupported optional continuation uses an
  explicit fresh-worker handoff; explicitly required retention still fails closed.
- Verified 140 unit tests, package integrity with zero findings, and suite inspection.
  A fresh read-only agent applied the policy correctly to supported delegation, direct
  work, optional fallback, opt-out, and required-but-unavailable retention. This was a
  policy-selection smoke, not end-to-end automatic worker dispatch or model-limit proof.

## 2026-11-03: Harness-Native Persistent Worker Graphs

- Define parent-owned worker graphs with same-role session retention, revision-scoped
  dependency joins, independent review, explicit fallback, and existing stop/replan rules.
  This is a skill execution contract, not a new scheduler or durable crash recovery.
- Integrate harness capability discovery and correction-round guidance into setup,
  planning, build, review, verification and debugging; extend the operations scope
  statement and the AGENTS reference inventory to name the contract. Preserve canonical
  `pass`/`fail`/`blocked` envelopes and the read-only router/validator boundaries.
- Add a manual graph pilot protocol and behavioral scenarios; existing evaluator fixtures
  do not establish persistent-worker identity reuse or model compliance.
- Observed an OMP parked-worker revival, then a disposable two-round signed-add pilot:
  the same replacement builder corrected the artifact and the same reviewer rechecked it;
  five actual CLI cases passed. An earlier builder was explicitly replaced during the
  pilot, and unsupported stalled-review claims were rejected.
  Cross-restart recovery and the additional manual edge scenarios were not exercised.
- Verified 140 unit tests, package integrity with zero findings, suite inspection, and
  actual feature-route CLI output. These checks do not prove automatic enforcement or
  persistent-worker support on other harnesses.

## 2026-11-03: Skill Instruction Clarity and Oracle History

- Reviewed the root skill and all ten modules; aligned wizard question pacing to at most five per round, debugging stop thresholds to two consecutive falsified hypotheses without narrowing, and planning document persistence with established project conventions.
- Removed the nonexistent canonical `architecture.md` document and stale `daw-patch` module references. Clarified that implementation belongs to `daw-build`, not the verifier, and improved illustrative review evidence and workspace authorization criteria.
- Initialize wizard transcripts before the first oracle call. History-aware oracles receive an empty file initially and prior completed questions and answers on subsequent turns.
- Verified 140 unit tests, package and suite integrity checks, all 12 JSON examples across 11 skill files, and a public CLI history-aware oracle smoke spanning two interview rounds, specification output, and fixture acceptance. This verifies runner behavior and instruction consistency, not model compliance or interview quality.

## 2026-11-03: Workflow Gate and Handoff Corrections

- Block patch routes with unknown or unclear requirements before build dispatch; retain clear patch and investigative bugfix behavior.
- Verify `.worktrees/` as a directory before its first creation, so directory-only ignore rules are recognized.
- Make module handoffs follow the active route: documentation-only plans and setup terminate with `null`, patches proceed to verification, and feature/bugfix builds proceed to review. Failed or blocked stages do not advance.
- Remove hidden requirement details from all bundled off-topic oracle responses and resolve the documented oracle executable before entering a disposable interview workspace.
- Verified 139 unit tests, package and suite integrity checks, actual routing rejection/acceptance cases, first-worktree creation in a disposable repository, all three off-topic oracle responses, and a two-turn benchmark plumbing run with the documented oracle argv. Handoff instruction checks do not establish model compliance or elicitation quality.

## 2026-11-02: Installer Migration and Benchmark Correctness Fixes

- Excluded hidden scenarios, acceptance scripts, and evaluator tests from staged wizard interview suites without changing source assets; staging is not an OS sandbox.
- Restored status, upgrade, and removal for owned eight-module installations while retaining receipt shape, inventory, alias ownership, collision, and canonical module-path checks.
- Reject acceptance timeouts, malformed or duplicate records, inconsistent exit statuses, and crashes after passing records instead of publishing perfect scores. Ordinary recorded acceptance failures retain fractional scores; custom graders must still emit their complete check set.
- Propagate failed or exhausted interviews and requested judge failures through nonzero CLI exits. Mixed judge results expose graded/error counts and partial-error status rather than silently dropping failed runs.
- Corrected bookmark persistence acceptance so either allowed tag order still requires valid URL, title, and record count.
- Verified 136 unit tests and four public CLI smoke checks, plus direct failure-path and historical-release migration smokes. These checks establish runner correctness, not model efficacy.

## 2026-11-02: Wizard Interview Benchmark and Research-Backed Interview Rules

- Added `scripts/wizard_bench.py`: a two-arm benchmark (`wizard` interview then build from `docs/specs/` only, versus `brief`-only baseline) scored by hidden acceptance tests, with optional strict-schema judge metrics (implicit-requirement elicitation ratio, redundancy, 8-item agent-ready checklist, unsupported claims). Unjudged metrics stay `ungraded`.
- Added three headless scenarios under `references/wizard-bench/` (expense tracker, bookmark manager, log analyzer; 7 hidden requirements each) and `scripts/wizard_oracle.py`, a deterministic keyword-weighted stand-in oracle; an LLM oracle is recommended for real runs.
- `daw-wizard` now filters already-answered questions, asks behavior-changing questions first, caps rounds at 5 questions, enforces the 8-item agent-ready checklist, and handles visual style through a user-supplied `DESIGN.md` or one drafted to the open DESIGN.md format. Sources: ReqElicitGym, CONTRA, Ambig-SWE, Asuka-Bench, Uvik SDD benchmark (cited in `references/evaluation.md`).
- Local gate: 121 tests passed; a scripted end-to-end smoke ran both arms. These results establish runner plumbing, not agent efficacy.

## 2026-11-02: Repository Setup and Greenfield Interview Wizard

- Added `daw-setup`: inspects a repository, confirms conventions with the operator in one batched round, and writes a single `<!-- daw-config:start -->` block (spec directory, test/lint/build commands, workspace policy, high-risk paths, issue tracker, default branch) into `AGENTS.md` or `CLAUDE.md`. New `setup` intent routes to it.
- Added `daw-wizard`: phased interview for blank workspaces that produces a confirmed, proportional subset of the 13-document matrix, recording unanswered material facts as Open Questions instead of inventing them. It is now the first `bootstrap` stage (`daw-wizard` -> `daw-design` -> `daw-plan`) and refuses non-empty targets in favor of `adopt`.
- `daw-design`, `daw-plan`, `daw-build`, `daw-verify` and `daw-workspace` read the configuration block before inferring conventions; values are hints and never grant authorization.
- Suite grows to 10 modules and 8 intents; the installer creates 10 module aliases. Local gate: 116 tests passed with package and suite checks passing.

## 2026-11-02: Installable 0.1.0 Distribution and Review Corrections

- Added an offline stdlib installer for project/user skill directories in Codex, Claude Code, Gemini CLI, Cursor, and Copilot, plus explicit custom directories. Complete bundle copies, relative module aliases, root-only fallback, ownership receipts, staged updates, removal, dry-run parity, locking, and retained recovery copies protect unrelated or edited installations.
- Added the operator-selected MIT license, package version, optional Codex UI metadata for all nine skills, current official discovery references, and source-checkout setup instructions.
- Fixed package containment through symlinked parent directories, conservative required-frontmatter type validation, and diagnostics that echoed untrusted payloads. Router inspection also prevents bytecode writes without requiring caller environment overrides.
- Corrected expected nonzero verification probes, completion of failed conformity reviews with bounded security triage, and the complete-bundle prerequisite in the stateless scenario.
- Added a configurable, opt-in behavioral evaluation runner with retained fixtures, transcripts, timing, source fingerprints, explicit artifact checks, and ungraded human-review criteria. Fake adapters in its tests establish runner plumbing, not agent efficacy.
- Local integration gate: 110 standard-library tests passed, with package and suite checks passing. A fresh-agent cache review returned failed conformity plus limited confidentiality triage without changing fixture bytes. Native Gemini CLI 0.62.0 discovered the root and all eight module aliases in an isolated temporary home.
- Added a GitHub Actions matrix for Linux, macOS, and Windows on Python 3.10/3.14. Hosted matrix execution and cross-client behavioral parity remain unexercised; no release, commit, or push was performed.
- Review corrections: installer receipts ignore bytecode and test caches, so running the bundled tests no longer blocks `status`, `--update`, or `uninstall`; lock collisions name the lock file. Evaluator placeholders substitute in one pass. Package validation reports `path_escapes_package` separately from `symlink_escapes_package` and enforces `version_mismatch` between `VERSION` and `SKILL.md` `metadata.version`. CI action SHA pins were confirmed against their tags.

## 2026-11-02: Module Governance, Canonical Handoffs & Crash Hardening

- **Module Direct Invocation Governance:** Enforced mandatory governance loading sequence across all 8 internal modules (`skills/daw-*/SKILL.md`). Modules resolve root contracts (`SKILL.md` §4 & §6, `references/routing.md` §5 & §6, `references/operations.md` §1 & §2) before executing mutations. High-risk actions fail closed to `blocked` without interactive operator confirmation at point of risk; safe read-only intake and inspection remain unblocked.
- **Canonical Handoff Envelope:** Standardized output across all 8 modules to canonical JSON envelope (`objective`, `input_paths`, `output_paths`, `acceptance_criteria`, `evidence`, `status`, `handoff_to`, `details`). Clarified that top-level `status` is stage-scoped and does not indicate end-to-end delivery. Rich domain facts reside inside `details`.
- **Canonical Template Paths:** Replaced phantom `*.template.md` references in `daw-design` with existing canonical templates (`templates/blueprint.md`, `templates/prd.md`).
- **Validator Complete Stage Crash Hardening:** Hardened `scripts/validate.py` in `complete` stage against non-list evidence structures (`evidence: 42`, `evidence: true`) and unhashable/non-string criterion IDs (`criterion_id: ["AC-1"]`), returning standard JSON error diagnostics without unhandled Python tracebacks.

## 2026-11-02: DAW Suite Architecture, Router Dispatch & Bundled Modules

- **Full Suite Architecture:** Expanded the standalone workflow into a cohesive 8-module suite bundled in `skills/daw-*/`:
  - `daw-design`: Specification authoring, technical requirements, and 13-doc matrix.
  - `daw-plan`: Task decomposition, execution sequencing, and task contracts.
  - `daw-debug`: Root cause analysis, minimal reproduction, and failure diagnostics.
  - `daw-build`: Implementation, code editing, and minimal change construction.
  - `daw-review`: Two-stage code review, architectural boundaries, and security audit.
  - `daw-verify`: Behavioral verification, test execution, and regression proof.
  - `daw-workspace`: Isolated workspace/worktree setup and lifecycle containment.
  - `daw-ask`: Read-only architecture advisory, contextual trade-offs, and Q&A.
- **Root Router Refactoring:** Rewrote root `SKILL.md` to act as the central dispatcher and governance contract. Removed duplicated execution prose from root; delegated depth to internal modules while preserving core bootstrap/adopt doc actions and safety gates.
- **Declarative Route Policy & Safety Limits:** Codified `references/suite-manifest.json` (schema 1) as the declarative route policy validated by `scripts/route.py` against exact canonical v1 stage pipelines. Implemented strict payload bounds (1 MiB request/manifest, 256 KiB module skill), finite type parsing, duplicate key rejection, and error value redaction.
- **Finite Intent Precedence:** Established strict classification precedence (`ask` -> `review` -> `bootstrap` -> `adopt` -> `bugfix` -> `patch` -> `feature`) requiring structured input facts. Disallowed arbitrary keyword heuristics.
- **Suite Integrity Verification (`--check-suite`):** Added `python3 scripts/route.py --check-suite` to validate manifest schema and verify all 8 internal modules exist within root without path traversal.
- **Suite Self-Contained Invariant:** Codified that the suite is completely self-contained with no external framework dependencies (e.g. Superpowers), but strictly requires all 8 internal bundled modules. Missing internal modules block execution without silent shallow fallback.
- **Distribution & Symlink Architecture:** Documented nested bundle layout and sibling symlinks (`daw-* -> deterministic-agentic-workflow/skills/daw-*`) for portable agent harness discovery.
- **Behavior Scenarios Matrix:** Authored `tests/behavior-scenarios.md` with 7 rigorous behavior scenarios covering failing-before/passing-after coding bug, feature test loop, review repair, read-only advisor, high-risk approval failure, workspace preservation, and finite routing boundary.
- **Observed Verification:** Package validation, suite integrity validation, and 72 standard-library regression tests passed on Python 3.14.7/Linux. All 189 finite routing combinations were evaluated twice with identical results; real CLI checks exercised ready, read-only, needs-input, error, redaction, and high-risk planning with authorization permanently false. CLI snapshots were unchanged.
- **Procedural Smoke Evidence:** Fresh agents fixed a pagination boundary bug (4 passing behavior tests), implemented strict stock validation (5 passing tests after correcting initially absent discoverable coverage), completed read-only advice and two-stage cache review, then repaired and independently rereviewed customer-specific cache behavior (1 passing regression). High-risk planning executed nothing. Workspace assessment and explicitly authorized sibling worktree creation preserved the original branch and uncommitted file hashes. Router bootstrap authored six default specifications without application code.
- **Coverage Preservation & Limits:** Retained the nine existing document/lifecycle scenarios and added seven suite procedure scenarios. Early integration failures exposed lost schema documentation, non-portable installation examples, and a stale test assertion; these were repaired rather than weakening validation. These checks demonstrate observed behavior, not parity certification, runtime interception, automatic authorization, or cross-client execution. No Git hooks, external dependencies, commits, or pushes were added.
