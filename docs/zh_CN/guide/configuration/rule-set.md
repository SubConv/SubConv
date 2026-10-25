# 规则集
你可以参考仓库内置的 [`template/zju.yaml`](https://github.com/SubConv/SubConv/blob/main/template/zju.yaml) 和 [`template/general.yaml`](https://github.com/SubConv/SubConv/blob/main/template/general.yaml)，其中的 `RULESET` 就是规则集的配置。  

以 `[]` 开头的条目是内联规则。对于支持可选参数的规则类型，策略名称会插入到末尾 `no-resolve`/`src` 参数之前，遵循 [mihomo 规则语法](https://wiki.metacubex.one/config/rules/)：

```yaml
RULESET:
  - [DIRECT, "[]IP-CIDR,10.0.0.0/8,no-resolve"]
  - [DIRECT, "[]DOMAIN-SUFFIX,example.com"]
  - [DIRECT, "[]FINAL"]
```

`PROCESS-NAME-REGEX` 等正则规则和 `AND` 等逻辑规则允许匹配内容包含逗号，不接受上述可选参数；策略名称始终位于最后。例如 `[DIRECT, "[]PROCESS-NAME-REGEX,my,src"]` 会生成 `PROCESS-NAME-REGEX,my,src,DIRECT`。
