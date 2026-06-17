import re
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.requests import Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from . import config
from . import packer
from . import subscription
from .converter import ConvertsV2Ray


@asynccontextmanager
async def lifespan(_: FastAPI):
    config.validate_templates_on_startup()
    yield


app = FastAPI(lifespan=lifespan)

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

    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await _fetch_remote_response(client, url, "v2rayn")
        result = await subscription.parseSubs(resp.text)
    return Response(content=result, headers=headers)


@app.get("/sub")
async def sub(request: Request):
    args = request.query_params
    interval = args.get("interval", "1800")
    short = args.get("short")
    notproxyrule = args.get("npr")
    direct_param = args.get("direct")
    template_name = _resolve_template_name(args.get("template"))
    template_config = await _load_template(template_name)

    url_param = args.get("url")
    if url_param is None:
        raise HTTPException(
            status_code=400, detail="Missing required query parameter: url"
        )

    url, urlstandalone_raw = _split_sources(url_param)

    urlstandby_param = args.get("urlstandby")
    urlstandby: list[str] | None = None
    urlstandbystandalone_raw: str | None = None
    if urlstandby_param:
        urlstandby, urlstandbystandalone_raw = _split_sources(urlstandby_param)

    urlstandalone = (
        await ConvertsV2Ray(urlstandalone_raw) if urlstandalone_raw else None
    )
    urlstandbystandalone = (
        await ConvertsV2Ray(urlstandbystandalone_raw)
        if urlstandbystandalone_raw
        else None
    )
    direct_hosts = _resolve_direct_hosts(direct_param, url, urlstandby)

    user_agent = request.headers.get("User-Agent", "v2rayn")

    async with httpx.AsyncClient(follow_redirects=True) as client:
        headers = {"Content-Type": "text/yaml;charset=utf-8"}
        content: list[str] | None = []
        if url is not None:
            for i in range(len(url)):
                resp = await _fetch_remote_response(client, url[i], user_agent)
                content.append(await subscription.parseSubs(resp.text))
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
    if content is not None and len(content) == 0:
        content = None
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
        direct_hosts=direct_hosts,
        content=content,
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
    client = httpx.AsyncClient()
    response = await client.send(
        client.build_request("GET", url, headers={"User-Agent": user_agent}),
        stream=True,
    )

    if response.status_code < 200 or response.status_code >= 400:
        body = await response.aread()
        await response.aclose()
        await client.aclose()
        raise HTTPException(
            status_code=response.status_code,
            detail=body.decode("utf-8", errors="ignore"),
        )

    async def stream_body():
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    content_type = response.headers.get("Content-Type")
    return StreamingResponse(stream_body(), media_type=content_type)


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


def _validate_remote_url(url: str) -> str:
    try:
        parsed = httpx.URL(url)
    except httpx.InvalidURL as exc:
        raise HTTPException(status_code=400, detail=f"Invalid upstream URL: {url}") from exc

    if parsed.scheme not in {"http", "https"} or parsed.host is None:
        raise HTTPException(status_code=400, detail=f"Invalid upstream URL: {url}")

    return str(parsed)


def _resolve_direct_hosts(
    direct_param: str | None,
    url: list[str] | None,
    urlstandby: list[str] | None,
) -> list[str] | None:
    if direct_param is None or direct_param.strip() == "":
        return None

    allowed_hosts = {
        host
        for source in (url or []) + (urlstandby or [])
        if (host := _resolve_remote_url_host(source)) is not None
    }
    direct_hosts: list[str] = []
    for item in filter(None, re.split(r"[|\n]", direct_param)):
        candidate = item.strip()
        if candidate == "":
            continue
        host = _resolve_direct_host(candidate)
        if host is None:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid direct target: {candidate}",
            )
        if host not in allowed_hosts:
            raise HTTPException(
                status_code=400,
                detail=f"Direct target is not present in url/urlstandby: {candidate}",
            )
        if host not in direct_hosts:
            direct_hosts.append(host)

    return direct_hosts or None


def _resolve_direct_host(candidate: str) -> str | None:
    if candidate.startswith(("http://", "https://")):
        try:
            parsed = httpx.URL(candidate)
        except httpx.InvalidURL:
            return None
        return parsed.host.lower() if parsed.host is not None else None

    if "/" in candidate or "?" in candidate or "#" in candidate:
        return None

    parsed = urlparse(f"//{candidate}")
    return parsed.hostname.lower() if parsed.hostname is not None else None


def _resolve_remote_url_host(url: str) -> str | None:
    try:
        parsed = httpx.URL(url)
    except httpx.InvalidURL as exc:
        raise HTTPException(status_code=400, detail=f"Invalid upstream URL: {url}") from exc

    if parsed.scheme not in {"http", "https"} or parsed.host is None:
        raise HTTPException(status_code=400, detail=f"Invalid upstream URL: {url}")
    return parsed.host.lower()


async def _fetch_remote_response(
    client: httpx.AsyncClient, url: str, user_agent: str
) -> httpx.Response:
    try:
        resp = await client.get(
            _validate_remote_url(url), headers={"User-Agent": user_agent}
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch upstream URL: {exc}"
        ) from exc

    if resp.status_code < 200 or resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp
