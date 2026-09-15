import os
import re

import ida_bytes
import ida_funcs
import ida_kernwin
import idaapi
import idc

from mcrit_plugin.core.Backend import Backend

try:
    import ida_hexrays
except ImportError:
    ida_hexrays = None


def _address_or_none(ea):
    if ea is None or ea == idaapi.BADADDR:
        return None
    return ea


class IdaBackend(Backend):
    name = "IDA"

    def get_input_md5(self):
        md5 = idc.retrieve_input_file_md5()
        return md5.hex() if md5 is not None else None

    def get_input_sha256(self):
        return idaapi.retrieve_input_file_sha256().hex()

    def get_input_filename(self):
        return os.path.basename(idaapi.get_root_filename())

    def get_input_size(self):
        return idaapi.retrieve_input_file_size()

    def export_smda_report(self):
        from smda.Disassembler import Disassembler
        from smda.ida.IdaInterface import IdaInterface

        return Disassembler(backend="IDA").disassembleBuffer(IdaInterface().getBinary(), 0)

    def get_binary_info(self):
        from smda.common.BinaryInfo import BinaryInfo
        from smda.ida.IdaInterface import IdaInterface

        ida_interface = IdaInterface()
        binary_info = BinaryInfo(ida_interface.getBinary())
        if not binary_info.architecture:
            binary_info.architecture = ida_interface.getArchitecture()
        if not binary_info.base_addr:
            binary_info.base_addr = ida_interface.getBaseAddr()
        if not binary_info.bitness:
            binary_info.bitness = ida_interface.getBitness()
        return binary_info

    def get_function_symbols(self):
        from smda.ida.IdaInterface import IdaInterface

        return IdaInterface().getFunctionSymbols()

    def get_cursor_address(self):
        return _address_or_none(ida_kernwin.get_screen_ea())

    def get_selection(self):
        start = _address_or_none(idc.read_selection_start())
        end = _address_or_none(idc.read_selection_end())
        if start is None or end is None:
            return None, None
        return start, end

    def get_current_function(self, view=None):
        """
        Courtesy of Alex Hanel's FunctionTrapperKeeper
        https://github.com/alexander-hanel/FunctionTrapperKeeper/blob/main/function_trapper_keeper.py
        """
        if view is None:
            return None
        widget_type = idaapi.get_widget_type(view)
        ea = self.get_cursor_address()
        if ea is None:
            return None
        if widget_type == idaapi.BWN_PSEUDOCODE:
            if ida_hexrays is None:
                return None
            try:
                cfunc = ida_hexrays.decompile(ea)
            except ida_hexrays.DecompilationFailure:
                return None
            # only accept cursor positions that map to an item of the decompiled tree
            if not any(item.ea == ea for item in cfunc.treeitems):
                return None
        elif widget_type != idaapi.BWN_DISASM:
            return None
        func = ida_funcs.get_func(ea)
        if not func:
            return None
        return _address_or_none(func.start_ea)

    def read_bytes(self, address, size):
        return ida_bytes.get_bytes(address, size)

    def jump_to(self, address):
        return idc.jumpto(address)

    def get_function_name(self, address):
        return ida_funcs.get_func_name(address)

    def set_function_name(self, address, name):
        return idc.set_name(address, name, idc.SN_NOWARN)

    def has_default_function_name(self, address):
        name = self.get_function_name(address)
        return bool(name) and re.match("sub_[0-9A-Fa-f]+$", name) is not None

    def run_on_ui_thread(self, func):
        try:
            return ida_kernwin.execute_sync(func, ida_kernwin.MFF_FAST)
        except Exception as e:
            print(
                f"[MCRIT] Failed to run on UI thread via ida_kernwin, running directly. Error: {e}"
            )
            return func()

    def ask_save_file(self, default_name, prompt):
        return ida_kernwin.ask_file(1, default_name, prompt) or None

    def ask_yes_no(self, prompt):
        return ida_kernwin.ask_yn(ida_kernwin.ASKBTN_NO, prompt) == ida_kernwin.ASKBTN_YES

    def show_warning(self, message):
        ida_kernwin.warning(message)

    def show_function_graph(self, parent, sample_entry, function_entry, smda_function, coloring):
        from mcrit_plugin.ida.SmdaGraphViewer import SmdaGraphViewer

        SmdaGraphViewer(parent, sample_entry, function_entry, smda_function, coloring).Show()
