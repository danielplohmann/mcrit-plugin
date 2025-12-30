# MCRIT IDA Plugin

[![IDA Version](https://img.shields.io/badge/IDA-9.0%2B-blue.svg)](https://hex-rays.com/ida-pro/)
[![Python](https://img.shields.io/badge/python-3.x-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-GPL--3.0-green.svg)](LICENSE)
[![HCLI Compatible](https://img.shields.io/badge/HCLI-compatible-brightgreen.svg)](https://hcli.docs.hex-rays.com/)

> Integration with MCRIT server for MinHash-based code similarity analysis in IDA Pro.

MCRIT (MinHash-based Code Relationship & Investigation Toolkit) is a framework that simplifies the application of the MinHash algorithm for code similarity detection. This plugin provides seamless integration with MCRIT servers directly from IDA Pro, enabling powerful malware analysis, code comparison, and function identification workflows.

## ✨ Features

- 🔍 **Code Similarity Analysis** - Compare functions and basic blocks against MCRIT database
- 🎯 **Function Matching** - Identify similar functions across different binaries
- 🏷️ **Label Management** - Submit and retrieve function labels from MCRIT server
- 📊 **Interactive Widgets** - Multiple views for blocks, functions, and overview analysis
- ⚙️ **Integrated Settings** - Configuration via IDA's native settings system (ida-settings)
- 🔌 **HCLI Support** - One-command installation via Hex-Rays Plugin Manager
- 🌐 **Server Connectivity** - Supports both standalone MCRIT and MCRITweb instances
- 📋 **YARA Integration** - Generate and copy YARA rule fragments

## 🚀 Installation

### Method 1: HCLI (Recommended)

The easiest way to install the MCRIT plugin is using [HCLI (Hex-Rays Command Line Interface)](https://hcli.docs.hex-rays.com/):

```bash
# Install HCLI if not already installed
# See: https://hcli.docs.hex-rays.com/getting-started/installation/

# Install the MCRIT plugin
hcli plugin install mcrit-ida
```

**That's it!** HCLI automatically:
- ✅ Downloads and installs the plugin to `$IDAUSR/plugins/mcrit-ida/`
- ✅ Installs all required Python dependencies
- ✅ Configures the plugin settings system
- ✅ Makes the plugin available in IDA Pro

### Method 2: Manual Installation

For manual installation or development purposes:

#### Prerequisites

- IDA Pro 9.0 or later
- Python 3.x (as used by your IDA installation)

#### Steps

1. **Clone or download this repository:**
   ```bash
   git clone https://github.com/danielplohmann/mcrit-plugins.git
   cd mcrit-plugins
   ```

2. **Install Python dependencies:**
   ```bash
   # Using the provided requirements.txt
   pip install -r requirements.txt

   # Or install individually:
   pip install mcrit>=1.4.3 requests lief>=0.16.0 smda>=1.13.19 \
               tqdm mmh3>=2.5.1 "numpy<2.0.0" pyperclip ida-settings>=3.3.0
   ```

3. **Copy plugin to IDA plugins directory:**
   ```bash
   # Find your IDAUSR directory
   # Windows: %APPDATA%\Hex-Rays\IDA Pro
   # Linux: ~/.idapro
   # macOS: ~/.idapro

   # Copy the plugin directory
   cp -r mcrit-plugins/ida "$IDAUSR/plugins/mcrit-ida"
   ```

4. **Verify installation:**
   - Launch IDA Pro
   - The MCRIT plugin should auto-load
   - Look for MCRIT menu items or widgets

## ⚙️ Configuration

The plugin uses [ida-settings](https://github.com/williballenthin/ida-settings) for configuration management. Settings can be configured through:

### 1. IDA Pro GUI (Recommended)

- Open IDA Pro
- Go to **Edit → Plugins → MCRIT Settings** (or via Plugin Manager)
- Configure settings through the GUI interface

### 2. HCLI Command Line

```bash
# View current settings
hcli config get mcrit-ida

# Set MCRIT server URL
hcli config set mcrit-ida.mcrit_server "http://your-server:8000/"

# Set API token for MCRITweb
hcli config set mcrit-ida.mcritweb_api_token "your_token_here"
```

### 3. Configuration File

Settings are stored in `$IDAUSR/ida-config.json`:

```json
{
  "plugins": {
    "mcrit-ida": {
      "mcrit_server": "http://127.0.0.1:8000/",
      "mcritweb_api_token": "",
      "mcritweb_username": "",
      "auto_analyze_smda_on_startup": false,
      "function_min_score": "50",
      "overview_min_score": "50"
    }
  }
}
```

### Key Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `mcrit_server` | string | `http://127.0.0.1:8000/` | MCRIT server URL |
| `mcritweb_api_token` | string | `""` | API token for MCRITweb authentication |
| `mcritweb_username` | string | `""` | Username (optional if using API token) |
| `auto_analyze_smda_on_startup` | boolean | `false` | Auto-convert IDB to SMDA on startup |
| `submit_function_names_on_close` | boolean | `false` | Prompt to upload function names on close |
| `function_min_score` | string | `"50"` | Minimum match score for functions |
| `overview_min_score` | string | `"50"` | Minimum match score for overview |
| `blocks_min_size` | string | `"4"` | Minimum block size for analysis |

For a complete list of settings, see `ida-plugin.json` in the plugin directory.

## 🔌 Connecting to MCRIT Server

The plugin can connect to:

1. **Standalone MCRIT Server**
   - Set `mcrit_server` to your server URL
   - Optionally set `mcritweb_username`

2. **MCRITweb Instance** (via API pass-through)
   - Set `mcrit_server` to MCRITweb URL
   - Set `mcritweb_api_token` for authentication
   - Username is inferred from token holder

**Example:**
```bash
hcli config set mcrit-ida.mcrit_server "https://mcritweb.example.com/api/"
hcli config set mcrit-ida.mcritweb_api_token "eyJ0eXAiOiJKV1QiLCJ..."
```

## 📖 Usage

### Basic Workflow

1. **Open a binary in IDA Pro**

2. **Access MCRIT widgets:**
   - View → Open subviews → MCRIT widgets
   - Or use the MCRIT menu items

3. **Analyze functions:**
   - Right-click on a function → MCRIT → Query function
   - View matches in the Function widget
   - Compare and label functions

4. **Export results:**
   - Generate YARA rules from matches
   - Copy results to clipboard
   - Submit function labels to server

### Widget Overview

- **Block Scope Widget** - Analyze and match basic blocks
  - Filter library functions
  - Live query mode
  - Configurable minimum block size

- **Function Scope Widget** - Match entire functions
  - View similarity scores
  - See matched samples and families
  - Submit function names

- **Function Overview Widget** - High-level analysis
  - Fetch labels automatically
  - Filter by labels or conflicts
  - Batch analysis of multiple functions

### Advanced Features

- **SMDA Analysis** - Automatic conversion of IDB to SMDA format
- **Live Querying** - Real-time updates as you navigate
- **Library Filtering** - Exclude common library functions
- **Score Thresholds** - Customize minimum match scores

## 🔧 Development

### Project Structure

```
mcrit-plugins/ida/
├── ida-plugin.json        # HCLI plugin metadata
├── ida_mcrit.py          # Main entry point
├── config.py             # Configuration with ida-settings integration
├── README.md             # This file
├── requirements.txt      # Python dependencies
├── icons/                # Plugin icons and logo
├── helpers/              # Helper modules and utilities
└── widgets/              # UI widgets for IDA Pro
```

### Building from Source

```bash
# Clone repository
git clone https://github.com/danielplohmann/mcrit-plugins.git
cd mcrit-plugins

# Install development dependencies
pip install -r requirements.txt

# Run tests (if available)
pytest tests/

# Install locally for testing
hcli plugin install .
```

### Testing

Test your changes in an isolated environment:

```bash
# Use a separate IDAUSR directory
export IDAUSR=~/.idapro-test

# Install plugin
cp -r mcrit-plugins/ida "$IDAUSR/plugins/mcrit-ida"

# Launch IDA
ida
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests.

### Guidelines

- Follow PEP 8 style guidelines
- Add tests for new features
- Update documentation as needed
- Ensure compatibility with IDA Pro 9.0+
- Test with both MCRIT standalone and MCRITweb

### Reporting Issues

Please report bugs and feature requests on the [GitHub Issues](https://github.com/danielplohmann/mcrit-plugins/issues) page.

## 📚 Resources

- **MCRIT Framework:** [github.com/danielplohmann/mcrit](https://github.com/danielplohmann/mcrit)
- **SMDA Disassembler:** [github.com/danielplohmann/smda](https://github.com/danielplohmann/smda)
- **IDA Pro:** [hex-rays.com/ida-pro](https://hex-rays.com/ida-pro/)
- **HCLI Documentation:** [hcli.docs.hex-rays.com](https://hcli.docs.hex-rays.com/)
- **ida-settings:** [github.com/williballenthin/ida-settings](https://github.com/williballenthin/ida-settings)
- **Plugin Repository:** [plugins.hex-rays.com](https://plugins.hex-rays.com/)

## 📋 Requirements

- **IDA Pro:** 9.0, 9.1, or 9.2
- **Python:** 3.x (as bundled with IDA)
- **Dependencies:**
  - mcrit >= 1.4.3
  - requests
  - lief >= 0.16.0
  - smda >= 1.13.19
  - tqdm
  - mmh3 >= 2.5.1
  - numpy < 2.0.0
  - pyperclip
  - ida-settings >= 3.3.0

## 📜 Version History

### v1.4.5 (2025-12-30)
- ✨ Full HCLI Plugin Manager support
- ⚙️ Migrated configuration to ida-settings
- 🔧 Fixed code quality issues
- 📝 Enhanced documentation
- ✅ Strict HCLI compliance

### v1.0.0 (2025-12-22)
- 🎉 Moved plugin to its own repository
- 🔄 Fixed compatibility with IDA 9.2 (PySide6)

## 📄 License

```
Plugins for MCRIT
Copyright (C) 2025+ Daniel Plohmann

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
```

## 👤 Author

**Daniel Plohmann**
- Email: daniel.plohmann@fkie.fraunhofer.de
- GitHub: [@danielplohmann](https://github.com/danielplohmann)

## 🙏 Acknowledgments

- The Hex-Rays team for IDA Pro and HCLI
- The reverse engineering community
- All contributors and users of MCRIT

---

**Need help?** Check the [documentation](https://github.com/danielplohmann/mcrit-plugins) or open an [issue](https://github.com/danielplohmann/mcrit-plugins/issues).
