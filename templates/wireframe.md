# Wireframe & Layout Specification: [Interface / Surface]

> **Fill-in Guidance:** Fill this template for user interfaces, visual CLI layouts, or terminal dashboards. Equivalent existing UI mocks, Figma/FigCraft frames, or renderable local HTML/SVG sources may be referenced directly when actually accessible; record the source truthfully and mark unavailable capability as `unexercised`. Mark N/A with rationale if the change has no visual or layout interface (e.g. backend service, batch worker, internal API). Visual states (empty, loading, populated, partial, error) are required only when applicable to the surface; mark unneeded states as N/A with rationale rather than inventing unnecessary UI elements. Do not invent decorative graphics, branding elements, or speculative UI states. Distinguish user requirements from author-proposed layout defaults using a concise provenance ledger or explicit labels. Unresolved layout questions block only impacted layout implementation. Never include secret values or credentials in templates. For UI-affecting work, record the actual rendered mockup (editable source or durable design ref + visual preview) and its review per [workflow-artifacts §5](../references/workflow-artifacts.md) — see §5 below; ASCII structure alone is explicitly insufficient as a visual mockup.

> **Status:** Draft (default for new documents; set to Approved only with exact observed human/provider approval evidence)
> **Owner:** [Supplied/verified owner name or role; otherwise Unassigned — requires owner decision]
> **Scope:** [Screens, modal flows, views, or CLI terminal screens]
> **Source Documents / Revision:** [Actual observed PRD, design.md, or relative path (marked unversioned if revision unobserved); never invent synthetic tags like @initial]
> **Assumptions:** [Target viewports, rendering engine, terminal/browser capabilities]
> **Open Decisions:** [Material layout questions — block impacted layout coding until resolved]
> **Acceptance Criteria IDs:** [WIRE-01, WIRE-02, ...]
> **Audience & Reader Task:** Product designers / frontend developers constructing responsive page layouts, information hierarchy, and layout grids.
> **Quality Reference:** Canonical rubric and transition gate criteria in [references/document-quality.md](../references/document-quality.md) (common `DQ-01`..`DQ-05`, `wireframe-01`..`wireframe-03`).

---

## 1. Screen Hierarchy & Navigation Flow

- **Parent Screen / Entry Point:** [URL, route, command, or screen triggering this layout]
- **Child Screens / Drill-Downs:** [Modal dialogs, drawers, secondary tabs, sub-routes]
- **Reachable Navigation Transitions:** [Reachable screen transitions, navigation flows, and user orientation cues across views]
- **Exit Paths:** [Back navigation, cancellation, completion routes]

## 2. Layout Structure & Content Blocks

_Represent layout structure using ASCII or text hierarchy. Document structural container hierarchy, spatial element allocations, and responsive information priorities. Do NOT invent decorative assets or non-existent brand components._

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

_Document responsive reflow rules and information hierarchy adjustments across applicable viewports. Breakpoints should follow repository conventions; mark N/A with rationale for non-UI or fixed-layout surfaces._

- **Mobile / Compact Viewport:** [Stacking behavior, collapsed drawers, bottom sheets, prioritized essential controls, or N/A]
- **Tablet / Medium Viewport:** [Grid column adjustments, visible tabs, secondary panels, or N/A]
- **Desktop / Wide Viewport:** [Multi-column split, persistent navigation, expanded data tables, or N/A]

## 5. Rendered Mockup Artifact & Review Record

_Canonical timing/proof/N/A rule: [references/workflow-artifacts.md](../references/workflow-artifacts.md) §5 — apply it here, do not duplicate it. Domain/flow are settled before this mockup is authored; UI implementation follows a reviewed current mockup. Reuse an existing matching mockup where applicable (record its ref, do not force a new one). No invented assets or fabricated token sources._

- **Mockup artifact:** [Editable source or durable design ref + visual preview link(s), or `N/A` with scoped rationale (no UI / nonvisual patch reusing existing matching design)]
- **Design source & actual capability:** [Existing matching mockup / Figma / FigCraft / renderable local HTML/SVG or other local rendered source actually accessible and used; record the real capability exercised, or `unexercised`/`unavailable` with scoped rationale — never claim a vendor/tool was exercised when it was not]
- **File / frame reference:** [File + frame/page/section reference, or local source path]
- **Revision / snapshot:** [Revision, version, snapshot, commit, or export timestamp; mark `unversioned` if revision unobserved]
- **Visual preview:** [Actual preview link, export, screenshot, or rendered file reference; ASCII diagram above documents structure only]
- **Coverage mapping:** [Requirement/AC/screen IDs → mockup screens, behavior states, viewports covered]
- **Token/component provenance:** [Existing tokens and primitives actually used in the mockup]
- **Review record & limits:** [Reviewer, date, observed result; static mockup labels are not runtime/click/keyboard proof — actual runtime is verified later]
- **Blocking condition:** [Material unavailable capability/direction blocks only this UI scope; no text-only fake pass]

## 6. Document Quality & Review Checks

_Verify against canonical [Document Quality Rubric](../references/document-quality.md) before workflow transitions. Mark N/A with rationale where proportional to scope._

- [ ] **wireframe-01:** Are target viewports, responsive breakpoints, or presentation layouts documented for applicable interfaces?
- [ ] **wireframe-02:** Are screen layouts, structural container hierarchies, and spatial element allocations mapped using clear structural representations?
- [ ] **wireframe-03:** Are primary navigation flows, user orientation cues, and screen transitions clearly defined across views?
