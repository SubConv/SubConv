"""
This scrip is to make rules cache
"""


from modules import rule


head = """\"\"\"
This file is a cache of rules from modules/ruleList.
And it's automatically generalted by GitHub Action
\"\"\"

"""
with open("cache.py", "w", encoding="utf-8") as cache:
    cache.write(head)
    cache.write("cache=\"\"\"")
    cache.write(rule.getFullRule())
    cache.write("\"\"\"")
