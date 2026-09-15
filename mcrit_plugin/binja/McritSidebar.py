import traceback

# binaryninjaui must be imported before PySide6 so Binary Ninja's bundled Qt binding is used
from binaryninjaui import (
    Menu,
    Sidebar,
    SidebarContextSensitivity,
    SidebarWidget,
    SidebarWidgetLocation,
    SidebarWidgetType,
    UIAction,
    UIActionHandler,
    UIContext,
    UIContextNotification,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget

from mcrit_plugin.binja.BinjaBackend import BinjaBackend, logger
from mcrit_plugin.binja.config import clear_stored_secrets, config
from mcrit_plugin.ui_qt.McritSession import McritSession

SIDEBAR_NAME = "MCRIT"
_SIDEBAR_WIDGETS = []


class McritSidebarWidget(SidebarWidget):
    def __init__(self, name, frame, bv):
        SidebarWidget.__init__(self, name)
        self.actionHandler = UIActionHandler()
        self.actionHandler.setupActionHandler(self)
        self.backend = BinjaBackend(bv)
        self.backend.view_frame = frame
        self.session = McritSession(self.backend, config)
        # the sidebar can be shorter than the widgets' minimum size, which squeezes their layouts
        # into overlapping rows; a scroll area keeps the minimum size and scrolls instead
        self.session.parent = QWidget()
        self.session.setupWidgets()
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setWidget(self.session.parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll_area)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(150)
        self._refresh_timer.timeout.connect(
            lambda: self.session.refreshCursorWidgets(self.backend.cursor_offset)
        )
        _SIDEBAR_WIDGETS.append(self)
        self.destroyed.connect(lambda: _forget(self))
        if config.AUTO_ANALYZE_SMDA_ON_STARTUP:
            self.session.main_widget._onConvertSmdaButtonClicked()

    def notifyViewChanged(self, view_frame):
        self.backend.view_frame = view_frame

    def notifyOffsetChanged(self, offset):
        # coalesce rapid cursor moves; live queries hit the MCRIT server
        self.backend.cursor_offset = offset
        self._refresh_timer.start()

    def contextMenuEvent(self, event):
        self.m_contextMenuManager.show(self.m_menu, self.actionHandler)


def _forget(widget):
    if widget in _SIDEBAR_WIDGETS:
        _SIDEBAR_WIDGETS.remove(widget)


def _sidebar_icon():
    """Grayscale 56x56 mask of the MCRIT logo; Binary Ninja tints white shapes to the theme."""
    logo = QImage(config.ICON_FILE_PATH + "mcrit.png").scaled(
        56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation
    )
    icon = QImage(56, 56, QImage.Format_RGB32)
    icon.fill(0)
    painter = QPainter(icon)
    x_offset = (56 - logo.width()) // 2
    y_offset = (56 - logo.height()) // 2
    for y in range(logo.height()):
        for x in range(logo.width()):
            alpha = logo.pixelColor(x, y).alpha()
            if alpha:
                painter.setPen(QColor(alpha, alpha, alpha))
                painter.drawPoint(x + x_offset, y + y_offset)
    painter.end()
    return icon


class McritSidebarWidgetType(SidebarWidgetType):
    def __init__(self):
        SidebarWidgetType.__init__(self, _sidebar_icon(), SIDEBAR_NAME)

    def createWidget(self, frame, data):
        # exceptions raised here are swallowed by the sidebar, leaving an empty panel
        try:
            return McritSidebarWidget(SIDEBAR_NAME, frame, data)
        except Exception:
            logger.log_error(f"Failed to create the MCRIT sidebar:\n{traceback.format_exc()}")
            raise

    def defaultLocation(self):
        return SidebarWidgetLocation.RightContent

    def contextSensitivity(self):
        # one MCRIT session per binary view, like Binary Ninja's own Tags/Strings/Memory Map sidebars
        return SidebarContextSensitivity.PerViewTypeSidebarContext


class McritCloseNotification(UIContextNotification):
    def OnBeforeCloseFile(self, context, file, frame):
        if not config.SUBMIT_FUNCTION_NAMES_ON_CLOSE:
            return True
        session_id = file.getMetadata().session_id
        for widget in list(_SIDEBAR_WIDGETS):
            if (
                widget.backend.bv.file.session_id != session_id
                or widget.session.local_smda_report is None
            ):
                continue
            session = widget.session
            if session.findUnsyncedFunctionNames() and widget.backend.ask_yes_no(
                "Function names changed since the SMDA report was created. "
                "Upload an updated report to the MCRIT server before closing?"
            ):
                session.uploadUpdatedReport()
        return True


def _session_for(context):
    """Open the MCRIT sidebar for the action's view and return its session."""
    ui_context = context.context or UIContext.activeContext()
    if ui_context is None or context.binaryView is None:
        return None
    sidebar = ui_context.sidebar()
    if sidebar is None:
        return None
    sidebar.activate(SIDEBAR_NAME)
    widget = _widget_for_view(context.binaryView)
    return widget.session if widget is not None else None


def _widget_for_view(bv):
    # per-view-type sidebars: the Raw and PE views of one file share a session_id
    for widget in _SIDEBAR_WIDGETS:
        widget_bv = widget.backend.bv
        if widget_bv.file.session_id == bv.file.session_id and widget_bv.view_type == bv.view_type:
            return widget
    return None


def _has_report(session):
    return session.local_smda_report is not None


# (action name, handler(session), enabled(session) or None when always available)
_ACTIONS = [
    ("MCRIT\\Show Sidebar", lambda session: None, None),
    (
        "MCRIT\\Convert to SMDA Report",
        lambda session: session.main_widget._onConvertSmdaButtonClicked(),
        None,
    ),
    (
        "MCRIT\\Upload SMDA Report",
        lambda session: session.main_widget._onUploadSmdaButtonClicked(),
        lambda session: session.main_widget.uploadSmdaAction.isEnabled(),
    ),
    (
        "MCRIT\\Fetch Matching Result",
        lambda session: session.main_widget._onGetMatchResultButtonClicked(),
        lambda session: session.main_widget.getMatchResultAction.isEnabled(),
    ),
    (
        "MCRIT\\Export SMDA Report...",
        lambda session: session.main_widget._onExportSmdaButtonClicked(),
        lambda session: session.main_widget.exportSmdaAction.isEnabled(),
    ),
    (
        "MCRIT\\Build YARA String from Selection",
        lambda session: session.main_widget._onBuildYaraStringButtonClicked(),
        lambda session: session.main_widget.buildYaraStringAction.isEnabled(),
    ),
    (
        "MCRIT\\Query Current Function",
        lambda session: session.function_match_widget.queryCurrentFunction(),
        _has_report,
    ),
    (
        "MCRIT\\Query Current Block",
        lambda session: session.block_match_widget.queryCurrentBlock(),
        _has_report,
    ),
]


def _register_global_actions():
    name = "MCRIT\\Clear Stored API Token"
    UIAction.registerAction(name)
    UIActionHandler.globalActions().bindAction(
        name, UIAction(lambda context: clear_stored_secrets())
    )
    Menu.mainMenu("Plugins").addAction(name, "MCRIT")


def _register_actions():
    for name, handler, enabled in _ACTIONS:

        def activate(context, handler=handler):
            session = _session_for(context)
            if session is not None:
                handler(session)

        def is_valid(context, enabled=enabled):
            if context.binaryView is None:
                return False
            if enabled is None:
                return True
            widget = _widget_for_view(context.binaryView)
            return widget is not None and enabled(widget.session)

        UIAction.registerAction(name)
        UIActionHandler.globalActions().bindAction(name, UIAction(activate, is_valid))
        Menu.mainMenu("Plugins").addAction(name, "MCRIT")


_close_notification = None


def register():
    global _close_notification
    if _close_notification is not None:
        return
    Sidebar.addSidebarWidgetType(McritSidebarWidgetType())
    _register_actions()
    _register_global_actions()
    _close_notification = McritCloseNotification()
    UIContext.registerNotification(_close_notification)
