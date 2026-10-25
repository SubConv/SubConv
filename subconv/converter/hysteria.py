"""Hysteria share link parser.

Format: ``hysteria://host:port?peer=xxx&auth=xxx&upmbps=xxx#name``

Aligned with mihomo ``common/convert/converter.go`` case ``"hysteria"``.
"""

from __future__ import annotations

import urllib.parse as urlparse

from pydantic import Field

from .models import MihomoBaseModel
from .registry import NameRegistry
from .util import ParseError, first_query_values, parse_optional_bool


class HysteriaProxy(MihomoBaseModel):
    name: str = Field(alias="name")
    type: str = Field(alias="type")
    server: str = Field(alias="server")
    port: int = Field(alias="port")
    sni: str | None = Field(None, alias="sni")
    obfs: str | None = Field(None, alias="obfs")
    alpn: list[str] | None = Field(None, alias="alpn")
    auth_str: str | None = Field(None, alias="auth-str")
    protocol: str | None = Field(None, alias="protocol")
    up: str | None = Field(None, alias="up")
    down: str | None = Field(None, alias="down")
    skip_cert_verify: bool | None = Field(None, alias="skip-cert-verify")

    def to_dict(self) -> dict[str, object]:
        return self.model_dump(by_alias=True, exclude_none=True)


def parse_hysteria(line: str, registry: NameRegistry) -> HysteriaProxy:
    url = urlparse.urlparse(line)
    if not url.hostname or not url.port:
        raise ParseError("hysteria: missing host or port")

    query = first_query_values(url.query)

    up = query.get("up") or query.get("upmbps", "")
    down = query.get("down") or query.get("downmbps", "")

    kwargs: dict[str, object] = {
        "name": registry.register(urlparse.unquote(url.fragment)),
        "type": "hysteria",
        "server": url.hostname,
        "port": url.port,
        "sni": query.get("peer") or None,
        "obfs": query.get("obfs") or None,
        "auth_str": query.get("auth") or None,
        "protocol": query.get("protocol") or None,
        "up": up or None,
        "down": down or None,
    }

    if alpn := query.get("alpn"):
        kwargs["alpn"] = alpn.split(",")

    if query.get("insecure"):
        kwargs["skip_cert_verify"] = parse_optional_bool(query["insecure"]) or False

    return HysteriaProxy.model_validate(kwargs)
