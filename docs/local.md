# Standalone local review

Use the local provider to review immutable Git changes and read the admitted
findings in a Markdown artifact and the console, without connecting the repository to a forge.
Install the toolkit and its [qualified OCR binary](../compatibility/ocr-support.json),
then configure the LLM environment described in [configuration.md](configuration.md).

```console
ocr-ci preflight --local
ocr-ci review --local --result review.json --stderr review.stderr --report review.md -- --commit HEAD
```

For a range, replace `--commit HEAD` with `--from BASE --to HEAD`. Both ends are
resolved to immutable commits before execution. Working-tree snapshots, repository
scans, resumed sessions and competing repository/background inputs are unsupported.
The toolkit owns JSON output and agent audience; contradictory `--format` or
`--audience` options fail before execution.

## Inputs and isolation

Local mode is explicit. It may run in a CI test job, but inherited CI identity does
not select a forge provider, acquire change-request data or authorize publication.
`preflight --local` checks the OCR binary and configured LLM, not forge access.
Set `OCR_REVIEW_CONTEXT_MODE` to `off` or leave it unset; other context modes and
any `OCR_REVIEW_CONTEXT_ADAPTERS_JSON` value are rejected before input acquisition.
Local mode has no discussion, command, suppression or approval channel.

The mandatory repository-evidence MCP remains enabled. Registry validation and
the toolkit's self-query do not substitute for the review's completed evidence
summary call: the result's claimed usage must reconcile with the real action
record. Operator-configured external MCP entries remain optional and cannot
replace mandatory evidence. Their capabilities and trust boundaries are described
in [MCP composition](configuration.md#mcp-composition-and-trust-boundary).

## Output and failures

Standard output contains shared review health, coverage, warnings, tool/token and
verified MCP facts, DLP admission status, and every admitted finding. It has no
posting caps, remote badges, HTML disclosures or platform publication claims.
Finding text and code are rendered as literal fenced content. Diagnostics use
standard error; JSON stays in the private `--result` artifact.

The same complete Markdown is published to `--report PATH`, defaulting to the
`--result` path plus `.md`. The report target must be fresh and distinct from
JSON/stderr; existing files and symlinks are never overwritten. Publication is
atomic with owner-only (`0600`) permissions. This is the same OCR/LLM/tool-use,
validation and DLP pipeline as CI, with local filesystem delivery instead of
forge API publication. It does not replace OCR with another local review engine.

Successful execution still requires result validation, DLP and cleanup. The
admitted JSON has no fabricated forge receipt. Filtered findings stay absent from
the console and safe JSON; omissions and original coverage remain explicit.
Legacy results without coverage counts remain unknown, not a fabricated complete
coverage manifest. A blocked run returns nonzero and prints a closed failure
summary naming its stage without presenting untrusted findings. An unavailable
output stream cannot guarantee delivery of that summary. Failures after the
report destination has been accepted also publish the closed failure report;
configuration or unsafe-destination failures print only to the console. A failed
artifact or console delivery returns nonzero; a completed artifact remains
available if the console fails afterward.

`--local` cannot be combined with legacy `--preserve-private-artifacts`, because
that diagnostic path intentionally bypasses ordinary result finalization. The
legacy option without `--local` retains its existing sensitive-artifact semantics.
