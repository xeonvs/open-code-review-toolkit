"""Hostile current receipt fields fail atomically through persisted result readback."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.ocr_result import OcrResultMalformed, load_ocr_result
from ocr_toolkit.review_receipt import toolkit_receipt_is_valid
from tests.diagrams.test_persistence import persisted_result
from tests.fuzz.strategies import json_values
from tests.test_review_receipt_v13 import RECEIPT_ENUM_PATHS, generated_diagram


@given(st.data(), json_values())
def test_nested_receipt_fields_never_escape_closed_atomic_readback(data, value):
    document = persisted_result(generated_diagram())
    metadata = document["_ocr_toolkit"]
    path = data.draw(
        st.sampled_from(
            (
                *RECEIPT_ENUM_PATHS,
                ("publication", "state"),
                ("range", "state"),
                *(
                    ("diagram", field)
                    for field in ("mode", "state", "reason", "calls", "failed_calls")
                ),
                *(
                    ("review", field)
                    for field in ("target_protection", "policy_protection", "protection_mode")
                ),
            )
        )
    )
    parent = metadata
    for part in path[:-1]:
        parent = parent[part]
    parent[path[-1]] = value
    valid = toolkit_receipt_is_valid(metadata)
    with TemporaryDirectory(prefix="ocr-receipt-readback-") as directory:
        target = Path(directory) / "result.json"
        target.write_text(json.dumps(document, ensure_ascii=True))
        try:
            loaded = load_ocr_result(target)
        except OcrResultMalformed:
            return
        assert valid and loaded["_ocr_toolkit"] == metadata
