"""mcrit_plugin.core must stay free of GUI toolkit imports so non-Qt frontends can reuse it."""

import importlib
import pkgutil
import sys

import mcrit_plugin.core

GUI_MODULES = ("PySide6", "PySide", "PyQt5", "shiboken6")


def _core_module_names():
    for module in pkgutil.walk_packages(mcrit_plugin.core.__path__, "mcrit_plugin.core."):
        if ".minimcrit." in module.name or ".pylev" in module.name:
            continue
        yield module.name


def test_core_modules_import_without_gui_toolkits(monkeypatch):
    for name in list(sys.modules):
        if name.startswith("mcrit_plugin.core") or name.startswith(GUI_MODULES):
            monkeypatch.delitem(sys.modules, name)
    for gui_module in GUI_MODULES:
        # a None entry makes any import of that module raise ImportError
        monkeypatch.setitem(sys.modules, gui_module, None)

    for name in _core_module_names():
        importlib.import_module(name)
