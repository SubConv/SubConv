# Rule sets
You can refer to the bundled templates [`template/zju.yaml`](https://github.com/SubConv/SubConv/blob/main/template/zju.yaml) and [`template/general.yaml`](https://github.com/SubConv/SubConv/blob/main/template/general.yaml). The `RULESET` variable defines the rule sets.  

Entries prefixed with `[]` are inline rules. For rule types that accept options, the policy is inserted before trailing `no-resolve`/`src` options, following [mihomo rule syntax](https://wiki.metacubex.one/config/rules/):

```yaml
RULESET:
  - [DIRECT, "[]IP-CIDR,10.0.0.0/8,no-resolve"]
  - [DIRECT, "[]DOMAIN-SUFFIX,example.com"]
  - [DIRECT, "[]FINAL"]
```

Regex rules such as `PROCESS-NAME-REGEX` and logical rules such as `AND` allow commas in their payload and do not accept these options. Their policy remains the final field; for example, `[DIRECT, "[]PROCESS-NAME-REGEX,my,src"]` generates `PROCESS-NAME-REGEX,my,src,DIRECT`.
