# Repository extension contract

Store the optional manifest at `.github/sdlc/extensions.json`. The program
repository entry may select another safe relative path with
`extensions_config`.

The manifest may declare:

- `instructions`: repository-specific rules;
- `skills`: reusable procedures rooted in that repository;
- `agents`: repository specialists and their roles;
- `quality_config`: a local quality configuration when the program entry does
  not pin one.

Every entry has an ID, safe repository-relative path, optional `enabled` and
`required` flags, and optional deterministic activation filters:

- `modes`: `implementation` or `validation`;
- `risk_tiers`: `low`, `medium`, `high`, or `critical`;
- `request_terms`: case-insensitive terms matched against the program request.

All configured filters must match. If `request_terms` is present, at least one
term must match.

The resolver:

1. rejects absolute paths, parent traversal, symlink escapes, missing files,
   oversized files, unknown fields, duplicate IDs, and repository-ID mismatch;
2. hashes the manifest and every selected file;
3. records selected content, quality-config precedence, exact repository HEAD,
   and the trust boundary;
4. persists a digest-bound packet in the program run.

Quality configuration precedence is:

1. `quality_config` pinned in central `program.json`;
2. `quality_config` declared by the repository extension;
3. `default_quality_configs[stack]` in central `program.json`;
4. otherwise `INCONCLUSIVE`.

Use `.github/sdlc/schemas/repository-extension.schema.json` and
`.github/sdlc/examples/repository-extensions.example.json` as the normative
schema and example.
