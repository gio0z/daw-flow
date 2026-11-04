# Domain Modeling & Architecture Decision Protocol

This reference defines the on-demand domain modeling and Architecture Decision Record (ADR) protocol for `daw-design`. It guides how design agents extract, ground, introduce, and persist domain terms and architectural decisions without fabricating agreements, forcing uncoordinated glossary paths, or rewriting history.

_Reference Links:_

- [Shared Grilling Protocol](../../../references/grilling.md)
- [Builder-Readiness Protocol](builder-readiness.md)
- [Parent Design Specification](../SKILL.md)
- [Shared Routing Reference](../../../references/routing.md)
- [Root Governance Specification](../../../SKILL.md)

---

## 1. Core Principles

1. **Grounded Reality & Legitimate Proposal:**
   - Ground existing domain vocabulary in observable codebase facts (source code, schemas, existing documentation).
   - Do NOT fabricate pre-existing consensus or claim an observed source for newly minted terms.
   - Agents MAY legitimately propose new domain concepts or entities required by the design; clearly mark them as `[Agent Recommendation]` or `[Human Decision]` once accepted, distinguishing them from `[Observed Fact]`.

2. **Inspect Existing Conventions First:**
   - Inspect repository patterns before creating files (e.g., `docs/adr/`, `doc/decisions/`, `docs/specs/`, `architecture/`, or embedded sections in `blueprint.md`).
   - Do NOT force a generic `/GLOSSARY.md` or arbitrary directory structure if the repo uses an alternative pattern or embeds terms directly in specifications. Reuse or update existing glossary entries when confirmed; preserve genuine terminology conflicts as unresolved until a legitimate decision is reached.

3. **Explicit Write-Authorization Boundary & Lazy Documentation:**
   - **Inspect / Read-Only by Default:** The design module inspects domain reality without modifying workspace files.
   - **Persistence Rule:** Persist settled domain models or ADRs ONLY if the user's task explicitly authorizes document authoring within an approved scope (e.g., updating `docs/specs/blueprint.md` or an existing ADR path).
   - **Fallback without Authorization:** If document authoring is not explicitly authorized in the task scope, return proposed terms, definitions, and decisions directly to the parent orchestrator in the handoff details without writing files.
   - Waive formal modeling for routine fixes or straightforward extensions.

---

## 2. Resolving Semantic Overload via Concrete Scenarios

When a domain term carries multiple competing meanings across modules or boundaries (e.g., "Account" meaning authentication identity vs. billing profile):

1. **Avoid Abstract Debates:** Ground the term in concrete operational scenarios rather than theoretical definitions.
2. **Identify Bounded Contexts:** Trace data ownership, identity lifecycle, and invariants per subsystem:
   - **Owning Subsystem:** Which module owns and mutates the entity.
   - **Consumer Boundary:** How outside modules interact with it (opaque ID, read-only projection, or domain event).
   - **Invariants:** Core business rules that must remain true in this context.
3. **Preserve Conflicts until Settled:** If competing interpretations cannot be resolved from existing evidence, preserve the ambiguity as an open question or resolve via the [Shared Grilling Protocol](../../../references/grilling.md); never fabricate an artificial compromise.

---

## 3. Architecture Decision Record (ADR) Conjunctive Gate

Author a dedicated ADR **only** when a decision meets all three conjunctive conditions:

1. **Hard-to-Reverse:** High migration, replacement, or refactoring cost (e.g. foundational storage engine, cross-service communication protocol, core data boundary).
2. **Non-Obvious without Context:** Rationale and constraints cannot be readily inferred from the resulting codebase or standard conventions.
3. **Genuine Architectural Trade-Off:** Involves deliberate sacrifice between competing quality attributes (e.g. consistency vs. latency, strict normalization vs. read performance).

**When the Gate Fails:**

- If any condition is absent, do NOT author a standalone ADR.
- Record material architectural choices directly within an authorized existing specification document (e.g., the Architecture section of `blueprint.md`).
- Trivial or routine implementation choices require no formal record.

### Decision Provenance Ledger

Distinguish origins to keep architectural history transparent:

- `[Observed Fact]`: Backed by existing workspace files, configurations, or schemas.
- `[Human Decision]`: Explicitly requested, confirmed, or approved by the user.
- `[Agent Recommendation]`: Proposed by the agent based on architectural analysis.

### Superseding History

When architectural constraints shift, **NEVER rewrite or delete past decision records**:

- Historical ADRs document why a choice was sound under historical conditions.
- Record changes in a new ADR that explicitly references the old one (`Supersedes: ADR-XXX`), updating the old record status to `Superseded`.
