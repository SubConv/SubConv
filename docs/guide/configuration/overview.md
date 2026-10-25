# Configuration

Runtime settings are described by `config.yaml.example` in the repository root. If you want to customize them, create `config.yaml` in your own deployment or fork. The runtime templates live in the root `template/` directory as `template/zju.yaml` and `template/general.yaml`.

The most important setting is `DEFAULT_TEMPLATE`, which defaults to `zju`. When the `template` query parameter is omitted, the server uses the template selected by `DEFAULT_TEMPLATE`.

If the default template file is missing locally, startup stops with an error.

If you are running from a source checkout, put your changes in `config.yaml`. If you are running a released binary, keep `config.yaml.example` next to `api`, and add `config.yaml` when you need custom runtime settings.

## Runtime Config Items

- `HOST`: the bind address of the backend process
- `PORT`: the listening port of the backend process
- `DEFAULT_TEMPLATE`: the template used when `/sub` or `/proxy` omits the `template` query parameter
- `DISALLOW_ROBOTS`: whether `/robots.txt` should return `Disallow: /` (defaults to `true`)

- `ALLOW_PRIVATE_NETWORKS`: allow subscriptions and rules to access private networks (defaults to `false`); redirect targets and all DNS addresses are checked. Enable only for deployments that need internal resources. Outbound requests connect directly, ignoring proxy environment variables.

Example `config.yaml`:

```yaml
HOST: 0.0.0.0
PORT: 8080
DEFAULT_TEMPLATE: zju
DISALLOW_ROBOTS: true
ALLOW_PRIVATE_NETWORKS: false
```

## Template File Items

- `HEAD`: Configuration before the node information, such as
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
        - 223.5.5.5
        - 8.8.8.8
        - 1.1.1.1
        proxy-server-nameserver:
        - https://dns.alidns.com/dns-query
        nameserver-policy:
          geosite:gfw,geolocation-!cn:
            - https://1.1.1.1/dns-query#🚀 节点选择
            - https://1.0.0.1/dns-query#🚀 节点选择
            - https://8.8.8.8/dns-query#🚀 节点选择
        nameserver:
        - https://dns.alidns.com/dns-query
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
- `TEST_URL`: The URL of the test node, such as
    ```yaml
    TEST_URL: https://www.gstatic.com/generate_204
    ```
- `RULESET`: Rule set, refer to [Rule Set](./rule-set)
- `CUSTOM_PROXY_GROUP` Custom proxy group, refer to [Proxy Groups](./proxy-groups)
