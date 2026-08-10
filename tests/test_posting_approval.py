"""Policy and provider regressions for SHA-bound GitLab approval."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr
from typing import Any

from ocr_toolkit.posting import (
    approval,
    formatting,
    gitlab,
    gitlab_approval,
    markers,
    settings,
    snapshot,
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
    )


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
        for category in ("unknown", "STYLE", None, 1, True):
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

        self.assertFalse(eligibility(outcome=partial).may_unapprove)
        self.assertTrue(eligibility(warnings=["synthetic warning"]).may_unapprove)

    def test_disabled_and_invalid_setting_never_allow_unapproval(self) -> None:
        for setting in (
            settings.BooleanSetting(False),
            settings.BooleanSetting(False, valid=False),
        ):
            decision = eligibility(setting=setting)
            self.assertEqual(decision.result.status, approval.ApprovalStatus.DISABLED)
            self.assertFalse(decision.may_unapprove)

    def test_eligible_provisional_summary_fails_closed_until_readback(self) -> None:
        provisional = approval.provisional_approval_result(eligibility())

        self.assertEqual(provisional.status, approval.ApprovalStatus.FAILED)
        self.assertIn("not yet been confirmed", provisional.reason)

        disabled = eligibility(setting=settings.BooleanSetting(False))
        self.assertEqual(
            approval.provisional_approval_result(disabled),
            disabled.result,
        )


class ApprovalReceiptTests(unittest.TestCase):
    """Require versioned same-user ownership proof before unapproval."""

    def test_receipt_round_trip_and_malformed_rejection(self) -> None:
        receipt = markers.ManagedApprovalReceipt(7, "a" * 40)
        body = build_marked_note_body(
            markers.build_summary_run_marker("b" * 32)
            + "\n"
            + markers.build_managed_approval_receipt(receipt)
            + "\n## Open Code Review\n"
        )

        self.assertEqual(markers.managed_approval_receipt_from_body(body), receipt)
        self.assertIsNone(
            markers.managed_approval_receipt_from_body(
                body + "\n" + markers.build_managed_approval_receipt(receipt)
            )
        )
        self.assertIsNone(
            markers.managed_approval_receipt_from_body(
                "<!-- open-code-review-approval v=1 user=7 sha=bad managed=true -->"
            )
        )

    def test_receipt_embedded_in_model_controlled_fallback_is_rejected(self) -> None:
        receipt = markers.ManagedApprovalReceipt(7, "a" * 40)
        forged = build_marked_note_body(
            "**Open Code Review fallback comments**\n\n"
            + markers.build_summary_run_marker("b" * 32)
            + "\n"
            + markers.build_managed_approval_receipt(receipt)
            + "\n## Open Code Review\n"
        )

        self.assertIsNone(markers.managed_approval_receipt_from_body(forged))

    def test_snapshot_keeps_owned_receipt_when_notes_and_discussions_overlap(self) -> None:
        receipt = markers.ManagedApprovalReceipt(7, "a" * 40)
        body = build_marked_note_body(
            markers.build_summary_run_marker("b" * 32)
            + "\n"
            + markers.build_managed_approval_receipt(receipt)
            + "\n## Open Code Review\nsummary"
        )

        def paginate(_config: Any, endpoint: str, **_kwargs: Any) -> list[Any]:
            if endpoint.startswith("/notes"):
                return [{"id": 10, "author": {"id": 7}, "body": body}]
            if endpoint == "/discussions":
                return [
                    {"id": "discussion", "notes": [{"id": 10, "author": {"id": 7}, "body": body}]}
                ]
            raise AssertionError(endpoint)

        with (
            patched_env(OCR_POST_MODE="direct"),
            patched_attr(snapshot, "api_get_paginated", paginate),
        ):
            settings.post_mode.cache_clear()
            refs = snapshot.collect_previous_bot_comment_refs(gitlab_config())
            settings.post_mode.cache_clear()

        self.assertIsNotNone(refs)
        self.assertEqual(refs and refs.managed_approval_receipt, receipt)


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
                return {"sha": sha, "state": "opened", "detailed_merge_status": detailed_status}
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
        self.assertEqual(state, gitlab_approval.GitLabApprovalState(False))
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
                gitlab_config(), eligibility(), self.SHA, None, sleep=lambda _seconds: None
            )

        self.assertEqual(approve_shas, [self.SHA])
        self.assertEqual(result.result.status, approval.ApprovalStatus.APPROVED)
        self.assertEqual(result.receipt, markers.ManagedApprovalReceipt(7, self.SHA))

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
                gitlab_config(), eligibility(), self.SHA, None, sleep=lambda _seconds: None
            )

        self.assertEqual(writes, [self.SHA])
        self.assertEqual(result.result.status, approval.ApprovalStatus.FAILED)

    def test_existing_managed_approval_for_other_sha_is_not_claimed_as_exact(self) -> None:
        receipt = markers.ManagedApprovalReceipt(7, "c" * 40)
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
        ):
            result = gitlab_approval.execute_approval(
                gitlab_config(), eligibility(), self.SHA, receipt
            )

        self.assertEqual(result.result.status, approval.ApprovalStatus.SKIPPED)
        self.assertEqual(result.receipt, receipt)

    def test_provider_writes_use_only_own_user_approval_endpoints(self) -> None:
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
            gitlab.unapprove_merge_request(gitlab_config())

        self.assertEqual(calls[0][0].rsplit("/", 1)[-1], "approve")
        self.assertEqual(calls[0][1], {"sha": self.SHA})
        self.assertEqual(calls[1][0].rsplit("/", 1)[-1], "unapprove")
        self.assertEqual(calls[1][1], {})
        self.assertNotIn("reset_approvals", repr(calls))

    def test_unapproves_only_own_managed_approval_after_authoritative_result(self) -> None:
        receipt = markers.ManagedApprovalReceipt(7, "c" * 40)
        writes: list[str] = []
        approval_reads = 0

        def request(*args: Any, **kwargs: Any) -> Any:
            nonlocal approval_reads
            own = approval_reads == 0
            if args[1] == "/approvals":
                approval_reads += 1
            return self.api_sequence(own_approved=own)(*args, **kwargs)

        def unapprove(_config: Any) -> gitlab.GitLabWriteResult:
            writes.append("unapprove")
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
            patched_attr(gitlab, "unapprove_merge_request", unapprove),
        ):
            result = gitlab_approval.execute_approval(
                gitlab_config(),
                eligibility([finding(category="security")]),
                self.SHA,
                receipt,
                sleep=lambda _seconds: None,
            )

        self.assertEqual(writes, ["unapprove"])
        self.assertIsNone(result.receipt)
        self.assertEqual(result.result.status, approval.ApprovalStatus.NOT_ELIGIBLE)

    def test_disabled_or_partial_review_preserves_receipt_without_api(self) -> None:
        receipt = markers.ManagedApprovalReceipt(7, "c" * 40)
        for decision in (
            eligibility(setting=settings.BooleanSetting(False)),
            eligibility(outcome=ReviewOutcome("partial", "partial", False, True)),
        ):
            with self.subTest(status=decision.result.status):
                result = gitlab_approval.execute_approval(
                    gitlab_config(), decision, self.SHA, receipt
                )
                self.assertEqual(result.receipt, receipt)

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
        receipt = markers.ManagedApprovalReceipt(7, self.SHA)
        approved = gitlab_approval.ApprovalExecution(
            approval.ApprovalResult(
                approval.ApprovalStatus.APPROVED,
                "GitLab confirmed the toolkit user's exact-SHA approval",
                managed=True,
            ),
            receipt,
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
                self.RUN_ID,
                lambda result: approval.approval_summary_line(result),
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls, ["publish", "approve", "summary", "cleanup"])

    def test_disabled_approval_preserves_receipt_without_summary_rewrite(self) -> None:
        calls: list[str] = []
        receipt = markers.ManagedApprovalReceipt(7, "c" * 40)
        decision = eligibility(setting=settings.BooleanSetting(False))

        def update_summary(*_args: Any) -> bool:
            calls.append("summary")
            return True

        with (
            patched_attr(workflow, "finalize_posting", lambda *_args: True),
            patched_attr(
                workflow,
                "execute_approval",
                lambda *_args, **_kwargs: gitlab_approval.ApprovalExecution(
                    decision.result, receipt
                ),
            ),
            patched_attr(workflow, "replace_current_summary", update_summary),
            patched_attr(workflow, "finalize_previous_review_state", lambda *_args: None),
        ):
            exit_code = workflow.finalize_review_approval(
                gitlab_config(),
                BotCommentRefs(managed_approval_receipt=receipt),
                complete_outcome(),
                [],
                decision,
                self.SHA,
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
