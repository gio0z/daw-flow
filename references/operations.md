# Operations, Execution, Verification & Maintenance Reference

This reference defines operational protocols for deterministic AI execution: preflight safety checks, fail-closed human/provider approvals, approval invalidation rules, immutable release rollback, tool reuse policies, semantic acceptance verification, secret redaction, and opt-in background maintenance.

Article Reference: Rama Digital — _Agentic Tapi Deterministic Workflow AI Agent_ (https://ramadigital.id/blog/agentic-tapi-deterministic-workflow-ai-agent).
_Advice separation note:_ Core article advice establishes the architectural principle of generative cognitive planning paired with deterministic, script-driven tool execution and verification gates. Local operational additions in this reference define explicit fail-closed authorization boundaries, release-snapshot rollback mechanics, and proactive background maintenance boundaries for multi-tenant and local workstation environments.

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

- **Documentation is Not Authorization:** The existence of a signed-off document or an approved plan does not waive the requirement for explicit user confirmation at the exact point of execution risk.
- **Reviewed Inactive Draft vs. Apply/Publish/Auto-Trigger:** Drafting or editing a specification, script, or configuration file in an inactive, non-executing state is bounded design work. However, files that can be auto-loaded, picked up by daemon watchers, published externally, or executed against live systems require explicit confirmation before apply, deploy, publish, or triggering.
- **Fail-Closed Default:** If human confirmation or provider authorization is unavailable, unverified, expires, or cannot be queried (e.g., headless session, non-interactive CI, missing UI dialog), execution MUST halt immediately with a clean abort status. Never proceed on assumption or silence.
- **High-Impact Point-of-Risk Triggers:** Explicit interactive confirmation is REQUIRED before:
  - Shared or production database schema changes (DDL, drops, migrations, destructive updates). Contrast with disposable, isolated local test fixtures created within an already authorized test run.
  - Production deployments, DNS updates, or network/routing cutovers.
  - Deletion or truncation of persistent production data, storage buckets, or backups.
  - Financial, billing, or subscription changes (e.g., Stripe, paid API upgrades).
  - Credential, secret, IAM role, or security permission modifications.
  - Pushes or tags to protected remote branches (`main`, `master`, `release/*`), or external publishing actions. Routine local branch commits within an authorized task scope proceed without redundant prompts.

### Approval Invalidation Rules

Any previously granted approval is immediately **invalidated** and rendered void if any of the following occur before or during execution:

1. **Target or Tenant Drift:** The execution target, database host, cloud project, or customer/tenant ID differs from what was presented during approval.
2. **Revision Drift:** The repository commit SHA changes, or upstream contract documents are modified.
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
   - Every background maintenance loop must have a clear named owner and an immediate disable mechanism (environment variable, flag, or kill-switch file).
   - Every maintenance action must emit a structured audit log (with secrets redacted) and generate a human-reviewable report detailing observations, actions taken, and verification results.
   - If an unexpected condition or verification failure occurs during maintenance: **Stop immediately, alert the owner, and return to the planning layer.** Never attempt unapproved self-directed system restructuring.
