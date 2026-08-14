# Project Principles

This document owns durable cross-cutting engineering invariants for Open Code Review Toolkit. Contributor and release procedures link to these invariants instead of restating them. Public product behavior remains owned by the user-facing documents listed under [Documentation ownership](#documentation-ownership).

## Product And Architecture

1. Keep provider-neutral behavior in the core and provider-specific behavior behind explicit adapters.
2. Keep runtime dependencies at zero until a documented package boundary justifies one.
3. Keep the Open Code Review binary external; the toolkit verifies but does not install it.
4. Keep supported user configuration environment-driven and documented in one public contract. A future non-secret file format requires an explicit schema, trust source, and precedence design.
5. Deliver large changes as coherent production-quality slices with explicit module and service boundaries rather than placeholder architecture.
6. Keep each runtime module centered on one cohesive owner and lifecycle. When independent parsing, acquisition, persistence, transport, or projection responsibilities accumulate, extract already characterized blocks behind explicit package boundaries before the unit can no longer be reviewed end to end. Reuse pure contracts and helpers rather than duplicating them. Size and complexity are review signals, not numeric lint targets.
7. Version public behavior deliberately. Readiness and delivery are different states; `docs/release.md` owns their lifecycle.
8. Treat automated security scores as evidence to classify, not targets to game. Repository-owned risks receive evidence-backed fixes; temporal and governance limits remain explicit.
9. Derive active scope and dependencies from current implementation, tests, and published behavior. Historical plans and backlog wording are intent evidence, not current-state authority.
10. Keep stable evidence identity tied to semantic applicability and source scope. Mutable versions and constraints remain values; alternatives that can coexist retain distinct identities.
11. Permit a missing fact to support absence only when the applicable component, domain, and scope report complete coverage. Partial, runtime-dependent, unavailable, and absent coverage remain unknown.

## Trust Boundary Invariants

### Repository content remains data

Treat analyzed repository content, inherited process state, subprocess output, and working-directory imports as untrusted. Do not import or execute code from the analyzed repository; inspect immutable objects and bounded text instead. Bounded diagnostic Git and toolkit subprocesses remain permitted when they preserve the same isolation boundary.

### Bounded data lifecycle

Enforce byte, code-point, line, record, and time limits while data is consumed or produced, with the unit named in the contract and exercised at its boundary. A post-hoc check cannot make an unbounded capture bounded. Bounded, redacted read-only diagnostics remain valid; the prohibited mechanism is unbounded acquisition or unsafe adoption of its result.

### Persisted and atomic state

Treat persisted evidence, configuration, security receipts, and release receipts as hostile on every load, including artifacts created by the toolkit. Revalidate exact closed schemas at every object level, apply bounds and recursive redaction again, and accept related snapshots, indexes, deltas, diagnostics, receipts, and report fields atomically.

### Immutable Git identity

Bind Git plumbing to the validated repository and immutable refs. Isolate object identity from process, global, system, repository, object-store, and replacement-ref controls; parse path-bearing records through NUL-delimited plumbing and transfer raw descriptor ownership exactly once. Read-only Git diagnosis remains valid when it uses the same isolated boundary.

### External format parsing

Define semantic grammar, normalization, optional-field handling, and bounded degradation before implementing a parser. Equivalent key order, indentation, scalar or mapping forms, markers, URLs, digests, and status variants must not acquire accidental semantics from one canonical fixture spelling.

### Network acquisition

Bounded HTTP reads are diagnostic evidence until a closed endpoint allowlist, redirect-safe authentication, transfer result, allowed status, and private same-directory atomic replacement all succeed. Read-only probes are permitted; a size limit alone does not authorize a response as trusted state.

### Provider mutation identity

A destructive provider mutation is automated only when the mutation request itself binds the validated immutable identity. Preflight and post-write reads may diagnose state but cannot close a mutation-time race. If the provider offers no guard, existing state is preserved for explicit provider-owned policy or operator action.

### Installed integration proof

Executable integration claims require clean built artifacts, restricted environments, hostile working-directory shadow packages, private permissions, and the real protocol client where practical. Unit mocks establish local behavior but not installation, import, process, or protocol correctness.

### Public source and disclosure

Tracked public source, fixtures, examples, diagnostics intended for publication, and release artifacts contain only synthetic names, hosts, repositories, and payloads. TestPyPI is public disclosure. Local secret scanning covers unpublished feature history before its first push; private audit inputs and artifacts remain outside tracked content.

### Outcome consistency

Mandatory evidence and usage metadata are composed once and applied across skipped, clean, warning, error, and finding outcomes. Independent outcome branches must not redefine whether the same run is complete, partial, clean, or failed.

## Documentation Ownership

- `README.md` owns the concise public introduction and quick start.
- `docs/configuration.md` owns the environment and generated-configuration contract.
- `docs/operations.md` owns the public review state machine; `docs/gitlab.md` owns GitLab setup and operator procedure.
- `docs/security.md` owns runtime trust guarantees; `SECURITY.md` owns vulnerability reporting.
- `docs/development.md` owns contributor workflow, implementation conventions, and validation selection.
- `docs/release.md` owns release classification, authorization, publication, recovery, and plan archival.
- `docs/engineering/toolkit_strategy.md` and `ROADMAP.md` own durable direction and outcome state; `PLANS.md` owns active or blocked repository work; `docs/codex/TASKS_BACKLOG.md` owns inactive work.
- `docs/codex/AGENT_EXECUTION_PITFALLS.md` is a diagnostic incident catalogue. It owns no engineering invariant or procedure.
- `docs/engineering/execution_history/` preserves historical plans and receipts without turning historical wording into current instruction.

An invariant or public behavior has one canonical owner. Secondary documents may link to it, describe applicability, or record historical evidence, but they do not create a competing imperative copy. Tests protect runtime behavior and concrete lifecycle gates rather than duplicated wording across instruction files.
