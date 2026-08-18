---
name: compile-requirements
description: Convert cited specification evidence into atomic, uniquely identified functional, non-functional, security, data, operational, migration, and regulatory requirements with measurable acceptance criteria. Use after specification ingestion and before architecture or coding.
---

# Compile Requirements

1. Read the frozen context pack for the change.
2. If a normative source cannot be read, a GUI baseline or affected state is
   missing, or an acceptance decision would require guessing, stop and ask the
   user concrete questions through the program intake clarification gate.
3. Create a frozen `source_set` with stable source IDs, versions, content
   SHA-256 values and locators; calculate `source_set_digest` from that exact
   inventory.
4. Create one atomic requirement per independently verifiable obligation.
5. Assign stable IDs without reusing deleted identifiers.
6. Include source citations, criticality, rationale, owning implementation repositories, dependencies, stable acceptance-criterion IDs, invariants, and required evidence.
7. Express acceptance criteria as observable outcomes without prescribing implementation unless the source requires it.
8. Build the per-change `verification` matrix. Map every owning repository to
   its reusable configured gate IDs, and map every acceptance-criterion ID and
   required evidence type to explicit repository or integration gate IDs.
9. Never put change-specific requirement IDs into a repository's reusable
   quality configuration; the frozen requirements own that mapping.
10. Add negative cases, boundary conditions, concurrency behavior, failure behavior, recovery behavior, and backward compatibility.
11. Draft `requirements.json`, `ambiguities.json`, and `source-coverage.json`
   payloads under `.github/sdlc/runs/<change-id>/work/`.
12. Validate the requirements payload with the requirements schema.
13. Block progression when a critical requirement lacks a citation, measurable acceptance criteria, complete verification mapping, or an accountable decision.

Do not invent business rules. Label derived requirements as `derived` and cite the evidence and reasoning that produced them.

Record all three payloads with `sdlc_engine.py record-artifact` as producer
`requirements-engineer`. Let the engine bind evidence to the commit and create
the immutable envelopes.
