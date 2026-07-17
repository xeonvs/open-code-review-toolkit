# Development

Install [uv](https://docs.astral.sh/uv/) and use the committed lockfile:

```console
uv sync --frozen
uv run ruff format --check .
uv run ruff check .
uv run mypy src/ocr_toolkit
uv run pytest --cov=ocr_toolkit --cov-report=term-missing --cov-fail-under=70
uv run python -m build
uv run twine check dist/*
```

For routine agent and contributor checks, prefer `scripts/quality.sh check`. It captures successful output under ignored `.quality-logs/` and prints only a short status; on failure it prints the last 80 lines. Individual modes are `format`, `lint`, `test`, `coverage`, and `types`.

Runtime code must remain compatible with Python 3.10-3.13 and standard-library-only. Tests and examples must use synthetic data. User-visible changes require a fragment in `changelog.d/`.

For artifact smoke tests, install the wheel and sdist into separate temporary virtual environments and run `ocr-ci --help`. Generic secret scanning uses Gitleaks; dependency auditing uses `pip-audit`.
