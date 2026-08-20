# Repository catalog contract 1.0

`.github/gts-repositories.json` is the single program-level repository catalog. GitHub and Copilot do not
require this file; `program-orchestrator` uses it to select a small affected subset without scanning every
repository. Do not create a second central catalog or a `.github/sdlc` directory.

## Catalog structure

The root object contains:

- `catalogVersion`: the catalog contract version;
- `programId`: the stable program identifier;
- `limits`: maximum catalog size, active repositories, parallel workers, review cycles, and repair attempts;
- `repositories`: one metadata entry per program repository.

Before impact selection, the parent verifies that the file parses, the repository count is within the configured
limit, repository IDs are unique, and required execution fields are present. Missing, stale, contradictory, or
unverified mandatory metadata fails closed.

## Required repository execution identity

Every repository entry used for `IMPLEMENTATION` or `VALIDATION_ONLY` contains:

- a unique `repositoryId`, `displayName`, `system`, and accountable `owners`;
- `lifecycle`, which is `ACTIVE`, `RETIRED`, or `EXCLUDED`;
- exactly one immutable 40-character Git commit in `revision`;
- `checkout.localCandidates` and, when cloning is allowed, an approved `checkout.remote`;
- components, owned paths, provided and consumed capabilities or contracts, and dependencies;
- applicable bootstrap, test, lint, build, integration, and security commands;
- optional repository-local instruction, agent, and skill paths.

Branch names, tags, `HEAD`, `latest`, and abbreviated SHAs are not immutable revisions. A worker's
`Base-Revision` must equal the registered revision. A different local `HEAD` blocks implementation until the
entry is deliberately refreshed and reviewed.

## Lifecycle and ownership

- `ACTIVE` repositories may be classified for implementation, validation, context, or exclusion.
- `RETIRED` repositories are context only unless an approved retirement-specific change says otherwise.
- `EXCLUDED` repositories are always `NOT_IMPACTED`.
- Owners identify accountable teams or repository owners; components and paths alone do not establish approval
  authority.

Catalog metadata never authorizes deletion, archival, approval, merge, release, deployment, or delivery.

## Local expertise

The target repository does not copy the control centre. `customizations` may point to its existing
`.github/copilot-instructions.md`, `.github/agents`, and `.agents/skills` content. These rules are loaded only for
selected repositories and may strengthen, but never weaken, evidence requirements or human gates.

## Catalog read and execution readiness

The parent reads the single catalog once and records selected repository IDs and revisions in the plan.
Specialists receive only the selected entries, frozen requirement sources, and explicitly allowed customization
paths. They must not rediscover repository identity through broad workspace searches.

Before Stage 3 completes, every implementation or validation-only repository must have an owner, pinned commit,
and either a resolvable local checkout or approved remote. A missing local checkout for an `existing-only` entry,
a non-Git path, or an unresolved revision results in `BLOCKED_SPEC` or `INCONCLUSIVE`. An
`existing-or-clone` entry may remain metadata-only during planning only when both an approved remote and pinned
commit exist; checkout verification is still required before implementation.
