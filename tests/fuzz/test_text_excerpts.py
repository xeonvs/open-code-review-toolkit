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


@given(
    st.lists(st.text(alphabet="abé\U0001f600\r\u2028", max_size=16), max_size=12),
    st.booleans(),
    st.lists(st.tuples(st.integers(1, 16), st.integers(1, 16)), max_size=12),
    st.integers(0, 160),
    st.integers(1, 19),
)
def test_overlapping_requests_have_chunk_and_order_independent_budget_results(
    lines, final_lf, requests, budget, chunk
):
    source = "\n".join(lines) + ("\n" if final_lf else "")
    spans = tuple((min(start, end), max(start, end)) for start, end in requests)
    count = source.count("\n") + int(bool(source) and not source.endswith("\n"))
    whole = TextExcerptCapture(spans, max_bytes=budget, max_source_chars=0)
    whole.feed(source, 1)
    expected = whole.finish(count)
    streamed = TextExcerptCapture(
        tuple(reversed(spans)) + spans, max_bytes=budget, max_source_chars=0
    )
    decoder = codecs.getincrementaldecoder("utf-8")("strict")
    data = source.encode()
    seen = 0
    for offset in range(0, len(data), chunk):
        part = data[offset : offset + chunk]
        streamed.feed(decoder.decode(part), seen + 1)
        seen += part.count(b"\n")
        assert 0 <= streamed.used_bytes <= budget
    decoder.decode(b"", final=True)
    assert streamed.finish(count) == expected
    assert streamed.used_bytes == whole.used_bytes <= budget
    # Also require positive results whenever all requested material fits. This
    # prevents an implementation that omits every request from passing symmetry.
    lf_lines = source.split("\n")
    required = sum(len("\n".join(lf_lines[start - 1 : end]).encode()) for start, end in set(spans))
    if required <= budget:
        for item in expected:
            assert item.reason == ("range" if item.end_line > count else "none")
            if item.reason == "none":
                assert item.text == "\n".join(lf_lines[item.start_line - 1 : item.end_line])
