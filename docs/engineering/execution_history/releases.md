# Release Execution History

This archive preserves completed execution plans moved out of the active registry; the release index associates each plan with the stable tag or release cycle it supported. `PLANS.md` remains the source for active or blocked repository work; historical receipts here remain part of the audit trail.

<a id="plan-toolkit-0-5-0"></a>

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

<a id="plan-toolkit-0-4-7"></a>

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

<a id="plan-toolkit-0-4-6-reconciliation"></a>

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

<a id="plan-toolkit-0-4-6"></a>

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

<a id="plan-toolkit-0-4-5"></a>

## Completed Plan: Qualify OCR 1.8.7-1.8.8 and release toolkit 0.4.5

Status: completed
Owner: Codex
Last Updated: 2026-08-05
Release Classification: release-required
Target Stable Version: 0.4.5
Tracking Issues: #60, #61
Included Pull Request: #59

### Goal

Qualify Open Code Review 1.8.7 and 1.8.8 as one ordered upstream release chain, promote checksum-verified 1.8.8 as the tested and recommended toolkit baseline, and publish stable toolkit 0.4.5 together with the separately reviewed cryptography 50.0.0 development-toolchain update from PR #59. Correct the compatibility workflow so multiple unseen patch releases retain adjacent comparison context and can produce one safe cumulative promotion without weakening human review for material changes.

### Decisions

- Merge PR #59 separately after lockfile, reverse-dependency, API-exposure, and hosted-check review. It changes the Linux development/release chain through `twine -> keyring -> secretstorage`; the published toolkit runtime remains dependency-free.
- Preserve one qualification issue and immutable evidence record per OCR release, but classify ordered candidates against their adjacent predecessor while retaining the current tested baseline separately.
- Any failed, material, ambiguous, discontinuous, or mixed candidate chain requires human conclusions and prevents an automatic update PR. A wholly automatic-safe contiguous chain may prepare one cumulative patch targeting only its newest version.
- Treat OCR 1.8.7 per-run provider/model selection and additive result identity as future BL-016/BL-017 inputs, not as completed toolkit profiles or telemetry. OCR 1.8.8 Nix/Haskell allowlist and built-in rules change the effective rules contract but do not implement toolkit evidence packs.
- Install the verified Darwin arm64 OCR 1.8.8 binary locally and run only deterministic compatibility probes. Do not perform a full LLM review of the release diff.
- Keep this plan active through feature merge, exact TestPyPI development verification, the release PR, stable TestPyPI/PyPI publication, annotated tag, immutable GitHub Release, provenance/hash reconciliation, supported-Python installs, and final issue closure.

### Work Queue

1. [x] Review and separately merge PR #59; verify protected checks, post-merge workflows, and its exact TestPyPI development artifact.
2. [x] Introduce backward-compatible chain-aware OCR evidence and workflow contracts with distinct tested-baseline and adjacent-comparison identities.
3. [x] Aggregate ordered qualification results so only a fully safe contiguous chain can prepare one cumulative update; preserve manual gates for any material member.
4. [x] Add regression coverage for ordering, gaps, duplicates, manual tags, mixed classifications, issue comparisons, cumulative promotion, additive LLM identity, and fail-closed workflow behavior.
5. [x] Record reviewed OCR 1.8.7 and 1.8.8 evidence and human conclusions, promote 1.8.8, and update every runtime, example, documentation, checksum, compatibility, and changelog contract.
6. [x] Reconcile BL-016/017 with upstream per-run LLM identity while preserving BL-008/009/010/018 status and roadmap truth.
7. [x] Atomically install checksum-verified OCR 1.8.8 Darwin arm64 in the active local `PATH` and run deterministic version/help/preview/result probes; exact MCP revision contracts remain covered by the repository suite because the OCR CLI has no standalone MCP probe command.
8. [x] Perform separate review checkpoints after PR #59, qualification-process work, and promotion/docs/backlog work; correct every actionable finding before continuing.
9. [x] Run focused and complete Python validation, compatibility/workflow checks, Gitleaks, lock/manifest/Towncrier checks, reproducible build/Twine, restricted-path wheel/sdist installs, and a final full-diff review.
10. [x] Merge the protected feature PR and independently reconcile its exact TestPyPI development artifacts, hashes, provenance, and supported install smokes.
11. [x] Prepare and merge `release/v0.4.5`; verify stable TestPyPI/PyPI artifacts, annotated tag, immutable GitHub Release, hashes, attestations, and Python 3.12-3.14 installs.
12. [x] Add human and release receipts to #60/#61, close them only after stable verification, and reconcile this plan plus every affected status-bearing representation.

### Qualification Process Review Checkpoint

- PR #59 changed only the universal lock, retains `cryptography` through the Linux-only Twine/SecretStorage development and publication path, and does not expose cryptography APIs or add a toolkit runtime dependency. Its 13 protected checks passed before squash merge `98cb3b7c45484bb1025a240c56d5770a5ebc1b0e`.
- The compatibility matrix now keeps the manifest recommendation as the tested baseline while comparing every unseen patch with its adjacent predecessor. Missing, duplicate, cross-minor, stale-baseline, incompatible, or mixed chains fail closed; only a wholly automatic-safe contiguous chain may create one cumulative patch and PR.
- Review found and corrected a partial-write boundary in cumulative promotion: all evidence assets, capabilities, human conclusions, source replacements, and manifest payloads are now validated before the checkout changes. Qualification also rejects stale or pre-baseline comparison inputs.
- Focused validation passes 31 tests plus Ruff lint and `git diff --check`. Tests cover 1.8.6 to 1.8.7 to 1.8.8 ordering, gaps, mixed classification, issue compare identity, additive LLM identity, cumulative reviewed promotion, and legacy single-evidence compatibility.

### Promotion, Documentation, And Backlog Review Checkpoint

- Hosted run `30987719228` supplied checksum-verified Linux amd64 evidence for both releases. The committed v2 records retain its exact asset matrices and machine contract results, add adjacent comparison identity, and add capabilities proven by independent checksum-verified Darwin arm64 probes. Evidence SHA-256 is `194c5697a0624ef917cfc59e939e4bcd95c30a6fde72f2cd99bc4d94c2c88ff7` for 1.8.7 and `3a88bd3d46b378b2b02e8e5324058eecdc21efd451927a1a305f107d38409c47` for 1.8.8.
- OCR 1.8.7's per-run provider/model flags and additive `llm` identity satisfy the upstream capability dependency for BL-016 and give BL-017 a bounded run identity to reuse. Neither backlog item is implemented: profiles still need an approved closed matrix/precedence contract, and telemetry still requires the planned gap audit.
- OCR 1.8.8's Nix/Haskell allowlist and built-in rules expand the effective review scope but do not resolve versions, framework identity, provenance, deltas, or completeness. BL-008, BL-009, and BL-010 remain unfinished; BL-018 remains conditional. Viewer, VS Code, upstream GitLab example, scan, model-catalog, documentation, and CI changes do not require toolkit runtime work. The consumed Go MCP SDK remains v1.6.1.
- Review found and corrected stale version-specific prose in MCP, operations, remote-header, security, and GitLab documents plus a duplicated security invariant. Runtime preflight, public example, Linux checksum, README, roadmap, strategy, backlog, tests, and Towncrier fragments now agree on OCR 1.8.8.
- `/opt/homebrew/bin/ocr` is the official Darwin arm64 1.8.8 binary with SHA-256 `db7da11ad1faa5ba3dca2d5add1ebe49ceedf37708e7044c92e9141721e50cd2`. Version/help/preview/synthetic JSON result and toolkit-consumer probes pass for both 1.8.7 and 1.8.8; 122 focused tests plus 15 MCP subtests pass and the manifest validates.
- The complete quality gate passes 545 tests plus 35 subtests at 79% coverage, Ruff formatting/lint, mypy, and Bandit. Review also replaced a brittle workflow test that looked for an inline limit string with contracts for the centralized chain builder, ten-release bound, aggregate assessment, artifact fan-in, and single cumulative promotion step. Lock validation, Towncrier draft rendering, workflow YAML parsing, and `git diff --check` pass.
- All post-merge workflows for PR #59 completed successfully. TestPyPI run `31009885896` published `0.4.5.dev38`; independently downloaded registry bytes match the workflow artifact: wheel SHA-256 `86587406a94b4f1ff585e113af67a017ac3d698b05cf6df93ad6eb61c6753cce`, sdist SHA-256 `ccb6f1716cd35912b921bf6d671f50b159012efe7ca19d20dd4f0dc6a7ca0ed2`. Both provenance records identify `testpypi.yml`, merge `98cb3b7c45484bb1025a240c56d5770a5ebc1b0e`, and the `testpypi-public-disclosure` environment.

### Final Pre-Push Review Checkpoint

- Final scope reconciliation added direct regressions for duplicate discovery and the next manually requested patch. It also corrected one fail-closed design edge: a genuine skipped, minor, or major upstream sequence must still receive machine evidence and a human-review issue. The matrix therefore preserves adjacent observed comparisons, while aggregation labels any non-contiguous sequence `human-review-required` and never prepares a patch.
- Checksum-pinned Gitleaks 8.24.3 passes the complete first-parent feature history. The locally installed 8.30.1 was deliberately not accepted as a substitute; the exact repository pin was downloaded and used for the gate.
- Two source-date-epoch-controlled builds are byte-identical and pass Twine: development wheel SHA-256 `870635bec8cb284bdc94f3995d4b28099b1f34647e7f8be5e13bf5894685fb61`, sdist SHA-256 `c46b80c39ab0cc1f31944f53a16815cfac07baf91489efc6e1e55557ff9232e4`. Restricted-path wheel installs pass on Python 3.12 and 3.13, and the sdist install passes on Python 3.14, all from a hostile shadow-package directory with the published CLI/import intact.

### Feature Merge And Development Publication

- Feature PR #62 passed all 13 protected checks with no review threads and merged as GitHub-verified squash commit `343fdf310708f67d732bf1ca9ecfffd9944e0a97`. All six protected-main workflow suites then passed.
- TestPyPI run `31012492656` published and installed immutable `0.4.5.dev39`. Cache-bypassed PEP 691 reads, freshly downloaded registry bytes, and the workflow artifact are byte-identical: wheel SHA-256 `bcd81ba83388b33ae5466ba08cc38df425355cac71815a7e3b5586485ad233bd`; sdist SHA-256 `e84484cd3538827a56c2e48013f20ff2638d7c84c8c987c8b557304197fbe28b`.
- TestPyPI provenance identifies `testpypi.yml`, merge `343fdf310708f67d732bf1ca9ecfffd9944e0a97`, and the `testpypi-public-disclosure` environment for both exact subjects. Restricted-path development installs passed from a hostile shadow-package directory across the supported wheel/sdist matrix.
- The v0.4.5 release branch consumes only the #60/#61 fragments, sets reproducible source epoch `1785938068` one second after the feature merge, and advances the next development line to 0.4.6.

### Release Preparation Review Checkpoint

- The release diff contains only the stable and next-development version markers, deterministic epoch, generated 0.4.5 changelog, consumed #60/#61 fragments, and current plan receipts. The release notes render the exact `v0.4.4...v0.4.5` comparison URL; no roadmap milestone or future-backlog item is being closed by the release commit.
- Release-focused tests pass 40 cases. The complete quality gate passes 547 tests plus 35 subtests at 79% coverage, Ruff formatting/lint, mypy, and Bandit; manifest, lock, workflow YAML, dependency audit, and `git diff --check` validation also pass.
- Two clean stable builds using version `0.4.5` and source epoch `1785938068` are byte-identical and pass Twine: wheel SHA-256 `15e70eff06f1c4a1f5f9e573b4bf55353938374404d01db1bba1ab920b5eda12`; sdist SHA-256 `d888a3a550836d175bf2520c024fa69d1f9ea5ca304459f0419b27076cdc0d4f`.
- Restricted-path installs of the stable wheel pass on Python 3.12 and 3.13, and the stable sdist install passes on Python 3.14. All three run the installed CLI/import from a private hostile shadow-package directory and report exactly 0.4.5.

### Stable Publication And Closure Evidence

- Release PR #63 passed all 13 protected checks with no review comments or threads and merged as GitHub-verified squash commit `e05c40627c8dbaa14f299d1567a8107f01812c24`. Release workflow run `31013395527` authorized that exact merge, repeated quality, audit, deterministic build and attestation gates, published to TestPyPI and PyPI, verified both registries, and published the tag plus GitHub Release successfully.
- Independent cache-bypassed PEP 691 reads expose exactly the reviewed hashes. Freshly downloaded TestPyPI, PyPI, workflow, and GitHub Release distributions are byte-identical: wheel SHA-256 `15e70eff06f1c4a1f5f9e573b4bf55353938374404d01db1bba1ab920b5eda12`; sdist SHA-256 `d888a3a550836d175bf2520c024fa69d1f9ea5ca304459f0419b27076cdc0d4f`.
- Both registry provenance records identify `release.yml`, merge `e05c40627c8dbaa14f299d1567a8107f01812c24`, run `31013395527`, and their expected `testpypi-public-disclosure` or `pypi-production` environment. GitHub attestation verification binds both exact subjects to the same release merge and protected-main workflow.
- Annotated tag `v0.4.5` resolves exactly to the release merge. The GitHub Release is public, non-draft, non-prerelease, and immutable; its four asset digests agree with the workflow artifact. Restricted-path installs of the published wheel pass on Python 3.12 and 3.13, and the published sdist passes on Python 3.14 from a private hostile shadow-package directory.
- Human checklists and stable release receipts are recorded on #60 and #61. The stale #61 comparison and skipped-patch reason were corrected to adjacent predecessor 1.8.7 before both issues were closed as completed.
- BL-016/BL-017 retain their documented future scope despite newly satisfied upstream prerequisites; BL-008/BL-009/BL-010 remain unfinished and BL-018 remains conditional. No roadmap milestone completed, so neither `ROADMAP.md` nor the backlog requires a closure status change. The final plan-only reconciliation is `no-release` and does not alter stable product behavior.

### Initial Evidence

- `main` is clean and synchronized at `77317c9`; stable PyPI, TestPyPI, tag, and immutable GitHub Release all report toolkit 0.4.4, while `.next-version` is 0.4.5.
- PR #59 is mergeable and all 13 hosted checks pass. Its only tracked change is `uv.lock`; `cryptography` is retained in the universal lock and installed through Twine's SecretStorage/keyring path on Linux, not as a toolkit runtime dependency.
- Issues #60/#61 contain checksum-verified compatible Linux amd64 evidence for OCR 1.8.7/1.8.8. The workflow classified both from tested baseline 1.8.6, causing #61's false skipped-patch reason even though its adjacent predecessor is 1.8.7.
- OCR 1.8.7 adds per-run provider/model flags and additive `llm` result identity, GitLab example routing, resumable full scans, model entries, and CLI handling changes. OCR 1.8.8 adds Nix/Haskell file/rule support plus Viewer, VS Code, documentation, and CI-only changes. The consumed Go MCP SDK remains v1.6.1.
- No `ocr` executable is currently available in `PATH`. The official 1.8.8 Darwin arm64 digest is `db7da11ad1faa5ba3dca2d5add1ebe49ceedf37708e7044c92e9141721e50cd2`; Linux amd64 is `68a9b8835f6e4e210531833657a3a4902841283c410322fc4342778d91959756`.

<a id="plan-toolkit-0-4-4"></a>

## Completed Plan: Complete evidence coverage and GitLab review health for v0.4.4

Status: completed
Owner: Codex
Last Updated: 2026-08-03
Release Classification: release-required
Target Stable Version: 0.4.4
Tracking Issues: #41, #42

### Goal

Make bounded repository evidence explicit about when negative conclusions are safe, repair Ansible dynamic-inventory and recursive role topology coverage, suppress exact no-op suggestions, and redesign the GitLab summary around independent review health, findings, and incomplete coverage. Close BL-022 by publishing the already-earned OpenSSF Best Practices badge and reconcile affected future backlog without claiming unrelated milestones.

### Decisions

- Build from verified toolkit v0.4.3 and retain checksum-qualified OCR 1.8.6; a newer OCR release requires separate qualification.
- Deliver #41, #42, and the OpenSSF documentation/backlog closure in one feature pull request, followed by the protected v0.4.4 release pull request.
- Treat OCR 1.8.6 `ocr.run-manifest/v1` failed coverage records as the canonical per-file failure source. Legacy warnings remain a bounded compatibility fallback, and `summary.files_reviewed` never proves successful coverage.
- Render a complete result with non-coverage warnings as `Review complete with warnings`; warnings do not demote validated complete coverage to incomplete.
- The OpenSSF record at project 13906 is publicly passing. Badge publication and BL-022 closure are `no-release` work bundled into this release-required objective.

### Work Queue

1. [x] Add a reusable scoped evidence-coverage schema, persistence/MCP/bootstrap contract, v1-store fail-closed compatibility, and deterministic coverage deltas.
2. [x] Classify static, dynamic, and executable inventory sources without execution; compose per-scope group coverage conservatively.
3. [x] Model Ansible's bounded recursive `defaults/main/` and `vars/main/` surfaces with upstream-compatible ordering and exclusions.
4. [x] Omit exact no-op suggestion blocks using the reviewed head blob while preserving findings and lifecycle identity.
5. [x] Normalize manifest/legacy incomplete-coverage diagnostics and render every result through one review-health/findings/coverage summary model.
6. [x] Add the OpenSSF badge, close BL-022 in planning truth, and reconcile BL-008/009/010/017 without changing their completion status or the roadmap.
7. [x] Add Towncrier fragments and update public evidence, GitLab operations, configuration, and security documentation.
8. [x] Run focused, complete, security, package, supported-Python, and GitLab Markdown contract validation. The optional live GitLab renderer requires authentication and is not a release gate.
9. [x] Merge the feature through protected main and independently verify its exact TestPyPI development artifacts against the workflow artifact and PEP 691 index.
10. [x] Prepare and merge `release/v0.4.4`, publish stable TestPyPI/PyPI artifacts, and independently verify tag/immutable GitHub Release, hashes, attestations, and Python 3.12-3.14 installs.
11. [x] Record final receipts and reconcile this plan plus every status-bearing roadmap/backlog representation affected by completed work.

### Initial Evidence

- `main` is clean and synchronized with `origin/main` at `ce48166`; the latest independently verified stable release is v0.4.3 and `.next-version` is 0.4.4.
- The recommended/tested OCR baseline is 1.8.6. Its versioned manifest provides selected/completed/reused/failed/waived partitions plus bounded failed-item path, classification, and redacted reason fields.
- OpenSSF project 13906 reports passing at 100% and publishes the exact requested badge Markdown, so BL-022 can close after the repository badge readback succeeds.
- #41 touches the established M1 evidence boundary but does not complete BL-008, BL-009, or BL-010. #42 establishes result-derived reporting that BL-017 must reuse rather than duplicate; it does not implement telemetry.

### Pre-push Review Checkpoint

- The v2 store persists `repository.evidence-coverage/v1` atomically with snapshot indexes and deterministic semantic deltas. Legacy v1 stores remain readable but carry an explicit unknown-completeness diagnostic; missing facts support absence only for applicable `complete` coverage.
- Ansible topology stays offline and read-only. Static supported inventory, plugin YAML, and executable sources compose per directory; malformed, templated, truncated, symlinked, unreadable, or over-limit topology degrades coverage. Recursive role-main precedence and exclusions follow the loader contract verified in ansible-core 2.17 through current 2.x/devel, without a 2.17-only version gate.
- GitLab output now has one visible heading, independent health/findings/coverage states, bounded manifest-first failed-file diagnostics, quiet inline metadata, aggregate emoji, collapsed operational details, and exact reviewed-head no-op suppression. Existing discussion identity, suppression, rollback, and prior-review preservation remain intact.
- `uv run pytest -q` passes 541 tests plus 35 subtests. Ruff format/lint, mypy, `scripts/quality.sh check` (coverage above 70%), manifest validation, `git diff --check`, and checksum-verified Gitleaks 8.24.3 all pass.
- Two clean builds are byte-identical. Twine passes; the wheel smoke passes on Python 3.12 and the sdist smoke passes on Python 3.14. Current development hashes are wheel `13b6843dd4003115b8f93cd900b914170fef1ff292e6979ee592a01663f05029` and sdist `2115f60d35da864439b588ba9561f6d15c08db7c0aabfb47ae23c8f14c82dc5b`.
- The exact OpenSSF badge and target both return HTTP 200, and the target resolves to the public passing record. BL-022 is therefore removed; BL-008/009/010/017 retain their future status with only overlap clarified. No roadmap milestone is completed.

### Execution Evidence

- Feature PR #56 merged through the active ruleset as GitHub-verified squash commit `c0d5de640f4bbd59a4d419ca227a11379aa24e91` after all 13 hosted checks passed and no review threads remained. Issues #41 and #42 closed automatically with the merge.
- TestPyPI development run `30817832682` published and installed immutable `0.4.4.dev35` artifacts. The downloaded workflow artifact, a cache-bypassed independent PEP 691 query, and freshly downloaded registry bytes are identical: wheel SHA-256 `854c2007aba98ec37abe74c315b818fac985e9033e25628afaa8ba480313adf7`; sdist SHA-256 `353a9666d2eea29417628c59fe4f0126684d93209ab1b097c5bfe7ddfbf28bb5`.
- The v0.4.4 release branch consumes only the #41/#42 fragments, sets reproducible source epoch `1785763484` one second after the feature merge, and advances the next development line to 0.4.5. BL-022 remains no-release documentation work bundled into this release and does not add a changelog entry.
- Release-focused validation passes the complete quality gate, manifest validation, Gitleaks, exact release-body rendering, and `git diff --check`. Two clean stable builds are byte-identical: wheel SHA-256 `c9fd35ea0a41984e804a750475cd2124530cb926b9d28f8fa50cfefb9abc0d98` and sdist SHA-256 `e9d3dd657ad00f7a54f9a87591667b119585547a6a0c639519b8e484ec1eb930`; Twine and restricted-path Python 3.12 wheel/Python 3.14 sdist installs pass with a hostile repository shadow package.
- Release PR #57 passed all 13 protected checks with no review threads and merged as GitHub-verified commit `5025c9d6d702e5f0b2d24610573cf1cd597ce606`. Release workflow run `30818451602` authorized that exact merge, rebuilt and attested the distributions, published and verified stable TestPyPI/PyPI, and created the tag plus GitHub Release successfully.
- Independent cache-bypassed PEP 691 reads from both registries expose exactly the reviewed hashes and provenance endpoints. Freshly downloaded TestPyPI, PyPI, workflow, and GitHub Release distributions are byte-identical; both registry provenance records identify `release.yml` and their expected trusted-publishing environments, while GitHub's Sigstore attestation binds both subjects to merge `5025c9d6d702e5f0b2d24610573cf1cd597ce606` and run `30818451602`.
- Annotated tag `v0.4.4` resolves exactly to the release merge. The GitHub Release is public, non-draft, non-prerelease, and immutable; its four assets match the workflow artifact and checksum metadata. Restricted-path installs of the published wheel pass on Python 3.12 and 3.13, and the published sdist passes on Python 3.14 with a hostile shadow package.
- Issues #41 and #42 remain closed. BL-022 was removed after the public passing badge readback; BL-008/009/010/017 remain future work with clarified overlap, and no roadmap milestone changed, so neither backlog nor roadmap needs a further closure edit.

<a id="plan-toolkit-0-4-3"></a>

## Completed Plan: Harden OCR compatibility automation and release v0.4.3

Status: completed
Owner: Codex
Last Updated: 2026-08-03
Release Classification: release-required
Target Stable Version: 0.4.3
Tracking Issue: #49

### Goal

Repair the scheduled OCR compatibility workflow as a durable product boundary: consume OCR's versioned run-manifest outcomes safely, keep exactly one enriched qualification issue per upstream version, qualify OCR 1.8.4 through 1.8.6, and publish stable toolkit 0.4.3. Reduce GitHub Actions storage without deleting audit metadata by constraining cache writers, adding bounded retention automation, and performing one verified cleanup of accumulated caches, logs, and artifacts.

### Root Causes And Decisions

- Run `30798939793` proved two independent defects. OCR 1.8.5 and 1.8.6 emit the new manifest-derived `complete` status, while both the qualification probe and runtime consumers still require the legacy `success` family. OCR 1.8.4 passed, but two workflow steps independently searched an eventually indexed HTML marker and each created an issue.
- Keep one canonical issue per stable OCR version. For v1.8.4 preserve issue #48, copy current evidence into it, and close #43 through #47 with the `duplicate` label and an explicit link to #48.
- Qualification issues include a bounded, neutralized upstream change summary plus official release/compare links, machine evidence, toolkit-impact classification, and the current workflow receipt. Raw upstream Markdown is never forwarded as trusted issue content.
- Normalize legacy and manifest outcomes through one runtime contract. `success` and `complete` are clean; `completed_with_warnings` is complete with warnings; `completed_with_errors`, `budget_exceeded`, and `partial` are partial; `failed` is a failure; `skipped` is skipped. Manifest v1 status, coverage partition, failure classes, and bounds must agree before any result is accepted.
- Cache writes become main-only for uv; pull requests may restore the main cache but cannot save branch-scoped copies. Disable both CodeQL TRAP caching and the separately controlled v4 overlay-database mode for this small repository. Keep run/check metadata, delete only aged logs/artifacts, and retain release logs longer than ordinary workflow logs.
- GitHub's managed repository cache retention/storage-limit endpoints return HTTP 402 without a payment method. Repository-owned bounded maintenance is therefore the available policy mechanism.

### Work Queue

1. [x] Create tracking issue #49 and the implementation branch from synchronized protected `main`.
2. [x] Add one provider-neutral OCR result contract used by review execution, GitLab posting, and compatibility qualification. Validate legacy outcomes plus `ocr.run-manifest/v1`, including record/field bounds, set partition, terminal-state derivation, failure classes, and budget consistency.
3. [x] Render clean, warning, partial, failed, and skipped outcomes from one normalized matrix. Preserve partial findings with an explicit coverage warning; never publish normal comments for failed results; retain legacy OCR compatibility.
4. [x] Replace full-text issue search with bounded exact-marker REST reconciliation. Pass one concrete issue number through issue upsert and patch preparation; ignore only closed issues explicitly labeled `duplicate`, fail closed on every other competing marker, and preserve fatal integrity/API failures.
5. [x] Add safe upstream change summaries and official release/compare links to qualification issues. Classify every OCR 1.8.4-1.8.6 changelog item as toolkit-owned contract work, future-backlog impact, or release-note-only context.
6. [x] Qualify checksum-pinned Linux amd64 OCR 1.8.4, 1.8.5, and 1.8.6; recommend 1.8.6; update the manifest, evidence, runtime/example/docs pins, exact checksums, tests, and Towncrier fragments.
7. [x] Make uv cache saving main-only, disable CodeQL TRAP caching, set transient build artifact retention to seven days, and add a weekly/manual bounded Actions maintenance workflow with explicit dry-run/apply behavior.
8. [x] Validate the retention selector against synthetic API fixtures, execute a live dry-run, then delete accumulated stale caches and policy-expired logs/artifacts. Preserve tags, Releases, attestations, registry artifacts, and workflow/check metadata; reread usage after GitHub's delayed accounting refresh.
9. [x] Run focused contract/workflow tests, the complete Python matrix, Gitleaks, diff checks, build/Twine, and clean wheel/sdist installs. Perform adversarial review of result parsing, GitHub API bounds, issue rendering, and destructive target selection.
10. [x] Merge protected feature PR #50 and independently verify its exact TestPyPI `0.4.3.dev31` wheel and sdist against the workflow artifact and PEP 691 index.
11. [x] Prepare and merge `release/v0.4.3`, publish stable TestPyPI/PyPI artifacts, and independently verify tag/immutable GitHub Release, hashes, attestations, and Python 3.12-3.14 installs.
12. [x] Correct the post-release CodeQL v4 overlay-cache gap through a protected no-release follow-up, delete the two newly written overlay caches, and prove through hosted CodeQL plus live cache readback that they do not return.
13. [x] Record final receipts, close the tracking issue, and reconcile this plan plus every status-bearing roadmap/backlog representation affected by completed work.

### Initial Evidence

- The repository is clean and synchronized at stable release `ee769c3` (`v0.4.2`); `.next-version` is already `0.4.3`.
- Run `30798939793` discovered v1.8.4-v1.8.6. v1.8.4 produced a valid automatic-safe patch, while v1.8.5 and v1.8.6 failed with `candidate full review emitted an unsupported result object`.
- Upstream v1.8.5 introduces `ocr.run-manifest/v1` and derives top-level `status` from `terminal_state` (`complete`, `partial`, `failed`, `skipped`). v1.8.6 retains that contract.
- Issues #43-#48 contain the same exact v1.8.4 marker. The workflow created #47 in the patch-preparation step and #48 seconds later in the final issue step because both relied on GitHub full-text search rather than a concrete issue identity.
- Current Actions artifacts total about 16.6 MiB, while 37 active caches consume 494,925,898 bytes. Twenty-two CodeQL caches consume about 182.3 MiB and fourteen setup-uv caches about 284.2 MiB. Keeping the current two main uv caches plus Gitleaks and removing obsolete setup-uv/CodeQL entries should reclaim roughly 393 MiB before log/artifact cleanup.

### Pre-push Review Checkpoint

- Reviewed the complete local diff before any push across result normalization/publication, issue reconciliation/untrusted release rendering, and every destructive Actions selector/URL.
- Corrected two review findings before publication: partial results now preserve the prior complete review, and log cleanup is idempotent with a bounded retry window instead of repeatedly traversing immutable run history.
- `scripts/quality.sh check`, 180 focused tests plus 12 subtests, Ruff, mypy, workflow YAML parsing, `git diff --check`, and checksum-verified Gitleaks 8.24.3 worktree scanning pass locally. Supported-Python and hosted workflow results remain pending the protected PR.
- A second review after hosted v1.8.5 qualification exposed a transport-only timeout while downloading `sha256sum.txt`. The correction retries only bounded transient timeout, connection, incomplete-read, and selected HTTP failures; resets partial files before each retry; preserves origin, byte, and digest checks; and still fails immediately on HTTP 404 and local I/O errors. Focused validation passes 27 tests plus Ruff, mypy, and `git diff --check`.
- Promotion review confirms all three committed evidence files are byte-identical to hosted artifacts, every manifest evidence hash matches, all runtime/example/documentation pins select v1.8.6 with its qualified Linux checksum, and the unchanged upstream MCP SDK remains v1.6.1. The complete quality gate, 117 focused tests plus 15 subtests, manifest validation, Twine, and restricted-path wheel/sdist smokes on Python 3.12/3.14 pass. Fetching the repository's published tags corrected a local fallback-version-only preview before the final artifact gate and restored the intended 0.4.3 development line.
- Release review caught that OCR v1.8.6's new default exclusions are an effective rules-contract change and therefore require the conditional `🧩 Rules` changelog section. The corrected release diff contains only the 0.4.3/0.4.4 version markers, deterministic epoch, generated changelog, consumed fragments, and current plan receipts; no unrelated roadmap or backlog status changes are implied.
- The required post-release review caught that CodeQL v4 controls overlay-base database caching separately from the configured TRAP cache input. The follow-up selects full-database mode explicitly, preserving complete analysis while eliminating that cache writer; focused tests, workflow parsing, the complete quality gate, Gitleaks, signed-commit verification, hosted CodeQL, and live cache readbacks all pass before closure.

### Execution Evidence

- Issues #43 through #47 are closed with the `duplicate` label and a link to canonical issue #48. The passing v1.8.4 qualification run `30807114499` updated #48 in place with bounded upstream release changes and its current receipt.
- The accumulated cleanup deleted 189 stale Actions objects while preserving workflow and check metadata. GitHub's refreshed aggregate and direct cache listings now agree on three current caches totaling 79,827,436 bytes. After the feature-PR and qualification runs, 108 policy-retained artifacts total 10,922,669 bytes.
- Hosted run `30807169920` reached v1.8.5 asset qualification but failed on a single read timeout, motivating the bounded transport retry correction above rather than weakening checksum or result-contract validation.
- Runs `30807639061` and `30807718526` then qualified v1.8.5 and v1.8.6 respectively, producing byte-identical committed evidence and one canonical release-enriched issue each (#51 and #52). The manifest records v1.8.6 as the tested recommendation with its exact Linux amd64 checksum `1f2611766a562aee300af75524270de9b99ab2cf5c63bf75a9546ebf809f78a6`.
- Release classification found one toolkit-owned contract change: v1.8.5's `ocr.run-manifest/v1`, handled by the shared normalized parser. v1.8.4's LLM/gitignore fixes and GitHub Action fallback, plus v1.8.5's telemetry, VS Code, manual-provider, configuration, and test changes, require no further toolkit adaptation. v1.8.6's expanded default exclusions are an accepted effective review-scope change; its session-comment command, truncated-chat retry, and test refactor require no toolkit work. No future-backlog item is warranted, and OCR's Go MCP SDK remains v1.6.1.
- Feature PR #50 merged through the active ruleset as signed squash commit `8106bcedf237b1efe132503bb7f7f8f2d712471b` after 13 required checks passed and zero review threads remained. A pre-merge ruleset audit caught unsigned checkpoint commits; the feature branch was re-signed with an already registered key, proven tree-identical, rescanned, and revalidated without using an administrative bypass.
- TestPyPI development run `30808897066` published and installed immutable `0.4.3.dev31` artifacts. The downloaded workflow artifact and independent PEP 691 query agree on wheel SHA-256 `3506f6789942309d2efc7849f2509e0cb707df4c3372592a18177eab332161f0` and sdist SHA-256 `49412600010f5d36b0ab1004a099778d92487c64c1cfafb6869e7168d3039131`.
- Because OCR v1.8.6 expands its default file exclusions, the stable 0.4.3 changelog includes a separate `🧩 Rules` entry in addition to the main feature entry. The reproducible source epoch is `1785755800`, one second after the feature merge commit, and `0.4.4` becomes the next development line.
- Release-focused validation passes 71 tests, the complete quality gate, manifest validation, exact release-body rendering, and `git diff --check`. Two independent stable builds are byte-identical: wheel SHA-256 `236b08306f6fe3a6fe65e1a96e8170ad3566b77e0cbf6d7c6525c1ec98432273` and sdist SHA-256 `4617ce04bb957130d1dae8be7237fe82a9d342ef09f45836779cfc1dec24ec92`; Twine and restricted-path Python 3.12 wheel/Python 3.14 sdist installs pass.
- Release PR #53 passed all 13 protected checks with no review threads and merged as GitHub-signed commit `a9822bfcf28c9f38d3f3078c31550a76a520eea9`. Release workflow run `30809679849` completed authorization, deterministic build, GitHub provenance attestation, stable TestPyPI and PyPI publication and verification, and GitHub Release publication successfully.
- Independent PEP 691 reads from TestPyPI and PyPI expose exactly the reviewed wheel and sdist hashes above, and the downloaded registry bytes, workflow artifact, and immutable GitHub Release assets are byte-identical. Both registries expose integrity attestations from their authorized `release.yml` environments, while `gh attestation verify` binds both distributions to the exact release merge and workflow run. Clean installs of the published wheel pass on Python 3.12 and 3.13; the published sdist install passes on Python 3.14.
- Annotated tag `v0.4.3` resolves exactly to the release merge, and the GitHub Release is public, non-draft, non-prerelease, and reports `immutable: true`. The automation-created annotated tag is not separately cryptographically signed; authenticity is carried by the GitHub-signed target commit and Sigstore-backed artifact provenance.
- Canonical qualification issues #48, #51, and #52 have checked human outcomes, preserve bounded upstream release changes, and are closed as completed; #43 through #47 remain closed and labeled as duplicates of #48. Tracking issue #49 was reopened for the post-release review correction and closed as completed only after protected-main and live-storage verification passed.
- No-release follow-up PR #54 passed all 13 protected checks with no review threads and merged as GitHub-signed commit `fdb5354d27c0a763ff14bfddb5a5d7e96e2dd72b`. PR CodeQL run `30810867531` and protected-main run `30811041908` both completed successfully in full-database mode without creating a CodeQL cache.
- The cleanup removed 192 stale or expired Actions storage objects in total, including one artifact that expired after the first readback and the two post-release `codeql-overlay-base-database-*` entries totaling 20,848,354 bytes. The post-follow-up aggregate and direct API listings agree on exactly three intended caches totaling 79,827,436 bytes and zero CodeQL caches; at that receipt, 122 non-expired policy-retained artifacts total 12,727,750 bytes, with no expired artifacts. Workflow/check metadata, tags, Releases, attestations, and registry artifacts remain preserved.
- Every protected-main follow-up workflow passed: CI run `30811041625`, Security `30811041628`, OpenSSF Scorecard `30811041871`, CodeQL `30811041908`, and TestPyPI development run `30811041769`. The latter published and installed immutable `0.4.4.dev33`; its workflow artifact and an independent PEP 691 query are byte-identical at wheel SHA-256 `7745ffe5cf084dbbe887c9663c7b236ca831156d770aacfc82c5451dbc994209` and sdist SHA-256 `c9eaeeaf96519da9c62ad422224927c72e4a267cc9fa1d90433bbaa2a08b9b29`.
- No roadmap milestone or future-backlog status was coupled to this operational compatibility/release plan, so `ROADMAP.md` and `docs/codex/TASKS_BACKLOG.md` require no closure change. The post-release repository-infrastructure correction is `no-release`; stable product behavior remains the published 0.4.3 release.

<a id="plan-toolkit-0-4-2"></a>

## Completed Plan: Qualify OCR 1.8.3 and release v0.4.2

Status: completed in repository; release PR is the final publication gate
Owner: Codex
Last Updated: 2026-07-31
Release Classification: release-required
Target Stable Version: 0.4.2
Tracking Issue: #38

### Goal

Qualify OCR 1.8.3 through the reduced patch-release path, recommend and pin it with exact checksums, adapt only consumed toolkit contracts proven to have changed, and publish stable toolkit 0.4.2. Preserve the protected implementation/release PR and external verification gates while avoiding unnecessary compatibility approval or post-release closure stages.

### Initial Impact Classification

- Per-file terminal-state handling is a possible result-contract interaction and must be covered by the normal JSON consumer probes before it can be declared compatible.
- The Cobra CLI migration changes implementation and adds shell completion, but the toolkit consumes only the existing review/help/version/config commands and flags; exact help/version/preview probes determine whether adaptation is needed.
- Viewer and VS Code changes are outside the toolkit contract. Configuration URL documentation and stale comments are release-note-only context unless the consumed rendered-config behavior changed.
- Rules content and OCR allowlisted file types do not change in 1.8.3. The upstream rules change adds integrity tests only, so 0.4.2 must omit `🧩 Rules` unless qualification finds a real effective-contract delta.

### Work Queue

1. [x] Run Linux amd64 qualification for OCR 1.8.3, preserve canonical evidence, and classify every release item against the toolkit/backlog contract.
2. [x] Add the reviewed manifest conclusion, recommend/pin OCR 1.8.3 everywhere, and update exact checksum regressions without weakening the future classifier.
3. [x] Add ordinary changelog entries without `🧩 Rules`, run proportional targeted/full/security/package validation, and verify the exact release-body comparison URL.
4. [x] Merge the protected implementation PR and verify its exact TestPyPI development build.
5. [x] Complete repository closure in `release/v0.4.2`, publish through the protected release workflow, and create no post-release repository PR.
6. [x] Hand stable TestPyPI/PyPI artifact, tag/immutable GitHub Release, hash, provenance, and Python 3.12-3.14 verification to the release workflow and external issue/goal closure.

### Initial Evidence

- OCR 1.8.3 release notes contain viewer comments, per-file terminal-state handling, VS Code force-kill behavior, a Cobra CLI migration with shell completion, configuration URL documentation, documentation cleanup, and rules-integrity tests. No built-in rules or file allowlist content change is advertised.
- Linux amd64 qualification passed all published asset and upstream checksum-file checks plus version, Cobra help/required-flag, preview, and additive result-consumer probes. Canonical evidence SHA-256: `4acc04e487834e367851c64b5cfa18316a09ae1c59f5c0c991eb69c712ef58bd`.
- Source-diff review confirms the MCP SDK remains Go MCP SDK v1.6.1. Per-file terminal-state fixes preserve the consumed result contract; the CLI migration preserves toolkit commands and flags. Viewer, VS Code, documentation/comment, gitignore, and rules-integrity changes need no toolkit adaptation.
- Targeted compatibility, integration, preflight, and evidence-MCP regressions pass with 109 tests and 15 subtests. The 0.4.2 Towncrier draft contains only `🚀 Features`; `🧩 Rules` is correctly omitted because toolkit `rules.json`, OCR built-ins, and OCR allowlist are unchanged.
- `scripts/quality.sh check` passes with 494 tests and 35 subtests at 78.73% coverage plus Ruff formatting/lint, strict mypy, and Bandit. Gitleaks, `git diff --check`, build/Twine, and clean wheel/sdist CLI installs on Python 3.12/3.14 pass.
- A disposable release build renders only the non-empty `🚀 Features` category and ends with `**Full Changelog**: https://github.com/xeonvs/open-code-review-toolkit/compare/v0.4.1...v0.4.2`; no `🧩 Rules` or conventional prefixes appear.
- Implementation PR #39 merged as `71af90da9258e57f1457ce86c94ffff403b8eb87` after every required check passed and no review threads remained. TestPyPI development run `30625374711` published and installed immutable `0.4.2.dev29` artifacts successfully.
- The final release branch renders the 0.4.2 changelog without `🧩 Rules`, authorizes reproducible artifacts from source epoch `1785495495`, establishes `0.4.3` as the next development line, and leaves no repository planning closure for after publication. Issue #38 remains the external stable-publication tracker.
- Two independent 0.4.2 release builds are byte-identical: wheel SHA-256 `0ca73e62dfaf4ebd478419cd6214c33444eff4697cd616accb6a33b7193b7e1d`, sdist SHA-256 `c7a341fd2de948c681093f03db1225cc6a145a4448fbc14fcb54b01da529f9ef`; Twine, exact release-body checks, and clean Python 3.12 wheel/Python 3.14 sdist installs pass.

<a id="plan-toolkit-0-4-1"></a>

## Completed Plan: Qualify OCR 1.8.1/1.8.2 and release v0.4.1

Status: completed in repository; release PR is the final publication gate
Owner: Codex
Last Updated: 2026-07-31
Release Classification: release-required
Target Stable Version: 0.4.1
Tracking Issue: #35

### Goal

Adopt OCR 1.8.1 and 1.8.2, make 1.8.2 the recommended version, preserve partial reviews when the upstream token budget is exhausted, and publish toolkit 0.4.1. Improve release notes with OCR-style emoji headings, an explicit `Rules` category for changes to the effective toolkit plus OCR rules/allowlist contract, and an exact full-changelog comparison link.

### Release Decisions

- The completed release-note and source review in this plan is the compatibility decision for both OCR releases. Do not create a separate compatibility issue or approval checkpoint; retain the conservative classifier for future unknown releases.
- `Rules` covers changes to `examples/gitlab/rules.json`, recommended OCR built-in rules, or the recommended OCR allowlist. It is present in 0.4.1 for the Go, PHP/Composer, Prisma, and Protocol Buffers changes even though the toolkit-owned `rules.json` content is unchanged.
- Keep BL-015 and BL-016. Refine BL-017/M5 to reuse OCR token, cost, and budget telemetry and limit toolkit-owned work to missing GitLab lifecycle, evidence/MCP, and posting signals.
- Complete repository planning closure in the final release branch before publication. Do not require a post-release closure PR.

### Work Queue

0. [x] Create tracking issue #35 and open the implementation branch from current `main`.
1. [x] Record qualification evidence for OCR 1.8.1 and 1.8.2; update the compatibility manifest and all recommended runtime, preflight, example, CI, and documentation pins to 1.8.2.
2. [x] Support `budget_exceeded`, `summary.budget_exceeded`, and `token_budget_reached` as a partial warning outcome while preserving findings and usage metadata.
3. [x] Authenticate compatibility metadata requests without forwarding credentials to release assets or diagnostics.
4. [x] Add conditional emoji Towncrier categories, the 0.4.1 `Rules` entries, and an exact GitHub Release `Full Changelog` link.
5. [x] Reconcile BL-017/M5 and document the upstream-impact classification; keep BL-015/BL-016 unchanged.
6. [x] Run targeted tests, full quality, Gitleaks, diff checks, distribution checks, and Linux amd64 OCR contract probes.
7. [x] Merge the protected implementation PR and verify the resulting TestPyPI development publication.
8. [x] Prepare `release/v0.4.1` with the final changelog, release authorization metadata, next development line, validation evidence, and repository planning closure.
9. [x] Hand stable TestPyPI/PyPI 0.4.1, exact tag and immutable GitHub Release, hash, provenance, and supported-Python verification to the release workflow and external issue/goal closure; no post-release repository PR is required.

### Validation Evidence

- Local Linux amd64 qualification probes completed for OCR 1.8.1 and 1.8.2: all release assets and `sha256sum.txt` matched, consumed CLI/preview/result contracts passed, and both candidates were compatible.
- Upstream impact review: OCR 1.8.1 adds budget termination fields, Go built-in guidance, and Prisma allowlist support; OCR 1.8.2 adds PHP/Composer built-in guidance and Protocol Buffers allowlist support. GitHub Action, VS Code, viewer/Pages, and unrelated provider/URL/help fixes do not require toolkit runtime adaptation.
- The scheduled compatibility run `30615923070` failed before qualification because anonymous GitHub metadata access returned HTTP 403 rate-limit exhaustion; authentication is therefore part of this correction.
- Compatibility manifest validation accepts the reviewed 1.8.1 -> 1.8.2 sequence, exact evidence hashes/assets, 1.8.2 recommendation, and 1.8.2 monitoring floor while preserving the conservative machine classifier.
- Targeted compatibility, release-note, review-runner, posting, integration, and evidence-MCP regressions pass. The 0.4.1 Towncrier draft contains non-empty `🚀 Features`, `🐛 Bug Fixes`, `📖 Documentation`, and five separate `🧩 Rules` entries; empty categories and conventional prefixes are absent.
- BL-015 and BL-016 remain unchanged. BL-017 and M5 now explicitly reuse OCR token/cost/budget telemetry and restrict future toolkit telemetry to demonstrated GitLab lifecycle, evidence/MCP, posting, and review-value gaps.
- `scripts/quality.sh check` passes with 494 tests and 35 subtests at 78.73% coverage, plus Ruff formatting/lint, strict mypy, and Bandit. Gitleaks and `git diff --check` pass; wheel and sdist pass Twine and clean Python 3.12 install/CLI smoke tests.
- A disposable release build renders exact conditional emoji headings, five separate `🧩 Rules` entries without conventional prefixes, and `**Full Changelog**: https://github.com/xeonvs/open-code-review-toolkit/compare/v0.4.0...v0.4.1`.
- Implementation PR #36 merged as `5c205a7f59a32556264957c4b70eb0517521cdb9` after every required check passed and no review threads remained. TestPyPI development run `30623803468` published and installed immutable `0.4.1.dev2+g5c205a7f5` artifacts successfully.
- The final release branch renders the 0.4.1 changelog, authorizes reproducible artifacts from source epoch `1785493846`, establishes `0.4.2` as the next development line, and leaves no repository planning closure for after publication. Issue #35 remains the external stable-publication tracker.
- Release-branch validation passes 494 tests and 35 subtests at 78.73% coverage plus release-specific authorization/documentation tests, Gitleaks, and diff checks. Two independent 0.4.1 builds are byte-identical: wheel SHA-256 `d71d64cd2d40fa3d09e7d849bd42ab17f5339b57e6589be7299cb0332cb2b033`, sdist SHA-256 `3dfee22ca57ca8941a946e928c5cb4f9e2a0e61e6bad1199b5df359480ef821f`; Twine, exact metadata/content checks, and clean Python 3.12/3.14 installs pass.

<a id="plan-toolkit-0-4-0"></a>

## Completed Plan: Implement M1 evidence architecture for v0.4.0

Status: completed; stable release and external reconciliation verified
Owner: Codex
Last Updated: 2026-07-31
Release Classification: release-required
Target Stable Version: 0.4.0
Tracking Issue: #30

### Goal

Replace the bounded legacy Markdown context generator with a schema-versioned repository evidence engine, base/head snapshots and typed deltas, compact bootstrap projection, and a built-in read-only MCP server. Preserve all safe legacy facts through semantic parity checks, remove the legacy public contract only after end-to-end verification, and improve GitLab review outcome rendering.

### Work Queue

0. [x] Refresh the zero-runtime-dependency build/test toolchain and pinned GitHub Actions from authoritative upstream release metadata. The 12 direct build/dev requirements have a combined declared floor of Python 3.10 and no declared upper bound; the already approved M1 toolkit contract remains Python 3.12 through 3.14. The complete locked toolchain and 524 tests plus 53 subtests pass separately on 3.12, 3.13, and 3.14, while 3.15 remains unclaimed until the complete toolchain and project suite are qualified there. All 11 Action repositories resolve their documented stable tags to the pinned immutable SHAs. The isolated quality gate passes formatting, lint, strict typing, Bandit, 524 tests plus 53 subtests, and 78.37% coverage. Fresh wheel/sdist artifacts pass Twine 7, zero-runtime-dependency metadata checks, and Python 3.12 wheel/Python 3.14 sdist smoke installs. Package metadata and CI remain the version source of truth; the README development notice no longer duplicates Python numbers. This is release-deferred work for 0.4.0 and remains a separate signed checkpoint from legacy removal.

1. [x] Update the effective local OCR binary to verified upstream v1.8.0 while retaining a rollback copy.
2. [x] Freeze legacy context behavior and upstream OCR v1.8.0 result contracts in synthetic tests and fixtures.
3. [x] Implement the dependency-free evidence schema, bounded store, redaction-before-storage, deterministic identities, and serialization (BL-004).
4. [x] Implement immutable base/head file snapshots and repository-file deltas with explicit missing, both rename sides, deletion, symlink, submodule, and shallow-clone behavior (first BL-005 slice).
5. [x] Complete typed dependency/runtime/container/guidance collection and deltas for both refs without routing facts through legacy Markdown (BL-005). The typed-only path, source-aware identities, container images, application/infrastructure pins, guidance, Ansible topology/Galaxy parity, and Python, JavaScript, Go, and Composer/PHP declarations/locks are implemented and validated. The v0.4 package/runtime floor is Python 3.12, matching the documented `python:3.12-slim` CI integration and allowing the standard-library TOML parser to remain dependency-free, with tested support through Python 3.14. Missing lockfiles remain represented as absent resolved facts rather than an invented error: only a present candidate can be malformed or unavailable.
   - Ecosystem parser boundaries are final before implementation: shared normalized contracts live in `evidence.manifest_model`, orchestration and immutable reads stay in `evidence.collectors`, and each ecosystem owns a dedicated parser module. JavaScript, Go, and Composer/PHP must be implemented directly in their final modules, without temporary duplicate parsers in the orchestrator.
   - JavaScript checkpoint: `evidence.javascript_manifests` directly preserves `package.json` Node/npm/Yarn/pnpm runtime and package-manager constraints, production/development/peer/optional declarations, npm lock v1-v3, Yarn Classic/Modern, and pnpm v5-v9 resolved facts without a YAML runtime dependency.
   - Go checkpoint: `evidence.go_manifests` directly preserves module identity, Go language/toolchain/GODEBUG declarations, direct/indirect requirements, replace/exclude/tool/retract/ignore semantics, and `go.sum` module/content checksum pairs as separately typed resolved evidence.
   - Composer/PHP checkpoint boundary and test matrix: implement `composer.json` and `composer.lock` directly in `evidence.composer_manifests`, while `evidence.collectors` retains only registry and immutable-read orchestration. Preserve package identity, production/development requirements, PHP/HHVM/extension/Composer platform constraints, configured platform overrides, provide/replace/conflict semantics, stability preferences, locked production/development packages, lock platform requirements, content/plugin API metadata, safe source classifications and references, aggregate bounds, malformed-versus-missing lock behavior, base/head deltas, and built-in MCP visibility. Repository-controlled URLs and paths remain untrusted and are classified or redacted rather than copied as credentials.
   - Composer/PHP checkpoint validation: the dedicated parser preserves the planned declaration, virtual-platform, lock, safe-source, bounds, delta, and MCP contracts; legacy PHP context facts remain covered semantically while the typed model adds scopes and resolution metadata. Focused parser/collector tests pass with 38 tests; the full gate passes with 504 tests and 53 subtests at 77.97% coverage; strict typing/lint, a fresh package build with metadata checks, and Python 3.12 wheel/Python 3.14 sdist smoke installs pass.
   - Remaining application/infrastructure checkpoint boundary: implement conservative version-like key and nested-image extraction directly in `evidence.infrastructure`, register only the legacy-supported declarative configuration surfaces, and collect them from immutable base/head blobs. Emit `application.version` for non-image pins and the established image kinds for image pins, with path/key/name identities that turn upgrades into `changed` deltas. Preserve fixture/environment exclusions, interpolation and unpinned/latest rejection, schema/API/config metadata exclusions, redaction, deterministic aggregate bounds, bounded diagnostics, and MCP visibility. Extend the dedicated Ansible topology parser only for history-backed core-manifest gaps proven by the migration matrix; do not turn this compatibility checkpoint into an unbounded framework detector.
   - Application/infrastructure checkpoint validation: conservative declarative pins, nested image tags/digests, Dockerfile stages, exclusions, interpolation/latest rejection, redaction, aggregate bounds, application/image changed deltas, normalized parity tokens, Ansible role vars, and MCP visibility pass 45 focused tests. The full gate passes with 510 tests and 53 subtests at 78.27% coverage; strict typing/lint, a fresh package build with metadata checks, and Python 3.12 wheel/Python 3.14 sdist smoke installs pass.
6. [x] Separate collection, storage, planning, and rendering completely; remove legacy rendering only after the typed path passes its removal gates (BL-006). The lifecycle/composition checkpoint is sealed in signed commit `dda2efe`. The removal audit maps every migration-matrix row to typed tests, preserves renderer-independent GitLab CI/docs/project-rule/test-integrity contracts, and proves 11/11 non-empty legacy dependency/image facts on immutable refs with no missing fact. Public `context`, temporary `evidence-parity`, `ocr_toolkit.context`, `ocr_toolkit.evidence.parity`, and the `repository.context` schema kind are removed. The full isolated quality/security gate passes 412 tests plus 35 subtests at 77.41% coverage; fresh wheel/sdist artifacts pass Twine, contain no legacy modules or runtime dependencies, and clean-install on Python 3.12/3.14 without exposing legacy CLI commands.
7. [x] Integrate compact bootstrap and deterministic JSON projections into one toolkit-owned review preflight; `.review-context/evidence.json` and `.review-context/bootstrap.md` are private implementation artifacts, not a separately configured user workflow.
8. [x] Complete the bounded read-only `ocr_toolkit_evidence` stdio MCP integration (BL-007): toolkit-owned artifact discovery, toolkit-owned internal module registration, review-lifecycle startup, bounded diagnostics, and proven non-zero calls from real OCR. OCR's registry contains independent MCP entries: the built-in evidence server is always one mandatory entry, while every retained or newly configured local/remote server remains a separate optional entry. Current architecture reserves the mandatory server and tool names, derives bootstrap inventory from the exact registry, owns artifact preparation inside `ocr-ci review`, and never passes evidence JSON to OCR. Real OCR 1.8.0 exposed two compatibility gaps before its LLM review could prove use: its exact `go-sdk` v1.6.1 client negotiates MCP revision `2025-11-25`, and a clean-start review showed that registering the bare `ocr-ci` console script incorrectly depended on the caller's `PATH`. Both are corrected. The registry now uses the current absolute Python executable with isolated mode and an internal module entrypoint, so editable and wheel installs remain self-contained with an empty `PATH` and an untrusted repository shadow package cannot intercept imports. Python lifecycle contracts, a 87-test/15-subtest focused gate, a clean Python 3.12 wheel adversarial subprocess probe, the full 415-test/35-subtest quality/security gate at 77.38% coverage, and a process-level initialize/initialized/ping/list/summary/list/get probe through exact Go MCP SDK v1.6.1 pass. The two completed real OCR reviews then recorded 165 and 220 verified `ocr_toolkit_evidence` calls respectively, proving non-zero use through the integrated lifecycle and closing the item.
9. [x] Improve GitLab summary outcomes, zero-counter suppression, severity/category presentation, and the default-on `OCR_POST_EMOJI` switch.
   - MCP usage reporting maps OCR's structured per-tool counters back to the exact validated independent server registry used by that review. The review step atomically binds only positive per-server counts in a schema-versioned toolkit receipt to the private result; posting consumes that receipt rather than reconstructing environment-dependent MCP state. Commands, URLs, headers, arguments, inputs, results, repository contents, and configured-but-unused entries remain absent. Cross-server tool-name collisions are rejected because OCR exposes one global tool namespace and attribution would otherwise be ambiguous.
   - Telemetry remains outside M1. Upstream OCR already owns provider-level duration, LLM/token, and tool-call metrics. M1 E2E will record whether structured OCR results and existing telemetry expose mandatory evidence-MCP/optional-MCP usage and lifecycle outcomes adequately; M5/BL-017 now starts with that gap audit and permits a no-new-layer conclusion.
   - Lifecycle checkpoint validation passes 522 tests and 53 subtests at 78.17% coverage with formatting, lint, strict typing, and the medium-confidence/medium-severity source security scan clean. Its 183 focused tests and 27 subtests cover registry readback, independent entry preservation, global tool-name collision rejection, evidence summary/list/get self-query, mandatory-use gating, skipped results, optional-server attribution, reserved receipt spoofing, symlink/hard-link rejection, bounded/deep result parsing, reporting, and zero-use omission. A fresh wheel and sdist pass Twine and zero-runtime-dependency metadata checks; Python 3.12 wheel and Python 3.14 source-distribution smoke installs pass. The subsequent real OCR reviews supplied the remaining non-zero-use evidence for item 8.
10. [x] Audit the complete pre-M1 repository-context pipeline from the merge-base and repository history, then run legacy/evidence semantic parity cycles, component-level MCP verification, and a full synthetic GitLab-style OCR v1.8.0 E2E without posting. The history-backed coverage matrix maps every legacy source and contract to typed evidence or an explicit removal. The temporary oracle matched all 11 non-empty comparable dependency/image facts with none missing. The completed public `ocr-ci review` release gate reviewed one synthetic source change, recorded one `ocr_toolkit_evidence` call in both OCR counters and the toolkit receipt, and kept private `.review-context` artifacts outside Git. The real-engine synthetic E2E remains a manual release gate: stable automated coverage stays at component, clean-install subprocess, real protocol-client, and artifact-boundary layers unless repeated releases justify a permanent local HTTPS/LLM harness.
11. [x] Remove the legacy implementation, CLI, environment contract, and compatibility path after the new path passes all gates. Signed checkpoint `c2caa9d` removed the renderer, CLI/environment surface, compatibility assertions, and temporary parity code only after the migration matrix and non-empty history-backed oracle passed; the final integration suite asserts that the retired contract is absent.
12. [x] Reconcile user, agent, engineering, security, configuration, roadmap, plan, and backlog documentation.
13. [x] Run complete validation, review the full feature diff with OCR through the new local MCP, fix valid findings, create and verify the final signed checkpoint, and finish the local ready-PR audit.
14. [x] Add and run an explicit local pre-push Gitleaks gate that uses the same explicitly pinned scanner version, configuration, and first-parent branch-history scope as CI, and record the missed-gate failure mode in contributor and agent guidance. The wrapper is the single pin owner, exposes a side-effect-free `--version` for the hosted security job, and remains separate from the Python quality environment. TestPyPI and stable-release workflows do not duplicate the dedicated security job. The exact Gitleaks 8.24.3 binary was checksum-verified from its upstream release before installation; the local first-parent feature-history scan and focused shell/contracts tests pass.
15. [x] Update the ready feature PR without prematurely closing issue #30, verify its exact current head, required review, resolved conversations, and Actions state, and merge through the protected `main` branch. PR #31 kept issue #30 open, all current-head required checks passed, no review conversations remained, and GitHub created verified signed squash commit `53f559ab2db4918d990575063c836ae99ee871b2` on `main`. The active ruleset's obsolete Python 3.10 required contexts were corrected to the implemented Python 3.12 endpoints before merge.
    - The first `main` development-build attempt exposed a gate-integration omission: `scripts/quality.sh check` correctly failed closed because the hosted TestPyPI job had not provisioned the newly required scanner. The correction adds one checksum-verified Linux installer shared by the TestPyPI and stable-release workflows, with focused success-path and workflow-contract regressions; it will be delivered through the normal protected hotfix PR before retrying publication.
16. [x] Verify the resulting immutable TestPyPI development build and independently smoke-install its wheel and source distribution. TestPyPI workflow run 30614810741 published and read back `0.3.1.dev24` from exact signed `main` SHA `0396dd200e6097e2a650a2ce07c5236bcd8ff33f`; the run artifact and registry wheel/sdist SHA-256 values matched byte-for-byte, metadata retained `Requires-Python >=3.12,<3.15` with zero runtime dependencies, and independent clean installs passed for the wheel on Python 3.12 and sdist on Python 3.14.
17. [x] Prepare a signed `release/v0.4.0` branch and exact-title release PR with the stable version marker, deterministic source epoch, generated Towncrier changelog, and next development line. The branch starts at exact `origin/main` SHA `0396dd200e6097e2a650a2ce07c5236bcd8ff33f`; its deterministic source epoch is `1785484860`, and the stable and next development lines are both 0.4.0. The pre-commit release checkpoint passes the explicit first-parent Gitleaks gate and the complete Python 3.12 matrix: 480 tests plus 35 subtests, 79.04% coverage, Ruff formatting/checks, strict mypy, and Bandit. Two independent deterministic builds produce byte-identical artifacts (`665ba25e375cb91df1815c2a7d27dda6605872121b8f5bfd76a08495ae8e7f15` wheel, `9c7bd39e7fc613ba3686a31c7d0afbdedb30297c2c1bb7da74f213c9f8eada8b` sdist); Twine, exact metadata/content, zero runtime dependencies, Python 3.12.13 wheel, Python 3.14.6 sdist, runtime version, and CLI smoke checks pass. Signed checkpoint `8f7b72e15991fc09c0f9251c5dad3352f992d2cc` and exact-title release PR #33 complete the item.
18. [x] Verify and merge the protected release PR, then monitor stable TestPyPI and PyPI publication, the annotated `v0.4.0` tag, immutable GitHub Release, attestations/provenance, and exact artifact hashes. All exact-head checks passed before PR #33 merged as GitHub-signed commit `251315dda9e025ad0ca76dd28011e6c85903aa9c`. Release workflow run `30617233026` completed every authorize, build, attestation, TestPyPI, PyPI, registry-smoke, and GitHub Release job. Both registries and Release assets expose the reviewed hashes, `gh attestation verify` accepts both distributions, the annotated tag resolves to the merge commit, and GitHub API version `2026-03-10` reports `immutable: true`.
19. [x] Independently smoke-install the published wheel on Python 3.12 and source distribution on Python 3.14, close issue #30, reconcile M1 as established across the plan, roadmap table/diagram, and backlog, and verify the final external state. Files downloaded directly from PyPI match the reviewed hashes and pass runtime-version plus CLI smoke checks on Python 3.12.13 and 3.14.6; issue #30 is closed. The final planning-only closure change removes only completed BL-004 through BL-007 and promotes M1 consistently in the roadmap table and diagram.

   - Closure-documentation checkpoint: the history-backed parity/removal and public-invocation synthetic E2E gates are now reconciled across this plan, the roadmap completion signal, and the active BL-004 through BL-007 scope. User operations guidance now documents the H1 summary, distinct skipped/clean outcomes, positive clean report, zero-counter omission, used-MCP inventory, and the default-on emoji switch. The complete quality gate passes formatting, lint, strict typing, Bandit, 453 tests plus 35 subtests, and 78.31% coverage. The final OCR/security results and ready-PR state recorded below subsequently closed item 12.
   - The first completed full OCR review covered 42 files, made 423 core tool calls including 165 verified `ocr_toolkit_evidence` calls, and returned 31 findings (10 high, 20 medium, 1 low). Root-cause analysis grouped them into post-hoc rather than streaming bounds, byte/code-point confusion, incomplete hostile-environment isolation, validate-on-write without validate-on-read, canonical-only parser fixtures, non-atomic cross-references, mocked rather than installed subprocess contracts, and drift between report outcomes. Durable principles, agent defaults, failure-mode corrections, and the contributor boundary checklist were updated before the findings were corrected and the full OCR review was repeated.
   - The second completed full OCR review covered 69 files, made 549 core tool calls including 220 verified `ocr_toolkit_evidence` calls, and returned 35 findings. Corrections are grouped by root-cause class: sibling trust boundaries, NUL-safe Git records, applicability-aware identities, semantic parser variants, exact negative-test paths, and hermetic synthetic Git repositories. Per owner direction, a third local OCR review is intentionally not run; ordinary quality/build matrices and Codex Security remain the independent final gates.
   - The second-OCR correction implementation now passes the complete Python 3.12 quality gate: formatting, Ruff, strict mypy, Bandit, 472 tests plus 35 subtests, and 78.54% coverage. Fresh wheel and sdist artifacts pass Twine, hash-locked isolated installs, zero-runtime-dependency metadata checks, and restricted-`PATH` `ocr-ci --help` smoke tests on Python 3.12. Per owner direction this correction checkpoint does not repeat the already completed 3.13/3.14 M1 qualification.
   - Codex Security diff review of the complete M1 merge-base-to-checkpoint range validated two root-cause classes. Repository replacement refs could substitute content behind authenticated SHAs in both evidence collection and GitLab remap helpers; the existing OCR config reader also captured an unbounded linked file before JSON parsing. The correction disables replacement objects, isolates process/global/system Git configuration for both sibling readers, bounds config reads/writes at one MiB through a regular single-link descriptor, and adds real replacement-ref, hostile-environment, oversized, UTF-8 path, and hard-link regressions. No third OCR review was run per owner direction. The post-security Python 3.12 quality/artifact gates and signed checkpoint recorded below subsequently closed item 12 and the non-PR portion of item 13; complete publication was later authorized and is tracked by items 15 through 19.
   - First OCR correction checkpoint: record and delta values are recursively immutable; deserialization rejects type-confused metadata and limits; and persisted record, delta, top-level diagnostic, and snapshot diagnostic payloads are re-redacted and re-bounded before MCP exposure. Adversarial mutation, secret, oversized-value, diagnostics, snapshot-reference, and metadata regressions pass in the 225-test/15-subtest evidence/review/docs gate with Ruff, formatting, strict mypy, and whitespace checks clean. A corrected process-level cProfile workload validates 200 real `summary`/`list`/`get` cycles (600 tool calls, 603 responses, zero errors) over the 340-record review store: wall time under profiling is 0.964 seconds, strict cold read accounts for 0.829 seconds, and an unprofiled run measures 0.210 seconds cold read plus 0.090 ms per steady-state call. The previous 0.596-second profile is retained only as a transport/error-dispatch baseline because its request generator omitted `action`; it is not evidence for successful tool semantics. Remaining OCR findings stay open.
   - Second OCR correction checkpoint: all parser-semantic findings now have direct regressions for Ansible indentation and Galaxy key order/scalar sources, standard and named `pylock` manifests, Composer malformed optional repository URLs and disabled platform entries, quoted Go tokens, infrastructure digest fields and plain variables, npm v1 traversal coverage, Poetry interpreter declarations, and stable list-valued alternatives. Boundary regressions additionally cover atomic snapshot admission, hard-linked artifacts, notification response suppression, streaming MCP request limits, inert bootstrap diagnostics, hostile Git object-store/replacement overrides, immutable OCR ref binding with non-diff option preservation, timeout normalization, short result reads, cyclic warning objects, consistent clean/skipped MCP reporting, and quick-action-safe fallback fences. Focused validation completed with 78 parser tests, 140 evidence/MCP/review-runner tests, and 100 posting tests plus 12 subtests. The complete quality gate passes 453 tests and 35 subtests at 78% coverage with Ruff, formatting, strict mypy, Bandit (zero medium/high findings), and `git diff --check` clean. The signed checkpoint is `fe8f62b`; its ED25519 signature is verified.
   - Post-checkpoint qualification reruns all 453 tests plus 35 subtests independently on Python 3.12.13, 3.13.4, and 3.14.6. Fresh wheel and sdist artifacts pass Twine and installed `ocr-ci --help` smoke tests under restricted `PATH` on Python 3.12 and 3.14 respectively. The public `ocr-ci review` flow then completes against a fresh synthetic repository and deterministic local HTTPS LLM gateway: evidence preflight binds the immutable base/head pair, creates four private records, OCR reviews exactly the intended source change, calls `ocr_toolkit_evidence` once, and the validated result records `tool_calls.total=1`, `tool_calls.by_tool.ocr_toolkit_evidence=1`, and `_ocr_toolkit.mcp_usage.ocr_toolkit_evidence=1`. The diff contains only the synthetic source file; `.review-context` remains outside Git and both internal artifacts are mode `0600` under a `0700` directory. The temporary localhost certificate/trust entry, gateway, repository, and OCR home are test-only and removed after evidence capture.

### Validation And Review Gates

- Every completed implementation slice receives a signed checkpoint commit after targeted tests, `scripts/quality.sh check`, `git diff --check`, and plan/backlog reconciliation.
- Python 3.12 is the minimum toolkit runtime for v0.4.0. This is an intentional release-required contract change rather than a bundled TOML backport: package metadata, Ruff/mypy targets, Linux/macOS endpoint CI, release smoke documentation, backlog version references, and clean wheel/sdist installation must agree on the supported 3.12-3.14 range. The recommended GitLab image remains `python:3.12-slim`; repository evidence may still describe any target project's Python constraints and is not limited to the toolkit's own runtime range.
- Review each committed diff for correctness, architecture, security, compatibility, tests, documentation, and hidden legacy dependencies. Fix every valid finding in a signed follow-up commit and repeat the gate before starting the next slice.
- Semantic parity compares facts, trust, ref, component, and provenance rather than exact Markdown. Any unexplained divergence starts another analysis, implementation, test, and review cycle.
- Legacy parity is history-backed rather than renderer-only: characterization fixtures and the temporary projection are checked against the context collectors and orchestration as they existed at the M1 merge-base, including their evolution where later commits fixed meaningful omissions. Similar prose or dependency counts alone are insufficient evidence of parity.
- Production collection is now typed-only: `ocr-ci review` no longer invokes the legacy renderer or persists `repository.context`. The legacy projection was attached only by an explicit migration-oracle helper used by parity tests before the parity gate closed. Immutable candidate blobs are size-checked and read in bounded Git batches (two `cat-file` processes per ref) rather than one process per file. Batch-check and response framing are adversarially validated; oversized candidates degrade individually with explicit coverage diagnostics, and YAML collection is restricted to changed or repository-context-relevant paths. History-backed migration coverage is tracked in `docs/engineering/evidence_migration_matrix.md`; resolving its partial/pending rows and removing the public legacy namespace closed BL-006.
- Typed evidence now owns deterministic multi-category changed-path classification and manifest discovery without importing the legacy context namespace. One immutable internal manifest registry owns path matching, ecosystem metadata, and bounded parser dispatch for every implemented ecosystem. Dependency/runtime identities include the immutable source path, while CI/container image identities separate component name from version so version updates produce one `changed` delta. Deleted-path categories retain base-ref provenance and target-repository trust.
- A separate bounded Ansible topology collector now describes root playbooks, canonical role metadata/defaults, inventory paths and immediate inventory groups from immutable blobs. Synthetic integration verifies that these records survive the common store and are queryable through filtered MCP `list` plus stable-ID `get`; generic root YAML and host/group variable payloads are not misclassified. Galaxy evidence distinguishes roles and collections, preserves redacted sources and explicit missing-version state, supports documented shorthand and bounded immutable include graphs, and diagnoses malformed, conflicting, missing, cyclic, escaping, depth-limited, and truncated input.
- Review-invocation evidence is isolated from immutable repository collectors: a GitLab provider adapter supplies only bounded numeric project/pipeline/job/MR identifiers to provider-neutral normalized descriptors with `invocation` trust. URLs, refs, tokens and arbitrary environment values are never read. Mutable locally installed tool versions remain intentionally excluded and are represented by an explicit toolkit-owned coverage diagnostic rather than an implicit context loss.
- Final validation includes unit, contract, adversarial, packaging, clean-install, protocol, subprocess MCP, source/head snapshot, failure-mode, and real OCR v1.8.0 E2E checks.
- Architecture correction implemented for the review boundary: evidence preparation, fixed internal artifact paths, compact-bootstrap injection, the BL-007 composition foundation, and bounded lifecycle diagnostics now belong to `ocr-ci review`. The public `OCR_EVIDENCE_STORE_PATH` contract and user-facing `evidence-build` workflow are removed; only the hidden lower-level stdio launch target remains for OCR, with toolkit-owned defaults. Collection uses the exact immutable OCR refs, completes before OCR starts, and fails closed on invalid refs, unsafe artifacts, collection, composition, or health-summary failures. The reserved built-in server is mandatory and authoritative; validated external MCP definitions compose alongside it and cannot shadow or remove it, including replacement mode.
- Bootstrap planning must describe the complete composed capability set available to OCR: always the built-in evidence tool plus only the explicitly allowlisted external MCP servers/tools that survive validation. It must not expose secrets, setup commands, URLs, headers, or stale OCR config entries. The generated MCP config and bootstrap therefore come from the same validated composition plan, preventing capability drift between instructions and the actual OCR tool loop.
- M1 implements only the provider-neutral composition foundation required for BL-007 correctness: reserved built-in server/tool names, deterministic augmentation by already-supported validated external definitions, and shared capability rendering. BL-013 remains in M3 for provider examples, external-reference instructions, threat-model-dependent integrations, and the broader composition product surface; M1 must not claim BL-013 complete or bypass BL-011/BL-012 dependencies.
- Real OCR v1.8.0 integration exposed three distinct fail-open boundaries that remained part of the gate rather than being hidden by handwritten mocks: OCR first treated the built-in server's prose `setup` value as a shell command; its exact Go SDK then required MCP revision `2025-11-25`; and a clean-start run showed that a bare `ocr-ci` registry command depended on the caller's `PATH`. Empty setup, protocol negotiation, and path-independent isolated launch were corrected and covered by editable plus clean-wheel adversarial subprocess checks. Both completed full OCR reviews later produced structured non-zero `ocr_toolkit_evidence` use.
- Corrected preflight/composition validation: 432 tests and 53 subtests pass with 75.13% coverage; Ruff formatting/checks, strict mypy, Bandit, build metadata, and repository contracts pass through `scripts/quality.sh check`. A real local automatic preflight for `origin/main..HEAD` created a `0700` internal directory and `0600` store/bootstrap, collected 134 records, wrote an empty built-in `setup`, and kept config/bootstrap capability inventories identical. A second preflight in replacement mode retained the mandatory built-in server and added a synthetic allowlisted external server in both outputs. The two subsequent full OCR reviews closed the real-use gate with 165 and 220 verified built-in MCP calls.
- Baseline before M1 runtime changes: 368 tests and 41 subtests passed. OCR v1.8.0 structured skip, clean result, subtask error, severity, and category contracts are pinned in synthetic fixtures sourced from upstream tag v1.8.0. Existing context regression coverage remains the legacy behavior baseline.
- BL-004 evidence model validation: 17 focused evidence/OCR contract tests pass; Ruff and mypy pass. Self-review added strict unknown-field rejection, mapping-key redaction, sensitivity promotion, and deduplication that supports structured JSON values. The v0.4.0 Towncrier draft was rendered successfully, and fragment authoring guidance now covers grouped related outcomes without using the changelog as a backlog.
- Snapshot/projection checkpoint validation: 26 focused evidence tests pass; Ruff and mypy pass. Synthetic two-commit repositories cover add, delete, both rename sides, changed blobs, unavailable commits, symlink refusal, tree/blob limits, semantic retention of the bounded legacy context, and explicit compact-bootstrap truncation. Self-review found that the transitional collector still calls `build_context()` and reparses Markdown; BL-005 and BL-006 therefore remain incomplete until typed collectors are projection-independent.
- MCP protocol checkpoint validation: 88 focused evidence, CLI, MCP-configuration, and runtime-helper tests plus 15 subtests pass; Ruff and strict mypy pass. The server protocol itself completes initialize, tools/list, summary, list, get, cursor binding, request/response bounds, and safe-error contracts over stdio, while generated private artifacts remain mode 0600 and existing parent-directory permissions are preserved. A direct local stdio handshake initially exposed the misclassified `setup`; the corrected integrated review lifecycle and later real OCR call receipts closed BL-007.
- Version ownership self-review: MCP server metadata now reads the installed package version from centralized `ocr_toolkit.__version__`, generated by `hatch-vcs` from SCM. The durable project principle forbids duplicated toolkit release literals and distinguishes release versions from independently versioned schema, wire-protocol, fixture, and qualified-upstream contracts.
- GitLab presentation checkpoint: posting summaries now use `# Open Code Review summary`, preserve the exact structured OCR v1.8.0 clean/skipped/warning/error message, suppress zero tool-call and posting counters, and render optional status, severity, and category emoji. `OCR_POST_EMOJI` is default-on and disables all toolkit-added emoji without rewriting OCR content. Focused posting validation passes with 97 tests and 24 subtests; the full suite passes with 417 tests and 53 subtests; Ruff and strict mypy pass.
- Typed collector checkpoint: immutable base/head collectors now parse Python, JavaScript/npm, Go, Composer, Ansible, container/CI image, project-guidance, and accepted-decision evidence directly from bounded Git blobs; typed facts no longer come from reparsing legacy Markdown. Semantic dependency/runtime/image deltas are explicit, malformed manifests degrade to bounded diagnostics, and changed head guidance cannot self-authorize policy. Focused collector/snapshot validation passes with 17 tests; the full suite passes with 422 tests and 53 subtests; Ruff and strict mypy pass. At this checkpoint legacy Markdown remained only as the temporary parity projection; the later parity and removal checkpoints closed BL-006.
- Public integration migration is corrected: the synthetic GitLab example calls one `ocr-ci review` lifecycle, which prepares its own private store/bootstrap, composes MCP configuration, reports bounded preflight diagnostics, and invokes OCR. It no longer exposes evidence paths, `OCR_EVIDENCE_STORE_PATH`, a separate `evidence-build`, manual built-in `mcp-config`, or caller-owned `--background-file`. The legacy context command remains physically present only until history-backed parity and integrated E2E pass.
- Semantic parity checkpoint: `ocr-ci evidence-parity` compares independently typed dependency/image records against the temporary legacy projection and fails when comparable coverage is absent or missing. The current branch report is clean with 11 comparable facts matched and none missing. Language documentation consistently keeps English as the default and presents Russian only as one localization example. The first full run exposed one stale documentation assertion; the test was corrected to enforce the intended default/example wording.
- Python checkpoint validation: 29 collector tests cover PEP 621/735, Poetry, recursive requirements, uv/Poetry/Pipenv/pylock facts, unsafe include modes, redaction, changed lock-version deltas, missing versus malformed locks, and built-in MCP visibility. `scripts/quality.sh check`, `uv lock --check`, wheel/sdist metadata checks, and isolated Python 3.12 wheel plus Python 3.14 sdist smoke installs pass.
- JavaScript checkpoint validation: focused tests cover scoped `package.json` declarations, runtime/package-manager constraints, aggregate bounds, npm lock v1-v3, Yarn Classic/Modern, pnpm v5-v9, malformed/unsupported contracts, redacted source classification, changed locked versions, and built-in MCP visibility. Read-only qualification against current upstream-generated Yarn Classic/Modern and pnpm v6/v7/v8/current locks produced bounded typed facts with explicit truncation notices. `scripts/quality.sh check`, wheel/sdist metadata checks, and isolated Python 3.12 wheel plus Python 3.14 sdist smoke installs pass.
- Go checkpoint validation: focused tests cover module identity, language/toolchain/GODEBUG declarations, direct and indirect requirements, module/local replacements, exclusions, tool/retract/ignore directives, aggregate bounds, module and go.mod checksums, safe malformed-line diagnostics, base/head changes, and built-in MCP visibility. Read-only qualification compares the parser output with `go mod edit -json` and checks real generated `go.sum` pairs. `scripts/quality.sh check`, wheel/sdist metadata checks, and isolated Python 3.12 wheel plus Python 3.14 sdist smoke installs pass.
- Planning reconciliation at the implementation checkpoint kept M1 `next` until release completion and retained BL-004 through BL-007 as active acceptance criteria linked to issue #30. The stable-release closure recorded above now promotes M1 and removes those completed entries without altering the historical checkpoint evidence.
- Codex Security reviewed the complete M1 runtime/package diff through signed checkpoint `9a58ccf`: all 42 deterministic worklist rows were closed and two validated findings were corrected. Authenticated Git reads now share one isolation policy that disables replacement objects and inherited process/global/system configuration across evidence and inline remapping, and OCR configuration reads reject links and oversized payloads before bounded JSON decoding. The final Python 3.12.13 gate passes with 477 tests, 35 subtests, 79% line coverage, Ruff, strict mypy, and no Bandit medium/high findings. Fresh wheel and sdist builds pass Twine, contain zero runtime dependencies, install from hash-locked local requirements into isolated Python 3.12 environments, and run `ocr-ci --help` under restricted `PATH` from a hostile shadow-package working directory. A third OCR review was intentionally not run.
- The final local implementation checkpoint was signed and verified. At that checkpoint the branch contained only signed commits, `git diff --check` was clean, the worktree had no project changes, no extra worktrees or validation/profiling processes remained, and disposable OCR/build/quality artifacts were removed. The owner then authorized and completed the full v0.4.0 delivery cycle recorded in items 15 through 19.

### Release Delivery And Closure

- The owner explicitly authorized the complete release cycle on 2026-07-30. Proceed through the feature PR, protected merge, immutable TestPyPI development verification, release PR, stable publication, tag/immutable GitHub Release, provenance/hash checks, and supported-Python smoke installs without stopping at intermediate checkpoints.
- The feature and release PR merges remain the repository's protected human publication gates; do not bypass required checks, resolved-conversation requirements, signed-commit policy, or the workflow's fail-closed registry verification.
- Stable publication and the closure sequence are complete, so M1 is `established` in the roadmap and this release-required plan is closed.

<a id="plan-m0-reconciliation"></a>

## Completed Plan: Reconcile completed M0 planning state

Status: completed; planning sources reconciled and M1 entry state verified
Owner: Codex
Last Updated: 2026-07-28
Release Classification: no-release
Target Stable Version: not applicable

### Goal

Make the roadmap and backlog consistently represent M0 as completed after the verified 0.3.0 release closure, without changing runtime or published behavior.

### Work Queue

1. [x] Reconcile the M0 execution plan, protected repository state, release, issue, and compatibility-workflow evidence.
2. [x] Audit the release-closure instructions and history to identify why publication receipts were reconciled without reconciling the roadmap and future-work backlog.
3. [x] Mark M0 unambiguously established in every roadmap representation, use a documented status color legend for all milestone nodes, and remove completed M0 implementation items from the future-work backlog.
4. [x] Correct stale completed-item retention in the remaining backlog; restore unimplemented BL-004 as the ready entry point for M1.
5. [x] Add a durable release-closure instruction requiring status-bearing roadmap diagrams, tables, backlog, and execution plans to be reconciled together.
6. [x] Review the resulting planning diff, render the Mermaid graph with Mermaid CLI 11.16.0, validate status/dependency references and repository whitespace, and record post-change truth.

### Release Gates

- This is a planning-state correction only: no runtime, CLI, configuration, schema, integration, or packaging behavior changes.
- No Towncrier fragment or stable release is required.
- Mermaid colors encode status only: established is green, next is blue, planned is neutral gray, and conditional is amber. Nodes with mixed phases use the earliest actionable status, while the label retains the detailed phase split.

### Closure Evidence

- Repository history shows the 0.3.0 closure PR updated only `PLANS.md`; it did not perform the promised post-release cleanup of `ROADMAP.md` and `docs/codex/TASKS_BACKLOG.md`.
- The M0 feature commit also marked BL-004 complete even though its evidence-model deliverables were not implemented; source inspection confirms the model remains the first M1 implementation slice, so BL-004 is restored as `ready`.
- Mermaid CLI 11.16.0 rendered the roadmap successfully with all seven milestone nodes colored according to the documented status legend: one established, two next, three planned, and one conditional.
- Targeted stale-state and dependency searches plus `git diff --check` pass. Public runtime, package contents, CLI/configuration contracts, and release artifacts are unchanged.

<a id="plan-toolkit-0-3-1"></a>

## Completed Plan: Qualify OCR 1.8.0, add native remote MCP, and release v0.3.1

Status: completed; stable release, development-line verification, and external reconciliation verified
Owner: Codex
Last Updated: 2026-07-28
Tracking Issue: #24
Qualification Issue: #23
Release Classification: release-required
Target Stable Version: 0.3.1

### Goal

Human-qualify OCR 1.8.0 from the successful M0 workflow evidence, promote it to the tested and recommended baseline, expose its native Streamable HTTP MCP transport through the existing bounded toolkit configuration contract, correct the durable OAuth backlog boundary, and carry the complete result through stable 0.3.1 publication and external reconciliation.

### Fixed Decisions

- Start from clean protected `main` merge `3ddbb4e`, which is synchronized with `origin/main` and records completed 0.3.0 publication.
- OCR compatibility workflow run `30344510383` passed every machine probe for v1.8.0 and classified it `human-review-required`; issue #23 is the human qualification record. Promote only after recording the reviewed upstream impact and normalized evidence.
- Of the OCR 1.8.0 changes, only native remote MCP changes a toolkit-owned integration contract. The remaining upstream changes receive a concise compatibility/release impact review and no artificial toolkit implementation or roadmap work.
- Extend `OCR_MCP_SERVERS_JSON` with explicit `stdio` and `remote` transports. Missing `type` remains `stdio`; stdio remains a supported local and OAuth-proxy fallback. Remote authentication in 0.3.1 is limited to environment-backed static headers.
- Preserve zero runtime dependencies, bounded parsing, fail-closed validation, redacted output, synthetic public content, and minimal wheel/sdist contents.
- Keep `scripts/quality.sh` isolated and quiet: repair only its disposable environment when interrupted editable metadata lacks `RECORD`, then synchronize once and run checks without repeated package mutation.
- Keep new runtime functions purpose-documented and comment non-obvious security, compatibility, and state-transition decisions; record this durable expectation in `AGENTS.md`.
- Do not push or open the feature PR until implementation, full validation, multiple self-review/fix cycles, and exactly one final complete local OCR 1.8.0 review of `main..HEAD` are finished. Fix every actionable OCR finding and rerun deterministic validation without a second OCR review.

### Work Queue

1. [x] Reconcile current repository and external qualification state, close the stale M0 plan checkbox, create tracking issue #24, and branch from synchronized protected `main`.
2. [x] Promote OCR 1.8.0 in the compatibility manifest and all durable version/checksum pins using normalized workflow evidence and a recorded human conclusion; document why non-MCP upstream changes require no toolkit code.
3. [x] Add bounded native remote MCP parsing and OCR config projection with HTTPS-only URLs, environment-backed secret headers, sensitive-literal rejection, transport field separation, redaction, and backward-compatible stdio behavior.
4. [x] Update public configuration/security/compatibility documentation, synthetic examples, durable strategy/backlog boundaries, project-agent upstream-impact instructions, and Towncrier fragments. Reconcile the documented `OCR_MCP_REPLACE` behavior with runtime truth.
5. [x] Add positive, negative, adversarial, documentation, manifest, workflow, quality-environment, and distribution-content tests while retaining zero runtime dependencies and minimal published artifacts.
6. [x] Run targeted checks, the complete local validation matrix, and three self-review/fix cycles covering architecture/compatibility, security/redaction, and documentation/packaging/release completeness.
7. [x] Run exactly one final local OCR 1.8.0 review over the complete feature diff, retain ignored evidence, fix every actionable finding, and rerun the deterministic validation matrix without another OCR review.
8. [x] Update plan/backlog to post-commit truth, create signed feature commits, push the branch, open the non-draft feature PR, resolve review feedback, pass all protected checks, merge, and verify the exact immutable TestPyPI development artifacts, provenance, and smoke installs.
9. [x] Create signed `release/v0.3.1` from refreshed `main`, render and verify Towncrier release notes, open the exact-title release PR, pass all gates, merge, and monitor stable TestPyPI/PyPI/tag/immutable GitHub Release publication.
10. [x] Reconcile registry, workflow, and GitHub hashes and provenance; smoke-install the wheel on Python 3.10 and hash-locked sdist on Python 3.14; close issues #23 and the tracking issue through a checked documentation-only closure PR.

### Release Gates

- Feature merge and TestPyPI development publication are intermediate checkpoints, not completion.
- Wheel contents remain limited to the runtime package and required metadata; repository qualification evidence, workflows, docs, examples, tests, plans, release tooling, and fragments remain excluded.
- Stable publication is blocked until OCR 1.8.0 is human-qualified, the final one-shot local OCR review is addressed, all protected checks pass, and the release PR is merged.
- Closure requires exact registry/GitHub/workflow hash equality, provenance verification, exact annotated tag target, immutable Release state, supported-Python smoke installs, external issue closure, and recorded receipts.

### Completed Checkpoints

- Repository started clean and synchronized at `3ddbb4e`; tracking issue #24 records the release objective and issue #23 records OCR qualification.
- Public ruleset `Protect main` now requires the M0 `sast-bandit` check in addition to the existing quality, platform, dependency, build, CodeQL, and security contexts; API readback confirmed the active rule on 2026-07-28.
- OCR 1.8.0 is recorded as tested and recommended from normalized run evidence; the changelog review found native remote MCP to be the only toolkit-owned contract change and moved managed OAuth lifecycle work to BL-012.
- Three self-review cycles fixed merge-vs-replace MCP semantics, private artifact race/permissions, remote field and control-character bounds, ruleset coverage, stale artifact-dependent tests, and repeated quality-environment mutation. The quality wrapper now repairs an interrupted missing-`RECORD` install only inside its disposable environment, syncs once, and runs all tools with `--no-sync`; its focused 366-test run is warning-free.
- The one permitted complete local OCR review used the checksum-verified OCR 1.8.0 Darwin arm64 binary and the toolkit's `ocr-ci review` path against a disposable index containing all 24 changed files. No GitLab command or credential was used. OCR returned success with six actionable findings; all were repaired: visible quality-sync failures, broader credential-header rejection, environment-secret and URL bounds, regular-file/hard-link/FIFO artifact validation, and same-inode output separation. Post-review deterministic validation passes with 368 tests plus 41 subtests, compatibility validation/discovery, lockfile, Towncrier draft, build/Twine, minimal artifact inspection, Python 3.10/3.14 wheel smoke installs, and `git diff --check`; no second OCR review was run.
- Feature PR #25 merged as protected-main squash `4513956` after every required CI, security, dependency, build, and CodeQL check passed with no review threads. TestPyPI workflow run `30350463053` then built, published, provenance-attested, hash-verified, and wheel/sdist smoke-installed immutable `0.3.0.dev18`. That version reflects the pre-release `.next-version` state inherited from 0.3.0; this release PR advances the stable authorization and next development line to 0.3.1.
- Release PR #26 merged as protected-main squash `035864d`; release workflow run `30351032061` published and verified the same bytes on TestPyPI and PyPI, then created annotated tag `v0.3.1` targeting that merge and an immutable GitHub Release. Wheel SHA-256 is `d37233e0f8736418f69b5a26fe1342dbed7b0c16a75962ce7f98200cfd9a71ee`; sdist SHA-256 is `aa403ec1b4bc052ae6d3a97980e81bc356e3513dd196cdb37f51488028c1452e`. Registry and GitHub hashes agree, both artifacts have release-workflow provenance bound to `035864d`, and fresh local smoke installs passed for the wheel on Python 3.10 and sdist on Python 3.14. Issue #23 is closed; closure of tracking issue #24 is carried by this documentation-only PR.
- Documentation closure PR #27 merged as `532b7a3`, closed issue #24, and passed every protected check. Its post-merge TestPyPI workflow run `30351569649` published, provenance-attested, hash-verified, and wheel/sdist smoke-installed `0.3.1.dev20`; all post-merge CI, Security, CodeQL, and OpenSSF runs also passed.

<a id="plan-toolkit-0-3-0"></a>

## Completed Plan: Complete M0 foundation and release v0.3.0

Status: completed; stable release and external reconciliation verified
Owner: Codex
Last Updated: 2026-07-27
Tracking Issue: #19
Release Classification: release-required
Target Stable Version: 0.3.0

### Goal

Complete roadmap milestone M0 as one production-quality feature: add a bounded Bandit repository gate, establish one versioned OCR compatibility manifest, automate checksum-verified evidence collection for unseen stable OCR releases without automatic upgrades, and carry the result through the full protected release path to stable 0.3.0 publication.

### Fixed Decisions

- Start from protected `main` merge `808a7f7`, which is the merged tree of PR #18 and has successful post-merge CI, Security, CodeQL, Scorecard, and TestPyPI development workflows.
- Deliver implementation through one `feature/m0-foundation` PR with coherent signed intermediate commits, then a separate `release/v0.3.0` PR. Do not push the feature branch or open its PR until iterative self-review, full local validation, and the single final local OCR review are complete.
- OCR 1.7.17 is the only tested and recommended baseline. Releases after 1.7.17 are classified by deterministic policy: a same-minor patch with unchanged consumed contracts may produce a bot-ready compatibility patch, while every ambiguous or material change remains an observed candidate requiring explicit human qualification.
- Candidate execution is Linux amd64; all published upstream assets and the checksum file are independently verified. The compatibility contract covers only toolkit-consumed CLI and JSON behavior and permits unknown additive upstream fields.
- The final OCR gate is one checksum-verified OCR 1.7.17 review of the complete `main..HEAD` feature diff. Any finding is fixed and locally revalidated before the feature branch is committed for PR handoff; OCR is not rerun.

### Work Queue

1. [x] Reconcile the checkout with merged PR #18, refresh `main`, verify a clean tree, and create tracking issue #19 and `feature/m0-foundation`.
2. [x] Add Bandit 1.9.4 as a development-only dependency; scan only `src/ocr_toolkit` at medium severity and confidence; document narrow B108 suppressions; expose the scan through `scripts/quality.sh security`; add a dedicated Security workflow job. The local gate and targeted tests pass; adding the new context to protected-main requirements remains a post-merge repository-admin checkpoint so the branch is not deadlocked before the workflow exists on `main`.
3. [x] Add a versioned OCR support manifest with 1.7.17 as the only tested/recommended baseline, all upstream asset metadata, deterministic machine evidence, human rationale, and cross-field validation.
4. [x] Add a standard-library-only qualification harness for bounded stable-release discovery, double-source checksum verification, Linux amd64 execution, synthetic CLI/preview/review contract probes, normalized evidence, conservative automatic-safe classification, and fail-closed behavior.
5. [x] Add scheduled/manual candidate qualification automation that emits an idempotent human-review issue for material/ambiguous candidates and a bot-ready patch artifact for strictly compatible same-minor patches. It never silently modifies `main`; a real PR is opened only when `OCR_UPDATE_BOT_TOKEN` is configured, otherwise the issue and artifact are the exact resume path.
6. [x] Update public security/development/compatibility documentation, roadmap/strategy/backlog state, and Towncrier fragments; add unit, contract, workflow, adversarial, documentation, and distribution-content tests. Published wheel/sdist contents are explicitly minimal and exclude all qualification and repository-only tooling.
7. [x] Complete multiple self-review and fix cycles covering architecture, security boundaries, workflow permissions/idempotency, test quality, documentation truth, and repository hygiene. Fixes include bounded pagination to the monitoring floor, sequential patch-only automatic classification, final asset redirect origin validation, optional bot identity validation, strict Mypy compatibility restored across the existing runtime, and minimal distribution composition.
8. [x] Run the complete local matrix: `scripts/quality.sh check` passes with 351 tests and 26 subtests at 73.54% branch coverage; Bandit gates pass; build/Twine and exact wheel/sdist smoke installs pass; `uv lock --check`, workflow/config contracts, public-content scan, Markdown target validation, official upstream discovery dry run, and `git diff --check` pass. The wheel contains 38 runtime/metadata entries; the sdist roots are only `src`, `README.md`, `LICENSE`, `pyproject.toml`, generated `PKG-INFO`, and Hatch's forced `.gitignore`.
9. [x] Complete the final local OCR 1.7.17 review over `main..HEAD` with project rules and prepared background, retain ignored local evidence, fix every actionable finding, and rerun deterministic validation without another OCR review. Initial session `d01fd4a6-82ce-4a58-8356-f26feea2eae1` failed all items before review because the external key returned `429`; after reset OCR refused resume because no file had completed, so replacement session `f568b93c-29f8-4bd9-81f8-5dca16c0f388` was required. It reviewed all 13 files, returned six medium findings and zero warnings, and all six were fixed: Mypy/Bandit table ownership, portable issue-number capture, idempotent bot branches, manifest/evidence asset equality, monitoring-floor bounds, and controlled missing `tool_calls`. The post-fix quality gate passes with 353 tests and 26 subtests at 73.54% branch coverage.
10. [x] Push the signed feature branch, open a non-draft PR, resolve review feedback, require all protected checks including Bandit, merge through protected `main`, and verify the resulting 0.3.0.devN TestPyPI artifacts, hashes, attestations, and smoke installs.
11. [x] Create signed `release/v0.3.0` from refreshed `main`, render and verify Towncrier release notes, set reproducible release authorization metadata, validate the exact release diff, open the release PR, and merge only after all protected checks pass.
12. [x] Monitor stable TestPyPI, PyPI, annotated tag, provenance, and immutable GitHub Release; independently reconcile all distribution hashes and smoke-install the wheel on Python 3.10 and hash-locked sdist on Python 3.14.
13. [x] Record exact external evidence in `PLANS.md`, merge the documentation-only closure PR #22, verify its checks, and only then compact the completed M0 plan.

### Completed Checkpoints

- Feature PR #20 passed every protected check, including the new `sast-bandit` job, and was squash-merged to protected `main` as `b23fcece393b52557ad7b66d2f57b6efe6b9cb3b` on 2026-07-28.
- TestPyPI development workflow run `30341458637` published and exact-hash verified `0.3.0.dev15`; wheel SHA-256 is `2869be43396a4b4df4d7c3a9098d48c8bd6f99960819b798480e4b6276ce9c26`, sdist SHA-256 is `47c54863cc580a2624ed9cd56e40e416bb71e3b0f606c49d751cd12945cbee76`, and registry JSON matches the reviewed workflow artifact. The workflow's provenance publication and exact wheel/sdist smoke verification succeeded.
- Release PR #21 passed every protected check and was squash-merged to protected `main` as `2e2cc835966f51cd378f46abfc15b0c625f4a7c6` on 2026-07-28. Release workflow run `30342158059` completed successfully.
- Stable TestPyPI and PyPI `0.3.0`, the reviewed workflow artifact, and immutable GitHub Release `v0.3.0` have identical distribution hashes: wheel `d752d18a8d7650e11e1a8066fab0b71e94f6d1625824112844de36a866e1def5`, sdist `ccd78c9262cc0aefcae0b13df982a015933896bc19428341c210f195bedc075f`. `artifact-hashes.json` and `SHA256SUMS` agree.
- GitHub provenance verification succeeds for both distributions. Annotated tag `v0.3.0` targets exact release merge `2e2cc835966f51cd378f46abfc15b0c625f4a7c6`; the release is non-draft, non-prerelease, and immutable.
- Independently reconciled artifacts install successfully: the wheel reports `0.3.0` and runs `ocr-ci --help` on Python 3.10; the hash-reviewed sdist reports `0.3.0` and runs `ocr-ci --help` on Python 3.14.

### Release Gates

- Feature merge and any TestPyPI `.devN` build are intermediate checkpoints, not completion.
- Wheel contents remain limited to the `ocr_toolkit` runtime package plus required distribution metadata; sdist contents remain limited to runtime source, readme, license, build/generated package metadata, and Hatch's automatically force-included `.gitignore`. Tests, examples, documentation trees, planning sources, release automation, compatibility qualification evidence, repository workflows, and changelog fragments are excluded from published distributions and checked by an explicit build-content contract.
- A stable release is blocked by any unseen upstream stable OCR release above 1.7.17 until it is either classified automatic-safe by the complete deterministic gate or receives human compatibility classification. Automatic-safe candidates still travel through a normal compatibility PR and a separate signed release PR; failures and ambiguity cannot auto-promote.
- Release closure requires registry/GitHub hash equality, GitHub artifact attestation verification, immutable non-draft release state, exact tag target, and supported-Python smoke installs.

<a id="plan-roadmap-dependencies"></a>

## Completed Plan: Refine roadmap dependency and rollout safety

Status: completed
Owner: Codex
Last Updated: 2026-07-27
Release Classification: no-release
Release Decision: documentation correction only; retain the Towncrier fragment for the next planned release

### Goal

Correct dependency and rollout mistakes in the durable strategy, milestone roadmap, and regenerated backlog without implementing product features or publishing another package release. Separate current external MCP capabilities from future evidence MCP composition, preserve atomic bootstrap/MCP delivery, parallelize independent foundations, and replace speculative framework priorities with an evidence-based selection gate.

### Work Queue

1. [x] Reinspect current external MCP configuration, context rendering, strategy, roadmap, backlog dependencies, planning tests, and execution pitfalls against the architecture-review findings.
2. [x] Update strategy and roadmap to show parallel compatibility/evidence foundations, early external-reference security/current-MCP documentation, and late built-in/external MCP composition.
3. [x] Review all 22 backlog items and rewrite the dependency graph, rollout boundaries, selection gates, trust semantics, validation expectations, and activation triggers where repository evidence exposed omissions.
4. [x] Record the planning failure mode. Remove brittle planning-content tests instead of encoding mutable item counts, wording, or temporary dependency edges into the permanent product suite.
5. [x] Render and visually inspect the updated Mermaid roadmap, validate public-content hygiene, run `git diff --check`, and the complete quality gate.
6. [x] Perform architecture and rollout-safety self-review passes, correct findings, close this plan to post-change truth, and prepare a signed ready PR without auto-merge or a stable release.

### Root-cause Hypothesis

- The original backlog projected the desired end-state architecture into an overly linear implementation order.
- It did not distinguish existing external MCP primitives from future built-in evidence MCP composition.
- It separated implementation modules without preserving the user-safe release boundary between compact bootstrap and on-demand evidence.
- Framework priorities were inferred from current parser maturity rather than selected through a documented pilot-repository inventory.

### Backlog Review Findings

- OCR candidate qualification now enumerates every unseen stable release oldest-first, verifies API asset digests and checksum manifests before runner-platform execution, separates machine-tested from human-compatible/recommended states, and cannot mutate production contracts.
- Evidence foundations now cover schema evolution, trust/sensitivity, redaction before storage, source/target git edge cases, migration parity, MCP response/session budgets, lockfile variants, and mutable image-tag semantics.
- External MCP security and documentation use the current configurator; only reserved-name composition waits for built-in evidence MCP. Compact bootstrap and evidence MCP ship atomically with legacy rollback.
- Accepted decisions define duplicate/scope/expiry/authority behavior; guidance requires target-ref-aware upstream capability and nested precedence; framework plugins require anonymized inventory and scoring.
- Profiles define field-level precedence and capability validation; metrics are low-cardinality, privacy-bounded, opt-in, and non-fatal; routing preserves a repository minimum profile.
- Later file configuration rejects secrets and source self-authorization with explicit migration/rollback; host adapters require a capability matrix and explicit degradation; fuzzing chooses a backend through a bounded target-specific spike.
- The roadmap no longer blocks profiles and measurement on completion of every ecosystem, external MCP, and policy item.

### Validation and Review Record

- First review corrected current-vs-future MCP boundaries, independent compatibility/evidence foundations, atomic compact-bootstrap/evidence-MCP rollout, and framework selection based on anonymized inventory rather than parser familiarity.
- Second review covered every remaining backlog item and added missing semantics for release candidate qualification, evidence trust/schema/migration, git-ref edge cases, dependency and image evidence, decisions/guidance, profiles/metrics/routing, fuzzing, file configuration, and host adapter degradation.
- Removed `tests/test_project_strategy.py`: permanent tests tied to 22 temporary item IDs and exact prose would fail as completed backlog entries are removed and would make normal planning maintenance look like a product regression. Durable prevention now lives in explicit review guidance rather than brittle content assertions.
- The updated Mermaid roadmap renders successfully and remains readable without synthetic dates. Local Markdown link targets exist; public-content scans found no concrete OCR version pins, private infrastructure names, or credential markers in durable planning documents.
- `UV_CACHE_DIR=.quality-logs/uv-cache ./scripts/quality.sh check` passes with 332 tests and 26 subtests at 73.60% branch coverage. `git diff --check` is clean.

<a id="plan-toolkit-0-2-1"></a>

## Completed Plan: Publish stable 0.2.1

Status: completed
Owner: Codex
Last Updated: 2026-07-27
Release Classification: release-required
Target Stable Version: 0.2.1

### Goal

Publish the OCR compatibility update and durable strategy/roadmap documentation as stable `0.2.1` through the protected release-PR workflow, then independently verify registry, GitHub Release, hashes, attestations, and supported-Python installs.

### Work Queue

1. [x] Confirm PR #14 merged as signed squash commit `3a8a8c9`, all feature and post-merge checks passed, build artifacts exist, and TestPyPI development version `0.3.0.dev9` was published.
2. [x] Create `release/v0.2.1` from exact `origin/main` and confirm stable trusted-publisher environments, protected-main ruleset, and release workflow authorization contract remain configured.
3. [x] Set stable release metadata, assemble the 0.2.1 changelog from issue #12 and #13 fragments, and remove only those consumed fragments.
4. [x] Run complete quality, deterministic build, artifact metadata, wheel/sdist smoke-install, and release-contract validation; correct every finding.
5. [x] Commit and push the signed release branch, open `Release v0.2.1`, and merge only after every required check succeeds.
6. [x] Monitor production publication and independently reconcile stable TestPyPI/PyPI files, immutable GitHub Release assets, hashes, attestations, and Python 3.10/3.14 installs before closing this plan.

### Release Inputs

- Feature merge: `3a8a8c982fca5cc7b270bd1b0ce0085f514a3c13`.
- Development verification: TestPyPI `0.3.0.dev9` and retained workflow artifacts from successful post-merge automation.
- Stable changes: OCR compatibility target 1.7.17; durable strategy and milestone roadmap; regenerated 22-item backlog and canonical documentation links.
- Exact OCR versions remain only in operational compatibility surfaces, not durable strategy or roadmap.

### Pre-merge Validation Record

- `UV_CACHE_DIR=.quality-logs/uv-cache ./scripts/quality.sh check`: 338 tests and 26 subtests pass at 73.60% branch coverage.
- Two isolated `0.2.1` builds are byte-identical. Wheel SHA-256 is `46c8ef99f4cb6b62b22d5407474aa32e1c2e41b7fb02a08a880c1d4803893d4b`; sdist SHA-256 is `0fdde8b7f20221b6a04ff5a17a46c77d036866ecdf7a3e21d424561e8a49d0cd`.
- `twine check` passes for wheel and sdist; metadata reports version `0.2.1`, Python 3.10-3.14 classifiers, and no runtime dependencies.
- Python 3.10 installs the wheel and Python 3.14 builds/installs the hash-locked sdist; both report package version `0.2.1` and run `ocr-ci --help`.
- The release authorization helper accepts the exact repository-owned `release/v0.2.1` / `Release v0.2.1` contract. `git diff --check` is clean.

### Publication Record

- Release PR #15 passed every required CI, security, dependency, CodeQL, and build check and merged as signed squash commit `24a6ba6f3684acda6d6698f7a2269fa58f0cd28a`.
- Release workflow `30258933950` completed successfully: stable TestPyPI and PyPI publication, exact registry verification, build-provenance attestation, and GitHub Release publication all passed.
- TestPyPI, PyPI, and immutable GitHub Release `v0.2.1` contain the same wheel (`46c8ef99f4cb6b62b22d5407474aa32e1c2e41b7fb02a08a880c1d4803893d4b`) and sdist (`15d8eb5bd14d614d6c4aad3c3d801c2724451a8c2cb78e43a367c9fcedf4f607`). `SHA256SUMS` and `artifact-hashes.json` agree with those files.
- GitHub provenance verification succeeds for both published distributions. The annotated `v0.2.1` tag targets exact release merge `24a6ba6`; the release is non-draft, non-prerelease, and immutable.
- Independently downloaded PyPI artifacts install successfully: the wheel on Python 3.10 and hash-locked sdist on Python 3.14 both report `0.2.1` and run `ocr-ci --help`.

<a id="plan-strategy-roadmap"></a>

## Completed Plan: Establish durable strategy and roadmap

Status: completed
Owner: Codex
Last Updated: 2026-07-27
Release Classification: no-release
Release Line: included with the pending 0.2.1 compatibility work; no independent publication required

### Goal

Establish a durable product and architecture strategy, an outcome-oriented milestone roadmap, and a completely reconciled implementation backlog based on the repository's current behavior and compatibility policy. Keep the work documentation-only and make every future capability explicit as implemented, partial, planned, conditional, or rejected.

### Work Queue

1. [x] Inspect the canonical instructions, all execution plans, the existing backlog, public documentation, context and MCP implementation, preflight/configuration boundaries, GitLab normalization/posting code, tests, examples, and the latest official OCR release.
2. [x] Create the durable toolkit strategy and concise milestone/dependency roadmap, including rendered Mermaid component, data-flow, and roadmap diagrams.
3. [x] Regenerate the backlog as 22 coherent production-quality items and record an explicit disposition for native fuzzing, OpenSSF registration, additional code-hosting adapters, and file-based configuration.
4. [x] Update the canonical source index, concise README development section, Towncrier fragment, and documentation contract tests.
5. [x] Validate Markdown links and anchors, render Mermaid blocks, scan public documentation for private infrastructure or credentials, run focused tests, `git diff --check`, and the complete quality gate.
6. [x] Perform self-review, correct all findings, record post-change truth, close this plan, and prepare a separate signed documentation commit on `chore/ocr-1.7.17`.

### Established Decisions

- Use a Mermaid milestone dependency flowchart rather than a calendar Gantt; synthetic milestone identifiers express order without inventing deadlines.
- Place Bandit in M0 as high-priority repository maintenance, while keeping it outside the toolkit product architecture and outside this documentation-only implementation.
- Treat ecosystem/framework evidence and additional code-hosting adapters as separate concerns: the former describes reviewed repositories, while the latter changes the forge, CI, and publication adapter boundary.
- Preserve signed commit `c0630bf` as the OCR 1.7.17 compatibility change and add this work as a second commit without amending it.

### Completion Record

- Created `docs/engineering/toolkit_strategy.md` and `ROADMAP.md`; updated `AGENTS.md`, `README.md`, `docs/codex/TASKS_BACKLOG.md`, and this execution record; added issue #13 Towncrier documentation fragment and strategy contract tests.
- Regenerated 22 backlog items across M0-M6. Native fuzzing was retained and tied to parser attack surfaces; OpenSSF remained an owner action; provider adapters were clarified as code-hosting/review-host adapters; file configuration was deferred until profile/MCP/evidence schemas stabilize.
- Kept exact OCR versions out of durable strategy, roadmap, and backlog. The operational version remains in preflight, installation guidance, checksum-pinned examples, and compatibility tests where it is required.
- Rendered all three Mermaid blocks through Mermaid CLI and installed Chrome, producing readable temporary diagrams of 2860x796, 2368x398, and 3160x556 pixels. No generated image is tracked.
- Local Markdown links resolve; bounded checks of the public GitHub, PyPI, and OpenSSF links passed. Public planning documents contain no private infrastructure names, credential markers, or secrets.
- Strategy/release contract tests pass with 10 tests. The complete quality gate passes with 340 tests and 26 subtests at 73.73% branch coverage; `git diff --check` is clean. The final rerun used the repository-isolated `UV_CACHE_DIR=.quality-logs/uv-cache` because the sandbox cannot read the shared user uv cache.

<a id="plan-ocr-1-7-17"></a>

## Closed Plan: Target Open Code Review 1.7.17

Status: closed; stable-release monitoring explicitly deferred by the owner
Owner: Codex
Last Updated: 2026-07-27
Release Classification: release-required
Target Stable Version: 0.2.1

### Goal

Update the locally installed Open Code Review binary and the toolkit's exact supported-version contract from 1.7.14 to 1.7.17, verify the upstream release notes and immutable asset checksums, and deliver the compatibility update through the complete protected release path.

### Work Queue

1. [x] Review the v1.7.15-v1.7.17 release notes and classify toolkit impact; retain the existing adapter and configuration contracts unless CLI/runtime verification proves a required change.
2. [x] Review the parked backlog for a coherent companion item. Keep native fuzzing, OpenSSF registration, additional provider adapters, and file-based configuration separate because each has an independent activation trigger or owner boundary.
3. [ ] Atomically replace the local darwin-arm64 OCR binary only after verifying the official v1.7.17 checksum manifest and release-asset digest. The candidate is verified and executable; replacing `~/.local/bin/ocr` was deferred after the approval service repeatedly returned HTTP 502.
4. [x] Update preflight, tests, public documentation, and the checksum-pinned linux-amd64 GitLab example to v1.7.17; add a Towncrier compatibility fragment linked to issue #12.
5. [x] Run focused compatibility checks, self-review, the complete quality gate, and release-contract validation; correct every finding before handoff.
6. [x] Prepare the validated feature branch for a signed commit, protected-main pull request, and owner-requested immediate merge without post-merge monitoring.
7. [ ] Verify the post-merge TestPyPI development build, prepare and merge `release/v0.2.1`, then reconcile stable TestPyPI/PyPI, tag, immutable GitHub Release, hashes, attestations, and Python 3.10/3.14 smoke installs. Explicitly deferred by the owner on 2026-07-27; resume by confirming the merged feature SHA and successful TestPyPI development build, then create `release/v0.2.1` from that `main`.

### Upstream Review

- v1.7.15 contains fixes relevant to CI review correctness: per-file comment work no longer races pool submissions, merge commits are reviewed against their first parent, binary diff markers are anchored correctly, and hand-edited `timeout_sec` survives config round-trips.
- v1.7.16 removes a hardcoded 180-second review-filter timeout and corrects reviewed-file accounting; its new provider and GraphQL support do not require toolkit changes.
- v1.7.17 adds OpenCode, Julia, and Rust-rule features and normalizes code-comment metadata enums. None changes the documented `ocr review`, configuration, or JSON result contract used by the toolkit according to the release notes; runtime verification remains required.
- The v1.7.17 official release records SHA-256 `d1771b962ae518bd0e75093b695633e1d12f80700521f5eb5872651b83595012` for darwin-arm64 and `ab2fae81796a00dda292def8261bec2203d03f3909673c08219e7c5df5f4feee` for linux-amd64.
- The downloaded darwin-arm64 candidate matches both the official checksum manifest and GitHub asset digest, reports `open-code-review v1.7.17 (0ced7165)`, preserves the toolkit-used `review` flags, and successfully previews a repository diff.
- Focused tests pass with 162 tests and 18 subtests. The complete quality gate passes with 332 tests and 26 subtests at 73.60% branch coverage; `git diff --check` is clean.
- The owner explicitly requested plan closure after feature merge and waived further monitoring. Stable `0.2.1` publication is therefore not claimed as complete; its exact resume action remains work item 7.

<a id="plan-toolkit-0-2-0"></a>

## Completed Plan: Publish stable 0.2.0

Status: completed
Owner: Codex
Last Updated: 2026-07-27

### Goal

Publish the incompatible reviewer-command contract, GitLab operations model, documented accepted-decision guidance, and OCR v1.7.14 compatibility target as stable `0.2.0`, using the already validated development artifact line and the protected release-PR automation.

### Work Queue

1. [x] Verify feature PR #8 merged into `main`, all post-merge workflows passed, and TestPyPI `0.2.0.dev7` was published and installed successfully.
2. [x] Prepare reproducible stable release metadata, consume the 0.2.0 Towncrier fragments, and move the following development line to `0.3.0.devN`.
3. [x] Run the complete quality, package, and release-contract validation gates; close implementation preparation to release-PR truth. A second security scan was explicitly waived because the feature branch already completed a full repository scan and this patch changes release metadata, generated changelog, tests, and process documentation only.
4. [x] Merge the registry-boundary fix through protected `main`, then recreate `release/v0.2.0` from that merge so the stable artifact necessarily contains the fix.
5. [x] Verify and document the retained `.opencodereview/accepted-decisions.md` contract, update the supported local and CI OCR version to v1.7.14, and regenerate the complete 0.2.0 changelog.
6. [x] Run the complete quality, package, release-contract, reproducibility, and Python 3.10/3.14 validation gates. The user explicitly waived another security scan for this release.
7. [x] Deliver a signed `release/v0.2.0` pull request. Its merge is the human authorization gate for TestPyPI `0.2.0`, production PyPI, tag, attestations, and immutable GitHub Release publication.
8. [x] After merge, monitor the complete release chain and independently verify registry/GitHub bytes, hashes, provenance, metadata, and Python 3.10/3.14 installs.

### Process Correction

- No repository instruction prohibited the stable release. The implementation mistake was closing the command-contract task after the feature PR and TestPyPI development build even though `0.2.0` had already been selected.
- `AGENTS.md` now makes stable publication or explicit deferral part of closure for incompatible public-contract changes.
- The stable artifact must be built from the release PR merge commit; no feature-branch artifact or TestPyPI development bytes are promoted in place.
- Release preparation uses stable version `0.2.0`, deterministic epoch `1784558537`, and next development line `0.3.0`. Two local builds were byte-identical; Twine, Python 3.10 wheel installation, Python 3.14 sdist installation, complete quality checks, and release-contract tests passed.
- First production run `29753514788` stopped before artifact upload or publication. Registry classification incorrectly treated legitimate `0.2.0.devN` TestPyPI files as conflicts for stable `0.2.0`; the boundary must accept other valid versions while still rejecting malformed filenames and duplicate/conflicting exact-version artifacts.
- The Ubuntu CI matrix is intentionally reduced to the supported endpoints, Python 3.10 and 3.14, matching macOS. The protected-main ruleset must remove the retired 3.11-3.13 job contexts in the same change so future PRs cannot wait for checks that no longer exist.
- PR #10 merged the registry-boundary fix into `main`. The first release branch is obsolete: the replacement `release/v0.2.0` is based on merge `39d8517`, so no recovery path can publish the pre-fix source.
- Accepted decisions remain implemented as bounded, sanitized project guidance. The public contract must explain the Markdown entry format, optional `ocr-accept` marker convention, prompt-level suppression semantics, and fail-closed omission when the decision file is changed by the current MR or changed-file discovery fails.
- OCR v1.7.14 is the compatibility target for this stable release. The local darwin-arm64 binary and public linux-amd64 example must use independently checked release-asset digests.
- The official v1.7.14 checksum manifest verified the example's linux-amd64 digest `f5ee3118...cc5f8b`; the local darwin-arm64 binary was atomically replaced only after verifying digest `48301e64...06929f6`, and reports `open-code-review v1.7.14 (870fc6a4)`.
- Accepted-decision support was not lost in extraction: the toolkit retained the earlier bounded reader, trusted-path check, Markdown sanitization/redaction, prompt section, and changed-file fail-closed guard. This release adds the missing user-facing contract instead of duplicating the feature or parking a false backlog item.
- The complete quality gate passes with 332 tests and 26 subtests at 73.60% branch coverage. Two stable builds were byte-identical, Twine accepted both distributions, the exact wheel/sdist set matched the release contract, and local smoke installs passed for the Python 3.10 wheel and Python 3.14 sdist.
- The only failed GitHub run was production release `29753514788`: it failed before upload because the old classifier mistook existing `0.2.0.devN` artifacts for malformed stable files. PR #10 fixed that boundary; every check on merge `39d8517` passed, including the reduced 3.10/3.14 matrix and verified `0.3.0.dev1` publication.
- Replacement release PR #11 merged as signed commit `11a526e`; TestPyPI and PyPI contain stable `0.2.0`, and immutable GitHub Release `v0.2.0` publishes the wheel, sdist, `SHA256SUMS`, and `artifact-hashes.json`.

<a id="plan-gitlab-discussions"></a>

## Completed Plan: Document and simplify GitLab discussion lifecycle

Status: completed
Owner: Codex
Last Updated: 2026-07-20

### Goal

Make repeated OCR reviews and GitLab discussion ownership understandable to developers and CI operators, replace ambiguous reviewer commands with an explicit pre-1.0 contract, and publish a complete operations guide grounded in the existing fail-closed posting behavior.

### Work Queue

1. [x] Replace `/ocr keep` and `/ocr skip` with `/ocr resolve` and `/ocr suppress`, remove legacy aliases, and preserve human-reply ownership and fingerprint suppression.
2. [x] Add focused lifecycle, command parsing, duplicate suppression, compatibility-removal, and documentation contract tests.
3. [x] Add `docs/operations.md` with a Mermaid state machine, rerun/deduplication semantics, posting modes, token permissions, limits, failure behavior, and operator-facing examples.
4. [x] Add a concise README overview, link the GitLab and configuration guides, and update the public GitLab CI example with recommended blocking-job defaults.
5. [x] Isolate `scripts/quality.sh` in its own ignored environment so routine checks never mutate or warn about a developer's shared `.venv`.
6. [x] Complete self-review, full validation, complete security scan, close the plan to post-change truth, and prepare a signed pull request for the 0.2.0 development line.

### Locked Decisions

- `/ocr resolve` preserves and suppresses the finding, then resolves the discussion after the next successful posting transaction.
- `/ocr suppress` preserves the discussion open and suppresses matching future findings.
- `/ocr keep` and `/ocr skip` are removed without aliases; their previous messages remain ordinary human replies and therefore retain the thread and exact-finding suppression without command-specific state changes.
- Any human reply still transfers the thread out of bot-only cleanup and suppresses findings matching its recorded inline position or compatible fingerprint.
- README remains concise; the complete operator model lives in `docs/operations.md`.
- `OCR_POST_MODE=draft` is the safe default; blocking review jobs should use `OCR_STRICT_POSTING=true`.
- Documentation targets both CI operators and developers who add or maintain the job. It does not add fork/protected-variable guidance, a connection-verification procedure, or a standalone troubleshooting section.

### Validation Record

- `scripts/quality.sh check` passes in its isolated `.quality-logs/venv` with 99.67% branch coverage and no shared-`.venv` uninstall warning.
- Focused lifecycle and documentation contracts pass alongside the complete test suite; all workflow/example YAML parses, shell syntax is valid, and `git diff --check` passes.
- Runtime dependency export is empty and `pip-audit` reports no known vulnerabilities. Secret-pattern review found only fixed synthetic redaction fixtures.
- A complete Codex Security repository scan reviewed all 68 inventoried runtime, workflow, release, test, example, package, security, and operator-documentation files, including the working tree, and finalized with zero reportable findings in 2 minutes 51 seconds.
- PR validation exposed that the ruleset-required `dependency-review` check still had pull-request path filters. The workflow now runs for every pull request so protected `main` never waits for a required check that GitHub did not create.
- The first Mermaid state diagram rendered poorly in GitHub because long transition labels and self-loops forced an excessively wide layout. It was replaced with a compact top-down decision flow and rendered locally before handoff.

<a id="plan-release-no-op"></a>

## Completed Plan: Make non-release merges a clean release-workflow no-op

Status: completed
Owner: Codex
Last Updated: 2026-07-20

### Goal

Ensure the production release workflow distinguishes an ordinary merged pull request from a malformed release attempt before running strict release authorization, so normal merges do not create failed Actions runs while release-branch/title/version/commit validation remains fail-closed.

### Work Queue

1. [x] Reconcile every post-merge run for PR #6 and identify the only failure as `Release / authorize-release` rejecting the ordinary `hardening/scorecard-follow-up` branch.
2. [x] Add a read-only classification gate that selects only merged `release/v*` pull requests or explicit recovery dispatches for production authorization.
3. [x] Add contract tests for ordinary merge no-op, malformed release fail-closed, and unchanged authorized release behavior.
4. [x] Make the required `build-distributions` check unconditional for pull requests so path filtering cannot leave otherwise valid PRs permanently blocked.
5. [x] Repeat full validation and security diff review, close this plan, and prepare the signed pull request for merge.

### Current Evidence

- All six `main` push workflows for merge `5a0f754ede10834f703965946470bd04219ac379` succeeded: CI, build, Security, CodeQL, Scorecard, and TestPyPI development publication.
- TestPyPI published and independently verified `0.2.0.dev5`; the stable `0.1.0` PyPI and immutable GitHub Release artifacts remain unchanged.
- Scorecard closed all four `Pinned-Dependencies` alerts and now reports only six classified governance, age, historical coverage, fuzzing, and badge signals.
- The sole post-merge failure is run `29740626723`, triggered by `pull_request.closed`; strict authorization treated an ordinary merge as a release attempt and raised `release pull request branch must start with release/v`.
- The six remaining Code Scanning entries are current Scorecard posture signals, not failed jobs or CodeQL vulnerabilities: Fuzzing, SAST history coverage, OpenSSF Best Practices registration, repository age, external code review, and maximal multi-maintainer branch protection. They must not be dismissed or cosmetically suppressed.
- Targeted release contracts (24 tests), the complete quality suite, workflow YAML parsing, and `git diff --check` pass. Codex Security reviewed all five changed files in full and finalized a complete diff report with zero reportable findings.
- PR #7 exposed a second workflow-contract issue: `build-distributions` is required by the `main` ruleset but its pull-request trigger had path filters, so a release-workflow-only patch produced no required check and remained blocked despite every started check passing. The required PR build is now unconditional; optional `main` push builds retain their path filter.
- The repeated complete security diff review covers all six changed files and reports zero findings; targeted contracts, the full quality suite, workflow parsing, and diff checks remain green.

<a id="plan-toolkit-0-1-0-release"></a>

## Completed Plan: Release 0.1.0 and remediate public security findings

Status: completed
Owner: Codex
Last Updated: 2026-07-20

### Goal

Recover the authorized 0.1.0 release after the TestPyPI Trusted Publisher rejected the first OIDC exchange, finish the exact-artifact TestPyPI-to-PyPI-to-GitHub publication chain, and then address the actionable OpenSSF Scorecard findings without weakening the single-maintainer release controls.

### Work Queue

1. [x] Confirm that the failed run stopped before external publication and preserved the reviewed artifact set.
2. [x] Correct and read back the TestPyPI Trusted Publisher for `release.yml` and `testpypi-public-disclosure`.
3. [x] Rerun the failed release jobs and monitor TestPyPI, PyPI, tag, attestations, and immutable GitHub Release publication through independent byte and install verification.
4. [x] Classify every open Scorecard alert as actionable, historical, temporal, or an intentional single-maintainer tradeoff.
5. [x] Fix repository-owned workflow and hardening findings, add focused regressions and documentation, and preserve required signed commits and protected-main checks.
6. [x] Run the complete validation matrix and a security diff review, close this plan to post-change truth, and prepare the follow-up for delivery through a signed pull request.

### Locked Decisions

- 2026-07-20: The merge of release PR #5 is the sole human authorization gate; recovery may only publish version 0.1.0 from merge commit `96d6d33d2faa1d664b41f4b19d3498a7bb148d72`.
- 2026-07-20: The first failed release run published nothing. Recovery must reuse the workflow's deterministic build contract and accept existing registry state only when exact filenames and SHA-256 values match.
- 2026-07-20: Scorecard findings are not assumed to be code vulnerabilities. Repository-owned CI findings will be fixed, while historical, age-based, and incompatible multi-reviewer expectations will be documented rather than misrepresented.
- 2026-07-20: No API tokens or long-lived publication secrets will be introduced; TestPyPI and PyPI remain OIDC Trusted Publisher integrations.

### Validation Evidence

- Release run `29738037085` completed authorization, quality, dependency audit, secret scan, deterministic build, Twine, exact version/hash checks, provenance attestation, and artifact upload before TestPyPI rejected the OIDC publisher identity.
- Release run `29738037085` attempt 2 succeeded end to end. TestPyPI and PyPI expose the exact same wheel (`ad2ddac2...d6016`) and sdist (`34400866...8ce9`) bytes; the immutable GitHub Release `v0.1.0` exposes the same assets and checksum manifest, and GitHub provenance verifies against `release.yml`.
- Independent Python 3.10 wheel and Python 3.14 sdist installs passed with package version `0.1.0` and `Requires-Python: >=3.10,<3.15`. The GitHub Release is immutable and its annotated tag resolves to the authorized merge `96d6d33d2faa1d664b41f4b19d3498a7bb148d72`.
- All ten open code-scanning alerts are OpenSSF Scorecard findings; Dependabot and secret-scanning have no open alerts, and CodeQL reported no source vulnerability. Four actionable Pinned-Dependencies alerts are scanner-visible sdist smoke installs. Branch-Protection and Code-Review reflect the documented single-maintainer model; Maintained is age-gated; SAST is historical coverage while CodeQL is already required; CII Best Practices needs truthful owner registration; fuzzing needs a separately designed native integration rather than a cosmetic workflow.
- `scripts/quality.sh check`, targeted workflow tests, a real hash-locked sdist install, YAML parsing, shell syntax checks, `git diff --check`, and OpenSSF Scorecard v5.5.0 `Pinned-Dependencies` analysis all pass; the local Scorecard result is 10/10 for dependency pinning. The first CI attempt exposed that `pip --require-hashes` also requires an explicit digest for a local path, so the final implementation generates a one-artifact requirements file from the just-read SHA-256 before installation.
- Codex Security reviewed all ten changed files in full and finalized a complete working-tree diff report with zero reportable findings. The generated report is outside the repository under the system temporary Codex Security scan directory.
- The signed follow-up pull request is the remaining delivery operation, not unfinished implementation or validation.

<a id="plan-toolkit-0-1-0-preparation"></a>

## Completed Plan: Public release 0.1.0 preparation

Status: completed
Owner: Codex
Last Updated: 2026-07-20

### Goal

Publish the first stable public toolkit release as one reproducible artifact set across TestPyPI, PyPI, and an immutable GitHub Release; update the supported Open Code Review CLI to 1.7.13; and establish a protected public trunk with deterministic `0.2.0.devN` TestPyPI builds after future merges.

### Work Queue

1. [x] Update the local OCR binary and toolkit contract to the verified 1.7.13 release.
2. [x] Replace private alpha and PAT-based release preparation with public trunk development builds and a local release-PR flow.
3. [x] Make the stable workflow reproducible and idempotent across TestPyPI, PyPI, Git tagging, attestations, and GitHub Release publication.
4. [x] Generate the 0.1.0 changelog, stable package metadata, release notes, documentation, and checksum-pinned public example.
5. [x] Enable and validate the GitHub protections and security features unlocked by public visibility.
6. [x] Complete iterative self-review, full quality/build/package checks, and a diff-scoped Codex Security scan; repair every actionable result.
7. [x] Close this plan to post-change truth and prepare the release branch for commit, pull request, required-check monitoring, and the single squash-merge gate.
8. [ ] After the owner merges the release PR, verify exact 0.1.0 bytes on TestPyPI, PyPI, and GitHub, plus tag, attestations, independent installs, and the next 0.2.0.devN build.

### Locked Decisions

- The repository is public and remains public throughout release publication.
- The owner-configured TestPyPI and PyPI Trusted Publishers are the only registry credentials; no API token or release PAT is stored in GitHub.
- Feature work remains trunk-based through pull requests into protected `main`; no persistent `develop` branch is introduced.
- Every non-release merge to `main` publishes one idempotent `0.2.0.dev<GITHUB_RUN_NUMBER>` development build to TestPyPI.
- Squash-merging the exact `release/v0.1.0` pull request is the only human publication gate. The external publication chain then runs automatically and fails closed.
- TestPyPI, PyPI, and GitHub Release receive the same reviewed wheel and sdist bytes; an existing partial or hash-conflicting release is never overwritten.
- GitHub distribution consists of release assets, checksums, and provenance attestations. GitHub Packages is not used because it does not provide a Python package registry.
- At the v0.1.0 release checkpoint, runtime dependencies remained empty and supported Python was 3.10 through 3.14; M1 raises the v0.4 floor to Python 3.12.

### Validation Record

- Local OCR was atomically replaced with the official darwin-arm64 v1.7.13 binary after SHA-256 verification; `ocr --version` reports commit `a4a281c1`.
- `scripts/quality.sh check` passed on the final staged diff: 312 tests and 26 subtests with 73.37% branch coverage, plus Ruff formatting/lint and strict mypy.
- The complete test suite passed independently on Python 3.10.20 and 3.14.6 with 312 tests and 26 subtests on each interpreter.
- `pip-audit --skip-editable`, Gitleaks v8.30.1 over all history and the staged diff, Zizmor v1.27.0, YAML parsing, shell syntax, `uv lock --check`, and `git diff --check` passed.
- Two independent exact `0.1.0` builds were byte-identical. Twine, metadata, archive-content inspection, wheel install, and sdist install passed. Reviewed SHA-256 values are `ad2ddac2fe39bc204a1ea5f80340a126faee96797de97e8505c18b2acb7d6016` for the wheel and `912923a8cedee8a2a4de103b1b490120212b1d0bad49e35b9d5718b205886386` for the sdist.
- Codex Security diff scan completed with 39 of 39 staged files covered. One low-severity immutable-release rerun finding was remediated; validation and attack-path analysis leave zero open findings and zero deferred work.
- Public GitHub readback confirms the active `main` ruleset, immutable releases, private vulnerability reporting, secret scanning with push protection, Dependabot security updates, and protected-branch policies on both publication environments. CodeQL and OpenSSF Scorecard completed successfully after public disclosure.
- Pull-request readback exposed that the distribution build previously ran only after pushes to `main`; the build workflow now runs as a bounded `build-distributions` pull-request gate with non-isolated builds and no-dependency smoke installs. Its follow-up contract tests, YAML parse, Ruff, Zizmor, Gitleaks, and diff review passed.
- Owner-configured TestPyPI and PyPI Trusted Publishers remain the only publication credentials. Registry publication, tag creation, GitHub Release publication, attestations, and independent external installs are intentionally pending the owner squash-merge gate.

<a id="plan-initial-extraction"></a>

## Completed Plan: Initial standalone toolkit extraction

Status: completed
Owner: Codex
Last Updated: 2026-07-17

### Goal

Create the first production-quality standalone Open Code Review Toolkit repository: extract the existing CI helper behavior into the `ocr_toolkit` package, expose a unified `ocr-ci` CLI, publish only synthetic public material, add packaging and automation, validate the complete deliverable, and create a clean initial commit only after all gates pass.

### Requested Scope

- Preserve parity for rendering safety, redaction, runtime and MCP configuration, preflight, context generation, repository and manifest inspection, guidance extraction, categorization, reusable Ansible context, GitLab posting, payload normalization, markers, fingerprints, snapshots, rollback, and ownership boundaries.
- Provide `ocr-ci preflight`, `configure`, `mcp-config`, `context`, and `post`.
- Add a PEP 621/Hatchling/hatch-vcs package, uv lockfile, Ruff, strict mypy, pytest, coverage, build and security tooling.
- Add English public documentation, synthetic GitLab examples, pinned GitHub Actions, Dependabot, changelog fragments, and gated OIDC release automation.
- Validate privacy and source-repository immutability before the initial commit.
- External account setup and public disclosure remain paused until explicit owner actions.

### Constraints

- The extraction source is read-only; never edit, stage, commit, switch branches, or inspect its untracked private test material.
- Do not copy local paths, private identities, private infrastructure, or the one-time private audit criteria into tracked files.
- Do not bundle or download the OCR binary in the Python package.
- Runtime configuration remains environment-only in v0.1.
- Posting accepts only `GITLAB_API_TOKEN`; remove all legacy fallback variables and messages.
- Do not provide the old package namespace or `python -m` compatibility contract.
- Runtime targets Python 3.10 through 3.13 on Linux and macOS.
- Keep the task specification local-only through `.git/info/exclude`.
- Multi-agent execution is disabled for this repository.

### Inputs

- Local extraction material kept outside version control.
- Tracked runtime and test sources from the read-only source repository at commit `b770f6e66b504a675ba7f594b55f4b156b8a2a53`.
- Tracked rules and design documentation listed by the extraction specification.
- `engineering-workflow` v0.4.0 scaffold and validation guidance.

### Completed Baseline State

- [x] Target directory exists and is initialized as a Git repository on `main`.
- [x] Multi-agent support is disabled by project-local Codex configuration.
- [x] Local extraction material is ignored and absent from Git status.
- [x] Source repository branch, commit, tracked candidate list, and pre-existing untracked paths were recorded without opening private untracked content.
- [x] Source baseline in the specification records 252 passing tests and standard-library-only runtime code.
- [x] Engineering-workflow audit classified the target as a minimal repository.

### Current Work Queue

1. [x] Bootstrap the canonical workflow documentation for this repository.
2. [x] Extract tracked runtime/tests, rename imports to `ocr_toolkit`, and remove all legacy environment aliases.
3. [x] Implement and test the unified `ocr-ci` parser and required subcommands.
4. [x] Add packaging, quality tooling, changelog infrastructure, and a reproducible lockfile.
5. [x] Rewrite public documentation and add synthetic GitLab fixtures/examples.
6. [x] Add pinned CI, build, security, dependency review, Scorecard, Dependabot, provenance, and OIDC release workflows.
7. [x] Run tests, coverage, Ruff, strict mypy, build/twine/install/CLI smoke checks, workflow checks, and generic secret scanning.
8. [x] Run the one-time public-safety/privacy audit and verify the source repository is unchanged.
9. [x] Update this plan to final truth and prepare the clean initial import commit after every available gate passed.

### Locked Decisions

- 2026-07-17: Distribution and repository name are `open-code-review-toolkit`; import namespace is `ocr_toolkit`; CLI is `ocr-ci`.
- 2026-07-17: Provider-neutral core with GitLab as the first adapter; Ansible support remains a reusable context feature.
- 2026-07-17: Apache-2.0, Hatchling, hatch-vcs, src layout, standard-library-only runtime, and SCM-derived versions.
- 2026-07-17: Public API and schema are provisional before 1.0 but every 0.1.x user-visible change requires a changelog fragment.
- 2026-07-17: External GitHub/PyPI setup and public visibility are not attempted until their explicit approval gates.

### Verification

- Adapted pytest suite and measured 70% coverage threshold.
- `ruff check`, `ruff format --check`, and strict `mypy` over `src/ocr_toolkit`.
- Build wheel and sdist, `twine check`, and isolated install smoke for both artifacts.
- CLI smoke for all required subcommands.
- Synthetic GitLab API posting tests.
- Generic secret scan plus one-time external privacy/public-safety audit.
- GitHub workflow/action pin audit and YAML parse.
- `git diff --check`, ignored-task verification, clean source-repository status comparison, and final target status review.

### Latest Validation Results

- Local extraction material is ignored outside tracked repository content.
- Engineering workflow audit: minimal repository; no prompt-injection warnings.
- Source read-only inventory: expected tracked candidates present; only the known private untracked paths were reported and not inspected.
- `engineering-workflow` scaffold and read-only validator applied; canonical workflow files are present.
- 258 adapted tests pass; measured branch coverage is 72.51% against the 70% gate.
- Private GitHub repository created; Actions default to read-only tokens, SHA pinning is enforced, allowed Actions are restricted, Dependabot alerts/security fixes are enabled, and TestPyPI/PyPI environments exist.
- GitHub Free rejected branch protection, rulesets, secret-scanning push protection, and environment approval rules for this private repository. These remain owner gates: upgrade the plan or make the repository public only after the privacy/license checkpoint, then enable them before any release.
- No repository credential values were invented or copied from another project. OIDC publication needs no PyPI token, and stable release pull requests are prepared locally without a long-lived GitHub credential.
- Pre-commit security review is in progress using the diff-scoped Codex Security workflow in single-agent mode, followed by a final engineering review.
- Focused security review found and fixed one fail-open posting path: missing/invalid GitLab configuration now exits nonzero and has a regression test. No unresolved high-confidence vulnerability remains in the reviewed trust boundaries.
- Engineering review also corrected the public GitLab example to the supported OCR `--format json` CLI contract and added a regression assertion.
- Dependabot version updates are configured monthly in grouped Python-tooling and GitHub Actions PRs; vulnerability alerts and automated security fixes are enabled through GitHub.
- Public-safety scans found no private paths, infrastructure markers, legacy integration names, high-confidence secret patterns, or local specification files in the staged tree.
- Source repository verification still reports branch `ai-ocr` at `b770f6e66b504a675ba7f594b55f4b156b8a2a53` with only the two pre-existing untracked paths documented by the extraction input.
- Final workflow policy check: all third-party Actions use full commit SHAs, `pull_request_target` is absent, workflow tokens default to read-only, and repository Actions SHA pinning is enforced.
- Final GitHub Actions audit updated checkout, setup-uv, PyPI publishing, and Gitleaks to their current 2026 releases while retaining immutable full-SHA pins and readable version comments.
- Live private-repository runs confirmed CI, build, dependency/security, and Dependabot workflows. Scorecard and CodeQL are intentionally skipped while private because GitHub Free blocks their repository integrations; both activate automatically after the public-visibility approval gate.
- Final quality wrapper: 259 tests pass with branch coverage above the 70% gate; Ruff format/check and strict mypy pass. Build, Twine, Python 3.13 wheel/sdist install smokes, Towncrier draft, YAML parsing, and `pip-audit --skip-editable` pass.

### Resume Point

- Initial import commit `9fdc8fa282480c83ad1d8d3a33744dffbbbbf2f3` was pushed once to seed the private remote. Use pull requests only from this point. Before release, satisfy the owner gates below.

### Handoff Notes

- Do not create the initial commit while any validation, privacy audit, or source-integrity check is pending.
- Stop for owner action before PAT setup, Trusted Publisher setup, final public-package approval, or visibility changes.
- The later public-release plan replaced these historical owner gates with local release-PR preparation, Trusted Publishing, public rulesets, private vulnerability reporting, secret-scanning push protection, and immutable releases.

<a id="plan-private-testpypi-preview"></a>

## Completed Plan: Private TestPyPI preview

Status: completed
Owner: Codex
Last Updated: 2026-07-18

### Goal

Keep the source repository private while publishing a prerelease to TestPyPI for installation testing. Defer public GitHub visibility, public-only GitHub protections, and production PyPI publication to a separate explicitly approved release task.

### Work Queue

1. [x] Verify the current GitHub Free/private-repository limits and the current PyPI Trusted Publisher setup flow against official documentation.
2. [x] Split private TestPyPI preview automation from the production release workflow.
3. [x] Make unavailable GitHub Free/private integrations skip cleanly while preserving local dependency and secret checks.
4. [x] Validate the workflow syntax, quality suite, build, and focused security properties.
5. [x] Open pull request #2 and wait for all applicable GitHub Actions checks.
6. [x] Configure the TestPyPI Trusted Publisher, publish `0.1.0a1`, and verify the public artifacts.

### Locked Decisions

- 2026-07-17: The GitHub repository remains private during TestPyPI validation.
- 2026-07-17: TestPyPI publication is a public package disclosure, but it is not the production release and must not publish to PyPI or publish a GitHub Release.
- 2026-07-17: Production publication remains fail-closed until the repository is public and the public-only GitHub hardening is configured.

### Validation Evidence

- `scripts/quality.sh check`: 259 tests and 26 subtests passed; branch coverage 72.67% against the 70% gate; Ruff and strict mypy passed.
- All workflow YAML files parsed successfully and `git diff --check` passed.
- A synthetic `0.1.0a1` wheel and sdist built successfully, passed Twine metadata checks, contained the exact requested version, and installed into a Python 3.13 smoke environment.
- The wheel and sdist contain no local extraction material, Codex configuration, Git metadata, or IDE metadata. Local-only configuration remains ignored and untracked.
- Gitleaks v8.30.1 scanned all Git history and the built `dist/` artifacts with no leaks found.
- Zizmor 1.27.0 reported no findings in the private-preview, Security, and Dependency Review workflows. The pre-existing production release workflow has only low/informational hardening suggestions and remains fail-closed while private.
- Focused review confirms that the preview publishes only from the current `main` SHA, accepts only canonical prerelease versions, refuses an existing TestPyPI version, stores no index credential, disables provenance disclosure from the private workflow, and smoke-installs from TestPyPI without dependency confusion fallback.
- Pull request #2 passed the complete Python 3.10-3.13 Linux/macOS CI matrix, quality, pip-audit, and Gitleaks checks. CodeQL and Dependency Review skipped as designed for GitHub Free/private mode.

<a id="historical-recently-completed-marker"></a>

## Recently Completed

- None yet.

<a id="plan-ocr-1-7-12"></a>

## Completed Plan: OCR 1.7.12 compatibility and correctness hardening

Status: completed
Owner: Codex
Last Updated: 2026-07-18

### Goal

Harden the current standalone toolkit with regression coverage, update OCR compatibility to 1.7.12, and reach a clean review/security state before opening a pull request.

### Work Queue

1. [x] Verify the OCR 1.7.12 release, checksum, CLI contract, and local installation.
2. [x] Reassess inherited behavior against the current toolkit and preserve only applicable product fixes.
3. [x] Add focused regression tests and implement confirmed fixes without broad refactors.
4. [x] Update public documentation, examples, compatibility pins, prerelease metadata, and Towncrier fragments.
5. [x] Complete targeted and full quality, build, package, and supply-chain validation.
6. [x] Validate bounded context, manifest, and version discovery against a tracked consumer snapshot without adding consumer-specific behavior.
7. [x] Complete iterative internal self-review and repair cycles with no remaining actionable findings.
8. [x] Complete the full repository security scan, fix validated findings, and seal a post-remediation rescan with no open findings.
9. [x] Update this plan to post-change truth before commit and pull request creation.

### Locked Decisions

- Local-only material remains ignored and is not staged, committed, packaged, or quoted into public artifacts.
- The source integration repository remains read-only; fixes are implemented in the standalone toolkit only.
- Consumer validation may inspect only tracked source-integration files and run the standalone toolkit against that repository. No consumer-specific path, host, package, version, or layout may enter toolkit runtime code, tests, documentation, or examples.
- Multi-agent Codex features remain disabled for this project; the complete security scan ran sequentially with exhaustive primary-agent receipts.
- Runtime dependencies remain empty; fixes should use the standard library.
- The package version remains SCM-derived. This change advances the next development/release line through changelog fragments and the eventual release tag rather than hard-coding a package version.

<a id="plan-language-testpypi-alpha"></a>

## Completed Plan: Unified review language and automatic TestPyPI alpha releases

Status: completed
Owner: Codex
Last Updated: 2026-07-19

### Goal

Make `OCR_REVIEW_LANGUAGE` the single safe language contract with default `English`, synchronize public GitLab examples, support Python 3.14, and publish one deterministic TestPyPI alpha for every successful merge into `main`.

### Work Queue

1. [x] Implement one shared language resolver used by runtime configuration and generated context; remove the legacy language identifier from tracked and built content.
2. [x] Pin the synthetic GitLab example to a checksum-verified TestPyPI wheel downloaded with bounded retries and timeouts.
3. [x] Convert the TestPyPI workflow to automatic `main` publication using `0.1.0a${GITHUB_RUN_NUMBER}` and idempotent PEP 691 artifact verification.
4. [x] Add regression, workflow, versioning, registry-state, documentation, and packaging tests.
5. [x] Extend package metadata, CI, documentation, and install smokes through Python 3.14.
6. [x] Run iterative internal self-review and repair cycles until no actionable findings remain.
7. [x] Run the full repository Codex Security scan, fix every validated finding, repeat self-review and validation, and seal a clean post-remediation scan.
8. [x] Validate the package and read-only consumer flow and close this implementation plan to post-change truth before commit and pull-request publication.

### Validation Evidence

- The complete quality wrapper passes with 301 tests, 26 subtests, 73.37% branch coverage, Ruff format/check, and strict mypy.
- Independent Python 3.10 and Python 3.14 test runs pass the complete 301-test suite.
- Duplicate `0.1.0a3` wheel and sdist builds are byte-identical, pass Twine, exclude ignored local files, and install successfully on supported Python versions.
- `pip-audit --skip-editable`, locked dependency validation, YAML parsing, and Zizmor over every GitHub workflow pass; Zizmor reports no findings.
- Live TestPyPI PEP 691 metadata for `0.1.0a2` matches the public example's immutable wheel URL and SHA-256.
- A full repository Codex Security scan covered runtime and privileged CI surfaces. One production-release artifact-binding issue was fixed; the sealed post-remediation result has no open findings or deferred scope.
- A tracked-only archive of the read-only consumer repository generates bounded context with the default English review language and no toolkit-specific hardcoding; its existing local untracked files remain unchanged and unread.

### Locked Decisions

- Default review language is `English`; `Russian` is the documented explicit example.
- At the v0.1.0 release checkpoint, supported Python versions were 3.10 through 3.14 on Linux and macOS; M1 raises the v0.4 floor to Python 3.12.
- The legacy language identifier is removed rather than supported as an alias.
- TestPyPI run number maps directly to the alpha number; run #3 publishes `0.1.0a3`, reruns are idempotent, and subsequent merges consume subsequent alpha numbers.
- The public example remains pinned to the already verified `0.1.0a2` wheel; the automatic workflow never commits its own published URL back to `main`.
- Production PyPI publication, Git tags, and GitHub Release creation are not executed in this change; their existing workflow now verifies published files against the reviewed artifact hashes.
- Pull-request checks, squash merge, and independent `0.1.0a3` TestPyPI verification are operational follow-through after this implementation plan is closed.
