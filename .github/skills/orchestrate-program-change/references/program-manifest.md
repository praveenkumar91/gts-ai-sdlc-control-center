# Program manifest rules

`program.json` is the authoritative inventory and dependency graph.

- Use one stable, lowercase repository ID.
- Set `system` explicitly (`p7`, `t7`, `shared`, or another registered system)
  so agent and skill selection never depends on a repository-name prefix.
- Use the exact canonical Git remote.
- Keep `local_path` relative to `workspace_root`; reject absolute paths and `..`.
- Model `A depends_on B` when A consumes B's code, API, schema, event or deployable behavior.
- Keep dependencies acyclic.
- Pin `quality_config` when a repository owns non-standard deterministic
  commands. Otherwise configure `default_quality_configs[stack]` centrally.
- Configure `integration_quality_config` with reusable deterministic
  cross-repository gate commands. The per-change requirements matrix selects
  gate IDs from this file; the file must not contain requirement IDs.
- Configure `agent_runtime_config` as a safe repository-relative path to the
  versioned worker runtime contract. Production adoption requires both the
  program and runtime adoption flags, an enabled worker, and explicit
  `{prompt}` binding in its argument vector.
- Use `extensions_config` only when the repository manifest is not at
  `.github/sdlc/extensions.json`; set `extensions_required` when its absence
  must block workspace preparation.
- Set criticality from business impact, not repository size.
- Disable a repository until ownership, commands, credentials and controls are adopted.

The program orchestrator remains the sole authority for lifecycle state and the
commit vector. The agent supervisor may launch and retry repository workers,
but workers must never record gate evidence, approve, push, merge or deploy.

The seed set means "repositories expected to change." The orchestrator adds:

- downstream dependents to `validation_scope`;
- transitive prerequisites to `checkout_scope`;
- dependency-ordered `execution_waves`.

Every enabled repository is recorded in the frozen plan as `IMPLEMENTATION`,
`VALIDATION_ONLY`, `CONTEXT_ONLY`, or `NOT_IMPACTED`. This provides complete
program accounting while checking out and prompting only the relevant graph.

Do not mark every repository as a seed to avoid impact analysis. If the graph is incomplete, stop at `INCONCLUSIVE` and fix the manifest under review.
