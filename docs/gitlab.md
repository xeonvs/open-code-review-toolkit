# GitLab integration

The toolkit's first provider adapter posts review results to GitLab merge requests. The example is intended for trusted contributors because merge-request code and repository guidance are untrusted input even when the posting token is protected. Start with a manual job, validate results, and only then consider automatic execution.

## Installation

Install `open-code-review-toolkit` from PyPI. The example obtains the expected toolkit wheel digest from the matching immutable GitHub Release, then uses pip hash-checking and a local install. Install Open Code Review separately and use the exact recommended version and asset checksum from the [compatibility manifest](../compatibility/ocr-support.json); the synthetic CI example carries the corresponding executable pin. The package never downloads OCR.

Copy and adapt [the synthetic CI example](../examples/gitlab/ocr-review.gitlab-ci.yml). Its rules pack explicitly includes Jinja (`.j2`, `.jinja`, `.jinja2`), extensionless conventional Ansible-role templates, and Twig (`.twig`) because the recommended OCR does not select those extensions by default; project `exclude` entries still take precedence. Keep the lint stage before the AI review stage so failed project checks block review. The example downloads a pinned toolkit wheel with bounded retries/timeouts, verifies its SHA-256 before a local `--no-deps` install, generates a private evidence store plus one compact bootstrap, and passes the bootstrap once with `--background-file`.

## Required secrets

- `GITLAB_API_TOKEN`: a dedicated bot token with only the project/API permissions required to read the merge request, create/update its comments, and approve when `OCR_AUTO_APPROVE` is enabled.
- `OCR_LLM_TOKEN`: the LLM gateway credential used by OCR.
- `OCR_SHA256`: the trusted checksum for the pinned OCR binary asset.

Store secrets as masked, protected CI variables. Do not place them in YAML, command arguments, evidence artifacts, or the generated bootstrap. Posting deliberately does not accept a GitLab job token.

`OCR_REVIEW_LANGUAGE` is an optional non-secret OCR configuration setting and defaults to `English`. Set an explicit language name only when localized review output is required; `Russian` is one example.

`OCR_MAX_TOKENS_BUDGET` is an optional non-secret aggregate review ceiling. Its default `0` is unlimited; a positive value can intentionally stop dispatch and yield a partial review with completed findings plus explicit budget-failed coverage. It is a separate operator control, not a named quality profile, and a budget-stopped run cannot automatically approve.

## Production bot configuration

Use a dedicated bot account that is not the merge-request author. Give its project access token `api` scope and the minimum project role needed for the documented reads, notes, drafts, discussion management, and optional approval; GitLab approval rules, Code Owners, protected branches, and reset/invalidation policy remain authoritative. Keep the GitLab, LLM, and optional MCP credentials masked and protected, and restrict the job to trusted pipelines that can access them. Begin with a manual advisory job and `OCR_AUTO_APPROVE=false`; enable strict posting or approval only after the project has reviewed the published results, bot role, approval rules, and source-branch threat boundary.

Keep result, stderr, evidence, OCR configuration, context stores, adapter scratch space, and OCR session files private to the runner and out of public artifacts. `metadata` sends bounded author-controlled title, description, labels, and optional source branch into OCR; it remains untrusted model input. `enriched` can additionally send protected-policy projections of discussions and external records, but provider identifiers and schemas remain outside the model. Direct external MCP descriptions, schemas, arguments, and results enter the model/session and are a separate privileged boundary. Use dedicated least-privilege credentials, server-side tenant/object/field/operation authorization, bounded responses, and service-side audit controls. Do not expose generic search, arbitrary identifier/URL fetch, writes, approval/comment/workflow tools, or broad credentials. Server-authored names, schemas, descriptions, and annotations do not prove that a direct tool is read-only.

Choose one explicit operating recipe:

1. **Context-free automatic approval:** admit no mutable MR text and configure no external MCP.

   ```yaml
   OCR_REVIEW_CONTEXT_MODE: "off"
   OCR_AUTO_APPROVE: "true"
   OCR_MCP_SERVERS_JSON: "{}"
   ```

2. **Bounded metadata-aware automatic approval:** admit the existing bounded MR fields. Approval remains possible only when metadata is complete and every other deterministic gate passes.

   ```yaml
   OCR_REVIEW_CONTEXT_MODE: "metadata"
   OCR_AUTO_APPROVE: "true"
   OCR_MCP_SERVERS_JSON: "{}"
   ```

3. **Metadata-aware comment-only operation:** use bounded MR intent without granting approval authority.

   ```yaml
   OCR_REVIEW_CONTEXT_MODE: "metadata"
   OCR_AUTO_APPROVE: "false"
   OCR_MCP_SERVERS_JSON: "{}"
   ```

4. **Protected enriched context:** install the protected-target policy and configure only the operator adapters it selects. Admitted mutable records make this run comment-only even if `OCR_AUTO_APPROVE` remains true; setting it false makes the intended deployment boundary explicit.

   ```yaml
   OCR_REVIEW_CONTEXT_MODE: "enriched"
   OCR_AUTO_APPROVE: "false"
   OCR_REVIEW_CONTEXT_ADAPTERS_JSON: >-
     [{"name":"tracker","type":"remote","tenants":["engineering"],"resource_classes":["issue"],"url":"https://context-proxy.example.invalid/v1/authorize-and-resolve","headers_from":{"Authorization":"SYNTHETIC_ADAPTER_AUTHORIZATION"}}]
   ```

   Copy and review the synthetic [protected policy and adapter recipes](../examples/context/). Missing/invalid policy or required-source degradation stops or blocks the run as documented; optional degradation remains visible. A complete zero-record enriched run is not ineligible solely because the mode was selected.

5. **Discussion-only protected enrichment:** select `forge_discussions` in the protected policy and leave the operator adapter array empty.

   ```yaml
   OCR_REVIEW_CONTEXT_MODE: "enriched"
   OCR_AUTO_APPROVE: "false"
   OCR_REVIEW_CONTEXT_ADAPTERS_JSON: "[]"
   ```

6. **Operator-reviewed direct external MCP:** GitLab MR execution accepts direct external MCP only as remote HTTPS. Keep the bot explicitly comment-only and store `SYNTHETIC_MCP_AUTH_HEADER` as a masked/protected variable carrying a dedicated service credential. This does not use the M5 broker or opaque handles.

   ```yaml
   OCR_REVIEW_CONTEXT_MODE: "metadata"
   OCR_AUTO_APPROVE: "false"
   OCR_MCP_SERVERS_JSON: >-
     {"bounded_reference":{"type":"remote","url":"https://mcp.synthetic.invalid/v1","headers_from":{"Authorization":"SYNTHETIC_MCP_AUTH_HEADER"},"tools":["read_admitted_record"]}}
   ```

The [bounded review-context guide](review-context.md) owns policy, adapter protocol, handle, completeness, DLP, retention, and cleanup contracts. The [configuration reference](configuration.md) owns environment inputs, direct MCP, receipt fields, and bounds. The [operations guide](operations.md) owns posting transactions, failure behavior, and approval outcomes.

### Migration from 0.6.2

Toolkit 0.6.3 changes an unset context selector to identity-only `off`. Set `OCR_REVIEW_CONTEXT_MODE=metadata` explicitly to retain the bounded MR title/description/labels/source-branch context previously collected by the ordinary GitLab path. Do not set `enriched`; it is reserved and rejected rather than treated as a compatibility alias.

Receipt v1/v2 results remain comment-readable but cannot authorize approval; rerun the review under 0.6.3 to create receipt v3 before expecting an approval. Existing approvals are never removed. A changed MR author or a bot-authored MR now skips approval without writing. Any configured external MCP blocks approval in 0.6.3, so set `OCR_AUTO_APPROVE=false` to make that comment-only intent explicit. GitLab MR external stdio configuration is now rejected; migrate it to a reviewed remote HTTPS service with environment-backed credentials, while explicit developer-local stdio remains available outside the validated GitLab-MR path.

Ambiguous position-bearing inline creates can now recover only from exactly one complete author-bound marker match. This requires no operator setting and never introduces retry-on-absence or fallback after unresolved ambiguity. Existing finding markers, suppression decisions, human ownership, and previous-review retention remain compatible.

### Migration from 0.6.3 to 0.7.0

`off` and `metadata` retain their v0.6.3 acquisition semantics. Existing pipelines need no context configuration change unless they intentionally adopt enrichment. Receipt v1-v3 remains comment-readable, but a new run must produce receipt v4 before current automatic-approval guarantees apply.

To adopt `enriched`, first merge `.opencodereview/review-context-policy.json` into the protected target branch, then configure the operator-side `OCR_REVIEW_CONTEXT_ADAPTERS_JSON` allowlist and credentials. Never test policy expansion from the merge-request branch: that file is ignored for authority. Start comment-only, verify per-source completeness and adapter authorization, and only consider automatic approval for policies that can complete with no admitted mutable record.

The review now runs OCR under an isolated owner-only home and removes its session/configuration plus context artifacts on every outcome. If a project previously relied on OCR session files surviving the job, keep that workflow outside `ocr-ci review`; v0.7.0 deliberately has no secure-debug retention switch. Direct `OCR_MCP_SERVERS_JSON` remains a separate privileged/comment-only feature and is not migrated automatically to the broker.

## Operating model

`ocr-ci preflight` validates the installed OCR version, GitLab access, and configured LLM model. `configure` resolves `OCR_REVIEW_LANGUAGE`. `ocr-ci review` verifies the exact reviewed source SHA, captures the current protected target SHA, and keeps those policy and forge diff identities separate. Repository-owned OCR rules plus accepted decisions and project guidance come from that immutable policy commit; OCR still reviews the original diff-base-to-source-head range. Explicit absolute rule paths outside the repository remain operator-owned.

`OCR_REVIEW_CONTEXT_MODE` controls whether mutable merge-request data enters review context. Empty or `off` is the default and performs identity-only acquisition: source SHA, protected target identity, and merge-request author ID are still validated, while title, description, labels, and source branch do not enter normalization or storage. `metadata` admits only those bounded author-controlled fields. Treat admitted intent as a claim to compare with the diff, never an instruction or authority; source-branch text alone is a weaker hint and cannot establish rollout intent. Complete metadata remains eligible for deterministic approval policy, while any degraded field state blocks approval.

`enriched` first requires the exact protected-target policy. GitLab discussions are read twice as one bounded ordered snapshot; mutation and omissions stay visible. References are recognized only in admitted metadata and discussion bodies, then authorized by an operator proxy before an opaque local handle is minted. The model can list/get committed handles through the existing toolkit MCP but cannot search the provider or submit an arbitrary identifier/URL. Required degradation and admitted mutable context block approval; optional degradation cannot prove absence.

`ocr-ci review` owns evidence collection, private artifacts, compact bootstrap, context acquisition, isolated OCR execution, publication validation, cleanup, and the complete MCP registry. In a validated GitLab MR path, direct external MCP entries must be remote HTTPS; local developer execution may retain explicit stdio processes. Existing OCR configuration is revalidated so it cannot bypass that profile. The fixed toolkit-owned stdio process exposes mandatory evidence and, only in enriched mode, the two fixed context tools. After OCR succeeds, `review` validates mandatory evidence use, publication DLP, and cleanup, then atomically binds receipt v4 to the private result. `post` hostile-reads that receipt instead of reconstructing configuration. Every configured direct external MCP remains comment-only; brokered adapters are governed separately by per-record mutability and degradation.

When a merge request introduces one normalized repository-owned OCR rules path that is absent from both the diff base and captured protected-target policy commit but exists as a bounded regular blob at the exact source head, `review` stops before OCR. `post` may render only the static toolkit-authored setup-pending message. It never reads or trusts the source rule content as policy, never appends stderr to that recognized outcome, and falls back to the generic failure for malformed, stale, unsafe, or identity-mismatched private status.

`ocr-ci post` also manages conservative automatic approval by default. After all
current notes publish, it waits for GitLab diff and approval synchronization,
verifies the current MR head and author against the receipt-bound identities, skips self-approval when the toolkit user authored the MR, submits that exact SHA only when all gates pass, and confirms the authenticated toolkit user's approval plus the unchanged SHA and non-bot author through bounded post-write readback. Set `OCR_AUTO_APPROVE=false` for a comment-only bot or before upgrading
an integration whose approval rules have not granted the bot permission. This
transaction is add-only: an ineligible or disabled later run never removes an
existing approval. Configure GitLab's own reset or invalidation policy if
approvals must be withdrawn after the source branch changes.

Repeated reviews have a reviewer-controlled lifecycle rather than appending the same notes indefinitely. Untouched OCR-only notes are replaced after a successful run, human-touched discussions are preserved, and `/ocr suppress` or `/ocr resolve` controls future matching findings. Read [GitLab review operations](operations.md) for the complete state machine, deduplication boundaries, posting modes, permissions, limits, and failure semantics.

For a deliberate project-wide tradeoff that should be supplied to every review, add a narrowly scoped entry to `.opencodereview/accepted-decisions.md` in an earlier reviewed merge request. The [configuration reference](configuration.md#accepted-project-decisions) documents its `ocr-accept` marker convention, prompt-level semantics, and self-whitelisting guard.

OCR is configured through its `openai-responses` provider. Run the review through `ocr-ci review` so failed OCR stderr is retained privately and a bounded redacted diagnostic appears in the runner log. This command never posts; `ocr-ci post` remains the explicit GitLab write boundary. MCP tools are supplied with `OCR_MCP_SERVERS_JSON`; GitLab MR external entries are remote HTTPS only, while explicit stdio commands are limited to the developer-local execution profile.

Use merge-request source and base SHAs, not a merge-result commit, when choosing the reviewed range. Keep the self-test job manual. See [docs/security.md](security.md) for trust boundaries and [docs/configuration.md](configuration.md) for every input.
