# Changelog

## [v4.0.0] - 2026-10-26

### Breaking Changes

- Block private-network upstream subscriptions and rule URLs by default. Trusted deployments that need local or private upstreams must set `ALLOW_PRIVATE_NETWORKS: true` in `config.yaml` or the equivalent environment variable.
- Reject an entire conversion when any node is malformed instead of silently dropping failed nodes. Invalid direct links return 400; invalid upstream subscriptions return 502. Blank lines and `#` metadata comments remain supported.
- Enforce subscription and YAML resource limits, including 10,000 proxies and 10 MiB of expanded scalar fields per parsed subscription. Unsupported template filter syntax now fails validation at startup.

### Features and Fixes

- Align share-link conversion with mihomo Meta across VLESS, VMess, Shadowsocks, SSR, Trojan, Hysteria, Hysteria2, TUIC, AnyTLS and Mieru, including transport options, credentials, Base64 validation and repeated query parameters.
- Normalize Telegram SOCKS links to mihomo's `socks5` type and reject unsupported Telegram proxy types.
- Support bounded YAML anchors, aliases and merge keys while preserving subscription names such as `on`, `off`, `yes` and `no` as strings.
- Validate DNS addresses and redirect targets, pin outbound connections to checked addresses, retain Host/SNI, race TCP connections and bound decompression at every layer.
- Close proxied upstream resources on cancellation and disconnects, including failures while sending response headers.
- Preserve SubConv's direct-node filtering, primary/standby and `manual` semantics; fix empty groups, name collisions and inline rule option placement.
- Validate update intervals and report clipboard failures accurately in the Web UI.

### Build and Dependencies

- Add offline backend regression tests and CI coverage for converters, routes, grouping, YAML and upstream transports.
- Repair multi-platform Alpine/Nuitka image builds and update the GitHub release action to v2.
- Refresh backend, frontend, documentation and build dependencies, including FastAPI, uvicorn, Vue, Element Plus, Vite and VitePress; pin HTTPcore for the checked-address transport integration.
- Update English and Chinese documentation with migration settings, limits and API error behavior.

**Full Changelog**: https://github.com/SubConv/SubConv/compare/v3.1.0...v4.0.0

## [v3.1.0] - 2026-04-26

### Features

- Add AnyTLS and Mieru converters aligned with mihomo share-link parsing
- Align VLESS XHTTP parsing with current mihomo converter behavior
- Add AI proxy group to the default templates

### Dependencies

- Bump FastAPI 0.135.3 → 0.136.0
- Bump pydantic-settings 2.13.1 → 2.14.0
- Bump Vite 8.0.8 → 8.0.9 (frontend)
- Bump @vitejs/plugin-vue 6.0.5 → 6.0.6 (frontend)

### Documentation

- Mention AnyTLS and Mieru support in the docs

**Full Changelog**: https://github.com/SubConv/SubConv/compare/v3.0.1...v3.1.0

## [v3.0.1] - 2026-04-16

### Fixes

- Fix Docker/Nuitka startup path resolution so onefile builds load external runtime files from the executable directory

**Full Changelog**: https://github.com/SubConv/SubConv/compare/v3.0.0...v3.0.1

## [v3.0.0] - 2026-04-11

### Breaking Changes

- **Python 3.13 is now required** (up from 3.11); `distutils` usage removed
- **Backend rewritten from `modules/` to `subconv/` package** with Pydantic model-based parsing aligned to mihomo source (`converter.go`, `v.go`)
- **Template system reworked**: Python-embedded template dicts replaced by file-based YAML templates in `template/*.yaml`
- **All CLI arguments removed**; host/port/default-template are now read from `config.yaml` exclusively
- **`DISALLOW_ROBOTS` migrated from `eval()` on env var to pydantic-settings config field** (default changed from `False` to `True`)
- **`/sub` endpoint now passes client User-Agent to upstream** instead of hardcoding `"v2rayn"` for GET requests
- **Release workflow no longer triggers on pushes to `main`**; only version tags (`v*`) produce releases
- **Frontend package manager switched from Yarn to Bun** (pinned `bun@1.3.11`)

### Features

- Add `/config` endpoint returning `defaultTemplate` and `availableTemplates`
- Add `/robots.txt` endpoint controlled by `DISALLOW_ROBOTS` config setting
- Add URL whitelist check in `/proxy` endpoint (only allows URLs from the selected template's `RULESET`)
- Add template selector to the Web UI, driven by the `/config` endpoint with auto-retry on failure
- Add `/config` route to `vercel.json` for Vercel deployments
- Import VitePress docs from separate repository, switch to Bun, add GitHub Pages deploy workflow
- Update region regex to regexp2-compatible patterns and add UK proxy group
- Include `template/` and `config.yaml.example` in release archives for self-contained VPS deployment

### Fixes

- Secure static file serving with path traversal protection (`_resolve_static_path`)
- Centralize remote URL fetching with `_fetch_remote_response` and `_validate_remote_url` for consistent error handling
- Fix `chdir` to script directory in `api.py __main__`
- Correct Vercel catch-all route destination to `/mainpage/$1`
- Set Node.js 24.x in `package.json` engines for Vercel
- Add `DISALLOW_ROBOTS` to `config.yaml.example`
- Fix Vercel router for `/robots.txt`
- Fix base64 padding error in subscription parsing
- Fix `+` character in node names being incorrectly decoded
- Fix error parsing trojan nodes
- Fix h2 transport handling
- Fix bug in `/proxy` endpoint introduced in earlier commit
- Make `CUSTOM_PROXY_GROUP` and `RULESET` nullable in template config
- Fix Caddy reverse proxy URL errors
- Resolve Nuitka onefile build failure in CI
- Replace `distutils.util.strtobool` with pydantic `TypeAdapter` (removed in Python 3.12+)
- Replace `pydantic-settings-yaml` with built-in `YamlConfigSettingsSource` (available in pydantic-settings v2.8+)
- Add back `path` field in rule-providers for older mihomo kernels

### Improvements

- Migrate from `pip`/`requirements.txt` to `uv` with `pyproject.toml` + `uv.lock`
- Remove committed `static/` build output; Vercel builds frontend at deploy time
- Simplify `vercel.json` routing for new module layout
- Remove `generate-mainpage.yml` workflow (Vercel handles frontend build)
- Relay client User-Agent through to upstream subscription providers
- Scope CI workflow triggers to relevant file paths
- Add template and `config.yaml.example` paths to build workflow triggers
- Docker: pin Alpine 3.22, bootstrap uv via pip, use `uv sync` for deps

### Dependencies

- Bump FastAPI 0.111.0 → 0.135.3
- Bump uvicorn 0.29.0 → 0.44.0
- Bump httpx 0.27.0 → 0.28.1
- Bump PyYAML 6.0.1 → 6.0.3
- Bump Vite 5.4.21 → 8.0.8 (frontend)
- Bump @vitejs/plugin-vue 5.2.4 → 6.0.5 (frontend)

### Documentation

- Fix typos: "airpots" → "airports", "Getting Started", broken Releases URL
- Fix template wording in landing and intro pages
- Align HEAD and proxy-groups examples with `general.yaml` template
- Document `/config`, `/robots.txt` endpoints and `t.me` handling in API docs
- Update deployment instructions for Docker Compose and VPS `setcap`
- Fix `config.yml` → `config.yaml` and `chmod +x api.py` → `chmod +x api` in deploy docs
- Describe SubConv as mihomo-oriented (not Clash) in intro pages
- Update backend startup instructions in READMEs
- Update DISALLOW_ROBOTS references from env var to `config.yaml`

**Full Changelog**: https://github.com/SubConv/SubConv/compare/v2.1.3...v3.0.0

## [v2.1.3] - 2024-04-04

> **From this version, the Docker image is published on Docker Hub. Change the `image` field in `docker-compose.yml` from `ghcr.io/subconv/subconv:latest` to `wouisb/subconv:latest`.**

### Fixes

- Make [Vercel](https://vercel.com) happy

**Full Changelog**: https://github.com/SubConv/SubConv/compare/v2.1.2...v2.1.3

## [v2.1.2] - 2024-03-24

### Fixes

- [core] Add back support for Clash Meta <= v1.15.1 (#30)
- [ui] Fix title of the web page (#31)
- [config] Fix config generation & error handling (#32)

**Full Changelog**: https://github.com/SubConv/SubConv/compare/v2.1.0...v2.1.2

## [v2.1.1] - 2024-02-15

**Full Changelog**: https://github.com/SubConv/SubConv/compare/v2.1.0...v2.1.1

## [v2.1.0] - 2024-02-14

### Breaking Changes

- Change default port (#22)

### Fixes

- Handle redirect (#21)
- Fix fatal error in redirect handling (#23)

### Improvements

- Change default port (#22)

**Full Changelog**: https://github.com/SubConv/SubConv/compare/v2.0.0...v2.1.0

## [v2.0.0] - 2024-02-10

### Features

- Support Docker; CI build and build image; CI release (#17)
- CLI to generate config file (#18)

### Breaking Changes

Please refer to [docs](https://subconv.is-sb.com) for configuration.

- Support config for headers (like DNS, etc.) (#14)
- Use YAML config (#16)

**Full Changelog**: https://github.com/SubConv/SubConv/compare/v1.0.0...v2.0.0

## [v1.0.0] - 2024-02-08

### Breaking Changes

- Remove `region_dict` in config file because it duplicates the function of `regex` field.

### Changes

- Use rule-provider

### Features

- Support proxy of url of rulesets to ensure that rulesets can be downloaded.
