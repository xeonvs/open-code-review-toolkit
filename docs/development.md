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
