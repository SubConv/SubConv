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
    assert result["h2-opts"] == {"path": "/h2p", "headers": {"Host": ["h.example.com"]}}


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
    with pytest.raises(ParseError, match="missing host or port"):
        parse_vmess("vmess://!!!notbase64!!!", registry)


def test_duplicate_names_deduplicated(registry):
    uri = vmess_uri(BASE_CFG)
    assert parse_vmess(uri, registry).to_dict()["name"] == "Node"
    assert parse_vmess(uri, registry).to_dict()["name"] == "Node-01"
