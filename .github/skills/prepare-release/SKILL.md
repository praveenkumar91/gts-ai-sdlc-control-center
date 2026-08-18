---
name: prepare-release
description: Assemble and evaluate production release evidence, including requirement coverage, independent verification, security findings, migrations, rollback, observability, provenance, approvals, and residual risk. Use only after implementation and independent reviews finish.
---

# Prepare Release

1. Validate the evidence manifest with `.github/scripts/validate_evidence.py`.
2. Confirm the commit under review is the commit that produced all evidence.
3. Confirm all mandatory gates for the risk tier passed and no evidence is stale.
4. Confirm migrations are backward compatible or explicitly governed, tested, and reversible.
5. Confirm rollout, health signals, abort thresholds, rollback, ownership, and incident response.
6. Confirm artifacts have provenance and an SBOM when artifacts are produced.
7. Produce one decision: `RELEASE_READY`, `BLOCKED`, or `INCONCLUSIVE`.
8. Never convert missing evidence into a waiver. Require a separately authorized, time-bounded exception with an owner and compensating controls.

The release controller may assemble evidence but may not approve its own exception or production deployment.

Draft `evidence-manifest.json` and `release-decision.json` payloads under the
run's `work/` directory and record both through `sdlc_engine.py
record-artifact` as producer `release-controller`. Never create or alter the
external human-approval attestation.
