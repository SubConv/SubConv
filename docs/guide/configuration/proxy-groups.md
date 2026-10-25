# Proxy Groups
Except for the `🚀 节点选择` group, all proxy-groups can be customized through the YAML files under `template/`. Proxy-groups are generated based on `CUSTOM_PROXY_GROUP` in the selected template file.  

Group filters are checked when templates load. They use the shared Python/regexp2 syntax subset: literals, character classes, quantifiers, alternation, lookarounds and `i/m/s/x` flags. Named groups may use `(?<region>HK)` or `(?P<region>HK)`; output uses mihomo's form. Named references are normalized as well. Numeric references, conditional groups, possessive quantifiers, nested/subtracted classes and Python-only flags or `\N`/`\U` escapes are rejected at startup. Quantifiers require an explicit minimum and counts no greater than 2,147,483,647. Group names must be ASCII identifiers.

Separate filters with a backtick, for example ``HK`JP``. Each filter is case-insensitive by default and applies in the listed order. SubConv filters direct share-link nodes on the server using Python matching semantics, including Unicode; only matching nodes are written to the group's explicit `proxies`. `manual: false` considers primary nodes, while `manual: true` also includes standby nodes. Groups with neither providers nor matching nodes are omitted.

Remote providers use the normalized `filter` in mihomo's regexp2 engine. Because Unicode tables and case folding can differ, SubConv conservatively retains uncertain remote providers for client filtering. This can retain an empty remote group; it never adds unmatched direct nodes.

## customize proxy-groups
Here is an example of `custom_proxy_group` (from `template/general.yaml`):
```yaml
CUSTOM_PROXY_GROUP:
- name: ♻️ 自动选择
  type: url-test
  rule: false
- name: 🚀 手动切换1
  type: select
  manual: true
  rule: false
- name: 🚀 手动切换2
  type: select
  manual: true
  rule: false
- name: 🔯 故障转移
  type: fallback
  rule: false
- name: 🔮 负载均衡
  type: load-balance
  rule: false
- name: 📲 电报消息
  type: select
  prior: PROXY
- name: 💬 Ai平台
  type: select
  prior: PROXY
- name: 📹 油管视频
  type: select
  prior: PROXY
- name: 🎥 奈飞视频
  type: select
  prior: PROXY
- name: 📺 巴哈姆特
  type: select
  prior: PROXY
- name: 📺 哔哩哔哩
  type: select
  prior: DIRECT
- name: 🌍 国外媒体
  type: select
  prior: PROXY
- name: 🌏 国内媒体
  type: select
  prior: DIRECT
- name: 📢 谷歌FCM
  type: select
  prior: DIRECT
- name: 📢 谷歌服务
  type: select
  prior: PROXY
- name: Ⓜ️ 微软Bing
  type: select
  prior: PROXY
- name: Ⓜ️ 微软云盘
  type: select
  prior: DIRECT
- name: Ⓜ️ 微软服务
  type: select
  prior: DIRECT
- name: 🍎 苹果服务
  type: select
  prior: DIRECT
- name: 🎮 游戏平台
  type: select
  prior: DIRECT
- name: 🎶 网易音乐
  type: select
  prior: DIRECT
- name: 🎶 Spotify
  type: select
  prior: DIRECT
- name: 🎯 全球直连
  type: select
  prior: DIRECT
- name: 🛑 广告拦截
  type: select
  prior: REJECT
- name: 🍃 应用净化
  type: select
  prior: REJECT
- name: 🛡️ 隐私防护
  type: select
  prior: REJECT
- name: 🐟 漏网之鱼
  type: select
  prior: PROXY
- name: 🇭🇰 香港节点
  type: url-test
  rule: false
  regex: (?i:\b(?:HK|HKG)\d*\b|Hong.*?Kong|\bHKT\b|\bHKBN\b|\bHGC\b|\bWTT\b|\bCMI\b|[^-]港)
- name: 🇨🇳 台湾节点
  type: url-test
  rule: false
  regex: (?i:\b(?:TW|TWN)\d*\b|Taiwan|新北|彰化|\bCHT\b|台湾|[^-]台|\bHINET\b)
- name: 🇸🇬 狮城节点
  type: url-test
  rule: false
  regex: (?i:\b(?:SG|SGP)\d*\b|Singapore|新加坡|狮城|[^-]新)
- name: 🇯🇵 日本节点
  type: url-test
  rule: false
  regex: (?i:\b(?:JP|JPN)\d*\b|Japan|Tokyo|Osaka|Saitama|日本|东京|大阪|埼玉|[^-]日)
- name: 🇰🇷 韩国节点
  type: url-test
  rule: false
  regex: (?i:(?<!North\s)(\b(?:KR|KOR)\d*\b|Korea|首尔|韩|韓))
- name: 🇬🇧 英国节点
  type: url-test
  rule: false
  regex: (?i:\b(?:UK|GB|GBR)\d*\b|United.*?Kingdom|Britain|London|Manchester|Birmingham|英国|[^-]英)
- name: 🇺🇸 美国节点
  type: url-test
  rule: false
  regex: (?i:\b(?:US|USA)\d*\b|America|United.*?States|美国|[^-]美|波特兰|达拉斯|俄勒冈|凤凰城|费利蒙|硅谷|拉斯维加斯|洛杉矶|圣何塞|圣克拉拉|西雅图|芝加哥)
```
1. `custom_proxy_group` is a list, where each element is a dictionary representing a proxy-group.  
   The basic structure of each dictionary is as follows:
    ```yaml
    name: <name of the proxy-group>
    type: <type of the proxy-group>
    # other fields
    ```
   Here are other possible fields:
   - `"rule"`: whether this is a rule group (a rule group is a group used for routing, such as `📲 电报消息`, rather than `♻️ 自动选择` which is used for node selection. **Default value is `true`**  
   - `"prior"`: **Only applies when `"rule"` is `true` and `"type"` is `select`**. Choices are `"DIRECT"`, `"PROXY"`, and `"REJECT"`, with `"PROXY"` as the default. It selects the first choice in the group; `"PROXY"` means `"🚀 节点选择"`.
   - `"regex"`: **works only if `"rule"` is `false`**. A regular expression used to match the node name. If a match is found, the node will be added to this proxy-group. If this field is not specified, all nodes will be added to this proxy-group.  
    - `"manual"`: **works only if `"rule"` is `false`**. Possible values are `true` or `false`. If `true`, this proxy-group will contain standby nodes. If `false`, this proxy-group will not contain backup nodes. **Default value is `false`**.  
