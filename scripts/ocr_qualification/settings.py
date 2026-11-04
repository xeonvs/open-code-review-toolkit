"""Pinned metadata limits and current OCR contract inputs."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TypeVar

ROOT = Path(__file__).resolve().parents[2]


DEFAULT_MANIFEST = ROOT / "compatibility" / "ocr-support.json"


PREFLIGHT = ROOT / "src" / "ocr_toolkit" / "preflight.py"


GITLAB_EXAMPLE = ROOT / "examples" / "gitlab" / "ocr-review.gitlab-ci.yml"


UPSTREAM_REPOSITORY = "alibaba/open-code-review"


UPSTREAM_API = f"https://api.github.com/repos/{UPSTREAM_REPOSITORY}"


USER_AGENT = "open-code-review-toolkit-compatibility/1"


HTTP_TIMEOUT_SECONDS = 30


MAX_HTTP_BYTES = 2_000_000


MAX_ASSET_BYTES = 64 * 1024 * 1024


MAX_ASSETS = 16


MAX_TOTAL_ASSET_BYTES = 384 * 1024 * 1024


MAX_RELEASES_PER_PAGE = 50


MAX_RELEASE_PAGES = 4


MAX_ISSUE_PAGES = 10


MAX_ISSUE_RESPONSE_BYTES = 8 * 1024 * 1024


MAX_RELEASE_CHANGES_CHARS = 4_000


MAX_RELEASE_CHANGES_LINES = 50


MAX_QUALIFICATION_CHAIN = 10


MAX_CLI_PROBE_BYTES = 100_000


MAX_GROUPING_INVENTORY_ENTRIES = 100


MAX_GROUPING_PATH_CHARS = 1_000


MAX_GROUPING_CHURN = 1_000_000_000


GROUPING_PROMPT_PREFIX = "Group the following changed files:\n\n"


GROUPING_RESPONSE_BOUNDARY = (
    '\n\nRespond with a JSON array, where "files" holds the integer indices shown in '
    "brackets beside each file:"
)


DOWNLOAD_ATTEMPTS = 3


VERSION_RE = re.compile(r"^v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


VERSION_LINE_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


SHA256_RE = re.compile(r"^(?:sha256:)?([0-9a-f]{64})$")


REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


PUBLISHED_AT_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")


SAFE_NOTES_RE = re.compile(
    r"\b(fix|bug|documentation|docs|test|chore|refactor|performance)\b", re.I
)


MATERIAL_NOTES_RE = re.compile(
    r"\b(breaking|remove[ds]?|deprecat|security|vulnerab|protocol|schema|format|cli|flag|config|providers?|gitlab|features?|llm|openrouter|models?|timeouts?|deadlines?)\b"
    r"|^[ \t]*-[ \t]*feat(?:\([^\r\n)]{1,80}\))?:",
    re.I | re.M,
)


REQUIRED_REVIEW_FLAGS = {
    "--audience",
    "--effort",
    "--background-file",
    "--format",
    "--max-tokens-budget",
    "--max-tools",
    "--from",
    "--preview",
    "--rule",
    "--to",
}


PRIOR_FINDING_RECHECK_MARKER = "Prior/filter-surviving findings remain unverified"


MAX_TOOLS_NORMALIZATION_RE = re.compile(
    r"\[ocr\] --max-tools ([0-9]{1,12}) is below minimum ([0-9]{1,12}), "
    r"using ([0-9]{1,12})\n?\Z"
)


MAX_TOOLS_NEGATIVE_RE = re.compile(
    r"Error: --max-tools must be a non-negative integer "
    r"\(0 means use template default\)\n?\Z"
)


MAX_TOKENS_BUDGET_NEGATIVE_RE = re.compile(
    r"Error: --max-tokens-budget must be a non-negative integer "
    r"\(0 means unlimited\)\n?\Z"
)


CURRENT_NUMERIC_CLI_CONTRACT: dict[str, object] = {
    "max_tokens_budget": {
        "cases": {
            "invalid_below": {"effective": None, "input": -1, "outcome": "rejected"},
            "minimum": {"effective": 1, "input": 1, "outcome": "accepted"},
            "omitted": {"effective": "unlimited", "input": None, "outcome": "accepted"},
            "representative": {"effective": 30_000, "input": 30_000, "outcome": "accepted"},
            "sentinel": {"effective": "unlimited", "input": 0, "outcome": "accepted"},
        },
        "maximum": None,
        "owner": "ocr-cli",
    },
    "max_tools": {
        "cases": {
            "invalid_below": {"effective": None, "input": -1, "outcome": "rejected"},
            "minimum": {"effective": 100, "input": 50, "outcome": "accepted"},
            "minimum_minus_one": {
                "effective": 100,
                "input": 49,
                "outcome": "normalized",
                "reported_normalization": 50,
            },
            "omitted": {"effective": 100, "input": None, "outcome": "accepted"},
            "representative": {"effective": 101, "input": 101, "outcome": "accepted"},
            "sentinel": {"effective": 100, "input": 0, "outcome": "accepted"},
        },
        "maximum": None,
        "owner": "ocr-template-or-higher-cli",
        "reported_minimum": 50,
    },
    "result": "passed",
}


CURRENT_LANGUAGE_RULES = {
    "views/page.pug": "**/*.pug",
    "views/page.jinja2": "**/*.{jinja2,j2}",
    "views/component.j2": "**/*.{jinja2,j2}",
    "rtl/module.v": "**/*.{v,sv,vh}",
    "rtl/include.vh": "**/*.{v,sv,vh}",
    "rtl/module.sv": "**/*.{v,sv,vh}",
    "rtl/entity.vhd": "**/*.{vhd,vhdl}",
    "rtl/entity.vhdl": "**/*.{vhd,vhdl}",
    "src/module.mjs": "**/*.{ts,js,tsx,jsx,mjs,cjs}",
    "src/module.cjs": "**/*.{ts,js,tsx,jsx,mjs,cjs}",
    "native/source.cxx": "**/*.{cpp,cc,cxx,hpp,hxx}",
    "native/header.hxx": "**/*.{cpp,cc,cxx,hpp,hxx}",
    "native/object.mm": "**/*.mm",
    "src/parser.ml": "**/*.{ml,mli}",
    "src/parser.mli": "**/*.{ml,mli}",
    "src/component.re": "**/*.{re,rei}",
    "src/component.rei": "**/*.{re,rei}",
    "scripts/setup.kts": "**/*.{kt,kts}",
    "policies/authz.rego": "**/*.rego",
    "types/interface.pyi": "**/*.{py,pyi,ipynb}",
    "src/Program.fs": "**/*.{fs,fsi,fsx}",
    "src/Program.fsi": "**/*.{fs,fsi,fsx}",
    "scripts/check.fsx": "**/*.{fs,fsi,fsx}",
    "scripts/setup.ps1": "**/*.{ps1,psm1,psd1}",
    "scripts/module.psm1": "**/*.{ps1,psm1,psd1}",
    "scripts/module.psd1": "**/*.{ps1,psm1,psd1}",
    "scripts/setup.nu": "**/*.nu",
    "shaders/main.glsl": "**/*.{glsl,hlsl,wgsl,metal}",
    "shaders/main.hlsl": "**/*.{glsl,hlsl,wgsl,metal}",
    "shaders/main.wgsl": "**/*.{glsl,hlsl,wgsl,metal}",
    "shaders/main.metal": "**/*.{glsl,hlsl,wgsl,metal}",
    "infra/main.tofu": "**/*.{tf,tofu,hcl,tfvars}",
}


CURRENT_DEFAULT_EXCLUDED_PATHS = (
    "src/test/kotlin/scripts/Example.kts",
    "test/parser.ml",
    "src/test_helpers.py",
    "src/WidgetTest.fs",
    "node_modules/example/index.ts",
    "dist/generated.js",
)


PYTEST_PREFIX_EXCLUDED_PATH = "src/test_helpers.py"


PYTEST_PREFIX_CONTROL_PATHS = ("src/contest_helpers.py", "src/test_helpers.go")


GRACE_COMPLETION_CUTOFF = (1, 13, 1)


LANGUAGE_1_13_2_CUTOFF = (1, 13, 2)


POWERSHELL_SCRIPT_PATH = "scripts/setup.ps1"


LANGUAGE_1_13_2_PATHS = (
    "scripts/module.psm1",
    "scripts/module.psd1",
    "scripts/setup.nu",
    "shaders/main.glsl",
    "shaders/main.hlsl",
    "shaders/main.wgsl",
    "shaders/main.metal",
    "infra/main.tofu",
)


REQUIRED_ASSETS = {
    "opencodereview-darwin-amd64",
    "opencodereview-darwin-arm64",
    "opencodereview-linux-amd64",
    "opencodereview-linux-arm64",
    "opencodereview-windows-amd64.exe",
    "opencodereview-windows-arm64.exe",
    "sha256sum.txt",
}


KNOWN_OPTIONAL_CAPABILITIES = {
    "llm_result_identity",
    "per_run_model_override",
    "per_run_provider_override",
    "review_effort",
    "semantic_grouping",
}


QUALIFICATION_STATUS_SCHEMA = "ocr-toolkit.compatibility-status/v1"


QUALIFICATION_PHASES = {"environment", "metadata", "artifact", "contracts", "evidence", "complete"}


QUALIFICATION_REASONS = {
    "dependency-setup-failed",
    "metadata-invalid",
    "metadata-request-failed",
    "artifact-verification-failed",
    "contract-probe-failed",
    "evidence-write-failed",
    "issue-body-write-failed",
    "status-write-failed",
    "unexpected-error",
    "compatible",
}


QUALIFICATION_FAILURE_REASONS = {
    "environment": frozenset({"dependency-setup-failed"}),
    "metadata": frozenset({"metadata-invalid", "metadata-request-failed", "unexpected-error"}),
    "artifact": frozenset({"artifact-verification-failed", "unexpected-error"}),
    "contracts": frozenset({"contract-probe-failed", "unexpected-error"}),
    "evidence": frozenset(
        {
            "evidence-write-failed",
            "issue-body-write-failed",
            "status-write-failed",
            "unexpected-error",
        }
    ),
}


T = TypeVar("T")
