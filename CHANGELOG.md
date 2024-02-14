# Changelog

## [v2.1.0] - 2024-02-14

## What's Changed
### Breaking Changes
* perf!: change default port by @wouiSB in https://github.com/SubConv/SubConv/pull/22
### Fixes
* fix: handle redirect by @wouiSB in https://github.com/SubConv/SubConv/pull/21
* fix: fatal error in last fix by @wouiSB in https://github.com/SubConv/SubConv/pull/23
### Improvements
* perf!: change default port by @wouiSB in https://github.com/SubConv/SubConv/pull/22

## [v2.0.0] - 2024-02-10

### Features
* feat: support docker; ci: build and build image; ci: release by @wouiSB in https://github.com/SubConv/SubConv/pull/17
* feat: cli to generate config file by @wouiSB in https://github.com/SubConv/SubConv/pull/18
### Breaking Changes
* feat: support config for headers (like DNS, etc.) by @wouiSB in https://github.com/SubConv/SubConv/pull/14
* refactor: use yaml config by @wouiSB in https://github.com/SubConv/SubConv/pull/16

**Full Changelog**: https://github.com/SubConv/SubConv/compare/v1.0.0...v2.0.0

## [v1.0.0] - 2024-02-08

### Breaking Changes
- Remove `region_dict` in config file because it duplicates the function of `regex` field.
### Changes
- Use rule-provider
### Features
- Support proxy of url of rulesets to ensure that rulesets can be downloaded.
