# Release process

Versions come from SCM tags through hatch-vcs. The first prerelease is `0.1.0a1`; release tags use `vX.Y.Z`. Public interfaces remain provisional before 1.0, but every user-visible 0.1.x change still needs a Towncrier fragment.

## Preparation

The manual preparation workflow validates a PEP 440 version, a synchronized `main`, changelog fragments, and the generated changelog. It creates a release branch and pull request using a fine-grained repository-scoped `RELEASE_PR_TOKEN` with only the required Contents and pull-request permissions. Required CI must run on that PR. GitHub does not allow the workflow to mint this PAT; an owner must create it and add it to the `release-preparation` environment.

## Publication

After the special release PR is approved by someone other than its author and merged, the release workflow rechecks that approval, binds wheel and sdist to the exact reviewed merge commit, creates an annotated tag and draft GitHub Release, and waits at a protected environment for final privacy/license approval. TestPyPI is public disclosure, so approval occurs before its OIDC Trusted Publishing step.

The workflow installs and smokes the TestPyPI package, then passes through a separate protected PyPI environment, publishes with OIDC, installs and smokes the production package, attaches the reviewed artifacts, and publishes the GitHub Release. No repository PyPI token is used.

Trusted Publisher records, protected environments, branch protection, and the release-preparation credential require owner setup. Repository visibility changes are separate manual actions.

The repository is initially private. GitHub Free does not enforce protected branches or environment reviewers on a private repository; those controls must be enabled immediately after a GitHub Pro upgrade or when the repository becomes public. Until then, do not push `main` after the initial import: use pull requests and treat the empty environment protection rules as an explicit release blocker.
