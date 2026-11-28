# Local GitLab review reports

Use `ocr-ci telemetry` on a workstation to measure delivery and the surrounding merge request process. An authorized collector reads GitLab with `glab`. Anyone authorized to hold the private snapshot can later generate the HTML report and aggregate JSON offline with the toolkit alone.

## Collect and refresh

Run the first collection from a directory where `glab` selects the intended GitLab instance. Check that context with `glab auth status`. Collection requires an HTTPS instance URL in the authenticated user's profile. For an update, select the same instance recorded in the snapshot. Use a project ID or namespace/path to select a project. Repeat `--project` for more than one.

```sh
ocr-ci telemetry collect --project example/service --from 2026-11-01
ocr-ci telemetry collect --update
```

Without `--project`, discovery uses projects with observed contributions by `mr.bot` visible to the signed-in user. This population can miss projects with no bot activity. An explicit selection includes accessible projects with zero events. Each selected project's MR population includes MRs created during the period, including MRs with no observed review. `--bot` changes the exact bot username. `--job-name` replaces the default `open_code_review` job used to count attempts and can be repeated. The default excludes the sample self-test. Explicitly selecting `--job-name open_code_review_self_test` includes qualifying attempts from that job. A published Toolkit result can still be observed if job history is unavailable.

The first collection defaults to November 1, 2026 through today in UTC, inclusive. `--from` and `--to` accept ISO dates. Updates retain the original scope and job selection. A moving end date advances to today. An explicit end date stays fixed until extended with `--update --to`. Use another state directory for a different population or a fresh observation history. Updated snapshots retain previously observed publications. A message already deleted before the first collection is unknown.

The period selects MRs by creation date. Cohort totals include observations of those MRs available at collection, which may include a review published after the period. Calendar charts count publications and other events by their own dates inside the period. The fourteen-day completion comparison uses the earlier of the period end and collection time.

## Generate the report

```sh
ocr-ci telemetry report --lang en
ocr-ci telemetry report --lang ru --anonymize
```

Each command prints a fresh local directory containing `report.html` and `report.json`. Open the HTML locally. The command can run with an empty network environment, without the OCR executable, a model key or `glab`. `--lang` overrides `OCR_REVIEW_LANGUAGE`; English is the default. The JSON uses stable English field names in both languages.

The overview shows delivery, review attempts, outcomes, changes over time and usage. The process section covers participation, observed discussion and revision activity, elapsed time and project history. Before/after comparisons require at least ten comparable MRs on each side per project. The technical section reports signals observed in Toolkit publications and data completeness. A successful job and a successfully published review are separate observations. A reply, resolved discussion or later commit alone cannot establish that a defect was corrected. Read each fraction with its stated denominator. A short observation window or restricted endpoint can leave a metric unavailable.

| Data in GitLab | What the report can observe |
| --- | --- |
| Toolkit status and summary notes | Pre-model stops, review outcomes, partial findings, terminal lifecycle and status-note classifications. Some failures end after a CI attempt without publishing a note. |
| Findings and technical details | Finding counts, severity and category, posting placement, suppression, review mode, selected/completed/reused/failed/waived coverage, and repository coverage when published. |
| Publication DLP and federation signals | Validated counts by stage and reason, including source classes where present. A source can contribute to several counts. Neither a matched value nor an argument to a tool is part of the report. |
| Usage lines | Token buckets, OCR tool attempts, MCP use and completed evidence actions. A missing line provides no observed zero. |
| Jobs and project-scoped MR data | Attempts, retries, snapshots of discussions and reactions, approvals, dates and comparable first-parent changes. Restricted or incomplete sources limit the observations available. |

The collector verifies the configured bot's identity before interpreting its messages. A human quoting an entire Toolkit summary contributes no bot publication. Review and posting modes can expose different fields; the report records what GitLab actually received.

### Cost and model coverage

Collection uses the configured provider's model catalog and headers, including `OCR_LLM_MODELS_URL` or the catalog derived from `OCR_LLM_URL`, and `OCR_LLM_TOKEN`. Catalogs can publish per-token `prompt`, `completion` and `input_cache_read` prices. The snapshot stores normalized rates and capture time. Existing rates carry their original timestamp when an update cannot refresh them. Prices can change and are estimates for the recorded usage, not invoices.

New GitLab review summaries can include the model selected for that run alongside token usage in Technical details. The toolkit publishes the model name when the native result agrees with the run's configured model and the field passes DLP. Some legitimate IDs, including certain dated identifiers, can resemble protected values. In that case the review continues with the model field omitted. A provider may route a model alias internally. The report uses the published name for pricing and preserves it in the private snapshot.

Older messages can lack the model name. For those results, collection reads the project's `OCR_LLM_MODEL` variable for the default environment scope. The value and observation time stay in the private snapshot. A historical estimate uses the model configured at collection time. Earlier jobs may have used a different model or overridden that setting. The report labels these estimates separately from costs based on a model recorded in the review.

Reading a project variable can require more access than reading MRs. If the variable is inaccessible, protected, masked, hidden or scoped to another environment, collection continues. Missing usage or prices also reduce cost coverage. The report shows the denominator for priced results. A catalog is requested only when a model is available. `collect --no-costs` skips both the project-variable and pricing requests. `report --no-costs` omits cost information from both outputs.

## Private files and access

The default directory is `$XDG_STATE_HOME/ocr-toolkit/telemetry` or `~/.local/state/ocr-toolkit/telemetry`. Supply the same `--state-dir` after `collect` or `report` to use another physical directory outside Git worktrees. A snapshot contains private project and MR data required for updates. Keep it, every HTML/JSON output and their directories out of repositories and CI artifacts. Directories require mode `0700` and files `0600`. For offline use, copy `snapshot.json` through an approved private channel, preserving permissions, to a private state directory on the recipient's machine.

An ordinary HTML report can contain project labels and MR links. `--anonymize` removes links and substitutes report-local labels. Both forms remain private. Note bodies, code, diffs, credentials and provider error responses do not belong in the resulting files or collection diagnostics.
