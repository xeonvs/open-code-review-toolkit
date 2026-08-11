# Releases

Production versions come from SCM tags through hatch-vcs. The tracked `.release-version` and `.release-source-date-epoch` files authorize one reproducible stable build, while `.next-version` defines the next TestPyPI development line. Public interfaces may evolve before 1.0, but every user-visible 0.x change still requires a Towncrier fragment.
OCR compatibility updates may be prepared mechanically only after the [qualification policy](compatibility.md) returns `automatic-safe`; this never replaces the protected feature and stable-release PR gates.

Towncrier renders `🚀 Features`, `🐛 Bug Fixes`, `🔧 Refactoring`, and `📖 Documentation` only when their categories have entries; Security, Deprecations, and Removals remain conditional categories as well. Use `🧩 Rules` when the effective rules contract changes in the toolkit `examples/gitlab/rules.json`, the recommended OCR release's built-in rules, or OCR's allowlist of reviewable file types. Omit `🧩 Rules` when all three layers are unchanged. Write readable entries without conventional-commit prefixes. GitHub Release notes contain the exact new Towncrier section and end with `**Full Changelog**:` comparing the adjacent previous stable changelog section to the release being published.

## Release-required changes

A change is release-required when it removes or incompatibly changes a public CLI, environment variable, generated schema, reviewer command, or documented integration behavior, or when the user explicitly requests stable publication. Select the target version before implementation closure and keep one active plan through implementation, publication, and external reconciliation. Other user-visible fixes and features must still be classified explicitly; they are not automatically entitled to a stable release after every merge.

The delivery sequence is:

1. implement and validate the feature;
2. merge the protected feature pull request to `main`;
3. verify the deterministic `.devN` wheel and sdist on TestPyPI;
4. prepare and merge a protected signed `release/vX.Y.Z` pull request;
5. monitor stable TestPyPI and PyPI publication, annotated tag, provenance, attestations, and immutable GitHub Release;
6. independently compare artifact hashes and smoke-install every supported Python boundary;
7. independently read the immutable `release-receipt.json`, close the tracked issues, and finish the active objective without another repository pull request.

The release pull request is the final repository mutation. It owns repository-side preparation: stable and next version markers, deterministic source epoch, tracked release authorization metadata, generated Towncrier changelog, release notes, and reconciliation of `PLANS.md`, the execution-history index, roadmap, backlog, strategy, and README where applicable. It lists external checks as pending and must not claim that registry files, provenance, tag, immutable Release, receipt, or installs already exist.

The post-merge workflow executes its authorizer from the protected base SHA that
predates the release PR; candidate head and squash-merge commits are inspected
only as bounded data and cannot supply the code that authorizes themselves.
Authorization then binds the squash merge to the exact reviewed release-head
tree, its exact protected base parent, and the live `main` ruleset's required
checks. It publishes or exact-hash-verifies the stable artifacts, verifies
registry and GitHub provenance plus supported-Python installs, and creates
`ocr-toolkit.release-receipt/v1` before publishing the GitHub Release. The
receipt deliberately marks Release asset self-readback as pending; the workflow
then downloads the complete asset set, publishes the draft, requires GitHub's
immutable state, and only afterward records idempotent issue receipts and closes
the tracked issues. Do not mark the release objective complete after feature
merge, development publication, or release-PR preparation. If the owner
explicitly defers stable publication, keep the release-required plan active or
blocked and record the reason, target stable version, completed checkpoints,
and exact resume action.

## Development builds

Every non-release push to protected `main` runs the **TestPyPI development build** workflow. The immutable workflow run number produces `<next-version>.devN` (for example `0.3.0.devN` after the 0.2.0 release); rerunning the same run reuses the version and succeeds only when the already-published filenames and SHA-256 values match the reviewed artifacts. The workflow uses TestPyPI Trusted Publishing, publishes attestations, verifies bounded HTTPS downloads, and smoke-installs the exact wheel and sdist locally with `--no-deps`.

Development builds never create tags or GitHub Releases and never publish to production PyPI. TestPyPI is public disclosure, so only reviewed pull requests may reach `main`.

## Stable release

Prepare `release/vX.Y.Z` locally from synchronized `main`. Update `.release-version`, `.release-source-date-epoch`, package metadata, documentation, checksum-pinned examples, and the Towncrier changelog. The pull request title must be exactly `Release vX.Y.Z`. Required CI, security, CodeQL, Dependency Review, and build checks must pass before squash merge.

Squash-merging that exact repository-owned release PR is the only human publication gate. The **Release** workflow then:

1. validates the branch, title, tracked metadata, reviewed head/base, exact required checks, squash-tree equivalence, merge parent, canonical version, and tracked build epoch;
2. repeats quality, dependency, packaging, and artifact-set checks;
3. builds wheel and sdist once, records SHA-256 values, and creates GitHub provenance attestations;
4. publishes or exact-hash-verifies the same bytes on TestPyPI through OIDC;
5. publishes or exact-hash-verifies the same bytes on PyPI through OIDC;
6. verifies every supported Python minor, registry provenance, and GitHub artifact attestations;
7. creates an annotated `vX.Y.Z` tag and GitHub Release with wheel, sdist, `SHA256SUMS`, `artifact-hashes.json`, `release-receipt.json`, and the matching `CHANGELOG.md` section;
8. reads back the complete asset set and immutable Release before closing the tracked issues.

Registry reruns are fail-closed. An absent release may be published and an exact existing artifact set may be accepted; partial sets, extra files, unexpected hosts, or digest mismatches stop the workflow. No registry API token or long-lived release PAT is stored in GitHub.

## Required configuration

- TestPyPI Trusted Publisher: workflow `release.yml`, environment `testpypi-public-disclosure`.
- PyPI Trusted Publisher: workflow `release.yml`, environment `pypi-production`.
- Both environments restrict deployment to protected `main` and do not add a second manual approval after the release PR merge.
- The `main` ruleset requires pull requests, linear history, signed commits, resolved conversations, required merge checks, and blocks deletion and force pushes.
- Public security features include secret scanning and push protection, private vulnerability reporting, Dependabot, CodeQL, Dependency Review, OpenSSF Scorecard, and immutable releases.

After publication, independently compare TestPyPI, PyPI, the GitHub workflow artifact, and GitHub Release assets by SHA-256; verify registry/GitHub provenance, the annotated tag target, immutable Release, and `release-receipt.json`; then smoke-install published artifacts on every Python minor derived from the canonical `requires-python` range.

## External reconciliation and plan archiving

The immutable receipt carries the release PR, reviewed base/head/merge/tree, original workflow run and attempt, tracked issue set, distribution hashes, registry/provenance verification states, annotated-tag target, and supported-Python matrix. Independent external readback confirms facts that the receipt cannot assert about itself, especially Release asset equality and immutable state. Issue comments retain the receipt asset hash and are the durable post-merge closure surface.

`PLANS.md` keeps the just-prepared release cycle so its pending gates and later external receipt remain immediately discoverable from the tag and tracked issues. During the next release PR, move the previously retained externally reconciled cycle without rewriting it into `docs/engineering/execution_history/releases.md`, add or update the corresponding stable-tag row in the [execution-history index](engineering/execution_history/README.md), and validate every archive anchor. Preserve dates inside archived plans; stable tags, not calendar years, are the lookup keys.

Recovery dispatch is bound to the original release PR, version, merge commit,
reviewed head, and protected reviewed base. It executes the same trusted-base
authorizer, accepts only exact registry bytes and the existing immutable
receipt's closed release identity, and rejects unknown receipt fields. If only
issue commenting or closure failed, recovery reuses the exact GitHub
Actions-owned receipt comment, accepts an already-completed issue, and does not
change repository files, tag, or immutable Release assets. A user-authored
marker cannot preempt that bot-owned receipt.
