---
applyTo: "**/*"
---

For production code, require explicit error behavior, input validation, authorization, structured audit events, observable health signals, safe timeouts, bounded retries, idempotency where retries are possible, and no silent data loss.

Use exact decimal or domain money types for monetary values. Do not use binary floating point for balances, prices, quantities, fees, rates, or settlement amounts unless an authoritative design explicitly requires it.

Treat timestamps as timezone-aware and define business date, cutoff, ordering, and clock-skew behavior.
