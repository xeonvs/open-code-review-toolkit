# Tasks Backlog

This file tracks future work that is not active. Active extraction work is owned by `PLANS.md`.

## Backlog Item: Native fuzzing campaign

Status: parked
Priority: medium

### Activation Trigger

- A supported Python fuzzing backend is selected with reproducible local execution, bounded CI resources, and corpus ownership.

### Goal

Fuzz the untrusted-input boundaries with meaningful targets for result normalization, context rendering, GitLab payload parsing, and registry metadata validation. Integrate a public fuzzing service only after the targets demonstrate useful coverage and stable crash minimization.

### Next Safe Action

1. Compare Atheris with property-based alternatives across Python 3.10-3.14 and design a small synthetic seed corpus without adding a runtime dependency.

### Exit Criteria

- Native targets run locally and in bounded CI, retain minimized synthetic regressions, publish no repository or provider secrets, and are recognized by the selected fuzzing service.

## Backlog Item: OpenSSF Best Practices registration

Status: owner action
Priority: low

### Activation Trigger

- The owner is ready to authenticate at `bestpractices.dev` and attest every passing-level criterion truthfully.

### Goal

Register the public repository for an OpenSSF Best Practices badge without guessing owner-only governance or project-usage answers.

### Next Safe Action

1. Complete the passing-level questionnaire with evidence links to the public repository and leave unsupported criteria unmet.

### Exit Criteria

- The public badge record exists, all answers have current evidence, and the README displays only the earned status.

## Backlog Item: Additional provider adapters

Status: parked
Priority: low

### Activation Trigger

- A provider-neutral core has shipped and a concrete provider integration has an owner and testable API contract.

### Goal

Add another code-hosting adapter without weakening the provider-neutral core or GitLab behavior.

### Next Safe Action

1. Write an adapter contract proposal based on the shipped GitLab boundary and validate it against synthetic fixtures.

### Exit Criteria

- The new adapter has isolated tests, documentation, and no provider-specific leakage into core modules.

## Backlog Item: File-based user configuration

Status: parked
Priority: low

### Activation Trigger

- Environment-only configuration becomes a demonstrated usability constraint after v0.1.

### Goal

Evaluate a versioned user configuration file without silently changing environment precedence or secret handling.

### Next Safe Action

1. Draft a schema and threat model; do not implement until compatibility and migration behavior are agreed.

### Exit Criteria

- Schema, precedence, migration, secret handling, and validation behavior are documented and tested.
