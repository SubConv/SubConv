"""Tests for the mieru (mierus://) and Telegram (tg://, t.me) parsers."""

import pytest

from subconv.converter.mieru import parse_mieru
from subconv.converter.telegram import parse_tg, parse_tg_https
from subconv.converter.util import ParseError


# --- mieru ---


def test_mieru_expands_port_protocol_pairs(registry):
    line = (
        "mierus://user:pass@mieru.example.com"
        "?port=2027&protocol=TCP&port=2028&protocol=UDP#MieruProfile"
    )
    results = [p.to_dict() for p in parse_mieru(line, registry)]
    assert results == [
        {
            "name": "MieruProfile:2027/TCP",
            "type": "mieru",
            "server": "mieru.example.com",
            "transport": "TCP",
            "udp": True,
            "username": "user",
            "password": "pass",
            "port": 2027,
        },
        {
            "name": "MieruProfile:2028/UDP",
            "type": "mieru",
            "server": "mieru.example.com",
            "transport": "UDP",
            "udp": True,
            "username": "user",
            "password": "pass",
            "port": 2028,
        },
    ]


def test_mieru_port_range(registry):
    results = parse_mieru("mierus://mieru.example.com?port=10000-10010&protocol=TCP#Range", registry)
    assert len(results) == 1
    result = results[0].to_dict()
    assert result["port-range"] == "10000-10010"
    assert "port" not in result


def test_mieru_profile_query_used_as_name_fallback(registry):
    results = parse_mieru("mierus://m.example.com?port=2027&protocol=TCP&profile=ProfName", registry)
    assert results[0].to_dict()["name"] == "ProfName:2027/TCP"


def test_mieru_optional_query_fields(registry):
    line = (
        "mierus://u:p@m.example.com?port=2027&protocol=TCP"
        "&multiplexing=MULTIPLEXING_LOW&handshake-mode=HANDSHAKE_NO_WAIT#X"
    )
    result = parse_mieru(line, registry)[0].to_dict()
    assert result["multiplexing"] == "MULTIPLEXING_LOW"
    assert result["handshake-mode"] == "HANDSHAKE_NO_WAIT"


def test_mieru_mismatched_port_protocol_raises(registry):
    with pytest.raises(ParseError, match="mismatched port/protocol"):
        parse_mieru("mierus://mieru.example.com?port=2027#x", registry)


def test_mieru_missing_host_raises(registry):
    with pytest.raises(ParseError, match="missing host"):
        parse_mieru("mierus://?port=2027&protocol=TCP#x", registry)


@pytest.mark.parametrize("password", ["x" * 700, "密" * 240])
def test_mieru_rejects_repeated_fields_before_creating_models(registry, monkeypatch, password):
    from subconv.converter import mieru

    monkeypatch.setattr(mieru, "MAX_CONTENT_BYTES", 1024)

    def unexpected_model(*args, **kwargs):
        pytest.fail("Expansion must be checked before allocating per-port models")

    monkeypatch.setattr(mieru.MieruProxy, "model_validate", unexpected_model)
    with pytest.raises(ParseError, match="expanded nodes exceed size limit"):
        parse_mieru(f"mierus://u:{password}@m.example?port=1&protocol=TCP&port=2&protocol=TCP", registry)


# --- telegram ---


def test_tg_socks_link(registry):
    line = "tg://socks?server=tg.example.com&port=1080&user=u&pass=p&remark=MyTG"
    result = parse_tg(line, registry).to_dict()
    assert result == {
        "name": "MyTG",
        "type": "socks5",
        "server": "tg.example.com",
        "port": 1080,
        "username": "u",
        "password": "p",
    }


def test_tg_https_link(registry):
    line = "https://t.me/socks?server=tg.example.com&port=1080&remark=TGHTTPS"
    result = parse_tg_https(line, registry).to_dict()
    assert result == {
        "name": "TGHTTPS",
        "type": "socks5",
        "server": "tg.example.com",
        "port": 1080,
    }


def test_tg_name_falls_back_to_proxy_type(registry):
    line = "tg://socks?server=tg.example.com&port=1080"
    assert parse_tg(line, registry).to_dict()["name"] == "socks"


def test_tg_https_rejects_other_hosts(registry):
    with pytest.raises(ParseError, match="invalid host"):
        parse_tg_https("https://example.com/socks?server=a&port=1", registry)


def test_tg_missing_server_raises(registry):
    with pytest.raises(ParseError, match="missing server"):
        parse_tg("tg://socks?port=1080", registry)


def test_tg_missing_port_raises(registry):
    with pytest.raises(ParseError, match="missing port"):
        parse_tg("tg://socks?server=a.example.com", registry)


def test_tg_invalid_port_raises(registry):
    with pytest.raises(ParseError, match="invalid port"):
        parse_tg("tg://socks?server=a.example.com&port=abc", registry)


def test_tg_missing_type_raises(registry):
    with pytest.raises(ParseError, match="missing proxy type"):
        parse_tg("tg://?server=a.example.com&port=1080", registry)


@pytest.mark.parametrize('line', ['tg://proxy?server=tg.example.com&port=443&secret=abcdef', 'https://t.me/proxy?server=tg.example.com&port=443&secret=abcdef'])
def test_unsupported_telegram_mtproto_is_rejected(registry, line):
    parse = parse_tg if line.startswith('tg:') else parse_tg_https
    with pytest.raises(ParseError, match='unsupported proxy type'):
        parse(line, registry)
