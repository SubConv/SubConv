#!/usr/bin/env python3
# coding=utf-8

from fastapi import FastAPI, HTTPException
from fastapi.requests import Request
from fastapi.responses import FileResponse, Response, StreamingResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

import httpx

import yaml

from urllib.parse import urlencode, unquote, urlparse
import argparse
from pathlib import Path
import re
import os

DISALLOW_ROBOTS = bool(eval(os.environ.get("DISALLOW_ROBOTS", "False")))

"""
main routine
"""
if __name__ == "__main__":
    from modules import config_template
    # generate config file
    class GenerateConfigAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            yaml.SafeDumper.ignore_aliases = lambda *args : True
            if values == "default":
                with open("config.yaml", "w", encoding="utf-8") as f:
                    f.write(yaml.safe_dump(config_template.template_default, allow_unicode=True, sort_keys=False))
            elif values == "zju":
                with open("config.yaml", "w", encoding="utf-8") as f:
                    f.write(yaml.safe_dump(config_template.template_zju, allow_unicode=True, sort_keys=False))
            parser.exit()

    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", "-P", type=int, default=8080, help="port of the api, default: 8080")
    parser.add_argument("--host", "-H", type=str, default="0.0.0.0", help="host of the api, default: 0.0.0.0")
    parser.add_argument("--version", "-V", action="version", version="version: v2.0.0")
    parser.add_argument("--generate-config", "-G", type=str, choices=("default", "zju"), action=GenerateConfigAction, help="generate a default config file")
    args = parser.parse_args()

    # init config
    from modules import config

    # Debug
    # uvicorn.run("api:app", host=args.host, port=args.port, reload=True)
    # Production
    print("host:", args.host)
    print("port:", args.port)
    if DISALLOW_ROBOTS:
        print("robots: Disallow")
    else:
        print("robots: Allow")
    module_name = __name__.split(".")[0]
    uvicorn.run(module_name+":app", host=args.host, port=args.port, workers=4)


"""
FastAPI App
"""
from modules import pack
from modules import parse
from modules.convert import converter


def length(sth):
    if sth is None:
        return 0
    else:
        return len(sth)

app = FastAPI()
async def fetch_url(url: str, request: Request, method: str):
    headers = {"Content-Type": "text/yaml;charset=utf-8"}
    redirect_count = 0
    max_redirects = 5

    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method, url, headers={"User-Agent": request.headers["User-Agent"]}
        )
        if resp.status_code < 200 or resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        elif resp.status_code >= 300 and resp.status_code < 400:
            while resp.status_code >= 300 and resp.status_code < 400:
                if redirect_count >= max_redirects:
                    raise HTTPException(status_code=500, detail="Too many redirects")
                url = resp.headers['Location']
                resp = await client.request(
                    method, url, headers={"User-Agent": request.headers["User-Agent"]}
                )
                redirect_count += 1
                if resp.status_code < 200 or resp.status_code >= 400:
                    raise HTTPException(status_code=resp.status_code, detail=resp.text)
        original_headers = resp.headers
        if "subscription-userinfo" in original_headers:
            headers["subscription-userinfo"] = original_headers["subscription-userinfo"]
        if "Content-Disposition" in original_headers:
            headers["Content-Disposition"] = original_headers[
                "Content-Disposition"
            ].replace("attachment", "inline")
    return resp, headers

# mainpage
app.mount("/static", StaticFiles(directory="static"), name="static")
@app.get("/")
async def mainpage():
    return FileResponse("static/index.html")

# /robots.txt
@app.get("/robots.txt")
async def robots():
    if DISALLOW_ROBOTS:
        return Response(content="User-agent: *\nDisallow: /", media_type="text/plain")
    else:
        return Response(status_code=404)

# subscription to proxy-provider
@app.get("/provider")
async def provider(request: Request):
    url = request.query_params.get("url")
    resp, headers = await fetch_url(url, request, method="GET")
    result = await parse.parseSubs(resp.text)
    return Response(content=result, headers=headers)


# subscription to proxy-provider
@app.head("/provider")
async def provider_head(request: Request):
    url = request.query_params.get("url")
    _, headers = await fetch_url(url, request, method="HEAD")
    return Response(content=None, headers=headers)


# subscription converter api
@app.get("/sub")
async def sub(request: Request):
    args = request.query_params
    # get interval
    interval = args.get("interval", "1800")
    short = args.get("short")

    # get proxyrule
    notproxyrule = args.get("npr")


    # get the url of original subscription
    url = args.get("url")
    url = re.split(r"[|\n]", url)
    # remove empty lines
    tmp = list(filter(lambda x: x!="", url)) 
    url = []
    urlstandalone = []
    for i in tmp:
        if (i.startswith("http://") or i.startswith("https://")) and not i.startswith("https://t.me/"):
                url.append(i)
        else:
            urlstandalone.append(i)
    urlstandalone = "\n".join(urlstandalone)
    if len(url) == 0:
        url = None
    if len(urlstandalone) == 0:
        urlstandalone = None

    urlstandby = args.get("urlstandby")
    urlstandbystandalone = None
    if urlstandby:
        urlstandby = re.split(r"[|\n]", urlstandby)
        tmp = list(filter(lambda x: x!="", urlstandby))
        urlstandby = []
        urlstandbystandalone = []
        for i in tmp:
            if (i.startswith("http://") or i.startswith("https://")) and not i.startswith("https://t.me/"):
                urlstandby.append(i)
            else:
                urlstandbystandalone.append(i)
        urlstandbystandalone = "\n".join(urlstandbystandalone)
        if len(urlstandby) == 0:
            urlstandby = None
        if len(urlstandbystandalone) == 0:
            urlstandbystandalone = None

    if urlstandalone:
        urlstandalone = await converter.ConvertsV2Ray(urlstandalone)
    if urlstandbystandalone:
        urlstandbystandalone = await converter.ConvertsV2Ray(urlstandbystandalone)

    if url is not None and len(url) == 1:
        resp, headers = await fetch_url(url[0], request, method="HEAD")

    content = []  # the proxies of original subscriptions
    if url is not None:
        for i in range(len(url)):
            resp, _ = await fetch_url(url[i], request, method="GET")
            content.append(await parse.parseSubs(resp.text))
            url[i] = "{}provider?{}".format(request.base_url, urlencode({"url": url[i]}))
    if len(content) == 0:
        content = None
    if urlstandby:
        for i in range(len(urlstandby)):
            urlstandby[i] = "{}provider?{}".format(request.base_url, urlencode({"url": urlstandby[i]}))

    # get the domain or ip of this api to add rule for this
    domain = re.search(r"([^:]+)(:\d{1,5})?", request.url.hostname).group(1)
    # generate the subscription
    result = await pack.pack(url=url, urlstandalone=urlstandalone, urlstandby=urlstandby,urlstandbystandalone=urlstandbystandalone, content=content, interval=interval, domain=domain, short=short, notproxyrule=notproxyrule, base_url=request.base_url)
    return Response(content=result, headers=headers)

@app.head("/sub")
async def get_remote_headers(request: Request):
    args = request.query_params
    url = args.get("url")
    if url:
        url = re.split(r"[|\n]", url)
        tmp = list(filter(lambda x: x != "", url))
        url = [i for i in tmp if i.startswith("http://") or i.startswith("https://")]
    if not url:
        raise HTTPException(
            status_code=400, detail="URL is required and should be valid"
        )
    if len(url) == 1:
        _, headers = await fetch_url(url[0], request, method="HEAD")
    return Response(content=None, headers=headers)


# proxy
@app.get("/proxy")
async def proxy(request: Request, url: str):
    parsed_url = urlparse(url)
    if parsed_url.netloc != "raw.githubusercontent.com":
        return PlainTextResponse("Forbidden", status_code=403)
    # file was big so use stream
    async def stream():
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", url, headers={'User-Agent':request.headers['User-Agent']}) as resp:
                yield resp.status_code
                yield resp.headers
                if resp.status_code < 200 or resp.status_code >= 400:
                    yield await resp.aread()
                    return
                async for chunk in resp.aiter_bytes():
                    yield chunk
    streamResp = stream()
    status_code = await streamResp.__anext__()
    headers = await streamResp.__anext__()
    if status_code < 200 or status_code >= 400:
        raise HTTPException(status_code=status_code, detail=await streamResp.__anext__())
    return StreamingResponse(streamResp, media_type=headers['Content-Type'])

# static files
@app.get("/{path:path}")
async def index(path):
    if Path("static/"+path).exists():
        return FileResponse("static/"+path)
    else:
        raise HTTPException(status_code=404, detail="Not Found")
