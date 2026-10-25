from __future__ import annotations

import base64
import binascii
import urllib.parse as urlparse

from pydantic import Field

from .models import MihomoBaseModel
from .registry import NameRegistry
from .util import ParseError, normalize_url_userinfo


class HttpSocksProxy(MihomoBaseModel):
    name: str = Field(alias="name")
    type: str = Field(alias="type")
    server: str = Field(alias="server")
    port: int = Field(alias="port")
    username: str | None = Field(None, alias="username")
    password: str | None = Field(None, alias="password")
    tls: bool | None = Field(None, alias="tls")
    skip_cert_verify: bool | None = Field(None, alias="skip-cert-verify")

    def to_dict(self) -> dict[str, object]:
        return self.model_dump(by_alias=True, exclude_none=True)


def parse_http_socks(line: str, registry: NameRegistry) -> HttpSocksProxy:
    url = urlparse.urlparse(line)
    server = url.hostname
    if not server:
        raise ParseError("http/socks: missing host")

    try:
        port = url.port
    except ValueError as exc:
        raise ParseError("http/socks: invalid port") from exc

    if port is None:
        raise ParseError("http/socks: missing port")

    proxy_type = _proxy_type(url.scheme.lower())
    username, password = _parse_credentials(url)
    name = registry.register(urlparse.unquote(url.fragment) or f"{server}:{port}")

    payload: dict[str, object] = {
        "name": name,
        "type": proxy_type,
        "server": server,
        "port": port,
        "skip_cert_verify": True,
    }

    if username is not None:
        payload["username"] = username
    if password is not None:
        payload["password"] = password
    if url.scheme.lower() == "https":
        payload["tls"] = True

    return HttpSocksProxy.model_validate(payload)


def _proxy_type(scheme: str) -> str:
    if scheme in {"socks", "socks5", "socks5h"}:
        return "socks5"
    if scheme in {"http", "https"}:
        return "http"
    raise ParseError("http/socks: unsupported scheme")


def _parse_credentials(url: urlparse.ParseResult) -> tuple[str | None, str | None]:
    raw_userinfo, _, _ = url.netloc.rpartition("@")
    if not raw_userinfo:
        return None, None

    userinfo = normalize_url_userinfo(raw_userinfo)
    # Match mihomo's DecodeBase64: strict standard Base64, then plaintext.
    encoded = userinfo if "=" in userinfo else userinfo + "=" * (-len(userinfo) % 4)
    try:
        decoded = base64.b64decode(encoded, validate=True).decode(
            "utf-8", errors="replace"
        )
    except binascii.Error:
        decoded = userinfo

    parts = decoded.split(":")
    return parts[0] or None, (parts[1] or None) if len(parts) == 2 else None
