# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and before handoff or commit. Completed stable plans are indexed in [the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Plan: toolkit 0.6.3 context approval and GitLab write reconciliation

- **Status:** ready for feature publication; implementation, owner-capped local OCR, MCP profiling, logical history consolidation, deterministic/package/security/privacy review, and final self-review are complete; hosted PR/CI, merge, development publication, and stable release closure remain.
- **Release classification:** `release-required`.
- **Target stable version:** `0.6.3`; `.next-version` already selects this development line.
- **Tracked release work:** [#100](https://github.com/xeonvs/open-code-review-toolkit/issues/100) and [#101](https://github.com/xeonvs/open-code-review-toolkit/issues/101), plus intervening OCR 1.9.6 qualification [#105](https://github.com/xeonvs/open-code-review-toolkit/issues/105), assigned to GitHub milestone `v0.6.3`.
- **Deferred existing-M5 work:** BL-023 retains the complete enriched context broker. The separate same-session external-MCP proposal [#103](https://github.com/xeonvs/open-code-review-toolkit/issues/103) is closed as not planned: it repeated the removed direct-provider direction rather than the brokered M5 architecture. It is not a `0.6.3` or future delivery claim.
- **Baseline:** clean synchronized `main` at `5d63d67`; latest stable toolkit `0.6.2`; recommended and PATH-effective checksum-qualified OCR `1.9.5` at activation; no open PR existed at activation.
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

The release explicitly does not claim enforceable external-MCP read-only semantics. OCR 1.9.5/1.9.6 has no same-session hook that can reject a discovered tool from its current annotations before registration/model projection, and a reconnecting probe has a capability-swap race. More importantly, annotation-gated direct provider composition is not the target M5 architecture: BL-023 keeps external records behind toolkit-owned broker authorization and fixed tools. Direct external MCP remains privileged operator configuration and comment-only in 0.6.3; no separate future implementation is promised.

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
7. Only after external readback, verify Actions-owned closure of #100/#101, close milestone `v0.6.3`, confirm #103 remains closed as not planned, retain discussion #911 as the sole Alibaba-side object, retain unfinished BL-023, and reconcile clean local `main`.

#### Current checkpoint and exact resume action

Planning sources, GitHub milestone `v0.6.3`, #100/#101/#105 assignment, signed planning commit `b99c4c4`, and draft PR #104 are live and read back. The prematurely activated #103/BL-024 direction remains closed as not planned against the established M3/M5 architecture; discussion #911 remains the only intended Alibaba repository thread and no Alibaba mutation belongs to this delivery. Slices 1-5 and repeated invariant audits implement and document the closed context/receipt/approval/MCP topology plus one-shot ambiguous inline-create reconciliation and explicit transaction rollback. The complete Python 3.12-3.14, quality, dependency, Gitleaks, privacy/license, deterministic-build/Twine, archive, and clean wheel/sdist install gates passed before OCR remediation. Intervening OCR 1.9.6 is hosted-qualified and integrated through #105.

The first OCR pass selected all 20 runtime/compatibility files and produced six findings but was correctly rejected because OCR recorded zero mandatory evidence calls. Four independently validated findings were fixed in signed commit `3947ce7`; two rollback suggestions were rejected because they weakened the explicit no-marker-rescan/baseline ownership boundary. A second exact-range pass proved 66 evidence calls but was partial on `review_runner.py`; its three validated findings were fixed in signed commit `b6ff1cd`, while regular-note reconciliation and approval compensation remained rejected against the explicit #101/add-only boundaries. The next OCR 1.9.6 pass (`5d63d67..b6ff1cd`, session `8f5b3775-d5a6-45a0-af8e-f7d0af61a91e`) completed all 20 selected files with 22 mandatory evidence calls. Its two validated trust-boundary findings were fixed in signed commit `a5ca41f`: write identity is parsed only from the toolkit-owned preamble so quoted marker-like finding text cannot poison reconciliation, and inherited environment-resolved MCP credentials remain in the composition redaction inventory. The remaining regular-note/snapshot pair is the same explicitly excluded non-position-bearing create scope from #101, and the `mcp-config` finding is inapplicable because the current GitLab example no longer calls that retired standalone step and the review owner already selects the internal validated `gitlab_mr` profile.

The following exact-range pass (`5d63d67..a5ca41f`, session `03858948-87c9-4479-8109-aa4f53f31b35`) proved 23 mandatory evidence calls and completed 19 of 20 files; `workflow.py` exhausted its model tool-round budget, so the partial manifest did not close the gate. Independent audit accepted its composer defense-in-depth check and three marker-parser cleanup findings. The repeated regular-note finding remained outside #101, and the forged-receipt claim was rejected: receipt v3 is toolkit-authored only after OCR under a private same-owner artifact replacement, provider output containing `_ocr_toolkit` is rejected, posting binds the receipt source/author to live GitLab state, and an actor able to rewrite same-owner CI artifacts can already invoke the exposed job credential directly. Those accepted cleanups were folded into signed commit `101e9c7`.

The exact-range OCR 1.9.6 pass over `5d63d67..101e9c7` (session `0c329aec-6aed-46fc-9d6a-6d6ba137c2cb`) completed all 20 selected files with 21 mandatory evidence calls. Independent audit confirms two narrow consistency fixes: explicit same-name MCP input must replace stale inherited state before profile revalidation, and receipt source/author extraction for the published summary must be atomic. The repeated regular-note/snapshot findings remain the same expressly excluded non-position-bearing #101 scope, and the request to make complete bounded metadata ineligible directly contradicts #100's release outcome. The two confirmed fixes and regressions are implemented and will be folded into the signed remediation commit. The owner-capped final local OCR 1.9.6 run is session `0f1de407-a937-4ecb-b469-5dcdc9030ab6` over exact range `5d63d67b1abef8b0aac951d235d4aead82429b94..657bce78a50bf3c18a81e569837c27b5dcdcc4a5` (private result SHA-256 `b07bca956aee0c286f03eda3a7ce902465e8e70f0fae4ad2fdc5297887cc1b32`). It selected 20 files, completed 19, recorded 21 mandatory `ocr_toolkit_evidence` calls, returned zero final findings, and classified only `review_runner.py` as budget-failed after exhausting model tool rounds. The owner explicitly capped local OCR at this run, including after any later fix; no further local OCR is permitted. Manual compensation traced every intermediate `review_runner.py` hypothesis through the result producer, manifest parser, receipt writer, GitLab snapshot/profile selection, approval readback, and focused tests. Skipped results retain the pinned zero-call envelope, GitLab MR acquisition always validates a positive author before selecting the remote-only profile, local receipts are intentionally comment-only, pre-tool failed manifests do not invent evidence use, and unknown tools cannot enter the toolkit-owned capability receipt. No runtime fix was confirmed from those hypotheses.

The MCP profile found 21 identical `summary` requests: one per selected-file worker and a second request from the budget-exhausted `review_runner.py` worker. Each response was 1,044 bytes with zero-millisecond recorded server duration; OCR 1.9.6 materialized the known inactive union-schema fields, which the action owner intentionally ignores and regression tests cover. No `list` or `get` request was needed for this diff. Roughly 22 KiB of repeated summary output is not a toolkit performance bottleneck beside the run's 3,067,930 model tokens; changing the qualified union schema would add compatibility risk without meaningful measured gain.

After that run, the focused trust-boundary suite passed with 369 tests and 158 subtests. The owner then limited the final local runtime matrix to Python 3.12: its complete suite passed with 863 tests and 174 subtests. The intentionally started Python 3.13 and duplicate Python 3.14 pytest runs were interrupted and are not evidence; Ruff formatting/check, strict mypy, medium-or-higher Bandit, lock validation, OCR compatibility validation, and `pip-audit --skip-editable` passed independently. Earlier complete Python 3.12-3.14 evidence remains historical pre-remediation evidence. On the consolidated six-commit history, all commit signatures and exact implementation-tree equivalence were verified; pinned Gitleaks, public privacy/license and archive-content scans, reproducible wheel/sdist, Twine, clean Python 3.12 wheel/sdist installs, CLI smoke, Bandit, dependency audit, architecture/ownership review, and the complete security diff inventory passed with no reportable finding. The final self-review maps #100, #101, and #105 requirements to production owners and hostile boundary tests, confirms regular non-position-bearing note reconciliation remains outside #101, and confirms no Alibaba mutation or second M5 path. The branch is ready for its one completed feature push; hosted PR/CI and exact-head review remain before merge.
