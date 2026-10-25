# Proxy Groups
除了 `🚀 节点选择` 组为硬编码以外，其他 proxy-groups 都可以通过 `template/` 目录下的 YAML 模板文件进行自定义。proxy-groups 根据当前所选模板中的 `CUSTOM_PROXY_GROUP` 生成。

模板加载时会校验分组正则。支持 Python/regexp2 的公共语法子集：字面字符、字符类、量词、分支、前后向断言及 `i/m/s/x` 标志。命名组可写成 `(?<region>HK)` 或 `(?P<region>HK)`，输出统一为 mihomo 的形式；命名反引用也会规范化。数字反引用、条件组、占有量词、嵌套或相减字符类、Python 专有标志以及 `\N`/`\U` 转义会在启动时被拒绝。量词必须显式写出下界，计数不能超过 2,147,483,647；命名组名称须为 ASCII 标识符。

用反引号分隔多个 filter，例如 ``HK`JP``；每段默认忽略大小写，并按列出的顺序应用。直接分享节点由 SubConv 在服务端按 Python 的匹配语义筛选，Unicode 名称也必须匹配，才会写入分组的显式 `proxies`。`manual: false` 只考虑主节点，`manual: true` 同时考虑备用节点。没有 provider 且没有匹配节点的分组会被省略。

远程 provider 由 mihomo 的 regexp2 引擎执行规范化后的 `filter`。由于 Unicode 表和大小写折叠可能不同，SubConv 会保守保留不确定的远程 provider，交由客户端筛选。这可能保留一个最终为空的远程分组，但不会将不匹配的直接节点加入分组。

## 自定义 proxy-groups
下面是一个有效的 `CUSTOM_PROXY_GROUP` 的例子（来自 `template/general.yaml`）：  
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
1. `CUSTOM_PROXY_GROUP` 为一个列表，其中每个元素都是一个字典，代表一个 proxy-group。  
   每个字典的基本格式为：
    ```yaml
    name: <名称>
    type: <类型>
    # 其他字段
    ```
   其他字段包括：
    - `"rule"`: 表示这是否是一个规则组（规则组指的是类似 `📲 电报消息` 这样用于分流的组，而非 `♻️ 自动选择` 等用于选择节点的组。**默认值为`true`**  
    - `"prior"`: **仅当 `"rule"` 为 `true` 且 `"type"` 为 `select` 时有效**。可选值为 `"DIRECT"`、`"PROXY"`、`"REJECT"`，默认 `"PROXY"`。表示分组的默认选择，其中 `"PROXY"` 对应 `"🚀 节点选择"`。
    - `"regex"`: **仅当`"rule"`字段为`false`时有效**。一个正则表达式，用于匹配节点名称。如果匹配成功，则将节点加入到这个 proxy-group 中。如果不指定这个字段，则所有节点都会被加入到这个 proxy-group 中。  
    - `"manual"`: **仅当`"rule"`字段为`false`时有效**。可选值为`true`或`false`。当值为`true`时，这个 proxy-group 会包含备用节点。当值为`false`时，这个 proxy-group 不会包含备用节点。**默认值为`false`**。  
