# Changelog

## [7.0.1] - 2023-11-02

### Fixed
- fix: Quart设置的response headers貌似会在Vercel上的类型有问题，所以换成Fastapi

### Changed
- perf: Quart换成了Fastapi，提升性能

## [7.0.0] - 2023-10-24
### **Breaking Changes**
配置文件有变动，原配置文件无法正常工作，"手动选择"、"自动选择"、"负载均衡"、"故障转移"、"ZJU"等规则组需要重新配置，同时新增了一个必填字段`region_dict`，请参考[docs](https://subconv.github.io/guide/configuration/proxy-groups.html)或仓库中的`config.py`  
新用户无需关心，直接使用即可  

### Add
- feat: 支持节点分享链接（不是订阅链接）  
- feat: 支持tg格式分享链接  
- feat: 支持 unofficial TUIC 分享链接  
- feat: 除了 节点选择 规则组，其余规则组都支持在配置文件配置  
- feat: 支持备用节点  

### Changed
- perf: 把Flask换成Quart，提升性能  
- refactor: 生成yaml配置从纯文字处理改为先生成序列化对象再转yaml，增加可维护性  

### Fixed
- fix: 修复vmess v2链接解析的一个bug  
- fix: 修复负载均衡规则组可能重复的问题  

## [6.1.0] - 2023-05-24
### Changed
- perf: 删除了原有的针对meta的组内filter，因为原版clash也已实现  

## [6.0.0] - 2023-05-19
### Add
- feat: 支持了hysteria, vmess, vless, trojan, vless, ss, ssr的base64订阅，也就是基本上所有订阅都能用了  


## [5.0.0] - 2023-04-06
### Add
- feat: 支持规则组配置文件  


## [4.0.0] - 2023-03-23
### Add
- feat: 实现了转换provider的api，不再依赖其他项目  


## [3.2.0] - 2023-03-22
### Fixed
- fix: 无论如何都会又台湾规则组，导致如果没有台湾节点原版内核会报错的问题  


## [3.1.0] - 2023-03-18
### Add
- feat: 增加了生成组内filter的开关，可以极大地减少vercel用量  


## [3.0.0] - 2023-02-26
### Add
- feat: 支持了多机场  
- feat: 增加订阅转换的webUI @Musanico  


## [2.2.0] - 2023-02-02
### Add
- feat: 支持了多种GUI客户端里流量信息显示的功能  


## [2.1.0] - 2023-01-30
### Changed
- perf: 简化定期缓存规则的方式  


## [2.0.0] - 2023-01-27
### Changed
- refactor & feat: 重构配置生成的流程，适配几乎所有Clash订阅（原先只适配了一元只因厂）  
- perf: 每次生成Clash配置时拉取规则改为每7天更新一次规则到仓库，提升Clash配置生成速度  


## [1.1.0] - 2023-01-15
### Add
- feat: 添加自定义规则，只需在custom-rules分支的direct.list文件中添加需要直连的规则即可（默认不在规则里的都会走“漏网之鱼”规则组，他可以选择流量流向且默认走代理，所以不需要为需要为需要走代理的添加规则）  


## [1.0.0] - 2022-06-27
### Add
- feat: 基本能自用，只适配了一元机场  
