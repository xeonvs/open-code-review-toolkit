# GitLab integration

GitLab is the toolkit's first forge provider. The provider layer owns GitLab API identity, merge-request snapshots, discussions, notes, approval writes, and pagination semantics; the evidence, context broker, DLP, store, MCP, and review lifecycle remain provider-neutral. Merge-request code, metadata, discussions, and repository guidance are untrusted even when CI credentials are protected.

## Installation

Install `open-code-review-toolkit` from PyPI and install Open Code Review separately. Use the exact recommended OCR version and asset checksum from the [compatibility manifest](../compatibility/ocr-support.json); the toolkit package never downloads OCR.

Start with the [complete checksum-pinned pipeline](../examples/gitlab/ocr-review.gitlab-ci.yml), then choose one configuration from the [GitLab mode matrix](../examples/gitlab/README.md). The pipeline keeps the repository's lint/test stage ahead of AI review, verifies the release runtime lock and toolkit wheel, installs hash-locked binary dependencies followed by the wheel, checks dependency consistency, runs preflight and configuration, performs one production `ocr-ci review`, and makes `ocr-ci post` the sole GitLab write boundary. The rules pack adds Jinja, conventional Ansible-role templates, and Twig to the recommended OCR file selection; project exclusions still win.

## Required configuration

The complete variable inventory, owner, requirement, exact default, and behavior are in [Environment configuration](configuration.md). The principal secrets are:

- `GITLAB_API_TOKEN`: a dedicated bot token with the minimum project/API permissions needed for the selected reads and writes;
- `OCR_LLM_TOKEN`: the LLM gateway credential used by OCR;
- governed federation credentials named by reviewed `token_from`, `headers_from`, or local-only `env_from` entries.

The public pipeline stores the OCR binary checksum as the non-secret `OCR_SHA256` pin. Store actual credentials as masked, protected CI variables; do not place their values in YAML, command arguments, repository evidence, or the generated bootstrap. GitLab job tokens are not accepted for posting.

The pipeline leaves `OCR_GITLAB_TARGET_PROTECTION_MODE` unset so its pinned toolkit wheel supplies the default. In toolkit 0.13.0, that default is `auto`. If the actual target is protected, it remains its own policy authority. If it is unprotected, the toolkit reviews only this MR's actual delta under the same project's captured protected default-branch policy. Set exact `required` to keep the former strict behavior, or exact `unprotected` to choose the earlier limited profile. Explicit empty, malformed, mixed-case, or unknown values fail closed. Neither unprotected-target path can add an automatic approval, even when `OCR_AUTO_APPROVE=true`; an earlier bot approval may remain until GitLab's own reset or invalidation policy removes it.

Projects inheriting the unset value need no CI/CD variable or policy-field
change. A shared CI template that explicitly sets `required` keeps rejecting
unprotected targets until its owner changes that one central setting to `auto`;
the toolkit does not override explicit operator intent.

`OCR_REVIEW_LANGUAGE` defaults to `English`; `Russian` is one example of an explicit review language. The example pins its qualified OCR release and sets `OCR_REVIEW_EFFORT=medium`, allowing two review rounds; `low` and `high` explicitly select one or three. OCR may stop early when a round adds no finding. OCR scales its 15-minute per-subtask base to 15/30/45 minutes for low/medium/high, so the example allows 45 minutes at the GitLab job boundary. `OCR_MAX_TOOLS=0` selects the embedded template default `100`. Values `1-49` report normalization to `50` but remain effectively `100`; explicit `50` also cannot lower the template, and only a value above `100` raises the cap. `OCR_MAX_TOKENS_BUDGET` defaults to `0`, meaning unlimited; a positive budget may stop dispatch and produce an explicitly partial, automatic-approval-ineligible review. `OCR_LLM_MAX_COMPLETION_TOKENS` defaults to unset and separately controls only the provider request's completion/output cap. Select an explicit value only from the deployment's provider/model contract; the toolkit does not recommend or hardcode a provider-specific cap.

OCR semantically groups related changed files before review and filters candidates per group. Its private grouping and other-files prompts use status-first `STATUS   path (+N/-M)` entries; the toolkit does not parse that inventory in production. Grouping, filtering, and multiple rounds can increase provider requests, latency, and token cost, while the manifest and aggregate budget continue to report completeness. Grouping, grace-round, provider-native reasoning/thinking, and tool-choice request state are retained only inside OCR's isolated private session. Group labels, paths, reasoning, signed/encrypted native payloads, and request controls remain untrusted: the toolkit does not publish or use them for severity, fingerprints, lifecycle commands, receipts, DLP counts, telemetry, tool/token summaries, or approval. OCR's separately configured telemetry may export high-cardinality repository-derived values, so keep `OCR_TELEMETRY_ENABLED=false` unless the exporter and retention policy are approved.

The summary keeps four inputs separate: OCR manifest coverage, publication integrity, published findings, and an optional OCR core advisory. Complete manifest coverage that later loses public fields keeps completed native analysis distinct from incomplete publication. It is labelled `Analysis complete; output incomplete`; it is warning-bearing and approval-ineligible, but it is not called incomplete OCR coverage and does not invent failed-file diagnostics. Actual partial, failed, waived, or budget-stopped manifest coverage keeps its stronger status. Ordinary OCR warnings retain their own complete-with-warnings state. The reviewer guide ranks bounded focus areas only when at least two findings are published; one finding remains in its inline or fallback discussion without a duplicate snippet. Security focus uses explicit published metadata, strong vulnerability terms, and closed injection classes rather than the standalone word `injection`, so neutral knowledge/dependency terminology cannot increase its count or effort estimate.

Toolkit 0.13.1 adds a separate effective repository-coverage line when the MR
changes a qualified Git submodule pointer. The installed OCR 1.13.3 reviews
selected ordinary files against the original MR `B..H` range; the changed
pointer and submodule contents remain unreviewed. Receipt v14 records only
closed counts and the partial reason. The GitLab adapter checks those counts
against Git and OCR's native selected/completed manifest before posting, keeps
prior finding discussions, and never automatically approves this run. A
gitlink-only or fully excluded ordinary diff produces a v6 no-model advisory
note; default posting exits 0 and strict posting exits 1. Older or unqualified
OCR/gitlink shapes stop before the model and cannot claim a partial review.

The collapsed technical details keep aggregate input/output/cache token usage separate from OCR tool activity. The existing `all OCR tool calls` line lists every non-zero count for the closed review set (`file_read`, `file_read_diff`, `file_find`, `code_search`, `code_comment`, `task_done`, `ocr_toolkit_evidence`, `ocr_toolkit_evidence_search`, `ocr_toolkit_evidence_coverage`, `context_list`, and `context_get`) and is omitted when that admitted list is empty. These counts help explain whether OCR read context, searched the repository, checked cross-file diffs, consulted toolkit evidence, searched unknown evidence identities, checked absence coverage, or emitted review output; they are not per-tool token attribution. Dynamic external MCP tool names remain private and appear only through the existing verified per-server aggregate. A separate action line contains only reconciled non-zero `summary/list/get/search/coverage` counts; arguments, queries, scopes, IDs, and results stay private. Tool and token lines remain independent of `passed`, `private-sanitized`, or `publication-filtered` receipt state. If OCR accepts a background above its recommended character count, a separate `OCR core advisory` line contains only the actual and recommended counts. It does not become a warning or change review completeness or approval eligibility.

## Choose one operating mode

`OCR_REVIEW_CONTEXT_MODE` selects `off`, `metadata`, or `enriched`; governed federation is configured independently through registry v2.

| Mode | Context admitted to OCR | Network/tool boundary | Approval posture |
| --- | --- | --- | --- |
| [Identity only](../examples/gitlab/modes/identity-only.gitlab-ci.yml) | No MR title, description, labels, source branch, or discussion text | GitLab identity/policy reads before OCR | May approve when every deterministic gate passes |
| [Metadata](../examples/gitlab/modes/metadata.gitlab-ci.yml) | Bounded MR title, description, labels, and source branch | GitLab reads before OCR | May approve when DLP and every other gate pass |
| [Explicit limited unprotected target](../examples/gitlab/modes/unprotected-target.gitlab-ci.yml) | `off` or bounded `metadata`; exact-target Rules are untrusted guidance | Built-in immutable evidence only; no protected policy or federation | Structurally comment-only when the actual target is unprotected |
| [Enriched discussions](../examples/gitlab/modes/enriched-discussions.gitlab-ci.yml) | Metadata plus protected-policy generic discussions and verified remediation threads | Stable double-read GitLab snapshot before OCR | Recipe is explicitly comment-only |
| [Same-revision CI outcomes](../examples/gitlab/context/policy-ci-outcomes.json) | Protected-policy exact check names and path prefixes | Twice-read exact-head GitLab pipeline/job metadata; no logs or artifacts | Context only; never suppression or approval authority |
| [Governed MCP federation](../examples/gitlab/modes/direct-mcp.gitlab-ci.yml) | Metadata plus model-selected admitted tool results | Registry-v2 HTTPS upstream through the bounded gateway | Used advisory tools are comment-only; unused services and successful `review_read` use are not independent blockers |

Approval in this table is available only when the actual target is protected;
an unprotected target remains comment-only under either selector profile.

The [bounded-context recipes](../examples/gitlab/context/) implement the
[protected policy v4](review-context.md#protected-policy-v4) contract for
discussions, remediation history, and exact same-revision CI outcomes. Copy one template to `.opencodereview/review-context-policy.json` and merge it into the selected protected policy branch before selecting `enriched`: the target when protected, or the default branch in `auto` for an unprotected target. A source-branch copy cannot expand authority. Missing or invalid policy stops before OCR. Legacy v1-v3 policies remain parse-only: safe selectors continue, optional references are skipped, and required references make the run comment-only. Configure external tools separately with registry v2. DLP rejection and required-source degradation block approval; every admitted remediation thread does too.

Governed federation is operator-owned and GitLab accepts only registry-v2 HTTPS upstreams. The gateway freezes the allowlist, validates schemas, arguments, origins, DLP and bounds, and reconciles content-free outcomes. Use dedicated least-privilege credentials and service-side tenant/object/field/operation authorization; gateway controls do not make an overprivileged service identity safe.

For an unprotected target under default `auto`, the protected default commit P supplies repository-relative Rules, context policy, accepted decisions, and eligible guidance. The current MR diff base B, actual target head T, and source head H remain separate: OCR reviews `B..H`, including when `B != T`. Code evidence retains its actual revision and is never relabelled as policy evidence; this single-MR review does not review a parent MR. `off`, `metadata`, `enriched`, and configured governed federation retain their established acquisition, DLP, object/tenant authorization, and budget gates. No repository policy field or new CI variable is needed. An omitted `--rule` or an external absolute Rules file cannot claim P provenance and is rejected on this path. Failed target or policy reads never cause a guessed fallback.

The built-in evidence MCP can also offer bounded `ref=target` facts at T:
metadata for changed paths present there and relevant declared/locked
dependency facts. The optional target snapshot does not include source text,
Rules, decisions, guidance, delta records, or an absence guarantee. Its caps
and possible omission stay explicit; it supplies code context only and cannot
make a parent or future integration review claim. [Repository evidence](configuration.md#repository-evidence)
owns the exact admission bounds.

The explicit `unprotected` recipe retains the earlier limited profile: only `off` or bounded `metadata`, no enriched context or federation, required repository Rules read from T as untrusted guidance, and no structured guidance or accepted decisions. It also stays comment-only. A valid v13 `auto` summary identifies the captured protected policy anchor by full P SHA and states that automatic approval was unavailable; explicit `unprotected` retains the *limited, comment-only mode* line. Neither status changes OCR completeness; old or contradictory receipts cannot assert the new authority. [Environment configuration](configuration.md#gitlab-target-protection-selector) owns the exact selector rules.

## First integration sequence

Use two merge requests for the recommended setup:

1. merge `examples/gitlab/rules.json` or the chosen repository Rules path and any protected policy configuration into the selected policy branch;
2. enable the OCR CI job in a later merge request, after the captured policy commit contains that configuration.

If review of the integration merge request itself is unnecessary, adding Rules and the CI job together can stop before OCR with a recognized setup-pending note when the configured repository Rules are absent from the selected protected policy commit and the bounded source candidate is safe. Retrying that same merge request cannot make source-branch Rules authoritative; subsequent merge requests work after the setup change merges. Explicit `unprotected` with missing target Rules still fails closed. A missing, malformed, stale, or mismatched private status stops posting without a merge-request note and leaves the earlier review intact; the error remains in the job.

An exact merge-request lifecycle read also precedes evidence collection. If the identity-bound MR is already `merged` or `closed`, no OCR/model work starts and one toolkit-owned plain status note is created or updated without replacing findings, summaries, suppression, discussions, or approval state. Every path that could otherwise return advisory success confirms the exact MR is still terminal; close/reopen timing therefore fails and requires a new review even after a note-side error. Its marker is recognized only in a reserved control preamble, never from finding text. `merged` is irreversible and may finish successfully; `closed` stays advisory-only, while `OCR_STRICT_POSTING=true` remains nonzero so a required gate cannot be reused after reopening. If the MR becomes terminal after v13 review, posting reports stale state before a normal publication write, preserves the prior review, and adds no approval. Unknown states, provider failures, and identity mismatches likewise fail closed before publication.

GitLab Code Owners and code-owner approval rules are separate project merge policy. They are not prerequisites for OCR execution and cannot give unprotected repository content policy authority. Likewise, a green advisory pipeline or allowed-to-fail OCR job proves neither that `ocr-ci review` completed nor that OCR or its model executed. Inspect the review result, manifest coverage, receipt, and published status.

## Production bot configuration

Use a dedicated bot account that is not the merge-request author. Give its project access token `api` scope and the minimum project role needed for the selected reads, notes, drafts, discussion management, and optional approval. GitLab approval rules, Code Owners, protected branches, and reset/invalidation policy remain authoritative.

Begin with a manual advisory job and `OCR_AUTO_APPROVE=false`. Enable strict posting or approval only after the project has reviewed published results, bot permissions, exact receipt gates, and all source-data boundaries. Keep result, stderr, evidence, generated OCR configuration, context stores, gateway state, and OCR sessions private to the runner and out of public artifacts. The local-only `ocr-ci review --preserve-private-artifacts` diagnostic is rejected by the validated GitLab merge-request profile and must not be added to a CI job.

Before treating the advisory job as a required gate, run `ocr llm test` with the same generated OCR configuration and protected credential path. `ocr-ci preflight` always checks that the required toolkit inputs exist and can optionally validate model metadata through `/models`, but that metadata read is not a full review request and cannot guarantee that a gateway credential, protocol, deployment, spending policy, or requested output cap will accept the later conversation. The toolkit never derives `OCR_LLM_MAX_COMPLETION_TOKENS` from `/models.max_completion_tokens`. Keep `allow_failure` only when a missing review is intentionally advisory; a green pipeline with an allowed-to-fail OCR job is not evidence that OCR produced a usable review.

The toolkit authenticates the token owner with live `GET /user`. No configured bot ID or username is trusted. The returned ID owns note/fingerprint checks; the validated username owns exact mention-command parsing.

## Operating model

`ocr-ci preflight` validates OCR compatibility, GitLab access, registry v2, upstream inventory, and optional model metadata. `ocr-ci configure` writes the isolated OCR configuration. `ocr-ci review` accepts a detached MR pipeline only: GitLab's predefined `CI_MERGE_REQUEST_EVENT_TYPE` must be `detached`, and its checked-out `CI_COMMIT_SHA` must match the authenticated current source H. The example uses `CI_MERGE_REQUEST_DIFF_BASE_SHA` for `--from` and `CI_COMMIT_SHA` for `--to`. In a detached pipeline the MR-specific source SHA can be empty. Merged-results, merge-train, missing, or contradictory event/commit identities stop before model execution; no project variable or merge-strategy change is required.

An intentionally absent toolkit receipt retains a compatible standalone
direct-posting path outside GitLab CI, without automatic approval or a v13
freshness claim. A detached GitLab MR job requires v13/v14 for normal result
publication: a missing receipt stays in the job and cannot publish findings or
replace the previous review. A present v9-v12 receipt remains readable for
historical diagnostics but blocks a new current MR publication.

The provider validates same-project ownership, the current MR diff base/start/head/version, source H, actual target branch/T/protection, and selected policy branch/P/protection before OCR. Missing, pending, malformed, or contradictory diff data is unavailable or stale, not an empty review; a valid empty delta is a normal no-change case. `ocr-ci review` collects immutable evidence from actual code revisions, admits context under the selected policy capability, applies DLP and budgets, runs OCR once, reconciles federation, validates the result, cleans private state, and attaches receipt v13. `ocr-ci post` hostile-reads that receipt rather than reconstructing authority from a later environment and rejects another `CI_JOB_ID` in a current-review result or preview/setup status when present. A successful result covers this MR only: no parent-MR lookup, chain review, integration claim, extra pipeline trigger, or merge is performed. Arbitrary valid branch names and a target with no parent MR are supported.

`off` still validates the source/diff, actual target and selected policy authority, merge-request author, and live bot identity while withholding mutable MR text. `metadata` admits only bounded DLP-checked title, description, labels, and optional source branch. Treat those fields as claims to compare with the diff, never as instructions, policy, or proof. A comment claiming “approved” or asking to skip security checks cannot authorize a tool, waive a gate, or grant consent, regardless of who authored it.

`enriched` loads the protected policy and may add one stable GitLab discussion snapshot, verified toolkit-owned remediation threads, and exact same-revision CI outcomes. Generic discussion and remediation projections are mutually exclusive for a toolkit-owned root. Remediation roots require both the authenticated live bot ID and a valid toolkit marker/fingerprint. Raw GitLab IDs, usernames, provider objects, and rejected values are not stored or returned. The model sees only opaque local handles; it cannot search GitLab or submit an arbitrary provider ID or URL.

`OCR_DLP_ENABLED` defaults to enabled. A parsed false value disables context/federation and publication DLP, emits a prominent GitLab warning, and makes the run comment-only. Service egress and GitLab publication may then expose sensitive data, and the toolkit cannot retract it. Diagnose locally with `--preserve-private-artifacts` before considering this escape hatch; invalid values fail before OCR.

Remediation text is untrusted review history. It may locate a claim that OCR must re-check against current code and tests, but it cannot change severity, prove a fix, suppress or resolve a finding, issue a lifecycle command, or authorize approval. Any admitted remediation record therefore makes the review comment-only. DLP-clean non-remediation context does not independently disable an otherwise eligible receipt; a DLP rejection cannot make approval easier.

A protected CI pass is narrower than a general green-pipeline claim: it applies only to its exact reviewed head, exact protected job name, and declared path prefixes. It may challenge an unconditional claim about code that the job actually exercised, but it cannot suppress a finding, prove unrelated absence, change severity/lifecycle, or authorize approval. Stale, advisory, skipped, canceled, failed, unknown, incomplete, mutated, or ambiguous data cannot be treated as a required pass. The toolkit does not fetch job logs, artifacts, URLs, users, runners, variables, or raw IDs.

Provider configuration is forge-neutral. Configure and preflight share one normalized absolute HTTPS API root, explicit protocol, headers, request-body controls, and optional models URL. A protocol-mismatched terminal endpoint, embedded credential, or fragment fails before OCR. A classified provider failure stays in the job because no completed v13 review identity can authorize an MR note; raw provider/model fields, response bodies, request IDs, paths, warnings, and stderr remain private. The review log may contain one toolkit-authored line of closed HTTP detail and non-zero aggregate retry counts from a fully validated retry report. `rate-or-spending-limit` job guidance suggests lowering `OCR_REVIEW_CONCURRENCY` and/or `OCR_LLM_MAX_COMPLETION_TOKENS`, starting a new merge request pipeline, and then checking provider request/account limits without claiming either setting caused the failure. The previous successful review remains visible, no failed-result findings are posted, and approval is not attempted.

When a merge request introduces a repository-owned OCR rules path absent from both selected protected policy baselines, `review` stops before OCR and `post` may publish only the static setup-pending message after hostile identity validation. The source file never becomes policy evidence for its own merge request. Under explicit `unprotected` with an actually unprotected target, target Rules are still mandatory but remain untrusted guidance; a missing target blob fails before OCR without promoting the source copy.

## Reviewer commands and no-commit reruns

Inside a toolkit-owned discussion, a human non-system reply may contain exactly one lifecycle command:

- `/ocr suppress` or `@<live-bot-username> suppress` keeps the discussion open and suppresses the matching finding;
- `/ocr resolve` or `@<live-bot-username> resolve` suppresses the finding and resolves the discussion after the next successful posting transaction.

Commands are case-insensitive and allow surrounding whitespace only. For a bot named `mr.bot`, `@mr.bot resolve` is valid. Prose, code blocks, `supress`, another mention, `retest`, bot replies, system notes, and commands outside a toolkit-owned discussion are ignored. If several recognized human commands exist, the newest wins. See [GitLab review operations](operations.md#reviewer-commands) for the state machine.

The GitLab integration runs in CI and does not receive a comment event by itself, so `@bot retest` is not supported. To rerun without a commit, use GitLab's [Retry UI/API](https://docs.gitlab.com/ci/jobs/#retry-jobs). Creating a new merge-request pipeline is also available through the [merge-request pipeline API](https://docs.gitlab.com/api/merge_requests/#create-merge-request-pipeline). A deployment that wants comment-triggered reruns needs a separate authenticated and authorized [Note Hook receiver](https://docs.gitlab.com/user/project/integrations/webhook_events/); that receiver is outside this toolkit's trust and lifecycle boundary.

## Accepted project decisions in a later merge request

Copy [`examples/gitlab/accepted-decisions.md`](../examples/gitlab/accepted-decisions.md) to `.opencodereview/accepted-decisions.md` and merge it through an earlier reviewed change to the selected protected policy branch. In a later merge request that touches a matching scope, the evidence collector marks the decision applicable against the actual code delta and the bootstrap lists its decision ID and scope.

OCR can then inspect the actual protected decision through the built-in `ocr_toolkit_evidence` tool:

```json
{"action":"list","kind":"repository.accepted_decision","ref":"policy"}
```

The returned record contains a stable `id`. OCR retrieves that exact record with:

```json
{"action":"get","id":"<id returned by list>"}
```

The rationale is evidence to compare with current code, tests, and applicability, not a suppression or authorization rule. A decision added or changed by the current source branch is excluded. The full format, scope grammar, staleness, and authority limits are in [Accepted project decisions](configuration.md#accepted-project-decisions).

Use the authenticated current MR diff base and source SHAs, never a synthetic merge-result commit, for the reviewed range. Keep the self-test job manual. See [GitLab review operations](operations.md#current-mr-freshness) for publication and approval revalidation, [Security and trust model](security.md), [Environment configuration](configuration.md), and [Bounded review context](review-context.md) for the exact contracts.
