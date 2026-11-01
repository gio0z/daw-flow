# Installation & Agent Discovery Reference

This document describes how to install, locate, and activate the `deterministic-agentic-workflow` skill package across different AI coding environments.

---

## 1. Package Characteristics

- **Zero External Dependencies:** Built strictly with standard Markdown files and Python 3.10+ standard library modules. No third-party packages or virtual environment activation required.
- **Instruction-First:** The core cognitive workflows, 13-doc specification planning matrices, specialist routing rules, and verification principles operate entirely through prompt and instruction reading.
- **Read-Only Package Validator:** A lightweight, read-only Python utility (`scripts/validate.py`) is provided for structural and boundary verification.

---

## 2. Installation Approaches

Installation is user-controlled. There is no automated shell script, background daemon, or system configuration modifier. Choose the method appropriate for your environment:

### Method A: Copy into an Agent Skills Directory

Agent platforms that support the Agent Skills specification discover skills by scanning dedicated directories for a folder containing `SKILL.md`.

1. Copy the entire `deterministic-agentic-workflow` directory into your agent client's designated skills folder:
   - **Local project skills:** `<project-root>/.agents/skills/deterministic-agentic-workflow`
   - **Global user skills:** `~/.agents/skills/deterministic-agentic-workflow` (or the path defined in your tool's documentation).
2. Ensure you copy the complete directory including `scripts/`, `tests/`, `references/`, and `templates/`, while excluding `.git/`, test caches (`__pycache__`), environment secrets, or editor temp files.
3. Verify that `SKILL.md` resides directly at the root of the copied directory:
   ```text
   <skills-dir>/deterministic-agentic-workflow/
   ├── SKILL.md
   ├── README.md
   ├── references/
   │   ├── routing.md
   │   ├── operations.md
   │   ├── validation.md
   │   ├── installation.md
   │   └── task-contract.example.json
   ├── templates/
   │   └── ... (13 doc templates)
   ├── scripts/
   │   └── validate.py
   └── tests/
       └── test_validate.py
   ```

_Note: While `.agents/skills` is an emerging convention among various agent implementations, discovery directories are not universally standardized. Always verify your specific client tool's documentation for supported skill paths._

### Method B: Manual Instruction Inclusion (Non-Skills Environments)

If your AI environment or web interface does not support automated skill discovery directories (e.g., standard API prompts, prompt chains, or system instructions):

1. **System Prompt / Instruction File:** Load the contents of `SKILL.md` directly into your agent's system prompt or project instruction file (such as `.cursorrules`, `CLAUDE.md`, or custom instructions).
2. **Context Referencing:** Reference supporting files (`references/routing.md`, `references/operations.md`, `templates/`) on demand when entering planning, design, or verification phases.
3. **Environments Without Shell or Python:** In environments without command-line access or Python installed, agents read the guidelines, 13-doc templates, and review checklists directly as instructional prompts. Standalone root instructions operate fully without Python or shell access. However, automated structural checks, hash verifications, and observable runtime proof cannot be executed programmatically in shellless environments.

---

## 3. Running the Validator Tool

When Python 3 (3.10+ intended) is available in the execution environment, you can run the read-only validator CLI.

The validator requires manual invocation via standard Python; copying or installing the skill package does not automatically execute Python or register background hooks.

Set `SKILL_DIR` to the actual resolved location of the skill folder (e.g. `"$HOME/.agents/skills/deterministic-agentic-workflow"` if copied to user skills, or your workspace path):

### Pasteable Command Examples:

```bash
# Define resolved skill directory and target project directory
SKILL_DIR="$HOME/.agents/skills/deterministic-agentic-workflow"
PROJECT_DIR="/path/to/project"

# Validate package integrity
python3 "$SKILL_DIR/scripts/validate.py" package

# Validate package with JSON output envelope
python3 "$SKILL_DIR/scripts/validate.py" package --format json

# Validate a task contract at planning stage
python3 "$SKILL_DIR/scripts/validate.py" contract "$PROJECT_DIR/task-contract.json" --project-root "$PROJECT_DIR" --stage plan

# Validate a task contract at completion stage
python3 "$SKILL_DIR/scripts/validate.py" contract "$PROJECT_DIR/task-contract.json" --project-root "$PROJECT_DIR" --stage complete
```

---

## 4. Compatibility & Limitations

- **Format Portability:** The package follows standard Agent Skills directory conventions (`SKILL.md` frontmatter with `name`, `description`, and `compatibility`).
- **Discovery & Client Testing Status:** The core instructional format is portable across AI agent clients. Only execution under the available local environment (Python 3.14 on Linux) has been verified; syntax uses standard Python 3.10+ constructs, but compatibility has not been matrix-tested across prior versions or multiple operating systems. Discovery behavior, automatic loading, or hook execution in other agent clients (Claude Code, Cursor, Codex, OpenCode, etc.) is unverified and vendor-dependent.
- **Security & Integrity:** The validator utility (`scripts/validate.py`) is strictly read-only and never modifies files, spawns subprocesses, or connects to networks. The overarching skill package contains guidelines and contracts intended to guide project state mutations through explicit, user-authorized agent tools. The skill itself installs no background services, global symlinks, or automatic hooks.
