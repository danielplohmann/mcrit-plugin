import json
import logging
import os
import sys

import ida_settings

import helpers.McritTableColumn as McritTableColumn


# --- Settings Wrapper ---
class SettingsWrapper:
    """Wrapper around ida_settings that coerces types and provides defaults."""

    def __init__(self):
        """Initialize the wrapper with default settings values."""
        self._defaults = {
            "mcritweb_username": "",
            "mcrit_server": "http://127.0.0.1:8000/",
            "mcritweb_api_token": "",
            "mcrit_request_timeout": "10",
            "sample_group_only": False,
            "auto_analyze_smda_on_startup": False,
            "use_smda_for_analysis": False,
            "submit_function_names_on_close": False,
            "blocks_filter_library_functions": False,
            "blocks_live_query": False,
            "blocks_min_size": "4",
            "function_filter_library_functions": False,
            "function_live_query": False,
            "function_min_score": "50",
            "overview_fetch_labels_automatically": False,
            "overview_filter_to_labels": False,
            "overview_filter_to_conflicts": False,
            "overview_min_score": "50",
        }
        # a little developer convenience to override settings without messing with IDA settings
        CONFIG_FILE_PATH = os.path.abspath(__file__)
        PROJECT_ROOT = os.path.dirname(CONFIG_FILE_PATH)
        if os.path.exists(PROJECT_ROOT + os.sep + "config_override.json"):
            try:
                with open(PROJECT_ROOT + os.sep + "config_override.json", "r") as override_file:
                    override_settings = json.load(override_file)
                    for key in self._defaults.keys():
                        self._defaults[key] = override_settings.get(key, self._defaults[key])
            except (json.JSONDecodeError, IOError):
                pass

    def _get(self, key):
        """Get a setting from IDA settings, falling back to defaults on error.

        Args:
            key: Setting key to retrieve.

        Returns:
            The setting value or its default.
        """
        try:
            return ida_settings.get_current_plugin_setting(key)
        except (KeyError, AttributeError, ValueError, TypeError, RuntimeError):
            return self._defaults.get(key)

    def _get_bool(self, key):
        """Get a setting and coerce it to boolean.

        Args:
            key: Setting key to retrieve.

        Returns:
            Boolean value of the setting.
        """
        value = self._get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @property
    def MCRITWEB_USERNAME(self):
        """MCRITWeb username for authentication."""
        return self._get("mcritweb_username")

    @property
    def MCRIT_SERVER(self):
        """URL of the MCRIT server."""
        return self._get("mcrit_server")

    @property
    def MCRITWEB_API_TOKEN(self):
        """API token for MCRITWeb authentication."""
        return self._get("mcritweb_api_token")

    @property
    def MCRIT_REQUEST_TIMEOUT(self):
        """Timeout in seconds for MCRIT API requests."""
        value = self._get("mcrit_request_timeout")
        try:
            return int(value)
        except (ValueError, TypeError):
            return 10

    @property
    def SAMPLE_GROUP_ONLY(self):
        """Restrict matching results to samples in the current sample group."""
        return self._get_bool("sample_group_only")

    @property
    def AUTO_ANALYZE_SMDA_ON_STARTUP(self):
        """Auto-convert IDB to SMDA representation on plugin startup."""
        return self._get("auto_analyze_smda_on_startup")

    @property
    def USE_SMDA_FOR_ANALYSIS(self):
        """Use SMDA backend for code analysis instead of IDA's engine."""
        return self._get("use_smda_for_analysis")

    @property
    def SUBMIT_FUNCTION_NAMES_ON_CLOSE(self):
        """Submit updated function names to MCRIT on IDB close."""
        return self._get("submit_function_names_on_close")

    # Widget specific settings
    @property
    def BLOCKS_FILTER_LIBRARY_FUNCTIONS(self):
        """Filter out library functions in Block Scope Widget."""
        return self._get("blocks_filter_library_functions")

    @property
    def BLOCKS_LIVE_QUERY(self):
        """Enable live query updates in Block Scope Widget."""
        return self._get("blocks_live_query")

    @property
    def BLOCKS_MIN_SIZE(self):
        """Minimum block size for Block Scope Widget analysis."""
        value = self._get("blocks_min_size")
        try:
            return int(value) if not isinstance(value, int) else value
        except (ValueError, TypeError):
            return 4

    @property
    def FUNCTION_FILTER_LIBRARY_FUNCTIONS(self):
        """Filter out library functions in Function Scope Widget."""
        return self._get("function_filter_library_functions")

    @property
    def FUNCTION_LIVE_QUERY(self):
        """Enable live query updates in Function Scope Widget."""
        return self._get("function_live_query")

    @property
    def FUNCTION_MIN_SCORE(self):
        """Minimum match score for Function Scope Widget."""
        value = self._get("function_min_score")
        try:
            return int(value) if not isinstance(value, int) else value
        except (ValueError, TypeError):
            return 50

    @property
    def OVERVIEW_FETCH_LABELS_AUTOMATICALLY(self):
        """Auto-fetch labels in Function Overview Widget."""
        return self._get("overview_fetch_labels_automatically")

    @property
    def OVERVIEW_FILTER_TO_LABELS(self):
        """Filter to labeled functions in Function Overview Widget."""
        return self._get("overview_filter_to_labels")

    @property
    def OVERVIEW_FILTER_TO_CONFLICTS(self):
        """Filter to conflicting labels in Function Overview Widget."""
        return self._get("overview_filter_to_conflicts")

    @property
    def OVERVIEW_MIN_SCORE(self):
        """Minimum match score for Function Overview Widget."""
        value = self._get("overview_min_score")
        try:
            return int(value) if not isinstance(value, int) else value
        except (ValueError, TypeError):
            return 50


settings = SettingsWrapper()


# --- Original Config Constants ---
VERSION = "1.1.8"
# relevant paths
CONFIG_FILE_PATH = os.path.abspath(__file__)
PROJECT_ROOT = os.path.dirname(CONFIG_FILE_PATH)
# PLUGINS_ROOT = str(os.path.abspath(os.sep.join([PROJECT_ROOT, ".."]))) # No longer needed as icons are inside
ICON_FILE_PATH = os.path.join(PROJECT_ROOT, "icons") + os.sep

### Configuration of Logging
LOG_PATH = "./"
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)-15s: %(name)-25s: %(message)s"


def _configure_plugin_loggers():
    """Keep plugin-related logs from inheriting another IDA plugin's root formatter."""
    formatter = logging.Formatter("%(asctime)-15s: %(name)-32s - %(levelname)s: %(message)s")
    for logger_name in ("helpers.minimcrit", "smda"):
        logger = logging.getLogger(logger_name)
        logger.setLevel(LOG_LEVEL)
        logger.propagate = False
        if any(getattr(handler, "_mcrit4ida_handler", False) for handler in logger.handlers):
            continue
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(LOG_LEVEL)
        handler.setFormatter(formatter)
        handler._mcrit4ida_handler = True
        logger.addHandler(handler)


_configure_plugin_loggers()

MCRIT4IDA_PLUGIN_ONLY = False

# Proxy properties to settings wrapper
MCRITWEB_USERNAME = settings.MCRITWEB_USERNAME
MCRIT_SERVER = settings.MCRIT_SERVER
MCRITWEB_API_TOKEN = settings.MCRITWEB_API_TOKEN
MCRIT_REQUEST_TIMEOUT = settings.MCRIT_REQUEST_TIMEOUT
SAMPLE_GROUP_ONLY = settings.SAMPLE_GROUP_ONLY

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
