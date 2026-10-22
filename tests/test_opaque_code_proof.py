"""Exact reviewed-source proof for optional opaque code publication."""

from __future__ import annotations

import unittest
from typing import Any

from ocr_toolkit.evidence.opaque_code import OpaqueCodeProof, prove_opaque_code

SOURCE = (
    "header\r\n"
    "type Entry = List<Entry>\r\n"
    "pattern: (?P<entry>[a-z]+)\r\n"
    "  markup: <Entry active={true} />\r\n"
    "footer\r\n"
)


def proof(**overrides: Any) -> OpaqueCodeProof:
    comment: dict[str, Any] = {
        "start_line": 2,
        "end_line": 4,
        "existing_code": (
            "type Entry = List<Entry>\n"
            "pattern: (?P<entry>[a-z]+)\n"
            "  markup: <Entry active={true} />"
        ),
        "suggestion_code": (
            "type Entry = List<Entry>\n"
            "pattern: (?P<entry>[a-z]+)\n"
            "  markup: <Entry active={false} />"
        ),
    }
    comment.update(overrides)
    return prove_opaque_code(comment, "config/example.yml", lambda _path: SOURCE)


class OpaqueCodeProofTests(unittest.TestCase):
    def test_exact_contiguous_generic_regex_yaml_jsx_and_indentation(self) -> None:
        self.assertEqual(proof(), OpaqueCodeProof(True, True))

    def test_original_without_replacement_has_its_own_proof(self) -> None:
        self.assertEqual(proof(suggestion_code=None), OpaqueCodeProof(True, False))

    def test_source_mismatch_and_noncontiguous_range_fail_closed(self) -> None:
        self.assertEqual(proof(existing_code="type Entry = List<Entry>"), OpaqueCodeProof())
        self.assertEqual(proof(start_line=2, end_line=3), OpaqueCodeProof())
        self.assertEqual(proof(start_line=4, end_line=2), OpaqueCodeProof())

    def test_missing_source_and_reader_error_fail_closed(self) -> None:
        comment = {"line": 2, "existing_code": "type Entry = List<Entry>"}
        self.assertEqual(
            prove_opaque_code(comment, "config/example.yml", lambda _path: None),
            OpaqueCodeProof(),
        )

        def failed_read(_path: str) -> str:
            raise OSError("private path and content must not escape")

        self.assertEqual(
            prove_opaque_code(comment, "config/example.yml", failed_read), OpaqueCodeProof()
        )

    def test_invalid_path_is_rejected_before_read(self) -> None:
        calls: list[str] = []

        def read(path: str) -> str:
            calls.append(path)
            return SOURCE

        comment = {"line": 2, "existing_code": "type Entry = List<Entry>"}
        self.assertEqual(prove_opaque_code(comment, "../secret", read), OpaqueCodeProof())
        self.assertEqual(calls, [])

    def test_noncontiguous_or_malformed_suggestion_does_not_gain_proof(self) -> None:
        self.assertEqual(proof(suggestion_code="...\n<unsafe>"), OpaqueCodeProof(True, False))
        self.assertEqual(
            proof(suggestion_code="```suggestion\n<unsafe>\n```"),
            OpaqueCodeProof(True, False),
        )
        self.assertEqual(proof(suggestion_code="/approve"), OpaqueCodeProof(True, False))

    def test_bounded_work_and_bad_model_types_fail_closed(self) -> None:
        self.assertEqual(proof(existing_code="x" * 12_001), OpaqueCodeProof())
        self.assertEqual(proof(suggestion_code="x" * 12_001), OpaqueCodeProof(True, False))
        self.assertEqual(proof(suggestion_code=["<Entry />"]), OpaqueCodeProof(True, False))
        self.assertEqual(proof(start_line="9" * 5_000), OpaqueCodeProof())
        self.assertEqual(proof(existing_code=["type Entry = List<Entry>"]), OpaqueCodeProof())
        comment = {"line": 1, "existing_code": "x"}
        self.assertEqual(
            prove_opaque_code(comment, "x.py", lambda _path: "x" * 256_001),
            OpaqueCodeProof(),
        )

    def test_no_op_replacement_is_source_proven_without_authored_fences(self) -> None:
        existing = "type Entry = List<Entry>"
        comment = {"line": 2, "existing_code": existing, "suggestion_code": existing}
        self.assertEqual(
            prove_opaque_code(comment, "config/example.yml", lambda _path: SOURCE),
            OpaqueCodeProof(True, True),
        )


if __name__ == "__main__":
    unittest.main()
