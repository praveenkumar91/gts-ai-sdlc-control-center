# Generic Core Mode

This mode keeps the control plane as the main SDLC authority while allowing each managed repository to contribute project-specific context.

## Goal

- Central control plane remains authoritative for state transitions, evidence rules, approvals, and integrity verification.
- Managed repositories may add local instructions, skills, agents, and quality overrides.
- Local repository content is additive only and cannot weaken central controls.

## Resolution Order Used By Program Orchestrator

For each repository, quality configuration is selected in this order:

1. `repositories[].quality_config` from central `program.json`
2. `quality_config` from repository-local `.github/sdlc/extensions.json`
3. `default_quality_configs[stack]` from central `program.json`
4. otherwise run is blocked as inconclusive for missing quality config

This precedence is implemented in `program_orchestrator.py` by `resolve_repository_extensions`.

## Recommended Setup

1. Use central defaults for all stacks in `default_quality_configs`.
2. Keep repository entries generic (no repository-specific command paths unless required).
3. Set `extensions_config` to `.github/sdlc/extensions.json` for every managed repository.
4. Keep `extensions_required` as `false` unless a repository must provide local extensions.
5. Let each repository opt in to project-specific instructions and skills through its own extension manifest.

## Example Files

- Central generic main manifest:
  - `.github/sdlc/examples/program.generic-main.example.json`
- Project overlay manifest (in each managed repository):
  - `.github/sdlc/examples/extensions.project-overlay.example.json`

## Validation Commands

Run from the control-plane repository root:

```bash
python .github/scripts/program_orchestrator.py validate --adoption
python .github/scripts/agent_supervisor.py validate --adoption
python .github/scripts/validate_control_plane.py --adoption
```

After Human Gate 1, run `agent_supervisor.py run --change-id <id>`. It resumes
from hash-chained state, launches fresh repository-scoped worker attempts, runs
deterministic repository and integration gates, and stops before independent
Plan Closure and PR approval. Configure and adopt `agent-runtime.json` before
using a real worker command.

Inspect how a repository extension resolves for a change:

```bash
python .github/scripts/program_orchestrator.py extensions --change-id CHG-1234 --repository project-a
```

## What To Keep Central vs Local

Keep central:

- state machine and run integrity
- evidence contracts and approval gates
- repository graph and execution waves
- baseline quality command policy

Keep local per repository:

- domain-specific instructions
- domain skills and optional domain reviewer agent
- repository-specific quality command overrides when needed

## Adoption Checklist

1. Replace placeholder URLs and program ID in your production `program.json`.
2. Enable real repositories.
3. Add central stack defaults in `default_quality_configs`.
4. Add local `.github/sdlc/extensions.json` only where domain overrides are needed.
5. Validate adoption and run one smoke change from start to PR approval.
