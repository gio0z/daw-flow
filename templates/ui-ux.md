# UI/UX & Interaction Design Specification: [Feature / Surface]

> **Fill-in Guidance:** Fill this template for interactive behaviors, state transitions, and accessibility compliance. Equivalent existing interaction specs or Storybook stories may be referenced directly. Honor the repository or project's required accessibility standard for web applications (do NOT downgrade AAA if specified; default to WCAG 2.2 AA if unspecified for applicable web surfaces). For non-web environments (CLI, backend, embedded libraries), mark web WCAG conformance as N/A and document platform-specific proposed usability/ergonomics criteria (e.g. terminal contrast, keyboard shortcuts); never claim empirical screen-reader or platform compatibility absent observed tests. Unresolved interaction questions block only impacted UI component work. Never include secret values or credentials. For UI-affecting work, record the actual rendered mockup (editable source or durable design ref + visual preview) and its review per [workflow-artifacts §5](../references/workflow-artifacts.md) — see §5 below; prose behavior specs alone are insufficient.

> **Status:** Draft (default for new documents; set to Approved only with exact observed human/provider approval evidence)
> **Owner:** [Supplied/verified owner name or role; otherwise Unassigned — requires owner decision]
> **Scope:** [Interaction behaviors, accessibility states, keyboard navigation, focus management, micro-interactions]
> **Source Documents / Revision:** [Actual observed Wireframe, PRD, or relative path (marked unversioned if revision unobserved); never invent synthetic tags like @initial]
> **Target Accessibility Baseline:** [For applicable web: WCAG 2.2 AA default, or WCAG 2.2 AAA if project/user specified — never downgrade; for non-web CLI/backend: N/A web conformance with platform-specific proposed usability criteria — never claim empirical compatibility absent tests]
> **Assumptions:** [Design system version, baseline browser/device support, input modalities]
> **Open Decisions:** [Material interaction ambiguities — block impacted UI implementation until resolved]
> **Acceptance Criteria IDs:** [UIUX-01, UIUX-02, ...]
> **Audience & Reader Task:** UI engineers / QA verifying interactive states, motion curves, keyboard navigation, and accessibility conformance.
> **Quality Reference:** Canonical rubric and transition gate criteria in [references/document-quality.md](../references/document-quality.md) (common `DQ-01`..`DQ-05`, `ui-ux-01`..`ui-ux-03`).

---

## 1. Interaction Behaviors & State Transitions

_Document state transitions for all actionable elements, covering input, state, error, focus, and keyboard accessible behavior._

- **Interactive Elements:** [Buttons, inputs, dropdowns, table rows, modal triggers]
  - **Default / Resting:** [Resting interactive visual state]
  - **Hover / Pointer:** [Pointer hover feedback and state transitions]
  - **Focus / Active:** [Visible focus indicator satisfying WCAG 2.4.7 Focus Visible, ensuring focus is not obscured per WCAG 2.4.11 (Level AA; WCAG 2.4.13 Focus Appearance at Level AAA where required, rather than an assumed universal offset); active press styling]
  - **Disabled:** [Disabled treatment with accessible explanation or tooltip if blocked]
  - **Read-Only / Permission-Denied:** [Visual representation when user lacks edit permissions; explain missing privilege]
- **Transitions & Motion:** [Subtle CSS transitions; respect `prefers-reduced-motion` to reduce or remove non-essential motion while preserving essential state feedback per WCAG 2.3.3]

## 2. Comprehensive Surface States

_Define behavior for all operational interface states:_

- **Loading State:** [Skeleton screens, inline progress indicators, disabled action triggers]
- **Empty State:** [Clear descriptive message and constructive call-to-action when zero records exist]
- **Error State:** [Inline field errors, banner alerts with actionable recovery advice]
- **Success State:** [Confirmation feedback, toast notification, view transitions]
- **Offline / Degraded State (if applicable):** [Cached view indicators, offline queue banner, retry trigger]

## 3. Responsive Reflow & Target Sizing

- **Responsive Reflow:** [Ensure content reflows down to $320\text{px}$ width without horizontal scrolling (WCAG 2.2 SC 1.4.10), or N/A with rationale for non-web/CLI interfaces]
- **Target Size Compliance:** [Adhere to required standard target-size rules: WCAG 2.2 AA SC 2.5.8 minimum $24 \times 24\text{ CSS px}$ with spacing/inline exceptions; recommend $44 \times 44\text{px}$ where feasible or if repo/AAA mandates, or N/A with rationale for non-web/CLI interfaces]

## 4. Accessibility & Keyboard Navigation

- **Keyboard Tab Order:** [Sequential order of focusable targets]
- **Keybindings & Shortcuts:** [Explicit keyboard actions, e.g., `Esc` to close, `Enter` to submit, arrow navigation]
- **ARIA & Assistive Attributes:** [Roles, `aria-expanded`, `aria-live`, `aria-label`, semantic markup]
- **Focus Management:** [Focus trapping in modal dialogues, focus restoration to trigger upon dismiss; verify focus indicator visibility (WCAG 2.4.7) and ensure focus is not obscured by sticky containers or overlays (WCAG 2.4.11)]
- **Form Validation Timing:** [Validation on blur or submit; error messages programmatically linked to fields via `aria-describedby`]

## 5. Rendered Mockup Artifact & Review Record

_Canonical timing/proof/N/A rule: [references/workflow-artifacts.md](../references/workflow-artifacts.md) §5 — apply it here, do not duplicate it. Domain/flow are settled before this mockup is authored; UI implementation follows a reviewed current mockup. Reuse an existing matching mockup where applicable (record its ref, do not force a new one). No invented assets or fabricated token sources._

- **Mockup artifact:** [Editable source or durable design ref + visual preview link(s), or `N/A` with scoped rationale (no UI / nonvisual patch reusing existing matching design)]
- **Coverage mapping:** [Requirement/AC/screen IDs → mockup screens, behavior states, viewports covered]
- **Token/component provenance:** [Existing tokens and primitives actually used in the mockup]
- **Review record & limits:** [Reviewer, date, observed result; static mockup labels are not runtime/click/keyboard proof — actual runtime is verified later]
- **Blocking condition:** [Material unavailable capability/direction blocks only this UI scope; no text-only fake pass]

## 6. Document Quality & Review Checks

_Verify against canonical [Document Quality Rubric](../references/document-quality.md) before workflow transitions. Mark N/A with rationale where proportional to scope._

- [ ] **ui-ux-01:** Are interactive component states (e.g. default, active, disabled, loading, error) specified for applicable interface elements?
- [ ] **ui-ux-02:** Are interaction behaviors, transitions, and progressive disclosure rules explicitly defined?
- [ ] **ui-ux-03:** Are keyboard navigation paths, ARIA semantics, and accessibility compliance rules (including WCAG 2.4.7 Focus Visible and WCAG 2.4.11 Focus Not Obscured) detailed for applicable UI?
