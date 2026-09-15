"""Binary Ninja GUI smoke test, installed as startup.py of a throwaway user directory.

scripts/run_binja_smoke.py prepares that directory and launches Binary Ninja on the query
sample. Checks run as chained event-loop callbacks so the UI thread is never blocked; the
outcome is written to gui-smoke.log in the user directory.
"""

import os
import threading
import time
import traceback

import binaryninja
from binaryninjaui import UIAction, UIContext, UIContextNotification
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

# startup.py is executed without __file__
LOG = os.path.join(binaryninja.user_directory(), "gui-smoke.log")
TIMEOUT = int(os.environ.get("MCRIT_BN_SMOKE_TIMEOUT", "120"))


def log(message):
    with open(LOG, "a", encoding="utf-8") as handle:
        handle.write(f"{time.strftime('%H:%M:%S')} {message}\n")


class Smoke:
    def __init__(self, bv):
        self.bv = bv
        self.widget = None
        self.session = None
        self.job_id = None
        self.target = None

    def finish(self, ok, message=""):
        log("MCRIT_BN_SMOKE_OK" if ok else f"MCRIT_BN_SMOKE_FAILURE: {message}")
        if os.environ.get("MCRIT_BN_SMOKE_KEEP_OPEN") != "1":
            QTimer.singleShot(1000, QApplication.instance().quit)

    def step(self, func, delay=0):
        def run():
            try:
                func()
            except Exception as exc:
                self.finish(False, f"{exc}\n{traceback.format_exc()}")

        QTimer.singleShot(delay, run)

    def wait(self, predicate, then, what):
        deadline = time.time() + TIMEOUT

        def poll():
            if predicate():
                log(f"PASS {what}")
                then()
            elif time.time() > deadline:
                raise AssertionError(f"timed out: {what}")
            else:
                self.step(poll, 250)

        self.step(poll)

    def check(self, condition, what):
        if not condition:
            raise AssertionError(what)
        log(f"PASS {what}")

    def start(self):
        from mcrit_plugin.binja import McritSidebar

        self.sidebar_module = McritSidebar
        self.check(
            binaryninja.Settings().contains("mcrit.mcrit_server"), "MCRIT settings registered"
        )
        for name, _handler, _enabled in McritSidebar._ACTIONS:
            self.check(UIAction.isActionRegistered(name), f"action registered: {name}")
        UIContext.activeContext().sidebar().activate(McritSidebar.SIDEBAR_NAME)
        self.wait(self.find_widget, self.convert, "MCRIT sidebar created for the binary view")

    def find_widget(self):
        for widget in self.sidebar_module._SIDEBAR_WIDGETS:
            if widget.backend.bv.file.session_id == self.bv.file.session_id:
                self.widget = widget
                self.session = widget.session
                return True
        return False

    def convert(self):
        main_widget = self.session.main_widget
        expected_sha256 = os.environ["MCRIT_BN_SMOKE_SHA256"]
        self.check(
            self.session.cc.backend.get_input_sha256() == expected_sha256,
            "input sha256 matches file",
        )

        class InfoDialog(main_widget.SmdaInfoDialog):
            def exec_(dialog):
                dialog.edit_family.setText("binja-smoke")
                dialog.edit_version.setText("fixture-query")
                dialog._cb_is_library.setChecked(False)
                dialog.ok_button.click()
                return 1

        main_widget.SmdaInfoDialog = InfoDialog
        main_widget.parseSmdaAction.trigger()
        self.wait(
            lambda: self.session.local_smda_report is not None,
            self.upload,
            "Convert action produced an SMDA report in the background",
        )

    def upload(self):
        main_widget = self.session.main_widget
        report = self.session.local_smda_report
        self.check(len(list(report.getFunctions())) > 0, "SMDA report contains functions")
        self.check(
            report.smda_version.startswith("MCRIT4BinaryNinja"),
            "report records the Binary Ninja producer",
        )
        self.check(
            main_widget.uploadSmdaAction.isEnabled(), "upload action enabled after conversion"
        )
        main_widget.uploadSmdaAction.trigger()
        client = self.session.mcrit_interface.mcrit_client
        self.wait(
            lambda: (
                self.session.remote_sample_id is not None
                and bool(client.getFunctionsBySampleId(self.session.remote_sample_id))
            ),
            self.request_matching,
            "upload finished and the server indexed the functions",
        )

    def request_matching(self):
        interface = self.session.mcrit_interface
        client = interface.mcrit_client
        main_widget = self.session.main_widget
        interface.querySampleSha256(self.session.local_smda_report.sha256)
        interface.queryAllFamilyEntries()
        interface.queryAllSampleEntries()
        self.check(self.session.remote_sample_entry is not None, "uploaded sample found by sha256")

        job_ids = []
        original_request = client.requestMatchesForSample

        def capture_request(*args, **kwargs):
            job_id = original_request(*args, **kwargs)
            job_ids.append(job_id)
            return job_id

        original_dialog = main_widget.ResultChooserDialog

        class RequestDialog(original_dialog):
            def exec_(dialog):
                dialog.create_button.click()
                return 1

        client.requestMatchesForSample = capture_request
        main_widget.ResultChooserDialog = RequestDialog
        try:
            main_widget.getMatchResultAction.trigger()
        finally:
            client.requestMatchesForSample = original_request
            main_widget.ResultChooserDialog = original_dialog
        self.check(bool(job_ids and job_ids[-1]), "Create Matching Job returned a job id")
        self.job_id = job_ids[-1]
        self.wait(
            lambda: client.getResultForJob(self.job_id) is not None,
            self.select_matching,
            "matching job finished",
        )

    def select_matching(self):
        client = self.session.mcrit_interface.mcrit_client
        main_widget = self.session.main_widget
        reference_sha256 = os.environ.get("MCRIT_BN_SMOKE_REFERENCE_SHA256")
        if reference_sha256:
            result = client.getResultForJob(self.job_id)
            reference = client.getSampleBySha256(reference_sha256)
            matched_samples = {
                match.get("sample_id")
                for match in (result.get("matches", {}).get("samples") or [])
                if isinstance(match, dict)
            }
            self.check(
                reference is not None and reference.sample_id in matched_samples,
                "Binary Ninja report matches the reference sample",
            )

        target_job = str(self.job_id)
        original_dialog = main_widget.ResultChooserDialog

        class SelectDialog(original_dialog):
            def exec_(dialog):
                rows = [
                    row
                    for row, info in enumerate(dialog.job_infos)
                    if str(info.job_id) == target_job
                ]
                if not rows:
                    raise AssertionError(f"matching job {target_job} was not listed")
                dialog.table_jobs.selectRow(rows[0])
                dialog.select_button.click()
                return 1

        main_widget.ResultChooserDialog = SelectDialog
        try:
            main_widget.getMatchResultAction.trigger()
        finally:
            main_widget.ResultChooserDialog = original_dialog
        self.check(
            self.session.matching_report is not None, "result chooser loaded the MatchingResult"
        )
        self.check(
            main_widget.tabs.currentWidget() is self.session.function_widget,
            "Function Overview shown with results",
        )
        self.step(self.navigate)

    def navigate(self):
        self.target = max(self.bv.functions, key=lambda function: len(function.basic_blocks))
        self.widget.backend.jump_to(self.target.start)
        self.wait(
            lambda: self.widget.backend.get_cursor_address() == self.target.start,
            self.query_function,
            "navigation moved the cursor",
        )

    def query_function(self):
        self.widget.notifyOffsetChanged(self.target.start)
        self.wait(
            lambda: self.session.current_function == self.target.start,
            self.query_current_function,
            "Function Scope follows the cursor after the debounce",
        )

    def query_current_function(self):
        self.session.function_match_widget.queryCurrentFunction()
        self.wait(
            lambda: self.session.function_match_widget.table_function_matches.rowCount() > 0,
            self.rename_and_graph,
            "Function Scope lists matches for the current function",
        )

    def rename_and_graph(self):
        backend = self.session.cc.backend
        original_name = self.target.name
        self.check(
            backend.set_function_name(self.target.start, "mcrit_smoke_name"), "rename applied"
        )
        self.check(
            backend.get_function_name(self.target.start) == "mcrit_smoke_name", "rename visible"
        )
        self.bv.undo()
        self.check(self.target.name == original_name, "rename is undoable")

        smda_function = self.session.local_smda_report.getFunction(self.target.start)
        function_entry = type("FunctionEntry", (), {"function_id": 0})()
        backend.show_function_graph(
            None,
            self.session.remote_sample_entry,
            function_entry,
            smda_function,
            {self.target.start: 0x00DDFF},
        )
        log("PASS CFG graph report opened")
        self.finish(True)


class SmokeNotification(UIContextNotification):
    def __init__(self):
        UIContextNotification.__init__(self)
        self.started = False

    def OnAfterOpenFile(self, context, file, frame):
        if self.started:
            return
        self.started = True
        bv = frame.getCurrentBinaryView()
        log(f"opened {bv.file.filename} ({bv.view_type})")
        smoke = Smoke(bv)

        def analyze():
            bv.update_analysis_and_wait()
            binaryninja.execute_on_main_thread(lambda: smoke.step(smoke.start))

        threading.Thread(target=analyze, daemon=True).start()


if os.environ.get("MCRIT_BN_SMOKE_SHA256"):
    open(LOG, "w").close()
    _smoke_notification = SmokeNotification()
    UIContext.registerNotification(_smoke_notification)
