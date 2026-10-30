# Private offline DLP audits

`ocr-ci dlp-audit` is a local diagnostic tool for testing production DLP against selected
text and code, including other projects. It ships with the toolkit on Linux and
macOS. Commands run manually, write private reports and never grant publication
or approval authority. They do not invoke OCR, import audited code, read
target-owned exclusions, or add a GitLab pipeline stage. Use a trusted toolkit
installation or its development environment:

```sh
ocr-ci dlp-audit --help
ocr-ci dlp-audit --state-dir "$audit_state" scan --help
```

## Capture and evaluate

The audit needs only the toolkit installation. OCR, LLM credentials and provider
preflight are unnecessary. The scanner is always enabled for this diagnostic
command, including when `OCR_DLP_ENABLED=false` is set for other toolkit work.
Ambient configured secret values still participate in DLP; only their keyed
set fingerprint persists, so changing that set invalidates comparison.

Select an explicit **private state directory outside every input root and Git
worktree**. Physical ancestors must not be symlinks; state directories require
mode 0700 and files mode 0600. The helper snapshots the selected input bytes for
later comparisons. Before capturing private code, inspect provenance and exclude
whole files containing working credentials, keys, measurements, dumps, generated
profiles or logs. Moving inputs, limits and unsupported inputs cannot pass.

For a new disposable private location, create and resolve it before the scan:

```sh
audit_state=$(mktemp -d)
audit_state=$(cd "$audit_state" && pwd -P)
```

```sh
ocr-ci dlp-audit --state-dir "$audit_state" \
  scan --root "$source_root" --git-ref "$immutable_ref"

ocr-ci dlp-audit --state-dir "$audit_state" \
  scan --root "$source_root" --files-from0 "$private_selection"

printf 'amount = 17\n' | ocr-ci dlp-audit \
  --state-dir "$audit_state" scan --stdin
```

The file-list mode accepts a bounded UTF-8, NUL-terminated list of exact relative
file names. It does not recurse. Symlinks, hardlinks, devices and FIFOs are not
read as source. Git mode reads immutable blobs with the production Git reader,
without checking them out, fetching or initializing submodules. Gitlinks and
unsupported/binary inputs are explicit omissions, not successful checks. File
selection is checked again before capture to reject a changing source tree.

When source copying is inappropriate, add `--metadata-only` to an explicit
file-list scan. Only authenticated metadata/identities persist; source bytes
remain in memory. `scan --snapshot` then rereads the exact original files and
checks every fingerprint before and after evaluation. Changed or unavailable
originals make replay invalid, rather than comparing different corpora. This
mode cannot be combined with Git/snippet input. It preserves full evaluation
without retaining a second copy of potentially sensitive code.

Input limits are 20000 files, 1 MiB per file, 16 MiB total and 200000
whole-file/nonempty-line units. Oversize files are rejected from metadata before
reading; NUL bytes or invalid UTF-8 reject binary content during acquisition,
regardless of filename extension. Git size preflight applies the remaining
aggregate budget before transferring blob bodies.

A single isolated worker is reused within one scan and evaluates one file at a
time; no source-bearing request queue is built. Each exchange has a fresh request
identity and bounded length framing. A stale/invalid response cannot count as
evaluation of the next file. Source-bearing locals are released between files. Defaults are 900 seconds overall, 60 seconds per file and 120
seconds per Git command. For large projects or slower hosts, use `--seconds`
(1–86400), `--file-seconds` and `--git-seconds` (both 1–3600). The total deadline
also caps each child process and source verification. Increasing time does not
increase input/output budgets. Existing review Git readers keep their original
timeouts. Effective execution settings are recorded but do not make otherwise
identical complete scanner comparisons incompatible.

At most 80000 rejection records and 24 MB of their encoded data are retained.
These limits are enforced while producing and accepting records, leaving room
inside the 32 MB authenticated-document limit for omissions and the envelope.
A capped file contributes no partial pass population; unprocessed files remain
explicit omissions. Worker timeout, launch failure, unsuccessful exit, observed
allocation failure and output caps have closed diagnoses. A killed worker alone
is not classified as out of memory. Timeouts/cancellation kill and reap the owned
worker. A failed peer is reaped and restarted for a later file; normal scan
teardown also reaps it. Storage/allocation failures that prevent a report return exit 2; the
previously saved corpus inventory still owns raw cleanup. These are bounded
application-data/work limits, not an exact process-RAM guarantee. Workers execute
only the trusted installed toolkit; Python isolation prevents imports from the
audited working directory.

Every whole file and nonempty line is checked as publication text and as an
existing-code field. Text uses the ordinary prose contract; only code permits
horizontal tabs. A raw rejection is replayed through the real immutable
source-proof and publication-projection owners. Raw admission dominates the
source interpretation; integration tests protect that relationship. Proof
eligibility remains bounded by the production code-field contracts. Whole-file
and line observations are different units; a count is not a false-positive rate.
The scanner records one primary rejection per role, not every possible match.

## Reports and exact classifications

Console output contains generated identities and aggregate counts. Private JSON
and Markdown reports contain no snippets or matched values. The authenticated
corpus manifest maps generated file slots to local source locators; keep it
private too. JSON reports contain each rejected unit's role, line, primary
reason, detector and source-proof fact. Markdown lists the ten largest primary
detector groups. The key, local paths and reports must never be committed or
attached to a public issue. Use independently constructed synthetic examples
for public regressions.

An operator can classify exact rejected identities from a complete run:

```sh
ocr-ci dlp-audit --state-dir "$audit_state" \
  annotate "$baseline_run" --label confirmed-benign --hit "$exact_hit"
```

Labels mean:

- `expected-protection`: this exact unit must remain rejected.
- `confirmed-benign`: this exact unit should be admitted; its rejection remains
  an unsatisfied expectation, even after classification.
- `conservative-ambiguity`: retain the reviewed conservative rejection until
  stronger evidence justifies a change.

These labels do not suppress scanning or modify runtime policy. A private HMAC
key binds identities to the exact corpus, file bytes, unit and sink role.
Annotations also bind the profile and effective environment-secret set. New
inputs cannot inherit an old exemption. A changed rejected reason or proof fact
needs an explicit new classification. Untriaged rejections remain visible.

## Replay and compare

Keep the captured corpus unchanged while changing the scanner:

```sh
ocr-ci dlp-audit --state-dir "$audit_state" \
  scan --snapshot "$corpus_id"

ocr-ci dlp-audit --state-dir "$audit_state" \
  compare "$baseline_run" "$candidate_run"
```

Comparisons require complete identical populations, profile and secret-set
fingerprints. They include previously passing inputs. A verified complete run's
rejection set plus exact evaluated population allows the other units to be
treated as passes; a missing record in an incomplete run proves nothing.
New rejections, lost protection, unexplained admissions and unreviewed decision
changes require triage. A lower rejection count alone cannot pass acceptance.
After fixing findings, repeat both complete captured corpora and scan the new
candidate repository, then inspect every unexpected transition.

Exit 0 means complete evaluation with satisfied expectations; exit 1 means a
complete evaluation needs triage or has a regression; exit 2 means invalid,
incomplete or incomparable execution. `annotate` exit 0 only confirms the state
update, not scanner acceptance. Reports are diagnostics, not review receipts.

## Remove raw snapshots

Source copying has an authenticated ownership inventory before any raw write,
including when capture is interrupted. Preserve its recovery location while
work is active. After the task's required verification, remove every owned raw
corpus:

```sh
ocr-ci dlp-audit --state-dir "$audit_state" \
  cleanup "$corpus_id"
```

Cleanup revalidates ownership, rejects unowned entries and substituted links,
removes only inventoried raw copies, verifies their absence, and is idempotent.
It preserves original inputs and source-free reports/expectations. Metadata-only
corpora have no raw source directory to remove. Cleanup failure leaves the task
incomplete; do not replace it with a recursive deletion of an arbitrary directory.
