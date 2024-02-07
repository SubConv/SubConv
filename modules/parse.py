"""
This module is to get the list of regions available in orginal subscription
"""


import re
import yaml
import modules.convert.converter as converter


# regions and the regular expression to match them

# parse yaml
async def parseSubs(content):
    try:
        proxies =  yaml.safe_dump(
            {"proxies": yaml.load(content, Loader=yaml.FullLoader).get("proxies")},
            allow_unicode=True,  # display characters like Chinese
            sort_keys=False  # keep the original sequence
        )
    except:
        proxies = yaml.safe_dump(
            {"proxies": await converter.ConvertsV2Ray(content)},
            allow_unicode=True,  # display characters like Chinese
            sort_keys=False  # keep the original sequence
        )
    return proxies

# create a dict containg resions and corresponding proxy group
async def mkListProxyNames(content: list):
    providerProxyNames = []
    if content:
        for u in content:
            # preprocess the content
            contentTmp = re.findall(r"- name: (.+)", u)
            providerProxyNames.extend(contentTmp)
    return providerProxyNames