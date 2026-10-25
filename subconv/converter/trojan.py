"""Trojan share link parser.

Format: ``trojan://password@host:port?sni=xxx&alpn=xxx&type=ws&path=xxx#name``

Aligned with mihomo ``common/convert/converter.go`` case ``"trojan"``.
"""

from __future__ import annotations

import urllib.parse as urlparse

from pydantic import Field

from .models import GrpcOpts, MihomoBaseModel, WsOpts
from .registry import NameRegistry
from .util import ParseError, first_query_values, parse_optional_bool, rand_user_agent


class TrojanProxy(MihomoBaseModel):
    name: str = Field(alias="name")
    type: str = Field(alias="type")
    server: str = Field(alias="server")
    port: int = Field(alias="port")
    password: str = Field(alias="password")
    udp: bool = Field(True, alias="udp")
    skip_cert_verify: bool | None = Field(None, alias="skip-cert-verify")
    sni: str | None = Field(None, alias="sni")
    alpn: list[str] | None = Field(None, alias="alpn")
    network: str | None = Field(None, alias="network")
    grpc_opts: GrpcOpts | None = Field(None, alias="grpc-opts")
    ws_opts: WsOpts | None = Field(None, alias="ws-opts")
    client_fingerprint: str | None = Field(None, alias="client-fingerprint")
    fingerprint: str | None = Field(None, alias="fingerprint")

    def to_dict(self) -> dict[str, object]:
        return self.model_dump(by_alias=True, exclude_none=True)


def parse_trojan(line: str, registry: NameRegistry) -> TrojanProxy:
    url = urlparse.urlparse(line)
    if not url.hostname or not url.port:
        raise ParseError("trojan: missing host or port")
    if not url.username:
        raise ParseError("trojan: missing password")

    query = first_query_values(url.query)

    kwargs: dict[str, object] = {
        "name": registry.register(urlparse.unquote(url.fragment)),
        "type": "trojan",
        "server": url.hostname,
        "port": url.port,
        "password": urlparse.unquote(url.username),
    }

    if query.get("allowInsecure"):
        kwargs["skip_cert_verify"] = parse_optional_bool(query["allowInsecure"]) or False

    if sni := query.get("sni"):
        kwargs["sni"] = sni

    if alpn := query.get("alpn"):
        kwargs["alpn"] = alpn.split(",")

    network = query.get("type", "").lower()
    if network:
        kwargs["network"] = network

    if network == "ws":
        headers = {"User-Agent": rand_user_agent()}
        ws_opts = WsOpts.model_validate(
            {"path": query.get("path") or None, "headers": headers if headers else None}
        )
        kwargs["ws_opts"] = ws_opts
    elif network == "grpc":
        kwargs["grpc_opts"] = GrpcOpts.model_validate(
            {"grpc-service-name": query.get("serviceName")}
        )

    fp = query.get("fp", "")
    kwargs["client_fingerprint"] = fp if fp else "chrome"

    if pcs := query.get("pcs"):
        kwargs["fingerprint"] = pcs

    return TrojanProxy.model_validate(kwargs)
