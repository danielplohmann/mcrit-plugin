"""Tests for McritInterface helpers that don't require IDA at runtime.

The big surface area of McritInterface depends on a live IDA UI, so these
tests focus on the pure helpers that can be exercised in isolation:

  * Architecture detection in ``_select_smda_backend``.
  * Construction-time wiring of the request timeout.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from mcrit_plugin.core.McritInterface import McritInterface


class _FakeBinaryInfo:
    """Fake BinaryInfo for testing architecture detection."""

    def __init__(self, architecture):
        """Initialize with an architecture string."""
        self.architecture = architecture


class _FakeSmdaFunction:
    """Fake SmdaFunction for testing."""

    def __init__(self, offset):
        """Initialize with a function offset."""
        self.offset = offset


class _FakeSmdaReport:
    """Fake SmdaReport for testing."""

    def __init__(self, functions):
        """Initialize with a list of functions."""
        self._functions = functions

    def getFunctions(self):
        """Return the list of functions."""
        return self._functions


def _make_interface(timeout=10, sample_group_only=False):
    """Build a McritInterface instance bypassing __init__ to avoid IDA-specific setup.

    Args:
        timeout: MCRIT request timeout in seconds.
        sample_group_only: Whether to restrict to sample group.

    Returns:
        A partially initialized McritInterface for testing.
    """
    inst = McritInterface.__new__(McritInterface)
    inst.parent = SimpleNamespace(
        local_widget=MagicMock(),
        config=SimpleNamespace(
            MCRIT_REQUEST_TIMEOUT=timeout,
            SAMPLE_GROUP_ONLY=sample_group_only,
        ),
        remote_sample_id=23,
        function_matches={},
        function_id_to_offset={},
    )
    inst.config = inst.parent.config
    inst.mcrit_client = MagicMock()
    return inst


@pytest.mark.parametrize(
    "architecture, expected",
    [
        ("x86", "intel"),
        ("X86_64", "intel"),
        ("amd64", "intel"),
        ("i386", "intel"),
        ("intel", "intel"),
        ("AARCH64", "aarch64"),
        ("arm64", "aarch64"),
    ],
)
def test_select_smda_backend_known_arches(architecture, expected):
    interface = _make_interface()
    assert interface._select_smda_backend(_FakeBinaryInfo(architecture)) == expected


@pytest.mark.parametrize("architecture", ["riscv", "arm", "mips", "ppc", "powerpc64", "sparc"])
def test_select_smda_backend_unknown_returns_none(architecture):
    # SMDA only offers intel, aarch64, cil and dalvik; any other name would leave the
    # Disassembler without a backend instead of raising, so it must answer None here.
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


class TestSampleGroupOnly:
    def test_request_matching_job_passes_configured_sample_group_only(self):
        interface = _make_interface(sample_group_only=True)
        interface.mcrit_client.requestMatchesForSample.return_value = "job-1"

        interface.requestMatchingJob(23, force_update=True)

        interface.mcrit_client.requestMatchesForSample.assert_called_once_with(
            23,
            band_matches_required=2,
            force_recalculation=True,
            sample_group_only=True,
        )

    def test_request_matching_job_defaults_sample_group_only_to_false(self):
        interface = _make_interface()
        interface.mcrit_client.requestMatchesForSample.return_value = "job-1"

        interface.requestMatchingJob(23)

        interface.mcrit_client.requestMatchesForSample.assert_called_once_with(
            23,
            band_matches_required=2,
            force_recalculation=False,
            sample_group_only=False,
        )

    def test_query_smda_function_matches_passes_configured_sample_group_only(self):
        interface = _make_interface(sample_group_only=True)
        interface.mcrit_client.getMatchesForSmdaFunction.return_value = None
        smda_report = _FakeSmdaReport([_FakeSmdaFunction(0x401000)])

        interface.querySmdaFunctionMatches(smda_report)

        interface.mcrit_client.getMatchesForSmdaFunction.assert_called_once_with(
            smda_report,
            exclude_self_matches=False,
            sample_group_only=True,
        )
