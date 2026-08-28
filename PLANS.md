# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and
before handoff or commit. Completed stable plans are indexed in
[the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Toolkit 0.8.6 — OCR 1.11.0 and precise security signals

Status: active — Draft implementation exists; independent review and full stable delivery
are in progress.

Release classification: `release-required`

Target stable version: `0.8.6`

#### Goal

Deliver toolkit 0.8.6 as an immutable stable release. The release must qualify and require
OCR 1.11.0, fix false security promotion for neutral domain phrases, keep provider-private
reasoning and request state outside every public/receipt/approval sink, pass local and hosted
validation, and finish with independently verified registry and GitHub artifacts, closed
release issues and milestone, and synchronized clean `main`.

#### Scope And Decisions

- Continue from Draft PR #154 and issues #153/#155; inspect the complete Draft rather than
  assuming its existing green checks prove readiness.
- OCR 1.11.0 is the sole supported runtime. OCR 1.10.2 remains comparison evidence only.
- Preserve one provider-neutral flow:
  `private OCR state -> canonical projection -> DLP -> publication -> receipt/approval`.
- Keep grouping inventory, timeout scaling, Handlebars/Mustache Rules, `file_find`, result,
  manifest, receipt v5, DLP, telemetry, summary, and approval contracts internally
  consistent and covered by synthetic tests.
- Fix #153 only in reviewer-guide analytics: neutral phrases such as knowledge or dependency
  injection must not increase the security count or effort, while explicit metadata and a
  closed set of vulnerability phrases remain promoted.
- Required configuration variables remain bold in public documentation.
- Do not set or recommend a provider-specific `4096` completion cap. The active default is
  unset and inherits the qualified OCR/provider contract. Historical wire evidence may retain
  its exact tested value when explicitly labelled as historical evidence.
- Update the PATH-effective local Darwin arm64 OCR atomically to checksum-verified 1.11.0.
- Run one semantic local OCR review against the exact final feature head with concurrency 1.
  If it fails exclusively because every provider request is HTTP 429, record the gate as
  owner-authorized `waived`, not passed, do not retry again, and continue release delivery.
- Keep full test and OCR output in ignored owner-only temporary logs. Public plans, issues,
  PRs, changelog, release notes, and summaries contain only synthetic or bounded structural
  evidence and never private paths, credentials, provider/model identity, prompts, reasoning,
  tool payloads, request IDs, or raw OCR output.
- macOS hosted checks remain advisory; Linux supported-Python checks and protected release
  authorization are the release priority.
- No B2B, `core/common`, shared-template, or consumer-repository integration is in scope.

#### Requirements And Evidence

| ID | Requirement | Authoritative evidence |
| --- | --- | --- |
| `R1` | Exact OCR 1.11.0 qualification and sole-runtime pin | Upstream release/source review, compatibility evidence/hash validation, preflight/example tests, local binary digest/version/help |
| `R2` | Correct grouping/rules/timeout/file lookup behavior | Qualification-only parser tests, installed-artifact no-LLM probes, runtime contract tests |
| `R3` | Provider-private fields cannot affect public state | Hostile projection, DLP, receipt, cleanup, telemetry, summary, and approval tests |
| `R4` | #153 false-positive classification fixed without broad regression | Exact reproducer plus positive, neutral, Unicode, boundary, determinism, and immutability tests |
| `R5` | Documentation/examples/changelog are current and consistent | Documentation contracts, version searches, Towncrier draft, complete diff review |
| `R6` | Feature tree is release-ready | Targeted tests, full quality/coverage, security, package determinism, local OCR, self-review, exact PR head/check/thread readback |
| `R7` | Stable release is authorized and published | Release plan/receipt, release PR exact-head checks, protected stable workflow success |
| `R8` | Publication is independently closed | Byte equality across workflow/TestPyPI/PyPI/Release, provenance and attestations, tag target, Python 3.12–3.14 installs, release-note/asset readback |
| `R9` | Repository and tracking state are closed | Actions-owned issue receipts, #153/#155 closed, milestone closed, archived plan, clean `main == origin/main == v0.8.6^{}` |

#### Work Queue

| Queue | Status | Deliverable |
| --- | --- | --- |
| `WQ-01` | `done` | Live `main`, Draft PR, issues, milestone, upstream release, roadmap/backlog, and release owners inspected. |
| `WQ-02` | `done` | Draft #154 implementation and documentation audited; release plan and completion-cap wording corrected. |
| `WQ-03` | `done` | Exact local OCR 1.11.0 installed and qualified; the single concurrency-1 semantic review completed 7/7 selected files. |
| `WQ-04` | `done` | The one confirmed OCR finding is fixed; full gates and holistic self-review pass, and the signed final feature-head commit is ready to bind. |
| `WQ-05` | `in progress` | Push the final feature head, update and mark PR ready, verify protected checks/threads/policy, merge, and verify development publication. |
| `WQ-06` | `pending` | Prepare signed `release/v0.8.6` state, generated changelog, archived plan, receipt inputs, and release PR. |
| `WQ-07` | `pending` | Verify release PR, merge exact reviewed tree, and complete the protected stable workflow. |
| `WQ-08` | `pending` | Independently verify registries, bytes, provenance, attestations, tag, immutable Release, receipt, and supported-Python installs. |
| `WQ-09` | `pending` | Verify issue receipts, close issues/milestone, synchronize clean `main`, remove task-owned temporary material, and perform final audit. |

#### Validation Contract

- During iteration: focused tests for every changed parser, subprocess, persistence, DLP,
  posting, receipt, configuration, compatibility, and documentation boundary.
- Final feature gate: `scripts/quality.sh check`, all coverage floors, compatibility manifest,
  lockfile, Towncrier draft, Ruff format/lint, strict MyPy, Bandit, checksum-verified
  Gitleaks, package build/determinism, and `git diff --check`.
- OCR gate: exact installed 1.11.0 identity and one semantic review at concurrency 1; inspect
  the result/manifest and coverage rather than process exit alone. A pure repeated HTTP 429 is
  a documented waiver, never a pass.
- PR gates: exact head/base/tree, all required checks complete, no unresolved review threads,
  current merge policy, and re-read immediately before merge.
- Stable closure: independent artifact bytes, TestPyPI/PyPI metadata and PEP 740 provenance,
  GitHub attestations and immutable Release, annotated tag peeled target, receipt schema and
  hashes, clean wheel/sdist installs on Python 3.12–3.14, issue/milestone receipts, and clean
  synchronized `main`.

#### Risks And Recovery

- A Draft-green check can miss semantic or privacy defects. Fix only evidence-backed findings,
  repeat the affected gate, and then rerun the single complete final gate.
- Local OCR replacement can fail. Verify the candidate before atomic replacement and retain a
  verified rollback copy until 1.11.0 passes local identity and no-LLM probes.
- Provider rate limiting can make semantic OCR unavailable. After the single concurrency-1 run,
  accept only an all-429 outcome for the authorized waiver; mixed or product failures require
  diagnosis and remediation.
- Registry propagation can lag. Verify JSON/simple-index state and retry once without cache;
  do not misclassify cache lag as an artifact defect.
- Stable release publication is irreversible. Re-read exact release head, authorization,
  checks, and receipt inputs immediately before merge; stop on any mismatch.

#### Current Evidence

- Draft PR #154 starts from released v0.8.5 and had 13/13 hosted checks green at head
  `79d5587`; issues #153/#155 and milestone v0.8.6 are open.
- Hosted OCR compatibility run 33158664020 verified the official 1.11.0 assets and generated
  the accepted human-review-required evidence. Adjacent source review maps each consumed
  contract or records it as no-impact.
- PATH-effective OCR is official Darwin arm64 1.11.0 with SHA-256
  `ac8bf5a0fcd176bb9dcc15b169e90f4b52bf32787adef17a850489dbed97fb78`.
  The installed `probe-local` contract passed version/help, preview, grouping, Rules, result,
  budget, numeric CLI, and completion-cap checks.
- The only configured-provider OCR review ran at concurrency 1 on exact head `d2249ab` and
  finished in 396 seconds with manifest `complete`: 7 selected, 7 completed, 0 failed,
  0 reused, and 0 waived. It returned one medium bug finding; this is a passing semantic
  gate, so no provider waiver applies.
- The finding correctly identified that the qualification-only grouping parser accepted the
  historical wire shape only for 1.10.2 even though repeatable semantic probes cover the full
  qualified 1.10.0–1.10.2 line. The parser now binds that exact old shape to all 1.10.x
  releases while production preflight remains exact 1.11.0. All 86 compatibility tests pass.
- Targeted privacy/posting/configuration/release suites pass 480 tests plus 243 subtests;
  manifest validation, Towncrier draft, Ruff format check, and diff checks pass.
- The final canonical gate passes 1,321 tests plus 363 subtests at 86.52% branch
  coverage. The four locked risk groups pass at 85%, 82%, 86%, and 87%; Ruff format/lint,
  strict MyPy, and Bandit pass in the same run.
- Independent lock and OCR-manifest validation, rendered 0.8.6 Towncrier draft,
  dependency audit, pinned Gitleaks, and `git diff --check` pass. Two deterministic
  wheel/sdist builds are byte-identical; Twine and archive content/privacy checks pass,
  and clean wheel plus sdist installs and CLI smoke pass on Python 3.12, 3.13, and 3.14.
- Holistic feature-diff self-review found and fixed one documentation drift: the current
  compatibility guide now describes only an operator-selected positive completion-cap
  override and the full qualification-only historical 1.10.x inventory parser range.
  Machine qualification evidence retains its exact checksum-bound tested probe. No other
  correctness, privacy, release, documentation, or example inconsistency remains.

#### Closure Gate

- [ ] Every requirement has direct current-state evidence.
- [ ] Feature and release PRs are merged from exact reviewed heads with required checks green.
- [ ] Stable 0.8.6 artifacts, provenance, attestations, tag, Release, receipt, and installs are independently verified.
- [ ] Issues #153/#155 and milestone v0.8.6 are closed through truthful release evidence.
- [ ] The active plan is archived, local and remote release branches are removed, task-owned temporary material is cleaned, and `main` is clean and synchronized.
