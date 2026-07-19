# Release process

Versions come from SCM tags through hatch-vcs. Automatic TestPyPI previews use final alpha versions derived from the immutable workflow run number; release tags use `vX.Y.Z`. Public interfaces may evolve before 1.0, but every user-visible 0.1.x change still needs a Towncrier fragment.

## Private TestPyPI preview

Every push to `main` runs the **TestPyPI preview** workflow. The workflow maps its immutable run number directly to the alpha number (`run #3` becomes `0.1.0a3`), repeats quality and security gates, builds deterministic wheel and sdist artifacts, and publishes only through TestPyPI OIDC. A rerun reuses the same version and succeeds only when the already-published artifact SHA-256 values match exactly. It does not create a Git tag, publish a GitHub Release, or publish to production PyPI. TestPyPI is still public disclosure, so merge only reviewed commits. TestPyPI has a separate account database from PyPI.

The workflow validates that checkout `HEAD` is the triggering `main` SHA, verifies the exact local artifact set against the PEP 691 Simple API, and fails closed on partial releases or SHA conflicts. The OIDC publish job runs only when the version is absent; verification always downloads immutable published files with bounded retries/timeouts, checks their SHA-256 values, and smoke-installs both wheel and sdist.

GitHub artifact attestations are omitted from this private preview because GitHub Free supports them only for public repositories. The PyPA publisher's PEP 740 attestations are also disabled so the public TestPyPI preview does not publish provenance claims about the private workflow. The production workflow retains both forms of provenance for use after the repository becomes public.

Configure a pending TestPyPI Trusted Publisher with project name `open-code-review-toolkit`, owner `xeonvs`, repository `open-code-review-toolkit`, workflow `testpypi.yml`, and environment `testpypi-public-disclosure`. No TestPyPI API token is stored in GitHub.

## Production preparation

The manual preparation workflow validates a PEP 440 version, a synchronized `main`, changelog fragments, and the generated changelog. It creates a release branch and pull request using a fine-grained repository-scoped `RELEASE_PR_TOKEN` with only the required Contents and pull-request permissions. Required CI must run on that PR. GitHub does not allow the workflow to mint this PAT; an owner must create it and add it to the `release-preparation` environment.

## Publication

Production release preparation is fail-closed while the repository is private. After the repository becomes public and its available protections are enabled, the special release PR must be approved by someone other than its author and merged. The release workflow rechecks that approval, binds wheel and sdist to the exact reviewed merge commit, creates an annotated tag and draft GitHub Release, and waits at a protected environment for final approval. TestPyPI is public disclosure, so approval occurs before its OIDC Trusted Publishing step.

The workflow verifies each published TestPyPI and PyPI file against the SHA-256 of the reviewed build artifact, downloads it with bounded HTTPS retries and timeouts, and smoke-installs the local wheel and sdist with dependencies disabled. It then publishes the GitHub Release. No repository PyPI token is used.

Trusted Publisher records, protected environments, branch protection, and the release-preparation credential require owner setup. Repository visibility changes are separate manual actions.

The repository is initially private. GitHub Free does not enforce protected branches or environment reviewers on a private repository, and Dependency Review, CodeQL upload, and Scorecard integrations are unavailable there. Those jobs skip while private. Until public-release preparation, use pull requests by policy, inspect their checks manually, and treat the empty environment protection rules as a production-release blocker.
