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
- Performing regression bisection when a known-good revision exists: narrow the introducing commit between last-good and first-bad, then hand the culprit commit to `daw-plan`/`daw-build` (see [Regression Bisection Protocol](../../references/developer-lifecycle.md#6-regression-bisection-protocol)).
- Analyzing incorrect behavioral output, silent data corruption, or inconsistent state transitions.
- Investigating performance degradations, timeouts, deadlocks, or resource leaks.
- Diagnosing user-reported errors or production incidents where the causal mechanism is unknown.
- Working under a declared time-box budget per [Time-Boxing & Escalation Budgets](../../references/developer-lifecycle.md#2-time-boxing--escalation-budgets).

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

### Step 2A: Regression Bisection (known-good revision exists)

When the failure is a regression and a last-known-good revision is available:

1. Confirm the failure reproduces at the first-bad revision and passes at the last-good revision (do not rerun user-reported failures solely to confirm them; use a targeted reproduction script per §2).
2. Bisect: `git bisect start <first-bad> <last-good>` (or `git bisect run <narrowest failing check>` for an automated verdict), alternating until one commit remains; record each verdict against the hypothesis ledger.
3. `git bisect reset` when done; report the single culprit commit with its diff and the changed contract (what the commit altered) as the confirmed mechanism input.
4. Work inside the time-box budget for this step; on expiry stop mid-bisection, record the current `git bisect` state and narrowed range, and escalate to the parent instead of guessing.
5. Bisect verdicts count toward the 3-hypothesis per-symptom budget in Step 4; at the cap, stop and escalate with the narrowed range.

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

- **Anti-Thrashing Rule (time-box budget):** Per [Time-Boxing & Escalation Budgets](../../references/developer-lifecycle.md#2-time-boxing--escalation-budgets): two consecutive falsified hypotheses without narrowing the boundary triggers an early stop and replan below; the hard cap is 3 distinct hypotheses per symptom total — at the cap, stop and escalate to the parent rather than testing a fourth. Contradictory reproduction results also trigger the stop:
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

Use [routing §5: Canonical Module Handoff Contract](../../references/routing.md#5-canonical-module-handoff-contract) for the complete outer JSON schema and transport. Deliver the actual, inspectable envelope to the parent before downstream transition; concise direct-human diagnostic reports do not replace that handoff. Do not dump envelopes into normal user replies or create unrequested transport files.

### Diagnostic Details Contract

Preserve under `details`:

- `problem_summary`, `reproduction_command`, and `failing_signature` (`error_type`, `message`, `source_location`): the exact failure boundary. Distinguish user-provided failure evidence from new hypothesis-isolation experiments; an unrun command is a proposal, not execution evidence.
- `hypothesis_ledger`: distinct candidates with `id`, `cause`, `test`, `status`, and `evidence`; retain falsified hypotheses and exact observations, not only the winning theory.
- `root_cause`: confirmed `mechanism` and `symptom_vs_root_distinction`; if unconfirmed, state that explicitly without presenting a hypothesis as fact.
- `remediation_contract`: the `invariant` to restore, `target_files`, and `recommended_regression_test`, not an implemented fix claim.
- `open_questions`: remaining boundary questions or missing prerequisites, including observed contradictions and anti-thrashing reasons when stopping/replanning.

Compact hypothetical `details` (not a complete handoff):

```json
{
  "problem_summary": "Refreshed sessions lose token_version during serialization.",
  "reproduction_command": "pytest tests/auth/test_session_serializer.py -k roundtrip",
  "failing_signature": {
    "error_type": "KeyError",
    "message": "'token_version'",
    "source_location": "src/auth/session.py:84"
  },
  "hypothesis_ledger": [
    {
      "id": "H1",
      "cause": "Serializer omits token_version",
      "test": "Round-trip a session with token_version set",
      "status": "Confirmed",
      "evidence": "Isolated round-trip output lacks token_version"
    },
    {
      "id": "H2",
      "cause": "Migration omitted the default",
      "test": "Inspect schema and affected row",
      "status": "Falsified",
      "evidence": "Inspected column and affected row both contain token_version=1"
    }
  ],
  "root_cause": {
    "mechanism": "Explicit serializer field mapping omits token_version, causing later deserialization to raise KeyError.",
    "symptom_vs_root_distinction": "Catching KeyError would mask lost session data; restore the serializer field instead."
  },
  "remediation_contract": {
    "invariant": "Session serialization round-trips every required field.",
    "target_files": ["src/auth/serializer.py"],
    "recommended_regression_test": "tests/auth/test_session_serializer.py::test_token_version_roundtrip"
  },
  "open_questions": []
}
```

`status: "pass"` proposes satisfaction of diagnostic-stage criteria only, not bug-fix implementation, resolution, parent acceptance, or runtime correctness. Select advisory `handoff_to` from the active route under §7 — on the canonical `bugfix` route, `daw-plan` (never skip directly to `daw-build`); on `status: "fail"` or `"blocked"`, return `handoff_to: null` and the active ledger and boundary questions to the parent. The handoff is advisory metadata for the parent orchestrator, and `daw-debug` never invokes another module directly.

## 6. Stop / Replan Protocols

Immediately halt debugging and return control to the parent orchestrator if:

- **Contradictory Ground Truth:** Observed runtime facts directly contradict user-provided environmental guarantees.
- **Destructive Mutation Required:** Reproduction or investigation would require destructive changes to production data, credentials, or untracked repository changes.
- **Deep Thrashing Threshold Reached:** Two consecutive hypotheses falsified without narrowing the boundary (see Step 4 Anti-Thrashing), indicating incorrect boundary assumptions or unobserved external state.

---

## 7. Handoff

Upon exit, return the Diagnostic Handoff to the parent orchestrator with advisory `handoff_to` selected from the active route only per §4; the parent exclusively decides dispatch and `daw-debug` never invokes another module directly.

- If causal root is confirmed (`status: "pass"`): recommend `handoff_to: "daw-plan"` — the next stage on the canonical `bugfix` route (`daw-debug` -> `daw-plan` -> `daw-build` -> `daw-review` -> `daw-verify`); never skip directly to `daw-build`.
- If blocked or replanning (`status: "blocked"` / `"fail"`): return `handoff_to: null` and hand off the active Hypothesis Ledger, observed falsifications, and specific boundary questions to the parent orchestrator; a halted debug stage never advances the pipeline.
- **Post-release feedback / incident intake (when diagnosing a deployed-release failure):** Surface the closure inputs for the parent's intake record per `references/operations.md#post-release-feedback--incident-closure`: affected release/artifact digest, source and evidence reference, observed impact, and a proposed classification (bug vs. operational incident). Report the classification as a proposal only — the parent owns the disposition, owner, and closure. A locally confirmed root cause is diagnostic evidence only and MUST be recorded as local proof, never as production resolution; no remediation claim may assert production recovery without deployed post-release evidence observed by the parent. `daw-debug` starts no automatic publish or monitoring; operations maintenance remains opt-in.
- References:
  - Root contract: `../../SKILL.md`
  - Specifications and routing: `../../references/routing.md`
