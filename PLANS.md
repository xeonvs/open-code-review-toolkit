# Execution Plans

## Active Plan: Toolkit 0.14.8 — OCR 1.13.8, provider HTTP and first integration

plan_schema_version: 2
Status: active
Release classification: release-required
Target release: 0.14.8
Next development marker: 0.15.0
Last Updated: 2026-11-12

### Goal

Implement, publish and independently reconcile toolkit 0.14.8 with qualified OCR
1.13.8, consistent forge API User-Agent, protocol-aware LLM URL normalization,
complete preflight prerequisites and a usable first GitLab integration. Carry
one delivery objective through feature review, stable publication, external
readback, local OCR update, synchronized main and task-owned cleanup.

### Plan Origin

plan_mode_approved

Full materialization of the owner-approved replacement plan and implementation
request, including the subsequent requirement to run the GitHub qualification
workflow and use its canonical issue. No implementation precedes this write.

### Requested Scope

Qualify exact OCR 1.13.8, freeze 1.13.7 readback, prove comparison-side reads and
real toolkit MCP/federation/diagram/gitlink handoffs. Run the repository's OCR
compatibility Action for this exact tag and retain its canonical issue.

Correct #306 through one provider-neutral default User-Agent and the single new
OCR_FORGE_API_USER_AGENT variable. Correct #307 through shared protocol-aware URL
normalization, mandatory API configuration validation and clear safe endpoint
diagnostics. Improve the canonical integration/configuration documentation,
standalone manual self-test installation, current max-tools guidance and tests.

### Requirement Traceability

| Requirement | Outcome | Queue | Status |
| --- | --- | --- | --- |
| REQ-001 | Full plan fidelity, signed draft PR and sustained delivery goal | WQ-01, WQ-08 | done |
| REQ-002 | Exact OCR assets, 1.13.7 frozen readback and 1.13.8 comparison-side contract | WQ-02 | done |
| REQ-003 | Hosted exact-tag qualification and canonical Actions-owned issue | WQ-02, WQ-07 | in_progress |
| REQ-004 | Qualified MCP/federation/grouping/diagram/gitlink consumers and manifest-based native inventory | WQ-02, WQ-06 | done |
| REQ-005 | One shared default and validated OCR_FORGE_API_USER_AGENT for all forge API methods | WQ-03 | done |
| REQ-006 | Protocol-aware implicit /v1 only for pathless OpenAI inputs; explicit paths preserved | WQ-04 | done |
| REQ-007 | Complete preflight inputs and bounded safe URL diagnostics without extra inference requests | WQ-04 | done |
| REQ-008 | Correct first-integration docs, independent example jobs and current max-tools guidance | WQ-05 | done |
| REQ-009 | Real-boundary, property and installed tests; coverage floors | WQ-03, WQ-04, WQ-05, WQ-06 | done |
| REQ-010 | Aggregate review, one Security scan, own-tool review with admitted diagram and final quality | WQ-06 | done |
| REQ-011 | Protected feature merge and development TestPyPI verification | WQ-07 | pending |
| REQ-012 | Signed release PR, metadata/authorization/pins and checked archive/reset handoff | WQ-08 | pending |
| REQ-013 | Stable registry/receipt/tag/issue/site/main verification | WQ-09 | pending |
| REQ-014 | Paired local OCR/toolkit update, obsolete binary removal and task cleanup | WQ-09 | pending |
| REQ-015 | Preserve valid URI semantics separately from qualified native query capability; upstream general correction proposal | WQ-04 | done |

### Explicit Non-Goals

No additional environment variables, endpoint-probe CLI flag, malformed inference
POST, endpoint guessing/fallback, model/profile defaults, new dependencies,
general HTTP framework or new forge adapter. Do not activate conditional backlog
items, rewrite historical evidence, change DLP detectors, replay unrelated private
corpora, weaken publication identity or add a second review engine. No landing
chat handoff or post-release closure PR. No private hostnames, source snapshots,
credentials, raw debug traces or internal conversation identifiers in public work.

### Constraints

- First repository write is this complete plan. Reconcile with the approved
  specification before implementation. First signed push opens a draft feature
  PR with the plan; keep subsequent implementation local until acceptance.
- Use ordinary native CLI execution, bounded output and completion-driven waits;
  no per-command receipts, duplicate transcripts or custom command runners.
- Review each logical commit, format code and scan the exact staged index.
  Amend unpublished corrections. Run tree/history/dependency gates before push.
- Freeze dependency/upstream composition before expensive review. No libraries
  are needed; preserve Python 3.12–3.15, hash-locked binary-only runtime installs,
  overall 88% coverage and existing module/security floors.
- Reporting stays pure. Shared header policy and URL interpretation are pure;
  adapters/orchestration own environment selection, networking and log emission.
- Keep result, diagram and receipt schemas unchanged. Optional diagram errors
  remain independent of findings, completeness, approval and cleanup.
- The normal preflight adds no inference request. Existing ocr llm test is an
  explicit private model-backed check, not a token-free or full-review proof.
- Preserve auth, redirects, retries, mutation ambiguity, freshness and bot
  identity gates. A failed /user read never authorizes publication.

### Inputs And Sources

- Owner-approved replacement plan and explicit implementation/hosted-workflow requests.
- AGENTS.md and canonical development, release, compatibility, configuration,
  GitLab, local-review, security and decision-flow owners.
- https://github.com/xeonvs/open-code-review-toolkit/issues/306
- https://github.com/xeonvs/open-code-review-toolkit/issues/307
- https://github.com/xeonvs/open-code-review-toolkit/issues/308 (canonical Actions-owned qualification)
- https://github.com/xeonvs/open-code-review-toolkit/pull/309 (initial signed plan draft)
- https://github.com/alibaba/open-code-review/releases/tag/v1.13.8
- https://github.com/alibaba/open-code-review/issues/1916 (actual query loss and general correction proposal)
- Upstream source commit 4236c871fe8130aa840a2a1c0922f469e87e0416.
- Official asset metadata and sha256sum.txt; current support manifest and
  read-only planning-stage qualification outputs.
- Cloudflare 1010 documentation recommends a descriptive application User-Agent:
  https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-1xxx-errors/error-1010/
- GitLab protected-resource prerequisites:
  https://docs.gitlab.com/ci/pipelines/merge_request_pipelines/#control-access-to-protected-variables-and-runners
- Installed engineering-workflow planning/lifecycle references; inactive backlog.

### User Decisions And Answers

- Exactly one new environment variable: OCR_FORGE_API_USER_AGENT, shared with
  future forge adapters, default open-code-review-toolkit-provider/1.
- Use OCR_LLM_PROTOCOL for URL semantics. Pathless openai/openai-responses roots
  receive /v1 with a warning; anthropic does not receive that correction.
- Show the base URL; exclude credentials/query from diagnostics. Preserve explicit
  prefixes and matching terminal endpoints, including endpoints without /v1.
- No separate endpoint-probe variable or CLI flag after this correction.
- Improve onboarding, update the local OCR binary and remove its predecessor.
- Follow the ordinary feature/release lifecycle, including accepted own-review
  diagram, one aggregate Security scan and external release verification.
- Use gpt-6.1-sol/xhigh for the next model review after checking availability.
- Launch the GitHub qualification Action so it creates the canonical issue.
- Owner approved a clearer variable name; FORGE_API explicitly covers reads and
  writes and excludes LLM. No alias for the superseded unreleased proposal.
- Audit all forge request paths, defaults, overrides, tests and current docs for
  User-Agent tails; retain unrelated services' independently owned headers.
- Refresh the draft's plan through a signed amend and guarded force-with-lease
  push. Keep unfinished runtime changes local until the final feature update.
- Actual Responses wire capture exposed lost inference query parameters. The
  owner authorized a pre-model refusal and upstream issue, then requested a
  general solution. Keep valid query syntax intact in the pure parser; exact
  native capability validation owns temporary review refusal. Upstream correction
  uses parsed URL components and existing SDK query operations, without gateway
  keys, proxies or new settings. Separately owned metadata queries remain valid.

### Completed Baseline State

- Clean synchronized main at fa64183f2c9d9aca85ab5d1575c1e140d844925b; stable 0.14.7.
- No open dependency PRs at planning inventory. Composition is existing lock
  plus exact OCR 1.13.8, subject to mandatory audit findings.
- Official Linux amd64 SHA-256:
  32187a8afa11b9c37fe549a0c879152e716496445a7eb67baa917d0103f22146.
- Official Darwin arm64 SHA-256:
  21ea25d40a744b909906f316361049d174b761c111607394c7dcca4741151f64.
- Full existing Linux suite passed locally with compatible/human-review-required;
  Darwin contract probes passed. These are not hosted qualification claims and
  do not yet establish the new comparison-side or optional toolkit handoffs.
- Toolkit does not consume removed --tools. Source review found MCP definitions
  still appended to main/plan tasks. No live paid-model call was made in planning.
- Reproduced preflight accepting missing API URL/token when /models is disabled.
- Found manual self-test missing an independent installation and stale max-tools
  guidance; observed explicit 50/75 limits are 50/75, not the former floor 100.
- Temporary source copies were removed after planning probes; verified assets
  and necessary synthetic qualification evidence remain private for reuse.
- Remaining backlog items are conditional/parked with unmet activation triggers.

### Current Work Queue

| Queue | Work and completion signal | Requirements | Status |
| --- | --- | --- | --- |
| WQ-01 | Full plan checks, signed initial plan push and draft PR #309 completed | REQ-001 | done |
| WQ-02 | Hosted baseline #308 passed; freeze 1.13.7; comparison-side/wire/native proof; promote qualified 1.13.8 | REQ-002, REQ-003, REQ-004 | in_progress |
| WQ-03 | Shared forge User-Agent default/override, early validation and real transport regressions | REQ-005, REQ-009 | done |
| WQ-04 | Shared protocol URL normalization, complete preflight, native query capability, diagnostics and real handoffs | REQ-006, REQ-007, REQ-009, REQ-015 | done |
| WQ-05 | Canonical onboarding docs, shared example install/manual self-test, public contracts and notes | REQ-008, REQ-009 | done |
| WQ-06 | Aggregate review, one Security scan, admitted own-review diagram, fixes, final quality/installed/secret/dependency gates | REQ-004, REQ-009, REQ-010 | done |
| WQ-07 | Final feature push with diagram, hosted qualification reconciliation, protected CI/merge and development registry proof | REQ-003, REQ-011 | pending |
| WQ-08 | Signed Release v0.14.8 PR, authorization/epoch/notes/pins, checked plan archive and CI/merge | REQ-001, REQ-012 | pending |
| WQ-09 | Stable external receipts/installs/tag/issues/site/main, paired local OCR update and cleanup | REQ-013, REQ-014 | pending |

### Locked Decisions

#### Forge HTTP policy

One provider-neutral constant owns the default. The operator variable applies to
every forge API HTTP method, including preflight/acquisition GETs and publication
writes. Resolve from operator input
when preparing applicable clients; unrelated standalone local review ignores it.
Accept a nonblank printable ASCII value of at most 256 bytes. Reject malformed
values before any forge request without echoing them. Do not introduce a
transport framework or propagate this header to LLM/federation/asset requests.

#### LLM URL and preflight

The shared provider-config owner applies defaults only to raw API inputs. Process
matching terminal endpoints first. For openai/openai-responses, a pathless root
uses /v1; explicit prefix paths and explicit root terminal endpoints stay intact.
Anthropic retains its existing root plus /v1/messages semantics. Unknown/mismatched
protocols remain errors. Preserve inference query as valid configuration data and
existing explicit /models override rules. Consumers use canonical config without
applying defaults again. Before inference, require exact native query capability;
current clients lack it. This is not a permanent URL-syntax ban. Configure alone
is not execution proof. Upstream #1916 proposes one parsed-URL owner plus existing
SDK query operations, including repeated/encoded values and actual request tests.

Return normalization notice data from the pure owner. Preflight/configure/review
orchestration emits one safe notice per command when a default was applied; show
base URL and effective endpoint without query/credentials. This informational
correction does not change review completeness, outcome or approval eligibility.
Always require API URL/token/model and valid controls before networking; disabled
/models affects only metadata reads. Native ChatGPT stays separate. No new probe.

#### OCR qualification

Preserve old evidence bytes and freeze 1.13.7 before advancing the live boundary.
Require new/old/default reads through all three native code tools, source-side
paths for renames/deletions and exact immutable comparison identities. Qualify
MCP, federation, grouping, diagrams and gitlinks through actual controlled peers
before optional-capability promotion. Use manifest/evidence-derived native test
inventory with historical negative controls. Run exact tag v1.13.8 in the GitHub
Action; reuse its eligible canonical issue and reconcile current-contract hosted
proof after a materially changed probe suite. No unbounded release discovery.

Copilot/plugin, ACP and viewer are unconsumed. MiniMax suggestions do not change
toolkit model defaults. No new Rules entry unless effective inventory changed.
Keep the weekly schedule. Use verified candidate executables during acceptance;
replace the system OCR only with the paired ready toolkit update.

#### Documentation and examples

Configuration owns URL/header semantics; GitLab documentation owns first setup.
Explain roots/terminal URLs, protocol tails, query/metadata handling, bearer and
extra-header semantics and the different evidence each command establishes.
Document installation, secrets availability, Rules/policy merge, manual readiness,
private explicit model test, advisory review and publication. Cover architecture,
Git/refs, detached same-project MR, permissions, WAF/CA and approval boundaries.
Protected variables have GitLab prerequisites independent of toolkit policy;
do not recommend unprotecting secrets as a general solution.

Share installation through a hidden example job. Manual self-test independently
installs and runs preflight/configure, without deliberately deleting a token or
automatically sending a model request. Explain current max-tools accurately;
preserve historical sections and remove false preflight registry/inventory/full-
inference claims. No additional configuration knobs or setup wizard.

### Verification

- Forge production callers through controlled HTTPS peers: library-signature
  blocking reproduction, exact default/override on all clients/methods, malformed
  value rejection before transport, unchanged non-forge headers and 403 gates.
- Inventory every forge transport entry and current User-Agent/configuration
  reference; verify all paths use one resolved policy and no obsolete name remains.
- URL/preflight: missing required inputs with metadata disabled; pathless
  openai/responses/anthropic; explicit terminals without /v1; custom prefixes;
  no doubled /v1; queries/metadata overrides; no extra inference requests;
  preflight/configure/native wire agreement and unchanged native-auth behavior.
- OCR: official assets, frozen readback, live comparison-side schema and actual
  reads/find/search, different B/H/T, dirty worktree, rename/delete/invalid side,
  real MCP/federation/group/diagram/gitlink transfers and failure isolation.
- Hypothesis: structured URL/protocol/delimiter/query variants, Unicode/control
  inputs, safe diagnostics and User-Agent length/ASCII boundaries; 100 default
  examples and 1000 local examples for touched properties/minimized regressions.
- Installed wheel/sdist entry points and independently usable manual example
  job; real boundary tests rather than mocked owner claims. New helpers/preflight
  >=90% branch-aware coverage; preserve overall 88% and existing floors.
- Review each logical commit; aggregate final diff; one Security diff scan then
  actual own-tool review with ChatGPT gpt-6.1-sol/xhigh, private debug, diagram
  mode local and --max-tokens-budget 0 after preparation/reachability checks.
  Inspect raw/admitted findings, DLP omissions, warnings and failed auxiliary
  reads. Second successful model review only for a concrete acceptance gap.
- Retain the exact admitted diagram in the feature PR. After corrections run
  one full quality gate on the final runtime head with appropriate installed
  checks, tree/history secret gates and dependency audit. Docs-only corrections
  do not repeat the global Security scan or full runtime gate.
- Protected feature CI and development publication; final release-focused set
  after metadata/archive; stable registry/receipt/tag/attestation/provenance and
  supported Python installs; independently read external state and site/main.

### Latest Validation Results

- Draft PR #309 contains the signed plan at 94b14c6. Signed local logical
  commits contain qualification, forge headers, URL/preflight, integration
  documentation and reviewed corrections; implementation has not been pushed.
- Exact-tag hosted baseline 43215747102 passed and created eligible Actions-owned
  issue #308. It predates the changed probe suite; current-contract hosted proof
  remains required at final feature delivery.
- Verified official Linux/Darwin binaries pass all twenty current contract
  groups. Frozen 1.13.7 readback preserves original bytes. Qualification-focused
  tests pass: 359 tests/10 opt-in skips. The consumer set passes 114 checks;
  its stale future-version negative control is corrected and passes separately.
- Actual HTTPS checks cover default/override GET/POST/PUT/DELETE headers,
  configuration propagation and the fail-closed `/user` 403 gate. New header
  and native-capability helpers measure 100% branch-aware coverage.
- Seven real Linux native TLS routes agree with environment/config normalization.
  Actual Responses query loss is recorded in upstream #1916. Pure parsing keeps
  valid URI components; exact native capability gates unsupported review routing.
  Metadata queries are separately verified through the toolkit HTTPS client.
  Native private-CA TLS fixtures run on Linux because macOS Go uses Keychain.
- Provider/native-auth/local focused checks pass: 274 tests/42 subtests, 92%
  preflight and 96% provider-config coverage. Structured provider properties pass
  with 1000 examples per property, including repeated/empty/encoded query values.
  Query-safe diagnostic regressions pass in the 98-test/42-subtest focused set.
- Documentation/example contracts pass 85 tests. The security-model refinement
  and accurate posting redirect docstring pass 54 affected contract checks.
  Changelog classification separates new comparison capability, pin maintenance
  and the independently installed manual-readiness bug fix.
- Aggregate self-review and the single Security diff scan of fa64183..6c2f9ce are
  complete. The sealed scan covers all eighteen changed source/evidence items
  plus supporting contracts, with no plausible candidates or deferred source.
  Independent architecture review backs the canonical model's environment,
  client-redirect, URL/native-capability and external-policy clarifications.
- The first real own-tool review of fa64183..6c2f9ce completed all 35 selected
  files with gpt-6.1-sol/xhigh, high effort and unlimited aggregate tokens. All
  three raw findings survived DLP. Corrected two stale test-double interfaces and
  strengthened the comparison oracle so base/head/target/index/worktree paths
  differ; inverse checks reject mixed-side enumeration. The 113-test focused set
  passes with official Darwin OCR, and 31 comparison checks pass with Linux OCR.
- The model-generated diagram was admitted and retained for the feature PR.
  No budget, tool-round or context-exhaustion warning occurred. Three optional
  planning requests timed out; upstream explicitly continues the main review
  without that plan, and every selected file completed. A failed guessed CLI
  read followed successful reads of the actual owner, leaving no owner gap.
  Debug trace retention reached its documented byte limit (307/315 tool calls
  retained); result, diagram, bootstrap and MCP inventory are complete. This
  diagnostic limit did not truncate the model's review context. The bootstrap's
  soft 2086/2000-character recommendation also caused no truncation. Unchanged
  oversized lock evidence remains explicitly omitted, not absent.
- Focused real-boundary fixes and scoped semantic review close all three
  findings; no uncovered runtime boundary requires a second full model review.
- The final full quality gate passes on the reviewed runtime: 5048 tests,
  357 subtests and 69 opt-in skips; 90% overall branch-aware coverage, 92%
  preflight, 96% provider configuration, 92% GitLab CI and 99% result contract.
  Clean wheel/sdist installations exercise the actual CLI and MCP outside the
  checkout. Public-tree/history secret scans and locked dependency audits pass.
  Current-contract hosted qualification, protected delivery and cleanup remain.

### Risks And Recovery

- Pathless OpenAI roots intentionally change to /v1. Explicit terminals without
  /v1 preserve the supported escape for a real root endpoint. Test both paths
  through actual configuration and native wire before acceptance.
- A shared User-Agent cannot guarantee every WAF rule; preserve real HTTP/auth
  failures and allow an explicit operator override without automatic spoofing.
- Qualification failures remain closed; inspect the failing owner before retry.
  A passing old suite is baseline evidence, not promotion authority for new probes.
- Hosted issue upsert must reuse eligible canonical identity. Reconcile duplicates
  through existing policy rather than creating a manual competing issue.
- Preserve private debug/auth/audit state and task process identity; clean only
  owned resources after extracting required proof. Do not kill unrelated work.
- On interruption recover from this complete plan, Git and required artifacts;
  do not replay side effects or completed expensive checks blindly.

### Resume Point

Push the fully checked feature with its exact admitted diagram, run exact-tag
hosted qualification on the current probe suite and reconcile its proof. Complete
protected feature/development delivery, then ordinary release delivery. No repeated
aggregate Security scan, full model review or runtime gate is justified by this
status-only update. Local paired update and cleanup remain required.

### Plan Fidelity Check

- [x] All approved outcomes and the hosted-workflow addition have REQ/WQ mapping.
- [x] One new variable, no endpoint-probe feature, protocol-specific /v1 behavior
  and explicit-path preservation match the approved replacement plan.
- [x] Local binary update, coverage, own-review diagram, ordinary release and
  external closure are included; unrelated conditional backlog remains inactive.
- [x] Sources, boundaries, tests, non-goals, risks/recovery and resume are complete.
- [x] Checked lifecycle/fidelity validation passes before implementation.

### Reconciliation Check

- [x] Initial local/remote main and clean tree matched the planning baseline.
- [x] Existing probes are identified as local baseline, not final hosted proof.
- [x] Initial active state and checked plan validation are reconciled.
- [ ] Final implementation, public contracts, review findings and delivery agree.

### Closure Gate

- [ ] All repository requirements have applicable final evidence.
- [ ] Findings and scope/state documents are reconciled without hidden tails.
- [ ] Feature delivery and development publication are verified.
- [ ] Release PR owns final notes/pins/authorization and checked archive/reset.
- [ ] Required external delivery is truthfully represented in Post-Close Delivery.

### Post-Close Delivery

The repository plan remains active until the release PR owns the checked archive
and reset. At that transition explicitly preserve all still-unverified protected
release CI/merge, stable publication/readback, issue/site/main reconciliation and
local update/cleanup as required external delivery. The overall goal stays active
until those outcomes are independently established. Do not create a closure PR.

### Handoff Notes

No unfinished implementation is hidden in an archived or compressed summary.
Qualification and review data stay private unless explicitly normalized and
admitted as public synthetic evidence. Preserve canonical release receipts,
Actions-owned issue comments and sealed Security findings; remove temporary
copies/build/debug assets after their required evidence has been extracted.

## Recently Completed

- [x] 2026-11-10: Completed Toolkit 0.14.7 — OCR 1.13.7, recoverable diagrams and private diagnostics; [full archived plan](docs/engineering/execution_history/plans/2026-11-10-toolkit-0-14-7-ocr-1-13-7-recoverable-diagrams-and-private-diagnostics.md).
- [x] 2026-11-06: Completed Internal engineering cycle corrections; [full archived plan](docs/engineering/execution_history/plans/2026-11-06-internal-engineering-cycle-corrections.md).
- [x] 2026-11-06: Completed Toolkit 0.14.6 — OCR 1.13.6, DLP precision and efficient delivery; [full archived plan](docs/engineering/execution_history/plans/2026-11-06-toolkit-0-14-6-ocr-1-13-6-dlp-precision-and-efficient-delivery.md).
- [x] 2026-11-04: Completed Toolkit 0.14.5 — DLP precision, OCR qualification and maintenance quality; [full archived plan](docs/engineering/execution_history/plans/2026-11-04-toolkit-0-14-5-dlp-precision-ocr-qualification-and-maintenance-quality.md).
- [x] 2026-10-31: Completed Toolkit 0.14.4 systematic DLP corrections and diagram source validation; [full archived plan](docs/engineering/execution_history/plans/2026-10-31-toolkit-0-14-4-systematic-dlp-corrections-and-diagram-source-validation.md).
- [x] 2026-10-30: Completed Toolkit 0.14.3 source-aware DLP and private corpus audits; [full archived plan](docs/engineering/execution_history/plans/2026-10-30-toolkit-0-14-3-source-aware-dlp-and-private-corpus-audits.md).
- [x] 2026-10-30: Completed Toolkit 0.14.2 compact bootstrap, diagram-only reports and DLP corrections; [full archived plan](docs/engineering/execution_history/plans/2026-10-30-toolkit-0-14-2-compact-bootstrap-diagram-only-reports-and-dlp-corrections.md).
- [x] 2026-10-29: Completed Toolkit 0.14.1 grouped diagrams and private debug qualification; [full archived plan](docs/engineering/execution_history/plans/2026-10-29-toolkit-0-14-1-grouped-diagrams-and-private-debug-qualification.md).
- [x] 2026-10-29: Completed Toolkit 0.14.0 range identity, typed diagrams, DLP qualification and Python 3.15; [full archived plan](docs/engineering/execution_history/plans/2026-10-29-toolkit-0-14-0-range-identity-typed-diagrams-dlp-qualification-and-python-3-15.md).
- [x] 2026-10-25: Completed Two-day GitHub Actions retention; [full archived plan](docs/engineering/execution_history/plans/2026-10-25-two-day-github-actions-retention.md).
