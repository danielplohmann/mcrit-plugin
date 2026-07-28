# AGENTS.md — MCRIT IDA Plugin (`mcrit-ida`)

This repository is the **IDA Pro plugin for MCRIT** (MinHash-based Code Relationship & Investigation Toolkit). It provides a GUI interface within IDA Pro (9.0+) to interact with an **existing** MCRIT server for interactive code-similarity analysis: querying functions/blocks, syncing labels, and visualizing matches. It is a *client* of the MCRIT core service (see [mcrit](https://github.com/danielplohmann/mcrit)), not the server itself — the server runs elsewhere and is contacted over its REST API.

For the MCRIT methodology (PicHash/MinHash, LSH banding) see the [mcrit `AGENTS.md`](../mcrit/AGENTS.md) and the [README](README.md).

## Repository layout

- `ida_mcrit.py` — plugin entry point (registers actions, widgets, menus in IDA).
- `config.py` — `SettingsWrapper` around `ida-settings`; **defaults** for every setting.
- `ida-plugin.json` — **HCLI/IDA plugin metadata**: the single source of truth for the plugin `version` and the declarative `settings` list.
- `helpers/` — plugin logic.
  - `McritInterface.py` — orchestrates server communication, background jobs, UI-thread dispatch.
  - `McritClient` (under `helpers/minimcrit/`) — the **internalized** MCRIT client + DTOs (the `mcrit` package is no longer a dependency; see "Vendored vs. internalized" below).
  - `IdaProxy.py` — abstraction over the IDA/IDAPython API.
  - `QtShim.py` — PySide6/Qt abstraction for the widgets.
  - `ScoreColorProvider.py`, `McritTableColumn.py`, `ClassCollection.py`, `HeadlessMcritContext.py` — UI/util helpers.
  - `minimcrit/`, `pylev/`, `pyperclip/` — see "Vendored vs. internalized".
- `widgets/` — Qt views (`MainWidget`, `FunctionMatchWidget`, `BlockMatchWidget`, `FunctionOverviewWidget`, `SampleInfoWidget`, `LocalInfoWidget`, dialogs, `SmdaGraphViewer`).
- `scripts/` — packaging, metadata/settings verification, and IDA/IDALib smoke-test harnesses.
- `tests/` — pure-Python pytest suite (IDA/SMDA are stubbed in `conftest.py`).
- `icons/`, `qt-designer-mockup/` — resources.

## Development setup

**Python:** the runtime floor is **Python 3.11** (enforced by the `smda>=4.3.10` co-dependency). IDA 9 bundles its own interpreter (3.11/3.12); the `scripts/*.py` harnesses run under a separate venv of the same minor series. Note: `pyproject.toml` sets ruff `target-version = "py38"` for formatting compatibility only — do **not** read that as a supported runtime floor.

Install dependencies with the IDA-bundled or matching Python:

```bash
python -m pip install "smda>=4.3.10" "ida-settings>=3.5.1"
```

Install the plugin via HCLI (`hcli plugin install ...`) or by copying the repo into `$IDAUSR/plugins/mcrit-ida/` (see README for both paths).

## Common commands

Lint (run before considering work done):

```bash
ruff format --check .
ruff check .
```

Tests (no IDA/license required — IDA and SMDA are stubbed):

```bash
python -m pytest tests
```

Packaging metadata / settings sanity (must pass before release; see "Settings & version sync"):

```bash
python scripts/verify_metadata_sync.py --repo .
python scripts/verify_settings_sync.py --repo .
python scripts/run_quality_checks.py --repo .
python scripts/package_plugin.py --repo . --output dist/mcrit-ida.zip
```

## Architecture primer

- **Entry** (`ida_mcrit.py`) registers IDA menus/actions/hotkeys and the MCRIT widget subviews.
- **`McritInterface`** owns the connection to the MCRIT server, runs long operations (convert IDB→SMDA, upload, query, match) off the UI thread, and dispatches results back to the widgets.
- **`McritClient`** (internalized under `helpers/minimcrit/`) is the HTTP client speaking the MCRIT REST API. The plugin intentionally vendors a minified copy of the core client so it has no hard dependency on the `mcrit` package.
- **IDB→SMDA conversion** uses SMDA (optionally as the analysis backend via `use_smda_for_analysis`); results feed matching and label sync.
- **Widgets** render matches/blocks/functions/overview and are built on PySide6 through `QtShim`.

## Key concepts

These mirror the MCRIT core vocabulary (the plugin is a client of them):

- **PicHash / PicBlockHash** — exact, position-independent hashes (function- and block-level).
- **MinHash signature** — fuzzy similarity estimate derived from shingled code features.
- **Band / LSH** — candidate generation during fuzzy matching.
- **Family / Sample / Function** — the three-tier storage hierarchy on the server.
- **Label** — a server-side function name; the plugin can fetch, sync, and push function names.
- **Settings** — per-plugin configuration via `ida-settings`, declared in `ida-plugin.json`.

## Code conventions

- Lint/format: `ruff` (line-length 100, `target-version = "py38"`, selects `E4/E7/E9/F/I`). Run `ruff format .` to auto-format. Vendored dirs (`helpers/minimcrit`, `helpers/pylev`, `helpers/pyperclip`, `icons`, `qt-designer-mockup`) are excluded from ruff.
- License: GPL-3.0-only.
- Do **not** introduce or log secrets/API tokens.

## Agent guardrails

- **Never** run `git commit`, `git push`, or open a PR unless explicitly instructed.
- **Never** commit secrets: `mcritweb_api_token`, `mcritweb_username`, `ida-config.json`, or a `config_override.json` containing credentials. These must stay out of the tree.
- **Settings & version sync** (this is the easy-to-break part):
  - Settings are **declared** in `ida-plugin.json` (`settings` array) and have **defaults** in `config.py` (`SettingsWrapper._defaults`). These two must stay in sync; `verify_settings_sync.py` enforces it.
  - The plugin `version` lives only in `ida-plugin.json` and is mirrored in the README changelog. **Do not bump the version unless explicitly asked.** When it is bumped, update both `ida-plugin.json` and the README "Version History".
  - Always run `verify_metadata_sync.py` and `verify_settings_sync.py` after touching either file.
- **Testing**: run `ruff format --check`, `ruff check`, and `python -m pytest tests` before considering work complete. The pure pytest suite is secret-free and runs in CI on every push/PR.
- **IDA-licensed integration tests** (`.github/workflows/ida-tests.yml`) require a licensed IDA Pro and the `IDA_LICENSE_ID`/`HCLI_API_KEY` secrets. They are **not** available to fork PRs and must **not** be run by default. They are referenced here for completeness only; drive them via manual workflow dispatch or the local `scripts/run_idalib_smoke.py` / `scripts/run_ida_smoke.py` harnesses when a licensed IDA is present.
- **Vendored vs. internalized**:
  - `helpers/pylev` and `helpers/pyperclip` are third-party vendored libraries. Do **not** edit them.
  - `helpers/minimcrit` is the *minified* MCRIT API surface internalized for this plugin. Enhancing it (e.g. exposing more functionality) is allowed, **but its `McritClient` interface must not deviate from the core `mcrit` package's `McritClient`** unless the core client is enhanced in lockstep. Keep the two aligned.

## Related repositories (reference only)

- [mcrit](https://github.com/danielplohmann/mcrit) — core server, worker, Python client, CLI (this plugin is a client of it).
- [mcrit-web](https://github.com/fkie-cad/mcritweb) — Flask browser front-end + user management.
- [docker-mcrit](https://github.com/danielplohmann/docker-mcrit) — containerized full-stack deployment.
- [mcrit-data](https://github.com/danielplohmann/mcrit-data) — ready-to-use reference data.
