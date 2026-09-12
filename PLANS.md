# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and
before handoff or commit. Completed stable plans are indexed in
[the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### v0.10.1 terminal merge-request lifecycle and OCR 1.11.9 qualification

- **Classification:** `release-required`; target stable version `0.10.1`.
- **Authorized scope:** GitHub issues `#187`, `#194`, `#195`, and `#196` only.
  Do not change the v0.11.0 feature backlog or broaden the release.
- **Branch / delivery:** implement on
  `codex/v0.10.1-terminal-mr-ocr-1.11.9`, deliver one feature pull request,
  then follow the complete stable-release and reconciliation lifecycle in
  `docs/release.md`.

#### Production slices

1. Parse GitLab merge-request lifecycle and identity through one strict shared
   contract. Treat malformed, unknown, mismatched, or unavailable provider data
   as fail-closed.
2. Before OCR admission, publish one idempotent toolkit status note when the
   merge request is already `merged` or `closed`; do not invoke OCR, fabricate
   evidence, erase prior review state, or attempt approval.
3. For an admitted result, re-read exact merge-request identity immediately
   before the first publication mutation. A terminal transition keeps normal
   findings, summaries, DLP, posting-limit, transaction, and reconciliation
   behavior, while reporting the reviewed commit and skipping approval.
4. Qualify OCR `1.11.7` through `1.11.9`. Freeze the `1.11.6`/`1.11.7`
   qualification contract, require the current Rego probe from `1.11.8`, and
   promote the recommended and minimum compatible OCR version to `1.11.9` only
   from verified workflow evidence plus bounded human conclusions.
5. Update the affected operator, security, compatibility, test-evidence,
   decision-flow, and changelog contracts. Preserve existing qualification
   evidence bytes for OCR `1.11.6` and earlier.

#### Acceptance and publication gates

- Run focused Python and synthetic-provider tests while iterating; never invoke
  local OCR because this checkout has no configured LLM.
- Cover early terminal races, duplicate jobs, emoji variants, preservation and
  cleanup of the terminal marker, admitted terminal results, approval
  suppression, hostile provider/schema data, DLP/budget/posting limits, and
  pre-/post-mutation failures.
- Cover frozen historical qualification, Rego-aware current qualification,
  cumulative `prepare-update`, and fail-before-write behavior.
- Before each logical commit: update this plan to post-commit truth, inspect the
  complete diff, run `git diff --check`, and run the owning targeted checks.
- Before every push: complete a security diff scan and `scripts/gitleaks.sh`.
  Before feature merge, run the full repository-owned local gate without OCR,
  then require all remote feature checks.
- Generate OCR `1.11.8` and `1.11.9` qualification evidence from exact branch
  workflows, verify and promote it, merge the feature PR, verify the TestPyPI
  development artifact, then prepare and merge `Release v0.10.1`.
- Close issues and milestone only after the stable PyPI/GitHub/tag/smoke receipt
  is verified. Finish with the no-release reconciliation PR, archived execution
  plan, and release-branch cleanup.

#### Progress

- [x] Activated the release plan and assigned `#187`, `#194`, `#195`, and
  `#196` to milestone v0.10.1.
- [x] Implemented and documented the strict terminal GitLab MR lifecycle,
  pre-execution status v3, idempotent terminal note, admitted-result guard,
  approval suppression, and successful-publication cleanup for `#194`.
- [x] Remediated the first pre-push scan and follow-up rescan findings: terminal
  markers are preamble-bound; every advisory-success path revalidates lifecycle;
  and strict gates stay nonzero for reopenable `closed` MRs. Final full-range
  scan `4d87525d-442a-4b66-aac5-8135740e67bf` completed at `efc6281` with no
  findings; the pinned Gitleaks gate and full local gate also passed before push.
- [x] Freeze the historical OCR `1.11.6`/`1.11.7` qualification contract and add
  the current Rego probe plus shared version-selected validation for OCR
  `1.11.8` and later.
- [x] Route live candidate probe inventories and observations through that same
  version-selected epoch, retain next-epoch language paths as negative controls,
  and add an exact `through_tag` ceiling for release-scoped hosted chains. The
  exploratory unbounded run was cancelled before creating an OCR 1.12.0 issue
  or artifact.
- [ ] Qualify and promote OCR `1.11.7` through `1.11.9` from exact hosted
  evidence and the recorded source-review conclusions.
- [ ] Complete the feature PR and hosted evidence, stable release, external
  receipt, issue/milestone closure, and reconciliation.
