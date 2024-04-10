"""
This module is to general a complete config for Clash
"""


from modules import parse
import re
from . import config
import yaml
import random

from urllib.parse import urlparse, urlencode

async def pack(url: list, urlstandalone: list, urlstandby:list, urlstandbystandalone: list, content: str, interval: str, domain: str, short: str, notproxyrule: str, base_url: str):
    providerProxyNames = await parse.mkListProxyNames(content)
    result = {}

    if short is None:
        # head of config
        result.update(config.configInstance.HEAD)

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
                            "url": config.configInstance.TEST_URL
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
                             "url": config.configInstance.TEST_URL
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
    for group in config.configInstance.CUSTOM_PROXY_GROUP:
        if group.rule == False:
            proxySelect["proxies"].append(group.name)
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
    for group in config.configInstance.CUSTOM_PROXY_GROUP:
        type = group.type
        regex = group.regex

        rule = group.rule

        if type == "select" and rule:
            prior = group.prior
            if prior == "DIRECT":
                proxyGroups["proxy-groups"].append({
                    "name": group.name,
                    "type": "select",
                    "proxies": [
                        "DIRECT",
                        "REJECT",
                        "🚀 节点选择",
                        *[_group.name for _group in config.configInstance.CUSTOM_PROXY_GROUP if _group.rule == False]
                    ]
                })
            elif prior == "REJECT":
                proxyGroups["proxy-groups"].append({
                    "name": group.name,
                    "type": "select",
                    "proxies": [
                        "REJECT",
                        "DIRECT",
                        "🚀 节点选择",
                        *[_group.name for _group in config.configInstance.CUSTOM_PROXY_GROUP if _group.rule == False]
                    ]
                })
            else:
                proxyGroups["proxy-groups"].append({
                    "name": group.name,
                    "type": "select",
                    "proxies": [
                        "🚀 节点选择",
                        *[_group.name for _group in config.configInstance.CUSTOM_PROXY_GROUP if _group.rule == False],
                        "DIRECT",
                        "REJECT"
                    ]
                })

        elif type == "load-balance" or type == "select" or type == "fallback" or type == "url-test":
            # init
            proxyGroup = {
                "name": group.name,
                "type": type
            }
            # add proxies
            if regex is not None:
                tmp = [regex]
                if len(tmp) > 0:
                    providerProxies = []
                    proxyGroupProxies = []
                    proxyGroup["filter"] = "|".join(tmp)
                    # check if the proxy is in the subscription match the regex
                    # check if the standalone proxy match the regex
                    if group.manual:
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
                        proxyGroups["proxy-groups"][0]["proxies"].remove(group.name)
                        proxyGroup = None
                else:
                    proxyGroups["proxy-groups"][0]["proxies"].remove(group.name)
                    proxyGroup = None
                if proxyGroup is not None:
                    if type == "load-balance":
                        proxyGroup["strategy"] = "consistent-hashing"
                        proxyGroup["url"] = config.configInstance.TEST_URL
                        proxyGroup["interval"] = 60
                        proxyGroup["tolerance"] = 50
                    elif type == "fallback":
                        proxyGroup["url"] = config.configInstance.TEST_URL
                        proxyGroup["interval"] = 60
                        proxyGroup["tolerance"] = 50
                    elif type == "url-test":
                        proxyGroup["url"] = config.configInstance.TEST_URL
                        proxyGroup["interval"] = 60
                        proxyGroup["tolerance"] = 50
            else:
                if group.manual:
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

    # remove proxies that do not exist in any proxy group
    proxyGroupAndProxyList = (["DIRECT", "REJECT"])
    proxyGroupAndProxyList.extend([i["name"] for i in proxyGroups["proxy-groups"]])
    if proxiesStandbyName is not None:
        proxyGroupAndProxyList.extend(proxiesStandbyName)
    for proxygroup in proxyGroups["proxy-groups"]:
        if "proxies" not in proxygroup:
            continue
        proxygroup["proxies"] = [proxy for proxy in proxygroup["proxies"] if proxy in proxyGroupAndProxyList]

    result.update(proxyGroups)

    # rules
    # rule-providers
    rule_providers = {
        "rule-providers": {}
    }
    rule_map = {}
    classical = {
        "type": "http",
        "behavior": "classical",
        "format": "text",
        "interval": 86400 * 7,
    }
    for item in config.configInstance.RULESET:
        url = item[1]
        # use filename
        name = urlparse(url).path.split("/")[-1].split(".")[0]
        # unique name
        while name in rule_map:
            name += str(random.randint(0, 9))
        rule_map[name] = item[0]
        if url.startswith("[]"):
            continue
        if notproxyrule is None:
            url = "{}proxy?{}".format(base_url, urlencode({"url": url}))

        rule_providers["rule-providers"].update({
            name: {
                **classical,
                "path": "./rule/{}.txt".format(name),
                "url": url
            }
        })
    result.update(rule_providers)

    # add rule
    rules = {
        "rules": []
    }
    rules["rules"].append(
        f"DOMAIN,{domain},DIRECT"
    )
    for k, v in rule_map.items():
        if not k.startswith("[]"):
            rules["rules"].append(
                f"RULE-SET,{k},{v}"
            )
        elif k[2:] != "FINAL" and k[2:] != "MATCH":
            rules["rules"].append(
                f"{k[2:]},{v}"
            )
        else:
            rules["rules"].append(
                f"MATCH,{v}"
            )

    result.update(rules)

    yaml.SafeDumper.ignore_aliases = lambda *args : True
    
    return yaml.safe_dump(result, allow_unicode=True, sort_keys=False)
