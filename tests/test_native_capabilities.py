"""Runtime support alone cannot authorize an unqualified native handoff."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.diagrams.lifecycle import DiagramExecution
from ocr_toolkit.native_capabilities import supports_native_capability
from tests.diagrams.support import REVIEW_RANGE

QUALIFIED = ("1.13.3", "1.13.4", "1.13.5", "1.13.6", "1.13.7")


@pytest.mark.parametrize("version", QUALIFIED)
def test_exact_qualified_versions_enable_optional_diagram_collector(tmp_path, version):
    execution = DiagramExecution.prepare(
        "local",
        local=True,
        native_version=version,
        review_range=REVIEW_RANGE,
        path=tmp_path / "diagram.json",
    )
    assert execution.collector is not None
    assert execution.result.state == "not-generated"
    assert supports_native_capability(version, "gitlink_projection")


@pytest.mark.parametrize("version", [None, "1.13.2", "1.13.8", "1.14.0", "v1.13.7", "1.13.7 "])
def test_unqualified_diagram_version_is_optional_and_does_not_create_output(tmp_path, version):
    path = tmp_path / "diagram.json"
    execution = DiagramExecution.prepare(
        "local",
        local=True,
        native_version=version,
        review_range=REVIEW_RANGE,
        path=path,
    )
    assert execution.result.state == "unsupported"
    assert execution.collector is None
    assert not path.exists()
    assert not supports_native_capability(version, "gitlink_projection")


@given(
    st.one_of(
        st.text(max_size=80),
        st.sampled_from(QUALIFIED),
        st.sampled_from(
            [
                prefix + version + suffix
                for version in QUALIFIED
                for prefix, suffix in (("v", ""), ("", " "), ("", ".0"))
            ]
        ),
    ),
    st.sampled_from(["diagram_output", "gitlink_projection"]),
)
def test_qualification_never_follows_version_prefix_or_a_future_patch(version, capability):
    assert supports_native_capability(version, capability) == (version in QUALIFIED)
