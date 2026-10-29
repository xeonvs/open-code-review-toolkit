"""Synthetic address grammars, malformed neighbors and whole-unit DLP safety."""

from ipaddress import IPv4Network, IPv6Address

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.context.dlp import check_text

BUDGETS = TextBudgets(2000, 8000, 10)


@st.composite
def network_text(draw):
    host = draw(st.integers(1, 254))
    address = f"192.0.2.{host}"
    form = draw(st.sampled_from(("ipv4", "cidr4", "mask", "ipv6", "cidr6", "mapped")))
    if form == "ipv4":
        return f"IP {address}:{draw(st.integers(1, 65535))}"
    if form == "cidr4":
        return f"network {address}/{draw(st.integers(0, 32))}"
    if form == "mask":
        network = IPv4Network(f"192.0.2.0/{draw(st.integers(0, 32))}", strict=False)
        mask = network.netmask if draw(st.booleans()) else network.hostmask
        return f"network {address}/{mask}"
    if form == "mapped":
        return f"network ::ffff:{address}/{draw(st.integers(0, 128))}"
    ipv6 = IPv6Address(int(IPv6Address("2001:db8::")) | draw(st.integers(0, 2**96 - 1)))
    rendered = ipv6.exploded if draw(st.booleans()) else ipv6.compressed
    if form == "cidr6":
        return f"network {rendered}/{draw(st.integers(0, 128))}"
    return f"IP [{rendered}]:{draw(st.integers(1, 65535))}"


@given(network_text(), st.booleans())
def test_valid_synthetic_network_notation_is_not_a_contact(text, publication):
    result = check_text(text, budgets=BUDGETS, publication=publication)
    assert result.admitted, (text, result.reason, result.detector)
    assert result.text == text


@given(
    network_text(),
    st.sampled_from(
        ("; Call +1 202 555 0142", "; person@example.invalid", '; api_key: "synthetic-secret"')
    ),
    st.booleans(),
)
def test_network_notation_never_exempts_contacts_or_secrets(text, sensitive, prepend):
    mixed = sensitive + "; " + text if prepend else text + sensitive
    result = check_text(mixed, budgets=BUDGETS, publication=True)
    assert not result.admitted and result.reason in {"pii", "secret"}


@given(
    st.integers(256, 999),
    st.integers(33, 999),
    st.sampled_from(("octet", "prefix", "noncontiguous-mask", "leading-zero")),
)
def test_phone_shaped_invalid_ipv4_cannot_get_a_network_exception(octet, prefix, form):
    text = {
        "octet": f"IP 192.0.2.{octet}",
        "prefix": f"network 192.0.2.1/{prefix}",
        "noncontiguous-mask": "network 192.0.2.1/255.0.255.0",
        "leading-zero": "IP 192.000.2.1",
    }[form]
    result = check_text(text, budgets=BUDGETS, publication=True)
    assert not result.admitted and result.reason == "pii"


@given(
    st.lists(st.integers(0, 9999), min_size=4, max_size=4),
    st.integers(1, 9999),
    st.integers(0, 3),
    st.integers(256, 9999),
    st.sampled_from(("", "IP ", "network ", "host ")),
    st.sampled_from(("", "/32", "/255.255.255.0", ":443")),
    st.booleans(),
)
def test_ip_lookalikes_with_any_invalid_octet_remain_phone_candidates(
    octets, first, index, invalid, prefix, suffix, publication
):
    parts = list(octets)
    parts[0] = first
    parts[index] = invalid
    text = prefix + ".".join(str(octet) for octet in parts) + suffix
    checked = check_text(text, budgets=BUDGETS, publication=publication)
    assert not checked.admitted and checked.reason == "pii", text


@pytest.mark.parametrize("prefix", ("", "IP ", "network "))
@pytest.mark.parametrize("suffix", ("", "/32", "/255.255.255.0", ":443"))
def test_invalid_ip_lookalike_minimized_regression(prefix, suffix):
    checked = check_text(prefix + "123.456.789.385" + suffix, budgets=BUDGETS, publication=True)
    assert not checked.admitted and checked.reason == "pii"


@pytest.mark.parametrize("prefix", ("", "IP ", "network "))
def test_prefix_35_is_invalid_for_ipv4_but_valid_for_ipv6(prefix):
    invalid = check_text(prefix + "192.0.2.1/35", budgets=BUDGETS, publication=True)
    assert not invalid.admitted and invalid.reason == "pii"
    for address in ("2001:db8::/35", "::ffff:192.0.2.1/35"):
        valid = check_text(prefix + address, budgets=BUDGETS, publication=True)
        assert valid.admitted and valid.text == prefix + address


@pytest.mark.parametrize(
    "text",
    (
        "IP 2001:db8:::1",
        "IP 2001:db8::gggg",
        "network 2001:db8::/129",
        "network 2001:db8::/-1",
        "IP [2001:db8::1",
        "IP 2001:db8::ffff:192.0.2.999",
        "network ::ffff:192.0.2.1/129",
    ),
)
def test_malformed_ipv6_is_bounded_and_cannot_hide_a_contact(text):
    # DLP is not a network-configuration validator. Malformed syntax without a
    # phone-shaped token may pass; it never suppresses a real neighboring contact.
    result = check_text(text, budgets=BUDGETS, publication=True)
    assert result.reason in {"admitted", "pii"}
    mixed = check_text(text + "; Call +1 202 555 0142", budgets=BUDGETS, publication=True)
    assert not mixed.admitted and mixed.reason == "pii"


@pytest.mark.parametrize(
    "prefix",
    (
        ":::",
        "ffff:",
        "2001:db8::: ",
        "x2001:db8::",
        "_2001:db8::",
        "a" * 64 + "2001:db8::",
        "%2001:db8::",
    ),
)
def test_invalid_ipv6_prefix_cannot_exempt_the_dotted_candidate(prefix):
    checked = check_text(f"network {prefix}192.0.2.1/96", budgets=BUDGETS, publication=True)
    assert not checked.admitted and checked.reason == "pii"


@pytest.mark.parametrize("text", ("network ::ffff:192.0.2.1/96", "network 2001:db8::192.0.2.1/128"))
def test_ipv6_embedded_ipv4_minimized_false_positive(text):
    checked = check_text(text, budgets=BUDGETS, publication=True)
    assert checked.admitted and checked.text == text


@pytest.mark.parametrize(
    "text",
    (
        "network 192.0.2.100/255.255.255.255",
        "network 192.0.2.100/0.0.0.0",
        "network 192.0.2.100/0.0.0.255",
        "network 192.0.2.100/32.",
    ),
)
def test_dotted_network_masks_do_not_depend_on_the_phone_match_length(text):
    checked = check_text(text, budgets=BUDGETS, publication=True)
    assert checked.admitted and checked.text == text


@pytest.mark.parametrize(
    "text",
    (
        "network 192.0.2.100/255.255.255.255.0",
        "network 192.0.2.100/" + "0" * 100 + "32",
        "network " + "a" * 100 + "::ffff:192.0.2.100/96",
        "network 192.0.2.100/32x",
        "network 192.0.2.100/255.255.255.255-1",
        "network ::ffff:192.0.2.1/129",
    ),
)
def test_partial_or_overlong_network_tokens_are_not_technical_exceptions(text):
    checked = check_text(text, budgets=BUDGETS, publication=True)
    assert not checked.admitted and checked.reason == "pii"


@pytest.mark.parametrize("context", ("Call", "phone", "tel", "contact"))
def test_explicit_contact_context_keeps_priority_over_a_network_exception(context):
    checked = check_text(f"{context} 192.0.2.100/32", budgets=BUDGETS, publication=True)
    assert not checked.admitted and checked.reason == "pii"


@pytest.mark.parametrize("port", (-1, 0, 65536, 999999, 2**64))
def test_invalid_port_cannot_create_an_ipv4_exception(port):
    checked = check_text(f"IP 192.0.2.100:{port}", budgets=BUDGETS, publication=True)
    assert not checked.admitted and checked.reason == "pii"


@pytest.mark.parametrize("port", (1, 65000, 65001, 65534, 65535))
def test_valid_port_boundaries_preserve_the_ipv4_value(port):
    text = f"IP 192.0.2.100:{port}"
    checked = check_text(text, budgets=BUDGETS, publication=True)
    assert checked.admitted and checked.text == text


@given(st.integers(65536, 2**64), st.booleans())
def test_out_of_range_ports_cannot_hide_contacts(port, ipv6):
    host = "[2001:db8::1]" if ipv6 else "192.0.2.100"
    text = f"IP {host}:{port}"
    checked = check_text(text + "; Call +1 202 555 0142", budgets=BUDGETS, publication=True)
    assert not checked.admitted and checked.reason == "pii"
