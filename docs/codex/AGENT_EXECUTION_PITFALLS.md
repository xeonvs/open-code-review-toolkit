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

## Source And Privacy Boundaries

- Inventory tracked source explicitly and avoid broad copy commands that could include ignored or untracked files.
- Do not turn one-time private marker criteria into a tracked denylist or test fixture.
- Do not use real provider payloads, hosts, repositories, or credentials in public fixtures.

## Tooling And Validation Hygiene

- Prefer the narrowest reproducer before broad reruns.
- Verify both UTF-8 byte limits and Python character limits when changing note formatting.
- Treat tests, lint, typing, artifact checks, install smoke, privacy scans, and source-integrity checks as distinct gates.
- Pin third-party Actions by full commit SHA and keep readable version comments beside the pin.

## Learning Loop

- Promote a repeated stable lesson into `docs/engineering/project_principles.md`.
- Record actionable future work in `docs/codex/TASKS_BACKLOG.md` only when it has an activation trigger and next safe action.
