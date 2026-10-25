import asyncio
import gzip
import zlib

import httpx
import httpcore
import pytest
from fastapi import HTTPException

from subconv import config, upstream, http_body


@pytest.fixture(autouse=True)
def public_dns(monkeypatch):
    async def resolve(host, port):
        return ['93.184.216.34']
    monkeypatch.setattr(upstream, '_resolve_addresses', resolve)
    monkeypatch.setattr(config, 'appConfigInstance', config.AppConfig(ALLOW_PRIVATE_NETWORKS=False))


def fetch(handler, url='https://provider.example/sub'):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await upstream.fetch_upstream(client, url, 'test-agent')
    return asyncio.run(run())


def test_requests_pin_address_and_preserve_host_and_sni():
    def handler(request):
        assert request.url.host == '93.184.216.34'
        assert request.headers['host'] == 'provider.example'
        assert request.extensions['sni_hostname'] == 'provider.example'
        return httpx.Response(200, text='ok')
    assert fetch(handler).text == 'ok'


@pytest.mark.parametrize('address', ['127.0.0.1', '10.0.0.1', '169.254.169.254', '::1', 'fe80::1', '::ffff:127.0.0.1', '224.0.0.1'])
def test_private_and_special_addresses_are_blocked(monkeypatch, address):
    async def resolve(host, port): return [address]
    monkeypatch.setattr(upstream, '_resolve_addresses', resolve)
    def handler(request): pytest.fail('Forbidden address was contacted')
    with pytest.raises(HTTPException) as error:
        fetch(handler)
    assert error.value.status_code == 403


def test_mixed_public_private_dns_is_blocked(monkeypatch):
    async def resolve(host, port): return ['93.184.216.34', '127.0.0.1']
    monkeypatch.setattr(upstream, '_resolve_addresses', resolve)
    with pytest.raises(HTTPException):
        fetch(lambda request: pytest.fail('Mixed DNS was contacted'))


def test_redirect_targets_are_revalidated(monkeypatch):
    seen = []
    async def resolve(host, port):
        seen.append(host)
        return ['127.0.0.1'] if host == 'private.example' else ['93.184.216.34']
    monkeypatch.setattr(upstream, '_resolve_addresses', resolve)
    def handler(request): return httpx.Response(302, headers={'location': 'http://private.example/internal'})
    with pytest.raises(HTTPException) as error:
        fetch(handler)
    assert error.value.status_code == 403
    assert seen == ['provider.example', 'private.example']


def test_private_access_requires_explicit_setting(monkeypatch):
    monkeypatch.setattr(config, 'appConfigInstance', config.AppConfig(ALLOW_PRIVATE_NETWORKS=True))
    async def resolve(host, port): return ['127.0.0.1']
    monkeypatch.setattr(upstream, '_resolve_addresses', resolve)
    assert fetch(lambda request: httpx.Response(200, text='allowed')).text == 'allowed'


def test_upstream_error_body_is_not_read_and_response_is_closed():
    closed = []
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            raise httpx.ReadError('secret internal response')
            yield b''
        async def aclose(self): closed.append(True)
    with pytest.raises(HTTPException) as error:
        fetch(lambda request: httpx.Response(503, stream=Stream()))
    assert error.value.status_code == 502
    assert 'secret' not in error.value.detail
    assert closed


def test_size_limit_closes_response(monkeypatch):
    monkeypatch.setattr(http_body, 'MAX_CONTENT_BYTES', 8)
    closed = []
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self): yield b'0123456789'
        async def aclose(self): closed.append(True)
    with pytest.raises(HTTPException) as error:
        fetch(lambda request: httpx.Response(200, stream=Stream()))
    assert error.value.status_code == 502
    assert closed


@pytest.mark.parametrize('encoding,compress', [('gzip', gzip.compress), ('deflate', zlib.compress)])
def test_encoded_body_is_decoded_once_and_preserves_subscription_headers(encoding, compress):
    content = b'proxies: [{name: A}]'
    encoded = compress(content)
    closed = []
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self): yield encoded
        async def aclose(self): closed.append(True)
    response = fetch(lambda request: httpx.Response(200, headers={
        'content-encoding': encoding,
        'content-length': str(len(encoded)),
        'subscription-userinfo': 'upload=0; download=0; total=100',
    }, stream=Stream()))
    assert response.content == content
    assert 'content-encoding' not in response.headers
    assert response.headers['content-length'] == str(len(content))
    assert response.headers['subscription-userinfo'] == 'upload=0; download=0; total=100'
    assert closed


def test_compressed_response_limit_applies_after_decoding(monkeypatch):
    monkeypatch.setattr(http_body, 'MAX_CONTENT_BYTES', 128)
    encoded = gzip.compress(b'x' * 1024)
    assert len(encoded) < 128
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self): yield encoded
    with pytest.raises(HTTPException) as error:
        fetch(lambda request: httpx.Response(200, headers={'content-encoding': 'gzip'}, stream=Stream()))
    assert error.value.status_code == 502


@pytest.mark.parametrize('first_error', [httpx.ConnectError, httpx.ConnectTimeout])
def test_connection_failure_tries_next_validated_address(monkeypatch, first_error):
    async def resolve(host, port): return ['93.184.216.34', '93.184.216.35']
    monkeypatch.setattr(upstream, '_resolve_addresses', resolve)
    attempted = []
    def handler(request):
        attempted.append(request.url.host)
        if request.url.host.endswith('.34'):
            raise first_error('unavailable', request=request)
        return httpx.Response(200, text='ok')
    assert fetch(handler).text == 'ok'
    assert attempted == ['93.184.216.34', '93.184.216.35']


def test_all_addresses_timing_out_returns_502(monkeypatch):
    async def resolve(host, port): return ['93.184.216.34', '93.184.216.35']
    monkeypatch.setattr(upstream, '_resolve_addresses', resolve)
    attempted = []
    def handler(request):
        attempted.append(request.url.host)
        raise httpx.ConnectTimeout('unavailable', request=request)
    with pytest.raises(HTTPException) as error:
        fetch(handler)
    assert error.value.status_code == 502
    assert attempted == ['93.184.216.34', '93.184.216.35']


def test_pinned_transport_races_tcp_only_preserving_host_sni_and_one_get(monkeypatch):
    attempted, cancelled, writes, sni = [], [], [], []
    class Stream(httpcore.AsyncNetworkStream):
        async def read(self, max_bytes, timeout=None):
            return b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok'
        async def write(self, buffer, timeout=None): writes.append(buffer)
        async def start_tls(self, ssl_context, server_hostname=None, timeout=None):
            sni.append(server_hostname)
            return self
        async def aclose(self): pass
    async def connect(self, host, port, timeout=None, local_address=None, socket_options=None):
        attempted.append(host)
        if host.endswith('.34'):
            try: await asyncio.sleep(30)
            finally: cancelled.append(host)
        return Stream()
    async def resolve(*args): return ['93.184.216.34', '93.184.216.35']
    monkeypatch.setattr(httpcore.AnyIOBackend, 'connect_tcp', connect)
    monkeypatch.setattr(upstream, '_resolve_addresses', resolve)
    async def run():
        async with upstream.upstream_client() as client:
            client.timeout = httpx.Timeout(0.6)
            return await upstream.fetch_upstream(client, 'https://provider.example/sub', 'test')
    assert asyncio.run(run()).text == 'ok'
    assert attempted == ['93.184.216.34', '93.184.216.35']
    assert cancelled == ['93.184.216.34']
    assert sni == ['provider.example']
    request = b''.join(writes)
    assert request.count(b'GET /sub HTTP/1.1') == 1
    assert b'Host: provider.example\r\n' in request


@pytest.mark.parametrize('blackhole', [False, True])
def test_pinned_transport_has_one_connection_deadline_without_repeating_address_set(monkeypatch, blackhole):
    attempted = []
    async def connect(self, host, port, timeout=None, local_address=None, socket_options=None):
        attempted.append(host)
        if blackhole:
            await asyncio.sleep(30)
        raise httpcore.ConnectError('unavailable')
    async def resolve(*args): return ['93.184.216.34', '93.184.216.35']
    monkeypatch.setattr(httpcore.AnyIOBackend, 'connect_tcp', connect)
    monkeypatch.setattr(upstream, '_resolve_addresses', resolve)
    async def run():
        async with upstream.upstream_client() as client:
            client.timeout = httpx.Timeout(0.3)
            await upstream.fetch_upstream(client, 'http://provider.example/sub', 'test')
    with pytest.raises(HTTPException) as error:
        asyncio.run(run())
    assert error.value.status_code == 502
    assert attempted == ['93.184.216.34', '93.184.216.35']


@pytest.mark.parametrize('location', ['ftp://provider.example/file', 'file:///etc/passwd', 'http://provider.example:0/file'])
def test_invalid_redirect_is_502_not_400(location):
    with pytest.raises(HTTPException) as error:
        fetch(lambda request: httpx.Response(302, headers={'location': location}))
    assert error.value.status_code == 502


@pytest.mark.parametrize('url', ['ftp://provider.example/file', 'http://provider.example:0/file'])
def test_invalid_initial_url_remains_400(url):
    with pytest.raises(HTTPException) as error:
        fetch(lambda request: pytest.fail('Invalid URL was fetched'), url)
    assert error.value.status_code == 400


def test_redirect_cookie_uses_logical_host_and_path():
    seen = []
    def handler(request):
        seen.append(request.headers.get('cookie'))
        if request.url.path == '/start':
            return httpx.Response(302, headers={'location': '/sub/data', 'set-cookie': 'access=ok; Domain=provider.example; Path=/sub; Secure'})
        return httpx.Response(200 if request.headers.get('cookie') == 'access=ok' else 401, text='ok')
    assert fetch(handler, 'https://provider.example/start').text == 'ok'
    assert seen == [None, 'access=ok']


@pytest.mark.parametrize('location', ['https://other.example/sub', 'https://provider.example/other', 'http://provider.example/sub'])
def test_redirect_cookie_respects_domain_path_and_secure(location):
    def handler(request):
        if request.url.path == '/start':
            return httpx.Response(302, headers={'location': location, 'set-cookie': 'access=secret; Path=/sub; Secure'})
        assert 'cookie' not in request.headers
        return httpx.Response(200, text='ok')
    assert fetch(handler, 'https://provider.example/start').text == 'ok'


def test_cookies_do_not_leak_between_subscription_fetches():
    async def run():
        def handler(request):
            assert 'cookie' not in request.headers
            return httpx.Response(200, text='ok', headers={'set-cookie': 'access=secret; Path=/'})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            for url in ['https://provider.example/one', 'https://provider.example/two', 'https://other.example/three']:
                await upstream.fetch_upstream(client, url, 'test')
    asyncio.run(run())


@pytest.mark.parametrize('encoding', ['gzip', 'deflate', 'deflate-raw', 'gzip, gzip', 'deflate, gzip'])
@pytest.mark.parametrize('chunk_size', [1, 7, 65536])
def test_bounded_decoding_handles_split_headers_and_stacked_encodings(encoding, chunk_size):
    content = b'proxies: [{name: A}]' * 20
    if encoding == 'deflate-raw':
        encoder = zlib.compressobj(wbits=-zlib.MAX_WBITS)
        encoded = encoder.compress(content) + encoder.flush()
        header = 'deflate'
    else:
        encoded = content
        for name in encoding.split(', '):
            encoded = gzip.compress(encoded) if name == 'gzip' else zlib.compress(encoded)
        header = encoding
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            for offset in range(0, len(encoded), chunk_size):
                yield encoded[offset:offset + chunk_size]
    response = fetch(lambda request: httpx.Response(200, headers={'content-encoding': header}, stream=Stream()))
    assert response.content == content


def test_nested_bomb_is_limited_before_large_allocation(monkeypatch):
    monkeypatch.setattr(http_body, 'MAX_CONTENT_BYTES', 4096)
    encoded = gzip.compress(gzip.compress(b'x' * (1024 * 1024)))
    limits, outputs = [], []
    original = zlib.decompressobj
    class Observed:
        def __init__(self, *args): self.decoder = original(*args)
        def __getattr__(self, name): return getattr(self.decoder, name)
        def decompress(self, data, max_length=0):
            limits.append(max_length)
            assert 0 < max_length <= 4097
            result = self.decoder.decompress(data, max_length)
            outputs.append(len(result))
            return result
    monkeypatch.setattr(http_body.zlib, 'decompressobj', Observed)
    closed = []
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self): yield encoded
        async def aclose(self): closed.append(True)
    with pytest.raises(HTTPException) as error:
        fetch(lambda request: httpx.Response(200, headers={'content-encoding': 'gzip, gzip'}, stream=Stream()))
    assert error.value.status_code == 502
    assert limits and max(outputs) <= 4097
    assert closed


@pytest.mark.parametrize('encoded', [gzip.compress(b'a') + gzip.compress(b'b'), gzip.compress(b'ab')])
def test_concatenated_gzip_members_share_one_budget(encoded, monkeypatch):
    monkeypatch.setattr(http_body, 'MAX_CONTENT_BYTES', 128)
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            for byte in encoded: yield bytes([byte])
    assert fetch(lambda request: httpx.Response(200, headers={'content-encoding': 'gzip'}, stream=Stream())).content == b'ab'


@pytest.mark.parametrize('encoded', [gzip.compress(b'abc')[:-4], b'not gzip', gzip.compress(b'abc') + b'junk'])
def test_corrupt_compressed_body_is_502(encoded):
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self): yield encoded
    with pytest.raises(HTTPException) as error:
        fetch(lambda request: httpx.Response(200, headers={'content-encoding': 'gzip'}, stream=Stream()))
    assert error.value.status_code == 502


@pytest.mark.parametrize('encoding', ['br', 'zstd', ','.join(['gzip'] * 5)])
def test_unsupported_or_excessive_coding_layers_are_rejected(encoding):
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self): pytest.fail('Unsupported encoding body was read'); yield b''
    with pytest.raises(HTTPException) as error:
        fetch(lambda request: httpx.Response(200, headers={'content-encoding': encoding}, stream=Stream()))
    assert error.value.status_code == 502


@pytest.mark.parametrize('chunk_size', [1, 2, 3, 4, 5, 7, 65536])
def test_raw_deflate_with_zlib_like_prefix_still_works(chunk_size):
    # A non-final stored block may have padding bits resembling a zlib header.
    content = b'x' * 156
    encoded = b'\x78\x9c\x00\x63\xff' + content + b'\x01\x00\x00\xff\xff'
    assert zlib.decompress(encoded, -zlib.MAX_WBITS) == content
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            for offset in range(0, len(encoded), chunk_size): yield encoded[offset:offset + chunk_size]
    assert fetch(lambda request: httpx.Response(200, headers={'content-encoding': 'deflate'}, stream=Stream())).content == content


@pytest.mark.parametrize('chunk_size', [1, 4096, 65536])
def test_raw_deflate_fallback_survives_wrong_candidate_size_limit(monkeypatch, chunk_size):
    limit = 65536
    monkeypatch.setattr(http_body, 'MAX_CONTENT_BYTES', limit)
    encoder = zlib.compressobj(wbits=-zlib.MAX_WBITS)
    bomb = encoder.compress(b'x' * (limit + 1)) + encoder.flush()
    # This valid raw stored block resembles a zlib header. Interpreting its
    # payload as zlib expands the embedded bomb, exceeding the wrong budget.
    content = (b'\x9c\xf8' + b'\0' * 1891 + bomb).ljust(0xf89c, b'\0')
    encoded = b'\x78\x9c\xf8\x63\x07' + content + b'\x01\x00\x00\xff\xff'
    assert len(content) < limit and zlib.decompress(encoded, -zlib.MAX_WBITS) == content
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            for offset in range(0, len(encoded), chunk_size):
                yield encoded[offset:offset + chunk_size]
    assert fetch(lambda request: httpx.Response(200, headers={'content-encoding': 'deflate'}, stream=Stream())).content == content


def test_nested_gzip_members_have_bounded_input_windows(monkeypatch):
    inner = gzip.compress(b'', mtime=0) * 1000 + gzip.compress(b'ok', mtime=0)
    encoded = gzip.compress(inner, mtime=0)
    original = zlib.decompressobj
    windows = []
    class Observed:
        def __init__(self, *args): self.decoder = original(*args)
        def __getattr__(self, name): return getattr(self.decoder, name)
        def decompress(self, data, max_length=0):
            windows.append(len(data))
            assert 0 < len(data) <= 4096
            return self.decoder.decompress(data, max_length)
    monkeypatch.setattr(http_body.zlib, 'decompressobj', Observed)
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self): yield encoded
    response = fetch(lambda request: httpx.Response(200, headers={'content-encoding': 'gzip, gzip'}, stream=Stream()))
    assert response.content == b'ok'
    assert len(windows) > 1000
