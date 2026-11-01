# Operational Runbook: [Service / Feature]

> **Fill-in Guidance:** Fill this template using verified repository commands, scripts, and parameters. Equivalent existing ops manuals or runbooks may be reused directly. Do not invent executable commands, script paths, CLI flags, or mock "HEALTHY" output strings. Critical operations require explicit human approval by reference only (ticket ID / approval request ID; never include secret values or credentials). Rollback must target an explicit known-good release; database or state restoration snapshot is required ONLY when data recovery is applicable (stateless services roll back artifact without database restoration). Preflight backups require verified integrity and restore-test status (mark N/A for stateless or harmless operations). Unresolved material operational questions block impacted operations only. Never record secret values or credentials in templates or evidence logs.

> **Status:** Draft / Ready for Review / Approved / Superseded
> **Owner:** [Site Reliability Engineer / On-Call Lead]
> **Scope:** [Service operations, preflight gates, fail-closed approval, incident triage, recovery]
> **Source Documents / Revision:** [FRD, deployment.md, git commit SHA]
> **Assumptions:** [Access permissions, verified backup schedule, available monitoring tools]
> **Open Decisions:** [Material operational questions — block impacted deployment/operations only]
> **Acceptance Criteria IDs:** [OPS-01, OPS-02, ...]

---

## 1. Preflight Verification Checklist & Explicit Approval Gate

_All checks must pass before executing critical operations._

- [ ] Target environment accessibility verified.
- [ ] Configuration and environment variable pointers confirmed against validated schema (no secrets in logs/templates).
- [ ] **Pre-Flight Backup / State Snapshot (Mark N/A for stateless/harmless ops):**
  - Snapshot Identifier / Reference: `[verified-snapshot-id or N/A - Stateless / Read-only operation]`
  - Snapshot Verification Status: `[Integrity checksum verified / restore-test passed / N/A]`
- [ ] **Explicit Human Approval Gate:**
  - Approving User / Identity: `[Authorized user identifier / username]`
  - Approval Reference: `[Change Ticket # / PR Review ID / Approval System Reference — NEVER enter secret tokens]`
  - Explicit Action Scope: `[Exact operation authorized, e.g., deploy release vX, run migration]`
  - Target Environment & Tenant Scope: `[Exact target environment and tenant boundary]`
  - Data Impact Boundary: `[Specific schemas, tables, or directories affected, or N/A for stateless]`
  - Approval Expiration / TTL: `[Timestamp or window after which approval is void]`
  - _Fail-Closed Policy:_ Prior approval is immediately invalidated if source revision, target environment, action scope, or tenant context changes. When approval interface or mechanism is unavailable, execution MUST fail closed. Document presence never substitutes for live approval.

## 2. Standard Operational Procedures (SOP)

_Fill in verified repository commands and proven arguments. Do not invent hypothetical scripts._

### Procedure A: Routine Health & Diagnostic Inspection

- **Command / Path:** `[Verified repo command or script path]`
- **Required Arguments / Flags:** `[e.g., --target=<environment> --timeout=<duration>]`
- **Command Provenance:** `[Existing repo script / package manager command / CI step]`
- **Observed Healthy Verification:** [Concrete observable condition, e.g., expected HTTP status, process exit code 0, specific field value in response]
- **Degraded / Failure Conditions:** [Specific exit codes, error output patterns, or timeout criteria]

### Procedure B: Schema / State Migration Execution

- **Dry-Run / Inspection Procedure:** `[Verified repo migration command with dry-run/preview flag, or documented schema diff inspection if dry-run flag unsupported, or N/A if stateless]`
- **Execution Command:** `[Verified repo migration execution command, or N/A]`
- **Required Parameters:** `[Target database, migration direction, explicit backup reference ID]`
- **Approval Requirement:** Requires explicit human approval gate prior to running execution command.

## 3. Incident Triage & Emergency Response

_Define triage steps and containment actions. Do not default to traffic draining or service disruption unless specifically justified by incident conditions._

- **Triage Checklist:**
  1. _Elevated Error Rate:_ [Specific log search query, error pattern, or metric dashboard to inspect]
  2. _Elevated Latency:_ [Specific resource pool or upstream dependency to verify]
  3. _Data Boundary / Auth Anomaly:_ [Immediate containment action, notification pathway, and escalation procedure]
- **Targeted Containment Action (if justified):**
  - Command / Action: `[Verified command for targeted rate-limiting, circuit-breaking, or maintenance routing]`
  - Justification Required: [Conditions under which containment is authorized]

## 4. Rollback & State Restoration Protocol

_CRITICAL: Rollback MUST target an explicitly verified, known-good release artifact. Snapshot restoration is required ONLY when state/data corruption occurred. For stateless services or releases without data corruption, execute Step 2 only. Any state restoration procedure must preserve later concurrent writes and verify schema compatibility._

- **Step 1 (Containment):** Apply approved containment action if active traffic is causing state degradation.
- **Step 2 (Release Artifact Reversion):**
  - Verified Target Release: `[Exact known-good artifact digest or release commit SHA]`
  - Release Deployment Command: `[Verified deployment command with explicit release identifier]`
- **Step 3 (Targeted State Restoration - ONLY If Data Recovery Applicable):**
  - Data Recovery Needed: `[Yes / No - Stateless or uncorrupted state requires no restoration]`
  - Recovery Scope: `[Specific tables, partitions, or records impacted by the incident]`
  - Verified Snapshot Identifier: `[Specific pre-migration snapshot ID taken immediately prior to release]`
  - State Compatibility & Concurrent Write Preservation: `[Documented procedure to restore affected scope without clobbering concurrent unrelated tenant writes or valid subsequent records]`
  - Restoration Command: `[Verified database restoration command with explicit snapshot ID]`
- **Step 4 (Post-Rollback Verification):**
  - Verification Check: `[Specific queries or test cases demonstrating restored service health and data consistency for affected scope]`

## 5. Escalation & Contact Directory

- **Primary On-Call:** `[On-call engineer handle / Pager link]`
- **Secondary On-Call / Escalation Lead:** `[Lead engineer handle]`
- **Security Incident Response:** `[Security team channel / on-call]`
