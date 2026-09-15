# MCRIT IDA Plugin

[![IDA Version](https://img.shields.io/badge/IDA-9.0%2B-blue.svg)](https://hex-rays.com/ida-pro/)
[![Python](https://img.shields.io/badge/python-3.x-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-GPL--3.0-green.svg)](LICENSE)
[![HCLI Compatible](https://img.shields.io/badge/HCLI-compatible-brightgreen.svg)](https://hcli.docs.hex-rays.com/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/danielplohmann/mcrit-plugin)

> **Integration with MCRIT** for MinHash-based code similarity analysis in IDA Pro.

MCRIT (MinHash-based Code Relationship & Investigation Toolkit) simplifies MinHash-based code similarity detection.
This plugin seamlessly integrates the interaction with MCRIT servers from with IDA Pro for malware analysis and function identification.

## ✨ Features

- **Code Similarity** - Compare functions/blocks against MCRIT.
- **Function Matching** - Identify similar functions across binaries.
- **Label Management** - Sync function labels with the server.
- **Interactive Widgets** - Dedicated views for blocks, functions, and overview.
- **Integrated Settings** - Native configuration via `ida-settings`.
- **HCLI Support** - Easy installation and updates.

## 🚀 Installation

### Option 1: HCLI

For new users, start with [HCLI](https://hcli.docs.hex-rays.com/). The package to install is `ida-hcli`, and the command you will use afterward is `hcli`.

```bash
python -m pip install --upgrade ida-hcli
hcli --version
```

If `mcrit-ida` has already been indexed by the Hex-Rays plugin repository, install it directly:

```bash
hcli plugin search mcrit
hcli plugin install mcrit-ida
```

Useful follow-up commands:

```bash
hcli plugin status
hcli plugin upgrade mcrit-ida
hcli plugin uninstall mcrit-ida
```

If the plugin has not been indexed yet, or you want to test a local build first, package the plugin locally and install the ZIP:

```bash
python scripts/ida/package_plugin.py --repo . --output ../mcrit-ida.zip
hcli plugin install ../mcrit-ida.zip
```

For headless shells or CI, pass settings explicitly so `hcli` does not try to open its interactive configuration prompt:

```bash
hcli plugin install ../mcrit-ida.zip \
  --config mcrit_server=https://mcrit.example.com/api/ \
  --config mcritweb_api_token=YOUR_TOKEN \
  --config mcritweb_username=analyst \
  --config mcrit_request_timeout=10
```

### Option 2: Manual Installation Without HCLI

If you do not want to use HCLI at all, you can install the plugin manually:

1. Extract a packaged release ZIP (or one built with `scripts/ida/package_plugin.py`) into `$IDAUSR/plugins/mcrit-ida/`. A repository checkout is not an IDA plugin directory: the packager places `ida-plugin.json` and `ida_mcrit.py` at the archive root.
2. Ensure the plugin directory contains at least `ida-plugin.json`, `ida_mcrit.py`, `mcrit_plugin/`, and `icons/`.
3. Install the Python dependencies with the Python interpreter bundled with your IDA installation:

```bash
python -m pip install "smda>=4.3.10" "ida-settings>=3.5.1"
```

4. Restart IDA Pro.

If your installation of IDA Pro is in an offline Windows VM, use the wheelhouse bundle from the release assets instead. After unpacking it, install from the local directory:

```bash
python -m pip install --no-index --find-links=. -r requirements.txt
```

### Binary Ninja

The same repository is a Binary Ninja plugin (Binary Ninja 6.0+, Python 3). Install it through the Extension Manager, or clone it into the Binary Ninja user plugins folder; `requirements.txt` lists the Python dependencies the Extension Manager installs.

- Configure the server and behavior under **Settings → MCRIT** (same settings as the IDA plugin).
- An API token entered in Settings is moved into the system keychain and the Settings field is cleared; **MCRIT → Clear Stored API Token** removes it again.
- Open the **MCRIT** sidebar from the right sidebar, or run any **MCRIT** action from the command palette or **Plugins → MCRIT**.
- SMDA reports are exported from Binary Ninja's own analysis; **Query Current Function** and **Query Current Block** follow the cursor, and remote CFGs open as Binary Ninja graph reports.


## ⚙️ Configuration

Configuration is managed via [ida-settings](https://github.com/williballenthin/ida-settings).

### Configure with HCLI

If you installed via HCLI, inspect and update settings from the command line:

```bash
hcli plugin config mcrit-ida list
hcli plugin config mcrit-ida get mcrit_server
hcli plugin config mcrit-ida set mcrit_server https://mcrit.example.com/api/
hcli plugin config mcrit-ida set mcritweb_api_token YOUR_TOKEN
hcli plugin config mcrit-ida set mcrit_request_timeout 10
```

You can also export or import settings as JSON:

```bash
hcli plugin config mcrit-ida export
hcli plugin config mcrit-ida import "{\"mcrit_server\":\"https://mcrit.example.com/api/\",\"mcrit_request_timeout\":\"10\"}"
```

### Configure with the GUI

Install `ida-settings-editor` and configure the plugin through **Edit -> Plugins -> Plugin Settings Manager**:

```bash
hcli plugin install ida-settings-editor
```

### Configure Manually

If you are not using HCLI, the most practical manual override is a `config_override.json` placed in the installed plugin root, next to `ida_mcrit.py` (template: `docs/config_override.json.template`). A minimal example looks like this:

```json
{
  "mcrit_server": "https://mcrit.example.com/api/",
  "mcritweb_api_token": "YOUR_TOKEN",
  "mcritweb_username": "analyst",
  "mcrit_request_timeout": "10"
}
```

You can also manage settings through `$IDAUSR/ida-config.json` if you already use `ida-settings`.

### Connecting to Server
Configure the plugin to connect to your MCRIT instance:

| Setting | Description | Example |
| :--- | :--- | :--- |
| `mcrit_server` | Server URL | `https://mcrit.example.com/api/` |
| `mcritweb_api_token` | API Token (for MCRITweb) | `eyJ0eXAi...` |
| `mcritweb_username` | Username (optional) | `analyst` |
| `sample_group_only` | Restrict matching queries to the server-side sample group | `false` |

**Note**: For MCRITweb, the username is inferred automatically by setting the API token.

## 📖 Usage

1.  **Open Binary**: Load a file in IDA Pro.
2.  **Open Widgets**: View → Open subviews → MCRIT widgets.
3.  **Analyze**: Right-click a function → **MCRIT** → **Query function**.
4.  **Matches**: Review results in the **Function Scope Widget**.

## 🔧 Development

### Project Structure
```text
mcrit-plugin/
├── plugin.json            # Binary Ninja plugin metadata (must stay at the repository root)
├── __init__.py            # Binary Ninja entry point
├── requirements.txt       # Binary Ninja Python dependencies
├── mcrit_plugin/
│   ├── core/              # no GUI imports: MCRIT client, settings (+ settings.json), Backend interface, revision
│   ├── ui_qt/             # Qt shim, session host and widgets shared by IDA and Binary Ninja
│   ├── headless/          # licence-free backend: SMDA disassembles the file, labels stay in memory
│   ├── ida/               # ida-plugin.json, ida_mcrit.py entry, IDA backend, ida-settings binding, graph viewer
│   └── binja/             # Binary Ninja backend, SMDA exporter interface, settings, sidebar and actions
├── icons/                 # Resources shared by both plugins
├── tests/
│   ├── core/              # pytest suite (IDA and SMDA are stubbed in tests/conftest.py)
│   ├── ida/               # IDA GUI and IDALib integration tests
│   ├── binja/             # Binary Ninja GUI integration test
│   └── fixtures/
├── scripts/
│   ├── ida/               # packaging, metadata check, IDA integration runners
│   ├── binja/             # Binary Ninja integration runner
│   └── common/            # settings check, quality checks, fixtures, MCRIT seeding, headless test, report comparison
└── docs/                  # config_override.json.template, Qt Designer mockup
```

### Local Build & Install
To install a development version from source:

```bash
# 1. Clone
git clone https://github.com/danielplohmann/mcrit-plugin.git
cd mcrit-plugin

# 2. Package
python scripts/ida/package_plugin.py --repo . --output ../mcrit-ida.zip

# 3. Install
hcli plugin install ../mcrit-ida.zip
```

### Validation
Run the local checks before publishing:

```bash
python scripts/ida/verify_metadata_sync.py --repo .
python scripts/common/verify_settings_sync.py --repo .
python scripts/common/run_quality_checks.py --repo .
python scripts/ida/package_plugin.py --repo . --output dist/mcrit-ida.zip
hcli plugin lint .
hcli plugin lint dist/mcrit-ida.zip
```

### IDA and MCRIT Integration Tests

The repository keeps the normal pytest and Ruff jobs secret-free. Licensed IDA
testing is isolated in `.github/workflows/ida-tests.yml`: it runs on pushes to
`main` and through manual dispatch, using the `IDA_LICENSE_ID` and
`HCLI_API_KEY` repository secrets. Pull requests, including fork pull requests,
do not receive those secrets.

The required Linux job installs IDA Pro 9.3, starts a local MCRIT server backed
by MongoDB, seeds a deterministic reference binary, and runs an IDALib MCRIT
integration test followed by a GUI-process toolbar integration test. To run the broader
IDA-version/platform IDALib checks, manually dispatch the workflow with
`run_matrix` enabled.

#### Local IDALib integration test

IDALib runs the IDA analysis APIs without a GUI. Use it for the package,
conversion, upload, and matching workflow; the separate GUI integration test below covers
the actual toolbar callbacks. Use the Python ABI configured for the installed
IDA version (the CI job deliberately selects Python 3.12); install the
`idapro` package from that IDA distribution and use an isolated IDA user
directory:

```bash
python3 -m venv .venv-idalib
.venv-idalib/bin/python -m pip install --upgrade \
  "/path/to/IDA Professional 9.3/idalib/python"/idapro-*.whl \
  "smda==4.8.0" "ida-settings==3.5.1"

python scripts/common/build_test_fixture.py \
  --source tests/fixtures/mcrit_sample.c \
  --output /tmp/mcrit-idalib-fixture \
  --variant 1

.venv-idalib/bin/python scripts/ida/run_idalib_integration.py \
  --ida-dir "/path/to/IDA Professional 9.3" \
  --input /tmp/mcrit-idalib-fixture \
  --idausr /tmp/mcrit-idalib-user \
  --mcrit-server http://127.0.0.1:8000
```

The runner activates IDALib for that virtual environment, installs the local
ZIP into the isolated profile, and restores its MCRIT settings afterwards.
Use `--offline` to validate package loading and IDB-to-SMDA conversion without
a MCRIT service.

#### Local IDA GUI integration test

The local runner uses an existing IDA installation and your normal IDA user
profile; it does not require an HCLI API key. When `hcli` is available it
installs the current local ZIP into that profile when no copy is present; an
already-installed copy is refreshed directly without HCLI. The headless
process therefore loads the same plugin setup that your normal IDA session
uses. It invokes IDA with `-A -S` and chooses the GUI executable by default
because IDA's `idat` binary refuses to import PySide6. It uses the native
`cocoa` Qt platform on macOS and `offscreen` elsewhere; use `--ida-binary` or
`--qt-platform` to override either choice.

```bash
python scripts/common/build_test_fixture.py \
  --source tests/fixtures/mcrit_sample.c \
  --output /tmp/mcrit-ida-fixture \
  --variant 1

python scripts/ida/run_gui_integration.py \
  --ida-dir "/path/to/IDA Professional 9.3.app" \
  --input /tmp/mcrit-ida-fixture \
  --mcrit-server http://127.0.0.1:8000
```

If the plugin is already installed and should not be replaced, pass its
installed directory explicitly:

```bash
python scripts/ida/run_gui_integration.py \
  --ida-dir "/path/to/IDA Professional 9.3.app" \
  --input /tmp/mcrit-ida-fixture \
  --plugin-root "$HOME/.idapro/plugins/mcrit-ida" \
  --mcrit-server http://127.0.0.1:8000
```

The CI workflow passes `--idausr` to create an isolated profile; the default
local path deliberately reuses the profile that already has IDAPython and the
plugin configured. The runner temporarily points that profile at the requested
MCRIT server and restores its original `ida-config.json` afterward.

IDA itself still enforces its license when it starts; the runner does not
perform or bypass that check. If headless execution reports that Python is not
configured, run the matching `idapyswitch --auto-apply` from that IDA
installation first.

For a live local MCRIT test, use Python 3.12 for the service, then run
MongoDB and the two MCRIT processes in separate terminals. The workflow pins
MCRIT `1.5.0`; it requires Python 3.11 or 3.12 (use 3.12) and its default API is
`http://127.0.0.1:8000`:

```bash
docker run --rm --name mcrit-mongo -p 27017:27017 mongo:5.0
python3.12 -m venv .venv-mcrit
.venv-mcrit/bin/python -m pip install "mcrit==1.5.0"
.venv-mcrit/bin/python -m mcrit server
.venv-mcrit/bin/python -m mcrit worker
```

For a deterministic positive local match, build and seed the reference variant
before running the query fixture; `seed_mcrit.py` waits for the worker:

```bash
python scripts/common/build_test_fixture.py \
  --source tests/fixtures/mcrit_sample.c \
  --output /tmp/mcrit-ida-reference \
  --variant 0
.venv-mcrit/bin/python scripts/common/seed_mcrit.py \
  --server http://127.0.0.1:8000 \
  --sample /tmp/mcrit-ida-reference
```

Use `--offline` with `run_gui_integration.py` when a live MCRIT service is not
available; the GUI integration test still drives conversion, metadata dialogs, YARA, and
isolated settings. With a live service it additionally drives
upload/query/matching, labels, graphs, and SMDA export. A manual GUI pass is
still useful for visual rendering: open the MCRIT views, inspect labels and
graphs, and verify settings through the Plugin Settings Manager.

#### Local Binary Ninja GUI integration test

Requires a licensed Binary Ninja installation (the test runs in the GUI, not headless), a live MCRIT
service seeded with a reference sample, and a Python 3 environment matching Binary Ninja's
interpreter with `smda` and `requests` installed:

```bash
python scripts/binja/run_gui_integration.py \
  --input /tmp/mcrit-binja-query.exe \
  --reference-sha256 <sha256 of the seeded reference sample> \
  --mcrit-server http://127.0.0.1:8000/
```

The runner creates a throwaway Binary Ninja user directory (license copy, this checkout linked
as a plugin, `tests/binja/gui_integration.py` as `startup.py`), so the local Binary Ninja profile is not
touched. The test drives the MCRIT sidebar through conversion, upload, matching job creation
and selection, cursor-following function queries, undoable renames, and the CFG graph report.

#### Headless integration test (no disassembler licence)

`scripts/common/run_headless_integration.py` drives the shared core (conversion, upload, matching,
label import) with the headless backend against a live MCRIT service. CI runs it on every push and
pull request:

```bash
python scripts/common/run_headless_integration.py \
  --input /tmp/mcrit-headless-query \
  --reference-sha256 <sha256 of the seeded reference sample>
```

#### Exporter agreement

MCRIT matches on normalized instruction sequences, so IDA, Binary Ninja and SMDA's own disassembler
must produce the same PicHashes for the same binary. Compare exported reports (optionally adding
SMDA's own disassembly and a failure threshold):

```bash
python scripts/common/compare_smda_reports.py \
  --report ida=ida.smda --report binja=binja.smda --binary sample.exe --min-agreement 0.9
```

### Release Workflow
IDA and Binary Ninja are versioned and released independently from the same repository.

**IDA** releases are tag-driven and publish a dedicated plugin ZIP as the HCLI package artifact:

```bash
git tag ida-v1.2.0
git push origin ida-v1.2.0
```

The IDA release workflow validates metadata, builds `mcrit-ida-<version>.zip`, lints the ZIP with `hcli`, and creates the GitHub release with the archive attached. The offline dependency workflow then attaches the optional wheelhouse bundles. IDA releases are never marked as the latest GitHub release, and `ida-plugin.json` is excluded from GitHub source archives (`.gitattributes`), so HCLI only indexes the attached ZIP.

**Binary Ninja** releases are started manually: Actions → Binary Ninja release → Run workflow, or

```bash
gh workflow run binja-release.yml -f dry-run=true
gh workflow run binja-release.yml -f version=1.1.0
```

The workflow runs the checks on the default branch, then [Vector35/plugin_actions](https://github.com/Vector35/plugin_actions) bumps the `plugin.json` version (the last number when `version` is blank), commits it as `github-actions[bot]`, tags the commit with the bare version and publishes it as the latest GitHub release. The extension manager reads `plugin.json` at that release and only compares its `version`, so every release must increase it. If the default branch is protected, `github-actions[bot]` must be allowed to push. Binary Ninja versions `1.1.4`, `1.1.5` and `1.1.7`–`1.1.9` are unavailable because older IDA releases used `v1.1.x` tags, and the action refuses to reuse them. The first release also has to be announced once in an issue on [Vector35/community-plugins](https://github.com/Vector35/community-plugins) to be listed on extensions.binary.ninja.

##  Version History

See [CHANGELOG.md](CHANGELOG.md) for the full release history.

## 📄 License
GPL-3.0. See [LICENSE](LICENSE) for details.

## 👤 Author
**Daniel Plohmann** ([@danielplohmann](https://github.com/danielplohmann))  
**Rony** ([@r0ny123](https://github.com/r0ny123))
