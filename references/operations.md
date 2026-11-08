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
  - Merging a pull request, force-pushing, tagging a release, publishing a package, or deploying release artifacts (the `ship` route never auto-authorizes these; see [PR/CI protocol](developer-lifecycle.md#8-pull-request--ci-protocol) and [release readiness](developer-lifecycle.md#10-release-readiness)).

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
   - **Contract binding at completion:** A `complete` claim passes only if evidence is committed-durable (`evidence_not_durable` rejected on every stage), unchanged since recorded (`evidence_hash_mismatch`), produced for the `result` revision (`missing_evidence_revision`, `evidence_revision_mismatch`), and the `result` files have not changed since (`result_changed`). `baseline` is the pre-change snapshot; `result` is the post-change snapshot recorded after verify; verify evidence must be produced against `result.revision`; any edit after recording `result` invalidates completion and requires re-verify. The validator never evaluates semantic truth of evidence — the parent must open the evidence.
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

### Operational Rule Diagnostics

This subsection is a practical lens on the existing gates in this
reference, not a new schema, stage, checklist, or mandatory
artifact. Use it when authoring or applying an operational rule.
Record only relevant entries in existing finding, plan, or
handoff fields; do not demand a full per-rule record for every
task, and do not create a parallel diagnostics file.

**Compact model.** For each applicable rule, connect four elements:

1. **Trigger:** the condition that invokes the rule (for example,
   a completion claim, a high-risk mutation, or a changed invariant).
2. **Tell:** the observable sign of a violation or misapplication,
   plus its consequence, stated as inspectable evidence rather
   than a subjective impression. For a preventative safety
   requirement the tell is the observable prerequisite gap
   itself (for example, a missing approval), not observed harm;
   safety does not wait for harm to become observable.
3. **Fix:** the scoped corrective action bounded by the rule's
   authority. Direction and requirements supply intent; the fix
   must not invent product requirements, scope, or proof beyond
   the cited direction.
4. **Proof:** the sufficient evidence that the fix held, recorded
   with the existing verdict vocabulary: `passed`, `failed`,
   `blocked`, `unexercised`, and parent `accepted` or `not accepted`.
   No new verdict, status, or field is introduced.

**Classify before acting:**

- **Hard obligations** (safety gates, accepted contracts,
  point-of-risk approvals where required): non-negotiable.
  Rationalizing them away, or treating a document or plan as
  authorization, is itself a tell. Stop the affected action
  and resolve the relevant prerequisite or repair the defect
  under existing authority; obtain point-of-risk approval only
  where that authority requires it.
- **Contextual choices** (direction, requirements, purpose):
  judge against the actual requirement and purpose. A cosmetic
  preference, naming taste, or subjective style defect is not
  a gate violation on its own.
- **Consistency checks:** keep them proportional to the changed
  scope. Cite the existing authority (§1–§5 and the Parent
  Acceptance Checkpoint) instead of restating it at length.

| Diagnostic case                              | Tell / consequence                                                                                 | Scoped fix                                                                                                                                                                                                                                                                       | Sufficient proof                                                                                            |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Unsupported completion claim                 | Worker `pass` with missing primary evidence, or executed output contradicting the expected outcome | Missing evidence marks the relevant check `unexercised` and the parent records `not accepted`; contradicted executed evidence marks the check `failed`; the module maps these to its existing `fail` / `blocked` outer status. Repair only the missing or contradicted evidence. | Fresh primary observation vs. expected outcome on the affected revision; parent `accepted` / `not accepted` |
| Missing material direction vs. settled patch | A material unknown treated as settled, or a pre-diagnosed fix blocked on ceremony                  | Halt `blocked` naming the question and next permitted action for true unknowns; proceed directly for settled patches                                                                                                                                                             | Recorded question plus blocking impact, or settled contract plus targeted proof                             |
| Cosmetic preference vs. actual invariant     | Nit framed as gate failure while the real invariant goes untested                                  | Downgrade the nit to an advisory note; verify the invariant through existing proof, asking the authorized verifier to re-execute only if that proof is insufficient                                                                                                              | Proof of the invariant (schema, boundary, behavior), not agreement with taste                               |
| Out-of-scope cleanup                         | Unrelated rewrite, migration, or cleanup smuggled into the change                                  | Remove it from scope or split it as a separate scoped task; never bundle it to "improve while here"                                                                                                                                                                              | Diff limited to the declared scope; separate work only if separately authorized                             |
| Stale proof / negative expected exit         | Pass reused after an affected revision change, or expected tool failure read as worker failure     | Invalidate the affected evidence on relevant revision, scope, or context change and reinspect; treat expected negative exits as valid checks                                                                                                                                     | Fresh observation on the affected revision; expected exit matched, distinct from transport failure          |

Static proof (diff inspection, AST or type checks, structural
grep in context) suffices for documentation and read-only
review where it directly establishes the claim; runtime claims
require execution on the actual surface, and a read-only
reviewer must not execute commands to manufacture it. Missing
required evidence blocks completion but not unrelated tasks;
repair it under the existing retry and correction protocol,
with no forced giant audit of unaffected scope.

_Inspiration note (pinned, no external dependency):_ adopted
the trigger/tell/fix/proof framing and observable-tell
discipline from [anti-slop](https://github.com/miqdadbadjuber/anti-slop/blob/9504989f162a92b1996853eccbb3d8a86e73df68/antislop.md)
and `skills/antislop-code/SKILL.md` at that same commit.
Excluded: its visual ban list, any new gate stage or
per-rule-diary mechanism, and any universal quality claim.
This subsection adds no runtime promise, dependency, schema,
or gate stage.

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

   - **No-fabrication pending for missing evidence:** Missing, stale, or unverifiable primary evidence is recorded as `pending / unexercised` with the exact missing ref named; it is never recorded as accepted, and never backfilled from narrative, checkbox, or desired-work text. The disposition stays `not accepted` until fresh inspected proof exists.

- **Result Snapshot & Evidence Binding:** At final completion the parent requires the contract `result` object (post-change snapshot, recorded after verify; `baseline` is the pre-change snapshot). Verify evidence must be produced against `result.revision`; any edit after recording `result` invalidates completion and requires re-verify (`result_changed`). Evidence artifacts must be durable on every stage (`evidence_not_durable`), carry a matching `sha256` (`missing_evidence_sha256`, `invalid_sha256`, `evidence_hash_mismatch`), and be bound by `revision` to `result.revision` (`missing_evidence_revision`, `evidence_revision_mismatch`). The validator never evaluates the semantic truth of evidence; the parent must open the evidence to accept it.

- Expected negative tool exit codes or expected error messages from tools (e.g., a test asserting that invalid CLI flags exit with code 2) are valid verification checks, distinct from worker execution or transport failures.
- Existing evidence can be inspected and reused when current, relevant, and sufficient; do not mandate universal rerun of identical checks when the underlying revision is unchanged. Record explicit evidence invalidation whenever the underlying artifact revision, criteria, scope, or relevant environment context changes.
- Parent stage acceptance verifies that execution criteria were satisfied; it NEVER constitutes operational authorization for high-risk actions (production deployment, destructive migrations, or external mutations).

5. **Source vs. Runtime Evidence Distinction:**
   - **Source/Static Proof:** Inspectable diffs, AST/type checks, structural grep, and file content reviews constitute sufficient proof for documentation updates, specification alignment, architectural design, and read-only code review when they directly establish the relevant claim (a bare pattern match alone without verifying context is never sufficient).
   - **Runtime Proof:** Functional behavior, side effects, API responses, CLI commands, and database state mutations require inspectable runtime execution evidence (test runner output, command exit code + stdout, rendered UI state).
   - NEVER force runtime command execution or test runs during read-only reviews or static document edits where source inspection is the appropriate proof.

<a id="mandatory-pre-dispatch-dependency-joins"></a>

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

<a id="ranked-result-triage"></a>

### Ranked Result Triage

Every completed worker result goes through parent triage before acceptance or fix dispatch. Triage is per-result and dependency-local: the parent MUST consume each returned result before accepting the stage it belongs to or dispatching a dependent, but MUST NOT insert a global barrier that waits for unrelated pending siblings before dispositioning a ready result. A completed result whose mandatory predecessor join is already accepted can be dispositioned and, when eligible, dispatched while an independent sibling is still pending. Only the dependent consumer waits on its own missing predecessor; unrelated pending work never blocks it.

**Worker output contract (compact, existing details/findings — no mandatory giant schema per child):** each completed worker returns only actionable, evidence-backed findings or remaining fixes in its own proposed priority order, each with source scope, impact/urgency rationale, and dependency where relevant; or an explicit statement of no actionable finding (see step 2 for the scoped-evidence requirement). Implemented work is reported as an integration candidate plus the verification it still needs — never a fake `needs fix` for work already done. A child priority proposal never constitutes self-acceptance or deployment permission.

1. **Inspect:** Verify primary evidence against the current revision and scope (identity, round, revision, criterion IDs copied from the dispatch contract). Deduplicate and merge overlapping findings from multiple workers.
2. **Reject with record / no-findings gate:** Unsupported, out-of-scope, or advisory findings are rejected with an explicit not-accepted/advisory rationale — never silently dropped. A statement of no actionable finding receives a concise `accepted / no corrective action` disposition ONLY after the parent has inspected sufficient scoped evidence for the claim (source/runtime proof proportionate to the scope, or an explicitly recorded scoped N/A). A bare "no findings" claim with no inspected evidence is recorded `not accepted` pending that scoped proof; never manufacture a fix queue from clean results, and never grant free acceptance either.
3. **Parent re-rank:** The parent validates and re-ranks across all returned results into a single queue — never blindly trusts child rank. Assign relative ordered rank from severity/impact, urgency, and dependency-unblock effect — not arbitrary numeric scores or blanket P0. Keep severity distinct from dispatch order: eligible prerequisites dispatch before dependents, while independent safe work continues.
4. **Record queue:** For multi-step work, in the existing durable plan/progress record ([Workflow Artifacts](workflow-artifacts.md)), write a compact queue entry per finding/result: finding/result ID, source worker, evidence/revision, impact/urgency justification, rank, dependencies, disposition/next action, and integration verification ref. Preserve retry/dependency joins and retry history; a later correction round appends, it does not erase the prior queue entries.
5. **Dispatch & verify:** Dispatch fixes per the ranked eligible queue, integrate into the intended target, verify against the current revision, and close only via parent acceptance. Existing pre-dispatch joins and correction recurrence limits apply; read-only roles gain no write authority. External deploy still requires exact target/scope permission at the point of risk — triage never authorizes it automatically.

No new Python schema, outer JSON field, or global scheduler is introduced; the queue lives in existing plan/progress artifacts.

### Post-Release Feedback & Incident Closure

Authorized post-release feedback or incident handling re-enters existing routes only
(bugfix, feature, patch, operational runbook, or maintenance opt-in per §6); it adds
no new route, publish automation, or monitoring automation. Preflight (§1), fail-closed approvals (§2),
rollback (§3), and parent acceptance / ranked triage (§§ Parent Acceptance Checkpoint, Ranked Result Triage) apply unchanged.

1. **Intake (parent-owned):** record source (report, log, telemetry query, operator observation), affected release/artifact digest
   and revision, evidence reference, impact (scope, severity, affected tenants/users), and named owner. Source, release, and
   evidence are copied from observed artifacts, never synthesized; missing items stay `unexercised` for that element.
2. **Classify exactly one disposition class per item:** `bug` (defect vs. accepted spec), `new requirement` (spec gap or
   requested behavior change), `operational incident` (live-service failure or degradation), or `no-change/deferred`
   (rejected, out of scope, or explicitly deferred with reason). No-change/deferred names the reason and a revisit trigger or
   expiry; it is a valid closure, not a deferral to an unnamed future.
3. **Route through existing gates:** `bug` and `new requirement` dispatch through the canonical plan/build/review/verify path
   with linked REQ/AC/task when actioned; `operational incident` follows `templates/runbook.md` containment/rollback and
   point-of-risk approval before any production change; `no-change/deferred` requires no build but still records disposition
   and owner. Triage or intake never authorizes deployment, publication, or production mutation.
4. **Close only on parent-observed evidence:** closure requires (a) recorded disposition, (b) linked REQ/AC/task where actioned,
   (c) parent-observed scoped verification on the current revision, and (d) post-release evidence only if the fix was
   actually deployed to that release surface (log/health observation, digest, and observation window). Local unit tests,
   dry-runs, or staging proof satisfy (c) for code correctness but never satisfy (d) and MUST be recorded as
   "local proof only — production resolution unexercised", never as production resolved.
5. **No automatic publish or monitoring:** intake and closure MUST NOT auto-publish, auto-open remote issues/PRs, or claim
   active monitoring. Background monitoring, polling, or auto-fix remain strictly opt-in per §6 (explicit human enablement,
   named owner, kill-switch, audit log); operations maintenance stays opt-in.

Evidence integrity is unchanged: unexercised closure elements block final completion; an executed failure stays `failed`,
never downgraded to `deferred` to obtain closure.

<a id="checkpoint-boundaries"></a>
The execution pipeline requires the parent orchestrator to apply three discrete verification checkpoints. Each boundary enforces explicit entry prerequisites, evidence evaluation rules, and parent decision options:

| Boundary                                                                         | Inputs                                                                                                                                                                                                                          | Parent Decision                                                                                                                                                                                   | Advance Condition                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| :------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Pre-Dispatch Checkpoint** (prior to worker dispatch)                           | Predecessor artifact revisions with `accepted` parent status (or validated diagnostic failure findings under explicit correction scope), declared scope, and operational permissions (acceptance != operational authorization). | `dispatch_eligible` vs `hold` / `blocked` (evaluates readiness to dispatch, not evidence success; planned checks remain unexercised).                                                             | All mandatory predecessor dependencies accepted for current revisions (or validated diagnostic failure findings consumed for scoped corrective round); dispatch worker to execute assigned scope.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| **Result Acceptance Checkpoint** (upon worker envelope return)                   | Worker envelope (`status: "pass"\|"fail"\|"blocked"`), current artifact revision snapshot, and primary observable evidence.                                                                                                     | `accepted` vs `not accepted` with criterion rationale (worker proposed pass or worker-forged `accepted` is untrusted; failure findings authorize scoped correction without unlocking downstream). | If `accepted`: all stage criteria verified by primary observable evidence matching expected outcomes, advance to next stage. If `not accepted`: retain failure findings and dispatch scoped correction (or halt); never advance downstream on unaccepted results.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| **Prefinal Coupling Checkpoint** (prior to final delivery of code-changing work) | Changed diff, affected public interfaces and caller dependencies, existing accepted `daw-review` results (feature/bugfix), or bounded diff inspection (patch).                                                                  | `coupling_accepted` vs `coupling_not_accepted` / `escalate_untangle` (recorded in parent acceptance details; not a new outer JSON envelope status).                                               | Proportional structural check satisfied ([references/change-coupling.md#prefinal-coupling-checkpoint](change-coupling.md#prefinal-coupling-checkpoint)): feature/bugfix reuses current accepted review without duplicate pass; patch completes bounded diff check (noting single-perspective fallback if without independent reviewer); docs/non-code records inline N/A. Material structural blockers absent. Bounded `daw-untangle` invoked only on demonstrated boundary obscurity.                                                                                                                                                                                                                                                                                                                                      |
| **Final Completion Checkpoint** (at workflow conclusion)                         | Audit across all pipeline stages, user acceptance criteria, and evidence freshness across all artifact revisions.                                                                                                               | `completed` vs `incomplete` (or `blocked`).                                                                                                                                                       | All required route and user criteria accepted; zero required downstream, review, or verification tasks remain pending or blocked. A completion claim additionally requires `validate.py contract --stage complete` passing with a result snapshot: durable evidence (`evidence_not_durable` rejected on every stage), evidence `sha256` present and matching (`missing_evidence_sha256`, `invalid_sha256`, `evidence_hash_mismatch`), evidence `revision` bound to `result.revision` (`missing_evidence_revision`, `evidence_revision_mismatch`), `result` present and unchanged (`missing_result`, `empty_result_files`, `result_changed`, `result_revision_unchanged`, `invalid_result_revision`, `result_not_allowed`). The validator never evaluates the semantic truth of evidence; the parent must open the evidence. |

- **Stage Acceptance vs. Final Completion Rule:** At result acceptance, accept a stage whose own required criteria and mandatory predecessors pass even when a required LATER or independent sibling stage remains pending; only final completion is withheld. A pending mandatory predecessor instead blocks dependent stage dispatch.
  <a id="evidence-reuse--invalidation-rule"></a>
- **Evidence Reuse & Invalidation Rule:** Existing evidence may be reused when current, relevant, and sufficient without arbitrary full-suite mandates. Record explicit evidence invalidation whenever the underlying artifact revision, criteria, scope, or relevant environment context changes. Do not carry forward prior passed source or runtime proof across modified artifacts without reinspection. `baseline` is the pre-change snapshot; `result` is the post-change snapshot recorded after verify. Verify evidence must be produced against `result.revision`; any edit after recording `result` invalidates completion and requires re-verify.
- **Proportional Prefinal Coupling Check Rule:** Before final completion of code-changing work, the parent orchestrator checks the changed diff and directly affected interfaces/dependencies for structural coupling ([references/change-coupling.md#prefinal-coupling-checkpoint](change-coupling.md#prefinal-coupling-checkpoint)). For feature/bugfix routes, the parent reuses the current accepted `daw-review` result for matching revision/scope without duplicate review overhead; for patch routes, the parent performs a bounded proportional diff check (documenting single-perspective fallback limits if operating without an independent reviewer) without injecting a new reviewer stage or untangle pass; for docs-only tasks, an explicit inline N/A rationale is recorded. Escalation to `daw-untangle` is strictly exceptional and reserved for demonstrated boundary obscurity over a bounded scope.
- **Separate Authorization Rule:** Parent stage acceptance verifies that execution criteria were satisfied; it NEVER constitutes operational authorization for high-risk actions (production deployment, destructive migrations, or external mutations).
- **Inline vs. JSON Representation:** Recording parent acceptance is optional in format only for single-session trivial/patch work: such work may record criteria and decisions inline within existing plan or handoff notes without extra JSON or worker ceremony. Multi-session or multi-commit work MUST persist the task contract at `docs/evidence/<task-id>/contract.json` and `daw-verify` evidence in the repo under `docs/evidence/<task-id>/` (the task-contract path convention: one contract per task directory at `docs/evidence/<task-id>/contract.json`; evidence files live alongside it or at the contract's evidence paths) before commit; inline-only acceptance is not sufficient for that scope. Multi-stage or complex workflows may use the optional parent-owned acceptance JSON structure embedded below.
- **Authorized Execution Mandatory:** Verification requires running actual commands against the live working environment and inspecting exit codes, stdout, and stderr. Merely printing or echoing a command, asserting file presence, or ticking a task checkbox is NOT execution.
- **Scoped Pause/Resume & Canonical Block State in Records:** When an execution node cannot proceed due to missing material decisions, unanswered human queries, or ungranted high-risk approvals, it halts as canonical `status: "blocked"`. The parent orchestrator or pausing module records the halt details in the parent acceptance record or module handoff details: `blocked_reason`, `responsible_party`, `pending_question_or_decision`, `next_permitted_action`, `current_revisions`, `pending_dependencies`, and `verified_evidence`. In non-interactive contexts, an unanswered query NEVER constitutes tacit approval. On resume, the orchestrator re-evaluates the blocking condition, artifact revisions, prerequisites, and operational authorizations before re-dispatching.
- **Proportional Invalidation & Document Gate Re-Entry:** Modifying implementation code invalidates affected runtime verification evidence and postbuild reviews, but does NOT invalidate accepted specification documents. Code edited after a `result` snapshot invalidates completion (`result_changed`) and requires re-verify against the new `result.revision`. When formal accepted specification documents are modified, they MUST re-enter the existing five-edge document transition gate (`review-rework` -> `rework-review` -> `review-ready`). Agents MUST NOT invent a non-existent transition named `rework`.

<a id="correction-loop--route-re-entry"></a>

### Correction Loop & Route Re-Entry

This section is the single canonical definition of where an error loops back and when the loop must stop. It adds no route, stage, or schema; it names the existing edges so no agent has to improvise them.

**Where the loop lives.** The loop is not inside a module. It is the parent-owned edge out of the **Result Acceptance Checkpoint**: a stage whose criteria fail, or whose evidence is missing, stale, or contradicted, is `not accepted`; the parent then records a bounded correction scope and re-dispatches into the earliest stage that can actually change the failing artifact.

| Failing evidence                                                 | Re-enter at                                                                   | Rationale                                                                      |
| :--------------------------------------------------------------- | :---------------------------------------------------------------------------- | :----------------------------------------------------------------------------- |
| Wrong behavior, cause unknown; reproduction unclear              | `daw-debug`                                                                   | Diagnosis precedes another edit; never patch a symptom whose cause is unknown. |
| Cause known, fix or plan step wrong                              | `daw-build` (bounded correction scope)                                        | Re-implement only the failing scope; no re-plan ceremony for a settled cause.  |
| Cause known but tasks, order, or scope of the plan are wrong     | `daw-plan`                                                                    | Reconcile the plan before more code changes.                                   |
| Requirement or acceptance criterion itself is wrong or ambiguous | existing design/clarification route, or `spike` when the unknown is technical | Do not "fix" code against an unvalidated requirement.                          |
| Review finding of hidden behavior change in a `refactor`         | `daw-build` under the characterization oracle                                 | Restore equivalence or split the change out as `feature`/`bugfix`.             |
| CI `real failure` or reviewer `must-fix` on the `ship` route     | `patch`/`bugfix`/`feature`/`maintain`/`refactor` via the parent               | `daw-ship` never edits product code; the fix re-enters a build route.          |
| Structural coupling that makes the change unsafe                 | bounded read-only `daw-untangle` diagnosis, then `daw-plan`                   | Analysis only; no mutation authority.                                          |

**Round definition.** One correction round = one parent-recorded correction scope, one re-dispatch of the affected stage(s), and one fresh acceptance evaluation on the resulting revision. Every code change invalidates affected review and runtime evidence for prior revisions (see [Evidence Reuse & Invalidation Rule](#evidence-reuse--invalidation-rule)); a round is never counted as converged because an older revision passed.

**Caps and escalation.** Module-local caps apply as written: `daw-debug` 2 consecutive non-narrowing hypotheses and 3 hypotheses per symptom; inner loop 3 failures of the same check without a new hypothesis; `daw-ship` 3 review rounds per thread; `spike` time-box ([developer-lifecycle.md §2](developer-lifecycle.md#2-time-boxing--escalation-budgets)). At the workflow level:

- **Progress test:** a round made progress only if it reduced the set of failing criteria, or replaced an unproven cause with a proven one. Re-running the same failing criterion with a different guess is not progress.
- **Escalate after 3 non-progressing rounds** on the same criterion set, or at the first tighter lifecycle cap (the [build iteration cap](developer-lifecycle.md#2-time-boxing--escalation-budgets) of 5 edit-verify cycles per criterion measures the same loop per criterion): stop re-dispatching `daw-build`, record the failing evidence, and escalate to `daw-debug` (unknown cause), `daw-plan` (wrong decomposition), or the user (external blocker, requirement conflict, or a decision the agent cannot make).
- **Hard stop at 3 escalation cycles** in one workflow: halt as `blocked` with the full round log, or return to the parent for an explicit scope change. Silent continuation past this point is forbidden.
- **Blocked is not a loop.** Missing approvals, missing environments, and unanswered questions are `blocked`, not a correction round; retrying them without new information is forbidden.

**Terminal outcomes.** Every loop ends in exactly one recorded state: `accepted` (criteria verified on the current revision), `replanned` (a new plan supersedes the failing tasks), `blocked` (named missing prerequisite or decision), or `abandoned` (scope dropped with a stated reason and the evidence retained). Reporting "still failing" without one of these four is not a valid handoff.

### Parent-Owned Acceptance Record

The parent orchestrator writes and owns the acceptance record after independent inspection of primary evidence. Worker-supplied `details` are NOT parent-owned decisions. The parent may annotate its own details or handoff record after independent inspection; any worker envelope claiming a `parent_decision` or self-granted acceptance—even if formatted identically—is strictly untrusted.
Parent evaluators MUST copy exact task and criterion IDs and cited observation references directly from predeclared dispatch contracts; never synthesize missing source content. Any missing, mismatched, or extraneous criterion IDs constitute an incomplete handoff and strictly preclude stage acceptance. Before accepting a completion claim the parent must open the evidence (the validator never evaluates semantic truth of evidence) and confirm the `result` snapshot (post-change, after verify) and evidence bindings: durable references (`evidence_not_durable`), `sha256` match (`missing_evidence_sha256`, `invalid_sha256`, `evidence_hash_mismatch`), `revision` equal to `result.revision` (`missing_evidence_revision`, `evidence_revision_mismatch`), and `result` integrity (`missing_result`, `result_not_allowed`, `invalid_result_revision`, `empty_result_files`, `result_changed`, `result_revision_unchanged`).

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
   - **Patch Route:** The patch route remains strictly streamlined (`daw-build` -> `daw-verify`). The parent orchestrator performs a bounded, proportional inspection of the changed diff and directly affected interfaces. It MUST NOT mandate a new intermediate reviewer stage or routine `daw-untangle` escalation. A structurally-free local patch MAY record one-line N/A only after that bounded diff confirms no affected interface, shared state, order, or cross-module dependency; file count alone never exempts demonstrated risk. When operating without an independent review stage, the parent explicitly notes the single-perspective verification fallback limitation in its acceptance record rather than claiming simulated independent acceptance.
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
   - **Applicable Route Retry & Stop Rules:** Corrective iterations follow the canonical [Correction Loop & Route Re-Entry](#correction-loop--route-re-entry) (re-entry edges, round definition, progress test, escalation caps) plus the module-local caps named there; no new ad-hoc caps are invented. Executed criteria that fail retain status `fail`; unexercised prerequisites or missing approvals become `blocked`.

4. **Observability & Acceptance Record:**
   - Coupling verification is recorded directly within existing plan, handoff, or parent checkpoint records. It requires NO mandatory new files, custom schemas, or hidden storage.
   - Populates existing fields inline: `scope` (paths and interfaces evaluated), `revision` (artifact revision snapshot), `evidence` (accepted review ref, diff inspection summary, or untangle finding IDs), and `disposition` (`accepted`, `not accepted`, or `N/A` with clear rationale).
   - Before final delivery, the parent answers the canonical three questions of [`references/change-coupling.md#prefinal-coupling-checkpoint`](change-coupling.md#prefinal-coupling-checkpoint) inside these existing fields — affected interfaces/dependencies; essential vs. accidental coupling with evidence; sufficient evidence or specific unresolved boundary plus disposition/escalation reason. Do not duplicate the canonical trigger table here; cite and follow it.
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

### Workflow Resume & Durable Progress Checkpoint

The REQUIRED parent-owned durable progress record and its resume/revalidation rules are owned canonically by [Workflow Artifacts](workflow-artifacts.md) (§3–§4). Do not maintain a second optional resume summary. The parent opens the progress record at intake, updates it only on real phase entry/acceptance, correction, block/resume, relevant revision change, stop, or final, and on resume revalidates current references, reconstructs mandatory predecessor joins, and preserves retry state before any dispatch. Read-only modules never write it and never gain write authority from it.

Scoped revalidation: reload the progress record and spec/plan revisions, verify the blocking condition cleared and approvals still bind to the current action/target/revision/scope, inspect referenced handoffs and primary evidence, and treat missing or stale evidence as unverified (not an accepted prerequisite). Invalidate only the affected scope on revision change; never carry prior pass proofs across modified artifacts without reinspection.

Optional worker retention (continued completed-worker identity in the owning session) is distinct from this durable-artifact requirement and remains optional per [Persistent Worker Graphs](#persistent-worker-graphs-harness-native) above.

### Optional OMP Mapping

When exposed by the host, `task` creates workers, `write agent://ID` continues a retained
idle/parked worker, and results arrive automatically; use `wait` only when blocked.
Observe successful continuation before relying on it. A drained `workpool` is not a
retained worker graph. Other harnesses may expose different tools or no continuation;
apply the capability/fallback rules above rather than requiring OMP commands.
<a id="native-workflow-tracking-and-scheduling"></a>

## Native Workflow Tracking & Scheduling

At intake, “discover the actual native task/todo tracker” means inspecting exposed harness tools/documentation and reusing still-applicable observed discovery: record in the existing plan/handoff which native tracker is present, its name/ID namespace, and the observed schema/fields — never assume a fixed client, vendor, or field set, and never enable global settings to obtain one.

### Tracker binding & separation of execution from acceptance

1. When a native tracker is present: bind each stable plan task ID to its native ref (create or reuse the actual ref if the tracker supports it); parent updates in the tracker derive only from observed worker lifecycle transitions.
2. A worker's `done`/`pass` is a proposal, not parent acceptance. The tracker MUST NOT duplicate authoritative acceptance status: the structured plan/handoff and [Parent Acceptance Checkpoint](#parent-acceptance-checkpoint) remain the authority — the tracker references them (e.g. tracker item → plan task ID + current revision + acceptance record ref). Static plan desired dependencies and criteria are preserved in the plan; the tracker carries execution progress only. Parent acceptance is recorded per [Parent-Owned Acceptance Record](#parent-owned-acceptance-record), never by writing `accepted` into the tracker from a worker claim.
3. If a tracker lacks fields (identity, revision, evidence), carry those in the existing handoff/plan records — never claim the native tracker supports them. A UI-only step completion or checkbox MUST NOT be interpreted as entire-task success.
4. No automatic external issue creation, state resets, or global scans. Existing worker graph continuity is unchanged.

### Structured fallback (no tracker)

When no native tracker exists, use structured records in the existing plan/handoff (task ID, owner, depends_on, acceptance_criteria, verification_command, evidence, status) as the record. The native fallback complements the mandatory durable multi-step artifacts owned by [Workflow Artifacts](workflow-artifacts.md): a chat payload or native todo alone cannot substitute for the saved plan or parent-owned progress record, and the parent-only durable record remains the authority for multi-step work. Parent-only updates write the progress record; workers return proposals that the parent records after inspection. Evidence unavailable means `unexercised`, never a fake pass.

### Native DAG/batch scheduling

When the harness exposes a native DAG/batch scheduler, the parent MAY use it for independent, disjoint items (non-overlapping write ownership). It MUST NOT dispatch success-dependent consumers on automatic worker completion alone: consumers dispatch only after the parent's current-revision acceptance joins the predecessor (per [Mandatory Pre-Dispatch Dependency Joins](#parent-acceptance-checkpoint)). If the scheduler cannot represent that gate, hold at a phase boundary until parent acceptance; corrective dispatch consumes validated failure findings per existing correction rules.
