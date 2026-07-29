from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QIcon, QAction
import sys
from pathlib import Path


def _tray_icon_path() -> str:
    try:
        base = Path(sys._MEIPASS)
    except AttributeError:
        base = Path(__file__).parent.parent
    candidates = [
        base / "bin" / "flux_tray.png",
        base / "bin" / "flux.ico",
        base / "Flux detail.png",
    ]
    for p in candidates:
        if p.exists():
            return str(p.resolve())
    return str(candidates[0])


class SystemTray(QSystemTrayIcon):
    show_window_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    connect_requested = pyqtSignal()
    disconnect_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._connected = False
        self._setup()

    def _setup(self):
        path = _tray_icon_path()
        self.setIcon(QIcon(path))
        self.setToolTip("Flux")

        self._menu = QMenu()

        self._status_action = QAction("Status: Disconnected")
        self._status_action.setEnabled(False)
        self._menu.addAction(self._status_action)

        self._menu.addSeparator()

        self._connect_action = QAction("Connect")
        self._connect_action.triggered.connect(self._on_connect)
        self._menu.addAction(self._connect_action)

        self._disconnect_action = QAction("Disconnect")
        self._disconnect_action.triggered.connect(self._on_disconnect)
        self._disconnect_action.setVisible(False)
        self._menu.addAction(self._disconnect_action)

        self._menu.addSeparator()

        exit_action = QAction("Exit")
        exit_action.triggered.connect(self._on_quit)
        self._menu.addAction(exit_action)

        self.setContextMenu(self._menu)
        self.activated.connect(self._on_activated)

    def set_connected(self, connected: bool):
        self._connected = connected

        if connected:
            self._status_action.setText("Status: Connected")
            self._connect_action.setVisible(False)
            self._disconnect_action.setVisible(True)
            self.setToolTip("Flux - Connected")
        else:
            self._status_action.setText("Status: Disconnected")
            self._connect_action.setVisible(True)
            self._disconnect_action.setVisible(False)
            self.setToolTip("Flux - Disconnected")

    def _on_connect(self):
        self.connect_requested.emit()

    def _on_disconnect(self):
        self.disconnect_requested.emit()

    def _on_show(self):
        self.show_window_requested.emit()

    def _on_quit(self):
        self.quit_requested.emit()

    def _on_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_window_requested.emit()
