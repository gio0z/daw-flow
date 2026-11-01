# Product Requirements Document (PRD): [Feature Name]

> **Fill-in Guidance:** Fill this template using verified product outcomes and observable acceptance criteria. Equivalent existing specs or feature briefs may be reused directly. Mark N/A with rationale if not applicable (e.g. pure refactors or internal bugfixes). Do not invent user personas, market stats, UI flows for non-UI features, or speculative acceptance criteria. Non-UI features (CLI, backend, workers) must focus on programmatic actors and operational outcomes. Unresolved questions block only impacted feature paths.

> **Status:** Draft / Ready for Review / Approved / Superseded
> **Owner:** [Product Manager / Tech Lead]
> **Scope:** [Product surface: CLI, API, Service, or User Interface]
> **Source Documents / Revision:** [Source issue, BRD, or document@rev]
> **Assumptions:** [User capability, data availability, or platform baseline]
> **Open Decisions:** [Material product questions — block impacted feature paths until settled]
> **Acceptance Criteria IDs:** [PRD-01, PRD-02, ...]

---

## 1. Problem Statement & Target Actor

- **Target Actor:** [API client, system administrator, internal operator, or end user]
- **Core Problem:** [Concrete workflow breakdown or unmet need with observed evidence]
- **Context of Use:** [Circumstances under which the actor encounters this problem]

## 2. Product Objectives & Observable Outcomes

- **Desired Behavior:** [What the actor or consuming system can accomplish after completion]
- **Key Tenets:** [Simplicity, determinism, transparency, or zero-latency overhead]
- **Explicit Non-Goals:** [Adjoining features or workflows explicitly excluded from this iteration]

## 3. User & System Scenarios

_Applicable to UI screens, CLI commands, or programmatic backend consumers. Do not force UI flows for backend or CLI features._

- **Primary Scenario:** [Step-by-step progression of the happy path]
- **Edge Scenario 1:** [Invalid inputs, partial data, or missing prerequisites]
- **Edge Scenario 2:** [Timeouts, network degradation, or conflicting concurrent actions]

## 4. Acceptance Criteria Matrix

- **PRD-01:** Given [preconditions], when [action taken], then [observable state change / response].
- **PRD-02:** Given [preconditions], when [invalid action], then [deterministic error returned].

## 5. Dependencies & Non-Functional Expectations

- **Cross-Service Dependencies:** [Upstream services, external APIs, shared libraries]
- **Performance Expectations:** [Target response latency or throughput within known system constraints]
- **Telemetry & Logging:** [Required user action events or audit milestones]
