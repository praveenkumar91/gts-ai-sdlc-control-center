---
name: ingest-specifications
description: Build a versioned, cited context pack from large authoritative specifications, DFS or FSD documents, interface contracts, architecture records, data definitions, policies, and existing code. Use before planning or implementation whenever a request depends on complex or distributed requirements.
---

# Ingest Specifications

1. Read `.github/sdlc/sources.json` and classify each source as normative, supporting, or informative.
2. Record the source path or URI, version, revision date, and SHA-256 when locally available.
3. Search by business terms, interface names, data entities, control identifiers, and cross-references.
4. Expand every referenced normative section needed to interpret the selected text.
5. Draft `context-pack.json` and `ingestion-diagnostics.json` payloads under
   `.github/sdlc/runs/<change-id>/work/`.
6. Cite source ID, section, page or anchor, and exact version for every extracted rule.
7. Record contradictions, missing sources, unreadable content, and undefined terminology.
8. Mark the run `BLOCKED_SPEC` when a high-criticality rule is ambiguous or a required normative source is unavailable.

Never silently choose between conflicting specifications. Never treat model memory, comments, or implementation behavior as authoritative when a normative source exists.

Record both payloads with `sdlc_engine.py record-artifact` as producer
`spec-ingestion`. Use `PASS` only when the deterministic source snapshot is
PASS and the cited context is complete. Let the engine create the envelopes.
