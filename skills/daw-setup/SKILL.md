---
name: daw-setup
description: "Repository configuration and environment initialization for deterministic workflows: discovers project commands, spec conventions, and risk boundaries, confirming with the operator before writing an agent configuration block."
compatibility: "Fully self-contained procedural skill; no external dependencies required."
---

# DAW Setup (`daw-setup`)

The setup module initializes or updates Deterministic Agentic Workflow (DAW) configuration for a repository. Run once per repo (and re-runnable to update), `daw-setup` operates on a strict sequence: Explore (read-only) -> present findings -> confirm with user -> write configuration block.

**Invariant:** `daw-setup` mutates ONLY the designated DAW configuration block in a single context file (`AGENTS.md` or `CLAUDE.md`). It never touches application source code, executes untrusted build scripts, or invents configuration values.

---

## 1. Trigger & Scope

### When to Invoke

- First-time repository onboarding to the Deterministic Agentic Workflow suite.
- Reconfiguring project conventions (spec directory, test/lint/build commands, risk gates, default branch).
- Re-running to synchronize changed repository commands or workflows.

### Non-Goals & Invariants

- **Single Fenced Block Mutation:** Only modifies or inserts the `<!-- daw-config:start -->` block in the target agent file.
- **Diff Before Write:** Always present the exact proposed block diff and await explicit operator confirmation before writing.
- **No Command Invention:** Unknown or non-existent test/lint/build commands must be set to `none`, never guessed.
- **Blank Workspace Handling:** If the workspace is empty/blank, `daw-setup` recommends running `daw-wizard` first, recording `none` for unknown build/test commands.
- **Issue Tracker Recording Only:** Records issue tracker preference (`github` | `gitlab` | `local-markdown` | `none`); DAW never automatically writes remote tracker issues.

---

## 2. Inputs & Governance Loader Sequence

### Canonical Path Resolution & Governance Loading

1. **Physical Root Resolution:**
   - Resolve this `SKILL.md` to its canonical physical directory. The suite root is canonical `../..`.
   - Resolve all relative links (`../../references/...`, `../../SKILL.md`) relative to the physical module directory.
2. **Mandatory Governance Loading:**
   - Before executing phase work, load root governance (`../../SKILL.md` §4 Safety & §6 Handoff Contract Schema) and canonical routing (`../../references/routing.md` §5 & §6).
   - Before any file mutation, load `../../references/operations.md` §1 Preflight Safety & §2 High-Risk Approvals.
   - Unknown risk, ambiguous scope, or missing confirmation must immediately transition to `blocked` before writing to disk.

---

## 3. Operational Steps

### Step 1: Explore (Read-Only Discovery)

Inspect observable repository facts without executing mutating commands:

- Git remote: `git remote -v` and default branch (`main` / `master`).
- Existing agent context files: Check root `AGENTS.md`, `CLAUDE.md`, or `GEMINI.md` and inspect if a `## DAW Configuration` block already exists.
- Specification directory conventions: Inspect `docs/specs/`, `docs/`, `docs/adr/`. Default is `docs/specs/`.
- Project build/test/lint configurations:
  - Node/JS: `package.json` scripts (`test`, `lint`, `build`).
  - Python: `pyproject.toml`, `setup.cfg`, `pytest.ini`, `Makefile`.
  - Rust: `Cargo.toml`.
  - Go: `go.mod`.
  - CI workflows: `.github/workflows/`, `.gitlab-ci.yml`.
- Monorepo signals: Multi-package directories, workspaces configuration (`pnpm-workspace.yaml`, lerna).

### Step 2: Formulate Findings & Batched Confirmation

Present discovered facts to the operator in one single batched round, pre-filling defaults:

1. **spec_dir:** Default `docs/specs/` (or discovered existing path).
2. **test_command:** Discovered test command or `none`.
3. **lint_command:** Discovered linter command or `none`.
4. **build_command:** Discovered build command or `none`.
5. **workspace:** `in-place` | `isolated` (default `in-place`).
6. **high_risk_paths:** Identified sensitive paths (e.g. `migrations/`, `deploy/`, `infra/`, `.github/workflows/`) or `none`.
7. **issue_tracker:** `github` | `gitlab` | `local-markdown` | `none`.
8. **default_branch:** Detected default branch (`main` or `master`).

Show the proposed block diff and obtain explicit confirmation.

### Step 3: Write Configuration Block

Apply the target file rule:

- If `AGENTS.md` exists: edit `AGENTS.md`.
- Else if `CLAUDE.md` exists: edit `CLAUDE.md`.
- Else: create `AGENTS.md`. Never create both.
- Replace an existing block in place between markers; never duplicate.

Exact block format:

```markdown
<!-- daw-config:start -->

## DAW Configuration

- schema: 1
- spec_dir: docs/specs
- test_command: python3 -m unittest discover -s tests
- lint_command: none
- build_command: none
- workspace: in-place
- high_risk_paths: migrations/, deploy/
- issue_tracker: github
- default_branch: main

<!-- daw-config:end -->
```

---

## 4. Output Contract

Every completion of `daw-setup` delivers a structured handoff payload adhering to the canonical suite envelope. `setup` is a single-stage terminal route: on `status: "pass"` it returns `handoff_to: null`.

```json
{
  "objective": "Initialize repository DAW configuration in AGENTS.md.",
  "input_paths": ["package.json", "AGENTS.md"],
  "output_paths": ["AGENTS.md"],
  "acceptance_criteria": [
    {
      "criterion": "Discovered repository test/lint/build commands and spec directory conventions",
      "status": "pass"
    },
    {
      "criterion": "Operator explicitly approved DAW configuration settings",
      "status": "pass"
    },
    {
      "criterion": "Wrote single fenced DAW configuration block in AGENTS.md between markers",
      "status": "pass"
    }
  ],
  "evidence": [
    {
      "reference": "AGENTS.md",
      "summary": "Fenced daw-config block written with verified test runner and spec directory"
    }
  ],
  "status": "pass",
  "handoff_to": null,
  "details": {
    "target_file": "AGENTS.md",
    "configuration": {
      "schema": 1,
      "spec_dir": "docs/specs",
      "test_command": "npm test",
      "lint_command": "npm run lint",
      "build_command": "none",
      "workspace": "in-place",
      "high_risk_paths": ["migrations/", "deploy/"],
      "issue_tracker": "github",
      "default_branch": "main"
    }
  }
}
```
