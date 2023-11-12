import urllib.parse as urlparse
from modules.convert.util import uniqueName
from modules.convert.util import get, RandUserAgent


def handleVShareLink(names: dict, url: urlparse.ParseResult, scheme: str, proxy: dict):
    query = dict(urlparse.parse_qsl(url.query))
    proxy["name"] = uniqueName(names, urlparse.unquote(url.fragment))
    if url.hostname == "":
        raise
    if url.port == "":
        raise
    proxy["type"] = scheme
    proxy["server"] = url.hostname
    proxy["port"] = url.port
    proxy["uuid"] = url.username
    proxy["udp"] = True
    tls = get(query.get("security")).lower()
    if tls.endswith("tls") or tls == "reality":
        proxy["tls"] = True
        fingerprint = get(query.get("fp"))
        if fingerprint == "":
            proxy["client-fingerprint"] = "chrome"
        else:
            proxy["client-fingerprint"] = fingerprint
        alpn = get(query.get("alpn"))
        if alpn != "":
            proxy["alpn"] = alpn.split(",")
    sni = get(query.get("sni"))
    if sni != "":
        proxy["servername"] = sni
    realityPublicKey = get(query.get("pbk"))
    if realityPublicKey != "":
        proxy["reality-opts"] = {
            "public-key": realityPublicKey,
            "short-id": get(query.get("sid"))
        }
    
    switch = get(query.get("packetEncoding"))
    if switch == "none" or switch == "":
        pass
    elif switch == "packet":
        proxy["packet-addr"] = True
    else:
        proxy["xudp"] = True

    network = get(query.get("type")).lower()
    if network == "":
        network = "tcp"
    fakeType = get(query.get("headerType")).lower()
    if fakeType == "http":
        network = "http"
    elif network == "http":
        network = "h2"
    proxy["network"] = network
    if network == "tcp":
        if fakeType != "none" and fakeType != "":
            headers = {}
            httpOpts = {}
            httpOpts["path"] = "/"

            host = get(query.get("host"))
            if host != "":
                headers["Host"] = str(host)

            method = get(query.get("method"))
            if method != "":
                httpOpts["method"] = method

            path = get(query.get("path"))
            if path != "":
                httpOpts["path"] = str(path)
            
            httpOpts["headers"] = headers
            proxy["http-opts"] = httpOpts

    elif network == "http":
        headers = {}
        h2Opts = {}
        h2Opts["path"] = "/"
        path = get(query.get("path"))
        if path != "":
            h2Opts["path"] = str(path)
        host = get(query.get("host"))
        if host != "":
            h2Opts["host"] = str(host)
        h2Opts["headers"] = headers
        proxy["h2-opts"] = h2Opts
    
    elif network == "ws":
        headers = {}
        wsOpts = {}
        headers["User-Agent"] = RandUserAgent()
        headers["Host"] = get(query.get("host"))
        wsOpts["path"] = get(query.get("path"))
        wsOpts["headers"] = headers

        earlyData = get(query.get("ed"))
        if earlyData != "":
            try:
                med = int(earlyData)
            except:
                raise
            wsOpts["max-early-data"] = med
        earlyDataHeader = get(query.get("edh"))
        if earlyDataHeader != "":
            wsOpts["early-data-header-name"] = earlyDataHeader

        proxy["ws-opts"] = wsOpts

    elif network == "grpc":
        grpcOpts = {}
        grpcOpts["grpc-service-name"] = get(query.get("serviceName"))
        proxy["grpc-opts"] = grpcOpts