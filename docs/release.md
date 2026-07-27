# Releases

Production versions come from SCM tags through hatch-vcs. The tracked `.release-version` and `.release-source-date-epoch` files authorize one reproducible stable build, while `.next-version` defines the next TestPyPI development line. Public interfaces may evolve before 1.0, but every user-visible 0.x change still requires a Towncrier fragment.
OCR compatibility updates may be prepared mechanically only after the [qualification policy](compatibility.md) returns `automatic-safe`; this never replaces the protected feature and stable-release PR gates.

## Release-required changes

A change is release-required when it removes or incompatibly changes a public CLI, environment variable, generated schema, reviewer command, or documented integration behavior, or when the user explicitly requests stable publication. Select the target version before implementation closure and keep one active plan through both development and release delivery. Other user-visible fixes and features must still be classified explicitly; they are not automatically entitled to a stable release after every merge.

The delivery sequence is:

1. merge the feature through protected `main`;
2. verify the deterministic `.devN` wheel and sdist on TestPyPI;
3. prepare a signed `release/vX.Y.Z` pull request containing the stable version marker, deterministic epoch, generated Towncrier changelog, and next development line;
4. use release-PR merge as the human authorization gate;
5. monitor TestPyPI stable publication, production PyPI publication, signed tag, provenance, and immutable GitHub Release;
6. independently compare artifact hashes and smoke-install the wheel on Python 3.10 and the sdist on Python 3.14.

Do not mark the objective complete after step 1 or 2. If the owner explicitly defers stable publication, record the target version and exact resume point in `PLANS.md`.

## Development builds

Every non-release push to protected `main` runs the **TestPyPI development build** workflow. The immutable workflow run number produces `<next-version>.devN` (for example `0.3.0.devN` after the 0.2.0 release); rerunning the same run reuses the version and succeeds only when the already-published filenames and SHA-256 values match the reviewed artifacts. The workflow uses TestPyPI Trusted Publishing, publishes attestations, verifies bounded HTTPS downloads, and smoke-installs the exact wheel and sdist locally with `--no-deps`.

Development builds never create tags or GitHub Releases and never publish to production PyPI. TestPyPI is public disclosure, so only reviewed pull requests may reach `main`.

## Stable release

Prepare `release/vX.Y.Z` locally from synchronized `main`. Update `.release-version`, `.release-source-date-epoch`, package metadata, documentation, checksum-pinned examples, and the Towncrier changelog. The pull request title must be exactly `Release vX.Y.Z`. Required CI, security, CodeQL, Dependency Review, and build checks must pass before squash merge.

Squash-merging that exact repository-owned release PR is the only human publication gate. The **Release** workflow then:

1. validates the branch, title, merge commit, canonical version, and tracked build epoch;
2. repeats quality, dependency, packaging, and artifact-set checks;
3. builds wheel and sdist once, records SHA-256 values, and creates GitHub provenance attestations;
4. publishes or exact-hash-verifies the same bytes on TestPyPI through OIDC;
5. publishes or exact-hash-verifies the same bytes on PyPI through OIDC;
6. creates an annotated `vX.Y.Z` tag and GitHub Release with wheel, sdist, `SHA256SUMS`, `artifact-hashes.json`, and the matching `CHANGELOG.md` section.

Registry reruns are fail-closed. An absent release may be published and an exact existing artifact set may be accepted; partial sets, extra files, unexpected hosts, or digest mismatches stop the workflow. No registry API token or long-lived release PAT is stored in GitHub.

## Required configuration

- TestPyPI Trusted Publisher: workflow `release.yml`, environment `testpypi-public-disclosure`.
- PyPI Trusted Publisher: workflow `release.yml`, environment `pypi-production`.
- Both environments restrict deployment to protected `main` and do not add a second manual approval after the release PR merge.
- The `main` ruleset requires pull requests, linear history, signed commits, resolved conversations, required merge checks, and blocks deletion and force pushes.
- Public security features include secret scanning and push protection, private vulnerability reporting, Dependabot, CodeQL, Dependency Review, OpenSSF Scorecard, and immutable releases.

After publication, independently compare TestPyPI, PyPI, the GitHub workflow artifact, and GitHub Release assets by SHA-256, then smoke-install the wheel on Python 3.10 and the sdist on Python 3.14.
