import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget,
    QStatusBar, QLabel, QPushButton, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCloseEvent, QIcon

from .sub_tab import SubscriptionTab
from .servers_tab import ServersTab
from .settings_tab import SettingsTab
from .log_tab import LogTab
from .tray import SystemTray
from .styles import DARK_STYLE

from core.subscription import SubscriptionManager
from core.settings_manager import SettingsManager
from core.dual_mgr import DualManager
from core.config_builder import build_xray_proxy_config
from core.translations import tr
from main import find_icon
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(
        self,
        sub_manager: SubscriptionManager,
        settings_mgr: SettingsManager,
        xray_mgr: DualManager,
        vault: Fernet,
        data_dir,
    ):
        super().__init__()
        self.sub_manager = sub_manager
        self.settings_mgr = settings_mgr
        self.xray_mgr = xray_mgr
        self.vault = vault
        self.data_dir = data_dir
        self._connected = False
        self._current_proxy_tag = "auto"

        logger.info("Initializing MainWindow...")
        self.setWindowTitle("Flux")
        icon_path = find_icon("flux.ico")
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
        self.setMinimumSize(640, 480)
        self.resize(960, 680)
        self.setStyleSheet(DARK_STYLE)

        self._tray = SystemTray(self)
        self._tray.show_window_requested.connect(self._show_from_tray)
        self._tray.quit_requested.connect(self._quit_app)
        self._tray.connect_requested.connect(self._on_connect_from_tray)
        self._tray.disconnect_requested.connect(self._on_disconnect_from_tray)

        self._setup_ui()
        self._setup_statusbar()

        self._ping_timer = QTimer(self)
        self._ping_timer.timeout.connect(self._auto_refresh_status)
        self._ping_timer.start(10000)

        self._servers_tab.load_servers()
        self._on_ping_servers("__all__")
        self.set_connected(False)

        if self.settings_mgr.settings.minimize_to_tray:
            self._tray.show()
            logger.debug("System tray icon shown")

        if not self.settings_mgr.settings.start_minimized:
            self.show()
            logger.info("Main window shown")
        else:
            self.hide()
            logger.info("Starting minimized (hidden)")

        self._tray.show()

    def changeEvent(self, event):
        if event.type() == event.Type.WindowStateChange and self.windowState() & Qt.WindowState.WindowMinimized:
            event.ignore()
            self.hide()
            return
        super().changeEvent(event)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tabs = QTabWidget()

        self._servers_tab = ServersTab(self.sub_manager)
        self._servers_tab.connect_requested.connect(self._on_server_selected)
        self._servers_tab.disconnect_requested.connect(self._on_disconnect)
        self._servers_tab.ping_requested.connect(self._on_ping_servers)
        self._tabs.addTab(self._servers_tab, tr("tab_servers"))

        self._sub_tab = SubscriptionTab(self.sub_manager)
        self._sub_tab.update_requested.connect(self._on_update_sub)
        self._sub_tab.add_requested.connect(self._on_add_sub)
        self._tabs.addTab(self._sub_tab, tr("tab_subscriptions"))

        self._settings_tab = SettingsTab(self.settings_mgr)
        self._settings_tab.settings_changed.connect(self._on_settings_changed)
        self._tabs.addTab(self._settings_tab, tr("tab_settings"))

        self._log_tab = LogTab()
        self._tabs.addTab(self._log_tab, tr("tab_logs"))

        layout.addWidget(self._tabs)
        logger.debug("UI tabs set up: Subscriptions, Servers, Settings, Logs")

    def _setup_statusbar(self):
        status = QStatusBar()
        status.setStyleSheet("""
            QStatusBar {
                background-color: #181825;
                color: #a6adc8;
                border-top: 1px solid #313244;
                font-size: 11px;
            }
        """)

        self._status_text = QLabel(" " + tr("ready"))
        status.addWidget(self._status_text)

        self._traffic_label = QLabel("")
        status.addPermanentWidget(self._traffic_label)

        self.setStatusBar(status)
        logger.debug("Status bar ready")

    def _on_update_sub(self, url: str):
        logger.info("UI: update requested for subscription: %s", url[:80])
        self._status_text.setText(f" Updating subscription: {url[:60]}...")
        try:
            servers = self.sub_manager.update_subscription(url)
            self._sub_tab.refresh_after_update()
            self._servers_tab.load_servers()
            logger.info("Subscription updated: %d servers from %s", len(servers), url[:60])
            self._status_text.setText(f" Subscription updated: {len(servers)} servers")
        except Exception as e:
            logger.error("Subscription update failed: %s", e, exc_info=True)
            QMessageBox.critical(
                self, tr("update_error"),
                f"{tr('update_err_msg')}:\n{e}",
            )
            self._status_text.setText(" " + tr("update_failed"))

    def _on_add_sub(self, url: str, name: str):
        logger.info("UI: add subscription requested: url=%s, name=%s", url[:80], name or "(auto)")
        self._status_text.setText(f" Fetching subscription: {url[:60]}...")
        try:
            servers = self.sub_manager.update_subscription(url)
            self._sub_tab.refresh_after_update()
            self._servers_tab.load_servers()
            logger.info("Subscription added: %s → %d servers", url[:60], len(servers))
            self._status_text.setText(f" Subscription added: {len(servers)} servers")
        except Exception as e:
            logger.error("Failed to add subscription: %s", e, exc_info=True)
            self._status_text.setText(" Fetch failed")
            QMessageBox.critical(
                self, tr("error"),
                f"{tr('fetch_err_msg')}\n\n{e}",
            )

    def _on_server_selected(self, tag: str):
        logger.info("UI: server selected: %s", tag)
        if tag == "__auto__":
            self._current_proxy_tag = "auto"
        else:
            self._current_proxy_tag = tag

        if self._connected and self.xray_mgr.is_running:
            logger.info("Restarting xray with new server: %s", tag)
            self._disconnect_vpn()
            self._connect_vpn()
        else:
            logger.info("Not connected, starting VPN...")
            self._connect_vpn()

    def _on_disconnect(self):
        logger.info("UI: disconnect requested")
        self._disconnect_vpn()

    def _on_connect_from_tray(self):
        logger.info("Tray: connect requested")
        self._connect_vpn()

    def _on_disconnect_from_tray(self):
        logger.info("Tray: disconnect requested")
        self._disconnect_vpn()

    def _connect_vpn(self):
        logger.info("=== CONNECTING VPN ===")
        self._status_text.setText(" " + tr("connecting"))

        servers = self.sub_manager.get_all_servers()
        logger.info("Servers available for connection: %d", len(servers))

        if not servers:
            logger.warning("No servers available for connection")
            QMessageBox.warning(self, tr("no_servers_title"), tr("no_servers"))
            self._status_text.setText(" " + tr("no_servers_title"))
            return

        logger.info("Building configs for %d servers (selected=%s)...",
                   len(servers), self._current_proxy_tag)
        try:
            if self.settings_mgr.settings.proxy.auto_select:
                selected_tag = servers[0].tag
            else:
                selected_tag = (
                    self._current_proxy_tag if self._current_proxy_tag != "auto"
                    else servers[0].tag
                )
            xray_cfg = build_xray_proxy_config(servers, selected_tag)
        except Exception as e:
            logger.error("Config build failed: %s", e, exc_info=True)
            QMessageBox.critical(self, tr("config_error"), str(e))
            self._status_text.setText(" " + tr("config_error"))
            return

        success, mode = self.xray_mgr.start(
            xray_cfg, self.settings_mgr.settings)

        if success:
            self.set_connected(True)
            self._status_text.setText(f" " + tr("connected_tun") + f" ({len(servers)} " + tr("servers_count").lower() + ")")
            logger.info("=== CONNECTED (%s) ===", mode)
        else:
            logger.error("=== CONNECTION FAILED ===")
            QMessageBox.critical(self, tr("connection_failed"),
                                mode or "Could not start.")
            self._status_text.setText(" " + tr("connection_failed"))

    def _disconnect_vpn(self):
        logger.info("=== DISCONNECTING ===")
        self.xray_mgr.stop()
        self.set_connected(False)
        self._status_text.setText(" " + tr("disconnected"))

    def set_connected(self, connected: bool):
        logger.debug("Connection state change: %s -> %s", self._connected, connected)
        self._connected = connected
        self._servers_tab.set_connected(connected)
        self._tray.set_connected(connected)

    def _on_ping_servers(self, tag: str):
        logger.info("UI: ping requested: %s", tag)

        if tag == "__all__":
            servers = self.sub_manager.get_all_servers()
            self._status_text.setText(" Testing all servers...")
            logger.info("TCP pinging %d servers...", len(servers))
            delays = self.xray_mgr.tcp_ping_servers(servers, timeout=2.0)
            self._servers_tab.update_delays(delays)
            ok = sum(1 for v in delays.values() if v >= 0)
            self._status_text.setText(f" Ping complete: {ok}/{len(delays)} responded")
            logger.info("Ping all: %d/%d responded", ok, len(delays))
        else:
            servers = self.sub_manager.get_all_servers()
            srv = next((s for s in servers if s.tag == tag), None)
            if srv:
                delay = self.xray_mgr.tcp_ping(srv.server, srv.port)
                self._servers_tab.update_delays({tag: delay})
                status = f"{delay} ms" if delay >= 0 else "timeout"
                self._status_text.setText(f" {tag}: {status}")
                logger.info("Ping %s: %s", tag, status)

    def _on_settings_changed(self):
        logger.info("Settings changed by user")
        if self._connected:
            logger.info("VPN is connected, asking about restart...")
            reply = QMessageBox.question(
                self, "Restart Required",
                "Settings changed. Restart VPN to apply?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                logger.info("Restarting VPN due to setting changes")
                self._disconnect_vpn()
                self._connect_vpn()
            else:
                logger.info("User declined VPN restart - new settings will apply on next connect")

    def _auto_refresh_status(self):
        try:
            if self._connected and not self.xray_mgr.is_running:
                logger.warning("Connection lost")
                self.set_connected(False)
                self._status_text.setText(" Connection lost")
        except Exception:
            pass

    def _show_from_tray(self):
        logger.debug("Restoring window from tray")
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _save_final_log(self):
        log_path = self.data_dir / "logs"
        log_path.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_log = log_path / f"myvpn_exit_{ts}.log"

        from core.log_utils import get_signal_handler
        handler = get_signal_handler()
        if handler:
            lines = list(handler.buffer)
            final_log.write_text("\n".join(lines), encoding="utf-8")
            logger.info("Final log saved: %s (%d lines)", final_log, len(lines))
        else:
            logger.warning("No log handler available for final save")

    def _force_exit(self):
        logger.info("=" * 50)
        logger.info("FORCE EXIT requested")
        logger.info("=" * 50)
        logger.info("Stopping xray...")
        self.xray_mgr.stop()
        logger.info("Saving final log...")
        self._save_final_log()
        logger.info("Hiding tray...")
        self._tray.hide()
        logger.info("Closing all windows...")
        from PyQt6.QtWidgets import QApplication
        QApplication.closeAllWindows()
        logger.info("Quitting application...")
        QApplication.quit()

    def _quit_app(self):
        self._force_exit()

    def closeEvent(self, event: QCloseEvent):
        event.ignore()
        self._force_exit()


def _format_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    elif n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    elif n < 1024 * 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MB"
    else:
        return f"{n / (1024 * 1024 * 1024):.2f} GB"
