"""The optimized candidate search must preserve Python's complete Unicode semantics."""

from ocr_toolkit.context.dlp.presentation import canonical_whitespace, is_display_control


def test_canonical_whitespace_matches_reference_for_every_unicode_codepoint():
    for start in range(0, 0x110000, 0x4000):
        text = "".join(chr(point) for point in range(start, min(start + 0x4000, 0x110000)))
        expected = "".join(" " if c.isspace() else "" if is_display_control(c) else c for c in text)
        assert canonical_whitespace(text) == expected
