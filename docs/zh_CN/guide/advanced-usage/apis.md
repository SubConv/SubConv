# APIs
下面是API的介绍：

## GET /sub
这是用于子部分转换的API，它包含在Web界面生成的链接中。

它接受GET请求。以下是参数说明：

| 参数 | 描述 | 可选 | 默认值 | 备注 |
| --- | --- | --- | --- | --- |
| url | 原始订阅链接或节点分享链接。**需要进行URIComponent编码。** | 否 | - | 支持多个订阅链接。您可以使用换行符或"\|"分隔它们。`https://t.me/...` 链接会被视为独立分享链接（按 V2Ray 节点解析），而非远程订阅 URL。 |
| template | 用于渲染最终配置的模板 ID。 | 是 | zju | 当前内置值为 `zju` 和 `general`。不传时默认使用 `zju`。 |
| interval | 代理更新间隔。 | 是 | 1800 | 单位：秒。 |
| urlstandby | 备用订阅链接或节点分享链接。其中的代理将仅添加到**手动切换组**(配置文件中`"manual"`为`True`的组)中，并不会归类到区域组中。**建议进行URIComponent编码。** | 是 | - | 支持多个订阅链接。您可以使用换行符或"|"分隔它们。 |
| direct | 需要在生成的 mihomo 规则中强制 `DIRECT` 的原始订阅链接或域名。**需要进行URIComponent编码。** | 是 | - | 支持用换行符或"|"分隔多个条目。每个域名必须来自 `url` 或 `urlstandby`，否则请求返回 400。只会生成精确的 `DOMAIN,<host>,DIRECT` 规则。 |
| short | 如果设置了此参数（无论取值为何），将不会生成包含 allow-lan 等内容的标头部分和 dns 部分。 | 是 | - | - |
| npr | 如果设置了此参数（无论取值为何），将不会代理 ruleset 的 URL | 是 | - | 默认情况下，会使用这个服务来代理 ruleset 的 URL，以保证能正常获取规则集。若设置了此参数，将不会代理 ruleset 的 URL。 |

`direct` 主要用于本地网关或透明代理部署场景。它会让生成的 mihomo 配置把指定原始订阅域名直连，从而在同一个 mihomo 实例承载透明代理流量时，降低 SubConv 后续后端拉取订阅被失效代理链路卡住的概率。它不会改变 SubConv 后端 HTTP client 本身的连接方式，也不能解决首次生成配置前后端已经无法拉取原始订阅的冷启动问题。

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
