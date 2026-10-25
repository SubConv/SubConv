"""Tests for subconv.converter.util: base64 helpers and misc utilities."""

import base64

import pytest

from subconv.converter.util import (
    ParseError,
    base64_raw_std_decode,
    base64_raw_url_decode,
    rand_user_agent,
    url_safe,
)


def test_base64_raw_std_decode_without_padding():
    # "hello world" base64-encodes with one "=" of padding; raw form drops it.
    assert base64_raw_std_decode("aGVsbG8gd29ybGQ") == "hello world"


def test_base64_raw_std_decode_with_padding_present():
    assert base64_raw_std_decode("aGVsbG8gd29ybGQ=") == "hello world"


def test_base64_raw_std_decode_empty_string():
    assert base64_raw_std_decode("") == ""


def test_base64_raw_std_decode_unicode_payload():
    raw = base64.b64encode("héllo".encode("utf-8")).decode().rstrip("=")
    assert base64_raw_std_decode(raw) == "héllo"


def test_base64_raw_url_decode_urlsafe_alphabet():
    # ">>>" encodes to "Pj4+" in std base64 and "Pj4-" urlsafe.
    assert base64_raw_url_decode("Pj4-") == ">>>"
    # "???" encodes to "Pz8/" in std base64 and "Pz8_" urlsafe.
    assert base64_raw_url_decode("Pz8_") == "???"


def test_base64_raw_url_decode_unicode_payload():
    raw = base64.urlsafe_b64encode("héllo?".encode("utf-8")).decode().rstrip("=")
    assert base64_raw_url_decode(raw) == "héllo?"


def test_base64_std_decode_invalid_utf8_raises():
    # b"\xff\xfe" is valid base64 input but not valid UTF-8 text.
    with pytest.raises(UnicodeDecodeError):
        base64_raw_std_decode("//4")


def test_url_safe_replaces_plus_and_slash():
    assert url_safe("a+b/c") == "a-b_c"
    assert url_safe("+++///") == "---___"


def test_url_safe_leaves_plain_text_unchanged():
    assert url_safe("plain-text_123") == "plain-text_123"
    assert url_safe("") == ""


def test_rand_user_agent_returns_known_agent():
    from subconv.converter import util

    for _ in range(20):
        assert rand_user_agent() in util._USER_AGENTS


def test_parse_error_is_exception_subclass():
    assert issubclass(ParseError, Exception)
    with pytest.raises(ParseError, match="boom"):
        raise ParseError("boom")
