"""
This module get rules according to ruleList.py and composed them
"""


import config
import re
import requests


# pull rules from the url given
def getRule(sort, url):
    result = ""
    item = requests.get(url).text
    item = item.splitlines()
    i = 0
    while i < len(item):
        tem = item[i]
        if "" == tem\
                or tem.lstrip().startswith("#")\
                or tem.lstrip().startswith("USER-AGENT")\
                or tem.lstrip().startswith("URL-REGEX")\
                or tem.lstrip().startswith("PROCESS-NAME"):
            item.remove(tem)
            i -= 1
        else:
            tem2 = re.search("(.+,.+)(,.+)", tem)
            if tem2 is not None:
                item[i] = tem2.group(1) + "," + sort + tem2.group(2)
            else:
                item[i] += "," + sort
            result += "  - " + item[i] + "\n"
        i += 1
    print("Successfully cached", sort, url)
    return result


# pack all rules
def getFullRule():
    result = ""
    for i in config.ruleset:
        if i[1][:2] != "[]":
            result += getRule(i[0], i[1])
        else:
            if i[1][2:] != "FINAL" and i[1][2:] != "MATCH":
                result += "  - " + i[1][2:] + "," + i[0] +"\n"
            else:
                result += "  - MATCH," + i[0]
    return result
