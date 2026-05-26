---
name: teams
description: "Generic Microsoft Teams communication skill. Use when: sending deployment notifications, requesting approvals, posting standup updates, or notifying stakeholders about incidents or releases."
systems: [all]
---

# Teams Skill

Provides standard Microsoft Teams communication patterns reusable across all GTS systems.

## Notification Types

### Deployment Notification
```
🚀 **Deployment Complete** — {System} {Environment}
**Version**: {tag/commit}
**Changes**: {summary of changes}
**Status**: ✅ Success / ❌ Failed
**Deployed by**: {name}
**Time**: {timestamp}
```

### Approval Request
```
⏳ **Approval Required** — {what needs approval}
**Requested by**: {name}
**Context**: {brief description}
**Deadline**: {date/time}
**Action**: [Approve] [Reject] {link}
```

### Incident Alert
```
🔴 **Incident** — {system} {severity: P1/P2/P3}
**Impact**: {who/what is affected}
**Started**: {timestamp}
**Owner**: {incident owner}
**Bridge**: {call link}
```

### Standup Update
```
**{Date} Standup — {Name}**
✅ Done: {completed items}
🔨 Today: {planned items}
🚧 Blockers: {any blockers or "None"}
```

## Conventions
- Always tag relevant people using @mention for action items
- Use adaptive cards for approval flows when possible
- Do not post sensitive data (credentials, PII) in Teams channels
- Prefer threaded replies for follow-ups on incident/deployment posts
