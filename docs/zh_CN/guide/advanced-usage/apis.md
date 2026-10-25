# APIs
下面是API的介绍：

Telegram SOCKS 分享链接（`tg://socks?...` 和 `https://t.me/socks?...`）会生成 mihomo 的 `socks5` 节点。不支持 MTProto 链接（`tg://proxy?...` 和 `https://t.me/proxy?...`），遇到时整份转换失败：直接输入返回 400，上游订阅返回 502。无法序列化的超大整数字段也会使上游订阅返回 502。

## GET /sub
这是用于子部分转换的API，它包含在Web界面生成的链接中。

它接受GET请求。以下是参数说明：

| 参数 | 描述 | 可选 | 默认值 | 备注 |
| --- | --- | --- | --- | --- |
| url | 原始订阅链接或节点分享链接。**需要进行URIComponent编码。** | 否 | - | 支持多个订阅链接。您可以使用换行符或"\|"分隔它们。`https://t.me/...` 链接会被视为独立分享链接（按 V2Ray 节点解析），而非远程订阅 URL。 |
| template | 用于渲染最终配置的模板 ID。 | 是 | zju | 当前内置值为 `zju` 和 `general`。不传时默认使用 `zju`。 |
| interval | 代理更新间隔。 | 是 | 1800 | 单位：秒，整数范围为 1–2147483647。 |
| urlstandby | 备用订阅链接或节点分享链接。其中的代理将仅添加到**手动切换组**(配置文件中`"manual"`为`True`的组)中，并不会归类到区域组中。**建议进行URIComponent编码。** | 是 | - | 支持多个订阅链接。您可以使用换行符或"|"分隔它们。 |
| short | 如果设置了此参数（无论取值为何），将不会生成包含 allow-lan 等内容的标头部分和 dns 部分。 | 是 | - | - |
| npr | 如果设置了此参数（无论取值为何），将不会代理 ruleset 的 URL | 是 | - | 默认情况下，会使用这个服务来代理 ruleset 的 URL，以保证能正常获取规则集。若设置了此参数，将不会代理 ruleset 的 URL。 |

## GET /provider
此API可将订阅转换为 proxy-provider 需要的配置。每当通过 proxy-provider 更新代理时，将调用此API。
它接受GET请求。以下是参数说明：

| 参数 | 描述 | 可选 | 默认值 | 备注 |
| --- | --- | --- | --- | --- |
| url | 原始订阅链接的URL。**需要进行URIComponent编码。** | 否 | - | 应为单个订阅链接。 |

## GET /config
此 API 返回 Web UI 所使用的运行时配置。它接受 GET 请求，不需要任何参数。

响应 JSON 字段：

| 字段 | 描述 |
| --- | --- |
| defaultTemplate | 当 `/sub` 或 `/proxy` 不带 `template` 查询参数时使用的模板名称（来自 `config.yaml` 中的 `DEFAULT_TEMPLATE`）。 |
| availableTemplates | `template/` 目录下所有可用模板名称的列表。 |

## GET /robots.txt
根据 `config.yaml` 里的 `DISALLOW_ROBOTS` 配置返回 `robots.txt` 响应。当 `DISALLOW_ROBOTS=true` 时，返回 `User-agent: * / Disallow: /`；否则返回 404。

## GET /proxy
此API用于通过本服务代理访问指定的URL。
它接受GET请求。以下是参数说明：

| 参数 | 描述 | 可选 | 默认值 | 备注 |
| --- | --- | --- | --- | --- |
| url | 需要被代理的URL。**需要进行URIComponent编码。** | 否 | - | 使用本服务来访问这个URL并返回结果。 |
| template | 用于规则白名单校验的模板 ID。 | 是 | zju | 应与 `/sub` 使用的模板保持一致；生成出的配置在需要时会自动带上该参数。 |

## 错误响应和限制

直接提交的分享链接无效时返回 HTTP 400；上游订阅解析失败时返回 HTTP 502，并在适用时标明订阅序号和分享链接行号。转换会整体失败，不会丢弃失败节点后返回部分结果。程序自身的异常仍返回 HTTP 500。`interval` 必须是 1–2147483647 范围内的整数，否则在访问上游前返回 HTTP 400。

分享链接订阅中的空行和以 `#` 开头的元数据注释（包括含 URL 的注释）会被忽略，原文和 Base64 均支持。`trojan:/...` 等可识别的畸形链接仍会导致整体转换失败。

上游 HTTP 错误统一返回 HTTP 502，不透传上游响应正文。内网目标默认返回 HTTP 403，除非开启 `ALLOW_PRIVATE_NETWORKS`。这些检查同样适用于 `/proxy`，该接口还要求 URL 出现在所选模板的 `RULESET` 中。

Base64 外层编码支持标准带 padding 和不带 padding 的格式，并按 mihomo 行为允许 CR/LF 换行；非法字符及 padding 后的额外内容不会被静默丢弃。

同一上游重定向链会按域名、路径和 HTTPS 限制携带 Cookie，不同订阅请求不会共享 Cookie。用户提交的 HTTP URL 无效时返回 400，上游给出无效重定向目标时返回 502。

订阅支持 YAML anchor、alias 和合并键；输出可能包含 mihomo 和 Stash 支持的引用。输入、上游响应及 YAML 展开后的标量数据最大为 10 MiB，YAML 嵌套最多 32 层，展开后的 YAML 结构最多 100,000 个节点；递归引用会被拒绝。响应正文读取超时为 30 秒。`/proxy` 流式响应发出响应头后若读取失败，会中止传输并关闭相关资源。

上游响应支持 identity、gzip 和 deflate，最多四层压缩。传输正文和每一层解压输出均限制为 10 MiB，并在解压分配期间执行限制。其他编码或损坏的压缩流会导致转换失败。

每份解析后的订阅最多包含 10,000 个代理，展开后的标量字段合计最多为 10 MiB，包括重复的认证信息、嵌套选项和节点名称。所有协议和 Clash YAML 共用这套预算；Mieru 多端口展开还会在分配模型前检查。超限会导致整体转换失败。YAML 响应的序列化在工作线程执行。

`/sub` 至少需要一个非空的主订阅或主分享链接，仅提供备用来源会返回 HTTP 400。

订阅 YAML 中未加引号的 `on`、`off`、`yes` 和 `no` 会保留为字符串，与 mihomo 的订阅映射一致；`true` 和 `false` 仍为布尔值。

TCP 连接会在已验证的地址之间每隔 250 毫秒错峰竞速，共用一个连接期限。只有选中的连接发送 HTTP 请求，并保留 Host、TLS SNI 和 DNS 固定连接检查。
