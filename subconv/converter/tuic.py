"""TUIC share link parser.

Format: ``tuic://uuid:password@host:port?sni=xxx#name`` (v5)
     or ``tuic://token@host:port?sni=xxx#name`` (v4)

Aligned with mihomo ``common/convert/converter.go`` case ``"tuic"``.
"""

from __future__ import annotations

import urllib.parse as urlparse

from pydantic import Field

from .models import MihomoBaseModel
from .registry import NameRegistry
from .util import ParseError, first_query_values


class TuicProxy(MihomoBaseModel):
    name: str = Field(alias="name")
    type: str = Field(alias="type")
    server: str = Field(alias="server")
    port: int = Field(alias="port")
    udp: bool = Field(True, alias="udp")
    uuid: str | None = Field(None, alias="uuid")
    password: str | None = Field(None, alias="password")
    token: str | None = Field(None, alias="token")
    congestion_controller: str | None = Field(None, alias="congestion-controller")
    alpn: list[str] | None = Field(None, alias="alpn")
    sni: str | None = Field(None, alias="sni")
    disable_sni: bool | None = Field(None, alias="disable-sni")
    udp_relay_mode: str | None = Field(None, alias="udp-relay-mode")

    def to_dict(self) -> dict[str, object]:
        return self.model_dump(by_alias=True, exclude_none=True)


def parse_tuic(line: str, registry: NameRegistry) -> TuicProxy:
    url = urlparse.urlparse(line)
    if not url.hostname or not url.port:
        raise ParseError("tuic: missing host or port")

    query = first_query_values(url.query)

    kwargs: dict[str, object] = {
        "name": registry.register(urlparse.unquote(url.fragment)),
        "type": "tuic",
        "server": url.hostname,
        "port": url.port,
    }

    password = url.password
    if password is not None:
        kwargs["uuid"] = urlparse.unquote(url.username or "")
        kwargs["password"] = urlparse.unquote(password)
    else:
        kwargs["token"] = urlparse.unquote(url.username or "")

    if cc := query.get("congestion_control"):
        kwargs["congestion_controller"] = cc

    if alpn := query.get("alpn"):
        kwargs["alpn"] = alpn.split(",")

    if sni := query.get("sni"):
        kwargs["sni"] = sni

    if query.get("disable_sni") == "1":
        kwargs["disable_sni"] = True

    if mode := query.get("udp_relay_mode"):
        kwargs["udp_relay_mode"] = mode

    return TuicProxy.model_validate(kwargs)
