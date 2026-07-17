# Open Code Review Toolkit

Open Code Review Toolkit is a community-maintained, unofficial CI integration layer for [Alibaba Open Code Review](https://github.com/alibaba/open-code-review). It provides bounded repository context generation, environment-driven OCR configuration, preflight validation, and safe GitLab merge-request posting. It does **not** bundle or download the upstream `ocr` binary.

The first release targets Python 3.10-3.13 on Linux and macOS. The public API, CLI, environment contract, and generated schemas remain provisional before 1.0.

## Install

Install the Python package from PyPI and install a supported upstream OCR binary separately:

```console
python -m pip install open-code-review-toolkit
ocr --version
ocr-ci --help
```

The current compatibility target is upstream OCR `1.7.11`. CI should pin the release and verify its published checksum before execution.

## GitLab CI quick start

1. Configure protected/masked `GITLAB_API_TOKEN` and LLM variables in GitLab.
2. Pin and checksum the upstream OCR binary.
3. Install this package.
4. Run the five helper stages around `ocr review`:

```console
ocr-ci preflight
ocr-ci configure
ocr-ci mcp-config
ocr-ci context --output .review-context/dependencies.md
# run: ocr review ... --format json
ocr-ci post --result /tmp/ocr-result.json --stderr /tmp/ocr-stderr.log
```

See the fully synthetic [`examples/gitlab/ocr-review.gitlab-ci.yml`](examples/gitlab/ocr-review.gitlab-ci.yml) and the [GitLab guide](docs/gitlab.md).

## Configuration and safety

Configuration is environment-only in v0.1. The [configuration reference](docs/configuration.md) documents supported `OCR_*`, `CI_*`, `GITLAB_*`, and MCP inputs. Posting requires `GITLAB_API_TOKEN`; job tokens and legacy aliases are deliberately unsupported.

Repository content, OCR output, and provider responses are untrusted inputs. The toolkit applies bounded reads and writes, secret redaction, Unicode normalization, Markdown/quick-action neutralization, fingerprinted comments, ownership boundaries for human replies, and rollback controls. Review the [security and trust model](docs/security.md) before enabling write access.

## Development and release

- [Contributing](CONTRIBUTING.md)
- [Development guide](docs/development.md)
- [Security policy](SECURITY.md)
- [Release process](docs/release.md)
- [Changelog](CHANGELOG.md)

Licensed under Apache-2.0.
