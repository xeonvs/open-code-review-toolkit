# Execution History Index

`PLANS.md` owns active, blocked, and recently completed execution. This archive preserves older completed plans so an agent can recover the decisions, validation evidence, merge receipts, hashes, and resume context behind a published toolkit version.

## Release index

| Stable tag | Primary archived plan | Related context in the same archive |
| --- | --- | --- |
| `v0.4.6` | [OCR 1.8.9-1.8.10 qualification and toolkit 0.4.6](../../../PLANS.md#completed-plan-qualify-ocr-189-1810-and-release-toolkit-046) | The latest externally reconciled cycle remains in the active registry until the next stable closure. |
| `v0.4.5` | [OCR 1.8.7-1.8.8 qualification and toolkit 0.4.5](releases.md#plan-toolkit-0-4-5) | Compatibility-chain automation and the toolchain update included in that release. |
| `v0.4.4` | [Evidence coverage and GitLab review health](releases.md#plan-toolkit-0-4-4) | Scoped completeness, failed-file coverage, and summary separation. |
| `v0.4.3` | [OCR compatibility automation hardening](releases.md#plan-toolkit-0-4-3) | Retention and compatibility issue lifecycle. |
| `v0.4.2` | [OCR 1.8.3 qualification](releases.md#plan-toolkit-0-4-2) | CLI and per-file terminal-state compatibility. |
| `v0.4.1` | [OCR 1.8.1-1.8.2 qualification](releases.md#plan-toolkit-0-4-1) | Partial-review and compatibility hardening. |
| `v0.4.0` | [M1 evidence architecture](releases.md#plan-toolkit-0-4-0) | Typed evidence, compact bootstrap, built-in MCP, legacy removal, security review, publication, and the preceding [M0 reconciliation](releases.md#plan-m0-reconciliation). |
| `v0.3.1` | [OCR 1.8.0 and native remote MCP](releases.md#plan-toolkit-0-3-1) | Native HTTPS transport and stable publication. |
| `v0.3.0` | [M0 foundation](releases.md#plan-toolkit-0-3-0) | Compatibility policy, security gate, [roadmap dependency correction](releases.md#plan-roadmap-dependencies), and stable publication. |
| `v0.2.1` | [Stable 0.2.1 publication](releases.md#plan-toolkit-0-2-1) | [Strategy and roadmap establishment](releases.md#plan-strategy-roadmap) and [OCR 1.7.17 qualification](releases.md#plan-ocr-1-7-17). |
| `v0.2.0` | [Stable 0.2.0 publication](releases.md#plan-toolkit-0-2-0) | [GitLab discussion lifecycle](releases.md#plan-gitlab-discussions) and [non-release workflow no-op](releases.md#plan-release-no-op). |
| `v0.1.0` | [Stable 0.1.0 release and security remediation](releases.md#plan-toolkit-0-1-0-release) | [Release preparation](releases.md#plan-toolkit-0-1-0-preparation), [initial extraction](releases.md#plan-initial-extraction), [private TestPyPI preview](releases.md#plan-private-testpypi-preview), [OCR 1.7.12 hardening](releases.md#plan-ocr-1-7-12), and [language/TestPyPI alpha work](releases.md#plan-language-testpypi-alpha). |

The most recent completed release cycle remains in `PLANS.md` until the next stable cycle is externally reconciled. During each post-release no-release closure, move the previously retained cycle into `releases.md`, add or update its tag row here, verify every anchor, and preserve the original receipts rather than summarizing away audit evidence.
