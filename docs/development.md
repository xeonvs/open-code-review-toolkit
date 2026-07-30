# Development

Install [uv](https://docs.astral.sh/uv/) and use the committed lockfile:

```console
uv sync --frozen
uv run ruff format --check .
uv run ruff check .
uv run mypy src/ocr_toolkit
uv run bandit -r src/ocr_toolkit --severity-level medium --confidence-level medium
uv run pytest --cov=ocr_toolkit --cov-report=term-missing --cov-fail-under=70
uv run python -m build
uv run twine check dist/*
```

For routine agent and contributor checks, prefer `scripts/quality.sh check`. It captures successful output under ignored `.quality-logs/` and prints only a short status; on failure it prints the last 80 lines. Individual modes are `format`, `lint`, `test`, `coverage`, `types`, and `security`. The Bandit gate scans only the supported runtime package at medium-or-higher severity and confidence; tests and synthetic fixtures are intentionally outside that bounded gate.

Runtime code must remain compatible with Python 3.12-3.14 and standard-library-only. Tests and examples must use synthetic data. User-visible changes require a fragment in `changelog.d/`.
Repository-only qualification tools and evidence live under `scripts/` and `compatibility/`; they are excluded from both published distributions. Validate the manifest with `PYTHONPATH=src python scripts/ocr_compat.py validate`.

For artifact smoke tests, install the wheel and sdist into separate temporary virtual environments and run `ocr-ci --help`. Generic secret scanning uses Gitleaks; dependency auditing uses `pip-audit`.

## Boundary-focused test checklist

Before closing a parser, repository reader, persisted schema, subprocess, or report-rendering change, add the applicable boundary tests:

- exercise byte limits with multibyte input and prove reading or writing stops at the boundary instead of checking only after full capture;
- reload persisted artifacts as hostile input and verify schema, size, redaction, control-character, and cross-reference invariants again;
- vary valid parser syntax, including key order, indentation, scalar versus mapping forms, optional fields, markers, URLs, digests, and Git status letters;
- clear Git repository/object-store controls and replacement refs in subprocess tests, then verify immutable refs remain bound to the validated work tree;
- run installed wheel and sdist entrypoints with a restricted environment and a repository-local shadow package; and
- assert mandatory fields for skipped, clean, warning, error, and finding summaries through one shared outcome matrix.

Performance evidence must separate cold-start validation from steady-state requests. Profile realistic bounded stores and report wall time plus dominant cumulative functions; optimize the measured bottleneck.
