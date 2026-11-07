# Visual Design System & Tokens: [Feature / Surface]

> **Fill-in Guidance:** Fill this template using existing repository design tokens and component libraries. Equivalent existing design files or token definitions may be linked directly. New design tokens are permitted when explicitly requested or required by new feature requirements; document them with technical rationale rather than claiming a fabricated upstream design source. Honor the repository or project's required accessibility standard for web applications (do NOT downgrade AAA if specified; default to WCAG 2.2 AA if unspecified for applicable web surfaces). For non-web environments (CLI, backend, headless services), mark web WCAG styling conformance as N/A and document platform-appropriate proposed visual/formatting conventions (e.g. ANSI colors, terminal formatting); never claim empirical screen-reader or platform compatibility absent observed tests. Mark N/A with rationale if the change has no visual styling impact. Unresolved visual questions block only impacted visual/frontend implementation. Never include secret values or credentials. For UI-affecting work, record the actual rendered mockup (editable source or durable design ref + visual preview) and its review per [workflow-artifacts §5](../references/workflow-artifacts.md) — see §5 below; prose alone is insufficient.

> **Status:** Draft (default for new documents; set to Approved only with exact observed human/provider approval evidence)
> **Owner:** [Supplied/verified owner name or role; otherwise Unassigned — requires owner decision]
> **Scope:** [Visual surfaces, design tokens, styling primitives, theme extensions]
> **Source Documents / Revision:** [Actual observed Figma/token source, PRD, or relative path (marked unversioned if revision unobserved); never invent synthetic tags like @initial]
> **Target Accessibility Baseline:** [For applicable web: WCAG 2.2 AA default, or WCAG 2.2 AAA if project/user specified — never downgrade; for non-web CLI/backend: N/A web conformance with platform-specific proposed formatting criteria — never claim empirical compatibility absent tests]
> **Assumptions:** [Existing styling framework (e.g. Tailwind, CSS variables), theme mode support]
> **Open Decisions:** [Material visual questions — block impacted visual implementation only]
> **Acceptance Criteria IDs:** [DES-01, DES-02, ...]
> **Audience & Reader Task:** Frontend engineers / designers implementing visual foundations, tokens, and design system components.
> **Quality Reference:** Canonical rubric and transition gate criteria in [references/document-quality.md](../references/document-quality.md) (common `DQ-01`..`DQ-05`, `design-01`..`design-03`).

---

## 1. Design Tokens & Core Primitives

_Document existing repository token bindings, source/reuse relationships, and design constraints. New tokens may be proposed with clear technical rationale._

- **Color Palette & Semantic Tokens:**
  - Primary / Brand: `[Existing repo token / CSS variable / class]`
  - Neutral / Surfaces: `[Background, card surface, border tokens]`
  - Feedback / Status: `[Success, Warning, Danger, Info tokens]`
  - _Proposed New Tokens (if requested):_ `[Token name, proposed value, rationale for addition]`
- **Typography Hierarchy & Scales:**
  - Heading Scales: `[Font family, weight, size, line-height]`
  - Body & Microcopy: `[Font family, weight, size, line-height]`
  - Monospace / Code: `[Font family, size, line-height]`
- **Spacing, Radius & Layout Dimensions:**
  - Spacing Scale: `[Base spacing unit / scale multipliers]`
  - Border Radii: `[Small, Medium, Large radius tokens]`
  - Container / Grid Widths: `[Max content widths, gutter sizes]`

## 2. Reusable Component Primitives

_Inventory existing repository UI primitives used to assemble this surface._

- **Component Primitives Reused:** `[e.g., Button, Modal, Card, InputField, Table from existing repo components]`
- **Variant & Property Extensions:** `[Specific props or visual variants added to existing primitives]`
- **New Primitives Required (if any):** `[Justification for why no existing component primitive fits]`

## 3. Visual Layout & Theming Rules

- **Theme Modes:** `[Light mode / Dark mode / System preference behavior]`
- **Elevation & Depth:** `[Shadow tokens, border treatments, surface layering]`
- **Visual Boundaries & Grouping:** [Visual dividers, card encapsulation, visual grouping rules]

## 4. Accessibility & Contrast Rationale

_Verify compliance against the target accessibility baseline (WCAG 2.2 AA default, or AAA if required). For non-UI / CLI / headless surfaces, mark web contrast rules N/A with rationale._

- **Text Contrast Rationale:** [Proof that normal text tokens maintain required contrast ($\ge 4.5:1$ for AA, $\ge 7:1$ for AAA) against bound surface backgrounds, or N/A with rationale for non-UI/CLI surfaces]
- **Large Text / UI Control Contrast:** [Proof that headers and interactive borders maintain required contrast ($\ge 3:1$ for AA, $\ge 4.5:1$ for AAA) against adjacent surfaces, or N/A with rationale for non-UI/CLI surfaces]
- **Color Independence:** [Visual indicators (icons, text labels, borders) ensuring meaning is not conveyed by color alone, or N/A with rationale for non-UI/CLI surfaces]

## 5. Rendered Mockup Artifact & Review Record

_Canonical timing/proof/N/A rule: [references/workflow-artifacts.md](../references/workflow-artifacts.md) §5 — apply it here, do not duplicate it. Domain/flow are settled before this mockup is authored; UI implementation follows a reviewed current mockup. Reuse an existing matching mockup where applicable (record its ref, do not force a new one). No invented assets or fabricated token sources._

- **Mockup artifact:** [Editable source or durable design ref + visual preview link(s), or `N/A` with scoped rationale (no UI / nonvisual patch reusing existing matching design)]
- **Coverage mapping:** [Requirement/AC/screen IDs → mockup screens, behavior states, viewports covered]
- **Token/component provenance:** [Existing tokens and primitives actually used in the mockup; any new token with stated rationale]
- **Review record & limits:** [Reviewer, date, observed result; static mockup labels are not runtime/click/keyboard proof — actual runtime is verified later]
- **Blocking condition:** [Material unavailable capability/direction blocks only this UI scope; no text-only fake pass]

## 6. Document Quality & Review Checks

_Verify against canonical [Document Quality Rubric](../references/document-quality.md) before workflow transitions. Mark N/A with rationale where proportional to scope._

- [ ] **design-01:** Are design tokens (e.g. colors, typography, spacing, radii) canonically defined with semantic mappings where applicable to the project interface?
- [ ] **design-02:** Are visual contrast and accessibility considerations documented against applicable standards (e.g. WCAG 1.4.3 / 1.4.11) or explicitly declared not applicable?
- [ ] **design-03:** Are reusable UI component structures, visual variants, and responsive layout rules specified for applicable surfaces?
