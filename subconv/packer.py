import asyncio
from typing import Any

from urllib.parse import urlparse, urlencode

from . import config
from .converter.registry import NameRegistry
from .filters import ambiguous_unicode_names, compile_group_filter, filter_names
from .yaml_utils import dump_yaml


ProxyMapping = dict[str, Any]

# These mihomo rule types allow commas in their payload and have no options.
# Their policy must remain the final field (rules/common.ParseRulePayload).
_RULES_WITH_COMMA_PAYLOAD = {
    "NOT", "OR", "AND", "SUB-RULE", "DOMAIN-REGEX",
    "PROCESS-NAME-REGEX", "PROCESS-PATH-REGEX",
}


async def pack(
    url: list[str] | None,
    urlstandalone: list[ProxyMapping] | None,
    urlstandby: list[str] | None,
    urlstandbystandalone: list[ProxyMapping] | None,
    provider_names: list[str],
    interval: int,
    domain: str,
    short: str | None,
    notproxyrule: str | None,
    base_url: str,
    template_name: str,
    template_config: config.TemplateConfig,
) -> str:
    result: ProxyMapping = {}

    if short is None:
        result.update(template_config.HEAD)

    proxies: ProxyMapping | None = {"proxies": []}
    proxies_list: list[ProxyMapping] = proxies["proxies"]
    proxiesName: list[str] | None = []
    proxiesStandbyName: list[str] | None = []

    registry = NameRegistry()
    for reserved in {"DIRECT", "REJECT", "REJECT-DROP", "PASS", "PASS-RULE", "GLOBAL", "COMPATIBLE", "🚀 节点选择"} | {
        group.name for group in template_config.CUSTOM_PROXY_GROUP
    }:
        registry.register(reserved)

    def unique_nodes(nodes):
        for node in nodes or []:
            yield {**node, "name": registry.register(node["name"])}

    if urlstandalone or urlstandbystandalone:
        if urlstandalone:
            for i in unique_nodes(urlstandalone):
                proxies_list.append(i)
                proxiesName.append(i["name"])
                proxiesStandbyName.append(i["name"])
        if urlstandbystandalone:
            for i in unique_nodes(urlstandbystandalone):
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
            for u in range(len(url)):
                provider_map.update(
                    {
                        "subscription{}".format(u): {
                            "type": "http",
                            "url": url[u],
                            "interval": interval,
                            "path": "./sub/subscription{}.yaml".format(u),
                            "health-check": {
                                "enable": True,
                                "interval": 60,
                                "url": template_config.TEST_URL,
                            },
                        }
                    }
                )
        if urlstandby:
            for u in range(len(urlstandby)):
                provider_map.update(
                    {
                        "subscription{}".format("sub" + str(u)): {
                            "type": "http",
                            "url": urlstandby[u],
                            "interval": interval,
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
    uncertain_provider_names = ambiguous_unicode_names(provider_names)
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
            proxyGroup: ProxyMapping = {"name": group.name, "type": type_}
            provider_ids = standby if group.manual else subscriptions
            node_names = proxiesStandbyName if group.manual else proxiesName
            if regex is not None:
                patterns, client_filter = compile_group_filter(regex)
                # Explicit proxies are not filtered again by mihomo. Preserve
                # SubConv's server-side matching semantics for these nodes.
                node_names = filter_names(patterns, node_names or [])
                # Only remote providers defer uncertain Unicode matching to the
                # client's regexp2 engine, which actually filters provider use.
                if any(not pattern.pattern.isascii() or r'\u' in pattern.pattern or r'\x' in pattern.pattern for pattern in patterns):
                    provider_matches = bool(provider_names)
                else:
                    provider_matches = any(name in uncertain_provider_names or pattern.search(name) for pattern in patterns for name in provider_names)
                # Standby providers are loaded by the client; their names are unknown.
                if not provider_matches and not (group.manual and urlstandby):
                    provider_ids = None
                proxyGroup["filter"] = client_filter
            if not provider_ids and not node_names:
                _remove_group_proxy(proxy_groups_list[0], group.name)
                continue
            if provider_ids:
                proxyGroup["use"] = provider_ids
            if node_names:
                proxyGroup["proxies"] = node_names
            if type_ != "select":
                proxyGroup.update(url=template_config.TEST_URL, interval=60, tolerance=50)
                if type_ == "load-balance":
                    proxyGroup["strategy"] = "consistent-hashing"
            proxy_groups_list.append(proxyGroup)

    proxyGroupAndProxyList = ["DIRECT", "REJECT"]
    proxyGroupAndProxyList.extend(str(i["name"]) for i in proxy_groups_list)
    if proxiesStandbyName is not None:
        proxyGroupAndProxyList.extend(proxiesStandbyName)
    valid_proxy_names = set(proxyGroupAndProxyList)
    for proxygroup in proxy_groups_list:
        if "proxies" not in proxygroup:
            continue
        proxygroup["proxies"] = [
            proxy
            for proxy in _group_proxies(proxygroup)
            if isinstance(proxy, str) and proxy in valid_proxy_names
        ]

    result.update(proxyGroups)

    rule_providers: dict[str, dict[str, ProxyMapping]] = {"rule-providers": {}}
    rule_provider_map = rule_providers["rule-providers"]
    next_rule_suffix: dict[str, int] = {}
    rules_list = [f"DOMAIN,{domain},DIRECT"]
    classical: ProxyMapping = {
        "type": "http",
        "behavior": "classical",
        "format": "text",
        "interval": 86400 * 7,
    }
    for policy, rule_url in template_config.RULESET:
        if rule_url.startswith("[]"):
            inline_rule = rule_url[2:]
            if inline_rule in {"FINAL", "MATCH"}:
                inline_rule = "MATCH"
            parts = inline_rule.split(",")
            options = []
            if parts[0].strip().upper() not in _RULES_WITH_COMMA_PAYLOAD:
                while len(parts) > 2 and parts[-1].strip() in {"no-resolve", "src"}:
                    options.insert(0, parts.pop())
            rules_list.append(",".join([*parts, policy, *options]))
            continue
        base_name = urlparse(rule_url).path.rsplit("/", 1)[-1].split(".")[0] or "ruleset"
        suffix = next_rule_suffix.get(base_name, 0)
        name = f"{base_name}-{suffix}" if suffix else base_name
        while name in rule_provider_map:
            suffix += 1
            name = f"{base_name}-{suffix}"
        next_rule_suffix[base_name] = suffix + 1
        if notproxyrule is None:
            query_params = {"url": rule_url}
            if template_name != config.default_template_name():
                query_params["template"] = template_name
            rule_url = "{}proxy?{}".format(base_url, urlencode(query_params))
        rule_provider_map[name] = {
            **classical, "path": f"./rule/{name}.txt", "url": rule_url
        }
        rules_list.append(f"RULE-SET,{name},{policy}")
    result.update(rule_providers)
    result["rules"] = rules_list

    return await asyncio.to_thread(dump_yaml, result)


def _group_proxies(group: ProxyMapping) -> list[str]:
    proxies = group.get("proxies")
    if isinstance(proxies, list):
        return proxies
    return []


def _remove_group_proxy(group: ProxyMapping, name: str) -> None:
    proxies = _group_proxies(group)
    if name in proxies:
        proxies.remove(name)
