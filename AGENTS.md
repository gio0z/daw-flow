# AGENTS.md — Deterministic Agentic Workflow Repository Contract

## CONTEXT-MAP

- **Repository Root:** The directory containing this file; all links below are repository-relative.
- **Core Specification:** [`SKILL.md`](SKILL.md) (Portable Agent Skills specification format)
- **Validator CLI & Engine:** [`scripts/validate.py`](scripts/validate.py)
  - Runtime: Python 3.10+ standard library only (`argparse`, `hashlib`, `json`, `os`, `pathlib`, `re`, `sys`, `urllib.parse`).
  - Dependencies: Zero third-party runtime dependencies; strictly read-only filesystem access; no network, no Git CLI execution, no subshell spawning.
  - Subcommands: `package` (package integrity & link resolution) and `contract` (JSON task contract lifecycle validation).
- **Test Suite:** [`tests/test_validate.py`](tests/test_validate.py)
  - Framework: Standard library `unittest` (56 unit tests verifying package checks, contract schemas, boundary traversal prevention, duplicate-key rejection, and stage transitions).
  - Test Execution: `python3 -m unittest discover -s tests -p "test_*.py"` or isolated test runners (`pytest`).
- **Operational & Schema References:**
  - [`references/validation.md`](references/validation.md): Authoritative validator CLI reference, exit codes, and JSON task-contract schema.
  - [`references/routing.md`](references/routing.md): 13-document specification matrix, trigger conditions, specialist routing, and handoff protocols.
  - [`references/operations.md`](references/operations.md): Operational execution invariants, fail-closed boundaries, baseline hashing, and rollback evidence.
  - [`references/installation.md`](references/installation.md): Environment discovery paths, packaging layout, and skill registration.
  - [`references/task-contract.example.json`](references/task-contract.example.json): Canonical JSON task-contract example envelope.
- **Specification Document Templates (13 Documents):**
  - [`templates/brd.md`](templates/brd.md), [`templates/prd.md`](templates/prd.md), [`templates/frd.md`](templates/frd.md), [`templates/techstack.md`](templates/techstack.md), [`templates/design.md`](templates/design.md), [`templates/wireframe.md`](templates/wireframe.md), [`templates/ui-ux.md`](templates/ui-ux.md), [`templates/blueprint.md`](templates/blueprint.md), [`templates/security.md`](templates/security.md), [`templates/qa.md`](templates/qa.md), [`templates/deployment.md`](templates/deployment.md), [`templates/runbook.md`](templates/runbook.md), [`templates/roadmap.md`](templates/roadmap.md).
- **Standalone Repository Specifications:**
  - [`docs/BRD.md`](docs/BRD.md): Business Requirements Document.
  - [`docs/PRD.md`](docs/PRD.md): Product Requirements Document.
  - [`docs/TRD.md`](docs/TRD.md): Technical Requirements Document (architecture & engine).
  - [`docs/UIRD.md`](docs/UIRD.md): User Interface Requirements Document (CLI terminal & JSON streams).
  - [`docs/DESIGN.md`](docs/DESIGN.md): CLI architecture, data flow, and diagnostic design.

## Operational Directives for Agents

1. **Standard Library Exclusivity:** All modifications to `scripts/validate.py` must use Python standard library only. Never introduce third-party runtime package dependencies.
2. **Read-Only Inspection Engine:** The validator is strictly read-only. It inspects file trees, reads file bytes for SHA-256 computation, and parses JSON/Markdown. It never writes files, mutates filesystem nodes, or executes subprocesses.
3. **Approval Presence vs Runtime Authorization:** Validation verifies structural presence and field equality (`action`, `target`, `revision`, `scope`) of an opaque approval reference. It never authenticates cryptographic signatures or grants runtime execution tokens.
4. **Evidence Presence vs Semantic Truth:** Validation confirms evidence reference files exist within `--project-root` and correlate with declared criteria. It never evaluates semantic truth or executes reference files.
5. **No Runtime Hook Modification:** Never alter global git hooks, quality gate scripts, or environment security policies to bypass gates.

## BLOCKERS

- None currently known. The repository quality gate passed using an isolated pytest runner; rerun the gate before each push rather than treating this record as authorization or a reusable pass.
