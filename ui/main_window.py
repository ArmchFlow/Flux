import json
import logging
import sys
import threading
import subprocess
import time
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget,
    QStatusBar, QLabel, QPushButton, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QCloseEvent, QIcon

from .sub_tab import SubscriptionTab
from .servers_tab import ServersTab
from .settings_tab import SettingsTab
from .log_tab import LogTab
from .tray import SystemTray
from .styles import DARK_STYLE
from .animations import ToastManager
from .widgets import StatusIndicator

from core.subscription import SubscriptionManager
from core.settings_manager import SettingsManager
from core.dual_mgr import DualManager
from core.config_builder import build_xray_proxy_config
from core.traffic_monitor import TrafficMonitor
from core.translations import tr
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

_DOWNLOAD_TEST_URL = "https://speed.cloudflare.com/__down?bytes=15728640"
_UPLOAD_TEST_URL = "https://speed.cloudflare.com/__up"
_UPLOAD_TEST_BYTES = 10 * 1024 * 1024
_RECONNECT_MAX_ATTEMPTS = 3
_RECONNECT_DELAY_MS = 3000


class _VpnSignals(QObject):
    done = pyqtSignal(bool, str, int)


class _SpeedSignals(QObject):
    done = pyqtSignal(bool, str)


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
        self._active_tag = None
        self._connecting = False
        self._reconnect_attempts = 0
        self._auto_reconnecting = False
        self._vpn_sig = _VpnSignals()
        self._vpn_sig.done.connect(self._on_connect_done)
        self._speed_sig = _SpeedSignals()
        self._speed_sig.done.connect(self._on_speed_done)
        self._traffic = TrafficMonitor()

        if sys.platform == "win32":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            hwnd = kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)

        logger.info("Initializing MainWindow...")
        self.setWindowTitle("Flux")
        try:
            _base = Path(sys._MEIPASS)
        except AttributeError:
            _base = Path(__file__).parent.parent
        for _p in [_base / "bin" / "flux.ico", _base / "Flux light 2.png"]:
            if _p.exists():
                self.setWindowIcon(QIcon(str(_p.resolve())))
                break
        self.setMinimumSize(640, 480)
        self.resize(960, 680)
        self.setStyleSheet(DARK_STYLE)

        self._tray = SystemTray(self)
        self._tray.show_window_requested.connect(self._show_from_tray)
        self._tray.quit_requested.connect(self._quit_app)
        self._tray.connect_requested.connect(self._on_connect_from_tray)
        self._tray.disconnect_requested.connect(self._on_disconnect_from_tray)
        self._tray.quick_connect_requested.connect(self._on_quick_connect)
        self._tray.recent_selected.connect(self._on_recent_selected)
        self._tray.menu.aboutToShow.connect(self._refresh_tray_recent)
        self._last_tag, self._recent = self._load_last_server()
        self._tray.set_quick_connect_enabled(self._last_tag is not None)

        self._setup_ui()
        self._setup_statusbar()

        self._toasts = ToastManager.instance(self)

        self._ping_timer = QTimer(self)
        self._ping_timer.timeout.connect(self._auto_refresh_status)
        self._ping_timer.start(10000)

        self._traffic_timer = QTimer(self)
        self._traffic_timer.timeout.connect(self._update_traffic)
        self._traffic_timer.start(1000)

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
        self._servers_tab.speed_test_requested.connect(self._on_speed_test)
        self._tabs.addTab(self._servers_tab, tr("tab_servers"))

        self._sub_tab = SubscriptionTab(self.sub_manager)
        self._sub_tab.update_requested.connect(self._on_update_sub)
        self._sub_tab.batch_update_requested.connect(self._on_update_all_subs)
        self._sub_tab.add_requested.connect(self._on_add_sub)
        self._sub_tab.conf_imported.connect(self._on_conf_imported)
        self._sub_tab.export_requested.connect(self._on_export_subs)
        self._sub_tab.import_requested.connect(self._on_import_subs)
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

        self._status_dot = StatusIndicator(10, "#f38ba8")
        status.addWidget(self._status_dot)

        self._status_text = QLabel(" " + tr("ready"))
        status.addWidget(self._status_text)

        self._traffic_label = QLabel("")
        status.addPermanentWidget(self._traffic_label)

        self.setStatusBar(status)
        logger.debug("Status bar ready")

    def _set_status_dot(self, state: str):
        if state == "connected":
            self._status_dot.set_color("#a6e3a1")
            self._status_dot.set_pulsing(True, speed=1.5)
        elif state == "connecting":
            self._status_dot.set_color("#f9e2af")
            self._status_dot.set_pulsing(True, speed=2.0)
        else:
            self._status_dot.set_color("#f38ba8")
            self._status_dot.set_pulsing(False)

    def _on_update_sub(self, url: str):
        logger.info("UI: update requested for subscription: %s", url[:80])
        sel_tag = None
        rows = {idx.row() for idx in self._servers_tab.table.selectedIndexes()}
        if rows:
            item = self._servers_tab.table.item(rows.pop(), 0)
            if item:
                sel_tag = item.data(Qt.ItemDataRole.UserRole)
        self._status_text.setText(" " + tr("updating_sub").format(url[:60]))
        try:
            servers = self.sub_manager.update_subscription(url)
            self._sub_tab.refresh_after_update()
            self._servers_tab.load_servers()
            if sel_tag:
                for r in range(self._servers_tab.table.rowCount()):
                    it = self._servers_tab.table.item(r, 0)
                    if it and it.data(Qt.ItemDataRole.UserRole) == sel_tag:
                        self._servers_tab.table.selectRow(r)
                        break
            logger.info("Subscription updated: %d servers from %s", len(servers), url[:60])
            self._status_text.setText(" " + tr("sub_updated_count").format(len(servers)))
            self._toasts.show(f"{tr('subscription_updated')}: {len(servers)}", "success", 2500)
        except Exception as e:
            logger.error("Subscription update failed: %s", e, exc_info=True)
            QMessageBox.critical(
                self, tr("update_error"),
                f"{tr('update_err_msg')}:\n{e}",
            )
            self._status_text.setText(" " + tr("update_failed"))

    def _on_update_all_subs(self, urls: list):
        self._status_text.setText(" " + tr("updating_all_subs"))
        total = len(urls)
        def _work():
            try:
                for i, url in enumerate(urls, 1):
                    QTimer.singleShot(0, lambda i=i: self._status_text.setText(
                        " " + tr("updating_sub_n_of").format(i, total)))
                    try:
                        self.sub_manager.update_subscription(url)
                    except Exception as e:
                        logger.error("Update failed for %s: %s", url[:60], e)
            finally:
                QTimer.singleShot(0, self._refresh_after_all_update)
        threading.Thread(target=_work, daemon=True).start()

    def _refresh_after_all_update(self):
        sel_tag = None
        rows = {idx.row() for idx in self._servers_tab.table.selectedIndexes()}
        if rows:
            item = self._servers_tab.table.item(rows.pop(), 0)
            if item:
                sel_tag = item.data(Qt.ItemDataRole.UserRole)
        self._sub_tab.refresh_after_update()
        self._servers_tab.load_servers()
        if sel_tag:
            for r in range(self._servers_tab.table.rowCount()):
                it = self._servers_tab.table.item(r, 0)
                if it and it.data(Qt.ItemDataRole.UserRole) == sel_tag:
                    self._servers_tab.table.selectRow(r)
                    break
        self._status_text.setText(" " + tr("all_subs_updated"))
        self._toasts.show(tr("subscription_updated"), "success", 2500)

    def _on_add_sub(self, url: str, name: str):
        logger.info("UI: add subscription requested: url=%s, name=%s", url[:80], name or "(auto)")
        self._status_text.setText(" " + tr("fetching_sub").format(url[:60]))
        try:
            servers = self.sub_manager.update_subscription(url)
            self._sub_tab.refresh_after_update()
            self._servers_tab.load_servers()
            logger.info("Subscription added: %s → %d servers", url[:60], len(servers))
            self._status_text.setText(" " + tr("sub_added_count").format(len(servers)))
            self._toasts.show(f"{tr('subscription_added')}: {len(servers)}", "success", 2500)
        except Exception as e:
            logger.error("Failed to add subscription: %s", e, exc_info=True)
            self._status_text.setText(" " + tr("fetch_failed"))
            QMessageBox.critical(
                self, tr("error"),
                f"{tr('fetch_err_msg')}\n\n{e}",
            )

    def _on_conf_imported(self, filepath: str):
        logger.info("UI: importing AWG config: %s", filepath)
        try:
            srv = self.sub_manager.import_conf_file(filepath)
            if srv:
                self._servers_tab.load_servers()
                self._status_text.setText(" " + tr("imported_name").format(srv.name))
                self._toasts.show(tr("config_imported"), "success", 2500)
        except Exception as e:
            logger.error("Import AWG config failed: %s", e, exc_info=True)
            QMessageBox.critical(self, tr("error"), f"{tr('import_conf_failed')}\n{e}")

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

    def _connect_vpn(self, *, auto: bool = False):
        logger.info("=== CONNECTING VPN ===")
        if self._connecting:
            logger.info("Already connecting, skipping")
            return
        if not auto:
            self._reconnect_attempts = 0
        self._connecting = True
        self._status_text.setText(" " + tr("connecting"))
        self._set_status_dot("connecting")
        self._servers_tab.set_connecting(True)

        servers = self.sub_manager.get_all_servers()
        logger.info("Servers available for connection: %d", len(servers))

        if not servers:
            logger.warning("No servers available for connection")
            QMessageBox.warning(self, tr("no_servers_title"), tr("no_servers"))
            self._status_text.setText(" " + tr("no_servers_title"))
            self._connecting = False
            self._servers_tab.set_connecting(False)
            return

        if self.settings_mgr.settings.proxy.auto_select and self._current_proxy_tag == "auto":
            selected_tag = servers[0].tag
        else:
            selected_tag = (
                self._current_proxy_tag if self._current_proxy_tag != "auto"
                else servers[0].tag
            )

        srv = next((s for s in servers if s.tag == selected_tag), None)
        if not srv:
            self._connecting = False
            self._servers_tab.set_connecting(False)
            return

        self._active_tag = selected_tag
        self._status_text.setText(" " + tr("connecting_to").format(srv.display_name))

        if srv.protocol == "awg":
            self._start_awg(srv)
            return

        logger.info("Building xray config for %s...", selected_tag)
        try:
            xray_cfg = build_xray_proxy_config(servers, selected_tag)
        except Exception as e:
            logger.error("Config build failed: %s", e, exc_info=True)
            QMessageBox.critical(self, tr("config_error"), str(e))
            self._status_text.setText(" " + tr("config_error"))
            self._connecting = False
            self._servers_tab.set_connecting(False)
            return

        def _work():
            success, mode = self.xray_mgr.start(xray_cfg, self.settings_mgr.settings)
            self._vpn_sig.done.emit(success, mode, len(servers))

        threading.Thread(target=_work, daemon=True).start()

    @staticmethod
    def _get_physical_gateway() -> str:
        try:
            import subprocess
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-NetRoute -DestinationPrefix '0.0.0.0/0' "
                 "| Select-Object -First 1 -ExpandProperty NextHop"],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return r.stdout.strip()
        except Exception:
            return ""

    def _start_awg(self, srv):
        addr = ""
        dns = "1.1.1.1"
        endpoint_ip = ""
        for line in srv.awg_raw.splitlines():
            s = line.strip().lower()
            if s.startswith("address") and "=" in s:
                addr = s.split("=", 1)[1].strip().split(",")[0].strip()
            if s.startswith("dns") and "=" in s:
                raw_dns = s.split("=", 1)[1].strip().split(",")[0].strip()
                if raw_dns:
                    dns = raw_dns
            if s.startswith("endpoint") and "=" in s:
                ep = s.split("=", 1)[1].strip()
                if ":" in ep:
                    endpoint_ip = ep.rsplit(":", 1)[0]
                else:
                    endpoint_ip = ep
        tun_ip = addr.split("/")[0] if addr else ""

        conf_path = self.data_dir / f"awg_{srv.tag}.conf"
        conf_path.write_bytes(srv.awg_raw.encode("utf-8"))
        self.xray_mgr.init_amnezia(self.xray_mgr.sb_path.parent)


        def _work():
            ok = False
            msg = ""
            try:
                logger.info("=== STARTING AMNEZIA WG (async) ===")
                ok, msg = self.xray_mgr.start_amnezia(str(conf_path))
                if ok:
                    logger.info("=== AMNEZIA WG OK, configuring anti-lockout route ===")
                    nf = subprocess.CREATE_NO_WINDOW

                    if endpoint_ip:
                        gw = self._get_physical_gateway()
                        if gw:
                            try:
                                subprocess.run(["route", "add", endpoint_ip, "mask",
                                               "255.255.255.255", gw, "metric", "1"],
                                              capture_output=True, timeout=30, creationflags=nf)
                                logger.info("Anti-lockout route: %s via %s",
                                            endpoint_ip, gw)
                            except subprocess.TimeoutExpired:
                                logger.warning("Anti-lockout route add timed out (30s), continuing anyway")
                            except Exception as e:
                                logger.warning("Anti-lockout route add failed: %s", e)
                    logger.info("=== AMNEZIA WG anti-lockout configured ===")
                else:
                    logger.error("=== AMNEZIA WG failed: %s ===", msg)
            except Exception as e:
                logger.exception("AMNEZIA WG thread error: %s", e)
                ok, msg = False, f"Thread error: {e}"
            finally:
                self._vpn_sig.done.emit(ok, msg, 0)

        threading.Thread(target=_work, daemon=True).start()

    def _on_connect_done(self, success: bool, mode: str, count: int):
        if not self._connecting:
            return
        self._connecting = False
        self._servers_tab.set_connecting(False)
        if success:
            self._reconnect_attempts = 0
            self._auto_reconnecting = False
            self.set_connected(True)
            self._set_status_dot("connected")
            self._traffic.start()
            self._save_last_server(self._active_tag)
            if mode == "AWG":
                self._status_text.setText(" " + tr("connected_tun") + " (AWG)")
                self._toasts.show(tr("connected_tun") + " (AWG)", "success", 2500)
                logger.info("=== CONNECTED (AWG) ===")
            else:
                self._status_text.setText(" " + tr("connected_tun") + f" ({count} " + tr("servers_count").lower() + ")")
                self._toasts.show(tr("connected_tun"), "success", 2500)
                logger.info("=== CONNECTED (%s) ===", mode)
        else:
            logger.error("=== CONNECTION FAILED ===")
            self._set_status_dot("disconnected")
            QMessageBox.critical(self, tr("connection_failed"), mode or tr("could_not_start"))
            self._status_text.setText(" " + tr("connection_failed"))

    def _disconnect_vpn(self):
        logger.info("=== DISCONNECTING ===")
        self._connecting = False
        self._auto_reconnecting = False
        self._reconnect_attempts = 0
        self._traffic.stop()
        self._servers_tab.set_connecting(False)
        self.xray_mgr.stop()
        self.set_connected(False)
        self._set_status_dot("disconnected")
        self._status_text.setText(" " + tr("disconnected"))
        self._toasts.show(tr("disconnected"), "info", 2000)

    def set_connected(self, connected: bool):
        logger.debug("Connection state change: %s -> %s", self._connected, connected)
        self._connected = connected
        self._servers_tab.set_connected(connected)
        self._tray.set_connected(connected)
        self._tray.set_quick_connect_enabled(not connected and self._last_tag is not None)

    def _load_last_server(self):
        try:
            import json
            f = Path(self.data_dir) / "last_server.json"
            if f.exists():
                data = json.loads(f.read_text(encoding="utf-8"))
                return data.get("last"), list(data.get("recent", []))
        except Exception:
            pass
        return None, []

    def _save_last_server(self, tag: str):
        try:
            import json
            recent = [tag] + [t for t in self._recent if t != tag][:4]
            f = Path(self.data_dir) / "last_server.json"
            f.write_text(json.dumps({"last": tag, "recent": recent}), encoding="utf-8")
            self._last_tag = tag
            self._recent = recent
            self._tray.set_quick_connect_enabled(not self._connected)
        except Exception:
            pass

    def _refresh_tray_recent(self):
        try:
            names = {}
            for s in self.sub_manager.get_all_servers():
                names[s.tag] = s.display_name
            recent = [(t, names.get(t, t)) for t in self._recent]
            self._tray.set_recent_servers(recent)
        except Exception:
            pass

    def _on_quick_connect(self):
        logger.info("Tray: quick connect requested")
        if self._connected or not self._last_tag:
            return
        self._current_proxy_tag = self._last_tag
        self._connect_vpn()

    def _on_recent_selected(self, tag: str):
        logger.info("Tray: recent server selected: %s", tag)
        if self._connected:
            return
        self._current_proxy_tag = tag
        self._connect_vpn()

    def _on_ping_servers(self, tag: str):
        logger.info("UI: ping requested: %s", tag)

        if tag == "__all__":
            servers = self.sub_manager.get_all_servers()
            self._status_text.setText(" " + tr("testing_all"))
            logger.info("TCP pinging %d servers...", len(servers))
            delays = self.xray_mgr.tcp_ping_servers(servers, timeout=2.0)
            self._servers_tab.update_delays(delays)
            ok = sum(1 for v in delays.values() if v >= 0)
            self._status_text.setText(" " + tr("ping_complete_count").format(ok, len(delays)))
            logger.info("Ping all: %d/%d responded", ok, len(delays))
        else:
            servers = self.sub_manager.get_all_servers()
            srv = next((s for s in servers if s.tag == tag), None)
            if srv:
                delay = self.xray_mgr.tcp_ping(srv.server, srv.port)
                self._servers_tab.update_delays({tag: delay})
                status = f"{delay} {tr('ping_ms')}" if delay >= 0 else tr("timeout")
                self._status_text.setText(f" {tag}: {status}")
                logger.info("Ping %s: %s", tag, status)

    def _on_settings_changed(self):
        logger.info("Settings changed by user")
        if self._connected:
            logger.info("VPN is connected, asking about restart...")
            reply = QMessageBox.question(
                self, tr("restart_required"), tr("restart_msg"),
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
                self._traffic.stop()
                self._set_status_dot("disconnected")
                self._status_text.setText(" " + tr("connection_lost"))
                self._toasts.show(tr("connection_lost"), "error", 3000)
                if (self.settings_mgr.settings.auto_reconnect
                        and self._last_tag):
                    self._try_reconnect()
        except Exception:
            pass

    def _try_reconnect(self):
        if self._reconnect_attempts >= _RECONNECT_MAX_ATTEMPTS:
            logger.warning("Auto-reconnect exhausted all attempts")
            self._reconnect_attempts = 0
            self._status_text.setText(" " + tr("reconnect_failed"))
            self._toasts.show(tr("reconnect_failed"), "error", 3000)
            return
        self._reconnect_attempts += 1
        logger.info("Auto-reconnect attempt %d/%d",
                    self._reconnect_attempts, _RECONNECT_MAX_ATTEMPTS)
        self._status_text.setText(" " + tr("reconnecting").format(
            self._reconnect_attempts, _RECONNECT_MAX_ATTEMPTS))
        self._toasts.show(tr("reconnecting").format(
            self._reconnect_attempts, _RECONNECT_MAX_ATTEMPTS), "info", 2000)
        QTimer.singleShot(_RECONNECT_DELAY_MS, self._do_reconnect)

    def _do_reconnect(self):
        if self._connected or self._connecting:
            self._reconnect_attempts = 0
            return
        self._auto_reconnecting = True
        self._current_proxy_tag = self._last_tag
        self._connect_vpn(auto=True)

    def _update_traffic(self):
        up, down, total_up, total_down, secs = self._traffic.snapshot()
        if not self._traffic.is_running:
            self._traffic_label.setText("")
            return
        speed_up = f"{_format_bytes(up)}/s"
        speed_down = f"{_format_bytes(down)}/s"
        text = tr("traffic_label").format(
            speed_down, speed_up,
            _format_bytes(total_down), _format_bytes(total_up),
            _format_uptime(secs),
        )
        self._traffic_label.setText(text)

    def _on_speed_test(self):
        logger.info("Speed test requested")
        if not self._connected:
            self._toasts.show(tr("speed_test_note"), "warning", 2000)
            return
        self._servers_tab.set_speed_testing(True)
        self._status_text.setText(" " + tr("speed_testing"))

        def _work():
            try:
                down = _measure_download()
                up = _measure_upload()
                self._speed_sig.done.emit(
                    True, tr("speed_result").format(
                        f"{down:.2f}", f"{up:.2f}"))
            except Exception as e:
                logger.error("Speed test failed: %s", e)
                self._speed_sig.done.emit(False, tr("speed_timeout"))

        threading.Thread(target=_work, daemon=True).start()

    def _on_speed_done(self, success: bool, msg: str):
        self._servers_tab.set_speed_testing(False)
        self._status_text.setText(" " + msg)
        if success:
            self._toasts.show(msg, "success", 4000)
        else:
            self._toasts.show(msg, "error", 3000)

    def _on_export_subs(self, path: str):
        logger.info("Exporting subscriptions backup to %s", path)
        try:
            data = [s.to_dict() for s in self.sub_manager.subscriptions]
            Path(path).write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self._toasts.show(tr("exported_ok"), "success", 2500)
        except Exception as e:
            logger.error("Export failed: %s", e, exc_info=True)
            QMessageBox.critical(self, tr("error"), f"{tr('export_failed')}\n{e}")

    def _on_import_subs(self, path: str):
        logger.info("Importing subscriptions from %s", path)
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(data, list):
                raise ValueError("Bad backup format")
            existing = {s.url for s in self.sub_manager.subscriptions}
            added = 0
            for item in data:
                url = item.get("url") if isinstance(item, dict) else None
                if not url or url in existing:
                    continue
                self.sub_manager.add_subscription(url, item.get("name") or "")
                existing.add(url)
                added += 1
            self._sub_tab.refresh_after_update()
            self._servers_tab.load_servers()
            self._toasts.show(
                tr("imported_ok_count").format(added), "success", 2500)
        except Exception as e:
            logger.error("Import failed: %s", e, exc_info=True)
            QMessageBox.critical(self, tr("error"), f"{tr('import_failed')}\n{e}")

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
        self._traffic.stop()
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


def _format_uptime(secs: int) -> str:
    if secs <= 0:
        return "00:00:00"
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _measure_download(timeout: float = 45.0) -> float:
    import urllib.request
    start = time.perf_counter()
    size = 0
    req = urllib.request.Request(
        _DOWNLOAD_TEST_URL, headers={"User-Agent": "Flux/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        while True:
            chunk = r.read(65536)
            if not chunk:
                break
            size += len(chunk)
    dt = time.perf_counter() - start
    if dt <= 0:
        return 0.0
    return size / 1024 / 1024 / dt


def _measure_upload(timeout: float = 45.0) -> float:
    import urllib.request
    payload = b"x" * _UPLOAD_TEST_BYTES
    req = urllib.request.Request(
        _UPLOAD_TEST_URL, data=payload, method="POST",
        headers={
            "User-Agent": "Flux/1.0",
            "Content-Type": "application/octet-stream",
        })
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        r.read()
    dt = time.perf_counter() - start
    if dt <= 0:
        return 0.0
    return _UPLOAD_TEST_BYTES / 1024 / 1024 / dt
