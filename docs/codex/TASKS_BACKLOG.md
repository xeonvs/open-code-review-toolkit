# Tasks Backlog

This file tracks future work that is not active. Active extraction work is owned by `PLANS.md`.

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
