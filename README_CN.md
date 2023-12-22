# Subscription Converter
[English](README.md) | Chinese  
![license](https://img.shields.io/github/license/SubConv/SubConv) ![last commit](https://img.shields.io/github/last-commit/SubConv/SubConv)  
这个项目是面向所有Clash用户的订阅转换，如果你需要ZJU专版，请移步[SubConv 4 ZJU](https://github.com/SubConv/SubConv-4-ZJU)  

## 功能
- 支持Clash配置和V2ray格式的base64链接（即原始订阅不一定是Clash）  
- 一个可以勉强能看的订阅转换 Web-UI (感谢 [@Musanico](https://github.com/musanico))  
- 大体基于 ACL 的规则  
- 基于 Provider 的节点自动更新  
- （为土豪）多机场用户提供了支持  
- 剩余流量和总流量的显示（单机场的时候才有用，需要你的机场和你用的Clash同时支持，已知Clash for Windows, Clash Verge, Stash, Clash Meta for Android等已支持）  
- 实现了订阅转换成 proxy-provider 的 api, (一般人也不会去用吧)
- 支持配置文件 (`config.py`，之后说不定会写subconverter配置到本项目的转换)  

## 文档
[docs](https://subconv.is-sb.com) (中英都有, 但是机翻)  

## 说明
**若为原版内核需要v1.15.0或更新，否则会出现地区分组分类失败的情况**  
~~本接口适用于一元机场的订阅转换（大概率不适用于别的机场）~~ 现理论上适配所有机场，由于使用了clash特性proxy-provider，Linux用户只需保存转换后的配置可实现自动更新节点(不需要自动更新的脚本，是clash核心本身支持的)<br>
目前 hysteria, hysteria2, TUIC 的转换未经测试，遇到问题请提issue，并提供日志（Vercel可以看日志，VPS部署可以看输出的错误信息）  

## 食用方法
自己根据 [文档](https://subconv.is-sb.com) 部署  

## 为本项目贡献
欢迎 issue 和 PR。如果要提pr请从main分支开新分支然后提pr到dev分支，或者也可以先把main合并到dev然后在dev里改，最后提pr到dev  

## 致谢
- [subconverter](https://github.com/tindy2013/subconverter)  
- [mihomo](https://github.com/MetaCubeX/mihomo)  
- ~~[Proxy Provider Converter](https://github.com/qier222/proxy-provider-converter)~~  

## 许可证
本项目采用 [MPL-2.0 License](https://github.com/SubConv/SubConv/blob/main/LICENSE) 分发  
