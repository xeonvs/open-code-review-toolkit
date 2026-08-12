#!/bin/sh
set -eu

mode=${1:-check}
log_dir=${OCR_TOOLKIT_LOG_DIR:-.quality-logs}
mkdir -p "$log_dir"
log_file="$log_dir/${mode}.log"
quality_environment=${OCR_TOOLKIT_QUALITY_ENVIRONMENT:-$log_dir/venv}
export UV_PROJECT_ENVIRONMENT="$quality_environment"

# An interrupted editable install can leave dist-info without RECORD. uv then
# warns while trying an uninstall that cannot be complete. This environment is
# private to the quality wrapper, so rebuild only that disposable environment
# before uv attempts package synchronization.
for metadata in "$quality_environment"/lib/python*/site-packages/open_code_review_toolkit-*.dist-info; do
  [ -e "$metadata" ] || continue
  if [ ! -f "$metadata/RECORD" ]; then
    uv venv --clear "$quality_environment" >"$log_dir/environment-repair.log" 2>&1
    break
  fi
done

# Synchronize the disposable environment before `uv run`. Besides keeping the
# subsequent commands quiet, this prevents uv from inspecting or repairing the
# developer's active environment when the wrapper is launched from one.
environment_sync_log=$log_dir/environment-sync.log
if ! uv sync --locked --all-groups >"$environment_sync_log" 2>&1; then
  echo "quality environment sync failed; last 80 lines follow" >&2
  tail -n 80 "$environment_sync_log" >&2
  exit 1
fi

case "$mode" in
  format)
    set -- uv run --no-sync ruff format .
    ;;
  lint)
    set -- uv run --no-sync ruff check .
    ;;
  test)
    set -- uv run --no-sync pytest -q
    ;;
  coverage)
    set -- uv run --no-sync pytest -q --cov=ocr_toolkit --cov-report=term --cov-fail-under=70
    ;;
  types)
    set -- uv run --no-sync mypy src/ocr_toolkit
    ;;
  security)
    set -- uv run --no-sync bandit -r src/ocr_toolkit --severity-level medium --confidence-level medium
    ;;
  check)
    for command in "ruff format --check ." "ruff check ." "mypy src/ocr_toolkit" "bandit -r src/ocr_toolkit --severity-level medium --confidence-level medium" "pytest -q --cov=ocr_toolkit --cov-report=term --cov-fail-under=70"; do
      if ! uv run --no-sync sh -c "$command" >>"$log_file" 2>&1; then
        echo "quality check failed: $command" >&2
        tail -n 80 "$log_file" >&2
        exit 1
      fi
    done
    printf 'quality checks passed; full output: %s\n' "$log_file"
    exit 0
    ;;
  *)
    echo "usage: scripts/quality.sh [check|format|lint|test|coverage|types|security]" >&2
    exit 2
    ;;
esac

if "$@" >"$log_file" 2>&1; then
  printf '%s passed; full output: %s\n' "$mode" "$log_file"
else
  status=$?
  echo "$mode failed; last 80 lines follow" >&2
  tail -n 80 "$log_file" >&2
  exit "$status"
fi
