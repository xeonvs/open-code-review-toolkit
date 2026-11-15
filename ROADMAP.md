# Roadmap

This roadmap describes the nearest and conditional outcomes, without calendar
commitments. [PLANS.md](PLANS.md) owns active execution. The
[toolkit strategy](docs/engineering/toolkit_strategy.md) owns implemented
architecture; [execution history](docs/engineering/execution_history/README.md)
owns completed milestones and releases. The [backlog](docs/codex/TASKS_BACKLOG.md)
keeps stable task IDs, dependencies, activation signals, next actions and exit
criteria.

**In progress** identifies active implementation and acceptance. **Conditional**
requires a demonstrated need and an approved bounded scope; **parked** has no
current activation signal. A qualified upstream capability alone does not activate
a new toolkit product or expand trust.

| Outcome | State | Scope and activation | Owner |
| --- | --- | --- | --- |
| Complete immutable evidence for large changes | In progress | Atomic B/H/P snapshots remain bounded without an artificial file-count ceiling; genuine hard limits stop before the model with a closed identity-bound diagnosis. | [Active plan](PLANS.md) |
| Bounded static .NET evidence and numeric precision | In progress | Declared project/package/framework facts, conservative source-scoped central links and shared MCP; full-span numeric DLP with inverse controls and private corpus replay. | [Active plan](PLANS.md), BL-010 slice |
| Further ecosystem/framework evidence | Conditional | One demonstrated missing pack with deterministic semantics, provenance, scoped completeness and common MCP validation. | [BL-010](docs/codex/TASKS_BACKLOG.md#bl-010-add-evidence-packs-from-demonstrated-use-cases) |
| Federation authentication and more forges | Conditional | A real upstream OAuth requirement or funded forge use case, preserving resource authorization and provider-neutral lifecycle boundaries. | [External integrations](docs/codex/TASKS_BACKLOG.md#external-integrations), BL-012 and BL-021 |
| Related-change or combined-delivery review | Conditional | An explicitly approved product/graph, immutable revision and publication contract, bounded resources and a separate implementation plan. | [BL-025](docs/codex/TASKS_BACKLOG.md#bl-025-evaluate-optional-review-of-related-mrs-and-delivery-sets) |
| File configuration and explicit model profiles | Parked | Repeated operational evidence must show direct settings are insufficient; choose one closed schema or matrix before implementation. | [Configuration and model profiles](docs/codex/TASKS_BACKLOG.md#configuration-and-model-profiles), BL-020 and BL-016 |
| Automatic profile routing | Conditional | Depends on explicit profiles, an owner-approved quality/cost policy and representative offline replay. | [BL-018](docs/codex/TASKS_BACKLOG.md#bl-018-evaluate-conservative-automatic-profile-routing) |

## Ordering notes

- Finish and externally verify the active release before activating an unrelated
  conditional product. Keep completed work out of future-work tables.
- Extend the existing evidence, framework, policy and federation owners. A new
  language rule does not supply a framework evidence pack; authentication does
  not supply object authorization.
- Versioned documentation remains a separate integration: the toolkit supplies
  package/version evidence and does not store documentation.
- Conditional profiles retain the existing signal-ownership conclusion and
  explicit budget/completeness controls. No new telemetry layer follows from
  upstream viewer, session or diagnostic changes.
