import os
import json
import logging
import ida_settings
import helpers.McritTableColumn as McritTableColumn

# --- Settings Wrapper ---
class SettingsWrapper:
    def __init__(self):
        self._defaults = {
            "mcritweb_username": "",
            "mcrit_server": "http://127.0.0.1:8000/",
            "mcritweb_api_token": "",
            "auto_analyze_smda_on_startup": False,
            "use_smda_for_analysis": False,
            "submit_function_names_on_close": False,
            "blocks_filter_library_functions": False,
            "blocks_live_query": False,
            "blocks_min_size": 4,
            "function_filter_library_functions": False,
            "function_live_query": False,
            "function_min_score": 50,
            "overview_fetch_labels_automatically": False,
            "overview_filter_to_labels": False,
            "overview_filter_to_conflicts": False,
            "overview_min_score": 50
        }
        # a little developer convenience to override settings without messing with IDA settings
        CONFIG_FILE_PATH = os.path.abspath(__file__)
        PROJECT_ROOT = os.path.dirname(CONFIG_FILE_PATH)
        if os.path.exists(PROJECT_ROOT + os.sep  + "config_override.json"):
            try:
                with open(PROJECT_ROOT + os.sep  + "config_override.json", "r") as override_file:
                    override_settings = json.load(override_file)
                    for key in self._defaults.keys():
                        self._defaults[key] = override_settings.get(key, self._defaults[key])
            except (json.JSONDecodeError, IOError):
                pass

    def _get(self, key):
        try:
            return ida_settings.get_current_plugin_setting(key)
        except (KeyError, AttributeError, ValueError, TypeError, RuntimeError):
            return self._defaults.get(key)

    @property
    def MCRITWEB_USERNAME(self):
        return self._get("mcritweb_username")

    @property
    def MCRIT_SERVER(self):
        return self._get("mcrit_server")

    @property
    def MCRITWEB_API_TOKEN(self):
        return self._get("mcritweb_api_token")

    @property
    def AUTO_ANALYZE_SMDA_ON_STARTUP(self):
        return self._get("auto_analyze_smda_on_startup")

    @property
    def USE_SMDA_FOR_ANALYSIS(self):
        return self._get("use_smda_for_analysis")

    @property
    def SUBMIT_FUNCTION_NAMES_ON_CLOSE(self):
        return self._get("submit_function_names_on_close")

    # Widget specific settings
    @property
    def BLOCKS_FILTER_LIBRARY_FUNCTIONS(self):
        return self._get("blocks_filter_library_functions")

    @property
    def BLOCKS_LIVE_QUERY(self):
        return self._get("blocks_live_query")

    @property
    def BLOCKS_MIN_SIZE(self):
        value = self._get("blocks_min_size")
        try:
            return int(value) if not isinstance(value, int) else value
        except (ValueError, TypeError):
            return 4

    @property
    def FUNCTION_FILTER_LIBRARY_FUNCTIONS(self):
        return self._get("function_filter_library_functions")

    @property
    def FUNCTION_LIVE_QUERY(self):
        return self._get("function_live_query")

    @property
    def FUNCTION_MIN_SCORE(self):
        value = self._get("function_min_score")
        try:
            return int(value) if not isinstance(value, int) else value
        except (ValueError, TypeError):
            return 50

    @property
    def OVERVIEW_FETCH_LABELS_AUTOMATICALLY(self):
        return self._get("overview_fetch_labels_automatically")

    @property
    def OVERVIEW_FILTER_TO_LABELS(self):
        return self._get("overview_filter_to_labels")

    @property
    def OVERVIEW_FILTER_TO_CONFLICTS(self):
        return self._get("overview_filter_to_conflicts")

    @property
    def OVERVIEW_MIN_SCORE(self):
        value = self._get("overview_min_score")
        try:
            return int(value) if not isinstance(value, int) else value
        except (ValueError, TypeError):
            return 50

settings = SettingsWrapper()


# --- Original Config Constants ---
VERSION = "1.1.0"
# relevant paths
CONFIG_FILE_PATH = os.path.abspath(__file__)
PROJECT_ROOT = os.path.dirname(CONFIG_FILE_PATH)
# PLUGINS_ROOT = str(os.path.abspath(os.sep.join([PROJECT_ROOT, ".."]))) # No longer needed as icons are inside
ICON_FILE_PATH = os.path.join(PROJECT_ROOT, "icons") + os.sep

### Configuration of Logging
LOG_PATH = "./"
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)-15s: %(name)-25s: %(message)s"
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)

MCRIT4IDA_PLUGIN_ONLY = False

# Proxy properties to settings wrapper
MCRITWEB_USERNAME = settings.MCRITWEB_USERNAME
MCRIT_SERVER = settings.MCRIT_SERVER
MCRITWEB_API_TOKEN = settings.MCRITWEB_API_TOKEN

### UI behavior configurations
## General behavior
AUTO_ANALYZE_SMDA_ON_STARTUP = settings.AUTO_ANALYZE_SMDA_ON_STARTUP
USE_SMDA_FOR_ANALYSIS = settings.USE_SMDA_FOR_ANALYSIS
SUBMIT_FUNCTION_NAMES_ON_CLOSE = settings.SUBMIT_FUNCTION_NAMES_ON_CLOSE

## Widget specific behavior
# Block Scope Widget
BLOCKS_FILTER_LIBRARY_FUNCTIONS = settings.BLOCKS_FILTER_LIBRARY_FUNCTIONS
BLOCKS_LIVE_QUERY = settings.BLOCKS_LIVE_QUERY
BLOCKS_MIN_SIZE = settings.BLOCKS_MIN_SIZE
#
BLOCK_SUMMARY_TABLE_COLUMNS = [
    McritTableColumn.OFFSET,
    McritTableColumn.PIC_BLOCK_HASH,
    McritTableColumn.SIZE,
    McritTableColumn.FAMILIES,
    McritTableColumn.SAMPLES,
    McritTableColumn.FUNCTIONS,
    McritTableColumn.IS_LIBRARY,
]
BLOCK_MATCHES_TABLE_COLUMNS = [
    McritTableColumn.FAMILY_NAME,
    McritTableColumn.FAMILY_ID,
    McritTableColumn.SAMPLE_ID,
    McritTableColumn.FUNCTION_ID,
    McritTableColumn.OFFSET,
    # McritTableColumn.SHA256,
]
# Function Scope Widget
FUNCTION_FILTER_LIBRARY_FUNCTIONS = settings.FUNCTION_FILTER_LIBRARY_FUNCTIONS
FUNCTION_LIVE_QUERY = settings.FUNCTION_LIVE_QUERY
FUNCTION_MIN_SCORE = settings.FUNCTION_MIN_SCORE
#
FUNCTION_MATCHES_TABLE_COLUMNS = [
    McritTableColumn.SCORE,
    McritTableColumn.SHA256,
    # McritTableColumn.OFFSET,
    McritTableColumn.FAMILY_NAME,
    McritTableColumn.VERSION,
    McritTableColumn.SAMPLE_ID,
    McritTableColumn.FUNCTION_ID,
    McritTableColumn.PIC_HASH_MATCH,
    McritTableColumn.IS_LIBRARY,
]
FUNCTION_NAMES_TABLE_COLUMNS = [
    McritTableColumn.FUNCTION_ID,
    McritTableColumn.SCORE,
    McritTableColumn.USER,
    McritTableColumn.FUNCTION_LABEL,
    # McritTableColumn.TIMESTAMP,
]
# Function Overview Widget
OVERVIEW_FETCH_LABELS_AUTOMATICALLY = settings.OVERVIEW_FETCH_LABELS_AUTOMATICALLY
OVERVIEW_FILTER_TO_LABELS = settings.OVERVIEW_FILTER_TO_LABELS
OVERVIEW_FILTER_TO_CONFLICTS = settings.OVERVIEW_FILTER_TO_CONFLICTS
OVERVIEW_MIN_SCORE = settings.OVERVIEW_MIN_SCORE
#
OVERVIEW_TABLE_COLUMNS = [
    McritTableColumn.OFFSET,
    McritTableColumn.FAMILIES,
    McritTableColumn.SAMPLES,
    McritTableColumn.FUNCTIONS,
    McritTableColumn.IS_LIBRARY,
    McritTableColumn.SCORE_AND_LABEL,
]
