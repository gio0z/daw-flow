# ERD and Application Lifecycle Correction

## Specification

- Status: authoring; parent-owned record. Scope: DAW suite instructions, templates, document registries and their existing behavioral checks.
- Source: user authorizes all findings from the application-flow comparison and explicitly requests ERD as a separate document. Baseline source revision: f1bdfda.
- Audience/task: suite maintainers and agents selecting, authoring, reviewing and validating project documents.
- Objective: make Blueprint substantive, introduce a separate first-class ERD document, and close the post-release feedback/incident loop through existing routes.
- Non-goals: no new module/route, deployment or monitoring automation, semantic keyword parser, dependency, production schema operation, commit/push or installed-skill update. Mockup remains an artifact rather than a canonical document kind.

### Requirements and acceptance criteria

- REQ-LC-01 / AC-LC-01: When a Blueprint is authored, its template guides system context/boundaries, components/responsibilities, primary interaction/data flows, domain invariants and failure/transaction boundaries. Detailed relationships reference the separate ERD; no invented architecture or duplicated data authority.
- REQ-LC-02 / AC-LC-02: When persisted entities or relationships are introduced, materially changed or adopted without an adequate existing model, select a separate ERD document using repository conventions (default erd.md). It covers logical entities/identity, relationships with cardinality/optionality, integrity/ownership/lifecycle and traceability. Physical PK/FK/index/deletion details apply only when storage choices warrant them; no invented schema or migration authorization. No applicable persistent model means scoped skip/N/A. Reuse an adequate separate existing model.
- REQ-LC-03 / AC-LC-03: The package validator requires templates/erd.md, accepts erd as a contract document kind, and the docs transition gate accepts erd with DQ-01..05 plus erd-01..03 while rejecting missing or foreign criteria and stale evidence. The current catalog has 14 kinds, full-suite requests cover all 14, baseline six remains unchanged plus conditional ERD. Old kinds and routes remain valid.
- REQ-LC-04 / AC-LC-04: For authorized post-release feedback or incident handling, parent records source/release/evidence, impact and owner; distinguishes bug, new requirement, operational incident and no-change/deferred outcomes; uses existing routes with prerequisites/approvals intact. Closure requires disposition, linked REQ/AC/task where actioned, parent-observed scoped verification and post-release evidence if actually deployed. Local verification never claims production resolution; no automatic publication or monitoring.
- REQ-LC-05 / AC-LC-05: All current authoritative instructions, matrices and examples consistently expose ERD and the feedback loop; historical changelog/evaluation records remain historical. QA/build/mockup rules are retained, not rewritten as new capabilities. All checks are reported at their actual evidence level.

## Plan

All slices depend on parent acceptance of this plan's readiness review. They then run concurrently on disjoint files; workers skip tests/lint/build/formatters. Parent alone runs final integration checks. No LSP server is configured; scoped source inspection is the available intelligence fallback. ERD criteria contract: erd-01 entities/identity and sourced attributes; erd-02 relationships/cardinality/optionality and ownership; erd-03 integrity/lifecycle/traceability and applicable physical design. Five common DQ criteria and outer schemas remain unchanged.

| Task  | Owner             | Exact files                                                                                                                                                                                                               | AC       | Expected verification                                                                                   |
| ----- | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------- |
| LC-T1 | BlueprintErd      | templates/blueprint.md, templates/erd.md, templates/frd.md, templates/techstack.md                                                                                                                                        | 01,02    | Concrete architecture prompts; separate nonduplicated ERD authority; rubric checklist matches           |
| LC-T2 | ErdRegistry       | scripts/validate.py, scripts/doc_quality.py, references/document-quality-rubric.json, references/document-quality.md, tests/test_validate.py, tests/test_doc_quality.py, tests/test_doc_rubric.py, tests/test_evaluate.py | 03       | Existing unittest suite; real CLI accepts erd, rejects missing template/check/stale hash                |
| LC-T3 | MatrixDocs        | SKILL.md, references/routing.md, references/validation.md, README.md, AGENTS.md, docs/PRD.md, docs/BRD.md, docs/DESIGN.md, docs/evaluation/guide.md, CHANGELOG.md                                                         | 02,03,05 | 14-kind matrix + routing labels, six baseline + conditional ERD, no current count contradictions        |
| LC-T4 | DesignPropagation | skills/daw-design/SKILL.md, skills/daw-design/references/builder-readiness.md, skills/daw-design/references/domain-modeling.md, skills/daw-plan/SKILL.md, skills/daw-wizard/SKILL.md, references/workflow-artifacts.md    | 01,02,05 | Conditional ERD selection/readiness and domain-before-physical-design; mockup still not a kind          |
| LC-T5 | MaintainLoop      | references/operations.md, templates/deployment.md, templates/runbook.md, skills/daw-verify/SKILL.md, skills/daw-debug/SKILL.md, tests/behavior-scenarios.md                                                               | 04,05    | Evidence-backed intake/routing/closure examples, local vs deployed proof distinction, scenario coverage |

Parent integration: independent scoped postbuild review; run unittest discovery, package CLI and suite CLI; smoke docs transitions for erd in disposable fixtures (valid and invalid cases) plus inspect bounded feedback cases (bug/new requirement/deferred/local-only). Structural checks do not prove semantic model quality or autonomous agent compliance. Add no source-text assertion tests. Parent writes criterion-specific acceptance and actual evidence here after checks; current evidence is unexercised.

## Progress

- Actual stage: completed local integration and verification; parent acceptance recorded below. Not committed, pushed, or installed.
- Active tasks: none.
- Spec ref: this file, Specification section; baseline f1bdfda plus current scoped bytes.
- Plan ref: this file, Plan section; owner parent, saved after Specification.
- Blockers: none. Mockup: N/A, suite governance/CLI change without product UI.
- Acceptance: readiness accepted (ReadinessReplacement, FastReadiness). LC-T1..5 accepted by parent per criterion below.
- Next permitted action: operator inspects local changes; commit/push/install only on explicit request.

### Observations and triage

- Readiness reviewer LifecycleReadiness failed at transport (stream stall), supplied no completed verdict; not accepted, replaced by ReadinessReplacement. No implementation dispatched on that failure.
- Formal specification intake gate: docs/PRD.md, intake-authoring, eligible true with zero findings. First temporary record outside project root was rejected as record_path_outside_root; retried with contained temporary record and removed it after use.
- Before-change CLI smoke: a grounded erd intake record is rejected with doc_kind_invalid (exit 1). This is the expected missing-kind behavior, not a model-quality finding.
- Registry/template seam: frd-01 retains behavioral payload types/validation and references ERD for persistent identity/relationships; no wholesale removal of existing FRD contracts.
- ReadinessReplacement transport delivered a review verdict but omitted the requested full handoff envelope; bounded review evidence accepted, not misrepresented as a schema-valid module envelope. Parent owns this readiness decision. Formal outer schema compliance remains a reporting limitation, not an implementation result.
- FastReadiness independently returned PASS with three verification additions, accepted by parent: smoke all four feedback outcomes (bug, new requirement, operational incident, no-change/deferred) plus local-only proof; reject foreign ERD criteria; sweep T3/T4/T5 outputs for 14-kind, baseline-six and conditional ERD consistency. Unit tests listed for LC-T2 are parent-run only.
- Integration corrections by parent: removed duplicate techstack routing heading (reported to MatrixDocs, fixed there); aligned techstack-01 checklist with rubric (SliceReview P3); restored historical WF non-goal wording and replaced colliding PRD REQ-LC-01/02 with a pointer to this spec; SCN-06 and a patch scenario updated from 13 to 14 / generic matrix wording; ERD routing title aligned to "Entity-Relationship Document" and vendor-named capability replaced with generic database design capability.
- Independent postbuild reviews: SliceReview (non-matrix slices) correct, one P3 fixed; MatrixReview (matrix/docs slice) correct, no findings. Changelog diff is additive only.

### Parent acceptance (current working tree over f1bdfda)

- AC-LC-01 accepted: templates/blueprint.md has context/boundaries, components/interfaces, interaction/data flows, domain invariants, failure/transaction boundaries, and links ERD; blueprint-01 rubric matches.
- AC-LC-02 accepted: templates/erd.md is logical-first (entities/identity, relationships/cardinality/optionality/ownership, integrity/lifecycle/traceability), physical design conditional, explicitly no schema/migration authorization; selection is conditional with scoped N/A and reuse.
- AC-LC-03 accepted: unittest discovery 246 tests OK (1 skip); package VALID with 14 templates/14 routing sections; suite ready. Real CLI smoke in disposable fixture: erd intake/authoring-review/review-ready eligible; foreign criterion (check_id_unknown), missing erd-03 (missing_checks) and post-review edit (doc_sha256_mismatch) rejected; legacy frd intake still eligible. Before change, erd intake was rejected (doc_kind_invalid).
- AC-LC-04 accepted at instruction level: references/operations.md Post-Release Feedback & Incident Closure (intake, four dispositions, existing routes, closure gates, local proof recorded as production resolution unexercised, monitoring opt-in), surfaced in deployment/runbook/debug/verify; manual scenarios SCN-M-01..05. Scenarios are unexecuted manual expectations.
- AC-LC-05 accepted: cross-file sweep finds no current 13-kind claim outside historical records; mockup remains non-kind.
- Limits: structural checks do not prove ERD semantic quality or autonomous agent compliance; behavior scenarios not run with fresh agents. Coupling checkpoint: registry change is contained to existing tuples/rubric and derived counts; no route, module, schema version, or outer handoff change.
