"""Vary XML structure and literal values rather than project-specific examples."""

from xml.sax.saxutils import escape, quoteattr

from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.evidence.ecosystems.dotnet import parse_msbuild


@given(
    package=st.from_regex(r"[A-Za-z][A-Za-z0-9_.]{0,30}", fullmatch=True),
    version=st.tuples(st.integers(0, 99), st.integers(0, 99), st.integers(0, 999)).map(
        lambda parts: ".".join(map(str, parts))
    ),
    conditional=st.booleans(),
    child_version=st.booleans(),
    namespace=st.booleans(),
)
def test_literal_declarations_preserve_scope_and_version(
    package: str, version: str, conditional: bool, child_version: bool, namespace: bool
) -> None:
    """Preserve literal package values and inherited conditions across XML forms."""
    condition = ' Condition="flag"' if conditional else ""
    declaration = f"<PackageReference Include={quoteattr(package)}"
    declaration += (
        f"><Version>{escape(version)}</Version></PackageReference>"
        if child_version
        else f" Version={quoteattr(version)}/>"
    )
    xml = (
        "<Project"
        + (' xmlns="http://schemas.microsoft.com/developer/msbuild/2003"' if namespace else "")
        + f"><ItemGroup{condition}>{declaration}</ItemGroup></Project>"
    )
    result = parse_msbuild(xml)
    facts = [fact for fact in result.facts if fact.kind == "dependency.declared"]
    assert len(facts) == 1
    assert facts[0].value["name"] == package
    assert facts[0].value["version"] == version
    assert facts[0].value["conditions"] == (["flag"] if conditional else [])
    assert result.runtime_dependent == conditional


@given(
    st.sampled_from(["TargetFramework", "Nullable", "LangVersion"]),
    st.text(alphabet="abc<>;&\"'012", max_size=40),
)
def test_escaped_literal_text_is_not_reinterpreted_as_markup(name: str, value: str) -> None:
    """Keep escaped XML scalar content as declaration data rather than nested elements."""
    result = parse_msbuild(
        f"<Project><PropertyGroup><{name}>{escape(value)}</{name}></PropertyGroup></Project>"
    )
    fact = next(fact for fact in result.facts if fact.kind == "dotnet.property")
    assert fact.value["value"] == value.strip()


@given(
    st.integers(0, 255),
    st.sampled_from(["PackageReference", "FrameworkReference", "PackageVersion"]),
)
def test_msbuild_escaped_item_names_never_claim_literal_completeness(code, element):
    """Retain every percent escape as raw data without inventing evaluated identity."""
    name = f"Example%{code:02X}.Item"
    result = parse_msbuild(
        f'<Project><ItemGroup><{element} Include="{name}"/></ItemGroup></Project>'
    )
    assert result.runtime_dependent
    assert any(fact.value.get("name") == name for fact in result.facts)
