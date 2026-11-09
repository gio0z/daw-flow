# AGENTS.md — Deterministic Agentic Workflow Repository Contract

## CONTEXT-MAP

- **Repository Root:** The directory containing this file; all links below are repository-relative.
- **Core Router Specification:** [`SKILL.md`](SKILL.md) (Deterministic Agentic Workflow Suite Router specification)
- **Suite Module Skills (`skills/daw-*`):**
  - [`skills/daw-design/SKILL.md`](skills/daw-design/SKILL.md): System architecture, technical requirements & specification design.
  - [`skills/daw-plan/SKILL.md`](skills/daw-plan/SKILL.md): Structured task planning, phase breakdowns & risk assessment.
  - [`skills/daw-debug/SKILL.md`](skills/daw-debug/SKILL.md): Root cause analysis, reproduction & failure diagnostics.
  - [`skills/daw-build/SKILL.md`](skills/daw-build/SKILL.md): Implementation, code editing & minimal change construction.
  - [`skills/daw-review/SKILL.md`](skills/daw-review/SKILL.md): Two-stage code review, boundary compliance & security audit.
  - [`skills/daw-verify/SKILL.md`](skills/daw-verify/SKILL.md): Verification, testing, behavioral validation & evidence checks.
  - [`skills/daw-workspace/SKILL.md`](skills/daw-workspace/SKILL.md): Isolated workspace/worktree setup & lifecycle management.
  - [`skills/daw-ask/SKILL.md`](skills/daw-ask/SKILL.md): Read-only architectural guidance & consultation (original advisor; no persona impersonation).
  - [`skills/daw-setup/SKILL.md`](skills/daw-setup/SKILL.md): Interactive configuration setup, tool command discovery & project conventions.
  - [`skills/daw-wizard/SKILL.md`](skills/daw-wizard/SKILL.md): Interactive greenfield requirements interview & initial specification document authoring.
  - [`skills/daw-untangle/SKILL.md`](skills/daw-untangle/SKILL.md): Read-only system coupling analysis, hidden dependency mapping & bounded boundary unentanglement.
  - [`skills/daw-ship/SKILL.md`](skills/daw-ship/SKILL.md): Integration & delivery: commit hygiene, pull requests, CI triage, review feedback, merge & release readiness.
- **Route Engine & Policy:**
  - [`scripts/route.py`](scripts/route.py): Read-only, zero-dependency suite routing engine and `--check-suite` structural validator.
  - [`references/suite-manifest.json`](references/suite-manifest.json): Declarative routing policy table and module mapping schema.
- **Validator CLI & Engine:** [`scripts/validate.py`](scripts/validate.py) (CLI dispatch only: argparse, dispatch, exit codes)
  - Runtime: Python 3.10+ standard library only (`argparse`, `hashlib`, `json`, `os`, `pathlib`, `re`, `sys`, `urllib.parse`).
  - Dependencies: Zero third-party runtime dependencies; strictly read-only filesystem access; no network, no Git CLI execution, no subshell spawning.
  - Subcommands: `package` (package integrity & link resolution), `contract` (JSON task contract lifecycle validation, including the UI `surface_session` completion gate), `docs`, `ledger`, `config`, `status` (read-only aggregate preflight; see `references/validation.md` §10), `flow` (§11), and `verify` (§13).
  - Flat module layout in `scripts/` (no subpackages):
    - `scripts/daw_common.py`: shared helpers (strict JSON, frontmatter, bounded paths, SHA-256, finding helpers, `output_result`).
    - `scripts/check_package.py`: package integrity and link resolution (`validate_package`).
    - `scripts/check_contract.py`: task-contract lifecycle validation.
    - `scripts/check_docs.py`: documentation workflow transition validation (`docs`).
    - `scripts/check_ledger.py`: spec-ledger validation (`ledger`).
    - `scripts/check_config.py`: DAW configuration block validation (`config`), including `daw_version`.
    - `scripts/check_status.py`: aggregate `status` preflight composition (owns no rules of its own).
    - `scripts/check_flow.py`: adopted best-practice flow mapping (`flow`).
    - `scripts/check_surface.py`: role-based UI surface-session validation (`verify`), also consumed by `contract` at `complete`.
- **Ledger Derivation Tool (the only writer):** [`scripts/derive_ledger.py`](scripts/derive_ledger.py) projects `<spec_dir>/ledger.json` from existing doc-transition records. It is deliberately **not** part of the read-only validator: it needs `--write` to emit the ledger, refuses to run when any error finding exists, and never invents a `sha256` — it copies only hashes declared by records whose document bytes still match. Markdown specifications stay the single hand-authored source; the ledger is a verified projection of the review records, never a re-pin of edited bytes.
- **Behavioral Evaluations & Benchmarks (Developer Tooling):** [`tools/evaluation/evaluate.py`](tools/evaluation/evaluate.py), [`tools/evaluation/wizard_bench.py`](tools/evaluation/wizard_bench.py), and evaluation guides in [`docs/evaluation/`](docs/evaluation/) run explicitly configured agent commands in disposable fixtures and retain evidence. Plumbing tests do not establish model quality.
- **Test Suites & Fixtures:**
  - [`tests/test_validate.py`](tests/test_validate.py): Standard library `unittest` verifying package checks, contract schemas, boundary traversal prevention, duplicate-key rejection, and stage transitions.
  - [`tests/test_route.py`](tests/test_route.py): Standard library `unittest` verifying route calculations, schema constraints, path containment, high-risk flags, error envelopes, and `--check-suite`.
  - [`tests/test_surface.py`](tests/test_surface.py): Standard library `unittest` verifying surface-session shape rules and the contract completion gate that consumes them.
  - [`tests/fixtures/wizard-bench`](tests/fixtures/wizard-bench): Evaluation benchmark scenario fixtures (bookmark manager, expense tracker, log analyzer).
  - Test Execution: `python3 -m unittest discover -s tests -p "test_*.py"` or isolated test runners (`pytest`).
- **Operational & Schema References:**
  - [`references/suite-manifest.json`](references/suite-manifest.json): Authoritative suite manifest, module locations, route definitions, and schema definitions.
  - [`references/validation.md`](references/validation.md): Authoritative validator CLI reference, exit codes, and JSON task-contract schema.
  - [`references/routing.md`](references/routing.md): 14-document specification matrix (baseline six + conditional ERD), trigger conditions, specialist routing, and handoff protocols.
  - [`references/operations.md`](references/operations.md): Operational execution invariants, fail-closed boundaries, baseline hashing, rollback evidence, and the harness-native persistent worker graph contract.
  - [`references/installation.md`](references/installation.md): Environment discovery paths, packaging layout, sibling symlink distribution, and skill registration.
  - [`references/task-contract.example.json`](references/task-contract.example.json): Canonical JSON task-contract example envelope.
  - [`references/change-coupling.md`](references/change-coupling.md): Change-coupling taxonomy, dependency tracing heuristics, and boundary unentanglement reference.
  - [`references/developer-lifecycle.md`](references/developer-lifecycle.md): Professional delivery lifecycle protocols (inner loop, time-boxing, spike, refactor, maintenance, bisection, commit hygiene, PR/CI, review feedback, release, retro).
- - [`templates/brd.md`](templates/brd.md), [`templates/prd.md`](templates/prd.md), [`templates/frd.md`](templates/frd.md), [`templates/techstack.md`](templates/techstack.md), [`templates/design.md`](templates/design.md), [`templates/wireframe.md`](templates/wireframe.md), [`templates/ui-ux.md`](templates/ui-ux.md), [`templates/blueprint.md`](templates/blueprint.md), [`templates/security.md`](templates/security.md), [`templates/qa.md`](templates/qa.md), [`templates/deployment.md`](templates/deployment.md), [`templates/runbook.md`](templates/runbook.md), [`templates/roadmap.md`](templates/roadmap.md), [`templates/erd.md`](templates/erd.md) (conditional).
- **Standalone Repository Specifications:**
  - [`CHANGELOG.md`](CHANGELOG.md): Chronological suite change history and architecture decisions log.
  - [`docs/BRD.md`](docs/BRD.md): Business Requirements Document.
  - [`docs/PRD.md`](docs/PRD.md): Product Requirements Document.
  - [`docs/TRD.md`](docs/TRD.md): Technical Requirements Document (architecture & engine).
  - [`docs/UIRD.md`](docs/UIRD.md): User Interface Requirements Document (CLI terminal & JSON streams).
  - [`docs/DESIGN.md`](docs/DESIGN.md): CLI architecture, data flow, and diagnostic design.
  - [`docs/evaluation/guide.md`](docs/evaluation/guide.md): Evaluation harness usage, benchmark protocols, and research basis.
  - [`docs/evaluation/observations.md`](docs/evaluation/observations.md): Empirical baseline findings and benchmark observation records.

## Operational Directives for Agents

1. **Standard Library Exclusivity:** All modifications to `scripts/validate.py` and `scripts/route.py` must use Python standard library only. Never introduce third-party runtime package dependencies.
2. **Read-Only Inspection Engine:** The validator and route engine are strictly read-only. They inspect file trees, read file bytes for SHA-256 computation, and parse JSON/Markdown. They never write files, mutates filesystem nodes, or executes subprocesses. The single exception in the suite is `scripts/derive_ledger.py`, a separate generator that writes only `<spec_dir>/ledger.json` and only under an explicit `--write`; it is never invoked by `validate.py` or `route.py`.
3. **Suite Routing & Dispatch:** Routing is governed declaratively by `references/suite-manifest.json` via `scripts/route.py REQUEST`. Router skills dispatch to specialized modules (`skills/daw-*`) rather than running flat monolithic procedures.
4. **Deep Module Boundaries:** Modules do not call root router or each other recursively; each finishes with a clean handoff back to the orchestrator.
5. **Distribution & Symlinks:** In installed environments, sibling directories symlink into the bundled `skills/daw-*` directories. Standalone compatibility claims are rejected; clients must keep the suite together.
6. **Approval Presence vs Runtime Authorization:** Validation verifies structural presence and field equality (`action`, `target`, `revision`, `scope`) of an opaque approval reference. It never authenticates cryptographic signatures or grants runtime execution tokens. High-risk operations flag constraints (`interactive_approval_required: true`, `authorization_granted: false`); routing never executes approvals.
7. **Evidence Presence vs Semantic Truth:** Validation confirms evidence reference files exist within `--project-root` and correlate with declared criteria. It never evaluates semantic truth or executes reference files.
8. **No Runtime Hook Modification:** Never alter global git hooks, configuration daemons, or environment security policies to bypass gates.

## BLOCKERS

- None currently known. The repository quality gate passed using an isolated pytest runner; rerun the gate before each push rather than treating this record as authorization or a reusable pass.
