import json
import os

from binaryninja import Settings

from mcrit_plugin.core.config import PLUGIN_ROOT, McritConfig

GROUP = "mcrit"
SECRET_SETTINGS = {"mcritweb_api_token"}
# ida-settings only has string/boolean, so numeric settings are declared as strings in ida-plugin.json
NUMBER_SETTINGS = {
    "mcrit_request_timeout": (0, 3600),
    "blocks_min_size": (4, 20),
    "function_min_score": (0, 100),
    "overview_min_score": (0, 100),
}


def _read_json(filename):
    with open(os.path.join(PLUGIN_ROOT, filename), "r", encoding="utf-8") as handle:
        return json.load(handle)


VERSION = _read_json("plugin.json")["version"]
# shared with ida-plugin.json (kept identical by scripts/verify_settings_sync.py); ida-plugin.json
# itself is excluded from GitHub source archives, which is what Binary Ninja installs
_DECLARED_SETTINGS = {
    setting["key"]: setting
    for setting in _read_json(os.path.join("mcrit_plugin", "core", "settings.json"))
}


def register_settings():
    settings = Settings()
    settings.register_group(GROUP, "MCRIT")
    defaults = McritConfig(VERSION)._defaults
    for key, declared in _DECLARED_SETTINGS.items():
        properties = {
            "title": declared["name"],
            "type": declared["type"],
            "default": defaults[key],
            "description": declared["documentation"],
            "ignore": ["SettingsProjectScope", "SettingsResourceScope"],
        }
        if key in NUMBER_SETTINGS:
            properties["type"] = "number"
            properties["default"] = int(defaults[key])
            properties["minValue"], properties["maxValue"] = NUMBER_SETTINGS[key]
        if key in SECRET_SETTINGS:
            properties["hidden"] = True
        settings.register_setting(f"{GROUP}.{key}", json.dumps(properties))


def _get_setting(key):
    full_key = f"{GROUP}.{key}"
    settings = Settings()
    if not settings.contains(full_key):
        raise KeyError(key)
    if key in NUMBER_SETTINGS:
        return settings.get_integer(full_key)
    if _DECLARED_SETTINGS[key]["type"] == "boolean":
        return settings.get_bool(full_key)
    return settings.get_string(full_key)


config = McritConfig(VERSION, _get_setting)
