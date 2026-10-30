"""Source semantics must survive the real proof/publication boundary."""

from __future__ import annotations

import pytest

from ocr_toolkit import review_runner
from ocr_toolkit.evidence.opaque_code import prove_opaque_code


def projected_source(
    source: str,
    *,
    line: int = 2,
    path: str = "src/parser.py",
    prose: str = "Inspect this source expression.",
):
    excerpt = source.splitlines()[line - 1]
    comment = {
        "path": path,
        "start_line": line,
        "end_line": line,
        "content": prose,
        "existing_code": excerpt,
    }
    proof = prove_opaque_code(comment, path, lambda _path: source)
    assert proof.existing_verified
    result, publication, _ = review_runner._publication_projection(
        {"status": "success", "warnings": [], "comments": [comment]},
        forbidden=(),
        allowed_tools=frozenset(),
        code_proof=lambda _comment: proof,
    )
    return result, publication, excerpt


@pytest.mark.parametrize(
    "expression",
    [
        'token = "".join(parts)',
        "token = parts[index]",
        "api_token = parse_parts(parts)",
        "password: str",
        "token = None",
        "return build(token=parts)",
        "token = parts[start:end]",
        'token = ""',
    ],
)
def test_source_reference_and_empty_binding_survive_real_publication(expression) -> None:
    source = "def parse(parts, index=0, start=0, end=1):\n    " + expression + "\n"
    result, publication, excerpt = projected_source(source)
    assert result["comments"][0].get("existing_code") == excerpt
    assert publication["state"] == "passed"


@pytest.mark.parametrize(
    "expression",
    [
        'token = "synthetic-short-credential"',
        "password = 1234",
        'token = decode("synthetic-encoded-material")',
        'token = f"prefix-{parts}"',
        "token = parts  # password=synthetic-short-value",
        "token = parts  # contact +1 202-555-0114",
        "token = parts  # person@example.invalid",
        r"token = parts  # 202\-555\-0114",
        "token = parts  # 202 **555** 0114",
        "token = parts  # 202 *555* 0114",
    ],
)
def test_source_provenance_does_not_authorize_literal_secrets_or_contacts(expression) -> None:
    result, publication, _ = projected_source("def parse(parts):\n    " + expression + "\n")
    assert "existing_code" not in result["comments"][0]
    assert publication["state"] == "publication-filtered"


def test_code_shaped_prose_inside_docstring_does_not_get_a_syntax_waiver() -> None:
    result, publication, _ = projected_source('"""Example:\ntoken = shortCredential\n"""\n')
    assert "existing_code" not in result["comments"][0]
    assert publication["state"] == "publication-filtered"


def test_source_proof_does_not_waive_mandatory_finding_prose() -> None:
    result, publication, _ = projected_source(
        'def parse(parts):\n    token = "".join(parts)\n', prose="token = parse_parts(parts)"
    )
    assert not result["comments"]
    assert publication["state"] == "publication-filtered"


@pytest.mark.parametrize(
    "path", ["src/script", "src/example.txt", "src/example.py", "src/example.pyi"]
)
@pytest.mark.parametrize(
    "source",
    [
        "token: syntheticShortCredential\n",
        "token=syntheticShortCredential\n",
        '{"token":"syntheticShortCredential"}\n',
        'const token = "syntheticShortCredential";\n',
    ],
)
def test_file_extension_cannot_authorize_data_or_unknown_syntax(path, source) -> None:
    result, publication, _ = projected_source(source, line=1, path=path)
    assert "existing_code" not in result["comments"][0]
    assert publication["state"] == "publication-filtered"


@pytest.mark.parametrize("path", ["bin/parser", "src/parser.py", "src/parser.txt"])
def test_full_source_syntax_is_independent_of_extension(path) -> None:
    result, _, excerpt = projected_source(
        'def parse(parts):\n    token = "".join(parts)\n', path=path
    )
    assert result["comments"][0].get("existing_code") == excerpt


@pytest.mark.parametrize(
    "path,source,line",
    [
        ("src/a.c", "int main(void) {\n  int size = 1024*1024;\n}\n", 2),
        ("src/a.js", "function size() {\n  const bytes = 1024*1024;\n}\n", 2),
        ("bin/limits", '#!/bin/sh\nbytes="1024*1024"\n', 2),
    ],
)
def test_literal_renderer_fix_does_not_require_python(path, source, line) -> None:
    result, _, excerpt = projected_source(source, path=path, line=line)
    assert result["comments"][0].get("existing_code") == excerpt


@pytest.mark.parametrize(
    "source",
    [
        "int main(void) {\n  int size = 2 *1024*1024;\n}\n",
        "function size() {\n  const bytes = 2 *1024*1024;\n}\n",
        '#!/bin/sh\nbytes="2 *1024*1024"\n',
    ],
)
def test_unknown_numeric_interpretation_preserves_strict_checks_and_finding(source):
    result, publication, _ = projected_source(source, path="source", line=2)
    assert len(result["comments"]) == 1 and "existing_code" not in result["comments"][0]
    assert publication["state"] == "publication-filtered"


def test_source_context_cannot_cross_text_or_prose_boundaries() -> None:
    from ocr_toolkit.context.contracts import TextBudgets
    from ocr_toolkit.context.dlp import check_text

    source = 'def parse(parts):\n    token = "".join(parts)\n'
    comment = {
        "path": "src",
        "start_line": 2,
        "end_line": 2,
        "existing_code": source.splitlines()[1],
    }
    proof = prove_opaque_code(comment, "src", lambda _path: source)
    assert proof.existing_context is not None
    budgets = TextBudgets(20000, 80000, 300)
    assert not check_text(
        comment["existing_code"],
        budgets=budgets,
        publication=True,
        code_context=proof.existing_context,
    ).admitted
    assert not check_text(
        'token = "synthetic-short-value"',
        budgets=budgets,
        publication=True,
        allow_opaque_code=True,
        code_context=proof.existing_context,
    ).admitted


def test_full_source_docstring_and_comment_roles_stay_strict_with_real_declarations() -> None:
    for source in (
        '"""Example:\ntoken = shortCredential\n"""\ndef parse():\n    pass\n',
        "def parse():\n    # token = shortCredential\n    pass\n",
    ):
        result, _, _ = projected_source(source)
        assert "existing_code" not in result["comments"][0]


def test_environment_snapshot_and_unique_view_checks_are_scoped_to_one_admission(
    monkeypatch,
) -> None:
    from ocr_toolkit.context.contracts import TextBudgets
    from ocr_toolkit.context.dlp import admission as dlp

    budgets = TextBudgets(20000, 80000, 300)
    collected = []
    checked = []
    original_collect = dlp.environment_secret_values
    original_check = dlp.has_sensitive_material

    def collect():
        collected.append(True)
        return original_collect()

    def classify(value, **kwargs):
        checked.append(value)
        return original_check(value, **kwargs)

    monkeypatch.setattr(dlp, "environment_secret_values", collect)
    monkeypatch.setattr(dlp, "has_sensitive_material", classify)
    assert dlp.check_text("amount = 17", budgets=budgets, publication=True).admitted
    assert len(collected) == 1 and checked == ["amount = 17"]
    monkeypatch.setenv("OCR_LLM_TOKEN", "amount = 17")
    assert not dlp.check_text("amount = 17", budgets=budgets, publication=True).admitted
    assert len(collected) == 2


@pytest.mark.parametrize(
    "value",
    [
        "The api key identifies a field.",
        "Use an auth token reference.",
        "token=***",
        "Authorization: ***",
    ],
)
def test_diagnostic_normalization_and_masked_markers_are_not_material(value) -> None:
    from ocr_toolkit.common.redaction import has_sensitive_material

    assert not has_sensitive_material(value)
    assert has_sensitive_material(value + "\npassword=synthetic-short-value")


def project_whole_source(source):
    comment = {
        "path": "source",
        "start_line": 1,
        "end_line": len(source.splitlines()),
        "content": "Inspect this implementation.",
        "existing_code": source.rstrip("\n"),
    }
    proof = prove_opaque_code(comment, "source", lambda _path: source)
    assert proof.existing_verified
    result, publication, _ = review_runner._publication_projection(
        {"status": "success", "comments": [comment], "warnings": []},
        forbidden=(),
        allowed_tools=frozenset(),
        code_proof=lambda _comment: proof,
    )
    return result, publication


@pytest.mark.parametrize(
    "source",
    [
        'def parse():\n    return {"password=syntheticShortCredential": None}\n',
        "#!/bin/sh\nimport os\ntoken=syntheticShortCredential\n",
        "#!/usr/bin/env sh\nimport os\ntoken=syntheticShortCredential\n",
        "import os\ntoken=syntheticShortCredential\n",
        'def parse():\n    value="syntheticShortCredential"\n    password=value\n',
        'def parse():\n    value="syntheticShortCredential"\n    alias=value\n    password=alias\n',
        'def parse():\n    value="syntheticShortCredential"\n    send(password=value)\n',
        'def parse(value="syntheticShortCredential"):\n    password=value\n',
        'def fetch():\n    return "syntheticShortCredential"\ndef parse():\n    password=fetch()\n',
        'def parse(parts):\n    value=f"synthetic-{parts}"\n    password=value\n',
    ],
)
def test_literal_material_and_contradictory_formats_never_gain_source_waivers(source) -> None:
    result, publication = project_whole_source(source)
    assert "existing_code" not in result["comments"][0]
    assert publication["state"] == "publication-filtered"


@pytest.mark.parametrize("expression", ["token=parts", 'token=""', "token=None", "token=token"])
def test_source_assignment_spacing_does_not_change_admission(expression) -> None:
    result, publication, excerpt = projected_source("def parse(parts):\n    " + expression + "\n")
    assert result["comments"][0]["existing_code"] == excerpt
    assert publication["state"] == "passed"


def test_reference_only_excerpt_can_survive_material_outside_its_published_span() -> None:
    result, publication, excerpt = projected_source(
        'def parse(value="syntheticShortCredential"):\n    password=value\n'
    )
    assert result["comments"][0]["existing_code"] == excerpt
    assert publication["state"] == "passed"


def test_same_text_in_docstring_and_code_uses_distinct_scoped_contexts() -> None:
    source = '"""Example:\n    token = "".join(parts)\n"""\ndef parse(parts):\n    token = "".join(parts)\n'
    comments = [
        dict(
            path="source",
            start_line=line,
            end_line=line,
            content="Inspect the statement.",
            existing_code=source.splitlines()[line - 1],
        )
        for line in (2, 5)
    ]
    cache = {}
    result, publication, _ = review_runner._publication_projection(
        {"status": "success", "warnings": [], "comments": comments},
        forbidden=(),
        allowed_tools=frozenset(),
        code_proof=lambda comment: prove_opaque_code(
            comment, "source", lambda _path: source, syntax_cache=cache
        ),
    )
    assert "existing_code" not in result["comments"][0]
    assert result["comments"][1]["existing_code"] == comments[1]["existing_code"]
    assert publication["omitted"]["fields"] == 1


@pytest.mark.parametrize(
    "spans",
    [
        None,
        [(0, 5)],
        (None,),
        ((True, 5),),
        ((5, 2),),
        ((-1, 5),),
        ((0, 500),),
        ((0, 5), (2, 4)),
        ((0, 1),) * 4097,
    ],
)
def test_malformed_context_spans_fail_closed(spans) -> None:
    import hashlib

    from ocr_toolkit.context.code_text import CodeTextContext

    value = "token=parts"
    context = CodeTextContext(hashlib.sha256(value.encode()).hexdigest(), spans)
    assert context.credential_view(value) == value


@pytest.mark.parametrize(
    "limit,value", [("MAX_SYNTAX_CHARS", 16), ("MAX_SYNTAX_NODES", 2), ("MAX_KEY_SPANS", 0)]
)
def test_syntax_resource_limits_keep_source_credentials_strict(monkeypatch, limit, value) -> None:
    from ocr_toolkit.evidence import source_syntax

    monkeypatch.setattr(source_syntax, limit, value)
    source = 'def parse(parts):\n    token = "".join(parts)\n'
    result, publication, _ = projected_source(source)
    assert "existing_code" not in result["comments"][0]
    assert publication["state"] == "publication-filtered"


def test_syntax_token_budget_and_invalid_python_do_not_grant_interpretation(monkeypatch) -> None:
    from ocr_toolkit.evidence import source_syntax

    monkeypatch.setattr(source_syntax, "MAX_SYNTAX_NODES", 30)
    assert (
        source_syntax.analyze_python_source("# comment\n" * 100 + "def parse():\n    pass\n")
        is None
    )
    for source in ("def parse(:\n pass", "def parse(parts):\n\f token=parts\n"):
        assert source_syntax.analyze_python_source(source) is None


@pytest.mark.parametrize(
    "header", ["#!/usr/bin/python3", "#!/usr/bin/env python3", "#!/usr/bin/env -S python3 -I"]
)
def test_explicit_python_interpreter_can_qualify_import_only_module(header) -> None:
    source = header + "\nfrom library import parts\ntoken=parts\n"
    result, publication, excerpt = projected_source(source, line=3, path="bin/tool")
    assert result["comments"][0]["existing_code"] == excerpt
    assert publication["state"] == "passed"


@pytest.mark.parametrize(
    "header",
    ["#!", "#!/usr/bin/env", "#!/usr/bin/env -S", "#!/usr/bin/env -u python3 sh", "#!/bin/sh"],
)
def test_unknown_and_other_interpreters_keep_strict_material_checks(header) -> None:
    source = header + "\nimport os\ntoken=syntheticShortCredential\n"
    result, publication = project_whole_source(source)
    assert "existing_code" not in result["comments"][0]
    assert publication["state"] == "publication-filtered"


def test_syntax_cache_is_bounded_and_never_reuses_changed_source() -> None:
    from ocr_toolkit.evidence.opaque_code import MAX_SYNTAX_CACHE_FILES

    cache = {}
    source = "def parse(parts):\n    token=parts\n"
    for number in range(MAX_SYNTAX_CACHE_FILES + 3):
        path = f"source-{number}"
        comment = dict(path=path, start_line=2, end_line=2, existing_code=source.splitlines()[1])
        assert (
            prove_opaque_code(
                comment, path, lambda _path: source, syntax_cache=cache
            ).existing_context
            is not None
        )
        assert len(cache) <= MAX_SYNTAX_CACHE_FILES
    path = "changing-source"
    comment = dict(path=path, start_line=2, end_line=2, existing_code="    token=parts")
    proven = prove_opaque_code(comment, path, lambda _path: source, syntax_cache=cache)
    data = '"""Example:\n    token=parts\n"""\ndef parse(parts):\n    pass\n'
    strict = prove_opaque_code(comment, path, lambda _path: data, syntax_cache=cache)
    assert proven.existing_context is not None and strict.existing_context is None
    assert len(cache) <= MAX_SYNTAX_CACHE_FILES


@pytest.mark.parametrize("count", [50, 400])
def test_many_proofs_prepare_one_source_once(monkeypatch, count) -> None:
    from ocr_toolkit.evidence import opaque_code

    source = "def parse(parts):\n" + "    token=parts\n" * count
    original = opaque_code._prepare_source
    work = []

    def prepare(value):
        work.append(len(value))
        return original(value)

    monkeypatch.setattr(opaque_code, "_prepare_source", prepare)
    cache = {}
    for line in range(2, count + 2):
        comment = dict(
            path="source", start_line=line, end_line=line, existing_code="    token=parts"
        )
        assert prove_opaque_code(
            comment, "source", lambda _path: source, syntax_cache=cache
        ).existing_verified
    assert work == [len(source)]


@pytest.mark.parametrize(
    "secret", ["synthetic-a\u0301bcZ-credential", " synthetic-private-credential "]
)
def test_configured_values_are_checked_before_text_normalization(monkeypatch, secret) -> None:
    from ocr_toolkit.context.contracts import TextBudgets
    from ocr_toolkit.context.dlp import check_text

    monkeypatch.setenv("OCR_LLM_TOKEN", secret)
    assert not check_text(secret, budgets=TextBudgets(20000, 80000, 300), publication=True).admitted


@pytest.mark.parametrize("key", ["syntheticShortCredential", "password", "token"])
def test_dictionary_keys_remain_literal_material_even_when_they_look_like_labels(key) -> None:
    source = f"def parse():\n    values={{{key!r}: None}}\n    password=next(iter(values))\n"
    result, publication = project_whole_source(source)
    assert "existing_code" not in result["comments"][0]
    assert publication["state"] == "publication-filtered"


def test_repository_without_python_files_crosses_real_git_proof_and_audit(tmp_path) -> None:
    import subprocess
    import time

    from ocr_toolkit.common.git import isolated_git_environment
    from ocr_toolkit.dlp_audit.corpus import capture, cleanup, manifest
    from ocr_toolkit.dlp_audit.scanner import scan
    from ocr_toolkit.dlp_audit.state import State

    root = tmp_path.resolve() / "source"
    root.mkdir()
    sources = {
        "main.c": "#include <stdint.h>\nint main(void) {\n  int bytes = 1024*1024;\n}\n",
        "main.js": "function bytes() {\n  const size = 1024*1024;\n}\n",
        "settings.json": '{"password":"syntheticShortCredential"}\n',
    }
    for name, text in sources.items():
        (root / name).write_text(text)
    prefix = [
        "git",
        "-C",
        str(root),
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "commit.gpgsign=false",
        "-c",
        "user.name=Synthetic Author",
        "-c",
        "user.email=author@example.invalid",
    ]
    for arguments in (["init", "-q"], ["add", "."], ["commit", "-qm", "synthetic input"]):
        subprocess.run(
            [*prefix, *arguments], env=isolated_git_environment(), check=True, capture_output=True
        )
    with State(tmp_path.resolve() / "private-state", create=True) as state:
        identity = capture(state, root=root, git_ref="HEAD", deadline=time.monotonic() + 30)
        try:
            data = manifest(state, identity)
            _, result = scan(state, identity, deadline=time.monotonic() + 30)
            slots = {item["path"]: item["slot"] for item in data["files"]}
            assert result["complete"]
            assert not any(
                hit["role"] == "existing_code"
                and hit["slot"] in {slots["main.c"], slots["main.js"]}
                for hit in result["hits"]
            )
            assert any(
                hit["role"] == "existing_code" and hit["slot"] == slots["settings.json"]
                for hit in result["hits"]
            )
        finally:
            cleanup(state, identity)


@pytest.mark.parametrize(
    "value",
    [
        "call +1 **202**-555-0114",
        "call +1 *202-555-0114",
        "call 202 **555** 0114",
        "call +1 <b>202</b>-555-0114",
        "person**@**example.invalid",
        "pass**word**=syntheticShortCredential",
        r"202\-555\-0114",
        "202 **555** 0114",
        "202 *555* 0114",
        "ｃａｌｌ ＋１ ＊＊２０２＊＊－５５５－０１１４",  # noqa: RUF001 - minimized Unicode regression
    ],
)
def test_literal_sink_keeps_independent_obfuscated_material_checks(value) -> None:
    from ocr_toolkit.context.code_text import TextSink
    from ocr_toolkit.context.contracts import TextBudgets
    from ocr_toolkit.context.dlp import check_text

    assert not check_text(
        value,
        budgets=TextBudgets(20000, 80000, 300),
        publication=True,
        allow_opaque_code=True,
        sink=TextSink.LITERAL_CODE,
    ).admitted


@pytest.mark.parametrize("path", ("settings", "unknown.ext", "workflow.yml"))
def test_origin_and_filename_cannot_declassify_application_permission_literals(path):
    source = "permissions:\n  id-token: write\n  contents: read\n"
    result, _, excerpt = projected_source(source, path=path, line=2)
    assert "existing_code" not in result["comments"][0]
    from ocr_toolkit.context.contracts import TextBudgets
    from ocr_toolkit.context.dlp import check_text

    assert not check_text(excerpt, budgets=TextBudgets(2000, 8000, 10), publication=True).admitted


@pytest.mark.parametrize(
    "source,line",
    (
        ("other:\n  id-token: write\n", 2),
        ("permissions:\n  id-token: synthetic-material\n", 2),
        ('def example():\n    """permissions:\n      id-token: write\n    """\n', 3),
        ('payload = """\npermissions:\n  password: write\n"""\n', 3),
        ("const payload = `\npermissions:\n  password: write\n`;\n", 3),
        ("payload: |\n  permissions:\n    password: write\n", 3),
        ("payload: >\n  permissions:\n    password: write\n", 3),
    ),
)
def test_permission_roles_cannot_be_borrowed_from_unrelated_or_quoted_structure(source, line):
    result, _, _ = projected_source(source, path="source", line=line)
    assert "existing_code" not in result["comments"][0]
