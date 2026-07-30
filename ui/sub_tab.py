import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QMessageBox, QMenu,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QFileDialog

from core.subscription import SubscriptionManager, Subscription
from core.translations import tr

logger = logging.getLogger(__name__)


class SubscriptionTab(QWidget):
    update_requested = pyqtSignal(str)
    batch_update_requested = pyqtSignal(list)
    add_requested = pyqtSignal(str, str)
    conf_imported = pyqtSignal(str)

    def __init__(self, sub_manager: SubscriptionManager, parent=None):
        super().__init__(parent)
        self.sub_manager = sub_manager
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel(tr("subscription_mgmt"))
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        add_layout = QHBoxLayout()
        add_layout.setSpacing(8)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(tr("url_placeholder"))
        self.url_input.setMinimumHeight(36)
        self.url_input.setMinimumWidth(200)
        add_layout.addWidget(self.url_input, 1)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(tr("name_placeholder"))
        self.name_input.setMinimumHeight(36)
        self.name_input.setMaximumWidth(140)
        add_layout.addWidget(self.name_input)

        add_btn = QPushButton(tr("add_subscription"))
        add_btn.setObjectName("successBtn")
        add_btn.setMinimumHeight(36)
        add_btn.clicked.connect(self._on_add)
        add_layout.addWidget(add_btn)

        import_btn = QPushButton(tr("import_awg"))
        import_btn.setMinimumHeight(36)
        import_btn.clicked.connect(self._on_import_conf)
        add_layout.addWidget(import_btn)

        layout.addLayout(add_layout)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        update_all_btn = QPushButton(tr("update_all"))
        update_all_btn.clicked.connect(self._on_update_all)
        btn_layout.addWidget(update_all_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            tr("name"), tr("url"), tr("last_updated"),
            tr("servers_count"), tr("status")
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.cellChanged.connect(self._on_cell_changed)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        self.table.setColumnWidth(0, 160)

        layout.addWidget(self.table)

    def _load_data(self):
        self.table.blockSignals(True)
        try:
            self.table.setRowCount(0)
            from PyQt6.QtCore import Qt

            for sub in self.sub_manager.subscriptions:
                row = self.table.rowCount()
                self.table.insertRow(row)

                ni = QTableWidgetItem(sub.display_name)
                self.table.setItem(row, 0, ni)

                ui = QTableWidgetItem(sub.url)
                ui.setFlags(ui.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 1, ui)

                from datetime import datetime
                if sub.last_updated > 0:
                    dt = datetime.fromtimestamp(sub.last_updated)
                    updated = dt.strftime("%Y-%m-%d %H:%M")
                else:
                    updated = tr("never")
                ut = QTableWidgetItem(updated)
                ut.setFlags(ut.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 2, ut)

                sc = QTableWidgetItem(str(len(self.sub_manager.get_cached_servers(sub.url))))
                sc.setFlags(sc.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 3, sc)

                st = QTableWidgetItem(
                    tr("active") if sub.enabled else tr("disabled")
                )
                st.setFlags(st.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 4, st)
        finally:
            self.table.blockSignals(False)

    def _on_add(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, tr("error"), tr("add_sub_error"))
            return

        name = self.name_input.text().strip()
        logger.info("UI: Adding new subscription: url=%s, name=%s", url[:80], name or "(auto)")

        try:
            sub = self.sub_manager.add_subscription(url, name)
            self.add_requested.emit(url, name)
            self.url_input.clear()
            self.name_input.clear()
            self._load_data()
        except Exception as e:
            logger.error("Failed to add subscription via UI: %s", e, exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to add subscription:\n{e}")

    def _on_update_all(self):
        urls = [sub.url for sub in self.sub_manager.subscriptions
                if sub.url != "amnezia://imported"]
        self.batch_update_requested.emit(urls)

    def _on_cell_changed(self, row, col):
        if col != 0:
            return
        url_item = self.table.item(row, 1)
        name_item = self.table.item(row, 0)
        if not url_item or not name_item:
            return
        url = url_item.text()
        new_name = name_item.text().strip()
        if not new_name:
            return
        for sub in self.sub_manager.subscriptions:
            if sub.url == url:
                if sub.name != new_name:
                    sub.name = new_name
                    self.sub_manager._save()
                    logger.info("Subscription name updated: %s", url[:60])
                break

    def refresh_after_update(self):
        logger.debug("Refreshing subscription list UI")
        self._load_data()

    def _on_import_conf(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import AmneziaWG Config", "", "Config files (*.conf);;All files (*)")
        if path:
            self.conf_imported.emit(path)

    def _on_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        url_item = self.table.item(item.row(), 1)
        if not url_item:
            return
        url = url_item.text()
        menu = QMenu(self)
        update_act = QAction(tr("update"), self)
        update_act.triggered.connect(lambda: self.update_requested.emit(url))
        menu.addAction(update_act)
        remove_act = QAction(tr("remove"), self)
        remove_act.triggered.connect(lambda: self._remove_by_url(url))
        menu.addAction(remove_act)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _remove_by_url(self, url: str):
        logger.info("UI: Removing subscription: %s", url[:60])
        self.sub_manager.remove_subscription(url)
        self._load_data()
