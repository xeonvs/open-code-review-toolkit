# Agent Execution Pitfalls

This is a diagnostic catalogue of recurring incident classes. It is not an instruction source: current requirements live with the linked canonical owner, and prevention lives in the linked subsystem check. Historical evidence explains why the control exists without making old plans normative.

Root-cause vocabulary:

- **missing rule** - no canonical requirement existed when the incident occurred;
- **conflicting rule** - active sources prescribed incompatible outcomes;
- **not loaded** - the requirement existed only in secondary context that the workflow did not reliably select;
- **unenforced rule** - prose existed, but the relevant process had no effective stop.

## Delivery closed at readiness

- **Symptom:** A feature merge or development package was treated as delivery while stable users still received the old contract.
- **Root cause:** missing rule; implementation and stable delivery were modelled as separate objectives.
- **Canonical owner:** [Release-required changes](../release.md#release-required-changes).
- **Control:** release authorization, receipt, immutable-release, registry, provenance, install, and issue-closure checks in `.github/workflows/release.yml` and their release test suites.
- **Historical evidence:** [0.2.0 process correction](../engineering/execution_history/releases.md#plan-toolkit-0-2-0).

## Candidate supplied its own release authorizer

- **Symptom:** Candidate code could decide whether its own tree, metadata, and checks authorized publication.
- **Root cause:** unenforced rule; exact-tree validation did not establish the trust source of the validator.
- **Canonical owner:** [Stable release](../release.md#stable-release).
- **Control:** `.github/workflows/release.yml` checks out the protected reviewed base for authorization; `tests/test_release_authorization.py` binds that checkout separately from candidate inspection.
- **Historical evidence:** [0.4.7 final OCR correction](../engineering/execution_history/releases.md#plan-toolkit-0-4-7).

## Status representations drifted from current state

- **Symptom:** Implemented scope remained in the backlog or status tables, diagrams, and narrative current-state prose disagreed.
- **Root cause:** not loaded; the implementation changed without selecting every status-bearing representation owned by the milestone.
- **Canonical owner:** [Planning and documentation lifecycle](../development.md#planning-and-documentation-lifecycle).
- **Control:** logical-commit and release-PR self-review reconcile current code, roadmap table and diagram, backlog, strategy, and README before changing milestone state.
- **Historical evidence:** [execution-history index](../engineering/execution_history/README.md).

## A completed plan remained in the active registry

- **Symptom:** `PLANS.md` retained an externally reconciled release cycle and became a second release-history database.
- **Root cause:** conflicting rule; active-state and archive lifecycle descriptions prescribed different retention points.
- **Canonical owner:** [External reconciliation and plan archiving](../release.md#external-reconciliation-and-plan-archiving).
- **Control:** ordinary release-PR documentation review follows the canonical lifecycle; no archive-specific executable gate is needed.
- **Historical evidence:** [M2 archive correction](../engineering/execution_history/releases.md#plan-toolkit-0-5-0).

## Unpublished history reached the remote secret scan first

- **Symptom:** Tip validation passed, but a secret-shaped synthetic value in an intermediate commit failed the hosted feature-range scan after push.
- **Root cause:** unenforced rule; local validation did not reproduce the pinned scanner and complete first-parent range.
- **Canonical owner:** [Public source and disclosure](../engineering/project_principles.md#public-source-and-disclosure) and the [local validation procedure](../development.md#local-validation).
- **Control:** `scripts/gitleaks.sh` fails closed on the pinned engine and complete unpublished feature range; `tests/test_quality_script.py` protects that range construction.
- **Historical evidence:** [M2 rewritten-range gate](../engineering/execution_history/releases.md#plan-toolkit-0-5-0).

## A post-hoc limit was called bounded I/O

- **Symptom:** A complete subprocess, Git, HTTP, configuration, or protocol payload was captured before its byte, line, record, or time limit was checked.
- **Root cause:** unenforced rule; ordinary fixtures tested the final value rather than acquisition at the boundary.
- **Canonical owner:** [Bounded data lifecycle](../engineering/project_principles.md#bounded-data-lifecycle).
- **Control:** boundary-specific tests exercise over-limit producers, multibyte units, missing terminators, descriptor growth, timeout/termination, and retained prior state.
- **Historical evidence:** [0.4.7 final OCR correction](../engineering/execution_history/releases.md#plan-toolkit-0-4-7).

## Persisted state bypassed hostile readback

- **Symptom:** A toolkit-created artifact bypassed exact schema, redaction, size, or cross-reference checks when loaded again.
- **Root cause:** unenforced rule; file ownership was mistaken for future content integrity.
- **Canonical owner:** [Persisted and atomic state](../engineering/project_principles.md#persisted-and-atomic-state).
- **Control:** hostile reload tests reject unknown nested fields, replaced or linked artifacts, oversized values, invalid references, and partial state.
- **Historical evidence:** [0.4.7 final OCR correction](../engineering/execution_history/releases.md#plan-toolkit-0-4-7).

## A bounded HTTP response became trusted too early

- **Symptom:** A size-limited response crossed into trusted state before endpoint, redirects, authentication, transfer status, and atomic replacement all committed.
- **Root cause:** unenforced rule; a byte limit was treated as the complete trust decision.
- **Canonical owner:** [Network acquisition](../engineering/project_principles.md#network-acquisition).
- **Control:** bounded HTTP tests reject unknown endpoints, unsafe authentication redirects, failed status or transfer, partial output, and non-atomic replacement.
- **Historical evidence:** [0.4.7 final OCR correction](../engineering/execution_history/releases.md#plan-toolkit-0-4-7).

## Git identity was isolated in only one caller

- **Symptom:** A sibling Git helper, repository configuration, object-store override, or replacement ref changed which object a reviewed SHA named.
- **Root cause:** unenforced rule; isolation was implemented as a local environment checklist rather than one object-identity invariant.
- **Canonical owner:** [Immutable Git identity](../engineering/project_principles.md#immutable-git-identity).
- **Control:** real-repository tests cover process, global/system, repository, object-store, replacement-ref, path-record, and sibling-caller behavior.
- **Historical evidence:** [0.4.7 final OCR correction](../engineering/execution_history/releases.md#plan-toolkit-0-4-7).

## Destructive provider write lacked a mutation-time guard

- **Symptom:** Automation read an expected SHA, then deleted, reset, withdrew, or invalidated state through an endpoint that could not bind that SHA.
- **Root cause:** unenforced rule; preflight and readback were treated as a substitute for mutation-time identity.
- **Canonical owner:** [Provider mutation identity](../engineering/project_principles.md#provider-mutation-identity); public supported behavior remains in [operations](../operations.md).
- **Control:** provider transaction tests assert exact-SHA guarded write endpoints and absence of unsupported destructive operations.
- **Historical evidence:** [0.4.7 final OCR correction](../engineering/execution_history/releases.md#plan-toolkit-0-4-7).

## One fixture spelling stood in for a parser contract

- **Symptom:** Equivalent valid key order, indentation, scalar/mapping, marker, URL, digest, or status forms failed despite one canonical fixture passing.
- **Root cause:** unenforced rule; tests mirrored implementation structure instead of the external grammar.
- **Canonical owner:** [External format parsing](../engineering/project_principles.md#external-format-parsing).
- **Control:** semantic-variant matrices exercise equivalent forms, malformed optional values, and bounded degradation that preserves unrelated facts.
- **Historical evidence:** [M2 framework parser corrections](../engineering/execution_history/releases.md#plan-toolkit-0-5-0).

## Mocks stood in for installed integration

- **Symptom:** Unit tests passed while the built artifact failed under the real protocol client, restricted `PATH`, permissions, or hostile working directory.
- **Root cause:** unenforced rule; function behavior was mistaken for installation and process-lifecycle proof.
- **Canonical owner:** [Installed integration proof](../engineering/project_principles.md#installed-integration-proof).
- **Control:** clean wheel/sdist, hostile-shadow, restricted-environment, private-permission, and real-protocol E2E tests.
- **Historical evidence:** [M2 release-grade installed-artifact checkpoint](../engineering/execution_history/releases.md#plan-toolkit-0-5-0).

## A relevant boundary rule lived only in secondary context

- **Symptom:** A typical parser, provider, or subprocess change passed routine checks but repeated a known failure class that was described only in a long incident document not selected for the change.
- **Root cause:** not loaded; applicability depended on an agent remembering to reread an accumulating secondary rule set.
- **Canonical owner:** [Local validation](../development.md#local-validation) selects the relevant [trust-boundary invariant](../engineering/project_principles.md#trust-boundary-invariants) from the changed subsystem.
- **Control:** the active plan identifies changed boundaries and focused behavioral tests before the complete quality gate; the incident catalogue is consulted only to diagnose a matching failure.
- **Historical evidence:** [0.4.7 final OCR correction](../engineering/execution_history/releases.md#plan-toolkit-0-4-7).

## Outcome branches disagreed about the same run

- **Symptom:** Clean, skipped, warning, or error branches omitted mandatory evidence or described inconsistent completion state.
- **Root cause:** unenforced rule; outcomes were assembled independently and tests asserted prose rather than one result invariant.
- **Canonical owner:** [Outcome consistency](../engineering/project_principles.md#outcome-consistency).
- **Control:** table-driven result and posting tests cover skipped, clean, warning, error, finding, partial, and zero-value cases through shared contracts.
- **Historical evidence:** [0.4.7 final OCR correction](../engineering/execution_history/releases.md#plan-toolkit-0-4-7).
