"""Tests for hysteria (v1) and hysteria2 share link parsers."""

import pytest

from subconv.converter.hysteria import parse_hysteria
from subconv.converter.hysteria2 import parse_hysteria2
from subconv.converter.util import ParseError


# --- hysteria v1 ---


def test_hysteria_full_config(registry):
    line = (
        "hysteria://hy.example.com:443?peer=sni.example.com&auth=myauth"
        "&upmbps=100&downmbps=50&alpn=h3&insecure=1&protocol=udp&obfs=obfsval#HY1"
    )
    result = parse_hysteria(line, registry).to_dict()
    assert result == {
        "name": "HY1",
        "type": "hysteria",
        "server": "hy.example.com",
        "port": 443,
        "sni": "sni.example.com",
        "obfs": "obfsval",
        "alpn": ["h3"],
        "auth-str": "myauth",
        "protocol": "udp",
        "up": "100",
        "down": "50",
        "skip-cert-verify": True,
    }


def test_hysteria_up_down_preferred_over_mbps_aliases(registry):
    line = "hysteria://hy.example.com:443?up=200&upmbps=100&down=80&downmbps=50#Pref"
    result = parse_hysteria(line, registry).to_dict()
    assert result["up"] == "200"
    assert result["down"] == "80"


def test_hysteria_missing_port_raises(registry):
    with pytest.raises(ParseError, match="missing host or port"):
        parse_hysteria("hysteria://hy.example.com#x", registry)


# --- hysteria2 ---


def test_hysteria2_full_config(registry):
    line = "hysteria2://authpass@hy2.example.com:443?sni=sni.example.com&insecure=1&alpn=h3#My%20HY2"
    result = parse_hysteria2(line, registry).to_dict()
    assert result == {
        "name": "My HY2",
        "type": "hysteria2",
        "server": "hy2.example.com",
        "port": 443,
        "password": "authpass",
        "sni": "sni.example.com",
        "skip-cert-verify": True,
        "alpn": ["h3"],
    }


def test_hysteria2_default_port_is_443(registry):
    result = parse_hysteria2("hy2://authpass@hy2.example.com#DefaultPort", registry).to_dict()
    assert result["port"] == 443
    assert result["type"] == "hysteria2"


def test_hysteria2_obfs_and_bandwidth(registry):
    line = (
        "hysteria2://authpass@hy2.example.com:8443?obfs=salamander"
        "&obfs-password=obfspw&down=100&up=50&pinSHA256=abc123#Obfs"
    )
    result = parse_hysteria2(line, registry).to_dict()
    assert result["obfs"] == "salamander"
    assert result["obfs-password"] == "obfspw"
    assert result["down"] == "100"
    assert result["up"] == "50"
    assert result["fingerprint"] == "abc123"


@pytest.mark.parametrize(
    "value,expected", [("1", True), ("true", True), ("0", False), ("false", False)]
)
def test_hysteria2_insecure_variants(registry, value, expected):
    line = f"hysteria2://auth@h.example.com:443?insecure={value}#I"
    assert parse_hysteria2(line, registry).to_dict()["skip-cert-verify"] is expected


def test_hysteria2_without_auth_has_no_password(registry):
    result = parse_hysteria2("hysteria2://hy2.example.com:443#NoAuth", registry).to_dict()
    assert "password" not in result


def test_hysteria2_missing_host_raises(registry):
    with pytest.raises(ParseError, match="missing host"):
        parse_hysteria2("hysteria2://authpass@:443#x", registry)
