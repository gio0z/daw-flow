# Installation and Agent Compatibility

DAW is distributed as one complete root skill with twelve bundled modules. Install via the interactive setup wizard, the `install.sh` / `uvx` one-liners, native plugin manifests, or directly from a complete checkout/release using Python 3.10+. `scripts/install.py` itself uses only the standard library and performs no network access.

## Install

### Interactive Wizard & One-Liners

Run `scripts/install.py` (or `daw install`) with no action in a TTY, or pass `--interactive` (`-i`), to launch the guided setup wizard:

- Detects existing agent configuration directories (`~/.agents`, `~/.claude`, `~/.gemini`, `~/.cursor`, `~/.copilot`, `~/.config/opencode`, `~/.gemini/antigravity`, or project equivalents).
- Prompts for scope (`user` vs `project`) and target agent(s) (single number/name, comma-separated list, or `a`/`all`).
- When installing at `project` scope without an existing `<!-- daw-config:start -->` block, offers to initialize one in `AGENTS.md` (or `CLAUDE.md`).
- Prints the exact non-interactive `daw install install ...` command for reproducibility.

Zero-clone installation options:

```bash
# Shell bootstrapper (clones into a temporary directory when run outside a checkout)
curl -fsSL https://raw.githubusercontent.com/gio0z/daw-flow/main/install.sh | bash

# Zero-clone wheel execution via uvx (operational suite bundled via setup.py into share/deterministic-agentic-workflow)
uvx --from git+https://github.com/gio0z/daw-flow daw install
```

### Non-Interactive Checkout Install

```bash
git clone https://github.com/gio0z/daw-flow.git
cd daw-flow
python3 scripts/install.py install --agent codex --scope user
```

Replace `codex` with `claude`, `gemini`, `cursor`, `copilot`, `opencode`, `antigravity`, or `all`. A user installation serves your projects on that machine. A project installation targets one repository and can optionally write a validated `<!-- daw-config:start -->` block via `--init-config`:

```bash
python3 scripts/install.py install --agent claude --scope project --project-root /path/to/project --init-config
```

`--init-config` applies only to `install` with `--scope project`. It appends `<!-- daw-config:start --> ... <!-- daw-config:end -->` to `AGENTS.md` (or `CLAUDE.md` if present without `AGENTS.md`), ensures `spec_dir` exists (`docs/specs` or existing `docs`), and is idempotent if a block already exists.

To install across every preset client at the selected scope:

```bash
python3 scripts/install.py install --agent all --scope project --project-root /path/to/project
```

The default is `--agent codex --scope project`, with the current directory as project root. Specify `--project-root` when running from the DAW checkout to install into a different project. An explicit directory overrides both presets (and cannot be combined with `--agent all` or `--interactive`):

```bash
python3 scripts/install.py install --skills-dir /path/to/client/skills
```

The target directory contains a real copy of `deterministic-agentic-workflow/` and relative sibling directory symlinks such as:

```text
skills/
├── deterministic-agentic-workflow/
│   ├── SKILL.md
│   ├── LICENSE
│   ├── VERSION
│   ├── agents/openai.yaml
│   ├── scripts/
│   ├── references/
│   ├── templates/
│   └── skills/daw-build/SKILL.md
├── daw-build -> deterministic-agentic-workflow/skills/daw-build
└── ... eleven other module aliases
```

The copy survives removal of the original checkout. The installed operational bundle includes only runtime operational files (`SKILL.md`, `LICENSE`, `VERSION`, optional `agents/` metadata and `.claude-plugin/`, `.cursor-plugin/`, `.codex-plugin/` plugin manifests, operational `scripts/`, `references/`, `templates/`, and `skills/`). Repository developer resources (`docs/`, `tests/`, `tools/`, `CHANGELOG.md`, `README.md`, `pyproject.toml`, `setup.py`, `install.sh`, and evaluation harnesses) remain in the source repository and are not shipped in the installed bundle. All twelve modules remain required; optional external specialist skills are not required. Never install flat independent copies of `daw-*`: their root-relative governance and resource links require the complete bundle.

## Client locations

These presets follow official local discovery documentation:

| Agent       | Project preset               | User preset                    | Official reference                                                                                |
| ----------- | ---------------------------- | ------------------------------ | ------------------------------------------------------------------------------------------------- |
| Codex       | `.agents/skills`             | `~/.agents/skills`             | [Build skills](https://learn.chatgpt.com/docs/build-skills)                                       |
| Claude Code | `.claude/skills`             | `~/.claude/skills`             | [Skills](https://code.claude.com/docs/en/skills)                                                  |
| Gemini CLI  | `.gemini/skills`             | `~/.gemini/skills`             | [Agent skills](https://geminicli.com/docs/cli/skills/)                                            |
| Cursor      | `.cursor/skills`             | `~/.cursor/skills`             | [Skills](https://cursor.com/docs/skills)                                                          |
| Copilot CLI | `.github/skills`             | `~/.copilot/skills`            | [Add skills](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills) |
| OpenCode    | `.opencode/skills`           | `~/.config/opencode/skills`    | OpenCode project/user skills directory                                                            |
| Antigravity | `.gemini/antigravity/skills` | `~/.gemini/antigravity/skills` | Antigravity skills directory                                                                      |

Several clients also recognize shared `.agents/skills` directories, and Gemini CLI / Antigravity share the `.gemini/` parent namespace. Use `--skills-dir` for a shared location or a different supported client, and run `doctor` to detect duplicate installations in overlapping discovery paths at the same scope.

### Native plugin manifests

The repository includes native plugin manifests for direct client plugin discovery under the `deterministic-agentic-workflow` plugin name (matching `VERSION`):

- **Claude Code:** `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` (`/plugin marketplace add https://github.com/gio0z/daw-flow`, `/plugin install deterministic-agentic-workflow@deterministic-agentic-workflow`, or `--plugin-dir /path/to/daw-flow`).
- **Cursor:** `.cursor-plugin/plugin.json` (`/agent plugin marketplace add https://github.com/gio0z/daw-flow`).
- **Codex CLI:** `.codex-plugin/plugin.json` (`codex plugin marketplace add gio0z/daw-flow`, `codex plugin add deterministic-agentic-workflow@deterministic-agentic-workflow`).
- **Antigravity CLI:** `agy plugin install https://github.com/gio0z/daw-flow`.

When any of `.claude-plugin`, `.cursor-plugin`, or `.codex-plugin` is present, `scripts/validate.py package` validates its bounded paths, strict JSON syntax, plugin name, and `VERSION` alignment.

The Markdown skills use the [Agent Skills specification](https://agentskills.io/specification). Codex UI metadata is optional; it does not prevent other clients from reading `SKILL.md`. Host-native tools and approval semantics differ, so instructions defer to the host's actual capabilities and permissions. No vendor-specific tool whitelist is imposed.

These locations establish layout compatibility. Client discovery, automatic triggering, tool execution, and cloud synchronization require separate runtime checks. In particular, local folders may not synchronize into cloud agents, and Cursor/Copilot symlink handling is not assumed from directory documentation alone.

After installation, restart the agent or reload its skills, inspect its skill list, and invoke the root by name. Codex supports `$deterministic-agentic-workflow`; Claude Code supports `/deterministic-agentic-workflow`. Gemini provides `/skills list` and `/skills reload`. Natural-language invocation works only when the client has loaded the skill.

## Development link mode (`--link`)

For local DAW development, install a live directory symlink to your source checkout instead of copying files:

```bash
python3 scripts/install.py install --agent codex --scope project --link
```

- `<skills_dir>/deterministic-agentic-workflow` is created as a directory symlink pointing to the resolved source checkout, alongside relative sibling module aliases (`daw-*`, unless `--no-aliases` is passed).
- Ownership metadata is stored in `<skills_dir>/.daw-install-link.json` (never inside the source checkout, keeping `git status` clean).
- `status`, `install --update`, and `uninstall` recognize link-mode installations cleanly while still rejecting unowned foreign symlinks or tampered targets. Removing a link-mode installation removes only the symlinks and `.daw-install-link.json`, leaving the source checkout untouched.
- Switching between copy mode and link mode requires `--update` (e.g., `install --link --update` or `install --update`).
- `--link` requires host directory symlink support and cannot be combined with `--no-aliases` to bypass the root bundle symlink itself.

## Hosts without symlinks

```bash
python3 scripts/install.py install --agent codex --scope user --no-aliases
```

This installs the same complete root bundle without sibling aliases. The root router loads children through `$SUITE_ROOT/skills/daw-*/SKILL.md`; independent ambient discovery of child modules depends on the client's recursive scan. Do not claim missing aliases are missing bundled modules.

On Windows, use `python` when `python3` is unavailable. Directory symlink creation may require Developer Mode or privileges; the installer does not change system policy. If symlink creation fails, it aborts without applying the new bundle and suggests `--no-aliases`. See [Python's symlink documentation](https://docs.python.org/3/library/os.html#os.symlink).

## Status, updates, diagnostics, and removal

Use the same agent (`codex`, ..., or `all`), scope, project, or custom directory for each operation:

```bash
python3 scripts/install.py status --agent codex --scope user --json
python3 scripts/install.py install --agent codex --scope user --update
python3 scripts/install.py uninstall --agent codex --scope user
python3 scripts/install.py doctor --scope project --project-root /path/to/project --json
```

`--agent all` operates across every preset client (`codex`, `claude`, `gemini`, `cursor`, `copilot`, `opencode`, `antigravity`) at the selected `--scope` for `install`, `status`, and `uninstall`, returning per-agent summaries in both text and `--json`.

`doctor` is strictly read-only and checks:

- Python `>= 3.10`
- `git >= 2.20` availability
- Host directory symlink support (probed in an isolated temporary directory)
- Installation status across all preset clients at the chosen scope
- Overlapping or duplicate installations at the same scope (such as `.agents/skills` alongside `.claude/skills`, or `.gemini/skills` alongside `.gemini/antigravity/skills`)

Updates read the checkout that contains the invoked installer. Refresh that checkout first, then run `install --update`. Repeat `--no-aliases` for an installation that should remain root-only, or `--link` to maintain link mode. Reinstalling identical contents (matching version, mode/files, and aliases) short-circuits inside the lock without creating a staging copy and returns `unchanged`.

### Migration from historical releases

Installations created with historical module sets (such as the 8-module, 10-module, or 11-module releases) are supported for status inspection, updates, and removal:

- `status`: validates the installed bundle against historical known alias subsets without requiring manual receipt changes.
- `install --update`: stages the full 12-module bundle, verifies existing alias symlinks and file inventory, creates symlinks for newly introduced modules (`daw-ship`, alongside previously introduced `daw-untangle`, `daw-setup`, and `daw-wizard`), and writes an updated receipt containing all canonical modules. Existing collisions with newly added module names abort the update to preserve foreign skills.
- `uninstall`: cleanly removes historical installations by unlinking only the aliases recorded in the previous receipt and removing the suite bundle.

Updating the bundle does not migrate project artifacts. After installing a newer suite, each project that uses DAW must run the `daw-setup` Upgrade Re-check (read-only diagnosis) before spec-dependent work: `validate.py config` reports `config_daw_version_stale` when the project's recorded `daw_version` predates the installed `VERSION`; the Upgrade Re-check collects `### Project migration` items between versions, runs `validate.py config`, `validate.py ledger`, and `validate.py docs` per ledger record, and only bumps `daw_version` after all errors are resolved and the user confirms.

`--dry-run` inspects the source and destination without creating files or directories. An actual update stages and validates the new bundle before replacement. The installer records file hashes and alias ownership in `.daw-install.json` inside its installed bundle (or link target and aliases in `<skills_dir>/.daw-install-link.json` for `--link`). Updated, added, or missing installed files and changed aliases or link targets block both replacement and removal. Preserve your edits outside the installation and resolve the discrepancy before retrying; there is no force-overwrite option. Unrelated skills are left untouched.

Updates and removal require an installer-owned bundle. An existing manually copied suite or unowned foreign symlink is preserved; choose another target or move it aside yourself. The receipt is a local ownership record, not a signature or authorization token. A lock prevents simultaneous installer mutations in the same skill directory. A stale lock after interruption must be inspected before manual removal. If rollback itself fails, the installer retains the previous bundle in a staging directory and reports its recovery path.

Use `--json` for machine-readable results. Exit `0` means the operation succeeded, `doctor` found no prerequisite/installation errors, or a dry-run plan was produced; `1` means a missing or partial installation, collision, changed files, failed validation, prerequisite error in `doctor`, or filesystem failure; `2` means invalid command arguments. `status`, `doctor`, and `--dry-run` are read-only.

## Unified `daw` CLI

A zero-dependency `daw` CLI wrapper (`scripts/daw.py`, packaged via `pyproject.toml` for `pip install -e .`, `pipx`, or `uv tool`) dispatches all suite tools from a single command:

```bash
daw --version
daw --help
daw route "<request>"
daw validate package --root .
daw run next --plan <plan.md>
daw worktree status --project-root .
daw install doctor --scope project --project-root .
daw derive-ledger --spec-dir docs
daw derive-tasks --plan <plan.md>
```

From a source checkout without installing the console script, invoke `python3 scripts/daw.py <subcommand> [args...]`.

## Canonical paths and verification

Resolve a discovered module's directory symlink to its physical target before resolving `../../SKILL.md`, references, templates, or scripts. The suite root is the canonical module directory's `../..`. If resolution fails, report the missing dependency without scanning unrelated directories.

From the installed root, run:

```bash
python3 scripts/route.py --check-suite
python3 scripts/validate.py package
```

Both utilities remain strictly read-only. Structural validity does not establish semantic success, grant operational authorization, or prove native client discovery. The mutating installer is separate from these inspection engines.

Third-party skill managers may copy nested modules independently or omit supporting resources. Use this installer (or the Claude Code plugin manifest) as the supported installation path and keep the complete suite intact. The project does not yet certify `npx skills add --all` or hosted agent synchronization.
