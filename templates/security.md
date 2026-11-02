# Security Specification & Threat Model: [Feature / Service]

> **Fill-in Guidance:** Fill this template for sensitive assets, authorization rules, and threat vectors using actual controls approved for the repository or environment. Equivalent existing threat models or security RFCs may be linked directly. Mark N/A with rationale only if there is zero impact on data, auth, tenancy, dependencies, or external surfaces. Do not use fixed placeholder protocols (like TLS 1.3 or zero-trust) unless verified as applicable; record actual controls and note unresolved applicability. Security risk ratings and classifications must be labeled as proposed assessments rather than verified facts. Frontend changes with token storage, DOM rendering, or script injection impact MUST be analyzed here. The security exit gate records the review status of planned mitigations and verification evidence (drafting does not require a finalized zero-CVE proof). Unresolved security items block impacted execution paths until reviewed. Never include secret values or credentials in templates.

> **Status:** Draft (default for new documents; set to Approved only with exact observed human/provider approval evidence)
> **Owner:** [Supplied/verified owner name or role; otherwise Unassigned — requires owner decision]
> **Scope:** [Data boundaries, authentication, authorization, external surfaces, front-end security impact]
> **Source Documents / Revision:** [Actual observed FRD, techstack.md, or relative path (marked unversioned if revision unobserved); never invent synthetic tags like @initial]
> **Assumptions:** [Network perimeter, trust zones, underlying cryptography primitives]
> **Open Decisions:** [Material security trade-offs — block impacted execution until resolved and approved]
> **Acceptance Criteria IDs:** [SEC-01, SEC-02, ...]

---

## 1. Sensitive Assets & Data Classification

| Asset / Data Element             | Classification            | Storage Location                    | In-Transit Protection          | Retention & Deletion Policy         |
| :------------------------------- | :------------------------ | :---------------------------------- | :----------------------------- | :---------------------------------- |
| `[e.g., API Keys / Secrets]`     | `[Confidential / Secret]` | `[Approved secret store / env ref]` | `[Approved channel control]`   | `[Key rotation / cleanup policy]`   |
| `[e.g., User PII / Identifiers]` | `[Restricted / Internal]` | `[Encrypted DB / Secure Store]`     | `[Approved transport control]` | `[Data lifecycle / retention rule]` |
| `[e.g., Session Identifiers]`    | `[Internal / Sensitive]`  | `[Session store / Auth cookie]`     | `[Approved transport control]` | `[Session TTL / expiry rule]`       |

## 2. Trust Boundaries & Tenant Isolation

- **Perimeter Boundaries:** [Network ingress, gateway, service boundaries, or local IPC]
- **Tenant Separation:** [Tenant identifier binding, query scoping, or multi-tenant isolation mechanisms]
- **Cross-Tenant Guardrail:** [Deterministic rejection of queries or mutations lacking verified tenant scope]

## 3. Authentication & Authorization Matrix

- **Authentication Mechanism:** [Session management, OAuth2/OIDC, tokens, or local credentials per repo architecture]
- **Role-Based Access Control (RBAC):**
  - **Role [Admin / Privileged]:** [Explicit permissions allowed]
  - **Role [Standard User / Member]:** [Explicit permissions allowed; actions forbidden]
  - **Anonymous / Unauthenticated:** [Allowed public operations, or N/A if all require authentication]

## 4. Threat Modeling & Targeted Mitigations

_Identify relevant threat vectors (e.g. STRIDE / OWASP) and specify concrete approved mitigations. Note unresolved applicability._

- **Threat Vector 1 (e.g., IDOR / BOLA / Cross-Tenant Access):**
  - **Impact:** [Cross-tenant data exposure or unauthorized mutation]
  - **Specific Mitigation:** [Enforce tenant ownership validation in service/query layer before data access]
  - **Negative Verification:** [Negative test proving request across tenant boundaries is deterministically denied]
- **Threat Vector 2 (e.g., Frontend Token Exposure / Script Injection):**
  - **Applicability:** [Applicable if web/UI interface handles sensitive tokens or untrusted user content, else N/A]
  - **Specific Mitigation:** [Threat-specific control, e.g. appropriate cookie storage flags, CSP header, or input sanitization per repo standard]
  - **Negative Verification:** [Test verifying malicious payload is escaped and auth credentials inaccessible to script]

## 5. Security Verification Gates & Evidence Status

- [ ] Threat model and planned mitigations reviewed and approved by security owner.
- [ ] Negative authorization tests planned/passing (unauthenticated request rejected, wrong-role request rejected, cross-tenant access denied).
- [ ] Secrets scanning verified (no embedded credentials or hardcoded keys in code or templates).
- [ ] Dependency vulnerability assessment status: `[Scheduled / In-progress / Passed without blocking CVEs]`.
