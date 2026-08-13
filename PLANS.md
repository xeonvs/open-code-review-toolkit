# Execution Plans

Use this file for active, blocked, or recently completed execution work. Update it before implementation and before handoff or commit. Older completed plans are indexed in [the execution-history archive](docs/engineering/execution_history/README.md).

## Active Plan: M4 policy and project guidance for 0.6.0

Status: active; nested target guidance ready for third checkpoint commit
Owner: Codex
Last Updated: 2026-08-13
Release Classification: release-required
Target Stable Version: 0.6.0
Next Development Version After Release PR: 0.6.1
Tracking Issue: #81
Branch: `feat/m4-policy-guidance`; no checkpoint commit is pushed individually
Qualified OCR Baseline At Activation: 1.9.2

### Goal And Closure Boundary

Deliver all of M4 as stable toolkit 0.6.0: BL-014 structured accepted
 decisions and BL-015 safe nested target-branch project guidance through the
 established read-only evidence MCP. Keep the lifecycle active through focused
 implementation commits, complete validation, Codex Security before OCR, one
 full local OCR review at concurrency 2, feature and release PRs, stable
 TestPyPI/PyPI publication, provenance, annotated tag, immutable Release,
 supported-Python installs, immutable receipt readback, and closure of issue
 #81. Feature merge and development publication are intermediate receipts.

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
- `evidence.collectors` retains bounded Git/tree/blob orchestration and changed
  path identity. `evidence.store` owns admission, recursive redaction, closed
  schema validation, atomic persistence, and hostile readback. `evidence.project`
  owns only compact bootstrap projection. `evidence.mcp` remains the one
  read-only stdio transport.
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
4. **Production integration and security hygiene.** Add synthetic installed
   wheel/sdist and real stdio MCP E2E, security/user docs, remaining Towncrier
   fragments, and only demonstrated least-privilege fixes for actionable GitHub
   Code scanning alerts.

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
- The previously retained externally reconciled M2 cycle moved byte-for-byte
  into the stable release archive under `plan-toolkit-0-5-0`; its SHA-256 before
  and after extraction is
  `dd699e63f81faa3d3baf2cc302864ecc1514de874cbcb88d8ff37ffec43a9f79`.
  The archive index resolves every unique anchor. `PLANS.md` now contains only
  this active M4 lifecycle and will return to its template state after 0.6.0
  immutable receipt reconciliation.

### Validation, Codex Security, And OCR Gates

1. Run complete deterministic validation without OCR: Python 3.12-3.14,
   `scripts/quality.sh`, Bandit, focused security/dependency/privacy/Gitleaks
   gates, reproducible wheel/sdist hashes, clean installed-artifact smoke with
   restricted `PATH`, hostile shadow package and private permissions, real
   stdio MCP, bootstrap budgets, hostile schema readback, and synthetic
   multi-component E2E.
2. Before OCR, run Codex Security `security-diff-scan` for the exact merge-base
   `origin/main..HEAD`: repository-level threat model, diff-scoped discovery
   with one work-ledger completion receipt per changed source-like file,
   validation of every candidate, attack-path analysis for every remaining
   candidate, and canonical report/coverage receipts in the authoritative
   ignored private scan directory. Fix actionable findings, audit siblings and
   boundaries, rerun deterministic validation, and rerun the needed security
   verification until the security cycle is closed.
3. Then run exactly one complete local OCR review over the full M4 diff with the
   latest fully qualified stable OCR, concurrency 2, posting disabled, private
   ignored artifacts, and proven `ocr_toolkit_evidence` summary/list/get use for
   policy and guidance. Fix actionable findings, audit the root cause and
   sibling module/service boundaries, repeat deterministic validation and final
   self-review, but do not run a routine second OCR without new authorization.
   A later OCR qualification that changes executable contracts or the reviewed
   tree invalidates the gate and requires a new final concurrency-2 review.
   Runtime/trust-boundary OCR fixes require a final Codex Security verification.
4. Consolidate unpublished history into the four logical commits, prove exact
   final-tree equivalence, verify signatures, and rerun Gitleaks over the full
   first-parent range. Only then make one initial push of the complete branch.

### Upstream OCR Monitoring

At activation and between completed logical stages, query stable upstream OCR
releases and this project's release issues. If OCR 1.9.3 or newer appears,
qualify the complete adjacent chain from 1.9.2. Classify every upstream item as
 consumed-contract change, future-backlog impact, or release-note-only context;
adapt only demonstrated toolkit contracts. Add one logical compatibility commit
if repository changes are required and use the latest fully qualified release
for installed E2E and final OCR. At activation on 2026-08-13, live readback still
reports v1.9.2 as latest and issue #81 is the only open toolkit issue.

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

### Feature, Release, And Stable Closure

- Open the feature PR only after the one complete push. Read back exact head,
  required checks, review threads, and merge policy. Group CI/review fixes into
  completed self-reviewed batches rather than pushing every commit. After merge,
  independently verify TestPyPI development artifacts, hashes, installs, and
  exact merged tree.
- The release PR is the final repository mutation. Preserve the already archived
  M2 receipts, consume Towncrier fragments into 0.6.0 notes, set the following
  line to 0.6.1, and reconcile `PLANS.md`, roadmap table/diagram, backlog,
  strategy, and narrative docs to repository-complete/publication-pending truth.
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
5. [ ] Complete logical commit 4: production E2E, documentation, fragments, and
   demonstrated Code scanning workflow improvements.
6. [ ] Complete deterministic Python/package/security/privacy validation.
7. [ ] Complete Codex Security diff scan, remediation, sibling audit, and
   required security revalidation before OCR.
8. [ ] Complete one full local OCR review at concurrency 2, evidence-MCP receipt,
   remediation, deterministic revalidation, and final self-review.
9. [ ] Consolidate and verify unpublished history, run full-range Gitleaks, and
   push the complete feature branch once.
10. [ ] Complete feature PR and independent TestPyPI development readback.
11. [ ] Prepare the final repository mutation in the release PR and reconcile
    backlog, roadmap, strategy, and release metadata honestly.
12. [ ] Complete stable 0.6.0 publication/readback and close issue #81 only from
    the immutable release receipt; archive this M4 cycle and return `PLANS.md`
    to its template state as part of externally reconciled closure.
