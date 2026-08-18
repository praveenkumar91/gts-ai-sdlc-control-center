---
name: p7-verification
description: "P7-specific pre-completion verification skill. Use when: about to mark any P7 task, fix, or feature as done, before submitting a PR, or before handing off to the next pipeline stage. Auto-triggers on: 'done', 'complete', 'finished', 'ready for review', 'should work now', 'I've implemented'."
systems: [p7]
extends: skills/common/sdlc-verification
---

# P7 Verification

**Extends: skills/common/sdlc-verification**

Applies the common verification checklist (Code Quality → Testing → Security → Documentation → Integration) with P7-specific layer build commands, the 12-step new-view checklist, and end-to-end WebSocket integration verification.

## The Rule

```
CLAIM DONE ONLY AFTER RUNNING, NOT AFTER WRITING
```

"It should work" is not verification. Evidence is verification. Every layer has observable evidence of correctness — collect it.

---

## Layer-Specific Verification

### Frontend (React/TypeScript)

- [ ] TypeScript compiles without errors: `cd gts.p7.frontend && npx tsc --noEmit`
- [ ] New/modified tests pass: `npm test -- --testPathPattern=<path>`
- [ ] Full test suite passes (no regressions): `npm run test`
- [ ] No `console.log` statements: `grep -rn "console\.log" src/`
- [ ] No hardcoded URLs: `grep -rn "localhost\|:8080\|:3000" src/`
- [ ] `useShallow()` on all object/array selectors: `grep -n "use[A-Z].*({" src/`
- [ ] Real-time data flows via `useBroadcastStore`, not local component state
- [ ] Component renders correctly in the app (manual or snapshot test)
- [ ] Multi-window behaviour tested if `BroadcastChannel` is involved

### Middleware (Node.js/Express)

- [ ] Entry point loads without errors: `cd middleware && node -e "require('./src/index.js')"`
- [ ] New routes are reachable: `curl http://localhost:<port>/api/<route>` returns expected response
- [ ] No `console.log` statements: `grep -rn "console\.log" src/`
- [ ] No ES `import` statements (CommonJS only): `grep -rn "^import " src/`
- [ ] Winston logger calls present for new logic: `grep -rn "logger\." src/`
- [ ] Socket.IO event names match frontend handler names exactly
- [ ] Faye WebSocket subscription channel matches PE emit channel name

### Pricing Engine (C++17)

- [ ] Builds without errors: `cd gts.p7.pricingengine/obj-debug && make -j4`
- [ ] C++ unit tests pass: run the relevant test binary in `test/`
- [ ] Python REST tests pass: `python3 test/testWrapper.py --env=005 --root=$(pwd)`
- [ ] New Crow route registered in `CrowHandler` and responding: `curl http://localhost:<pe-port>/api/<endpoint>`
- [ ] WebSocket push verified in logs when the trigger condition occurs
- [ ] No memory leaks: new objects have matching constructors/destructors

### Database (CMDB / PEDB)

- [ ] SQL scripts run without errors against a test instance
- [ ] DDL is migration-safe (ALTER TABLE, not DROP+CREATE)
- [ ] New/modified queries return expected data (run manually and verify)
- [ ] Foreign key constraints intact after all changes
- [ ] Rollback path documented (how to undo this migration)

---

## New View Checklist (12 Steps)

When adding a new AG Grid view or page, verify ALL 12 steps are complete:

1. - [ ] Grid ID added to `GridIds.tsx`
2. - [ ] API URL key(s) added to `constants/urlConfig.tsx`
3. - [ ] Zustand slice file created and registered in `useStore.tsx`
4. - [ ] Service object created using `axiosApi`
5. - [ ] Page component created in `pages/` with `memo()` applied
6. - [ ] Sub-components created in `component/` (if needed)
7. - [ ] Route added to the router configuration
8. - [ ] Express route added in `middleware/src/routes/api/`
9. - [ ] PE REST endpoint (`.cxx/.hxx`) created and registered in `CrowHandler`
10. - [ ] Socket.IO event name wired end-to-end: PE → middleware emit → `useBroadcastStore` handler
11. - [ ] Jest tests written and passing for the new slice and service
12. - [ ] Python REST tests written and passing for the new PE endpoint

---

## Integration Verification (Multi-Layer Changes)

When changes span layers, verify the end-to-end data flow explicitly:

- [ ] PE produces correct data (verified in PE logs or `curl` REST response)
- [ ] Middleware receives PE data (verified in Winston logger output)
- [ ] Middleware emits correct Socket.IO event (verify event name + payload shape)
- [ ] Frontend receives event and `useBroadcastStore` is updated (verify in React DevTools or temp log)
- [ ] Grid/component renders the new data (manual verification)

---

## Final "Done" Gate

Run this before reporting any task as DONE:

- [ ] Every changed file is saved and syntactically valid
- [ ] Tests were RUN, not just written
- [ ] Failing tests (RED) failed for the right reason before implementation
- [ ] Passing tests (GREEN) pass after implementation
- [ ] No test passes trivially (e.g., `expect(true).toBe(true)`)
- [ ] Build succeeds for all changed layers
- [ ] No TODO / FIXME / placeholder left in code
- [ ] Acceptance criteria from the plan are verifiably met

**If any box is unchecked — you are not done.**

---

## Common "Done" Anti-Patterns

| Anti-Pattern | Reality |
|---|---|
| "I've written the code, it should work" | Evidence required. Run it. |
| "The test is there, so it's covered" | Did you run the test? Did it fail first (RED)? |
| "It compiled, so it's fine" | Compilation ≠ correctness |
| "Middleware has no tests so I can skip" | Manual `curl` verification is required |
| "The logic is the same as the existing pattern" | Run it and verify. Patterns can be wrong. |
| "I'll double-check after the PR" | Verification before, not after. |
