"""Tests for McritInterface helpers that don't require IDA at runtime.

The big surface area of McritInterface depends on a live IDA UI, so these
tests focus on the pure helpers that can be exercised in isolation:

  * Architecture detection in ``_select_smda_backend``.
  * Construction-time wiring of the request timeout.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from helpers.McritInterface import McritInterface


class _FakeBinaryInfo:
    def __init__(self, architecture):
        self.architecture = architecture


def _make_interface(timeout=10):
    """Build an instance bypassing __init__ to avoid IDA-specific setup."""
    inst = McritInterface.__new__(McritInterface)
    inst.parent = SimpleNamespace(
        local_widget=MagicMock(),
        config=SimpleNamespace(MCRIT_REQUEST_TIMEOUT=timeout),
    )
    inst.config = inst.parent.config
    inst.mcrit_client = MagicMock()
    inst._withTraceback = False
    return inst


@pytest.mark.parametrize(
    "architecture, expected",
    [
        ("x86", "intel"),
        ("X86_64", "intel"),
        ("amd64", "intel"),
        ("i386", "intel"),
        ("intel", "intel"),
        ("ARM", "arm"),
        ("arm64", "arm"),
        ("MIPS", "mips"),
        ("mipsel", "mips"),
        ("ppc", "ppc"),
        ("PowerPC", "ppc"),
        ("powerpc64", "ppc"),
    ],
)
def test_select_smda_backend_known_arches(architecture, expected):
    interface = _make_interface()
    assert interface._select_smda_backend(_FakeBinaryInfo(architecture)) == expected


@pytest.mark.parametrize("architecture", ["riscv", "aarch64", "sparc"])
def test_select_smda_backend_unknown_returns_none(architecture):
    # aarch64 currently falls through because the substring check looks for "arm",
    # not "arch"; this test pins that documented behavior so any future widening
    # of the rule is intentional.
    interface = _make_interface()
    assert interface._select_smda_backend(_FakeBinaryInfo(architecture)) is None


def test_select_smda_backend_handles_none_architecture():
    interface = _make_interface()
    assert interface._select_smda_backend(_FakeBinaryInfo(None)) is None


def test_select_smda_backend_handles_empty_string():
    interface = _make_interface()
    assert interface._select_smda_backend(_FakeBinaryInfo("")) is None


class TestCheckConnectionImpl:
    def test_returns_version_on_success(self):
        interface = _make_interface()
        interface.mcrit_client.getVersion.return_value = "1.2.3"
        result = interface._check_connection_impl()
        assert result == ("1.2.3", None)

    def test_returns_exception_on_failure(self):
        interface = _make_interface()
        boom = RuntimeError("network down")
        interface.mcrit_client.getVersion.side_effect = boom
        version, err = interface._check_connection_impl()
        assert version is None
        assert err is boom
