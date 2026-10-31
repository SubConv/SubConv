# 配置

仓库根目录下的 `config.yaml.example` 描述了默认的运行时参数。如果你需要自定义，请在自己的部署环境或 fork 仓库里创建 `config.yaml`。运行时模板使用 YAML 格式，位于仓库根目录的 `template/` 下，当前内置 `template/zju.yaml` 和 `template/general.yaml` 两个文件。

最重要的参数是 `DEFAULT_TEMPLATE`，默认值为 `zju`。当请求里不传 `template` 查询参数时，服务就会使用 `DEFAULT_TEMPLATE` 指定的模板。

如果默认模板文件在本地不存在，程序会直接报错并停止启动。

如果你是从源码运行，请把你的改动放在 `config.yaml` 里。如果你使用的是发布版二进制文件，请确保 `config.yaml.example` 与解压后的 `template/` 目录和 `api` 放在一起；如果需要自定义运行时参数，再额外提供 `config.yaml`。

## 运行时配置项

- `HOST`：后端绑定地址
- `PORT`：后端监听端口
- `DEFAULT_TEMPLATE`：当 `/sub` 或 `/proxy` 不带 `template` 查询参数时使用的模板
- `DISALLOW_ROBOTS`：是否让 `/robots.txt` 返回 `Disallow: /`（默认值为 `true`）

- `ALLOW_PRIVATE_NETWORKS`：是否允许订阅和规则访问内网（默认 `false`）；重定向目标和全部 DNS 解析地址都会检查。仅在部署确实需要内部资源时开启。出站请求直接连接，不使用代理环境变量。

示例 `config.yaml`：

```yaml
HOST: 0.0.0.0
PORT: 8080
DEFAULT_TEMPLATE: zju
DISALLOW_ROBOTS: true
ALLOW_PRIVATE_NETWORKS: false
```

## 模板文件项

- `HEAD`: 节点信息之前的配置，如
    ```yaml
    HEAD:
      mixed-port: 7890
      allow-lan: true
      mode: rule
      log-level: info
      external-controller: :9090
      dns:
        enable: true
        listen: 0.0.0.0:1053
        default-nameserver:
        - 119.29.29.29
        - 8.8.8.8
        - 1.1.1.1
        proxy-server-nameserver:
        - https://doh.pub/dns-query
        nameserver-policy:
          geosite:gfw,geolocation-!cn:
            - https://1.1.1.1/dns-query#🚀 节点选择
            - https://1.0.0.1/dns-query#🚀 节点选择
            - https://8.8.8.8/dns-query#🚀 节点选择
        nameserver:
        - https://doh.pub/dns-query
        - https://8.8.8.8/dns-query#🚀 节点选择
        fallback:
        - https://1.1.1.1/dns-query#🚀 节点选择
        - https://1.0.0.1/dns-query#🚀 节点选择
        - https://8.8.8.8/dns-query#🚀 节点选择
        fallback-filter:
          geoip: false
          geoip-code: CN
          ipcidr:
          - 240.0.0.0/4
        fake-ip-filter:
        - +.lan
        - +.microsoft*.com
        - localhost.ptlogin2.qq.com
    ```
- `TEST_URL`: 测试节点的 URL，如
    ```yaml
    TEST_URL: https://www.gstatic.com/generate_204
    ```
- `RULESET`: 规则集，参考 [规则集](./rule-set)
- `CUSTOM_PROXY_GROUP` 自定义代理组，参考 [Proxy Groups](./proxy-groups)
