# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and before handoff or commit. Completed stable plans are indexed in [the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### M5 bounded review-context enrichment and stable v0.7.0 delivery

- **Status:** active; planning checkpoint.
- **Release classification:** `release-required`.
- **Target stable version:** `0.7.0`; feature delivery moves `.next-version` to `0.7.0`, and the release PR advances it to `0.7.1`.
- **Tracked GitHub issues:** #107, #108, #109, #110, and #111. Do not create another implementation issue or GitHub milestone.
- **Branch and publication cadence:** `codex/m5-bounded-context-v0.7.0`; push this signed planning commit to one draft feature PR, then keep all implementation commits local until the complete branch passes holistic review and local acceptance gates. A later protected `release/v0.7.0` PR is the distinct release-lifecycle PR required by `docs/release.md`.
- **Outcome:** complete BL-023/M5 through one stable product delivery without a second model review engine. Preserve the v0.6.3 `off`/`metadata` foundation while activating protected-target `enriched` context, GitLab discussions, brokered external records, fixed context tools, OCR-session containment, independent publication validation, visible degradation, and receipt-bound approval policy.

#### Fixed product and trust decisions

- `.opencodereview/review-context-policy.json` is exact-schema protected-target policy. Only the captured protected-target SHA may provide it; source content cannot expand context access.
- `OCR_REVIEW_CONTEXT_MODE=enriched` requires a validated GitLab merge request and valid protected policy. It includes the existing bounded MR metadata plus policy-selected forge discussions and external records. `off` and `metadata` retain their published v0.6.3 behavior.
- Context policy separates retrieval, model egress, publication, and retention projections. Text, upstream identifiers, personal display data, URLs, and raw provider payloads never enter the retention receipt.
- Deterministic toolkit recognizers produce candidates only. Operator adapter allowlists, protected policy, adapter-owned exact object authorization, version binding, normalization, DLP, atomic storage, and expiry must all pass before a handle is exposed.
- `OCR_REVIEW_CONTEXT_ADAPTERS_JSON` supports operator-managed absolute-command stdio and redirect-free HTTPS transports through one fixed `authorize_and_resolve` protocol. No external schema, search, arbitrary model-selected ID/URL, setup command, write, or adapter network path exists inside the OCR model loop.
- Context records use an independent private atomic store and opaque run-bound `ctx1_` handles. Context budgets cannot consume or evict repository evidence budgets.
- The existing built-in MCP process conditionally adds fixed closed-schema `context_list` and `context_get` tools in enriched mode. `ocr_toolkit_evidence(action=summary)` remains independently mandatory and must be requested explicitly in the toolkit bootstrap.
- Receipt v4 records only closed review, policy, completeness, usage, publication, and cleanup facts. Legacy receipts remain comment-readable but cannot acquire v4 approval guarantees.
- Any admitted mutable discussion/external record or required-source degradation blocks automatic approval. A complete enriched run with no admitted mutable record may proceed through every existing approval gate. Direct operator MCP remains the separate privileged, comment-only v0.6.3 boundary.
- OCR runs with an owner-only isolated home and deterministic cleanup. Cleanup or publication-DLP uncertainty blocks normal publication. v0.7.0 has no secure-debug retention exception.
- Runtime remains standard-library-only on Python 3.12-3.14. GitLab is the only forge adapter in M5; issue, documentation/wiki, and arbitrary read-only MCP pilots stay behind the common broker protocol rather than adding vendor-specific clients.

#### Logical implementation checklist

Check a box only in the signed commit that completes the entire slice, its focused evidence, self-review, and directly affected status documentation.

- [x] **A. Architecture and OCR capability checkpoint.** Rebuilt the live capability matrix; qualified OCR 1.9.7 and 1.9.8 with hosted official-digest probes, adjacent source review, and a checksum-verified local 1.9.8 probe; promoted 1.9.8; moved `.next-version` to `0.7.0`; froze exact policy, adapter, store, handle, receipt, containment, publication, and one-pass OCR contracts; assigned intended production owners in the threat/evidence matrix.
- [x] **B. Mandatory evidence bootstrap (#111).** Put the toolkit-authored `action=summary` requirement before repository-derived bootstrap data, retained zero-call rejection, and proved that preflight self-query does not count.
- [ ] **C. Common context contracts.** Implement the protected policy parser, independent budgets/projections, fixed recognizers, DLP normalization, atomic hostile-readable store, run-bound opaque handles, expiry/replay protection, and private artifacts.
- [ ] **D. Forge and external acquisition.** Implement bounded stable GitLab discussion snapshots, provider account classes and run pseudonyms, fixed stdio and HTTPS adapters, adapter-owned authorization, and broker admission. Qualify synthetic issue, document/wiki, and MCP-bridge peers through real transport owners.
- [ ] **E. OCR and publication containment.** Activate enriched mode, expose fixed local context tools, isolate and clean OCR home/session state, record receipt v4, enforce required completeness and approval behavior, and validate publication independently of retrieval/model egress.
- [ ] **F. Protected rules-path setup outcome (#107).** Classify only the exact immutable path-introduction case, carry a closed private identity-bound status envelope, and render static posting text while preserving prior comments and existing exit semantics.
- [ ] **G. GitLab CI inheritance uncertainty (#110).** Prohibit default inference through unresolved `extends`/includes, add the four synthetic cases, and retain arbitrary include/compiled-config acquisition outside the production boundary.
- [ ] **H. Public documentation and qualification.** Document the complete configuration, security, operations, GitLab, migration, receipt, residual-risk, and synthetic adapter contracts; update examples and Towncrier fragments; convert planned evidence claims only when production-path tests exist.
- [ ] **I. Holistic feature closure.** Review the complete range and every commit; perform requirement-to-evidence, architecture, privacy/license, and attack-path/security reviews; run one checksum-verified real OCR 1.9.8 review; remediate validated findings; rerun deterministic gates; verify the signed tree; then perform the single complete feature push.
- [ ] **J. Hosted feature delivery.** Pass all required hosted checks and resolved review on the exact head, mark the draft ready, squash-merge the reviewed tree, read it back on `main`, and verify the exact `0.7.0.devN` TestPyPI development artifacts and provenance.
- [ ] **K. Stable release and external reconciliation.** Prepare and merge exact `Release v0.7.0`, archive this plan with external delivery pending, publish/verify TestPyPI and PyPI bytes, provenance, attestations, annotated tag, immutable GitHub Release and receipt, smoke-install on Python 3.12-3.14, confirm issue receipts/closure, and finish without another repository PR.

#### Boundary and integration evidence contract

- Every new parser records grammar, normalization, optional/degraded states, byte/code-point/line/item/time units, impossible states, and hostile variants before implementation closure.
- Git, provider HTTP, adapter HTTP, stdio subprocess, persistence, MCP, OCR process, result/receipt, publication, and cleanup claims must cross their real production owner. A mock may prove orchestration only; use immutable temporary repositories, local TLS peers, real child processes, real stdio MCP, persisted hostile artifacts, and installed wheel/sdist paths.
- GitLab discussion acquisition binds the validated project/MR/head, bounded pagination, account class, thread/reply identity and order, edit/version/timestamp, anchor, resolved/outdated state, and a stable repeated snapshot. Partial, mutated, unavailable, unknown-identity, or over-budget data stays visible and cannot prove absence.
- Adapter responses collapse denied, missing, and foreign-tenant objects to one unavailable outcome. Unknown fields/statuses, request mismatch, authorization/version ambiguity, excess bytes, partial frames, DLP uncertainty, replay, or expired state cannot mint a handle.
- Model-facing context contains no raw actor identity or upstream object identifier. Names, usernames, email, avatars, profile URLs, commands, endpoints, credentials, external schemas, and adapter diagnostics remain outside model and publication projections.
- Publication validation runs after OCR but cannot claim to reverse model disclosure or detect arbitrary semantic paraphrase. Document that a lying adapter, broader service credential, same-owner host compromise, and model judgment remain residual risks requiring service-side authorization/audit and least-privilege credentials.

#### Issue-specific acceptance

- **#107:** setup-pending is emitted only when one normalized repository rule path is absent at diff base and captured policy SHA but exists at exact source SHA as a bounded regular blob. Divergence/removal, operator paths, absent/unsafe/oversized source, unknown identities, malformed status, changed target branch, lookalike repository text, and error-details mode retain safe outcomes from the issue matrix.
- **#108/#109:** the contiguous 1.9.7/1.9.8 compatibility evidence, official asset digests, adjacent source review, required result/MCP/session probes, human conclusions, manifest promotion, runtime pin, and synthetic GitLab executable pin agree exactly. Later upstream releases do not expand this delivery unless they break a consumed M5 capability.
- **#110:** unresolved parent evidence cannot support a default-dependent finding; bounded effective `allow_failure=true` cannot support one; bounded false under applicable policy and an explicit local false override may support one. No arbitrary include fetch or cross-repository model access is introduced.
- **#111:** the bootstrap explicitly mandates model-recorded `ocr_toolkit_evidence(action=summary)` even for a small/self-contained diff, states zero use is rejected, and retains the existing fail-closed receipt check.

#### Validation and self-review gates

Before every logical commit: update this checklist and status-bearing documents to post-commit truth, inspect status/staged scope and the complete slice diff, trace requirements through production flow and sibling boundaries, run focused real-owner tests, run `git diff --check`, apply privacy checks, fix every task-relevant defect, and sign the commit. Pre-push corrections may be amended into their owning local commit after re-signing and rerunning that slice's gates.

Before the complete feature push:

- run focused suites and `scripts/quality.sh check`;
- run Python 3.12-3.14 tests, OCR compatibility/lock validation, dependency audit, and medium-or-higher Bandit;
- build wheel and sdist reproducibly twice, run Twine/manifest checks, and smoke-install both artifacts through clean supported-Python environments with the real CLI and stdio MCP;
- run pinned complete-history `scripts/gitleaks.sh`, public privacy/license and archive scans, and `git diff --check`;
- review `origin/main...HEAD`, every commit, ownership/dependency direction, schemas, degradation, docs, changelog, private/public boundaries, and release truth;
- run a security diff/attack-path review and one final checksum-verified OCR 1.9.8 review with posting disabled; remediate validated findings and repeat affected deterministic checks plus the holistic review;
- verify every commit signature and that the pushed tree is the exact locally accepted tree.

#### Push, merge, and release gates

- The planning commit is the only early feature push. Keep subsequent work local; update the draft PR checklist and push again only after slice I is complete. Hosted remediation is pushed only as a complete signed correction after exact remote-head readback and the affected local gates.
- Feature merge requires exact-head readback, all required CI/security checks, no unresolved review, and squash-tree equivalence. Development publication must produce and independently verify the exact `0.7.0.devN` wheel/sdist and provenance before release preparation.
- The release PR is prepared from synchronized `main`, titled exactly `Release v0.7.0`, and tracks sorted issues `[107, 108, 109, 110, 111]`. It owns `.release-version=0.7.0`, `.next-version=0.7.1`, source epoch, generated changelog/notes, stable pins/checksums, plan archive, roadmap/backlog/strategy/README reconciliation, and returning `PLANS.md` to its template state.
- Completion requires independent TestPyPI/PyPI/GitHub hash equality, provenance and attestations, Python 3.12-3.14 installs, annotated tag target, immutable Release and `release-receipt.json`, plus Actions-owned receipts and closed state for all five issues. Feature readiness, feature merge, development publication, or release-PR preparation alone is not completion.
