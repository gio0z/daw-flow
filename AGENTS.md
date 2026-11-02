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
- **Route Engine & Policy:**
  - [`scripts/route.py`](scripts/route.py): Read-only, zero-dependency suite routing engine and `--check-suite` structural validator.
  - [`references/suite-manifest.json`](references/suite-manifest.json): Declarative routing policy table and module mapping schema.
- **Validator CLI & Engine:** [`scripts/validate.py`](scripts/validate.py)
  - Runtime: Python 3.10+ standard library only (`argparse`, `hashlib`, `json`, `os`, `pathlib`, `re`, `sys`, `urllib.parse`).
  - Dependencies: Zero third-party runtime dependencies; strictly read-only filesystem access; no network, no Git CLI execution, no subshell spawning.
  - Subcommands: `package` (package integrity & link resolution) and `contract` (JSON task contract lifecycle validation).
- **Installer:** [`scripts/install.py`](scripts/install.py) is a separate, explicitly mutating stdlib CLI for complete-bundle installation, ownership-checked updates, status, and removal. Its mutation behavior never extends to the validator or route engine.
- **Behavioral Evaluations:** [`scripts/evaluate.py`](scripts/evaluate.py) and [`references/evaluation.md`](references/evaluation.md) run explicitly configured agent commands in disposable fixtures and retain evidence. Plumbing tests do not establish model quality.
- **Test Suites:**
  - [`tests/test_validate.py`](tests/test_validate.py): Standard library `unittest` verifying package checks, contract schemas, boundary traversal prevention, duplicate-key rejection, and stage transitions.
  - [`tests/test_route.py`](tests/test_route.py): Standard library `unittest` verifying route calculations, schema constraints, path containment, high-risk flags, error envelopes, and `--check-suite`.
  - Test Execution: `python3 -m unittest discover -s tests -p "test_*.py"` or isolated test runners (`pytest`).
- **Operational & Schema References:**
  - [`references/suite-manifest.json`](references/suite-manifest.json): Authoritative suite manifest, module locations, route definitions, and schema definitions.
  - [`references/validation.md`](references/validation.md): Authoritative validator CLI reference, exit codes, and JSON task-contract schema.
  - [`references/routing.md`](references/routing.md): 13-document specification matrix, trigger conditions, specialist routing, and handoff protocols.
  - [`references/operations.md`](references/operations.md): Operational execution invariants, fail-closed boundaries, baseline hashing, and rollback evidence.
  - [`references/installation.md`](references/installation.md): Environment discovery paths, packaging layout, sibling symlink distribution, and skill registration.
  - [`references/task-contract.example.json`](references/task-contract.example.json): Canonical JSON task-contract example envelope.
  - [`references/route-request.example.json`](references/route-request.example.json): Canonical JSON route request example envelope.
- - [`templates/brd.md`](templates/brd.md), [`templates/prd.md`](templates/prd.md), [`templates/frd.md`](templates/frd.md), [`templates/techstack.md`](templates/techstack.md), [`templates/design.md`](templates/design.md), [`templates/wireframe.md`](templates/wireframe.md), [`templates/ui-ux.md`](templates/ui-ux.md), [`templates/blueprint.md`](templates/blueprint.md), [`templates/security.md`](templates/security.md), [`templates/qa.md`](templates/qa.md), [`templates/deployment.md`](templates/deployment.md), [`templates/runbook.md`](templates/runbook.md), [`templates/roadmap.md`](templates/roadmap.md).
- **Standalone Repository Specifications:**
  - [`docs/BRD.md`](docs/BRD.md): Business Requirements Document.
  - [`docs/PRD.md`](docs/PRD.md): Product Requirements Document.
  - [`docs/TRD.md`](docs/TRD.md): Technical Requirements Document (architecture & engine).
  - [`docs/UIRD.md`](docs/UIRD.md): User Interface Requirements Document (CLI terminal & JSON streams).
  - [`docs/DESIGN.md`](docs/DESIGN.md): CLI architecture, data flow, and diagnostic design.

## Operational Directives for Agents

1. **Standard Library Exclusivity:** All modifications to `scripts/validate.py` and `scripts/route.py` must use Python standard library only. Never introduce third-party runtime package dependencies.
2. **Read-Only Inspection Engine:** The validator and route engine are strictly read-only. They inspect file trees, read file bytes for SHA-256 computation, and parse JSON/Markdown. They never write files, mutates filesystem nodes, or executes subprocesses.
3. **Suite Routing & Dispatch:** Routing is governed declaratively by `references/suite-manifest.json` via `scripts/route.py REQUEST`. Router skills dispatch to specialized modules (`skills/daw-*`) rather than running flat monolithic procedures.
4. **Deep Module Boundaries:** Modules do not call root router or each other recursively; each finishes with a clean handoff back to the orchestrator.
5. **Distribution & Symlinks:** In installed environments, sibling directories symlink into the bundled `skills/daw-*` directories. Standalone compatibility claims are rejected; clients must keep the suite together.
6. **Approval Presence vs Runtime Authorization:** Validation verifies structural presence and field equality (`action`, `target`, `revision`, `scope`) of an opaque approval reference. It never authenticates cryptographic signatures or grants runtime execution tokens. High-risk operations flag constraints (`interactive_approval_required: true`, `authorization_granted: false`); routing never executes approvals.
7. **Evidence Presence vs Semantic Truth:** Validation confirms evidence reference files exist within `--project-root` and correlate with declared criteria. It never evaluates semantic truth or executes reference files.
8. **No Runtime Hook Modification:** Never alter global git hooks, configuration daemons, or environment security policies to bypass gates.

## BLOCKERS

- None currently known. The repository quality gate passed using an isolated pytest runner; rerun the gate before each push rather than treating this record as authorization or a reusable pass.
