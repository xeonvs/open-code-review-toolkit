# Project Principles

This is the short index of stable cross-cutting engineering rules for Open Code Review Toolkit.

## Core Principles

1. Keep the package provider-neutral; isolate GitLab behavior behind its adapter boundary.
2. Preserve safety properties before compatibility: bounded input, redaction, rendering safety, write limits, and ownership boundaries are part of the product contract.
3. Keep runtime dependencies at zero until a documented package boundary justifies one.
4. Keep public examples and fixtures synthetic and free from local or private infrastructure details.
5. Keep the Open Code Review binary external; preflight verifies it but the package does not install it.
6. Keep user configuration environment-only during v0.1 and document every supported variable centrally.
7. Keep active work resumable from `PLANS.md`; keep inactive work in `docs/codex/TASKS_BACKLOG.md`.
8. Use coherent production-quality slices when work must be decomposed; do not leave placeholder architecture as a milestone.
9. Require changelog fragments for user-visible 0.1.x changes and SCM tags for versions.
10. Treat TestPyPI as public disclosure and preserve the manual privacy/license gate before publishing.

## Documentation Ownership

- `README.md` owns the concise public introduction and quick start.
- `docs/configuration.md` owns the environment contract.
- `docs/gitlab.md` owns GitLab installation and operating guidance.
- `docs/security.md` owns the runtime trust model; `SECURITY.md` owns vulnerability reporting.
- `docs/development.md` owns local contributor commands.
- `docs/release.md` owns the release and disclosure process.
- `AGENTS.md`, `PLANS.md`, and `docs/codex/` own agent workflow rather than product behavior.
