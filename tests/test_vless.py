"""Tests for subconv.converter.vless.parse_vless."""

import pytest

from subconv.converter.util import ParseError
from subconv.converter.vless import parse_vless

UUID = "b831381d-6324-4d53-ad4f-8cda48b30811"


@pytest.mark.parametrize('host,port', [('cn.xyz', 443), ('cc.example', 22)])
def test_plain_host_is_not_guessed_as_permissive_base64(registry, host, port):
    result = parse_vless(f'vless://{UUID}@{host}:{port}', registry).to_dict()
    assert result['server'] == host and result['port'] == port


def test_excessively_deep_xhttp_extra_is_ignored_like_mihomo(registry):
    from urllib.parse import quote
    extra = '{"ignored":' + '[' * 10000 + '0' + ']' * 10000 + '}'
    result = parse_vless(f'vless://{UUID}@example.com:443?type=xhttp&extra=' + quote(extra), registry).to_dict()
    assert result['xhttp-opts'] == {}


def test_ws_tls_full_config(registry):
    line = (
        f"vless://{UUID}@vless.example.com:443?security=tls&encryption=none"
        "&type=ws&path=%2Fws&host=cdn.example.com&sni=sni.example.com"
        "&flow=xtls-rprx-vision#My%20VLESS"
    )
    result = parse_vless(line, registry).to_dict()
    assert result["name"] == "My VLESS"
    assert result["type"] == "vless"
    assert result["server"] == "vless.example.com"
    assert result["port"] == 443
    assert result["uuid"] == UUID
    assert result["flow"] == "xtls-rprx-vision"
    assert result["tls"] is True
    assert result["encryption"] == "none"
    assert result["network"] == "ws"
    assert result["servername"] == "sni.example.com"
    assert result["client-fingerprint"] == "chrome"
    assert result["xudp"] is True
    assert result["ws-opts"]["path"] == "/ws"
    assert result["ws-opts"]["headers"]["Host"] == "cdn.example.com"
    assert "User-Agent" in result["ws-opts"]["headers"]


def test_reality_config(registry):
    line = (
        f"vless://{UUID}@vless.example.com:443?security=reality&pbk=PUBKEY123"
        "&sid=ab12&sni=www.microsoft.com&fp=firefox&type=tcp#Reality"
    )
    result = parse_vless(line, registry).to_dict()
    assert result["tls"] is True
    assert result["reality-opts"] == {"public-key": "PUBKEY123", "short-id": "ab12"}
    assert result["servername"] == "www.microsoft.com"
    assert result["client-fingerprint"] == "firefox"
    assert result["network"] == "tcp"
    assert "flow" not in result


def test_plain_tcp_no_security(registry):
    result = parse_vless("vless://uuid-123@vless.example.com:80#Plain", registry).to_dict()
    assert result == {
        "name": "Plain",
        "type": "vless",
        "server": "vless.example.com",
        "port": 80,
        "uuid": "uuid-123",
        "udp": True,
        "xudp": True,
        "network": "tcp",
    }


def test_grpc_network(registry):
    line = "vless://uuid-123@vless.example.com:443?security=tls&type=grpc&serviceName=myservice#GRPC"
    result = parse_vless(line, registry).to_dict()
    assert result["network"] == "grpc"
    assert result["grpc-opts"] == {"grpc-service-name": "myservice"}


def test_type_http_maps_to_h2_network(registry):
    line = "vless://u-1@v.example.com:443?security=tls&type=http#H2"
    result = parse_vless(line, registry).to_dict()
    assert result["network"] == "h2"
    assert result["h2-opts"] == {"path": "/"}


def test_tcp_with_http_header_type_maps_to_http_network(registry):
    line = (
        "vless://u-1@v.example.com:80?type=tcp&headerType=http"
        "&path=%2Fhp&host=h.example.com&method=GET#TH"
    )
    result = parse_vless(line, registry).to_dict()
    assert result["network"] == "http"
    assert result["http-opts"] == {
        "method": "GET",
        "path": ["/hp"],
        "headers": {"Host": ["h.example.com"]},
    }


def test_xhttp_network(registry):
    line = "vless://u-1@v.example.com:443?security=tls&type=xhttp&path=%2Fx&mode=auto#XH"
    result = parse_vless(line, registry).to_dict()
    assert result["network"] == "xhttp"
    assert result["xhttp-opts"] == {"path": "/x", "mode": "auto"}


def test_flow_is_lowercased(registry):
    line = "vless://u-1@v.example.com:443?flow=XTLS-RPRX-VISION#F"
    assert parse_vless(line, registry).to_dict()["flow"] == "xtls-rprx-vision"


def test_packet_encoding_packet_sets_packet_addr(registry):
    line = "vless://u-1@v.example.com:443?packetEncoding=packet#Pkt"
    result = parse_vless(line, registry).to_dict()
    assert result["packet-addr"] is True
    assert "xudp" not in result


def test_plus_in_fragment_is_preserved(registry):
    line = "vless://u-1@v.example.com:443#Name+With+Plus"
    assert parse_vless(line, registry).to_dict()["name"] == "Name+With+Plus"


def test_missing_port_raises(registry):
    with pytest.raises(ParseError, match="missing port"):
        parse_vless("vless://uuid-123@vless.example.com#NoPort", registry)


def test_missing_host_raises(registry):
    with pytest.raises(ParseError, match="missing host"):
        parse_vless("vless://u-1@:443#x", registry)


def test_invalid_port_raises(registry):
    with pytest.raises(ParseError, match="invalid port"):
        parse_vless("vless://uuid-123@vless.example.com:abc#Bad", registry)


def test_invalid_ws_early_data_raises(registry):
    with pytest.raises(ParseError, match="bad WebSocket max early data"):
        parse_vless("vless://u-1@v.example.com:443?type=ws&ed=abc#BadEd", registry)


@pytest.mark.parametrize('value', ['1_0', ' 10', '١٠', '9223372036854775808', '-9223372036854775809'])
def test_ws_early_data_uses_go_integer_syntax_and_range(registry, value):
    from urllib.parse import urlencode
    with pytest.raises(ParseError, match='bad WebSocket max early data'):
        parse_vless('vless://u@example.com:443?' + urlencode({'type': 'ws', 'ed': value}), registry)
