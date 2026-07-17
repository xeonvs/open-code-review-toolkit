# Contributing

Thank you for improving Open Code Review Toolkit. Keep changes focused, add regression tests for behavior changes, and use synthetic examples only.

1. Create a branch from `main`.
2. Install the locked development environment with `uv sync --frozen`.
3. Update `PLANS.md` for substantial work.
4. Add a Towncrier fragment for user-visible changes.
5. Run the checks in [docs/development.md](docs/development.md).
6. Open a pull request; direct changes to `main` are not part of the project workflow.

Do not include real credentials, provider payloads, internal hosts, or private repository details. Security reports should follow [SECURITY.md](SECURITY.md), not public issues.
