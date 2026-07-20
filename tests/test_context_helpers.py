"""Thematic OCR CI regression tests."""

from __future__ import annotations

import ast
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from ocr_toolkit.common.markdown import open_markdown_fence
from ocr_toolkit.context import ansible as context_ansible
from ocr_toolkit.context import categorize as context_categorize
from ocr_toolkit.context import instructions as context_instructions
from ocr_toolkit.context import manifests as context_manifests
from ocr_toolkit.context import planner as context_planner
from ocr_toolkit.context import render as context_render
from ocr_toolkit.context import repo as context_repo
from ocr_toolkit.context import settings as context_settings
from ocr_toolkit.posting import result
from ocr_toolkit.posting.formatting import truncate_note_body
from tests.support import (
    HELPER_DIR,
    cleared_env,
    patched_attr,
    patched_env,
    patched_root,
)


class InventoryTopologyTests(unittest.TestCase):
    def test_ini_group_suffixes_are_not_part_of_group_name(self) -> None:
        from ocr_toolkit.context.ansible import extract_inventory_topology

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inventory = root / "inventory.ini"
            inventory.write_text(
                "[web:children]\nblue\n[db:vars]\nansible_user=root\n[plain]\nhost1\n",
                encoding="utf-8",
            )

            with patched_root(root):
                items = extract_inventory_topology(["inventory.ini"])

        self.assertIn("web", items)
        self.assertIn("db", items)
        self.assertIn("plain", items)
        self.assertNotIn("web:children", items)


class AnsiblePlaybookDetectionTests(unittest.TestCase):
    def test_nested_hosts_key_does_not_make_root_yaml_a_playbook(self) -> None:
        from ocr_toolkit.context.ansible import is_root_ansible_playbook

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "not_playbook.yml").write_text(
                "- name: data\n  tasks:\n    - name: nested\n      vars:\n        hosts: not-a-play\n",
                encoding="utf-8",
            )
            (root / "playbook.yml").write_text(
                "- name: deploy\n  hosts: app\n  tasks: []\n",
                encoding="utf-8",
            )

            with patched_root(root):
                self.assertFalse(is_root_ansible_playbook("not_playbook.yml"))
                self.assertTrue(is_root_ansible_playbook("playbook.yml"))


class GuidanceTrustTests(unittest.TestCase):
    def test_keyword_window_bounds_both_sides_on_one_long_line(self) -> None:
        text = "a" * 2_000 + " security " + "b" * 2_000

        excerpt = context_instructions._keyword_window(text, radius=100)

        self.assertLessEqual(len(excerpt), 200)
        self.assertIn("security", excerpt)
        self.assertNotIn("a" * 500, excerpt)

    def test_keyword_window_uses_original_text_offsets(self) -> None:
        text = "ß" * 2_000 + "\nSecurity must validate input.\n" + "x" * 800

        excerpt = context_instructions.selected_instruction_excerpt(
            "AGENTS.md", text, max_bytes=900
        )

        self.assertIn("Security must validate input", excerpt)

    def test_parent_symlink_instruction_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside = root / "outside"
            outside.mkdir()
            (outside / "copilot-instructions.md").write_text("secret", encoding="utf-8")
            (root / ".github").symlink_to(outside, target_is_directory=True)

            with patched_root(root):
                instructions = context_instructions.read_project_instructions(changed_paths=[])

        self.assertEqual(instructions, [])

    def test_regular_untracked_agents_file_is_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("local guidance", encoding="utf-8")

            with patched_root(root):
                instructions = context_instructions.read_project_instructions(changed_paths=[])

        self.assertEqual(len(instructions), 1)
        self.assertEqual(instructions[0][0], "AGENTS.md")
        self.assertIn("local guidance", instructions[0][1])

    def test_changed_instruction_paths_are_compared_case_insensitively(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("changed guidance", encoding="utf-8")

            with patched_root(root):
                instructions = context_instructions.read_project_instructions(
                    changed_paths=["agents.md"]
                )

        self.assertEqual(instructions, [])

    def test_guidance_text_is_redacted_before_background_use(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text(
                "Authorization: Bearer test-redaction-token", encoding="utf-8"
            )
            ocr_dir = root / ".opencodereview"
            ocr_dir.mkdir()
            (ocr_dir / "accepted-decisions.md").write_text(
                "password=test-redaction-password", encoding="utf-8"
            )

            with patched_root(root):
                instructions = context_instructions.read_project_instructions(changed_paths=[])
                decisions = context_instructions.read_accepted_decisions(changed_paths=[])

        self.assertNotIn("test-redaction-token", instructions[0][1])
        self.assertNotIn("test-redaction-password", decisions)

    def test_guidance_url_userinfo_is_redacted_in_background(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text(
                "Use https://user:pass@example.com/guide", encoding="utf-8"
            )
            ocr_dir = root / ".opencodereview"
            ocr_dir.mkdir()
            (ocr_dir / "accepted-decisions.md").write_text(
                "Accepted https://user:token@example.com/repo", encoding="utf-8"
            )

            with patched_root(root):
                with patched_attr(context_repo, "changed_files", lambda: []):
                    background = context_render.build_context()

        self.assertNotIn("user:pass", background)
        self.assertNotIn("user:token", background)
        self.assertIn("https://***@example.com/guide", background)
        self.assertIn("https://***@example.com/repo", background)

    def test_guidance_reader_redacts_url_userinfo_before_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text(
                "Use https://user:pass@example.com/guide", encoding="utf-8"
            )

            with patched_root(root):
                instructions = context_instructions.read_project_instructions(changed_paths=[])

        self.assertNotIn("user:pass", instructions[0][1])
        self.assertIn("https://***@example.com/guide", instructions[0][1])

    def test_instruction_sections_can_be_found_after_output_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text(
                "# Repository Guidelines\nkeep root guidance\n"
                + ("filler\n" * 80)
                + "### OCR CI Review\nkeep late ocr review guidance\n",
                encoding="utf-8",
            )

            with (
                patched_root(root),
                patched_attr(
                    context_repo,
                    "LOCAL_GUIDANCE_STATUS_PATHS",
                    frozenset({"AGENTS.md"}),
                ),
            ):
                instructions = context_instructions.read_project_instructions(
                    limit_bytes=150,
                    changed_paths=[],
                )

        self.assertEqual(instructions[0][0], "AGENTS.md")
        self.assertIn("Repository Guidelines", instructions[0][1])
        self.assertIn("ocr review", instructions[0][1].lower())

    def test_instruction_excerpt_handles_agents_without_headings(self) -> None:
        text = (
            "intro\n\n"
            + ("filler\n" * 80)
            + "OCR CI must redact token values before GitLab posting.\n"
        )

        excerpt = context_instructions.selected_instruction_excerpt(
            "AGENTS.md", text, max_bytes=140
        )

        self.assertIn("intro", excerpt)
        self.assertIn("redact token", excerpt)

    def test_instruction_excerpt_without_relevant_keywords_uses_full_budget(self) -> None:
        text = "intro\n" + ("general guidance\n" * 80)

        excerpt = context_instructions.selected_instruction_excerpt(
            "AGENTS.md", text, max_bytes=220
        )

        self.assertGreater(len(excerpt), 150)
        self.assertIn("general guidance", excerpt)

    def test_guidance_score_does_not_match_short_keywords_inside_words(self) -> None:
        text = "# configuration\nspecific decision content only\n" + ("filler\n" * 40)

        excerpt = context_instructions.selected_instruction_excerpt(
            "AGENTS.md", text, max_bytes=180
        )

        self.assertIn("configuration", excerpt)
        self.assertNotIn("---", excerpt)

    def test_instruction_excerpt_uses_keyword_window_inside_long_heading_sections(self) -> None:
        text = "# Guide\n" + ("filler\n" * 80) + "OCR CI must preserve token redaction.\n"

        excerpt = context_instructions.selected_instruction_excerpt(
            "AGENTS.md", text, max_bytes=160
        )

        self.assertIn("token redaction", excerpt)


class ContextChangedFilesTests(unittest.TestCase):
    def test_output_path_rejects_symlinked_file_and_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside = root / "outside.txt"
            outside.write_text("safe", encoding="utf-8")
            (root / "context.md").symlink_to(outside)
            (root / "linked").symlink_to(root, target_is_directory=True)

            with patched_root(root):
                self.assertIsNone(context_repo.resolve_output_path("context.md"))
                self.assertIsNone(context_repo.resolve_output_path("linked/context.md"))
                self.assertEqual(
                    context_repo.resolve_output_path("new/context.md"),
                    (root / "new/context.md").resolve(),
                )
                self.assertEqual(
                    context_repo.resolve_output_path("/tmp/ocr-context.md"),
                    Path("/tmp/ocr-context.md").resolve(),
                )
                canonical_tmp = Path("/tmp").resolve() / "ocr-context.md"
                self.assertEqual(
                    context_repo.resolve_output_path(str(canonical_tmp)),
                    canonical_tmp,
                )

    def test_changed_files_prefers_source_branch_sha(self) -> None:
        calls: list[list[str]] = []

        def fake_run_command(cmd: list[str], timeout: int = 10) -> context_repo.CommandResult:
            calls.append(cmd)
            if cmd[:3] == ["git", "merge-base", "origin/main"]:
                return context_repo.CommandResult("base\n", "", 0)
            if cmd[:3] == ["git", "diff", "--name-only"]:
                return context_repo.CommandResult("file.py\0", "", 0)
            return context_repo.CommandResult("", "", 1)

        with (
            cleared_env("CI_MERGE_REQUEST_DIFF_BASE_SHA"),
            patched_env(
                CI_MERGE_REQUEST_TARGET_BRANCH_NAME="main",
                CI_MERGE_REQUEST_SOURCE_BRANCH_SHA="source-sha",
                CI_COMMIT_SHA="synthetic-sha",
            ),
            patched_attr(context_repo, "run_command", fake_run_command),
        ):
            files = context_repo.changed_files()

        self.assertEqual(files, ["file.py"])
        self.assertIn(["git", "merge-base", "origin/main", "source-sha"], calls)
        self.assertIn(["git", "diff", "--name-only", "-z", "base", "source-sha"], calls)
        self.assertNotIn(["git", "merge-base", "origin/main", "synthetic-sha"], calls)

    def test_background_mentions_source_sha_when_pipeline_sha_is_synthetic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patched_root(root), cleared_env("CI_MERGE_REQUEST_DIFF_BASE_SHA"):
                with patched_env(
                    CI_MERGE_REQUEST_TARGET_BRANCH_NAME="main",
                    CI_MERGE_REQUEST_SOURCE_BRANCH_NAME="feature",
                    CI_MERGE_REQUEST_SOURCE_BRANCH_SHA="source-sha",
                    CI_COMMIT_SHA="synthetic-sha",
                ):
                    with patched_attr(context_repo, "changed_files", lambda: []):
                        background = context_render.build_context()

        self.assertIn("- Source commit SHA: `source-sha`", background)
        self.assertIn("- Pipeline commit SHA: `synthetic-sha`", background)

    def test_merged_result_without_source_sha_fails_closed(self) -> None:
        calls: list[list[str]] = []

        def fake_run_command(cmd: list[str], timeout: int = 10) -> context_repo.CommandResult:
            calls.append(cmd)
            return context_repo.CommandResult("", "", 0)

        with redirect_stderr(io.StringIO()):
            with patched_attr(context_repo, "run_command", fake_run_command):
                with cleared_env("CI_MERGE_REQUEST_SOURCE_BRANCH_SHA"):
                    with patched_env(
                        CI_MERGE_REQUEST_EVENT_TYPE="merged_result",
                        CI_MERGE_REQUEST_TARGET_BRANCH_NAME="main",
                        CI_COMMIT_SHA="synthetic-sha",
                    ):
                        self.assertIsNone(context_repo.changed_files())

        self.assertEqual(calls, [])

    def test_local_changed_files_includes_only_untracked_guidance(self) -> None:
        def fake_run_command(cmd: list[str], timeout: int = 10) -> context_repo.CommandResult:
            if cmd[:2] == ["git", "symbolic-ref"]:
                return context_repo.CommandResult("origin/main\n", "", 0)
            if cmd[:3] == ["git", "merge-base", "origin/main"]:
                return context_repo.CommandResult("base\n", "", 0)
            if cmd[:3] == ["git", "diff", "--name-only"]:
                return context_repo.CommandResult("tracked.py\0", "", 0)
            if cmd[:3] == ["git", "status", "--porcelain=v1"]:
                return context_repo.CommandResult(
                    "?? AGENTS.md\0?? .env-test\0?? docs/test_lab/case.yml\0",
                    "",
                    0,
                )
            return context_repo.CommandResult("", "", 1)

        with (
            cleared_env(
                "CI_MERGE_REQUEST_TARGET_BRANCH_NAME",
                "CI_MERGE_REQUEST_SOURCE_BRANCH_SHA",
                "CI_COMMIT_SHA",
            ),
            patched_attr(context_repo, "run_command", fake_run_command),
        ):
            with redirect_stderr(io.StringIO()):
                files = context_repo.local_changed_files()

        self.assertEqual(files, ["tracked.py", "AGENTS.md"])

    def test_git_status_parser_prefers_new_rename_path(self) -> None:
        result = context_repo.CommandResult(
            "R  AGENTS.md\0OLD_AGENTS.md\0C  CLAUDE.md\0OLD_CLAUDE.md\0",
            "",
            0,
        )

        self.assertEqual(
            context_repo.parse_git_status_porcelain_output(result),
            ["AGENTS.md", "CLAUDE.md"],
        )

    def test_untracked_local_guidance_is_not_used_for_own_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("local guidance", encoding="utf-8")

            with patched_root(root):
                with patched_attr(context_repo, "changed_files", lambda: ["AGENTS.md"]):
                    background = context_render.build_context()

        self.assertNotIn("## Project instruction files", background)
        self.assertNotIn("local guidance", background)


class ManifestParsingTests(unittest.TestCase):
    def test_go_mod_ignores_comments_inside_require_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            go_mod = root / "go.mod"
            go_mod.write_text(
                "module example\n\ngo 1.22\nrequire (\n  // keep comment\n  example.com/lib v1.2.3\n)\n",
                encoding="utf-8",
            )

            with patched_root(root):
                parsed = context_manifests.parse_go_mod(go_mod)

        self.assertEqual(parsed["modules"], ["example.com/lib v1.2.3"])
        self.assertEqual(parsed["modules_omitted"], 0)

    def test_manifest_parsers_report_omitted_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            requirements = root / "requirements.txt"
            requirements.write_text(
                "\n".join(f"pkg{i}==1.{i}" for i in range(5)),
                encoding="utf-8",
            )
            go_mod = root / "go.mod"
            go_mod.write_text(
                "module example\nrequire (\n"
                + "\n".join(f"  example.com/lib{i} v1.0.{i}" for i in range(5))
                + "\n)\n",
                encoding="utf-8",
            )
            composer_lock = root / "composer.lock"
            composer_lock.write_text(
                json.dumps(
                    {
                        "packages": [
                            {"name": f"vendor/pkg{i}", "version": f"1.0.{i}"} for i in range(5)
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with patched_root(root):
                parsed_requirements = context_manifests.parse_requirements_txt(
                    requirements, limit=2
                )
                with patched_attr(context_manifests, "MAX_BACKGROUND_SECTION_ITEMS", 2):
                    parsed_go = context_manifests.parse_go_mod(go_mod)
                    parsed_lock = context_manifests.parse_composer_lock(composer_lock)

        self.assertEqual(parsed_requirements["dependencies"], ["pkg0==1.0", "pkg1==1.1"])
        self.assertEqual(parsed_requirements["dependencies_omitted"], 3)
        self.assertEqual(len(parsed_go["modules"]), 2)
        self.assertEqual(parsed_go["modules_omitted"], 3)
        self.assertEqual(len(parsed_lock["packages"]), 2)
        self.assertEqual(parsed_lock["packages_omitted"], 3)

    def test_requirements_txt_keeps_unpinned_direct_and_include_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            requirements = root / "requirements.txt"
            requirements.write_text(
                "\n".join(
                    [
                        "--index-url https://example.invalid/simple",
                        "-r base.txt",
                        "--constraint constraints.txt",
                        "plain-package",
                        "pkg @ https://user:token@example.com/pkg.whl",
                        "editable-package>=1",
                    ]
                ),
                encoding="utf-8",
            )

            with patched_root(root):
                parsed = context_manifests.parse_requirements_txt(requirements)

        self.assertEqual(
            parsed["dependencies"],
            [
                "-r base.txt",
                "--constraint constraints.txt",
                "plain-package",
                "pkg @ https://***@example.com/pkg.whl",
                "editable-package>=1",
            ],
        )

    def test_large_json_manifest_returns_explicit_parse_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_json = root / "package.json"
            package_json.write_text('{"dependencies": {"a": "1"}}', encoding="utf-8")

            with patched_root(root), patched_env(OCR_MANIFEST_PARSE_MAX_BYTES="1"):
                parsed = context_manifests.parse_package_json(package_json)

        self.assertIn("OCR_MANIFEST_PARSE_MAX_BYTES", parsed["parse_error"])

    def test_repo_read_text_reads_only_requested_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            large = root / "large.txt"
            large.write_text("abcdef", encoding="utf-8")

            with patched_root(root):
                text = context_repo.read_text(large, max_bytes=3)

        self.assertIn("abc", text)
        self.assertIn("truncated", text)

    def test_repo_read_text_zero_budget_has_no_truncation_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            large = root / "large.txt"
            large.write_text("abcdef", encoding="utf-8")

            with patched_root(root):
                text = context_repo.read_text(large, max_bytes=0)

        self.assertEqual(text, "")

    def test_discover_pyproject_matches_only_basename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = root / "services" / "api"
            service.mkdir(parents=True)
            (service / "not_pyproject.toml").write_text("[project]", encoding="utf-8")
            (service / "pyproject.toml").write_text("[project]", encoding="utf-8")

            with patched_root(root):
                discovered = context_manifests.discover_pyproject_paths(
                    ["services/api/not_pyproject.toml", "services/api/pyproject.toml"]
                )

        self.assertEqual(discovered.paths, ["services/api/pyproject.toml"])
        self.assertEqual(discovered.omitted, 0)

    def test_discover_package_json_finds_nested_changed_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = root / "services" / "web"
            service.mkdir(parents=True)
            (service / "package.json").write_text('{"engines": {"node": ">=20"}}', encoding="utf-8")

            with patched_root(root):
                discovered = context_manifests.discover_package_json_paths(
                    ["services/web/src/app.ts", "services/web/package.json"]
                )

        self.assertEqual(discovered.paths, ["services/web/package.json"])
        self.assertEqual(discovered.omitted, 0)

    def test_discover_package_json_limit_returns_discovery_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("a", "b"):
                package_dir = root / name
                package_dir.mkdir()
                (package_dir / "package.json").write_text("{}", encoding="utf-8")

            with patched_root(root):
                discovered = context_manifests.discover_package_json_paths(
                    ["a/package.json", "b/package.json"],
                    limit=1,
                )

        self.assertEqual(discovered.paths, ["a/package.json"])
        self.assertEqual(discovered.omitted, 1)

    def test_application_version_discovery_prunes_fixture_dirs_before_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index in range(100):
                chart = root / "tests" / f"fixture-{index}" / "Chart.yaml"
                chart.parent.mkdir(parents=True)
                chart.write_text("appVersion: 0.0.1\n", encoding="utf-8")
            real_chart = root / "deploy" / "Chart.yaml"
            real_chart.parent.mkdir()
            real_chart.write_text("appVersion: 2.4.6\n", encoding="utf-8")

            with patched_root(root):
                versions = context_ansible.extract_application_versions([])

        self.assertIn("deploy/Chart.yaml: appVersion=2.4.6", versions)
        self.assertFalse(any("fixture" in item for item in versions))

    def test_application_version_discovery_is_global_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index in range(90):
                manifest = root / "collections" / f"item-{index:03d}" / "defaults" / "main.yml"
                manifest.parent.mkdir(parents=True)
                manifest.write_text("item_version: 1.0.0\n", encoding="utf-8")
            target = root / "roles" / "service" / "defaults" / "main.yml"
            target.parent.mkdir(parents=True)
            target.write_text("service_version: 2.4.6\n", encoding="utf-8")

            with patched_root(root):
                versions = context_ansible.extract_application_versions([], limit=160)

        self.assertIn("roles/service/defaults/main.yml: service_version=2.4.6", versions)

    def test_application_version_discovery_skips_changed_fixture_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture_chart = root / "tests" / "fixture" / "Chart.yaml"
            fixture_chart.parent.mkdir(parents=True)
            fixture_chart.write_text("appVersion: 0.0.1\n", encoding="utf-8")

            with patched_root(root):
                versions = context_ansible.extract_application_versions(
                    ["tests/fixture/Chart.yaml"]
                )

        self.assertEqual(versions, [])

    def test_manifest_discovery_reports_omitted_unique_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("a", "b", "c"):
                package_dir = root / name
                package_dir.mkdir()
                (package_dir / "package.json").write_text("{}", encoding="utf-8")

            with patched_root(root):
                discovered = context_manifests.discover_package_json_paths(
                    ["a/index.ts", "b/index.ts", "c/index.ts", "c/package.json"],
                    limit=2,
                )

        self.assertEqual(discovered.paths, ["c/package.json", "a/package.json"])
        self.assertEqual(discovered.omitted, 1)

    def test_pyproject_omitted_deduplicates_repeated_overflow_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("a", "b"):
                package_dir = root / name
                package_dir.mkdir()
                (package_dir / "pyproject.toml").write_text("[project]", encoding="utf-8")

            with patched_root(root):
                discovered = context_manifests.discover_pyproject_paths(
                    ["a/one.py", "b/one.py", "b/two.py", "b/pyproject.toml"],
                    limit=1,
                )

        self.assertEqual(discovered.paths, ["b/pyproject.toml"])
        self.assertEqual(discovered.omitted, 1)

    def test_large_requirements_and_go_mod_surface_parse_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            requirements = root / "requirements.txt"
            go_mod = root / "go.mod"
            requirements.write_text("package==1.0\n", encoding="utf-8")
            go_mod.write_text("module example.com/app\n", encoding="utf-8")

            with patched_root(root), patched_env(OCR_MANIFEST_PARSE_MAX_BYTES="1"):
                reqs = context_manifests.parse_requirements_txt(requirements)
                parsed_go = context_manifests.parse_go_mod(go_mod)

        self.assertIn("parse_error", reqs)
        self.assertIn("parse_error", parsed_go)

    def test_ansible_requirement_parser_resets_stale_name_between_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reqs = root / "requirements.yml"
            reqs.write_text(
                "roles:\n  - name: old.role\n  - src: https://example.com/new.git\n    version: v2\n",
                encoding="utf-8",
            )

            with patched_root(root):
                parsed = context_render.parse_ansible_requirements(reqs)
                pins = context_render.parse_ansible_requirement_version_pins(reqs)

        self.assertEqual(parsed, ["old.role", "https://example.com/new.git: v2"])
        self.assertEqual(pins, ["requirements.yml: https://example.com/new.git=v2"])

    def test_ansible_requirement_parser_resets_stale_name_under_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reqs = root / "requirements.yml"
            reqs.write_text(
                "collections:\n  - name: old.collection\n  - source: https://example.com/new.git\n    version: main\n",
                encoding="utf-8",
            )

            with patched_root(root):
                parsed = context_render.parse_ansible_requirements(reqs)
                pins = context_render.parse_ansible_requirement_version_pins(reqs)

        self.assertEqual(parsed, ["old.collection"])
        self.assertEqual(pins, [])

    def test_ansible_requirement_parser_keeps_name_for_nested_lists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reqs = root / "requirements.yml"
            reqs.write_text(
                "- name: signed.role\n  signatures:\n    - abc\n  version: v1\n",
                encoding="utf-8",
            )

            with patched_root(root):
                pins = context_render.parse_ansible_requirement_version_pins(reqs)

        self.assertEqual(pins, ["requirements.yml: signed.role=v1"])

    def test_ansible_requirement_parser_does_not_overwrite_item_indent_for_child_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reqs = root / "requirements.yml"
            reqs.write_text(
                "roles:\n"
                "  - src: https://example.com/first.git\n"
                "    name: first.role\n"
                "  - src: https://example.com/second.git\n"
                "    version: main\n",
                encoding="utf-8",
            )

            with patched_root(root):
                parsed = context_render.parse_ansible_requirements(reqs)
                pins = context_render.parse_ansible_requirement_version_pins(reqs)

        self.assertEqual(parsed, ["first.role", "https://example.com/second.git: main"])
        self.assertEqual(pins, ["requirements.yml: https://example.com/second.git=main"])

    def test_large_pyproject_returns_explicit_parse_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pyproject = root / "pyproject.toml"
            pyproject.write_text("[project]\nname = 'x'\n", encoding="utf-8")

            with patched_root(root), patched_env(OCR_MANIFEST_PARSE_MAX_BYTES="1"):
                parsed = context_manifests.parse_pyproject(pyproject)

        self.assertIn("OCR_MANIFEST_PARSE_MAX_BYTES", parsed["parse_error"])

    def test_pyproject_relative_heading_uses_inline_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pkg = root / "services" / "api"
            pkg.mkdir(parents=True)
            (pkg / "pyproject.toml").write_text(
                "[project]\nname = 'x'\ndependencies = ['a==1']\n", encoding="utf-8"
            )

            with (
                patched_root(root),
                patched_attr(
                    context_repo,
                    "changed_files",
                    lambda: ["services/api/app.py"],
                ),
            ):
                background = context_render.build_context()

        self.assertIn("(`services/api/pyproject.toml`)", background)
        self.assertNotIn("(services/api/pyproject.toml)", background)

    def test_composer_and_package_outputs_are_limited_by_parser_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            composer = root / "composer.json"
            package = root / "package.json"
            composer.write_text(
                json.dumps({"require": {f"pkg{i}": "1" for i in range(200)}}),
                encoding="utf-8",
            )
            package.write_text(
                json.dumps({"dependencies": {f"pkg{i}": "1" for i in range(200)}}),
                encoding="utf-8",
            )

            with patched_root(root):
                composer_parsed = context_manifests.parse_composer_json(composer)
                package_parsed = context_manifests.parse_package_json(package)

        self.assertEqual(
            len(composer_parsed["require"]), context_settings.MAX_BACKGROUND_SECTION_ITEMS
        )
        self.assertEqual(composer_parsed["require_omitted"], 80)
        self.assertEqual(
            len(package_parsed["dependencies"]), context_settings.MAX_BACKGROUND_SECTION_ITEMS
        )
        self.assertEqual(package_parsed["dependencies_omitted"], 80)

    def test_manifest_rendering_reports_real_omitted_count_once(self) -> None:
        rendered = context_render.format_manifest_items(
            [f"pkg{i}: 1" for i in range(120)], omitted=80, limit=100
        )

        self.assertIn("- ... and 100 more", rendered)
        self.assertEqual(rendered.count("... and"), 1)

    def test_requirements_rendering_uses_shared_dependency_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index in range(3):
                (root / f"requirements-{index}.txt").write_text(
                    "\n".join(f"pkg{index}_{item}==1.{item}" for item in range(60)),
                    encoding="utf-8",
                )

            with (
                patched_root(root),
                patched_attr(
                    context_repo,
                    "changed_files",
                    lambda: [f"requirements-{index}.txt" for index in range(3)],
                ),
            ):
                background = context_render.build_context()

        self.assertLessEqual(background.count("==1."), 100)
        self.assertIn("- ... and 1 requirements file(s) omitted", background)
        self.assertNotIn("requirements-style dependencies (`requirements-2.txt`)", background)

    def test_requirements_path_cap_reports_omitted_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            changed = []
            for index in range(32):
                path = f"requirements-{index:02d}.txt"
                (root / path).write_text("package==1.0\n", encoding="utf-8")
                changed.append(path)

            with (
                patched_root(root),
                patched_attr(context_repo, "changed_files", lambda: changed),
            ):
                background = context_render.build_context()

        self.assertIn("- ... and 2 requirements file(s) omitted", background)


class ApplicationVersionExtractionTests(unittest.TestCase):
    def test_application_version_extracts_nested_ci_image_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ci = root / "pipeline.yml"
            ci.write_text(
                "default:\n  image:\n    name: registry.example/python:3.12-slim\nmetadata:\n  name: not-an-image\n",
                encoding="utf-8",
            )

            with patched_root(root):
                versions = context_ansible.extract_application_versions(
                    ["pipeline.yml"], include_discovered=False
                )

        self.assertEqual(
            versions,
            ["pipeline.yml: image=registry.example/python:3.12-slim"],
        )

    def test_application_version_extracts_nested_repository_tag_and_digest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            values = root / "values.yaml"
            values.write_text(
                "worker:\n  image:\n    repository: registry.example/worker\n\n    # pinned release\n    tag: 4.2.1\napi:\n  image:\n    repository: registry.example/api\n    digest: sha256:abc123\n",
                encoding="utf-8",
            )

            with patched_root(root):
                versions = context_ansible.extract_application_versions(
                    ["values.yaml"], include_discovered=False
                )

        self.assertEqual(
            versions,
            [
                "values.yaml: image=registry.example/worker:4.2.1",
                "values.yaml: image=registry.example/api@sha256:abc123",
            ],
        )

    def test_application_version_extraction_is_product_agnostic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "deployment.yaml"
            manifest.write_text("acme_widget_version: 4.2.1\n", encoding="utf-8")

            with patched_root(root):
                versions = context_ansible.extract_application_versions(
                    ["deployment.yaml"], include_discovered=False
                )

        self.assertEqual(versions, ["deployment.yaml: acme_widget_version=4.2.1"])

    def test_schema_api_version_is_not_an_application_version_pin(self) -> None:
        from ocr_toolkit.context.ansible import extract_application_versions

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "deployment.yaml"
            manifest.write_text(
                "apiVersion: apps/v1\nkind: Deployment\nimage: registry/app:1.2.3\n",
                encoding="utf-8",
            )

            with patched_root(root):
                versions = extract_application_versions(["deployment.yaml"])

        self.assertIn("deployment.yaml: image=registry/app:1.2.3", versions)
        self.assertNotIn("deployment.yaml: apiVersion=apps/v1", versions)

    def test_application_version_output_redacts_sensitive_values(self) -> None:
        from ocr_toolkit.context.ansible import extract_application_versions

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "deployment.yaml"
            manifest.write_text(
                "image: registry/app:1.2.3?private_token=secret-value\n",
                encoding="utf-8",
            )

            with patched_root(root):
                versions = extract_application_versions(["deployment.yaml"])

        self.assertEqual(
            versions,
            ["deployment.yaml: image=registry/app:1.2.3?private_token=***"],
        )

    def test_application_version_output_skips_latest_image_tags(self) -> None:
        from ocr_toolkit.context.ansible import extract_application_versions

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "deployment.yaml"
            manifest.write_text(
                "image: registry.example.com:5000/app:latest\n"
                "sidecar_image: registry.example.com:5000/sidecar:1.2.3\n"
                "debug_image: registry.example.com:5000/debug:latest\n"
                "implicit_image: nginx\n"
                "templated_image: registry/app:{{ app_version }}\n"
                "env_image: registry/app:${APP_VERSION}\n"
                "dockerImage: nginx:alpine\n"
                "containerImage: redis:bullseye\n",
                encoding="utf-8",
            )

            with patched_root(root):
                versions = extract_application_versions(["deployment.yaml"])

        self.assertEqual(
            versions,
            [
                "deployment.yaml: sidecar_image=registry.example.com:5000/sidecar:1.2.3",
                "deployment.yaml: dockerImage=nginx:alpine",
                "deployment.yaml: containerImage=redis:bullseye",
            ],
        )

    def test_application_version_output_keeps_digest_pinned_images(self) -> None:
        from ocr_toolkit.context.ansible import extract_application_versions

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "deployment.yaml"
            manifest.write_text(
                "image: registry.example.com:5000/app@sha256:abc123\n",
                encoding="utf-8",
            )

            with patched_root(root):
                versions = extract_application_versions(["deployment.yaml"])

        self.assertEqual(
            versions,
            ["deployment.yaml: image=registry.example.com:5000/app@sha256:abc123"],
        )


class ContextRenderingTests(unittest.TestCase):
    def test_review_language_contract_defaults_to_english_and_supports_russian(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("docs\n", encoding="utf-8")

            with (
                patched_root(root),
                patched_attr(context_repo, "changed_files", lambda: ["README.md"]),
            ):
                with patched_env(OCR_REVIEW_LANGUAGE=""):
                    english = context_render.build_context()
                with patched_env(OCR_REVIEW_LANGUAGE="Russian"):
                    russian = context_render.build_context()

        self.assertIn("Response language: English.", english)
        self.assertIn(
            "All user-visible review comments, summaries, warnings and recommendations MUST be written",
            english,
        )
        self.assertIn("Response language: Russian.", russian)
        self.assertIn(
            "All user-visible review comments, summaries, warnings and recommendations MUST be written",
            russian,
        )

    def test_build_context_discovers_related_unchanged_version_pins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "roles" / "demo" / "tasks").mkdir(parents=True)
            (root / "roles" / "demo" / "tasks" / "main.yml").write_text(
                "- debug: msg=ok\n", encoding="utf-8"
            )
            (root / "defaults.yml").write_text("service_version: 2.4.6\n", encoding="utf-8")

            with patched_root(root):
                with patched_attr(
                    context_repo,
                    "changed_files",
                    lambda: ["roles/demo/tasks/main.yml"],
                ):
                    rendered = context_render.build_context()

        self.assertIn("defaults.yml: service_version=2.4.6", rendered)

    def test_discovered_application_versions_precede_requirement_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "roles" / "demo" / "tasks").mkdir(parents=True)
            (root / "roles" / "demo" / "tasks" / "main.yml").write_text(
                "- debug: msg=ok\n", encoding="utf-8"
            )
            (root / "defaults.yml").write_text("service_version: 2.4.6\n", encoding="utf-8")
            (root / "requirements.yml").write_text(
                "- src: https://example.com/collection.git\n  version: 1.0.0\n",
                encoding="utf-8",
            )

            with patched_root(root):
                with patched_attr(
                    context_repo,
                    "changed_files",
                    lambda: ["roles/demo/tasks/main.yml"],
                ):
                    rendered = context_render.build_context()

        self.assertLess(
            rendered.index("defaults.yml: service_version=2.4.6"),
            rendered.index("requirements.yml: https://example.com/collection.git=1.0.0"),
        )

    def test_tiny_section_budget_never_returns_partial_heading(self) -> None:
        section = context_planner.ContextSection(title="Multibyte section", body="данные" * 20)

        rendered = context_planner._truncate_section(section, 6)

        self.assertEqual(rendered, "")

    def test_python_change_includes_existing_root_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "module.py").write_text("print('ok')\n", encoding="utf-8")
            (root / "requirements.txt").write_text("example-package==1.2.3\n", encoding="utf-8")

            with patched_root(root):
                with patched_attr(context_repo, "changed_files", lambda: ["module.py"]):
                    rendered = context_render.build_context()

        self.assertIn("requirements-style dependencies (`requirements.txt`)", rendered)
        self.assertIn("example-package==1.2.3", rendered)

    def test_non_python_change_does_not_seed_root_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("docs\n", encoding="utf-8")
            (root / "requirements.txt").write_text("example-package==1.2.3\n", encoding="utf-8")

            with patched_root(root):
                with patched_attr(context_repo, "changed_files", lambda: ["README.md"]):
                    rendered = context_render.build_context()

        self.assertNotIn("requirements-style dependencies", rendered)

    def test_recursive_glob_matches_root_and_nested_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "galaxy.yml").write_text("name: root\n", encoding="utf-8")
            (root / "nested").mkdir()
            (root / "nested" / "galaxy.yml").write_text("name: nested\n", encoding="utf-8")

            with patched_root(root):
                matches = [
                    path.relative_to(root).as_posix()
                    for path in context_repo.iter_repo_glob(
                        "**/galaxy.yml", frozenset(), files_only=True
                    )
                ]

        self.assertEqual(matches, ["galaxy.yml", "nested/galaxy.yml"])

    def test_recursive_globstar_segment_can_match_zero_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "inventory").mkdir()
            (root / "inventory" / "prod.yml").write_text("all: {}\n", encoding="utf-8")
            (root / "inventory" / "region").mkdir()
            (root / "inventory" / "region" / "prod.yml").write_text("all: {}\n", encoding="utf-8")

            with patched_root(root):
                matches = [
                    path.relative_to(root).as_posix()
                    for path in context_repo.iter_repo_glob(
                        "inventory/**/*", frozenset(), files_only=True
                    )
                ]

        self.assertEqual(matches, ["inventory/prod.yml", "inventory/region/prod.yml"])

    def test_context_planner_keeps_every_active_domain_under_pressure(self) -> None:
        sections = [
            context_planner.ContextSection(
                title=f"Domain {index}",
                body=("данные " * 200) + f"tail-{index}",
                priority=100 - index,
            )
            for index in range(6)
        ]

        rendered = context_planner.render_context(
            "# Review Background\n\nMandatory instructions.", sections, 1_600
        )

        self.assertLessEqual(len(rendered.encode("utf-8")), 1_600)
        self.assertIn("Mandatory instructions.", rendered)
        for index in range(6):
            self.assertIn(f"## Domain {index}", rendered)
        self.assertIn("section truncated", rendered)

    def test_context_planner_does_not_add_a_blank_prefix_without_preamble(self) -> None:
        rendered = context_planner.render_context(
            "",
            [context_planner.ContextSection(title="Only", body="body")],
            1_000,
        )

        self.assertEqual(rendered, "## Only\nbody\n")

    def test_context_planner_closes_truncated_fence(self) -> None:
        rendered = context_planner.render_context(
            "# Review Background",
            [
                context_planner.ContextSection(
                    title="Guidance",
                    body="```markdown\n" + "x" * 2_000 + "\n```",
                )
            ],
            420,
        )

        self.assertLessEqual(len(rendered.encode("utf-8")), 420)
        self.assertIsNone(open_markdown_fence(rendered))
        self.assertIn("section truncated", rendered)

    def test_context_planner_ignores_headings_inside_fences(self) -> None:
        preamble, sections = context_planner.split_markdown_sections(
            "# Background\n\n## First\n```markdown\n## Not a section\n```\n\n## Second\nbody\n"
        )

        self.assertEqual(preamble, "# Background")
        self.assertEqual([section.title for section in sections], ["First", "Second"])
        self.assertIn("## Not a section", sections[0].body)

    def test_context_planner_omits_low_priority_domains_when_headings_do_not_fit(self) -> None:
        sections = [
            context_planner.ContextSection(
                title=f"Domain {index}",
                body="content",
                priority=100 - index,
            )
            for index in range(30)
        ]

        rendered = context_planner.render_context(
            "# Review Background",
            sections,
            1_200,
            max_chars=500,
        )

        self.assertLessEqual(len(rendered), 500)
        self.assertLessEqual(len(rendered.encode("utf-8")), 1_200)
        self.assertIn("## Domain 0", rendered)
        self.assertIn("## Context coverage", rendered)
        self.assertIsNone(open_markdown_fence(rendered))

    def test_build_context_activates_only_relevant_ecosystem_sections(self) -> None:
        cases = [
            (
                {
                    "src/app.py": "print('ok')\n",
                    "pyproject.toml": "[project]\nrequires-python = '>=3.12'\n",
                },
                ["src/app.py", "pyproject.toml"],
                {"Python context"},
                {"Go context", "PHP context", "JavaScript/TypeScript context"},
            ),
            (
                {
                    "inventories/prod/hosts.yml": "all:\n  hosts: {}\n",
                    "roles/app/defaults/main.yml": "app_version: 1.2.3\n",
                },
                ["inventories/prod/hosts.yml", "roles/app/defaults/main.yml"],
                {"Ansible inventory topology files"},
                {"Python context", "Go context", "PHP context"},
            ),
            (
                {
                    "package.json": '{"engines":{"node":">=20"}}\n',
                    "src/index.ts": "export const value = 1;\n",
                },
                ["package.json", "src/index.ts"],
                {"JavaScript/TypeScript context"},
                {"Python context", "Go context", "PHP context"},
            ),
        ]
        for files, changed, present, absent in cases:
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                for rel_path, content in files.items():
                    path = root / rel_path
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content, encoding="utf-8")
                with (
                    patched_root(root),
                    patched_attr(context_repo, "changed_files", lambda: changed),
                    patched_attr(context_repo, "tool_version", lambda *_args, **_kwargs: []),
                    patched_attr(context_render, "read_project_instructions", lambda **_kwargs: []),
                    patched_attr(context_render, "read_accepted_decisions", lambda **_kwargs: ""),
                    patched_env(
                        OCR_BACKGROUND_MAX_BYTES="65536",
                        OCR_BACKGROUND_MAX_CHARS="7950",
                    ),
                ):
                    rendered = context_render.build_context()

                self.assertLessEqual(len(rendered), 7_950)
                self.assertLessEqual(len(rendered.encode("utf-8")), 65_536)
                for title in present:
                    self.assertIn(f"## {title}", rendered)
                for title in absent:
                    self.assertNotIn(f"## {title}", rendered)

    def test_format_manifest_items_preserves_omitted_count_without_visible_items(self) -> None:
        self.assertEqual(context_render.format_manifest_items([], omitted=3), "- ... and 3 more")

    def test_recursive_glob_honors_limit_and_skips_seen_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index in range(5):
                path = root / "roles" / f"role{index}" / "defaults" / "main.yml"
                path.parent.mkdir(parents=True)
                path.write_text("---\n", encoding="utf-8")

            with patched_root(root):
                paths = list(
                    context_repo.iter_repo_glob(
                        "roles/**/defaults/main.yml",
                        frozenset(),
                        limit=2,
                        files_only=True,
                        skip_rel_paths={"roles/role0/defaults/main.yml"},
                    )
                )

        self.assertEqual(len(paths), 2)
        self.assertNotIn("role0", {part for path in paths for part in path.parts})

    def test_format_items_redacts_and_escapes_at_output_boundary(self) -> None:
        rendered = context_render.format_items(
            ["pkg @ https://user:token@example.com/simple/pkg\n/close"]
        )

        self.assertNotIn("user:token", rendered)
        self.assertIn("https://***@example.com/simple/pkg\\n/close", rendered)

    def test_nested_package_json_is_rendered_with_relative_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = root / "services" / "web"
            service.mkdir(parents=True)
            (service / "package.json").write_text('{"engines": {"node": ">=20"}}', encoding="utf-8")

            with (
                patched_root(root),
                patched_attr(
                    context_repo,
                    "changed_files",
                    lambda: ["services/web/package.json"],
                ),
            ):
                background = context_render.build_context()

        self.assertIn("### `services/web/package.json`", background)
        self.assertIn("node: >=20", background)

    def test_context_rendering_redacts_scalar_manifest_values_and_headings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = root / "token=secret" / "web"
            service.mkdir(parents=True)
            (service / "package.json").write_text(
                json.dumps(
                    {
                        "engines": {"node": "https://user:token@example.com/node"},
                    }
                ),
                encoding="utf-8",
            )

            with (
                patched_root(root),
                patched_attr(
                    context_repo,
                    "changed_files",
                    lambda: ["token=secret/web/package.json"],
                ),
            ):
                background = context_render.build_context()

        self.assertNotIn("user:token", background)
        self.assertNotIn("token=secret", background)
        self.assertIn("https://***@example.com/node", background)
        self.assertIn("### `token=***/web/package.json`", background)

    def test_context_rendering_redacts_secret_keys_inside_path_segments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            secret_dir = root / "config"
            secret_dir.mkdir()
            package_json = secret_dir / "db-password=hunter2-package.json"
            package_json.write_text('{"engines": {"node": ">=20"}}', encoding="utf-8")

            with (
                patched_root(root),
                patched_attr(
                    context_repo,
                    "changed_files",
                    lambda: ["config/db-password=hunter2-package.json"],
                ),
            ):
                background = context_render.build_context()

        self.assertNotIn("hunter2", background)
        self.assertIn("config/db-password=***", background)

    def test_context_rendering_redacts_separator_secret_path_segments(self) -> None:
        rendered = context_render.safe_inline_path(
            "secrets/prod-token-abc/private_key.pem/id_ed25519"
        )

        self.assertNotIn("abc", rendered)
        self.assertNotIn("private_key", rendered)
        self.assertNotIn("id_ed25519", rendered)
        self.assertIn("prod-token-***", rendered)

    def test_context_rendering_redacts_standalone_secret_path_basenames(self) -> None:
        rendered = context_render.safe_inline_path(
            "password.txt/api_key.yaml/secret.env/aws_secret_access_key=abc"
        )

        self.assertNotIn("password", rendered)
        self.assertNotIn("api_key", rendered)
        self.assertNotIn("secret.env", rendered)
        self.assertNotIn("abc", rendered)

    def test_context_rendering_redacts_key_created_by_control_removal(self) -> None:
        for path in (
            "reports/pass\u200dword=hunter2.txt",
            "reports/pass\nword=hunter2.txt",
            "reports/pass\tword=hunter2.txt",
            "reports/api_\nkey=hunter2.txt",
        ):
            with self.subTest(path=path):
                rendered = context_render.safe_inline_path(path)
                self.assertNotIn("hunter2", rendered)
                self.assertNotIn("\n", rendered)
                self.assertNotIn("\t", rendered)

    def test_context_rendering_preserves_benign_secret_adjacent_path(self) -> None:
        rendered = context_render.safe_inline_path(
            "reports/данные-\ue000-passwordless_mode=true.txt"
        )

        self.assertIn("данные-\ue000-passwordless_mode=true.txt", rendered)

    def test_accepted_decision_headings_stay_inside_parent_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = root / ".opencodereview"
            decisions.mkdir()
            (decisions / "accepted-decisions.md").write_text(
                "# Accepted root\n\n## Nested decision\n\n##### Deep decision\n",
                encoding="utf-8",
            )

            with patched_root(root):
                with patched_attr(context_repo, "changed_files", lambda: []):
                    background = context_render.build_context()

        summary = context_render.summarize_context(background, 65536)
        self.assertIn("Accepted project decisions", summary)
        self.assertNotIn("Accepted root", summary)
        self.assertNotIn("Nested decision", summary)
        self.assertIn("###### Deep decision", background)
        self.assertNotIn("#######", background)

    def test_context_truncation_does_not_append_stale_fence(self) -> None:
        text = "```" + ("`" * 120) + "\nsecret\n"

        limited = context_render.limit_text_bytes(text, max_bytes=80)

        self.assertLessEqual(len(limited.encode("utf-8")), 80)
        self.assertIn("Context truncation", limited)

    def test_context_truncation_ignores_invalid_fence_closer(self) -> None:
        text = "```text\nbody\n```not-a-close\n" + ("x" * 300)

        limited = context_render.limit_text_bytes(text, max_bytes=180)

        self.assertLessEqual(len(limited.encode("utf-8")), 180)
        self.assertIn("```not-a-close", limited)
        self.assertIn("\n```\n\n## Context truncation", limited)

    def test_context_summary_uses_footer_for_truncation_status(self) -> None:
        background = (
            "## Project instructions\n"
            "Repository text mentions ## Context truncation notice but was not clipped.\n"
        )

        summary = context_render.summarize_context(background, 65536)

        self.assertIn("truncated: no", summary)

    def test_note_truncation_reserves_space_for_long_fence(self) -> None:
        body = "`" * 80 + "\n" + "x" * 400

        limited = truncate_note_body(body, max_chars=260)

        self.assertLessEqual(len(limited), 260)
        self.assertIn("Raw Markdown excerpt follows", limited)

    def test_bounded_glob_returns_deterministic_sorted_top_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ["z.txt", "a.txt", "m.txt", "b.txt"]:
                (root / name).write_text("x", encoding="utf-8")

            with patched_root(root):
                matched = context_repo.bounded_rel_glob(["*.txt"], limit=2)

        self.assertEqual(matched, ["a.txt", "b.txt"])

    def test_bounded_glob_does_not_collect_more_than_requested_for_plain_globs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ["a.txt", "b.txt", "c.txt", "d.txt"]:
                (root / name).write_text("x", encoding="utf-8")

            with patched_root(root):
                matched = [
                    path.relative_to(root).as_posix()
                    for path in context_repo.iter_plain_glob("*.txt", frozenset(), limit=2)
                ]

        self.assertEqual(matched, ["a.txt", "b.txt"])

    def test_plain_glob_applies_filters_before_its_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".DS_Store").write_text("ignored", encoding="utf-8")
            (root / "a.txt").write_text("skip", encoding="utf-8")
            (root / "b.txt").write_text("keep", encoding="utf-8")

            with patched_root(root):
                matched = [
                    path.relative_to(root).as_posix()
                    for path in context_repo.iter_repo_glob(
                        "*",
                        context_repo.DEFAULT_EXCLUDE_DIRS,
                        limit=1,
                        files_only=True,
                        skip_rel_paths={"a.txt"},
                    )
                ]

        self.assertEqual(matched, ["b.txt"])

    def test_rel_glob_files_does_not_underfill_when_directories_sort_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ["a_dir", "b_dir"]:
                (root / name).mkdir()
            for name in ["c.txt", "d.txt"]:
                (root / name).write_text("x", encoding="utf-8")

            with patched_root(root):
                matched = context_repo.rel_glob_files(["*"], limit=2)

        self.assertEqual(matched, ["c.txt", "d.txt"])

    def test_plain_glob_prunes_symlinked_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside = Path(tmp) / "outside"
            outside.mkdir()
            (outside / "leak.txt").write_text("x", encoding="utf-8")
            link = root / "linked"
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"symlinks unavailable: {exc}")

            with patched_root(root):
                matched = context_repo.bounded_rel_glob(["linked/*.txt"], limit=10)

        self.assertEqual(matched, [])

    def test_plain_glob_rejects_parent_directory_segments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            outside = Path(tmp) / "outside.txt"
            outside.write_text("x", encoding="utf-8")

            with patched_root(root):
                matched = context_repo.bounded_rel_glob(["../*.txt"], limit=10)

        self.assertEqual(matched, [])

    def test_bounded_glob_does_not_underfill_overlapping_plain_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ["a.txt", "b.txt"]:
                (root / name).write_text("x", encoding="utf-8")

            with patched_root(root):
                matched = context_repo.bounded_rel_glob(["a.txt", "*.txt"], limit=2)

        self.assertEqual(matched, ["a.txt", "b.txt"])

    def test_bounded_glob_prunes_vendor_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "vendor" / "pkg").mkdir(parents=True)
            (root / "vendor" / "pkg" / "package.json").write_text("{}", encoding="utf-8")
            (root / "package.json").write_text("{}", encoding="utf-8")

            with patched_root(root):
                matched = context_repo.bounded_rel_glob(["**/package.json"], limit=10)

        self.assertEqual(matched, ["package.json"])


class RuleCoverageTests(unittest.TestCase):
    def test_project_rules_extend_instead_of_replacing_system_rules(self) -> None:
        rule_data = json.loads((HELPER_DIR / "rules.json").read_text(encoding="utf-8"))
        rules = rule_data.get("rules", [])
        paths = [rule.get("path") for rule in rules]

        self.assertNotIn("**/*.{py,pyi}", paths)
        self.assertNotIn("**/*", paths)
        self.assertNotIn("**/*.go", paths)
        self.assertNotIn("**/*.php", paths)
        self.assertNotIn("**/*.{js,jsx,ts,tsx,mjs,cjs}", paths)
        self.assertNotIn("**/*.{tf,tfvars,hcl}", paths)
        self.assertEqual(paths.count("**/*.sql"), 1)
        sql_rule = rules[paths.index("**/*.sql")]
        self.assertIn("Determine the SQL dialect", sql_rule["rule"])
        galaxy_path = (
            "{requirements.yml,requirements.yaml,**/requirements.yml,**/requirements.yaml}"
        )
        self.assertIn(galaxy_path, paths)
        generic_manifest_path = next(path for path in paths if path and "pyproject.toml" in path)
        self.assertNotIn("requirements.yml", generic_manifest_path)
        self.assertNotIn("requirements.yaml", generic_manifest_path)
        for rule in rules:
            self.assertTrue(rule.get("merge_system_rule"), rule.get("path"))

    def test_ci_uses_single_generated_background_file(self) -> None:
        ci_text = (HELPER_DIR / "ocr-review.gitlab-ci.yml").read_text(encoding="utf-8")
        review_block = ci_text[
            ci_text.index("\nopen_code_review:\n") : ci_text.index(
                "\n\nopen_code_review_self_test:"
            )
        ]

        self.assertIn(
            'REVIEW_BACKGROUND_FILE=".review-context/dependencies.md"',
            review_block,
        )
        self.assertEqual(review_block.count("--background-file"), 1)
        self.assertNotIn("cat .review-context/dependencies.md", review_block)

    def test_lint_job_is_required_in_merge_request_pipeline(self) -> None:
        ci_text = (HELPER_DIR / "ocr-review.gitlab-ci.yml").read_text(encoding="utf-8")
        lint_block = ci_text[ci_text.index("\nlint:\n") : ci_text.index("\n\nopen_code_review:")]
        stages_block = ci_text[ci_text.index("stages:") : ci_text.index("\n\ndefault:")]
        review_block = ci_text[
            ci_text.index("\nopen_code_review:\n") : ci_text.index(
                "\n\nopen_code_review_self_test:"
            )
        ]

        self.assertLess(stages_block.index("- lint"), stages_block.index("- ai_review"))
        self.assertIn("stage: lint", lint_block)
        self.assertIn("if: '$CI_PIPELINE_SOURCE == \"merge_request_event\"'", lint_block)
        self.assertIn("when: on_success", lint_block)
        self.assertIn("- when: never", lint_block)
        self.assertIn("stage: ai_review", review_block)
        self.assertNotIn("needs:", review_block)

    def test_ci_does_not_run_ocr_helper_regressions_by_default(self) -> None:
        ci_text = (HELPER_DIR / "ocr-review.gitlab-ci.yml").read_text(encoding="utf-8")
        helper_test = "uv run pytest tests"
        context_generation = "ocr-ci context"
        token_export = "export OCR_LLM_TOKEN="

        self.assertIn(helper_test, ci_text)
        self.assertIn('OCR_RUN_HELPER_TESTS: "false"', ci_text)
        self.assertIn('OCR_LLM_ALLOWED_MODELS: ""', ci_text)
        self.assertIn("OCR_RUN_HELPER_TESTS:-false", ci_text)
        self.assertLess(ci_text.index(helper_test), ci_text.index(token_export))
        self.assertLess(ci_text.index(helper_test), ci_text.index(context_generation))
        self.assertIn("--format json", ci_text)
        self.assertNotIn("--output-format", ci_text)
        self.assertIn("\nopen_code_review_self_test:\n", ci_text)
        self.assertIn("open_code_review_self_test:\n  stage: ai_review", ci_text)
        self.assertIn(
            "open_code_review_self_test:\n  stage: ai_review",
            ci_text,
        )
        self.assertIn("when: manual", ci_text[ci_text.index("open_code_review_self_test:") :])

    def test_changed_file_categories_cover_operational_paths(self) -> None:
        categories = context_categorize.categorize_files(
            [
                "Dockerfile.ansible",
                "roles/sample_role/tasks/main.yml",
                "requirements.yml",
                "roles/another_role/molecule/default/molecule.yml",
                "roles/sample_role/files/app.service",
                ".opencodereview/ocr_toolkit/posting/workflow.py",
                "roles/app/templates/Dockerfile.j2",
                "requirements/archive/notes.txt",
                "requirements/dev.in",
            ]
        )

        self.assertEqual(
            categories["containers"],
            ["Dockerfile.ansible", "roles/app/templates/Dockerfile.j2"],
        )
        self.assertIn("roles/sample_role/tasks/main.yml", categories["ansible_roles"])
        self.assertEqual(
            categories["dependency_manifests"], ["requirements.yml", "requirements/dev.in"]
        )
        self.assertIn("requirements/archive/notes.txt", categories["other"])
        self.assertEqual(
            categories["molecule_tests"],
            ["roles/another_role/molecule/default/molecule.yml"],
        )
        self.assertEqual(categories["systemd_units"], ["roles/sample_role/files/app.service"])
        unit_categories = context_categorize.categorize_files(
            [
                "roles/sample_role/files/cache.automount",
                "roles/sample_role/files/swap.swap",
                "roles/sample_role/files/device.device",
                "roles/sample_role/files/job.scope",
                "roles/sample_role/files/app.service.d/override.conf",
                "root.service.d/override.conf",
            ]
        )
        self.assertEqual(
            unit_categories["systemd_units"],
            [
                "roles/sample_role/files/cache.automount",
                "roles/sample_role/files/swap.swap",
                "roles/sample_role/files/device.device",
                "roles/sample_role/files/job.scope",
                "roles/sample_role/files/app.service.d/override.conf",
                "root.service.d/override.conf",
            ],
        )
        self.assertEqual(
            categories["ocr_integration"],
            [".opencodereview/ocr_toolkit/posting/workflow.py"],
        )
        self.assertIn("roles/app/templates/Dockerfile.j2", categories["containers"])
        self.assertIn("roles/app/templates/Dockerfile.j2", categories["ansible_roles"])
        self.assertIn("roles/app/templates/Dockerfile.j2", categories["templates"])

    def test_context_provider_activation_is_manifest_specific(self) -> None:
        cases = {
            "requirements.yml": {"ansible"},
            "requirements/dev.in": {"python"},
            "constraints.txt": {"python"},
            "Pipfile": {"python"},
            "pyproject.toml": {"python"},
            "go.mod": {"go"},
            "composer.json": {"php"},
            "package.json": {"javascript"},
            "inventories/environment_a/hosts.yml": {"ansible"},
            "templates/page.j2": set(),
            "roles/app/templates/config.j2": {"ansible"},
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                categories = context_categorize.categorize_files([path])
                self.assertEqual(
                    context_categorize.active_context_providers([path], categories),
                    expected,
                )

        paths = ["pyproject.toml", "package.json", "src/main.go"]
        categories = context_categorize.categorize_files(paths)
        self.assertEqual(
            context_categorize.active_context_providers(paths, categories),
            {"python", "javascript", "go"},
        )

    def test_root_playbook_category_uses_content_detector(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "service.yml").write_text("- hosts: app\n  tasks: []\n", encoding="utf-8")
            (root / "requirements.yml").write_text(
                "roles:\n  - name: example.role\n", encoding="utf-8"
            )

            with patched_root(root):
                categories = context_categorize.categorize_files(
                    ["service.yml", "requirements.yml"]
                )

        self.assertEqual(categories["ansible_playbooks"], ["service.yml"])
        self.assertEqual(categories["dependency_manifests"], ["requirements.yml"])

    def test_bounded_recursive_glob_does_not_spend_limit_on_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "real.txt").write_text("ok", encoding="utf-8")
            (root / "outside").mkdir()
            (root / "outside" / "secret.txt").write_text("bad", encoding="utf-8")
            (root / "linked.txt").symlink_to(root / "outside" / "secret.txt")

            with patched_root(root):
                matches = context_repo.bounded_rel_glob(["**/*.txt"], limit=1, files_only=True)

        self.assertEqual(matches, ["real.txt"])

    def test_inventory_filenames_are_categorized_outside_inventory_dirs(self) -> None:
        categories = context_categorize.categorize_files(["deploy/hosts.yml", "ops/inventory.ini"])

        self.assertEqual(categories["ansible_inventory"], ["deploy/hosts.yml", "ops/inventory.ini"])

    def test_changed_file_categories_have_stable_key_order(self) -> None:
        categories = context_categorize.categorize_files(
            ["README.md", ".gitlab-ci.yml", "roles/app/tasks/main.yml"]
        )

        self.assertEqual(list(categories), ["ci", "ansible_roles", "docs"])


class DocumentationConsistencyTests(unittest.TestCase):
    def test_open_code_review_docs_match_current_ci_surface(self) -> None:
        docs = (HELPER_DIR.parents[1] / "docs" / "gitlab.md").read_text(encoding="utf-8")
        ci = (HELPER_DIR / "ocr-review.gitlab-ci.yml").read_text(encoding="utf-8")
        internals = (HELPER_DIR.parents[1] / "docs" / "security.md").read_text(encoding="utf-8")

        self.assertIn('OCR_VERSION: "v1.7.13"', ci)
        self.assertIn("v1.7.13", docs)
        self.assertIn("v1.7.13", internals)
        self.assertIn("openai-responses", docs)
        self.assertIn("OCR_MCP_SERVERS_JSON", docs)
        self.assertIn("stdio bridge", docs)
        self.assertIn("manual", docs.lower())
        self.assertIn("trusted contributors", docs.lower())
        self.assertIn("docs/security.md", docs)
        self.assertNotIn("## OCR JSON metadata", docs)
        self.assertIn('OCR_LLM_VALIDATE_MODEL: "false"', ci)
        self.assertIn('OCR_LLM_ALLOWED_MODELS: ""', ci)
        self.assertIn('OCR_REVIEW_LANGUAGE: "Russian"', ci)
        self.assertIn("defaults to `English`", docs)
        self.assertIn("set `Russian`", docs)
        self.assertIn("ocr-ci preflight", ci)
        self.assertIn("ocr-ci configure", ci)
        self.assertIn("uv run pytest tests", ci)
        self.assertIn("ocr-ci preflight", ci)
        self.assertIn("--background-file", ci)
        self.assertEqual(ci.count("--background-file"), 1)
        self.assertNotIn('set -- "$@" --background ', ci)
        self.assertNotIn("review-background.md", ci)
        self.assertIn('--from "${CI_MERGE_REQUEST_DIFF_BASE_SHA}"', ci)
        self.assertIn('--to "${CI_MERGE_REQUEST_SOURCE_BRANCH_SHA}"', ci)
        self.assertNotIn("ocr review --commit", ci)
        self.assertNotIn("ocr config set", ci)
        self.assertIn("when: manual", ci)
        self.assertIn("env -u OCR_LLM_TOKEN", ci)

    def test_ci_does_not_inline_python_heredocs(self) -> None:
        ci = (HELPER_DIR / "ocr-review.gitlab-ci.yml").read_text(encoding="utf-8")

        self.assertNotIn("<<'PY'", ci)
        self.assertNotIn("OCR review scope:", ci)


class ManifestParserAdditionalTests(unittest.TestCase):
    def test_pyproject_includes_optional_and_dependency_groups(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pyproject = root / "pyproject.toml"
            pyproject.write_text(
                """
[project]
dependencies = ["basepkg>=1"]
[project.optional-dependencies]
dev = ["pytest>=8"]
[dependency-groups]
docs = ["mkdocs>=1"]
[tool.poetry.group.lint.dependencies]
ruff = "^0.5"
""".strip(),
                encoding="utf-8",
            )

            with patched_root(root):
                parsed = context_manifests.parse_pyproject(pyproject)

        deps = "\n".join(parsed["dependencies"])
        self.assertIn("basepkg>=1", deps)
        self.assertIn("optional.dev: pytest>=8", deps)
        self.assertIn("group.docs: mkdocs>=1", deps)
        self.assertIn("poetry.lint.ruff: ^0.5", deps)

    def test_pyproject_redacts_credentialed_dependency_urls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pyproject = root / "pyproject.toml"
            pyproject.write_text(
                '[project]\ndependencies = ["pkg @ https://user:token@example.com/simple/pkg"]\n',
                encoding="utf-8",
            )

            with patched_root(root):
                parsed = context_manifests.parse_pyproject(pyproject)

        self.assertEqual(
            parsed["dependencies"],
            ["pkg @ https://***@example.com/simple/pkg"],
        )

    def test_requirements_redacts_credentialed_dependency_urls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            requirements = Path(tmp) / "requirements.txt"
            requirements.write_text(
                "pkg @ https://user:token@example.com/simple/pkg\n",
                encoding="utf-8",
            )

            with patched_root(Path(tmp)):
                parsed = context_manifests.parse_requirements_txt(requirements)

        self.assertEqual(
            parsed["dependencies"],
            ["pkg @ https://***@example.com/simple/pkg"],
        )

    def test_root_pyproject_survives_discovery_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                "[project]\nrequires-python = '>=3.12'\n", encoding="utf-8"
            )
            (root / "pkg").mkdir()
            (root / "pkg" / "module.py").write_text("pass\n", encoding="utf-8")

            with patched_root(root):
                discovery = context_manifests.discover_pyproject_paths(
                    ["pkg/pyproject.toml", "pkg/module.py"], limit=1
                )

        self.assertEqual(discovery.paths, ["pyproject.toml"])
        self.assertGreaterEqual(discovery.omitted, 0)

    def test_dockerfile_from_options_do_not_hide_image_pin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dockerfile = root / "Dockerfile"
            dockerfile.write_text(
                "FROM --platform=$BUILDPLATFORM python:3.12-slim AS builder\n",
                encoding="utf-8",
            )

            with patched_root(root):
                pins = context_ansible.extract_application_versions(["Dockerfile"])

        self.assertIn("Dockerfile: image=python:3.12-slim", pins)

    def test_billing_classifier_matches_insufficient_quota(self) -> None:
        warnings = [{"message": "LLM error: insufficient_quota"}]

        self.assertTrue(result.llm_billing_failure_warnings(warnings))


class TestSuiteIntegrityTests(unittest.TestCase):
    def test_no_duplicate_test_method_names_inside_classes(self) -> None:
        duplicates: list[str] = []
        for test_path in sorted(Path(__file__).parent.glob("test_*.py")):
            tree = ast.parse(test_path.read_text(encoding="utf-8"))
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                seen: dict[str, int] = {}
                for child in node.body:
                    if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    if not child.name.startswith("test_"):
                        continue
                    if child.name in seen:
                        duplicates.append(
                            f"{test_path.name}:{node.name}.{child.name}: "
                            f"{seen[child.name]} and {child.lineno}"
                        )
                    else:
                        seen[child.name] = child.lineno

        self.assertEqual(duplicates, [])
