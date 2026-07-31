import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QPlainTextEdit, QComboBox, QLabel,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor, QColor

from core.log_utils import SignalEmitter, get_signal_handler
from core.translations import tr


LEVEL_COLORS = {
    "DEBUG": QColor("#6c7086"),
    "INFO": QColor("#cdd6f4"),
    "WARNING": QColor("#f9e2af"),
    "ERROR": QColor("#f38ba8"),
    "CRITICAL": QColor("#eba0ac"),
}


class LogTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._paused = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        from core.translations import tr
        title = QLabel(tr("log_window"))
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        controls = QHBoxLayout()
        controls.setSpacing(8)

        self.filter_cb = QComboBox()
        self.filter_cb.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.filter_cb.currentTextChanged.connect(self._on_filter)
        self.filter_cb.setMinimumWidth(120)
        self.filter_cb.setMinimumHeight(28)
        controls.addWidget(QLabel("Level:"))
        controls.addWidget(self.filter_cb)

        controls.addStretch()

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setCheckable(True)
        self.pause_btn.toggled.connect(self._on_toggle_pause)
        self.pause_btn.setMinimumHeight(28)
        controls.addWidget(self.pause_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._on_clear)
        clear_btn.setMinimumHeight(28)
        controls.addWidget(clear_btn)

        copy_btn = QPushButton("Copy All")
        copy_btn.clicked.connect(self._on_copy)
        copy_btn.setMinimumHeight(28)
        controls.addWidget(copy_btn)

        layout.addLayout(controls)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(10000)
        self.log_view.setUndoRedoEnabled(False)
        self.log_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.log_view.setStyleSheet("""
            QPlainTextEdit {
                background-color: #11111b;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 6px;
                font-family: "Consolas", "Courier New", monospace;
                font-size: 12px;
                padding: 8px;
                selection-background-color: #89b4fa;
                selection-color: #1e1e2e;
            }
        """)
        layout.addWidget(self.log_view)

        self._load_buffer()

        emitter = SignalEmitter.get()
        emitter.emitter.log_line.connect(self._on_log_line)

    def _load_buffer(self):
        handler = get_signal_handler()
        if handler:
            for line in list(handler.buffer):
                self._append_line(line)

    def _on_log_line(self, line: str):
        if not self._paused:
            self._append_line(line)

    def _append_line(self, line: str):
        level = self._detect_level(line)
        current_filter = self.filter_cb.currentText()
        if current_filter != "ALL" and level != current_filter:
            return

        color = LEVEL_COLORS.get(level, QColor("#cdd6f4"))
        cursor = self.log_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_view.setTextCursor(cursor)

        fmt = cursor.charFormat()
        fmt.setForeground(color)
        cursor.setCharFormat(fmt)
        cursor.insertText(line + "\n")

        scrollbar = self.log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _detect_level(self, line: str) -> str:
        if " | DEBUG | " in line or "| DEBUG " in line:
            return "DEBUG"
        if " | INFO | " in line or "| INFO " in line:
            return "INFO"
        if " | WARNING | " in line or "| WARNING " in line:
            return "WARNING"
        if " | ERROR | " in line or "| ERROR " in line:
            return "ERROR"
        if " | CRITICAL | " in line or "| CRITICAL " in line:
            return "CRITICAL"
        return "INFO"

    def _on_filter(self, level: str):
        self.log_view.clear()
        self._load_buffer()

    def _on_toggle_pause(self, paused: bool):
        self._paused = paused
        self.pause_btn.setText(tr("resume") if paused else tr("pause"))

    def _on_clear(self):
        self.log_view.clear()

    def _on_copy(self):
        self.log_view.selectAll()
        self.log_view.copy()
        cursor = self.log_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_view.setTextCursor(cursor)
