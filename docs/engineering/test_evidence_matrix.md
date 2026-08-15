# Test Evidence Matrix

This matrix records what the repository test suite proves and, equally importantly, what it does not prove. The governing rule is [Test doubles and integration proof](project_principles.md#test-doubles-and-integration-proof): a double may replace a collaborator beyond the production owner under test, but it may not replace that owner and still be cited as integration evidence.

## Evidence classes

- **Unit or policy:** pure parsing, normalization, ordering, rendering, validation, or orchestration. A replaced boundary owner limits the claim to wiring.
- **Boundary integration:** the production owner crosses a real filesystem, Git, HTTP, process, persistence, or protocol boundary; a controlled peer may sit beyond it.
- **Installed integration:** a built wheel or sdist-derived wheel runs in a clean environment with hostile import and path conditions.
- **External qualification:** the actual external component is executed. This evidence is version-specific and is not replaced by a fake response.
- **Static contract:** repository configuration, workflows, public examples, package contents, or documentation are inspected without claiming execution of the external service.

## v0.6.1 requirement-to-evidence audit

| Requirement or boundary | Production owner and entry point | Required observable result | Evidence | Double boundary and claim limit | State |
| --- | --- | --- | --- | --- | --- |
| #87 capture current protected target identity | `providers.gitlab.acquire_review_snapshot` | MR head, target project, protected branch, and target SHA agree through bounded HTTPS | `test_gitlab_snapshot_crosses_real_https_adapter_and_binds_protected_target`; identity, redirect, size, and deadline variants in the same module | local TLS GitLab peer is beyond the production urllib adapter | proven |
| #87 source cannot select policy and concurrent movement cannot switch the captured object | `review_runner._prepare_policy_context`; `GitRepositoryReader.fetch_commit` | exact captured SHA is fetched without moving checkout refs; unavailable or unsafe objects fail closed | `test_bounded_fetch_gets_exact_commit_without_moving_refs`; policy input negative cases; complete review-preflight E2E | real local bare remote is beyond Git plumbing; no Git reader mock | proven |
| #87 exact repository-owned rules and operator-owned external rules | `_prepare_policy_context`; `write_private_bytes`; `GitRepositoryReader.read_blob` | exact policy-commit blob becomes mode-0600 private input; checkout is unchanged; external absolute path is preserved | exact-policy transport test and complete review-preflight E2E | no owner is replaced | proven |
| #87 unchanged diff range with actual OCR rule consumption | `ocr_compat.run_contracts` invoking real `ocr review --preview` | the same base/head excludes the synthetic extension without the rule and selects it with target rules | `target_rule_selection_probe` in the OCR compatibility harness; committed OCR 1.9.4 evidence after rerun | actual OCR binary; no LLM needed for deterministic selection | proven |
| #87 target guidance and decisions, not base/source policy | `collect_repository_evidence(..., policy_ref=...)`; store; MCP | policy records bind policy SHA and changed-path applicability, source policy has no authority | collector policy tests; schema-v4 hostile readback; installed wheel/sdist MCP; complete review-preflight E2E | real Git/store/stdio in integration tests | proven |
| #87 schema compatibility | `EvidenceStore.read/write` | v4 policy identity round-trips; v1-v3 retain explicit legacy semantics and hostile extensions fail | schema tests in `test_evidence_model.py` | persisted files are real; mutation of fixture data is beyond loader | proven |
| #88 changed-template priority | template plugin plus core/store admission | added, modified, removed, renamed, and over-limit changed templates precede unchanged inventory without raising limits; partial remains explicit | `test_evidence_framework_plugins.py` priority cases and collector/store limit cases | temporary Git repositories and real store | proven |
| #88 installed queryability and version CLI | installed `ocr-ci`; installed stdio MCP | direct wheel and sdist-derived wheel expose typed late template facts and centralized version under hostile import/PATH conditions | `test_installed_policy_e2e.py` | clean built artifacts; real child process and stdio protocol | proven |
| #89 bounded provider projection | GitLab adapter plus `normalize_merge_request_context` | only title, description, labels, branch, identity and statuses survive; limits, controls, redaction and collisions are enforced | real-TLS adversarial provider test plus normalizer boundary tests | local TLS peer beyond adapter | proven |
| #89 source-head binding and quality-signal degradation | `acquire_review_snapshot`; `run_evidence_review` | mismatched head is rejected; no fabricated intent enters the store | real-TLS mismatch and complete preflight E2E | no provider-owner mock | proven |
| #89 persistence, hostile readback, bootstrap omission, MCP query | store/readback/project/MCP | closed invocation-trust descriptor round-trips; raw values are absent from bootstrap; summary/list/get expose values | `test_review_context.py`; installed wheel/sdist stdio MCP; complete preflight E2E | real files and stdio; direct dispatcher test alone is component evidence | proven |
| #89 raw text absent from argv, environment, logs, and receipts | `run_evidence_review`; result metadata | child argv contains only private bootstrap/rule paths; raw values are not serialized into those channels; receipt contains bounded toolkit reason | complete preflight E2E, review-context/bootstrap tests, approval receipt tests | synthetic child is beyond real subprocess launcher and queries real MCP before reporting calls | proven |
| #89 metadata cannot authorize policy, configuration, posting, suppression, or approval | separate provider projection, policy collector, posting policy | no data dependency from context values to those owners; any admitted field blocks automatic approval while comments remain eligible | architecture/static dependency review; receipt and posting-policy tests; complete preflight E2E | posting workflow mocks prove ordering/policy, not live GitLab mutation | proven for toolkit authority |
| #89 matching, contradictory, absent/ambiguous intent and objective-defect review semantics | toolkit-authored bootstrap guidance consumed by OCR/model | model output demonstrates calibrated outcomes without a follow-up question | deterministic guidance assertions exist; no fixed-response test is accepted as model evidence | a fake LLM would replace the behavior being claimed | qualification pending |
| #90 OCR 1.9.4 CLI/result/selection compatibility | compatibility harness against checksum-verified asset | actual binary passes version, help, preview, target-rule selection, deterministic local-gateway review, and result consumer contracts | hosted qualification plus local `probe-local`; compatibility evidence must be regenerated after adding selection probe | local gateway is beyond OCR's HTTP client and proves protocol/result behavior, not general model quality | proven |

The complete `run_evidence_review` synthetic test deliberately uses one controlled child executable beyond the production subprocess launcher. The child reads the exact generated rule artifact, starts the configured production MCP server over stdio, queries summary/policy guidance/MR context, and only then emits tool-call counts. It proves orchestration and boundary composition; it does not claim to be the real OCR selector. The separate compatibility probe supplies that real-consumer proof.

## Complete suite module audit

Every top-level test module is classified below. A module can contain more than one evidence class; the strongest class applies only to the named boundary, never to all tests in that file.

| Test module | Primary owners and evidence | Doubles and non-claims |
| --- | --- | --- |
| `test_actions_cleanup.py` | cleanup planning and bounded deletion policy; static workflow contract | API replacement tests prove classification/idempotence, not live GitHub deletion |
| `test_cli.py` | parser/dispatch unit contract; source version identity | patched dispatch is wiring only; installed CLI is proven in installed E2E |
| `test_common_helpers.py` | pure redaction/Markdown/config parsing | environment patching supplies hostile input, not an external integration claim |
| `test_distribution_contents.py` | real wheel/sdist archive contents | no registry publication claim |
| `test_evidence_ansible.py` | real temporary Git collection, typed store, MCP dispatcher | dispatcher calls are component evidence, not stdio; installed stdio is elsewhere |
| `test_evidence_categorize.py` | pure deterministic categorization | no boundary claim |
| `test_evidence_collectors.py` | parsers plus real immutable Git/store collection and deltas | monkeypatches around read counters or constrained stores prove batching/admission policy only |
| `test_evidence_composer.py` | parser semantics plus real Git/store/MCP component projection | no Composer execution or Packagist claim |
| `test_evidence_ecosystems.py` | static architecture/dependency ownership | no runtime integration claim |
| `test_evidence_framework_plugins.py` | pure static plugin contracts plus real Git/core/store priority cases | patched limits are boundary-condition inputs; no framework runtime execution claim |
| `test_evidence_go.py` | parser plus real Git/store/MCP component projection | no Go toolchain execution claim |
| `test_evidence_infrastructure.py` | parser plus real Git/store/MCP component projection | no container/CI execution claim |
| `test_evidence_invocation.py` | closed environment-to-identifier projection | synthetic mappings, no provider API claim |
| `test_evidence_javascript.py` | parser plus real Git/store/MCP component projection | no npm/Yarn/pnpm execution or registry claim |
| `test_evidence_mcp.py` | dispatcher abuse tests and real stdio child-process protocol launch | in-memory `serve` tests are component evidence; process tests prove stdio/import/PATH |
| `test_evidence_model.py` | real persistence, atomic replacement, hostile readback, schema and budgets | patched `os` calls prove error handling/ordering where the filesystem owner is not claimed |
| `test_evidence_policy.py` | pure closed policy grammar, matching and bounds | no repository acquisition claim |
| `test_evidence_repository.py` | real Git objects/plumbing, private files, collection/store | subprocess wrappers used for counting/corruption limit those cases to orchestration/parser rejection; neighboring real Git tests prove plumbing |
| `test_gitlab_provider.py` | local TLS provider transport, real Git fetch/object reads, full read-only review preflight through real store/config/stdio/subprocess | local peer and synthetic child sit beyond production owners; actual OCR selection is separately qualified |
| `test_install_local_artifact.py` | exact requirement/hash generation unit policy | monkeypatched hash/metadata inputs do not prove pip installation |
| `test_installed_policy_e2e.py` | clean wheel and sdist-derived wheel, isolated imports, private files, real Git and stdio MCP | package installer/venv are real; no OCR model claim |
| `test_integration_contracts.py` | static public example/workflow/rules contracts | “integration” here means repository integration configuration, not execution |
| `test_ocr_compat.py` | qualification policy/unit tests; committed evidence validation | mocked GitHub/download responses prove bounds/retries only; hosted and local harness runs prove actual asset execution |
| `test_ocr_result_contract.py` | fixed upstream-result parser compatibility | fixture parsing, not OCR execution |
| `test_operations_docs.py` | static public documentation/workflow contract | no operator or provider execution claim |
| `test_posting_approval.py` | approval policy, exact-SHA request construction, ordering and fail-closed workflow | API owners are replaced; no live GitLab approval integration is claimed because writes are unsafe in tests |
| `test_posting_helpers.py` | pure formatting/workflow policy, real Git reads, real local HTTP transport serialization, real result-file boundaries | mocked GitLab API owner cases prove response/error/workflow behavior only; local peer proves transport, not GitLab semantics |
| `test_posting_suggestions.py` | pure proof-bound suggestion decisions | fake readers are collaborators beyond the pure decision owner; no Git blob integration claim |
| `test_python_support.py` | static metadata/CI support range | supported interpreters are proven by the quality matrix, not this test alone |
| `test_quality_script.py` | real synthetic Git history for Gitleaks range plus static wrapper policy | fake scanner proves wrapper invocation/range, not secret-detection efficacy; pinned real Gitleaks runs before push |
| `test_release_authorization.py` | pure authorization rules plus real bounded helper subprocess/filesystem behavior | API response fixtures do not prove GitHub state; release closure requires live readback |
| `test_release_notes.py` | parser and repository changelog structure | no GitHub Release publication claim |
| `test_release_receipt.py` | receipt schemas, descriptor-safe files, release workflow policy | mocked provider requests prove request sequencing/parsing only; stable closure requires live registry/GitHub readback |
| `test_result_contract.py` | pure normalized outcome parser | no OCR execution claim |
| `test_review_context.py` | real store persistence/hostile reload and MCP component projection | direct dispatcher is not stdio; stdio proof is installed/full-preflight E2E |
| `test_review_runner.py` | private result/filesystem owner, real child-process launcher, receipt parser; separate wiring tests | patched subprocess/orchestration tests are explicitly unit evidence only |
| `test_runtime_helpers.py` | config filesystem boundaries and real local preflight HTTP transport; MCP/config parsing | mocked binary and `URL_OPENER` cases prove version/request/error policy only, not executable/network integration |
| `test_testpypi_preview.py` | registry-manifest parser and static workflow contract | fixture index payloads do not prove publication; live TestPyPI/PyPI verification is a release gate |

## Unsafe or nondeterministic external boundaries

The suite intentionally does not perform live GitLab comment, discussion, cleanup, or approval writes; live GitHub issue/release mutations; or PyPI publication. Their tests prove closed payloads, ordering, fail-closed decisions, transport serialization, and receipt parsing. Release completion requires independent live readback as defined in `docs/release.md`.

Likewise, a deterministic local LLM gateway proves OCR request/result integration but cannot prove general model judgment. Model-dependent intent calibration remains a named qualification item until exercised against the supported OCR/model path; no mock-selected finding can close it.
