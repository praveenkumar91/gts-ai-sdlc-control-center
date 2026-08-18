# GUI evidence contract

A GUI PASS package must contain:

1. UI contract identifier and approved plan digest.
2. Requirement-to-journey and requirement-to-test mapping.
3. Exact frontend and dependent backend commit SHAs.
4. Browser, operating-system image and viewport matrix.
5. Component and end-to-end results.
6. Reference, actual and diff screenshots for every changed approved surface.
7. Accessibility scan results and manual keyboard/focus assessment.
8. Trace and video locations for critical journeys and failures.
9. Currency, precision, date, timezone, stale-data and authorization checks.
10. Performance measurements against approved budgets.
11. Known limitations and open findings.

Required minimum states are normal, loading, empty, partial, validation error, server error, timeout, disconnected and unauthorized. Critical transaction screens also require confirmation, duplicate-action prevention, cancellation, stale-price/data handling and reconciliation visibility.

Automated accessibility evidence does not replace human accessibility or inclusive user assessment when policy requires it.
