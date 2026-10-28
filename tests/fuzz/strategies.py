"""Bounded JSON variation shared by hostile boundary properties."""

from hypothesis import strategies as st


def json_values() -> st.SearchStrategy[object]:
    """Vary JSON types, Unicode and nested combinations within two levels."""

    scalar = st.one_of(
        st.none(),
        st.booleans(),
        st.integers(-(2**128), 2**128),
        st.floats(allow_nan=False, allow_infinity=False, width=32),
        st.text(max_size=40),
        st.sampled_from(("\x00", "\u202e", "\ud800")),
    )
    value: st.SearchStrategy[object] = scalar
    for _depth in range(2):
        value = st.one_of(
            scalar,
            st.lists(value, max_size=4),
            st.dictionaries(st.text(max_size=12), value, max_size=4),
        )
    return value
