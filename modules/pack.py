"""
This module is to general a complete config for Clash
"""


from modules import parse
from modules import head
import re
import config
import yaml
import cache


async def pack(url: list, urlstandalone: list, urlstandby:list, urlstandbystandalone: list, content: str, interval, domain, short):
    regionDict, total, providerProxyNames = await parse.mkList(content, urlstandalone)  # regions available and corresponding group name
    result = {}

    # create a snippet containing region groups
    regionGroups = []
    for i in total.values():
        regionGroups.append(i[1])
    

    if short is None:
        # head of config
        result.update(head.HEAD)

        # dns
        result.update(head.DNS)

    # proxies
    proxies = {
        "proxies": []
    }
    proxiesName = []
    proxiesStandbyName = []

    if urlstandalone or urlstandbystandalone:
        if urlstandalone:
            for i in urlstandalone:
                proxies["proxies"].append(
                    i
                )
                proxiesName.append(i["name"])
                proxiesStandbyName.append(i["name"])
        if urlstandbystandalone:
            for i in urlstandbystandalone:
                proxies["proxies"].append(
                    i
                )
                proxiesStandbyName.append(i["name"])
    if len(proxies["proxies"]) == 0:
        proxies = None
    if len(proxiesName) == 0:
        proxiesName = None
    if len(proxiesStandbyName) == 0:
        proxiesStandbyName = None
    if proxies:
        result.update(proxies)


    # proxy providers
    providers = {
        "proxy-providers": {}
    }
    if url or urlstandby:
        if url:
            for u in range(len(url)):
                providers["proxy-providers"].update({
                    "subscription{}".format(u): {
                        "type": "http",
                        "url": url[u],
                        "interval": int(interval),
                        "path": "./sub/subscription{}.yaml".format(u),
                        "health-check": {
                            "enable": True,
                            "interval": 60,
                            # "lazy": True,
                            "url": "https://www.apple.com/library/test/success.html"
                        }
                    }
                })
        if urlstandby:
            for u in range(len(urlstandby)):
                providers["proxy-providers"].update({
                    "subscription{}".format("sub"+str(u)): {
                        "type": "http",
                        "url": urlstandby[u],
                        "interval": int(interval),
                        "path": "./sub/subscription{}.yaml".format("sub"+str(u)),
                        "health-check": {
                            "enable": True,
                            "interval": 60,
                            # "lazy": True,
                            "url": "https://www.apple.com/library/test/success.html"
                        }
                    }
                })
    if len(providers["proxy-providers"]) == 0:
        providers = None
    if providers:
        result.update(providers)

    # result += head.PROXY_GROUP_HEAD
    proxyGroups = {
        "proxy-groups": []
    }
    
    # add proxy select
    proxySelect = {
        "name": "🚀 节点选择",
        "type": "select",
        "proxies": []
    }
    for group in config.custom_proxy_group:
        if group.get("rule") == False:
            proxySelect["proxies"].append(group["name"])
    proxySelect["proxies"].extend(regionGroups)
    proxySelect["proxies"].append("DIRECT")
    proxyGroups["proxy-groups"].append(proxySelect)

    

    # generate subscriptions and standby subscriptions list
    subscriptions = []
    if url:
        for u in range(len(url)):
            subscriptions.append("subscription{}".format(u))
    standby = subscriptions.copy()
    if urlstandby:
        for u in range(len(urlstandby)):
            standby.append("subscriptionsub{}".format(u))
    if len(subscriptions) == 0:
        subscriptions = None
    if len(standby) == 0:
        standby = None


    # add proxy groups
    for group in config.custom_proxy_group:
        type = group["type"]
        region = group.get("region")
        regex = group.get("regex")

        rule = group.get("rule")
        if rule is None:
            rule = True

        if type == "select" and rule:
            prior = group["prior"]
            if prior == "DIRECT":
                proxyGroups["proxy-groups"].append({
                    "name": group["name"],
                    "type": "select",
                    "proxies": [
                        "DIRECT",
                        "REJECT",
                        "🚀 节点选择",
                        *regionGroups,
                        *[_group["name"] for _group in config.custom_proxy_group if _group.get("rule") == False]
                    ]
                })
            elif prior == "REJECT":
                proxyGroups["proxy-groups"].append({
                    "name": group["name"],
                    "type": "select",
                    "proxies": [
                        "REJECT",
                        "DIRECT",
                        "🚀 节点选择",
                        *regionGroups,
                        *[_group["name"] for _group in config.custom_proxy_group if _group.get("rule") == False]
                    ]
                })
            else:
                proxyGroups["proxy-groups"].append({
                    "name": group["name"],
                    "type": "select",
                    "proxies": [
                        "🚀 节点选择",
                        *regionGroups,
                        *[_group["name"] for _group in config.custom_proxy_group if _group.get("rule") == False],
                        "DIRECT",
                        "REJECT"
                    ]
                })

        elif type == "load-balance" or type == "select" or type == "fallback" or type == "url-test":
            # init
            proxyGroup = {
                "name": group["name"],
                "type": type
            }
            # add proxies
            if regex is not None or region is not None:
                if regex is not None:
                    tmp = [regex]
                else:
                    tmp = []
                    for i in region:
                        if i in total:
                            tmp.append(total[i][0])
                if len(tmp) > 0:
                    providerProxies = []
                    proxyGroupProxies = []
                    proxyGroup["filter"] = "|".join(tmp)
                    # check if the proxy is in the subscription match the regex
                    # check if the standalone proxy match the regex
                    if group.get("manual"):
                        if standby:
                            for p in standby:
                                if re.search(
                                    proxyGroup["filter"],
                                    p,
                                    re.I
                                ) is not None:
                                    providerProxies.append(p)
                                    break
                            if len(providerProxies) > 0:
                                proxyGroup["use"] = standby
                        if proxiesStandbyName:
                            for p in proxiesStandbyName:
                                if re.search(
                                    proxyGroup["filter"],
                                    p,
                                    re.I
                                ) is not None:
                                    proxyGroupProxies.append(p)
                            if len(proxyGroupProxies) > 0:
                                proxyGroup["proxies"] = proxyGroupProxies
                    else:
                        if subscriptions:
                            for p in providerProxyNames:
                                if re.search(
                                    proxyGroup["filter"],
                                    p,
                                    re.I
                                ) is not None:
                                    providerProxies.append(p)
                                    break
                            if len(providerProxies) > 0:
                                proxyGroup["use"] = subscriptions
                        if proxiesName:
                            for p in proxiesName:
                                if re.search(
                                    proxyGroup["filter"],
                                    p,
                                    re.I
                                ) is not None:
                                    proxyGroupProxies.append(p)
                            if len(proxyGroupProxies) > 0:
                                proxyGroup["proxies"] = proxyGroupProxies
                    # if no proxy match the regex, remove the name in the first group
                    if len(providerProxies) + len(proxyGroupProxies) == 0:
                        proxyGroups["proxy-groups"][0]["proxies"].remove(group["name"])
                        proxyGroup = None
                else:
                    proxyGroups["proxy-groups"][0]["proxies"].remove(group["name"])
                    proxyGroup = None
                if proxyGroup is not None:
                    if type == "load-balance":
                        proxyGroup["strategy"] = "consistent-hashing"
                        proxyGroup["url"] = "https://www.apple.com/library/test/success.html"
                        proxyGroup["interval"] = 60
                        proxyGroup["tolerance"] = 50
                    elif type == "fallback":
                        proxyGroup["url"] = "https://www.apple.com/library/test/success.html"
                        proxyGroup["interval"] = 60
                        proxyGroup["tolerance"] = 50
                    elif type == "url-test":
                        proxyGroup["url"] = "https://www.apple.com/library/test/success.html"
                        proxyGroup["interval"] = 60
                        proxyGroup["tolerance"] = 50
            else:
                if group.get("manual"):
                    if standby:
                        proxyGroup["use"] = standby
                    if proxiesStandbyName:
                        proxyGroup["proxies"] = proxiesStandbyName
                else:
                    if subscriptions:
                        proxyGroup["use"] = subscriptions
                    if proxiesName:
                        proxyGroup["proxies"] = proxiesName
            if proxyGroup is not None:
                proxyGroups["proxy-groups"].append(proxyGroup)
        

    # add region groups
    for i in total:
        urlTest = {
            "name": total[i][1],
            "type": "url-test",
            "url": "https://www.apple.com/library/test/success.html",
            "interval": 60,
            "tolerance": 50,
            "filter": total[i][0]
        }
        if subscriptions:
            urlTest["use"] = subscriptions
        if proxiesName:
            urlTestProxies = []
            for p in proxiesName:
                if re.search(
                    total[i][0],
                    p,
                    re.I
                ) is not None:
                    urlTestProxies.append(p)
            if len(urlTestProxies) > 0:
                urlTest["proxies"] = urlTestProxies
            else:
                urlTestProxies = None
        proxyGroups["proxy-groups"].append(urlTest)

    result.update(proxyGroups)

    # rules
    yaml.SafeDumper.ignore_aliases = lambda *args : True
    result = yaml.safe_dump(result, allow_unicode=True, sort_keys=False)
    result += ("rules:\n  - DOMAIN,{},DIRECT\n".format(domain) + cache.cache)
    return result