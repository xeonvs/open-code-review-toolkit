"""Policy and provider regressions for SHA-bound GitLab approval."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr
from typing import Any

import pytest

from ocr_toolkit import ocr_result
from ocr_toolkit.posting import (
    approval,
    formatting,
    gitlab,
    gitlab_approval,
    markers,
    settings,
    workflow,
)
from ocr_toolkit.posting.payloads import build_marked_note_body
from ocr_toolkit.posting.snapshot import BotCommentRefs
from ocr_toolkit.result_contract import ReviewOutcome
from tests.support import cleared_env, gitlab_config, patched_attr, patched_env


def complete_outcome() -> ReviewOutcome:
    """Return an authoritative complete synthetic OCR outcome."""

    return ReviewOutcome(
        status="complete",
        kind="clean",
        budget_exceeded=False,
        manifest_present=True,
        selected_count=1,
        completed_count=1,
    )


def finding(category: Any = "style", severity: Any = "low") -> dict[str, Any]:
    """Return one synthetic structured finding."""

    return {"category": category, "severity": severity}


def receipt_v7(
    *,
    context_state: str = "disabled",
    external: bool = False,
    author_id: int | None = 41,
    target_protection: str = "protected",
) -> dict[str, Any]:
    """Return one closed synthetic review-time receipt."""

    mode = "metadata" if context_state != "disabled" else "off"
    capabilities = [
        {
            "server": "ocr_toolkit_evidence",
            "transport": "builtin",
            "tools": [
                "ocr_toolkit_evidence",
                "ocr_toolkit_evidence_search",
                "ocr_toolkit_evidence_coverage",
            ],
        }
    ]
    if external:
        capabilities.append(
            {"server": "documentation", "transport": "remote", "tools": ["docs_read"]}
        )
    return {
        "schema_version": 7,
        "review": {
            "source_sha": "a" * 40,
            "policy_sha": "b" * 40,
            "target_sha": "b" * 40,
            "target_protection": target_protection,
            "mr_author_id": author_id,
        },
        "context": {
            "mode": mode,
            "state": context_state,
            "classes": ["merge_request_metadata"] if mode == "metadata" else [],
            "policy_digest": None,
            "per_source": {},
            "degradation_counts": {"invalid": 0, "limit": 0, "unavailable": 0},
            "required_degraded": False,
            "mutable_admitted": False,
            "tool_usage": {"context_get": 0, "context_list": 0},
        },
        "mcp": {
            "capabilities": capabilities,
            "usage": {"ocr_toolkit_evidence": 1},
        },
        "evidence": {
            "mandatory": True,
            "used": True,
            "calls": 1,
            "actions": {
                "state": "verified",
                "summary": 1,
                "list": 0,
                "get": 0,
                "search": 0,
                "coverage": 0,
            },
        },
        "publication": {"state": "passed"},
        "cleanup": {"result": "passed"},
    }


def test_unprotected_receipt_is_valid_but_structurally_comment_only() -> None:
    receipt = receipt_v7(target_protection="unprotected")

    assert approval.toolkit_receipt_is_valid(receipt)
    decision = approval.evaluate_approval_policy(
        settings.BooleanSetting(True), complete_outcome(), [], [], 0, receipt
    )
    assert decision.eligible is False
    assert decision.result.reason == (
        "the GitLab target branch was unprotected; limited reviews are comment-only"
    )


def test_unprotected_receipt_never_reaches_approval_mutation_path() -> None:
    receipt = receipt_v7(target_protection="unprotected")
    eligibility = approval.evaluate_approval_policy(
        settings.BooleanSetting(True), complete_outcome(), [], [], 0, receipt
    )
    calls: list[str] = []

    with (
        patched_attr(
            gitlab_approval,
            "wait_for_synchronized_approval_state",
            lambda *_args, **_kwargs: calls.append("synchronize") or (None, None),
        ),
        patched_attr(
            gitlab,
            "approve_merge_request",
            lambda *_args, **_kwargs: calls.append("approve"),
        ),
    ):
        result = gitlab_approval.execute_approval(
            gitlab_config(), eligibility, "a" * 40, expected_author_id=41
        )

    assert calls == []
    assert result.result == eligibility.result


@pytest.mark.parametrize(
    "value",
    (None, "", "required", "UNPROTECTED", True, False, 0, {}, [], "unprotected "),
)
def test_hostile_target_protection_states_invalidate_receipt(value: Any) -> None:
    receipt = receipt_v7()
    receipt["review"]["target_protection"] = value
    assert not approval.toolkit_receipt_is_valid(receipt)
    assert workflow.unprotected_target_limitation(receipt) is False


def test_target_sha_is_exactly_bound_to_policy_sha() -> None:
    for mutate in (
        lambda review: review.update({"target_sha": "c" * 40}),
        lambda review: review.pop("target_sha"),
        lambda review: review.update({"extra": "c" * 40}),
    ):
        receipt = receipt_v7()
        mutate(receipt["review"])
        assert not approval.toolkit_receipt_is_valid(receipt)


def eligibility(
    comments: list[dict[str, Any]] | None = None,
    *,
    outcome: ReviewOutcome | None = None,
    warnings: list[Any] | None = None,
    omitted: int = 0,
    setting: settings.BooleanSetting | None = None,
) -> approval.ApprovalEligibility:
    """Evaluate the fixed policy with concise synthetic defaults."""

    return approval.evaluate_approval_policy(
        setting or settings.BooleanSetting(True),
        outcome or complete_outcome(),
        comments or [],
        warnings or [],
        omitted,
        receipt_v7(),
    )


def enriched_receipt(*, mutable: bool = False, required_degraded: bool = False) -> dict[str, Any]:
    """Return one v7 local-store-only enrichment receipt."""

    receipt = receipt_v7()
    receipt["context"] = {
        "mode": "enriched",
        "state": "degraded" if required_degraded else "complete",
        "classes": ["merge_request_metadata", "forge_discussions", "external_records"],
        "policy_digest": "c" * 64,
        "per_source": {"forge:gitlab_discussions": "complete"},
        "degradation_counts": {
            "invalid": 0,
            "limit": 0,
            "unavailable": 1 if required_degraded else 0,
        },
        "required_degraded": required_degraded,
        "mutable_admitted": mutable,
        "tool_usage": {"context_get": 0, "context_list": 0},
    }
    receipt["mcp"]["capabilities"][0]["tools"] = [
        "ocr_toolkit_evidence",
        "ocr_toolkit_evidence_search",
        "ocr_toolkit_evidence_coverage",
        "context_list",
        "context_get",
    ]
    return receipt


class ApprovalSettingTests(unittest.TestCase):
    """Lock default-on configuration and fail-closed invalid values."""

    def tearDown(self) -> None:
        settings.auto_approve.cache_clear()

    def test_defaults_on_and_accepts_complete_boolean_vocabulary(self) -> None:
        with cleared_env("OCR_AUTO_APPROVE"):
            settings.auto_approve.cache_clear()
            self.assertEqual(settings.auto_approve(), settings.BooleanSetting(True))
        for value in ("true", "1", "yes", "on", "TRUE"):
            with self.subTest(value=value), patched_env(OCR_AUTO_APPROVE=value):
                settings.auto_approve.cache_clear()
                self.assertEqual(settings.auto_approve(), settings.BooleanSetting(True))
        for value in ("false", "0", "no", "off", "FALSE"):
            with self.subTest(value=value), patched_env(OCR_AUTO_APPROVE=value):
                settings.auto_approve.cache_clear()
                self.assertEqual(settings.auto_approve(), settings.BooleanSetting(False))

    def test_invalid_value_disables_without_logging_raw_input(self) -> None:
        stderr = io.StringIO()
        with patched_env(OCR_AUTO_APPROVE="secret-token-value"), redirect_stderr(stderr):
            settings.auto_approve.cache_clear()
            value = settings.auto_approve()

        self.assertEqual(value, settings.BooleanSetting(False, valid=False))
        self.assertNotIn("secret-token-value", stderr.getvalue())


class ApprovalPolicyTests(unittest.TestCase):
    """Lock every allow and deny branch in the fixed first-release policy."""

    def test_clean_zero_and_one_to_three_allowed_findings_are_eligible(self) -> None:
        self.assertTrue(eligibility().eligible)
        for count in range(1, 4):
            with self.subTest(count=count):
                self.assertTrue(eligibility([finding()] * count).eligible)

    def test_four_findings_and_every_blocking_category_are_ineligible(self) -> None:
        self.assertFalse(eligibility([finding()] * 4).eligible)
        for category in ("bug", "security", "test", "performance", "other"):
            with self.subTest(category=category):
                self.assertFalse(eligibility([finding(category=category)]).eligible)

    def test_blocking_or_malformed_metadata_is_ineligible(self) -> None:
        for severity in ("critical", "high", "medium", "LOW", None, 1, True):
            with self.subTest(severity=severity):
                self.assertFalse(eligibility([finding(severity=severity)]).eligible)
        for category in ("unknown", "STYLE", None, 1, True, [], {}):
            with self.subTest(category=category):
                self.assertFalse(eligibility([finding(category=category)]).eligible)

    def test_incomplete_warning_omitted_budget_waived_and_legacy_block(self) -> None:
        legacy = ReviewOutcome("success", "clean", False)
        partial = ReviewOutcome("partial", "partial", False, manifest_present=True)
        budget = ReviewOutcome("partial", "partial", True, manifest_present=True)
        waived = ReviewOutcome("complete", "clean", False, manifest_present=True, waived_count=1)
        for name, decision in (
            ("legacy", eligibility(outcome=legacy)),
            ("partial", eligibility(outcome=partial)),
            ("budget", eligibility(outcome=budget)),
            ("waived", eligibility(outcome=waived)),
            ("warning", eligibility(warnings=["synthetic warning"])),
            ("omitted", eligibility(omitted=1)),
        ):
            with self.subTest(name=name):
                self.assertFalse(decision.eligible)

    def test_degraded_context_receipt_blocks_without_exposing_provider_text(self) -> None:
        decision = approval.evaluate_approval_policy(
            settings.BooleanSetting(True),
            complete_outcome(),
            [],
            [],
            0,
            receipt_v7(context_state="degraded", author_id=41),
        )

        self.assertFalse(decision.eligible)
        self.assertEqual(decision.result.status, approval.ApprovalStatus.NOT_ELIGIBLE)
        self.assertEqual(decision.result.reason, "the selected review context was degraded")

    def test_publication_dlp_filtered_receipt_is_valid_but_never_eligible(self) -> None:
        receipt = receipt_v7()
        receipt["publication"] = {
            "state": "publication-filtered",
            "reason_counts": {
                "forbidden": 1,
                "invalid_text": 0,
                "laundering": 0,
                "limit": 0,
                "pii": 0,
                "secret": 0,
            },
            "retained": {"comments": 1, "warnings": 0},
            "omitted": {"comments": 1, "warnings": 0, "fields": 0},
            "original": {
                "outcome": "clean",
                "selected": 2,
                "completed": 2,
                "reused": 0,
                "failed": 0,
                "waived": 0,
            },
        }

        decision = approval.evaluate_approval_policy(
            settings.BooleanSetting(True),
            complete_outcome(),
            [finding()],
            [],
            0,
            receipt,
        )

        self.assertFalse(decision.eligible)
        self.assertEqual(decision.result.status, approval.ApprovalStatus.NOT_ELIGIBLE)
        self.assertEqual(
            decision.result.reason,
            "publication DLP filtered the complete review result",
        )

    def test_provider_private_fields_cannot_enter_approval_receipt(self) -> None:
        """Reject replay or request-control fields at the closed receipt boundary."""

        for field in ("reasoning_content", "native_payload", "tool_choice"):
            receipt = receipt_v7()
            receipt[field] = "private"

            with self.subTest(field=field):
                self.assertFalse(approval.toolkit_receipt_is_valid(receipt))

    def test_filtered_receipt_rejects_outcomes_that_contradict_coverage(self) -> None:
        """Accept run-level failure but reject impossible coverage/outcome combinations."""

        publication = {
            "state": "publication-filtered",
            "reason_counts": {
                "forbidden": 1,
                "invalid_text": 0,
                "laundering": 0,
                "limit": 0,
                "pii": 0,
                "secret": 0,
            },
            "retained": {"comments": 0, "warnings": 0},
            "omitted": {"comments": 1, "warnings": 0, "fields": 0},
            "original": {
                "outcome": "failed",
                "selected": 2,
                "completed": 2,
                "reused": 0,
                "failed": 0,
                "waived": 0,
            },
        }
        self.assertEqual(approval.publication_dlp_state(publication), "publication-filtered")

        invalid_originals = (
            {"outcome": "partial", "selected": 0, "completed": 0, "failed": 0},
            {"outcome": "clean", "selected": 0, "completed": 0, "failed": 0},
            {"outcome": "warning", "selected": 0, "completed": 0, "failed": 0},
            {"outcome": "skipped", "selected": 1, "completed": 1, "failed": 0},
            {"outcome": "partial", "selected": 2, "completed": 2, "failed": 0},
            {"outcome": "partial", "selected": 2, "completed": 0, "failed": 2},
            {"outcome": "clean", "selected": 2, "completed": 0, "failed": 2},
            {"outcome": "warning", "selected": 2, "completed": 0, "failed": 2},
        )
        for original in invalid_originals:
            candidate = {
                **publication,
                "original": {
                    "reused": 0,
                    "waived": 0,
                    **original,
                },
            }
            with self.subTest(original=original):
                self.assertIsNone(approval.publication_dlp_state(candidate))

    def test_private_only_sanitization_keeps_existing_approval_gates(self) -> None:
        receipt = receipt_v7()
        receipt["publication"] = {
            "state": "private-sanitized",
            "reason_counts": {
                "forbidden": 0,
                "invalid_text": 0,
                "laundering": 0,
                "limit": 0,
                "pii": 1,
                "secret": 0,
            },
            "sanitized_fields": 1,
        }

        decision = approval.evaluate_approval_policy(
            settings.BooleanSetting(True), complete_outcome(), [], [], 0, receipt
        )

        self.assertTrue(decision.eligible)

    def test_evidence_action_attribution_does_not_change_approval_eligibility(self) -> None:
        receipt = receipt_v7()
        receipt["evidence"]["actions"] = {
            "state": "verified",
            "summary": 1,
            "list": 0,
            "get": 0,
            "search": 0,
            "coverage": 0,
        }
        decision = approval.evaluate_approval_policy(
            settings.BooleanSetting(True), complete_outcome(), [], [], 0, receipt
        )
        self.assertTrue(decision.eligible)

        receipt["evidence"]["actions"]["summary"] = 0
        decision = approval.evaluate_approval_policy(
            settings.BooleanSetting(True), complete_outcome(), [], [], 0, receipt
        )
        self.assertFalse(decision.eligible)
        self.assertIn("receipt is missing or invalid", decision.result.reason)

    def test_complete_metadata_and_external_mcp_have_independent_approval_effects(self) -> None:
        complete_metadata = approval.evaluate_approval_policy(
            settings.BooleanSetting(True),
            complete_outcome(),
            [],
            [],
            0,
            receipt_v7(context_state="complete", author_id=41),
        )
        external = approval.evaluate_approval_policy(
            settings.BooleanSetting(True), complete_outcome(), [], [], 0, receipt_v7(external=True)
        )

        self.assertTrue(complete_metadata.eligible)
        self.assertFalse(external.eligible)
        self.assertEqual(
            external.result.reason, "external MCP was configured for a comment-only review"
        )

    def test_enriched_zero_record_can_approve_but_mutable_or_required_degradation_cannot(
        self,
    ) -> None:
        complete = approval.evaluate_approval_policy(
            settings.BooleanSetting(True), complete_outcome(), [], [], 0, enriched_receipt()
        )
        mutable = approval.evaluate_approval_policy(
            settings.BooleanSetting(True),
            complete_outcome(),
            [],
            [],
            0,
            enriched_receipt(mutable=True),
        )
        degraded = approval.evaluate_approval_policy(
            settings.BooleanSetting(True),
            complete_outcome(),
            [],
            [],
            0,
            enriched_receipt(required_degraded=True),
        )

        self.assertTrue(complete.eligible)
        self.assertEqual(mutable.result.reason, "mutable review context was admitted")
        self.assertEqual(degraded.result.reason, "the selected review context was degraded")

    def test_optional_context_mutation_remains_visible_without_becoming_required_failure(
        self,
    ) -> None:
        receipt = enriched_receipt()
        receipt["context"]["per_source"] = {"forge:gitlab_discussions": "mutated"}
        receipt["context"]["degradation_counts"]["invalid"] = 1

        decision = approval.evaluate_approval_policy(
            settings.BooleanSetting(True), complete_outcome(), [], [], 0, receipt
        )

        self.assertTrue(decision.eligible)

    def test_receipt_accepts_ocr_compatible_non_identifier_tool_names(self) -> None:
        metadata = receipt_v7(external=True)
        metadata["mcp"]["capabilities"][1]["tools"] = ["repo.search", "records/read"]

        decision = approval.evaluate_approval_policy(
            settings.BooleanSetting(True), complete_outcome(), [], [], 0, metadata
        )

        self.assertFalse(decision.eligible)
        self.assertEqual(
            decision.result.reason,
            "external MCP was configured for a comment-only review",
        )

    def test_every_pre_v7_receipt_is_rejected(self) -> None:
        for version in range(1, 7):
            with self.subTest(version=version):
                decision = approval.evaluate_approval_policy(
                    settings.BooleanSetting(True),
                    complete_outcome(),
                    [],
                    [],
                    0,
                    {"schema_version": version, "mcp_usage": {"ocr_toolkit_evidence": 1}},
                )

                self.assertFalse(decision.eligible)
                self.assertEqual(
                    decision.result.reason,
                    "the review-time approval receipt is missing or invalid",
                )

    def test_missing_or_malformed_v7_receipt_fails_closed(self) -> None:
        cases: list[Any] = [None, {"schema_version": 7}]
        for mutate in (
            lambda value: value["context"].update({"state": "complete"}),
            lambda value: value["review"].update({"source_sha": "invalid"}),
            lambda value: value["mcp"].update({"usage": {"unknown": 1}}),
            lambda value: value["evidence"].update({"used": False}),
        ):
            candidate = receipt_v7()
            mutate(candidate)
            cases.append(candidate)
        for metadata in cases:
            with self.subTest(metadata=metadata):
                decision = approval.evaluate_approval_policy(
                    settings.BooleanSetting(True), complete_outcome(), [], [], 0, metadata
                )
                self.assertFalse(decision.eligible)
                self.assertEqual(
                    decision.result.reason,
                    "the review-time approval receipt is missing or invalid",
                )

    def test_group_diagnostics_cannot_extend_the_closed_receipt(self) -> None:
        """Reject OCR-owned group or round fields if they enter the approval receipt."""

        for field, value in (
            ("groups", [{"label": "core", "files": ["src/core.py"]}]),
            ("review_rounds", 2),
        ):
            receipt = receipt_v7()
            receipt[field] = value

            decision = approval.evaluate_approval_policy(
                settings.BooleanSetting(True), complete_outcome(), [], [], 0, receipt
            )

            self.assertFalse(decision.eligible)
            self.assertEqual(
                decision.result.reason,
                "the review-time approval receipt is missing or invalid",
            )

    def test_impossible_v6_capability_and_evidence_states_fail_closed(self) -> None:
        cases: list[dict[str, Any]] = []

        builtin_remote = receipt_v7()
        builtin_remote["mcp"]["capabilities"][0]["transport"] = "remote"
        cases.append(builtin_remote)

        external_builtin = receipt_v7(external=True)
        external_builtin["mcp"]["capabilities"][1]["transport"] = "builtin"
        cases.append(external_builtin)

        wrong_builtin_tool = receipt_v7()
        wrong_builtin_tool["mcp"]["capabilities"][0]["tools"] = ["other_read"]
        cases.append(wrong_builtin_tool)

        duplicate_tool = receipt_v7(external=True)
        duplicate_tool["mcp"]["capabilities"][1]["tools"] = ["ocr_toolkit_evidence"]
        cases.append(duplicate_tool)

        too_many_tools = receipt_v7(external=True)
        too_many_tools["mcp"]["capabilities"][1]["tools"] = [
            f"tool_{index}" for index in range(129)
        ]
        cases.append(too_many_tools)

        usage_mismatch = receipt_v7()
        usage_mismatch["mcp"]["usage"] = {}
        cases.append(usage_mismatch)

        usage_overflow = receipt_v7()
        usage_overflow["mcp"]["usage"] = {"ocr_toolkit_evidence": 1_000_000_001}
        cases.append(usage_overflow)

        missing_author = receipt_v7(author_id=None)
        cases.append(missing_author)

        mandatory_mismatch = receipt_v7()
        mandatory_mismatch["evidence"] = {"mandatory": False, "used": True}
        cases.append(mandatory_mismatch)

        for metadata in cases:
            with self.subTest(metadata=metadata):
                decision = approval.evaluate_approval_policy(
                    settings.BooleanSetting(True), complete_outcome(), [], [], 0, metadata
                )
                self.assertFalse(decision.eligible)
                self.assertEqual(
                    decision.result.reason,
                    "the review-time approval receipt is missing or invalid",
                )

    def test_disabled_and_invalid_setting_remain_non_actionable(self) -> None:
        for setting in (
            settings.BooleanSetting(False),
            settings.BooleanSetting(False, valid=False),
        ):
            decision = eligibility(setting=setting)
            self.assertEqual(decision.result.status, approval.ApprovalStatus.DISABLED)

    def test_eligible_provisional_summary_fails_closed_until_readback(self) -> None:
        provisional = approval.provisional_approval_result(eligibility())

        self.assertEqual(provisional.status, approval.ApprovalStatus.FAILED)
        self.assertIn("not yet been confirmed", provisional.reason)

        disabled = eligibility(setting=settings.BooleanSetting(False))
        self.assertEqual(
            approval.provisional_approval_result(disabled),
            disabled.result,
        )


class GitLabApprovalAdapterTests(unittest.TestCase):
    """Exercise synchronization, exact-SHA writes, and bounded readback."""

    SHA = "a" * 40

    @staticmethod
    def api_sequence(
        own_approved: bool = False,
        *,
        sha: str = SHA,
        detailed_status: str = "mergeable",
        patch_id: str | None = "b" * 40,
    ) -> Any:
        def request(_config: Any, endpoint: str, **_kwargs: Any) -> Any:
            if endpoint == "":
                return {
                    "sha": sha,
                    "state": "opened",
                    "author": {"id": 41},
                    "detailed_merge_status": detailed_status,
                }
            if endpoint == "/approvals":
                return {"approved_by": ([{"user": {"id": 7}}] if own_approved else [])}
            raise AssertionError(endpoint)

        return request

    def test_waits_for_sync_without_writing_and_rejects_stale_sha(self) -> None:
        sleeps: list[float] = []
        mr_reads = 0

        def request(*args: Any, **kwargs: Any) -> Any:
            nonlocal mr_reads
            if args[1] == "":
                pending = mr_reads == 0
                mr_reads += 1
                return {
                    "sha": self.SHA,
                    "state": "opened",
                    "author": {"id": 41},
                    "detailed_merge_status": "checking" if pending else "mergeable",
                }
            return self.api_sequence()(*args, **kwargs)

        def latest(_config: Any) -> dict[str, Any]:
            pending = mr_reads == 1
            return {
                "id": mr_reads,
                "head_commit_sha": self.SHA,
                "patch_id_sha": None if pending else "b" * 40,
            }

        with (
            patched_attr(gitlab, "api_request", request),
            patched_attr(gitlab_approval, "_latest_diff_version", latest),
        ):
            state, error = gitlab_approval.wait_for_synchronized_approval_state(
                gitlab_config(), self.SHA, sleep=sleeps.append
            )

        self.assertIsNone(error)
        self.assertEqual(state, gitlab_approval.GitLabApprovalState(False, 41))
        self.assertEqual(sleeps, [2.0])

        with (
            patched_attr(gitlab, "api_request", self.api_sequence(sha="c" * 40)),
            patched_attr(
                gitlab_approval,
                "_latest_diff_version",
                lambda _config: {
                    "id": 1,
                    "head_commit_sha": "c" * 40,
                    "patch_id_sha": "b" * 40,
                },
            ),
        ):
            stale_state, stale = gitlab_approval.wait_for_synchronized_approval_state(
                gitlab_config(), self.SHA, sleep=lambda _seconds: None
            )
        self.assertIsNone(stale_state)
        self.assertEqual(stale and stale.status, approval.ApprovalStatus.SKIPPED)

    def test_eligible_review_approves_exact_sha_and_confirms_own_user(self) -> None:
        approval_reads = 0
        approve_shas: list[str] = []

        def request(*args: Any, **kwargs: Any) -> Any:
            nonlocal approval_reads
            endpoint = args[1]
            own = approval_reads > 0
            if endpoint == "/approvals":
                approval_reads += 1
            return self.api_sequence(own_approved=own)(*args, **kwargs)

        def approve(_config: Any, sha: str) -> gitlab.GitLabWriteResult:
            approve_shas.append(sha)
            return gitlab.GitLabWriteResult("posted")

        with (
            patched_attr(gitlab, "api_request", request),
            patched_attr(
                gitlab_approval,
                "_latest_diff_version",
                lambda _config: {
                    "id": 2,
                    "head_commit_sha": self.SHA,
                    "patch_id_sha": "b" * 40,
                },
            ),
            patched_attr(gitlab, "approve_merge_request", approve),
        ):
            result = gitlab_approval.execute_approval(
                gitlab_config(), eligibility(), self.SHA, 41, sleep=lambda _seconds: None
            )

        self.assertEqual(approve_shas, [self.SHA])
        self.assertEqual(result.result.status, approval.ApprovalStatus.APPROVED)

    def test_post_write_author_change_fails_closed_after_exact_sha_approval(self) -> None:
        for post_write_author in (42, 7):
            with self.subTest(post_write_author=post_write_author):
                mr_reads = 0
                writes: list[str] = []

                def request(_config: Any, endpoint: str, **_kwargs: Any) -> Any:
                    nonlocal mr_reads
                    if endpoint == "":
                        mr_reads += 1
                        return {
                            "sha": self.SHA,
                            "state": "opened",
                            "author": {"id": 41 if mr_reads == 1 else post_write_author},
                            "detailed_merge_status": "mergeable",
                        }
                    if endpoint == "/approvals":
                        return {"approved_by": ([{"user": {"id": 7}}] if mr_reads > 1 else [])}
                    raise AssertionError(endpoint)

                def approve(_config: Any, sha: str) -> gitlab.GitLabWriteResult:
                    writes.append(sha)
                    return gitlab.GitLabWriteResult("posted")

                with (
                    patched_attr(gitlab, "api_request", request),
                    patched_attr(
                        gitlab_approval,
                        "_latest_diff_version",
                        lambda _config: {
                            "id": 2,
                            "head_commit_sha": self.SHA,
                            "patch_id_sha": "b" * 40,
                        },
                    ),
                    patched_attr(gitlab, "approve_merge_request", approve),
                ):
                    result = gitlab_approval.execute_approval(
                        gitlab_config(), eligibility(), self.SHA, 41, sleep=lambda _seconds: None
                    )

                self.assertEqual(writes, [self.SHA])
                self.assertEqual(result.result.status, approval.ApprovalStatus.FAILED)
                self.assertIn("post-write merge-request author", result.result.reason)

    def test_ambiguous_approve_is_not_retried(self) -> None:
        writes: list[str] = []

        def approve(_config: Any, sha: str) -> gitlab.GitLabWriteResult:
            writes.append(sha)
            return gitlab.GitLabWriteResult("write_failed")

        with (
            patched_attr(gitlab, "api_request", self.api_sequence()),
            patched_attr(
                gitlab_approval,
                "_latest_diff_version",
                lambda _config: {
                    "id": 2,
                    "head_commit_sha": self.SHA,
                    "patch_id_sha": "b" * 40,
                },
            ),
            patched_attr(gitlab, "approve_merge_request", approve),
        ):
            result = gitlab_approval.execute_approval(
                gitlab_config(), eligibility(), self.SHA, 41, sleep=lambda _seconds: None
            )

        self.assertEqual(writes, [self.SHA])
        self.assertEqual(result.result.status, approval.ApprovalStatus.FAILED)

    def test_existing_approval_is_preserved_without_write(self) -> None:
        writes: list[str] = []
        with (
            patched_attr(gitlab, "api_request", self.api_sequence(own_approved=True)),
            patched_attr(
                gitlab_approval,
                "_latest_diff_version",
                lambda _config: {
                    "id": 2,
                    "head_commit_sha": self.SHA,
                    "patch_id_sha": "b" * 40,
                },
            ),
            patched_attr(
                gitlab,
                "approve_merge_request",
                lambda *_args: writes.append("approve"),
            ),
        ):
            result = gitlab_approval.execute_approval(gitlab_config(), eligibility(), self.SHA, 41)

        self.assertEqual(result.result.status, approval.ApprovalStatus.SKIPPED)
        self.assertEqual(writes, [])

    def test_author_mismatch_and_self_approval_skip_without_write(self) -> None:
        writes: list[str] = []

        def approve(*_args: Any) -> gitlab.GitLabWriteResult:
            writes.append("approve")
            return gitlab.GitLabWriteResult("posted")

        with (
            patched_attr(gitlab, "api_request", self.api_sequence()),
            patched_attr(
                gitlab_approval,
                "_latest_diff_version",
                lambda _config: {
                    "id": 2,
                    "head_commit_sha": self.SHA,
                    "patch_id_sha": "b" * 40,
                },
            ),
            patched_attr(gitlab, "approve_merge_request", approve),
        ):
            mismatch = gitlab_approval.execute_approval(
                gitlab_config(), eligibility(), self.SHA, 42, sleep=lambda _seconds: None
            )
            self_authored = gitlab_approval.execute_approval(
                gitlab_config(current_user_id=41),
                eligibility(),
                self.SHA,
                41,
                sleep=lambda _seconds: None,
            )

        self.assertEqual(writes, [])
        self.assertIn("author no longer matches", mismatch.result.reason)
        self.assertIn("is the merge-request author", self_authored.result.reason)

    def test_malformed_author_readback_fails_before_write(self) -> None:
        def request(_config: Any, endpoint: str, **_kwargs: Any) -> Any:
            if endpoint == "":
                return {
                    "sha": self.SHA,
                    "state": "opened",
                    "author": {"id": True},
                    "detailed_merge_status": "mergeable",
                }
            if endpoint == "/approvals":
                return {"approved_by": []}
            raise AssertionError(endpoint)

        with (
            patched_attr(gitlab, "api_request", request),
            patched_attr(
                gitlab_approval,
                "_latest_diff_version",
                lambda _config: {
                    "id": 2,
                    "head_commit_sha": self.SHA,
                    "patch_id_sha": "b" * 40,
                },
            ),
        ):
            result = gitlab_approval.execute_approval(
                gitlab_config(), eligibility(), self.SHA, 41, sleep=lambda _seconds: None
            )

        self.assertEqual(result.result.status, approval.ApprovalStatus.FAILED)
        self.assertIn("author metadata", result.result.reason)

    def test_provider_write_uses_only_exact_sha_approval_endpoint(self) -> None:
        calls: list[tuple[str, dict[str, Any], str]] = []

        def write(
            url: str,
            api_token: str,
            auth_header: str,
            data: dict[str, Any],
            method: str = "POST",
            **_kwargs: Any,
        ) -> gitlab.GitLabWriteResult:
            self.assertEqual(api_token, "token")
            self.assertEqual(auth_header, "PRIVATE-TOKEN")
            calls.append((url, data, method))
            return gitlab.GitLabWriteResult("posted")

        with patched_attr(gitlab, "api_write_url_detailed", write):
            gitlab.approve_merge_request(gitlab_config(), self.SHA)

        self.assertEqual(calls[0][0].rsplit("/", 1)[-1], "approve")
        self.assertEqual(calls[0][1], {"sha": self.SHA})
        self.assertNotIn("reset_approvals", repr(calls))

    def test_disabled_or_partial_review_performs_no_approval_api(self) -> None:
        for decision in (
            eligibility(setting=settings.BooleanSetting(False)),
            eligibility(outcome=ReviewOutcome("partial", "partial", False, True)),
        ):
            with self.subTest(status=decision.result.status):
                result = gitlab_approval.execute_approval(gitlab_config(), decision, self.SHA, 41)
                self.assertEqual(result.result, decision.result)

    def test_current_user_approval_rejects_nonpositive_user_ids(self) -> None:
        for value in (True, 0, -1, "7", 7.0):
            with self.subTest(value=value):
                self.assertIsNone(
                    gitlab_approval._current_user_approved(
                        {"approved_by": [{"user": {"id": value}}]}, 7
                    )
                )

    def test_latest_diff_version_uses_highest_valid_id_not_response_order(self) -> None:
        versions = [
            {"id": 2, "head_commit_sha": "b" * 40},
            {"id": 5, "head_commit_sha": "e" * 40},
            {"id": 3, "head_commit_sha": "c" * 40},
        ]
        with patched_attr(gitlab, "api_get_paginated", lambda *_args, **_kwargs: versions):
            latest = gitlab_approval._latest_diff_version(gitlab_config())

        self.assertEqual(latest, versions[1])


class ApprovalWorkflowTests(unittest.TestCase):
    """Keep advisory publication successful and approval status truthful."""

    SHA = "a" * 40
    RUN_ID = "b" * 32

    def tearDown(self) -> None:
        settings.post_mode.cache_clear()

    def test_receipt_identity_is_atomic_for_summary_and_approval(self) -> None:
        valid = receipt_v7(author_id=41)
        self.assertEqual(workflow.approval_receipt_identity(valid), ("a" * 40, 41))

        for mutate in (
            lambda value: value["review"].update({"source_sha": "invalid"}),
            lambda value: value["review"].update({"mr_author_id": None}),
            lambda value: value["review"].update({"mr_author_id": True}),
            lambda value: value.update({"cleanup": {"result": "unknown"}}),
            lambda value: value.update({"extra": True}),
        ):
            candidate = receipt_v7(author_id=41)
            mutate(candidate)
            with self.subTest(candidate=candidate):
                self.assertEqual(workflow.approval_receipt_identity(candidate), ("", None))

    def test_valid_receipt_binds_advisory_without_changing_summary_or_approval_inputs(self) -> None:
        """Publish one closed advisory in Technical details with ordinary clean status."""

        receipt = receipt_v7(author_id=41)
        self.assertTrue(approval.toolkit_receipt_is_valid(receipt))
        notes: list[str] = []

        def capture_note(_config: Any, _title: str, body: str, *_args: Any) -> dict[str, int]:
            notes.append(body)
            return {"id": 1}

        with (
            patched_attr(
                workflow, "collect_previous_bot_comment_refs", lambda _config: BotCommentRefs()
            ),
            patched_attr(workflow, "post_review_note_bounded", capture_note),
            patched_attr(workflow, "finalize_review_approval", lambda *_args, **_kwargs: 0),
        ):
            exit_code = workflow.post_results(
                gitlab_config(),
                {
                    "status": "complete",
                    "comments": [],
                    "warnings": [],
                    "manifest": {
                        "schema_version": "ocr.run-manifest/v1",
                        "operation": "review",
                        "terminal_state": "complete",
                        "coverage": {
                            "selected": [{"item_id": "synthetic-item"}],
                            "completed": [{"item_id": "synthetic-item"}],
                            "reused": [],
                            "failed": [],
                            "waived": [],
                        },
                    },
                    "_ocr_toolkit": receipt,
                    ocr_result.TOOLKIT_ADVISORY_KEY: ocr_result.toolkit_advisory_payload(
                        ocr_result.background_recommended_advisory(
                            actual=2_100,
                            recommended=2_000,
                        )
                    ),
                },
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(notes), 1)
        visible, technical = notes[0].split("<details>", 1)
        self.assertIn("Review complete — no findings", visible)
        self.assertNotIn("warnings", visible.casefold())
        self.assertNotIn("OCR core advisory", visible)
        self.assertIn(
            "OCR core advisory: background 2100 characters; recommended 2000 characters; "
            "accepted by OCR core",
            technical,
        )

    def test_unprotected_limitation_is_adjacent_once_for_all_receipt_outcomes(self) -> None:
        scenarios = (
            ("complete", [], "complete", {}, []),
            (
                "complete",
                [],
                "complete",
                {},
                [
                    {
                        "path": "src/example.py",
                        "line": 7,
                        "content": "Keep the boundary explicit.",
                        "severity": "low",
                        "category": "maintainability",
                    }
                ],
            ),
            ("complete", ["Synthetic warning."], "complete", {}, []),
            ("partial", [], "partial", {}, []),
            ("partial", [], "partial", {"budget_exceeded": True}, []),
            ("skipped", [], "skipped", {}, []),
            ("failed", [], "failed", {}, []),
        )
        for status, warnings, manifest_state, summary, comments in scenarios:
            with self.subTest(status=status, manifest_state=manifest_state):
                self._assert_unprotected_limitation_is_adjacent_once(
                    status, warnings, manifest_state, summary, comments
                )

    def _assert_unprotected_limitation_is_adjacent_once(
        self,
        status: str,
        warnings: list[str],
        manifest_state: str,
        summary: dict[str, bool],
        comments: list[dict[str, Any]],
    ) -> None:
        receipt = receipt_v7(target_protection="unprotected")
        if status in {"skipped", "failed"}:
            receipt["evidence"] = {
                "mandatory": False,
                "used": False,
                "calls": 0,
                "actions": {"state": "unavailable"},
            }
            receipt["mcp"]["usage"] = {}
        selected = (
            []
            if status == "skipped"
            else [{"item_id": "synthetic-a"}, {"item_id": "synthetic-b"}]
            if manifest_state == "partial"
            else [{"item_id": "synthetic-item"}]
        )
        completed = (
            selected
            if manifest_state == "complete"
            else selected[:1]
            if manifest_state == "partial"
            else []
        )
        failed = [] if manifest_state == "complete" else selected[-1:]
        if failed:
            failed = [
                {
                    **failed[0],
                    "classification": "budget" if summary else "provider",
                }
            ]
        result = {
            "status": status,
            "comments": comments,
            "warnings": warnings,
            "tool_calls": (
                {"total": 0, "by_tool": {}}
                if status in {"skipped", "failed"}
                else {"total": 1, "by_tool": {"ocr_toolkit_evidence": 1}}
            ),
            "manifest": {
                "schema_version": "ocr.run-manifest/v1",
                "operation": "review",
                "terminal_state": manifest_state,
                "coverage": {
                    "selected": selected,
                    "completed": completed,
                    "reused": [],
                    "failed": failed,
                    "waived": [],
                },
            },
            "_ocr_toolkit": receipt,
        }
        if summary:
            result["summary"] = summary
        notes: list[str] = []

        def capture(_config: Any, _title: str, body: str, *_args: Any) -> dict[str, int]:
            notes.append(body)
            return {"id": len(notes)}

        with (
            patched_attr(
                workflow, "collect_previous_bot_comment_refs", lambda _config: BotCommentRefs()
            ),
            patched_attr(workflow, "get_diff_refs", lambda _config: None),
            patched_attr(workflow, "post_review_note_bounded", capture),
            patched_attr(workflow, "finalize_posting", lambda *_args: True),
            patched_attr(workflow, "finalize_review_approval", lambda *_args, **_kwargs: 0),
        ):
            workflow.post_results(gitlab_config(), result)

        limitation = formatting.UNPROTECTED_TARGET_LIMITATION
        summary_note = next(note for note in notes if "## Open Code Review" in note)
        assert summary_note.count(limitation) == 1
        visible = summary_note.splitlines()
        status_index = next(index for index, line in enumerate(visible) if "**Review" in line)
        assert visible[status_index + 1] == limitation

    def test_unprotected_limitation_requires_fully_validated_v7_receipt(self) -> None:
        valid = receipt_v7(target_protection="unprotected")
        assert workflow.unprotected_target_limitation(valid)
        for candidate in (
            {**valid, "schema_version": 6},
            {**valid, "cleanup": {"result": "unknown"}},
            {**valid, "extra": True},
            receipt_v7(target_protection="unprotected", external=True),
        ):
            assert workflow.unprotected_target_limitation(candidate) is False

    def test_complete_filtered_review_keeps_coverage_and_activity_dimensions_separate(
        self,
    ) -> None:
        """Render scenario B without inventing partial coverage or a failed item."""

        receipt = receipt_v7(author_id=41, target_protection="unprotected")
        receipt["publication"] = {
            "state": "publication-filtered",
            "reason_counts": {
                "forbidden": 0,
                "invalid_text": 2,
                "laundering": 0,
                "limit": 0,
                "pii": 0,
                "secret": 0,
            },
            "retained": {"comments": 1, "warnings": 0},
            "omitted": {"comments": 0, "warnings": 0, "fields": 2},
            "original": {
                "outcome": "clean",
                "selected": 5,
                "completed": 5,
                "reused": 0,
                "failed": 0,
                "waived": 0,
            },
        }
        notes: list[tuple[str, str]] = []

        def capture_note(
            _config: Any,
            title: str,
            body: str,
            *_args: Any,
        ) -> dict[str, int]:
            notes.append((title, body))
            return {"id": len(notes)}

        with (
            patched_attr(
                workflow, "collect_previous_bot_comment_refs", lambda _config: BotCommentRefs()
            ),
            patched_attr(workflow, "get_diff_refs", lambda _config: None),
            patched_attr(workflow, "post_review_note_bounded", capture_note),
            patched_attr(workflow, "finalize_review_approval", lambda *_args, **_kwargs: 0),
        ):
            exit_code = workflow.post_results(
                gitlab_config(),
                {
                    "status": "completed_with_errors",
                    "message": "Publication policy produced a safe partial OCR result.",
                    "comments": [
                        {
                            "path": "src/example.py",
                            "line": 7,
                            "content": "Keep the validated branch.",
                            "severity": "low",
                            "category": "maintainability",
                        }
                    ],
                    "warnings": [],
                    "tool_calls": {"total": 2, "by_tool": {"file_read": 2}},
                    "usage": {"input_tokens": 40, "output_tokens": 8},
                    "_ocr_toolkit": receipt,
                    ocr_result.TOOLKIT_ADVISORY_KEY: ocr_result.toolkit_advisory_payload(
                        ocr_result.background_recommended_advisory(
                            actual=2_248,
                            recommended=2_000,
                        )
                    ),
                },
            )

        self.assertEqual(exit_code, 0)
        summary = next(body for title, body in notes if not title and "## Open Code Review" in body)
        self.assertIn("Review complete with publication filtering — 1 finding published", summary)
        visible = summary.splitlines()
        status_index = next(index for index, line in enumerate(visible) if "**Review" in line)
        self.assertEqual(visible[status_index + 1], formatting.UNPROTECTED_TARGET_LIMITATION)
        self.assertNotIn("Review incomplete", summary)
        self.assertNotIn("OCR reported partial coverage", summary)
        self.assertNotIn("failed item(s) had no safe", summary)
        self.assertIn("Coverage: selected 5; completed 5; reused 0; failed 0; waived 0.", summary)
        self.assertIn("The public projection changed", summary)
        self.assertNotIn("### Recommended focus areas", summary)
        self.assertIn("- all OCR tool calls: 2 total (`file_read`: 2)", summary)
        self.assertIn("- token usage: 48 total (input: 40, output: 8)", summary)
        self.assertIn("OCR core advisory: background 2248 characters", summary)
        self.assertIn("Automatic approval: `not eligible`", summary)

    def test_private_sanitized_review_keeps_tool_and_token_activity_visible(self) -> None:
        """Keep independent numeric activity lines after private-only sanitization."""

        receipt = receipt_v7(author_id=41)
        receipt["publication"] = {
            "state": "private-sanitized",
            "reason_counts": {
                "forbidden": 0,
                "invalid_text": 0,
                "laundering": 0,
                "limit": 0,
                "pii": 1,
                "secret": 0,
            },
            "sanitized_fields": 1,
        }
        notes: list[str] = []

        def capture_note(_config: Any, _title: str, body: str, *_args: Any) -> dict[str, int]:
            notes.append(body)
            return {"id": 1}

        with (
            patched_attr(
                workflow, "collect_previous_bot_comment_refs", lambda _config: BotCommentRefs()
            ),
            patched_attr(workflow, "post_review_note_bounded", capture_note),
            patched_attr(workflow, "finalize_review_approval", lambda *_args, **_kwargs: 0),
        ):
            exit_code = workflow.post_results(
                gitlab_config(),
                {
                    "status": "complete",
                    "comments": [],
                    "warnings": [],
                    "manifest": {
                        "schema_version": "ocr.run-manifest/v1",
                        "operation": "review",
                        "terminal_state": "complete",
                        "coverage": {
                            "selected": [{"item_id": "safe-item"}],
                            "completed": [{"item_id": "safe-item"}],
                            "reused": [],
                            "failed": [],
                            "waived": [],
                        },
                    },
                    "tool_calls": {"total": 3, "by_tool": {"file_read": 3}},
                    "usage": {"input_tokens": 20, "output_tokens": 4},
                    "_ocr_toolkit": receipt,
                },
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(notes), 1)
        self.assertIn("- all OCR tool calls: 3 total (`file_read`: 3)", notes[0])
        self.assertIn("- token usage: 24 total (input: 20, output: 4)", notes[0])
        self.assertIn("Private result sanitization signal", notes[0])

    def test_current_summary_readback_requires_one_owned_run_marker(self) -> None:
        body = build_marked_note_body(markers.build_summary_run_marker(self.RUN_ID) + "\nsummary")
        notes = [
            {"id": 9, "author": {"id": 7}, "body": body},
            {"id": 8, "author": {"id": 8}, "body": body},
        ]
        with patched_attr(gitlab, "api_get_paginated", lambda *_args, **_kwargs: notes):
            self.assertEqual(
                workflow.find_current_summary_note(gitlab_config(), self.RUN_ID),
                9,
            )

        notes.append({"id": 10, "author": {"id": 7}, "body": body})
        with patched_attr(gitlab, "api_get_paginated", lambda *_args, **_kwargs: notes):
            self.assertIsNone(workflow.find_current_summary_note(gitlab_config(), self.RUN_ID))

    def test_finalize_orders_publish_approval_summary_update_and_cleanup(self) -> None:
        calls: list[str] = []
        approved = gitlab_approval.ApprovalExecution(
            approval.ApprovalResult(
                approval.ApprovalStatus.APPROVED,
                "GitLab confirmed the toolkit user's exact-SHA approval",
            ),
        )

        def publish(*_args: Any) -> bool:
            calls.append("publish")
            return True

        def approve(*_args: Any, **_kwargs: Any) -> gitlab_approval.ApprovalExecution:
            calls.append("approve")
            return approved

        def update_summary(*_args: Any) -> bool:
            calls.append("summary")
            return True

        def cleanup(*_args: Any) -> None:
            calls.append("cleanup")

        with (
            patched_attr(workflow, "finalize_posting", publish),
            patched_attr(workflow, "execute_approval", approve),
            patched_attr(workflow, "replace_current_summary", update_summary),
            patched_attr(workflow, "finalize_previous_review_state", cleanup),
        ):
            exit_code = workflow.finalize_review_approval(
                gitlab_config(),
                BotCommentRefs(),
                complete_outcome(),
                [1],
                eligibility(),
                self.SHA,
                None,
                self.RUN_ID,
                lambda result: approval.approval_summary_line(result),
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls, ["publish", "approve", "summary", "cleanup"])

    def test_disabled_approval_does_not_rewrite_unchanged_summary(self) -> None:
        calls: list[str] = []
        decision = eligibility(setting=settings.BooleanSetting(False))

        def update_summary(*_args: Any) -> bool:
            calls.append("summary")
            return True

        with (
            patched_attr(workflow, "finalize_posting", lambda *_args: True),
            patched_attr(
                workflow,
                "execute_approval",
                lambda *_args, **_kwargs: gitlab_approval.ApprovalExecution(decision.result),
            ),
            patched_attr(workflow, "replace_current_summary", update_summary),
            patched_attr(workflow, "finalize_previous_review_state", lambda *_args: None),
        ):
            exit_code = workflow.finalize_review_approval(
                gitlab_config(),
                BotCommentRefs(),
                complete_outcome(),
                [],
                decision,
                self.SHA,
                None,
                self.RUN_ID,
                lambda result: approval.approval_summary_line(result),
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls, [])

    def test_unprotected_review_never_calls_approval_or_rewrites_summary(self) -> None:
        decision = approval.evaluate_approval_policy(
            settings.BooleanSetting(True),
            complete_outcome(),
            [],
            [],
            0,
            receipt_v7(target_protection="unprotected"),
        )
        calls: list[str] = []

        with (
            patched_attr(workflow, "finalize_posting", lambda *_args: True),
            patched_attr(
                workflow,
                "execute_approval",
                lambda *_args, **_kwargs: calls.append("approve"),
            ),
            patched_attr(
                workflow,
                "replace_current_summary",
                lambda *_args, **_kwargs: calls.append("summary") or True,
            ),
            patched_attr(workflow, "finalize_previous_review_state", lambda *_args: None),
        ):
            exit_code = workflow.finalize_review_approval(
                gitlab_config(),
                BotCommentRefs(),
                complete_outcome(),
                [],
                decision,
                self.SHA,
                41,
                self.RUN_ID,
                lambda result: approval.approval_summary_line(result),
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls, [])

    def test_approval_failure_is_nonfatal_unless_strict(self) -> None:
        failed = gitlab_approval.ApprovalExecution(
            approval.ApprovalResult(
                approval.ApprovalStatus.FAILED,
                "the GitLab approve result was not safely confirmed",
            )
        )
        for strict, expected in (("false", 0), ("true", 1)):
            with self.subTest(strict=strict), patched_env(OCR_STRICT_POSTING=strict):
                with (
                    patched_attr(workflow, "finalize_posting", lambda *_args: True),
                    patched_attr(
                        workflow,
                        "execute_approval",
                        lambda *_args, **_kwargs: failed,
                    ),
                    patched_attr(workflow, "replace_current_summary", lambda *_args: True),
                    patched_attr(
                        workflow,
                        "finalize_previous_review_state",
                        lambda *_args: None,
                    ),
                ):
                    exit_code = workflow.finalize_review_approval(
                        gitlab_config(),
                        BotCommentRefs(),
                        complete_outcome(),
                        [],
                        eligibility(),
                        self.SHA,
                        None,
                        self.RUN_ID,
                        lambda result: approval.approval_summary_line(result),
                    )
            self.assertEqual(exit_code, expected)

    def test_summary_update_failure_never_rolls_back_published_review(self) -> None:
        calls: list[str] = []
        failed = gitlab_approval.ApprovalExecution(
            approval.ApprovalResult(approval.ApprovalStatus.APPROVED, "confirmed")
        )

        def update_summary(*_args: Any) -> bool:
            calls.append("summary-failed")
            return False

        def cleanup(*_args: Any) -> None:
            calls.append("cleanup")

        with (
            patched_env(OCR_STRICT_POSTING="true"),
            patched_attr(workflow, "finalize_posting", lambda *_args: True),
            patched_attr(
                workflow,
                "execute_approval",
                lambda *_args, **_kwargs: failed,
            ),
            patched_attr(workflow, "replace_current_summary", update_summary),
            patched_attr(workflow, "finalize_previous_review_state", cleanup),
            redirect_stderr(io.StringIO()),
        ):
            exit_code = workflow.finalize_review_approval(
                gitlab_config(),
                BotCommentRefs(),
                complete_outcome(),
                [],
                eligibility(),
                self.SHA,
                None,
                self.RUN_ID,
                lambda result: approval.approval_summary_line(result),
            )

        self.assertEqual(exit_code, 1)
        self.assertEqual(calls, ["summary-failed", "cleanup"])

    def test_summary_renders_exactly_one_bounded_approval_state(self) -> None:
        rendered = formatting.summarize_result(
            total=0,
            inline_count=0,
            fallback_count=0,
            warning_count=0,
            approval_result=approval.ApprovalResult(
                approval.ApprovalStatus.NOT_ELIGIBLE,
                "the OCR review reported warnings",
            ),
            emoji=False,
        )

        self.assertEqual(rendered.count("Automatic approval:"), 1)
        self.assertIn("`not eligible`", rendered)


if __name__ == "__main__":
    unittest.main()
