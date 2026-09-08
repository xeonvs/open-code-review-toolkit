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

## Private debug bundle

Add `--debug-dir PATH` to retain diagnostics from the same review execution.
The directory must be fresh, must not traverse symlinks, and must not contain
the normal result, stderr or report destinations. It is created with mode `0700`;
its files use `0600`. This option requires `--local` and rejects legacy private
artifact retention. It does not bypass validation, DLP or ordinary session cleanup.

| Artifact | Contents | Maximum retained bytes |
| --- | --- | --- |
| `raw-result.json` | Original OCR output before finalization, when execution reached OCR | 20,000,000 |
| `raw-stderr.log` | Original OCR diagnostic stream | 2,000,000 |
| `safe-result.json` | Successfully finalized JSON, if available | 20,000,000 |
| `summary.md` | Admitted report or closed failure summary | 20,000,000 |
| `journal.json` | Actual phase observations and value-free DLP decisions | 1,000,000 |

Raw files can contain rejected confidential content. Do not upload the bundle
as a public CI artifact. No environment dump, authentication token, full runtime
configuration or OCR session is copied into it. Configuration observations name
the selected protocol, language, review effort and logging flags; the model
selection is represented by a SHA-256 fingerprint, not provider acceptance.

The journal records passed, failed, degraded and not-run checks at their execution
owners. Passing a collection phase does not imply complete repository coverage;
coverage remains a separate review fact. DLP entries describe real detection,
omission or redaction branches, with bounded locations, sizes and value digests.
They are not the results of a second DLP scan and do not authorize publication.
At most 1,000 DLP decisions and 128 phase transitions are retained; omitted counts
remain explicit. Unknown field names are fingerprinted rather than copied.

Capture metadata distinguishes missing, unavailable and not-run artifacts.
Truncation and source changes are explicit. `sha256_captured` covers only the
retained bytes, never an implied complete source. A truncated Markdown/JSON copy
may end inside a UTF-8 character or JSON value; use the normal artifact for the
complete admitted output.

`complete: true` means the journal's observation lifecycle finished, not that the
review succeeded. Initial snapshots have `complete: false`. An unsafe initial
directory fails before review. Later diagnostic write failures do not replace the
review outcome or suppress cleanup: unavailable captures are marked in the journal,
and a journal write failure emits a bounded stderr warning. An earlier incomplete
snapshot can remain when the final journal cannot be written.
