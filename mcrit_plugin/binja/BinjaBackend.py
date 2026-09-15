import hashlib
import os
import re
import traceback

import binaryninja
from binaryninja import Logger, interaction
from binaryninja.enums import (
    BranchType,
    InstructionTextTokenType,
    MessageBoxButtonResult,
    MessageBoxButtonSet,
    MessageBoxIcon,
)

from mcrit_plugin.binja.BinjaSmdaInterface import BinjaSmdaInterface
from mcrit_plugin.core.Backend import Backend

TITLE = "MCRIT"
logger = Logger(0, TITLE)


class BinjaBackend(Backend):
    name = "Binary Ninja"
    plugin_name = "MCRIT4BinaryNinja"

    def __init__(self, bv):
        self.bv = bv
        self.view_frame = None
        self.cursor_offset = None
        self._input_hashes = None

    def _smda_interface(self):
        return BinjaSmdaInterface(self.bv)

    def _input_bytes(self):
        raw = self.bv.file.raw
        return raw.read(raw.start, raw.length) if raw is not None else b""

    def _hashes(self):
        if self._input_hashes is None:
            data = self._input_bytes()
            self._input_hashes = (
                hashlib.md5(data).hexdigest(),
                hashlib.sha256(data).hexdigest(),
                len(data),
            )
        return self._input_hashes

    def get_input_md5(self):
        return self._hashes()[0]

    def get_input_sha256(self):
        return self._hashes()[1]

    def get_input_filename(self):
        return os.path.basename(self.bv.file.original_filename or self.bv.file.filename)

    def get_input_size(self):
        return self._hashes()[2]

    def export_smda_report(self):
        from smda.Disassembler import Disassembler
        from smda.ida.IdaExporter import IdaExporter

        interface = self._smda_interface()
        disassembler = Disassembler()
        # same path as Disassembler(backend="IDA"): an explicitly pinned exporter backend
        disassembler.disassembler = IdaExporter(disassembler.config, ida_interface=interface)
        disassembler._explicit_backend = True
        return disassembler.disassembleBuffer(interface.getBinary(), 0)

    def get_binary_info(self):
        from smda.common.BinaryInfo import BinaryInfo

        interface = self._smda_interface()
        binary_info = BinaryInfo(interface.getBinary())
        binary_info.architecture = interface.getArchitecture()
        binary_info.base_addr = interface.getBaseAddr()
        binary_info.bitness = interface.getBitness()
        return binary_info

    def get_function_symbols(self):
        return self._smda_interface().getFunctionSymbols()

    def get_cursor_address(self):
        if self.view_frame is not None:
            return self.view_frame.getCurrentOffset()
        return self.cursor_offset

    def get_selection(self):
        if self.view_frame is None:
            return None, None
        view = self.view_frame.getCurrentViewInterface()
        if view is None:
            return None, None
        start, end = view.getSelectionOffsets()
        if start == end:
            return None, None
        return start, end

    def get_current_function(self, view=None):
        """view is the offset reported by the sidebar; None means no location update."""
        if view is None:
            return None
        functions = self.bv.get_functions_containing(view)
        return functions[0].start if functions else None

    def read_bytes(self, address, size):
        return self.bv.read(address, size)

    def jump_to(self, address):
        if self.view_frame is not None:
            self.view_frame.navigate(self.bv, address)
        else:
            self.bv.navigate(self.bv.view, address)

    def get_function_name(self, address):
        function = self.bv.get_function_at(address)
        return function.name if function is not None else None

    def set_function_name(self, address, name):
        function = self.bv.get_function_at(address)
        if function is None:
            return False
        with self.bv.undoable_transaction():
            function.name = name
        return True

    def has_default_function_name(self, address):
        function = self.bv.get_function_at(address)
        if function is None:
            return False
        return function.symbol.auto and re.match("sub_[0-9a-fA-F]+$", function.name) is not None

    def run_background(self, title, work, on_done):
        backend = self

        class Task(binaryninja.BackgroundTaskThread):
            def run(task):
                try:
                    task.progress = f"{title} (waiting for analysis)"
                    # reports must reflect finished analysis; not allowed on UI or worker threads
                    backend.bv.update_analysis_and_wait()
                    task.progress = title
                    result = work()
                except Exception:
                    logger.log_error(f"{title} failed:\n{traceback.format_exc()}")
                    binaryninja.execute_on_main_thread(
                        lambda: backend.show_warning(f"{title} failed, see the log for details.")
                    )
                    return
                binaryninja.execute_on_main_thread(lambda: on_done(result))

        Task(title, False).start()

    def run_on_ui_thread(self, func):
        result = []
        binaryninja.execute_on_main_thread_and_wait(lambda: result.append(func()))
        return result[0] if result else None

    def ask_save_file(self, default_name, prompt):
        return interaction.get_save_filename_input(prompt, "smda", default_name) or None

    def ask_yes_no(self, prompt):
        answer = interaction.show_message_box(
            TITLE, prompt, MessageBoxButtonSet.YesNoButtonSet, MessageBoxIcon.QuestionIcon
        )
        return answer == MessageBoxButtonResult.YesButton

    def show_warning(self, message):
        interaction.show_message_box(
            TITLE, message, MessageBoxButtonSet.OKButtonSet, MessageBoxIcon.WarningIcon
        )

    def show_function_graph(self, parent, sample_entry, function_entry, smda_function, coloring):
        if smda_function is None:
            return
        graph = binaryninja.FlowGraph()
        nodes = {}
        for block in smda_function.getBlocks():
            node = binaryninja.FlowGraphNode(graph)
            lines = []
            for instruction in block.getInstructions():
                api = smda_function.apirefs.get(instruction.offset, "")
                operands = f"[{api}]" if api else instruction.operands
                lines.append(
                    binaryninja.DisassemblyTextLine(
                        [
                            binaryninja.InstructionTextToken(
                                InstructionTextTokenType.AddressDisplayToken,
                                f"{instruction.offset:x}  ",
                                instruction.offset,
                            ),
                            binaryninja.InstructionTextToken(
                                InstructionTextTokenType.InstructionToken,
                                f"{instruction.mnemonic:<8}",
                            ),
                            binaryninja.InstructionTextToken(
                                InstructionTextTokenType.TextToken, operands
                            ),
                        ],
                        instruction.offset,
                    )
                )
            node.lines = lines
            if block.offset in coloring:
                rgb = coloring[block.offset]
                node.highlight = binaryninja.HighlightColor(
                    red=(rgb >> 16) & 0xFF, green=(rgb >> 8) & 0xFF, blue=rgb & 0xFF
                )
            graph.append(node)
            nodes[block.offset] = node
        for source, targets in smda_function.blockrefs.items():
            for target in targets:
                if source in nodes and target in nodes:
                    nodes[source].add_outgoing_edge(BranchType.UnconditionalBranch, nodes[target])
        title = (
            f"MCRIT CFG: sample {sample_entry.sample_id} ({sample_entry.family}), "
            f"function {function_entry.function_id}@0x{smda_function.offset:x}"
        )
        self.bv.show_graph_report(title, graph)
