"""Bounded immutable-range properties independent of coverage or outcome prose."""

from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.result_contract import OcrResultContractError
from ocr_toolkit.review_range import ReviewRange, admit_native_range
from tests.test_review_range import native_result

SHA = st.text(alphabet="0123456789abcdef", min_size=40, max_size=40)


@given(SHA, SHA)
def test_only_exact_native_endpoints_prove_the_expected_range(base: str, head: str) -> None:
    expected = ReviewRange(base, head)
    result = native_result(expected)
    assert admit_native_range(result, expected) == expected
    # Mutate one endpoint without depending on random inequality or file counts.
    wrong_base = ("0" if base[0] != "0" else "1") + base[1:]
    result["manifest"]["input"]["resolved_base"] = wrong_base
    try:
        admit_native_range(result, expected)
    except OcrResultContractError:
        pass
    else:
        raise AssertionError("different immutable base was accepted")
