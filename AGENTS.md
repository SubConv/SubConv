# SubConv Agent Notes

## What matters

- SubConv ships three parts: a FastAPI backend in `subconv/`, a Vue/Vite frontend in `mainpage/`, and VitePress docs in `docs/`.
- `api.py` must keep exporting `app` from `subconv.app`; Vercel routes API traffic to `api.py`, and the CLI entrypoint also lives there.
- The public converter entrypoint is `subconv.converter.ConvertsV2Ray`; `subconv/subscription.py` falls back to it when incoming content is not Clash YAML.
- Runtime settings precedence is env vars > repo-root `config.yaml` > `config.yaml.example`; `.env` files are not loaded. Keep `config.yaml.example` in sync with required fields.
- Runtime templates live in the repo-root `template/` directory. `zju.yaml` is the default template when `/sub` or `/proxy` omits the `template` query parameter.

## Local commands

- Install Python deps with `uv sync`.
- Backend runtime settings load from env/config as above; user-specific file changes belong in uncommitted `config.yaml`.
- Start the backend with `uv run python api.py` (host/port come from `config.yaml`).
- Do not ask users to install a specific Bun version; use the repo commands and lockfiles.
- Frontend dev server: `cd mainpage && bun install && bun run dev`.
- Frontend production build: `cd mainpage && bun install && bun run build`; CI uses `bun ci && bun run build`.
- Docs dev server: `cd docs && bun install && bun run dev`.
- Docs production build: `cd docs && bun install && bun run build`; CI uses `bun ci && bun run build`.
- Nuitka/build dependencies are in the `build` group: use `uv sync --locked --group build` before local binary or image build work.

## Verification

- Converter tests live under `tests/` and run without network access. Install their optional dependencies with `uv sync --locked --group test`, then run `uv run --no-sync python -m pytest tests/`.
- For backend changes, also run `python3 -m compileall subconv api.py` and any focused smoke script needed for the touched parser/route; the converter suite does not cover HTTP routes.
- For frontend-only changes, the CI-equivalent check is `cd mainpage && bun install && bun run build`.
- For docs-only changes, the CI-equivalent check is `cd docs && bun install && bun run build`.
- If you touch packaging/build flow, also read the matching workflow under `.github/workflows/` and keep local verification aligned with it.
- After backend, frontend, config, CLI, deployment, or other user-facing changes, review `docs/` and `README*.md` to see whether documentation needs updating; when behavior or examples changed, update the docs in the same change.

## Architecture boundaries

- `subconv/app.py` owns all HTTP routes: `/`, `/sub`, `/provider`, `/proxy`, `/config`, `/robots.txt`, plus static file serving from `mainpage/dist`.
- `mainpage/src/App.vue` depends on `/config` for available templates; keep the Vercel `/config` route intact.
- `subconv/cli.py` owns CLI parsing and `uvicorn.run(...)`; `api.py` is intentionally thin and `chdir`s to its own directory when run as `__main__` so relative runtime files resolve beside the binary/script.
- `subconv/config.py` loads runtime settings and validates all local templates from `template/*.yaml`; startup should fail fast if any template or the configured default template is invalid.
- `subconv/packer.py` assembles the final mihomo config. Its proxy-group filtering intentionally mutates the first group’s `proxies` list when removing empty groups.
- `subconv/converter/` is protocol-specific share-link parsing. Keep field aliases aligned with mihomo YAML keys and align share-link parsing behavior with mihomo's converter: https://github.com/MetaCubeX/mihomo/tree/Meta/common/convert
- `docs/` is a standalone VitePress site deployed by GitHub Pages; keep it separate from app/Vercel runtime assumptions.

## Repo-specific gotchas

- `DISALLOW_ROBOTS` is a typed boolean loaded through `pydantic-settings`; use YAML booleans like `true`/`false` in config files.
- `/proxy` only fetches rule URLs present in the selected template’s `RULESET`; generated configs include `template=` when needed so whitelist checks use the same template.
- `_split_sources()` in `subconv/app.py` treats `https://t.me/...` specially as standalone share links rather than remote subscription URLs.
- `subconv/subscription.py` falls back to `ConvertsV2Ray()` on any exception while trying Clash YAML shape parsing; inside `ConvertsV2Ray`, per-line parsing should only skip malformed links by catching `ParseError`, not broad exceptions.
- Use mihomo docs as the config/protocol reference: https://wiki.metacubex.one
- Align protocol config fields with mihomo config definitions: https://github.com/MetaCubeX/mihomo/tree/Meta/config
- `static/` and frontend build output are not committed. Local backend UI serving depends on a manual `mainpage/dist` build.
- Frontend package management is Bun-based; keep `mainpage/package.json` and `mainpage/bun.lock` in sync.
- Docs package management is Bun-based; keep `docs/package.json` and `docs/bun.lock` in sync.
- Root `package.json` only pins Node `24.x`; app scripts live under `mainpage/` and `docs/`.

## Deployment and CI facts

- Vercel uses legacy `builds` in `vercel.json`: `@vercel/python` for `api.py` and `@vercel/static-build` for `mainpage/package.json`. Keep existing API paths (`/sub`, `/provider`, `/proxy`, `/config`, `/robots.txt`) intact.
- Docker build is Alpine-based and compiles the backend with Nuitka, then copies `mainpage/dist`, `config.yaml.example`, and `template/` into the runtime image.
- `docker-compose.yml` mounts `./config.yaml:/app/config.yaml` and `./template:/app/template`; keep runtime template examples under `template/`, not `subconv/`.
- CI pins Python 3.13 and Bun 1.3.11 for frontend/docs builds. `build.yml` builds binaries plus the frontend; `test-mainpage.yml` and `test-docs.yml` only verify buildability.
- Docs deploy separately through a GitHub Pages workflow rooted at `docs/`; keep that workflow aligned with the original docs repo behavior, just using Bun.
- Releases are tag-driven (`v*`) and zip per-platform artifacts after reusing the build workflow; dev image builds trigger from `dev` path changes.

## Contribution workflow

- README says contributors branch from `main` and open PRs against `dev` (or merge `main` into `dev` first, then PR to `dev`).
- All future commits must follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/).
- Use `<type>[optional scope][!]: <description>`. Keep types lowercase and use a meaningful scope when it clarifies the affected area, such as `converter`, `api`, or `docs`.
- Choose the type by the change: `feat` for new functionality, `fix` for bug fixes, `perf` for performance improvements, `refactor` for restructuring without behavior changes, and `docs`, `test`, `build`, `ci`, or `chore` where appropriate.
- Mark breaking changes with `!` before the colon or a `BREAKING CHANGE: <description>` footer. Separate the optional body and footers from preceding sections with a blank line.
- Keep commits focused and split unrelated concerns into separate commits.
