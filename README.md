# Deterministic Agentic Workflow

A portable, document-driven planning and verification framework for AI coding agents.

> **"Otaknya boleh generative, tangannya harus deterministic."**
> _(Generative reasoning for cognitive planning; deterministic execution and verification for system state)._

Based on the architectural principles articulated in Rama Digital's [_Agentic Tapi Deterministic Workflow AI Agent_](https://ramadigital.id/blog/agentic-tapi-deterministic-workflow-ai-agent), this package provides a structured instructional contract covering a 13-document specification matrix, specialist role routing, fail-closed approval triggers, and verifiable acceptance gates.

---

## 1. Quickstart

### Inspecting the Core Instructions

The primary workflow specification is defined in [`SKILL.md`](SKILL.md). In environments with file-based context loading, provide `SKILL.md` to your agent alongside relevant references:

- [`references/routing.md`](references/routing.md): 13-doc matrix, triggers, conditional skills, inputs/outputs, handoffs.
- [`references/operations.md`](references/operations.md): Multi-step execution rules, fail-closed boundaries, baseline verification.
- [`references/validation.md`](references/validation.md): Task contract specification and validator API.
- [`references/installation.md`](references/installation.md): Installation and discovery across various environments.
- [`templates/`](templates/): Canonical templates for all 13 specification documents.

---

## 2. Validator CLI

The package includes a read-only, standard library Python utility (`scripts/validate.py`) for checking package structure and project task contracts. It runs strictly within Python and does not spawn external shell commands or Git subprocesses.

### Operational Scope & Truthful Limits

- **Structural Verification Only:** Checks syntax, schemas, relative paths, hashes, and stage gating. It does NOT execute tests, inspect runtime state, authenticate user approvals, verify live Git revisions, or infer risk levels.
- **Standalone Root Instructions:** The core instructions and 13-document planning matrix in `SKILL.md` and `references/` operate standalone in any environment that loads Markdown files into agent context, even where Python or shell execution is unavailable.
- **Environment Compatibility:** Tested under the local Linux environment (Python 3.14). Syntax uses Python 3.10+ standard library features, but compatibility has not been matrix-tested across prior versions or multiple operating systems. Automated skill loading in other agent clients is unverified and client-dependent.

### Validate Skill Package Integrity

From within the cloned skill directory:

```bash
# Validate package integrity (text output)
python3 scripts/validate.py package

# Validate package with machine-readable JSON envelope
python3 scripts/validate.py package --format json
```

From any other location, provide the resolved path to `scripts/validate.py`:

```bash
python3 "/path/to/skill/scripts/validate.py" package
```

### Validate a Project Task Contract

Contract validation requires `--project-root` and a contract file (specified either as a project-relative path or an absolute path):

```bash
# Validate contract at planning stage
python3 "/path/to/skill/scripts/validate.py" contract task-contract.json --project-root "/path/to/project" --stage plan

# Validate contract at execution stage
python3 "/path/to/skill/scripts/validate.py" contract task-contract.json --project-root "/path/to/project" --stage execute

# Validate contract at completion stage (requires evidence for all criteria)
python3 "/path/to/skill/scripts/validate.py" contract task-contract.json --project-root "/path/to/project" --stage complete
```

### Exit Codes

- `0`: Valid (all structural checks passed; non-blocking warnings may exist).
- `1`: Validation error (schema violation, boundary escape, hash mismatch, or stage gating violation).
- `2`: Input or invocation error (malformed JSON, duplicate keys, unreadable file, or invalid CLI arguments).

---

## 3. Running Regression Tests

The test suite relies entirely on Python's standard `unittest` library without external dependencies:

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

---

## 4. Repository & Distribution

- **Repository:** Private GitHub repository at [https://github.com/gio0z/deterministic-agentic-workflow](https://github.com/gio0z/deterministic-agentic-workflow).
- **Cloning:** Clone via normal Git authentication (SSH or HTTPS with existing GitHub credentials; never embed access tokens in repo files or instructions):
  ```bash
  git clone git@github.com:gio0z/deterministic-agentic-workflow.git
  # or
  git clone https://github.com/gio0z/deterministic-agentic-workflow.git
  ```
- **Dependencies:** Zero external dependencies. Python 3.10+ standard library.
- **Read-Only Tooling:** The included validator never modifies files, never spawns subprocesses, and never connects to the network.
