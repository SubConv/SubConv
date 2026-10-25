"""Tests for subconv.converter.trojan.parse_trojan."""

import urllib.parse

import pytest

from subconv.converter.trojan import parse_trojan
from subconv.converter.util import ParseError


def rebuild_uri(proxy: dict) -> str:
    """Rebuild a trojan:// URI from a parsed proxy dict (round-trip helper)."""
    query = {}
    if proxy.get("sni"):
        query["sni"] = proxy["sni"]
    if proxy.get("alpn"):
        query["alpn"] = ",".join(proxy["alpn"])
    qs = urllib.parse.urlencode(query)
    return (
        f"trojan://{proxy['password']}@{proxy['server']}:{proxy['port']}"
        f"?{qs}#{urllib.parse.quote(proxy['name'])}"
    )


def test_basic_trojan_with_sni_and_alpn(registry):
    line = "trojan://mypassword@trojan.example.com:443?sni=sni.example.com&alpn=h2,http/1.1#My%20Trojan"
    result = parse_trojan(line, registry).to_dict()
    assert result == {
        "name": "My Trojan",
        "type": "trojan",
        "server": "trojan.example.com",
        "port": 443,
        "password": "mypassword",
        "udp": True,
        "sni": "sni.example.com",
        "alpn": ["h2", "http/1.1"],
        "client-fingerprint": "chrome",
    }


def test_ws_network_and_allow_insecure(registry):
    line = "trojan://pw@trojan.example.com:443?type=ws&path=%2Ftrojan-ws&allowInsecure=1#TrojanWS"
    result = parse_trojan(line, registry).to_dict()
    assert result["network"] == "ws"
    assert result["skip-cert-verify"] is True
    assert result["ws-opts"]["path"] == "/trojan-ws"
    assert "User-Agent" in result["ws-opts"]["headers"]


def test_allow_insecure_zero_means_false(registry):
    line = "trojan://pw@t.example.com:443?allowInsecure=0#I0"
    assert parse_trojan(line, registry).to_dict()["skip-cert-verify"] is False


def test_grpc_network_and_fingerprint_params(registry):
    line = "trojan://pw@t.example.com:443?type=grpc&serviceName=svc&fp=firefox&pcs=pin123#TG"
    result = parse_trojan(line, registry).to_dict()
    assert result["network"] == "grpc"
    assert result["grpc-opts"] == {"grpc-service-name": "svc"}
    assert result["client-fingerprint"] == "firefox"
    assert result["fingerprint"] == "pin123"


def test_percent_encoded_password_is_decoded(registry):
    line = "trojan://p%40ss%3Aword@t.example.com:443#EncPW"
    assert parse_trojan(line, registry).to_dict()["password"] == "p@ss:word"


def test_missing_password_raises(registry):
    with pytest.raises(ParseError, match="missing password"):
        parse_trojan("trojan://trojan.example.com:443#NoPW", registry)


def test_missing_port_raises(registry):
    with pytest.raises(ParseError, match="missing host or port"):
        parse_trojan("trojan://pw@trojan.example.com#NoPort", registry)


def test_parse_rebuild_parse_round_trip():
    from subconv.converter.registry import NameRegistry

    line = "trojan://mypassword@trojan.example.com:443?sni=sni.example.com&alpn=h2,http/1.1#My%20Trojan"
    first = parse_trojan(line, NameRegistry()).to_dict()
    second = parse_trojan(rebuild_uri(first), NameRegistry()).to_dict()
    assert second == first
