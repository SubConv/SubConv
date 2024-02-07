#!/usr/bin/env python3
# coding=utf-8
from modules import pack
from modules import parse
from modules.convert import converter

from fastapi import FastAPI, HTTPException
from fastapi.requests import Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

import httpx

from urllib.parse import urlencode, unquote
import argparse
from pathlib import Path
import re


def length(sth):
    if sth is None:
        return 0
    else:
        return len(sth)


app = FastAPI()


# mainpage
app.mount("/static", StaticFiles(directory="static"), name="static")
@app.get("/")
async def mainpage():
    return FileResponse("static/index.html")


# subscription to proxy-provider
@app.get("/provider")
async def provider(request: Request):
    headers = {'Content-Type': 'text/yaml;charset=utf-8'}
    url = request.query_params.get("url")
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers={'User-Agent':'clash'})
        if resp.status_code < 200 or resp.status_code >= 300:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        result = await parse.parseSubs(resp.text)
    return Response(content=result, headers=headers)

    
# subscription converter api
@app.get("/sub")
async def sub(request: Request):
    args = request.query_params
    # get interval
    if "interval" in args:
        interval = args["interval"]
    else:
        interval = "1800"

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

    async with httpx.AsyncClient() as client:
        # get original headers
        headers = {'Content-Type': 'text/yaml;charset=utf-8'}
        # if there's only one subscription, return userinfo
        if length(url) == 1:
            resp = await client.head(url[0], headers={'User-Agent':'clash'})
            if resp.status_code < 200 or resp.status_code >= 300:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            originalHeaders = resp.headers
            if 'subscription-userinfo' in originalHeaders:  # containing info about ramaining flow
                headers['subscription-userinfo'] = originalHeaders['subscription-userinfo']
            if 'Content-Disposition' in originalHeaders:  # containing filename
                headers['Content-Disposition'] = originalHeaders['Content-Disposition'].replace("attachment", "inline")

        content = []  # the proxies of original subscriptions
        if url is not None:
            for i in range(len(url)):
                # the test of response
                respText = (await client.get(url[i], headers={'User-Agent':'clash'})).text
                content.append(await parse.parseSubs(respText))
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

# proxy
@app.get("/proxy")
async def proxy(url: str):
    # file was big so use stream
    async def stream():
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", url, headers={'User-Agent':'clash'}) as resp:
                yield resp.status_code
                yield resp.headers
                if resp.status_code < 200 or resp.status_code >= 300:
                    yield await resp.aread()
                    return
                async for chunk in resp.aiter_bytes():
                    yield chunk
    streamResp = stream()
    status_code = await streamResp.__anext__()
    headers = await streamResp.__anext__()
    if status_code < 200 or status_code >= 300:
        raise HTTPException(status_code=status_code, detail=await streamResp.__anext__())
    return StreamingResponse(streamResp, media_type=headers['Content-Type'])

# static files
@app.get("/{path:path}")
async def index(path):
    if Path("static/"+path).exists():
        return FileResponse("static/"+path)
    else:
        raise HTTPException(status_code=404, detail="Not Found")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", "-P", type=int, default=443, help="port of the api, default: 443")
    parser.add_argument("--host", "-H", type=str, default="0.0.0.0", help="host of the api, default: 0.0.0.0")
    args = parser.parse_args()
    print("host:", args.host)
    print("port:", args.port)
    # Debug
    # uvicorn.run("api:app", host=args.host, port=args.port, reload=True)
    # Production
    module_name = __name__.split(".")[0]
    uvicorn.run(module_name+":app", host=args.host, port=args.port, workers=4)
