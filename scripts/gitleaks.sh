#!/bin/sh
set -eu

GITLEAKS_VERSION=8.24.3
readonly GITLEAKS_VERSION

usage() {
  echo "usage: scripts/gitleaks.sh [<base-ref> [<head-ref>]]" >&2
  exit 2
}

[ "$#" -le 2 ] || usage

repository_root=$(git rev-parse --show-toplevel)
head_ref=${2:-HEAD}

if [ "$#" -ge 1 ]; then
  base_ref=$1
else
  base_ref=
  for candidate in origin/main main; do
    if git rev-parse --verify --quiet "${candidate}^{commit}" >/dev/null; then
      base_ref=$candidate
      break
    fi
  done
  if [ -z "$base_ref" ]; then
    echo "gitleaks base ref not found; fetch origin/main or pass an explicit base ref" >&2
    exit 2
  fi
fi

base_commit=$(git rev-parse --verify "${base_ref}^{commit}")
head_commit=$(git rev-parse --verify "${head_ref}^{commit}")

if ! git merge-base --is-ancestor "$base_commit" "$head_commit"; then
  echo "gitleaks base ref must be an ancestor of the head ref" >&2
  exit 2
fi

if ! command -v gitleaks >/dev/null 2>&1; then
  echo "gitleaks ${GITLEAKS_VERSION} is required; install it before validation" >&2
  exit 2
fi

installed_version=$(gitleaks version | sed -n '1s/^[vV]ersion: *//; s/^v//; p')
if [ "$installed_version" != "$GITLEAKS_VERSION" ]; then
  echo "gitleaks ${GITLEAKS_VERSION} is required; found ${installed_version:-unknown}" >&2
  exit 2
fi

# Match the pinned GitHub Action's pull-request scan: first-parent, no-merge
# patches beginning with the first feature commit. The Action receives that
# first commit as baseRef and expands it to baseRef^..headRef.
first_commit=$(git rev-list --first-parent --no-merges --reverse "${base_commit}..${head_commit}" | sed -n '1p')
if [ -n "$first_commit" ]; then
  log_opts="--no-merges --first-parent ${first_commit}^..${head_commit}"
else
  log_opts="--no-merges --first-parent -1 ${head_commit}"
fi

cd "$repository_root"
exec gitleaks detect --redact --exit-code=1 --log-level=warn --log-opts="$log_opts"
