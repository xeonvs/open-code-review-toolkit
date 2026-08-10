# Project Principles

This is the short index of stable cross-cutting engineering rules for Open Code Review Toolkit.

## Core Principles

1. Keep the package provider-neutral; isolate GitLab behavior behind its adapter boundary.
2. Preserve safety properties before compatibility: bounded input, redaction, rendering safety, write limits, and ownership boundaries are part of the product contract.
3. Keep runtime dependencies at zero until a documented package boundary justifies one.
4. Keep public examples and fixtures synthetic and free from local or private infrastructure details.
5. Keep the Open Code Review binary external; preflight verifies it but the package does not install it.
6. Keep current user configuration environment-driven and document every supported variable centrally. Any future non-secret file configuration requires an explicit trust, schema, and precedence design.
7. Keep active work resumable from `PLANS.md`; keep inactive work in `docs/codex/TASKS_BACKLOG.md`.
8. Use coherent production-quality slices when work must be decomposed; do not leave placeholder architecture as a milestone.
9. Require changelog fragments for user-visible 0.x changes and SCM tags for versions.
10. Treat TestPyPI as public disclosure and preserve the manual privacy/license gate before publishing.
11. Treat automated security scores as evidence to classify, not targets to game; remediate concrete repository-owned risk and document temporal or governance constraints truthfully.
12. Version public behavior deliberately. An incompatible pre-1.0 contract change may select the next minor version, but it is not delivered to stable users until the versioned package and release artifacts are published and independently verified.
13. Keep implementation and release as one traceable objective whenever stable publication is requested or required. Feature validation proves readiness; registry and GitHub readback prove delivery.
14. A deferral is a blocked or pending release state, not successful closure. Preserve the exact continuation point so a later agent does not infer that a development build satisfied a stable-release promise.
15. Keep the toolkit release version single-sourced from VCS tags through `hatch-vcs`. Runtime code reads `ocr_toolkit.__version__`; it must not duplicate an upcoming or current release literal in servers, user agents, reports, or tests. Schema, wire-protocol, fixture, and qualified-upstream versions are separate compatibility contracts: use explicitly named constants and change them only with their own migration or qualification evidence.
16. Treat secret scanning as a local publication gate, not only a hosted CI check. Pin one scanner version in the repository-owned wrapper and make CI read that pin, scan feature history before it is pushed, and fail closed when the exact engine or authenticated base range is unavailable. Keep the external scanner lifecycle separate from the Python quality environment.
17. Reconcile planning from current code, tests, and published behavior before retaining historical backlog wording. An original end-state description is evidence of intent, not proof that its scope or dependency graph remains current.
18. Classify dependencies by purpose: implementation dependencies provide a consumed interface, safety dependencies guard a risk boundary, and rollout dependencies keep an intermediate release coherent. Conditional work never blocks unconditional work merely because both appear in the desired end state.
19. Separate repository authorization from external delivery without duplicating repository work. The release PR is the final repository mutation and records only reviewed repository truth plus pending external gates. Exact-tree authorization, an immutable machine-readable release receipt, independent registry/tag/Release/provenance/hash/install readback, and issue closure complete delivery after merge without a redundant closure PR.
20. When an architectural milestone becomes implemented, update narrative current-state documentation in the same closure as plan, roadmap, and backlog status. Strategy and README must not continue describing the shipped architecture as a transition or target.
21. Archive older completed execution plans by stable release tag only after their receipts are complete. Maintain a validated index that lets future agents find the original decisions and evidence without turning `PLANS.md` into the permanent release-history database.

## Boundary Invariants

1. Enforce limits while consuming or producing data, not after an unbounded operation completes. Every limit names and tests its unit: bytes, code points, lines, records, or elapsed time.
2. Treat repository content, persisted evidence, subprocess output, inherited environment, and working-directory imports as untrusted at every boundary. Revalidate and redact on load even when the toolkit created the artifact.
3. Bind every Git plumbing caller to the validated repository and immutable refs. Remove process-level repository/object-store overrides, ignore global/system configuration, constrain repository configuration, and disable replace-object behavior.
4. Test semantic parsers against the external format, including key reordering, indentation width, scalar/mapping alternatives, markers, optional fields, status variants, digests, URLs, and bounded malformed-input degradation.
5. Treat one validated defect as a risk class: audit sibling trust boundaries and parsers, and make negative tests reach and assert the intended rejection or degradation path. Evidence identities describe stable applicability and source scope, while mutable constraints and versions remain values; alternatives that can coexist require distinct identities.
6. Keep related state transitions atomic: snapshots, indexes, deltas, receipts, and reports must not reference records or mandatory fields that were rejected, truncated, or omitted. Use NUL-delimited Git path records, explicit raw-descriptor ownership transfer, and recursive nested-configuration redaction at their trust boundaries.
7. Prove executable integrations from installed artifacts with restricted environments, hostile working-directory shadow modules, private permissions, and the real protocol client when available.
8. Compose mandatory report metadata once and apply it to skipped, clean, warning, error, and finding outcomes through one invariant matrix.
9. Profile realistic bounded data by separating cold-start validation from steady-state requests; optimize the measured bottleneck rather than protocol dispatch by assumption.
10. Before implementing a parser or trust boundary, record the grammar, normalization and degradation policies, budget units, inherited-process state, and adversarial fixtures in the active plan or tests.
11. Missing evidence supports a negative conclusion only when the applicable component, domain, and scope explicitly report complete coverage; absent, partial, runtime-dependent, and unavailable coverage remain unknown.

## Documentation Ownership

- `README.md` owns the concise public introduction and quick start.
- `docs/configuration.md` owns the environment contract.
- `docs/gitlab.md` owns GitLab installation and operating guidance.
- `docs/security.md` owns the runtime trust model; `SECURITY.md` owns vulnerability reporting.
- `docs/development.md` owns local contributor commands.
- `docs/release.md` owns release classification, delivery, and disclosure.
- `AGENTS.md`, `PLANS.md`, and `docs/codex/` own agent workflow rather than product behavior.
