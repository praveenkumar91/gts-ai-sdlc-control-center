---
name: p7-github
description: "P7-specific GitHub operations skill. Use when: writing commit messages, creating branches, preparing PRs, or performing any GitHub workflow operations on the P7 platform."
systems: [p7]
extends: skills/common/github
---

# P7 GitHub

**Extends: skills/common/github**

Applies the common GitHub conventions (Conventional Commits, branch naming, PR template) with P7-specific layer scopes, Jira project key examples, and a layer impact table required in every P7 PR description.

---

## P7 Commit Scope Conventions

Use layer-specific scopes in all Conventional Commits on the P7 platform:

| Scope | Layer | Example |
|-------|-------|---------|
| `frontend` | React/TypeScript (`gts.p7.frontend/`) | `feat(frontend): add settlement pricing view` |
| `middleware` | Node.js/Express (`middleware/`) | `fix(middleware): correct Socket.IO event name for volas push` |
| `pe` | Pricing Engine C++ (`gts.p7.pricingengine/`) | `feat(pe): add theo price REST endpoint` |
| `db` | Any database change | `fix(db): correct foreign key on positions table` |
| `cmdb` | CMDB-specific changes (`gts.p7.common.controller-monitor.database/`) | `feat(cmdb): add divident adjustment column` |
| `pedb` | PEDB-specific changes (`gts.p7.pricingengine/sql/`) | `feat(pedb): add volas snapshot table` |

**Multi-layer commits**: use the primary layer as scope; list all layers in the commit body:
```
feat(frontend): add real-time volas grid

Layers changed:
- frontend: new VolasView component and Zustand slice
- middleware: new Socket.IO event handler for volas push
- pe: new /api/volas REST endpoint registered in CrowHandler
```

---

## P7 Branch Naming

Follow the common pattern `{jira-ticket}-{short-description}` using P7 Jira project keys:

| Jira Project | Layer Focus | Example Branch |
|-------------|-------------|---------------|
| `P7` | Any P7 feature/bug | `P7-123-add-divident-view` |
| `P7` | Frontend-only | `P7-456-volas-grid-columns` |
| `P7` | PE fix | `P7-789-theo-price-ws-push` |
| `P7` | Database migration | `P7-321-pedb-snapshot-table` |

Branch names must use P7 terminology as-is: `divident` not `dividend`, `volas` not `volatilities`.

---

## P7 PR Description Template

Every P7 PR MUST include the standard layer impact table in the description. Extend the common PR template:

```markdown
## Summary
{What does this PR do? One paragraph.}

## Layer Impact
| Layer | Changed? | Files Modified |
|-------|----------|---------------|
| Frontend | Yes / No | `src/pages/...`, `src/stores/...` |
| Middleware | Yes / No | `src/routes/api/...` |
| Pricing Engine | Yes / No | `app/RestEndPoints/...` |
| CMDB | Yes / No | `commondb/schema/...` |
| PEDB | Yes / No | `sql/schema/...` |

## Changes
- `{file}`: {what changed}

## Data Flow Impact
{Describe any change to the PE → middleware → frontend data flow, including:}
- Faye channel name (if changed): `{channel}`
- Socket.IO event name (if changed): `{event}`
- Store slice key (if changed): `{key}`

## Testing
- [ ] Frontend: `npm test` passes
- [ ] Middleware: `curl` verification performed
- [ ] PE: `make -j4` builds; Python REST tests pass
- [ ] Database: migration ran without errors on test instance
- [ ] End-to-end: real-time data flows from PE to frontend grid

## Linked Issues
Closes #{jira-ticket}
```

---

## P7-Specific Review Checklist

Before requesting review on a P7 PR, verify:

- [ ] Commit scope matches the primary changed layer (`frontend`, `middleware`, `pe`, `db`, `cmdb`, `pedb`)
- [ ] Layer impact table is filled in accurately
- [ ] Socket.IO event names and Faye channel names are documented if changed
- [ ] No `console.log` in any layer (`grep -rn "console\.log" src/`)
- [ ] No hardcoded URLs in frontend (`grep -rn "localhost" src/`)
- [ ] No ES imports in middleware (`grep -rn "^import " middleware/src/`)
- [ ] P7 terminology preserved (divident, volas) in all new identifiers
- [ ] All CI checks pass before requesting review
