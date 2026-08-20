# Repository descriptor contract 1.1

This document is the normative semantic contract for `.github/sdlc/schemas/repository.schema.json`.
The JSON Schema is authoritative for structure; this document is authoritative for meaning. A catalog
descriptor is control-plane evidence, not a convenient hint. Missing, stale, contradictory or unverified
mandatory metadata fails closed.

## Identity and immutable revision

- `repositoryId` is the stable program-wide identifier and must never be reused for another repository.
- `system` selects the system-specific orchestration family; it does not prove impact by itself.
- `revision.commitSha` is exactly one immutable 40-character Git commit SHA. Branch names, tags, `HEAD`,
  `latest` and abbreviated SHAs are invalid.
- Every repository-worker `Base-Revision` must equal this pinned SHA. A different local `HEAD` blocks execution
  until the descriptor is deliberately refreshed and reviewed.

## Lifecycle and retirement

- `ACTIVE` means the repository may be classified for implementation, validation, context or exclusion.
- `RETIRED` requires a `retirementMarker` with `marker: RETIRED`, effective date, reason and stable evidence
  reference. Impact analysis must classify it as retirement-only context. It receives no product worktree or
  implementation task.
- `EXCLUDED` is a program-policy exclusion and must be classified `NOT_IMPACTED`.
- A retirement marker is program metadata. It does not authorize deleting, archiving or changing GitHub state.

## Compatibility policy

- `compatibility.contract` is `gts-repository-descriptor`.
- `compatibility.version` identifies the descriptor version authored by that repository.
- `compatibleWith` lists the descriptor versions the repository-local integration accepts. Version `1.1`
  must be present for this control centre.
- Removing or changing the meaning of a required field is a breaking contract change and requires a new major
  contract plus an explicit migration plan. Additive optional fields require schema, validator and compatibility
  tests before adoption. Unknown compatibility is `BLOCKED_SPEC`, never assumed.

## Authority and evidence

- `ownership.owners` identifies accountable teams or repository owners; component/path ownership alone is
  insufficient for a human gate.
- Every `evidenceSources` row has a stable ID, kind, location, revision and authority. The revision must make
  the cited evidence reproducible. A mutable page without a version/date is not frozen evidence.
- `checkout.remote` and `defaultBranch` are acquisition metadata only. The pinned commit, not the branch tip,
  is the planning and implementation baseline.

## Customization namespace

- `customizations.namespace` is unique across the program catalog.
- Product repositories are not added as VS Code workspace roots. Their instructions, agents and skills are
  explicitly routed under this namespace when the impact graph selects the repository.
- Repository-local rules may strengthen central policy but cannot weaken evidence, review or human gates.

## Catalog read and execution readiness

The parent agent performs one metadata-only read of the registered catalog and records the selected descriptor
paths and revisions in the plan. Specialists receive only those descriptors, frozen requirement sources and
explicitly allowed customization paths. They must not rediscover repository identity through broad workspace
searches.

Before Stage 3 completes, every implementation or validation-only repository must have a readable descriptor,
owner, pinned commit and either a resolvable local checkout or approved remote. If an `existing-only` checkout is
missing, the local path is not Git, or its required revision cannot be resolved, the run is `BLOCKED_SPEC` or
`INCONCLUSIVE`. An `existing-or-clone` repository may remain metadata-only during planning only when both an
approved remote and pinned commit exist; checkout verification is still required before implementation.
