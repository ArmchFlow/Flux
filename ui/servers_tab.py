import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QComboBox, QLineEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.subscription import SubscriptionManager
from core.proxy_parser import ProxyServer

logger = logging.getLogger(__name__)


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
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(8)

        title = QLabel("Servers")
        title.setObjectName("titleLabel")
        top_layout.addWidget(title)

        top_layout.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search servers...")
        self.search_input.setMaximumWidth(250)
        self.search_input.setMinimumHeight(30)
        self.search_input.textChanged.connect(self._on_search)
        top_layout.addWidget(self.search_input)

        protocol_filter = QComboBox()
        protocol_filter.addItem("All Protocols")
        protocol_filter.addItems(["vless", "vmess", "ss", "trojan", "hysteria2"])
        protocol_filter.currentTextChanged.connect(self._on_filter)
        protocol_filter.setMaximumWidth(150)
        protocol_filter.setMinimumHeight(30)
        top_layout.addWidget(protocol_filter)

        layout.addLayout(top_layout)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setObjectName("connectBtn")
        self.connect_btn.clicked.connect(self._on_connect)
        btn_layout.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setObjectName("disconnectBtn")
        self.disconnect_btn.clicked.connect(self._on_disconnect)
        self.disconnect_btn.hide()
        btn_layout.addWidget(self.disconnect_btn)

        ping_selected_btn = QPushButton("Ping Selected")
        ping_selected_btn.clicked.connect(self._on_ping_selected)
        btn_layout.addWidget(ping_selected_btn)

        ping_all_btn = QPushButton("Ping All")
        ping_all_btn.clicked.connect(self._on_ping_all)
        btn_layout.addWidget(ping_all_btn)

        self.auto_select_cb = QComboBox()
        self.auto_select_cb.addItem("Auto Select (URLTest)")
        self.auto_select_cb.addItem("Manual Select")
        self.auto_select_cb.setMaximumWidth(200)
        self.auto_select_cb.setMinimumHeight(30)
        self.auto_select_cb.currentIndexChanged.connect(self._on_auto_select_changed)
        btn_layout.addWidget(self.auto_select_cb)

        btn_layout.addStretch()

        self.status_label = QLabel("Disconnected")
        self.status_label.setObjectName("statusDisconnected")
        btn_layout.addWidget(self.status_label)

        layout.addLayout(btn_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Name", "Protocol", "Address", "Port", "Ping", "Subscription"
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.sectionClicked.connect(self._on_header_clicked)

        self.table.doubleClicked.connect(self._on_connect)

        layout.addWidget(self.table)

    def load_servers(self):
        self._servers = self.sub_manager.get_all_servers()
        logger.debug("ServersTab loading %d servers", len(self._servers))
        self._render_table(self._servers)

    def _render_table(self, servers: list[ProxyServer], filter_text: str = ""):
        self.table.setRowCount(0)

        for srv in servers:
            if filter_text:
                text = filter_text.lower()
                if (text not in srv.display_name.lower()
                        and text not in srv.server.lower()
                        and text not in srv.protocol.lower()):
                    continue

            row = self.table.rowCount()
            self.table.insertRow(row)

            name_item = QTableWidgetItem(srv.display_name)
            name_item.setData(Qt.ItemDataRole.UserRole, srv.tag)
            self.table.setItem(row, 0, name_item)

            self.table.setItem(row, 1, QTableWidgetItem(srv.protocol.upper()))
            self.table.setItem(row, 2, QTableWidgetItem(srv.server))
            self.table.setItem(row, 3, QTableWidgetItem(str(srv.port)))

            delay = self._delays.get(srv.tag, -1)
            if delay >= 0:
                ping_text = f"{delay} ms"
                if delay < 100:
                    ping_text = f"★ {ping_text}"
            else:
                ping_text = "—"
            self.table.setItem(row, 4, QTableWidgetItem(ping_text))

            self.table.setItem(row, 5, QTableWidgetItem(srv.subscription_tag))

    def update_delays(self, delays: dict[str, int]):
        logger.debug("Updating delays: %d results", len(delays))
        self._delays.update(delays)
        self._render_table(self._servers, self.search_input.text())

    def set_connected(self, connected: bool):
        self._connected = connected
        if connected:
            self.connect_btn.hide()
            self.disconnect_btn.show()
            self.status_label.setText("Connected")
            self.status_label.setObjectName("statusConnected")
        else:
            self.connect_btn.show()
            self.disconnect_btn.hide()
            self.status_label.setText("Disconnected")
            self.status_label.setObjectName("statusDisconnected")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def _on_connect(self):
        rows = {idx.row() for idx in self.table.selectedIndexes()}
        if not rows:
            logger.debug("Connect clicked with no selection")
            return

        row = rows.pop()
        name_item = self.table.item(row, 0)
        if name_item:
            tag = name_item.data(Qt.ItemDataRole.UserRole)
            logger.info("UI: Connect to server %s", tag)
            self.connect_requested.emit(tag)

    def _on_disconnect(self):
        logger.info("UI: Disconnect clicked")
        self.disconnect_requested.emit()

    def _on_ping_selected(self):
        rows = {idx.row() for idx in self.table.selectedIndexes()}
        logger.debug("Ping selected: %d rows selected", len(rows))
        for row in rows:
            name_item = self.table.item(row, 0)
            if name_item:
                tag = name_item.data(Qt.ItemDataRole.UserRole)
                self.ping_requested.emit(tag)

    def _on_ping_all(self):
        logger.info("UI: Ping all servers")
        self.ping_requested.emit("__all__")

    def _on_auto_select_changed(self, index: int):
        if index == 0:
            logger.info("UI: Auto select (URLTest) chosen")
            self.connect_requested.emit("__auto__")

    def _on_search(self, text: str):
        self._render_table(self._servers, text)

    def _on_filter(self, protocol: str):
        logger.debug("Filter changed to: %s", protocol)
        if protocol == "All Protocols":
            self._render_table(self._servers, self.search_input.text())
        else:
            filtered = [s for s in self._servers if s.protocol == protocol.lower()]
            self._render_table(filtered, self.search_input.text())

    def _on_header_clicked(self, col: int):
        if col != 4:
            return
        self._ping_sort_asc = not self._ping_sort_asc
        srv = sorted(
            self._servers,
            key=lambda s: self._delays.get(s.tag, 99999),
            reverse=not self._ping_sort_asc,
        )
        self._render_table(srv, self.search_input.text())
