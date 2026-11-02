# Wireframe & Layout Specification: [Interface / Surface]

> **Fill-in Guidance:** Fill this template for user interfaces, visual CLI layouts, or terminal dashboards. Equivalent existing UI mocks or Figma frame links may be referenced directly. Mark N/A with rationale if the change has no visual or layout interface (e.g. backend service, batch worker, internal API). Visual states (empty, loading, populated, partial, error) are required only when applicable to the surface; mark unneeded states as N/A with rationale rather than inventing unnecessary UI elements. Do not invent decorative graphics, branding elements, or speculative UI states. Distinguish user requirements from author-proposed layout defaults using a concise provenance ledger or explicit labels. Unresolved layout questions block only impacted layout implementation. Never include secret values or credentials in templates.

> **Status:** Draft (default for new documents; set to Approved only with exact observed human/provider approval evidence)
> **Owner:** [Supplied/verified owner name or role; otherwise Unassigned — requires owner decision]
> **Scope:** [Screens, modal flows, views, or CLI terminal screens]
> **Source Documents / Revision:** [Actual observed PRD, design.md, or relative path (marked unversioned if revision unobserved); never invent synthetic tags like @initial]
> **Assumptions:** [Target viewports, rendering engine, terminal/browser capabilities]
> **Open Decisions:** [Material layout questions — block impacted layout coding until resolved]
> **Acceptance Criteria IDs:** [WIRE-01, WIRE-02, ...]

---

## 1. Screen Hierarchy & Navigation Flow

- **Parent Screen / Entry Point:** [URL, route, command, or screen triggering this layout]
- **Child Screens / Drill-Downs:** [Modal dialogs, drawers, secondary tabs, sub-routes]
- **Exit Paths:** [Back navigation, cancellation, completion routes]

## 2. Layout Structure & Content Blocks

_Represent layout structure using ASCII or text hierarchy. Do NOT invent decorative assets or non-existent brand components._

```text
+------------------------------------------------------------------+
| Header / Breadcrumbs: [Application / Current Location]           |
+------------------------------------------------------------------+
| Main Workspace / Viewport                                        |
|  - Content Area (Primary data presentation / form inputs)        |
|  - Action Panel (Submit, Cancel, Secondary actions)              |
+------------------------------------------------------------------+
| Status Bar / Footer (Context info, pagination, keybindings)      |
+------------------------------------------------------------------+
```

## 3. Screen States Matrix

_Define states applicable to this surface; mark N/A with justification if not applicable._

- **Empty State:** [Appearance and actionable call-to-action when zero records exist, or N/A]
- **Loading / Skeleton State:** [Visual structure while data resolves asynchronously, or N/A]
- **Populated State:** [Standard visual structure with representative data items, or N/A]
- **Partial / Filtered State:** [Visual feedback when filters match a subset or zero items, or N/A]
- **Error / Fault State:** [Visual representation when fetch or mutation fails, or N/A]

## 4. Responsive & Breakpoint Adjustments

- **Mobile (<640px):** [Stacking behavior, collapsed drawers, bottom sheets, or N/A]
- **Tablet (640px - 1024px):** [Grid column adjustments, visible tabs, or N/A]
- **Desktop (>1024px):** [Multi-column split, persistent navigation, or N/A]
