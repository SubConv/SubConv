"""Decode streamed HTTP bodies with bounded memory and linear input work."""

import zlib

import httpx
from fastapi import HTTPException

from .yaml_utils import MAX_CONTENT_BYTES

# Bound unused_data copies even when an outer coding yields a large inner chunk.
_INPUT_WINDOW = 4096


def _check_size(size: int):
    if size > MAX_CONTENT_BYTES:
        raise HTTPException(502, 'Upstream response exceeds 10 MiB limit')


class _Inflater:
    def __init__(self, encoding: str):
        self.encoding = encoding
        self.size = 0
        self.prefix = bytearray()
        self.ambiguous = False
        self.decoder = zlib.decompressobj(16 + zlib.MAX_WBITS) if encoding == 'gzip' else None

    def decode(self, data: bytes) -> bytes:
        if not data:
            return b''
        if self.decoder is None:
            _check_size(len(self.prefix) + len(data))
            self.prefix.extend(data)
            if self.ambiguous or len(self.prefix) < 2:
                return b''
            first, second = self.prefix[:2]
            wrapped = first & 15 == 8 and first >> 4 <= 7 and (first * 256 + second) % 31 == 0
            if wrapped:
                if len(self.prefix) < 5:
                    return b''
                # A zlib header can also begin a raw stored block. Only this
                # rare ambiguous prefix needs buffering until EOF; selecting
                # a format earlier would make correctness depend on TCP chunks.
                if self.prefix[1] ^ self.prefix[3] == 255 and self.prefix[2] ^ self.prefix[4] == 255:
                    self.ambiguous = True
                    return b''
            self.decoder = zlib.decompressobj(zlib.MAX_WBITS if wrapped else -zlib.MAX_WBITS)
            data, self.prefix = self.prefix, bytearray()
        return self._inflate(data)

    def _inflate(self, data: bytes) -> bytes:
        chunks = []
        view = memoryview(data)
        for offset in range(0, len(view), _INPUT_WINDOW):
            pending = view[offset:offset + _INPUT_WINDOW]
            while pending:
                if self.decoder.eof:
                    if self.encoding != 'gzip':
                        raise httpx.DecodingError('Trailing data in compressed upstream response')
                    self.decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
                try:
                    chunk = self.decoder.decompress(pending, MAX_CONTENT_BYTES - self.size + 1)
                except zlib.error as exc:
                    raise httpx.DecodingError('Invalid compressed upstream response') from exc
                self.size += len(chunk)
                _check_size(self.size)
                chunks.append(chunk)
                pending = self.decoder.unused_data
        return b''.join(chunks)

    def finish(self) -> bytes:
        if self.ambiguous:
            # Both candidates retain the same hard output budget. Prefer the
            # standards-compliant zlib representation when both are valid.
            exceeded = False
            for window in (zlib.MAX_WBITS, -zlib.MAX_WBITS):
                self.decoder = zlib.decompressobj(window)
                self.size = 0
                try:
                    result = self._inflate(self.prefix)
                except httpx.DecodingError:
                    continue
                except HTTPException as exc:
                    if exc.status_code != 502:
                        raise
                    # The wrong format can expand differently from the valid
                    # one. Its size failure must not prevent bounded fallback.
                    exceeded = True
                    continue
                if self.decoder.eof:
                    self.prefix = bytearray()
                    return result
            if exceeded:
                _check_size(MAX_CONTENT_BYTES + 1)
            raise httpx.DecodingError('Invalid deflate upstream response')
        # decompress(..., max_length) emitted all permitted output. flush(length)
        # is not a hard allocation limit, so do not use it on untrusted bodies.
        if self.decoder is None or not self.decoder.eof:
            raise httpx.DecodingError('Incomplete compressed upstream response')
        return b''


async def iter_limited(response: httpx.Response):
    if response.is_stream_consumed:
        _check_size(len(response.content))
        yield response.content
        return
    encodings = [item.strip().lower() for item in response.headers.get('content-encoding', '').split(',')]
    encodings = [item for item in encodings if item and item != 'identity']
    if len(encodings) > 4 or any(item not in {'gzip', 'deflate'} for item in encodings):
        raise HTTPException(502, 'Unsupported upstream Content-Encoding')
    decoders = [_Inflater(encoding) for encoding in reversed(encodings)]
    size = 0
    async for chunk in response.aiter_raw():
        size += len(chunk)
        _check_size(size)
        for decoder in decoders:
            chunk = decoder.decode(chunk)
        if chunk:
            yield chunk
    for index, decoder in enumerate(decoders):
        chunk = decoder.finish()
        for downstream in decoders[index + 1:]:
            chunk = downstream.decode(chunk)
        if chunk:
            yield chunk
