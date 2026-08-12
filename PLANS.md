# Execution Plans

Use this file for active, blocked, or recently completed execution work. Update it before implementation and before handoff or commit. Older completed plans are indexed in [the execution-history archive](docs/engineering/execution_history/README.md).

## Active Plan: M2 ecosystem and framework coverage for 0.5.0

Status: active; implementation checkpoints in progress
Owner: Codex
Last Updated: 2026-08-12
Release Classification: release-required
Target Stable Version: 0.5.0
Tracking Issues: #76, #78 (OCR 1.9.2); feature PR #77

### Goal

Deliver M2 as stable toolkit 0.5.0 with bounded static framework plugins for
Jinja2, Go web frameworks, Symfony/PHP, and React/TypeScript. Make Jinja and
Twig template files actually reviewable by the recommended OCR through the
public synthetic rules pack, expose framework/template state and deltas through
the existing read-only evidence MCP, repair issue #76 release recovery, and
qualify checksum-pinned OCR 1.9.2 through issue #78 before final validation.
Deliver completed slices as local checkpoint commits without intermediate
pushes. Complete the synthetic installed-artifact E2E and the already-run local
review, remediate it, finish the framework-package slice and full deterministic
validation, then run one additional full local OCR review with concurrency 2.
Remediate that review and push feature PR #77 only once after final local
validation, before protected feature and stable delivery.

### Decisions

- Release-required target is 0.5.0. Keep this plan active through feature PR,
  TestPyPI development verification, final release PR, stable registries,
  provenance, annotated tag, immutable Release, receipt, supported-Python
  installs, and completed closure of issues #76 and #78.
- Use only anonymized technology selection conclusions from the private
  inventory. Never persist private host, project, namespace, path, payload, or
  identifying aggregate data; all public fixtures and examples are synthetic.
- Add a static package-owned plugin registry. Plugins consume immutable bounded
  normalized evidence only and cannot load repository code, execute commands,
  use network access, mutate repositories, or start a second MCP/review flow.
- Preserve one built-in `ocr_toolkit_evidence` MCP with summary/list/get. Store
  validated framework and template records before OCR starts; MCP performs no
  plugin collection at request time.
- Make `.j2`, `.jinja`, `.jinja2`, extensionless Ansible-role templates, and
  `.twig` files reviewable through explicit additive `include` patterns plus
  specific merged rules in `examples/gitlab/rules.json`.
- Qualify the full adjacent OCR 1.9.1 to 1.9.2 transition from published
  checksums, source/tag history, release notes, and consumed-contract probes.
  Classify every upstream item, adapt only demonstrated toolkit contracts, and
  use qualified OCR 1.9.2 for installed-artifact E2E and local reviews.
- The original one-review limit governed the first full local OCR 1.9.2 review
  and its deterministic remediation. The owner explicitly superseded that limit
  on 2026-08-12: after complete deterministic validation, run one additional
  full repository review with OCR concurrency 2, require real evidence-MCP use,
  keep posting disabled and artifacts private, then fix actionable findings and
  return to deterministic validation without another OCR rerun.
- Between completed checkpoints, query the public project for newly opened OCR
  compatibility/release issues. If a newer stable OCR appears, qualify its
  complete adjacent chain and include required contract/rules adaptations in
  0.5.0 before the next pending full OCR review.
- Keep completed implementation slices as local checkpoint commits with tests,
  self-review, documentation, and release-issue monitoring. Do not push each
  checkpoint or retrigger PR checks; update feature PR #77 once, only after all
  M2 implementation, installed-artifact E2E, both authorized OCR review cycles,
  and final local validation are complete.
- Before that single push, partially rewrite the unpublished feature history
  into several signed functional slices. Absorb plan-only and fixup commits into
  the implementation they describe rather than making one monolithic squash.
  Prove the corrected tree is unchanged by the rewrite, refresh recorded commit
  identities, scan the complete rewritten first-parent range, and update the
  existing draft branch once with `--force-with-lease`.
- After deterministic remediation of the final OCR findings, make framework
  support one behavior-preserving structural slice under
  `ocr_toolkit.evidence.frameworks`. Separate plugin contracts, generic package
  detection, package-owned ecosystem provider declarations, template inventory,
  closed schemas, and the static registry; remove the old flat framework modules
  without compatibility shims. Do not create competing `frameworks/` and
  `plugins/` trees, move core Git/tree/manifest collection or MCP lifecycle into
  the package, or change evidence schemas and public behavior in that slice.
- M2 component scoping may make a clean 0.5.0 schema-semantic change without
  preserving branch-only legacy behavior. Use `.` as the canonical repository-root
  component and treat `repository` as an ordinary real top-level directory; update
  facts, coverage, deltas, MCP filters, tests, and durable documentation atomically.
  Raise any affected closed schema version when its serialized meaning changes, and
  do not add aliases, projections, or compatibility shims.
- After remediating the additional OCR findings, make normalized source parsers
  one separate behavior-preserving structural slice under
  `ocr_toolkit.evidence.ecosystems`. Keep common manifest contracts plus Python,
  JavaScript, Go, and PHP adapters there; place Ansible Galaxy requirements and
  topology/inventory analysis under `ecosystems.ansible`. This package remains
  below `frameworks`: it parses bounded immutable blobs into normalized facts
  and source coverage, while framework plugins derive higher-level evidence.
  Keep Git/tree orchestration in `collectors.py`, cross-ecosystem container/CI
  extraction in `infrastructure.py`, and store/MCP lifecycle outside both
  packages. Remove old flat parser modules without compatibility shims and make
  no schema or behavior change in the structural slice.

### Work Queue

1. [x] Reconcile the externally completed 0.4.7 starting point, create the M2
   branch and draft feature PR #77, activate release-required 0.5.0 planning,
   and set the next development line to 0.5.0.
2. [x] Repair issue #76 draft-Release identity, canonical issue-comment
   newline, and idempotent skipped-publisher recovery with synthetic tests.
3. [x] Implement the bounded static plugin protocol, manifest-root components,
   closed framework/template records, limits, coverage, and MCP/store contracts.
4. [x] Implement Jinja2 dependency and Jinja/Ansible-template evidence plus the
   additive Jinja rules pack.
5. [x] Implement direct Echo/Fiber evidence and conservative related gRPC data.
6. [x] Implement Symfony/Twig dependency, configuration, template, and rules
   evidence.
7. [x] Implement React/Next framework evidence with TypeScript/Vite related
   signals and npm/Yarn/pnpm resolution.
8. [x] Qualify OCR 1.9.2 against 1.9.1 through canonical issue #78,
   preserve checksum/source/probe evidence, classify every upstream change,
   update tested/recommended pins and contracts, and use 1.9.2 thereafter.
9. [x] Complete cross-provider deltas, coverage, bootstrap/MCP projections,
   documentation, strategy, roadmap, backlog, and current milestone
   reconciliation. The roadmap remains honestly in progress until installed
   E2E, final review, and stable delivery; conditional future packs no longer
   block M2 closure.
10. [x] Run complete Python 3.12-3.14, security, privacy, package, installed
    artifact, rules-preview, real-MCP-client, and synthetic no-post E2E gates.
11. [x] Finish deterministic remediation of the first full OCR review, complete
    and prove the behavior-preserving framework package reorganization, then run
    the complete deterministic package/E2E/privacy validation without OCR.
12. [ ] Remediate the completed owner-authorized additional OCR review, audit
    sibling boundaries, and complete the separate `evidence.ecosystems` source-
    adapter reorganization. Repeat deterministic validation without another OCR
    run, then finish Gitleaks, self-review, feature PR checks/threads, merge, and
    TestPyPI development readback.
13. [ ] Prepare the final release PR as the last repository mutation, archive
    completed 0.4.7 history, consume fragments 76, 77, and 78, and reconcile M2
    to implemented truth while leaving external publication pending.
14. [ ] Complete stable 0.5.0 TestPyPI/PyPI, provenance/hash/tag/immutable
    Release/receipt/Python-install readback and close #76 and #78 as completed
    without another repository PR.

### Issue #76 Checkpoint

- Stable delivery now retains a validated numeric GitHub Release ID from draft
  creation/discovery through asset upload and publication. A bounded,
  redirect-free helper uses closed GitHub API and upload endpoints, exact
  metadata, unique asset names, regular-file/size checks, and fails closed for
  duplicate, partial, mismatched, or published-but-incomplete states.
- The final Release job uses an explicit `always()` success matrix over its
  direct authorization, build, and registry-verification prerequisites, so
  idempotently skipped registry publishers cannot suppress final immutable
  Release and issue closure work while failed or cancelled verification still
  blocks it.
- Issue receipts now have one canonical representation ending in exactly one
  newline. `--body-output` writes that exact representation and bot-comment
  readback compares it byte-for-byte without accepting altered whitespace,
  ownership, marker, version, issue, or hash.
- Focused release authorization/receipt tests pass, including numeric identity,
  duplicate/mismatched metadata, canonical comment-file bytes, bounded API
  allowlists, exact recovery workflow structure, and completed issue closure.
  Durable release documentation now records the numeric-draft boundary.

### OCR 1.9.2 Qualification Checkpoint

- Hosted workflow `31571999318` verified every published release asset against
  GitHub digest metadata and `sha256sum.txt`, then passed Linux version, CLI,
  JSON preview, full-review result, additive-thinking, and posting-consumer
  probes. Canonical issue #78 records the human-review-required lane.
- Adjacent source review found that the tags diverge only because the retry
  documentation commit was reapplied on the 1.9.2 line; both commits have the
  same stable patch ID, so no 1.9.1 runtime behavior was dropped. The effective
  rules/file-extension set and Go MCP SDK remain unchanged.
- The only toolkit-consumed source change corrects OCR directory-only gitignore
  matching for ancestor, glob, and root-anchor semantics. It is a compatible
  file-selection fix and requires no toolkit runtime adaptation. New built-in
  LLM providers, Pages/viewer changes, Action pinning, skill/retry/agent
  documentation, and upstream CI are release-note-only context for this
  toolkit. No future backlog item is activated.
- Compatibility evidence, recommended/tested manifest state, runtime preflight,
  and the checksum-pinned synthetic CI example now target 1.9.2. General user
  documentation refers to the compatibility manifest instead of duplicating a
  patch number; promotion automation no longer rewrites those durable pages.
- The official Darwin arm64 binary was installed atomically only after its
  published size and SHA-256 matched both release metadata and the checksum
  file. Installed-path readback and local deterministic contract probes pass.
  Final focused validation passes 148 tests plus 15 subtests; full quality
  passes 635 tests plus 85 subtests at 79.77% coverage with Ruff, mypy, and
  Bandit. Workflow YAML, Towncrier draft, manifest linkage, changed-public-file
  privacy scan, and `git diff --check` pass. Issue #78 remains open until
  protected 0.5.0 delivery and immutable release readback, alongside issue #76.

### Framework Plugins And Template Review Checkpoint

- A static package-owned plugin registry now interprets existing immutable
  Python, Go, Composer, npm, Yarn, and pnpm evidence without giving plugins Git,
  filesystem, subprocess, network, mutation, or MCP lifecycle capabilities.
  Jinja2, Echo/Fiber, Symfony/Twig, and React/Next are direct-declaration
  providers; gRPC, TypeScript, and Vite are bounded direct related signals.
- New closed `framework.detected` and `template.file` records preserve semantic
  component identity while versions, configuration paths, template object IDs,
  and related signals remain delta values. Nested schemas are revalidated on
  hostile store load; shared store limits, redaction, coverage, base/head
  deltas, and existing MCP summary/list/get projection remain authoritative.
- Jinja `.j2`/`.jinja`/`.jinja2`, extensionless conventional Ansible-role
  templates, and Twig `.twig` files are inventoried without persisting or
  rendering content. The public synthetic rules pack adds explicit additive
  includes and ordered merged Jinja/Twig guidance; direct OCR rules and
  preview probes select root, nested, role, and Twig paths that were previously
  rejected as `unsupported_ext`.
- Focused self-review confirmed lock/checksum-only packages do not activate a
  framework, components follow the nearest manifest or conventional role root,
  and the MCP requires no new server or tool. Follow-up hardening now records
  exact supported-source states, treats direct/effectively replaced `go.mod`
  versions correctly, isolates every package-owned provider failure, binds
  nested plugin/framework/engine identities, and degrades declaration,
  resolution, configuration, or template coverage on malformed/omitted inputs,
  item/path/fact limits, local replacements, or unsafe object types. Excludes
  retain precedence and ordinary supported files remain reviewable. The focused
  cross-provider suite passes 75 tests; its dedicated plugin suite passes 10,
  while focused Ruff and strict mypy pass. Public configuration, GitLab, and
  strategy documentation describe the implemented boundaries, degradation, and
  review-selection behavior.

### Cross-provider Delta And MCP Projection Checkpoint

- The shared evidence MCP now exposes already-collected base/head changes as a
  first-class `repository.evidence_delta` projection. `delta_kind` narrows the
  original fact domain, ordinary unfiltered lists remain backward compatible,
  and stable delta IDs support the existing `get` action without adding a tool,
  server, plugin-owned lifecycle, filesystem access, or network access.
- Delta values and metadata are recursively re-redacted, re-bounded, validated
  against the closed evidence-kind vocabulary, deduplicated after normalization,
  and only then assigned content-addressed IDs. Persisted delta objects reject
  unknown fields and over-limit collections. The collector derives typed deltas
  from canonical records actually accepted by the store, so rejected, omitted,
  deduplicated, or redaction-equivalent facts cannot leave dangling changes.
- A synthetic multi-ecosystem contract exercises Jinja2 templates, Go web
  providers, Symfony/Twig, and React/Next together. It proves framework and
  template additions, removals, and changes; scoped-completeness transitions;
  summary and filtered list/get projection for facts, coverage, and deltas; and
  compact-bootstrap orientation without embedding detailed paths or versions.
- Durable architecture, configuration, security, roadmap, and backlog text now
  describes the implemented shared projection. Completed BL-008 and BL-009
  scope is removed from future work; demand-triggered evidence packs remain a
  separate conditional item and do not keep M2 permanently open. The roadmap
  keeps M2 in progress until installed-artifact E2E, the authorized local OCR
  review cycles, and independently verified stable delivery complete its signal.
- Focused evidence, MCP, model, repository, documentation, and integration
  validation passes. The complete routine quality gate passes 651 tests plus 85
  subtests at 79.96% coverage with formatting, Ruff, strict mypy, and the
  medium-confidence/medium-severity Bandit gate clean. Towncrier draft,
  changed-public-file privacy scan, issue monitoring, and `git diff --check`
  pass. Full release-grade installed-artifact validation remains next.

### Release-grade Installed-artifact E2E Checkpoint

- Full tests pass independently on every supported Python interpreter. Gitleaks
  over the unpublished feature range, dependency audit, OCR compatibility
  manifest validation, changed-shell ShellCheck, and the existing privacy gate
  pass without relying on hosted PR checks.
- Two target-version builds are byte-identical. Twine and closed archive-content
  inspection confirm a runtime-only wheel, the intentionally minimal sdist,
  zero runtime dependencies, and the supported-Python contract. The wheel
  SHA-256 is `b713676d47b4c9b8615e6bb81216b4ab1e2133ccd750e793401417b92e565056`;
  the sdist SHA-256 is
  `baab422d378caaaa17487ab7bb5d31b3478144bfadf4212b7f71d6baf918eded`.
- Hash-locked wheel installs pass on the lower and intermediate supported
  interpreters, and a hash-locked sdist build/install passes on the upper
  interpreter. Each clean environment passes `pip check`, imports the exact
  target development version from site-packages under isolated mode despite a
  hostile repository-local shadow package, and runs the installed `ocr-ci`
  entry point with a restricted `PATH`.
- A real installed subprocess follows the generated mandatory MCP command and
  completes initialize, initialized notification, ping, tool discovery,
  summary, fact list/get, coverage list, and framework-delta list/get. Stable
  fact and delta IDs, read-only annotations, exact installed server version,
  private artifact modes, and the public page-size boundary are verified.
- OCR rules preview with the qualified binary selects root and nested Jinja,
  Twig, and extensionless conventional Ansible-role templates without an
  unsupported-extension result or a preview session side effect.
- The installed-wheel synthetic OCR E2E runs in a read-only Linux container
  with no network, using only loopback HTTPS, a process-local CA, the
  checksum-qualified OCR binary, public rules, and synthetic multi-ecosystem
  history. The review completes with two real `ocr_toolkit_evidence` calls:
  summary followed by a filtered framework-delta query. The toolkit receipt
  matches OCR counters; Jinja2, Echo/Fiber, Symfony/Twig, React/Next,
  TypeScript/Vite, templates, scoped completeness, and semantic deltas are
  present; private modes and a clean Git status are preserved; no posting path
  is invoked.
- Read-only checkpoint monitoring still finds only issues #76 and #78 open, and
  the latest upstream stable OCR remains the already qualified 1.9.2. No push
  was made. The first full local review described below has since run; the next
  authorized OCR action is the additional concurrency-2 review only after the
  current remediation and complete deterministic validation finish.

### Additional OCR Review Remediation Checkpoint

- The owner-authorized additional full OCR review completed successfully over
  exact range `3caa50b4fc5026da79c7f2ceae1deef31715f814..4fe85549d66acd9fba57fb2ad39cf173b4d91053`
  with checksum-qualified OCR 1.9.2, configured concurrency 2, the public rules
  pack, and exact-HEAD installed wheel version `0.5.0.dev0+g4fe85549`.
- All selected items completed with no failed or waived coverage. The result has
  terminal state `complete`, contains eight findings, and records 113 mandatory
  `ocr_toolkit_evidence` calls; the toolkit receipt matches the OCR counter.
  Evidence base/head refs and the result manifest both match the requested exact
  range. No further OCR rerun is authorized.
- The review used an isolated owner-only HOME, only the built-in evidence MCP,
  and an environment with GitLab token variables removed. No posting command was
  invoked. Result, stderr, bootstrap, store, config, and receipts are ignored,
  owner-only private artifacts; private-marker and posting scans are clean, and
  the tracked worktree remained unchanged.
- All review findings now have focused regressions that first failed at the
  reported boundary and pass after deterministic correction. Release creation
  validates protected identity before discovery or mutation and checks the first
  page outside its bounded scan. Arbitrary Python requirement includes receive
  exact source status. Framework scoping uses `.` for the root and ordinary paths
  for every named directory, including MCP fact/delta filters. Provider output is
  bounded and admitted atomically; template-limit coverage is emitted once per
  scope; manifest scalars use field-specific bounds; persisted plugin schemas are
  validated after redaction and total-value bounding.
- Sibling audits covered other bounded GitHub pagination, all framework component
  consumers, provider facts/coverage/notices, path versus manifest-scalar limits,
  and every store reload path. The focused release/evidence suites pass. The root
  semantic is a clean unreleased 0.5.0 contract change, not a compatibility shim;
  nested fact schema versions remain unchanged because component lives in the
  common evidence envelope and its closed shape did not change.
- After this remediation checkpoint, complete the separately bounded
  `evidence.ecosystems` structural slice described in Decisions. It is not part
  of `frameworks`: manifest and Ansible source adapters feed normalized evidence
  into the higher framework layer. Deterministic validation follows both slices
  and OCR will not be run again.

### Pre-additional-review Deterministic Validation Checkpoint

- Signed local checkpoint `1f64c8a112c54df289649fcbc0d06ef9f91dbe84`
  is the exact validated tree; its signature, clean worktree, and ancestry from
  stable 0.4.7 are verified. No branch push occurred.
- Routine formatting, Ruff, strict mypy, Bandit, branch coverage, and the full
  test suite pass. Independent full test runs pass on each supported Python
  interpreter. Complete first-parent Gitleaks and dependency audit are clean.
- Two target-version builds are byte-identical and pass Twine plus closed wheel
  and sdist inspection. The wheel contains the framework package/provider
  layout, omits the removed flat modules, and retains zero runtime dependencies.
  Hash-locked wheel installs on the lower and intermediate supported Python
  versions and a hash-locked sdist install on the upper version pass `pip check`,
  exact-version import, hostile-shadow isolation, restricted-`PATH` CLI smoke,
  and private permissions.
- The installed artifact collects a private synthetic multi-ecosystem base/head
  store and serves it through a real stdio MCP process. Initialize, initialized,
  ping, tool discovery, summary, filtered framework fact/list/get, and filtered
  framework delta/list/get all pass with read-only annotations, exact installed
  server version, framework/template facts, scoped coverage, and semantic deltas.
- The effective OCR binary remains checksum-qualified 1.9.2. Its JSON preview
  selects root and nested Jinja, Twig, and extensionless conventional role
  templates alongside an ordinary supported file, reports no unsupported
  extension, and creates no session store.
- Towncrier draft, OCR compatibility manifest, lockfile, complete-range source
  integrity, changed-public-content privacy, tracked-artifact exclusion,
  `git diff --check`, and private receipt modes pass. Work Queue item 12 and the
  owner-authorized additional full OCR review with concurrency 2 are now the
  only next review-stage actions.

### First Full OCR Review And Remediation Checkpoint

- The first full local OCR review ran once over exact range
  `3caa50b4fc5026da79c7f2ceae1deef31715f814..69a44f7efb053ff11cfc28da1ae910e8f34a8d0b`
  with the checksum-qualified OCR 1.9.2 binary through an exact-HEAD installed
  wheel. No GitLab posting command or credential was used. Private result,
  stderr, bootstrap, and evidence artifacts retain owner-only permissions and
  the ignored review context is absent from the tracked range.
- OCR completed most selected items and stopped two evidence modules at its
  tool-round budget. The accepted partial result contains eight findings and
  records 261 mandatory `ocr_toolkit_evidence` calls; the toolkit-authored
  receipt matches that counter and persisted evidence is bound to the exact
  reviewed refs. The original no-rerun rule was honored until the owner
  explicitly authorized one additional full review on 2026-08-12.
- Deterministic remediation is complete for every reported defect class.
  Release notes, assets, and issue evidence are read through validated stable
  descriptors; manifest include degradation reaches only affected roots; plugin
  kinds remain closed; Go replacements obey source-version applicability and
  exact replacements outrank package-wide fallbacks; bounded store omissions do
  not become hard validation errors; truncation fixtures are order-independent;
  and subprocess tests use the active interpreter.
- The sibling-boundary audit covered the parallel release-receipt reader,
  Python and Ansible include graphs, replacement precedence, store exception
  hierarchy, and the built-in MCP delta/query path. Manual review of the two
  budget-stopped evidence modules found no additional MCP lifecycle or generic
  detector defect requiring a change.
- Framework support now has one internal `ocr_toolkit.evidence.frameworks`
  ownership package. Immutable contracts, the closed schema, generic detection,
  template inventory, static registry, and ecosystem provider declarations are
  separate modules; core Git/tree/manifest collection, storage, and MCP serving
  remain outside. The old flat modules are absent without compatibility shims.
  An architecture contract rejects provider I/O and dynamic discovery, locks
  immutable context fields and provider order, and keeps Jinja2 first.
- Focused regression, full routine quality/security, and every supported-Python
  test run pass. Built-wheel inspection proves the new package layout, old-module
  absence, unchanged schema versions/provider order, zero runtime dependencies,
  and isolated installed import/CLI behavior. Towncrier draft, OCR compatibility
  manifest, lockfile, public-content privacy scan, and `git diff --check` pass.
  Work Queue item 11 remains open until the exact committed tree completes the
  full reproducible package, installed-artifact/MCP/E2E, and privacy gates.

### Initial Evidence

- Clean synchronized `main` was exact annotated tag `v0.4.7` at
  `3caa50b4fc5026da79c7f2ceae1deef31715f814`; stable 0.4.7 is externally
  complete, while the retained plan below still records its former pending
  pre-publication state.
- The recommended OCR resolves a custom Jinja rule but excludes `.j2` as
  `unsupported_ext`; adding an explicit `include` pattern makes preview select
  it. `.j2`, `.jinja`, `.jinja2`, and `.twig` are absent from its built-in
  extension allowlist.
- Existing dependency parsers already expose direct declarations and lock facts
  for Python, Go, Composer, npm, Yarn, and pnpm. M2 adds interpretation,
  component scoping, template inventory, explicit completeness, and review
  selection rather than duplicating those parsers.
- Draft feature PR #77 supplies the real Towncrier identifier for M2 feature
  and rules fragments. Canonical OCR 1.9.2 qualification issue #78 is open and
  already contains passing hosted checksum/contract evidence; issue #76 and #78
  remain open until immutable stable delivery.

## Recently Completed Plan: Harden GitLab suggestions and add SHA-bound approval for 0.4.7

Status: completed; stable 0.4.7 externally delivered and independently read back
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
  metadata cannot be proven. Keep the transaction add-only: GitLab cannot bind
  unapproval to the reviewed SHA at mutation time, so ineligible or disabled
  later reviews preserve every existing approval.
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
   synchronization/write/readback, add-only provider semantics, documentation,
   complete regressions, review, and the #71 checkpoint commit. The original
   managed-unapproval design was removed after final OCR found that GitLab
   cannot provide the required mutation-time immutable guard.
3. [x] Replace the redundant post-release closure-PR contract with exact-tree
   release authorization and deterministic `ocr-toolkit.release-receipt/v1`
   evidence; update durable rules, recovery behavior, tests, and the lifecycle
   checkpoint commit.
4. [x] Inspect authoritative OCR 1.9.0 and 1.9.1 release notes and source
   changes, record separate consumed-contract/backlog/no-impact
   classifications and qualification issues, update compatibility records and
   the local checksum-pinned OCR 1.9.1 binary, and adapt the toolkit only where
   evidence requires it.
5. [x] Reconcile this plan, roadmap table/diagram, backlog, and current-state
   documentation against the implemented code. Run focused tests, the synthetic
   GitLab E2E, Python 3.12 quality, Towncrier draft, workflow/document/privacy
   checks, and `git diff --check`.
6. [x] Commit the complete feature tip and run one local toolkit-owned OCR review
   with private result/stderr artifacts, no GitLab posting, and verified nonzero
   built-in MCP use. Correct its findings, complete deterministic validation and
   final self-review, and do not run a second OCR or Codex Security review.
7. [x] Run deterministic post-review validation and pinned local Gitleaks over
   the unpublished history, push the exact reviewed branch, open one feature PR,
   resolve every conversation, pass protected checks, and squash-merge.
8. [x] Independently verify the exact TestPyPI development artifacts, hashes,
   provenance, and supported-Python installs before preparing `release/v0.4.7`.
9. [ ] Prepare and validate the final release PR, consuming fragments 69, 70,
   71, 72, and 73 and reconciling repository-side planning truth without
   claiming publication that has not happened.
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
  submits only the reviewed 40-hex SHA. Approve and summary-update writes are
  attempted once and followed by bounded readback.
- Approval is add-only. An already approved toolkit user is reported as skipped
  without a provider write; ineligible, partial, skipped, legacy, disabled, and
  ambiguous runs also make no approval write. The adapter exposes no unapprove
  operation or managed-approval receipt because GitLab cannot bind unapproval to
  the immutable reviewed SHA at mutation time. Project-owned reset and
  invalidation rules remain authoritative.
- The published summary contains one bounded approval state. Eligible runs first
  publish a conservative failed-until-confirmed state, then update the uniquely
  marked owned summary once after provider readback. Failure never rolls back the
  advisory review; strict mode returns nonzero while advisory mode remains
  nonfatal. Existing GitLab rules, groups, Code Owners, protected branches, and
  reauthentication stay authoritative.
- Self-review fixed version-order assumptions, different-SHA approval claims,
  and provisional-summary truth. The final OCR correction subsequently removed
  the unsafe managed-unapproval design and its receipt surface entirely. Ruff
  and strict mypy pass; 148 posting/approval/suggestion tests and 15 public
  documentation/integration contracts pass. Towncrier 0.4.7 draft includes the
  default-on write and opt-out, and `git diff --check` passes. Roadmap and future
  backlog statuses remain unchanged because neither issue completes an existing
  outcome milestone or activation trigger.

### Release Lifecycle Checkpoint

- The merged release PR is now the final repository mutation without claiming
  future delivery. Authorization executes from the protected reviewed base that
  predates the release candidate, treats candidate head and merge commits as
  bounded data, validates tracked metadata from the exact merge ref, proves
  squash-tree equivalence and parent identity, and requires every live strict
  `main` check context from its exact GitHub App on the reviewed head SHA.
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

### Final OCR Review And Correction Checkpoint

- The only final local OCR review covered
  `bb8827148f13b17b209495788ac4f7b15573a168..fe88f8d78744847bc58b35129de5c9130cd46853`
  with official OCR 1.9.1. It completed all 23 selected items in 39 minutes 5
  seconds with zero failed or waived items, returned 16 findings, and made 68
  mandatory `ocr_toolkit_evidence` calls. The private toolkit receipt records
  the same 68 calls; result/stderr and `.review-context` artifacts retain owner-
  only permissions, `.review-context` is absent from the reviewed diff, and no
  GitLab posting command ran.
- Thirteen findings exposed valid boundary defects or the same root-cause
  classes. Release authorization now executes from the protected pre-candidate
  base. The GitHub API helper has a closed endpoint grammar, redirect-safe
  bearer authentication, private same-directory temporary output, allowed-
  status validation, and atomic replacement. Minor/major OCR promotion requires
  chain-aware schema 2. Stable receipts reject unknown top-level and nested
  fields; malformed registry provenance URLs fail closed; unhashable finding
  categories degrade to not eligible; complete unified-diff replacements are
  rejected; and unused approval-receipt parsing was removed.
- The two unapproval findings and the approval-without-durable-receipt finding
  shared one architectural cause: GitLab's unapprove endpoint cannot receive the
  reviewed SHA, so preflight and readback cannot close its destructive TOCTOU
  gap. Automatic approval is therefore add-only. All unapproval and managed-
  receipt runtime paths were removed instead of adding another compensating
  state machine.
- Three suggestions were rejected after source and regression review. Python's
  `binascii.Error` is already a `ValueError`, so existing malformed-base64
  handling covers both flagged decode sites. A user-authored exact issue-receipt
  marker intentionally blocks closure as the documented anti-preemption,
  fail-closed contract; it is not trusted as a successful receipt.
- Root-cause sibling audits covered URL parsers, release/security receipt
  loaders, bounded HTTP helpers, and destructive provider writes. Public
  approval/release/security documentation and `AGENTS.md`, project principles,
  and execution pitfalls now encode the corrected boundaries. A direct
  regression proves that schema-1 evidence cannot cross minor or major OCR
  boundaries. No second OCR review or Codex Security run will be performed.
- The final post-correction gate runs from isolated Python 3.12.13 and passes
  formatting, Ruff, strict mypy, Bandit with zero medium/high findings, 623
  tests plus 85 subtests, and 79.09% coverage. OCR manifest validation,
  Towncrier 0.4.7 draft, changed-shell ShellCheck, workflow YAML parsing,
  changed-public-content privacy checks across 31 files, and `git diff --check`
  pass. Fresh `0.4.7.dev7` wheel and sdist pass Twine, canonical composition,
  centralized SCM-version, zero-runtime-dependency, and Python `>=3.12,<3.15`
  metadata checks. Separate Python 3.12 installs pass `pip check` and execute
  the installed CLI/import under restricted `PATH` from a hostile shadow-package
  working directory. Wheel SHA-256 is
  `0582f8b1ed7623cec55aaeef289bde7d9ccda9c1b9b856d30eacb95e57508ac6`;
  sdist SHA-256 is
  `4bdcfc1a302e1f7392623b2c651bf8d747e8228891b74f14257479e8ab93dee6`.
- Final manual self-review removed the obsolete `ApprovalResult.managed` flag,
  confirmed every workflow-used GitHub endpoint is represented by the closed
  helper grammar, verified recovery binds the protected reviewed base, and
  found no roadmap, backlog, or narrative status tail. Exactly one worktree is
  present and all review/quality artifacts remain ignored and private.

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

### Feature-tip Validation And E2E Checkpoint

- The signed `4f3dd29` tree builds on Python 3.12.13 as
  `0.4.7.dev6+g4f3dd2994`. Twine accepts both distributions; the wheel SHA-256
  is `295c0e9fa52492aa9e99c7dd11ae0b3a2b2c6339f3e4991ea3009e29812ed358`
  and the sdist SHA-256 is
  `c679d9490f8cb1fb58f37bac4eba24dcad52fb745814121523c2841a15096c55`.
  Metadata derives the version from SCM, requires Python 3.12 through 3.14,
  declares no runtime dependencies, and both archives contain only their
  intended package/source surfaces.
- Separate clean Python 3.12 wheel and hash-locked sdist installs pass
  `pip check`, import the same centralized version, and run the installed
  `ocr-ci --help` entry point under a restricted `PATH` from a repository that
  contains a hostile local `ocr_toolkit` shadow package. The installed artifact,
  rather than checkout code or the untrusted current directory, owns execution.
- One ignored, one-off synthetic repository E2E uses the installed wheel and the
  official local OCR 1.9.1 binary without adding a permanent harness. A local
  deterministic gateway forces OCR to query `ocr_toolkit_evidence` before it
  emits one synthetic finding. OCR finishes with `status=complete` and one
  built-in evidence call; `_ocr_toolkit.mcp_usage` records the same count. The
  exact base/head snapshots match the reviewed commits, `.review-context` is
  absent from Git status and the reviewed diff, its directory is `0700`, all
  store/bootstrap/result/stderr artifacts are `0600`, and no GitLab posting
  command is invoked.
- The complete posting/suggestion/approval/release/compatibility changed-surface
  suite passes 347 tests plus 73 subtests. The full gate executed directly from
  Python 3.12.13 passes 622 tests plus 81 subtests at 79.61% coverage; formatting,
  Ruff, strict mypy, Bandit, changed-shell ShellCheck, workflow YAML parsing,
  OCR manifest validation, Towncrier 0.4.7 draft, changed-public-content privacy,
  and `git diff --check` pass.
- Read-only validation against current public service payloads confirms that
  PyPI Integrity v1 uses the publisher and in-toto subject shape enforced by the
  release verifier, GitHub exposes strict effective `main` checks with exact App
  integration IDs, and immutable Release state is available through the pinned
  API version. No registry, Release, issue, or GitLab state was changed.
- Final reconciliation found no roadmap table/diagram, strategy, or backlog
  status transition: #70/#71 are release-scoped behavior rather than an outcome
  milestone, while OCR 1.9.0/1.9.1 inputs leave BL-008/009/010/015/016/017 at
  their documented triggers. Self-review corrected the release queue to consume
  all five fragments 69-73; every tracked issue remains open until stable 0.4.7
  delivery is proven by the immutable receipt and independent readback.

### Feature Merge And Development Publication

- Feature PR #74 was read back as exact head
  `2f63d250cb47ab3c7bcc174514949f7bb2d6e044` over base
  `bb8827148f13b17b209495788ac4f7b15573a168`, with zero comments, reviews, or
  review threads. All 13 exact-head required checks passed from their required
  App integration IDs before squash merge. The GitHub-verified merge
  `0534c54c7f00b5e391fd6a85d9fee41aaa6c1d70` has the reviewed head tree
  `9ff900ab33d3485cb4d6aadd0c88fe180e4a708b` and exact protected base as its
  only parent. The feature branch was deleted locally and remotely.
- TestPyPI run `31478171014` completed successfully for that exact merge and
  published immutable `0.4.7.dev45`. Cache-bypassed PEP 691 reads, freshly
  downloaded registry bytes, and Actions artifact `9096110238` are
  byte-identical: wheel SHA-256
  `e7aa351d30ae6da865e249ec353ebef2c4a2ba6eb2365370df86aa247d0116c9`;
  sdist SHA-256
  `ed05585e4d8c3104641a2309e830fad1738043c2fa1343febe0ceff9e559e251`.
  The Actions archive digest is
  `91018933dff03e8ad97fe5e814ab06776a9d246198bab3c68ae32bc8fa7e5fb2`.
- Independent PyPI Integrity reads bind both exact subjects to repository
  `xeonvs/open-code-review-toolkit`, workflow `testpypi.yml`, and environment
  `testpypi-public-disclosure`. Registry wheel installs pass on Python 3.12 and
  3.13; the registry sdist installs on Python 3.14. All three pass `pip check`,
  exact runtime-version import, and restricted-`PATH` CLI smoke from a hostile
  shadow-package working directory.
- The final release PR is the last repository mutation. It archives the complete
  externally reconciled 0.4.6 cycles under stable-tag anchors, consumes exactly
  fragments 69-73, records authorization metadata for issues 70-73, and lists
  stable registry, provenance, tag, immutable Release, receipt, install, and
  issue-closure checks as pending. Roadmap, strategy, and backlog statuses remain
  unchanged after another code-first reconciliation.

### Release Preparation Review Checkpoint

- The release branch starts from exact feature merge
  `0534c54c7f00b5e391fd6a85d9fee41aaa6c1d70`. Its tracked authorization
  metadata names stable 0.4.7 and the sorted issue set 70-73; stable and next
  version markers are 0.4.7 and 0.4.8, and deterministic epoch `1786440757` is
  exactly one second after the feature merge. Towncrier consumed only fragments
  69-73, and the generated release notes end with the exact
  `v0.4.6...v0.4.7` comparison.
- The previously retained 0.4.6 plans moved into the stable-tag archive without
  rewriting their plan text. Explicit anchors resolve from the execution-history
  index, and roadmap, strategy, README, and backlog review found no status or
  narrative change justified by this repository-only release preparation.
- The release-focused suite passes 137 tests plus 15 subtests. The complete
  isolated Python 3.12 gate passes formatting, Ruff, strict mypy, Bandit with
  zero medium/high findings, 623 tests plus 85 subtests, and 79.09% coverage.
  OCR manifest validation, workflow YAML parsing, changed-shell ShellCheck,
  release-note extraction, metadata/archive checks, and `git diff --check`
  pass. `pip-audit --skip-editable` reports no known dependency vulnerabilities.
- Two clean source-date-epoch-controlled stable builds are byte-identical and
  pass Twine, canonical archive composition, centralized SCM-version, zero
  runtime dependency, and Python `>=3.12,<3.15` metadata checks. Wheel SHA-256
  is `15c86588987fd441aebf7a43235571e2d14f789aa7a8e1f59cbd24ce113978b2`;
  sdist SHA-256 is
  `5ad2563c9cfc4e6fc9da95d425df44c5e53e62de05ddad462eeda0b41626ac6a`.
  Restricted-`PATH` hostile-shadow installs pass for the wheel on Python 3.12
  and 3.13 and the sdist on Python 3.14, including exact runtime version, CLI,
  and `pip check` readback.
- Stable TestPyPI/PyPI bytes, Integrity provenance, GitHub attestations, the
  annotated tag, immutable Release and exact asset set, release receipt,
  published-artifact installs, and issue receipt/closure remain external
  post-merge gates. None is represented as complete in this release PR, and no
  later repository closure PR is planned.
