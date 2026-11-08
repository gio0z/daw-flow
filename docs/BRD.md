# Business Requirements Document (BRD)

## Deterministic Agentic Workflow

### 1. Business Problem & Motivation

Autonomous AI coding agents frequently suffer from non-deterministic divergence when given unstructured or conversational tasks. High-level requests result in hallucinations, scope drift, unverified assumptions, and destructive alterations to codebases without baseline comparison. Existing agent frameworks often treat reasoning and execution as an undivided continuum, leading to:

1. **Unbounded Generative Execution:** Generative reasoning is applied directly to filesystem writes without pre-flight planning contracts.
2. **Missing Invariants:** Project conventions, capability boundaries, and architectural invariants are lost between sessions.
3. **Implicit or Hallucinated Completion:** Agents claim tasks are completed based on generative confidence rather than deterministic, machine-verifiable proof.
4. **Heavy Runtime Overhead:** Many workflow frameworks introduce complex server infrastructure, binary compilation requirements, or heavyweight runtime dependencies that impair portability across diverse developer environments.

### 2. Strategic Vision & Core Principles

This project provides a portable, document-driven planning, routing, and verification framework for AI coding agents based on the architectural principle:

> _"Otaknya boleh generative, tangannya harus deterministic."_ (Generative reasoning for cognitive planning; deterministic execution and verification for system state).

The business goal is not financial monetization or SaaS subscription revenue, but developer productivity, verification rigor, and zero-dependency ecosystem adoption across local development workspaces, containerized CI environments, and multi-agent harnesses.

### 3. Business Goals & Objectives

- **BG-01: Zero-Dependency Portability:** Deliver a workflow specification, suite router, and verification tool that executes anywhere Python 3.10+ standard library is present, requiring zero external package installation or build steps.
- **BG-02: Structured Pre-Code Governance:** Mandate structured planning via a 14-document specification matrix (baseline six + conditional ERD), declarative route manifest, and JSON task contracts prior to code modification.
- **BG-03: Modular Skill Specialization & Deep Boundaries:** Provide an integrated suite router (`SKILL.md`) and specialized modular skills (`skills/daw-*`: design, plan, debug, build, review, verify, workspace, ask, setup, wizard, untangle) with deep operational procedures, avoiding recursive skill sprawl and preventing persona impersonation.
- **BG-04: Deterministic Fail-Closed Verification:** Provide verifiable CLI validation of package integrity (`validate.py`), suite routing (`route.py --check-suite`), and contract lifecycles with deterministic exit codes (0 for ready/pass, 1 for violations/needs-input, 2 for malformed syntax/invocation).
- **BG-05: Portable Skill Interoperability:** Conform strictly to portable Agent Skills standards (`SKILL.md` with declarative frontmatter, reference docs, canonical templates, and bundled sibling symlink distribution).
- **BG-06: Defensible Audit Trail & Risk Constraints:** Ensure approvals, baseline hashes, and acceptance criteria are captured as machine-readable artifacts. High-risk operations flag constraints (`interactive_approval_required: true`, `authorization_granted: false`) without simulating runtime authority.

### 4. Target Stakeholders & User Persona

- **Autonomous Coding Agents:** Primary automated consumers of `SKILL.md`, template documents, and task contract schemas. Agents require unambiguous routing tables, explicit file requirements, and strict exit boundaries.
- **Software Engineers & Developers:** Human practitioners collaborating with agents. They require predictable diffs, explicit approval checkpoints before high-risk changes, and zero environmental lock-in.
- **Platform & Security Operators:** Maintainers responsible for repository health, automated quality gates, and compliance auditability.

### 5. Success Metrics & Evidence Criteria

- **Adoption Friction:** Time-to-first-validation under 5 seconds on any environment with Python 3.10+, verified by running `scripts/validate.py package` and `scripts/route.py --check-suite`.
- **Test Integrity:** 100% test pass rate across all baseline unit tests in `tests/test_validate.py` and `tests/test_route.py` without requiring third-party library installation.
- **Specification Coverage:** Complete, actionable reference documentation across all 14 document templates (baseline six plus conditional ERD), 11 specialized modular skills, and runtime specification documents.
- **Zero-Failure Gate Compliance:** Verification that task contracts and routing requests fail closed whenever required fields, valid hashes, or approved boundaries are violated.

### 6. Scope Boundaries & Non-Goals

- **In Scope:**
  - **Operational Installed Package:** Suite Router and Specialized Modular Skills package (`SKILL.md`, `LICENSE`, `VERSION`, `skills/daw-*`, operational `references/`, `templates/`, and operational scripts `scripts/{install,route,validate,doc_quality,package_layout}.py`).
  - **Developer & Repository Source:** Full repository checkout including developer test suites (`tests/test_validate.py`, `tests/test_route.py`), developer evaluation tooling (`tools/evaluation/`), repository documentation (`AGENTS.md`, `CHANGELOG.md`, `docs/`), and maintainer fixtures (`tests/fixtures/wizard-bench`).
  - Read-only standard library validation and routing engine (`scripts/validate.py`, `scripts/route.py`).
  - Declarative route policy manifest (`references/suite-manifest.json`).
  - Standard library test suites (`tests/test_validate.py`, `tests/test_route.py`).
  - Complete standalone engineering documentation suite (`AGENTS.md`, `CHANGELOG.md`, `docs/BRD.md`, `docs/PRD.md`, `docs/TRD.md`, `docs/UIRD.md`, `docs/DESIGN.md`, `docs/evaluation/`).
- **Non-Goals (Explicit Exclusions):**
  - No monetization engine, SaaS billing, or payment integration.
  - No hosted web service or centralized database requirement.
  - No automated runtime code execution, shell hook, or test-running daemon inside the validator or router.
  - No persona impersonation or external identity spoofing in advisory skills (`daw-ask`).
  - No proprietary agent harness lock-in or forced standalone unbundled module distribution.
