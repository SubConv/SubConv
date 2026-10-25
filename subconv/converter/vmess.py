from __future__ import annotations

import binascii
import json
import urllib.parse as urlparse
from json import JSONDecodeError
from typing import Any

from pydantic import Field

from .models import (
    ECHOpts,
    GrpcOpts,
    H2Opts,
    HttpOpts,
    MihomoBaseModel,
    RealityOpts,
    WsOpts,
    XhttpOpts,
)
from .registry import NameRegistry
from .util import ParseError, base64_raw_std_decode
from .vless import handle_v_share_link


type ModelData = dict[str, Any]


class VmessProxy(MihomoBaseModel):
    name: str = Field(alias="name")
    type: str = Field(alias="type")
    server: str = Field(alias="server")
    port: int = Field(alias="port")
    uuid: str = Field(alias="uuid")
    alter_id: int = Field(0, alias="alterId")
    cipher: str = Field("auto", alias="cipher")
    udp: bool = Field(True, alias="udp")
    network: str | None = Field(None, alias="network")
    tls: bool = Field(False, alias="tls")
    alpn: list[str] | None = Field(None, alias="alpn")
    skip_cert_verify: bool = Field(False, alias="skip-cert-verify")
    fingerprint: str | None = Field(None, alias="fingerprint")
    certificate: str | None = Field(None, alias="certificate")
    private_key: str | None = Field(None, alias="private-key")
    servername: str | None = Field(None, alias="servername")
    ech_opts: ECHOpts | None = Field(None, alias="ech-opts")
    reality_opts: RealityOpts | None = Field(None, alias="reality-opts")
    http_opts: HttpOpts | None = Field(None, alias="http-opts")
    h2_opts: H2Opts | None = Field(None, alias="h2-opts")
    grpc_opts: GrpcOpts | None = Field(None, alias="grpc-opts")
    ws_opts: WsOpts | None = Field(None, alias="ws-opts")
    xhttp_opts: XhttpOpts | None = Field(None, alias="xhttp-opts")
    packet_addr: bool | None = Field(None, alias="packet-addr")
    xudp: bool | None = Field(None, alias="xudp")
    packet_encoding: str | None = Field(None, alias="packet-encoding")
    global_padding: bool | None = Field(None, alias="global-padding")
    authenticated_length: bool | None = Field(None, alias="authenticated-length")
    client_fingerprint: str | None = Field(None, alias="client-fingerprint")

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=True)


def parse_vmess(line: str, registry: NameRegistry) -> VmessProxy:
    body = line.removeprefix("vmess://")

    try:
        values = _parse_legacy_values(body)
    except ParseError as exc:
        if str(exc) != "vmess: legacy base64 decode failed":
            raise
        return _parse_aead(line, registry)

    return VmessProxy.model_validate(_build_legacy_kwargs(values, registry))


def _parse_legacy_values(body: str) -> dict[str, Any]:
    try:
        decoded = base64_raw_std_decode(body)
    except (binascii.Error, UnicodeDecodeError) as exc:
        raise ParseError("vmess: legacy base64 decode failed") from exc

    try:
        values = json.loads(decoded)
    except JSONDecodeError as exc:
        raise ParseError("vmess: invalid legacy json") from exc

    if not isinstance(values, dict):
        raise ParseError("vmess: invalid legacy json")

    return values


def _build_legacy_kwargs(values: dict[str, Any], registry: NameRegistry) -> ModelData:
    server = _require_str(values.get("add"), "vmess: missing server")
    uuid = _require_str(values.get("id"), "vmess: missing uuid")
    port = _parse_port(values.get("port"))

    kwargs: ModelData = {
        "name": registry.register(str(values.get("ps") or "")),
        "type": "vmess",
        "server": server,
        "port": port,
        "uuid": uuid,
        "alter_id": _parse_int(values.get("aid"), default=0),
        "cipher": str(values.get("scy") or "auto"),
        "udp": True,
        "xudp": True,
        "tls": False,
        "skip_cert_verify": False,
    }

    if servername := _optional_str(values.get("sni")):
        kwargs["servername"] = servername

    tls = str(values.get("tls") or "")
    if tls.lower().endswith("tls"):
        kwargs["tls"] = True
        if alpn := _split_csv(values.get("alpn")):
            kwargs["alpn"] = alpn

    network = str(values.get("net") or "").lower()
    if str(values.get("type") or "").lower() == "http":
        network = "http"
    elif network == "http":
        network = "h2"

    if network:
        kwargs["network"] = network

    host = _optional_str(values.get("host"))
    path = _optional_str(values.get("path"))

    if network == "http":
        headers: dict[str, list[str]] = {}
        if host:
            headers["Host"] = [host]
        kwargs["http_opts"] = HttpOpts.model_validate(
            {"path": [path or "/"], "headers": headers}
        )
    elif network == "h2":
        kwargs["h2_opts"] = H2Opts.model_validate(
            {"path": path or "/", "host": [host] if host else None}
        )
    elif network in {"ws", "httpupgrade"}:
        kwargs["ws_opts"] = _build_ws_opts(path, host, network)
    elif network == "grpc":
        kwargs["grpc_opts"] = GrpcOpts.model_validate({"grpc-service-name": path})

    return kwargs


def _build_ws_opts(path: str | None, host: str | None, network: str) -> WsOpts:
    ws_path = path or "/"
    headers: dict[str, str] = {}
    if host:
        headers["Host"] = host

    opts_kwargs: ModelData = {
        "path": ws_path,
        "headers": headers,
    }

    if path:
        parsed = urlparse.urlparse(path)
        query = dict(urlparse.parse_qsl(parsed.query))

        if early_data := query.get("ed"):
            try:
                ed_int = int(early_data)
            except ValueError:
                pass
            else:
                if network == "ws":
                    opts_kwargs["max-early-data"] = ed_int
                    opts_kwargs["early-data-header-name"] = "Sec-WebSocket-Protocol"
                else:
                    opts_kwargs["v2ray-http-upgrade-fast-open"] = True

                query.pop("ed", None)
                parsed = parsed._replace(query=urlparse.urlencode(query))
                opts_kwargs["path"] = parsed.geturl() or ws_path

        if early_header := query.get("eh"):
            opts_kwargs["early-data-header-name"] = early_header

    return WsOpts.model_validate(opts_kwargs)


def _parse_aead(line: str, registry: NameRegistry) -> VmessProxy:
    url = urlparse.urlparse(line)
    query = urlparse.parse_qs(url.query, keep_blank_values=True)
    kwargs = handle_v_share_link(url, registry, "vmess", query)

    kwargs["alter_id"] = 0
    encryption = query.get("encryption")
    kwargs["cipher"] = encryption[0] if encryption and encryption[0] else "auto"

    return VmessProxy.model_validate(kwargs)


def _parse_port(value: Any) -> int:
    port = _parse_int(value, default=-1)
    if port <= 0:
        raise ParseError("vmess: invalid port")
    return port


def _parse_int(value: Any, default: int) -> int:
    if value in (None, ""):
        return default
    try:
        return int(str(value))
    except ValueError as exc:
        raise ParseError("vmess: invalid integer") from exc


def _require_str(value: Any, message: str) -> str:
    parsed = _optional_str(value)
    if parsed is None:
        raise ParseError(message)
    return parsed


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    parsed = str(value)
    return parsed if parsed else None


def _split_csv(value: Any) -> list[str] | None:
    text = _optional_str(value)
    if text is None:
        return None
    values = [item.strip() for item in text.split(",") if item.strip()]
    return values or None
