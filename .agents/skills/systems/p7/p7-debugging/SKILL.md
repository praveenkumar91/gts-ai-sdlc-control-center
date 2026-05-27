---
name: p7-debugging
description: "P7-specific systematic debugging skill. Use when: investigating any bug, test failure, unexpected behaviour, or runtime error on the P7 platform — before proposing any fix. Auto-triggers on: 'it's broken', 'not working', 'error', 'exception', 'test fails', 'why is', 'fix this bug'."
systems: [p7]
extends: skills/common/sdlc-debugging
---

# P7 Debugging

**Extends: skills/common/sdlc-debugging**

Applies the common systematic debugging protocol with P7-specific layer boundaries, log locations, debug commands, and known error patterns.

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

Complete the common skill's Phase 1–3 (Reproduce → Isolate → Hypothesize) before writing a single line of fix. "It should work" is not a root cause.

---

## P7 Layer Boundary Instrumentation

P7 has 5 observable boundaries. For any data-flow bug, instrument each boundary before touching code:

```
For each layer (PE → middleware → frontend):
  - What data enters this layer?
  - What data exits this layer?
  - Is the data correct at the boundary?
```

**Example — real-time data not appearing in the frontend grid:**
```
Boundary 1: PE WebSocket push         → Check PE logs for push events
Boundary 2: Middleware Faye receiver  → Add logger.debug at the handler entry
Boundary 3: Socket.IO emit            → Log event name + payload before emit
Boundary 4: Frontend useBroadcastStore → Add console.debug in the effect (temp only)
Boundary 5: Component / AG Grid       → Verify selector value in React DevTools
```

Identify WHICH boundary loses data before proposing a fix.

---

## Layer-Specific Debug Techniques

### Frontend (React/TypeScript)

| Tool | How to Use |
|------|-----------|
| Browser DevTools Console | Runtime errors, uncaught exceptions |
| Vite dev server output | TypeScript compilation errors, HMR failures |
| React DevTools | Component tree, prop values, store state |
| Zustand devtools middleware | Inspect store slice state in browser |
| Network tab → WS frames | Inspect raw Socket.IO messages arriving at frontend |

**Commands:**
```bash
cd gts.p7.frontend && npx tsc --noEmit     # TypeScript type errors
npm test -- --testPathPattern=<path>        # Run targeted Jest test
grep -rn "useShallow" src/                  # Verify useShallow usage on selectors
grep -rn "console\.log" src/               # Find forbidden console.log calls
```

### Middleware (Node.js)

| Tool | How to Use |
|------|-----------|
| Winston log output | `logger.debug` at handler entry/exit points |
| Express error handler | Unhandled route errors surface here |
| wscat / websocat | Connect to PE WebSocket channel to verify push |

**Commands:**
```bash
cd middleware && node -e "require('./src/index.js')"   # Syntax / load errors
grep -rn "console\.log" src/                           # Find forbidden logs
grep -rn "^import " src/                               # Find forbidden ES imports
```

Add temporary `logger.debug('handler reached', { payload })` at the top of any handler under investigation. Remove after debugging.

### Pricing Engine (C++17)

| Location | What It Contains |
|----------|-----------------|
| CMake/make output | Build errors, missing includes, linker errors |
| Crow exception logs | HTTP route errors and unhandled exceptions |
| PE stdout/stderr | Runtime log output (follows logger calls in codebase) |

**Commands:**
```bash
cd gts.p7.pricingengine/obj-debug && make -j4          # Build — shows compile errors
python3 test/testWrapper.py --env=005 --root=$(pwd)    # Python REST tests
curl http://localhost:<pe-port>/api/<endpoint>          # Verify endpoint responds
```

### Database (CMDB / PEDB)

- Run queries manually against a test instance to verify data before blaming code
- Check MySQL error codes in the query context (foreign key violations, column not found)
- Confirm which database you are targeting: **CMDB** (`gts.p7.common.controller-monitor.database/commondb/`) vs **PEDB** (`gts.p7.pricingengine/sql/schema/`)

---

## P7-Specific Error Patterns

| Layer | Error Pattern | Root Cause |
|-------|--------------|------------|
| Frontend | Infinite re-render loop | `useShallow()` missing on object/array selector |
| Frontend | Data never updates in grid | Real-time data stored in component state instead of `useBroadcastStore` |
| Frontend | Stale data after WebSocket event | Selector not subscribing to the correct store slice key |
| Middleware | Silent failure in handler | `console.log` used instead of Winston — no output in production |
| Middleware | Route not found (404) | New route file not `require()`-d in the router |
| Middleware | WS never receives PE data | Faye subscription channel name does not match PE emit channel |
| PE | 404 on new REST endpoint | Endpoint `.cxx` registered in its own file but not added to `CrowHandler` |
| PE | WebSocket push never fires | Push call exists but subscription or trigger condition is not wired up |
| Integration | Socket.IO event never arrives | Event name in middleware `emit()` differs from frontend `socket.on()` handler name |
| Database | Migration fails silently | DDL uses DROP+CREATE instead of migration-safe ALTER TABLE |
| Database | Wrong data returned | Query targets CMDB when it should target PEDB, or vice versa |

---

## P7 Red Flags — Stop and Re-investigate

If you catch yourself thinking any of the following, return to Phase 1:

- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "It's probably the Zustand selector — let me tweak it"
- "The PE and middleware look fine, must be the frontend" (assumed, not verified)
- "One more fix attempt" (when 2+ have already been tried)

**If 3+ fix attempts have failed**: stop and question the architecture. Each fix revealing new coupling in a different place is an architectural signal, not a debugging failure.

---

## Quick Phase Reference

| Phase | Key Activity | Done When |
|-------|-------------|-----------|
| 1. Root Cause | Read full errors, reproduce, instrument layer boundaries | Know WHAT fails and WHERE |
| 2. Pattern Analysis | Find working P7 example, compare differences | Know HOW it should work |
| 3. Hypothesis | Form one theory, test minimally (one change at a time) | Confirmed or new hypothesis |
| 4. Implementation | Write failing test, fix root cause, verify all tests pass | Bug resolved, no regressions |
