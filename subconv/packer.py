import re
import random
from dataclasses import dataclass
from typing import Any

import yaml
from urllib.parse import urlparse, urlencode

from . import config
from . import subscription


ProxyMapping = dict[str, Any]


@dataclass(frozen=True)
class RemoteSubscription:
    url: str
    force_direct: bool = False


async def pack(
    url: list[RemoteSubscription] | None,
    urlstandalone: list[ProxyMapping] | None,
    urlstandby: list[str] | None,
    urlstandbystandalone: list[ProxyMapping] | None,
    content: list[str] | None,
    interval: str,
    domain: str,
    short: str | None,
    notproxyrule: str | None,
    base_url: str,
    template_name: str,
    template_config: config.TemplateConfig,
) -> str:
    providerProxyNames = await subscription.mkListProxyNames(content)
    result: ProxyMapping = {}

    if short is None:
        result.update(template_config.HEAD)

    proxies: ProxyMapping | None = {"proxies": []}
    proxies_list: list[ProxyMapping] = proxies["proxies"]
    proxiesName: list[str] | None = []
    proxiesStandbyName: list[str] | None = []

    if urlstandalone or urlstandbystandalone:
        if urlstandalone:
            for i in urlstandalone:
                proxies_list.append(i)
                proxiesName.append(i["name"])
                proxiesStandbyName.append(i["name"])
        if urlstandbystandalone:
            for i in urlstandbystandalone:
                proxies_list.append(i)
                proxiesStandbyName.append(i["name"])
    if len(proxies_list) == 0:
        proxies = None
    if len(proxiesName) == 0:
        proxiesName = None
    if len(proxiesStandbyName) == 0:
        proxiesStandbyName = None
    if proxies:
        result.update(proxies)

    providers: ProxyMapping | None = {"proxy-providers": {}}
    provider_map: dict[str, ProxyMapping] = providers["proxy-providers"]
    if url or urlstandby:
        if url:
            for u, source in enumerate(url):
                provider: ProxyMapping = {
                    "type": "http",
                    "url": source.url,
                    "interval": int(interval),
                    "path": "./sub/subscription{}.yaml".format(u),
                    "health-check": {
                        "enable": True,
                        "interval": 60,
                        "url": template_config.TEST_URL,
                    },
                }
                if source.force_direct:
                    provider["proxy"] = "DIRECT"
                provider_map.update({"subscription{}".format(u): provider})
        if urlstandby:
            for u in range(len(urlstandby)):
                provider_map.update(
                    {
                        "subscription{}".format("sub" + str(u)): {
                            "type": "http",
                            "url": urlstandby[u],
                            "interval": int(interval),
                            "path": "./sub/subscription{}.yaml".format("sub" + str(u)),
                            "health-check": {
                                "enable": True,
                                "interval": 60,
                                "url": template_config.TEST_URL,
                            },
                        }
                    }
                )
    if len(provider_map) == 0:
        providers = None
    if providers:
        result.update(providers)

    proxyGroups: dict[str, list[ProxyMapping]] = {"proxy-groups": []}
    proxy_groups_list = proxyGroups["proxy-groups"]

    proxy_select_proxies: list[str] = []
    proxySelect: ProxyMapping = {
        "name": "🚀 节点选择",
        "type": "select",
        "proxies": proxy_select_proxies,
    }
    for group in template_config.CUSTOM_PROXY_GROUP:
        if group.rule == False:
            proxy_select_proxies.append(group.name)
    proxy_select_proxies.append("DIRECT")

    if len(template_config.CUSTOM_PROXY_GROUP) > 0:
        proxy_groups_list.append(proxySelect)

    subscriptions: list[str] | None = []
    if url:
        for u in range(len(url)):
            subscriptions.append("subscription{}".format(u))
    standby: list[str] | None = subscriptions.copy()
    if urlstandby:
        for u in range(len(urlstandby)):
            standby.append("subscriptionsub{}".format(u))
    if len(subscriptions) == 0:
        subscriptions = None
    if len(standby) == 0:
        standby = None

    for group in template_config.CUSTOM_PROXY_GROUP:
        type_ = group.type
        regex = group.regex

        rule = group.rule

        if type_ == "select" and rule:
            prior = group.prior
            if prior == "DIRECT":
                proxy_groups_list.append(
                    {
                        "name": group.name,
                        "type": "select",
                        "proxies": [
                            "DIRECT",
                            "REJECT",
                            "🚀 节点选择",
                            *[
                                _group.name
                                for _group in template_config.CUSTOM_PROXY_GROUP
                                if _group.rule == False
                            ],
                        ],
                    }
                )
            elif prior == "REJECT":
                proxy_groups_list.append(
                    {
                        "name": group.name,
                        "type": "select",
                        "proxies": [
                            "REJECT",
                            "DIRECT",
                            "🚀 节点选择",
                            *[
                                _group.name
                                for _group in template_config.CUSTOM_PROXY_GROUP
                                if _group.rule == False
                            ],
                        ],
                    }
                )
            else:
                proxy_groups_list.append(
                    {
                        "name": group.name,
                        "type": "select",
                        "proxies": [
                            "🚀 节点选择",
                            *[
                                _group.name
                                for _group in template_config.CUSTOM_PROXY_GROUP
                                if _group.rule == False
                            ],
                            "DIRECT",
                            "REJECT",
                        ],
                    }
                )

        elif (
            type_ == "load-balance"
            or type_ == "select"
            or type_ == "fallback"
            or type_ == "url-test"
        ):
            proxyGroup: ProxyMapping | None = {"name": group.name, "type": type_}
            if regex is not None:
                tmp = [regex]
                if len(tmp) > 0:
                    providerProxies: list[str] = []
                    proxyGroupProxies: list[str] = []
                    proxyGroup["filter"] = "|".join(tmp)
                    if group.manual:
                        if standby:
                            for p in standby:
                                if re.search(proxyGroup["filter"], p, re.I) is not None:
                                    providerProxies.append(p)
                                    break
                            if len(providerProxies) > 0:
                                proxyGroup["use"] = standby
                        if proxiesStandbyName:
                            for p in proxiesStandbyName:
                                if re.search(proxyGroup["filter"], p, re.I) is not None:
                                    proxyGroupProxies.append(p)
                            if len(proxyGroupProxies) > 0:
                                proxyGroup["proxies"] = proxyGroupProxies
                    else:
                        if subscriptions:
                            for p in providerProxyNames:
                                if re.search(proxyGroup["filter"], p, re.I) is not None:
                                    providerProxies.append(p)
                                    break
                            if len(providerProxies) > 0:
                                proxyGroup["use"] = subscriptions
                        if proxiesName:
                            for p in proxiesName:
                                if re.search(proxyGroup["filter"], p, re.I) is not None:
                                    proxyGroupProxies.append(p)
                            if len(proxyGroupProxies) > 0:
                                proxyGroup["proxies"] = proxyGroupProxies
                    if len(providerProxies) + len(proxyGroupProxies) == 0:
                        _remove_group_proxy(proxy_groups_list[0], group.name)
                        proxyGroup = None
                else:
                    _remove_group_proxy(proxy_groups_list[0], group.name)
                    proxyGroup = None
                if proxyGroup is not None:
                    if type_ == "load-balance":
                        proxyGroup["strategy"] = "consistent-hashing"
                        proxyGroup["url"] = template_config.TEST_URL
                        proxyGroup["interval"] = 60
                        proxyGroup["tolerance"] = 50
                    elif type_ == "fallback":
                        proxyGroup["url"] = template_config.TEST_URL
                        proxyGroup["interval"] = 60
                        proxyGroup["tolerance"] = 50
                    elif type_ == "url-test":
                        proxyGroup["url"] = template_config.TEST_URL
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
                proxy_groups_list.append(proxyGroup)

    proxyGroupAndProxyList = ["DIRECT", "REJECT"]
    proxyGroupAndProxyList.extend(str(i["name"]) for i in proxy_groups_list)
    if proxiesStandbyName is not None:
        proxyGroupAndProxyList.extend(proxiesStandbyName)
    for proxygroup in proxy_groups_list:
        if "proxies" not in proxygroup:
            continue
        proxygroup["proxies"] = [
            proxy
            for proxy in _group_proxies(proxygroup)
            if isinstance(proxy, str) and proxy in proxyGroupAndProxyList
        ]

    result.update(proxyGroups)

    rule_providers: dict[str, dict[str, ProxyMapping]] = {"rule-providers": {}}
    rule_provider_map = rule_providers["rule-providers"]
    rule_entries: list[tuple[str, str]] = []
    rule_provider_names: set[str] = set()
    classical: ProxyMapping = {
        "type": "http",
        "behavior": "classical",
        "format": "text",
        "interval": 86400 * 7,
    }
    for item in template_config.RULESET:
        rule_url = item[1]
        if rule_url.startswith("[]"):
            rule_entries.append((rule_url, item[0]))
            continue

        name = urlparse(rule_url).path.split("/")[-1].split(".")[0]
        while name in rule_provider_names:
            name += str(random.randint(0, 9))
        rule_provider_names.add(name)
        rule_entries.append((name, item[0]))
        if notproxyrule is None:
            query_params = {"url": rule_url}
            if template_name != config.default_template_name():
                query_params["template"] = template_name
            rule_url = "{}proxy?{}".format(base_url, urlencode(query_params))

        rule_provider_map.update(
            {name: {**classical, "path": "./rule/{}.txt".format(name), "url": rule_url}}
        )
    result.update(rule_providers)

    rules: dict[str, list[str]] = {"rules": []}
    rules_list = rules["rules"]
    rules_list.append(f"DOMAIN,{domain},DIRECT")
    for k, v in rule_entries:
        if not k.startswith("[]"):
            rules_list.append(f"RULE-SET,{k},{v}")
        elif k[2:] != "FINAL" and k[2:] != "MATCH":
            rules_list.append(f"{k[2:]},{v}")
        else:
            rules_list.append(f"MATCH,{v}")

    result.update(rules)

    yaml.SafeDumper.ignore_aliases = lambda self, data: True

    return yaml.safe_dump(result, allow_unicode=True, sort_keys=False)


def _group_proxies(group: ProxyMapping) -> list[str]:
    proxies = group.get("proxies")
    if isinstance(proxies, list):
        return proxies
    return []


def _remove_group_proxy(group: ProxyMapping, name: str) -> None:
    proxies = _group_proxies(group)
    if name in proxies:
        proxies.remove(name)
