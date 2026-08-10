#!/bin/sh
# Read one GitHub REST response with an enforced byte and time boundary.
set -eu

endpoint=${1:?GitHub API endpoint is required}
output=${2:?output path is required}
authentication=${3:-authenticated}
expected_statuses=${4:-200}
max_bytes=${5:-1048576}
accept=${6:-application/vnd.github+json}

case "${endpoint}" in
  repos/*) ;;
  *) echo "unsupported GitHub API endpoint" >&2; exit 2 ;;
esac
case "${authentication}" in
  authenticated)
    set -- --header "Authorization: Bearer ${GH_TOKEN:?GH_TOKEN is required}"
    ;;
  anonymous)
    set --
    ;;
  *) echo "unsupported GitHub API authentication mode" >&2; exit 2 ;;
esac
case "${expected_statuses}" in
  *[!0-9,]*|'') echo "invalid expected GitHub API statuses" >&2; exit 2 ;;
esac
case "${max_bytes}" in
  *[!0-9]*|'') echo "invalid GitHub API byte limit" >&2; exit 2 ;;
esac
test "${max_bytes}" -gt 0 && test "${max_bytes}" -le 10485760 || {
  echo "GitHub API byte limit is outside the supported range" >&2
  exit 2
}
case "${accept}" in
  application/vnd.github+json|application/octet-stream) ;;
  *) echo "unsupported GitHub API media type" >&2; exit 2 ;;
esac

if ! http_status=$(curl --silent --show-error \
  --location --connect-timeout 10 --max-time 60 --max-filesize "${max_bytes}" \
  --proto '=https' --proto-redir '=https' \
  --header "Accept: ${accept}" \
  --header "X-GitHub-Api-Version: ${GITHUB_API_VERSION:-2022-11-28}" \
  "$@" --output "${output}" --write-out '%{http_code}' \
  "https://api.github.com/${endpoint}"); then
  echo "bounded GitHub API read failed: ${endpoint}" >&2
  exit 1
fi
case ",${expected_statuses}," in
  *,"${http_status}",*) ;;
  *) echo "unexpected GitHub API status ${http_status}: ${endpoint}" >&2; exit 1 ;;
esac
printf '%s\n' "${http_status}"
