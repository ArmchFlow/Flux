import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QLineEdit, QMenu, QStackedWidget,
)
from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QColor, QFont

from core.subscription import SubscriptionManager
from core.proxy_parser import ProxyServer
from core.flags import extract_flag
from core.translations import tr
from .animations import attach_press_feedback
from .widgets import EmptyStateWidget, TrailRingOverlay, PulseHitOverlay, SpeedTrailOverlay

logger = logging.getLogger(__name__)

_COL_FLAG = 0
_COL_NAME = 1
_COL_PROTO = 2
_COL_PING = 3
_COL_SUB = 4

_ALL_PROTOCOLS = ["vless", "vmess", "ss", "trojan", "hysteria2", "awg"]


class ServersTab(QWidget):
    connect_requested = pyqtSignal(str)
    disconnect_requested = pyqtSignal()
    ping_requested = pyqtSignal(str)
    speed_test_requested = pyqtSignal()

    def __init__(self, sub_manager: SubscriptionManager, parent=None):
        super().__init__(parent)
        self.sub_manager = sub_manager
        self._servers: list[ProxyServer] = []
        self._rows: list[ProxyServer] = []
        self._delays: dict[str, int] = {}
        self._connected = False
        self._connecting = False
        self._comet = None
        self._pulse_hit = None
        self._speed_comet = None
        self._ping_sort_asc = True
        self._filter_proto = ""
        self._pinned: set[str] = set()
        self._active_tag: str | None = None
        self._pinned_file = Path(sub_manager.data_dir) / "pinned.json"
        self._load_pinned()
        self._setup_ui()

    def _load_pinned(self):
        try:
            if self._pinned_file.exists():
                import json
                self._pinned = set(json.loads(self._pinned_file.read_text(encoding="utf-8")))
        except Exception:
            self._pinned = set()

    def _save_pinned(self):
        try:
            import json
            self._pinned_file.write_text(json.dumps(list(self._pinned)), encoding="utf-8")
        except Exception:
            pass

    def _setup_ui(self):
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(12, 12, 12, 12)
        vbox.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        title = QLabel(tr("servers"))
        title.setObjectName("titleLabel")
        header_row.addWidget(title)

        self.count_label = QLabel("")
        self.count_label.setObjectName("countLabel")
        self.count_label.hide()
        header_row.addWidget(self.count_label)

        header_row.addStretch()
        vbox.addLayout(header_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self.connect_btn = QPushButton(tr("connect"))
        self.connect_btn.setObjectName("connectBtn")
        self.connect_btn.setMinimumHeight(30)
        self.connect_btn.clicked.connect(self._on_connect)
        attach_press_feedback(self.connect_btn)
        btn_row.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton(tr("disconnect"))
        self.disconnect_btn.setObjectName("disconnectBtn")
        self.disconnect_btn.setMinimumHeight(30)
        self.disconnect_btn.clicked.connect(self._on_disconnect)
        attach_press_feedback(self.disconnect_btn)
        self.disconnect_btn.hide()
        btn_row.addWidget(self.disconnect_btn)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("search_servers"))
        self.search_input.setMaximumWidth(150)
        self.search_input.setMinimumHeight(30)
        self.search_input.textChanged.connect(self._on_search)
        filter_act = QAction("\u25be", self)
        filter_act.triggered.connect(self._on_filter_menu)
        self.search_input.addAction(filter_act, QLineEdit.ActionPosition.TrailingPosition)
        btn_row.addWidget(self.search_input)

        ping_all_btn = QPushButton(tr("ping_all"))
        ping_all_btn.setMinimumHeight(30)
        ping_all_btn.clicked.connect(self._on_ping_all)
        attach_press_feedback(ping_all_btn)
        btn_row.addWidget(ping_all_btn)

        self.speed_test_btn = QPushButton(tr("speed_test"))
        self.speed_test_btn.setMinimumHeight(30)
        self.speed_test_btn.setToolTip(tr("speed_test_note"))
        self.speed_test_btn.setEnabled(False)
        self.speed_test_btn.clicked.connect(self._on_speed_test)
        attach_press_feedback(self.speed_test_btn)
        btn_row.addWidget(self.speed_test_btn)

        btn_row.addStretch()
        vbox.addLayout(btn_row)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "", tr("name"), tr("protocol"), tr("ping"), tr("subscription")
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)

        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.table.setColumnWidth(0, 44)
        self.table.setColumnWidth(4, 110)
        header.sectionClicked.connect(self._on_header_clicked)
        self.table.doubleClicked.connect(self._on_double_click)

        self._empty_state = EmptyStateWidget()
        self._empty_state.set_texts(tr("no_servers_title"), tr("no_servers_subtitle"))

        self._stack = QStackedWidget()
        self._stack.addWidget(self.table)
        self._stack.addWidget(self._empty_state)
        vbox.addWidget(self._stack, 1)

    def load_servers(self):
        self._servers = self.sub_manager.get_all_servers()
        self._render_table(self._servers)

    def _render_table(self, servers: list[ProxyServer], filter_text: str = ""):
        self.table.setRowCount(0)
        self._rows = []

        def match(s):
            if self._filter_proto and s.protocol.lower() != self._filter_proto:
                return False
            if filter_text:
                t = filter_text.lower()
                return (t in s.display_name.lower() or t in s.server.lower()
                        or t in s.protocol.lower())
            return True

        pinned = [s for s in servers if s.tag in self._pinned and match(s)]
        unpinned = [s for s in servers if s.tag not in self._pinned and match(s)]

        for srv in pinned + unpinned:
            if self._filter_proto and srv.protocol.lower() != self._filter_proto:
                continue
            if filter_text:
                t = filter_text.lower()
                if (t not in srv.display_name.lower()
                        and t not in srv.server.lower()
                        and t not in srv.protocol.lower()):
                    continue
            row = self.table.rowCount()
            self.table.insertRow(row)
            self._rows.append(srv)

            flag, display_name = extract_flag(srv.display_name)
            if flag:
                flag_label = QLabel(flag)
                flag_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                flag_label.setFont(QFont("Segoe UI Emoji", 14))
                self.table.setCellWidget(row, _COL_FLAG, flag_label)

            item = QTableWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, srv.tag)
            if srv.tag == self._active_tag:
                item.setText(f"{display_name}   {tr('connected_marker')}")
                item.setForeground(QColor("#a6e3a1"))
            self.table.setItem(row, _COL_NAME, item)
            pi = QTableWidgetItem(srv.protocol.upper())
            if srv.protocol == "awg" and srv.encryption:
                pi = QTableWidgetItem(srv.encryption.upper())
            pi.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            pi.setFlags(pi.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, _COL_PROTO, pi)
            d = self._delays.get(srv.tag, -1)
            if d >= 0:
                ping_text = f"{d} " + tr("ping_ms")
                if d < 100:
                    ping_text = f"\u2605 {ping_text}"
            else:
                ping_text = tr("dash")
            self.table.setItem(row, _COL_PING, QTableWidgetItem(ping_text))
            pi = self.table.item(row, _COL_PING)
            if pi:
                pi.setFlags(pi.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if d >= 0:
                    if d < 100:
                        pi.setForeground(QColor("#a6e3a1"))
                    elif d < 300:
                        pi.setForeground(QColor("#f9e2af"))
                    else:
                        pi.setForeground(QColor("#f38ba8"))
            si = QTableWidgetItem(srv.subscription_tag)
            si.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            si.setFlags(si.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, _COL_SUB, si)

            if srv.tag == self._active_tag:
                tint = QColor(162, 227, 161, 28)
                for col in range(self.table.columnCount()):
                    it = self.table.item(row, col)
                    if it:
                        it.setBackground(tint)

        count = self.table.rowCount()
        if count:
            self.count_label.setText(f"{tr('servers_total')} {count}")
            self.count_label.show()
        else:
            self.count_label.hide()

        if count == 0:
            self._stack.setCurrentWidget(self._empty_state)
        else:
            self._stack.setCurrentWidget(self.table)

    def update_delays(self, delays: dict[str, int]):
        self._delays.update(delays)
        self._render_table(self._servers, self.search_input.text())

    def _repolish_connect_btn(self):
        self.connect_btn.style().unpolish(self.connect_btn)
        self.connect_btn.style().polish(self.connect_btn)

    def set_connected(self, connected: bool):
        self._connected = connected
        self.speed_test_btn.setEnabled(connected)
        self.speed_test_btn.setToolTip(
            "" if connected else tr("speed_test_note"))
        if connected:
            if self._comet is not None:
                self._comet.fade_out(250)
            if self._pulse_hit is None:
                self._pulse_hit = PulseHitOverlay(self.connect_btn)
            self._pulse_hit.play()
            QTimer.singleShot(260, self._swap_to_disconnect)
        else:
            if self._comet is not None:
                self._comet.stop()
            if self._pulse_hit is not None:
                self._pulse_hit.stop()
            self.connect_btn.show()
            self.disconnect_btn.hide()

    def _swap_to_disconnect(self):
        if not self._connected:
            return
        self.connect_btn.hide()
        self.disconnect_btn.show()

    def set_active_server(self, tag: str | None):
        if self._active_tag == tag:
            return
        self._active_tag = tag
        self._render_table(self._servers, self.search_input.text())

    def set_connecting(self, connecting: bool):
        if connecting:
            self.connect_btn.setText(tr("connecting"))
            self.connect_btn.setEnabled(False)
            self.connect_btn.setProperty("connecting", True)
            self._repolish_connect_btn()
            if self._comet is None:
                self._comet = TrailRingOverlay(self.connect_btn)
            self._comet.start()
        else:
            self.connect_btn.setText(tr("connect"))
            self.connect_btn.setEnabled(True)
            self.connect_btn.setProperty("connecting", False)
            self._repolish_connect_btn()
            if self._comet is not None:
                self._comet.stop()

    def _selected_tag(self):
        r = {idx.row() for idx in self.table.selectedIndexes()}
        if not r:
            return None
        row = r.pop()
        if row < len(self._rows):
            return self._rows[row].tag
        return None

    def _on_connect(self):
        tag = self._selected_tag()
        if tag:
            self.connect_requested.emit(tag)

    def _on_double_click(self, index):
        row = index.row()
        if row < len(self._rows):
            tag = self._rows[row].tag
            self.connect_requested.emit(tag)

    def _on_disconnect(self):
        self.disconnect_requested.emit()

    def _on_ping_all(self):
        self.ping_requested.emit("__all__")

    def set_speed_testing(self, testing: bool):
        self.speed_test_btn.setEnabled(not testing and self._connected)
        if testing:
            self.speed_test_btn.setText(tr("speed_testing"))
            if self._speed_comet is None:
                self._speed_comet = SpeedTrailOverlay(self.speed_test_btn)
            self._speed_comet.start()
        else:
            self.speed_test_btn.setText(tr("speed_test"))
            if self._speed_comet is not None:
                self._speed_comet.stop()

    def _on_speed_test(self):
        self.speed_test_requested.emit()

    def _on_ping_server(self, tag: str):
        self.ping_requested.emit(tag)

    def _on_context_menu(self, pos):
        tag = self._selected_tag()
        if not tag:
            return
        menu = QMenu(self)
        ping_action = menu.addAction(tr("ping_selected"))
        ping_action.triggered.connect(lambda: self._on_ping_server(tag))
        if tag in self._pinned:
            pin_action = menu.addAction(tr("unpin"))
            pin_action.triggered.connect(lambda: self._toggle_pin(tag))
        else:
            pin_action = menu.addAction(tr("pin"))
            pin_action.triggered.connect(lambda: self._toggle_pin(tag))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _toggle_pin(self, tag: str):
        if tag in self._pinned:
            self._pinned.discard(tag)
        else:
            self._pinned.add(tag)
        self._save_pinned()
        self._render_table(self._servers, self.search_input.text())

    def _on_search(self, text: str):
        self._render_table(self._servers, text)

    def _on_filter_menu(self):
        menu = QMenu(self.search_input)
        all_act = menu.addAction(tr("all_protocols"))
        all_act.setCheckable(True)
        all_act.setChecked(self._filter_proto == "")
        all_act.triggered.connect(lambda: self._set_filter(""))
        menu.addSeparator()
        for p in _ALL_PROTOCOLS:
            a = menu.addAction(p.upper())
            a.setCheckable(True)
            a.setChecked(self._filter_proto == p)
            a.triggered.connect(lambda _, x=p: self._set_filter(x))
        menu.exec(self.search_input.mapToGlobal(
            self.search_input.rect().bottomRight()))

    def _set_filter(self, proto: str):
        self._filter_proto = proto
        self._render_table(self._servers, self.search_input.text())

    def _on_header_clicked(self, col: int):
        if col != _COL_PING:
            return
        sel = self._selected_tag()
        self._ping_sort_asc = not self._ping_sort_asc
        yes = [s for s in self._servers if self._delays.get(s.tag, -1) >= 0]
        no = [s for s in self._servers if self._delays.get(s.tag, -1) < 0]
        yes.sort(key=lambda s: self._delays.get(s.tag, 0))
        if not self._ping_sort_asc:
            yes.reverse()
        self._servers = yes + no
        self._render_table(self._servers, self.search_input.text())
        if sel:
            for row in range(self.table.rowCount()):
                if self.table.item(row, _COL_NAME) and self.table.item(row, _COL_NAME).data(Qt.ItemDataRole.UserRole) == sel:
                    self.table.selectRow(row)
                    break