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


def receipt_v5(
    *, context_state: str = "disabled", external: bool = False, author_id: int | None = 41
) -> dict[str, Any]:
    """Return one closed synthetic review-time receipt."""

    mode = "metadata" if context_state != "disabled" else "off"
    capabilities = [
        {
            "server": "ocr_toolkit_evidence",
            "transport": "builtin",
            "tools": ["ocr_toolkit_evidence"],
        }
    ]
    if external:
        capabilities.append(
            {"server": "documentation", "transport": "remote", "tools": ["docs_read"]}
        )
    return {
        "schema_version": 5,
        "review": {
            "source_sha": "a" * 40,
            "policy_sha": "b" * 40,
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
        "evidence": {"mandatory": True, "used": True, "calls": 1},
        "publication": {"state": "passed"},
        "cleanup": {"result": "passed"},
    }


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
        receipt_v5(),
    )


def enriched_receipt(*, mutable: bool = False, required_degraded: bool = False) -> dict[str, Any]:
    """Return one v5 local-store-only enrichment receipt."""

    receipt = receipt_v5()
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
            receipt_v5(context_state="degraded", author_id=41),
        )

        self.assertFalse(decision.eligible)
        self.assertEqual(decision.result.status, approval.ApprovalStatus.NOT_ELIGIBLE)
        self.assertEqual(decision.result.reason, "the selected review context was degraded")

    def test_publication_dlp_filtered_receipt_is_valid_but_never_eligible(self) -> None:
        receipt = receipt_v5()
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

    def test_private_only_sanitization_keeps_existing_approval_gates(self) -> None:
        receipt = receipt_v5()
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

    def test_complete_metadata_and_external_mcp_have_independent_approval_effects(self) -> None:
        complete_metadata = approval.evaluate_approval_policy(
            settings.BooleanSetting(True),
            complete_outcome(),
            [],
            [],
            0,
            receipt_v5(context_state="complete", author_id=41),
        )
        external = approval.evaluate_approval_policy(
            settings.BooleanSetting(True), complete_outcome(), [], [], 0, receipt_v5(external=True)
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
        metadata = receipt_v5(external=True)
        metadata["mcp"]["capabilities"][1]["tools"] = ["repo.search", "records/read"]

        decision = approval.evaluate_approval_policy(
            settings.BooleanSetting(True), complete_outcome(), [], [], 0, metadata
        )

        self.assertFalse(decision.eligible)
        self.assertEqual(
            decision.result.reason,
            "external MCP was configured for a comment-only review",
        )

    def test_every_pre_v5_receipt_is_rejected(self) -> None:
        for version in range(1, 5):
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

    def test_missing_or_malformed_v5_receipt_fails_closed(self) -> None:
        cases: list[Any] = [None, {"schema_version": 5}]
        for mutate in (
            lambda value: value["context"].update({"state": "complete"}),
            lambda value: value["review"].update({"source_sha": "invalid"}),
            lambda value: value["mcp"].update({"usage": {"unknown": 1}}),
            lambda value: value["evidence"].update({"used": False}),
        ):
            candidate = receipt_v5()
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

    def test_impossible_v5_capability_and_evidence_states_fail_closed(self) -> None:
        cases: list[dict[str, Any]] = []

        builtin_remote = receipt_v5()
        builtin_remote["mcp"]["capabilities"][0]["transport"] = "remote"
        cases.append(builtin_remote)

        external_builtin = receipt_v5(external=True)
        external_builtin["mcp"]["capabilities"][1]["transport"] = "builtin"
        cases.append(external_builtin)

        wrong_builtin_tool = receipt_v5()
        wrong_builtin_tool["mcp"]["capabilities"][0]["tools"] = ["other_read"]
        cases.append(wrong_builtin_tool)

        duplicate_tool = receipt_v5(external=True)
        duplicate_tool["mcp"]["capabilities"][1]["tools"] = ["ocr_toolkit_evidence"]
        cases.append(duplicate_tool)

        too_many_tools = receipt_v5(external=True)
        too_many_tools["mcp"]["capabilities"][1]["tools"] = [
            f"tool_{index}" for index in range(129)
        ]
        cases.append(too_many_tools)

        usage_mismatch = receipt_v5()
        usage_mismatch["mcp"]["usage"] = {}
        cases.append(usage_mismatch)

        usage_overflow = receipt_v5()
        usage_overflow["mcp"]["usage"] = {"ocr_toolkit_evidence": 1_000_000_001}
        cases.append(usage_overflow)

        missing_author = receipt_v5(author_id=None)
        cases.append(missing_author)

        mandatory_mismatch = receipt_v5()
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
        valid = receipt_v5(author_id=41)
        self.assertEqual(workflow.approval_receipt_identity(valid), ("a" * 40, 41))

        for mutate in (
            lambda value: value["review"].update({"source_sha": "invalid"}),
            lambda value: value["review"].update({"mr_author_id": None}),
            lambda value: value["review"].update({"mr_author_id": True}),
        ):
            candidate = receipt_v5(author_id=41)
            mutate(candidate)
            with self.subTest(candidate=candidate):
                self.assertEqual(workflow.approval_receipt_identity(candidate), ("", None))

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
