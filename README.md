# Open Code Review Toolkit

[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/13906/badge)](https://www.bestpractices.dev/projects/13906)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/xeonvs/open-code-review-toolkit/badge)](https://securityscorecards.dev/viewer/?uri=github.com/xeonvs/open-code-review-toolkit)
[![CodeQL](https://github.com/xeonvs/open-code-review-toolkit/actions/workflows/codeql.yml/badge.svg?branch=main)](https://github.com/xeonvs/open-code-review-toolkit/actions/workflows/codeql.yml)

Open Code Review Toolkit is an unofficial GitLab CI integration layer for [Alibaba Open Code Review](https://github.com/alibaba/open-code-review). It provides bounded repository evidence, a compact review bootstrap, a built-in read-only MCP server, environment-driven OCR configuration, preflight validation, and safe GitLab merge-request posting. It does **not** bundle or download the `ocr` binary.

> [!NOTE]
> The project is under active development; the public API, CLI, environment contract, and generated schemas may evolve before 1.0.

## Install

Install the Python package from PyPI and install a supported OCR binary separately:

```console
python -m pip install open-code-review-toolkit
ocr --version
ocr-ci --help
```

The exact recommended OCR release and its verified asset checksums live in the [versioned compatibility manifest](compatibility/ocr-support.json). CI should pin that release and checksum before execution.
The [versioned compatibility policy](docs/compatibility.md) records tested assets and evidence and describes the conservative Dependabot-like qualification workflow for later upstream releases.
Review output defaults to English. `OCR_REVIEW_LANGUAGE` accepts another explicit language name when a project needs localized review output; for example, `OCR_REVIEW_LANGUAGE=Russian`.
The current OCR 1.10.1 integration defaults `OCR_REVIEW_EFFORT` to `medium` for two review rounds. `low` and `high` are explicit one- and three-round alternatives; see the [configuration reference](docs/configuration.md#review-effort) for cost, budget, and precedence boundaries.

Stable distributions are published to [PyPI](https://pypi.org/project/open-code-review-toolkit/) and mirrored as checksum-listed, provenance-attested assets in the corresponding [GitHub Release](https://github.com/xeonvs/open-code-review-toolkit/releases). Development snapshots are published only to TestPyPI.

## How reviews evolve

On a successful rerun, the toolkit replaces untouched OCR-only notes instead of accumulating stale reviews. A human reply transfers that discussion to the team: the conversation is preserved and a matching finding is suppressed. Reply with `/ocr suppress` or `@<live-bot-username> suppress` to keep a discussion open without future repeats; use the corresponding `resolve` command to resolve it after the next successful posting transaction. For example, a bot named `mr.bot` accepts the exact reply `@mr.bot resolve`.

Suppression uses both the GitLab diff position and a stable finding fingerprint, so ordinary line shifts do not normally bring the same bug back. A materially changed finding can still receive a new discussion. See [GitLab review operations](docs/operations.md) for the complete lifecycle, posting modes, permissions, failure behavior, and Mermaid state diagram.

After every current review note publishes, the GitLab adapter can add a conservative approval bound to receipt v5's exact reviewed source SHA and merge-request author. This write is enabled by default; set `OCR_AUTO_APPROVE=false` when the bot must remain comment-only. DLP-clean metadata, generic discussions, and adapter records do not independently block approval, while degraded metadata, DLP rejection, required context degradation, admitted remediation history, legacy receipts, publication filtering, any direct external MCP, author movement, or bot self-authorship prevents an approval write. GitLab approval rules and protected-branch policy remain authoritative. The toolkit only adds an eligible approval; it never removes an existing approval when a later review is ineligible or disabled.

Accepted tradeoffs can be recorded in `.opencodereview/accepted-decisions.md`; the evidence collector supplies only applicable target-ref decisions and never lets a source change self-authorize its review. Root and nested target `AGENTS.md`/`CLAUDE.md` guidance is similarly exposed through the existing evidence MCP with deterministic scope and precedence, while any guidance touched by the merge request is excluded. See [Accepted project decisions](docs/configuration.md#accepted-project-decisions) and [Target project guidance](docs/configuration.md#target-project-guidance) for formats and trust boundaries.

## Project architecture

The shipped Repository Evidence Engine reads immutable base/head Git objects, stores bounded typed facts and deltas, creates the compact bootstrap used by OCR, and exposes detailed facts, scoped completeness, and base/head changes through the mandatory built-in read-only MCP server. Protected-policy enriched reviews can acquire stable GitLab discussions, verified remediation history, and authorized external issue/document records before OCR. Forge-specific acquisition and posting stay at provider edges; the broker, DLP, store, MCP, receipts, and tests use common contracts so a future GitHub adapter can reuse them without inheriting GitLab API semantics. The same built-in MCP exposes only opaque committed `context_list`/`context_get` handles; it has no provider network or arbitrary identifier path. Direct external MCP remains a separate privileged, comment-only operator boundary.

- [Toolkit strategy](docs/engineering/toolkit_strategy.md) - durable product boundaries, architecture, invariants, and non-goals.
- [Bounded review context](docs/review-context.md) - protected policy, adapter protocol, GitLab discussions, opaque handles, DLP, receipt, and cleanup contracts.
- [Roadmap](ROADMAP.md) - milestone status, dependencies, outcomes, and completion signals.
- [Backlog](docs/codex/TASKS_BACKLOG.md) - inactive implementation-ready work; active execution remains in `PLANS.md`.

## GitLab CI quick start

1. Configure protected/masked `GITLAB_API_TOKEN` and LLM variables in GitLab.
2. Pin and checksum the OCR binary.
3. Install this package.
4. Run the four public helper stages around `ocr review`:

```console
ocr-ci preflight
ocr-ci configure
ocr-ci review --result /tmp/ocr-result.json --stderr /tmp/ocr-stderr.log -- ... --format json
ocr-ci post --result /tmp/ocr-result.json --stderr /tmp/ocr-stderr.log
```

See the [GitLab mode matrix](examples/gitlab/README.md), the complete [`ocr-review.gitlab-ci.yml`](examples/gitlab/ocr-review.gitlab-ci.yml) pipeline, the [GitLab setup guide](docs/gitlab.md), and [GitLab review operations](docs/operations.md).

## Configuration and safety

Configuration is environment-driven. The [configuration reference](docs/configuration.md) documents supported `OCR_*`, `CI_*`, `GITLAB_*`, and MCP inputs. Posting requires `GITLAB_API_TOKEN`; job tokens and legacy aliases are deliberately unsupported.

Repository content, OCR output, and provider responses are untrusted inputs. The toolkit applies bounded reads and writes, secret redaction, Unicode normalization, Markdown/quick-action neutralization, fingerprinted comments, ownership boundaries for human replies, and rollback controls. Review the [security and trust model](docs/security.md) before enabling write access.

## Development and release

- [Documentation index](docs/README.md)
- [Contributing](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Development guide](docs/development.md)
- [Security policy](SECURITY.md)
- [Release process](docs/release.md)
- [Changelog](CHANGELOG.md)

Licensed under Apache-2.0.
