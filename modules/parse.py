"""
This module is to get the list of regions available in orginal subscription
"""


import re
import yaml
from config import region_dict
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
async def mkList(content: list, urlstandalone: list):
    result = []
    total = {}
    providerProxyNames = []
    if content:
        for u in content:
            tmp = {}
            # preprocess the content
            contentTmp = re.findall(r"- name: (.+)", u)
            providerProxyNames.extend(contentTmp)
            contentTmp = ",".join(contentTmp)

            for i in region_dict:
                if re.search(region_dict[i][0], contentTmp, re.I) is not None:
                    tmp[i] = region_dict[i]
                    total[i] = region_dict[i]
            result.append(tmp)
    if urlstandalone:
        for u in urlstandalone:
            tmp = {}
            for i in region_dict:
                if re.search(
                    region_dict[i][0],
                    u["name"],
                    re.I
                ) is not None:
                    tmp[i] = region_dict[i]
                    total[i] = region_dict[i]
            result.append(tmp)
    return result, total, providerProxyNames