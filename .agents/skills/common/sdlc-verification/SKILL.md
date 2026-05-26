---
name: sdlc-verification
description: "Generic pre-completion verification skill. Use when: about to mark a task as done, before submitting a PR, or before handing off to the next pipeline stage. Verifies completeness and quality."
systems: [all]
---

# SDLC Verification Skill

A generic pre-completion checklist to verify work quality before moving to the next pipeline stage. System-specific checklists (e.g., P7's 12-step new-view checklist) extend this with additional items.

## Universal Checklist

### Code Quality
- [ ] Code compiles / lints without errors or warnings
- [ ] No dead code, commented-out blocks, or TODO markers left in production code
- [ ] No hardcoded credentials, secrets, or environment-specific values
- [ ] Variable and function names are clear and descriptive

### Testing
- [ ] All new logic is covered by at least one unit test
- [ ] All acceptance criteria have a corresponding passing test
- [ ] Existing tests still pass (no regressions)
- [ ] Edge cases and error paths are tested

### Security (OWASP basics)
- [ ] All user inputs are validated at system boundaries
- [ ] No SQL/command injection vectors introduced
- [ ] No sensitive data logged or exposed in responses
- [ ] Authentication/authorization checks in place for new endpoints

### Documentation
- [ ] Commit message follows Conventional Commits format
- [ ] PR description is complete (summary, changes, testing notes)
- [ ] Any new API endpoints are documented

### Integration
- [ ] Changes work end-to-end in the target environment
- [ ] No breaking changes to existing interfaces (or breaking changes are documented)
- [ ] Dependent services/consumers are not broken

## Usage
Run this checklist before marking any task DONE. For system-specific verification, also run the system's skill (e.g., `p7-verification`).
