#!/bin/sh
# Read one GitHub REST response with an enforced byte and time boundary.
set -eu
umask 077

endpoint=${1:?GitHub API endpoint is required}
output=${2:?output path is required}
authentication=${3:-authenticated}
expected_statuses=${4:-200}
max_bytes=${5:-1048576}
accept=${6:-application/vnd.github+json}

python3 - "${endpoint}" <<'PY'
import re
import sys

endpoint = sys.argv[1]
repository = r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"
patterns = (
    rf"repos/{repository}/pulls/[1-9][0-9]*",
    rf"repos/{repository}/commits/[0-9a-f]{{40}}",
    rf"repos/{repository}/commits/[0-9a-f]{{40}}/check-runs\?filter=latest&per_page=100",
    rf"repos/{repository}/contents/\.release-metadata\.json\?ref=[0-9a-f]{{40}}",
    rf"repos/{repository}/rules/branches/main",
    rf"repos/{repository}/issues/[1-9][0-9]*",
    rf"repos/{repository}/issues/[1-9][0-9]*/comments\?per_page=100&page=[1-5]",
    rf"repos/{repository}/issues/[1-9][0-9]*/comments\?per_page=1&page=501",
    rf"repos/{repository}/releases/tags/v[0-9]+(?:\.[0-9]+)+",
    rf"repos/{repository}/releases/assets/[1-9][0-9]*",
)
if not any(re.fullmatch(pattern, endpoint) for pattern in patterns):
    raise SystemExit("unsupported GitHub API endpoint")
PY
case "${authentication}" in
  authenticated)
    set -- --oauth2-bearer "${GH_TOKEN:?GH_TOKEN is required}"
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

output_directory=$(dirname -- "${output}")
temporary_output=$(mktemp "${output_directory}/.bounded-github-api.XXXXXX")
cleanup() {
  rm -f -- "${temporary_output}"
}
trap cleanup EXIT HUP INT TERM

if ! http_status=$(curl --silent --show-error \
  --location --connect-timeout 10 --max-time 60 --max-filesize "${max_bytes}" \
  --proto '=https' --proto-redir '=https' \
  --header "Accept: ${accept}" \
  --header "X-GitHub-Api-Version: ${GITHUB_API_VERSION:-2022-11-28}" \
  "$@" --output "${temporary_output}" --write-out '%{http_code}' \
  "https://api.github.com/${endpoint}"); then
  echo "bounded GitHub API read failed: ${endpoint}" >&2
  exit 1
fi
case ",${expected_statuses}," in
  *,"${http_status}",*) ;;
  *) echo "unexpected GitHub API status ${http_status}: ${endpoint}" >&2; exit 1 ;;
esac
mv -- "${temporary_output}" "${output}"
trap - EXIT HUP INT TERM
printf '%s\n' "${http_status}"
