DARK_STYLE = """
QMainWindow {
    background-color: #1e1e2e;
    color: #cdd6f4;
}

QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Arial", sans-serif;
    font-size: 13px;
}

QTabWidget::pane {
    border: 1px solid #313244;
    background-color: #1e1e2e;
    border-radius: 4px;
}

QTabWidget::tab-bar {
    left: 5px;
}

QTabBar::tab {
    background-color: #181825;
    color: #a6adc8;
    padding: 8px 20px;
    border: 1px solid #313244;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border-bottom: 2px solid #89b4fa;
}

QTabBar::tab:hover:!selected {
    background-color: #313244;
    color: #cdd6f4;
}

QPushButton {
    background-color: #45475a;
    color: #cdd6f4;
    border: 1px solid #585b70;
    padding: 6px 16px;
    border-radius: 6px;
    min-height: 28px;
}

QPushButton:hover {
    background-color: #585b70;
    border-color: #89b4fa;
}

QPushButton:pressed {
    background-color: #313244;
}

QPushButton:disabled {
    background-color: #313244;
    color: #6c7086;
    border-color: #45475a;
}

QPushButton#connectBtn {
    background-color: #a6e3a1;
    color: #1e1e2e;
    border: none;
    padding: 8px 24px;
    font-weight: bold;
    font-size: 14px;
    border-radius: 8px;
    min-height: 36px;
}

QPushButton#connectBtn:hover {
    background-color: #94e2d5;
}

QPushButton#disconnectBtn {
    background-color: #f38ba8;
    color: #1e1e2e;
    border: none;
    padding: 8px 24px;
    font-weight: bold;
    font-size: 14px;
    border-radius: 8px;
    min-height: 36px;
}

QPushButton#disconnectBtn:hover {
    background-color: #eba0ac;
}

QPushButton#dangerBtn {
    background-color: #f38ba8;
    color: #1e1e2e;
    border: none;
    padding: 4px 12px;
    border-radius: 4px;
}

QPushButton#dangerBtn:hover {
    background-color: #eba0ac;
}

QPushButton#successBtn {
    background-color: #a6e3a1;
    color: #1e1e2e;
    border: none;
    padding: 4px 12px;
    border-radius: 4px;
}

QPushButton#successBtn:hover {
    background-color: #94e2d5;
}

QLineEdit {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 24px;
    selection-background-color: #89b4fa;
    selection-color: #1e1e2e;
}

QLineEdit:focus {
    border-color: #89b4fa;
}

QComboBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 24px;
}

QComboBox:hover {
    border-color: #89b4fa;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #313244;
    color: #cdd6f4;
    selection-background-color: #89b4fa;
    selection-color: #1e1e2e;
    border: 1px solid #45475a;
    border-radius: 4px;
}

QCheckBox {
    color: #cdd6f4;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #45475a;
    border-radius: 4px;
    background-color: #313244;
}

QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}

QCheckBox::indicator:hover {
    border-color: #89b4fa;
}

QSpinBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 8px;
    min-height: 24px;
}

QSpinBox:focus {
    border-color: #89b4fa;
}

QLabel {
    color: #cdd6f4;
    background: transparent;
}

QLabel#titleLabel {
    font-size: 18px;
    font-weight: bold;
    color: #cdd6f4;
}

QLabel#subtitleLabel {
    font-size: 11px;
    color: #a6adc8;
}

QLabel#statusConnected {
    color: #a6e3a1;
    font-weight: bold;
    font-size: 12px;
}

QLabel#statusDisconnected {
    color: #f38ba8;
    font-weight: bold;
    font-size: 12px;
}

QTableWidget {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    gridline-color: #313244;
    selection-background-color: rgba(137, 180, 250, 0.15);
    selection-color: #cdd6f4;
    alternate-background-color: #1e1e2e;
}

QTableWidget::item {
    padding: 6px 10px;
    border: none;
}

QTableWidget::item:selected {
    background-color: rgba(137, 180, 250, 0.25);
    color: #cdd6f4;
}

QHeaderView::section {
    background-color: #181825;
    color: #a6adc8;
    padding: 8px 10px;
    border: none;
    border-bottom: 2px solid #313244;
    font-weight: bold;
}

QHeaderView::section:hover {
    background-color: #313244;
}

QScrollBar:vertical {
    background-color: #1e1e2e;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #45475a;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #585b70;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #1e1e2e;
    height: 10px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background-color: #45475a;
    border-radius: 5px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #585b70;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

QGroupBox {
    color: #cdd6f4;
    font-weight: bold;
    border: 1px solid #313244;
    border-radius: 8px;
    margin-top: 12px;
    padding: 16px 12px 12px 12px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

QSplitter::handle {
    background-color: #313244;
}

QSplitter::handle:horizontal {
    width: 2px;
}

QSplitter::handle:vertical {
    height: 2px;
}

QProgressBar {
    background-color: #313244;
    border: none;
    border-radius: 4px;
    text-align: center;
    color: #cdd6f4;
    height: 8px;
}

QProgressBar::chunk {
    background-color: #89b4fa;
    border-radius: 4px;
}

QToolTip {
    background-color: #45475a;
    color: #cdd6f4;
    border: 1px solid #585b70;
    border-radius: 4px;
    padding: 4px 8px;
}

QMenu {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 24px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #89b4fa;
    color: #1e1e2e;
}

QMenu::separator {
    height: 1px;
    background-color: #45475a;
    margin: 4px 8px;
}

QSystemTrayIcon {
    background-color: transparent;
}
"""
