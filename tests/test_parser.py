"""Tests for the top-level ConvertsV2Ray subscription parser.

ConvertsV2Ray is a coroutine; tests drive it with asyncio.run so no
async pytest plugin is required.
"""

import asyncio
import base64

import pytest

from subconv.converter import ConvertsV2Ray

MIXED_SUBSCRIPTION = "\n".join(
    [
        "trojan://pw@t.example.com:443#Dup",
        "trojan://pw@t.example.com:443#Dup",
        "vless://u-1@v.example.com:80#Solo",
        "this is not a link",
        "ss://bad",
        "unknown://x@y:1#Z",
    ]
)


def convert(content):
    return asyncio.run(ConvertsV2Ray(content))


def test_mixed_subscription_parses_valid_and_skips_invalid():
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
        "socks",
        "mieru",
    ]


def test_https_tme_link_routes_to_telegram_parser():
    result = convert("https://t.me/socks?server=tg.example.com&port=1080&remark=T")
    assert result == [
        {"name": "T", "type": "socks", "server": "tg.example.com", "port": 1080}
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


def test_ssr_link_dispatches():
    def b64url(text: str) -> str:
        return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")

    inner = f"ssr.example.com:8388:origin:aes-256-cfb:plain:{b64url('pw')}/?remarks={b64url('R')}"
    result = convert("ssr://" + b64url(inner))
    assert result[0]["type"] == "ssr"
    assert result[0]["name"] == "R"
