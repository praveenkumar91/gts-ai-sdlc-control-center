---
name: assess-security
description: Perform an independent security and operational-risk assessment for production financial software, including abuse cases, access control, data integrity, auditability, secrets, dependencies, supply chain, privacy, resilience, and control evidence. Use for every production change with depth determined by risk tier.
---

# Assess Security

1. Read the requirement set, threat model, design, diff, dependency changes, and verification results.
2. Test authentication, authorization, tenant or account isolation, least privilege, and privileged operations.
3. Test injection, deserialization, path handling, cryptography, secrets, logging, privacy, and error disclosure.
4. Evaluate order duplication, replay, race conditions, numeric precision, time zones, stale data, partial failure, reconciliation, and audit gaps.
5. Review new dependencies, licenses, provenance, known vulnerabilities, build inputs, and artifact attestations.
6. Map findings to requirement and threat IDs with severity, exploitability, evidence, and remediation.
7. Block release for unresolved critical or high findings and for unapproved security exceptions.

Do not accept a model-generated assurance statement as security evidence.

Draft `security-report.json` under the run's `work/` directory and record it
through `sdlc_engine.py record-artifact` as producer `security-reviewer`. The
adversarial reviewer must independently record `adversarial-review.json`; do
not create it on that reviewer's behalf.
