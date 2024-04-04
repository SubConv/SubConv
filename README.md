# Subscription Converter

English | [中文](README_CN.md)

![license](https://img.shields.io/github/license/SubConv/SubConv) ![last commit](https://img.shields.io/github/last-commit/SubConv/SubConv)

~~This project is a subscription converter aiming to transform subscriptions to Clash format. If you need a ZJU version, please go to [SubConv 4 ZJU](https://github.com/SubConv/SubConv-4-ZJU)~~

We provide configurations for general users and ZJU version, you can check [docs](https://subconv.is-sb.com) to learn how to deploy with the corresponding configuration file.

## Screenshot

![screenshot](assets/image.png)

## Features

- Support Clash config and V2ray format base64 links (i.e. the original subscription does not have to be Clash)
- A Web-UI (thanks to [@Musanico](https://github.com/musanico))
- Rules based on ACL
- Nodes auto update based on proxy-provider
- Rules auto update based on rule-provider
- Support proxy rule-provider to prevent failure to get rules from GitHub
- Support multiple airpots
- Display remaining traffic and total traffic (only useful when you use a single airport, requires your airport and Clash to support it at the same time, Clash for Windows, Clash Verge, Stash, Clash Meta for Android, etc. are known to support it)
- Implement the api of subscription conversion to proxy-provider (normal people won't use it)
- Support configuration file

## Docs

[docs](https://subconv.is-sb.com) (both Chinese and English, but machine translated)

## P.S

**Clash Core from Dreamacro** (original Clash core) is no longer supported. It's recommended to use [mihomo](https://github.com/MetaCubeX/mihomo) instead.

## Usage

Deploy by yourself according to [docs](https://subconv.is-sb.com)

## Contribute

Welcome issue and PR. If you want to contribute, please create a new branch from main and then create a PR to dev, or you can merge main into dev first and then make changes in dev, and finally create a PR to dev branch.

## Credits

- [subconverter](https://github.com/tindy2013/subconverter)
- [mihomo](https://github.com/MetaCubeX/mihomo)
- ~~[Proxy Provider Converter](https://github.com/qier222/proxy-provider-converter)~~

## License

This project is distributed under [MPL-2.0 License](https://github.com/SubConv/SubConv/blob/main/LICENSE)
