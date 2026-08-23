#!/bin/sh
set -eu

mode=${1:-check}
log_dir=${OCR_TOOLKIT_LOG_DIR:-.quality-logs}
mkdir -p "$log_dir"
log_file="$log_dir/${mode}.log"
quality_environment=${OCR_TOOLKIT_QUALITY_ENVIRONMENT:-$log_dir/venv}
export UV_PROJECT_ENVIRONMENT="$quality_environment"

run_logged_command() {
  quality_command=$1
  if ! uv run --no-sync sh -c "$quality_command" >>"$log_file" 2>&1; then
    echo "quality check failed: $quality_command" >&2
    tail -n 80 "$log_file" >&2
    exit 1
  fi
}

run_coverage_gate() {
  run_logged_command "pytest -q --cov=ocr_toolkit --cov-report=term --cov-fail-under=85"
  run_logged_command "coverage report --include=src/ocr_toolkit/ocr_result.py,src/ocr_toolkit/preflight.py --fail-under=80"
  run_logged_command "coverage report --include=src/ocr_toolkit/posting/workflow.py,src/ocr_toolkit/posting/gitlab.py,src/ocr_toolkit/posting/snapshot.py,src/ocr_toolkit/posting/gitlab_approval.py --fail-under=80"
  run_logged_command "coverage report --include=src/ocr_toolkit/review_runner.py,src/ocr_toolkit/context/broker.py,src/ocr_toolkit/context/store.py,src/ocr_toolkit/context/dlp.py,src/ocr_toolkit/posting/approval.py --fail-under=85"
  run_logged_command "coverage report --include=src/ocr_toolkit/mcp_config.py,src/ocr_toolkit/providers/gitlab.py,src/ocr_toolkit/providers/gitlab_context.py,src/ocr_toolkit/providers/gitlab_discussions.py,src/ocr_toolkit/providers/gitlab_remediation.py,src/ocr_toolkit/context/policy.py,src/ocr_toolkit/result_contract.py --fail-under=85"
}

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
    run_coverage_gate
    printf '%s passed; full output: %s\n' "$mode" "$log_file"
    exit 0
    ;;
  types)
    set -- uv run --no-sync mypy src/ocr_toolkit
    ;;
  security)
    set -- uv run --no-sync bandit -r src/ocr_toolkit --severity-level medium --confidence-level medium
    ;;
  check)
    for command in "ruff format --check ." "ruff check ." "mypy src/ocr_toolkit" "bandit -r src/ocr_toolkit --severity-level medium --confidence-level medium"; do
      run_logged_command "$command"
    done
    run_coverage_gate
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
