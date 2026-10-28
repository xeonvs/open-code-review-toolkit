"""Distribution metadata cannot widen reviewed version/hash/host identities."""

from copy import deepcopy
from urllib.parse import urlsplit

from hypothesis import given
from hypothesis import strategies as st

from tests.fuzz.strategies import json_values
from tests.test_testpypi_preview import expected_hashes, payload, preview

VERSION = "0.1.0a3"
HASHES = expected_hashes(VERSION)


@given(json_values())
def test_registry_root_shapes_have_a_closed_parser_error(value) -> None:
    for parse in (preview.classify_index, preview.artifact_manifest):
        try:
            parsed = parse(value, VERSION, HASHES)
        except preview.PreviewError:
            continue
        assert (
            parsed in ("publish", "already-published")
            if isinstance(parsed, str)
            else len(parsed) == 2
        )


@given(
    st.sampled_from(("filename", "hashes", "url", "provenance")), json_values(), st.integers(0, 1)
)
def test_file_metadata_mutations_never_bypass_hash_and_url_validation(field, value, index) -> None:
    document = payload(HASHES)
    document["files"][index][field] = value
    try:
        admitted = preview.artifact_manifest(document, VERSION, HASHES)
    except preview.PreviewError:
        return
    assert {entry["filename"]: entry["sha256"] for entry in admitted} == HASHES
    assert all(urlsplit(entry["url"]).hostname == preview.ARTIFACT_HOST for entry in admitted)


@given(
    st.booleans(), st.sampled_from(("normal", "missing", "duplicate", "wrong-hash", "foreign-host"))
)
def test_registry_order_and_conflicting_sets_obey_idempotent_recovery(reverse, change) -> None:
    document = payload(HASHES)
    if reverse:
        document["files"].reverse()
    if change == "missing":
        document["files"].pop()
    elif change == "duplicate":
        document["files"].append(deepcopy(document["files"][0]))
    elif change == "wrong-hash":
        document["files"][0]["hashes"]["sha256"] = "c" * 64
    elif change == "foreign-host":
        document["files"][0]["url"] = document["files"][0]["url"].replace(
            "test-files.pythonhosted.org", "foreign.invalid"
        )
    try:
        admitted = preview.artifact_manifest(document, VERSION, HASHES)
    except preview.PreviewError:
        assert change != "normal"
    else:
        assert change == "normal" and len(admitted) == 2
        assert preview.classify_index(document, VERSION, HASHES) == "already-published"


@given(
    st.sampled_from(("url", "provenance")),
    st.sampled_from(("https", "HTTPS", "http")),
    st.sampled_from(
        ("normal", "uppercase", "foreign", "suffix", "userinfo", "port", "fragment", "control")
    ),
)
def test_structured_registry_urls_preserve_exact_origin_for_download_and_provenance(
    field, scheme, change
):
    document = payload(HASHES)
    original = urlsplit(document["files"][0][field])
    host = original.netloc
    if change == "uppercase":
        host = host.upper()
    elif change == "foreign":
        host = "foreign.invalid"
    elif change == "suffix":
        host += ".foreign.invalid"
    elif change == "userinfo":
        host = "synthetic@" + host
    elif change == "port":
        host += ":444"
    url = f"{scheme}://{host}{original.path}"
    if change == "fragment":
        url += "#fragment"
    elif change == "control":
        url += "\t"
    document["files"][0][field] = url
    safe = scheme.lower() == "https" and change in ("normal", "uppercase")
    try:
        admitted = preview.artifact_manifest(document, VERSION, HASHES)
    except preview.PreviewError:
        assert not safe
    else:
        assert safe and {item["filename"]: item["sha256"] for item in admitted} == HASHES


@given(st.data(), json_values(), st.sampled_from(("0.11.1", "0.11.0", "0.14.0")))
def test_legacy_registry_recovery_remains_scoped_to_its_exact_historical_release(
    data, value, version
):
    historical = "0.11.1"
    hashes = expected_hashes(historical)
    document = {
        "info": {"name": preview.PACKAGE, "version": historical},
        "urls": [
            {
                "filename": filename,
                "packagetype": "bdist_wheel" if kind == "wheel" else "sdist",
                "digests": {"sha256": hashes[filename]},
                "url": f"https://files.pythonhosted.org/packages/synthetic/{filename}",
                "yanked": False,
            }
            for filename, kind in preview.expected_filenames(historical).items()
        ],
    }
    paths = (
        ("info",),
        ("info", "name"),
        ("info", "version"),
        ("urls",),
        *(("urls", 0, field) for field in ("filename", "packagetype", "digests", "url", "yanked")),
    )
    path = data.draw(st.sampled_from(paths))
    parent = document
    for part in path[:-1]:
        parent = parent[part]
    parent[path[-1]] = value
    try:
        admitted = preview.pypi_release_json_manifest(document, version, expected_hashes(version))
    except preview.PreviewError:
        return
    assert version == historical
    assert {item["filename"]: item["sha256"] for item in admitted} == hashes
