# Suite Change History & Architecture Log

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
