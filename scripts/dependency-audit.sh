#!/bin/sh
set -eu

# Audit the same locked, installed dependency set locally and in security CI.
# Keep this environment separate from the caller's active project environment.
repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repository_root"
mkdir -p .quality-logs
UV_PROJECT_ENVIRONMENT=.quality-logs/dependency-audit-venv
export UV_PROJECT_ENVIRONMENT

UV_VERSION=0.13.4
installed_uv_version=$(uv --version 2>/dev/null || true)
case "$installed_uv_version" in
  "uv $UV_VERSION"|"uv $UV_VERSION "*) use_uvx=0 ;;
  *)
    if ! command -v uvx >/dev/null 2>&1; then
      echo "uv $UV_VERSION or uvx is required for dependency audit" >&2
      exit 2
    fi
    use_uvx=1
    ;;
esac

run_uv() {
  if [ "$use_uvx" -eq 1 ]; then
    uvx --from "uv==$UV_VERSION" uv "$@"
  else
    uv "$@"
  fi
}

run_uv sync --locked
run_uv run --no-sync pip-audit
