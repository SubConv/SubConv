import asyncio
import base64
import gzip
import importlib

import anyio

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from subconv import config, upstream

routes = importlib.import_module('subconv.app')


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(config, 'appConfigInstance', config.AppConfig(ALLOW_PRIVATE_NETWORKS=False))
    with TestClient(routes.app, raise_server_exceptions=False) as client:
        yield client


@pytest.mark.parametrize('interval', ['0', '-1', 'abc', '2147483648'])
def test_invalid_interval_fails_before_fetch(client, monkeypatch, interval):
    async def unexpected(*args): pytest.fail('Invalid interval fetched upstream')
    monkeypatch.setattr(routes, '_fetch_remote_response', unexpected)
    response = client.get('/sub', params={'url': 'https://example.com/sub', 'interval': interval})
    assert response.status_code == 400


@pytest.mark.parametrize('source', ['', '|', ' \n '])
def test_empty_primary_sources_are_rejected_even_with_standby(client, source):
    response = client.get('/sub', params={'url': source, 'urlstandby': 'trojan://pw@example.com:443#HK', 'template': 'general'})
    assert response.status_code == 400


@pytest.mark.parametrize('path', ['/sub', '/provider'])
def test_deep_legacy_json_returns_502_instead_of_500(client, monkeypatch, path):
    raw = '{"add":"example.com","id":"u","port":443,"extra":' + '[' * 10000 + '0' + ']' * 10000 + '}'
    link = 'vmess://' + base64.b64encode(raw.encode()).decode()
    async def fetch(*args): return httpx.Response(200, text=link)
    monkeypatch.setattr(routes, '_fetch_remote_response', fetch)
    assert client.get(path, params={'url': 'https://provider.example/sub'}).status_code == 502


def test_node_limit_reports_direct_400_and_upstream_502(client, monkeypatch):
    from subconv.converter import parser
    monkeypatch.setattr(parser, 'MAX_PROXY_NODES', 2)
    links = ['http://a:1#n'] * 3
    # Use a standalone protocol so /sub does not treat the input as an upstream URL.
    direct = '|'.join(['trojan://pw@example.com:443#n'] * 3)
    assert client.get('/sub', params={'url': direct}).status_code == 400
    async def fetch(*args): return httpx.Response(200, text='\n'.join(links))
    monkeypatch.setattr(routes, '_fetch_remote_response', fetch)
    assert client.get('/provider', params={'url': 'https://provider.example/sub'}).status_code == 502


@pytest.mark.parametrize('bad', ['trojan://secret@example.com:bad', 'trojan:/secret@example.com:443'])
def test_invalid_direct_link_reports_error_without_returning_partial_config(client, bad):
    response = client.get('/sub', params={'url': 'trojan://pw@example.com:443#good|' + bad})
    assert response.status_code == 400
    assert 'Line 2' in response.json()['detail']
    assert 'secret' not in response.text


@pytest.mark.parametrize('path', ['/sub', '/provider'])
def test_invalid_subscription_is_502(client, monkeypatch, path):
    async def fetch(*args):
        return httpx.Response(200, text='trojan://secret@example.com:bad')
    monkeypatch.setattr(routes, '_fetch_remote_response', fetch)
    response = client.get(path, params={'url': 'https://example.com/sub'})
    assert response.status_code == 502
    assert 'Subscription 1' in response.json()['detail']
    assert 'secret' not in response.text


def test_programming_errors_remain_500(client, monkeypatch):
    async def broken(*args): raise RuntimeError('bug')
    monkeypatch.setattr(routes, '_parse_links', broken)
    assert client.get('/sub', params={'url': 'trojan://pw@example.com:443'}).status_code == 500


@pytest.mark.parametrize('path', ['/sub', '/provider'])
def test_private_upstream_is_blocked_at_route(client, monkeypatch, path):
    async def resolve(*args): return ['127.0.0.1']
    monkeypatch.setattr(upstream, '_resolve_addresses', resolve)
    assert client.get(path, params={'url': 'http://localhost/secret'}).status_code == 403


@pytest.mark.parametrize('failure', ['connect', 'body', 'success'])
def test_proxy_closes_client_and_response_on_all_paths(client, monkeypatch, failure):
    closed = []
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            if failure == 'body':
                raise httpx.ReadError('broken stream')
            yield b'rule-content'
        async def aclose(self): closed.append('response')
    class UpstreamClient:
        def __init__(self, **kwargs): pass
        async def aclose(self): closed.append('client')
    async def open_response(*args):
        if failure == 'connect': raise HTTPException(502, 'Failed to fetch upstream resource')
        return httpx.Response(200, stream=Stream())
    async def template(*args):
        return config.TemplateConfig(RULESET=[('DIRECT', 'https://rules.example/list')])
    monkeypatch.setattr(routes, '_load_template', template)
    monkeypatch.setattr(routes.httpx, 'AsyncClient', UpstreamClient)
    monkeypatch.setattr(routes, 'open_upstream', open_response)
    response = client.get('/proxy', params={'url': 'https://rules.example/list'})
    assert 'client' in closed
    if failure == 'connect': assert response.status_code == 502
    else: assert 'response' in closed
    if failure == 'success': assert response.content == b'rule-content'


def test_proxy_disconnect_cannot_cancel_resource_cleanup(monkeypatch):
    closed = []
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self): yield b'rule-content'
        async def aclose(self):
            await anyio.sleep(0)
            closed.append('response')
    class UpstreamClient:
        def __init__(self, **kwargs): pass
        async def aclose(self):
            await anyio.sleep(0)
            closed.append('client')
    async def open_response(*args): return httpx.Response(200, stream=Stream())
    async def template(*args):
        return config.TemplateConfig(RULESET=[('DIRECT', 'https://rules.example/list')])
    monkeypatch.setattr(routes, '_load_template', template)
    monkeypatch.setattr(routes.httpx, 'AsyncClient', UpstreamClient)
    monkeypatch.setattr(routes, 'open_upstream', open_response)
    async def run():
        request = routes.Request({'type': 'http', 'query_string': b'', 'headers': []})
        response = await routes.proxy(request, 'https://rules.example/list')
        assert await anext(response.body_iterator) == b'rule-content'
        with anyio.CancelScope() as scope:
            scope.cancel()
            await response.body_iterator.aclose()
        assert closed == ['response', 'client']
    asyncio.run(run())


@pytest.mark.parametrize('path', ['/sub', '/provider'])
@pytest.mark.parametrize('value', ['2001-13-01', '!!timestamp invalid', '!!float nope'])
def test_invalid_yaml_scalar_returns_502(client, monkeypatch, path, value):
    async def fetch(*args):
        return httpx.Response(200, text='proxies: [{name: A, extra: ' + value + '}]')
    monkeypatch.setattr(routes, '_fetch_remote_response', fetch)
    response = client.get(path, params={'url': 'https://provider.example/sub'})
    assert response.status_code == 502
    assert 'Subscription 1' in response.json()['detail']


@pytest.mark.parametrize('path', ['/sub', '/provider'])
def test_upstream_missing_link_delimiter_returns_502(client, monkeypatch, path):
    async def fetch(*args):
        return httpx.Response(200, text='trojan://pw@example.com:443#good\ntrojan:/secret@example.com:443')
    monkeypatch.setattr(routes, '_fetch_remote_response', fetch)
    response = client.get(path, params={'url': 'https://provider.example/sub'})
    assert response.status_code == 502
    assert 'Line 2' in response.json()['detail']
    assert 'secret' not in response.text


@pytest.mark.parametrize('path', ['/sub', '/provider'])
@pytest.mark.parametrize('wrapped', [False, True])
def test_gzip_subscription_with_metadata_works_end_to_end(client, monkeypatch, path, wrapped):
    raw = '#profile-web-page-url: https://provider.example/\ntrojan://pw@example.com:443#HK'
    if wrapped:
        raw = base64.b64encode(raw.encode()).decode()
    encoded = gzip.compress(raw.encode())
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self): yield encoded
    def handler(request):
        return httpx.Response(200, headers={'content-encoding': 'gzip', 'content-length': str(len(encoded))}, stream=Stream())
    original_client = httpx.AsyncClient
    def upstream_client(**kwargs):
        return original_client(transport=httpx.MockTransport(handler), **kwargs)
    async def resolve(*args): return ['93.184.216.34']
    monkeypatch.setattr(upstream, '_resolve_addresses', resolve)
    monkeypatch.setattr(routes, 'upstream_client', upstream_client)
    response = client.get(path, params={'url': 'https://provider.example/sub'})
    assert response.status_code == 200
    if path == '/provider':
        assert 'name: HK' in response.text
    else:
        assert '🇭🇰 香港节点' in response.text


@pytest.mark.parametrize('path', ['/sub', '/provider'])
def test_base64_subscription_with_bad_tail_returns_502(client, monkeypatch, path):
    raw = base64.b64encode(b'trojan://pw@example.com:443#HKx').decode() + '\nunknown://secret'
    async def fetch(*args): return httpx.Response(200, text=raw)
    monkeypatch.setattr(routes, '_fetch_remote_response', fetch)
    response = client.get(path, params={'url': 'https://provider.example/sub'})
    assert response.status_code == 502
    assert 'secret' not in response.text


def test_large_share_subscription_has_consistent_provider_and_sub_results(client, monkeypatch):
    raw = '\n'.join(f'trojan://pw@example.com:443#HK{i}' for i in range(7000))
    async def fetch(*args): return httpx.Response(200, text=raw)
    monkeypatch.setattr(routes, '_fetch_remote_response', fetch)
    for path in ['/provider', '/sub']:
        response = client.get(path, params={'url': 'https://provider.example/sub'})
        assert response.status_code == 200, response.text
        assert 'HK6999' in response.text if path == '/provider' else '🇭🇰 香港节点' in response.text


@pytest.mark.parametrize('path', ['/provider', '/sub'])
def test_normalized_yaml_is_not_rechecked_as_external_input(client, monkeypatch, path):
    from subconv import yaml_utils
    monkeypatch.setattr(yaml_utils, 'MAX_CONTENT_BYTES', 1024)
    raw = 'proxies: [{name: HK, extra: "' + '\t' * 600 + '"}]'
    assert len(raw.encode()) < 1024
    async def fetch(*args): return httpx.Response(200, text=raw)
    monkeypatch.setattr(routes, '_fetch_remote_response', fetch)
    response = client.get(path, params={'url': 'https://provider.example/sub'})
    assert response.status_code == 200
    if path == '/provider': assert len(response.content) > 1024


@pytest.mark.parametrize('path', ['/provider', '/sub'])
def test_unrenderable_yaml_integer_returns_502(client, monkeypatch, path):
    raw = 'proxies: [{name: A, type: direct, extra: 0x' + 'f' * 4000 + '}]'
    async def fetch(*args): return httpx.Response(200, text=raw)
    monkeypatch.setattr(routes, '_fetch_remote_response', fetch)
    assert client.get(path, params={'url': 'https://provider.example/sub'}).status_code == 502


@pytest.mark.parametrize('disconnect_at', ['http.response.start', 'http.response.body'])
def test_proxy_closes_upstream_on_asgi24_send_disconnect(monkeypatch, disconnect_at):
    from starlette.requests import ClientDisconnect
    closed = []
    class Client:
        async def aclose(self): closed.append('client')
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self): yield b'rule-content'
        async def aclose(self): closed.append('response')
    async def open_response(*args): return httpx.Response(200, stream=Stream())
    async def template(*args):
        return config.TemplateConfig(RULESET=[('DIRECT', 'https://rules.example/list')])
    monkeypatch.setattr(routes, 'upstream_client', Client)
    monkeypatch.setattr(routes, 'open_upstream', open_response)
    monkeypatch.setattr(routes, '_load_template', template)

    async def run():
        request = routes.Request({'type': 'http', 'query_string': b'', 'headers': []})
        response = await routes.proxy(request, 'https://rules.example/list')
        async def send(message):
            if message['type'] == disconnect_at:
                raise OSError('downstream disconnected')
        async def receive(): return {'type': 'http.disconnect'}
        with pytest.raises(ClientDisconnect):
            await response({'type': 'http', 'asgi': {'spec_version': '2.4'}}, receive, send)
        assert set(closed) == {'response', 'client'}
    asyncio.run(run())
