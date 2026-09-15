#!/usr/bin/python
"""
MCRIT4IDA - integration with MCRIT server
code inspired by and based on IDAscope
"""

import ida_idaapi
import ida_kernwin
import idaapi
from ida_kernwin import PluginForm

from mcrit_plugin.core.McritSession import McritSession
from mcrit_plugin.ida.config import MCRIT4IDA_PLUGIN_ONLY, config

IdaBackend = None


def _require_gui():
    """Fail clearly when a GUI-only plugin action is invoked through IDALib."""
    is_idaq = getattr(ida_kernwin, "is_idaq", None)
    if not callable(is_idaq) or not is_idaq():
        raise RuntimeError("MCRIT4IDA's Qt interface requires the IDA GUI")


def _load_dependencies():
    """Load the IDA backend only when the form is opened; Qt and widgets load in McritSession."""
    _require_gui()
    global IdaBackend

    if IdaBackend is not None:
        return

    from mcrit_plugin.ida.IdaBackend import IdaBackend as _IdaBackend

    IdaBackend = _IdaBackend


################################################################################
# Core of the MCRIT4IDA GUI.
################################################################################

MCRIT4IDA = None
NAME = "MCRIT4IDA v%s" % config.VERSION

G_FORM = None


class IdaViewHooks(idaapi.View_Hooks):
    """
    Courtesy of Alex Hanel's FunctionTrapperKeeper
    https://github.com/alexander-hanel/FunctionTrapperKeeper/blob/main/function_trapper_keeper.py
    """

    def __init__(self, form):
        super().__init__()
        self.form = form

    def view_curpos(self, view):
        self.refresh_widget(view)

    def view_dblclick(self, view, event):
        self.refresh_widget(view)

    def view_click(self, view, event):
        self.refresh_widget(view)

    def view_loc_changed(self, view, now, was):
        self.refresh_widget(view)

    def refresh_widget(self, view):
        if not self.form:
            return
        for widget in self.form.hook_subscribed_widgets:
            widget.hook_refresh(view)


class Mcrit4IdaForm(PluginForm, McritSession):
    """
    This class contains the main window of MCRIT4IDA
    Setup of core modules and widgets is performed in here.
    """

    def __init__(self):
        _load_dependencies()
        PluginForm.__init__(self)
        McritSession.__init__(self, IdaBackend(), config)
        self.view_hook = None

    def OnCreate(self, form):
        """
        When creating the form, setup the shared modules and widgets
        """
        print("[+] Loading MCRIT4IDA")
        # compatibility with IDA < 6.9
        self.view_hook = IdaViewHooks(self)
        self.view_hook.hook()
        try:
            self.parent = self.FormToPySideWidget(form)
        except Exception:
            self.parent = self.FormToPyQtWidget(form)
        self.parent.setWindowIcon(self.icon)
        self.setupWidgets()
        if self.config.AUTO_ANALYZE_SMDA_ON_STARTUP:
            # simulate button click on "Convert IDB to SMDA" to capture potential family info
            print("Performing automatic SMDA analysis on startup...")
            self.main_widget._onConvertSmdaButtonClicked()

    def OnClose(self, form):
        """
        Perform cleanup.
        """
        # check if there is a mismatch between function names stored in self.local_smda_report and the atual IDB
        # if yes, ask the user if they want to upload an updated report to the MCRIT server
        if config.SUBMIT_FUNCTION_NAMES_ON_CLOSE:
            print("Checking for unsynced function names...")
            if self.findUnsyncedFunctionNames() and self.cc.backend.ask_yes_no(
                "There are new function name changes in the IDB. Do you want to upload an updated report to the MCRIT server before closing?"
            ):
                self.uploadUpdatedReport()
        self.release()

    def release(self):
        """Unhook and drop module references; safe to call more than once."""
        if self.view_hook is not None:
            self.view_hook.unhook()
            self.view_hook = None
        self.hook_subscribed_widgets = []
        global G_FORM
        if G_FORM is self:
            G_FORM = None
        global MCRIT4IDA
        if MCRIT4IDA is self:
            MCRIT4IDA = None

    def Show(self):
        if self.cc.backend.get_input_md5() is not None:
            # Show() takes WOPN_* flags and adds WOPN_RESTORE itself
            return PluginForm.Show(self, NAME, options=PluginForm.WOPN_PERSIST)
        return None


################################################################################
# Usage as plugin
################################################################################


def PLUGIN_ENTRY():
    return Mcrit4IdaPlugin()


def show_mcrit_form():
    global MCRIT4IDA
    try:
        _require_gui()
    except RuntimeError as exc:
        print(f"[!] {exc}")
        return None
    created_form = False
    if MCRIT4IDA is None:
        try:
            MCRIT4IDA = Mcrit4IdaForm()
            created_form = True
        except ImportError as exc:
            ida_kernwin.warning(str(exc))
            return None
    if MCRIT4IDA.Show() is None:
        if created_form:
            try:
                MCRIT4IDA.OnClose(MCRIT4IDA)
            except Exception as exc:
                print(f"[!] Error closing MCRIT4IDA after failed show: {exc}")
            MCRIT4IDA = None
        return None
    global G_FORM
    G_FORM = MCRIT4IDA
    return MCRIT4IDA


class Mcrit4IdaPlugmod(ida_idaapi.plugmod_t):
    """Per-database plugin instance (PLUGIN_MULTI); owns the form it opened."""

    def __init__(self):
        super().__init__()
        self.form = None

    def run(self, arg):
        self.form = show_mcrit_form()
        return True

    def __del__(self):
        # called when the database closes; IDA normally closes the form first (OnClose -> release)
        if self.form is not None:
            self.form.release()
            self.form = None


class Mcrit4IdaPlugin(ida_idaapi.plugin_t):
    """
    Plugin version of MCRIT4IDA. Use this to deploy MCRIT4IDA via IDA plugins folder.
    """

    flags = ida_idaapi.PLUGIN_MULTI
    comment = NAME
    help = "MCRIT4IDA - Plugin to interact with a MCRIT server."
    wanted_name = "MCRIT4IDA"
    wanted_hotkey = "Ctrl-F4"

    def init(self):
        return Mcrit4IdaPlugmod()


################################################################################
# Usage as script
################################################################################


def main():
    global MCRIT4IDA
    if MCRIT4IDA is not None:
        try:
            MCRIT4IDA.OnClose(MCRIT4IDA)
            print("reloading MCRIT4IDA")
        except Exception:
            pass
        MCRIT4IDA = None

    if MCRIT4IDA_PLUGIN_ONLY:
        print("MCRIT4IDA: configured as plugin-only mode, ignoring main function of script.")
        return

    show_mcrit_form()


if __name__ == "__main__":
    main()
