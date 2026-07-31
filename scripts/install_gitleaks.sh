#!/bin/sh
set -eu

GITLEAKS_VERSION=8.24.3
GITLEAKS_LINUX_X64_SHA256=9991e0b2903da4c8f6122b5c3186448b927a5da4deef1fe45271c3793f4ee29c
readonly GITLEAKS_VERSION GITLEAKS_LINUX_X64_SHA256

case "$(uname -s):$(uname -m)" in
  Linux:x86_64)
    archive="gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz"
    expected_sha256=$GITLEAKS_LINUX_X64_SHA256
    ;;
  *)
    echo "unsupported Gitleaks installer platform; install version ${GITLEAKS_VERSION} manually" >&2
    exit 2
    ;;
esac

destination=${1:-}
if [ -z "$destination" ]; then
  echo "usage: scripts/install_gitleaks.sh <destination-directory>" >&2
  exit 2
fi

mkdir -p "$destination"
temporary_directory=$(mktemp -d "${TMPDIR:-/tmp}/ocr-gitleaks.XXXXXX")
trap 'rm -rf "$temporary_directory"' EXIT HUP INT TERM
url="https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/${archive}"
curl --fail --location --silent --show-error --proto '=https' --proto-redir '=https' \
  --output "$temporary_directory/$archive" "$url"
actual_sha256=$(sha256sum "$temporary_directory/$archive" | cut -d ' ' -f 1)
if [ "$actual_sha256" != "$expected_sha256" ]; then
  echo "Gitleaks archive checksum mismatch" >&2
  exit 1
fi
tar -xzf "$temporary_directory/$archive" -C "$temporary_directory" gitleaks
install -m 0755 "$temporary_directory/gitleaks" "$destination/gitleaks"
