# Execution Plans

Use this file for active, blocked, or recently completed execution work. Update it before implementation and before handoff or commit. Older completed plans are indexed in [the execution-history archive](docs/engineering/execution_history/README.md).

## Recently Completed Plan: M2 ecosystem and framework coverage for 0.5.0

Status: completed; stable 0.5.0 delivery and external reconciliation verified
Owner: Codex
Last Updated: 2026-08-13
Release Classification: release-required
Target Stable Version: 0.5.0
Closure Reconciliation: no-release
Closure Target Stable Version: N/A
Tracking Issues: #76, #78 (OCR 1.9.2); feature PR #77; release PR #79

### Goal

Deliver M2 as stable toolkit 0.5.0 with bounded static framework plugins for
Jinja2, Go web frameworks, Symfony/PHP, and React/TypeScript. Make Jinja and
Twig template files actually reviewable by the recommended OCR through the
public synthetic rules pack, expose framework/template state and deltas through
the existing read-only evidence MCP, repair issue #76 release recovery, and
qualify checksum-pinned OCR 1.9.2 through issue #78 before final validation.
The implementation, installed-artifact E2E, both owner-authorized local OCR
review cycles, deterministic remediation, package reorganizations, protected
feature and release merges, stable publication, immutable evidence, issue
closure, and M2 external reconciliation are complete. This documentation-only
reconciliation records that externally verified outcome without changing the
package or publishing another artifact.

### Decisions

- The M2 lifecycle was release-required with target 0.5.0 and remained active
  through feature and release PRs, registry publication, provenance, annotated
  tag, immutable Release, receipt, supported-Python installs, and completed
  closure of issues #76 and #78.
- Release PR #79 correctly recorded external publication as pending before its
  merge. The immutable receipt and independent readback now prove stable
  delivery. The present status reconciliation is a no-release documentation
  correction and does not alter the completed release lifecycle.
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
  compatibility/release issues. If a newer stable OCR appears before 0.5.0
  delivery, qualify its complete adjacent chain and include required
  contract/rules adaptations in this release. Do not repeat a full local OCR
  review without separate owner authorization.
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
12. [x] Remediate the completed owner-authorized additional OCR review, audit
    sibling boundaries, complete the separate `evidence.ecosystems` source-
    adapter reorganization, and repeat deterministic package/E2E/privacy
    validation without another OCR run.
13. [x] Partially rewrite unpublished history into logical signed slices, absorb
    plan-only checkpoints into their owning functionality, verify every
    signature, and prove exact final-tree plus complete base-diff equivalence
    before recording the rewritten identities below.
14. [x] Rerun complete-history signature, Gitleaks, privacy, full quality and
    supported-Python gates; reproduce the target-version artifacts; verify
    hash-locked installs, installed MCP, template rules preview, and static
    workflow boundaries; then recheck public OCR release and issue/PR state.
15. [x] Update feature PR #77 once with `--force-with-lease`, read back its exact
    head, finish checks and review threads, merge it, and independently verify
    TestPyPI development delivery.
16. [x] Prepare and locally validate the final release candidate as the last
    repository mutation, archive completed 0.4.7 history, consume fragments 76,
    77, and 78, and reconcile M2 while leaving external publication pending.
17. [x] Push the release branch once, open the exact final release PR, read back
    its head, required checks, and review threads, then squash-merge only after
    every protected gate passes.
18. [x] Complete stable 0.5.0 TestPyPI/PyPI, provenance/hash/tag/immutable
    Release/receipt/Python-install readback and close #76 and #78 as completed
    without another repository PR.

### Stable Delivery And External Reconciliation Checkpoint

- Release PR #79 was read back at reviewed head
  `e3ceda38b28c056a3391492e542c7daf8bfbfc78` and merged as signed commit
  `008f99d8e8b745c19cc7064832890e31d7d8a555`; the merge and reviewed head
  have the same tree. Release workflow `31604133351` completed every
  authorization, build, registry, supported-Python verification, and immutable
  GitHub Release job successfully.
- Stable TestPyPI and PyPI artifacts, provenance, hashes, annotated tag
  `v0.5.0`, and the immutable GitHub Release were independently read back. The
  release receipt SHA-256 is
  `f375762bbac6659d296918b35a2f61155882311659add04310744921feaa293c`.
- Issues #76 and #78 contain the canonical receipt comment and are closed as
  completed. The next scheduled compatibility discovery completed successfully
  with OCR 1.9.2 still current and no newly opened release issue. BL-008 and
  BL-009 are complete; conditional BL-010 remains M6 work and does not block M2.
- M2 is therefore established. This no-release documentation reconciliation
  updates status-bearing sources only; it does not run OCR again, change the
  package version, or publish artifacts. The full 0.5.0 cycle remains here until
  the next release PR archives it under the documented lifecycle rule.

### Feature Merge And Development Publication Checkpoint

- Feature PR #77 was updated once after local consolidation and read back at
  exact reviewed head `a0a9e33ceda170c6339cbcc255b59d3a1538f74e` over stable
  base `3caa50b4fc5026da79c7f2ceae1deef31715f814`. All exact-head hosted checks
  passed, the thread-aware review inventory was empty, and the active `main`
  ruleset required no approving review while enforcing resolved conversations,
  signed linear history, and its complete check set.
- The GitHub-verified squash merge
  `a7d97ff0e0e128f833b1991e4e4af778b2e4fb8f` has the reviewed tree
  `e79bda9bcdbf7d3c3e3c6ab8a98635834aecc524` and stable base as its only
  parent. The remote feature branch was removed and `main` points to that merge.
- TestPyPI development workflow `31601538539` completed for the exact merge and
  published `0.5.0.dev47`. Fresh Simple API downloads are byte-identical to
  Actions artifact `9143315192`: wheel SHA-256
  `e9d8c2520f12efaa4c9ee1d7350bc946d33c1767daf0a86a8172a67d13996ec0` and
  sdist SHA-256
  `b2b6ac96edafeb69cc9cff4942512620cc16534a605435b3e31a17db9b9bf8f1`.
- Independent Integrity reads bind both subjects to repository
  `xeonvs/open-code-review-toolkit`, workflow `testpypi.yml`, and environment
  `testpypi-public-disclosure`. Published wheel installs pass on Python 3.12
  and 3.13 and the sdist on Python 3.14, including exact version, `pip check`,
  isolated import, and restricted-`PATH` CLI smoke.
- The release branch starts from that exact protected merge. It is the final
  repository mutation for this lifecycle; stable registry, provenance,
  attestation, tag, immutable Release, receipt, install, issue-closure, and M2
  roadmap completion signals remain pending and are not claimed by this PR.

### Release Preparation Validation Checkpoint

- The release branch starts from protected feature merge
  `a7d97ff0e0e128f833b1991e4e4af778b2e4fb8f`. Tracked authorization names
  stable 0.5.0 and sorted issues #76 and #78; the next line is 0.5.1, and the
  deterministic source epoch is exactly one second after the feature merge.
  Towncrier consumed only the four release fragments, and generated notes contain
  only the 0.5.0 section plus the exact `v0.4.7...v0.5.0` comparison.
- The externally reconciled 0.4.7 plan moved intact into the release-tag archive;
  its content is byte-identical to the protected feature-merge source, apart from
  the structural separator before the next anchor. Every indexed archive link
  resolves. Roadmap, strategy, README, and backlog reconciliation keeps M2 in
  progress only until independently read-back stable delivery; BL-010 remains
  conditional rather than blocking this release.
- The final release-focused suite passes 100 tests. Complete tests pass on Python 3.12,
  3.13, and 3.14 with 676 tests plus 85 subtests per interpreter; routine format,
  Ruff, strict mypy, Bandit, OCR-manifest, lock, workflow-YAML, ShellCheck, and
  dependency-audit gates pass. The release audit found and fixed one unquoted
  quality-environment export, added its contract regression, and audited every
  tracked shell script for the same class.
- Two source-date-epoch-controlled stable builds are byte-identical and pass
  Twine plus closed archive inspection. Wheel SHA-256 is
  `e3ffcdeb9052dc0dd57909ccb7867d546e11bd4e3bf8f43394896837cd3864d5`;
  sdist SHA-256 is
  `bda676aa0dde70ae73c49cf5a90dd85c46268b257f5f26afff212f6249b94153`.
  Both carry 0.5.0, Python `>=3.12,<3.15`, zero runtime dependencies, the new
  ecosystem/framework layout, and no removed flat modules. Hash-locked wheel
  installs on Python 3.12 and 3.13 plus an sdist install on Python 3.14 pass
  isolated import, hostile shadow, `pip check`, restricted `PATH`, and layout
  probes.
- The installed stable wheel passes the real stdio MCP protocol with the one
  read-only `ocr_toolkit_evidence` tool, including root and named components,
  framework facts, scoped coverage, deltas, Jinja2/Twig templates, and private
  artifacts. Checksum-qualified PATH-effective OCR 1.9.2 selects ordinary,
  Jinja, Twig, and extensionless conventional role-template files in JSON
  preview without an LLM run or session artifact. Changed-content and complete
  tracked-source privacy scans contain no private inventory marker or review
  artifact, and the release diff passes Gitleaks plus `git diff --check`.
- Stable registry bytes, provenance, GitHub attestations, annotated tag,
  immutable Release and complete asset set, release receipt, published installs,
  issue receipts/closure, and final M2 external completion remain post-merge
  gates. This release preparation does not claim any of them.

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
- Read-only checkpoint monitoring found only issues #76 and #78 open, and the
  latest upstream stable OCR remained the already qualified 1.9.2. No push was
  made. The first and additional owner-authorized local review cycles described
  below subsequently completed; no further OCR review is authorized.

### Additional OCR Review Remediation Checkpoint

- The owner-authorized additional full OCR review completed successfully over
  exact range `3caa50b4fc5026da79c7f2ceae1deef31715f814..4fe85549d66acd9fba57fb2ad39cf173b4d91053`
  with checksum-qualified OCR 1.9.2, configured concurrency 2, the public rules
  pack, and exact-HEAD installed wheel version `0.5.0.dev0+g4fe85549`. That
  pre-rewrite head remains the immutable review-receipt identity; rewritten
  signed checkpoint `a05399fd02916493bd516caae313b618becda221` has its exact tree.
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
  and every store reload path. The focused release/evidence suites and complete
  routine quality/security gate pass. Rewritten signed checkpoint
  `b35bb286938d923a29e8c51d87b152e6595e6825` contains the remediation with the
  exact pre-rewrite checkpoint tree and remains unpushed. The root semantic is
  a clean unreleased 0.5.0 contract change, not a compatibility shim; nested fact
  schema versions remain unchanged because component lives in the common evidence
  envelope and its closed shape did not change.
- The separately bounded `evidence.ecosystems` structural slice described in
  Decisions subsequently completed. It remains below `frameworks`: manifest and
  Ansible source adapters feed normalized evidence into the higher framework
  layer. Final deterministic validation covers both slices, and OCR was not run
  again.

### Ecosystem Adapter Package Checkpoint

- Normalized source adapters now form one lower-level
  `ocr_toolkit.evidence.ecosystems` package: shared contracts plus Python,
  JavaScript, Go, and PHP modules, with Galaxy requirements and
  topology/inventory split under `ecosystems.ansible`. Ansible remains an
  automation ecosystem feeding normalized evidence, not a framework provider.
- Git/tree reads, include-graph orchestration, source statuses, and parser
  registration remain in `collectors.py`; cross-ecosystem container/CI facts
  remain in `infrastructure.py`; framework derivation, store, and MCP remain
  higher independent layers. The old flat parser modules are absent without
  aliases or compatibility shims.
- An architecture contract locks the exact package layout and rejects adapter
  I/O, dynamic imports, and upward dependencies on collectors, frameworks,
  repository plumbing, store, or MCP. Parser, collector, framework, repository,
  model, and MCP suites pass, and a clean wheel-content test proves the package
  layout and absence of old modules. No evidence schema or parser behavior
  changed in this structural slice.

### Unpublished History Consolidation Checkpoint

- The unpublished range after the existing remote feature tip was consolidated
  into several coherent signed functional slices. Plan-only installed-E2E,
  pre-review, and final-validation commits were absorbed into the MCP,
  framework-remediation, and ecosystem slices they describe; the OCR
  qualification and additional-remediation slices remain distinct.
- A private owner-only pre-rewrite receipt and backup ref preserve the old tip.
  Before this metadata reconciliation, the rewritten tip had the same exact Git
  tree and binary diff from the remote tip as the validated pre-rewrite tip; a
  fixed-mtime archive of that tree was byte-identical. Every rewritten commit
  verifies with the configured signing identity, and the worktree was clean.
- OCR review ranges continue to name the commits actually reviewed. The plan
  records signed rewritten commits with identical corresponding trees rather
  than pretending the historical review executed against new commit objects.
  The next gate scans and builds the complete rewritten range before its single
  `--force-with-lease` branch update.

### Rewritten-range Validation And Handoff Checkpoint

- Every commit from stable 0.4.7 through the consolidated tip verifies with the
  configured signing identity. The complete rewritten range passes Gitleaks,
  owner-private marker and tracked-artifact scans, `git diff --check`, routine
  quality/security, and independent tests on each supported Python version.
- Two explicit 0.5.0 target-development builds are byte-identical and pass
  Twine, closed wheel/sdist inspection, zero-runtime-dependency, ecosystem and
  framework layout, and removed-module checks. Hash-locked wheel installs on
  the lower and intermediate supported versions plus an sdist install on the
  upper version pass isolated import, hostile shadow, `pip check`, restricted
  `PATH`, and module-layout probes.
- The installed artifact completes the real stdio MCP protocol with the one
  read-only `ocr_toolkit_evidence` tool. Synthetic summary, fact, coverage, and
  delta list/get calls preserve root and named-directory components and expose
  Jinja2/Twig template evidence. The checksum-qualified OCR binary only runs a
  JSON rules preview: ordinary source, Jinja/Twig files, and an extensionless
  conventional role template are selected with no session artifact or LLM run.
- Static shell/YAML checks, lock and compatibility manifests, dependency audit,
  Towncrier draft, and clean worktree checks pass. Read-only public readback
  still reports OCR 1.9.2 as latest, issues #76 and #78 open, and draft feature
  PR #77 at the old clean remote tip. The single branch update, hosted checks,
  merge, and development publication remain pending; no further OCR review is
  authorized.

### Final Local Deterministic Validation Checkpoint

- Package, install, MCP, and privacy receipts remain bound to signed
  pre-rewrite implementation checkpoint `14b074aab85f92a883b46a3994c4ae46a5e54598`.
  The rewritten ecosystem/validation slice preserves all non-plan content and
  absorbs only the final plan reconciliation; stable 0.4.7 ancestry and its
  signatures are verified, and the branch remains unpushed after the owner's
  push-policy correction.
- Routine formatting, Ruff, strict mypy, Bandit, coverage, and the complete test
  suite pass. Independent full tests also pass on each supported Python version;
  the lockfile, dependency audit, OCR compatibility manifest, changed shell and
  YAML files, and complete-range Gitleaks scan are clean.
- Two target-version builds are byte-identical and pass Twine plus closed archive
  inspection. The wheel and sdist retain zero runtime dependencies, contain the
  ecosystem/framework package layout, and omit removed flat modules. Hash-locked
  wheel and sdist installs pass supported-Python, hostile-shadow, isolated-import,
  `pip check`, and restricted-`PATH` command checks.
- An installed artifact completes the real stdio MCP protocol flow with the one
  read-only `ocr_toolkit_evidence` tool. Synthetic fact, coverage, and delta
  list/get checks preserve `.` as root and `repository` as an ordinary path;
  Jinja2 and Twig template evidence is present and private modes remain intact.
- Checksum-qualified OCR 1.9.2 preview selects ordinary source plus Jinja, Twig,
  and extensionless conventional role templates without an unsupported-extension
  result or session artifacts. This is a rules-selection probe, not another OCR
  review. Towncrier draft, source-integrity/privacy checks, and `git diff --check`
  pass. M2 implementation is locally complete; the roadmap remains in progress
  until feature and stable 0.5.0 delivery are independently read back.

### Pre-additional-review Deterministic Validation Checkpoint

- Rewritten signed checkpoint `a05399fd02916493bd516caae313b618becda221`
  has the exact pre-additional-review tree after absorbing its plan-only receipt;
  its signature, clean-tree evidence, and ancestry from stable 0.4.7 are verified.
  No branch push occurred.
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
  `git diff --check`, and private receipt modes pass. At this checkpoint, the
  additional concurrency-2 review and its bounded remediation remained; both
  subsequently completed as recorded above.

### First Full OCR Review And Remediation Checkpoint

- The first full local OCR review ran once over exact range
  `3caa50b4fc5026da79c7f2ceae1deef31715f814..69a44f7efb053ff11cfc28da1ae910e8f34a8d0b`
  with the checksum-qualified OCR 1.9.2 binary through an exact-HEAD installed
  wheel. That pre-rewrite head remains the immutable review-receipt identity;
  rewritten signed checkpoint `2ebc198c66217a49e5fd2aa92ab40d70c6a6d709`
  has its exact tree. No GitLab posting command or credential was used. Private
  result, stderr, bootstrap, and evidence artifacts retain owner-only permissions,
  and the ignored review context is absent from the tracked range.
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
