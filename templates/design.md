# Visual Design System & Tokens: [Feature / Surface]

> **Fill-in Guidance:** Fill this template using existing repository design tokens and component libraries. Equivalent existing design files or token definitions may be linked directly. New design tokens are permitted when explicitly requested or required by new feature requirements; document them with technical rationale rather than claiming a fabricated upstream design source. Honor the repository or project's required accessibility standard (do NOT downgrade AAA if specified; default to WCAG 2.2 AA if unspecified). Mark N/A with rationale if the change has no visual styling impact. Unresolved visual questions block only impacted visual/frontend implementation. Never include secret values or credentials.

> **Status:** Draft / Ready for Review / Approved / Superseded
> **Owner:** [Design Engineer / Frontend Engineer]
> **Scope:** [Visual surfaces, design tokens, styling primitives, theme extensions]
> **Source Documents / Revision:** [Figma/token source, PRD, or design system ref@rev]
> **Target Accessibility Baseline:** [WCAG 2.2 AA default, or WCAG 2.2 AAA if project/user specified — never downgrade]
> **Assumptions:** [Existing styling framework (e.g. Tailwind, CSS variables), theme mode support]
> **Open Decisions:** [Material visual questions — block impacted visual implementation only]
> **Acceptance Criteria IDs:** [DES-01, DES-02, ...]

---

## 1. Design Tokens & Core Primitives

_Document existing repository token bindings. New tokens may be proposed with clear rationale._

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

_Verify compliance against the target accessibility baseline (WCAG 2.2 AA default, or AAA if required)._

- **Text Contrast Rationale:** [Proof that normal text tokens maintain required contrast ($\ge 4.5:1$ for AA, $\ge 7:1$ for AAA) against bound surface backgrounds]
- **Large Text / UI Control Contrast:** [Proof that headers and interactive borders maintain required contrast ($\ge 3:1$ for AA, $\ge 4.5:1$ for AAA) against adjacent surfaces]
- **Color Independence:** [Visual indicators (icons, text labels, borders) ensuring meaning is not conveyed by color alone]
