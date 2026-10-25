"""Regression cases from mihomo Meta 3f27ef3, common/convert/v.go.

These expectations cover share-link conversion, not adapter validation or
whether the resulting node can establish a connection.
"""

import json
from urllib.parse import urlencode

import pytest

from subconv.converter.vless import parse_vless
from subconv.converter.vmess import parse_vmess


@pytest.fixture(params=[("vless", parse_vless), ("vmess", parse_vmess)])
def xhttp(request, registry):
    scheme, parser = request.param

    def convert(extra):
        query = urlencode({"type": "xhttp", "path": "/x", "mode": "auto", "extra": extra})
        return parser(f"{scheme}://uuid@example.com:443?{query}#XHTTP", registry).to_dict()

    return convert


def test_xhttp_alias_precedence_and_header_method_casing(xhttp):
    extra = {
        "headers": {"X-Test": "value"},
        "uplinkHTTPMethod": "PUT",
        "sessionPlacement": "header",
        "sessionIDPlacement": "cookie",
        "sessionKey": "legacy",
        "sessionIDKey": "session",
        "sessionIDTable": "abcdef",
        "sessionIDLength": "8-16",
    }
    assert xhttp(json.dumps(extra))["xhttp-opts"] == {
        "path": "/x",
        "mode": "auto",
        "headers": {"X-Test": "value"},
        "uplink-http-method": "PUT",
        "session-placement": "cookie",
        "session-key": "session",
        "session-table": "abcdef",
        "session-length": "8-16",
    }


def test_xhttp_empty_session_id_aliases_preserve_legacy_values(xhttp):
    extra = {
        "sessionPlacement": "header",
        "sessionIDPlacement": "",
        "sessionKey": "legacy",
        "sessionIDKey": "",
    }
    opts = xhttp(json.dumps(extra))["xhttp-opts"]
    assert opts["session-placement"] == "header"
    assert opts["session-key"] == "legacy"


def test_xhttp_download_reality_short_id_and_nested_reuse_settings(xhttp):
    extra = {
        "xmux": {"maxConnections": 2},
        "downloadSettings": {
            "address": "down.example.com",
            "port": 8443,
            "security": "reality",
            "realitySettings": {"shortId": "ab12"},
            "tlsSettings": {"serverName": "sni.example.com", "allowInsecure": True},
            "xhttpSettings": {
                "path": "/download",
                "host": "cdn.example.com",
                "headers": {"X-Download": "yes"},
                "extra": {"xmux": {"maxConcurrency": "4-8", "hKeepAlivePeriod": 30}},
            },
        },
    }
    assert xhttp(json.dumps(extra))["xhttp-opts"] == {
        "path": "/x",
        "mode": "auto",
        "reuse-settings": {"max-connections": "2"},
        "download-settings": {
            "server": "down.example.com",
            "port": 8443,
            "tls": True,
            "servername": "sni.example.com",
            "skip-cert-verify": True,
            "reality-opts": {"short-id": "ab12"},
            "path": "/download",
            "host": "cdn.example.com",
            "headers": {"X-Download": "yes"},
            "reuse-settings": {"max-concurrency": "4-8", "h-keep-alive-period": 30},
        },
    }


@pytest.mark.parametrize(
    "extra",
    [
        "{",
        "[]",
        "null",
        '{"uplinkChunkSize": NaN}',
        '{"uplinkChunkSize": Infinity}',
        '{"uplinkChunkSize": 1e400}',
    ],
)
def test_xhttp_invalid_extra_keeps_the_node_and_base_options(xhttp, extra):
    result = xhttp(extra)
    assert result["name"] == "XHTTP"
    assert result["network"] == "xhttp"
    assert result["xhttp-opts"] == {"path": "/x", "mode": "auto"}


def test_xhttp_json_numbers_follow_float64_and_integer_truncation(xhttp):
    opts = xhttp('{"sessionIDLength":9007199254740993,"uplinkChunkSize":12.75}')["xhttp-opts"]
    assert opts["session-length"] == "9007199254740992"
    assert opts["uplink-chunk-size"] == 12


def test_xhttp_boolean_is_not_a_numeric_option(xhttp):
    extra = {
        "sessionIDLength": True,
        "uplinkChunkSize": True,
        "xmux": {"maxConnections": True, "hKeepAlivePeriod": True},
    }
    assert xhttp(json.dumps(extra))["xhttp-opts"] == {"path": "/x", "mode": "auto"}
