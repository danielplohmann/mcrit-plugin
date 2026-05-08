"""Test bootstrap that stubs IDA/SMDA modules so the plugin code is importable."""

import os
import sys
import types

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _make_module(name, **attrs):
    module = types.ModuleType(name)
    for attr_name, attr_value in attrs.items():
        setattr(module, attr_name, attr_value)
    sys.modules[name] = module
    return module


# Stub `smda` and its submodules used at import time by the plugin helpers.
class _StubSmdaReport:
    @classmethod
    def fromDict(cls, data):
        instance = cls()
        instance._data = data
        return instance

    def toDict(self):
        return getattr(self, "_data", {})

    def getFunctions(self):
        return []


class _StubSmdaFunction:
    pass


class _StubBinaryInfo:
    def __init__(self, *args, **kwargs):
        self.architecture = ""
        self.base_addr = 0
        self.bitness = 32


class _StubDisassembler:
    def __init__(self, backend=None, *args, **kwargs):
        self.backend = backend

    def _disassemble(self, *args, **kwargs):
        return _StubSmdaReport()

    def disassembleBuffer(self, *args, **kwargs):
        return _StubSmdaReport()


class _StubIntelInstructionEscaper:
    pass


class _StubIdaInterface:
    def __init__(self, *args, **kwargs):
        pass

    def getBinary(self):
        return b""

    def getArchitecture(self):
        return ""

    def getBaseAddr(self):
        return 0

    def getBitness(self):
        return 32

    def getFunctionSymbols(self):
        return {}


_make_module("smda")
_make_module("smda.common")
_make_module("smda.common.SmdaReport", SmdaReport=_StubSmdaReport)
_make_module("smda.common.SmdaFunction", SmdaFunction=_StubSmdaFunction)
_make_module("smda.common.BinaryInfo", BinaryInfo=_StubBinaryInfo)
_make_module("smda.Disassembler", Disassembler=_StubDisassembler)
_make_module("smda.ida")
_make_module("smda.ida.IdaInterface", IdaInterface=_StubIdaInterface)
_make_module("smda.intel")
_make_module(
    "smda.intel.IntelInstructionEscaper",
    IntelInstructionEscaper=_StubIntelInstructionEscaper,
)


# Stub `ida_settings` so config.py imports succeed.
def _ida_get_current_plugin_setting(key):
    raise KeyError(key)


_make_module("ida_settings", get_current_plugin_setting=_ida_get_current_plugin_setting)
