#!/bin/sh
set -eu

mode=${1:-check}
log_dir=${OCR_TOOLKIT_LOG_DIR:-.quality-logs}
mkdir -p "$log_dir"
log_file="$log_dir/${mode}.log"
quality_environment=${OCR_TOOLKIT_QUALITY_ENVIRONMENT:-$log_dir/venv}
export UV_PROJECT_ENVIRONMENT=$quality_environment

case "$mode" in
  format)
    set -- uv run ruff format .
    ;;
  lint)
    set -- uv run ruff check .
    ;;
  test)
    set -- uv run pytest -q
    ;;
  coverage)
    set -- uv run pytest -q --cov=ocr_toolkit --cov-report=term --cov-fail-under=70
    ;;
  types)
    set -- uv run mypy src/ocr_toolkit
    ;;
  check)
    : >"$log_file"
    for command in "ruff format --check ." "ruff check ." "mypy src/ocr_toolkit" "pytest -q --cov=ocr_toolkit --cov-report=term --cov-fail-under=70"; do
      if ! uv run sh -c "$command" >>"$log_file" 2>&1; then
        echo "quality check failed: $command" >&2
        tail -n 80 "$log_file" >&2
        exit 1
      fi
    done
    printf 'quality checks passed; full output: %s\n' "$log_file"
    exit 0
    ;;
  *)
    echo "usage: scripts/quality.sh [check|format|lint|test|coverage|types]" >&2
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
