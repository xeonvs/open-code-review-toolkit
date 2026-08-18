# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and before handoff or commit. Completed stable plans are indexed in [the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Plan: toolkit 0.6.3 context approval and GitLab write reconciliation

- **Status:** active; implementation slices 1-5 and two complete-review invariant passes are complete locally; the second signed review-fix commit, one final complete-range review, and release gates are next.
- **Release classification:** `release-required`.
- **Target stable version:** `0.6.3`; `.next-version` already selects this development line.
- **Tracked release work:** [#100](https://github.com/xeonvs/open-code-review-toolkit/issues/100) and [#101](https://github.com/xeonvs/open-code-review-toolkit/issues/101), assigned to GitHub milestone `v0.6.3`.
- **Deferred existing-M5 work:** BL-023 retains the complete enriched context broker. The separate same-session external-MCP proposal [#103](https://github.com/xeonvs/open-code-review-toolkit/issues/103) is closed as not planned: it repeated the removed direct-provider direction rather than the brokered M5 architecture. It is not a `0.6.3` or future delivery claim.
- **Baseline:** clean synchronized `main` at `5d63d67`; latest stable toolkit `0.6.2`; recommended and PATH-effective checksum-qualified OCR `1.9.5`; no open PR existed at activation.
- **Branch:** `feature/0.6.3-context-approval-write-reconciliation`.

#### Outcome and release boundary

Deliver two independently reviewable user-visible changes in one stable release:

1. #100 separates bounded merge-request context selection from deterministic approval eligibility, introduces a closed review-time receipt, prevents self-approval, and hardens external-MCP topology without claiming that current OCR can enforce semantic read-only behavior.
2. #101 recovers exactly identifiable maybe-landed inline GitLab creates without retrying an absent or ambiguous write and without broadening rollback ownership.

The following #100 subset ships in `0.6.3`:

- `OCR_REVIEW_CONTEXT_MODE=off|metadata|enriched`, with missing/empty equal to `off`;
- receipt v3 carrying bounded identities, context state, MCP capability inventory and positive usage only;
- metadata-aware automatic approval when all deterministic review/provider gates pass;
- review-time and post-time MR-author identity validation plus explicit bot-is-author skip;
- GitLab-MR external MCP restricted to remote HTTPS through an internal execution profile, with strict transport schemas and complete inherited-config validation;
- every configured external MCP makes the `0.6.3` review comment-only and blocks automatic approval, independent of usage.

The release explicitly does not claim enforceable external-MCP read-only semantics. OCR 1.9.5 has no same-session hook that can reject a discovered tool from its current annotations before registration/model projection, and a reconnecting probe has a capability-swap race. More importantly, annotation-gated direct provider composition is not the target M5 architecture: BL-023 keeps external records behind toolkit-owned broker authorization and fixed tools. Direct external MCP remains privileged operator configuration and comment-only in 0.6.3; no separate future implementation is promised.

#### Public contracts and failure policy

##### Review context and provider snapshot

- Parse `OCR_REVIEW_CONTEXT_MODE` before provider acquisition or OCR execution. Unknown values and `enriched` fail closed before OCR and diagnostics never echo the raw value.
- `off` still acquires and validates the GitLab MR source SHA, protected target branch/SHA, and MR author ID required by policy and approval. Title, description, labels, and source branch must not enter normalization, persistence, MCP, OCR bootstrap, receipt, or diagnostics.
- `metadata` requires a validated GitLab merge-request environment. It projects the existing bounded `review.merge-request-context/v1` fields.
- Context completeness is closed and review-time owned. Every text field must be `absent` or `admitted`, and labels must be `absent` or `admitted`, for metadata state `complete`. Invalid, over-limit, redaction-limit, partial, or collision states produce `degraded`; they remain visible through bounded field statuses and block approval without leaking omitted content.
- Metadata remains untrusted data and cannot affect policy SHA, configuration, tools, suppression, commands, posting authority, finding thresholds, or credentials.
- The provider snapshot validates a positive bounded MR author ID together with source and protected-target identities. Posting re-reads the MR and requires source SHA and author ID to match the receipt before any approval write.

##### Receipt v3 and approval

- `_ocr_toolkit.schema_version=3` is an exact closed schema. It records source SHA, policy SHA, MR author ID where applicable; context mode/state/classes; complete configured MCP capability inventory with `builtin|stdio|remote` transport; positive known-tool usage counts; and mandatory evidence-use status.
- Receipt v3 never contains context text, provider URLs/bodies, MCP URL/command/setup/env/header values, descriptions, schemas, credentials, tool arguments/results, or repository content.
- Receipt v1/v2 remains readable for comment publication and bounded MCP summaries, but cannot authorize approval. Posting does not reconstruct or upgrade review-time context/MCP facts from its environment.
- `OCR_AUTO_APPROVE=false` remains a posting-time one-way kill switch. A valid default-on setting may approve only with receipt v3, authoritative clean coverage, no failed/waived/budget/warning/omitted outcome, acceptable finding policy, mandatory evidence proven, no external MCP configured, exact current source/author match, and provider confirmation.
- Built-in `ocr_toolkit_evidence` and complete metadata do not independently block approval. Degraded metadata and any configured external MCP do.
- If the authenticated bot ID equals the validated MR author ID, return a distinct bounded `skipped` result and perform no approval write. Preserve already-approved, stale-head, provider rejection, ambiguous write, confirmation failure, and approved states as distinct diagnostics.

##### External MCP execution profiles

- Do not add or consume a public `GITLAB_CI` policy variable. The validated provider path passes an internal `gitlab_mr` profile to MCP parsing/composition; non-MR/local execution uses `local`.
- `gitlab_mr` accepts operator-configured external MCP only as `type=remote` with absolute HTTPS `url`, optional bounded non-secret `headers`, environment-backed `headers_from`, and a non-empty explicit `tools` allowlist. It rejects `command`, `args`, `env`, `env_from`, and `setup`.
- `local` preserves developer-managed stdio command pass-through and existing stdio `setup` compatibility; the toolkit does not install, update, infer, or own the external process lifecycle. Remote entries reject `setup` in every profile.
- Merge mode revalidates every inherited OCR MCP entry against the active profile and exact schema before composition. Pre-existing external stdio or unknown fields cannot bypass GitLab-MR policy. The mandatory built-in entry is replaced by the toolkit-owned fixed stdio definition after validation and is the sole GitLab-MR stdio exception.
- Preserve explicit allowlists, reserved-name and cross-server collision rejection, bounded secret redaction, and independent built-in evidence requirements. Names, methods, descriptions, schemas, and annotations are not treated as proof of no side effects.

##### Ambiguous inline create reconciliation

- Refine create-specific results to `posted`, `invalid_position`, `definite_failure`, and `ambiguous_create`; unrelated write callers keep conservative non-create behavior and are not silently reclassified.
- Scope reconciliation only to position-bearing `POST /draft_notes` and `POST /discussions`. Regular drafts, fallback/summary/error notes, updates, deletes, resolve, draft publication, and approval receive no new retry or reconciliation behavior.
- A valid endpoint-specific 2xx identity is `posted`. A proven position validation rejection is `invalid_position`. A bounded provider response that proves no create is `definite_failure`. Timeout, transport failure after dispatch, HTTP 408/5xx, unexpected write redirect, oversized/invalid JSON success, or unusable 2xx identity is `ambiguous_create`.
- Mint `secrets.token_hex(16)` once before each inline create and serialize exactly `<!-- open-code-review-write id=<32 lowercase hex> -->`. It is independent of finding fingerprints, suppression, reviewer commands, authorization, and cross-run identity.
- Reserve ownership/fingerprint and write markers before character/UTF-8 truncation. Closed parsing rejects malformed, duplicate, or conflicting write markers.
- After one ambiguous draft create, perform one complete bounded `/draft_notes` pagination read. Recover only exactly one note whose exact write marker and expected `author_id` match and whose draft ID is a positive integer.
- After one ambiguous direct create, perform one complete bounded `/discussions` pagination read. Recover only exactly one note whose exact write marker, toolkit ownership marker, expected `author.id`, positive note ID, and bounded discussion ID match.
- Zero or multiple matches, malformed potential matches, foreign authors, unavailable/over-budget/incomplete pagination, or conflicting identities fail with no retry and no fallback. Only `invalid_position` may use the existing fallback note path.
- Track normal and recovered inline identities in explicit current-run transaction state. Draft publication consumes current-run draft IDs exactly once. Rollback deletes only explicit current-run draft/discussion identities while retaining the complete pre-run snapshot as a guard; it never derives ownership from marker-only global rescans or touches pre-run/human-owned state.

#### Implementation slices and commit gates

The first signed commit contains only this active plan and current planning-source reconciliation. It is the only early feature-branch push and opens a draft PR. No implementation commit is pushed until all local work and final review gates pass.

Subsequent signed local commits are:

1. **Context/provider/receipt:** closed mode parser; identity-only versus metadata provider projection; context completeness; author capture; receipt v3 serialization and hostile readback.
2. **Approval and MCP topology:** receipt-v3 approval policy; post-time author/source match and self-approval skip; internal MCP profiles; exact remote schema; inherited-config validation; external-MCP comment-only gate.
3. **Create outcomes and markers:** create-specific classification, endpoint identity validation, unguessable write marker, marker-aware body budgets.
4. **Reconciliation and transaction rollback:** one-shot complete readback for draft/direct, exact author-bound match, explicit current-run state, publish/rollback integration.
5. **Public contracts and evidence:** configuration/GitLab/operations/security guidance, synthetic examples, migration notes, evidence matrix, Towncrier fragments, and status reconciliation.
6. **OCR compatibility only if needed before feature merge:** qualify a stable OCR released before the final local OCR or immediately before feature merge; map every upstream change and repeat affected validation. Per owner instruction, do not perform new OCR-release checks after feature merge.

Before every commit:

- run the narrow tests owned by the changed boundary and make hostile cases enter through its production owner;
- inspect the staged diff and resulting `git show` for requirement coverage, architecture, security, privacy, and public-contract consistency;
- run `git diff --check` and the applicable boundary checklist from `docs/development.md`;
- update this plan and directly affected status sources to post-commit truth;
- fix findings before beginning the next slice rather than accumulating a cleanup commit.

#### Validation and evidence matrix

- **Context/parser:** empty/off/metadata/enriched/unknown; no raw invalid value; metadata outside MR; complete/absent fields; every degraded status; prove `off` metadata never reaches normalizer/store/bootstrap/MCP/result/logs.
- **Provider/receipt:** real local TLS peer and real Git object acquisition; source/protected-target/author validation; hostile v3 shape and impossible combinations; changed posting environment; v1/v2 comment-only compatibility; privacy assertions over all serialized channels.
- **Approval:** clean metadata approval; disabled; degraded context; external server configured but unused; missing evidence; warnings/findings/omissions/budget; stale source/author; bot-is-author with zero writes; provider rejection; ambiguous write; already approved; confirmed approval.
- **MCP:** production parser/composer with synthetic remote HTTPS and local stdio peers; GitLab-MR remote-only policy; strict transport fields; inherited-config bypass attempts; missing credentials; collision/reserved names; built-in independence. Record annotations/read-only semantics as an explicit non-claim.
- **Create transport:** real local HTTP peer exercises serialized request markers and all status/body/redirect/timeout/size/JSON branches through the production transport; mocks only prove orchestration beyond that owner.
- **Reconciliation:** zero/one/multiple/foreign/malformed matches, duplicate/conflicting marker, pagination sentinel, unavailable/over-budget reads, recovered IDs, exact once-only publish, rollback after later failure, baseline/human preservation for draft and direct modes.
- **Complete branch:** Python 3.12-3.14 quality matrix; security/dependency checks; pinned Gitleaks over complete feature history; public privacy/license scan; reproducible wheel/sdist; clean installed-artifact CLI and production-path smoke; requirement-to-evidence anti-mock audit; `git diff --check`.
- **Review:** review every commit and `origin/main..HEAD`; run architecture/security/privacy review; check current stable OCR before final local OCR; run one local OCR review over the exact complete range; independently validate findings and fix valid ones; repeat affected deterministic validation and OCR when a material runtime/trust-boundary fix changes the reviewed range; finish with a complete self-review.

#### Publication and closure

1. Push this planning-only commit and open a draft feature PR with a requirement/control checklist.
2. Complete all implementation commits locally without another push.
3. After full deterministic review and local OCR, push the complete feature branch once; wait for required CI, resolve review threads, check current stable OCR immediately before feature merge, then squash-merge the exact reviewed head.
4. Do not perform further OCR-release checks after feature merge. Verify the resulting TestPyPI development wheel/sdist, hashes, provenance/attestations, and clean installs.
5. Prepare `release/v0.6.3` from synchronized `main`. The exact `Release v0.6.3` PR owns stable markers, `.next-version=0.6.4`, source epoch, generated changelog/release notes, synthetic release pins, final planning/history reconciliation, and restoration of this file to its template.
6. Merge the release PR only after all protected checks and exact-head review pass. Independently read back stable TestPyPI/PyPI bytes and hashes, provenance/attestations, Python 3.12-3.14 installs, annotated tag, immutable GitHub Release, and `release-receipt.json`.
7. Only after external readback, verify Actions-owned closure of #100/#101, close milestone `v0.6.3`, confirm #103 remains closed as not planned and the mistakenly opened Alibaba issue has been withdrawn/deletion-requested, retain unfinished BL-023, and reconcile clean local `main`.

#### Current checkpoint and exact resume action

Planning sources, GitHub milestone `v0.6.3`, #100/#101 assignment, signed planning commit `b99c4c4`, and draft PR #104 are live and read back. The prematurely activated #103/BL-024 direction is closed as not planned against the established M3/M5 architecture. The mistakenly opened Alibaba issue is withdrawn with deletion requested; GitHub confirms that only an Alibaba maintainer can physically delete it, and discussion #911 remains the toolkit's only intended Alibaba repository thread. Slices 1-4 implement the closed context/receipt contract, metadata-aware eligibility, self-approval and author-race prevention, GitLab-MR remote-only MCP profiles, strict inherited-config validation, closed create outcomes, endpoint-specific identities, independent write markers, complete one-shot author-bound draft/direct reconciliation, exactly-once draft publication, and baseline-guarded explicit rollback. Slice 5 now documents the public configuration, production-bot recipes and 0.6.2 migration, operations/security contracts, synthetic example, evidence matrix, Towncrier entries, and corrected M5 disposition. The first complete review found and locally fixed three invariant classes: persisted toolkit MCP forms now survive exact profile revalidation without admitting public literal secret-reference syntax; receipt v3 now binds the exact built-in topology, unique bounded tools, bounded known usage, author identity, and evidence/outcome agreement; and non-create writes cannot acquire create-only invalid-position outcomes. The first focused review-fix suite passed with 267 tests and 132 subtests and was committed as `2e27dba`. A repeated complete-range review then found and fixed the sibling exact-identity/baseline class in signed commit `be5fa80`: posting author IDs no longer accept coercive strings/floats/non-positive values, reconciliation baselines contain every valid pre-run endpoint identity rather than only bot-owned entries, receipt use is bounded by OCR's aggregate call count, duplicate inherited header-source forms fail closed, and receipt identities are exact. A final sibling audit additionally centralized the bounded discussion-ID grammar and rejects bool/non-positive note, summary, transaction, and approval-user identities. The subsequent complete state-machine review found one post-write author race: approval confirmation re-read the author but did not compare it with the receipt. The final review-fix unit fails closed when post-write SHA/author/self-authorship no longer matches while preserving GitLab's existing approval state. The remaining work is a repeated exact complete-range review followed by all deterministic, package, privacy, Gitleaks, current-OCR, local-OCR, and final self-review gates preceding the second and final feature push.
