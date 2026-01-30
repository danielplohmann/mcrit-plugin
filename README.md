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

The recommended way to install is using [HCLI](https://hcli.docs.hex-rays.com/).

```bash
hcli plugin install mcrit-ida
```

This automatically handles dependencies (including `smda` and `mcrit` client) and configuration.

## ⚙️ Configuration

Configuration is managed via [ida-settings](https://github.com/williballenthin/ida-settings).

### Setup
1.  **GUI (Recommended)**: Install `ida-settings-editor` (`hcli plugin install ida-settings-editor`) and configure via **Edit → Plugins → Plugin Settings Manager**.
2.  **Interactive**: HCLI prompts for config values during installation.
3.  **Manual**: Edit `$IDAUSR/ida-config.json` (discouraged).

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
├── helpers/          # Utilities (incl. vendored pyperclip)
├── widgets/          # UI components
└── icons/            # Resources
```

### Local Build & Install
To install a development version from source:

```bash
# 1. Clone
git clone https://github.com/danielplohmann/mcrit-plugins.git
cd mcrit-plugins

# 2. Package
zip -r ../mcrit-ida.zip .

# 3. Install
hcli plugin install ../mcrit-ida.zip
```

##  Version History

### v1.1.4 (2026-01-30)
- Removed the mcrit package dependency by internalizing McritClient and required DTOs.
- Restored plugin hotkey handler and added a close action to the graph context menu.
- Improved resilience for missing or empty match data and guarded SMDA import paths.
- Hardened UI flows around function labels and form handling.
- Dev/CI: Added Ruff config + GitHub Action and reformatted the codebase.

### v1.1.3 (2026-01-28)
- ✨ Significantly improved usablity of FunctionOverviewWidget by being able to deconflict multiple candidate labels.

### v1.1.2 (2026-01-19)
- ✨ Optionally use SMDA as backend analysis engine (consistency towards MCRIT server), even when in IDA Pro.

### v1.1.1 (2026-01-15)
- ✨ Now coloring results in BlockMatch (by frequency) and FunctionMatch (by score) widgets
- ✨ Can now display offsets of matched functions in FunctionMatchWidget

### v1.1.0 (2025-12-30)
- ✨ Full HCLI Plugin Manager support.
- ⚙️ Migrated configuration to `ida-settings`.
- 🔧 Code quality improvements.
- ✅ Strict HCLI compliance.

### v1.0.0 (2025-12-22)
- 🎉 Initial standalone release.
- 🔄 IDA 9.2 (PySide6) compatibility.

## 📄 License
GPL-3.0. See [LICENSE](LICENSE) for details.

## 👤 Author
**Daniel Plohmann** ([@danielplohmann](https://github.com/danielplohmann))
