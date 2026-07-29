import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QLineEdit, QMenu,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction

from core.subscription import SubscriptionManager
from core.proxy_parser import ProxyServer
from core.translations import tr

logger = logging.getLogger(__name__)

_COL_NAME = 0
_COL_PROTO = 1
_COL_PING = 2
_COL_SUB = 3

_ALL_PROTOCOLS = ["vless", "vmess", "ss", "trojan", "hysteria2"]


class ServersTab(QWidget):
    connect_requested = pyqtSignal(str)
    disconnect_requested = pyqtSignal()
    ping_requested = pyqtSignal(str)

    def __init__(self, sub_manager: SubscriptionManager, parent=None):
        super().__init__(parent)
        self.sub_manager = sub_manager
        self._servers: list[ProxyServer] = []
        self._delays: dict[str, int] = {}
        self._connected = False
        self._ping_sort_asc = True
        self._filter_proto = ""
        self._setup_ui()

    def _setup_ui(self):
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(8)

        title = QLabel(tr("servers"))
        title.setObjectName("titleLabel")
        vbox.addWidget(title)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self.connect_btn = QPushButton(tr("connect"))
        self.connect_btn.setObjectName("connectBtn")
        self.connect_btn.setMinimumHeight(30)
        self.connect_btn.clicked.connect(self._on_connect)
        btn_row.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton(tr("disconnect"))
        self.disconnect_btn.setObjectName("disconnectBtn")
        self.disconnect_btn.setMinimumHeight(30)
        self.disconnect_btn.clicked.connect(self._on_disconnect)
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
        btn_row.addWidget(ping_all_btn)

        btn_row.addStretch()
        vbox.addLayout(btn_row)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            tr("name"), tr("protocol"), tr("ping"), tr("subscription")
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)

        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.table.setColumnWidth(3, 110)
        header.sectionClicked.connect(self._on_header_clicked)
        self.table.doubleClicked.connect(self._on_connect)

        vbox.addWidget(self.table, 1)

    def load_servers(self):
        self._servers = self.sub_manager.get_all_servers()
        self._render_table(self._servers)

    def _render_table(self, servers: list[ProxyServer], filter_text: str = ""):
        self.table.setRowCount(0)
        for srv in servers:
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
            item = QTableWidgetItem(srv.display_name)
            item.setData(Qt.ItemDataRole.UserRole, srv.tag)
            self.table.setItem(row, _COL_NAME, item)
            pi = QTableWidgetItem(srv.protocol.upper())
            pi.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, _COL_PROTO, pi)
            d = self._delays.get(srv.tag, -1)
            if d >= 0:
                ping_text = f"{d} " + tr("ping_ms")
                if d < 100:
                    ping_text = f"\u2605 {ping_text}"
            else:
                ping_text = tr("dash")
            self.table.setItem(row, _COL_PING, QTableWidgetItem(ping_text))
            si = QTableWidgetItem(srv.subscription_tag)
            si.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, _COL_SUB, si)

    def update_delays(self, delays: dict[str, int]):
        self._delays.update(delays)
        self._render_table(self._servers, self.search_input.text())

    def set_connected(self, connected: bool):
        self._connected = connected
        if connected:
            self.connect_btn.hide()
            self.disconnect_btn.show()
        else:
            self.connect_btn.show()
            self.disconnect_btn.hide()

    def _selected_tag(self):
        r = {idx.row() for idx in self.table.selectedIndexes()}
        if not r:
            return None
        item = self.table.item(r.pop(), _COL_NAME)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_connect(self):
        tag = self._selected_tag()
        if tag:
            self.connect_requested.emit(tag)

    def _on_disconnect(self):
        self.disconnect_requested.emit()

    def _on_ping_all(self):
        self.ping_requested.emit("__all__")

    def _on_ping_server(self, tag: str):
        self.ping_requested.emit(tag)

    def _on_context_menu(self, pos):
        tag = self._selected_tag()
        if not tag:
            return
        menu = QMenu(self)
        a = menu.addAction(tr("ping_selected"))
        a.triggered.connect(lambda: self._on_ping_server(tag))
        menu.exec(self.table.viewport().mapToGlobal(pos))

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