---
applyTo: ".github/workflows/**/*.{yml,yaml}"
---

Use least-privilege `permissions`, pin third-party actions to reviewed commit SHAs before production adoption, avoid pull-request secrets, avoid untrusted expression interpolation in shell commands, set timeouts, and preserve evidence.

Workflow changes require security review. Never grant `write-all`.
