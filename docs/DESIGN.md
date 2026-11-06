# Design Specification (DESIGN.md)

## Deterministic Agentic Workflow

### CONTEXT-MAP

```
+-----------------------------------------------------------------------------+
|                      CLI & Engine Dataflow Architecture                     |
+-----------------------------------------------------------------------------+

                          [User / Agent CLI Input]
                                     |
                 +-------------------+-------------------+
                 |                                       |
                 v                                       v
   [scripts/validate.py CLI]                [scripts/route.py CLI]
        |                |                       |             |
        v                v                       v             v
   [package]         [contract]              [REQUEST]   [--check-suite]
        |                |                       |             |
        v                v                       v             v
 +--------------+ +---------------+      +----------------+ +----------------+
 | ValidatePkg  | | ValidateContr |      | RouteEngine    | | SuiteChecker   |
 +--------------+ +---------------+      +----------------+ +----------------+
        |                |                       |             |
        +--------+-------+                       +------+------+
                 |                                      |
                 v                                      v
     +-----------------------+              +-----------------------+
     |   Findings Collector  |              | Structured Envelope   |
     | (Severity, Code, Path)|              | (Status, Stages, etc.)|
     +-----------------------+              +-----------------------+
                 |                                      |
        +--------+--------+                    +--------+--------+
        |                 |                    |                 |
        v                 v                    v                 v
   [format: text]    [format: json]       [format: text]    [format: json]
        |                 |                    |                 |
        +--------+--------+                    +--------+--------+
                 |                                      |
                 v                                      v
       [Deterministic Exit]                   [Deterministic Exit]
        (0: Pass / Valid)                      (0: Ready / Sound)
        (1: Validation Error)                  (1: Needs-Input / Error)
        (2: CLI / Syntax Error)                (2: CLI / Syntax Error)
```

---

### 1. User Interface & Experience Philosophy (CLI UX)

The Deterministic Agentic Workflow system is an offline command-line interface tool and specification library. It deliberately does not contain graphical user interfaces (GUI), web dashboards, visual widgets, CSS tokens, or frontend frameworks.

The user interface is entirely realized through standard POSIX command-line paradigms:

- Standard command invocation with options, flags, and arguments.
- Standard input/output stream segregation: deterministic data envelopes to standard output (`stdout`), diagnostic error banners to standard error (`stderr`).
- Deterministic, unambiguous process exit status codes (0, 1, 2) consumable by shell scripts, git hooks, CI pipelines, and agent harnesses.
- Dual-mode output formatting: human-oriented diagnostic text and machine-oriented structured JSON.

---

### 2. Output Formatting & Data Shapes

#### 2.1 Text Output Mode (`--format text`)

The text output mode is optimized for human inspection in local terminal sessions. It emits clear section headers, bulleted lists of issues categorized by severity, and concluding summary lines.

##### Success Output Example (Exit 0):

```text
Package validation passed: .
Warnings:
  - [baseline_unverified] baseline.files: Baseline file list is empty; pre-execution state cannot be verified against file hashes.
```

##### Failure Output Example (Exit 1):

```text
Contract validation failed: task-contract.json
Errors:
  - [missing_approval] approval: High-risk operation requires explicit approval in execute stage.
  - [hash_mismatch] baseline.files[0]: File hash mismatch for src/core.py (expected: abc123..., actual: def456...).
```

##### Command / Syntax Error Output Example (Exit 2, to stderr):

```text
Error: Duplicate key detected in JSON object: 'acceptance_criteria'
```

#### 2.2 JSON Output Mode (`--format json`)

The JSON mode guarantees that stdout contains exactly one valid, well-formed JSON object representing the validation envelope. Diagnostic progress messages or warnings are never interleaved into stdout as raw strings.

##### JSON Output Schema Definition:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["schema_version", "check", "valid", "findings", "limitations"],
  "properties": {
    "schema_version": {
      "type": "integer",
      "const": 1
    },
    "check": {
      "type": "string",
      "enum": ["package", "contract", "check-suite"]
    },
    "valid": {
      "type": "boolean"
    },
    "findings": {
      "items": {
        "type": "object",
        "required": ["severity", "code", "path", "message"],
        "properties": {
          "severity": {
            "type": "string",
            "enum": ["error", "warning"]
          },
          "code": {
            "type": "string"
          },
          "path": {
            "type": "string"
          },
          "message": {
            "type": "string"
          }
        }
      }
    },
    "limitations": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  }
}
```

##### Realized JSON Output Instance:

```json
{
  "schema_version": 1,
  "check": "contract",
  "valid": true,
  "findings": [],
  "limitations": [
    "Structural verification only; does not authenticate evidence authenticity, runtime safety, or operational authorization.",
    "Approval presence captures an opaque reference only and does not constitute runtime authorization.",
    "Baseline hashes verify recorded file states at validation time only; revision strings are not verified against VCS history."
  ]
}
```

##### Route Engine JSON Output Schema & Realized Instance:

The route engine emitted envelope guarantees standard keys:

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
    "Routing calculation only; does not execute stages, evaluate agent identity, or grant runtime authorization.",
    "Stage selection is derived from declarative policy in references/suite-manifest.json."
  ]
}
```

---

### 3. Component Interaction & Dataflow Design

The internal architecture of the DAW suite follows a modular, pipeline-oriented design pattern with explicit data boundaries:

#### 3.1 Suite Router & Specialized Modular Skills

1. **Root Router (`SKILL.md`):** Serves as the top-level suite entry point. Reads incoming user intent and coordinates child modules using `scripts/route.py` and `references/suite-manifest.json`. Router does not run bloated flat procedures.
2. **Specialized Child Skills (`skills/daw-*`):** 11 self-contained skills (`daw-design`, `daw-plan`, `daw-debug`, `daw-build`, `daw-review`, `daw-verify`, `daw-workspace`, `daw-ask`, `daw-setup`, `daw-wizard`, `daw-untangle`) containing concrete operational steps and returning clean orchestrator handoffs.
3. **Advisory Skill (`daw-ask`):** Acts as an original, objective architecture consultant without persona impersonation or external identity spoofing.
4. **Sibling Symlink Distribution:** Installed environments mount sibling directories symlinked to bundled `skills/daw-*` directories. Unbundled standalone claims are rejected.

#### 3.2 Route Engine (`scripts/route.py`)

1. **Input Parser & Strict JSON Hook:** Uses custom JSON object pairs hook to reject duplicate keys and verifies mandatory keys (`schema_version`, `intent`, `requirements`, `risk`, `workspace`). Unknown keys and nonstandard types fail immediately with exit code 2.
2. **Policy Evaluation Engine:** Evaluates declarative rules from `references/suite-manifest.json`. Maps intents (`bootstrap`, `adopt`, `feature`, `bugfix`, `patch`, `review`, `untangle`, `ask`, `setup`) to appropriate stages.
3. **Workspace Precedence:** Evaluates `workspace` for mutating intents (`feature`, `bugfix`, `patch`). Prepends `daw-workspace` if `isolated`; proceeds if `in-place`; marks `needs-input` if `unknown`.
4. **High-Risk Constraint Enforcing:** If `risk` is `high`, marks `constraints.interactive_approval_required: true`. Permanently emits `constraints.authorization_granted: false`.
5. **Structural Suite Checker (`--check-suite`):** Validates existence of all 11 module skill directories and files within the suite root boundary without circular imports.

#### 3.3 Validation Engine (`scripts/validate.py`)

1. **Argument Parsing (`argparse`):** Validates argument presence, flag compatibility, and command selection (`package` or `contract`).
2. **Path Containment Setup:** Establishes the authoritative base boundary (either package root or project root).
3. **Payload Ingestion:**
   - For `package`: Ingests markdown files through targeted text readers and scalar YAML frontmatter parser.
   - For `contract`: Ingests JSON using `json.loads(..., object_pairs_hook=_strict_json_object_pairs_hook)`.

#### 3.2 Evaluation Engines

1. **Package Evaluator:**
   - Scans `SKILL.md` for frontmatter fields (`name`, `description`, `compatibility`).
   - Verifies existence of all 13 canonical template files in `templates/`.
   - Audits routing tables in `references/routing.md` for mandatory columns and cross-links.
   - Evaluates markdown link targets, resolving URLs and rejecting unescaped host-specific URI schemes outside code fences.
2. **Contract Evaluator:**
   - Validates schema structure, type invariants, and non-empty strings.
   - Computes SHA-256 digests of files listed in `baseline.files` and compares against expected hashes during `plan` and `execute`; verifies historical syntax, digest formats, and bounded containment at `complete` without requiring live file existence or hash equality.
   - Validates `operation` descriptors and enforces risk-tiered `approval` bindings across lifecycle stages (`plan`, `execute`, `complete`).
   - Verifies `evidence` artifact records against `acceptance_criteria` and confirms referenced files exist within project root.

#### 3.3 Findings Aggregation & Exit Dispatch

1. Collected findings are segregated into `error` (fatal) and `warning` (non-fatal).
2. `valid` is set to `True` if and only if `error` count is 0.
3. Formatter serializes output according to `--format`.
4. Process terminates with `sys.exit(0)` when valid, or `sys.exit(1)` when invalid.

---

### 4. Failure Modes & Behavioral Contracts

The CLI is engineered with resilient failure isolation to guarantee predictable automation:

| Scenario / Trigger                       | Exit Code | Stdout Behavior                             | Stderr Behavior               |
| :--------------------------------------- | :-------- | :------------------------------------------ | :---------------------------- |
| Validation cleanly passed                | 0         | Human summary or JSON (`valid: true`)       | Clean (empty)                 |
| Validation passed with warnings          | 0         | Human summary or JSON (`valid: true`)       | Clean (empty)                 |
| Validation failed (contract/pkg invalid) | 1         | Human failure list or JSON (`valid: false`) | Clean (empty)                 |
| CLI usage error / missing required flags | 2         | Clean (empty)                               | Argparse usage diagnostic     |
| Target contract file does not exist      | 2         | Clean (empty)                               | Error: File not found         |
| Duplicate JSON keys in contract          | 2         | Clean (empty)                               | Error: Duplicate key detected |
| Malformed JSON syntax in contract        | 2         | Clean (empty)                               | Error: Invalid JSON           |

---

### 5. Architectural Non-Goals & Invariants

To maintain zero runtime bloat and six-month maintainability, the system enforces the following explicit boundaries:

1. **No Automatic Project Discovery:** The tool does not crawl parent or child directories searching for candidate projects. The user or runner must explicitly pass `--project-root` and contract file paths.
2. **No Automatic Hook Installation:** The tool does not automatically register itself into `.git/hooks` or configure global shell hooks. Integration is driven explicitly by callers.
3. **No Interactive Prompts:** The CLI is strictly non-interactive; it never halts to prompt the user for input (`stdin` is not read).
4. **No Code Sandboxing or Subprocess Execution:** The validator does not invoke unit tests, compile source code, or execute scripts referenced in contracts or evidence.
5. **No Network Telemetry:** The tool performs no remote API calls, analytics collection, or cloud synchronization.

---

### BLOCKERS

- None. The CLI design and output data shapes are fully implemented, verified across 56 regression tests, and adhere to strict POSIX and JSON standards.
