from __future__ import annotations

import urllib.parse as urlparse

from pydantic import Field

from .models import MihomoBaseModel
from .registry import NameRegistry
from .util import ParseError, first_query_values


class TelegramProxy(MihomoBaseModel):
    name: str = Field(alias="name")
    type: str = Field(alias="type")
    server: str = Field(alias="server")
    port: int = Field(alias="port")
    username: str | None = Field(None, alias="username")
    password: str | None = Field(None, alias="password")

    def to_dict(self) -> dict[str, object]:
        return self.model_dump(by_alias=True, exclude_none=True)


def parse_tg(line: str, registry: NameRegistry) -> TelegramProxy:
    url = urlparse.urlparse(line)
    proxy_type = url.hostname or ""
    query = first_query_values(url.query)

    return _build_telegram_proxy(
        proxy_type=proxy_type,
        query=query,
        registry=registry,
        fallback_name=proxy_type,
    )


def parse_tg_https(line: str, registry: NameRegistry) -> TelegramProxy:
    url = urlparse.urlparse(line)
    hostname = url.hostname or ""
    if hostname != "t.me":
        raise ParseError("telegram https: invalid host")

    proxy_type = url.path.strip("/")
    query = first_query_values(url.query)

    return _build_telegram_proxy(
        proxy_type=proxy_type,
        query=query,
        registry=registry,
        fallback_name=proxy_type,
    )


def _build_telegram_proxy(
    *,
    proxy_type: str,
    query: dict[str, str],
    registry: NameRegistry,
    fallback_name: str,
) -> TelegramProxy:
    if not proxy_type:
        raise ParseError("telegram: missing proxy type")
    if proxy_type not in {'socks', 'socks5'}:
        raise ParseError('telegram: unsupported proxy type')

    server = query.get("server") or ""
    if not server:
        raise ParseError("telegram: missing server")

    port_value = query.get("port") or ""
    if not port_value:
        raise ParseError("telegram: missing port")

    try:
        port = int(port_value)
    except ValueError as exc:
        raise ParseError("telegram: invalid port") from exc

    remark = query.get("remark") or query.get("remarks") or fallback_name

    return TelegramProxy.model_validate(
        {
            "name": registry.register(remark),
            "type": 'socks5',
            "server": server,
            "port": port,
            "username": query.get("user") or None,
            "password": query.get("pass") or None,
        }
    )
