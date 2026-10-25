"""Tests for the top-level ConvertsV2Ray subscription parser.

ConvertsV2Ray is a coroutine; tests drive it with asyncio.run so no
async pytest plugin is required.
"""

import asyncio
import base64

import pytest

from subconv.converter import ConvertsV2Ray
from subconv.converter.util import ParseError

MIXED_SUBSCRIPTION = "\n".join(
    [
        "trojan://pw@t.example.com:443#Dup",
        "trojan://pw@t.example.com:443#Dup",
        "vless://u-1@v.example.com:80#Solo",
        "this is not a link",
    ]
)


def convert(content):
    return asyncio.run(ConvertsV2Ray(content))


def test_mixed_subscription_parses_nodes_and_ignores_annotations():
    result = convert(MIXED_SUBSCRIPTION)
    assert [p["name"] for p in result] == ["Dup", "Dup-01", "Solo"]
    assert result[0]["type"] == "trojan"
    assert result[2]["type"] == "vless"


def test_base64_encoded_subscription_matches_plain():
    # Subscription payloads are usually base64-wrapped; both forms must
    # decode to the same proxy list (round-trip through the wrapper).
    encoded = base64.b64encode(MIXED_SUBSCRIPTION.encode()).decode()
    assert convert(encoded) == convert(MIXED_SUBSCRIPTION)


def test_bytes_input_matches_str_input():
    assert convert(MIXED_SUBSCRIPTION.encode()) == convert(MIXED_SUBSCRIPTION)


def test_empty_input_raises():
    with pytest.raises(Exception, match="No valid proxies found"):
        convert("")


def test_garbage_input_raises():
    with pytest.raises(Exception, match="No valid proxies found"):
        convert("nothing valid here")


def test_all_supported_schemes_dispatch():
    lines = [
        "vmess://eyJwcyI6IlYiLCJhZGQiOiJhLmV4YW1wbGUuY29tIiwicG9ydCI6IjQ0MyIsImlkIjoidS0xIiwiYWlkIjoiMCJ9",
        "vless://u-1@v.example.com:80#V",
        "trojan://pw@t.example.com:443#T",
        "ss://aes-256-gcm:pw@ss.example.com:8388#S",
        "hysteria://hy.example.com:443#H1",
        "hysteria2://auth@hy2.example.com:443#H2",
        "hy2://auth@hy2.example.com:443#H2B",
        "tuic://token@tuic.example.com:443#TU",
        "anytls://pw@a.example.com:443#A",
        "socks5://s.example.com:1080#SO",
        "http://h.example.com:8080#HT",
        "tg://socks?server=tg.example.com&port=1080#TG",
        "mierus://m.example.com?port=2027&protocol=TCP#MI",
    ]
    result = convert("\n".join(lines))
    assert [p["type"] for p in result] == [
        "vmess",
        "vless",
        "trojan",
        "ss",
        "hysteria",
        "hysteria2",
        "hysteria2",
        "tuic",
        "anytls",
        "socks5",
        "http",
        "socks5",
        "mieru",
    ]


def test_https_tme_link_routes_to_telegram_parser():
    result = convert("https://t.me/socks?server=tg.example.com&port=1080&remark=T")
    assert result == [
        {"name": "T", "type": "socks5", "server": "tg.example.com", "port": 1080}
    ]


def test_https_non_tme_link_routes_to_http_parser():
    result = convert("https://secure.example.com:8443#HTTPS")
    assert result[0]["type"] == "http"
    assert result[0]["tls"] is True


def test_mieru_link_expands_to_multiple_proxies():
    line = "mierus://m.example.com?port=2027&protocol=TCP&port=2028&protocol=UDP#M"
    result = convert(line)
    assert len(result) == 2
    assert result[0]["port"] == 2027
    assert result[1]["port"] == 2028


@pytest.mark.parametrize('line,key,expected', [
    ('trojan://pw@example.com:443?allowInsecure=0&allowInsecure=1', 'skip-cert-verify', False),
    ('anytls://pw@example.com:443?sni=one&sni=two', 'sni', 'one'),
    ('tuic://token@example.com:443?sni=one&sni=two', 'sni', 'one'),
    ('hysteria://example.com:443?insecure=0&insecure=1', 'skip-cert-verify', False),
    ('ss://aes-128-gcm:pw@example.com:443?uot=1&uot=0', 'udp-over-tcp', True),
])
def test_duplicate_queries_use_mihomo_first_value(line, key, expected):
    assert convert(line)[0][key] == expected


def test_node_limit_applies_to_ordinary_links_before_parsing_next_node(monkeypatch):
    from subconv.converter import parser
    monkeypatch.setattr(parser, 'MAX_PROXY_NODES', 2)
    assert len(convert('http://a:1#n\n' * 2)) == 2
    with pytest.raises(ParseError, match='Line 3'):
        convert('http://a:1#n\n' * 3)


def test_expansion_limit_covers_ordinary_protocol_fields(monkeypatch):
    from subconv.converter import parser
    monkeypatch.setattr(parser, 'MAX_CONTENT_BYTES', 180)
    line = 'anytls://' + 'x' * 70 + '@a:1#n'
    assert len(line.encode()) < 180
    with pytest.raises(ParseError):
        convert(line)


def test_mieru_expansion_budget_spans_subscription_links(monkeypatch):
    from subconv.converter import parser, mieru

    monkeypatch.setattr(parser, "MAX_CONTENT_BYTES", 2000)
    monkeypatch.setattr(mieru, "MAX_CONTENT_BYTES", 2000)
    line = f"mierus://u:{'x' * 600}@m.example?port=1&protocol=TCP&port=2&protocol=TCP"
    assert len((line + "\n" + line).encode()) < 2000
    assert len(convert(line)) == 2
    with pytest.raises(ParseError, match="Line 2"):
        convert(line + "\n" + line)


def test_ssr_link_dispatches():
    def b64url(text: str) -> str:
        return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")

    inner = f"ssr.example.com:8388:origin:aes-256-cfb:plain:{b64url('pw')}/?remarks={b64url('R')}"
    result = convert("ssr://" + b64url(inner))
    assert result[0]["type"] == "ssr"
    assert result[0]["name"] == "R"


def test_malformed_realm_line_rejects_subscription():
    lines = "\n".join([
        "hy2+realm://bad%GG@realm.example.com/room#Bad",
        "hy2+realm://token@realm.example.com/room?auth=password#Realm",
        "trojan://pw@t.example.com:443#Trojan",
    ])
    with pytest.raises(ParseError, match=r"Line 1 \(hy2\+realm\)"):
        convert(lines)


def test_unexpected_parser_errors_are_not_silenced(monkeypatch):
    from subconv.converter import parser

    def broken_parser(line, registry):
        raise RuntimeError("parser defect")

    monkeypatch.setitem(parser._DISPATCH, "trojan", broken_parser)
    with pytest.raises(RuntimeError, match="parser defect"):
        convert("trojan://pw@t.example.com:443#Trojan")


@pytest.mark.parametrize("bad", [
    "trojan://secret@a.example:bad", "tuic://secret@a.example:bad",
    "hysteria://a.example:bad", "vless://secret@[bad", "https://[bad",
    "ss://bad", "unknown://secret@a.example:443",
    "mierus://m.example?port=bad&protocol=TCP&port=443&protocol=TCP",
])
def test_invalid_link_rejects_entire_subscription_without_leaking_credentials(bad):
    with pytest.raises(ParseError, match="Line 2") as error:
        convert("trojan://pw@a.example:443#Good\n" + bad)
    assert "secret" not in str(error.value)


@pytest.mark.parametrize('wrapped', [False, True])
def test_metadata_comments_with_urls_are_ignored(wrapped):
    content = '#profile-web-page-url: https://provider.example/\n  # note: trojan://ignored\n  trojan://pw@example.com:443#HK'
    if wrapped:
        content = base64.b64encode(content.encode()).decode()
    assert [node['name'] for node in convert(content)] == ['HK']


@pytest.mark.parametrize('bad', [
    'trojan:/secret@example.com:443', 'trojan:secret', 'vmess:secret',
    'https:/secret', 'unknown:/secret', 'trojan//secret', 'vmess/secret',
])
def test_missing_link_delimiter_rejects_whole_subscription(bad):
    with pytest.raises(ParseError, match='Line 2') as error:
        convert('trojan://pw@example.com:443#good\n' + bad)
    assert 'secret' not in str(error.value)


@pytest.mark.parametrize('ending', ['unknown://secret', 'trojan:/secret@example.com:443', 'trojan://secret@example.com:bad'])
def test_base64_padding_cannot_hide_bad_tail(ending):
    encoded = base64.b64encode(b'trojan://pw@example.com:443#HKx').decode()
    assert encoded.endswith('=')
    with pytest.raises(ParseError):
        convert(encoded + '\n' + ending)


@pytest.mark.parametrize('padded', [False, True])
@pytest.mark.parametrize('newlines', [False, True])
def test_standard_raw_and_crlf_base64_are_supported(padded, newlines):
    raw = 'trojan://pw@example.com:443#HKx'
    encoded = base64.b64encode(raw.encode()).decode()
    if not padded: encoded = encoded.rstrip('=')
    if newlines: encoded = '\r\n'.join(encoded[i:i + 7] for i in range(0, len(encoded), 7))
    assert convert(encoded) == convert(raw)


def test_base64_cannot_ignore_non_alphabet_bytes():
    encoded = base64.b64encode(b'trojan://pw@example.com:443#HKx').decode()
    with pytest.raises(ParseError): convert(encoded[:8] + '!' + encoded[8:])
