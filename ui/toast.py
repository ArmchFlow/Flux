from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QFont
from typing import Optional


class Toast(QWidget):
    closed = pyqtSignal()

    def __init__(self, message: str, type: str = "info", duration: int = 3000, parent: Optional[QWidget] = None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._message = message
        self._type = type
        self._duration = duration

        self._setup_ui()
        self._setup_animation()

        QTimer.singleShot(duration, self.close_animated)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        icons = {
            "info": "ℹ",
            "success": "✓",
            "warning": "⚠",
            "error": "✕"
        }
        colors = {
            "info": "#89b4fa",
            "success": "#a6e3a1",
            "warning": "#f9e2af",
            "error": "#f38ba8"
        }

        icon_label = QLabel(icons.get(self._type, "ℹ"))
        icon_label.setStyleSheet(f"color: {colors.get(self._type, '#89b4fa')}; font-size: 16px; font-weight: bold;")
        icon_label.setFixedSize(24, 24)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        msg_label = QLabel(self._message)
        msg_label.setStyleSheet("color: #cdd6f4; font-size: 13px;")
        msg_label.setWordWrap(True)
        msg_label.setMaximumWidth(300)
        layout.addWidget(msg_label, 1)

        self.setLayout(layout)
        self.adjustSize()

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)

    def _setup_animation(self):
        self._slide_anim = QPropertyAnimation(self, b"geometry")
        self._slide_anim.setDuration(250)
        self._slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def showEvent(self, event):
        super().showEvent(event)
        start_rect = QRect(
            self.x() + 50, self.y(),
            self.width(), self.height()
        )
        end_rect = self.geometry()
        self.setGeometry(start_rect)
        self._slide_anim.setStartValue(start_rect)
        self._slide_anim.setEndValue(end_rect)
        self._slide_anim.start()

    def close_animated(self):
        self._slide_anim.setDuration(200)
        self._slide_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        end_rect = QRect(
            self.x() + 50, self.y(),
            self.width(), self.height()
        )
        self._slide_anim.setStartValue(self.geometry())
        self._slide_anim.setEndValue(end_rect)
        self._slide_anim.finished.connect(self._on_close_finished)
        self._slide_anim.start()

    def _on_close_finished(self):
        self.closed.emit()
        self.deleteLater()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 10, 10)

        painter.fillPath(path, QColor("#1e1e2e"))
        painter.setPen(QColor("#313244"))
        painter.drawPath(path)