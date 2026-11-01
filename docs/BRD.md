# Business Requirements Document (BRD)

## Deterministic Agentic Workflow

### 1. Business Problem & Motivation

Autonomous AI coding agents frequently suffer from non-deterministic divergence when given unstructured or conversational tasks. High-level requests result in hallucinations, scope drift, unverified assumptions, and destructive alterations to codebases without baseline comparison. Existing agent frameworks often treat reasoning and execution as an undivided continuum, leading to:

1. **Unbounded Generative Execution:** Generative reasoning is applied directly to filesystem writes without pre-flight planning contracts.
2. **Missing Invariants:** Project conventions, specialist boundaries, and architectural invariants are lost between sessions.
3. **Implicit or Hallucinated Completion:** Agents claim tasks are completed based on generative confidence rather than deterministic, machine-verifiable proof.
4. **Heavy Runtime Overhead:** Many workflow frameworks introduce complex server infrastructure, binary compilation requirements, or heavyweight runtime dependencies that impair portability across diverse developer environments.

### 2. Strategic Vision & Core Principles

This project provides a portable, document-driven planning, routing, and verification framework for AI coding agents based on the architectural principle:

> _"Otaknya boleh generative, tangannya harus deterministic."_ (Generative reasoning for cognitive planning; deterministic execution and verification for system state).

The business goal is not financial monetization or SaaS subscription revenue, but developer productivity, verification rigor, and zero-dependency ecosystem adoption across local development workspaces, containerized CI environments, and multi-agent harnesses.

### 3. Business Goals & Objectives

- **BG-01: Zero-Dependency Portability:** Deliver a workflow specification and verification tool that executes anywhere Python 3.10+ standard library is present, requiring zero external package installation or build steps.
- **BG-02: Structured Pre-Code Governance:** Mandate structured planning via a 12-to-13 document specification matrix and JSON task contracts prior to code modification.
- **BG-03: Deterministic Fail-Closed Verification:** Provide verifiable CLI validation of package integrity and contract lifecycles with deterministic exit codes (0 for pass, 1 for violations).
- **BG-04: Portable Skill Interoperability:** Conform strictly to portable Agent Skills standards (`SKILL.md` with declarative frontmatter, reference docs, and canonical templates).
- **BG-05: Defensible Audit Trail:** Ensure all approvals, baseline hashes, and acceptance criteria are captured as machine-readable artifacts, making code changes auditable over time.

### 4. Target Stakeholders & User Persona

- **Autonomous Coding Agents:** Primary automated consumers of `SKILL.md`, template documents, and task contract schemas. Agents require unambiguous routing tables, explicit file requirements, and strict exit boundaries.
- **Software Engineers & Developers:** Human practitioners collaborating with agents. They require predictable diffs, explicit approval checkpoints before high-risk changes, and zero environmental lock-in.
- **Platform & Security Operators:** Maintainers responsible for repository health, automated quality gates, and compliance auditability.

### 5. Success Metrics & Evidence Criteria

- **Adoption Friction:** Time-to-first-validation under 5 seconds on any environment with Python 3.10+, verified by running `scripts/validate.py package`.
- **Test Integrity:** 100% test pass rate across all 56 baseline unit tests in `tests/test_validate.py` without requiring third-party library installation.
- **Specification Coverage:** Complete, actionable reference documentation across all 13 document templates and 5 runtime specification documents.
- **Zero-Failure Gate Compliance:** Verification that task contracts fail closed whenever required fields, valid hashes, or approved boundaries are violated.

### 6. Scope Boundaries & Non-Goals

- **In Scope:**
  - Portable Agent Skills specification package (`SKILL.md`, `references/`, `templates/`).
  - Read-only standard library validation engine (`scripts/validate.py`).
  - Standard library test suite (`tests/test_validate.py`).
  - Complete standalone engineering documentation suite (`AGENTS.md`, `docs/BRD.md`, `docs/PRD.md`, `docs/TRD.md`, `docs/UIRD.md`, `docs/DESIGN.md`).
- **Non-Goals (Explicit Exclusions):**
  - No monetization engine, SaaS billing, or payment integration.
  - No hosted web service or centralized database requirement.
  - No automated runtime code execution or test-running daemon inside the validator.
  - No proprietary agent harness lock-in.
