"""Tests for subconv.converter.shadowsocks.parse_ss (SIP002 + legacy forms)."""

import base64
import urllib.parse

import pytest

from subconv.converter.shadowsocks import parse_ss
from subconv.converter.util import ParseError


def b64url(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def test_plain_userinfo(registry):
    result = parse_ss("ss://aes-256-gcm:mypassword@ss.example.com:8388#My%20SS", registry).to_dict()
    assert result == {
        "name": "My SS",
        "type": "ss",
        "server": "ss.example.com",
        "port": 8388,
        "password": "mypassword",
        "cipher": "aes-256-gcm",
        "udp": True,
    }


def test_base64_userinfo_sip002(registry):
    line = f"ss://{b64url('aes-128-gcm:secret123')}@ss.example.com:8389#SS-B64"
    result = parse_ss(line, registry).to_dict()
    assert result["cipher"] == "aes-128-gcm"
    assert result["password"] == "secret123"
    assert result["server"] == "ss.example.com"
    assert result["port"] == 8389


def test_fully_base64_encoded_legacy_link(registry):
    full = base64.b64encode(b"chacha20-ietf-poly1305:passw0rd@ss2.example.com:9999").decode()
    result = parse_ss(f"ss://{full}#Legacy", registry).to_dict()
    assert result["cipher"] == "chacha20-ietf-poly1305"
    assert result["password"] == "passw0rd"
    assert result["server"] == "ss2.example.com"
    assert result["port"] == 9999


def test_obfs_plugin(registry):
    line = (
        "ss://aes-256-gcm:pw@ss.example.com:8388/"
        "?plugin=obfs-local%3Bobfs%3Dhttp%3Bobfs-host%3Dexample.com#SSPlugin"
    )
    result = parse_ss(line, registry).to_dict()
    assert result["plugin"] == "obfs"
    assert result["plugin-opts"] == {"mode": "http", "host": "example.com"}


def test_v2ray_plugin(registry):
    line = (
        "ss://aes-256-gcm:pw@ss.example.com:8388/"
        "?plugin=v2ray-plugin%3Bmode%3Dwebsocket%3Bhost%3Dexample.com%3Bpath%3D%2Fws%3Btls#VP"
    )
    result = parse_ss(line, registry).to_dict()
    assert result["plugin"] == "v2ray-plugin"
    assert result["plugin-opts"] == {
        "mode": "websocket",
        "host": "example.com",
        "path": "/ws",
        "tls": True,
    }


def test_plugin_parameters_are_query_decoded_twice_and_keep_first_value(registry):
    plugin = 'v2ray-plugin;mode=websocket;path=%2Fws%3Ftoken%3Dx;path=wrong'
    line = 'ss://aes-128-gcm:pw@example.com:443?plugin=' + urllib.parse.quote(plugin, safe='')
    assert parse_ss(line, registry).to_dict()['plugin-opts']['path'] == '/ws?token=x'


def test_unknown_plugin_is_dropped(registry):
    line = "ss://aes-256-gcm:pw@ss.example.com:8388/?plugin=unknown-plugin%3Bfoo%3Dbar#UP"
    result = parse_ss(line, registry).to_dict()
    assert "plugin" not in result
    assert "plugin-opts" not in result


@pytest.mark.parametrize("query", ["udp-over-tcp=true", "uot=1"])
def test_udp_over_tcp_query_variants(registry, query):
    line = f"ss://aes-256-gcm:pw@ss.example.com:8388/?{query}#UOT"
    assert parse_ss(line, registry).to_dict()["udp-over-tcp"] is True


def test_invalid_scheme_raises(registry):
    with pytest.raises(ParseError, match="invalid scheme"):
        parse_ss("http://aes-256-gcm:pw@ss.example.com:8388#x", registry)


def test_missing_host_raises(registry):
    with pytest.raises(ParseError, match="missing host"):
        parse_ss("ss://aes-256-gcm:pw@:8388#x", registry)


def test_missing_userinfo_raises(registry):
    with pytest.raises(ParseError, match="missing userinfo"):
        parse_ss("ss://ss.example.com:8388#x", registry)


def test_missing_port_falls_into_base64_host_decode_and_raises(registry):
    # Current upstream behaviour: with no port, the parser treats the host
    # part as base64 and fails with an "invalid base64" ParseError.
    with pytest.raises(ParseError, match="invalid base64"):
        parse_ss("ss://aes-256-gcm:pw@ss.example.com#x", registry)


def test_parse_rebuild_parse_round_trip():
    from subconv.converter.registry import NameRegistry

    first = parse_ss(
        "ss://aes-256-gcm:mypassword@ss.example.com:8388#My%20SS", NameRegistry()
    ).to_dict()
    rebuilt = (
        f"ss://{first['cipher']}:{first['password']}@{first['server']}:{first['port']}"
        f"#{urllib.parse.quote(str(first['name']))}"
    )
    second = parse_ss(rebuilt, NameRegistry()).to_dict()
    assert second == first
