---
name: jira
description: "Generic Jira operations skill. Use when: creating tickets, transitioning issue status, linking issues, adding comments, querying sprint boards, or managing Jira workflow as part of any SDLC pipeline."
systems: [all]
---

# Jira Skill

Provides standard Jira operations reusable across all GTS systems.

## Operations

### Create a Ticket
- Type: Story / Bug / Task / Sub-task / Epic
- Required fields: summary, description, project key, issue type, assignee (optional)
- Add acceptance criteria in the description under `h2. Acceptance Criteria`
- Link to parent Epic if applicable

### Transition an Issue
- Use workflow transitions: `To Do` → `In Progress` → `In Review` → `Done`
- Add a comment explaining the transition when moving to `In Review` or `Done`
- Never skip transitions — always move through each state sequentially

### Link Issues
- Use link types: `blocks`, `is blocked by`, `relates to`, `duplicates`
- Link sub-tasks to their parent story
- Link bugs to the story that introduced the regression

### Query & Report
- Use JQL for searches: `project = {KEY} AND sprint in openSprints() AND assignee = currentUser()`
- When reporting status, include: ticket key, summary, status, and assignee

## Conventions
- Ticket titles: imperative verb phrase — "Add dividend calculation endpoint"
- Descriptions: user story format — "As a {role}, I want {goal} so that {benefit}"
- All code-related tickets must have a linked PR before moving to `Done`
