"""Tests for subconv.converter.vmess.parse_vmess (legacy JSON + AEAD forms)."""

import base64
import json

import pytest

from subconv.converter.registry import NameRegistry
from subconv.converter.util import ParseError
from subconv.converter.vmess import parse_vmess

UUID = "b831381d-6324-4d53-ad4f-8cda48b30811"


def vmess_uri(cfg: dict) -> str:
    """Build a legacy vmess:// URI from a JSON config dict."""
    return "vmess://" + base64.b64encode(json.dumps(cfg).encode()).decode()


BASE_CFG = {
    "v": "2",
    "ps": "Node",
    "add": "vmess.example.com",
    "port": "443",
    "id": UUID,
    "aid": "0",
    "scy": "auto",
    "net": "tcp",
    "type": "none",
}


def test_uppercase_scheme_is_accepted(registry):
    result = parse_vmess(vmess_uri(BASE_CFG).replace('vmess://', 'VMESS://', 1), registry).to_dict()
    assert result['server'] == BASE_CFG['add']


def test_ws_early_data_preserves_other_query_values(registry):
    cfg = {**BASE_CFG, 'net': 'ws', 'path': '/ws?token=one&ed=32&token=two&z='}
    result = parse_vmess(vmess_uri(cfg), registry).to_dict()
    assert result['ws-opts']['path'] == '/ws?token=one&token=two&z='


def test_deep_legacy_json_is_a_parse_error(registry):
    raw = '{"add":"example.com","id":"u","port":443,"extra":' + '[' * 10000 + '0' + ']' * 10000 + '}'
    link = 'vmess://' + base64.b64encode(raw.encode()).decode()
    with pytest.raises(ParseError, match='invalid legacy json'):
        parse_vmess(link, registry)


def test_legacy_ws_tls_full_config(registry):
    cfg = {
        **BASE_CFG,
        "ps": "My VMess",
        "net": "ws",
        "host": "cdn.example.com",
        "path": "/ws-path",
        "tls": "tls",
        "sni": "sni.example.com",
        "alpn": "h2,http/1.1",
    }
    result = parse_vmess(vmess_uri(cfg), registry).to_dict()
    assert result == {
        "name": "My VMess",
        "type": "vmess",
        "server": "vmess.example.com",
        "port": 443,
        "uuid": UUID,
        "alterId": 0,
        "cipher": "auto",
        "udp": True,
        "network": "ws",
        "tls": True,
        "alpn": ["h2", "http/1.1"],
        "skip-cert-verify": False,
        "servername": "sni.example.com",
        "ws-opts": {"path": "/ws-path", "headers": {"Host": "cdn.example.com"}},
        "xudp": True,
    }


def test_legacy_tcp_plain_defaults(registry):
    cfg = {**BASE_CFG, "ps": "Plain", "port": 8388, "aid": 2}
    result = parse_vmess(vmess_uri(cfg), registry).to_dict()
    assert result["name"] == "Plain"
    assert result["port"] == 8388
    assert result["alterId"] == 2
    assert result["network"] == "tcp"
    assert result["tls"] is False
    assert "ws-opts" not in result
    assert "alpn" not in result


def test_legacy_cipher_from_scy(registry):
    cfg = {**BASE_CFG, "scy": "aes-128-gcm"}
    assert parse_vmess(vmess_uri(cfg), registry).to_dict()["cipher"] == "aes-128-gcm"


def test_legacy_http_network_via_type_field(registry):
    cfg = {**BASE_CFG, "net": "tcp", "type": "http", "host": "h.example.com", "path": "/p"}
    result = parse_vmess(vmess_uri(cfg), registry).to_dict()
    assert result["network"] == "http"
    assert result["http-opts"] == {"path": ["/p"], "headers": {"Host": ["h.example.com"]}}


def test_legacy_net_http_maps_to_h2(registry):
    cfg = {**BASE_CFG, "net": "http", "host": "h.example.com", "path": "/h2p"}
    result = parse_vmess(vmess_uri(cfg), registry).to_dict()
    assert result["network"] == "h2"
    assert result["h2-opts"] == {"path": "/h2p", "host": ["h.example.com"]}


def test_legacy_grpc_network(registry):
    cfg = {**BASE_CFG, "net": "grpc", "path": "svcname"}
    result = parse_vmess(vmess_uri(cfg), registry).to_dict()
    assert result["network"] == "grpc"
    assert result["grpc-opts"] == {"grpc-service-name": "svcname"}


def test_legacy_ws_early_data_query(registry):
    cfg = {**BASE_CFG, "net": "ws", "path": "/p?ed=2048", "host": "h.example.com"}
    result = parse_vmess(vmess_uri(cfg), registry).to_dict()
    assert result["ws-opts"] == {
        "path": "/p",
        "headers": {"Host": "h.example.com"},
        "max-early-data": 2048,
        "early-data-header-name": "Sec-WebSocket-Protocol",
    }


def test_aead_url_style_link(registry):
    line = (
        f"vmess://{UUID}@vmess.example.com:443"
        "?security=tls&type=ws&path=%2Fray&host=cdn.example.com"
        "&sni=sni.example.com#AEAD-Node"
    )
    result = parse_vmess(line, registry).to_dict()
    assert result["name"] == "AEAD-Node"
    assert result["type"] == "vmess"
    assert result["server"] == "vmess.example.com"
    assert result["port"] == 443
    assert result["uuid"] == UUID
    assert result["alterId"] == 0
    assert result["cipher"] == "auto"
    assert result["tls"] is True
    assert result["network"] == "ws"
    assert result["servername"] == "sni.example.com"
    assert result["client-fingerprint"] == "chrome"
    assert result["ws-opts"]["path"] == "/ray"
    assert result["ws-opts"]["headers"]["Host"] == "cdn.example.com"


def test_missing_server_raises(registry):
    cfg = {"ps": "x", "port": "443", "id": UUID}
    with pytest.raises(ParseError, match="missing server"):
        parse_vmess(vmess_uri(cfg), registry)


def test_missing_uuid_raises(registry):
    cfg = {"ps": "x", "add": "a.example.com", "port": "443"}
    with pytest.raises(ParseError, match="missing uuid"):
        parse_vmess(vmess_uri(cfg), registry)


def test_non_numeric_port_raises(registry):
    with pytest.raises(ParseError, match="invalid integer"):
        parse_vmess(vmess_uri({**BASE_CFG, "port": "abc"}), registry)


def test_missing_port_raises(registry):
    cfg = {k: v for k, v in BASE_CFG.items() if k != "port"}
    with pytest.raises(ParseError, match="invalid port"):
        parse_vmess(vmess_uri(cfg), registry)


def test_non_json_payload_raises(registry):
    line = "vmess://" + base64.b64encode(b"not json").decode()
    with pytest.raises(ParseError, match="invalid legacy json"):
        parse_vmess(line, registry)


def test_non_object_json_payload_raises(registry):
    line = "vmess://" + base64.b64encode(b"[1,2]").decode()
    with pytest.raises(ParseError, match="invalid legacy json"):
        parse_vmess(line, registry)


def test_garbage_input_falls_through_to_aead_error(registry):
    # Undecodable legacy payloads fall back to the AEAD/URL parser, whose
    # error is what surfaces (current upstream behaviour).
    with pytest.raises(ParseError, match="missing port"):
        parse_vmess("vmess://!!!notbase64!!!", registry)


def test_duplicate_names_deduplicated(registry):
    uri = vmess_uri(BASE_CFG)
    assert parse_vmess(uri, registry).to_dict()["name"] == "Node"
    assert parse_vmess(uri, registry).to_dict()["name"] == "Node-01"


@pytest.mark.parametrize(
    "query,cipher",
    [
        ("encryption=none&encryption=auto", "none"),
        ("encryption=&encryption=none", "auto"),
    ],
)
def test_aead_encryption_uses_first_query_value(registry, query, cipher):
    result = parse_vmess(f"vmess://{UUID}@example.com:443?{query}#AEAD", registry).to_dict()
    assert result["cipher"] == cipher


@pytest.mark.parametrize("encoding", ["none", "packet"])
def test_aead_packet_encoding_does_not_force_xudp(registry, encoding):
    line = f"vmess://{UUID}@example.com:443?packetEncoding={encoding}#AEAD"
    result = parse_vmess(line, registry).to_dict()
    assert "xudp" not in result
    assert result.get("packet-addr", False) is (encoding == "packet")


@pytest.mark.parametrize('encoded', ['%FF', '%C0%AF'])
def test_ws_query_rebuild_preserves_raw_bytes(registry, encoded):
    cfg = {**BASE_CFG, 'net': 'ws', 'path': '/?ed=10&x=' + encoded}
    result = parse_vmess(vmess_uri(cfg), registry).to_dict()
    assert result['ws-opts']['path'] == '/?x=' + encoded


@pytest.mark.parametrize('value', ['1_0', ' 10', '١٠', '9223372036854775808', '-9223372036854775809'])
def test_ws_early_data_rejects_non_go_integers(registry, value):
    path = '/?ed=' + value
    cfg = {**BASE_CFG, 'net': 'ws', 'path': path}
    result = parse_vmess(vmess_uri(cfg), registry).to_dict()
    assert result['ws-opts']['path'] == path
    assert 'max-early-data' not in result['ws-opts']


def test_ws_early_data_accepts_long_leading_zeros(registry):
    cfg = {**BASE_CFG, 'net': 'ws', 'path': '/?ed=' + '0' * 5000 + '10'}
    result = parse_vmess(vmess_uri(cfg), registry).to_dict()
    assert result['ws-opts']['max-early-data'] == 10


@pytest.mark.parametrize('path', ['/?ed=10&eh=%FF', '/?eh=%FF'])
def test_ws_invalid_utf8_header_uses_go_json_replacement(registry, path):
    cfg = {**BASE_CFG, 'net': 'ws', 'path': path}
    result = parse_vmess(vmess_uri(cfg), registry).to_dict()
    assert result['ws-opts']['early-data-header-name'] == '�'
    assert result['ws-opts']['path'] == '/?eh=%FF'


def test_ws_query_rebuild_sorts_original_bytes(registry):
    cfg = {**BASE_CFG, 'net': 'ws', 'path': '/?ed=10&%FF=x&%EF%BF%BD=y'}
    result = parse_vmess(vmess_uri(cfg), registry).to_dict()
    assert result['ws-opts']['path'] == '/?%EF%BF%BD=y&%FF=x'


@pytest.mark.parametrize('path', ['/%GG?ed=10', '/%GG?ed=10&eh=custom', '/?ed=10#%GG', '/;%GG?ed=10'])
def test_ws_invalid_url_path_preserves_path_without_early_data(registry, path):
    cfg = {**BASE_CFG, 'net': 'ws', 'path': path}
    result = parse_vmess(vmess_uri(cfg), registry).to_dict()
    assert result['ws-opts'] == {'path': path, 'headers': {}}


@pytest.mark.parametrize('path,expected', [
    ('///a?ed=1', '///a'), ('?ed=1', ''), ('/a b?ed=1', '/a%20b'),
    ('/中文?ed=1', '/%E4%B8%AD%E6%96%87'), ('/a%2fb?ed=1', '/a%2fb'),
    ('/a?ed=1#b c', '/a#b%20c'), ('/a?ed=1#', '/a'),
])
def test_ws_early_data_rebuild_keeps_go_url_path_semantics(registry, path, expected):
    cfg = {**BASE_CFG, 'net': 'ws', 'path': path}
    result = parse_vmess(vmess_uri(cfg), registry).to_dict()
    assert result['ws-opts']['path'] == expected
    assert result['ws-opts']['max-early-data'] == 1


@pytest.mark.parametrize('value', ['1_0', ' 10', '١٠', '9223372036854775808'])
def test_aead_early_data_uses_same_go_integer_validation(registry, value):
    from urllib.parse import urlencode
    with pytest.raises(ParseError, match='bad WebSocket max early data'):
        parse_vmess(f'vmess://{UUID}@example.com:443?' + urlencode({'type': 'ws', 'ed': value}), registry)


def test_ws_early_data_rebuild_normalizes_scheme_like_go(registry):
    cfg = {**BASE_CFG, 'net': 'ws', 'path': 'HTTP://example.com/a?ed=1'}
    result = parse_vmess(vmess_uri(cfg), registry).to_dict()
    assert result['ws-opts']['path'] == 'http://example.com/a'


@pytest.mark.parametrize('path', ['/a\tb?ed=1', '/a\x00?ed=1', '//a:b/c?ed=1', '1:a?ed=1', '//exa mple/a?ed=1'])
def test_ws_go_url_parse_failures_keep_original_path_and_ignore_early_data(registry, path):
    cfg = {**BASE_CFG, 'net': 'ws', 'path': path}
    result = parse_vmess(vmess_uri(cfg), registry).to_dict()
    assert result['ws-opts'] == {'path': path, 'headers': {}}
