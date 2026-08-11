# Execution Plans

Use this file for active, blocked, or recently completed execution work. Update it before implementation and before handoff or commit. Older completed plans are indexed in [the execution-history archive](docs/engineering/execution_history/README.md).

## Active Plan: Harden GitLab suggestions and add SHA-bound approval for 0.4.7

Status: active; implementation, release-lifecycle, and OCR 1.9.1 qualification checkpoints complete
Owner: Codex
Last Updated: 2026-08-11
Release Classification: release-required
Target Stable Version: 0.4.7
Tracking Issues: #70, #71, #72 (OCR 1.9.1), #73 (OCR 1.9.0)

### Goal

Ship issues #70 and #71 as toolkit 0.4.7: publish actionable GitLab
suggestions only when they are proven to replace one contiguous range in the
reviewed immutable head, and add conservative default-on automatic approval
that is bound to the exact reviewed merge-request SHA. Preserve a successfully
published advisory review when approval management is ineligible, stale, or
fails, and complete the release only after immutable external evidence has been
independently read back.

### Decisions

- Use one feature branch and one protected feature pull request, with separate
  signed implementation checkpoints for #70, #71, and release-lifecycle
  hardening. Keep both issues open until stable external delivery is verified.
- Keep provider-neutral decisions in typed core objects and GitLab HTTP/state
  transitions behind the provider adapter. Add no runtime dependency, public
  evidence command, permanent OCR harness, telemetry expansion, or tunable
  approval-policy variables.
- Make `OCR_AUTO_APPROVE` default on with the established boolean vocabulary.
  An invalid value disables approval for that run. Encode the initial policy in
  code and fail closed when authoritative completeness or typed finding
  metadata cannot be proven.
- After the release-lifecycle checkpoint, qualify the contiguous Open Code
  Review 1.9.0 and 1.9.1 chain from authoritative release/source evidence.
  Preserve a separate checksum/contract record and human impact conclusion for
  each release, with a separate qualification issue for each version. Classify
  every upstream item as a toolkit-consumed contract change, future-backlog
  impact, or explicit no impact; adapt only demonstrated contracts and
  atomically replace the local checksum-pinned OCR binary with 1.9.1 before
  full E2E.
- After the complete feature implementation is committed, run exactly one real
  local OCR 1.9.1 review through `uv run ocr-ci review` over
  `origin/main..HEAD`. Require the built-in `ocr_toolkit_evidence` MCP receipt,
  do not post to GitLab, fix actionable findings, and then use deterministic
  validation and self-review rather than a second OCR run.
- Do not run Codex Security. Existing repository CI security checks and the
  checksum-pinned local Gitleaks gate remain required.
- Redesign the durable release lifecycle so the release PR is the final
  repository mutation without preclaiming external facts. Bind publication to
  the exact reviewed tree and emit an immutable machine-readable release
  receipt; close #70/#71 and both OCR qualification issues only after
  independent registry, provenance, tag, Release, receipt, hash, and
  supported-Python readback succeeds.

### Work Queue

1. [x] Implement typed contiguous-range suggestion validation, immutable-head
   proof, bounded omission reasons, documentation, complete regressions, review,
   and the #70 checkpoint commit.
2. [x] Implement typed auto-approval configuration and policy, exact-SHA GitLab
   synchronization/write/readback, managed own-user approval receipts,
   documentation, complete regressions, review, and the #71 checkpoint commit.
3. [x] Replace the redundant post-release closure-PR contract with exact-tree
   release authorization and deterministic `ocr-toolkit.release-receipt/v1`
   evidence; update durable rules, recovery behavior, tests, and the lifecycle
   checkpoint commit.
4. [x] Inspect authoritative OCR 1.9.0 and 1.9.1 release notes and source
   changes, record separate consumed-contract/backlog/no-impact
   classifications and qualification issues, update compatibility records and
   the local checksum-pinned OCR 1.9.1 binary, and adapt the toolkit only where
   evidence requires it.
5. [ ] Reconcile this plan, roadmap table/diagram, backlog, and current-state
   documentation against the implemented code. Run focused tests, the synthetic
   GitLab E2E, Python 3.12 quality, Towncrier draft, workflow/document/privacy
   checks, and `git diff --check`.
6. [ ] Commit the complete feature tip and run one local toolkit-owned OCR review
   with private result/stderr artifacts, no GitLab posting, and verified nonzero
   built-in MCP use. Correct findings and complete final self-review without a
   second OCR or Codex Security run.
7. [ ] Run deterministic post-review validation and pinned local Gitleaks over
   the unpublished history, push the exact reviewed branch, open one feature PR,
   resolve every conversation, pass protected checks, and squash-merge.
8. [ ] Independently verify the exact TestPyPI development artifacts, hashes,
   provenance, and supported-Python installs before preparing `release/v0.4.7`.
9. [ ] Prepare and validate the final release PR, consuming fragments 69, 70,
   and 71 and reconciling repository-side planning truth without claiming
   publication that has not happened.
10. [ ] Merge the release PR only after exact-head protected checks. Verify stable
   TestPyPI/PyPI artifacts, provenance/attestations, annotated tag, immutable
   GitHub Release and release receipt, hashes, and Python 3.12-3.14 installs.
   Record receipts and close #70/#71 plus both OCR qualification issues without
   another repository PR.

### Initial Evidence

- Clean synchronized `main` is `bb8827148f13b17b209495788ac4f7b15573a168`;
  stable toolkit 0.4.6 is published and `.next-version` targets 0.4.7.
- Issues #70 and #71 are open. Current suggestion handling proves exact no-op
  equality but does not prove changed `suggestion_code` applies to
  `existing_code` at the reviewed range; the toolkit has no approval-management
  transaction yet.
- The effective local binary is Open Code Review 1.8.10 and the checkout's
  `uv run ocr-ci review` path owns evidence collection, compact bootstrap,
  mandatory `ocr_toolkit_evidence` composition, use verification, and the
  private receipt.
- Current release guidance still requires a documentation-only closure PR and
  release authorization does not bind publication to the reviewed head tree and
  exact checks. Both are explicit scope of the lifecycle checkpoint.

### Issue #70 Checkpoint

- GitLab suggestion applicability is now a closed typed decision rather than a
  hidden mutation on the untrusted OCR comment. The renderer accepts only an
  already-proven replacement; impossible state/field combinations fail at the
  typed boundary.
- Validation binds a safe repository-relative path and inclusive range to one
  bounded immutable head blob, normalizes CRLF/CR and one terminal newline, and
  requires exact `existing_code` agreement before a changed replacement becomes
  actionable. Existing exact no-op suppression remains available even for the
  older no-`existing_code` result shape.
- Synthetic omission bridges across common comment syntaxes, diff-prefixed
  replacements, quick actions, unsafe fences, oversized values, stale source,
  and invalid ranges retain the finding but produce only a closed non-sensitive
  omission reason. Fallback notes never render an actionable suggestion fence.
- Focused Ruff and strict mypy pass. The complete posting/suggestion regression
  set passes 123 tests, including valid one-line and multiline replacements,
  newline equivalence, missing/stale source, invalid/out-of-bounds ranges,
  omission variants, diff prefixes, no-op behavior, typed invariants, unsafe
  paths, and workflow-level proof that only the apply fence is withheld.
  Towncrier 0.4.7 draft and `git diff --check` pass.

### Issue #71 Checkpoint

- `OCR_AUTO_APPROVE` is a typed default-on setting using the shared
  true/false, 1/0, yes/no, and on/off vocabulary. Invalid values fail closed to
  disabled without logging their contents. The fixed policy consumes the full
  unsuppressed OCR finding set and requires a complete manifest, zero warnings,
  failures, waivers, budget stop, or omitted findings, no more than three exact
  `low` findings, and only style/documentation/maintainability categories.
- Approval is a distinct post-publication transaction. The GitLab adapter reads
  bounded MR and full paginated diff-version state, selects the highest valid
  version ID, waits at most ten two-second intervals for merge/approval
  synchronization and a non-null patch ID, verifies the open current head, and
  submits only the reviewed 40-hex SHA. Approve, unapprove, and summary-update
  writes are attempted once and followed by bounded readback.
- Versioned managed-approval receipts are accepted only from the fixed prefix of
  an owned plain toolkit summary. Conflicting, forged fallback, malformed, or
  wrong-user receipts cannot authorize unapproval. A later complete
  authoritative ineligible review can remove only the authenticated user's
  proven managed approval; partial, skipped, legacy, disabled, and ambiguous
  states preserve it. No runtime path calls GitLab `reset_approvals`.
- The published summary contains one bounded approval state. Eligible runs first
  publish a conservative failed-until-confirmed state, then update the uniquely
  marked owned summary once after provider readback. Failure never rolls back the
  advisory review; strict mode returns nonzero while advisory mode remains
  nonfatal. Existing GitLab rules, groups, Code Owners, protected branches, and
  reauthentication stay authoritative.
- Self-review fixed receipt loss on partial reviews, version-order assumptions,
  receipt parsing after cross-endpoint deduplication, stale receipt inheritance,
  different-SHA approval claims, and provisional-summary truth. Ruff and strict
  mypy pass; 148 posting/approval/suggestion tests and 15 public
  documentation/integration contracts pass. Towncrier 0.4.7 draft includes the
  default-on write and opt-out, and `git diff --check` passes. Roadmap and future
  backlog statuses remain unchanged because neither issue completes an existing
  outcome milestone or activation trigger.

### Release Lifecycle Checkpoint

- The merged release PR is now the final repository mutation without claiming
  future delivery. Authorization executes from that exact merge checkout,
  validates tracked metadata from the same immutable ref, proves squash-tree
  equivalence and parent identity, and requires every live strict `main` check
  context from its exact GitHub App on the reviewed head SHA.
- Registry verification covers Python 3.12-3.14 and exact PyPI Integrity
  publisher/subject provenance. GitHub artifact attestations, annotated-tag
  target, exact Release metadata/assets, immutable status, and a deterministic
  `ocr-toolkit.release-receipt/v1` are verified before tracked issues close.
- Recovery is non-destructive and exact: existing registry and draft Release
  bytes must match, an existing receipt remains canonical across workflow
  reruns, asset reads work through bounded authenticated API calls, and no path
  replaces an existing tag, receipt, or Release asset.
- Issue closure is bounded and idempotent. Every tracked item is preflighted
  before publication; only an exact GitHub Actions-owned receipt marker is
  trusted, conflicting user markers fail closed, and an already-completed issue
  is accepted after final readback. Durable agent guidance, principles,
  pitfalls, release documentation, and execution-history rules now agree that
  no redundant post-release repository PR is required.
- Self-review corrected timestamp semantics, arbitrary receipt artifact names,
  incomplete check-run binding, unbounded API/asset/comment reads, draft asset
  download behavior, destructive `--clobber` recovery, receipt regeneration on
  reruns, metadata checkout drift, standalone provenance imports, and ambiguous
  Release/issue state. The focused suite passes 53 tests; strict mypy, Ruff,
  ShellCheck, workflow YAML parsing, OCR manifest validation, Towncrier 0.4.7
  draft, and `git diff --check` pass. Full `scripts/quality.sh check` passes 608
  tests plus 81 subtests at 79.62% coverage. Roadmap and backlog statuses remain
  unchanged at this checkpoint because the lifecycle hardening changes process,
  not an outcome milestone or future-work activation trigger.

### OCR 1.9.0-1.9.1 Qualification Checkpoint

- Canonical GitHub Actions run `31465539451` created separate open
  qualification issues #73 for 1.9.0 and #72 for 1.9.1. Local Python 3.12
  qualification independently downloaded all seven assets for each release,
  proved GitHub digests equal the upstream `sha256sum.txt`, executed the Linux
  amd64 version/help/JSON-preview/full-review/result/posting contracts, and
  reproduced both evidence files byte-for-byte from checkpoint `5acbf15`.
- OCR 1.9.0 is compatible after required human review. Toolkit-consumed changes
  are JSON preview output, preview session-store isolation, additive private
  comment `thinking`, merge-base range semantics, and the Nim rules/allowlist
  expansion. The harness now proves JSON preview, no session-store creation,
  additive `thinking` preservation, and non-publication of that private field;
  source review confirms reasoning-content backfill and the documented range
  semantics. The Nim change receives a separate `🧩 Rules` entry.
- OCR 1.9.0 per-file token limits and retry status codes are future profile or
  configuration inputs only and do not activate BL-016. Mistral and MiniMax
  providers, QCA delegation, the upstream GitLab example, Pages/viewer/CSP,
  scan and installation documentation, fork deployment, blog, package-manager,
  and other documentation fixes are not toolkit-owned contracts. They require
  no runtime, roadmap, or backlog activation.
- OCR 1.9.1 is an adjacent automatic-safe patch whose source was still reviewed.
  Viewer comment filters and suggestion-panel layout, CodeQL workflow
  permissions, upstream contributor/retry documentation, and the Anthropic
  dynamic cache breakpoint do not change toolkit CLI, result, posting,
  configuration, or MCP contracts. The cache change is a future profile/quality
  input only and does not complete BL-016 or BL-017.
- Both releases retain Go MCP SDK v1.6.1 and protocol revision `2025-11-25`, so
  the built-in MCP protocol matrix is unchanged. Both annotated upstream tags
  carry signatures that GitHub reports as `unknown_key`; compatibility does not
  misrepresent them as verified and instead relies on the double-source asset
  digest contract plus executed binary probes.
- Human-reviewed promotion now accepts only an adjacent patch, next minor `.0`,
  or next major `.0.0`; every minor/major transition requires an explicit
  bounded conclusion. The automatic lane remains patch-only. Self-review also
  isolated Git initialization, preview, and full-review probes from operator
  OCR/Git configuration and bounded optional automatic-safe conclusions.
- Manifest, preflight, public examples, documentation, tests, and Linux digest
  now target OCR 1.9.1. The PATH-effective Darwin arm64 binary is official OCR
  1.9.1 with SHA-256
  `5cffe45ef006b80dcbe95e6711807261850108d6390ce708cdac0e72cb261d1d`;
  its isolated local contract probe passes. Focused validation passes 265 tests
  plus 27 subtests, Ruff, strict mypy, manifest validation, Towncrier 0.4.7
  draft, and `git diff --check`.
- Backlog statuses, roadmap table/diagram, and strategy status remain unchanged.
  Nim is review-engine scope rather than an evidence pack; upstream `AGENTS.md`
  is contributor guidance rather than target-ref runtime guidance; token/cache
  changes do not supply the missing profile or telemetry policy contracts.
- The complete isolated Python 3.12.13 quality gate passes formatting, Ruff,
  strict mypy, Bandit, 622 tests plus 81 subtests, and 79.61% coverage. A fresh
  authenticated discovery after promotion reports zero unseen stable OCR
  releases. The gate uses `.quality-logs/py312` and does not mutate the host
  `.venv` or tracked checkout.

## Completed Plan: Reconcile 0.4.6 lifecycle, architecture, and backlog truth

Status: completed; validated documentation/process PR handoff
Owner: Codex
Last Updated: 2026-08-08
Release Classification: no-release
Target Stable Version: not applicable

### Goal

Close the externally completed toolkit 0.4.6 lifecycle in repository truth, document the established M1 architecture, re-audit every remaining backlog item against current code and published behavior, correct planning and release-process drift, and archive older execution plans without changing runtime or initiating package publication.

### Decisions

- Inspect current implementation before retaining backlog scope or dependencies; distinguish implemented, partial, planned, conditional, obsolete, and historical work.
- Adopt the durable lifecycle `feature PR -> TestPyPI development verification -> release PR -> stable publication -> external reconciliation -> no-release closure PR` for future release-required work.
- Keep `.release-version`, `.next-version`, `.release-source-date-epoch`, the recommended OCR baseline, dependencies, runtime behavior, and public contracts unchanged.
- Open one documentation/process pull request and leave it unmerged in this task because a merge to `main` would initiate the automatic TestPyPI development publication that this no-release task explicitly excludes.
- Preserve the complete audit trail by moving older completed plan detail to `docs/engineering/execution_history/releases.md`; keep the 0.4.6 cycle and this reconciliation in the compact active registry.

### Work Queue

1. [x] Read the canonical instructions, all current plans and durable documentation, the M1 implementation and tests, v0.4.0-v0.4.6 history, and live 0.4.6 release and issue receipts.
2. [x] Run bounded OCR discovery and confirm that no unseen stable upstream release exists.
3. [x] Reconcile the 0.4.6 plan and future release-lifecycle instructions from independently verified external evidence.
4. [x] Archive older completed plans without losing decisions, validation, links, hashes, or receipts.
5. [x] Rewrite durable strategy and README current-state prose and classify historical migration material explicitly.
6. [x] Audit every backlog item, narrow BL-008 and BL-013 to remaining work, park BL-012 conditionally, and correct other status/dependency errors.
7. [x] Correct the evidence MCP cursor terminology without changing behavior and add the documentation Towncrier fragment.
8. [x] Review each substantial workstream, render changed Mermaid diagrams, validate Markdown, public-content privacy, quality, Gitleaks, Towncrier, marker immutability, and the final diff.
9. [x] Update this plan to handoff truth, push the exact branch, and open one protected documentation/process pull request without merging or publishing packages.

### Initial Evidence

- The clean synchronized `main` branch is at annotated tag `v0.4.6`; the tag targets release merge `c87952559ec7e6bed4c1b38fcb0b41d2d5fcecf6`.
- Feature PR #67 merged as `2b0f8393ba86a6150a694180b10bae7d0907db09`; release PR #68 merged as `c87952559ec7e6bed4c1b38fcb0b41d2d5fcecf6`; release workflow `31250755741` completed successfully.
- TestPyPI, PyPI, and the immutable GitHub Release expose wheel SHA-256 `7a944f5f1332728d857574d81cb484507eb3c5a6f5105d71a35dfbec0329307d` and sdist SHA-256 `dcde562699c759764eb3cba4654cce511871c2e3c26a1ab2c1d9726fe94c5cba`.
- Registry provenance identifies `release.yml`, the release merge/run, and the `testpypi-public-disclosure` and `pypi-production` trusted-publishing environments. Published wheel installs passed on Python 3.12/3.13 and the sdist on Python 3.14.
- Issues #65 and #66 have completed four-item human checklists, owner conclusions, release receipts, and `completed` closure reasons.
- `scripts/ocr_compat.py discover` reports zero unseen stable OCR releases; no compatibility promotion belongs in this task.

### Code-First Backlog Audit

| Item | Current capability conclusion | Result |
| --- | --- | --- |
| BL-008 | Partially implemented | M1 already supplies the listed Python, JavaScript, Go, Composer, Ansible, image, immutable-delta, MCP, and scoped-completeness baseline. The item now contains only demonstrated format, installed-metadata, workspace/platform, precedence, tag/digest, component-scope, and completeness gaps. |
| BL-009 | Not implemented; selection trigger unmet | Remains planned, but no longer waits for all BL-008 gaps; only a selected plugin's actual evidence dependency applies. |
| BL-010 | Conditional trigger unmet | Remains conditional and no longer waits for broad BL-008/BL-009 completion. |
| BL-011 | Not implemented; ready safety work | Remains the prerequisite for automatic reference detection and provider-specific external-content examples. |
| BL-012 | Conditional trigger unmet | Moved from ready/high to conditional/low; no named provider currently requires managed browser OAuth beyond static headers or a reviewed stdio proxy. |
| BL-013 | Core implemented; provider examples not implemented | Mandatory built-in/external composition, transports, replacement, namespaces, collisions, capability rendering, secrets, receipts, and integration tests are complete. Only BL-011-gated synthetic provider examples remain; OAuth is not a blocker. |
| BL-014 | Not implemented; technical trigger met | Remains planned on established evidence and target-branch decision contracts. |
| BL-015 | Conditional trigger unmet | Remains conditional because no supported OCR contract proves target-ref-aware automatic guidance. |
| BL-016 | Partially unblocked | OCR per-run model/provider and result-identity capabilities exist; the owner-approved closed profile and precedence matrix remains the blocker. |
| BL-017 | Partially implemented inputs; audit ready | Existing OCR telemetry plus review-health, failed-file, finding, posting, suppression, and MCP-use receipts support an audit now. The item is narrowed to no-release gap analysis; any runtime telemetry becomes separate work. |
| BL-018 | Conditional trigger unmet | Remains conditional on profiles, the measurement conclusion, representative evidence, and an owner-approved routing policy. |
| BL-019 | Technical prerequisite met; operational trigger unmet | Stable M1 parser interfaces exist, but target selection, bounded resources, corpus ownership, and backend criteria remain unresolved, so the item stays parked. |
| BL-020 | Partially unblocked; demand trigger unmet | MCP composition and evidence schemas are stable; file configuration remains parked until operational need and a coherent non-secret schema are demonstrated. |
| BL-021 | Conditional trigger unmet | Remains conditional because no funded named forge, owner, fixture set, or parity matrix exists. |

### Architecture And Process Review Checkpoint

- Critical/Pareto review selected one compact active registry, one stable-tag index, and one full release archive. This preserves all nonblank historical plan content byte-for-byte while avoiding year-based hierarchy and duplicate summaries.
- The release contract now separates repository preparation from external publication and post-release reconciliation. The latest reconciled tag remains indexed from `PLANS.md`; older cycles retain stable explicit anchors in the archive.
- Source/test readback confirms the BL-008 implemented baseline and BL-013 composition baseline. Strategy claims match the current collector registry, mandatory MCP lifecycle, native HTTPS/stdio transports, scoped completeness, and distinct GitLab result/reporting concepts.
- No exact OCR version remains in durable strategy prose. Historical release numbers remain only in the archive/index, operational compatibility docs, changelog, and version-specific backlog evidence where they are intentional.

### Final Validation And Handoff

- `scripts/quality.sh check` passes Ruff formatting/lint, mypy, Bandit, 547 tests plus 35 subtests, and 79.01% coverage. The focused release-process, review-runner, result, posting, and runtime-helper suite passes 218 tests plus 27 subtests.
- Every changed Mermaid block renders successfully with Mermaid CLI 11.16.0 and passes visual review. All repository-local Markdown links and anchors validate, including every tag-index entry and explicit archive anchor.
- `uv run towncrier build --draft --version 0.4.7`, `uv run python scripts/ocr_compat.py validate`, the changed-public-content privacy scan, checksum-verified Gitleaks 8.24.3, and `git diff --check` pass. Final bounded OCR discovery still reports zero unseen stable releases.
- `.release-version`, `.next-version`, and `.release-source-date-epoch` are byte-identical to `origin/main`. The diff changes no CLI, environment, schema, MCP behavior, GitLab publication behavior, workflow, dependency, lock, or recommended OCR baseline; the only runtime-file edit corrects a cursor docstring.
- Protected documentation/process PR #69 carries this no-release closure on `agent/reconcile-0.4.6-lifecycle`. It remains unmerged because merging to `main` would initiate the repository's automatic TestPyPI development workflow; no package, tag, Release, attestation, or registry artifact was created by this task.

## Completed Plan: Qualify OCR 1.8.9-1.8.10 and release toolkit 0.4.6

Status: completed; stable publication and external reconciliation independently verified
Owner: Codex
Last Updated: 2026-08-08
Release Classification: release-required
Target Stable Version: 0.4.6
Tracking Issues: #65, #66

### Goal

Qualify Open Code Review 1.8.9 and 1.8.10 as one ordered upstream release chain, promote checksum-verified 1.8.10 as the tested and recommended toolkit baseline, update the local OCR installation and every affected test, example, documentation, and backlog contract, and publish stable toolkit 0.4.6. Reclaim GitHub Actions storage through the repository's bounded retention policy without deleting workflow run/check metadata, releases, tags, attestations, or registry artifacts.

### Decisions

- Treat OCR 1.8.9 and 1.8.10 as compatible human-reviewed candidates. Viewer, benchmark, Pages, OpenCode plugin, documentation, CI, and dependency changes are release-note-only context because the toolkit does not consume those surfaces.
- OCR 1.8.9 native `code_search` option-like reference hardening improves the upstream security boundary without changing the toolkit CLI, result, MCP, or configuration contract.
- OCR 1.8.10 rejects invalid extra positional CLI arguments, removes dead internal timeout fields, and renders tool parameters deterministically. Valid toolkit invocations remain compatible; deterministic rendering improves reproducibility but does not complete BL-016 or BL-017.
- Preserve all future backlog statuses. Verify that BL-019 retains one activation sentence and update only version-specific context proven stale by the promoted baseline; no roadmap milestone is completed.
- Install only the official checksum-verified Darwin arm64 OCR 1.8.10 binary locally and run deterministic compatibility probes. Do not perform an unbounded or paid LLM review.
- Use the existing bounded Actions maintenance policy: delete eligible caches, expired/aged artifacts, and aged downloadable log archives while retaining workflow run/check metadata and longer release/TestPyPI audit windows. Re-read repository storage APIs and repeat the dry-run after execution.
- The original combined release/closure decision is historical evidence of the process gap corrected after publication. Stable publication completed successfully, but repository-side closure required this later no-release reconciliation.
- Future release-required plans remain active through feature merge, TestPyPI development verification, release PR, stable publication, external reconciliation, and a separate no-release closure PR.

### Work Queue

1. [x] Repeat the Actions cleanup dry-run, execute the exact bounded policy through the maintenance workflow, and verify the resulting cache/artifact/log candidate state.
2. [x] Independently verify hosted evidence and official binaries for OCR 1.8.9 and 1.8.10; run deterministic local probes and atomically update local OCR to 1.8.10.
3. [x] Promote the cumulative reviewed baseline to 1.8.10 and update runtime, checksum, example, compatibility, configuration, security, and test contracts.
4. [x] Reconcile upstream changes against the backlog and roadmap, preserve unfinished scope, verify the single BL-019 activation line, and add one Towncrier feature fragment for the full chain.
5. [x] Review the cleanup, qualification/promotion, and documentation/backlog boundaries separately; correct every actionable finding before continuing.
6. [x] Run focused and complete Python validation, manifest/workflow/Towncrier checks, pinned Gitleaks, reproducible build/Twine, restricted-path wheel/sdist installs, and a final full-diff review.
7. [x] Merge the protected feature PR and independently reconcile its exact TestPyPI development artifacts, hashes, provenance, and supported install smokes.
8. [x] Prepare and merge release PR #68 as verified merge `c87952559ec7e6bed4c1b38fcb0b41d2d5fcecf6`.
9. [x] Verify stable TestPyPI/PyPI artifacts, annotated tag, immutable GitHub Release, hashes, attestations, and Python 3.12-3.14 installs through successful release workflow `31250755741` and independent registry/GitHub readback.
10. [x] Record the completed human conclusions and stable-release receipts on #65/#66 and close both issues as completed.

### Initial Evidence

- `main` is clean and synchronized at `b066140`; stable toolkit v0.4.5 is published and `.next-version` targets 0.4.6. The recommended and locally installed OCR baseline is 1.8.8.
- Open issues #65 and #66 contain hosted schema-v2 qualification evidence for OCR 1.8.9 and 1.8.10. Both machine contracts are compatible and require the human conclusions recorded above; the observed chain is contiguous from tested baseline 1.8.8.
- Official Darwin arm64 SHA-256 is `abb70af93c0dae6785e6129e9bb9ab50432f9d6b3164fa1d8ffdcd972a3fdf1d` for OCR 1.8.9 and `ee850ccd9ea69feb38b87dd4f789da7da5e96648c2747c52a01014eac2b87a23` for OCR 1.8.10. Official Linux amd64 SHA-256 is `43ea736e9e14501336db46a83e12f06f79eec690a019e2c186df98477c8b179c` and `7161500791b8d27906ee8a29bf4429953b27048e90e33dd9a4ff6118932c9001`, respectively.
- Repository storage reads found 195,180,119 bytes across six caches and 17,889,889 bytes across 167 artifacts before cleanup. The dry-run selected 267 bounded objects: three caches, 95 artifacts, and 169 log archives; known cache/artifact bytes total 125,000,205, excluding log archives whose API does not expose size.

### Actions Cleanup Review Checkpoint

- The execution-time dry-run reproduced the original scope exactly: 267 objects and 125,000,205 known bytes. Maintenance run `31250057127` completed successfully and deleted all three caches, 95 artifacts, and 169 log archives with zero already-absent responses; workflow run and check metadata remained available.
- Repository API readback reports 80,065,771 bytes across three active caches and 8,004,032 bytes across 72 active artifacts, about 84 MiB of known Actions storage. This is a 125,000,205-byte reduction in the API surfaces that expose sizes; GitHub's account billing meter can update later and is not available to the repository-scoped token.
- A manual audit still lists the 169 old run identities because `--include-all-old` deliberately plans against immutable run metadata. Direct reads of representative log archives return HTTP 404, proving their downloadable bytes are gone. Scheduled cleanup already limits retry planning to two weekly opportunities and does not need a policy or test change.

### Qualification, Promotion, And Backlog Review Checkpoint

- Hosted schema-v2 evidence from run `31243828961` forms a contiguous 1.8.8 to 1.8.9 to 1.8.10 chain. Official `sha256sum.txt` files and independently downloaded Darwin arm64 binaries agree with the evidence digests; deterministic version, help, preview, JSON-result, and optional-capability probes pass for both candidates.
- `/opt/homebrew/bin/ocr` was atomically replaced with the official Darwin arm64 1.8.10 binary. It reports `open-code-review v1.8.10`; SHA-256 is `ee850ccd9ea69feb38b87dd4f789da7da5e96648c2747c52a01014eac2b87a23`, and the installed-path compatibility probe passes.
- Source and release-note review confirms that 1.8.9's `code_search` hardening is upstream defense in depth without a consumed interface change. OCR 1.8.10's invalid positional-argument rejection does not affect valid toolkit calls, its timeout-field removal is internal, and deterministic tool-parameter rendering is additive. Both tags retain Go MCP SDK v1.6.1 and the existing protocol revision set.
- Runtime preflight, public GitLab example version and Linux checksum, README, compatibility/configuration/GitLab/security documentation, manifest, evidence, and current-baseline tests now agree on 1.8.10. One #66 Towncrier feature fragment covers the full reviewed chain; no rules fragment is justified because the consumed allowlist/rule surface did not change.
- Backlog review adds deterministic-rendering context to BL-016 and BL-017 without changing their planned status. BL-008/009/010 retain historically accurate 1.8.8 overlap notes, BL-019 already contains exactly one activation sentence, and no roadmap status changes.
- Review found four test cases whose semantics were "next patch after the current baseline" but whose fixtures remained pinned to 1.8.8/1.8.9. They now exercise 1.8.10 to 1.8.11. Focused validation passes 124 tests plus 15 MCP subtests, manifest validation, Ruff, and `git diff --check`.

### Pre-Commit Validation Checkpoint

- `scripts/quality.sh check` passes 547 tests plus 35 subtests at 79% coverage together with Ruff formatting/lint, mypy, and Bandit. Manifest validation, frozen-lock validation, workflow YAML parsing, Towncrier 0.4.6 draft rendering, dependency audit, and `git diff --check` pass.
- Two source-date-epoch-controlled development builds are byte-identical and pass Twine: wheel SHA-256 `ab92dd17be8c4bfaebc2d140e322edc4d3b152f8c2f77bb66b0d5ee06cccad2e`; sdist SHA-256 `2ee0b2e72e839feb1cf379327d50ea52a32b862dd1d8e4cc8d71238285e730d0`.
- Restricted-path installs pass from a private hostile shadow-package directory: the wheel on Python 3.12 and 3.13, and the sdist on Python 3.14. All three expose the installed CLI/import and exact development version without importing repository content.
- Final scope review confirms that evidence hashes match the manifest, current pins agree on OCR 1.8.10, remaining 1.8.8 references are historical fixtures or capability provenance, and no roadmap, runtime dependency, CLI, environment, schema, or provider contract changed beyond the expected OCR version baseline.
- Checksum-verified Gitleaks 8.24.3 passes the complete first-parent feature history. The locally installed 8.30.1 was not accepted as a substitute for the repository's exact security pin.

### Feature Merge And Development Publication

- Feature PR #67 passed all 13 protected checks with no conversation comments, reviews, or review threads and merged as GitHub-verified squash commit `2b0f8393ba86a6150a694180b10bae7d0907db09`. All six post-main workflow suites completed successfully.
- TestPyPI run `31250465780` published and installed immutable `0.4.6.dev42`. Cache-bypassed PEP 691 reads, freshly downloaded registry bytes, and the workflow artifact are byte-identical: wheel SHA-256 `c82121bd500afd808da784b9c2cdf2883ee979bec4e73578238e246bb3d526bb`; sdist SHA-256 `2372e29519a5a9bf6ec373de466451348eb4055e15479d8a4843c357dbf22b06`.
- TestPyPI provenance subjects match both exact digests and identify `testpypi.yml`, merge `2b0f8393ba86a6150a694180b10bae7d0907db09`, run `31250465780`, and the `testpypi-public-disclosure` environment. Restricted-path installs of registry bytes pass for the wheel on Python 3.12/3.13 and the sdist on Python 3.14 from a private hostile shadow-package directory.
- The release PR is also the repository-side closure PR as requested. It will consume the #66 fragment, reconcile the plan and unchanged roadmap/backlog statuses, and advance the next development line; stable publication evidence will be added only to #65/#66 after it exists, without a second repository PR.

### Release Preparation Review Checkpoint

- The combined release-and-closure diff contains only the stable/next version markers, deterministic source epoch, generated 0.4.6 changelog, consumed #66 fragment, and current plan receipts. The release notes render the exact `v0.4.5...v0.4.6` comparison; no roadmap milestone or future-backlog item is closed.
- The complete quality gate passes 547 tests plus 35 subtests at 79% coverage, Ruff formatting/lint, mypy, and Bandit. Manifest, frozen lock, release-note extraction, dependency audit, and both staged/unstaged `git diff --check` validation pass.
- Two clean stable builds with version `0.4.6` and source epoch `1786181004` are byte-identical and pass Twine: wheel SHA-256 `7a944f5f1332728d857574d81cb484507eb3c5a6f5105d71a35dfbec0329307d`; sdist SHA-256 `dcde562699c759764eb3cba4654cce511871c2e3c26a1ab2c1d9726fe94c5cba`.
- Restricted-path installs of the stable wheel pass on Python 3.12 and 3.13, and the stable sdist passes on Python 3.14. All three run the installed CLI/import from a private hostile shadow-package directory and report exactly 0.4.6.
- Checksum-verified Gitleaks 8.24.3 passes the release history from protected `main`; the final release commit remains signed and the combined diff is free of whitespace errors.


### External Release Reconciliation

- Feature PR #67 merged as `2b0f8393ba86a6150a694180b10bae7d0907db09`; release PR #68 merged as `c87952559ec7e6bed4c1b38fcb0b41d2d5fcecf6`.
- Stable release workflow `31250755741` completed successfully. The reviewed wheel SHA-256 is `7a944f5f1332728d857574d81cb484507eb3c5a6f5105d71a35dfbec0329307d`; the reviewed sdist SHA-256 is `dcde562699c759764eb3cba4654cce511871c2e3c26a1ab2c1d9726fe94c5cba`.
- Cache-bypassed TestPyPI and PyPI JSON reads, the workflow artifact, and immutable GitHub Release assets expose the same two filenames and hashes. Registry provenance subjects bind both distributions to `release.yml`, the exact release merge/run, and the `testpypi-public-disclosure` and `pypi-production` environments.
- Annotated tag object `b3fc3f1e0789142d27829ebf5cad5cd81ca79b8a` targets the release merge. GitHub reports the v0.4.6 Release immutable; GitHub artifact attestations verify both distributions.
- Published-artifact installs passed for the wheel on Python 3.12 and 3.13 and the sdist on Python 3.14 from the restricted hostile-shadow-package harness.
- Issues #65 and #66 each retain a completed four-item human checklist, an owner compatibility conclusion, the full release receipt, and a `completed` closure reason.
