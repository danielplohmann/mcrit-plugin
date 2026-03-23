# MCRIT IDA Plugin

[![IDA Version](https://img.shields.io/badge/IDA-9.0%2B-blue.svg)](https://hex-rays.com/ida-pro/)
[![Python](https://img.shields.io/badge/python-3.x-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-GPL--3.0-green.svg)](LICENSE)
[![HCLI Compatible](https://img.shields.io/badge/HCLI-compatible-brightgreen.svg)](https://hcli.docs.hex-rays.com/)

> **Integration with MCRIT** for MinHash-based code similarity analysis in IDA Pro.

MCRIT (MinHash-based Code Relationship & Investigation Toolkit) simplifies MinHash-based code similarity detection.
This plugin seamlessly integrates MCRIT servers with IDA Pro for malware analysis and function identification.

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
python scripts/package_plugin.py --repo . --output ../mcrit-ida.zip
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

1. Copy this repository, or extract a packaged release ZIP, into `$IDAUSR/plugins/mcrit-ida/`.
2. Ensure the plugin directory contains at least `ida-plugin.json`, `ida_mcrit.py`, `config.py`, `helpers/`, `widgets/`, and `icons/`.
3. Install the Python dependencies with the Python interpreter bundled with your IDA installation:

```bash
python -m pip install smda ida-settings>=3.3.0
```

4. Restart IDA Pro.

If your installation of IDA Pro is in an offline Windows VM, use the wheelhouse bundle from the release assets instead. After unpacking it, install from the local directory:

```bash
python -m pip install --no-index --find-links=. -r requirements.txt
```


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

If you are not using HCLI, the most practical manual override is a `config_override.json` placed next to `config.py`. A minimal example looks like this:

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
├── ida-plugin.json   # Plugin metadata
├── ida_mcrit.py      # Entry point
├── config.py         # Settings management
├── helpers/          # Utilities (incl. vendored pyperclip and pylev)
├── widgets/          # UI components
└── icons/            # Resources
```

### Local Build & Install
To install a development version from source:

```bash
# 1. Clone
git clone https://github.com/danielplohmann/mcrit-plugin.git
cd mcrit-plugin

# 2. Package
python scripts/package_plugin.py --repo . --output ../mcrit-ida.zip

# 3. Install
hcli plugin install ../mcrit-ida.zip
```

### Validation
Run the local checks before publishing:

```bash
python scripts/verify_metadata_sync.py --repo .
python scripts/verify_settings_sync.py --repo .
python scripts/run_quality_checks.py --repo .
python scripts/package_plugin.py --repo . --output dist/mcrit-ida.zip
hcli plugin lint .
hcli plugin lint dist/mcrit-ida.zip
```

### Release Workflow
This plugin publishes a dedicated plugin ZIP as the HCLI package artifact.

```bash
git tag v1.1.6
git push origin v1.1.6
```

The tag-driven release workflow validates metadata, builds `mcrit-ida-<version>.zip`, lints both the repo and the ZIP with `hcli`, and then creates the GitHub release with the plugin archive attached. The offline dependency workflow runs after the release is published and attaches the optional wheelhouse bundles.

##  Version History

### v1.1.6 (2026-03-23)
- Updated HCLI-facing plugin metadata for release packaging, including the `1.1.6` version, `IDA 9.0+` minimum, repository URL, and request-timeout setting.
- Added repo-local packaging and validation scripts for metadata sync, settings sync, Ruff checks, and minimal plugin ZIP creation.
- Added validation/release GitHub Actions to lint both the repo and packaged ZIP, publish `mcrit-ida-<version>.zip`, and attach offline dependency bundles to published releases.
- Switched the offline dependency workflow to run from published releases so wheelhouse bundles attach to the canonical release instead of tag pushes alone.
- Expanded the README with first-time HCLI setup, local ZIP installs, headless configuration examples, and manual installation steps without HCLI.

### v1.1.5 (2026-02-27)
- Added configurable MCRIT request timeouts via `mcrit_request_timeout` and aligned numeric setting defaults with the plugin settings metadata.
- Refactored `McritClient` HTTP calls through shared request helpers and added centralized timeout support via `setTimeout()`.
- Moved the initial server connection check off the UI thread and improved startup status reporting.
- Added architecture-aware SMDA backend selection with logging and fallback handling during IDB-to-SMDA conversion.
- Hardened `McritInterface` connection error handling and UI-thread dispatch for background updates.
- Guarded remote metadata lookups and empty/missing response data in `BlockMatchWidget`, `FunctionMatchWidget`, and `SampleInfoWidget` to avoid crashes when server state is incomplete.
- Added safety checks before applying labels in `FunctionOverviewWidget` when no label column is configured or no labels have been fetched.
- Fixed job dialog preselection when the selected row index is `0`.
- Removed the custom graph close action from `SmdaGraphViewer` to avoid the `AttributeError` path there.
- Cleaned up vendored `pyperclip` compatibility handling for newer Python versions and removed stray debug/formatting issues from the batch.

### v1.1.4 (2026-01-30)
- added Github action to build dependency packages to facilitate installation in offline environments.
- Removed the mcrit package dependency by internalizing McritClient and required DTOs.
- Restored plugin hotkey handler and added a close action to the graph context menu.
- Improved resilience for missing or empty match data and guarded SMDA import paths.
- Hardened UI flows around function labels and form handling.
- Dev/CI: Added Ruff config + GitHub Action and reformatted the codebase.

### v1.1.3 (2026-01-28)
- Significantly improved usablity of FunctionOverviewWidget by being able to deconflict multiple candidate labels.

### v1.1.2 (2026-01-19)
- Optionally use SMDA as backend analysis engine (consistency towards MCRIT server), even when in IDA Pro.

### v1.1.1 (2026-01-15)
- Now coloring results in BlockMatch (by frequency) and FunctionMatch (by score) widgets
- Can now display offsets of matched functions in FunctionMatchWidget

### v1.1.0 (2025-12-30)
- Full HCLI Plugin Manager support.
- Migrated configuration to `ida-settings`.
- Code quality improvements.
- Strict HCLI compliance.

### v1.0.0 (2025-12-22)
- Initial standalone release.
- IDA 9.2 (PySide6) compatibility.

## 📄 License
GPL-3.0. See [LICENSE](LICENSE) for details.

## 👤 Author
**Daniel Plohmann** ([@danielplohmann](https://github.com/danielplohmann))
