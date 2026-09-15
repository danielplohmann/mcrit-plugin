import ida_settings

from mcrit_plugin.core.config import McritConfig

VERSION = "1.1.9"
MCRIT4IDA_PLUGIN_ONLY = False

config = McritConfig(VERSION, ida_settings.get_current_plugin_setting)
