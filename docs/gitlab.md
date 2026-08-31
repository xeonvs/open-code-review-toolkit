# GitLab integration

GitLab is the toolkit's first forge provider. The provider layer owns GitLab API identity, merge-request snapshots, discussions, notes, approval writes, and pagination semantics; the evidence, context broker, DLP, store, MCP, and review lifecycle remain provider-neutral. Merge-request code, metadata, discussions, and repository guidance are untrusted even when CI credentials are protected.

## Installation

Install `open-code-review-toolkit` from PyPI and install Open Code Review separately. Use the exact recommended OCR version and asset checksum from the [compatibility manifest](../compatibility/ocr-support.json); the toolkit package never downloads OCR.

Start with the [complete checksum-pinned pipeline](../examples/gitlab/ocr-review.gitlab-ci.yml), then choose one configuration from the [GitLab mode matrix](../examples/gitlab/README.md). The pipeline keeps the repository's lint/test stage ahead of AI review, installs the toolkit wheel with hash verification, runs preflight and configuration, performs one production `ocr-ci review`, and makes `ocr-ci post` the sole GitLab write boundary. The rules pack adds Jinja, conventional Ansible-role templates, and Twig to the recommended OCR file selection; project exclusions still win.

## Required configuration

The complete variable inventory, owner, requirement, exact default, and behavior are in [Environment configuration](configuration.md). The principal secrets are:

- `GITLAB_API_TOKEN`: a dedicated bot token with the minimum project/API permissions needed for the selected reads and writes;
- `OCR_LLM_TOKEN`: the LLM gateway credential used by OCR;
- adapter or direct-MCP credentials named by reviewed `env_from` or `headers_from` entries.

The public pipeline stores the OCR binary checksum as the non-secret `OCR_SHA256` pin. Store actual credentials as masked, protected CI variables; do not place their values in YAML, command arguments, repository evidence, or the generated bootstrap. GitLab job tokens are not accepted for posting.

`OCR_REVIEW_LANGUAGE` defaults to `English`; `Russian` is one example of an explicit review language. The example pins its qualified OCR release and sets `OCR_REVIEW_EFFORT=medium`, allowing two review rounds; `low` and `high` explicitly select one or three. OCR may stop early when a round adds no finding. OCR 1.11.0 scales its 15-minute per-subtask base to 15/30/45 minutes for low/medium/high, so the example allows 45 minutes at the GitLab job boundary. `OCR_MAX_TOOLS=0` selects the embedded template default `100`. Values `1-49` report normalization to `50` but remain effectively `100`; explicit `50` also cannot lower the template, and only a value above `100` raises the cap. `OCR_MAX_TOKENS_BUDGET` defaults to `0`, meaning unlimited; a positive budget may stop dispatch and produce an explicitly partial, automatic-approval-ineligible review. `OCR_LLM_MAX_COMPLETION_TOKENS` defaults to unset and separately controls only the provider request's completion/output cap. Select an explicit value only from the deployment's provider/model contract; the toolkit does not recommend or hardcode a provider-specific cap.

OCR 1.11.0 semantically groups related changed files before review and filters candidates per group. Its private grouping and other-files prompts use status-first `STATUS   path (+N/-M)` entries; the toolkit does not parse that inventory in production. Grouping, filtering, and multiple rounds can increase provider requests, latency, and token cost, while the manifest and aggregate budget continue to report completeness. Grouping, grace-round, provider-native reasoning/thinking, and tool-choice request state are retained only inside OCR's isolated private session. Group labels, paths, reasoning, signed/encrypted native payloads, and request controls remain untrusted: the toolkit does not publish or use them for severity, fingerprints, lifecycle commands, receipts, DLP counts, telemetry, tool/token summaries, or approval. OCR's separately configured telemetry may export high-cardinality repository-derived values, so keep `OCR_TELEMETRY_ENABLED=false` unless the exporter and retention policy are approved.

The summary keeps four inputs separate: OCR manifest coverage, publication integrity, published findings, and an optional OCR core advisory. Complete manifest coverage that later loses public fields is labelled `Review complete with publication filtering`; it is warning-bearing and approval-ineligible, but it is not called incomplete OCR coverage and does not invent failed-file diagnostics. Actual partial, failed, waived, or budget-stopped manifest coverage keeps its stronger status. Ordinary OCR warnings retain their own complete-with-warnings state. The reviewer guide ranks bounded focus areas only when at least two findings are published; one finding remains in its inline or fallback discussion without a duplicate snippet. Security focus uses explicit published metadata, strong vulnerability terms, and closed injection classes rather than the standalone word `injection`, so neutral knowledge/dependency terminology cannot increase its count or effort estimate.

The collapsed technical details keep aggregate input/output/cache token usage separate from OCR tool activity. The existing `all OCR tool calls` line lists every non-zero count for the closed review set (`file_read`, `file_read_diff`, `file_find`, `code_search`, `code_comment`, `task_done`, `ocr_toolkit_evidence`, `ocr_toolkit_evidence_search`, `ocr_toolkit_evidence_coverage`, `context_list`, and `context_get`) and is omitted when that admitted list is empty. These counts help explain whether OCR read context, searched the repository, checked cross-file diffs, consulted toolkit evidence, searched unknown evidence identities, checked absence coverage, or emitted review output; they are not per-tool token attribution. Dynamic external MCP tool names remain private and appear only through the existing verified per-server aggregate. A separate action line contains only reconciled non-zero `summary/list/get/search/coverage` counts; arguments, queries, scopes, IDs, and results stay private. Tool and token lines remain independent of `passed`, `private-sanitized`, or `publication-filtered` receipt state. If OCR accepts a background above its recommended character count, a separate `OCR core advisory` line contains only the actual and recommended counts. It does not become a warning or change review completeness or approval eligibility.

## Choose one operating mode

`OCR_REVIEW_CONTEXT_MODE` selects `off`, `metadata`, or `enriched`; the mode recipes pair that selector with the appropriate approval, adapter, and direct-MCP controls.

| Mode | Context admitted to OCR | Network/tool boundary | Approval posture |
| --- | --- | --- | --- |
| [Identity only](../examples/gitlab/modes/identity-only.gitlab-ci.yml) | No MR title, description, labels, source branch, or discussion text | GitLab identity/policy reads before OCR | May approve when every deterministic gate passes |
| [Metadata](../examples/gitlab/modes/metadata.gitlab-ci.yml) | Bounded MR title, description, labels, and source branch | GitLab reads before OCR | May approve when DLP and every other gate pass |
| [Enriched discussions](../examples/gitlab/modes/enriched-discussions.gitlab-ci.yml) | Metadata plus protected-policy generic discussions and verified remediation threads | Stable double-read GitLab snapshot before OCR | Recipe is explicitly comment-only |
| [Enriched adapters](../examples/gitlab/modes/enriched-adapters.gitlab-ci.yml) | Metadata plus protected-policy discussion and adapter records | Fixed authorize-and-resolve protocol before OCR | Recipe is explicitly comment-only |
| [Same-revision CI outcomes](../examples/gitlab/context/policy-ci-outcomes.json) | Protected-policy exact check names and path prefixes | Twice-read exact-head GitLab pipeline/job metadata; no logs or artifacts | Context only; never suppression or approval authority |
| [Direct MCP](../examples/gitlab/modes/direct-mcp.gitlab-ci.yml) | Metadata plus model-selected external tool results | Reviewed remote HTTPS MCP during OCR | Always comment-only |

The [bounded-context recipes](../examples/gitlab/context/) contain protected policies plus local and remote adapter allowlists. Use the [policy decision guide](review-context.md#choosing-a-discussion-policy) to select generic discussions, verified remediation history, exact same-revision CI outcomes, or a policy that also requires adapters. Copy the chosen template to `.opencodereview/review-context-policy.json` and merge it into the protected target branch before selecting `enriched`; a source-branch copy cannot expand authority. Missing or invalid policy stops before OCR. DLP rejection and required-source degradation block approval. Safely admitted metadata, generic discussions, CI outcomes, and adapter records do not themselves block approval, but every admitted remediation thread does. The enriched recipes nevertheless disable approval explicitly so an operator can qualify the exact policy and source behavior before choosing a narrower approval posture.

Direct external MCP is a different and more privileged boundary. GitLab MR execution accepts it only as remote HTTPS. Tool names, descriptions, schemas, model-chosen arguments, and results enter OCR and its private session. Use dedicated least-privilege credentials and service-side tenant/object/field/operation authorization. Do not expose generic search, arbitrary URL or identifier fetch, writes, workflow tools, or broad service credentials.

## Production bot configuration

Use a dedicated bot account that is not the merge-request author. Give its project access token `api` scope and the minimum project role needed for the selected reads, notes, drafts, discussion management, and optional approval. GitLab approval rules, Code Owners, protected branches, and reset/invalidation policy remain authoritative.

Begin with a manual advisory job and `OCR_AUTO_APPROVE=false`. Enable strict posting or approval only after the project has reviewed published results, bot permissions, exact receipt gates, and all source-data boundaries. Keep result, stderr, evidence, generated OCR configuration, context stores, adapter scratch space, and OCR sessions private to the runner and out of public artifacts. The local-only `ocr-ci review --preserve-private-artifacts` diagnostic is rejected by the validated GitLab merge-request profile and must not be added to a CI job.

Before treating the advisory job as a required gate, run `ocr llm test` with the same generated OCR configuration and protected credential path. `ocr-ci preflight` always checks that the required toolkit inputs exist and can optionally validate model metadata through `/models`, but that metadata read is not a full review request and cannot guarantee that a gateway credential, protocol, deployment, spending policy, or requested output cap will accept the later conversation. The toolkit never derives `OCR_LLM_MAX_COMPLETION_TOKENS` from `/models.max_completion_tokens`. Keep `allow_failure` only when a missing review is intentionally advisory; a green pipeline with an allowed-to-fail OCR job is not evidence that OCR produced a usable review.

The toolkit authenticates the token owner with live `GET /user`. No configured bot ID or username is trusted. The returned ID owns note/fingerprint checks; the validated username owns exact mention-command parsing.

## Operating model

`ocr-ci preflight` validates OCR compatibility, GitLab access, and optional model metadata. `ocr-ci configure` writes the isolated OCR configuration. `ocr-ci review` captures the exact source head and protected-target policy SHA, collects immutable repository evidence, acquires selected provider/context data, applies DLP and budgets, runs OCR once under an owner-only isolated home, validates the result, cleans private state, and attaches receipt v6. `ocr-ci post` hostile-reads that receipt rather than reconstructing configuration from a later environment.

`off` still validates the source SHA, protected target, merge-request author, and live bot identity while withholding mutable MR text. `metadata` admits only bounded DLP-checked title, description, labels, and optional source branch. Treat those fields as claims to compare with the diff, never as instructions, policy, or proof.

`enriched` loads the protected policy and may add one stable GitLab discussion snapshot, verified toolkit-owned remediation threads, exact same-revision CI outcomes, and adapter-authorized records. Generic discussion and remediation projections are mutually exclusive for a toolkit-owned root. Remediation roots require both the authenticated live bot ID and a valid toolkit marker/fingerprint. Raw GitLab IDs, usernames, provider objects, and rejected values are not stored or returned. The model sees only opaque local handles; it cannot search GitLab or submit an arbitrary provider ID or URL.

Remediation text is untrusted review history. It may locate a claim that OCR must re-check against current code and tests, but it cannot change severity, prove a fix, suppress or resolve a finding, issue a lifecycle command, or authorize approval. Any admitted remediation record therefore makes the review comment-only. DLP-clean non-remediation context does not independently disable an otherwise eligible receipt; a DLP rejection cannot make approval easier.

A protected CI pass is narrower than a general green-pipeline claim: it applies only to its exact reviewed head, exact protected job name, and declared path prefixes. It may challenge an unconditional claim about code that the job actually exercised, but it cannot suppress a finding, prove unrelated absence, change severity/lifecycle, or authorize approval. Stale, advisory, skipped, canceled, failed, unknown, incomplete, mutated, or ambiguous data cannot be treated as a required pass. The toolkit does not fetch job logs, artifacts, URLs, users, runners, variables, or raw IDs.

Provider configuration is forge-neutral. Configure and preflight share one normalized absolute HTTPS API root, explicit protocol, headers, request-body controls, and optional models URL. A protocol-mismatched terminal endpoint, embedded credential, or fragment fails before OCR. On a classified provider failure, `post` publishes only a static safe reason and guidance; raw provider/model fields, response bodies, request IDs, paths, warnings, and stderr remain private. The review log may contain one toolkit-authored line of closed HTTP detail and non-zero aggregate retry counts from a fully validated retry report, but the GitLab summary does not. A `rate-or-spending-limit` note suggests lowering `OCR_REVIEW_CONCURRENCY` and/or `OCR_LLM_MAX_COMPLETION_TOKENS`, starting a new merge request pipeline, and then checking provider request/account limits without claiming either setting caused the failure. The previous successful review remains visible, no failed-result findings are posted, and approval is not attempted.

When a merge request introduces a repository-owned OCR rules path absent from both trusted baselines, `review` stops before OCR and `post` may publish only the static setup-pending message after hostile identity validation. The source file never becomes policy evidence for its own merge request.

## Reviewer commands and no-commit reruns

Inside a toolkit-owned discussion, a human non-system reply may contain exactly one lifecycle command:

- `/ocr suppress` or `@<live-bot-username> suppress` keeps the discussion open and suppresses the matching finding;
- `/ocr resolve` or `@<live-bot-username> resolve` suppresses the finding and resolves the discussion after the next successful posting transaction.

Commands are case-insensitive and allow surrounding whitespace only. For a bot named `mr.bot`, `@mr.bot resolve` is valid. Prose, code blocks, `supress`, another mention, `retest`, bot replies, system notes, and commands outside a toolkit-owned discussion are ignored. If several recognized human commands exist, the newest wins. See [GitLab review operations](operations.md#reviewer-commands) for the state machine.

The toolkit is CI-only and does not receive a GitLab comment event by itself, so `@bot retest` is not supported. To rerun without a commit, use GitLab's [Retry UI/API](https://docs.gitlab.com/ci/jobs/#retry-jobs). Creating a new merge-request pipeline is also available through the [merge-request pipeline API](https://docs.gitlab.com/api/merge_requests/#create-merge-request-pipeline). A deployment that wants comment-triggered reruns needs a separate authenticated and authorized [Note Hook receiver](https://docs.gitlab.com/user/project/integrations/webhook_events/); that receiver is outside this toolkit's trust and lifecycle boundary.

## Accepted project decisions in a later merge request

Copy [`examples/gitlab/accepted-decisions.md`](../examples/gitlab/accepted-decisions.md) to `.opencodereview/accepted-decisions.md` and merge it through an earlier reviewed change. In a later merge request that touches a matching scope, the protected-target collector marks the decision applicable and the bootstrap lists its decision ID and scope.

OCR can then inspect the actual protected decision through the built-in `ocr_toolkit_evidence` tool:

```json
{"action":"list","kind":"repository.accepted_decision","ref":"policy"}
```

The returned record contains a stable `id`. OCR retrieves that exact record with:

```json
{"action":"get","id":"<id returned by list>"}
```

The rationale is evidence to compare with current code, tests, and applicability, not a suppression or authorization rule. A decision added or changed by the current source branch is excluded. The full format, scope grammar, staleness, and authority limits are in [Accepted project decisions](configuration.md#accepted-project-decisions).

Use merge-request source and base SHAs, not a merge-result commit, for the reviewed range. Keep the self-test job manual. See [Security and trust model](security.md), [Environment configuration](configuration.md), and [Bounded review context](review-context.md) for the exact contracts.
