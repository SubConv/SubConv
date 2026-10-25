"""Shared utilities for V2Ray share link conversion."""

from __future__ import annotations

import base64
import random
import re
import string
import urllib.parse as urlparse


INVALID_URL_ESCAPE = re.compile(r"%(?![0-9a-fA-F]{2})")
_USERINFO_CHARS = string.ascii_letters + string.digits + "-._~!$&'()*+,;=:%@"


class ParseError(Exception):
    """Raised when a share link cannot be parsed.

    Only this exception is caught by the parser — all other exceptions
    propagate, preserving the "skip malformed links" behaviour without
    swallowing unrelated errors.
    """


def normalize_url_userinfo(userinfo: str) -> str:
    """Match Go's net/url.Userinfo.String, preserving the password delimiter."""
    if (
        any(char not in _USERINFO_CHARS for char in userinfo)
        or INVALID_URL_ESCAPE.search(userinfo)
    ):
        raise ParseError("invalid URL userinfo")
    username, separator, password = userinfo.partition(":")
    username = urlparse.quote_from_bytes(
        urlparse.unquote_to_bytes(username), safe="$&+,;="
    )
    if separator:
        password = urlparse.quote_from_bytes(
            urlparse.unquote_to_bytes(password), safe="$&+,;="
        )
        return f"{username}:{password}"
    return username


def parse_optional_bool(value: str) -> bool | None:
    """Match Go's strconv.ParseBool, preserving absent/invalid values."""
    if value in {"1", "t", "T", "true", "TRUE", "True"}:
        return True
    if value in {"0", "f", "F", "false", "FALSE", "False"}:
        return False
    return None


def base64_raw_std_decode(encoded: str) -> str:
    return base64.b64decode(encoded + "=" * (-len(encoded) % 4)).decode("utf-8")


def base64_raw_url_decode(encoded: str) -> str:
    return base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)).decode("utf-8")


def url_safe(string: str) -> str:
    return string.replace("+", "-").replace("/", "_")


_USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
]


def rand_user_agent() -> str:
    return _USER_AGENTS[random.randint(0, len(_USER_AGENTS) - 1)]
