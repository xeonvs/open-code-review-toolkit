# Agent Execution Pitfalls

## Closing a public-contract change after only the feature merge

**Failure mode:** A feature changes a public command or integration contract, its pull request merges, and a TestPyPI `.devN` build succeeds. The plan is then marked completed even though stable PyPI users still receive the old behavior.

**Why it happens:** Implementation, preview publication, and stable delivery are treated as separate mental tasks even when the user asked for one outcome. SCM-derived versions also make the source tree appear ready for the next version without proving that a stable tag or package exists.

**Required prevention:**

1. Classify the work at plan start and write the target stable version into `PLANS.md`.
2. Treat feature merge and TestPyPI `.devN` verification as intermediate receipts.
3. When release is required, prepare the version/changelog release PR immediately after the development build is verified.
4. Keep the objective active until the release workflow publishes and independent readback confirms PyPI, TestPyPI, the signed tag, immutable GitHub Release, hashes, attestations, and supported-Python installs.
5. If publication is intentionally deferred, record who deferred it, why, and the exact command or PR needed to resume.

**Closure question:** "Can a user installing from production PyPI obtain the promised behavior now?" If not, the stable-release objective is not complete.

This note records recurring execution mistake patterns discovered during real work. Record generalized lessons, not one-off complaints.

## Planning And Context Discipline

- Do not leave durable scope, source boundaries, or resume state only in chat; keep the active plan current.
- Do not treat a local working specification as publishable documentation; translate its public requirements and keep private audit criteria outside tracked files.
- Do not silently reduce extraction scope because the source is large; split it into coherent, validated subsystem slices.
- Do not commit completed work while the active plan still says `planned` or `in_progress`.
- Do not close a milestone by updating only its execution plan. Reconcile roadmap labels, diagram status colors, and the future backlog in the same closure change. Remove an entry only after its own deliverables and validation are proven complete; preserve unfinished adjacent work even if an earlier feature plan accidentally marked it complete.

## Source And Privacy Boundaries

- Inventory tracked source explicitly and avoid broad copy commands that could include ignored or untracked files.
- Do not turn one-time private marker criteria into a tracked denylist or test fixture.
- Do not use real provider payloads, hosts, repositories, or credentials in public fixtures.

## Tooling And Validation Hygiene

- Prefer the narrowest reproducer before broad reruns.
- Verify both UTF-8 byte limits and Python character limits when changing note formatting.
- Treat tests, lint, typing, artifact checks, install smoke, privacy scans, and source-integrity checks as distinct gates.
- Pin third-party Actions by full commit SHA and keep readable version comments beside the pin.
- When a review finds one boundary defect, enumerate and inspect sibling boundaries before declaring the class fixed.
- Give negative tests valid preconditions up to the exact branch they target, then assert the precise error contract. A fixture rejected earlier for an unrelated reason is missing coverage.
- Use NUL-delimited Git records for paths, explicit descriptor-ownership transfer for `fdopen`, and recursive redaction for nested diagnostic configuration.

## Learning Loop

- Promote a repeated stable lesson into `docs/engineering/project_principles.md`.
- Record actionable future work in `docs/codex/TASKS_BACKLOG.md` only when it has an activation trigger and next safe action.

## Deriving rollout dependencies from the desired end state

**Failure mode:** A backlog is organized as a linear path through the target architecture. Existing capabilities become blocked on future components, independent foundations become coupled, or one technical refactor ships an unsafe intermediate user state.

**Why it happens:** Architecture dependencies, implementation conveniences, and user-visible release dependencies are treated as the same graph. Candidate priorities may also be inferred from code that already exists rather than demonstrated repository demand. Field-completeness tests then preserve a structurally complete but semantically incorrect backlog.

**Required prevention:**

1. Inventory implemented primitives before assigning dependencies; a future integration may depend on a component even when current operation and documentation do not.
2. Label each edge as an implementation, safety, or rollout dependency and remove edges that express only the desired end state.
3. Test every proposed intermediate release: if it removes information or safety before its replacement is available, combine the work into one user-visible slice or retain an explicit compatibility mode.
4. Keep independent foundations parallel and join them only at the first interface that consumes both.
5. Select ecosystem and framework priorities from anonymized inventory, deterministic detection, synthetic fixtures, and expected review impact rather than parser familiarity.
6. Review critical forbidden and required edges explicitly when the backlog changes. Do not encode mutable item counts, identifiers, wording, or temporary dependency edges into the permanent product test suite.

## Treating post-hoc checks as bounded I/O

**Failure mode:** Code captures an entire Git response or newline-delimited request and only then checks its size or item count. Character counts are also used where the contract is bytes.

**Why it happens:** Ordinary fixtures make the final value look bounded, hiding the allocation and decoding that already happened. ASCII-only tests hide byte/code-point divergence.

**Correction:** Bound the read itself, stop producers after the allowed prefix plus one sentinel unit, and name the unit in the constant. Test a line without a newline, multibyte text, excessive Git output, and subprocess termination.

## Trusting toolkit-created evidence on reload

**Failure mode:** Collection validates records, but reload assigns snapshots, deltas, or diagnostics directly. A replaced private artifact bypasses the original redaction, size, or cross-reference checks.

**Why it happens:** File ownership is confused with future content integrity. Persistence is not treated as a fresh deserialization boundary.

**Correction:** Validate, bound, normalize, redact, and cross-check every persisted field on every read. Test missing references, oversized nested delta values, secrets, control characters, hard links, and schema/type mismatches.

## Testing only the canonical parser spelling

**Failure mode:** A parser accepts fixtures that mirror its implementation but rejects equivalent valid syntax: reordered keys, another indentation width, scalar sources containing colons, environment markers, alternate digests, malformed optional URLs, or additional Git status letters.

**Why it happens:** Fixtures come from the happy-path algorithm rather than the external format's semantic grammar and degradation policy.

**Correction:** Write a contract matrix before implementation. Cover equivalent forms, optional and unknown fields, malformed optional values, case variants, marker semantics, rename/copy/type changes, and bounded degradation that preserves unrelated facts.

## Proving subprocess integration only with mocks

**Failure mode:** A command works in unit tests but fails under the real caller because `PATH`, working directory, artifact contents, protocol revision, permissions, or import resolution differs.

**Why it happens:** Function tests are mistaken for installation and lifecycle tests. Editable environments accidentally supply executables and modules absent from clean installs.

**Correction:** Test built wheel and sdist artifacts in clean environments. Restrict `PATH`, add a hostile repository-local shadow package, verify private modes, use the exact protocol client when practical, and exercise the complete process lifecycle.

## Letting outcome branches drift

**Failure mode:** Normal and error reports include mandatory evidence or usage metadata, while a clean or skipped branch omits it.

**Why it happens:** Outcomes are assembled independently and tests assert prose rather than shared invariants.

**Correction:** Compose mandatory metadata once and apply it to every outcome. Test skipped, clean, warning, error, and finding states through one table, including zero-value omission and optional emoji behavior.
