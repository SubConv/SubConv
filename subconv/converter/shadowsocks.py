from __future__ import annotations

import binascii
import urllib.parse as urlparse

from pydantic import Field

from .models import MihomoBaseModel
from .registry import NameRegistry
from .util import ParseError, base64_raw_std_decode, base64_raw_url_decode, first_query_values


class ShadowsocksProxy(MihomoBaseModel):
    name: str = Field(alias="name")
    type: str = Field(alias="type")
    server: str = Field(alias="server")
    port: int = Field(alias="port")
    password: str = Field(alias="password")
    cipher: str = Field(alias="cipher")
    udp: bool = Field(True, alias="udp")
    plugin: str | None = Field(None, alias="plugin")
    plugin_opts: dict[str, str | bool] | None = Field(None, alias="plugin-opts")
    udp_over_tcp: bool | None = Field(None, alias="udp-over-tcp")
    udp_over_tcp_version: int | None = Field(None, alias="udp-over-tcp-version")
    client_fingerprint: str | None = Field(None, alias="client-fingerprint")

    def to_dict(self) -> dict[str, object]:
        return self.model_dump(by_alias=True, exclude_none=True)


def parse_ss(line: str, registry: NameRegistry) -> ShadowsocksProxy:
    url = _parse_ss_url(line)
    query = first_query_values(url.query)
    cipher, password = _parse_userinfo(url)
    server = url.hostname
    if server is None:
        raise ParseError("shadowsocks: missing host")

    udp_over_tcp = None
    if query.get("udp-over-tcp") == "true" or query.get("uot") == "1":
        udp_over_tcp = True

    plugin_name: str | None = None
    plugin_opts: dict[str, str | bool] | None = None
    if plugin := query.get("plugin"):
        parsed_plugin = _parse_plugin(plugin)
        if parsed_plugin is not None:
            plugin_name, plugin_opts = parsed_plugin

    payload: dict[str, object] = {
        "name": registry.register(urlparse.unquote(url.fragment)),
        "type": "ss",
        "server": server,
        "port": _get_port(url),
        "password": password,
        "cipher": cipher,
        "udp": True,
    }
    if plugin_name is not None:
        payload["plugin"] = plugin_name
    if plugin_opts is not None:
        payload["plugin-opts"] = plugin_opts
    if udp_over_tcp is not None:
        payload["udp-over-tcp"] = udp_over_tcp

    return ShadowsocksProxy.model_validate(payload)


def _parse_ss_url(line: str) -> urlparse.ParseResult:
    url = urlparse.urlparse(line)
    if url.scheme != "ss":
        raise ParseError("shadowsocks: invalid scheme")

    if not url.hostname:
        raise ParseError("shadowsocks: missing host")

    try:
        port = url.port
    except ValueError as exc:
        raise ParseError("shadowsocks: invalid port") from exc

    if port is not None:
        return url

    encoded_host = url.netloc.rsplit("@", 1)[-1]
    decoded_host = _decode_base64_value(encoded_host)
    reparsed = urlparse.urlparse(f"ss://{decoded_host}")

    if not reparsed.hostname:
        raise ParseError("shadowsocks: missing host")

    return reparsed._replace(query=url.query, fragment=url.fragment)


def _parse_userinfo(url: urlparse.ParseResult) -> tuple[str, str]:
    username = url.username
    password = url.password
    if username and password is not None:
        return urlparse.unquote(username), urlparse.unquote(password)

    raw_userinfo, _, _ = url.netloc.rpartition("@")
    if not raw_userinfo:
        raise ParseError("shadowsocks: missing userinfo")

    decoded_userinfo = _decode_base64_value(urlparse.unquote(raw_userinfo))
    cipher, separator, decoded_password = decoded_userinfo.partition(":")
    if not separator:
        raise ParseError("shadowsocks: invalid credentials")

    return cipher, decoded_password


def _parse_plugin(plugin: str) -> tuple[str, dict[str, str | bool] | None] | None:
    if ";" not in plugin:
        return None
    options = first_query_values("pluginName=" + plugin.replace(";", "&"))
    plugin_name = options.get("pluginName", "")

    if "obfs" in plugin_name:
        obfs_plugin_opts: dict[str, str | bool] = {}
        if mode := options.get("obfs"):
            obfs_plugin_opts["mode"] = mode
        if host := options.get("obfs-host"):
            obfs_plugin_opts["host"] = host
        return "obfs", obfs_plugin_opts or None

    if "v2ray-plugin" in plugin_name:
        v2ray_plugin_opts: dict[str, str | bool] = {}
        if mode := options.get("mode") or options.get("obfs"):
            v2ray_plugin_opts["mode"] = mode
        if host := options.get("host") or options.get("obfs-host"):
            v2ray_plugin_opts["host"] = host
        if path := options.get("path"):
            v2ray_plugin_opts["path"] = path
        if "tls" in plugin:
            v2ray_plugin_opts["tls"] = True
        return "v2ray-plugin", v2ray_plugin_opts or None

    return None


def _decode_base64_value(value: str) -> str:
    for decoder in (base64_raw_url_decode, base64_raw_std_decode):
        try:
            return decoder(value)
        except (ValueError, UnicodeDecodeError, binascii.Error):
            continue
    raise ParseError("shadowsocks: invalid base64")


def _get_port(url: urlparse.ParseResult) -> int:
    try:
        port = url.port
    except ValueError as exc:
        raise ParseError("shadowsocks: invalid port") from exc

    if port is None:
        raise ParseError("shadowsocks: missing port")

    return port
