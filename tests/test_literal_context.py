"""Literal-data proof bounds and unknown-syntax negative controls."""

import pytest

from ocr_toolkit.common.literal_context import LiteralContext


@pytest.mark.parametrize(
    "value, allowed",
    (
        ('"one"', True),
        ('call("one")', False),
        ('value = "one"', True),
        ('value: "one"', True),
        ('value = "one"; other = -2', True),
        ('value = "one"; other = unknown', False),
        ('"one" # material', False),
        ('\n\n+"one"', False),
        ('["one", "two"]', True),
        ('{"value": "one", "n": -2}', True),
        ('call("one", "two")', False),
        ('["one", "two"][0]', False),
        ('f"one" + "two"', False),
        ('["one", "two", unknown]', False),
        ('["one", "two"', False),
        ('["one", "two", "unterminated]', False),
        ('["one", "two", """triple"""]', False),
        ('["one", "two", "escaped\\"quote"]', True),
    ),
)
def test_context_proof_is_cached_and_closed(value, allowed):
    start = value.index('"one"')
    context = LiteralContext(value)
    for _ in range(2):
        assert context.proves_carrier(start, start + 5) is allowed
    assert not context.proves_carrier(start + 1, start + 5)


@pytest.mark.parametrize(
    "value",
    (
        '"one"' + " " * 2_000_000,
        '"one",' + '"",' * 32_769,
        '["one", "two", ' + "(" * 21 + "0" + ")" * 21 + "]",
        '["one", "two", "' + "." * 32_768 + '"]',
        '["one", "' + ")" * 25 + '", ' + "[" * 21 + "0" + "]" * 21 + "]",
    ),
)
def test_context_allocation_budgets(value):
    assert not LiteralContext(value).proves_carrier(value.index('"'), value.index('"') + 5)


def test_scalar_record_inventory_is_bounded():
    value = '"one"\n' + "1\n" * 32_769
    assert not LiteralContext(value).proves_carrier(0, 5)


@pytest.mark.parametrize("digits, admitted", ((4096, True), (4097, False)))
def test_data_parser_bounds_decimal_conversion_before_allocation(digits, admitted):
    value = '["one", "two", ' + "1" * digits + "]"
    assert LiteralContext(value).proves_carrier(1, 6) is admitted
