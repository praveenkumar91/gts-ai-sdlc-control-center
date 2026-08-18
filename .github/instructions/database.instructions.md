---
applyTo: "**/*.{sql,ddl,liquibase.xml,yaml,yml}"
---

Require migration ownership, compatibility analysis, data-volume assumptions, locking analysis, online migration strategy, validation query, rollback or forward-fix plan, and tested behavior with mixed application versions.

Never perform destructive schema or data changes in the same step that removes compatibility. Never assume a transaction protects operations across independent systems.
