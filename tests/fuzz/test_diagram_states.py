"""Model run-wide output transitions independently of the collector implementation."""

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.diagrams.collector import DiagramCollector
from ocr_toolkit.diagrams.contracts import (
    MAX_SUBMISSION_BYTES,
    MAX_SUBMISSIONS,
    bounded_json,
    parse_submission,
)
from tests.diagrams.support import REVIEW_RANGE, flow_submission


@given(
    st.lists(
        st.sampled_from(("first", "equivalent", "other", "absent", "invalid", "large")), max_size=12
    )
)
def test_submission_sequences_obey_sticky_omission_and_cumulative_budgets(
    actions: list[str],
) -> None:
    first = flow_submission()
    first["diagram"]["nodes"][0]["label"] = "Café"
    equivalent = deepcopy(first)
    equivalent["diagram"]["nodes"].reverse()
    equivalent["diagram"]["nodes"][1]["label"] = "  Cafe\u0301  "
    other = deepcopy(first)
    other["diagram"]["edges"][0]["condition"] = "a different route"
    absent = {
        "state": "not-applicable",
        "base_sha": REVIEW_RANGE.base,
        "head_sha": REVIEW_RANGE.head,
    }
    candidates = {"first": first, "equivalent": equivalent, "other": other, "absent": absent}
    identities = {"first": "first", "equivalent": "first", "other": "other", "absent": "absent"}
    with TemporaryDirectory(prefix="ocr-diagram-states-") as directory:
        collector = DiagramCollector(
            Path(directory).resolve() / "diagram.json", "d" * 32, REVIEW_RANGE
        )
        collector.initialize()
        count, total, reason, identity = 0, 0, "none", None
        for action in actions:
            candidate = candidates.get(action, {"state": "invalid"})
            size = MAX_SUBMISSION_BYTES if action == "large" else len(bounded_json(candidate))
            count = min(count + 1, MAX_SUBMISSIONS + 1)
            total = min(total + size, MAX_SUBMISSION_BYTES + 1)
            if count > MAX_SUBMISSIONS or total > MAX_SUBMISSION_BYTES:
                reason = "budget"
            elif reason == "none":
                if action in ("invalid", "large"):
                    reason = "invalid"
                elif identity is not None and identity != identities[action]:
                    reason = "conflict"
                else:
                    identity = identities[action]
            snapshot = collector.submit(candidate, input_bytes=size)
            assert (snapshot.submissions, snapshot.input_bytes, snapshot.reason) == (
                count,
                total,
                reason,
            )
            assert collector.read() == snapshot
            if reason == "none":
                expected = first if identity == "first" else candidates[identity]
                assert snapshot.candidate == parse_submission(expected, expected_range=REVIEW_RANGE)
            else:
                assert snapshot.candidate is None
        if not actions:
            snapshot = collector.read()
            assert (
                snapshot.submissions,
                snapshot.input_bytes,
                snapshot.reason,
                snapshot.candidate,
            ) == (0, 0, "none", None)
