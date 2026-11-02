# Installation, Discovery & Module Distribution Reference

This reference describes the installation models, filesystem layout, and discovery mechanisms for the Deterministic Agentic Workflow (DAW) suite.

---

## 1. Suite Packaging Model & Self-Contained Integrity

The DAW suite is self-contained as a full 8-module bundle. It requires **no external workflow frameworks (e.g. Superpowers) or third-party skill registries**.

### Mandatory Core Modules

All 8 internal execution modules bundled in `skills/` are strictly required:

1. `daw-design`
2. `daw-plan`
3. `daw-debug`
4. `daw-build`
5. `daw-review`
6. `daw-verify`
7. `daw-workspace`
8. `daw-ask`

> **Missing Module Policy:** All 8 modules are considered required core components. If any required internal module is missing or corrupted, the installation is considered **incomplete and blocked**. The suite does not provide silent inline fallbacks or pretend to run complex multi-step workflows without its core modules.

Optional external domain tools and skills remain subordinate to host policy and user permissions.

---

## 2. Directory Layout & Distribution Architecture

The DAW suite supports two primary installation architectures depending on whether the host agent environment supports nested sub-skills or flat sibling discovery:

```
[Agent Skills Directory or Local Repo]
├── deterministic-agentic-workflow/          <-- Suite Root Router
│   ├── SKILL.md                             <-- Root Router Skill
│   ├── README.md
│   ├── scripts/
│   │   ├── route.py                         <-- Read-only Manifest & Route Engine
│   │   └── validate.py                      <-- Read-only Package Validator
│   ├── references/
│   │   ├── suite-manifest.json              <-- Declarative Route Policy
│   │   ├── routing.md
│   │   ├── installation.md
│   │   └── validation.md
│   ├── templates/                           <-- 13 Specification Templates
│   └── skills/                              <-- Bundled Canonical Modules
│       ├── daw-design/SKILL.md
│       ├── daw-plan/SKILL.md
│       ├── daw-debug/SKILL.md
│       ├── daw-build/SKILL.md
│       ├── daw-review/SKILL.md
│       ├── daw-verify/SKILL.md
│       ├── daw-workspace/SKILL.md
│       └── daw-ask/SKILL.md
│
├── daw-design -> deterministic-agentic-workflow/skills/daw-design       <-- Sibling Symlink
├── daw-plan -> deterministic-agentic-workflow/skills/daw-plan           <-- Sibling Symlink
├── daw-debug -> deterministic-agentic-workflow/skills/daw-debug         <-- Sibling Symlink
├── daw-build -> deterministic-agentic-workflow/skills/daw-build         <-- Sibling Symlink
├── daw-review -> deterministic-agentic-workflow/skills/daw-review       <-- Sibling Symlink
├── daw-verify -> deterministic-agentic-workflow/skills/daw-verify       <-- Sibling Symlink
├── daw-workspace -> deterministic-agentic-workflow/skills/daw-workspace <-- Sibling Symlink
└── daw-ask -> deterministic-agentic-workflow/skills/daw-ask             <-- Sibling Symlink
```

---

## 3. Portable Installation Approaches

### Method A: Canonical Bundle with Sibling Symlinks (Recommended)

This approach keeps the entire repository unified under `deterministic-agentic-workflow/` while exposing the 8 child modules as top-level discoverable skills for agent platforms that only scan top-level directories. This prevents independent alias drift and maintains a single authoritative source of truth.

> **Direct Discovery & Governance Invariant:** When an agent environment discovers or invokes any child module directly via sibling symlinks (e.g. `skills/daw-build` or `~/.agents/skills/daw-build`), the child module MUST NOT bypass suite governance. It must execute the Governance Loader Sequence: resolve its physical path, load root governance (§4, §6) and `references/routing.md` §5, and pre-mutation operations rules from `references/operations.md`.

1. **Copy or Clone Suite Root:**
   Set `SKILLS_DIR` to your agent client's designated skills directory and copy or clone the complete package from its source repository:

   ```bash
   SKILLS_DIR="/path/to/client/skills"
   cp -R /path/to/source/deterministic-agentic-workflow "$SKILLS_DIR/deterministic-agentic-workflow"
   ```

2. **Create Relative Sibling Symlinks:**
   ```bash
   cd "$SKILLS_DIR"
   ln -s deterministic-agentic-workflow/skills/daw-design daw-design
   ln -s deterministic-agentic-workflow/skills/daw-plan daw-plan
   ln -s deterministic-agentic-workflow/skills/daw-debug daw-debug
   ln -s deterministic-agentic-workflow/skills/daw-build daw-build
   ln -s deterministic-agentic-workflow/skills/daw-review daw-review
   ln -s deterministic-agentic-workflow/skills/daw-verify daw-verify
   ln -s deterministic-agentic-workflow/skills/daw-workspace daw-workspace
   ln -s deterministic-agentic-workflow/skills/daw-ask daw-ask
   ```

### Method B: Non-Symlink Host Environments

For environments that forbid filesystem symlinks (such as certain restricted container sandboxes or operating system policies):

1. **Preserve Complete Nested Bundle:** Keep the entire `deterministic-agentic-workflow` directory intact as a single nested bundle.
2. **Do Not Make Standalone Flat Copies:** Flat copies of individual modules to sibling directories break root-relative links (`../../templates/...` and `../../references/...`). The suite relies on canonical root relative paths; flat independent copies suffer from semantic breakages and drift.
3. **Explicit Resolved Paths:** On platforms without symlink support, the root router and host orchestrators load modules using explicit, resolved real filesystem paths (`$SUITE_ROOT/skills/daw-*/SKILL.md`). Direct client ambient discovery of individual modules is unsupported unless the agent runner configuration explicitly supports nested skill discovery paths.

---

## 4. Canonical Relative Path Resolution & Symlink Disambiguation

To guarantee portability across operating systems, containers, and user directories:

- **No Hardcoded Absolute Paths:** Suite documents and module instructions never hardcode absolute host paths like `/home/...` or `/Users/...`.
- **No Proprietary Skill URIs:** Module cross-references use standard POSIX relative paths (`../../references/...`), never proprietary URI schemes or custom protocols.
- **Symlink / Alias Canonicalization:** When modules are installed via symlinks or aliases (such as `~/.agents/skills/daw-*` pointing to `deterministic-agentic-workflow/skills/daw-*`), standard Markdown link resolvers or tools may naively resolve relative paths (like `../../references/...`) against the logical alias path or working directory, failing to reach the suite root. Clients and agents MUST canonicalize the `SKILL.md` symlink to its physical target before reading relative references. The suite root is strictly `canonical_module_dir/../..`.
- **Resolution Fallbacks:** Use the host environment's native path resolution. Shell `realpath` is not mandatory; use whatever path resolution API the host provides. If a symlink or canonical target cannot be resolved, agents MUST report a blocked dependency rather than traversing arbitrary parent or unrelated directories.
- **Script Root Resolution:** `scripts/route.py` and `scripts/validate.py` automatically determine the suite root relative to `Path(__file__).resolve().parent.parent`.

## 5. Verification of Suite Installation

After installing or updating the suite, run the two read-only verification commands to confirm structural and operational readiness:

```bash
# 1. Check suite manifest schema and module availability
python3 "$SUITE_ROOT/scripts/route.py" --check-suite

# 2. Check package integrity and template availability
python3 "$SUITE_ROOT/scripts/validate.py" package
```

Both checks perform read-only structural verification (validating manifest schemas, template existence, and module file presence). Note that a status of `ready` indicates structural readiness of the installation; it does not substitute for runtime verification of operational code.
