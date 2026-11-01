# Design Specification (DESIGN.md)

## Deterministic Agentic Workflow

### CONTEXT-MAP

```
+-----------------------------------------------------------------------------+
|                         CLI Dataflow Architecture                           |
+-----------------------------------------------------------------------------+

      [User / Agent CLI Input]
                 |
                 v
   +---------------------------+
   |   argparse CLI Parser     |
   +---------------------------+
                 |
        +--------+--------+
        |                 |
        v                 v
   [package]          [contract]
        |                 |
        v                 v
 +--------------+  +---------------+
 | ValidatePkg  |  | ValidateContr |
 +--------------+  +---------------+
        |                 |
        +--------+--------+
                 |
                 v
     +-----------------------+
     |   Findings Collector  |
     | (Severity, Code, Path)|
     +-----------------------+
                 |
        +--------+--------+
        |                 |
        v                 v
   [format: text]    [format: json]
   (Human-readable)  (Single-envelope stdout)
        |                 |
        +--------+--------+
                 |
                 v
       [Deterministic Exit]
        (0: Clean / Warning)
        (1: Validation Error)
        (2: CLI / Syntax Error)
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
      "enum": ["package", "contract"]
    },
    "valid": {
      "type": "boolean"
    },
    "findings": {
      "type": "array",
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

---

### 3. Component Interaction & Dataflow Design

The internal architecture of `scripts/validate.py` follows a linear, pipeline-oriented design pattern with explicit data boundaries:

#### 3.1 Input Normalization & Parsing

1. **Argument Parsing (`argparse`):** Validates argument presence, flag compatibility, and command selection.
2. **Path Containment Setup:** Establishes the authoritative base boundary (either package root or project root).
3. **Payload Ingestion:**
   - For `package`: Ingests markdown files through targeted text readers and the scalar YAML frontmatter parser.
   - For `contract`: Ingests JSON using `json.loads(..., object_pairs_hook=_strict_json_object_pairs_hook)`.

#### 3.2 Evaluation Engines

1. **Package Evaluator:**
   - Scans `SKILL.md` for frontmatter fields (`name`, `description`, `compatibility`).
   - Verifies existence of all 13 canonical template files in `templates/`.
   - Audits routing tables in `references/routing.md` for mandatory columns and cross-links.
   - Evaluates markdown link targets, resolving URLs and rejecting unescaped host-specific URI schemes outside code fences.
2. **Contract Evaluator:**
   - Validates schema structure, type invariants, and non-empty strings.
   - Computes SHA-256 digests of files listed in `baseline.files` and compares against expected hashes.
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
