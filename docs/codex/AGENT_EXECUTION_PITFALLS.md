# Agent Execution Pitfalls

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
