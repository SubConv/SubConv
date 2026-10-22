"""Tests for subconv.converter.tuic.parse_tuic (v5 uuid+password, v4 token)."""

import pytest

from subconv.converter.tuic import parse_tuic
from subconv.converter.util import ParseError

UUID = "b831381d-6324-4d53-ad4f-8cda48b30811"


def test_tuic_v5_full_config(registry):
    line = (
        f"tuic://{UUID}:tuicpass@tuic.example.com:443?sni=sni.example.com"
        "&congestion_control=bbr&alpn=h3&udp_relay_mode=native#TUIC5"
    )
    result = parse_tuic(line, registry).to_dict()
    assert result == {
        "name": "TUIC5",
        "type": "tuic",
        "server": "tuic.example.com",
        "port": 443,
        "udp": True,
        "uuid": UUID,
        "password": "tuicpass",
        "congestion-controller": "bbr",
        "alpn": ["h3"],
        "sni": "sni.example.com",
        "udp-relay-mode": "native",
    }


def test_tuic_v4_token_form(registry):
    line = "tuic://tokenonly@tuic.example.com:8443?disable_sni=1#TUIC4"
    result = parse_tuic(line, registry).to_dict()
    assert result["token"] == "tokenonly"
    assert result["disable-sni"] is True
    assert "uuid" not in result
    assert "password" not in result


def test_tuic_disable_sni_only_when_1(registry):
    line = "tuic://tokenonly@tuic.example.com:8443?disable_sni=0#T"
    assert "disable-sni" not in parse_tuic(line, registry).to_dict()


def test_tuic_missing_port_raises(registry):
    with pytest.raises(ParseError, match="missing host or port"):
        parse_tuic("tuic://uuid:pw@tuic.example.com#x", registry)


def test_tuic_missing_host_raises(registry):
    with pytest.raises(ParseError, match="missing host or port"):
        parse_tuic("tuic://uuid:pw@:443#x", registry)
