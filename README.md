# Plugin(s) for the MinHash-based Code Relationship & Investigation Toolkit (MCRIT)

MCRIT is a framework created to simplify the application of the MinHash algorithm in the context of code similarity.  
This repository houses plugins to interact with an MCRIT instance from within other binary analyiss tools, with currently only IDA Pro being supported.

## Usage

### IDA Plugin

In order to use the plugin, MCRIT and its dependencies have to be installed within the Python version used by IDA Pro.
Additionally, `pyperclip` is used to facilitate copying data (YARA rule fragments) to the clipboard.
Using the `requirements.txt` for installation should provide everything needed.

Once installed, the plugin can be started by simply running `mcrit-plugins/ida/ida_mcrit.py` as a Python script from within IDA Pro.

### Configuration 

The plugin's behavior can be controlled through a config file.
To instantiate your config, copy or rename `template.config.py` to `config.py`.

#### Connecting to MCRIT

In order to fully use the plugin, you need to be able to interact with an MCRIT instance.  
This can be both a MCRIT standalone server or a MCRITweb instance via API pass-through.

To set up the connection use this section of the `config.py`:

```
MCRITWEB_USERNAME = ""
MCRIT_SERVER = "http://127.0.0.1:8000/"
MCRITWEB_API_TOKEN = ""
```

The username is only relevant if talking directly to MCRIT, because when using an API token as provided by MCRITweb, the username is automatically inferred from the token holder instead.

#### Startup and UI Behavior

The remaining part of the configuration file controls the behavior during startup and default settings for the individual widgets.


## Version History

 * 2025-12-22 v1.0.0:  Moved Plugin to its own repository. Fixed compatibility with up to version IDA 9.2 (adopting PySide6).

## Credits & Notes

Pull requests welcome! :)

## License
```
    Plugins for MCRIT
    Copyright (C) 2025+ Daniel Plohmann

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
    
    Some plug-ins and libraries may have different licenses. 
    If so, a license file is provided in the plug-in's folder.
```
