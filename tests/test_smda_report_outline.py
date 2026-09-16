"""Regression tests for the per-query SMDA report outline.

SMDA 4.8 memoises `SmdaReport.getFunctions()`, so reusing one outline object and only
swapping its `xcfg` makes every query after the first look at the first function again.
"""

import importlib
import sys
import types

import pytest


class _PluginT:
    """Minimal plugin base class for import-time stubs."""


class _PlugmodT:
    """Minimal plugmod base class for import-time stubs."""


class _PluginForm:
    """Minimal plugin form base class for import-time stubs."""


class _ViewHooks:
    """Minimal view hooks base class for import-time stubs."""


class _CachingSmdaReport:
    """SmdaReport stand-in with SMDA >= 4.8 `getFunctions()` caching semantics."""

    def __init__(self, xcfg=None, sha256="a" * 64):
        self.xcfg = xcfg or {}
        self.sha256 = sha256
        self._sorted_functions = None

    @classmethod
    def fromDict(cls, data):
        report = cls(data.get("xcfg"), data.get("sha256"))
        report._source = data
        return report

    def toDict(self):
        return {"xcfg": dict(self.xcfg), "sha256": self.sha256}

    def getFunctions(self):
        if self._sorted_functions is None:
            self._sorted_functions = (
                [function for _, function in sorted(self.xcfg.items())] if self.xcfg else []
            )
        yield from self._sorted_functions


@pytest.fixture
def outline_getter(monkeypatch):
    """The bare `getLocalSmdaReportOutline` method plus a caching SmdaReport."""
    monkeypatch.setitem(
        sys.modules,
        "ida_idaapi",
        types.SimpleNamespace(plugin_t=_PluginT, plugmod_t=_PlugmodT, PLUGIN_MULTI=1),
    )
    monkeypatch.setitem(
        sys.modules,
        "ida_kernwin",
        types.SimpleNamespace(PluginForm=_PluginForm, is_idaq=lambda: False),
    )
    monkeypatch.setitem(sys.modules, "idaapi", types.SimpleNamespace(View_Hooks=_ViewHooks))
    monkeypatch.delitem(sys.modules, "ida_mcrit", raising=False)

    ida_mcrit = importlib.import_module("ida_mcrit")
    monkeypatch.setattr(ida_mcrit, "SmdaReport", _CachingSmdaReport)
    return ida_mcrit.Mcrit4IdaForm.getLocalSmdaReportOutline


def _make_form(local_report):
    return types.SimpleNamespace(
        local_smda_report=local_report,
        local_smda_report_outline=None,
        _outline_source=None,
    )


def test_outline_is_a_fresh_report_per_query(outline_getter):
    """Each call yields an outline whose getFunctions() reflects its own xcfg."""
    local_report = _CachingSmdaReport({0x1000: "func_a", 0x2000: "func_b"})
    form = _make_form(local_report)

    first = outline_getter(form)
    first.xcfg = {0x1000: "func_a"}
    assert list(first.getFunctions()) == ["func_a"]

    second = outline_getter(form)
    second.xcfg = {0x2000: "func_b"}
    assert list(second.getFunctions()) == ["func_b"]

    assert first is not second


def test_outline_carries_no_functions(outline_getter):
    """The outline drops xcfg so only the caller's function is submitted."""
    local_report = _CachingSmdaReport({0x1000: "func_a", 0x2000: "func_b"})
    form = _make_form(local_report)

    outline = outline_getter(form)

    assert outline.xcfg == {}
    assert list(outline.getFunctions()) == []


def test_outline_follows_a_replaced_local_report(outline_getter):
    """Uploading on close swaps local_smda_report, and the outline must not stay on the old one."""
    form = _make_form(_CachingSmdaReport({0x1000: "func_a"}, sha256="b" * 64))
    outline_getter(form)

    form.local_smda_report = _CachingSmdaReport({0x3000: "func_c"}, sha256="c" * 64)
    refreshed = outline_getter(form)
    refreshed.xcfg = {0x3000: "func_c"}

    assert refreshed.sha256 == "c" * 64
    assert list(refreshed.getFunctions()) == ["func_c"]


def test_outline_is_none_without_a_local_report(outline_getter):
    """No local report means no outline, rather than an AttributeError."""
    assert outline_getter(_make_form(None)) is None
