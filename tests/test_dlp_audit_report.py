"""Private observation grouping stays source-free, deterministic and non-authoritative."""

from ocr_toolkit.dlp_audit.report import render_report


def hit(slot, unit, role, reason="pii", detector="phone:normalized", proof=False):
    return dict(slot=slot, unit=unit, role=role, reason=reason, detector=detector, proof=proof)


def test_groups_deduplicate_locations_and_separate_whole_file_probes():
    hits = [
        hit("a", 0, "text"),
        hit("a", 1, "text"),
        hit("a", 1, "existing_code", proof=True),
        hit("b", 0, "existing_code", "secret", "normalized"),
        hit("c", 2, "text"),
        hit("c", 2, "existing_code"),
    ]
    run = dict(hits=hits, complete=True, units=8, expected_units=8, errors=[])
    report = render_report("synthetic", run)
    for line in (
        "Distinct line locations: 2",
        "Whole-file role probes: 2",
        "Whole-file probes sharing a child primary reason: 1",
        "Whole-file probes without a child primary reason: 1",
        "Locations with one rejecting role: 2",
        "Locations with differing rejecting role facts: 1",
    ):
        assert line in report
    assert "not causal verdicts" in report
    assert "source-proof=True" in report and "source-proof=False" in report
    run["hits"] = list(reversed(hits))
    assert render_report("synthetic", run) == report


def test_empty_and_incomplete_reports_do_not_infer_passes():
    run = dict(
        hits=[],
        complete=False,
        units=0,
        expected_units=10,
        errors=[
            dict(reason="worker_timeout"),
            dict(reason="worker_timeout"),
            dict(reason="scan_deadline"),
        ],
    )
    report = render_report("synthetic", run)
    assert "worker_timeout: 2" in report and "scan_deadline: 1" in report
    assert "Incomplete runs cannot establish admissions" in report
    assert "Rejected role units: 0" in report
