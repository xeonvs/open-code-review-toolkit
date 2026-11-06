"""Completion requires a whole bounded tail, never a discarded continuation."""

import pytest

from ocr_toolkit.common.value_boundaries import (
    MAX_TAIL_CHARS,
    complete_carrier,
    complete_field,
    complete_value,
)


@pytest.mark.parametrize("complete", (complete_value, complete_field))
@pytest.mark.parametrize("tail", (" /* unfinished", " <!-- unfinished", " " * MAX_TAIL_CHARS + "x"))
def test_incomplete_or_over_budget_trivia_is_not_value_completion(complete, tail):
    prefix = 'token=""'
    assert not complete(prefix + tail, len(prefix))


@pytest.mark.parametrize("tail", (" ", "\n\t", "\r\n"))
def test_literal_carrier_can_finish_after_complete_whitespace(tail):
    carrier = '"token=***"'
    assert complete_carrier(carrier + tail, len(carrier), start=0)


@pytest.mark.parametrize("separator", ("", ","))
def test_closed_data_proof_does_not_enlarge_the_lexical_tail_budget(separator):
    carrier = '"token=***"'
    value = "(" + carrier + separator + " " * (MAX_TAIL_CHARS + 1)
    value += "0)" if separator else ")"
    assert not complete_carrier(value, len(carrier) + 1, start=1)
