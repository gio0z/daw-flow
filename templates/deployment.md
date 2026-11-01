# Deployment & Release Specification: [Service / Release]

> **Fill-in Guidance:** Fill this template using verified release mechanisms and immutable artifact digests. Equivalent existing release PRs or deployment configs may be linked directly. Mark N/A with rationale if the change has no deployment impact (e.g. documentation, local tooling). Pre-deployment backup is N/A for stateless services or releases without state/schema mutation. Human approvals must use system references only (Change Ticket # / Review ID; never copy secret tokens or credentials). Post-deployment log inspection is scoped by relevant service, release time window, and expected severity thresholds, not an unbounded check across all logs. Unresolved release items block deployment execution only. Never record secret values or credentials in templates or evidence logs.

> **Status:** Draft / Ready for Review / Approved / Superseded
> **Owner:** [Release Engineer / DevOps Lead]
> **Scope:** [Target environment, immutable artifacts, migrations, release verification]
> **Source Documents / Revision:** [FRD, runbook.md, git commit SHA / tag]
> **Assumptions:** [Cluster capacity, target infrastructure health, network routing]
> **Open Decisions:** [Material deployment blockers — block release execution until settled]
> **Acceptance Criteria IDs:** [DEP-01, DEP-02, ...]

---

## 1. Release Identification & Artifacts

_Enforce immutable artifacts. Never deploy unpinned mutable tags._

- **Target Environment:** `[staging / production]`
- **Source Revision:** `git commit [exact-commit-sha]`
- **Immutable Artifact Digest:** `[container registry sha256 digest or release archive checksum]`
- **Configuration & Secret Reference:** `[Secret version reference / Vault path pointer — NO secret values]`

## 2. Preflight Checklist & Explicit Approval Gate

- [ ] Target environment accessibility verified.
- [ ] Pre-deployment backup verified (Identifier: `[snapshot-id]`, Status: `[verified]`, or `[N/A - Stateless / No state mutation]`).
- [ ] Database / schema migration preflight executed with dry-run/preview if applicable (or `[N/A - No migrations]`).
- [ ] **Explicit Human Approval Gate:**
  - Approving User / Identity: `[Authorized user identifier / username]`
  - Approval Reference: `[Change Ticket # / Release Approval ID — NEVER enter secret tokens]`
  - Bound Source Revision: `[Exact commit SHA / artifact digest]`
  - _Fail-Closed Policy:_ Any change in target environment, revision, or tenant context invalidates approval. If approval mechanism is unavailable, deployment MUST fail closed.

## 3. Deployment Mechanics & Migration Sequence

- **Deployment Strategy:** `[Rolling update / Canary / Blue-Green / Direct process replacement]`
- **Step 1 (Pre-release Preparation):** Execute backward-compatible schema/state additions if applicable (or N/A).
- **Step 2 (Service Update):** Roll out immutable release artifact to target environment.
- **Step 3 (Post-release Tasks):** Apply non-destructive index creation, background task triggers, or N/A.

## 4. Post-Deployment Verification & Observability

- **Health Check Endpoint / Probe:** `[GET /healthz or service health check command]`
- **Canary / Telemetry Observation:** [Error rate and latency criteria observed over specified window]
- **Key Metrics & Dashboard:** `[Dashboard link / metric queries]`
- **Scoped Log Inspection:** Verification that target service logs within release observation window show expected startup messages and no abnormal error spikes above baseline severity.

## 5. Rollback Trigger & Execution

- **Rollback Triggers:** Error budget exceeded, unhandled panic in logs, broken operational invariant.
- **Rollback Target:** Explicit known-good artifact digest: `[exact-known-good-digest]` (NEVER deploy unverified `HEAD~1` or mutable `latest`).
- **Data Recovery:** Follow `runbook.md` section 4 only if data/state corruption occurred; stateless rollbacks require artifact reversion only.
