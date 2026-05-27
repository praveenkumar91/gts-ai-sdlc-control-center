---
name: p7-brainstorming
description: "P7-specific design exploration skill. Use when: planning a new feature, new view, new endpoint, or any change to the P7 platform — before touching any code. Auto-triggers on: 'add', 'build', 'create', 'implement', 'new feature', 'new view', 'new endpoint', 'change how'."
systems: [p7]
extends: skills/common/sdlc-brainstorming
---

# P7 Brainstorming

**Extends: skills/common/sdlc-brainstorming**

Applies the common brainstorming protocol (Clarify → Options → Risks → Recommend → Acceptance Criteria) with P7-specific layer analysis, architecture decision prompts, and data flow impact assessment.

## Hard Gate

```
DO NOT write any code, scaffold any files, or invoke any implementation skill
until the design is approved by the user.
```

This applies to every request regardless of perceived simplicity — "simple" features have the most unexamined assumptions.

Do NOT trigger for: bug fixes (use `p7-debugging`), pure refactoring, or documentation-only changes.

---

## Step 1: Explore P7 Context (Before Asking Questions)

Before asking the user anything, explore the codebase:

- Which P7 layer(s) does this likely touch? (Frontend / Middleware / PE / CMDB / PEDB)
- Are there existing views, components, or endpoints to follow as a pattern?
  - Check `gts.p7.frontend/src/pages/`, `component/`, `stores/`, `services/`
  - Check `middleware/src/routes/api/` for existing Express routes
  - Check `gts.p7.pricingengine/app/RestEndPoints/` for existing PE endpoints
- Note any constraints: naming conventions (divident, volas), real-time data flow, multi-window sync

---

## Step 2: P7-Specific Clarifying Questions (one at a time)

Focus on P7 architectural decisions. Ask one question per message; use multiple-choice when possible:

| Question | Why It Matters |
|----------|---------------|
| What is the data source? (CMDB / PEDB / PE REST / WebSocket) | Determines which layers are involved |
| Real-time push or on-demand REST fetch? | Determines middleware pattern and store type |
| New view/page or addition to an existing view? | Scope of frontend changes |
| New AG Grid instance or extending an existing grid? | Impacts `GridIds.tsx` and `gridCommons.tsx` usage |
| Which users / roles does this affect? | May require authorization checks |
| Any P7 domain terminology to preserve? | Prevents "fixing" intentional names like divident/volas |
| Does this require multi-window sync via BroadcastChannel? | Impacts store architecture |

---

## Step 3: P7 Architecture Decision Checklist

After gathering requirements, confirm each decision before proposing options:

- [ ] **Layers affected**: which of the 5 layers change? (Frontend / Middleware / PE / CMDB / PEDB)
- [ ] **Data transport**: WebSocket push (PE → Faye → Socket.IO → frontend) or REST (frontend → middleware → PE)?
- [ ] **Frontend state**: `useBroadcastStore` (real-time) or Zustand slice (on-demand)?
- [ ] **AG Grid**: new grid ID in `GridIds.tsx`? New column defs? Reuse existing grid?
- [ ] **API URLs**: new key(s) needed in `constants/urlConfig.tsx`?
- [ ] **Zustand slice**: new slice or extend existing? Registered in `useStore.tsx`?
- [ ] **Socket.IO event names**: decided and consistent across PE → middleware → frontend?
- [ ] **Database scope**: CMDB (controller/monitor data) or PEDB (pricing engine data)?
- [ ] **Naming**: all new identifiers consistent with P7 conventions (divident, volas, camelCase/PascalCase)?

---

## Step 4: Propose 2-3 Approaches with P7 Trade-offs

Present options referencing existing P7 files as patterns:

- **Option A (recommended)**: Follow existing pattern in `<file>` — least dev risk, consistent with P7 conventions
- **Option B**: Alternative approach — describe trade-offs (e.g., more layers involved, new store pattern)
- **Option C** (if relevant): Minimal/incremental path (e.g., REST first, WebSocket later)

Always lead with your recommendation and explain why it fits P7's architecture.

---

## Step 5: P7 Data Flow Impact Analysis

For any feature touching real-time data, draw the full impact chain:

```
[Trigger]
    │
    ▼
Pricing Engine (C++)
  └─ New/modified computation or data source
    │  WebSocket Faye channel: <channel-name>
    ▼
Middleware (Node.js)
  └─ New/modified Faye subscription + Socket.IO emit
    │  Socket.IO event: <event-name>
    ▼
Frontend (React)
  └─ useBroadcastStore handler → Zustand slice update
    │
    ▼
Component / AG Grid
  └─ useShallow selector → grid row data
```

Identify every file that needs to change at each boundary. Name the Faye channel and Socket.IO event explicitly — mismatches are the #1 integration bug.

---

## Step 6: Design Document

Save design docs to: `docs/p7/specs/YYYY-MM-DD-<feature-name>-design.md`

Include:
- Goal (one sentence)
- Architecture overview
- Layer breakdown with exact file paths and responsibilities
- Data flow diagram (ASCII, as above)
- P7 naming decisions (Faye channel, Socket.IO event name, store slice name, API URL key)
- Out-of-scope items explicitly listed

Commit the design doc before any implementation begins.

---

## Step 7: Spec Self-Review

Before presenting to the user:

- [ ] **Placeholder scan**: no "TBD" or incomplete sections
- [ ] **P7 conventions**: naming choices consistent with divident/volas/camelCase/PascalCase
- [ ] **Data flow complete**: end-to-end path (PE → middleware → frontend) fully specified
- [ ] **No invented patterns**: every pattern references an existing P7 file as the model
- [ ] **Scope**: implementable in one plan, or needs decomposition?

---

## P7 Design Checklist (Handoff Gate)

Before invoking the planner, confirm all items:

- [ ] All affected layers identified (Frontend / Middleware / PE / CMDB / PEDB)
- [ ] Exact file paths for creates/modifies decided
- [ ] AG Grid ID added to `GridIds.tsx` (if AG Grid view)
- [ ] API URL key added to `constants/urlConfig.tsx`
- [ ] Zustand slice name decided, registered in `useStore.tsx`
- [ ] Socket.IO event name(s) decided and documented
- [ ] Real-time vs. REST fetch decision made and justified
- [ ] CMDB vs. PEDB data source confirmed
- [ ] Multi-window sync (BroadcastChannel) considered
- [ ] P7 terminology preserved (divident, volas)
