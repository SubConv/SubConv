import asyncio
import re
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from anyio import CancelScope
from fastapi import FastAPI, HTTPException
from fastapi.requests import Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from starlette.background import BackgroundTask
from urllib.parse import urlencode

from . import config
from . import packer
from . import subscription
from .converter import ConvertsV2Ray
from .converter.util import ParseError
from .upstream import fetch_upstream, open_upstream, iter_limited, upstream_client


@asynccontextmanager
async def lifespan(_: FastAPI):
    config.validate_templates_on_startup()
    yield


app = FastAPI(lifespan=lifespan)


class _ProxyStreamingResponse(StreamingResponse):
    """Close upstream resources even if sending headers fails before iteration."""

    async def __call__(self, scope, receive, send):
        cleanup, self.background = self.background, None
        try:
            await super().__call__(scope, receive, send)
        finally:
            if cleanup is not None:
                await cleanup()

STATIC_DIR = Path("mainpage/dist")
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def mainpage():
    index_path = STATIC_DIR / "index.html"
    if index_path.is_file():
        return FileResponse(index_path)
    return Response(status_code=404)


@app.get("/robots.txt")
async def robots():
    if config.get_app_config().DISALLOW_ROBOTS:
        return Response(content="User-agent: *\nDisallow: /", media_type="text/plain")
    return Response(status_code=404)


@app.get("/config")
async def runtime_config():
    return {
        "defaultTemplate": config.default_template_name(),
        "availableTemplates": config.available_templates(),
    }


@app.get("/provider")
async def provider(request: Request):
    headers = {"Content-Type": "text/yaml;charset=utf-8"}
    url = request.query_params.get("url")
    if url is None:
        raise HTTPException(
            status_code=400, detail="Missing required query parameter: url"
        )

    async with upstream_client() as client:
        resp = await _fetch_remote_response(client, url, "v2rayn")
        result = await asyncio.to_thread(subscription.dump_proxies, await _parse_subscription(resp.text))
    return Response(content=result, headers=headers)


@app.get("/sub")
async def sub(request: Request):
    args = request.query_params
    try:
        interval = int(args.get("interval", "1800"))
        if not 1 <= interval <= 2**31 - 1:
            raise ValueError
    except ValueError as exc:
        raise HTTPException(400, "interval must be an integer between 1 and 2147483647") from exc
    short = args.get("short")
    notproxyrule = args.get("npr")
    template_name = _resolve_template_name(args.get("template"))
    template_config = await _load_template(template_name)

    url_param = args.get("url")
    if url_param is None:
        raise HTTPException(
            status_code=400, detail="Missing required query parameter: url"
        )

    url, urlstandalone_raw = _split_sources(url_param)
    if not url and not urlstandalone_raw:
        raise HTTPException(400, "At least one primary subscription or share link is required")

    urlstandby_param = args.get("urlstandby")
    urlstandby: list[str] | None = None
    urlstandbystandalone_raw: str | None = None
    if urlstandby_param:
        urlstandby, urlstandbystandalone_raw = _split_sources(urlstandby_param)

    urlstandalone = (
        await _parse_links(urlstandalone_raw) if urlstandalone_raw else None
    )
    urlstandbystandalone = (
        await _parse_links(urlstandbystandalone_raw)
        if urlstandbystandalone_raw
        else None
    )

    user_agent = request.headers.get("User-Agent", "v2rayn")

    async with upstream_client() as client:
        headers = {"Content-Type": "text/yaml;charset=utf-8"}
        provider_names: list[str] = []
        if url is not None:
            for i in range(len(url)):
                resp = await _fetch_remote_response(client, url[i], user_agent)
                nodes = await _parse_subscription(resp.text, i + 1)
                provider_names.extend(node["name"] for node in nodes)
                if len(url) == 1:
                    original_headers = resp.headers
                    if "subscription-userinfo" in original_headers:
                        headers["subscription-userinfo"] = original_headers[
                            "subscription-userinfo"
                        ]
                    if "Content-Disposition" in original_headers:
                        headers["Content-Disposition"] = original_headers[
                            "Content-Disposition"
                        ].replace("attachment", "inline")
                url[i] = "{}provider?{}".format(
                    str(request.base_url), urlencode({"url": url[i]})
                )
    if urlstandby:
        for i in range(len(urlstandby)):
            urlstandby[i] = "{}provider?{}".format(
                str(request.base_url), urlencode({"url": urlstandby[i]})
            )

    hostname = request.url.hostname
    if hostname is None:
        raise HTTPException(status_code=400, detail="Unable to determine request host")

    match = re.search(r"([^:]+)(:\d{1,5})?", hostname)
    if match is None:
        raise HTTPException(status_code=400, detail="Unable to parse request host")

    domain = match.group(1)
    result = await packer.pack(
        url=url,
        urlstandalone=urlstandalone,
        urlstandby=urlstandby,
        urlstandbystandalone=urlstandbystandalone,
        provider_names=provider_names,
        interval=interval,
        domain=domain,
        short=short,
        notproxyrule=notproxyrule,
        base_url=str(request.base_url),
        template_name=template_name,
        template_config=template_config,
    )
    return Response(content=result, headers=headers)


@app.get("/proxy")
async def proxy(request: Request, url: str):
    template_name = _resolve_template_name(request.query_params.get("template"))
    template_config = await _load_template(template_name)
    is_whitelisted = False
    for rule in template_config.RULESET:
        if rule[1] == url:
            is_whitelisted = True
            break
    if not is_whitelisted:
        raise HTTPException(status_code=403, detail="Forbidden: URL not in whitelist")

    user_agent = request.headers.get("User-Agent", "v2rayn")
    client = upstream_client()
    response = None

    async def close_resources():
        # Starlette cancels the stream when its downstream client disconnects.
        # Shield cleanup so cancellation cannot interrupt socket closure.
        with CancelScope(shield=True):
            try:
                if response is not None:
                    await response.aclose()
            finally:
                await client.aclose()

    try:
        response = await open_upstream(client, url, user_agent)
    except BaseException:
        await close_resources()
        raise

    async def stream_body():
        try:
            async with asyncio.timeout(30):
                async for chunk in iter_limited(response):
                    yield chunk
        finally:
            await close_resources()

    return _ProxyStreamingResponse(
        stream_body(),
        media_type=response.headers.get("Content-Type"),
        background=BackgroundTask(close_resources),
    )


@app.get("/{path:path}")
async def index(path: str):
    static_path = _resolve_static_path(path)
    if static_path is not None and static_path.is_file():
        return FileResponse(static_path)
    raise HTTPException(status_code=404, detail="Not Found")


def _split_sources(source: str) -> tuple[list[str] | None, str | None]:
    remote_urls: list[str] = []
    standalone_urls: list[str] = []

    for item in filter(None, re.split(r"[|\n]", source)):
        item = item.strip()
        if (
            item.startswith("http://") or item.startswith("https://")
        ) and not item.startswith("https://t.me/"):
            remote_urls.append(item)
        else:
            standalone_urls.append(item)

    standalone = "\n".join(standalone_urls) or None
    return (remote_urls or None, standalone)


def _resolve_template_name(template_name: str | None) -> str:
    try:
        return config.normalize_template_name(template_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def _load_template(template_name: str) -> config.TemplateConfig:
    try:
        return config.load_runtime_template(template_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=500, detail=f"Invalid template file '{template_name}': {exc}"
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _resolve_static_path(path: str) -> Path | None:
    try:
        static_root = STATIC_DIR.resolve()
        requested_path = (static_root / path).resolve()
        requested_path.relative_to(static_root)
    except ValueError:
        return None

    return requested_path


async def _parse_links(content: str):
    try:
        return await ConvertsV2Ray(content)
    except ParseError as exc:
        raise HTTPException(400, str(exc)) from exc


async def _parse_subscription(content: str, source: int = 1):
    try:
        return await subscription.parse_nodes(content)
    except ParseError as exc:
        raise HTTPException(502, f"Subscription {source}: {exc}") from exc


async def _fetch_remote_response(
    client: httpx.AsyncClient, url: str, user_agent: str
) -> httpx.Response:
    return await fetch_upstream(client, url, user_agent)
