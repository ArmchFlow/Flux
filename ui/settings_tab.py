import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout,
    QGroupBox, QCheckBox, QSpinBox, QLineEdit,
    QComboBox, QLabel, QScrollArea, QPushButton,
)
from PyQt6.QtCore import pyqtSignal

from core.settings_manager import SettingsManager
from core.translations import tr, set_language

logger = logging.getLogger(__name__)


class SettingsTab(QWidget):
    settings_changed = pyqtSignal()

    def __init__(self, settings_mgr: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings_mgr = settings_mgr
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        title = QLabel(tr("settings"))
        title.setObjectName("titleLabel")
        main_layout.addWidget(title)

        tun_group = QGroupBox(tr("tun_config"))
        tun_layout = QFormLayout(tun_group)
        tun_layout.setSpacing(8)

        self.tun_enabled = QCheckBox(tr("enable_tun"))
        self.tun_enabled.toggled.connect(self._on_setting_changed)
        tun_layout.addRow(self.tun_enabled)

        self.interface_name = QLineEdit()
        self.interface_name.textChanged.connect(self._on_setting_changed)
        tun_layout.addRow(tr("interface_name"), self.interface_name)

        self.tun_address = QLineEdit()
        self.tun_address.textChanged.connect(self._on_setting_changed)
        tun_layout.addRow(tr("tun_address"), self.tun_address)

        self.mtu = QSpinBox()
        self.mtu.setRange(1200, 65535)
        self.mtu.valueChanged.connect(self._on_setting_changed)
        tun_layout.addRow(tr("mtu"), self.mtu)

        self.auto_route = QCheckBox(tr("auto_route"))
        self.auto_route.toggled.connect(self._on_setting_changed)
        tun_layout.addRow(self.auto_route)

        self.strict_route = QCheckBox(tr("strict_route"))
        self.strict_route.toggled.connect(self._on_setting_changed)
        tun_layout.addRow(self.strict_route)

        self.stack = QComboBox()
        self.stack.addItems(["mixed", "system", "gvisor"])
        self.stack.currentTextChanged.connect(self._on_setting_changed)
        tun_layout.addRow(tr("stack"), self.stack)

        main_layout.addWidget(tun_group)

        split_group = QGroupBox(tr("split_tunneling"))
        split_layout = QVBoxLayout(split_group)
        split_layout.setSpacing(8)

        self.split_enabled = QCheckBox(tr("enable_split"))
        self.split_enabled.toggled.connect(self._on_setting_changed)
        split_layout.addWidget(self.split_enabled)

        self.bypass_china = QCheckBox(tr("bypass_china"))
        self.bypass_china.toggled.connect(self._on_setting_changed)
        split_layout.addWidget(self.bypass_china)

        self.proxy_lan = QCheckBox(tr("proxy_lan"))
        self.proxy_lan.toggled.connect(self._on_setting_changed)
        split_layout.addWidget(self.proxy_lan)

        custom_label = QLabel(tr("custom_bypass"))
        custom_label.setObjectName("subtitleLabel")
        split_layout.addWidget(custom_label)

        self.custom_routes = QLineEdit()
        self.custom_routes.setPlaceholderText("example.com, another.com")
        self.custom_routes.textChanged.connect(self._on_setting_changed)
        split_layout.addWidget(self.custom_routes)

        main_layout.addWidget(split_group)

        dns_group = QGroupBox(tr("dns"))
        dns_layout = QFormLayout(dns_group)
        dns_layout.setSpacing(8)

        self.local_dns = QLineEdit()
        self.local_dns.textChanged.connect(self._on_setting_changed)
        dns_layout.addRow(tr("local_dns"), self.local_dns)

        self.remote_dns = QLineEdit()
        self.remote_dns.textChanged.connect(self._on_setting_changed)
        dns_layout.addRow(tr("remote_dns"), self.remote_dns)

        self.fakeip_enabled = QCheckBox(tr("enable_fakeip"))
        self.fakeip_enabled.toggled.connect(self._on_setting_changed)
        dns_layout.addRow(self.fakeip_enabled)

        self.fakeip_range = QLineEdit()
        self.fakeip_range.textChanged.connect(self._on_setting_changed)
        dns_layout.addRow(tr("fakeip_range"), self.fakeip_range)

        main_layout.addWidget(dns_group)

        log_group = QGroupBox(tr("logging"))
        log_layout = QFormLayout(log_group)
        log_layout.setSpacing(8)

        self.log_level = QComboBox()
        self.log_level.addItems(["trace", "debug", "info", "warn", "error", "fatal"])
        self.log_level.currentTextChanged.connect(self._on_setting_changed)
        log_layout.addRow(tr("log_level"), self.log_level)

        self.log_timestamp = QCheckBox(tr("show_timestamps"))
        self.log_timestamp.toggled.connect(self._on_setting_changed)
        log_layout.addRow(self.log_timestamp)

        main_layout.addWidget(log_group)

        ui_group = QGroupBox(tr("interface"))
        ui_layout = QFormLayout(ui_group)
        ui_layout.setSpacing(8)

        self.minimize_to_tray = QCheckBox(tr("minimize_tray"))
        self.minimize_to_tray.toggled.connect(self._on_setting_changed)
        ui_layout.addRow(self.minimize_to_tray)

        self.start_minimized = QCheckBox(tr("start_minimized"))
        self.start_minimized.toggled.connect(self._on_setting_changed)
        ui_layout.addRow(self.start_minimized)

        self.auto_connect = QCheckBox(tr("auto_connect"))
        self.auto_connect.toggled.connect(self._on_setting_changed)
        ui_layout.addRow(self.auto_connect)

        self.auto_reconnect = QCheckBox(tr("auto_reconnect"))
        self.auto_reconnect.toggled.connect(self._on_setting_changed)
        ui_layout.addRow(self.auto_reconnect)

        self.language_cb = QComboBox()
        self.language_cb.addItem("English", "en")
        self.language_cb.addItem("Русский", "ru")
        self.language_cb.currentIndexChanged.connect(self._on_setting_changed)
        ui_layout.addRow(tr("language") + ":", self.language_cb)

        self.auto_select = QComboBox()
        self.auto_select.addItems([tr("manual_select"), tr("auto_select")])
        self.auto_select.currentIndexChanged.connect(self._on_setting_changed)
        ui_layout.addRow(tr("server_select"), self.auto_select)

        main_layout.addWidget(ui_group)
        main_layout.addStretch()

        scroll.setWidget(container)
        outer.addWidget(scroll, 1)

        save_btn = QPushButton(tr("apply_settings"))
        save_btn.setObjectName("successBtn")
        save_btn.setMinimumHeight(40)
        save_btn.clicked.connect(self._save_settings)
        outer.addWidget(save_btn)

    def _load_settings(self):
        s = self.settings_mgr.settings

        self.tun_enabled.setChecked(s.tun.enabled)
        self.interface_name.setText(s.tun.interface_name)
        self.tun_address.setText(s.tun.address)
        self.mtu.setValue(s.tun.mtu)
        self.auto_route.setChecked(s.tun.auto_route)
        self.strict_route.setChecked(s.tun.strict_route)
        idx = self.stack.findText(s.tun.stack)
        if idx >= 0:
            self.stack.setCurrentIndex(idx)

        self.split_enabled.setChecked(s.split_tunnel.enabled)
        self.bypass_china.setChecked(s.split_tunnel.bypass_china)
        self.proxy_lan.setChecked(s.split_tunnel.proxy_lan)
        self.custom_routes.setText("\n".join(s.split_tunnel.custom_routes))

        self.local_dns.setText(s.dns.local_dns)
        self.remote_dns.setText(s.dns.remote_dns)
        self.fakeip_enabled.setChecked(s.dns.fakeip_enabled)
        self.fakeip_range.setText(s.dns.fakeip_range)

        idx = self.log_level.findText(s.log.level)
        if idx >= 0:
            self.log_level.setCurrentIndex(idx)
        self.log_timestamp.setChecked(s.log.timestamp)

        self.minimize_to_tray.setChecked(s.minimize_to_tray)
        self.start_minimized.setChecked(s.start_minimized)
        self.auto_connect.setChecked(s.auto_connect)
        self.auto_reconnect.setChecked(s.auto_reconnect)
        l_idx = self.language_cb.findData(s.language)
        if l_idx >= 0:
            self.language_cb.setCurrentIndex(l_idx)
        self.auto_select.setCurrentIndex(1 if s.proxy.auto_select else 0)

    def _save_settings(self):
        s = self.settings_mgr.settings
        logger.info("Saving settings...")

        s.tun.enabled = self.tun_enabled.isChecked()
        s.tun.interface_name = self.interface_name.text()
        s.tun.address = self.tun_address.text()
        s.tun.mtu = self.mtu.value()
        s.tun.auto_route = self.auto_route.isChecked()
        s.tun.strict_route = self.strict_route.isChecked()
        s.tun.stack = self.stack.currentText()

        s.split_tunnel.enabled = self.split_enabled.isChecked()
        s.split_tunnel.bypass_china = self.bypass_china.isChecked()
        s.split_tunnel.proxy_lan = self.proxy_lan.isChecked()
        s.split_tunnel.custom_routes = [
            line.strip() for line in self.custom_routes.text().splitlines()
            if line.strip()
        ]

        s.dns.local_dns = self.local_dns.text()
        s.dns.remote_dns = self.remote_dns.text()
        s.dns.fakeip_enabled = self.fakeip_enabled.isChecked()
        s.dns.fakeip_range = self.fakeip_range.text()

        s.log.level = self.log_level.currentText()
        s.log.timestamp = self.log_timestamp.isChecked()

        s.minimize_to_tray = self.minimize_to_tray.isChecked()
        s.start_minimized = self.start_minimized.isChecked()
        s.auto_connect = self.auto_connect.isChecked()
        s.auto_reconnect = self.auto_reconnect.isChecked()
        s.language = self.language_cb.currentData() or "ru"
        s.proxy.auto_select = self.auto_select.currentIndex() == 1
        set_language(s.language)

        logger.debug("Settings values: TUN=%s, split=%s, auto_connect=%s",
                    s.tun.enabled, s.split_tunnel.enabled, s.auto_connect)

        self.settings_mgr.save()
        self.settings_changed.emit()

    def _on_setting_changed(self, *args):
        pass
