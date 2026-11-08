# Product Requirements Document (PRD)

## Deterministic Agentic Workflow

### 1. Product Overview & Purpose

Deterministic Agentic Workflow is an open-source, portable specification, suite router, and verification utility for AI coding agents. It provides a formal contract between generative planning and deterministic execution, enforcing pre-code documentation, role specialization across deep modular skills (`skills/daw-*`), declarative route resolution (`scripts/route.py`), fail-closed approval capturing, and stage-gated contract lifecycle verification (`scripts/validate.py`).

### 2. User Personas

- **Developer / Human Operator:** Configures project rules, reviews task contracts, reviews destructive approval requests, inspects routing plans, and evaluates validation output.
- **Autonomous Agent (Suite Router / Orchestrator):** Reads `SKILL.md`, executes declarative routing requests against `scripts/route.py`, evaluates the execution pipeline, and coordinates specialized module skills.
- **Specialized Module Worker (Agent):** Executes deep, bounded procedures (`daw-design`, `daw-plan`, `daw-debug`, `daw-build`, `daw-review`, `daw-verify`, `daw-workspace`, `daw-ask`, `daw-setup`, `daw-wizard`, `daw-untangle`), authoring specifications, executing code changes, performing read-only advisory, or conducting structural change-coupling investigation without persona impersonation, and returning clean handoffs without recursive router invocation.
- **Automated Quality Gate (CI / Harness):** Runs package, suite structure (`route.py --check-suite`), and contract validation in headless pipelines, evaluating deterministic exit codes to allow or reject progression.

### 3. Functional Requirements & Acceptance Criteria

#### Category: Package Integrity (`PKG`)

- **REQ-PKG-01: Structure & Manifest Verification**
  - _Description:_ The validator must inspect the skill root and verify the presence of mandatory files: `SKILL.md`, `references/routing.md`, `references/operations.md`, `references/validation.md`, `references/installation.md`, `references/task-contract.example.json`, and all 14 canonical template files in `templates/`.
  - _AC-PKG-01.1:_ Running `validate.py package` returns exit code 0 when all 20 structural files exist and are readable.
  - _AC-PKG-01.2:_ When any required file is missing, the validator returns exit code 1 with finding code `PKG_FILE_MISSING` indicating the exact missing path.
- **REQ-PKG-02: Document Link Resolution**
  - _Description:_ The validator must parse markdown links in `SKILL.md` and reference files, resolving local file targets.
  - _AC-PKG-02.1:_ Broken internal markdown links generate finding code `PKG_LINK_BROKEN` with source file, link target, and line context.

#### Category: Task Contract Lifecycle (`CTR`)

- **REQ-CTR-01: JSON Envelope & Duplicate Key Detection**
  - _Description:_ Task contracts must be strictly formatted JSON with unique keys.
  - _AC-CTR-01.1:_ Contracts containing duplicate JSON keys must fail closed with finding code `CTR_DUPLICATE_KEY`.
  - _AC-CTR-01.2:_ Malformed JSON must fail closed with finding code `CTR_INVALID_JSON`.
- **REQ-CTR-02: Stage Semantics & Transitions**
  - _Description:_ The validator must support three distinct lifecycle stages: `plan`, `execute`, and `complete`.
  - _AC-CTR-02.1 (`plan`):_ Requires canonical schema fields (`schema_version: 1`, `objective`, `baseline`, `documents`, `acceptance_criteria`, `operation`). Preflight baseline file checks verify that referenced files exist within `--project-root` and match their recorded SHA-256 digests on disk (warns if empty).
  - _AC-CTR-02.2 (`execute`):_ Requires all `plan` fields with non-empty `baseline.files`. Preflight baseline verification confirms on-disk existence and SHA-256 digest match for all baseline files before mutations begin. High-risk operations require an approval object.
  - _AC-CTR-02.3 (`complete`):_ Requires all structural `execute` fields with non-empty `baseline.files`, but does not re-verify live on-disk existence or hash equality against baseline files (allowing legitimate modifications, renames, and deletions). Requires mandatory `evidence` array mapping to existing disk files covering all acceptance criteria with status `"passed"`.
- **REQ-CTR-03: Boundary Enforcement & Path Security**
  - _Description:_ All target paths, document paths, and evidence paths must remain strictly bounded within `--project-root`.
  - _AC-CTR-03.1:_ Path traversal patterns (`../`, absolute paths attempting to escape root) must trigger `CTR_BOUNDARY_VIOLATION` and exit code 1.
- **REQ-CTR-04: Approval Capturing vs Proof of Authorization**
  - _Description:_ The validator must capture and verify the structure of human approval records for destructive triggers.
  - _AC-CTR-04.1:_ For operations with `risk: "high"`, `approval` must be provided in stages `execute` and `complete` as an opaque reference object whose `action`, `target`, `revision`, and `scope` fields strictly bind to `operation`.
  - _AC-CTR-04.2:_ Structural validation of an approval object constitutes proof of captured intent, not proof of cryptographic identity or runtime authorization tokens.

#### Category: Capability & Document Routing (`RTE`)

- **REQ-RTE-01: 14-Document Matrix Routing**
  - _Description:_ The workflow must provide unambiguous routing rules defining required documents and technical capabilities based on task impact tiers, scaled proportionally to task scope.
  - _AC-RTE-01.1:_ Small scoped fixes (single-line or localized bug fixes, typos) operate in zero-doc patch mode with an explicit documented reason (e.g., localized bug fix, bounded scope) rather than forcing synthetic specification bundles.
  - _AC-RTE-01.2:_ Full feature additions require a proportional written specification appropriate to the feature scope before code modification begins; the 14-document suite is required only when explicitly requested under REQ-MOD-01.
  - _AC-RTE-01.3:_ Required capabilities may be fulfilled directly by the current agent or delegated to a qualified subagent without requiring external skill registry lookups or named external skill dependencies.

#### Category: Lifecycle Invocation & Mode Precedence (`MOD`)

- **REQ-MOD-01: Execution Mode Resolution & Precedence**
  - _Description:_ The agent must resolve operating mode according to strict precedence rules: explicit review/audit (read-only) > explicit feature/fix (change) > explicit existing-project setup (adopt) > explicit new setup (bootstrap) > bare invocation (inspect target; enter adopt if implementation exists else bootstrap).
  - _AC-MOD-01.1:_ When an explicit mode is instructed, it supersedes heuristics or target state. Explicit review mode strictly forbids file creation or state mutations.
  - _AC-MOD-01.2:_ In bare invocation on an empty workspace without a product brief, the agent must inspect the workspace and ask exactly one clarifying question regarding product intent, rather than inventing synthetic features or phantom requirements.
- **REQ-MOD-02: Observable Document Action Transparency**
  - _Description:_ The agent must announce its operating mode, resolve target scope from user context or `cwd`, and output a structured document action table: planned actions (`create`, `update`, `reuse`, `skip`, `blocked` with path and reason) prior to execution, and final completed actions (`created`, `updated`, `reused`, `skipped`, `blocked` with path and reason) upon completion.
  - _AC-MOD-02.1:_ The agent must clearly distinguish planned document actions from final completed actions.
  - _AC-MOD-02.2:_ During adoption of an existing codebase, the agent must inspect actual code, dependencies, and docs, authoring missing baseline specifications from observed facts while preserving existing code and user-authored documents.
  - _AC-MOD-02.3:_ When an explicit full 14-document suite is requested, the agent must honor all requested documents with substantive scoped content or document explicit blockers/applicability limits, never silently shrinking the suite.
  - _AC-MOD-02.4:_ Baseline specs are the six contracts (`blueprint`, `prd`, `frd`, `techstack`, `security`, `roadmap`) plus conditional ERD when persisted entities/relationships are introduced, materially changed, or adopted without an adequate existing model; otherwise ERD records scoped skip/N/A. Reuse an adequate separate existing model.
  - _AC-MOD-02.5:_ ERD ownership: Blueprint = boundaries/components/flows/domain invariants linking ERD; ERD = persistent entities/relationships; FRD retains behavior/payload validation linked to ERD; techstack references ERD for the storage model. No invented schema or migration authorization.

#### Category: Workflow Artifacts &amp; Acceptance Quality (`WF`)

- **REQ-WF-01: Clear, observable acceptance criteria**
  - _Description:_ Acceptance criteria use canonical semantic EARS guidance with five patterns and optional composition, state the observable response or oracle, separate normal and error behavior, and treat no keyword parser, invented policy or number, or forced five-pattern use as the truth source. Given/When/Then remains valid.
  - _AC-WF-01.1:_ Every acceptance criterion states an observable response that can be checked without a keyword parser.
  - _AC-WF-01.2:_ Normal and error behavior are stated separately for every acceptance criterion.
  - _AC-WF-01.3:_ Acceptance criteria invent no policy, number, or dataset beyond the requirement source.
  - _AC-WF-01.4:_ Given/When/Then is accepted as valid acceptance-criteria form.
- **REQ-WF-02: Written specification before planning**
  - _Description:_ For multi-step authorized work, the parent persists a proportional authoritative specification before tactical decomposition, reusing adequate current specs and recording faithful bounded what/why/non-goals/AC for clear user requirements without a written source. The planner does not invent architecture or business choices; material ambiguity returns to the existing design/clarification route rather than a new daw-design insertion. Bootstrap starts from blueprint/domain/flow before UI/data design. Tiny settled patches and factual/read-only inquiries retain no-document paths.
  - _AC-WF-02.1:_ User requirements with no adequate written source have their faithful bounded what/why/non-goals/AC recorded in the chosen spec before daw-plan.
  - _AC-WF-02.2:_ Material ambiguity is returned to the existing design/clarification route; clear routes gain no new daw-design insertion.
  - _AC-WF-02.3:_ Tiny settled patches and factual/read-only inquiries remain on the no-document path.
  - _AC-WF-02.4:_ Bootstrap records blueprint/domain/flow before UI/data design.
- **REQ-WF-03: Specification-to-task verification mapping**
  - _Description:_ Multi-step plans persist stable requirement/AC IDs mapped to task IDs, exact target files, dependencies, parallel ownership, expected observations/check actions, evidence, and separate parent acceptance, with bound spec source revisions. Planned commands/checkboxes are not evidence; supporting infra is justified; one-off execution includes bounded tools/commands, expected results, and rollback only when relevant.
  - _AC-WF-03.1:_ Every planned task cites its requirement/AC IDs, exact target files, dependencies, and owner.
  - _AC-WF-03.2:_ Every planned task states expected verification that is not yet exercised and keeps parent acceptance distinct from worker pass.
  - _AC-WF-03.3:_ Planned commands and checkboxes are not presented as evidence.
- **REQ-WF-04: Persistent multi-step execution plan**
  - _Description:_ Multi-step plans are saved before build dispatch in an existing roadmap/issue-export/project document section when sufficient, otherwise in `docs/plans/<workflow-id>.md`. A chat payload or native todo is insufficient; task-tracker authority is not duplicated. The existing handoff details reference the plan artifact without changing the outer JSON schema. One document with separate spec, plan, and progress sections is allowed and preferred when lean.
  - _AC-WF-04.1:_ A persisted plan artifact exists before build dispatch for multi-step work.
  - _AC-WF-04.2:_ The plan reference appears in existing handoff details without changing the outer JSON schema.
  - _AC-WF-04.3:_ No second task tracker is introduced as concurrent authority.
- **REQ-WF-05: Durable project progress from intake**
  - _Description:_ A parent-owned durable project progress document/section is required from intake, using the established project document location with default `docs/workflows/<workflow-id>.md`, referencing specification/plan (default new specification `docs/specs/<workflow-id>.md` if no convention). It starts early even while clarifying with explicit not-yet-created references; states active module/stage and subphase, active tasks, accepted stages, current scoped revisions, blockers/owner/question, next permitted action, primary evidence/handoff refs, and parent acceptance distinct from worker pass. It updates on real phase entry/acceptance, correction, block/resume, relevant revision change, stop/final. The parent is sole owner; workers return proposals; read-only roles never write. A route list is not active state; desired work is not actual progress. History stays compact without fake percentages/approvals; resume reloads/revalidates current references and preserves retries and scoped invalidation. This is not a daemon, crash recovery, or runtime enforcement; the validator remains stateless.
  - _AC-WF-05.1:_ A parent-owned progress record exists from intake and names the actual active stage, subphase, and active task(s).
  - _AC-WF-05.2:_ Accepted stages, scoped revisions, blockers, owner, next permitted action, and parent acceptance are recorded distinctly from worker results.
  - _AC-WF-05.3:_ The record starts before active stage completion and uses explicit not-yet-created references for missing artifacts.
- **REQ-WF-06: Visual mockup before UI implementation**
  - _Description:_ UI-affecting work requires an actual inspectable rendered visual mockup, not prose, ASCII, or wireframe alone, derived from settled domain/flow and existing design source before UI implementation. An existing matching mockup may be reused. Relevant screens, behavior states, viewports, keyboard/focus, and requirement/AC/screen IDs are reviewed. The editable source or durable design reference and visual preview are saved using the actual available design/export/browser capability, with no vendor mandate and no external publish/account/asset actions without permission. Material missing capability/direction blocks only the UI scope, with no silent text fallback. Mockup acceptance is not runtime implementation proof or automatic human approval. No UI means explicit scoped N/A; small nonvisual fixes reuse existing material.
  - _AC-WF-06.1:_ UI work links requirement/AC/screen IDs and has an inspectable rendered mockup available before UI implementation.
  - _AC-WF-06.2:_ Missing material direction or capability blocks UI scope and does not silently fall back to text-only mockups.
  - _AC-WF-06.3:_ No-UI work records explicit scoped N/A for the mockup requirement.
  - _AC-WF-06.4:_ Mockup acceptance is not presented as runtime implementation proof or automatic human approval.
- **REQ-WF-07: Subagent-result triage and prioritized fix ranking**
  - _Description:_ Every completed subagent result is parent-triaged and ranked for prioritized fixing without noise, including rejected, stale, no-findings, and cancelled results — not only results that get integrated. Each worker returns findings or remaining fixes in its own proposed priority order plus evidence-backed remaining findings or an explicit no-actionable-finding statement; the parent independently validates and globally reranks across all returned results. Triage records result/finding ID, source worker, scope/current revision plus primary evidence, severity/impact, urgency justification, dependency/unblock relation, relative rank, disposition and next permitted action, and integration target plus observed verification/acceptance reference. Safety/correctness/material-acceptance blockers rank above nonblocking polish; severity stays distinct from executable order so a prerequisite may run before a higher-impact dependent fix. Deduplicate same-root-cause findings preserving source refs; unsupported/stale findings require bounded proof or rejection rather than auto-fix. No-findings results receive a concise no-corrective-action disposition after scoped sufficient source proof, not invented work. The parent owns acceptance; a child result or worker pass is never parent acceptance and a worker pass never authorizes external deployment. External deployment is not automatic: an ambiguous deploy instruction means integrate into the intended work target only, and real production deployment requires the exact user-specified target, scope, and point-of-risk permission.
  - _AC-WF-07.1:_ Every completed worker result receives a parent triage record — including integrated, rejected, stale, no-findings, and cancelled results — with source worker, current revision plus primary evidence, rank reason, disposition, next permitted action, and verification/integration reference.
  - _AC-WF-07.2:_ Workers propose priority order for their own findings; the parent globally reranks across all returned results by severity/impact, urgency, and dependency unblock effect, keeping severity distinct from dispatch order.
  - _AC-WF-07.3:_ Parent acceptance is recorded separately from any child worker pass; a worker pass never authorizes external deploy.
  - _AC-WF-07.4:_ External or production deployment is not performed automatically from an ambiguous deploy instruction; it requires the exact user-specified target, scope, and point-of-risk permission.
  - _AC-WF-07.5:_ Accepted in-scope corrective findings close only via integration into the intended target plus parent-observed verification on the current revision; rejected, out-of-scope, or advisory findings and merged duplicates close only with an explicit reason and source/merged reference, never via forced unauthorized fix; clean no-findings results close with sufficient bounded evidence and a concise no-actionable-finding disposition.

#### Category: Suite Routing & Module Execution (`RTE`)

- **REQ-RTE-01: Declarative Route Manifest & Policy**
  - _Description:_ Suite routing must be governed declaratively by `references/suite-manifest.json` via `scripts/route.py REQUEST`.
  - _AC-RTE-01.1:_ Input request schema requires strict JSON keys: `schema_version` (integer 1), `intent` (`bootstrap` | `adopt` | `feature` | `bugfix` | `patch` | `review` | `untangle` | `ask` | `setup` | `refactor` | `maintain` | `spike` | `ship`), `requirements` (`clear` | `unclear` | `unknown`), `risk` (`low` | `high` | `unknown`), and `workspace` (`in-place` | `isolated` | `unknown`). Rejects unknown keys, duplicate keys, or nonstandard constants.
  - _AC-RTE-01.2:_ Output response schema guarantees deterministic keys: `schema_version`, `status` (`ready` | `needs-input` | `blocked`), `stages` (ordered list of module names), `reasons` (list of strings), `blockers` (list of code/message objects), `constraints` (`read_only`, `documentation_only`, `interactive_approval_required`, `authorization_granted: false`), and `limitations` (list of strings).
  - _AC-RTE-01.3:_ Route execution exit codes: `0` (route ready), `1` (needs-input or incomplete modules), `2` (malformed input, manifest violation, or CLI usage error).
- **REQ-RTE-02: Policy Routing Logic & Workspace Selection**
  - `bootstrap` -> `[daw-wizard, daw-design, daw-plan]` (`documentation_only: true`).
  - `adopt` -> `[daw-design, daw-plan]` (`documentation_only: true`).
  - `setup` -> `[daw-setup]` (`documentation_only: true`).
  - `feature` with clear requirements -> `[daw-plan, daw-build, daw-review, daw-verify]`.
  - `feature` with unclear requirements -> `[daw-design, daw-plan, daw-build, daw-review, daw-verify]`.
  - `bugfix` -> `[daw-debug, daw-plan, daw-build, daw-review, daw-verify]`.
  - `patch` -> `[daw-build, daw-verify]`.
  - `review` -> `[daw-review]` (`read_only: true`).
  - `ask` -> `[daw-ask]` (`read_only: true`).
  - `untangle` -> `[daw-untangle]` (`read_only: true`).
  - `refactor` -> `[daw-untangle, daw-plan, daw-build, daw-review, daw-verify]`.
  - `maintain` -> `[daw-plan, daw-build, daw-review, daw-verify]`.
  - `spike` -> `[daw-workspace, daw-build, daw-ask]` (always isolated, throwaway output).
  - `ship` -> `[daw-ship]` (integration-only; unknown risk -> `needs-input`, high risk -> interactive approval).
  - _AC-RTE-02.1:_ For mutating intents (`feature`, `bugfix`, `patch`, `refactor`, `maintain`), when `workspace` is `isolated`, `daw-workspace` is prepended to the stage list. When `workspace` is `in-place`, execution proceeds normal. When `workspace` is `unknown`, status is `needs-input`.
  - _AC-RTE-02.2:_ Read-only intents (`ask`, `review`, `untangle`) ignore unknown risk and unknown workspace.
  - _AC-RTE-02.3:_ When `risk` is `high`, `constraints.interactive_approval_required` is set to `true`, and `constraints.authorization_granted` is permanently `false`.
- **REQ-RTE-03: Structural Suite Verification (`--check-suite`)**
  - _Description:_ `scripts/route.py --check-suite [--root ROOT]` validates structural consistency of the suite manifest and bundled modules without modifying existing validator contracts.
  - _AC-RTE-03.1:_ Validates all 12 declared module paths exist within the root boundary, checks frontmatter scalar integrity, and verifies route mapping soundness.
  - _AC-RTE-03.2:_ Returns exit code 0 when the suite is complete and sound; returns exit code 1 if any module or route definition is broken or missing.

### 4. Non-Functional Requirements

- **NFR-01: Standard Library Compatibility:** Must execute on Python 3.10, 3.11, 3.12, 3.13, and 3.14 using only the Python standard library.
- **NFR-02: Zero Network Access:** Must operate completely offline with no HTTP/HTTPS requests, socket creation, or external API dependencies.
- **NFR-03: Execution Performance:** Package validation and suite routing checks must execute in under 200ms on standard developer hardware.
- **NFR-04: Deterministic Output:** Text and JSON envelopes must produce identical, sorted findings across repeated runs on identical inputs.
- **NFR-05: Deep Module Independence & Distribution:** Modules are bundled under `skills/daw-*` with relative links to suite root. In installed environments, sibling symlinks point to bundled modules. Standalone unbundled distribution is unsupported.

### 5. Scope & Non-Goals

- **In Scope:**
  - Suite router and 12 specialized modular skills (`daw-design`, `daw-plan`, `daw-debug`, `daw-build`, `daw-review`, `daw-verify`, `daw-workspace`, `daw-ask`, `daw-setup`, `daw-wizard`, `daw-untangle`, `daw-ship`).
  - Declarative route policy engine and structural check (`scripts/route.py`, `references/suite-manifest.json`).
  - Static structural validation of skill packages and task contract schemas via `scripts/validate.py`.
  - Hash matching against disk files and root path containment verification.
- **Non-Goals:**
  - Automated code execution, shell hook enforcement, or background daemons inside the route engine or validator.
  - Persona impersonation or external identity spoofing in advisory skills (`daw-ask`).
  - Runtime credential validation or cryptographic authorization tokens.
  - Standalone unbundled distribution of child modules without the suite root.
- **Professional delivery lifecycle (PDL):** The `refactor`, `maintain`, `spike`, and `ship` intents (12-module suite, 13 intents) are authoritative in [`references/developer-lifecycle.md`](../references/developer-lifecycle.md): inner loop, time-boxing, spike, behavior-preserving refactor, maintenance upgrade, bisection, commit hygiene, PR/CI, review feedback, release readiness, and retro proposals feeding `AGENTS.md`. No daemon, auto-merge, or unattended publish/deploy.
  - Git branch, commit, or push orchestration.
- **Correction scope non-goals (WF):** Stateless validator engines bounded to current files; no new routes, modules, schemas, or templates beyond the then-existing 13 (the later LC correction below adds only the conditional ERD kind); no runtime daemon, crash recovery, or enforcement daemon; read-only roles do not write. Subagent triage does not transfer parent acceptance and external deployment is not automatic. Source provenance for REQ-WF-01..07: user conversation explicitly authorizing the WT docs stage, mockup, and ranking corrections, plus user-supplied articles [Cara Bikin Requirement Lebih Jelas (EARS patterns)](https://ramadigital.id/blog/acceptance-criteria-ears-pattern-cara-bikin-requirement-lebih-jelas) and [Agentic Tapi Deterministic: Workflow AI Agent](https://ramadigital.id/blog/agentic-tapi-deterministic-workflow-ai-agent); canonical DAW authorities are `references/workflow-artifacts.md`, `references/document-quality.md#acceptance-criteria-ears`, and `references/operations.md#ranked-result-triage`; inherited project guidance citations in `references/document-quality.md` (§2) remain existing guidance and are not claimed as user-supplied WF sources; no external provenance is claimed for runtime behavior.
- **Lifecycle correction (LC):** Requirements REQ-LC-01..05 and their acceptance criteria are authoritative in [ERD and Application Lifecycle Correction](erd-lifecycle-workflow.md): substantive Blueprint (LC-01), conditional separate ERD with erd-01..03 and no invented schema or migration authorization (LC-02), 14-kind registry/gate integration (LC-03), post-release feedback/incident closure through existing routes where local proof never means production resolved (LC-04), and consistent propagation (LC-05). No new route, module, monitoring, or publish automation.
