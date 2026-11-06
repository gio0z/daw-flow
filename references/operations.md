# Operations, Execution, Verification & Maintenance Reference

This reference defines operational protocols for deterministic AI execution: preflight safety checks, fail-closed human/provider approvals, approval invalidation rules, immutable release rollback, tool reuse policies, semantic acceptance verification, secret redaction, opt-in background maintenance, and harness-native persistent worker graph contracts.

Operational scope pairs generative cognitive planning with deterministic, script-driven tool execution and verification gates, alongside explicit fail-closed authorization boundaries, release-snapshot rollback mechanics, proactive background maintenance boundaries for multi-tenant and local workstation environments, and session-bounded worker retention scoped to the owning workflow.

### Self-Contained Execution & Risk Gating Invariants

- **No External Skill Gate:** High-risk operations fail closed strictly on missing human/provider approvals, missing operational credentials or permissions, unverified preflight checks, missing immutable rollback targets, or inadequate semantic evidence—NEVER because of the presence or absence of a specific named external skill.
- **Direct Execution vs. Delegation:** An agent may fulfill required operational capabilities directly or delegate to an appropriate subagent. The absence of an external registry or named skill package is never a blocker for reachable, authorized tasks. If tools or subagent delegation are unavailable, the agent executes directly via honest direct fallback in the current session.
- **Direct Module Invocation Governance & Progressive Disclosure:** When any internal module (`skills/daw-*/SKILL.md` or sibling symlinks) is invoked directly rather than through the root router, it MUST execute the Governance Loader Sequence: if root `SKILL.md` §4/§6, `references/routing.md` §5, and preflight rules are already loaded into context from a prior sequential stage in the same session, reuse them directly without redundant re-reading. Load only the current stage's module instructions. Reference documentation must be consulted using progressive disclosure by exact section heading rather than loading multi-thousand-line references upfront.
- **Subordination to Host Policy:** All actions remain subordinate to host environment security boundaries, sandboxing, and approval policies. The workflow never performs global tool uninstallation, system-wide configuration alterations, or unauthorized environmental overrides.
- **Read-Only Structural Analysis & No-Mutation Guard:** Read-only analysis modules (`daw-untangle`, `daw-review`, `daw-ask`) perform purely non-mutating inspection of codebase structure, dependency topology, and recorded evidence. Safe read-only inspection never requires production credentials, deployment approvals, clean git workspaces, or rollback snapshots. They MUST NOT mutate files, run tests, or execute builds. Structural findings identify boundaries and proposed changes; implementation or refactoring requires explicit operator authorization routed through standard implementation modules (`daw-plan` / `daw-build`). Structural analysis criteria are governed by [`references/change-coupling.md`](change-coupling.md).

---

## 1. Preflight Safety & Environment Checklist

Before running any state-mutating command, migration, deployment, or infrastructure operation, the execution layer must evaluate a deterministic preflight gate. Tailor preflight checks to the relevant scope of the change; do not require cloud or cluster verification for routine local file edits:

1. **Target Environment & Relevant Host Context:**
   - For environment-specific operations (deployments, infrastructure, shared databases): verify target environment explicitly (`local`, `test`, `staging`, `production`) and confirm active host/cluster context (`kubectl config current-context`, DB host/port, cloud account ID/project).
   - For routine local edits or test runs: verify local workspace target and relevant configuration without requiring external cloud context.
   - Abort if target environment is ambiguous or inferred.

2. **Working Tree, Revisions & Workspace Coexistence:**
   - Target baseline revision or content hash identified (e.g., commit SHA or file hash).
   - If unexpected or untracked changes exist in the workspace, do NOT abort automatically solely because the tree is dirty or contains untracked files; user work and parallel activities are normal.
   - **Adapt & Protect:** Never stash, revert, overwrite, or clean away unrelated user changes. Check whether planned edits directly overlap with modified files. Halt only if there is a direct collision, conflicting lock, or high risk of clobbering unreviewed work.

3. **Explicit Scope & Blast Radius:**
   - List of touched files, database tables, or infrastructure resources strictly bounded by upstream planning contracts or issue records.
   - Zero out-of-scope files or unrelated modules touched.

4. **Tools, Automation & Permissions:**
   - Binaries and tools verified present in path (`which <tool>`).
   - Credential scopes verified appropriate for target (e.g., staging credentials do not touch production).

5. **Dry-Run & Pre-Mutation Simulation:**
   - Where the underlying tool or platform natively supports simulation (e.g., `terraform plan`, package manager dry-runs, migration simulation), run it and inspect the diff against the contract.
   - If dry-run is natively unavailable, do NOT invent fake simulation flags or wrapper scripts; perform equivalent non-mutating validation (syntax check, query EXPLAIN, parameter validation) and gate critical mutations behind explicit approval.

---

## 2. Fail-Closed Approval Boundaries

AI agents generate, read, draft, and synthesize; they **never** authorize high-impact operations autonomously. Planning documents (`security.md`, `runbook.md`, `prd.md`) define contracts and intention—**they do not grant authorization**.

### Strict Operational Principles

- **Documentation is Not Authorization:** The existence of a signed-off document, pull request link, issue number, or approved plan does not waive the requirement for explicit, interactive user confirmation at the exact point of execution risk. Structural references are not operational authorization.
- **Reviewed Inactive Draft vs. Apply/Publish/Auto-Trigger:** Drafting or editing a specification, script, or configuration file in an inactive, non-executing state is bounded design work. However, files that can be auto-loaded, picked up by daemon watchers, published externally, or executed against live systems require explicit confirmation before apply, deploy, publish, or triggering.
- **Fail-Closed Default:** If human confirmation or provider authorization is unavailable, unverified, expires, or cannot be queried (e.g., headless session, non-interactive CI, missing UI dialog), execution MUST halt immediately with a clean abort status (`status: "blocked"`). Never proceed on assumption, silence, or vague verbal assent.
- **Unknown Risk / Unknown Scope Block:** If risk level, target environment, or mutation boundaries cannot be definitively verified from observable facts before mutating actions, execution must halt as `blocked` before any filesystem or system mutation. Safe read-only intake and assessment remain unblocked.
- **High-Impact Point-of-Risk Triggers:** Explicit interactive confirmation is REQUIRED before:
  - Shared or production database schema changes (DDL, drops, migrations, destructive updates). Contrast with disposable, isolated local test fixtures created within an already authorized test run.
  - Production deployments, DNS updates, or network/routing cutovers.
  - Deletion or truncation of persistent production data, storage buckets, or backups.
  - Financial, billing, or subscription changes (e.g., Stripe, paid API upgrades).
  - Credential, secret, IAM role, or security permission modifications.
  - Pushes or tags to protected remote branches (`main`, `master`, `release/*`), or external publishing actions. Routine local branch commits within an authorized task scope proceed without redundant prompts.

### Approval Invalidation Rules

Any previously granted operational approval is bound strictly to its specific action, target environment, artifact revision, and mutation scope. An approval is immediately **invalidated** and rendered void if any of the following occur before or during execution:

1. **Target or Tenant Drift:** The execution target, database host, cloud project, or customer/tenant ID differs from what was presented during approval.
2. **Revision Drift in Approved Scope:** The repository commit SHA changes, or upstream contract documents governing the specific mutating action are modified. Blanket, unrelated workspace updates (e.g., edits to unrelated documentation or disjoint modules) do NOT invalidate bound approvals.
3. **Data / State Drift:** Preflight checks discover state diverging from baseline (e.g., unexpected pending migrations, foreign lock contention, conflicting record states).
4. **Plan Mutation:** The execution sequence, command arguments, or affected resources differ from the approved dry-run plan.

When invalidation occurs: **Halt immediately. Disclose the exact drift to the user. Request fresh confirmation.**

### Handling Unforeseen Failures & Errors

- **Stop on Partial Failure:** If a multi-step execution fails midway (e.g., step 3 of 5 fails), stop immediately.
- **No Blind Retries:** Never blindly loop or retry failed mutation commands. Repeatedly executing a failing command risks compounding state corruption or exhausting rate limits.
- **Inspect and Replan:** Inspect exact exit codes and error logs. Transition back to Intent and Planning layers to formulate an updated remediation plan before touching state again.

---

## 3. Safe Rollback Protocols

Rollback restores system stability by reverting to a verifiable, known-good baseline or restoring a pre-change snapshot.

### Rollback Contract Rules

1. **Deploying Known-Good Release vs. Git Revert:**
   - Rolling back an application deployment means re-deploying a verified, immutable release artifact (e.g., previous container image digest, verified package version, or intact deployment artifact). This is distinct from creating a `git revert` commit in the codebase.
   - A `git revert` creates a new code commit to undo repository changes, but does not deploy or restore running infrastructure. Use the strategy appropriate to the failure domain.

2. **Explicit Immutable Snapshot Identifiers & Verification:**
   - Rollback targets MUST be explicit, tested snapshot or release identifiers captured prior to mutation:
     - Where stateful data recovery is explicitly selected: exact pre-change backup or snapshot ID. Before executing restore, verify snapshot integrity (checksum / signature), compatible application/database schema version, and test restoration status on an isolated test target where feasible. For stateless application rollbacks, re-deploy the immutable release artifact without invoking database restoration.
     - Exact immutable container image digest (`registry/image@sha256:...`) or package version. Because release tags can be mutable, resolve floating tags to exact immutable digests or SHAs before executing rollback.
     - Specific commit SHA verified as previously healthy.
   - **FORBIDDEN:** Rolling back to generic floating tags like `HEAD~1`, `latest`, `HEAD`, or `master`. In active repositories or failed deployments, `HEAD~1` may point to a broken merge or someone else's commit.
   - **FORBIDDEN:** Blindly restoring the "newest" backup file found on disk after a failure without verifying its creation timestamp, database version, and snapshot integrity. The newest file may be a partial, corrupted artifact generated during the failed run.

3. **Preservation of Unrelated Workspace Changes:**
   - Never run destructive whole-tree commands (`git reset --hard`, `git clean -fdx`) that discard unrelated working tree changes made by the user.
   - Revert only the specific commits, files, or services introduced by the failed operation.

4. **Schema, State & Downward Compatibility:**
   - Account for data written by the failed run before attempting database rollback. Blindly restoring an old database snapshot destroys legitimate user records written between the snapshot and the failure.
   - Do NOT assume downward migrations exist or are safe to run. Schema changes involving column drops or data transformations are often one-way; in such cases, choose an available forward-fix or point-in-time recovery strategy documented in `runbook.md`.

5. **Rollback Verification:**
   - After rollback execution, run verification checks against the restored target to confirm system health before declaring completion.

---

## 4. Tool Packaging & Reuse Rules

Deterministic execution favors stable, repeatable interfaces over ad-hoc shell commands.

1. **Tool Reuse Over Compulsory New Scripts:**
   - Prioritize existing repository tools, CLI scripts, test runners, package manager commands (`npm run build`, `pytest`, `cargo test`, `composer test`), and standard platform automation.
   - Do NOT force the creation of new wrapper scripts simply because a command is executed twice. If an existing CLI or build tool already provides clean arguments, logging, and idempotency, reuse it directly.
   - Create new wrapper scripts only when complex multi-step orchestration lacks a native CLI interface, requires repeatable error handling, or needs standard parameter parsing.

2. **Tool Contract Requirements (When Creating Custom Scripts):**
   - **CLI Flags:** Accept explicit arguments; avoid hidden ambient state.
   - **Dry-Run Mode:** Provide native `--dry-run` or `--simulate` where applicable for state mutations; if dry-run is not natively supported by the underlying tooling, perform equivalent non-mutating validation and never invent non-functional simulation flags.
   - **Explicit Exit Codes:** Return non-zero on any error condition; fail-closed on unhandled exceptions.
   - **Idempotency:** Re-running the script with identical parameters should not corrupt state or duplicate records.

---

## 5. Semantic Verification, Audit Records & Secret Redaction

Verification establishes truthful, observable evidence that the system satisfies the specification.

1. **Observable Semantic Proof Over Shallow Signals:**
   - Shallow indicators like HTTP 200 OK or exit code 0 are insufficient on their own. An HTTP 200 response may return an application error payload (`{"error": "Unauthorized"}`), an empty collection, or data leaked across tenant boundaries.
   - Verification MUST prove semantic correctness on the actual surface modified:
     - **API Endpoints:** Assert exact response schemas, expected key fields, correct status codes, and accurate data representations.
     - **CLI Commands:** Assert expected stdout formatting, exit codes, and required side effects on disk or environment.
     - **UI Components:** Assert presence and state of interactive elements, accessibility attributes, and visual hierarchy on rendered screens.
     - **Database / Storage:** Assert records exist with expected relations, timestamps, and tenant isolation (e.g., via row-level security or explicit tenant scoping as defined in the contract).
   - Tailor verification tests to the actual change; do not mandate universal full-suite integration tests for minor local edits.

2. **Execution & Audit Record Requirements with Secret Redaction:**
   - Maintain a factual audit record of all mutating actions:
     - Exact command executed and arguments used.
     - Target environment and host context.
     - Revision / commit SHA or file hash before and after execution.
     - Execution timestamp and observed duration.
     - Concrete verification evidence collected.
   - **Strict Secret & Data Redaction:** Commands, logs, error outputs, and audit records MUST redact all secrets, API tokens, passwords, private keys, authorization headers, and sensitive customer personal data. Record configuration key names or reference identifiers only (e.g., `AUTH_TOKEN=[REDACTED]`), never credential values.
   - **Distinguish Outcomes Truthfully:** Explicitly record whether checks are `passed`, `failed`, `blocked`, or `unexercised`. Never claim verification passed for tests that were skipped, mocked, or not run.

### Parent Acceptance Checkpoint

The parent orchestrator evaluates all module outputs through this canonical verification checkpoint before accepting any stage result or advancing the execution pipeline. These constraints are instructional contracts governing agent reasoning, not runtime enforcement hooks or daemon supervisors.

1. **Four Discrete Execution & Acceptance States:**
   A workflow distinguishes four separate states:
   - **Dispatch Completion:** The worker process or execution transport completed and returned an output payload or envelope.
   - **Proposed Module Pass:** The worker envelope declares `status: "pass"`, indicating the module self-reports that its internal stage criteria were met.
   - **Parent Stage Acceptance:** The parent orchestrator inspects primary evidence, verifies identity and criteria, and explicitly decides the stage is `accepted` (or `not accepted`). A proposed pass NEVER automatically constitutes stage acceptance.
   - **Final Workflow Completion:** All required route and user criteria are `accepted` and zero required downstream, review, or verification tasks remain pending or blocked. Required pending work strictly precludes declaring completion; optional unrequested follow-ups do not block completion.

2. **Predeclared Verification Contract & Proportional Checks:**
   - Before dispatching work or mutating state, the orchestrator or module predeclares each acceptance criterion, its expected outcome, and a proportional verification check.
   - Verification checks MUST be proportional to the change scope: unit tests or targeted command assertions for local bug fixes, schema/diff inspections for specifications, or integration assertions for multi-boundary changes. Do not require universal full-suite runs for minor local edits.
   - Small, direct tasks may record criteria and acceptance inline within existing plans or handoffs without spawning extra worker processes or ceremony. Both inline text and structured JSON formats are optional parent records.

3. **Identity, Revision & Transport Integrity:**
   - The parent validates the execution envelope against the current dispatch identity: node/task ID, worker ID, current round, assigned role, declared file/domain scope, and current artifact revision (commit SHA, file content hash, or immutable snapshot).
   - The parent MUST reject stale, duplicate, cancelled, mismatched-scope, or failed-transport deliveries as valid success claims (while retaining failure payloads as diagnostic evidence for corrective rounds). A result referencing an outdated round/revision or mismatched identity cannot be accepted.

4. **Primary Observable Evidence & Expected-vs-Actual Evaluation:**
   - Every applicable criterion must be mapped to an inspectable primary observation comparing expected versus actual results, along with the execution or transport outcome.
   - **Failures and Missing Evidence Cannot Become Pass:** If evidence is missing, unexercised, ambiguous, or contradicted by primary observations, the parent MUST reject the reported pass as a success and mark the stage `not accepted` with a criterion-specific reason, retaining failure outputs as diagnostic evidence.
   - Criteria are identified stably by existing criterion text or ID.
   - Optional criterion-to-evidence mappings belong inside existing envelope `details` or plan/handoff artifacts—NEVER requiring new mandatory outer envelope fields.
   - Expected negative tool exit codes or expected error messages from tools (e.g., a test asserting that invalid CLI flags exit with code 2) are valid verification checks, distinct from worker execution or transport failures.
   - Existing evidence can be inspected and reused when current, relevant, and sufficient; do not mandate universal rerun of identical checks when the underlying revision is unchanged. Record explicit evidence invalidation whenever the underlying artifact revision, criteria, scope, or relevant environment context changes.
   - Parent stage acceptance verifies that execution criteria were satisfied; it NEVER constitutes operational authorization for high-risk actions (production deployment, destructive migrations, or external mutations).

5. **Source vs. Runtime Evidence Distinction:**
   - **Source/Static Proof:** Inspectable diffs, AST/type checks, structural grep, and file content reviews constitute sufficient proof for documentation updates, specification alignment, architectural design, and read-only code review when they directly establish the relevant claim (a bare pattern match alone without verifying context is never sufficient).
   - **Runtime Proof:** Functional behavior, side effects, API responses, CLI commands, and database state mutations require inspectable runtime execution evidence (test runner output, command exit code + stdout, rendered UI state).
   - NEVER force runtime command execution or test runs during read-only reviews or static document edits where source inspection is the appropriate proof.

6. **Mandatory Pre-Dispatch Dependency Joins:**
   - Before dispatching any dependent downstream task, the parent orchestrator MUST join and verify that all mandatory inputs from predecessor tasks are accepted for their current expected input revisions (disjoint artifacts maintain their own revision hashes; there is no global single-hash requirement).
   - An earlier successful sibling or prior run cannot mask a failed, missing, outdated, or still-running dependency.
   - Success-dependent stages require accepted successful predecessors. A corrective
     dispatch instead consumes current, validated failure findings under explicit
     correction scope; accepting findings as diagnostic input does not mark the failed
     stage successful or unlock release. Missing or failed-transport output cannot
     supply findings it never produced.

7. **Parent Acceptance Record (`accepted` / `not accepted`):**
   - The parent records an explicit decision: `accepted` or `not accepted`, accompanied by a criterion-specific rationale for any rejection.
   - This decision is distinct from worker outer execution statuses (`pass`, `fail`, `blocked`). The outer status vocabulary remains strictly `"pass"`, `"fail"`, `"blocked"`; `not accepted` is solely the parent's evaluation decision label, never a new outer JSON envelope status.
   - No unexercised required criterion may be accepted. Missing observations must be explicitly marked absent or unexercised, never invented.

### Checkpoint Boundaries

The execution pipeline requires the parent orchestrator to apply three discrete verification checkpoints. Each boundary enforces explicit entry prerequisites, evidence evaluation rules, and parent decision options:

| Boundary                                                                         | Inputs                                                                                                                                                                                                                          | Parent Decision                                                                                                                                                                                   | Advance Condition                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| :------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Pre-Dispatch Checkpoint** (prior to worker dispatch)                           | Predecessor artifact revisions with `accepted` parent status (or validated diagnostic failure findings under explicit correction scope), declared scope, and operational permissions (acceptance != operational authorization). | `dispatch_eligible` vs `hold` / `blocked` (evaluates readiness to dispatch, not evidence success; planned checks remain unexercised).                                                             | All mandatory predecessor dependencies accepted for current revisions (or validated diagnostic failure findings consumed for scoped corrective round); dispatch worker to execute assigned scope.                                                                                                                                                                                                                                                                                      |
| **Result Acceptance Checkpoint** (upon worker envelope return)                   | Worker envelope (`status: "pass"\|"fail"\|"blocked"`), current artifact revision snapshot, and primary observable evidence.                                                                                                     | `accepted` vs `not accepted` with criterion rationale (worker proposed pass or worker-forged `accepted` is untrusted; failure findings authorize scoped correction without unlocking downstream). | If `accepted`: all stage criteria verified by primary observable evidence matching expected outcomes, advance to next stage. If `not accepted`: retain failure findings and dispatch scoped correction (or halt); never advance downstream on unaccepted results.                                                                                                                                                                                                                      |
| **Prefinal Coupling Checkpoint** (prior to final delivery of code-changing work) | Changed diff, affected public interfaces and caller dependencies, existing accepted `daw-review` results (feature/bugfix), or bounded diff inspection (patch).                                                                  | `coupling_accepted` vs `coupling_not_accepted` / `escalate_untangle` (recorded in parent acceptance details; not a new outer JSON envelope status).                                               | Proportional structural check satisfied ([references/change-coupling.md#prefinal-coupling-checkpoint](change-coupling.md#prefinal-coupling-checkpoint)): feature/bugfix reuses current accepted review without duplicate pass; patch completes bounded diff check (noting single-perspective fallback if without independent reviewer); docs/non-code records inline N/A. Material structural blockers absent. Bounded `daw-untangle` invoked only on demonstrated boundary obscurity. |
| **Final Completion Checkpoint** (at workflow conclusion)                         | Audit across all pipeline stages, user acceptance criteria, and evidence freshness across all artifact revisions.                                                                                                               | `completed` vs `incomplete` (or `blocked`).                                                                                                                                                       | All required route and user criteria accepted; zero required downstream, review, or verification tasks remain pending or blocked.                                                                                                                                                                                                                                                                                                                                                      |

- **Stage Acceptance vs. Final Completion Rule:** At result acceptance, accept a stage whose own required criteria and mandatory predecessors pass even when a required LATER or independent sibling stage remains pending; only final completion is withheld. A pending mandatory predecessor instead blocks dependent stage dispatch.
- **Evidence Reuse & Invalidation Rule:** Existing evidence may be reused when current, relevant, and sufficient without arbitrary full-suite mandates. Record explicit evidence invalidation whenever the underlying artifact revision, criteria, scope, or relevant environment context changes. Do not carry forward prior passed source or runtime proof across modified artifacts without reinspection.
- **Proportional Prefinal Coupling Check Rule:** Before final completion of code-changing work, the parent orchestrator checks the changed diff and directly affected interfaces/dependencies for structural coupling ([references/change-coupling.md#prefinal-coupling-checkpoint](change-coupling.md#prefinal-coupling-checkpoint)). For feature/bugfix routes, the parent reuses the current accepted `daw-review` result for matching revision/scope without duplicate review overhead; for patch routes, the parent performs a bounded proportional diff check (documenting single-perspective fallback limits if operating without an independent reviewer) without injecting a new reviewer stage or untangle pass; for docs-only tasks, an explicit inline N/A rationale is recorded. Escalation to `daw-untangle` is strictly exceptional and reserved for demonstrated boundary obscurity over a bounded scope.
- **Separate Authorization Rule:** Parent stage acceptance verifies that execution criteria were satisfied; it NEVER constitutes operational authorization for high-risk actions (production deployment, destructive migrations, or external mutations).
- **Inline vs. JSON Representation:** Recording parent acceptance is optional in format: direct or small tasks may record criteria and decisions inline within existing plan or handoff notes without extra JSON or worker ceremony. Multi-stage or complex workflows may use the optional parent-owned acceptance JSON structure embedded below.
- **Authorized Execution Mandatory:** Verification requires running actual commands against the live working environment and inspecting exit codes, stdout, and stderr. Merely printing or echoing a command, asserting file presence, or ticking a task checkbox is NOT execution.
- **Scoped Pause/Resume & Canonical Block State in Records:** When an execution node cannot proceed due to missing material decisions, unanswered human queries, or ungranted high-risk approvals, it halts as canonical `status: "blocked"`. The parent orchestrator or pausing module records the halt details in the parent acceptance record or module handoff details: `blocked_reason`, `responsible_party`, `pending_question_or_decision`, `next_permitted_action`, `current_revisions`, `pending_dependencies`, and `verified_evidence`. In non-interactive contexts, an unanswered query NEVER constitutes tacit approval. On resume, the orchestrator re-evaluates the blocking condition, artifact revisions, prerequisites, and operational authorizations before re-dispatching.
- **Proportional Invalidation & Document Gate Re-Entry:** Modifying implementation code invalidates affected runtime verification evidence and postbuild reviews, but does NOT invalidate accepted specification documents. When formal accepted specification documents are modified, they MUST re-enter the existing five-edge document transition gate (`review-rework` -> `rework-review` -> `review-ready`). Agents MUST NOT invent a non-existent transition named `rework`.

### Parent-Owned Acceptance Record

The parent orchestrator writes and owns the acceptance record after independent inspection of primary evidence. Worker-supplied `details` are NOT parent-owned decisions. The parent may annotate its own details or handoff record after independent inspection; any worker envelope claiming a `parent_decision` or self-granted acceptance—even if formatted identically—is strictly untrusted.
Parent evaluators MUST copy exact task and criterion IDs and cited observation references directly from predeclared dispatch contracts; never synthesize missing source content. Any missing, mismatched, or extraneous criterion IDs constitute an incomplete handoff and strictly preclude stage acceptance.

Below is an optional worked parent acceptance record illustrating a **rejection** at `checkpoint: "result_acceptance"` where a worker self-reported `status: "pass"` but actual runtime output contradicted the expected negative sum. All paths, snapshot IDs, and observations in this worked example are illustrative, not recorded executions; real IDs must resolve immutable inspected bytes:

```json
{
  "checkpoint": "result_acceptance",
  "task_id": "task-402-signed-sum",
  "worker_id": "daw-build-worker-1",
  "role": "builder",
  "round": 1,
  "scope": ["src/cli/signed_sum.py"],
  "artifact_revisions": {
    "src/cli/signed_sum.py": "snapshot:src/cli/signed_sum.py#rev-b1"
  },
  "input_provenance": [
    {
      "predecessor_id": "spec-design-301",
      "artifact": "docs/design.md",
      "revision": "snapshot:docs/design.md#rev-a3",
      "parent_status": "accepted"
    }
  ],
  "worker_envelope": {
    "status": "pass",
    "note": "Worker proposed pass claiming signed addition implemented"
  },
  "criteria_evaluations": [
    {
      "criterion_id": "AC-1-signed-addition",
      "kind": "runtime",
      "check": {
        "cwd": "/workspace",
        "command": "python3 -m src.cli.signed_sum -- -2 -3"
      },
      "expected": {
        "exit_code": 0,
        "stdout": "-5\n"
      },
      "observation": {
        "reference": "obs-run-signed-sum-r1",
        "revision": "snapshot:src/cli/signed_sum.py#rev-b1",
        "result": "failed",
        "observed": {
          "exit_code": 0,
          "stdout": "5\n"
        }
      }
    }
  ],
  "parent_decision": {
    "decision": "not accepted",
    "reason": "Criterion AC-1 failed: expected stdout '-5\n' but observed '5\n' (sign dropped). Worker self-reported pass rejected.",
    "next_action": "dispatch_correction",
    "correction_scope": {
      "target_file": "src/cli/signed_sum.py",
      "allowed_round": 2,
      "unlocked_downstream": false
    }
  }
}
```

##### Concise Accepted Variant

Following corrective round 2 on revised artifact `snapshot:src/cli/signed_sum.py#rev-b2`, the parent reruns `python3 -m src.cli.signed_sum -- -2 -3` in `/workspace`. The fresh observation records exit code 0 and stdout `"-5\n"`, matching expected outcome under reference `obs-run-signed-sum-r2`. The parent updates `parent_decision.decision` to `"accepted"` with reason `"Criterion AC-1 verified against fresh runtime execution on rev-b2"` and sets `next_action` to `"advance_to_daw_verify"`. Prior passed proofs are never carried over without reinspecting the modified artifact.

### Parent Prefinal Coupling Checkpoint

The parent orchestrator enforces a proportional structural coupling and boundary check **before final delivery** of any code-changing workflow, governed by [`references/change-coupling.md#prefinal-coupling-checkpoint`](change-coupling.md#prefinal-coupling-checkpoint).

This check ensures that modifications do not introduce unintended cross-module entanglements, circular dependencies, leaky abstractions, or accidental co-change coupling.

This is an **instructional procedural skill rule governing parent reasoning**, NOT a deterministic semantic enforcement hook, runtime daemon supervisor, or Claude Code Stop listener.

1. **Proportional Scope by Route:**
   - **Feature & Bugfix Routes:** Existing route-required `daw-review` already executes Stage 2 structural boundary and architectural audits. The parent orchestrator **reuses the existing accepted `daw-review` result** for the current matching artifact revision and scope. It MUST NOT execute a duplicate or redundant review pass if an accepted review already covers the current diff.
   - **Patch Route:** The patch route remains strictly streamlined (`daw-build` -> `daw-verify`). The parent orchestrator performs a bounded, proportional inspection of the changed diff and directly affected interfaces. It MUST NOT mandate a new intermediate reviewer stage or invoke `daw-untangle` for localized, low-risk, or single-file fixes. When operating without an independent review stage, the parent explicitly notes the single-perspective verification fallback limitation in its acceptance record rather than claiming simulated independent acceptance.
   - **Documentation & Non-Code Routes:** Tasks with zero structural code changes (docs-only, configuration descriptions, comments) record an explicit inline N/A rationale (e.g., `coupling_check: "N/A - documentation-only, no structural code changes"`) without structural analysis overhead.
   - **Implementation Rail:** During construction, `daw-build` applies lightweight change-coupling self-checks (minimal diff, avoiding accidental co-change, preserving public contracts) and notes observations inline in its handoff details.

2. **Escalation to `daw-untangle`:**
   - **Escalation Threshold:** Escalate ONLY when the parent or reviewer observes **demonstrated hidden, unclear, or circular dependency impacts** across modules that cannot be reliably resolved through direct inspection of the diff and local call sites.
   - **Strictly Bounded Scope:** Any escalation MUST target solely the specific affected boundary, component, or subsystem. An untangle escalation NEVER authorizes a whole-codebase scan, unsolicited architectural audit, or broad repository cleanup.
   - **Read-Only Analysis Contract:** `daw-untangle` returns bounded, evidence-backed read-only analysis to the parent orchestrator. It receives NO mutation authority. An untangle output status of `pass` indicates completion of structural diagnosis, NEVER proof of runtime behavioral correctness or operational fix.

3. **Findings Disposition & Revision Invalidation:**
   - **Material Structural Blockers:** Changes that break architectural boundaries, introduce circular dependencies, or violate subsystem encapsulation directly affecting the correctness, security, or stability of the change block parent final acceptance.
   - **Out-of-Scope Architectural Debt:** Pre-existing coupling, incidental refactoring opportunities, or stylistic boundary improvements are documented separately as advisory backlog observations. They MUST NOT trigger unsolicited refactoring or block acceptance of the immediate scoped fix.
   - **Authorized Correction Routing:** When structural corrections are required, the parent orchestrator routes them through standard planning and implementation modules (`daw-plan` / `daw-build`) under an explicit, bounded correction scope.
   - **Evidence Invalidation on Revision:** Any code modification made during correction **invalidates all affected review and runtime verification evidence** for prior revisions. The parent orchestrator must re-verify behavioral correctness and recheck the revised diff before final acceptance.
   - **Applicable Route Retry & Stop Rules:** Corrective iterations follow existing applicable route retry and stop rules without inventing new fixed caps. Executed criteria that fail retain status `fail`; unexercised prerequisites or missing approvals become `blocked`.

4. **Observability & Acceptance Record:**
   - Coupling verification is recorded directly within existing plan, handoff, or parent checkpoint records. It requires NO mandatory new files, custom schemas, or hidden storage.
   - Populates existing fields inline: `scope` (paths and interfaces evaluated), `revision` (artifact revision snapshot), `evidence` (accepted review ref, diff inspection summary, or untangle finding IDs), and `disposition` (`accepted`, `not accepted`, or `N/A` with clear rationale).
   - Default human final reporting remains concise and action-first; comprehensive JSON records remain internal to the parent orchestrator.

---

## 6. Proactive Background Maintenance (Opt-In Only)

Maintenance agents that monitor systems, audit logs, or patch security advisories operate under strict isolation and rate controls.

1. **Strictly Opt-In Activation:**
   - Maintenance loops NEVER activate spontaneously from the mere presence of a `runbook.md`, `roadmap.md`, or issue backlog.
   - Never claim an active monitoring service or background daemon exists without observing an actual running process, active monitoring endpoint, and real sample telemetry observations.
   - Maintenance loops MUST be explicitly configured and enabled by the human user with a designated operational scope.

2. **Defined Monitoring Sources & Metrics:**
   - Approved telemetry sources (e.g., Prometheus alert manager, Datadog metrics, Sentry error tracker, GitHub Dependabot alerts).
   - Explicit thresholds and evaluation windows (e.g., error rate $> 1\%$ over a 15-minute sliding window; memory usage $> 90\%$ sustained for 10 minutes).

3. **Cadence & Execution Bounds:**
   - Strictly bounded evaluation cadence (e.g., hourly, daily cron). Never run tight unthrottled infinite poll loops.
   - Rate limiting and maximum concurrency bounds (e.g., max 1 concurrent remediation run).

4. **Allowed Fix Classes vs. Approval-Only Tasks:**
   - **Auto-Fix Eligible (if explicitly authorized):** Non-breaking dependency patch upgrades passing full local CI test suites; automated log rotation or cache eviction within predefined thresholds.
   - **No Automated PR Publishing by Default:** Automated dependency upgrades or maintenance patches must not publish or open pull requests to remote repositories without explicit user authorization.
   - **Approval-Only (Always):** Production restarts, database indexing or compaction, configuration changes, schema migrations, and code modifications affecting core logic.

5. **Kill-Switch, Ownership & Reporting:**
   Every background maintenance loop must have a clear named owner and an immediate disable mechanism (environment variable, flag, or kill-switch file).
   Every maintenance action must emit a structured audit log (with secrets redacted) and generate a human-reviewable report detailing observations, actions taken, and verification results.
   If an unexpected condition or verification failure occurs during maintenance: Stop immediately, alert the owner, and return to the planning layer. Never attempt unapproved self-directed system restructuring.

## Persistent Worker Graphs (Harness-Native)

Persistent here means a harness can continue a completed worker with its identity and
conversation retained during the owning workflow session. DAW supplies instructions,
not a scheduler, backing store, daemon, or automatic recovery after process loss.
Idle/parked workers need not run continuously. Session history alone does not prove
that continuation is supported or that a workflow can resume after a crash.

### Capability Discovery & Fallback

At ordinary workflow intake, the parent MUST discover applicable harness capabilities
from exposed tools/documentation (or reuse still-applicable observed discovery). When
the task already warrants delegation and corrective rounds, completed-worker retention
is the default if supported, unless the user opts out. No persistence keyword, extra
confirmation, or prior `daw-setup` invocation is required. Small direct tasks remain
direct; never add workers or review stages merely to use retention. The active route
is unchanged. This default is optional persistence, not a requirement: unavailable or
failed continuation uses the explicit fresh-worker handoff below unless the user
explicitly requires retention. These are agent instructions, not runtime enforcement.

Inspect exposed harness tools/documentation for spawning, continuation after completion,
result delivery, independent reviewers, interactive approval, and lifecycle/resource
limits. Messaging a running worker or keeping a batch pool alive does not establish
completed-worker continuation. Do not enable global settings to obtain a capability.
When retention is optional and unavailable, report it and use a fresh worker with an
explicit handoff; never describe that as persistent reuse. If retention is required,
return `blocked`. Missing required approval also blocks the action; self-review must
never be presented as independent review.

### Parent-Owned Graph & Dispatch

1. **Register roles and dependencies:** The parent tracks node/task identity, role,
   harness worker ID, current round, artifact revision (hash or immutable snapshot),
   mandatory inputs, write ownership, and accepted evidence in its existing plan or
   handoff artifacts. This is workflow bookkeeping, not a new required JSON schema.
   Keep builder and independent read-only reviewer distinct; parallel writers need
   disjoint ownership or an explicit integration boundary. Do not retain secrets in
   messages or handoff artifacts.
2. **Dispatch eligible work:** Verify and record the pre-dispatch dependency join: start
   only nodes whose mandatory predecessor inputs are explicitly `accepted` for their current
   expected input revisions. Disjoint artifacts track their own revision hashes without
   requiring an artificial single global hash. Send the assigned scope, revision, criteria,
   worker ID/round, and allowed tools. Resume the same worker only in the same role when
   continuation is supported; reread current sources/constraints and perform proportional
   preflight on resumption. Retained context never extends permissions or authorizes a new scope.
3. **Accept results via canonical checkpoint, not narratives:** Evaluate all results
   through the [Parent Acceptance Checkpoint](#parent-acceptance-checkpoint). Match the
   worker ID, task, role, round and artifact revision to the current dispatch. Distinguish
   dispatch completion, proposed worker status, parent stage acceptance, and final workflow
   completion: a worker's proposed `status: "pass"` is merely a claim and NEVER automatically
   constitutes parent acceptance. Reject stale, duplicate, cancelled, mismatched-scope, or
   failed-transport deliveries as success claims (while retaining failure outputs as
   diagnostic evidence). Inspect primary observable evidence against expected outcomes;
   a reported pass with missing, unexercised, ambiguous, or contradicting evidence MUST be
   rejected as `not accepted` with a criterion-specific reason. Downstream dispatch proceeds
   only when all mandatory predecessor inputs are joined and accepted for their expected
   input revisions; an earlier successful sibling cannot hide a failed, missing, outdated, or running dependency.
   - **Observable Transition Checkpoint Invariant:** Complete canonical handoff JSON envelopes MUST be delivered and observable by the parent orchestrator BEFORE advancing to downstream stages. Delivery follows the transport hierarchy (module/subagent structured return, harness-native message, authorized workflow artifact, or labeled inline fallback). The parent orchestrator inspects the full JSON envelope and primary evidence before stage acceptance. Unconditional raw JSON display in final user replies is replaced by concise natural language as defined in [User-Facing Reports & Handoff Transport](routing.md#user-facing-reports--handoff-transport). Read-only modules remain safe and never write unauthorized disk artifacts.
4. **Control feedback at the parent:** On a correctable `fail`, send concrete findings
   to the retained builder, then send the corrected artifact to the retained reviewer.
   Advance the artifact revision and invalidate affected downstream review/verification
   passes. Bind high-risk approvals to the exact current action, target, revision and
   scope; previous approval is not inherited by a corrective round. `blocked` holds
   affected nodes while independent authorized work may continue. Follow the active
   route and existing review/debug retry and stop/replan rules; retention grants no
   extra attempts. The parent schedules successive rounds, never module-to-module
   recursion or a cyclic dependency inside an acyclic DAG/batch helper.
5. **Stop explicitly:** Report actual harness time/cost/iteration limits where exposed;
   do not invent hard enforcement. On stagnation, exhausted allowed retries, missing
   prerequisites or an operational bound, preserve evidence and stop/replan without
   claiming completion. A failed executed criterion remains `fail`; missing prerequisites
   remain `blocked`. At completion/stop record the final revision and pending work,
   disable further dispatch and cancel only workflow-owned running work when needed.
   Late output cannot restart the graph. End-to-end completion requires the active
   route's final criteria and actual current-revision verification, not a worker exit.

### Optional OMP Mapping

When exposed by the host, `task` creates workers, `write agent://ID` continues a retained
idle/parked worker, and results arrive automatically; use `wait` only when blocked.
Observe successful continuation before relying on it. A drained `workpool` is not a
retained worker graph. Other harnesses may expose different tools or no continuation;
apply the capability/fallback rules above rather than requiring OMP commands.
