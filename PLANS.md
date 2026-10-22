# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and
before handoff or commit. Completed stable plans are indexed in
[the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Internal CI and site notification maintenance (#260, #261)

- **Classification:** `no-release`; no stable or development artifact publication from this change.
- **Goal:** reduce repeated installed-artifact test latency while preserving required PR coverage, and tolerate bounded GitHub job-metadata lag before site dispatch.
- **Trust boundaries:** only an exact, nonempty main-push Git range of explicitly allowed CI/test/doc paths may skip the development build; unknown paths, renames, and Git failures run the normal artifact path. Release authorization remains tied to required PR checks and reviewed tree. Site notification retries only a read-only GitHub jobs query, keeps immutable release/receipt checks, and dispatches at most once per run.
- **Work:** measure and map duplicate checks; change CI matrix and release replay; add the exact no-artifact main-push classifier; add bounded site jobs retry; update tests and canonical development/release guidance; self-review logical commits and run focused/full validation and security review.
- **Current state:** the closed main-push classifier and its failure-path tests are implemented; CI/test ownership and site retry are pending.
- **Resume:** finish CI/test ownership, then site retry; verify the final PR and main-push workflow without publishing a package.
