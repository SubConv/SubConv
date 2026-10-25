"""Tests for subconv.converter.models transport/TLS option models."""

from subconv.converter.models import (
    GrpcOpts,
    H2Opts,
    HttpOpts,
    RealityOpts,
    WsOpts,
    XhttpOpts,
)


def test_ws_opts_to_dict_uses_hyphenated_aliases():
    opts = WsOpts.model_validate(
        {"path": "/p", "headers": {"Host": "h.example.com"}, "max-early-data": 2048}
    )
    assert opts.to_dict() == {
        "path": "/p",
        "headers": {"Host": "h.example.com"},
        "max-early-data": 2048,
    }


def test_ws_opts_empty_model_serializes_to_empty_dict():
    assert WsOpts.model_validate({}).to_dict() == {}


def test_ws_opts_populate_by_field_name():
    # MihomoBaseModel sets populate_by_name=True, so snake_case works too.
    opts = WsOpts(path="/x", max_early_data=100)
    assert opts.to_dict() == {"path": "/x", "max-early-data": 100}


def test_http_opts_fields():
    opts = HttpOpts.model_validate(
        {"method": "GET", "path": ["/a", "/b"], "headers": {"Host": ["h"]}}
    )
    assert opts.to_dict() == {
        "method": "GET",
        "path": ["/a", "/b"],
        "headers": {"Host": ["h"]},
    }


def test_h2_opts_fields():
    opts = H2Opts.model_validate({"host": ["h.example.com"], "path": "/h2"})
    assert opts.to_dict() == {"host": ["h.example.com"], "path": "/h2"}


def test_grpc_opts_service_name_alias():
    opts = GrpcOpts.model_validate({"grpc-service-name": "svc"})
    assert opts.to_dict() == {"grpc-service-name": "svc"}


def test_reality_opts_allows_short_id_without_public_key():
    # XHTTP downloadSettings can contain only realitySettings.shortId.
    assert RealityOpts.model_validate({"short-id": "ab"}).to_dict() == {
        "short-id": "ab"
    }


def test_reality_opts_short_id_optional():
    assert RealityOpts.model_validate({"public-key": "k"}).to_dict() == {
        "public-key": "k"
    }
    assert RealityOpts.model_validate(
        {"public-key": "k", "short-id": "ab"}
    ).to_dict() == {"public-key": "k", "short-id": "ab"}


def test_xhttp_opts_nested_reuse_settings():
    opts = XhttpOpts.model_validate(
        {
            "path": "/x",
            "mode": "auto",
            "reuse-settings": {"max-connections": "10", "h-keep-alive-period": 30},
        }
    )
    assert opts.to_dict() == {
        "path": "/x",
        "mode": "auto",
        "reuse-settings": {"max-connections": "10", "h-keep-alive-period": 30},
    }
