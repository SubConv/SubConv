"""Tests for subconv.converter.http_socks.parse_http_socks.

Credentials support both base64 userinfo and plaintext fallback, as in mihomo.
"""

import base64

import pytest

from subconv.converter.http_socks import parse_http_socks
from subconv.converter.util import ParseError


def b64creds(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def test_http_with_base64_credentials(registry):
    line = f"http://{b64creds('user:pass')}@http.example.com:8080#HTTPProxy"
    result = parse_http_socks(line, registry).to_dict()
    assert result == {
        "name": "HTTPProxy",
        "type": "http",
        "server": "http.example.com",
        "port": 8080,
        "username": "user",
        "password": "pass",
        "skip-cert-verify": True,
    }


def test_socks5_scheme_normalizes_to_socks5_type(registry):
    line = f"socks5://{b64creds('user:pass')}@socks.example.com:1080#SOCKS"
    result = parse_http_socks(line, registry).to_dict()
    assert result["type"] == "socks5"
    assert result["username"] == "user"
    assert result["password"] == "pass"


def test_socks5h_scheme_also_normalizes(registry):
    line = f"socks5h://{b64creds('user:pass')}@s.example.com:1080#S5H"
    assert parse_http_socks(line, registry).to_dict()["type"] == "socks5"


def test_bare_socks_scheme(registry):
    result = parse_http_socks("socks://s.example.com:1080#SocksNoCred", registry).to_dict()
    assert result["type"] == "socks5"
    assert "username" not in result


def test_https_sets_tls_and_http_type(registry):
    line = f"https://{b64creds('u:p')}@secure.example.com:8443#HTTPS"
    result = parse_http_socks(line, registry).to_dict()
    assert result["type"] == "http"
    assert result["tls"] is True


def test_no_credentials(registry):
    result = parse_http_socks("http://plain.example.com:3128#NoCred", registry).to_dict()
    assert result == {
        "name": "NoCred",
        "type": "http",
        "server": "plain.example.com",
        "port": 3128,
        "skip-cert-verify": True,
    }


def test_plain_text_credentials_are_preserved(registry):
    result = parse_http_socks("http://user:pass@http.example.com:8080#PlainCred", registry).to_dict()
    assert result["username"] == "user"
    assert result["password"] == "pass"


def test_default_name_is_host_port(registry):
    result = parse_http_socks("http://plain.example.com:3128", registry).to_dict()
    assert result["name"] == "plain.example.com:3128"


def test_missing_port_raises(registry):
    with pytest.raises(ParseError, match="missing port"):
        parse_http_socks("http://example.com#x", registry)


def test_missing_host_raises(registry):
    with pytest.raises(ParseError, match="missing host"):
        parse_http_socks("http://:8080#x", registry)


def test_unsupported_scheme_raises(registry):
    with pytest.raises(ParseError, match="unsupported scheme"):
        parse_http_socks("ftp://example.com:21#x", registry)
