"""Grammar and construction bounds for static .NET manifest parsers."""

import json

import pytest

from ocr_toolkit.evidence.ecosystems.dotnet import (
    parse_global_json,
    parse_msbuild,
    parse_packages_lock,
)


@pytest.mark.parametrize(
    "body",
    [
        "<Project>" + "<ItemGroup>" * 32 + "</ItemGroup>" * 32 + "</Project>",
        "<Project " + " ".join(f'a{i}="x"' for i in range(33)) + "/>",
        '<Project Sdk="' + "x" * 4097 + '"/>',
        "<Project>" + "x" * 4097 + "</Project>",
        "<Project>" + "<ItemGroup/>" * 4096 + "</Project>",
        "x" * 1_000_001,
        "界" * 333_334,
    ],
)
def test_xml_construction_bounds(body: str) -> None:
    with pytest.raises(ValueError):
        parse_msbuild(body)


def test_xml_fact_limit_and_semantic_identity() -> None:
    body = "".join(f'<PackageReference Include="Package{i}" Version="1.0"/>' for i in range(600))
    parsed = parse_msbuild("<Project><ItemGroup>" + body + "</ItemGroup></Project>")
    assert len(parsed.facts) == 512
    assert parsed.runtime_dependent and any("truncated" in notice for notice in parsed.notices)
    original = parse_msbuild(
        "<Project><PropertyGroup><Nullable>enable</Nullable></PropertyGroup></Project>"
    )
    changed = parse_msbuild(
        "<Project><PropertyGroup><LangVersion>12</LangVersion><Nullable>disable</Nullable></PropertyGroup></Project>"
    )
    before = next(fact for fact in original.facts if fact.kind == "dotnet.property")
    after = next(fact for fact in changed.facts if fact.value.get("name") == "Nullable")
    assert before.identity == after.identity and before.value != after.value


@pytest.mark.parametrize(
    "text",
    [
        "[]",
        "{}",
        '{"version":true,"dependencies":{}}',
        '{"version":3,"dependencies":{}}',
        '{"version":1,"dependencies":[]}',
        '{"version":1,"dependencies":{"net9.0":[]}}',
        '{"version":1,"version":1,"dependencies":{}}',
        '{"version":1,"dependencies":{"net9.0":{"P":[]}}}',
        '{"version":1,"dependencies":{"net9.0":{"P":{"type":[]}}}}',
        '{"version":1,"dependencies":{"net9.0":{"P":{"type":"Unknown"}}}}',
        '{"version":1,"dependencies":{"net9.0":{"P":{"type":"Direct","resolved":3}}}}',
        '{"version":1,"dependencies":{"net9.0":{"P":{"type":"Direct","resolved":"1","requested":[]}}}}',
        '{"version":1,"dependencies":{"":{"P":{"type":"Direct"}}}}',
        '{"version":1,"dependencies":{"net9.0":{"":{"type":"Direct"}}}}',
        '{"version":1,"dependencies":{},"unknown":NaN}',
    ],
)
def test_malformed_lock_inputs_fail_closed(text: str) -> None:
    with pytest.raises(ValueError):
        parse_packages_lock(text)


@pytest.mark.parametrize(
    "text",
    [
        '{"sdk":[]}',
        '{"sdk":{"version":3}}',
        '{"sdk":{"rollForward":false}}',
        '{"sdk":{"allowPrerelease":"true"}}',
        '{"sdk":{"paths":{}}}',
        '{"sdk":{"paths":[1]}}',
        '{"sdk":{"version":"' + "x" * 4097 + '"}}',
        '{"sdk":{},"extra":' + "[" * 33 + "0" + "]" * 33 + "}",
        '{"sdk":{},"extra":[' + ",".join("0" for _ in range(16_385)) + "]}",
        "[" * 2_000 + "0" + "]" * 2_000,
    ],
)
def test_malformed_sdk_inputs_fail_closed(text: str) -> None:
    with pytest.raises(ValueError):
        parse_global_json(text)


def test_lock_fact_limit_and_sdk_options() -> None:
    result = parse_packages_lock(
        json.dumps(
            {
                "version": 1,
                "dependencies": {
                    "net9.0": {
                        f"Package{i}": {"type": "Direct", "resolved": "1.0"} for i in range(513)
                    }
                },
            }
        )
    )
    assert len(result.facts) == 512 and result.notices
    sdk = parse_global_json('{"sdk":{"allowPrerelease":false,"paths":[".sdk"]}}')
    assert sdk.facts[0].value["allowPrerelease"] is False


def test_xml_namespace_conditions_children_and_sdk() -> None:
    parsed = parse_msbuild("""<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003" Sdk="Microsoft.NET.Sdk">
<PropertyGroup Condition="'$(Mode)' == 'release'"><TargetFramework>net9.0</TargetFramework><LangVersion>preview</LangVersion></PropertyGroup>
<ItemGroup><PackageReference Include="Example"><Version>2.3.4</Version><VersionOverride>5.0</VersionOverride></PackageReference></ItemGroup></Project>""")
    properties = [fact.value for fact in parsed.facts if fact.kind == "dotnet.property"]
    assert properties[0]["conditions"] == ["'$(Mode)' == 'release'"]
    assert properties[0]["value"] == "net9.0"
    dependency = next(fact.value for fact in parsed.facts if fact.kind == "dependency.declared")
    assert dependency["version"] == "2.3.4"
    assert dependency["version_overrides"] == ("5.0",)
    assert parsed.notices


def test_json_sdk_and_framework_scoped_lock() -> None:
    sdk = parse_global_json('{"sdk":{"version":"9.0.100","rollForward":"latestFeature"}}')
    assert sdk.facts[0].value["version_state"] == "declared"
    lock = parse_packages_lock(
        json.dumps(
            {
                "version": 2,
                "dependencies": {
                    "net8.0": {
                        "Example": {"type": "Direct", "requested": "[1.0,)", "resolved": "1.2"}
                    },
                    "net9.0": {
                        "Example": {"type": "Transitive", "resolved": "2.0"},
                        "Sibling": {"type": "Project"},
                    },
                },
            }
        )
    )
    assert len(lock.facts) == 2
    assert {fact.value["scope"] for fact in lock.facts} == {"direct", "transitive"}
    assert {fact.value["framework"] for fact in lock.facts} == {"net8.0", "net9.0"}


@pytest.mark.parametrize(
    "text",
    [
        "<!DOCTYPE Project><Project/>",
        '<!DOCTYPE Project [<!ENTITY x "secret">]><Project>&x;</Project>',
        '<!DOCTYPE Project SYSTEM "https://example.invalid/evil"><Project/>',
        "<Project>",
        "<NotProject/>",
        "",
    ],
)
def test_xml_rejects_malformed_or_entity_inputs(text: str) -> None:
    with pytest.raises(ValueError):
        parse_msbuild(text)


@pytest.mark.parametrize("declarations,attributes", [(33, 0), (17, 16), (1, 32)])
def test_namespaces_share_the_per_element_attribute_budget(declarations, attributes):
    names = " ".join(f'xmlns:n{i}="urn:{i}"' for i in range(declarations))
    values = " ".join(f'a{i}="x"' for i in range(attributes))
    with pytest.raises(ValueError):
        parse_msbuild(f"<Project {names} {values}/>")


@pytest.mark.parametrize(
    "value",
    [
        '<Project xmlns="' + "x" * 4097 + '"/>',
        "<Project xmlns:" + "x" * 4097 + '="urn:example"/>',
    ],
)
def test_namespace_values_are_bounded_before_expanded_names(value):
    with pytest.raises(ValueError):
        parse_msbuild(value)


def test_namespace_budget_resets_at_each_element():
    declarations = " ".join(f'xmlns:n{i}="urn:{i}"' for i in range(32))
    assert parse_msbuild(
        f'<Project xmlns=""><ItemGroup {declarations}/><PropertyGroup {declarations}/></Project>'
    ).facts
