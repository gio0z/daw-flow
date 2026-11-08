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
- **No Command Invention:** A newly discovered command with no authoritative configured value is recorded only when the repository supplies it; otherwise the field is `none`, never guessed. An existing configured value is authoritative and preserved verbatim by default, including when its executable is locally missing, and the resulting `config_command_unresolved` error is reported rather than erased. The sole exception is an explicit operator-authorized semantic replacement or removal shown as a delta in the confirmed diff.
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
   - Discover worker spawning, continuation after completion, parallel result delivery, independent review, interactive approval, and lifecycle limits from exposed harness tools/documentation. Running-only messaging is not persistence; do not change global settings to obtain it. Follow the [persistent worker graph contract](../../references/operations.md#persistent-worker-graphs-harness-native).
   - Setup can record capability hints, but is not a prerequisite for automatic worker selection: ordinary workflow intake performs lightweight discovery when needed, reusing observations only while applicable. No persistence keyword or additional confirmation is required.

---

## 3. Operational Steps

### Step 1: Explore (Read-Only Discovery)

Inspect observable repository facts without executing mutating commands:

- Git remote: `git remote -v` and default branch (`main` / `master`).
- Existing agent context files: Check root `AGENTS.md`, `CLAUDE.md`, or `GEMINI.md` and inspect if a `## DAW Configuration` block already exists.
- Specification directory conventions: Inspect `docs/specs/`, `docs/`, `docs/adr/`. Default is `docs/specs/`.
- Delivery conventions (for the `ship` route; see [Commit Hygiene](../../references/developer-lifecycle.md#7-commit-hygiene), [Pull Request & CI Protocol](../../references/developer-lifecycle.md#8-pull-request--ci-protocol), and [Release Readiness](../../references/developer-lifecycle.md#10-release-readiness)):
  - **Commit convention:** `CONTRIBUTING.md`, commitlint config (`.commitlintrc*`, `commitlint.config.*`), or observed `git log --oneline -20` prefixes (Conventional Commits, emoji/short-tag style). Record the observed format or `none`.
  - **PR template:** `.github/pull_request_template.md`, `docs/pull_request_template.md`, or a CONTRIBUTING check; record the path or `none`.
  - **CI config:** `.github/workflows/`, `.gitlab-ci.yml`, or equivalent; record the observed required-check names (for PR readiness) or `none`.
  - **Release process:** `CHANGELOG.md` presence, `release-please`/`semantic-release` config, tag format (`git tag --list | tail`), or version file (`VERSION`, `package.json` version, `Cargo.toml` version); record the observed process or `none`.
  - **Branch naming:** Observed active branches (`git branch -a`) and any branch-protection rule detectable from remotes/docs; record the pattern (e.g. `feature/*`, `daw/<task-id>-*`, `spike/<topic>`) or `none`.
- Project build/test/lint configurations:
  - Node/JS: `package.json` scripts (`test`, `lint`, `build`).
  - Python: `pyproject.toml`, `setup.cfg`, `pytest.ini`, `Makefile`.
  - Rust: `Cargo.toml`.
  - Go: `go.mod`.
  - CI workflows: `.github/workflows/`, `.gitlab-ci.yml`.
- Monorepo signals: Multi-package directories, workspaces configuration (`pnpm-workspace.yaml`, lerna).

### Step 2: Formulate Findings & Batched Confirmation

Present discovered facts as pre-filled defaults, not questions the repository already answers. Preserve ALL existing configured values verbatim by default; defaults apply only to absent fields. The sole exception is a semantic replacement or removal explicitly authorized in the confirmed diff. Ask only unresolved material config preferences using the [canonical native clarification transport](../../references/grilling.md#native-interactive-clarification-transport-canonical-rule): exposed tools only, frontier decisions in rounds of at most 5, cancellation remains unresolved, and clarification never grants mutation or point-of-risk approval. Batch compatible preferences without forcing dependent questions into the same round; the proposed diff still requires explicit confirmation before writing.

1. **schema:** `1`.
2. **daw_version:** Installed suite `VERSION` (semver X.Y.Z) — "last version this project passed re-check against", never just "last version touched"; updated only by the Upgrade Re-check below.
3. **test_command:** Existing configured value verbatim, or discovered test command, or `none` only when the field is absent.
4. **lint_command:** Existing configured value verbatim, or discovered linter command, or `none` only when the field is absent.
5. **build_command:** Existing configured value verbatim, or discovered build command, or `none` only when the field is absent.
6. **workspace:** `in-place` | `isolated` (default `in-place`).
7. **high_risk_paths:** Identified sensitive paths (e.g. `migrations/`, `deploy/`, `infra/`, `.github/workflows/`) or `none`.
8. **issue_tracker:** `github` | `gitlab` | `local-markdown` | `none`.
9. **default_branch:** Detected default branch (`main` or `master`).
10. **Delivery conventions (ship route):** `commit_convention`, `pr_template`, `ci_checks`, `release_process`, `branch_pattern` — discovered values or `none` (never guessed). Required for `ship` route readiness; `none` means the ship stage works from observed repo behavior with an explicit note.

Show the proposed block diff, including every semantic delta (each added, removed, or changed field with its old and new values), and obtain explicit confirmation. Format-only normalization (whitespace, quoting, or list rendering that preserves every stored value) is lossless and needs no separate semantic authorization; any change to a stored value is a semantic delta shown in the confirmed diff.

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
- daw_version: 0.3.0
- test_command: python3 -m unittest discover -s tests
- lint_command: none
- build_command: none
- workspace: in-place
- high_risk_paths: migrations/, deploy/
- issue_tracker: github
- default_branch: main
- commit_convention: conventional
- pr_template: .github/pull_request_template.md
- ci_checks: ci/test
- release_process: changelog+tags
- branch_pattern: feature/*

<!-- daw-config:end -->
```

After writing, `daw-setup` MUST run `python3 scripts/validate.py config AGENTS.md --project-root .` (or the edited `CLAUDE.md` path when applicable) and report findings verbatim. Preserve every existing configured `test_command`/`lint_command`/`build_command` verbatim by default, including one whose executable is locally missing, and keep any resulting `config_command_unresolved` error in the report — never silently replace the command with `none` or another tool just to pass. A semantic replacement or removal is permitted only when explicitly authorized in the confirmed diff (see Step 2). Only an absent field defaults to `none`. A `valid` config verdict certifies structural/resolvability checks only, not application or toolchain readiness. See [Validator Reference](../../references/validation.md).

### Step 4: Record Retrospective Lessons

After a shipped or completed workflow, record durable lessons (recurring verifier findings, convention gaps, recurring CI failures) into this same DAW config block or a `docs/retro/` note and reference it from the block, per [Retrospective & Convention Feedback](../../references/developer-lifecycle.md#11-retrospective--convention-feedback). Update in place; never duplicate the block.

### Step 5: Upgrade Re-check (Read-Only Diagnosis)

Trigger: `config_daw_version_stale` from `validate.py config`, or the user reports the DAW suite was updated. This section is strictly read-only diagnosis; it mutates no project files.

1. Read the CHANGELOG entries between the recorded `daw_version` and the installed `VERSION`; collect every `### Project migration` item (artifact, finding code or `manual`, fix route).
2. Run read-only validators:
   - `python3 scripts/validate.py config AGENTS.md --project-root .` (or the edited `CLAUDE.md`);
   - `python3 scripts/validate.py ledger <spec_dir>/ledger.json --project-root .` when the ledger exists — the absence of a ledger when `<spec_dir>` holds formal specs is itself a finding (report it, do not create the ledger here);
   - `python3 scripts/validate.py docs` on each ledger `record` with its state's transition.
3. List manual checks named in `### Project migration` that have no validator (e.g. ERD coverage, evidence persistence path) as manual findings.
4. Report findings grouped by artifact, each with its fix route: spec drift/schema → `daw-design` rework; unfinished code work → `daw-plan`; config → `daw-setup` write. Do not apply fixes during diagnosis.
5. Only after all errors are resolved and the user confirms, bump `daw_version` to the installed `VERSION`, then rerun `validate.py config` and report findings verbatim.

`daw_version` means "last version this project passed re-check against", never just "last version touched".

---

## 4. Output Contract

Use the complete outer envelope and transport in [routing §5](../../references/routing.md#5-canonical-module-handoff-contract), delivering inspectable JSON before concluding the stage. Direct-user reports remain concise natural language unless an explicit format request or the canonical inline fallback applies. `setup` is a single-stage terminal route: a proposed `status: "pass"` returns `handoff_to: null` and covers only discovered configuration, explicit operator approval, and the authorized single-block write, not parent acceptance or application readiness. Missing confirmation blocks the write; `fail` and `blocked` retain routing §5 semantics.

Required `details`: `target_file` and `configuration`, retaining all configuration fields below. This illustrative payload accompanies actual input/output paths, approval evidence, and observed write evidence in the outer envelope:

```json
{
  "target_file": "AGENTS.md",
  "configuration": {
    "schema": 1,
    "daw_version": "0.3.0",
    "spec_dir": "docs/specs",
    "test_command": "npm test",
    "lint_command": "npm run lint",
    "build_command": "none",
    "workspace": "in-place",
    "high_risk_paths": ["migrations/", "deploy/"],
    "issue_tracker": "github",
    "default_branch": "main",
    "commit_convention": "conventional",
    "pr_template": ".github/pull_request_template.md",
    "ci_checks": ["ci/test"],
    "release_process": "changelog+tags",
    "branch_pattern": "feature/*"
  }
}
```
