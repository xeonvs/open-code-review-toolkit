# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and before handoff or commit. Completed stable plans are indexed in [the execution-history archive](docs/engineering/execution_history/README.md).

## Active Plan: M4 policy and project guidance for 0.6.0

Status: active; local implementation, review, validation, and history consolidation complete; feature publication next
Owner: Codex
Last Updated: 2026-08-14
Release Classification: release-required
Target Stable Version: 0.6.0
Next Development Version After Release PR: 0.6.1
Tracking Issue: #81
Branch: `feat/m4-policy-guidance`; no checkpoint commit is pushed individually
Qualified OCR Baseline At Activation: 1.9.2
Current Qualified OCR: 1.9.3; local promotion complete, issue #82 closure pending merged-support readback

### Goal And Closure Boundary

Deliver all of M4 as stable toolkit 0.6.0: BL-014 structured accepted decisions
and BL-015 safe nested target-branch project guidance through the established
read-only evidence MCP. Keep the lifecycle active through focused implementation
commits, complete validation, the completed pre-review Codex Security gate,
local OCR review cycles at concurrency 2, feature and release PRs, stable TestPyPI/PyPI
publication, provenance, annotated tag, immutable Release, supported-Python
installs, immutable receipt readback, and closure of issue #81. Feature merge
and development publication are intermediate receipts.

The active Codex goal carries the same full closure boundary and explicitly
forbids pushing local commits one by one. The first feature push occurs only
once the complete implementation, security cycle, OCR remediation, final
validation, self-review, and local history consolidation are complete.

### Architecture And Service Boundaries

- Add a pure internal `ocr_toolkit.evidence.policy` package for closed policy
  contracts, accepted-decision parsing, scope/applicability/staleness, guidance
  applicability/precedence, and an explicit static provider registry.
- Policy providers consume already bounded immutable documents. They perform no
  Git/filesystem/network/subprocess I/O, dynamic import, entry-point discovery,
  repository-code execution, mutation, persistence, transport, or review.
- `evidence.collectors` is an intentional package facade over manifest registry,
  source selection, bounded immutable include-graph acquisition, record/coverage
  projection, and one-ref orchestration. `evidence.store` is an intentional
  package facade over contracts, recursive value normalization, in-memory
  admission/serialization, atomic persistence, and hostile readback.
  `evidence.project` owns only compact bootstrap projection. `evidence.mcp`
  remains the one read-only stdio transport.
- Decomposition is extract-and-delegate: move already characterized functions
  and classes as intact blocks, retain the established public import surfaces,
  and prove parity with the same contract suites before and after each move.
  Do not rewrite working collection or persistence algorithms merely to reduce
  file size. Module size is a reviewability signal; responsibility and dependency
  direction, not a numeric line threshold, determine a split.
- Preserve the single reserved `ocr_toolkit_evidence` MCP with the existing
  `summary`, `list`, and `get` actions. Do not add a review engine, service,
  CLI/environment contract, runtime dependency, dynamic plugin loading, or
  compatibility shim.
- All public fixtures, docs, hosts, paths, names, and payloads are synthetic.
  No private source, identifier, aggregate, URL, or project detail enters the
  repository, issue, PR, logs intended for publication, or release artifacts.

### Accepted-Decision Contract

- The only policy-authoritative source is the immutable target/base blob at
  `.opencodereview/accepted-decisions.md`. Source/head edits never create policy
  authority; the toolkit never imports or executes repository content.
- Every H2 section is one decision. Existing `## slug` plus rationale remains
  valid. Optional bullet metadata is `Scope`, `Category`, `Owner`, and
  `Review after`; `Scope` may repeat and means OR. Unknown metadata is inert and
  does not invalidate a document or acquire semantics. A malformed field or
  entry cannot invalidate unrelated entries.
- IDs are deterministic normalized heading slugs. Ambiguous normalized
  duplicates are diagnosed and none of the colliding entries apply.
- Scope is a case-sensitive repository-relative POSIX glob. Permit literals,
  `*`, `?`, and `**` only as a complete segment. Reject absolute/traversal,
  empty/dot segments, backslash, negation, bracket/brace/extglob syntax,
  controls, and unsafe segments. No scope means project-wide. Unsafe scopes
  make only their decision inapplicable and never widen applicability.
- Applicability is evaluated against normalized changed paths. Persist bounded
  matched paths plus an explicit state. `Review after` is strict ISO
  `YYYY-MM-DD`; a decision is stale from the start of that UTC date but remains
  visible and cannot silently suppress findings. Category and Owner are only
  descriptive.
- Bootstrap receives bounded summaries only for applicable decisions: ID,
  scopes, and staleness, never full rationale. MCP list/get exposes the full
  redacted rationale, target provenance, metadata, scopes, applicability, and
  staleness. Decisions are contextual evidence, not authorization or an
  unconditional finding waiver.

### Project-Guidance Contract

- Full content is read and stored only from immutable target/base tree blobs.
  Nested `AGENTS.md` and `CLAUDE.md` apply to changed files below their directory.
  Existing supported root-only guidance sources remain global bounded records.
- Presentation precedence is root-to-file: shallower directory first,
  deterministic directory/path order, then `AGENTS.md` before `CLAUDE.md` at
  one depth. This orders untrusted evidence; it does not execute instructions.
- Guidance touched by add/change/delete/rename is excluded. Changed path input
  includes both rename sides. Symlink, submodule, non-blob indirection,
  oversized content, invalid UTF-8, and unsafe paths fail closed with bounded
  diagnostics.
- Persist document type, target path, scope, applicability, bounded matched
  paths, precedence metadata, and redacted text. Bootstrap includes only safe
  normalized paths, scopes, and toolkit-generated applicability hints; full
  repository excerpts are MCP-only.
- Guidance cannot change system policy, tool permissions, finding/posting
  rules, permit actions, or self-authorize source changes. Native OCR guidance
  is used only if a newly qualified release proves a target-ref-aware contract;
  otherwise the evidence MCP is the complete safe delivery path and remains
  source of truth if an adapter is later justified.

### Persistence And MCP Contract

- Raise the evidence-store envelope to schema v3 with exact closed top-level,
  limits, snapshot, delta, record, and kind-specific nested shapes. Validate
  accepted-decision and guidance values after redaction at admission and again
  on every hostile readback.
- Read v1 and v2 only through their exact historical schemas. Reject unknown
  fields rather than silently accepting extensions. Legacy text decision or
  guidance records retain text evidence only and gain no implicit structured
  applicability or authority.
- Preserve evidence IDs and MCP tool/action names. Raise summary schema to v3,
  add policy/guidance counts, and describe target-only non-authoritative policy
  evidence. Snapshot IDs, coverage, deltas, diagnostics, and records remain one
  atomic accepted store.

### Logical Implementation Commits

1. **Policy core and accepted-decision parser.** Activate this plan and version
   in the same functional commit; add contracts, static registry, parser, ID
   normalization, deterministic diagnostics, focused tests, format/security
   documentation, and initial Towncrier fragment.
2. **Scope, schema v3, and decision projection.** Add safe glob matching,
   applicability/staleness, target-only collection, strict v1/v2/v3 readback,
   bootstrap summaries, MCP projection, hostile fixtures, and documentation.
3. **Nested target guidance.** Add immutable discovery, applicability,
   precedence, changed/renamed exclusion, object-type attacks, bootstrap/MCP
   integration, multi-component tests, and documentation.
4. **Instruction ownership and recurring-incident cleanup.** Apply the completed
   audit once: replace the duplicated instruction stack with a short loader,
   canonical rule owners, a non-normative incident catalogue, and focused
   controls at the actual subsystem boundaries. This is repository-development
   governance within the already release-required 0.6.0 lifecycle; it does not
   add a registry, policy engine, runtime dependency, or separate publication
   objective. This internal maintenance slice is `no-release` on its own and is
   included in the already release-required M4 lifecycle without a separate
   Towncrier entry.
5. **Production integration and security hygiene.** Add synthetic installed
   wheel/sdist and real stdio MCP E2E, security/user docs, remaining Towncrier
   fragments, and only demonstrated least-privilege fixes for actionable GitHub
   Code scanning alerts.
6. **OCR 1.9.3 compatibility and GitLab presentation.** Reconcile the adjacent
   upstream release from official Linux qualification evidence, promote the
   checksum-pinned compatibility manifest only after human contract review,
   keep the summary as one canonical outcome line, and add an independently
   configurable finding-badge renderer with text fallback. This commit also
   carries the generalized repository threat model derived from the completed
   security review. It changes no review, evidence-MCP, provider-mutation, or
   release-authorization boundary.

Before every commit: run focused tests and `git diff --check`; inspect the staged
diff; audit sibling implementations and module/service boundaries; verify
 purpose docstrings and why-comments; update documentation and this plan to
 post-commit truth; run privacy checks; and use only synthetic fixtures. Do not
 push a checkpoint commit. Fix-only, plan-only, Codex Security, and OCR commits
 are folded into the logical owner during final unpublished-history rewrite.

### Policy-Core Checkpoint

- Added the pure `evidence.policy` package with immutable contracts, explicit
  static provider registry, tolerant H2 accepted-decision parser, deterministic
  ID normalization and diagnostics, closed case-sensitive POSIX scope grammar,
  strict review dates, applicability/staleness, and exact structured value
  validators. The package has no Git, I/O, subprocess, network, persistence, or
  transport dependency.
- Focused tests cover the legacy format, optional and unknown metadata, repeated
  scopes, duplicate normalized IDs, malformed dates and fields, UTC staleness,
  unsafe glob syntax, recursive segment matching, case sensitivity, and
  toolkit-generated guidance applicability/precedence. Ruff, strict mypy, the
  focused suite, and `git diff --check` pass. Integration into collectors/store/
  bootstrap/MCP remains intentionally owned by the following commits.
- Public configuration and development docs now describe the structured contract
  and extension boundary. The first functional checkpoint also carries release
  activation (`.next-version` 0.6.0), the complete durable plan, and the initial
  Towncrier feature fragment.

### Decision-Integration Checkpoint

- Target/base accepted decisions now emit one structured record per accepted H2;
  the head/source document emits none, the canonical path is case-sensitive,
  target-only policy kinds are excluded from ordinary base/head deltas, and UTC
  staleness, applicability, matched-path, and dedicated policy provenance survive
  persistence and MCP list/get.
- Evidence-store schema v3 validates exact envelope, limits, snapshot, delta,
  record, and policy shapes on admission and hostile readback. Exact v1/v2
  historical shapes remain readable; v2 text-only policy records remain inert and
  gain no implicit structured authority. MCP summary is v3 and explicitly marks
  policy as target-only and non-authoritative.
- Bootstrap includes bounded ID/scope/staleness summaries for applicable target
  decisions only and never includes rationale. Focused decision, collector, store,
  bootstrap, MCP, framework and runner suites pass alongside Ruff and strict mypy.
  Public configuration now describes schema v3 and implemented decision
  behavior; durable strategy remains planned until the guidance slice completes.
  Nested guidance remains owned by the next logical slice.

### Nested-Guidance Checkpoint

- The collector now discovers root and nested `AGENTS.md`/`CLAUDE.md` plus
  established global guidance names from immutable target/base blobs only. It
  excludes every guidance path touched by add/change/delete/rename, emits no
  source/head guidance records, and reports rejected symlink/non-blob sources
  without dereferencing them.
- Structured guidance records preserve exact target path, document type, scope,
  applicability, bounded matched paths, full redacted MCP-only text, and
  root-to-file precedence with `AGENTS.md` before `CLAUDE.md`. Store readback
  rejects unknown nested fields, unsafe scopes or matched paths, invalid document
  types, mismatched envelope/source identity, non-target provenance, and
  type-confused or inconsistent precedence. Policy kinds remain outside ordinary
  source/target deltas because source policy is never authoritative.
- Bootstrap renders only normalized applicable guidance paths/scopes and
  toolkit-generated match counts; repository excerpts remain absent. Synthetic
  tests cover multi-component applicability, conflicts, changed and renamed
  attacks, symlink rejection, MCP/store redaction, and bootstrap secrecy. Public
  README, security, configuration, development, and strategy documentation now
  match the implemented service and trust boundaries.
- The previously retained externally reconciled M2 cycle moved into the stable
  release archive and is linked from the release index. `PLANS.md` now contains
  only this active M4 lifecycle; the 0.6.0 release PR will preserve its decisions
  and receipts in the archive and return this file to its empty template before
  publication.

### Instruction-Governance Remediation

The audit after checkpoint 3 found an unmodelled instruction lifecycle rather
than one missing prohibition. Incident corrections had been copied into
`AGENTS.md`, engineering principles, contributor/release procedures, pitfalls,
and phrase-presence tests without a unique owner and, where the requirement was
mechanically checkable, a subsystem-owned control. That made secondary guidance
easy not to load, let contradictory plan-archive rules survive, and tested
wording rather than behavior.

This self-reviewed logical checkpoint after `3a09194`:

- keep `AGENTS.md` as the short always-loaded repository map and workflow
  loader; it selects applicable canonical owners and procedures but does not
  restate their technical invariants;
- keep durable architecture/trust invariants in project principles, contributor
  procedure in `docs/development.md`, release lifecycle in `docs/release.md`,
  public operator/environment behavior in operational/provider/configuration
  docs, and runtime semantics in code plus contract tests;
- reduce `AGENT_EXECUTION_PITFALLS.md` to incident records with an allowed root
  cause (`missing-rule`, `conflicting-rule`, `not-loaded`, or `unenforced`), one
  canonical owner, one current control, and historical evidence. Remove generic
  imperative lists and one-off implementation detail; merge incidents that have
  the same cause and correction;
- map each mechanically checkable invariant directly to an existing focused
  test, script, or workflow gate owned by the affected subsystem. Remove tests
  that freeze copied instruction prose; ordinary documentation review owns
  non-mechanical organization such as plan archiving;
- correct the release/archive contradiction: the release PR archives the
  repository-complete cycle with external delivery pending and returns
  `PLANS.md` to its template; immutable receipt reconciliation then closes
  delivery without a repository mutation.

Acceptance scenarios: release tests and receipt gates stop 0.2.0-style closure
after a feature/development build; the trusted-base workflow test stops a
candidate from executing its authorizer; boundary tests stop bounded-after-
capture I/O; the local full-range Gitleaks gate stops secret-shaped history
before push; release preparation moves the completed repository plan without
making its Markdown layout an authorization input; and a typical parser/provider
change resolves to its canonical boundary owner and focused tests before routine
quality validation. HTTP, subprocess, provider, and cleanup rules permit bounded
read-only diagnosis and guarded reversible operations; they forbid only the
unsafe trust or mutation mechanism.

### Instruction-Governance Checkpoint

- `AGENTS.md` is now a short startup map. Project principles own durable
  architecture and trust invariants, development guidance owns contributor
  procedure and validation selection, release guidance owns delivery, and
  public operational documents retain product-contract ownership.
- The pitfalls document is a diagnostic incident catalogue with symptom, root
  cause, canonical owner, current control, and historical evidence. It no
  longer restates an imperative workflow or treats historical detail as current
  policy.
- Phrase-presence tests were removed. Existing parser, trust-boundary, release
  authorization, receipt, publication, and issue-closure suites remain the
  controls for mechanically checkable behavior. No runtime, workflow,
  authorization, dependency, or public product contract changed in this slice.
- Plan archiving remains ordinary release-PR documentation review, not a
  schema, helper, verifier, or publication gate. The release PR records external
  delivery as pending; the immutable receipt and independent readback close it
  without another repository mutation.
- A follow-up audit removed the unnecessary byte-for-byte/hash expectation for
  archived prose. Normal review checks only that decisions and receipts remain
  discoverable and the release index has a usable link; Git history preserves
  the original text without making Markdown layout a release boundary.
- Full quality, focused release and evidence suites, workflow YAML parsing,
  compatibility validation, Towncrier draft rendering, privacy inspection, and
  `git diff --check` pass. Self-review mapped every removed durable requirement
  to one canonical owner and retained bounded read-only diagnostics and guarded
  reversible operations.

### Validation, Codex Security, And OCR Gates

1. Run complete deterministic validation without OCR: Python 3.12-3.14,
   `scripts/quality.sh`, Bandit, focused security/dependency/privacy/Gitleaks
   gates, reproducible wheel/sdist hashes, clean installed-artifact smoke with
   restricted `PATH`, hostile shadow package and private permissions, real
   stdio MCP, bootstrap budgets, hostile schema readback, and synthetic
   multi-component E2E.
2. The pre-review Codex Security `security-diff-scan` is complete for exact
   committed range `fa65b2e..98aaa07`. Its ignored canonical receipt reports
   complete coverage, no deferred surfaces, and zero findings; findings and
   coverage hashes are `c885cabf99d78c31b067710636dd0ff8e7b1a690d7bf78fa76f0bf9eab4d3c0a`
   and `92c2639d5f5c07b500671f285b2fd12185697da671b48b71af20fbbe3c424695`.
   The generalized threat model is already reflected in public security docs.
   The owner explicitly replaced a further post-remediation security rerun with
   another local OCR review; do not run an additional Codex Security cycle for
   this release unless the user asks again or a new demonstrated security defect
   invalidates the completed receipt.
3. The first OCR 1.9.3 run at concurrency 2 reviewed 19 of 21 selected files,
   failed two oversized flat modules on tool-round budget, and produced five
   findings. Its exact `fa65b2e..98aaa07` result is retained privately with hash
   `f6f128ff5da5dbb3177d9b158ff0a7a33a05fc915180088dde92c50da2eec7e4`.
   All findings now have negative regressions and fixes: oversized decisions,
   empty-path root guidance, adjacent recursive scope segments, cap-before-
   precedence bootstrap ordering, and one-field badge paths. Sibling review also
   bounds the complete UTF-8 policy value before persistence/MCP projection.
4. Complete deterministic validation on the remediated and responsibility-
   decomposed tree, then run the newly authorized complete local OCR review over
   the full M4 diff with qualified OCR 1.9.3, concurrency 2, posting disabled,
   and private ignored artifacts. Record actual evidence-MCP use without claiming
   action granularity that the OCR receipt cannot prove. Fix every actionable
   result, inspect sibling boundaries, and repeat the applicable deterministic
   validation and final self-review. Do not run a third OCR without new approval.
5. Consolidate unpublished history into logical owner commits, prove exact
   final-tree equivalence, verify signatures, and rerun Gitleaks over the full
   first-parent range. Only then make one initial push of the complete branch.

### Upstream OCR Monitoring

At activation and between completed logical stages, query stable upstream OCR
releases and this project's release issues. Qualify every newly observed stable
release as one complete adjacent chain, classify every upstream item as a
consumed-contract change, future-backlog impact, or release-note-only context,
and adapt only demonstrated toolkit contracts. Use the latest fully qualified
release for installed E2E and final OCR. A later release that changes executable
contracts or the reviewed tree invalidates the final OCR gate as described
above.

#### OCR 1.9.3 Qualification And Contract Decision

- Official scheduled workflow run 31778152040 qualified exactly 1.9.2 -> 1.9.3
  on Linux amd64. Every release asset and `sha256sum.txt` digest matched, and
  version, help, preview, required review flags, result-consumer, additive-field,
  comment-thinking, and manifest probes passed. The chain result is
  `human-review-required`, tracked in issue #82. The human conclusion,
  manifest/evidence update, and focused tests qualify the exact local tree for
  installed E2E and OCR; repository-wide support is not externally complete
  until the feature PR merges and issue #82's evidence comment and closure are
  independently read back.
- The JSON result adds optional `retry_report` observability. The toolkit already
  accepts and preserves additive top-level fields and need not publish provider,
  model, request, or file-path retry details into GitLab. Keep the field private
  in the OCR result artifact; add no second retry-report schema or posting
  service unless a separate demonstrated operator need is activated.
- SARIF, `no-review`, trusted resume lineage, session affinity, stabilized
  upstream item fingerprints, and clearer non-review CLI argument errors do not
  alter toolkit-owned invocation, result normalization, suppression fingerprints,
  or provider mutation. The grace round may produce additional ordinary
  findings after tool-request exhaustion but does not change partial/budget
  outcome semantics consumed by the toolkit.
- User include/exclude patterns are now case-insensitive. Built-in allowlist
  membership is unchanged, the rules diff changes matching only, required flags
  remain present, and the consumed Go MCP SDK remains v1.6.1. Existing synthetic
  rules use portable lowercase patterns, so no rules or evidence-MCP adaptation
  is justified.
- Upstream image badges are a GitHub Action presentation feature implemented
  from existing comment `category` and `severity`; they are not a new OCR JSON
  field and do not belong in the toolkit summary/result parser. The toolkit may
  independently project the same normalized facts at its GitLab presentation
  boundary, subject to the privacy and fallback contract below.

#### GitLab Summary And Finding-Badge Contract

- The review summary and individual findings are separate presentation
  contracts. The summary has one bold text outcome line combining review health
  and publication state across clean, findings, warnings, incomplete coverage,
  token budget, skipped, failed, omitted, and reviewer-suppressed outcomes. It
  uses no remote image and remains readable with emoji disabled.
- Inline discussions and fallback finding notes own category/severity rendering.
  Existing normalized OCR enums and the `priority` compatibility fallback remain
  the sole metadata source. Unknown, malformed, control-bearing, or unsupported
  values are omitted; repository/model text is never interpolated into an image
  URL, alt delimiter, color, host, or query.
- Text tags remain the private-safe default. An explicit `OCR_POST_BADGES=shields`
  mode renders one static `img.shields.io` image before each finding when at
  least one normalized field is present. URL segments, host, severity colors,
  and category fallback color come from closed toolkit constants. The image alt
  text carries the same normalized `category · severity` label, so blocked or
  failed image loads degrade to text. Invalid configuration fails back to text
  without logging its raw value.
- The external mode is opt-in because a browser, GitLab instance, or image proxy
  may contact a third party while rendering an otherwise private review. Public
  docs must state that tradeoff and recommend text mode where external image
  requests or disclosure of viewer/network metadata are unacceptable. Badge
  selection never affects fingerprints, suppression, approval, posting limits,
  note ownership, draft transactions, rollback, or summary counts.
- Contract tests cover the complete summary matrix, emoji-disabled output,
  normalized badge combinations and color coverage, one-field badges, malformed
  metadata, text/alt fallback, invalid mode, inline/fallback placement, suggestion
  coexistence, bounded note rendering, and the absence of arbitrary URLs or
  untrusted metadata in generated Markdown.

### GitHub Code Scanning Audit

- Live readback at activation found no open CodeQL Python alerts, no secret
  scanning alerts, and no Dependabot alerts. Current CodeQL and security runs on
  `main` succeed.
- Scorecard alerts #17 (`release.yml`) and #15
  (`actions-maintenance.yml`) are concrete `TokenPermissionsID` candidates.
  Inspect complete job permissions and apply least privilege only where behavior
  and release authorization remain intact; verify hosted readback before
  considering them closed.
- Scorecard Fuzzing, Maintained, CodeReview, and BranchProtection alerts are not
  code defects to dismiss or spoof in M4. Fuzzing remains separately triggered
  work; maintenance/review/protection are repository-governance settings. Re-read
  them after feature/release delivery and close only with objective external
  evidence, otherwise preserve them open with an explicit no-change result.

### Production Integration Checkpoint

- A permanent installed-artifact E2E now builds one direct wheel and one sdist,
  rebuilds the sdist through its own package boundary, installs both without
  runtime dependencies, and verifies `pip check`, exact isolated import, and the
  installed `ocr-ci` entry point under a restricted `PATH`.
- Each installed artifact runs from a synthetic repository containing a hostile
  `ocr_toolkit` shadow package. It collects immutable target decisions and root/
  nested guidance, excludes a source-modified guidance file and source-only
  decision replacement, preserves complete changed-path applicability, writes
  owner-only artifacts, and exposes full target text only through a real
  read-only stdio MCP `summary`, filtered `list`, and stable-ID `get` lifecycle.
- The maintenance workflow now keeps `contents: read` at workflow scope and
  grants `actions: write` only to the cleanup job that owns bounded cache,
  artifact, and log deletion. Alert #15 remains open until a post-merge hosted
  Scorecard run reads the new workflow; its current main-branch instance still
  identifies the former top-level permission.
- Alert #17 is a documented no-change result: the final release job alone has
  `contents: write` and `issues: write` because it creates the authorized tag and
  immutable Release, uploads exact assets, writes receipt comments, and closes
  tracked issues only after readback. Removing, hiding, or splitting those
  required rights solely to change a score would weaken the release boundary.
- Sequential validation on one tree passes the installed E2E, routine quality
  gate, focused evidence/release/workflow suites, OCR manifest, workflow YAML,
  target 0.6.0 Towncrier rendering, privacy scan, and `git diff --check`. Live
  readback still reports OCR 1.9.2 as latest, issue #81 as the only open project
  issue, and no secret-scanning or Dependabot alerts.

### Deterministic Validation And Codex Security Remediation

- Exact commit `95c58d5142060c8f78f6b904d9ffc0c8f836ea60` passed the complete
  deterministic Python 3.12-3.14, routine quality, Bandit, dependency, package,
  reproducibility, installed-artifact, hostile-environment, privacy, Gitleaks,
  and real stdio MCP matrix. The ignored private receipt binds that tree and its
  development wheel/sdist hashes.
- The pre-OCR diff scan reviewed all changed runtime files and supporting
  collection, rendering, persistence, MCP, test, installed-package, and workflow
  boundaries. Two low-severity findings survived: repository backticks could
  escape fixed bootstrap code spans, and non-applicable nested guidance could
  consume the policy budget then stop unrelated typed evidence. Private-store
  provenance forgery and legacy summary misclassification reproduced as defects
  but were not security-reportable because their proven paths require
  operator-equivalent local artifact selection or write access.
- Remediation uses the existing module boundaries rather than adding a service:
  the pure policy package selects applicable ancestor guidance and owns its
  document bound; collectors read that bounded policy batch separately; generic
  store admission continues after one kind's ordinary truncation; schema-v3
  readback rejects legacy values and rebinds policy provenance/applicability to
  the exact snapshots; MCP derives legacy/target labels from actual records; and
  bootstrap rendering uses the shared delimiter-aware inline-code helper with
  complete-line clipping. Focused hostile tests and documentation are updated.
- Final pre-commit self-review also made canonical accepted decisions first in
  the isolated policy byte budget, so even a large set of genuinely applicable
  guidance cannot evict the decision document. A synthetic constrained-budget
  regression proves the decision survives while later guidance degrades with an
  explicit omission diagnostic.
- The remediation worktree before the final self-review refinement passed the
  corrected direct-interpreter Python 3.12-3.14 matrix, routine quality and security/dependency
  checks, deterministic target-version wheel/sdist builds, Twine, clean
  installed-artifact checks on every supported Python, hostile shadow-package
  imports, restricted-path CLI, real stdio MCP summary/list/get, private-mode
  and synthetic-repository checks, workflow parsing, compatibility validation,
  Towncrier rendering, Gitleaks, private-marker inspection, and diff hygiene.
  The earlier environment-manager matrix attempt is explicitly superseded and
  is not acceptance evidence. The final decision-priority refinement then
  passed the focused policy/evidence, integration/release, Ruff, strict-mypy,
  syntax, privacy, and diff-hygiene checks. The later exact-head security scan
  completed with zero findings as recorded below.
- Before that exact-head scan, the user requested a public posting refinement and
  OCR 1.9.3 became available. Keep review-health plus publication state in one
  canonical summary line, but treat the release's badges as finding-comment
  presentation rather than summary or result data. Implement the opt-in,
  closed-enum Shields projection and private-safe text fallback defined above;
  preserve incomplete coverage, warnings, approval, commit identity, posting
  counts, and tool/MCP/token receipts in their existing owned sections. The
  formatter remains presentation-only; result normalization and GitLab
  transaction boundaries do not change. Complete compatibility promotion,
  threat-model documentation, focused tests, self-review, and one new signed
  local commit before the exact-head security scan. Nothing is pushed before the
  later consolidated feature handoff.

### OCR 1.9.3 And GitLab Presentation Checkpoint

- Official run 31778152040 and the downloaded qualification artifact prove the
  complete adjacent 1.9.2 -> 1.9.3 chain, exact asset digests, and Linux amd64
  version/help/preview/result-consumer contracts. Human source review classifies
  the additive retry report as private observability, case-insensitive user
  filters as a compatible selection correction, and the remaining upstream
  features as outside toolkit-owned runtime contracts. The compatibility
  manifest, canonical evidence, preflight pin, synthetic CI example, and tests
  now target checksum-pinned 1.9.3. Issue #82 remains open until merged support
  and its evidence comment are independently read back.
- GitLab review health and publication state now render as one canonical summary
  line for every clean, finding, warning, partial, budget, skipped, failed,
  omitted, and suppressed state. Individual findings independently retain local
  text metadata by default and support opt-in `OCR_POST_BADGES=shields` images.
  Posting orchestration resolves that mode once and supplies it only to inline
  and fallback renderers; summaries, fingerprints, suppression, approval,
  transaction ownership, and counts do not consume it.
- The image projection accepts only normalized closed category/severity enums,
  a fixed host, and a complete fixed color map. Unknown or control-bearing
  metadata is omitted, alt text carries the same normalized label, invalid mode
  fails back to text without echoing its input, and docs explicitly describe the
  optional third-party render request. OCR 1.9.3 `retry_report` remains inside
  the private result artifact and is absent from GitLab notes.
- The repository threat model and scanner policy now generalize the completed
  security review into assets, attacker capabilities, trust boundaries,
  invariants, reportability calibration, safe diagnostics, and the remote-image
  boundary. The security-policy resolver finds one applicable root policy for
  the posting package; no duplicate nested scanner policy was introduced.
- Focused posting, workflow, compatibility, result-contract, operations,
  runtime, integration, and release-note suites pass. The complete quality gate
  passes 742 tests and 99 subtests with Ruff, strict mypy, Bandit, coverage,
  privacy, compatibility validation, Towncrier rendering, local-link checks,
  and diff hygiene. Live readback still reports OCR 1.9.3 as latest, issue #82
  open without a premature completion comment, no secret-scanning or Dependabot
  alerts, and the same six previously classified Scorecard alerts.

### First OCR Remediation And Evidence-Module Architecture Review

- The completed pre-review Codex Security diff scan is sealed under the ignored
  release evidence directory. It covered every changed source-like file and all
  supporting control surfaces at exact head `98aaa07`, has complete coverage,
  no deferred work, and zero findings. The user explicitly waived a redundant
  post-remediation security rerun in favor of a second local OCR cycle.
- OCR 1.9.3 then ran over the exact committed M4 range with posting disabled and
  concurrency 2. It selected 21 files, completed 19, failed the former flat
  `collectors.py` and `store.py` only after exhausting tool-request rounds, and
  returned five medium bug findings. The run is partial rather than clean. It
  made 47 calls attributed to `ocr_toolkit_evidence`; preflight separately
  proved summary/list/get, while the OCR receipt itself does not distinguish
  those action names.
- Negative tests reproduce and close every OCR finding: one oversized decision
  is isolated without dropping siblings; root `AGENTS.md`/`CLAUDE.md` remain
  global with empty changed-path identity; adjacent `**` segments fail closed;
  bootstrap caps apply after semantic ordering; and one-field Shields images use
  an explicit category or severity label. A sibling boundary audit additionally
  rejects complete multibyte policy values that cannot fit storage/MCP budgets,
  both before admission and on hostile schema-v3 readback. A final adversarial
  audit also proved that recursive redaction can expand repeated short secret
  fields; store admission now reapplies the whole-value UTF-8 budget after that
  trust transition, ordinary collection omits only the affected record, and
  hostile readback rejects the incomplete atomic envelope.
- Architecture review found the former flat collectors and store mixed distinct
  lifecycles. Using extract-and-delegate rather than algorithm rewrites,
  collectors now separates registry, source projections, immutable include
  graphs, record/coverage projections, and one-ref orchestration. Store separates
  contracts, recursive normalization, in-memory admission/serialization,
  owner-only atomic replacement, and hostile readback. Existing public package
  imports remain intentional facades; there are no flat compatibility modules,
  cycles, new runtime services, dependencies, configuration, or MCP lifecycle.
- The same characterization suites passed before and after every move. Current
  focused receipts include 97 collector tests and the complete policy/store/MCP
  boundary suite; the final broad installed-policy matrix passes 349 tests plus
  26 subtests. Architecture checks enforce required responsibility
  owners and forbidden upward imports without freezing line counts or every
  future helper filename. The canonical engineering principle treats size as a
  reviewability signal and requires cohesive owners and shared pure contracts.
- Final deterministic validation on the current tree passes 754 tests plus 99
  subtests independently on Python 3.12.14, 3.13.15, and 3.14.6. The complete
  quality gate passes Ruff format/lint, strict mypy, Bandit, the same test count,
  and 80.96% branch coverage. Lock validation, dependency audit, workflow YAML,
  shell syntax, OCR compatibility validation, Towncrier draft rendering,
  privacy inspection, complete committed-range Gitleaks, and diff hygiene pass.
- Two source-epoch-controlled target builds are byte-identical and pass Twine,
  closed package-content checks, zero-runtime-dependency metadata, and
  restricted-path hostile-shadow installs on every supported Python. The sealed
  `0.6.0.dev0` hashes are wheel
  `2e2af14595523ba81a44e420ebd2b245098415f639e29fdc67c6a4fa98bd8d76`
  and sdist
  `56f20ec1d55d71038ffa7c2e22d2a067d54b3149d556933572b0676fdb74dc1d`.
- That pre-second-review receipt is superseded for final-tree packaging by the
  post-remediation build recorded below. Final self-review is complete; the
  remaining work is history consolidation and the feature/release/publication
  lifecycle.

### Second OCR Review And Remediation

- The authorized second OCR 1.9.3 run reviewed the exact committed range
  `fa65b2e..39e9c26` through `ocr-ci review` with concurrency 2, JSON agent
  output, the public synthetic rules, and posting disabled. It completed all 31
  selected source-like files with no failed, waived, or reused item and made 67
  calls attributed to the built-in evidence MCP. Its private result hash is
  `e28cde985307b095a51bad3e383eecec0596cb588e54f80b64fe40ddd181b1fc`.
- Nine findings were validated as boundary classes rather than applied as raw
  suggestions. Negative tests and fixes now preserve every source when semantic
  delta identities collide or move; report all parents of a shared missing
  Python include; recognize YAML list-item images; cap decision matching work;
  distinguish a decision submodule diagnostic; reject boolean schema versions,
  unadmitted snapshot indexes, obfuscated sensitive mapping keys, and key
  collisions after redaction; and synchronize the store directory after atomic
  replacement through the existing cross-platform durability contract.
- Final sibling review applied the same source-provenance class to Ansible and
  later-depth Python include edges, and the same explicit object-type diagnostic
  to guidance submodules. These are narrow extensions of characterized graph and
  policy-source behavior, not rewrites of collector orchestration.
- The fixes remain inside the extracted responsibility owners. They do not
  recombine collectors/store, rewrite the characterized orchestration or
  persistence algorithms, add a service or MCP lifecycle, or change ordinary
  unique-fact delta values. A third OCR cycle is not authorized; the final
  focused, complete deterministic, package, E2E, privacy, and self-review gates
  passed as recorded below.
- Final post-remediation quality passes 766 tests plus 99 subtests with 81.12%
  branch coverage; exact Python 3.12.14, 3.13.15, and 3.14.7 matrices pass the same
  suite. The final source-epoch-controlled `0.6.0.dev0` builds are byte-identical
  with wheel hash
  `606582acb64e5e8add5df01d2b78517d87632d6d81283207c7e1cb29eb61d98a`
  and sdist hash
  `2c8e32b55f950acc9d88e2579cda316cf6cae7db92699c98bebdd7d0b34332e2`.
  Twine, lock, dependency audit, compatibility manifest, Towncrier draft,
  workflow/example YAML, changed-shell syntax, private-marker, diff-hygiene,
  facade/package-layout, and installed wheel/sdist policy-MCP gates pass. The
  installed-focused matrix passes 376 tests plus 49 subtests. No third OCR or
  redundant Codex Security cycle was run.

### Feature, Release, And Stable Closure

- Open the feature PR only after the one complete push. Read back exact head,
  required checks, review threads, and merge policy. Group CI/review fixes into
  completed self-reviewed batches rather than pushing every commit. After merge,
  independently verify TestPyPI development artifacts, hashes, installs, and
  exact merged tree.
- The release PR is the final repository mutation. Preserve the already archived
  M2 receipts, consume Towncrier fragments into 0.6.0 notes, set the following
  line to 0.6.1, archive this plan as repository-complete/external-delivery-
  pending, return `PLANS.md` to its template, and reconcile the roadmap table/
  diagram, backlog, strategy, and narrative docs to the same truth.
  Remove BL-014/BL-015 only after implementation evidence proves completion;
  retain a native target-ref OCR optimization only as a conditional follow-up
  if qualification does not establish it.
- After release-PR merge, verify stable TestPyPI/PyPI hashes, provenance and
  attestations, Python 3.12-3.14 clean installs, annotated tag and peeled target,
  immutable GitHub Release, machine receipt, and independent readback. Close
  issue #81 only after its canonical receipt evidence is present. Do not create
  another repository PR or artifact solely to copy external closure facts.

### Work Queue

1. [x] Reconcile clean `main`, create `feat/m4-policy-guidance`, create issue
   #81 and active lifecycle goal, classify 0.6.0, read current OCR, repository,
   PR, issue, Code scanning, secret scanning, and Dependabot state.
2. [x] Complete logical commit 1: policy core and accepted-decision parser.
3. [x] Complete logical commit 2: scope, schema v3, and decision projections.
4. [x] Complete logical commit 3: nested target guidance.
5. [x] Complete logical commit 4: canonical instruction ownership, recurring-
   incident catalogue cleanup, focused subsystem controls, and validation.
6. [x] Complete logical commit 5: production E2E, documentation, fragments, and
   demonstrated Code scanning workflow improvements.
7. [x] Complete deterministic Python/package/security/privacy validation.
8. [x] Complete OCR 1.9.3 human qualification and local compatibility promotion;
   finish the separate one-line summary, opt-in finding badges, threat-model
   documentation, focused validation, and logical commit 6.
9. [x] Complete the pre-review Codex Security diff scan with complete coverage
   and zero findings; retain its receipt and do not add the waived redundant rerun.
10. [x] Complete the first local OCR review, fix all five findings, audit sibling
   boundary risks, and decompose collectors/store by responsibility through
   characterized extract-and-delegate moves.
11. [x] Complete the second OCR 31/31 review, remediate all nine findings with
   negative tests, inspect sibling boundaries, and pass final deterministic,
   package, installed E2E, privacy, and self-review gates without a third OCR.
12. [ ] Unpublished history is consolidated with exact tree equivalence, signed
   commits, and a passing full-range Gitleaks scan; make and read back the one
   initial push of the complete feature branch.
13. [ ] Complete feature PR and independent TestPyPI development readback, then
   comment on and close OCR qualification issue #82 only after merged support is
   independently read back.
14. [ ] Prepare the final repository mutation in the release PR and reconcile
   backlog, roadmap, strategy, and release metadata honestly.
15. [ ] Complete stable 0.6.0 publication/readback and close issue #81 only from
   the immutable release receipt; use the release-PR archive and template state
   as repository evidence without another closure mutation.
