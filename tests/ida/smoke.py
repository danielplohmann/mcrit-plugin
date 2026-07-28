#!/usr/bin/env python3
"""Headless IDA test for the installed MCRIT4IDA plugin.

This intentionally drives the same Qt actions and signals a user would use in
IDA.  The only adapters are deterministic answers for modal dialogs and the
IDA graph window, which cannot be interacted with in a headless process.
"""

from __future__ import annotations

import datetime
import importlib
import json
import os
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

PLUGIN_ROOT = Path(os.environ["MCRIT_IDA_PLUGIN_ROOT"]).resolve()
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def _is_live() -> bool:
    return os.environ.get("MCRIT_IDA_SMOKE_LIVE", "1") == "1"


def _qexit(code: int) -> None:
    try:
        import ida_pro

        ida_pro.qexit(code)
    except Exception:
        import idaapi

        idaapi.qexit(code)


def _artifact_dir():
    value = os.environ.get("MCRIT_IDA_SMOKE_ARTIFACT_DIR")
    if not value:
        return None
    artifact_dir = Path(value).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    return artifact_dir


def _write_report_artifact(report, filename="generated-smda.json"):
    artifact_dir = _artifact_dir()
    if artifact_dir is None:
        return
    with (artifact_dir / filename).open("w", encoding="utf-8") as output:
        json.dump(report.toDict(), output, indent=1, sort_keys=True)


def _process_events(qt_application, rounds=1):
    for _ in range(rounds):
        qt_application.processEvents()


def _emit_table_signal(table, signal_name, row=0, column=0):
    index = table.model().index(row, column)
    getattr(table, signal_name).emit(index)


def _wait_for_functions(client, sample_id, qt_application=None):
    timeout = int(os.environ.get("MCRIT_IDA_SMOKE_TIMEOUT", "30"))
    deadline = time.monotonic() + timeout
    last_functions = None
    while time.monotonic() < deadline:
        last_functions = client.getFunctionsBySampleId(sample_id) or []
        if last_functions:
            return last_functions
        if qt_application is not None:
            _process_events(qt_application)
        time.sleep(2)
    raise TimeoutError(
        f"MCRIT did not finish processing query sample {sample_id} "
        f"within {timeout}s (functions={last_functions!r})"
    )


def _matches_sample(matches, sample_id):
    for sample_match in matches.get("samples", []) or []:
        if isinstance(sample_match, dict) and sample_match.get("sample_id") == sample_id:
            return True

    function_summaries = matches.get("functions", {}) or {}
    if isinstance(function_summaries, dict):
        function_summaries = function_summaries.values()
    for function_summary in function_summaries:
        for match_tuple in function_summary.get("matches", []) or []:
            if len(match_tuple) > 1 and match_tuple[1] == sample_id:
                return True
    return False


def _run_plugin_lifecycle(module):
    plugin = module.PLUGIN_ENTRY()
    _assert(plugin.wanted_name == "MCRIT4IDA", "unexpected plugin name")
    _assert(plugin.wanted_hotkey == "Ctrl-F4", "unexpected plugin hotkey")
    plugmod = plugin.init()
    _assert(plugmod is not None, "plugin init returned no plugmod")

    original_show = module.show_mcrit_form
    sentinel = object()
    module.show_mcrit_form = lambda: sentinel
    try:
        _assert(plugmod.run(0) is True, "plugmod.run did not succeed")
        _assert(plugmod.form is sentinel, "plugmod.run did not retain the form")
    finally:
        module.show_mcrit_form = original_show
    return plugin, plugmod


def _create_form(module):
    import helpers.QtShim as QtShim

    qt_widgets = QtShim.get_QtWidgets()
    qt_application = qt_widgets.QApplication.instance()
    if qt_application is None:
        qt_application = qt_widgets.QApplication([])

    form = module.Mcrit4IdaForm()
    form.parent = qt_widgets.QWidget()
    form.setupWidgets()
    _process_events(qt_application, rounds=2)
    return form, qt_application


@contextmanager
def _smda_info_adapter(main_widget, family="mcrit-plugin-ci", version="fixture-query"):
    original_dialog = main_widget.SmdaInfoDialog
    base_dialog = original_dialog

    class DeterministicSmdaInfoDialog(base_dialog):
        def exec_(self):
            self.edit_family.setText(family)
            self.edit_version.setText(version)
            self._cb_is_library.setChecked(False)
            self.ok_button.click()
            return 1

    main_widget.SmdaInfoDialog = DeterministicSmdaInfoDialog
    try:
        yield
    finally:
        main_widget.SmdaInfoDialog = original_dialog


@contextmanager
def _result_dialog_adapter(main_widget, mode, target_job_id=None):
    original_dialog = main_widget.ResultChooserDialog
    base_dialog = original_dialog
    target_text = str(target_job_id) if target_job_id is not None else None

    class DeterministicResultChooserDialog(base_dialog):
        def exec_(self):
            if mode == "request":
                self.create_button.click()
                return 1

            _assert(self.job_infos, "result chooser had no jobs for selection")
            selected_row = None
            for row, job_info in enumerate(self.job_infos):
                if str(job_info.job_id) == target_text:
                    selected_row = row
                    break
            _assert(selected_row is not None, f"matching job {target_text} was not listed")
            self.table_jobs.selectRow(selected_row)
            self.select_button.click()
            return 1

    main_widget.ResultChooserDialog = DeterministicResultChooserDialog
    try:
        yield
    finally:
        main_widget.ResultChooserDialog = original_dialog


@contextmanager
def _capture_graph_show(module_name):
    module = importlib.import_module(module_name)
    original_show = module.SmdaGraphViewer.Show
    captured = []

    def capture_show(viewer):
        callback_text = None
        callback_hint = None
        if viewer.smda_function is not None:
            blocks = list(viewer.smda_function.getBlocks())
            if blocks:
                block_offset = blocks[0].offset
                viewer._offset_to_node_id = {block_offset: 0}
                viewer._node_id_to_offset = {0: block_offset}
                callback_text = viewer.OnGetText(0)
                callback_hint = viewer.OnHint(0)
        captured.append((viewer, callback_text, callback_hint))
        return True

    module.SmdaGraphViewer.Show = capture_show
    try:
        yield captured
    finally:
        module.SmdaGraphViewer.Show = original_show


@contextmanager
def _ida_cursor(form, instruction):
    import ida_kernwin

    original_screen_ea = ida_kernwin.get_screen_ea
    ida_kernwin.get_screen_ea = lambda: instruction.offset
    proxy = form.cc.ida_proxy
    proxy_attributes = {
        "ReadSelectionStart": getattr(proxy, "ReadSelectionStart", None),
        "ReadSelectionEnd": getattr(proxy, "ReadSelectionEnd", None),
        "GetBytes": getattr(proxy, "GetBytes", None),
    }
    proxy.ReadSelectionStart = lambda: instruction.offset
    proxy.ReadSelectionEnd = lambda: instruction.offset + 1
    proxy.GetBytes = lambda *_args: b"\x90"
    try:
        yield
    finally:
        ida_kernwin.get_screen_ea = original_screen_ea
        for name, value in proxy_attributes.items():
            setattr(proxy, name, value)


def _exercise_yara_action(form, report, qt_application):
    main_widget = form.main_widget
    function = max(report.getFunctions(), key=lambda item: item.num_instructions)
    instructions = list(function.getInstructions())
    _assert(instructions, "SMDA report has no instructions for YARA test")
    instruction = instructions[0]

    yara_module = importlib.import_module("widgets.YaraStringBuilderDialog")
    original_copy = yara_module.pyperclip.copy
    original_dialog = main_widget.YaraStringBuilderDialog
    created_dialogs = []
    copied_values = []
    yara_module.pyperclip.copy = lambda value: copied_values.append(value)

    class AutoAcceptYaraDialog(original_dialog):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            created_dialogs.append(self)

        def exec_(self):
            if self.radio_block.isEnabled():
                self.radio_block.click()
            if self.radio_function.isEnabled():
                self.radio_function.click()
            self.cb_wildcards.click()
            self.copy_escaped_button.click()
            self.copy_yara_button.click()
            self.ok_button.click()
            return 1

    main_widget.YaraStringBuilderDialog = AutoAcceptYaraDialog
    try:
        with _ida_cursor(form, instruction):
            main_widget.buildYaraStringAction.trigger()
    finally:
        main_widget.YaraStringBuilderDialog = original_dialog

    _assert(created_dialogs, "YARA toolbar action did not create its dialog")
    _assert("rule " in created_dialogs[0].text_yara.toPlainText(), "YARA action produced no rule")
    _assert(len(copied_values) >= 2, "YARA dialog copy actions were not triggered")

    # Exercise each real scope and both copy buttons on the actual dialog class.
    dialog = original_dialog(
        main_widget,
        selection_sequence=instructions[:1],
        block_sequence=instructions,
        function_sequence=instructions,
        sha256=report.sha256,
        offset=instruction.offset,
        selection_start=instruction.offset,
        selection_end=instruction.offset + 1,
    )
    dialog.radio_selection.click()
    dialog.radio_block.click()
    dialog.radio_function.click()
    dialog.cb_wildcards.click()
    dialog.copy_escaped_button.click()
    dialog.copy_yara_button.click()
    _assert("rule " in dialog.text_yara.toPlainText(), "YARA scope controls produced no rule")
    dialog.ok_button.click()

    data_dialog = original_dialog(
        main_widget,
        data=b"\x90\x90",
        sha256=report.sha256,
        offset=instruction.offset,
        selection_start=instruction.offset,
        selection_end=instruction.offset + 2,
    )
    data_dialog.copy_escaped_button.click()
    data_dialog.copy_yara_button.click()
    _assert("rule " in data_dialog.text_yara.toPlainText(), "YARA data mode produced no rule")
    data_dialog.ok_button.click()
    yara_module.pyperclip.copy = original_copy
    _process_events(qt_application)


def _exercise_function_widget(form, report, qt_application):
    import helpers.McritTableColumn as McritTableColumn

    function_widget = form.function_match_widget
    candidate = max(report.getFunctions(), key=lambda item: item.num_instructions)
    _assert(
        candidate.num_instructions >= 10, "fixture has no function suitable for function queries"
    )
    form.current_function = candidate.offset
    function_widget.last_viewed = None
    function_widget.b_query_single.click()
    _process_events(qt_application, rounds=2)
    _assert(
        function_widget.table_function_matches.rowCount() > 0,
        "Function Scope query returned no rows",
    )

    function_widget.cb_activate_live_tracking.click()
    function_widget.cb_filter_library.click()
    threshold = function_widget.sb_score_threshold.value()
    function_widget.sb_score_threshold.setValue(threshold - 1 if threshold > 50 else threshold + 1)
    _process_events(qt_application, rounds=2)
    _assert(
        function_widget.table_function_matches.rowCount() > 0,
        "Function Scope controls removed all positive matches",
    )

    copied_sha256 = []
    original_copy = form.copyStringToClipboard
    form.copyStringToClipboard = lambda value: copied_sha256.append(value)
    try:
        sha_column = McritTableColumn.columnTypeToIndex(
            McritTableColumn.SHA256, form.config.FUNCTION_MATCHES_TABLE_COLUMNS
        )
        _assert(sha_column is not None, "Function Scope SHA256 column is not configured")
        function_widget.table_function_matches.setCurrentCell(0, sha_column)
        function_widget.table_function_matches.customContextMenuRequested.emit(
            form.cc.QtCore.QPoint(0, 0)
        )
    finally:
        form.copyStringToClipboard = original_copy
    _assert(copied_sha256, "Function Scope SHA256 context action did not copy a value")

    with _capture_graph_show("widgets.FunctionMatchWidget") as graphs:
        function_id_column = McritTableColumn.columnTypeToIndex(
            McritTableColumn.FUNCTION_ID, form.config.FUNCTION_MATCHES_TABLE_COLUMNS
        )
        _assert(
            function_id_column is not None, "Function Scope function-id column is not configured"
        )
        _emit_table_signal(
            function_widget.table_function_matches,
            "doubleClicked",
            0,
            function_id_column,
        )
    _assert(graphs, "Function Scope double-click did not open a graph viewer")
    _assert(graphs[0][1] and graphs[0][2], "Function graph callbacks returned no content")


def _exercise_block_widget(form, report, qt_application):
    import helpers.McritTableColumn as McritTableColumn

    block_widget = form.block_match_widget
    candidates = [
        function
        for function in report.getFunctions()
        if any(len(block.getInstructions()) >= 4 for block in function.getBlocks())
    ]
    _assert(candidates, "fixture has no function suitable for block queries")
    candidate = max(candidates, key=lambda item: item.num_instructions)
    block = next(block for block in candidate.getBlocks() if len(block.getInstructions()) >= 4)
    form.current_function = candidate.offset
    form.current_block = block.offset
    block_widget.last_viewed_function = None
    block_widget.b_query_single.click()
    _process_events(qt_application, rounds=2)
    _assert(block_widget._last_block_matches is not None, "Block Scope query did not cache results")
    _assert(block_widget.table_block_summary.rowCount() > 0, "Block Scope query returned no blocks")

    block_widget.cb_activate_live_tracking.click()
    block_widget.cb_filter_library.click()
    block_widget.sb_blocksize_threshold.setValue(block_widget.sb_blocksize_threshold.value())
    _process_events(qt_application, rounds=2)

    offset_column = McritTableColumn.columnTypeToIndex(
        McritTableColumn.OFFSET, form.config.BLOCK_SUMMARY_TABLE_COLUMNS
    )
    _assert(offset_column is not None, "Block Scope offset column is not configured")
    matched_offset = next(
        (offset for offset, entry in block_widget._last_block_matches.items() if entry["matches"]),
        None,
    )
    selected_row = 0
    if matched_offset is not None:
        for row in range(block_widget.table_block_summary.rowCount()):
            if (
                int(block_widget.table_block_summary.item(row, offset_column).text(), 16)
                == matched_offset
            ):
                selected_row = row
                break
    _emit_table_signal(block_widget.table_block_summary, "clicked", selected_row, offset_column)
    _assert(
        block_widget.table_block_matches.rowCount() > 0,
        "Block Scope did not render a positive block match",
    )

    jumped_to = []
    original_jump = block_widget.cc.ida_proxy.Jump
    block_widget.cc.ida_proxy.Jump = lambda offset: jumped_to.append(offset)
    try:
        _emit_table_signal(
            block_widget.table_block_summary,
            "doubleClicked",
            selected_row,
            offset_column,
        )
    finally:
        block_widget.cc.ida_proxy.Jump = original_jump
    _assert(jumped_to, "Block Scope summary double-click did not navigate")

    with _capture_graph_show("widgets.BlockMatchWidget") as graphs:
        _emit_table_signal(block_widget.table_block_matches, "doubleClicked", 0, 0)
    _assert(graphs, "Block Scope double-click did not open a graph viewer")
    _assert(graphs[0][1] and graphs[0][2], "Block graph callbacks returned no content")


def _exercise_sample_widget(form, qt_application):
    sample_widget = form.sample_widget
    form.main_widget.tabs.setCurrentIndex(form.main_widget.tabs.indexOf(sample_widget))
    sample_widget.update()
    _process_events(qt_application, rounds=2)
    _assert(
        sample_widget.table_best_family_matches.rowCount() > 0,
        "Sample Match Summary rendered no positive matches",
    )
    _emit_table_signal(sample_widget.table_best_family_matches, "clicked", 0, 0)
    _emit_table_signal(sample_widget.table_best_family_matches, "doubleClicked", 0, 0)
    sample_widget.cb_filter_library.click()
    _process_events(qt_application)
    _assert(
        "Best Matches per Family" in sample_widget.label_best_matches.text(),
        "Sample Match Summary filter did not update its label",
    )


def _exercise_overview_widget(form, report, qt_application):
    import ida_funcs

    import helpers.McritTableColumn as McritTableColumn

    overview = form.function_widget
    overview.b_fetch_labels.click()
    _process_events(qt_application, rounds=2)
    _assert(
        overview.table_local_functions.rowCount() > 0,
        "Function Overview rendered no matched local functions",
    )

    for radio_button in (
        overview.rb_filter_none,
        overview.rb_filter_labels,
        overview.rb_filter_applicable,
        overview.rb_filter_conflicted,
    ):
        radio_button.click()
    overview.sb_minhash_threshold.setValue(overview.sb_minhash_threshold.value())
    overview.b_select_deselect_all.click()
    overview.b_select_deselect_all.click()
    _process_events(qt_application, rounds=2)

    label_column = McritTableColumn.columnTypeToIndex(
        McritTableColumn.SCORE_AND_LABEL, form.config.OVERVIEW_TABLE_COLUMNS
    )
    offset_column = McritTableColumn.columnTypeToIndex(
        McritTableColumn.OFFSET, form.config.OVERVIEW_TABLE_COLUMNS
    )
    _assert(
        label_column is not None and offset_column is not None, "Overview columns are incomplete"
    )
    delegate = overview.table_local_functions.itemDelegateForColumn(label_column)
    _assert(hasattr(delegate, "getEditorForRow"), "Overview label delegate was not installed")
    editor = delegate.getEditorForRow(0)
    _assert(editor is not None, "Overview did not create a label editor")
    editor.setCurrentIndex(0)
    editor.activated.emit(0)
    editor.customContextMenuRequested.emit(form.cc.QtCore.QPoint(0, 0))
    _assert(editor.hasUserMadeSelection(), "Overview combo-box activation was not recorded")

    _emit_table_signal(overview.table_local_functions, "clicked", 0, label_column)
    _emit_table_signal(overview.table_local_functions, "doubleClicked", 0, label_column)

    # Make one local function look unnamed and run the real import action.
    imported_offset = int(overview.table_local_functions.item(0, offset_column).text(), 16)
    original_name = ida_funcs.get_func_name(imported_offset)
    overview.cc.ida_proxy.set_name(
        imported_offset, f"sub_{imported_offset:X}", overview.cc.ida_proxy.SN_NOWARN
    )
    overview.b_import_labels.click()
    imported_name = ida_funcs.get_func_name(imported_offset)
    _assert(
        imported_name and imported_name != f"sub_{imported_offset:X}",
        "Overview label import did not rename a function",
    )
    if original_name and original_name != imported_name:
        overview.cc.ida_proxy.set_name(
            imported_offset, original_name, overview.cc.ida_proxy.SN_NOWARN
        )

    # Populate the Function Scope name table after labels are loaded and use its
    # real double-click import path as well.
    function_widget = form.function_match_widget
    current_matches = form.function_matches.get(function_widget.current_function_offset)
    if current_matches:
        from helpers.minimcrit.storage.MatchingResult import MatchingResult

        function_widget.populateFunctionNameTable(MatchingResult.fromDict(current_matches))
        _process_events(qt_application)
        if function_widget.table_function_names.rowCount() > 0:
            label_index = McritTableColumn.columnTypeToIndex(
                McritTableColumn.FUNCTION_LABEL, form.config.FUNCTION_NAMES_TABLE_COLUMNS
            )
            _assert(label_index is not None, "Function Scope label column is not configured")
            _emit_table_signal(
                function_widget.table_function_names, "doubleClicked", 0, label_index
            )


def _exercise_live_mcrit(form, qt_application):
    from helpers.minimcrit.storage.FunctionLabelEntry import FunctionLabelEntry

    interface = form.mcrit_interface
    client = interface.mcrit_client
    main_widget = form.main_widget
    interface.checkConnection(async_=False)

    # Conversion and metadata are performed through the actual toolbar action.
    form.local_smda_report = None
    form.remote_sample_id = None
    form.remote_sample_entry = None
    with _smda_info_adapter(main_widget):
        main_widget.parseSmdaAction.trigger()
    _process_events(qt_application, rounds=2)
    report = form.local_smda_report
    _assert(report is not None, "Convert IDB action did not retain an SMDA report")
    _assert(list(report.getFunctions()), "Convert IDB action produced no functions")
    _assert(report.family == "mcrit-plugin-ci", "SMDA metadata dialog did not set family")
    _assert(report.version == "fixture-query", "SMDA metadata dialog did not set version")
    _write_report_artifact(report)
    _assert(main_widget.uploadSmdaAction.isEnabled(), "convert action did not enable upload")
    _assert(main_widget.exportSmdaAction.isEnabled(), "convert action did not enable export")
    _assert(main_widget.buildYaraStringAction.isEnabled(), "convert action did not enable YARA")

    # Upload through the real toolbar action, then wait for MCRIT's worker to
    # finish indexing the report.
    main_widget.uploadSmdaAction.trigger()
    _assert(form.remote_sample_id is not None, "Upload SMDA action returned no sample id")
    _wait_for_functions(client, form.remote_sample_id, qt_application)
    interface.querySampleSha256(report.sha256)
    _assert(form.remote_sample_entry is not None, "MCRIT SHA256 lookup returned no sample")
    interface.queryAllFamilyEntries()
    interface.queryAllSampleEntries()
    interface.queryFunctionEntriesBySampleId(form.remote_sample_id)

    # Request a matching result via the real result chooser and toolbar action.
    job_ids = []
    original_request = client.requestMatchesForSample

    def request_and_capture(*args, **kwargs):
        job_id = original_request(*args, **kwargs)
        job_ids.append(job_id)
        return job_id

    client.requestMatchesForSample = request_and_capture
    try:
        with _result_dialog_adapter(main_widget, "request"):
            main_widget.getMatchResultAction.trigger()
    finally:
        client.requestMatchesForSample = original_request
    _assert(job_ids and job_ids[-1], "Create Matching Job action returned no job id")

    result = client.awaitResult(job_ids[-1], sleep_time=1)
    _assert(isinstance(result, dict), "MCRIT matching result was not a JSON object")
    matches = result.get("matches", {})
    _assert(matches.get("samples") or matches.get("functions"), "MCRIT returned no matches")
    reference_sha256 = os.environ.get("MCRIT_IDA_SMOKE_REFERENCE_SHA256")
    if reference_sha256:
        reference_sample = client.getSampleBySha256(reference_sha256)
        _assert(reference_sample is not None, "MCRIT reference sample could not be retrieved")
        _assert(
            _matches_sample(matches, reference_sample.sample_id),
            "MCRIT did not return a match for the deterministic reference sample",
        )

    # Select the finished job through the actual result dialog.  This is the
    # path that decodes MatchingResult and switches to Function Overview.
    with _result_dialog_adapter(main_widget, "select", job_ids[-1]):
        main_widget.getMatchResultAction.trigger()
    _assert(form.matching_report is not None, "result chooser did not load MatchingResult")
    _assert(
        form.main_widget.tabs.currentWidget() is form.function_widget,
        "result retrieval did not focus Function Overview",
    )
    main_widget.modifySettingsAction.trigger()

    # The live server does not need seeded labels.  Add deterministic labels at
    # the plugin's existing interface boundary so the real label widgets and
    # import controls can be exercised without mutating the MCRIT database.
    original_query_labels = interface.queryFunctionEntriesById

    def query_with_deterministic_labels(function_ids, with_label_only=False):
        entries = original_query_labels(function_ids, with_label_only=with_label_only)
        if with_label_only and entries:
            for function_id, entry in entries.items():
                entry.function_labels = [
                    FunctionLabelEntry(
                        f"ci_label_{entry.offset:x}",
                        "ida-ci",
                        function_id=function_id,
                        timestamp=datetime.datetime(2020, 1, 1),
                    ),
                    FunctionLabelEntry(
                        f"ci_alt_{entry.offset:x}",
                        "ida-ci",
                        function_id=function_id,
                        timestamp=datetime.datetime(2020, 1, 2),
                    ),
                ]
        return entries

    interface.queryFunctionEntriesById = query_with_deterministic_labels
    try:
        _exercise_function_widget(form, report, qt_application)
        _exercise_block_widget(form, report, qt_application)
        _exercise_sample_widget(form, qt_application)
        _exercise_overview_widget(form, report, qt_application)

        artifact_dir = _artifact_dir()
        export_path = (
            artifact_dir / "exported-smda.json"
            if artifact_dir is not None
            else Path(tempfile.gettempdir()) / "mcrit-ida-smoke.smda"
        )
        import ida_kernwin

        original_ask_file = ida_kernwin.ask_file
        ida_kernwin.ask_file = lambda *_args: str(export_path)
        try:
            main_widget.exportSmdaAction.trigger()
        finally:
            ida_kernwin.ask_file = original_ask_file
        _assert(export_path.is_file(), "Export SMDA action did not create a file")
        json.loads(export_path.read_text(encoding="utf-8"))
        if artifact_dir is None:
            export_path.unlink(missing_ok=True)

        _exercise_yara_action(form, report, qt_application)
    finally:
        interface.queryFunctionEntriesById = original_query_labels

    return report


def _exercise_offline_plugin(form, qt_application):
    main_widget = form.main_widget
    with _smda_info_adapter(main_widget, family="offline-ci", version="no-server"):
        main_widget.parseSmdaAction.trigger()
    _process_events(qt_application, rounds=2)
    _assert(form.local_smda_report is not None, "offline Convert IDB action produced no report")
    _assert(main_widget.exportSmdaAction.isEnabled(), "offline conversion did not enable export")
    main_widget.modifySettingsAction.trigger()
    _exercise_yara_action(form, form.local_smda_report, qt_application)


def main() -> int:
    try:
        import ida_auto

        ida_auto.auto_wait()
        import ida_mcrit

        _run_plugin_lifecycle(ida_mcrit)
        form, qt_application = _create_form(ida_mcrit)
        ida_mcrit.MCRIT4IDA = form
        ida_mcrit.G_FORM = form

        if _is_live():
            _exercise_live_mcrit(form, qt_application)
        else:
            _exercise_offline_plugin(form, qt_application)

        form.OnClose(None)
        print("MCRIT_IDA_SMOKE_OK")
        _qexit(0)
        return 0
    except Exception as exc:
        print(f"MCRIT_IDA_SMOKE_FAILURE: {exc}")
        import traceback

        traceback.print_exc()
        try:
            _qexit(1)
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
