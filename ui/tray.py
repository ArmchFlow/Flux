from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtCore import pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QAction

from core.translations import tr


class SystemTray(QSystemTrayIcon):
    show_window_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    connect_requested = pyqtSignal()
    disconnect_requested = pyqtSignal()
    quick_connect_requested = pyqtSignal()
    recent_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._connected = False
        self._setup()

    def _setup(self):
        self.setIcon(self._make_icon(False))
        self.setToolTip("Flux")

        self._menu = QMenu()

        self._status_action = QAction(tr("status_disconnected"))
        self._status_action.setEnabled(False)
        self._menu.addAction(self._status_action)

        self._menu.addSeparator()

        self._quick_action = QAction(tr("quick_connect"))
        self._quick_action.triggered.connect(self._on_quick_connect)
        self._menu.addAction(self._quick_action)

        self._recent_menu = QMenu(tr("recent_servers"), self._menu)
        self._recent_menu_action = self._menu.addMenu(self._recent_menu)
        self._recent_menu_action.setVisible(False)

        self._connect_action = QAction(tr("connect"))
        self._connect_action.triggered.connect(self._on_connect)
        self._menu.addAction(self._connect_action)

        self._disconnect_action = QAction(tr("disconnect"))
        self._disconnect_action.triggered.connect(self._on_disconnect)
        self._disconnect_action.setVisible(False)
        self._menu.addAction(self._disconnect_action)

        self._menu.addSeparator()

        exit_action = QAction(tr("exit"))
        exit_action.triggered.connect(self._on_quit)
        self._menu.addAction(exit_action)

        self.setContextMenu(self._menu)
        self.activated.connect(self._on_activated)

    def set_connected(self, connected: bool):
        self._connected = connected
        self.setIcon(self._make_icon(connected))

        if connected:
            self._status_action.setText(tr("status_connected"))
            self._connect_action.setVisible(False)
            self._disconnect_action.setVisible(True)
            self.setToolTip(tr("tooltip_connected"))
        else:
            self._status_action.setText(tr("status_disconnected"))
            self._connect_action.setVisible(True)
            self._disconnect_action.setVisible(False)
            self.setToolTip(tr("tooltip_disconnected"))

    def set_quick_connect_enabled(self, enabled: bool):
        self._quick_action.setEnabled(enabled)

    def set_recent_servers(self, servers: list):
        self._recent_menu.clear()
        if not servers:
            self._recent_menu_action.setVisible(False)
            return
        for tag, name in servers:
            act = self._recent_menu.addAction(name)
            act.triggered.connect(lambda _, t=tag: self.recent_selected.emit(t))
        self._recent_menu_action.setVisible(True)

    @property
    def menu(self):
        return self._menu

    def _on_connect(self):
        self.connect_requested.emit()

    def _on_disconnect(self):
        self.disconnect_requested.emit()

    def _on_quick_connect(self):
        self.quick_connect_requested.emit()

    def _on_show(self):
        self.show_window_requested.emit()

    def _on_quit(self):
        self.quit_requested.emit()

    def _on_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_window_requested.emit()

    def _make_icon(self, connected: bool) -> QIcon:
        size = 64
        p = QPixmap(QSize(size, size))
        p.fill(QColor(0, 0, 0, 0))
        painter = QPainter(p)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if connected:
            painter.setBrush(QBrush(QColor("#a6e3a1")))
            painter.setPen(QColor("#1e1e2e"))
        else:
            painter.setBrush(QBrush(QColor("#585b70")))
            painter.setPen(QColor("#cdd6f4"))
        painter.drawEllipse(8, 8, size - 16, size - 16)
        painter.end()
        return QIcon(p)
