"""Tests for subconv.converter.anytls.parse_anytls."""

import pytest

from subconv.converter.anytls import parse_anytls
from subconv.converter.util import ParseError


def test_anytls_full_config(registry):
    line = "anytls://user:pass@anytls.example.com:443?sni=sni.example.com&insecure=1#AnyTLS"
    result = parse_anytls(line, registry).to_dict()
    assert result == {
        "name": "AnyTLS",
        "type": "anytls",
        "server": "anytls.example.com",
        "port": 443,
        "username": "user",
        "password": "pass",
        "sni": "sni.example.com",
        "skip-cert-verify": True,
        "udp": True,
    }


def test_anytls_single_credential_becomes_username_and_password(registry):
    # With only one userinfo component, it is used as both username
    # and password (current upstream behaviour).
    result = parse_anytls("anytls://onlypass@anytls.example.com:8443#Single", registry).to_dict()
    assert result["username"] == "onlypass"
    assert result["password"] == "onlypass"
    assert result["skip-cert-verify"] is False


def test_anytls_hpkp_maps_to_fingerprint(registry):
    line = "anytls://user:pass@a.example.com:443?hpkp=pinvalue&insecure=0#HPKP"
    result = parse_anytls(line, registry).to_dict()
    assert result["fingerprint"] == "pinvalue"
    assert result["skip-cert-verify"] is False


def test_anytls_default_name_is_host_port(registry):
    result = parse_anytls("anytls://user:pass@a.example.com:443", registry).to_dict()
    assert result["name"] == "a.example.com:443"


def test_anytls_missing_password_raises(registry):
    with pytest.raises(ParseError, match="missing password"):
        parse_anytls("anytls://anytls.example.com:443#x", registry)


def test_anytls_missing_port_raises(registry):
    with pytest.raises(ParseError, match="missing host or port"):
        parse_anytls("anytls://user:pass@anytls.example.com#x", registry)


def test_anytls_invalid_port_raises(registry):
    with pytest.raises(ParseError, match="invalid port"):
        parse_anytls("anytls://user:pass@anytls.example.com:abc#x", registry)
