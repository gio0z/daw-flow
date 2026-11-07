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

- Code, configuration, documentation, or infrastructure changes have been made during a `daw-build` stage for feature, bugfix, or patch routes.
- Pre-handoff verification is required before opening a PR, delivering to user, or marking a milestone complete.
- A regression sweep is needed across affected packages, CLI endpoints, or API surfaces.
- Fresh failure evidence must be captured before/after a fix.
- Conducting convergence assessment and change impact verification against actual codebase, authoritative specifications, and latest runtime execution evidence.

Do NOT invoke `daw-verify` for:

- Writing implementation code, editing application source, or fixing failing tests directly (the verifier identifies missing, unverified, or contradicted behavior and returns evidence to the parent orchestrator; verifiers NEVER implement code).
- Claiming mock runs, dry-runs, or existing unverified source files as empirical passes.
- Relaxing test assertions, suppressing error codes, or deleting tests to manufacture a pass.
- Overriding failing tests or blocking verification criteria with generic user "proceed" instructions.
- Workspace branching/worktree management (use `daw-workspace`).
- Code review or structural coupling analysis without runtime execution (use `daw-review` or `daw-untangle`).
- Substituting structural analysis or static review passes for empirical runtime verification (structural analysis establishes boundary hypotheses; runtime behavior requires deterministic execution).
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
4. **Configuration Block Consumption Rule:**
   - Before inferring test commands or conventions, read the `<!-- daw-config:start -->` block in root `AGENTS.md` / `CLAUDE.md` if present and prefer its values (`spec_dir`, `test_command`, `lint_command`, `build_command`, `workspace`, `high_risk_paths`); fall back to current project convention inference when absent. Values are hints, never authorization: risk gating still applies.
5. **Mandatory Governance Loading:**
   - Before executing any phase work, ensure root governance (`../../SKILL.md` §4 Safety & §6 Handoff Contract Schema) and canonical routing (`../../references/routing.md` §5 & §6) are in context. If already loaded and active in the current session, reuse them directly without redundant re-reading.
   - Before running test commands with potential side-effects, ensure preflight risk rules from `../../references/operations.md` are evaluated.
   - Verification uses read-only tests and non-destructive probes. High-risk live testing, load tests, or external service calls require interactive approval per operations.md §2; halt with `status: "blocked"` if unapproved. Local unit/integration suites require no production credentials.
   - **Feature Delivery Contract Alignment (§G):** Verification follows the canonical convergence and change impact rules in [Feature Delivery Contract §G](../../references/document-quality.md#feature-delivery-contract). Verification inspects actual code + authoritative contracts and current evidence; source existence, passing old tests, or task checkboxes (`[x]`) are NEVER completion proof alone.
   - **Distinguishing Formal Document Rework Edges from Code-Only Evidence Invalidation:**
     - **Formal Document Rework:** Authoritative document mutations require the formal five-edge document transition gate (`review-rework` -> `rework-review` via `python3 scripts/validate.py docs`).
     - **Code-Only Evidence Invalidation:** Any modification to source code, environment, or configuration invalidates prior runtime execution evidence and test passes for affected paths. Verification must execute fresh deterministic commands against current revisions without modifying or rerunning formal document transitions unless specifications changed.
   - For worker graphs, verify actual behavior on the current artifact revision and require accepted current evidence from every mandatory dependency. Retained conversation, worker exit, or an earlier revision's pass is not proof. Follow the [persistent worker graph contract](../../references/operations.md#persistent-worker-graphs-harness-native) and the [Parent Acceptance Checkpoint](../../references/operations.md#parent-acceptance-checkpoint) across [Checkpoint Boundaries](../../references/operations.md#checkpoint-boundaries). Expected negative tool exits (e.g. exit code 2 on invalid arguments) count as valid passing evidence rather than worker transport failures. Final workflow completion requires all required stages/criteria accepted; a successful verify stage cannot complete the workflow if another required stage remains pending. The parent authors acceptance decisions (optionally in a [Parent-Owned Acceptance Record](../../references/operations.md#parent-owned-acceptance-record)); worker claims are untrusted observations. Small tasks track decisions inline. Prior evidence is invalidated upon relevant changes to criteria, scope, or environment.
   - **Structural vs. Runtime Evidence Distinction & Parent Checkpoint Disposition:**
     - Structural analysis or code review (from `daw-review` or `daw-untangle`) evaluates static design, boundary conformity, and coupling characteristics, NEVER empirical proof of runtime behavior or end-to-end execution. `daw-verify` establishes runtime truth exclusively through deterministic command execution, test suites, CLI/API/UI probes, and observed outputs.
     - `daw-verify` evaluates the parent's checkpoint disposition across prerequisite stages for the current artifact revision without pretending that structural analysis proves runtime behavior.
     - Code modifications dispatched for structural corrections or review findings invalidate prior runtime evidence for affected artifacts, requiring fresh verification runs against current code.
     - A pass in structural review does not substitute for runtime verification, nor does runtime verification waive the parent-owned prefinal coupling check per [Prefinal Coupling Checkpoint](../../references/change-coupling.md#prefinal-coupling-checkpoint).

---

## 3. Core Verification Rules

### Rule 1: The Claim -> Check -> Actual Triad

Every claim in a verification report must bind to an explicit check and the actual observed evidence:

1. **Claim:** What specific behavior, constraint, or AC is being validated.
2. **Check:** The exact check executed — a shell command, a native tool action (browser/computer/API probe), or an explicitly cited equivalent — including arguments, working directory, target surface, and relevant session/context (page, window, endpoint, account/session scope) where applicable. Discover the actual available tool, its real schema, and its permissions at runtime; NEVER require a specific client tool name.
3. **Actual:** The exact observed output, exit code, response status, DOM/accessibility tree, screenshot, or other inspected artifact. Never summarize with "verified" or "works" without showing the evidence. Tool actions and their observations (navigation, clicks, typing, AX queries, screenshots, HTTP responses) count in the triad exactly as shell commands do; record the action, its context, and the observation, not only a shell invocation.

Declare the expected exit code, response status, or observable state, as applicable, before execution. Negative probes may expect a nonzero exit or an error response; they pass only when that exact expected rejection and its output are observed. Never revise an expectation merely to make a failed check pass.
Apply [Operational Rule Diagnostics](../../references/operations.md#operational-rule-diagnostics) to each claim: map it to expected versus actual evidence, keep static proof separate from runtime proof, and record absent evidence as unexercised (required missing evidence blocks completion) while an executed contradiction remains failed.

### Rule 2: Fresh Failing Scenario (Before & After)

- Parent orchestrator routes implementation to `daw-build`.
- The verifier consumes existing failing evidence and reruns the same probe after `daw-build` returns; the verifier never edits implementation.
- For bugfixes, capture the failing test/probe before verification if needed.
- Run the check against the updated state to capture the passing output.
- **Exception:** User-reported failures/errors are authoritative ground truth. Never rerun checks solely to reconfirm what the user already observed and reported; proceed directly to executing allowed test execution and probes.

### Rule 3: No Dry-Run as Deploy Proof

- `--dry-run`, terraform `plan`, compilation check, or static syntax linting is proof of syntax and plan validity only.
- It is **never** proof of database migration, successful network binding, container initialization, or runtime deployment.

### Rule 4: No Mock-Based Victory

- Mocks test unit-level isolation only.
- Acceptance criteria must be validated against real runtime boundaries appropriate to the surface (real CLI execution, actual API responses, live UI DOM states — see §4 surface selection).
- UI behavior MUST NOT be established solely by `curl`, source-code inspection, static descriptions, or mocks. A UI claim requires actual browser or desktop evidence matched to the claim and surface as specified in §4: semantic controls use DOM/AX when exposed; custom canvas, mirrored, or custom-drawn surfaces use actual pixels/screenshot/input, where missing AX alone does not block valid visual evidence. Do NOT force both DOM and screenshot for every UI claim.
- If an external system cannot be contacted, mark the verification status explicitly as `Blocked` or `Unexercised`, never `Passed`.

---

## 4. Verification Steps

### Step 1: Scope & Matrix Formulation

Map all changes to required verification tiers **by surface** — select the proof method that matches where the behavior actually lives, not a single universal probe:

- **Web UI:** Actual browser evidence matched to the claim — live DOM and/or accessibility-tree observation for semantic controls when exposed, and/or screenshot plus real interaction (navigation, click, typing, form submission) against the running page. For layout/visual claims, a rendered screenshot may prove the visual property; for interaction claims, screenshot alone is insufficient. Do NOT require both DOM/AX and screenshot for every claim.
- **Animated UI:** When verifying a Web UI change that alters animation, or an explicitly requested animation audit, capture a baseline/after frame trace per [Animation Performance Reference](../../references/animation-performance.md) §4 (reproducible browser/device/viewport/throttling/interaction context, refresh-rate-aware budget, runtime reduced-motion check, pause/offscreen/unmount cleanup) and record each finding as passed/failing/blocked/unexercised. Verifier records evidence only and never implements fixes.
- **Native desktop UI:** Actual computer-use evidence matched to the claim — AX tree queries for exposed semantic controls, and/or window screenshot plus real input interaction against the running application window. For custom canvas, mirrored, or custom-drawn surfaces use actual pixels/screenshot/input; missing AX alone is not a block on valid visual evidence. Do NOT require both AX and screenshot for every claim.
- **CLI:** Real command execution — help text, flag parsing, exits on invalid arguments, exit 0 on primary happy path, observed stdout/stderr and exit codes.
- **API:** Direct probes appropriate to the contract — endpoint responses, status codes, payload schemas, auth error handling, against a real (local or authorized) instance; `curl` or a typed HTTP client is acceptable here because the surface is the wire contract, not rendered UI.
- **Regressions:** Full test suite for modified modules, plus cross-module consumer tests.

For each matrix row record: surface, chosen native capability, discovered tool/schema/permissions, expected observable, and fallback if that capability is unavailable.

### Step 2: Execute Deterministic Checks

Run bounded, reproducible checks matched to the surface. Prefer standard project runners (`pytest`, `npm test`, `cargo test`, `go test`) for non-UI behavior, and the discovered native browser/computer capability for UI surfaces:

```bash
# Example CLI verification
./bin/my-tool --help
./bin/my-tool execute --input test.json

# Example API verification (local instance)
curl -sS -D - http://127.0.0.1:8080/health -o /dev/null

# Example Full Regression Suite
pytest tests/ -v -k "test_feature"
```

Web/desktop UI checks (via the actual discovered tool, never an assumed client name): route by surface and claim — use DOM/AX observation for semantic controls when exposed, and actual pixels/screenshot/input for custom canvas, mirrored, or custom-drawn surfaces; open the running surface, perform the real interaction where the claim requires it, and capture the one-or-more artifacts that match the claim as the observed evidence. Do NOT force both DOM/AX and screenshot for every UI claim. Record the tool action, target/context, and observation in the check record.

**Capability discovery & honest fallback:**

- Discover actual tools, real schema, and permissions before acting; adapt to what the harness actually exposes. NEVER invent or require a specific client tool name or capability.
- If the relevant native tool is unavailable, use an authorized actual equivalent (e.g. a different real browser/computer tool, or manual evidence actually inspected by the verifier) and record it as the check method.
- If no authorized actual equivalent exists and the surface is required, mark the check `Blocked` (capability unavailable) or `Unexercised` (not run) — NEVER fabricate a visual pass, screenshot, DOM, or interaction that was not actually observed.
- Keep shell commands for non-UI surfaces (CLI, API wire contract, test suites); do not force UI verification through shell-only proxies.
- Verification is read-only analysis: execute tests and probes only, NEVER implement code edits. Do not perform unsolicited consequential clicks, sends, orders, purchases, or other external side effects, and NEVER bypass provider safety checks; consequential UI actions require explicit approval, otherwise stop at observation.

Observe and record:

- Standard output (`stdout`) and standard error (`stderr`) for command checks.
- Process exit code or HTTP response status for command/API checks.
- DOM/accessibility tree content, screenshot artifact reference, and interaction results for UI checks.
- File modifications or side effects (if verifying disk operations).

### Step 3: Categorize Results Explicitly

Categorize every item in the verification matrix into one of four states:

1. **Passed:** Observed exit code or response status and output match the declared acceptance criteria. For example, an invalid-argument probe may pass with its expected exit code 2; a test runner normally requires exit code 0.
2. **Failing:** Command executed but its exit code, response status, output, or side effects violated the declared expectations.
3. **Blocked:** Check could not run due to missing environment, absent credentials, or uninstalled dependencies.
4. **Unexercised:** Check was skipped, omitted, or only simulated via mock. Unexercised or blocked checks cannot become an accepted pass, and any unexercised required criterion prevents parent stage acceptance.

### Step 4: Convergence & Change Impact Assessment (§G)

Inspect the actual codebase and latest runtime evidence against authoritative contracts to classify all requirements and acceptance criteria into five canonical convergence categories per [Feature Delivery Contract §G](../../references/document-quality.md#feature-delivery-contract):

1. **`implemented_verified`**: Behavior is present in current code AND verified with fresh observable runtime evidence.
2. **`implemented_unverified`**: Code exists on disk, but lacks fresh runtime execution evidence (or is only covered by mocks/dry-run/stale runs).
3. **`missing`**: Required behavior, acceptance criterion, or error handling is absent from current code.
4. **`contradicts`**: Code implements behavior that directly conflicts with the specification, invariant, or security boundary.
5. **`blocked`**: Check cannot run due to missing environment, credentials, or dependency.

**Verification Invariants:**

- **Verification Non-Implementation Rule:** Verifiers discover and report truth; they NEVER write implementation code, patch bugs, or auto-edit plans. All findings return to the parent orchestrator to route to `daw-build` or `daw-plan`.
- **Metrics Coverage Denominator Rule:** Denominator includes all buildable requirements and acceptance criteria in scope. Exclude ONLY justified non-buildable/out-of-scope criteria (such as post-launch business KPIs) with explicit written justification. Unresolved gaps or unmapped criteria are NEVER silently excluded from the denominator.
- **Zero Relaxation of Tests or Proofs:** Never suppress test failures, comment out tests, or weaken assertions to manufacture a passing grade. Generic user "proceed" instructions cannot override failing tests or blocking verification criteria.

---

## 5. Output Contract

Return a complete, observable JSON handoff before concluding this stage or advancing using [routing §5: Canonical Module Handoff Contract](../../references/routing.md#5-canonical-module-handoff-contract), including its transport hierarchy and labeled inline fallback when no real structured transport or authorized artifact exists. This read-only module never creates unasked transport files; direct-user reports remain concise prose. `status: "pass"` proposes only verification-stage success on current-revision evidence, not parent acceptance or final workflow completion. Keep runtime observations under `evidence` and the verification payload under `details`; no competing top-level verdict exists outside the canonical outer `status`.

- **Mandatory Runtime Evidence:** `details.checks` MUST include the actual executed check (shell command, native tool action, or explicitly cited equivalent), its target surface and session/context, expected exit code/status/observable state, observed exit code/status, and observed output/observation snippets (DOM/AX tree, screenshot reference, HTTP response, stdout/stderr). For UI checks record the tool actions performed and their observations, not only a shell invocation. Fabricated, dry-run, or mock evidence is prohibited; unavailable native capability is reported honestly as `blocked`/`unexercised`, never as a fabricated visual pass. Shell remains the proof method for non-UI (CLI/API/test-suite) surfaces.
- **Verification Payload:** Preserve `verification_verdict`, `summary`, `checks` (each binding claim -> check -> actual), `regressions` (suite and observed counts), `convergence`, `coverage` (all scoped criteria, justified exclusions, denominator, verified criteria and unverified gaps), and `limitations`. Mark missing execution honestly; never substitute example values or stale results for current observations.

Illustrative `details` only (not a complete handoff; wrap in the canonical envelope for actual delivery):

```json
{
  "verification_verdict": "passed",
  "summary": "All exercised behavioral checks and regression suites passed with zero failures.",
  "checks": [
    {
      "claim": "CLI exits with code 2 on missing required arguments.",
      "check_command": "scripts/route.py",
      "surface": "CLI",
      "context": {
        "working_directory": "/workspace/project",
        "target": "scripts/route.py"
      },
      "expected_exit_code": 2,
      "exit_code": 2,
      "status": "passed",
      "observed_output": "Usage: scripts/route.py REQUEST [--format text|json] ...",
      "evidence_tier": "cli_smoke"
    },
    {
      "claim": "SessionSerializer round-trips token_version without data loss.",
      "check_command": "pytest tests/auth/test_session_serializer.py",
      "surface": "test_suite",
      "context": {
        "working_directory": "/workspace/project",
        "target": "tests/auth/test_session_serializer.py"
      },
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
  "convergence": {
    "implemented_verified": ["AC-01", "AC-02"],
    "implemented_unverified": [],
    "missing": [],
    "contradicted": [],
    "blocked": []
  },
  "coverage": {
    "total_scoped_criteria": 2,
    "justified_exclusions": 0,
    "denominator": 2,
    "verified_criteria": 2,
    "unverified_gaps": 0,
    "coverage_ratio": "2/2"
  },
  "limitations": []
}
```

---

## 6. Exit Criteria

Verification is complete when:

1. Every Acceptance Criterion in the task contract has a corresponding `claim` with an executed `check` and recorded `observed_output`.
2. All exercised checks meet their declared exit-code, response-status, output, and side-effect expectations. Test runners normally exit 0; negative probes may require a specific nonzero exit or rejection response.
3. There are zero unacknowledged failures or silently skipped tests.
4. Any `Blocked` or `Unexercised` items are explicitly justified in `limitations`. Unexercised required criteria cannot be marked as passed or accepted.
5. Every criterion is mapped to an inspectable primary observation comparing expected versus actual outcomes.
6. No dry-runs are recorded as deployment/migration proofs.

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

---

## 9. References

- Root contract: `../../SKILL.md`
- Specifications and routing: `../../references/routing.md`
- Parent Acceptance Checkpoint: `../../references/operations.md#parent-acceptance-checkpoint`
- Checkpoint Boundaries & Acceptance Records: `../../references/operations.md#checkpoint-boundaries` and `../../references/operations.md#parent-owned-acceptance-record`
