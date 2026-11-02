# Installation and Agent Compatibility

DAW is distributed as one complete root skill with ten bundled modules. Install from a complete checkout or extracted release using Python 3.10+. The installer uses only the standard library and performs no network access.

## Install

```bash
git clone https://github.com/gio0z/deterministic-agentic-workflow.git
cd deterministic-agentic-workflow
python3 scripts/install.py install --agent codex --scope user
```

Replace `codex` with `claude`, `gemini`, `cursor`, or `copilot`. A user installation serves your projects on that machine. A project installation targets one repository:

```bash
python3 scripts/install.py install --agent claude --scope project --project-root /path/to/project
```

The default is `--agent codex --scope project`, with the current directory as project root. Specify `--project-root` when running from the DAW checkout to install into a different project. An explicit directory overrides both presets:

```bash
python3 scripts/install.py install --skills-dir /path/to/client/skills
```

The target directory contains a real copy of `deterministic-agentic-workflow/` and relative sibling directory symlinks such as:

```text
skills/
├── deterministic-agentic-workflow/
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   ├── scripts/
│   ├── references/
│   ├── templates/
│   └── skills/daw-build/SKILL.md
├── daw-build -> deterministic-agentic-workflow/skills/daw-build
└── ... nine other module aliases
```

The copy survives removal of the original checkout. All ten modules remain required; optional external specialist skills are not required. Never install flat independent copies of `daw-*`: their root-relative governance and resource links require the complete bundle.

## Client locations

These presets follow official local discovery documentation, checked 2 November 2026:

| Agent       | Project preset   | User preset         | Official reference                                                                                |
| ----------- | ---------------- | ------------------- | ------------------------------------------------------------------------------------------------- |
| Codex       | `.agents/skills` | `~/.agents/skills`  | [Build skills](https://learn.chatgpt.com/docs/build-skills)                                       |
| Claude Code | `.claude/skills` | `~/.claude/skills`  | [Skills](https://code.claude.com/docs/en/skills)                                                  |
| Gemini CLI  | `.gemini/skills` | `~/.gemini/skills`  | [Agent skills](https://geminicli.com/docs/cli/skills/)                                            |
| Cursor      | `.cursor/skills` | `~/.cursor/skills`  | [Skills](https://cursor.com/docs/skills)                                                          |
| Copilot CLI | `.github/skills` | `~/.copilot/skills` | [Add skills](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills) |

Several clients also recognize shared `.agents/skills` directories. Use `--skills-dir` for a shared location or a different supported client. Avoid duplicate installations in overlapping discovery paths.

The Markdown skills use the [Agent Skills specification](https://agentskills.io/specification). Codex UI metadata is optional; it does not prevent other clients from reading `SKILL.md`. Host-native tools and approval semantics differ, so instructions defer to the host's actual capabilities and permissions. No vendor-specific tool whitelist is imposed.

These locations establish layout compatibility. Client discovery, automatic triggering, tool execution, and cloud synchronization require separate runtime checks. In particular, local folders may not synchronize into cloud agents, and Cursor/Copilot symlink handling is not assumed from directory documentation alone.

After installation, restart the agent or reload its skills, inspect its skill list, and invoke the root by name. Codex supports `$deterministic-agentic-workflow`; Claude Code supports `/deterministic-agentic-workflow`. Gemini provides `/skills list` and `/skills reload`. Natural-language invocation works only when the client has loaded the skill.

## Hosts without symlinks

```bash
python3 scripts/install.py install --agent codex --scope user --no-aliases
```

This installs the same complete root bundle without sibling aliases. The root router loads children through `$SUITE_ROOT/skills/daw-*/SKILL.md`; independent ambient discovery of child modules depends on the client's recursive scan. Do not claim missing aliases are missing bundled modules.

On Windows, use `python` when `python3` is unavailable. Directory symlink creation may require Developer Mode or privileges; the installer does not change system policy. If symlink creation fails, it aborts without applying the new bundle and suggests `--no-aliases`. See [Python's symlink documentation](https://docs.python.org/3/library/os.html#os.symlink).

## Status, updates, and removal

Use the same agent, scope, project, or custom directory for each operation:

```bash
python3 scripts/install.py status --agent codex --scope user --json
python3 scripts/install.py install --agent codex --scope user --update
python3 scripts/install.py uninstall --agent codex --scope user
```

Updates read the checkout that contains the invoked installer. Refresh that checkout first, then run `install --update`. Repeat `--no-aliases` for an installation that should remain root-only. Reinstalling identical contents returns `unchanged`.

### Migration from historical releases

Installations created with historical module sets (such as the 8-module release) are supported for status inspection, updates, and removal:

- `status`: validates the installed bundle against historical known alias subsets without requiring manual receipt changes.
- `install --update`: stages the full 10-module bundle, verifies existing alias symlinks and file inventory, creates symlinks for newly introduced modules (`daw-setup` and `daw-wizard`), and writes an updated receipt containing all canonical modules. Existing collisions with newly added module names abort the update to preserve foreign skills.
- `uninstall`: cleanly removes historical installations by unlinking only the aliases recorded in the previous receipt and removing the suite bundle.

`--dry-run` inspects the source and destination without creating files or directories. An actual update stages and validates the new bundle before replacement. The installer records file hashes and alias ownership in `.daw-install.json` inside its installed bundle. Updated, added, or missing installed files and changed aliases block both replacement and removal. Preserve your edits outside the installation and resolve the discrepancy before retrying; there is no force-overwrite option. Unrelated skills are left untouched.

Updates and removal require an installer-owned bundle. An existing manually copied suite is preserved; choose another target or move it aside yourself. The receipt is a local ownership record, not a signature or authorization token. A lock prevents simultaneous installer mutations in the same skill directory. A stale lock after interruption must be inspected before manual removal. If rollback itself fails, the installer retains the previous bundle in a staging directory and reports its recovery path.

Use `--json` for machine-readable results. Exit `0` means the operation succeeded or a dry-run plan was produced; `1` means a missing installation, collision, changed files, failed validation, or filesystem failure; `2` means invalid command arguments. `status` and `--dry-run` are read-only.

## Canonical paths and verification

Resolve a discovered module's directory symlink to its physical target before resolving `../../SKILL.md`, references, templates, or scripts. The suite root is the canonical module directory's `../..`. If resolution fails, report the missing dependency without scanning unrelated directories.

From the installed root, run:

```bash
python3 scripts/route.py --check-suite
python3 scripts/validate.py package
```

Both utilities remain strictly read-only. Structural validity does not establish semantic success, grant operational authorization, or prove native client discovery. The mutating installer is separate from these inspection engines.

Third-party skill managers may copy nested modules independently or omit supporting resources. Use this installer as the supported installation path and keep the complete suite intact. The project does not yet certify `npx skills add --all`, marketplace installation, or hosted agent synchronization.
