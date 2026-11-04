"""Independent full-text oracle for arbitrary UTF-8 and LF chunk boundaries."""

import codecs

from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.evidence.text_excerpts import TextExcerptCapture


@given(
    st.lists(st.text(alphabet="abé\U0001f600\r\u2028", max_size=30), max_size=20),
    st.booleans(),
    st.integers(1, 24),
    st.integers(1, 10),
    st.integers(1, 17),
    st.integers(0, 100),
)
def test_excerpt_retention_matches_lf_oracle_across_split_utf8(
    lines, final_lf, start, span, chunk, limit
):
    source = "\n".join(lines) + ("\n" if final_lf else "")
    data = source.encode()
    capture = TextExcerptCapture(((start, start + span),), max_bytes=32_000, max_source_chars=limit)
    decoder = codecs.getincrementaldecoder("utf-8")("strict")
    seen = 0
    for offset in range(0, len(data), chunk):
        part = data[offset : offset + chunk]
        capture.feed(decoder.decode(part), seen + 1)
        seen += part.count(b"\n")
    decoder.decode(b"", final=True)
    total = source.count("\n") + int(bool(source) and not source.endswith("\n"))
    (excerpt,) = capture.finish(total)
    if start + span > total:
        assert excerpt.text is None and excerpt.reason == "range"
    else:
        assert excerpt.text == "\n".join(source.split("\n")[start - 1 : start + span])
        assert excerpt.reason == "none"
    assert capture.source == (source if limit and len(source) <= limit else None)
