---
name: daw-verify
description: "Use to verify implementation changes against explicit claims, acceptance criteria, and observable runtime evidence. Enforces claim-check-actual observation of latest outputs, meaningful smoke tests (CLI, API, UI), full relevant regression suites, fresh failure scenarios before/after without rerunning user-reported errors solely to confirm, and zero tolerance for mock-based claims or dry-run-as-deploy proofs."
compatibility: "POSIX shell, CLI/API/UI test frameworks, Python 3.10+; fully self-contained markdown procedure."
---

# DAW Verify (Deterministic Semantic & Runtime Verification)

Operate verification under the core architectural axiom: **"Otaknya boleh generative, tangannya harus deterministic."**
Generative analysis synthesizes test matrix needs and diagnoses failures, but truth is established exclusively via deterministic test commands, runtime probes, and direct output observations.

> **Verification Contract Notice:**
>
> - A passing unit test or green mock is **never** proof that a system works end-to-end.
> - Dry-run (`--dry-run`, plan mode, mock deploy) is **never** proof of a real migration, build, or deploy.
> - User-reported errors and failures are authoritative ground truth: **NEVER** rerun a check solely to confirm what the user already observed and reported.
> - Distinguish clearly between: **Passed**, **Failing**, **Blocked** (dependency/environment missing), and **Unexercised** (not run or mock-only).

---

## 1. Trigger

Invoke `daw-verify` when:

- Code, configuration, documentation, or infrastructure changes have been made during a `daw-build` or `daw-patch` stage.
- Pre-handoff verification is required before opening a PR, delivering to user, or marking a milestone complete.
- A regression sweep is needed across affected packages, CLI endpoints, or API surfaces.
- Fresh failure evidence must be captured before/after a fix.

Do NOT invoke `daw-verify` for:

- Workspace branching/worktree management (use `daw-workspace`).
- Code review without runtime execution (use `daw-review`).
- Architectural design or document drafting (use `daw-design` or `daw-plan`).

---

## 2. Inputs & Prerequisites

1. **Change Manifest / Task Contract:**
   - Modified files and target scope.
   - Exact Acceptance Criteria (AC) defined in the task contract or plan (`../../references/task-contract.example.json` or project plan).
2. **Execution Environment:**
   - Target runtime, CLI binaries, test harnesses, or local test services running or accessible.
3. **Baseline Ground Truth & Relative Reference Base:**
   - User observations, error logs, or reproduction steps (if verifying a bugfix).
   - When loaded via symlink or alias (e.g. `~/.agents/skills/daw-verify`), resolve THIS `SKILL.md` symlink to its physical/canonical target file first.
   - The suite root is the canonical module directory's `../..`.
   - Resolve all relative links (`../../references/...`, `../../SKILL.md`) relative to the canonical physical module directory, NEVER relative to the logical alias path or `cwd`.
   - Use the host environment's resolved path; when shell `realpath` is unavailable, use the host file system's native target resolution. If the target cannot be resolved, report a blocked dependency rather than scanning parent or unrelated directories.
4. **Mandatory Governance Loading:**
   - Before executing any phase work, load root governance (`../../SKILL.md` §4 Safety & §6 Handoff Contract Schema) and canonical routing (`../../references/routing.md` §5 & §6). Reading governance documentation is not recursive router execution.
   - Before running test commands, scripts, or operational verifications, load `../../references/operations.md` §1 Preflight Safety & §2 High-Risk Approvals.
   - Verification uses read-only tests and non-destructive probes. High-risk live testing, load tests, or external service calls require interactive approval per operations.md §2; halt with `status: "blocked"` if unapproved. Local unit/integration suites require no production credentials.

---

## 3. Core Verification Rules

### Rule 1: The Claim -> Check -> Actual Triad

Every claim in a verification report must bind to an explicit check command and the actual observed output:

1. **Claim:** What specific behavior, constraint, or AC is being validated.
2. **Check:** The exact deterministic command executed (including arguments and working directory).
3. **Actual:** The exact observed output, exit code, or response artifact. Never summarize with "verified" or "works" without showing the command output.

Declare the expected exit code or response status, as applicable, and behavioral assertions before execution. Negative probes may expect a nonzero exit or an error response; they pass only when that exact expected rejection and its output are observed. Never revise an expectation merely to make a failed check pass.

### Rule 2: Fresh Failing Scenario (Before & After)

- When verifying bugfixes, capture the failing test/probe _before_ the fix (or inspect historical user logs).
- Apply the fix, then run the exact same check to capture the _passing_ output.
- **Exception:** If the user reported the failure with output, that observation is already ground truth. Do not rerun the broken state just to see it fail; proceed directly to applying and verifying the fix against that reported case.

### Rule 3: No Dry-Run as Deploy Proof

- `--dry-run`, terraform `plan`, compilation check, or static syntax linting is proof of syntax and plan validity only.
- It is **never** proof of database migration, successful network binding, container initialization, or runtime deployment.

### Rule 4: No Mock-Based Victory

- Mocks test unit-level isolation only.
- Acceptance criteria must be validated against real runtime boundaries (real CLI execution, actual API responses, live UI DOM states).
- If an external system cannot be contacted, mark the verification status explicitly as `Blocked` or `Unexercised`, never `Passed`.

---

## 4. Verification Steps

### Step 1: Scope & Matrix Formulation

Map all changes to required verification tiers:

- **Smoke CLI:** Executable help text, flag parsing, exits on invalid arguments, exit 0 on primary happy path.
- **Smoke API:** Endpoint responses, status codes, payload contract schemas, authentication error handling.
- **Smoke UI:** Component rendering, user interaction, error boundary states, keyboard/accessibility focus.
- **Regressions:** Full test suite for modified modules, plus cross-module consumer tests.

### Step 2: Execute Deterministic Checks

Run bounded, reproducible commands. Prefer standard project runners (`pytest`, `npm test`, `cargo test`, `go test`):

```bash
# Example CLI verification
./bin/my-tool --help
./bin/my-tool execute --input test.json

# Example API verification (local instance)
curl -sS -D - http://127.0.0.1:8080/health -o /dev/null

# Example Full Regression Suite
pytest tests/ -v -k "test_feature"
```

Observe and record:

- Standard output (`stdout`) and standard error (`stderr`).
- Process exit code.
- File modifications or side effects (if verifying disk operations).

### Step 3: Categorize Results Explicitly

Categorize every item in the verification matrix into one of four states:

1. **Passed:** Observed exit code or response status and output match the declared acceptance criteria. For example, an invalid-argument probe may pass with its expected exit code 2; a test runner normally requires exit code 0.
2. **Failing:** Command executed but its exit code, response status, output, or side effects violated the declared expectations.
3. **Blocked:** Check could not run due to missing environment, absent credentials, or uninstalled dependencies.
4. **Unexercised:** Check was skipped, omitted, or only simulated via mock.

---

## 5. Output Contract

Every completion of `daw-verify` delivers a structured handoff payload adhering to the canonical suite envelope. Rich verification checks, regression counts, and diagnostic observations are preserved under `details`:

```json
{
  "objective": "Verify session serializer token rotation and CLI error handling.",
  "input_paths": [
    "src/auth/serializer.py",
    "tests/auth/test_session_serializer.py"
  ],
  "output_paths": [],
  "acceptance_criteria": [
    {
      "criterion": "CLI exits with code 2 on missing required arguments",
      "status": "pass"
    },
    {
      "criterion": "SessionSerializer round-trips token_version without data loss",
      "status": "pass"
    }
  ],
  "evidence": [
    {
      "reference": "tests/auth/test_session_serializer.py",
      "summary": "pytest tests/auth/test_session_serializer.py exited 0 (2 passed)"
    },
    {
      "reference": "scripts/route.py",
      "summary": "scripts/route.py executed without args exited 2 with usage instructions"
    }
  ],
  "status": "pass",
  "handoff_to": null,
  "details": {
    "verification_verdict": "passed",
    "summary": "All exercised behavioral checks and regression suites passed with zero failures.",
    "checks": [
      {
        "claim": "CLI exits with code 2 on missing required arguments.",
        "check_command": "scripts/route.py",
        "expected_exit_code": 2,
        "exit_code": 2,
        "status": "passed",
        "observed_output": "Usage: scripts/route.py REQUEST [--format text|json] ...",
        "evidence_tier": "cli_smoke"
      },
      {
        "claim": "SessionSerializer round-trips token_version without data loss.",
        "check_command": "pytest tests/auth/test_session_serializer.py",
        "expected_exit_code": 0,
        "exit_code": 0,
        "status": "passed",
        "observed_output": "2 passed in 0.04s",
        "evidence_tier": "unit_behavioral"
      }
    ],
    "regressions": {
      "suite": "pytest tests/",
      "total": 42,
      "passed": 42,
      "failed": 0,
      "skipped": 0
    },
    "limitations": []
  }
}
```

_(Note: `status: "pass"` indicates that the verification stage checks have been executed and passed. No competing top-level verdict exists outside `details`)._
---

## 6. Exit Criteria

Verification is complete when:

1. Every Acceptance Criterion in the task contract has a corresponding `claim` with an executed `check` and recorded `observed_output`.
2. All exercised checks meet their declared exit-code, response-status, output, and side-effect expectations. Test runners normally exit 0; negative probes may require a specific nonzero exit or rejection response.
3. There are zero unacknowledged failures or silently skipped tests.
4. Any `Blocked` or `Unexercised` items are explicitly justified in `limitations`.
5. No dry-runs are recorded as deployment/migration proofs.

---

## 7. Stop / Replan Triggers

Stop verification and escalate back to orchestrator or previous stage when:

- **Core AC Failure:** Observed behavior contradicts design or PRD specifications -> Replan to `daw-debug` or `daw-build`.
- **Unexpected Widespread Regression:** Changes break existing untouched tests -> Stop immediately; do not patch test expectations to force green.
- **Environment Blocked:** Crucial runtime services cannot start or local configuration is corrupt -> Escalate to user or orchestrator for environment remediation.

---

## 8. Handoff

Upon meeting exit criteria:

- **If Envelope Status is "pass":** Hand off verification evidence report to parent orchestrator for final delivery or user sign-off.
- **If Envelope Status is "fail":** Hand off structured check failure evidence (including command, exit code, and exact stderr) to `daw-debug` or `daw-build`.
- **If Envelope Status is "blocked":** Return blocked status with unexercised dependencies and missing environment preflights to orchestrator.
- Do not perform recursive invocations or silent self-healing.
