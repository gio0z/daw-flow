---
name: daw-debug
description: "Systematic hypothesis-driven root cause analysis and bug diagnosis: builds a hypothesis ledger, conducts single-variable falsification experiments, distinguishes causal roots from surface symptoms, respects user-reported failures as ground truth without re-running checks to verify them, and halts thrashing to replan."
compatibility: "Fully self-contained procedural skill; no external dependencies required."
---

# DAW Debug: Systematic Hypothesis-Driven Diagnosis

Structured root-cause diagnosis isolating causal mechanisms from surface symptoms through falsifiable hypotheses and bounded experiments.

---

## 1. Trigger & When to Use

Invoke `daw-debug` when:

- Investigating runtime failures, crashes, unhandled exceptions, or test regressions.
- Analyzing incorrect behavioral output, silent data corruption, or inconsistent state transitions.
- Investigating performance degradations, timeouts, deadlocks, or resource leaks.
- Diagnosing user-reported errors or production incidents where the causal mechanism is unknown.

**Do NOT use `daw-debug` for:**

- Routine feature implementation where no regression has occurred (use `daw-build`).
- Code style reviews, static lint audits, or security policy reviews (use `daw-review`).
- Greenfield architecture design or high-level requirements exploration (use `daw-design` or `daw-ask`).

---

## 2. Inputs & Prerequisites

Before initiating systematic debugging, collect or establish:

1. **Failure Observation / Incident Description:** The exact error text, stack trace, exit code, observed vs. expected behavior, and reproduction context.
2. **Ground Truth Baseline:**
   - **User-Reported Errors Are Ground Truth:** If a user or CI output reports a concrete failure, stack trace, or error message, never rerun checks merely to confirm that the failure occurred. Treat reported output as ground truth.
   - **Targeted Reproduction Experiments:** While rerunning checks just to confirm an already-reported failure is prohibited, running a new, targeted reproduction script or isolated test to isolate a specific causal hypothesis or capture diagnostic traces is permitted.
3. **Target System Snapshot:** Current workspace path, commit SHA or revision, and affected component paths.
4. **Boundary Constraints:** Allowed inspection commands (read-only logs, non-destructive test execution, isolated reproduction scripts).
5. **Relative Reference Base & Canonical Path Resolution:**
   - When loaded via symlink or alias (e.g. `~/.agents/skills/daw-debug`), resolve THIS `SKILL.md` symlink to its physical/canonical target file first.
   - The suite root is the canonical module directory's `../..`.
   - Resolve all relative links (`../../references/...`, `../../SKILL.md`) relative to the canonical physical module directory, NEVER relative to the logical alias path or `cwd`.
   - Use the host environment's resolved path; when shell `realpath` is unavailable, use the host file system's native target resolution. If the target cannot be resolved, report a blocked dependency rather than scanning parent or unrelated directories.

6. **Mandatory Governance Loading:**
   - Before executing any phase work, load root governance (`../../SKILL.md` §4 Safety & §6 Handoff Contract Schema) and canonical routing (`../../references/routing.md` §5 & §6). Reading governance documentation is not recursive router execution.
   - Before running any state-changing reproduction command, script, or environment action, load `../../references/operations.md` §1 Preflight Safety & §2 High-Risk Approvals.
   - Unknown risk, ambiguous target/scope, or missing required high-risk interactive approval/preflight must immediately transition to `blocked` before executing commands. Read-only diagnostic reads require no production credentials.
   - When a corrected artifact is re-diagnosed on a retained same-role worker, reread the current sources and reproduce against the current revision; an earlier diagnosis is not evidence for it. The existing anti-thrashing threshold (two consecutive falsified hypotheses) and stop/replan rules still bound retries. Follow the [persistent worker graph contract](../../references/operations.md#persistent-worker-graphs-harness-native).

---

## 3. Step-by-Step Procedure

### Step 1: Establish Problem Statement & Failure Boundary

- Record the exact failure signature: error name, message, stack trace frames, and failing component.
- Identify the scope boundary: input arguments, environment variables, external services, database state, and configuration.
- Determine whether an isolated reproduction vector (unit test, minimal fixture, CLI invocation) can isolate the variable under test.

### Step 2: Initialize Hypothesis Ledger

Construct an explicit hypothesis ledger before testing or inspecting source code deeply. Each ledger entry must be mutually distinct and falsifiable:

| ID  | Candidate Cause            | Mechanism / Theory                                       | Falsification Test                             | Status (`Open` / `Falsified` / `Confirmed`) | Evidence / Observation |
| --- | -------------------------- | -------------------------------------------------------- | ---------------------------------------------- | ------------------------------------------- | ---------------------- |
| H1  | Null/Undefined reference   | Optional field omitted in payload causing unpack failure | Pass explicit payload fixture with null field  | Open                                        | Awaiting test          |
| H2  | Concurrency race condition | Shared cache accessed without mutex under async load     | Execute serial reproduction vs concurrent test | Open                                        | Awaiting test          |
| H3  | Upstream contract breach   | Third-party parser returning unexpected shape            | Inspect raw wire payload at boundary           | Open                                        | Awaiting test          |

### Step 3: Single-Variable Isolation & Falsification

- **One Variable Experiment:** Change or test exactly one variable per experiment. If reproduction requires modifying code, environment, or configuration, modify one factor at a time.
- Execute the falsification test:
  - If the test disproves the mechanism, mark the hypothesis `Falsified` and document the exact observation.
  - If the test confirms the mechanism, isolate whether it is the **causal root** or merely an **intermediate symptom**.
- **Prefer Runtime Inspection When Available:** When the hypothesis turns on live process state, and the runtime exposes a native debugger capability, discover the actual capability name and schema from exposed harness tools/documentation — never assume or invent a specific client, command, or wire shape. Use bounded breakpoints, stack/backtrace reads, and targeted value inspection to falsify the hypothesis directly, in preference to adding log instrumentation, when the session is authorized and in scope.
  - No automatic attach to production or shared processes; run only an authorized, isolated, non-destructive local reproduction target. Avoid side effects and sensitive values (secrets, credentials, PII, full payloads) in inspected state. Obey actual tool schema, host policy, and existing read-only/action bounds; low-risk local inspection needs no new approval, but missing required authorization blocks debugger use.
  - Logging/tracing remain a valid fallback when the debugger is unavailable or inappropriate. Record only state actually observed and tie each observation to its hypothesis; an unavailable/unauthorized debugger is `unexercised`, never a fabricated debugger session or invented stack/value.
- **Distinguish Root Cause vs. Surface Symptom:**
  - _Symptom:_ `TypeError: Cannot read property 'id' of undefined` at line 142.
  - _Symptom Patch (FORBIDDEN):_ Adding optional chaining `user?.id` or `if (!user) return;` without understanding why `user` is undefined.
  - _Causal Root:_ User session lookup failed to deserialize JWT payload after schema migration because claim name changed from `sub` to `userId`.

### Step 4: Halt Thrashing & Replan Gate

- **Anti-Thrashing Rule:** If two consecutive hypotheses are falsified without narrowing the boundary, or if attempts to reproduce the issue yield contradictory results:
  1. Stop speculative testing immediately.
  2. Re-examine assumptions: verify whether environment, dependencies, dirty working tree state, or configuration drift are masking the issue.
  3. Expand appropriate observations — bounded debugger breakpoints/stack/value inspection when available and authorized, otherwise logging or tracing — at the outermost subsystem boundary rather than guessing deeper internal states.
  4. Escalate open design/infrastructure unknowns to the parent orchestrator via the Stop/Replan protocol.

### Step 5: Formulate Root Cause Dossier & Remediation Strategy

- Once a hypothesis is `Confirmed` with concrete falsification proof:
  - Detail the causal chain from triggering input to terminal failure.
  - Specify the required remediation contract (behavioral invariant to restore).
  - Define the regression test case required to prove the fix and prevent future regressions.

---

## 4. Output Contract

Every completion of `daw-debug` delivers a structured handoff payload adhering to the canonical suite envelope as an internal module-to-orchestrator handoff. Full canonical JSON MUST be delivered and inspectable before downstream stage transition per [User-Facing Reports & Handoff Transport](../../references/routing.md#user-facing-reports--handoff-transport) (via structured tool/subagent return, authorized artifact, or an explicit inline checkpoint fallback). Direct-user responses default to concise natural language. Rich diagnostic findings, hypothesis ledger, and root-cause analysis are preserved under `details`:

```json
{
  "objective": "Diagnose root cause of session KeyError on token refresh.",
  "input_paths": ["src/auth/session.py", "src/auth/serializer.py"],
  "output_paths": [],
  "acceptance_criteria": [
    {
      "criterion": "Causal mechanism distinguished from surface symptom with falsification evidence",
      "status": "pass"
    },
    {
      "criterion": "Targeted regression test case specified for remediation",
      "status": "pass"
    }
  ],
  "evidence": [
    {
      "reference": "tests/auth/test_token_refresh.py",
      "summary": "Isolated test execution confirmed KeyError at session.py:84 caused by missing token_version"
    }
  ],
  "status": "pass",
  "handoff_to": "daw-plan",
  "details": {
    "problem_summary": "Authentication token validation fails silently on valid refreshed tokens",
    "reproduction_command": "pytest tests/auth/test_token_refresh.py -k test_refresh_token_rotation",
    "failing_signature": {
      "error_type": "KeyError",
      "message": "'token_version' missing from session dict",
      "source_location": "src/auth/session.py:84"
    },
    "hypothesis_ledger": [
      {
        "id": "H1",
        "cause": "Session serializer dropped token_version during serialization",
        "test": "Unit test session serializer round-trip",
        "status": "CONFIRMED",
        "evidence": "SessionSerializer.to_dict() omitted token_version field in commit 3b1a2f"
      },
      {
        "id": "H2",
        "cause": "Database migration failed to backfill column default",
        "test": "Query database schema directly",
        "status": "FALSIFIED",
        "evidence": "Database column has default value 1 and all rows populated"
      }
    ],
    "root_cause": {
      "mechanism": "Commit 3b1a2f refactored SessionSerializer to use explicit field mapping but omitted token_version from the export list, causing deserialization on subsequent requests to throw KeyError.",
      "symptom_vs_root_distinction": "Catching KeyError in session.py:84 would have defaulted to guest mode, silently masking broken sessions. The root fix requires restoring token_version in SessionSerializer."
    },
    "remediation_contract": {
      "invariant": "SessionSerializer must round-trip all required session tokens without loss.",
      "target_files": ["src/auth/serializer.py"],
      "recommended_regression_test": "tests/auth/test_session_serializer.py::test_session_serialization_token_version_roundtrip"
    },
    "open_questions": []
  }
}
```

_(Note: `status: "pass"` indicates that the diagnostic phase criteria have been satisfied; it does not indicate bug fix implementation or resolution)._

## 6. Stop / Replan Protocols

Immediately halt debugging and return control to the parent orchestrator if:

- **Contradictory Ground Truth:** Observed runtime facts directly contradict user-provided environmental guarantees.
- **Destructive Mutation Required:** Reproduction or investigation would require destructive changes to production data, credentials, or untracked repository changes.
- **Deep Thrashing Threshold Reached:** Two consecutive hypotheses falsified without narrowing the boundary (see Step 4 Anti-Thrashing), indicating incorrect boundary assumptions or unobserved external state.

---

## 7. Handoff

Upon exit:

- If causal root is confirmed: Hand off the Diagnostic Report to the orchestrator for dispatch to `daw-build` (for test-driven remediation) or `daw-plan` (if the fix requires an architectural contract change).
- If blocked or replanning: Hand off the active Hypothesis Ledger, observed falsifications, and specific boundary questions to the parent orchestrator.
- References:
  - Root contract: `../../SKILL.md`
  - Specifications and routing: `../../references/routing.md`
