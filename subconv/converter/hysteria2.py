"""Hysteria2 share link parser.

Formats: ``hysteria2://auth@host:port?sni=xxx#name`` or ``hy2://...``
Port lists/ranges and the ``hysteria2+realm`` / ``hy2+realm`` schemes are supported.
All schemes normalize to ``type: "hysteria2"``.

Aligned with mihomo ``common/convert/converter.go`` case ``"hysteria2" | "hy2"``.
"""

from __future__ import annotations

import urllib.parse as urlparse

from pydantic import Field

from .models import MihomoBaseModel, RealmOpts
from .registry import NameRegistry
from .util import (
    INVALID_URL_ESCAPE,
    ParseError,
    normalize_url_userinfo,
    parse_optional_bool,
    parse_query,
)


class Hysteria2Proxy(MihomoBaseModel):
    name: str = Field(alias="name")
    type: str = Field(alias="type")
    server: str = Field(alias="server")
    port: int = Field(alias="port")
    ports: str | None = Field(None, alias="ports")
    realm_opts: RealmOpts | None = Field(None, alias="realm-opts")
    password: str | None = Field(None, alias="password")
    obfs: str | None = Field(None, alias="obfs")
    obfs_password: str | None = Field(None, alias="obfs-password")
    sni: str | None = Field(None, alias="sni")
    skip_cert_verify: bool | None = Field(None, alias="skip-cert-verify")
    alpn: list[str] | None = Field(None, alias="alpn")
    fingerprint: str | None = Field(None, alias="fingerprint")
    down: str | None = Field(None, alias="down")
    up: str | None = Field(None, alias="up")

    def to_dict(self) -> dict[str, object]:
        return self.model_dump(by_alias=True, exclude_none=True)


def parse_hysteria2(line: str, registry: NameRegistry) -> Hysteria2Proxy:
    line, ports = _split_hysteria2_ports(line)
    try:
        url = urlparse.urlparse(line)
        port = url.port if url.port is not None else 443
    except ValueError as exc:
        raise ParseError("hysteria2: invalid host or port") from exc
    if not url.hostname:
        raise ParseError("hysteria2: missing host")
    if INVALID_URL_ESCAPE.search(url.path) or INVALID_URL_ESCAPE.search(url.fragment):
        raise ParseError("hysteria2: invalid URL escape")

    query_values = parse_query(url.query)
    query = {key: values[0] for key, values in query_values.items()}

    kwargs: dict[str, object] = {
        "name": registry.register(urlparse.unquote(url.fragment)),
        "type": "hysteria2",
        "server": url.hostname,
        "port": port,
        "ports": ports or None,
        "obfs": query.get("obfs") or None,
        "obfs_password": query.get("obfs-password") or None,
        "sni": query.get("sni") or None,
    }

    if query.get("insecure"):
        kwargs["skip_cert_verify"] = parse_optional_bool(query["insecure"]) or False

    if alpn := query.get("alpn"):
        kwargs["alpn"] = alpn.split(",")

    userinfo, _, authority = url.netloc.rpartition("@")
    userinfo = normalize_url_userinfo(userinfo)
    if url.scheme.lower().endswith("+realm"):
        kwargs["realm_opts"] = RealmOpts.model_validate(
            {
                "server_url": "https://" + authority,
                "token": urlparse.unquote(userinfo) or None,
                "realm_id": urlparse.unquote(url.path.removeprefix("/")) or None,
                "stun_servers": query_values.get("stun") or None,
            }
        )
        if auth := query.get("auth"):
            kwargs["password"] = auth
    elif userinfo:
        kwargs["password"] = userinfo

    if fp := query.get("pinSHA256"):
        kwargs["fingerprint"] = fp

    if down := query.get("down"):
        kwargs["down"] = down
    if up := query.get("up"):
        kwargs["up"] = up

    return Hysteria2Proxy.model_validate(kwargs)


def _split_hysteria2_ports(line: str) -> tuple[str, str]:
    """Extract hopping ports before URL parsing, matching mihomo's converter."""
    head, separator, rest = line.partition("://")
    if not separator:
        return line, ""
    end = min((rest.find(char) for char in "/?#" if char in rest), default=len(rest))
    authority, tail = rest[:end], rest[end:]
    userinfo, at, hostport = authority.rpartition("@")
    if not at:
        hostport = authority
    # Upstream only extracts port lists for non-bracketed hosts.
    if "]" in hostport:
        return line, ""
    host, colon, ports = hostport.rpartition(":")
    if not colon or not any(char in ports for char in ",-"):
        return line, ""
    first = ports.replace("-", ",").split(",", 1)[0]
    if not first:
        return line, ""
    prefix = userinfo + at if at else ""
    return f"{head}://{prefix}{host}:{first}{tail}", ports
