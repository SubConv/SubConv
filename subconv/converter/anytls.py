from __future__ import annotations

import urllib.parse as urlparse

from pydantic import Field

from .models import MihomoBaseModel
from .registry import NameRegistry
from .util import ParseError, first_query_values


class AnyTLSProxy(MihomoBaseModel):
    name: str = Field(alias="name")
    type: str = Field(alias="type")
    server: str = Field(alias="server")
    port: int = Field(alias="port")
    username: str | None = Field(None, alias="username")
    password: str = Field(alias="password")
    sni: str | None = Field(None, alias="sni")
    fingerprint: str | None = Field(None, alias="fingerprint")
    skip_cert_verify: bool = Field(False, alias="skip-cert-verify")
    udp: bool = Field(True, alias="udp")

    def to_dict(self) -> dict[str, object]:
        return self.model_dump(by_alias=True, exclude_none=True)


def parse_anytls(line: str, registry: NameRegistry) -> AnyTLSProxy:
    url = urlparse.urlparse(line)
    try:
        port = url.port
    except ValueError as exc:
        raise ParseError("anytls: invalid port") from exc

    if not url.hostname or not port:
        raise ParseError("anytls: missing host or port")

    username = urlparse.unquote(url.username) if url.username is not None else None
    password = (
        urlparse.unquote(url.password)
        if url.password is not None
        else username
    )
    if not password:
        raise ParseError("anytls: missing password")

    query = first_query_values(url.query)
    name = urlparse.unquote(url.fragment) or f"{url.hostname}:{url.port}"

    return AnyTLSProxy.model_validate(
        {
            "name": registry.register(name),
            "type": "anytls",
            "server": url.hostname,
            "port": port,
            "username": username,
            "password": password,
            "sni": query.get("sni") or None,
            "fingerprint": query.get("hpkp") or None,
            "skip_cert_verify": query.get("insecure") == "1",
            "udp": True,
        }
    )
