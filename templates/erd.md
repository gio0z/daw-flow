# Entity-Relationship Document (ERD): [System / Feature]

> **Fill-in Guidance:** Fill this template using verified repository terms and observable facts adhering to the canonical shared procedural contract in [Canonical Document Quality & Workflow Transition Guide](../references/document-quality.md#feature-delivery-contract) and artifact persistence in [Workflow Artifacts](../references/workflow-artifacts.md). An adequate separate existing model may be linked or reused directly; do not duplicate it. The 14 specification types represent an available matrix, NOT a mandatory creation bundle. Select this ERD only when persisted entities or relationships are introduced, materially changed, or adopted without an adequate existing model. Mark N/A with scoped rationale — e.g. no persistent model applies, or an existing separate model already covers the scope — and do not force a model where none applies. Do not invent a physical schema, storage layout, or migration authorization: expected shape does not equal an enforced schema. Distinguish user requirements and observed source facts from author-proposed defaults using a concise provenance ledger or explicit labels (`[User Requirement]`, `[Observed Fact]`, `[Proposed Default]`). Record proposed/default vs decided. Unresolved model questions block only impacted paths, not unrelated work.

> **Status:** Draft (default for new documents; set to Approved only with exact observed human/provider approval evidence)
> **Owner:** [Supplied/verified owner name or role; otherwise Unassigned — requires owner decision]
> **Scope:** [Bounded persistent entities, relationships, and any storage choices warranted]
> **Source Documents / Revision:** [Actual observed blueprint, FRD, techstack, or relative path (marked unversioned if revision unobserved); never invent synthetic tags like @initial]
> **Assumptions:** [Storage engine capabilities and domain assumptions relied upon]
> **Open Decisions:** [Material modeling or storage questions — block impacted paths until resolved]
> **Acceptance Criteria IDs:** [ERD-01, ERD-02, ...]
> **Reader & Core Task:** [Data architect / backend engineer / implementer] — Locate persistent entities, identity, relationships and integrity rules without requiring ambient memory.
> **Quality Reference:** Canonical rubric and transition gate criteria in [references/document-quality.md](../references/document-quality.md) (common `DQ-01`..`DQ-05` and `erd-01`..`03`), [Feature Delivery Contract](../references/document-quality.md#feature-delivery-contract) (specifically [Governance Alignment](../references/document-quality.md#a-governance-and-authoring-alignment), [Clarification](../references/document-quality.md#b-clarification-and-technical-uncertainty-resolution), and [Feature Slicing](../references/document-quality.md#c-feature-slicing-and-behavioral-contract-oracles)), [EARS Semantic Guidance](../references/document-quality.md#acceptance-criteria-ears) (the single canonical source for acceptance-criteria semantics), and [Workflow Artifacts](../references/workflow-artifacts.md) (spec/plan/progress/mockup persistence and ownership).
>
> - **erd-01 (Entities & Identity):** Are the logical persistent entities, their identity, and their sourced attributes defined?
> - **erd-02 (Relationships & Ownership):** Are relationships expressed with cardinality, optionality, and ownership?
> - **erd-03 (Integrity, Lifecycle & Traceability):** Are integrity, lifecycle, and traceability rules defined, with physical design (PK/FK, indexes, deletion) only where storage choices warrant it?

---

## 1. Logical Model — Entities & Identity

_Table: one row per persistent entity. Attributes are sourced; mark each as `[User Requirement]`, `[Observed Fact]`, or `[Proposed Default]`. Do not invent attributes._

| Entity         | Identity (natural / surrogate)                  | Attributes (sourced)                | Source / Provenance                                     |
| :------------- | :---------------------------------------------- | :---------------------------------- | :------------------------------------------------------ |
| `[EntityName]` | [How instances are identified; uniqueness rule] | `[name: type, constraints, source]` | `[User Requirement / Observed Fact / Proposed Default]` |

- **Identity rules:** [Uniqueness, stability, and reuse of identifiers across entities and versions]
- **Scoped N/A:** [If no persistent model applies, record `N/A` with scoped rationale here and for the affected checks below]

## 2. Relationships, Cardinality, Optionality & Ownership

_Table: one row per relationship between entities. Direction and ownership matter; do not duplicate Blueprint flows or FRD behavior contracts._

| Relationship | From -> To             | Cardinality                                 | Optionality                       | Owner                          | Deletion / Lifecycle Effect                          |
| :----------- | :--------------------- | :------------------------------------------ | :-------------------------------- | :----------------------------- | :--------------------------------------------------- |
| `[RelName]`  | `[EntityA -> EntityB]` | `[one-to-one / one-to-many / many-to-many]` | `[required / optional, per side]` | `[Owning entity or component]` | [What happens to related instances on delete/retire] |

- **Ownership:** [Which entity or component owns each relationship and is responsible for enforcing it]
- **Unidirectional vs. bidirectional:** [Whether the relationship is navigable from one or both sides, and why]

## 3. Integrity, Lifecycle & Traceability

- **Integrity constraints:** [Uniqueness, referential, temporal, or domain constraints that must hold for persisted data]
- **Lifecycle states:** [Creation, update, archival, and retirement of persistent entities; valid transitions and forbidden transitions]
- **Traceability:** [Links from each entity/relationship to the REQ/AC IDs, FRD sections, or Blueprint flows that require it; reverse links from those documents to this ERD]
- **Consistency expectations:** [Cross-entity consistency and ordering guarantees applicable to persisted data, or scoped N/A with reason]

## 4. Physical Design (Conditional — Only When Storage Choices Warrant It)

_Record a physical design only when a storage choice has been made and warrants it. Otherwise record `N/A` with scoped rationale. Never invent a schema, indexes, keys, or migration authorization without a decided storage driver._

| Physical Detail | Applies?      | Detail                                                             |
| :-------------- | :------------ | :----------------------------------------------------------------- |
| Primary keys    | `[Yes / N/A]` | [Key choice and rationale, when storage warrants]                  |
| Foreign keys    | `[Yes / N/A]` | [Referential enforcement mechanism, when warranted]                |
| Indexes         | `[Yes / N/A]` | [Indexes and the access patterns they serve, when warranted]       |
| Deletion policy | `[Yes / N/A]` | [Hard/soft deletion, cascading, or retention rule, when warranted] |

- **Storage driver:** [The decided storage technology and why it warrants physical detail, or `N/A` with reason]
- **Schema or migration authorization:** [Explicitly none unless a decided, traceable driver exists; this template never authorizes a schema change on its own]

## 5. Provenance Ledger & Open Decisions

| ID / Topic   | Classification       | Content / Decision                                  | Status   | Impacted Execution Path |
| :----------- | :------------------- | :-------------------------------------------------- | :------- | :---------------------- |
| `ERD-DEC-01` | `[Decided]`          | [Confirmed modeling or storage decision]            | Settled  | All                     |
| `ERD-DEF-01` | `[Proposed Default]` | [Author-proposed attribute or relationship default] | Proposed | Entity B                |
| `ERD-OQ-01`  | `[Open Decision]`    | [Material modeling question; blocks dependent path] | Blocked  | Entity C only           |

## 6. Document Quality & Review Checks

_Verify against canonical [Document Quality Rubric](../references/document-quality.md) before workflow transitions. Mark N/A with rationale where proportional to scope._

- [ ] **erd-01:** Are the logical persistent entities, their identity, and their sourced attributes defined?
- [ ] **erd-02:** Are relationships expressed with cardinality, optionality, and ownership?
- [ ] **erd-03:** Are integrity, lifecycle, and traceability rules defined, with physical design (PK/FK, indexes, deletion) included only where storage choices warrant it?
