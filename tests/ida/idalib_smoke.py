#!/usr/bin/env python3
"""Live MCRIT integration test executed through IDALib, without Qt."""

# ruff: noqa: I001

from __future__ import annotations

# IDALib requires this to be the first import. Keep all other imports below it.
import idapro

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def _is_live():
    return os.environ.get("MCRIT_IDA_SMOKE_LIVE", "1") == "1"


def _write_report_artifact(report):
    value = os.environ.get("MCRIT_IDA_SMOKE_ARTIFACT_DIR")
    if not value:
        return
    artifact_dir = Path(value).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "idalib-smda.json").write_text(
        json.dumps(report.toDict(), indent=1, sort_keys=True), encoding="utf-8"
    )


def _wait_for_functions(client, sample_id):
    deadline = time.monotonic() + int(os.environ.get("MCRIT_IDA_SMOKE_TIMEOUT", "30"))
    while time.monotonic() < deadline:
        functions = client.getFunctionsBySampleId(sample_id) or []
        if functions:
            return functions
        time.sleep(2)
    raise TimeoutError(f"MCRIT did not process sample {sample_id} before the timeout")


def _matches_sample(matches, sample_id):
    for sample_match in matches.get("samples", []) or []:
        if isinstance(sample_match, dict) and sample_match.get("sample_id") == sample_id:
            return True
    function_summaries = matches.get("functions", {}) or {}
    if isinstance(function_summaries, dict):
        function_summaries = function_summaries.values()
    return any(
        len(match_tuple) > 1 and match_tuple[1] == sample_id
        for summary in function_summaries
        for match_tuple in summary.get("matches", []) or []
    )


def _load_plugin(plugin_root):
    if str(plugin_root) not in sys.path:
        sys.path.insert(0, str(plugin_root))
    qt_modules_before = {name for name in sys.modules if name.startswith(("PySide", "PyQt"))}
    import ida_mcrit

    _assert(
        qt_modules_before == {name for name in sys.modules if name.startswith(("PySide", "PyQt"))},
        "loading the plugin entry point imported a Qt binding under IDALib",
    )
    plugin = ida_mcrit.PLUGIN_ENTRY()
    _assert(plugin.wanted_name == "MCRIT4IDA", "unexpected plugin name")
    plugmod = plugin.init()
    _assert(plugmod is not None, "plugin init returned no plugmod")
    _assert(ida_mcrit.show_mcrit_form() is None, "GUI form unexpectedly opened under IDALib")


def _exercise_live_mcrit():
    import config
    from helpers.HeadlessMcritContext import HeadlessMcritContext

    context = HeadlessMcritContext(config)
    interface = context.mcrit_interface
    client = interface.mcrit_client
    interface.checkConnection(async_=False)
    _assert(
        context.local_widget.server and context.local_widget.server[1], "MCRIT connection failed"
    )

    report = interface.convertIdbToSmda()
    _assert(
        report is not None and list(report.getFunctions()),
        "IDALib conversion produced no functions",
    )
    report.family = "mcrit-plugin-ci"
    report.version = "idalib-query"
    context.local_smda_report = report
    _write_report_artifact(report)

    interface.uploadReport(report)
    _assert(context.remote_sample_id is not None, "MCRIT upload returned no sample id")
    _wait_for_functions(client, context.remote_sample_id)
    interface.querySampleSha256(report.sha256)
    _assert(context.remote_sample_entry is not None, "MCRIT SHA256 lookup returned no sample")
    interface.queryAllFamilyEntries()
    interface.queryAllSampleEntries()
    interface.queryFunctionEntriesBySampleId(context.remote_sample_id)

    job_id = interface.requestMatchingJob(context.remote_sample_id)
    _assert(job_id, "MCRIT matching request returned no job id")
    result = client.awaitResult(job_id, sleep_time=1)
    _assert(isinstance(result, dict), "MCRIT matching result was not a JSON object")
    matches = result.get("matches", {})
    _assert(matches.get("samples") or matches.get("functions"), "MCRIT returned no matches")
    reference_sha256 = os.environ.get("MCRIT_IDA_SMOKE_REFERENCE_SHA256")
    if reference_sha256:
        reference = client.getSampleBySha256(reference_sha256)
        _assert(reference is not None, "MCRIT reference sample was not retrievable")
        _assert(
            _matches_sample(matches, reference.sample_id),
            "MCRIT did not return the deterministic reference match",
        )
    interface.getMatchingJobById(job_id)
    _assert(
        context.matching_report is not None, "MCRIT result retrieval did not decode MatchingResult"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    plugin_root = Path(os.environ["MCRIT_IDA_PLUGIN_ROOT"]).resolve()
    database_open = False
    try:
        idapro.open_database(str(args.input.resolve()), True)
        database_open = True
        _load_plugin(plugin_root)
        if _is_live():
            _exercise_live_mcrit()
        print("MCRIT_IDALIB_SMOKE_OK")
        return 0
    except Exception as exc:
        print(f"MCRIT_IDALIB_SMOKE_FAILURE: {exc}")
        traceback.print_exc()
        return 1
    finally:
        if database_open:
            try:
                idapro.close_database(False)
            except TypeError:
                idapro.close_database()


if __name__ == "__main__":
    raise SystemExit(main())
