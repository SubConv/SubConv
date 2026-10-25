"""Fetch HTTP resources using validated, pinned DNS addresses."""

import asyncio
import ipaddress
import socket
from contextvars import ContextVar

import anyio
import httpcore
import httpx
from fastapi import HTTPException

from . import config
from .http_body import iter_limited


_checked_addresses = ContextVar('subconv_checked_addresses', default=())


class _PinnedBackend(httpcore.AnyIOBackend):
    """Race checked TCP addresses before sending a single HTTP request."""

    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        addresses = list(_checked_addresses.get())
        if not addresses or host not in addresses:
            raise httpcore.ConnectError('Missing validated upstream addresses')
        # Try the other address family second, as in Happy Eyeballs.
        for index, address in enumerate(addresses[1:], 1):
            if (':' in address) != (':' in addresses[0]):
                addresses.insert(1, addresses.pop(index))
                break
        connect = super().connect_tcp
        winner = None
        errors = []

        async def attempt(address, finished):
            nonlocal winner
            try:
                stream = await connect(address, port, timeout, local_address, socket_options)
                if winner is None:
                    winner = stream
                    group.cancel_scope.cancel()
                else:
                    with anyio.CancelScope(shield=True):
                        await stream.aclose()
            except (httpcore.ConnectError, httpcore.ConnectTimeout) as exc:
                errors.append(exc)
            finally:
                finished.set()

        try:
            with anyio.fail_after(timeout):
                async with anyio.create_task_group() as group:
                    for address in addresses:
                        finished = anyio.Event()
                        group.start_soon(attempt, address, finished)
                        with anyio.move_on_after(0.25):
                            await finished.wait()
        except BaseException as exc:
            if winner is not None:
                with anyio.CancelScope(shield=True):
                    await winner.aclose()
            if isinstance(exc, TimeoutError):
                raise httpcore.ConnectTimeout('Upstream connection deadline exceeded') from exc
            raise
        if winner is not None:
            return winner
        raise errors[-1] if errors else httpcore.ConnectError('Unable to connect to upstream')


class _PinnedTransport(httpx.AsyncHTTPTransport):
    def __init__(self):
        # HTTPX 0.28's protocol adapter accepts its HTTPcore pool through _pool;
        # only this integration point is private. Keep HTTP and TLS handling in
        # HTTPX/HTTPcore instead of duplicating their transport implementation.
        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=httpx.create_ssl_context(trust_env=False),
            max_keepalive_connections=0, network_backend=_PinnedBackend(),
        )

    async def handle_async_request(self, request):
        token = _checked_addresses.set(tuple(request.extensions['subconv_addresses']))
        request.extensions['subconv_address_race'] = True
        try:
            return await super().handle_async_request(request)
        finally:
            _checked_addresses.reset(token)


def upstream_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(trust_env=False, transport=_PinnedTransport())


async def _resolve_addresses(host: str, port: int) -> list[str]:
    try:
        records = await asyncio.wait_for(
            asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM),
            timeout=5,
        )
    except (OSError, TimeoutError) as exc:
        raise HTTPException(502, 'Unable to resolve upstream host') from exc
    addresses = list(dict.fromkeys(record[4][0] for record in records))
    if not addresses:
        raise HTTPException(502, 'Upstream host has no addresses')
    return addresses


def _is_public(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast and not ip.is_reserved


async def open_upstream(client: httpx.AsyncClient, url: str, user_agent: str) -> httpx.Response:
    # Keep cookies within one logical redirect chain, never across subscriptions
    # or numeric origins that happen to serve multiple unrelated hostnames.
    cookies = httpx.Cookies()
    for redirect_count in range(11):
        try:
            target = httpx.URL(url)
            if target.scheme not in {'http', 'https'} or not target.host or target.port == 0:
                raise ValueError
        except (httpx.InvalidURL, ValueError) as exc:
            if redirect_count:
                raise HTTPException(502, 'Invalid upstream redirect') from exc
            raise HTTPException(400, 'Invalid upstream HTTP URL') from exc

        addresses = await _resolve_addresses(target.host, target.port or (443 if target.scheme == 'https' else 80))
        if not config.get_app_config().ALLOW_PRIVATE_NETWORKS:
            if not all(_is_public(address) for address in addresses):
                raise HTTPException(403, 'Upstream private-network access is disabled')

        # Retain Host and TLS SNI while connecting to the checked numeric address.
        response = None
        for address in addresses:
            request = httpx.Request('GET', target, headers={
                'User-Agent': user_agent,
                'Accept-Encoding': 'identity',
                # Numeric origins can belong to different TLS hosts. Never reuse
                # an HTTP/1 connection across logical hostnames sharing an IP.
                'Connection': 'close',
            }, extensions={'sni_hostname': target.host, 'subconv_addresses': tuple(addresses)})
            cookies.set_cookie_header(request)
            request.url = target.copy_with(host=address)
            try:
                response = await client.send(request, stream=True, follow_redirects=False)
                # Cookie policies must see the logical URL, not the pinned IP.
                request.url = target
                cookies.extract_cookies(response)
                break
            except (httpx.ConnectError, httpx.ConnectTimeout):
                # Our transport already tried the entire checked address set.
                # Alternate transports still receive ordinary address fallback.
                if request.extensions.get('subconv_address_race'):
                    break
                continue
            except httpx.RequestError as exc:
                raise HTTPException(502, 'Failed to fetch upstream resource') from exc
        if response is None:
            raise HTTPException(502, 'Unable to connect to upstream host')
        if response.status_code in {301, 302, 303, 307, 308}:
            location = response.headers.get('location')
            await response.aclose()
            if not location:
                raise HTTPException(502, 'Upstream redirect has no location')
            try:
                url = str(target.join(location))
            except httpx.InvalidURL as exc:
                raise HTTPException(502, 'Invalid upstream redirect') from exc
            continue
        if not 200 <= response.status_code < 300:
            status = response.status_code
            await response.aclose()
            raise HTTPException(502, f'Upstream returned HTTP {status}')
        return response
    raise HTTPException(502, 'Too many upstream redirects')


async def fetch_upstream(client: httpx.AsyncClient, url: str, user_agent: str) -> httpx.Response:
    response = await open_upstream(client, url, user_agent)
    try:
        async with asyncio.timeout(30):
            content = b''.join([chunk async for chunk in iter_limited(response)])
        # iter_limited() has decoded the body. Do not decode it again or retain
        # lengths/framing that describe the upstream's encoded representation.
        headers = response.headers.copy()
        for name in ('content-encoding', 'content-length', 'transfer-encoding'):
            headers.pop(name, None)
        return httpx.Response(response.status_code, headers=headers, content=content, request=response.request)
    except (httpx.RequestError, TimeoutError) as exc:
        raise HTTPException(502, 'Failed to read upstream response') from exc
    finally:
        await response.aclose()
