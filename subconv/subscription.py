import asyncio
import re

import yaml

from .converter import ConvertsV2Ray
from .converter.registry import NameRegistry
from .converter.util import ParseError, ProxyBudget
from .yaml_utils import dump_yaml, load_yaml


async def parseSubs(content: str) -> str:
    return await asyncio.to_thread(dump_proxies, await parse_nodes(content))


def dump_proxies(proxies: list[dict]) -> str:
    return dump_yaml({'proxies': proxies})


async def parse_nodes(content: str) -> list[dict]:
    # Raw links can contain characters that YAML treats as syntax. Base64
    # subscriptions remain YAML scalars and are decoded by the converter below.
    lines = (line.strip() for line in content.splitlines())
    first_line = next((line for line in lines if line and not line.startswith('#')), '')
    if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', first_line):
        loaded = None
    else:
        try:
            loaded = load_yaml(content)
        except yaml.YAMLError as exc:
            raise ParseError('Invalid subscription YAML or structure limit exceeded') from exc
        if loaded is not None and not isinstance(loaded, (dict, str)):
            raise ParseError('Expected Clash YAML or share links')
        if isinstance(loaded, dict) and 'proxies' not in loaded:
            raise ParseError('Subscription YAML is missing proxies')

    if isinstance(loaded, dict) and 'proxies' in loaded:
        nodes = loaded['proxies']
        if not isinstance(nodes, list) or not nodes:
            raise ParseError('Subscription proxies must be a non-empty list')
        registry = NameRegistry()
        budget = ProxyBudget()
        budget.check_count(len(nodes))
        proxies = []
        for index, node in enumerate(nodes, 1):
            if not isinstance(node, dict) or not isinstance(node.get('name'), str):
                raise ParseError(f'Proxy {index}: expected a mapping with a string name')
            proxy = {**node, 'name': registry.register(node['name'])}
            budget.add(proxy)
            proxies.append(proxy)
    else:
        proxies = await ConvertsV2Ray(content)
    return proxies
