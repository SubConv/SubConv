from __future__ import annotations

import urllib.parse as urlparse
from collections.abc import Sequence
from typing import Callable, Protocol

from ..yaml_utils import MAX_CONTENT_BYTES
from .anytls import parse_anytls
from .hysteria import parse_hysteria
from .hysteria2 import parse_hysteria2
from .http_socks import parse_http_socks
from .mieru import parse_mieru
from .registry import NameRegistry
from .shadowsocks import parse_ss
from .shadowsocksr import parse_ssr
from .telegram import parse_tg, parse_tg_https
from .trojan import parse_trojan
from .tuic import parse_tuic
from .util import MAX_PROXY_NODES, ParseError, ProxyBudget, base64_raw_std_decode
from .vless import parse_vless
from .vmess import parse_vmess


class ProxyModel(Protocol):
    def to_dict(self) -> dict[str, object]: ...


ParserResult = ProxyModel | Sequence[ProxyModel] | None
ParserFn = Callable[[str, NameRegistry], ParserResult]


async def ConvertsV2Ray(buf: bytes | str) -> list[dict[str, object]]:
    data = _decode_subscription(buf)
    lines = data.splitlines()
    proxies: list[dict[str, object]] = []
    budget = ProxyBudget(MAX_PROXY_NODES, MAX_CONTENT_BYTES)
    registry = NameRegistry()

    for number, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        scheme, separator, remainder = line.partition(":")
        scheme = scheme.partition("/")[0].lower()
        known_scheme = scheme in _DISPATCH or scheme == "https"
        try:
            if "://" not in line:
                if (known_scheme and (separator or "/" in line)) or (separator and remainder.startswith("/")):
                    raise ParseError("missing share-link delimiter")
                continue
            parser = _select_parser(line, scheme)
            if parser is _unsupported:
                raise ParseError("unsupported protocol")
            budget.check_count()
            proxy = parser(line, registry)
            if isinstance(proxy, list):
                if not proxy:
                    raise ParseError("no nodes in share link")
                models = proxy
            elif proxy is None:
                raise ParseError("no nodes in share link")
            else:
                models = (proxy,)
            budget.check_count(len(models))
            for item in models:
                node = item.to_dict()
                budget.add(node)
                proxies.append(node)
        except (ParseError, ValueError) as exc:
            # Links and exception messages may contain credentials.
            protocol = scheme if known_scheme else "unknown protocol"
            raise ParseError(f"Line {number} ({protocol}): invalid share link") from exc

    if not proxies:
        raise ParseError("No valid proxies found")

    return proxies


def _decode_subscription(buf: bytes | str) -> str:
    try:
        raw = buf.encode('utf-8') if isinstance(buf, str) else buf
        if len(raw) > MAX_CONTENT_BYTES:
            raise ParseError("Subscription exceeds size limit")
        text = buf if isinstance(buf, str) else raw.decode('utf-8')
    except UnicodeError as exc:
        raise ParseError('Subscription must be UTF-8') from exc
    # A colon cannot occur in Base64. Plain links need no decoding or copies.
    if ':' in text:
        return text
    try:
        return base64_raw_std_decode(text)
    except (ValueError, UnicodeDecodeError):
        return text


def _unsupported(line: str, registry: NameRegistry) -> None:
    del line, registry
    return None


def _select_parser(line: str, scheme: str) -> ParserFn:
    if scheme == "https":
        hostname = urlparse.urlparse(line).hostname
        if hostname == "t.me":
            return parse_tg_https
        return parse_http_socks
    return _DISPATCH.get(scheme, _unsupported)


_DISPATCH: dict[str, ParserFn] = {
    "hysteria": parse_hysteria,
    "hysteria2": parse_hysteria2,
    "hy2": parse_hysteria2,
    "hysteria2+realm": parse_hysteria2,
    "hy2+realm": parse_hysteria2,
    "tuic": parse_tuic,
    "trojan": parse_trojan,
    "vless": parse_vless,
    "vmess": parse_vmess,
    "ss": parse_ss,
    "ssr": parse_ssr,
    "socks": parse_http_socks,
    "socks5": parse_http_socks,
    "socks5h": parse_http_socks,
    "http": parse_http_socks,
    "tg": parse_tg,
    "anytls": parse_anytls,
    "mierus": parse_mieru,
}
