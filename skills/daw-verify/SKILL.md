---
name: daw-verify
description: "Use to verify implementation changes against explicit claims, acceptance criteria, and observable runtime evidence. Enforces claim-check-actual observation of latest outputs, meaningful smoke tests (CLI, API, UI), role-based surface sessions on the real running product at phone and desktop widths before any UI pass, full relevant regression suites, fresh failure scenarios before/after without rerunning user-reported errors solely to confirm, and zero tolerance for mock-based claims or dry-run-as-deploy proofs."
compatibility: "POSIX shell, CLI/API/UI test frameworks, Python 3.10+; fully self-contained markdown procedure."
---

# DAW Verify (Deterministic Semantic & Runtime Verification)

Axiom: **"Otaknya boleh generative, tangannya harus deterministic."**
Generative reasoning designs test matrices and diagnoses failures; truth comes strictly from deterministic commands, runtime probes, and observed outputs.

> **Verification Contract:**
>
> - Passing unit tests or green mocks are **never** end-to-end proof.
> - Dry-runs (`--dry-run`, plan mode, mock deploy) are **never** proof of migration, build, or deploy.
> - User-reported failures are authoritative ground truth: **NEVER** rerun a check solely to confirm what the user already reported.
> - Distinguish strictly: **Passed**, **Failing**, **Blocked** (missing dep/env), and **Unexercised** (skipped or mock-only).

---

## 1. Trigger

Invoke `daw-verify` when:
- Code, config, docs, or infra changed during `daw-build` (`feature`, `bugfix`, `patch`, `refactor`, `maintain`).
- Proving refactor equivalence (identical suite + characterization probes before/after; see [Behavior-Preserving Refactor Protocol](../../references/developer-lifecycle.md#4-behavior-preserving-refactor-protocol)) or dependency upgrades (full regression + build + lockfile diff; see [Dependency & Maintenance Upgrade Protocol](../../references/developer-lifecycle.md#5-dependency--maintenance-upgrade-protocol)).
- Pre-handoff verification, regression sweeps across affected surfaces, or fresh before/after failure evidence is required.
- A UI-affecting change needs a Rule 8 role-based surface session (write leg, read-back leg, non-staff surface if present, phone/desktop viewports on layout changes).
- Assessing convergence (§G) or assembling `details.pre_ship_evidence` for `daw-ship`.

Do NOT invoke `daw-verify` to:
- Edit implementation/tests directly (return evidence to parent; verifiers NEVER implement code).
- Claim mocks, dry-runs, or unverified source files as passes; relax assertions, suppress errors, or delete tests; override failures with generic "proceed".
- Manage worktrees (`daw-workspace`), run static review/coupling analysis without runtime execution (`daw-review` / `daw-untangle`), or author design/plans (`daw-design` / `daw-plan`).

---

## 2. Inputs & Prerequisites

1. **Change Manifest / Task Contract:** Modified files, target scope, and exact AC (`../../references/task-contract.example.json` or saved plan).
2. **Saved Spec + Plan + Current Phase (multi-step):** Read saved proportional spec, saved plan, and parent-owned progress record (active phase/subphase, current scoped revision) per Workflow Artifacts §1–§4. Verifier inspects and proposes only — never writes progress, triage queue, mocks, or evidence. Tiny patches and read-only inquiries keep the zero-doc path. For UI-affecting work, confirm the rendered mockup passed parent acceptance before UI build (mockup acceptance != runtime UI proof).
3. **Execution Environment & Ground Truth:** Accessible runtime/CLI/test services plus user-reported errors/repro steps.
4. **Canonical Path Resolution:** Resolve THIS `SKILL.md` symlink to its physical target (`../..` = suite root; halt `blocked` if unresolvable, never scan parent dirs). Resolve all relative links (`../../references/...`, `../../SKILL.md`) from the physical module directory.
5. **Configuration Block Consumption:** Prefer values from `<!-- daw-config:start -->` in `AGENTS.md`/`CLAUDE.md` (`spec_dir`, `test_command`, `lint_command`, `build_command`, `workspace`, `high_risk_paths`) before inferring conventions (hints only; risk gating applies).
6. **Mandatory Governance & Evidence Rules:**
   - Reuse session-loaded root governance (`../../SKILL.md` §4/§6) and routing (`../../references/routing.md` §5/§6); evaluate `../../references/operations.md` preflight/risk rules before side-effecting checks. High-risk live/load/external probes require interactive approval per `operations.md` §2 (else `status: "blocked"`); local suites need no prod credentials.
   - **Convergence & Document vs Code Invalidation (§G):** Follow [Feature Delivery Contract §G](../../references/document-quality.md#feature-delivery-contract) (code + contracts + fresh evidence; source files, stale tests, or `[x]` checkboxes != proof). Formal spec edits require the 5-edge transition gate (`review-rework` -> `rework-review` via `python3 scripts/validate.py docs`); code/config/env edits invalidate prior runtime evidence for affected paths and require fresh runs against current revisions without rerunning doc transitions.
   - **Worker Graphs & Parent Checkpoint:** Verify current artifact revision with accepted evidence from every mandatory dependency (retained conversation, worker exit, or stale passes != proof) per [persistent worker graph contract](../../references/operations.md#persistent-worker-graphs-harness-native), [Parent Acceptance Checkpoint](../../references/operations.md#parent-acceptance-checkpoint), [Checkpoint Boundaries](../../references/operations.md#checkpoint-boundaries), and optional [Parent-Owned Acceptance Record](../../references/operations.md#parent-owned-acceptance-record). Expected negative exits (e.g. exit 2 on invalid args) count as passing evidence. Final completion requires all required stages/criteria accepted by the parent (worker claims are untrusted observations; small tasks track inline).
   - **Finding Output Contract:** Return prioritized, evidence-backed, actionable findings (with impact/urgency and dependencies) or an explicit no-actionable-finding statement with scoped N/A/proof. Report already-implemented work as an integration candidate plus needed verification, never a fake `needs-fix`. Parent holds [Ranked Result Triage](../../references/operations.md#ranked-result-triage); verifier never self-approves or deploys.
   - **Structural vs Runtime Evidence:** Static review/coupling (`daw-review`/`daw-untangle`) never substitutes for runtime proof, and runtime verify never waives the parent-owned [Prefinal Coupling Checkpoint](../../references/change-coupling.md#prefinal-coupling-checkpoint).

---

## 3. Core Verification Rules

### Rule 1: The Claim -> Check -> Actual Triad

Bind every report claim to an executed check and observed evidence:
1. **Claim:** Specific behavior, constraint, or AC being validated.
2. **Check:** Exact executed shell command, native tool action (browser/computer/API probe), or cited equivalent, with arguments, cwd, target surface, and session/context. Discover actual available tools/schemas/permissions at runtime; NEVER require a specific client tool name.
3. **Actual:** Exact observed output, exit code, HTTP status, DOM/AX tree, screenshot, or artifact — never `"verified"`/`"works"` alone.

Declare expected exit code/status/state before execution (negative probes pass only on the exact expected rejection; never revise expectations after failure). Apply [Operational Rule Diagnostics](../../references/operations.md#operational-rule-diagnostics): separate static vs runtime proof; mark missing evidence `unexercised` (blocking if required) and executed contradictions `failed`.

### Rule 2: Fresh Failing Scenario (Before & After)

- Parent routes fixes to `daw-build`; verifier consumes failing evidence and reruns the same probe after build (never edits code).
- Capture before/after failing-then-passing probes for bugfixes.
- **Exception:** Never rerun a check solely to reconfirm a user-reported failure.

### Rule 3: No Dry-Run as Deploy Proof

`--dry-run`, terraform `plan`, compilation, or static linting proves syntax/plan validity only — **never** DB migration, network binding, container startup, or deploy.

### Rule 4: No Mock-Based Victory

- Mocks prove unit isolation only. Validate AC against real runtime boundaries per §4 (CLI, API, live UI).
- UI claims require real browser/desktop evidence (DOM/AX for semantic controls when exposed; pixels/screenshot/input for custom canvas/mirrored/custom-drawn surfaces — missing AX alone does not block visual proof; do NOT force both DOM and screenshot for every claim), never `curl`, source inspection, or mocks alone.
- Unreachable external systems stay `Blocked` or `Unexercised`, never `Passed`.
- UI-affecting criteria must also pass Rule 8's role-based surface session.

---

## 4. Verification Steps

### Step 1: Scope & Matrix Formulation

Select proof methods **by surface** (record surface, native capability, discovered tool/schema/permissions, expected observable, fallback):
- **Web UI:** Browser DOM/AX observation for exposed semantic controls and/or screenshot + real interaction (click, type, navigate, submit; visual claims may use screenshot, interaction claims require real interaction; do not force both for every claim).
- **Animated UI:** For animation changes or animation audits, capture before/after frame trace per [Animation Performance Reference](../../references/animation-performance.md) §4 (reproducible browser/viewport/throttling context, refresh-rate budget, reduced-motion check, pause/offscreen/unmount cleanup). Record findings only; never implement fixes.
- **Native desktop UI:** AX queries for exposed semantic controls and/or window screenshot + real input (pixels/screenshot/input for custom/mirrored surfaces; do not force both for every claim).
- **CLI:** Real command execution (`--help`, flags, invalid-arg exits, exit 0 happy path, stdout/stderr).
- **API:** Real local/authorized wire probes (`curl` or HTTP client: status codes, schemas, auth errors).
- **Regressions:** Full affected test suite plus cross-module consumer tests.

### Step 2: Execute Deterministic Checks

Run bounded, reproducible checks with standard runners (`pytest`, `npm test`, `cargo test`, `go test`) for non-UI and discovered native tools for UI:

```bash
# Example CLI verification
./bin/my-tool --help
./bin/my-tool execute --input test.json

# Example API verification (local instance)
curl -sS -D - http://127.0.0.1:8080/health -o /dev/null

# Example Full Regression Suite
pytest tests/ -v -k "test_feature"
```

**Capability discovery & honest fallback:**
- Discover actual tools/schemas/permissions; never invent client names. If unavailable, use an authorized equivalent (or verifier-inspected manual evidence), else mark `Blocked` or `Unexercised` — never fabricate UI evidence or force UI checks through shell proxies.
- Read-only only: never edit code, trigger unsolicited external side effects (sends, orders, purchases), or bypass provider safety checks (consequential UI actions require explicit approval).
- Record `stdout`/`stderr`, exit code / HTTP status, DOM/AX/screenshot/interaction observations, and disk side effects.

### Step 3: Categorize Results Explicitly

1. **Passed:** Observed exit code/status/output matches declared expectations (e.g., exit code 2 for an invalid-arg probe, exit 0 for test suites).
2. **Failing:** Executed check violated declared expectations.
3. **Blocked:** Cannot run (missing env, credentials, dependencies).
4. **Unexercised:** Skipped, omitted, or mock-only (never accepted as pass; required unexercised criteria block parent acceptance).

### Step 4: Convergence & Change Impact Assessment (§G)

Classify all AC per [Feature Delivery Contract §G](../../references/document-quality.md#feature-delivery-contract):
1. **`implemented_verified`**: In current code AND verified by fresh runtime evidence.
2. **`implemented_unverified`**: On disk, but lacks fresh runtime evidence (or mock/dry-run/stale only).
3. **`missing`**: Required behavior or error handling absent.
4. **`contradicts`**: Conflicts with spec, invariant, or security boundary.
5. **`blocked`**: Cannot run due to missing env/credentials/dependency.

**Invariants:** Never implement code/fixes/plan edits; denominator covers all scoped buildable AC (exclude only justified non-buildable/post-launch KPIs; never silently drop gaps); never relax assertions or suppress failures.

### Rule 5: Refactor Equivalence Proof

Run identical test suite and characterization probes before and after; both must pass with zero behavior delta (any delta fails even if new tests pass). Ref: [Behavior-Preserving Refactor Protocol](../../references/developer-lifecycle.md#4-behavior-preserving-refactor-protocol).

### Rule 6: Upgrade Proof

Run full regression suite plus build and include lockfile diff in `details` (missing lockfile diff or suite failure -> failing). Ref: [Dependency & Maintenance Upgrade Protocol](../../references/developer-lifecycle.md#5-dependency--maintenance-upgrade-protocol).

### Rule 7: Pre-Ship Evidence Handoff

- On `status: "pass"` for code-changing routes, populate `details.pre_ship_evidence` (verdict, claim/check/actual checks, regression counts, convergence, coverage, limitations) for `daw-ship` (verifier never commits/pushes/opens PRs).
- Multi-session/multi-commit work persists the task contract and evidence under `docs/daw/evidence/<task-id>/` before commit; inline-only is limited to single-session trivial/patch work ([Operations §2](../../references/operations.md#inline-vs-json-representation)).

### Rule 8: Role-Based Surface Session (UI-Affecting Work)

UI-affecting changes require **one executed session on the running surface, walked as a named role**, before any UI leg marks `passed`. Record per leg:
1. **Interaction:** Actual action (navigate, type, click, submit) and target surface/context.
2. **Wire outcome:** Observed HTTP status + endpoint, exit code, or equivalent (visible success + hidden 4xx = failing leg).
3. **Operator-visible message:** Rendered text/empty state/error in the product's language (unread = `unexercised`; wrong-language server string leak = finding).

Coverage floor:
- **Write leg**, **read-back leg** (persisted after refresh), and **non-staff surface** (member/portal/customer) when one exists.
- **Two viewports** — phone (≈390 px) and desktop (≈1440 px) — whenever layout, navigation, or typography changed (unafforded hidden overflow = finding).
- Every role named in AC needs a session (reasoned-only role = `unexercised`).

Scoped N/A only for backend-only changes, nonexistent flows, or read-only exploratory work (unit tests / API probes never substitute). Record as `details.surface_session` (unwalked leg = `unexercised`, blocks UI AC):

```json
{
  "role": "PETUGAS_TPS",
  "viewports": [
    { "width": 390, "height": 844 },
    { "width": 1440, "height": 900 }
  ],
  "legs": [
    {
      "kind": "write",
      "name": "create deposit for today",
      "interaction": "fill ID/date/volume/fat/SNF, click Simpan setoran",
      "wire": "POST /api/v1/deposits -> 201",
      "message": "Setoran berhasil disimpan.",
      "status": "passed"
    },
    {
      "kind": "read_back",
      "name": "reopen the deposits screen",
      "interaction": "reload and read the saved row",
      "wire": "GET /api/v1/deposits?date=2026-11-09 -> 200",
      "message": "1 setoran hari ini",
      "status": "passed"
    }
  ]
}
```

**Mechanical enforcement:** `python3 "$SUITE_ROOT/scripts/validate.py" verify surface-session.json --project-root <project> --stage complete` checks role, both viewports, `write` + `read_back` legs, concrete wire status/exit, non-blank operator message, and `passed` status on every leg. Declaring `surface: "ui"` in the task contract enforces this at `contract --stage complete` (`surface_session_missing`, `surface_leg_not_passed`); declaring `surface: "non-ui"` over a UI-shaped `operation.scope` fails with `surface_declaration_mismatch`. Passing the validator never waives parent inspection.

---

## 5. Output Contract

Deliver an observable JSON handoff per [routing §5](../../references/routing.md#5-canonical-module-handoff-contract) (with its transport hierarchy and labeled inline fallback; direct-user replies remain concise prose; never create unasked transport files). `status: "pass"` proposes stage verification on current-revision evidence only, never parent acceptance or workflow completion; keep runtime observations in `evidence` and payload in `details`.

Required `details` rules:
- **Runtime Evidence (`details.checks`):** Executed check/tool action, target surface/context, expected vs observed exit/status, and observed output/DOM/AX/screenshot snippets (report unavailable capability honestly as `blocked`/`unexercised`; mockup acceptance != runtime UI proof).
- **Result Snapshot & Evidence Binding:** Before claiming complete, record post-change `result` snapshot (`baseline` is pre-change) and bind every evidence entry with 64-hex `sha256` and `revision == result.revision`. Post-`result` edits fail with `result_changed`; non-durable evidence refs fail with `evidence_not_durable`; parent must inspect evidence directly.
- **Payload Fields:** `verification_verdict`, `summary`, `checks`, `regressions`, `surface_session` (Rule 8 or scoped N/A), `convergence`, `coverage` (all scoped AC, justified exclusions, denominator, verified, unverified gaps), and `limitations`.
- **Finding Output Contract:** Prioritized, evidence-backed, actionable findings (or explicit no-actionable-finding statement + scoped N/A/proof); report implemented work as an integration candidate + needed verification, never fake `needs-fix`. Parent re-ranks in [Ranked Result Triage](../../references/operations.md#ranked-result-triage).

Illustrative `details` only (wrap in the canonical outer envelope):

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
  "surface_session": {
    "role": "PETUGAS_TPS",
    "viewports": [
      { "width": 390, "height": 844 },
      { "width": 1440, "height": 900 }
    ],
    "legs": [
      {
        "kind": "write",
        "name": "create deposit for today",
        "interaction": "fill ID/date/volume/fat/SNF, click Simpan setoran",
        "wire": "POST /api/v1/deposits -> 201",
        "message": "Setoran berhasil disimpan.",
        "status": "passed"
      },
      {
        "kind": "read_back",
        "name": "reopen the deposits screen",
        "interaction": "reload and read the saved row",
        "wire": "GET /api/v1/deposits?date=2026-11-09 -> 200",
        "message": "1 setoran hari ini",
        "status": "passed"
      }
    ]
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
1. Every task-contract AC has a `claim`, executed `check`, and `observed_output` matching declared expectations (zero unacknowledged failures or skipped tests).
2. Any `Blocked` or `Unexercised` items are justified in `limitations` (unexercised required criteria cannot pass/be accepted).
3. Every criterion maps to inspectable expected-vs-actual evidence; no dry-runs claimed as deploy/migration proof.
4. **Refactor / upgrade proof:** Refactor — identical behavior before/after on suite + characterization probes; upgrade — regression suite + build pass with lockfile diff.
5. **UI-affecting work (Rule 8):** `details.surface_session` covers write, read-back, non-staff surface (if present), and phone/desktop viewports (if layout touched) with wire outcomes and operator messages, or a scoped N/A reason.
6. **Result snapshot (complete only):** Post-change `result.revision` recorded, evidence entries carry `sha256` and `revision == result.revision`, `validate.py contract --stage complete` passes, and no code changed after `result`.

- **Post-release closure evidence rule:** Verify current-revision code correctness as scoped proof, but keep deployed proof separate — production-resolution claims require post-release surface evidence (log/health observation, artifact digest, window); local/staging runs stay local-only proof with production resolution explicitly unexercised. A verifier `pass` never closes an incident or authorizes publication; maintenance/monitoring stays opt-in per `references/operations.md` §6.

---

## 7. Stop / Replan Triggers

Escalate to orchestrator / previous stage when:
- **Core AC Failure:** Behavior contradicts spec/PRD -> Replan to `daw-debug` or `daw-build`.
- **Unexpected Regression:** Untouched tests break -> Stop immediately; never weaken expectations.
- **Environment Blocked:** Required services cannot start or local config is corrupt -> Escalate for remediation.

---

## 8. Handoff

- **`"pass"`:** Hand verification evidence to parent orchestrator (sits after `daw-review` on `feature`/`bugfix`, never instead of it).
- **`"fail"`:** Hand structured failure evidence (command, exit code, stderr) to `daw-debug` or `daw-build`.
- **`"blocked"`:** Return unexercised dependencies and missing preflights to orchestrator.
- Never invoke modules recursively or self-heal silently.

---

## 9. References

- Root contract: `../../SKILL.md`
- Specifications and routing: `../../references/routing.md`
- Parent Acceptance Checkpoint: `../../references/operations.md#parent-acceptance-checkpoint`
- Checkpoint Boundaries & Acceptance Records: `../../references/operations.md#checkpoint-boundaries` and `../../references/operations.md#parent-owned-acceptance-record`
