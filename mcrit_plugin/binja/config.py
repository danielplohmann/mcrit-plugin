import json
import os

from binaryninja import Settings

from mcrit_plugin.core.config import PLUGIN_ROOT, McritConfig

GROUP = "mcrit"


def _read_json(filename):
    with open(os.path.join(PLUGIN_ROOT, filename), "r", encoding="utf-8") as handle:
        return json.load(handle)


VERSION = _read_json("plugin.json")["version"]
# ida-plugin.json is the single declaration of the plugin settings for every disassembler
_DECLARED_SETTINGS = {
    setting["key"]: setting for setting in _read_json("ida-plugin.json")["plugin"]["settings"]
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
        settings.register_setting(f"{GROUP}.{key}", json.dumps(properties))


def _get_setting(key):
    full_key = f"{GROUP}.{key}"
    settings = Settings()
    if not settings.contains(full_key):
        raise KeyError(key)
    if _DECLARED_SETTINGS[key]["type"] == "boolean":
        return settings.get_bool(full_key)
    return settings.get_string(full_key)


config = McritConfig(VERSION, _get_setting)
