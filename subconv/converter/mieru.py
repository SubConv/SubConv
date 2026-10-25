from __future__ import annotations

import urllib.parse as urlparse

from pydantic import Field

from ..yaml_utils import MAX_CONTENT_BYTES
from .models import MihomoBaseModel
from .registry import NameRegistry
from .util import MAX_PROXY_NODES, ParseError, parse_query


class MieruProxy(MihomoBaseModel):
    name: str = Field(alias="name")
    type: str = Field(alias="type")
    server: str = Field(alias="server")
    transport: str = Field(alias="transport")
    udp: bool = Field(True, alias="udp")
    username: str | None = Field(None, alias="username")
    password: str | None = Field(None, alias="password")
    port: int | None = Field(None, alias="port")
    port_range: str | None = Field(None, alias="port-range")
    multiplexing: str | None = Field(None, alias="multiplexing")
    handshake_mode: str | None = Field(None, alias="handshake-mode")
    traffic_pattern: str | None = Field(None, alias="traffic-pattern")

    def to_dict(self) -> dict[str, object]:
        return self.model_dump(by_alias=True, exclude_none=True)


def parse_mieru(line: str, registry: NameRegistry) -> list[MieruProxy]:
    url = urlparse.urlparse(line)
    server = url.hostname
    if not server:
        raise ParseError("mieru: missing host")

    query = parse_query(url.query)
    ports = query.get("port", [])
    protocols = query.get("protocol", [])
    if not ports or len(ports) != len(protocols):
        raise ParseError("mieru: mismatched port/protocol")
    if len(ports) > MAX_PROXY_NODES:
        raise ParseError("mieru: expanded nodes exceed node limit")

    username = urlparse.unquote(url.username) if url.username is not None else None
    password = urlparse.unquote(url.password) if url.password is not None else None
    base_name = urlparse.unquote(url.fragment) or _query_first(query, "profile") or server
    common: dict[str, object] = {"type": "mieru", "server": server, "udp": True}
    if username is not None:
        common["username"] = username
    if password is not None:
        common["password"] = password
    for source, target in (
        ("multiplexing", "multiplexing"),
        ("handshake-mode", "handshake_mode"),
        ("traffic-pattern", "traffic_pattern"),
    ):
        value = _query_first(query, source)
        if value:
            common[target] = value

    # Reject multiplicative expansion before allocating a name/model per port.
    repeated_bytes = len(base_name.encode("utf-8")) + sum(
        len(key.encode("utf-8")) + (len(value.encode("utf-8")) if isinstance(value, str) else 0)
        for key, value in common.items()
    )
    if repeated_bytes * len(ports) > MAX_CONTENT_BYTES:
        raise ParseError("mieru: expanded nodes exceed size limit")
    proxies: list[MieruProxy] = []

    for port_value, protocol in zip(ports, protocols, strict=True):
        payload: dict[str, object] = {
            **common,
            "name": registry.register(f"{base_name}:{port_value}/{protocol}"),
            "transport": protocol,
        }
        if "-" in port_value:
            payload["port_range"] = port_value
        else:
            try:
                payload["port"] = int(port_value)
            except ValueError as exc:
                raise ParseError("mieru: invalid port") from exc

        proxies.append(MieruProxy.model_validate(payload))

    return proxies


def _query_first(query: dict[str, list[str]], key: str) -> str:
    values = query.get(key)
    if not values:
        return ""
    return values[0]
