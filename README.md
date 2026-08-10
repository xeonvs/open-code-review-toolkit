# Open Code Review Toolkit

[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/13906/badge)](https://www.bestpractices.dev/projects/13906)

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

The current compatibility target is OCR `1.8.10`. CI should pin the release and verify its published checksum before execution.
The [versioned compatibility policy](docs/compatibility.md) records tested assets and evidence and describes the conservative Dependabot-like qualification workflow for later upstream releases.
Review output defaults to English. `OCR_REVIEW_LANGUAGE` accepts another explicit language name when a project needs localized review output; for example, `OCR_REVIEW_LANGUAGE=Russian`.

Stable distributions are published to [PyPI](https://pypi.org/project/open-code-review-toolkit/) and mirrored as checksum-listed, provenance-attested assets in the corresponding [GitHub Release](https://github.com/xeonvs/open-code-review-toolkit/releases). Development snapshots are published only to TestPyPI.

## How reviews evolve

On a successful rerun, the toolkit replaces untouched OCR-only notes instead of accumulating stale reviews. A human reply transfers that discussion to the team: the conversation is preserved and a matching finding is suppressed. Reply with `/ocr suppress` to keep a discussion open without future repeats, or `/ocr resolve` to suppress it and resolve the discussion after the next successful posting transaction.

Suppression uses both the GitLab diff position and a stable finding fingerprint, so ordinary line shifts do not normally bring the same bug back. A materially changed finding can still receive a new discussion. See [GitLab review operations](docs/operations.md) for the complete lifecycle, posting modes, permissions, failure behavior, and Mermaid state diagram.

After every current review note publishes, the GitLab adapter can add a
conservative approval bound to the exact reviewed source SHA. This write is
enabled by default; set `OCR_AUTO_APPROVE=false` before upgrading when the bot
must remain comment-only. GitLab approval rules and protected-branch policy
remain authoritative.

Project-wide accepted tradeoffs can be recorded separately in `.opencodereview/accepted-decisions.md`; the evidence collector supplies target-ref decisions to OCR and never lets a source change self-authorize its own review. See [Accepted project decisions](docs/configuration.md#accepted-project-decisions) for the entry format, inline marker convention, security boundary, and limitations.

## Project architecture

The shipped Repository Evidence Engine reads immutable base/head Git objects, stores bounded typed facts and deltas, creates the compact bootstrap used by OCR, and exposes detailed evidence through the mandatory built-in read-only MCP server. Reviewed external stdio or native HTTPS MCP servers compose alongside it without replacing the built-in evidence boundary.

- [Toolkit strategy](docs/engineering/toolkit_strategy.md) - durable product boundaries, architecture, invariants, and non-goals.
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

See the fully synthetic [`examples/gitlab/ocr-review.gitlab-ci.yml`](examples/gitlab/ocr-review.gitlab-ci.yml), the [GitLab setup guide](docs/gitlab.md), and [GitLab review operations](docs/operations.md).

## Configuration and safety

Configuration is environment-driven. The [configuration reference](docs/configuration.md) documents supported `OCR_*`, `CI_*`, `GITLAB_*`, and MCP inputs. Posting requires `GITLAB_API_TOKEN`; job tokens and legacy aliases are deliberately unsupported.

Repository content, OCR output, and provider responses are untrusted inputs. The toolkit applies bounded reads and writes, secret redaction, Unicode normalization, Markdown/quick-action neutralization, fingerprinted comments, ownership boundaries for human replies, and rollback controls. Review the [security and trust model](docs/security.md) before enabling write access.

## Development and release

- [Contributing](CONTRIBUTING.md)
- [Development guide](docs/development.md)
- [Security policy](SECURITY.md)
- [Release process](docs/release.md)
- [Changelog](CHANGELOG.md)

Licensed under Apache-2.0.
