# Skill Change History

## 2026-11-01: Portable Package and Read-Only Validator

- Made the core and all 13 document routes self-contained; external specialists are optional capability enhancements, not installation dependencies.
- Added a Python 3.10+ standard-library CLI for package checks and strict plan/execute/complete JSON task contracts, with text/JSON reports and exit codes 0/1/2.
- Bound referenced paths to their roots before reads; covered symlink escapes, encoded/reference Markdown links, nested fences, metadata scalars, duplicate JSON keys, baseline drift, approval binding, and evidence coverage.
- Approval references are not authorization; evidence files are not authenticated proof; declared risk and revision identifiers are not independently verified. No runtime hooks were installed.
- Verification: 56 regression tests passed on Python 3.14.7/Linux, including the full suite from a copied package in an unrelated working directory. Package validation and syntax compilation passed. Read-only CLI smoke snapshots were unchanged; changed scope, missing approval references, and missing completion evidence were rejected.
- Other Python versions, operating systems, and client discovery integrations remain untested. Python language-server diagnostics were unavailable; syntax compilation and executable tests were used instead.
- Repository distribution is private; this entry does not claim live deployment, database restoration, or cross-client runtime enforcement.

## 2026-11-01: Audit Remediation & Deterministic Execution Refinement

- **Scope:** Complete remediation of audit findings across managed skill `deterministic-agentic-workflow`.
- **Proportional 13-Doc Contract Matrix:** Established the full 13-doc specification matrix (1 core system blueprint + 12 derivative specifications in `templates/`). Replaced mandatory-bundle assumptions with impact-driven selection (routine bugfixes require no new docs unless a material gap exists; internal backend PRDs omit frontend/SEO/UX docs; frontend changes with security impact enforce security contracts or equivalent existing security specifications).
- **Removed Unsafe Rollback Mechanics:** Replaced generic `HEAD~1`, `latest`, and unverified newest-file restorations with explicit immutable snapshot IDs, digest resolution, schema compatibility checks, and test restoration status. Distinguished redeploying known-good releases from `git revert` code commits. Preserved unrelated user workspace modifications.
- **Fail-Closed Point-of-Risk Approvals:** Codified strict fail-closed approval defaults. Distinguished reviewed inactive drafts from active apply/publish commands. Mandated explicit interactive user confirmation for shared/live database schema modifications, production deployments, secret changes, and protected branch pushes. Defined approval invalidation triggers for target, tenant, revision, or plan drift.
- **Surface-Tailored Semantic Verification:** Replaced superficial HTTP 200 / exit code 0 checks with semantic proof on actual modified surfaces (API schemas, CLI output, rendered UI components, tenant isolation). Mandated factual audit records distinguishing passed, failed, blocked, and unexercised states, with strict secret/PII redaction.
- **Opt-In Background Maintenance:** Bound maintenance loops to explicit user opt-in with defined monitoring sources, metrics thresholds, evaluation windows, rate limits, kill-switches, and no automated PR publishing by default. Prohibited claiming active daemons without observed running processes and sample telemetry.
- **Tool Reuse Over Compulsory Scripts:** Eliminated compulsory wrapper creation for repeat actions; existing CLI and build automation are prioritized directly.
- **Specialist Routing & Missing Specialist Policy:** Prohibited router recursion and unsuited silent fallbacks for missing specialist skills. Defined explicit low-risk inline capability vs. blocking escalation.
- **Source Separation:** Explicitly cited source article (Rama Digital — _Agentic Tapi Deterministic Workflow AI Agent_) and separated core architectural principles from local workstation and multi-agent operational extensions.
- **Verification Status:** Verified by parent integration checks across 17 markdown files, 13 templates, 13x9 routing fields, 32 installed target skills, zero broken links/fences, and 10/10 isolated dry-run scenario tests (routine patch, internal BRD, backend PRD, frontend security, stale contract, changed approval, rollback, maintenance, missing skill, and semantic proof). No live deployment or destructive restore executed.
