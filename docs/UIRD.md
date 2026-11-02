# User Interface Requirements Document (UIRD)

## Deterministic Agentic Workflow

### 1. Interface Scope & Philosophy

The Deterministic Agentic Workflow has no graphical user interface (no GUI, web views, desktop windows, or CSS design tokens). The entire interface consists of:

1. **Command Line Interface (CLI):** Invoked via terminal shell environments.
2. **Standard Output & Error Streams (`stdout` / `stderr`):** Predictable text or machine-parseable JSON envelopes.
3. **Exit Codes:** POSIX-compliant numeric status returns for process supervisors and quality gates.

The design philosophy emphasizes:

- **Portability:** Consistent behavior across Linux, macOS, and POSIX-compliant shells.
- **Screen Reader & Script Accessibility:** High-contrast plain text without decorative ASCII art or complex terminal escape animations.
- **Data Privacy:** Error and diagnostic output displays file paths and finding codes without leaking file contents, credentials, or sensitive environment state.

---

### 2. CLI Command Surface & Invocations

All commands are accessed via `scripts/validate.py` and `scripts/route.py` using Python 3.10+:

```bash
# General Validation Syntax
python3 scripts/validate.py <subcommand> [options]

# Subcommand 1: Package Validation
python3 scripts/validate.py package [--root SKILL_ROOT] [--format text|json]

# Subcommand 2: Contract Validation
python3 scripts/validate.py contract <CONTRACT_FILE> --project-root PROJECT_ROOT --stage plan|execute|complete [--format text|json]

# General Routing Syntax
python3 scripts/route.py <REQUEST_FILE> [--root SUITE_ROOT] [--format text|json]

# Suite Consistency Verification
python3 scripts/route.py --check-suite [--root SUITE_ROOT] [--format text|json]
```

#### Argument Definitions

- `subcommand`:
  - `package`: Verifies structural integrity of the skill package itself.
  - `contract`: Verifies a project's JSON task contract against its lifecycle stage.
- `--root <path>`:
  - Scope: `package` subcommand.
  - Optional. Default: Resolved parent directory of `scripts/` (the skill root).
- `<CONTRACT_FILE>`:
  - Scope: `contract` subcommand.
  - Required positional argument. Path to the task contract JSON file (either relative to `--project-root` or absolute).
- `--project-root <path>`:
  - Scope: `contract` subcommand.
  - Required. Absolute or relative path to the root of the project codebase being validated.
- `--stage plan|execute|complete`:
  - Scope: `contract` subcommand.
  - Required. Lifecycle validation gate to apply (`plan`, `execute`, or `complete`).
- `--format text|json`:
  - Scope: All subcommands across `validate.py` and `route.py`.
  - Optional. Default: `text`.
- `<REQUEST_FILE>`:
  - Scope: `scripts/route.py`.
  - Required positional argument (unless `--check-suite` is supplied). Path to JSON route request.
- `--check-suite`:
  - Scope: `scripts/route.py`.
  - Flag. Verifies manifest consistency, bundle containment, and module skill existence.

---

### 3. Exit Code Interface Contract

The CLI communicates deterministic pass/fail states via numeric process exit codes:

- **`0` (Success / Ready):** All structural checks, schemas, boundary constraints, and stage requirements passed with zero critical violations (`valid: true`), or route calculation produced status `ready`.
- **`1` (Validation Failure / Needs-Input):** One or more violations occurred (e.g., missing files, broken links, invalid JSON, missing contract fields, boundary breaches, hash mismatches), or route calculation requires user clarification / is blocked.
- **`2` (Invocation / CLI / Syntax Error):** Invalid command-line arguments, unknown flags, non-existent files passed to required CLI parameters, duplicate JSON keys, or malformed JSON payloads.

---

### 4. Text Stream Interface (`--format text`)

#### 4.1 Success Output (`stdout`)

On successful validation, the CLI outputs a concise summary to `stdout`:

```text
PASS: Package integrity verified (19 files checked, 0 broken links).
```

Or for contract validation:

```text
PASS: Contract 'TC-2026-001' verified for stage 'plan' (0 violations).
```

#### 4.2 Failure Output (`stdout` / `stderr`)

When violations are detected:

- Summary line and structured finding lines are written to `stdout`.
- Process exits with code `1`.
- Finding format: `[<FINDING_CODE>] <SEVERITY>: <MESSAGE> (Target: <PATH>, Line: <LINE_NUMBER>)`

Example:

```text
FAIL: Package validation failed with 1 finding(s):
  - [PKG_LINK_BROKEN] ERROR: Link 'templates/missing.md' does not exist (Target: SKILL.md, Line: 42)
```

Example (Contract Violation):

```text
FAIL: Contract validation failed with 2 finding(s):
  - [CTR_FIELD_MISSING] ERROR: Required field 'files_to_modify' missing for stage 'execute' (Target: task-contract.json)
  - [CTR_BOUNDARY_VIOLATION] ERROR: Path '../secret.env' escapes project root (Target: task-contract.json)
```

---

### 5. Routing CLI Stream Interface (`scripts/route.py`)

#### 5.1 Route Text Output (`stdout`)

```text
Status: ready
Stages: daw-plan, daw-build, daw-review, daw-verify
Reasons:
  - Routing intent 'feature' with clear requirements to execution pipeline.
Constraints:
  - read_only: false
  - documentation_only: false
  - interactive_approval_required: false
  - authorization_granted: false
Limitations:
  - Routing calculation only; does not execute stages or grant runtime authorization.
```

#### 5.2 Route JSON Output (`stdout`)

```json
{
  "schema_version": 1,
  "status": "ready",
  "stages": ["daw-plan", "daw-build", "daw-review", "daw-verify"],
  "reasons": [
    "Routing intent 'feature' with clear requirements to execution pipeline."
  ],
  "blockers": [],
  "constraints": {
    "read_only": false,
    "documentation_only": false,
    "interactive_approval_required": false,
    "authorization_granted": false
  },
  "limitations": [
    "Routing calculation only; does not execute stages, evaluate agent identity, or grant runtime authorization."
  ]
}
```

---

### 6. Validation JSON Stream Interface (`--format json`)

{
"status": "PASS",
"exit_code": 0,
"summary": {
"subcommand": "package",
"target_root": "/home/regio/projects/deterministic-agentic-workflow",
"findings_count": 0
},
"findings": []
}

````

#### 5.2 Failure JSON Envelope (`stdout`)

```json
{
  "status": "FAIL",
  "exit_code": 1,
  "summary": {
    "subcommand": "contract",
    "target_root": "/home/regio/projects/target-app",
    "stage": "complete",
    "findings_count": 1
  },
  "findings": [
    {
      "code": "CTR_HASH_MISMATCH",
      "severity": "ERROR",
      "target": "src/core.py",
      "message": "Recorded SHA-256 does not match disk file content",
      "details": {
        "expected": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "actual": "8743b52063cd84097a65d1633f5c74f5dbf3866c7ddbaccac97d40d837faefe9"
      }
    }
  ]
}
````

---

### 6. Accessibility, Privacy & Screen Reader Guarantees

- **No Interactive Blocking:** The CLI never prompts for interactive user input (`stdin` is not read); all configurations must be supplied via CLI flags.
- **Predictable Error Locations:** Machine parsers and screen readers can split finding lines reliably by delimiter ` - [` without regex ambiguity.
- **Redaction of File Payloads:** The CLI never prints the content of analyzed files, environment variables, or private keys into terminal output.
