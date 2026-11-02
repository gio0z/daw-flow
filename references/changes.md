# Suite Change History & Architecture Log

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
