from __future__ import annotations

import binascii
import urllib.parse as urlparse

from pydantic import Field

from .models import MihomoBaseModel
from .registry import NameRegistry
from .util import ParseError, base64_raw_url_decode, first_query_values, url_safe


class ShadowsocksRProxy(MihomoBaseModel):
    name: str = Field(alias="name")
    type: str = Field(alias="type")
    server: str = Field(alias="server")
    port: int = Field(alias="port")
    password: str = Field(alias="password")
    cipher: str = Field(alias="cipher")
    obfs: str = Field(alias="obfs")
    obfs_param: str | None = Field(None, alias="obfs-param")
    protocol: str = Field(alias="protocol")
    protocol_param: str | None = Field(None, alias="protocol-param")
    udp: bool = Field(True, alias="udp")

    def to_dict(self) -> dict[str, object]:
        return self.model_dump(by_alias=True, exclude_none=True)


def parse_ssr(line: str, registry: NameRegistry) -> ShadowsocksRProxy:
    try:
        if line.partition("://")[0].lower() != "ssr":
            raise ParseError("ssr: invalid scheme")

        decoded = base64_raw_url_decode(url_safe(line[6:]))
        before, separator, after = decoded.partition("/?")
        if not separator:
            raise ParseError("ssr: missing query separator")

        parts = before.split(":")
        if len(parts) != 6:
            raise ParseError("ssr: invalid server fields")

        query = first_query_values(url_safe(after), strict=True)

        remarks = query.get("remarks", "")
        obfs_param = query.get("obfsparam")
        protocol_param = query.get("protoparam")

        name = registry.register(base64_raw_url_decode(url_safe(remarks)))
        obfs_param_value = (
            base64_raw_url_decode(url_safe(obfs_param)) if obfs_param else None
        )
        protocol_param_value = (
            base64_raw_url_decode(url_safe(protocol_param)) if protocol_param else None
        )

        return ShadowsocksRProxy.model_validate(
            {
                "name": name,
                "type": "ssr",
                "server": parts[0],
                "port": int(parts[1]),
                "protocol": parts[2],
                "cipher": parts[3],
                "obfs": parts[4],
                "password": base64_raw_url_decode(url_safe(parts[5])),
                "obfs-param": obfs_param_value,
                "protocol-param": protocol_param_value,
                "udp": True,
            }
        )
    except (ValueError, UnicodeDecodeError, binascii.Error) as exc:
        raise ParseError(f"ssr: {exc}") from exc
