#!/bin/sh
set -eu

registry=${1:?registry is required}
version=${2:?version is required}
hashes=${3:?hash file is required}
workflow=${4:?expected publisher workflow is required}

case "${workflow}" in
  testpypi.yml|release.yml) ;;
  *) echo "unsupported publisher workflow: ${workflow}" >&2; exit 2 ;;
esac

case "${registry}" in
  testpypi)
    index_url=https://test.pypi.org/simple/open-code-review-toolkit/
    artifact_host=test-files.pythonhosted.org
    ;;
  pypi)
    index_url=https://pypi.org/simple/open-code-review-toolkit/
    artifact_host=files.pythonhosted.org
    ;;
  *)
    echo "unsupported registry: ${registry}" >&2
    exit 2
    ;;
esac

index=/tmp/${registry}-index.json
manifest=/tmp/${registry}-artifact-manifest.json
downloads=/tmp/${registry}-artifact-downloads.tsv
provenance_downloads=/tmp/${registry}-provenance-downloads.tsv
destination=/tmp/${registry}-artifacts-${version}
wheel_environment=/tmp/${registry}-wheel-${version}
sdist_environment=/tmp/${registry}-sdist-${version}

for attempt in 1 2 3 4 5; do
  if curl --fail --location --silent --show-error \
    --retry 3 --retry-delay 2 --retry-connrefused \
    --connect-timeout 10 --max-time 120 \
    --max-filesize 10485760 \
    --proto '=https' --proto-redir '=https' \
    --header 'Accept: application/vnd.pypi.simple.v1+json' \
    "${index_url}" --output "${index}"; then
    if python scripts/testpypi_preview.py artifact-manifest \
      --version "${version}" \
      --index-json "${index}" \
      --hashes-json "${hashes}" \
      --artifact-host "${artifact_host}" \
      > "${manifest}"; then
      break
    fi
  fi
  test "${attempt}" -lt 5 || exit 1
  sleep 15
done

python scripts/testpypi_preview.py artifact-manifest \
  --version "${version}" \
  --index-json "${index}" \
  --hashes-json "${hashes}" \
  --artifact-host "${artifact_host}" \
  > "${manifest}"
python - "${destination}" "${wheel_environment}" "${sdist_environment}" <<'PY'
import shutil
import sys
from pathlib import Path

for raw_path in sys.argv[1:]:
    path = Path(raw_path)
    if path.parent != Path("/tmp") or not path.name.startswith(("testpypi-", "pypi-")):
        raise SystemExit(f"refusing to reset unexpected verification path: {path}")
    shutil.rmtree(path, ignore_errors=True)
PY
python - "${manifest}" <<'PY' > "${downloads}"
import json
import sys
from pathlib import Path

for item in json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")):
    print(item["sha256"], item["url"], item["filename"], sep="\t")
PY
python - "${manifest}" <<'PY' > "${provenance_downloads}"
import json
import sys
from pathlib import Path

for item in json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")):
    print(item["provenance"], item["filename"], sep="\t")
PY

mkdir -p "${destination}"
tab=$(printf '\t')
while IFS="${tab}" read -r sha256 url filename; do
  curl --fail --location --silent --show-error \
    --retry 3 --retry-delay 2 --retry-connrefused \
    --connect-timeout 10 --max-time 120 \
    --max-filesize 10485760 \
    --proto '=https' --proto-redir '=https' \
    "${url}" --output "${destination}/${filename}"
  echo "${sha256}  ${destination}/${filename}" | sha256sum --check --strict
done < "${downloads}"

case "${registry}" in
  testpypi) provenance_environment=testpypi-public-disclosure ;;
  pypi) provenance_environment=pypi-production ;;
esac
while IFS="${tab}" read -r provenance_url filename; do
  provenance_file="${destination}/${filename}.provenance.json"
  curl --fail --location --silent --show-error \
    --retry 3 --retry-delay 2 --retry-connrefused \
    --connect-timeout 10 --max-time 120 \
    --max-filesize 1048576 \
    --proto '=https' --proto-redir '=https' \
    --header 'Accept: application/vnd.pypi.integrity.v1+json' \
    "${provenance_url}" --output "${provenance_file}"
  python scripts/verify_registry_provenance.py \
    --payload "${provenance_file}" \
    --hashes "${hashes}" \
    --filename "${filename}" \
    --environment "${provenance_environment}" \
    --repository "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}" \
    --workflow "${workflow}"
done < "${provenance_downloads}"

python -m venv "${wheel_environment}"
"${wheel_environment}/bin/pip" install --no-deps "${destination}"/*.whl
"${wheel_environment}/bin/ocr-ci" --help
python -m venv "${sdist_environment}"
python scripts/install_local_artifact.py \
  --python "${sdist_environment}/bin/python" \
  --artifact "$(find "${destination}" -maxdepth 1 -name '*.tar.gz' -print -quit)" \
  --requirements "/tmp/${registry}-sdist-${version}-requirements.txt"
"${sdist_environment}/bin/ocr-ci" --help
