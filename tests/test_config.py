"""Tests for the SettingsWrapper in config.py.

The wrapper coerces strings coming from IDA's settings store into the right
Python types and substitutes a sane default if coercion fails. These tests
pin those rules so a future refactor can't silently regress them.
"""

import importlib
import sys
from unittest.mock import patch

import pytest


def _reload_config():
    if "config" in sys.modules:
        del sys.modules["config"]
    return importlib.import_module("config")


@pytest.fixture
def fresh_config():
    return _reload_config()


def test_mcrit_request_timeout_default(fresh_config):
    settings = fresh_config.SettingsWrapper()
    assert settings.MCRIT_REQUEST_TIMEOUT == 10


@pytest.mark.parametrize(
    "raw_value, expected",
    [
        ("15", 15),
        (20, 20),
        ("0", 0),
    ],
)
def test_mcrit_request_timeout_valid_coercions(fresh_config, raw_value, expected):
    settings = fresh_config.SettingsWrapper()
    with patch.object(settings, "_get", return_value=raw_value):
        assert settings.MCRIT_REQUEST_TIMEOUT == expected


@pytest.mark.parametrize(
    "raw_value",
    [
        "not-a-number",
        None,
        object(),
    ],
)
def test_mcrit_request_timeout_invalid_falls_back_to_default(fresh_config, raw_value):
    settings = fresh_config.SettingsWrapper()
    with patch.object(settings, "_get", return_value=raw_value):
        assert settings.MCRIT_REQUEST_TIMEOUT == 10


def test_sample_group_only_default(fresh_config):
    settings = fresh_config.SettingsWrapper()
    assert settings.SAMPLE_GROUP_ONLY is False


@pytest.mark.parametrize(
    "raw_value, expected",
    [
        (False, False),
        (True, True),
        ("false", False),
        ("False", False),
        ("0", False),
        ("true", True),
        ("yes", True),
        (1, True),
    ],
)
def test_sample_group_only_coerces_setting_value(fresh_config, raw_value, expected):
    settings = fresh_config.SettingsWrapper()
    with patch.object(settings, "_get", return_value=raw_value):
        assert settings.SAMPLE_GROUP_ONLY is expected


def test_blocks_min_size_default(fresh_config):
    settings = fresh_config.SettingsWrapper()
    assert settings.BLOCKS_MIN_SIZE == 4


def test_blocks_min_size_string_coerced(fresh_config):
    settings = fresh_config.SettingsWrapper()
    with patch.object(settings, "_get", return_value="8"):
        assert settings.BLOCKS_MIN_SIZE == 8


def test_blocks_min_size_invalid_falls_back(fresh_config):
    settings = fresh_config.SettingsWrapper()
    with patch.object(settings, "_get", return_value="bogus"):
        assert settings.BLOCKS_MIN_SIZE == 4


def test_function_min_score_default(fresh_config):
    settings = fresh_config.SettingsWrapper()
    assert settings.FUNCTION_MIN_SCORE == 50


def test_overview_min_score_default(fresh_config):
    settings = fresh_config.SettingsWrapper()
    assert settings.OVERVIEW_MIN_SCORE == 50


def test_version_constant_exists_and_is_string(fresh_config):
    assert isinstance(fresh_config.VERSION, str)
    assert fresh_config.VERSION  # non-empty


def test_version_matches_ida_plugin_json():
    """ida-plugin.json and config.VERSION must agree on the plugin version."""
    import json
    import os

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    with open(os.path.join(project_root, "ida-plugin.json"), "r") as fh:
        manifest = json.load(fh)
    config = _reload_config()
    assert manifest["plugin"]["version"] == config.VERSION


def test_manifest_declares_sample_group_only_setting():
    import json
    import os

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    with open(os.path.join(project_root, "ida-plugin.json"), "r") as fh:
        manifest = json.load(fh)

    settings = {setting["key"]: setting for setting in manifest["plugin"]["settings"]}
    assert settings["sample_group_only"]["type"] == "boolean"
    assert settings["sample_group_only"]["default"] is False


def test_override_template_declares_sample_group_only_default():
    import json
    import os

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    with open(os.path.join(project_root, "config_override.json.template"), "r") as fh:
        override_template = json.load(fh)

    assert override_template["sample_group_only"] is False
