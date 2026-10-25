"""Tests for subconv.converter.shadowsocksr.parse_ssr."""

import base64

import pytest

from subconv.converter.shadowsocksr import parse_ssr
from subconv.converter.util import ParseError


def b64url(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def ssr_uri(inner: str) -> str:
    return "ssr://" + b64url(inner)


def test_uppercase_scheme_is_accepted(registry):
    line = ssr_uri('example.com:443:origin:aes-128-gcm:plain:' + b64url('pw') + '/?remarks=' + b64url('Node'))
    assert parse_ssr(line.replace('ssr://', 'SSR://', 1), registry).to_dict()['name'] == 'Node'


def test_full_ssr_link(registry):
    inner = (
        "ssr.example.com:8388:auth_aes128_md5:aes-256-cfb:tls1.2_ticket_auth:"
        f"{b64url('ssrpassword')}/?remarks={b64url('My SSR')}"
        f"&obfsparam={b64url('obfs-param-val')}&protoparam={b64url('proto-param-val')}"
    )
    result = parse_ssr(ssr_uri(inner), registry).to_dict()
    assert result == {
        "name": "My SSR",
        "type": "ssr",
        "server": "ssr.example.com",
        "port": 8388,
        "password": "ssrpassword",
        "cipher": "aes-256-cfb",
        "obfs": "tls1.2_ticket_auth",
        "obfs-param": "obfs-param-val",
        "protocol": "auth_aes128_md5",
        "protocol-param": "proto-param-val",
        "udp": True,
    }


def test_ssr_without_optional_params(registry):
    inner = (
        "ssr.example.com:443:origin:rc4-md5:plain:"
        f"{b64url('pw')}/?remarks={b64url('Bare')}"
    )
    result = parse_ssr(ssr_uri(inner), registry).to_dict()
    assert result["name"] == "Bare"
    assert result["protocol"] == "origin"
    assert result["cipher"] == "rc4-md5"
    assert result["obfs"] == "plain"
    assert "obfs-param" not in result
    assert "protocol-param" not in result


def test_wrong_scheme_raises(registry):
    with pytest.raises(ParseError, match="invalid scheme"):
        parse_ssr("ss://whatever", registry)


def test_garbage_payload_raises(registry):
    with pytest.raises(ParseError):
        parse_ssr("ssr://!!!", registry)


def test_missing_query_separator_raises(registry):
    inner = "ssr.example.com:8388:origin:rc4-md5:plain:" + b64url("pw")
    with pytest.raises(ParseError, match="missing query separator"):
        parse_ssr(ssr_uri(inner), registry)


def test_wrong_field_count_raises(registry):
    inner = "only:three:fields/?remarks=" + b64url("X")
    with pytest.raises(ParseError, match="invalid server fields"):
        parse_ssr(ssr_uri(inner), registry)


@pytest.mark.parametrize('bad', ['bad=%GG', 'bad=x;y'])
def test_ssr_rejects_any_invalid_query_pair(registry, bad):
    inner = 'example.com:443:origin:aes-128-gcm:plain:cHc/?remarks=bg&' + bad
    with pytest.raises(ParseError):
        parse_ssr(ssr_uri(inner), registry)
