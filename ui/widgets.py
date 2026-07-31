from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QColor, QPainter, QRadialGradient
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from typing import Optional, Callable

import math


class StatusIndicator(QWidget):
    def __init__(self, size: int = 12, color: str = "#f38ba8", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._size = size
        self._color = QColor(color)
        self._pulse = 0.0
        self._pulsing = False
        self.setFixedSize(size + 8, size + 8)
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)

    def set_color(self, color: str):
        self._color = QColor(color)
        self.update()

    def set_pulsing(self, on: bool, speed: float = 1.0):
        self._pulsing = on
        self._pulse = 0.0
        self._speed = max(0.1, speed)
        if on:
            self._timer.start()
        else:
            self._timer.stop()
            self._pulse = 0.0
        self.update()

    def _tick(self):
        self._pulse = (self._pulse + 0.05 * self._speed) % 1.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx = self.width() / 2
        cy = self.height() / 2
        r = self._size / 2

        if self._pulsing:
            glow = 0.35 + 0.65 * abs(math.sin(self._pulse * math.pi))
            grad = QRadialGradient(cx, cy, r * 3)
            base = self._color
            grad.setColorAt(0.0, QColor(base.red(), base.green(), base.blue(), int(120 * glow)))
            grad.setColorAt(1.0, QColor(base.red(), base.green(), base.blue(), 0))
            painter.setBrush(grad)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(cx - r * 3, cy - r * 3, r * 6, r * 6))

        painter.setBrush(self._color)
        painter.setPen(QColor(255, 255, 255, 40))
        painter.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))


class EmptyStateWidget(QWidget):
    def __init__(self, icon_color: str = "#45475a", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._icon_color = QColor(icon_color)
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch(1)

        inner = QVBoxLayout()
        inner.setSpacing(8)
        inner.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = _EmptyIcon(32, self._icon_color)
        inner.addWidget(icon, 0, Qt.AlignmentFlag.AlignHCenter)

        self._title = QLabel()
        self._title.setObjectName("emptyTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.addWidget(self._title)

        self._subtitle = QLabel()
        self._subtitle.setObjectName("emptySubtitle")
        self._subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle.setWordWrap(True)
        self._subtitle.setMaximumWidth(360)
        inner.addWidget(self._subtitle)

        self._action_btn = QPushButton()
        self._action_btn.setObjectName("ghostBtn")
        self._action_btn.hide()
        inner.addWidget(self._action_btn, 0, Qt.AlignmentFlag.AlignHCenter)

        outer.addLayout(inner)
        outer.addStretch(1)

    def set_texts(self, title: str, subtitle: str = ""):
        self._title.setText(title)
        self._subtitle.setText(subtitle)

    def set_action(self, text: str, callback: Optional[Callable] = None):
        self._action_btn.setText(text)
        self._action_btn.show()
        try:
            self._action_btn.clicked.disconnect()
        except TypeError:
            pass
        if callback:
            self._action_btn.clicked.connect(callback)


class _EmptyIcon(QWidget):
    def __init__(self, size: int = 32, color: QColor = QColor("#45475a"), parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = painter.pen()
        pen.setColor(self._color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        w, h = self.width(), self.height()
        painter.drawRoundedRect(1, 1, w - 2, h - 2, 8, 8)
        bar_w = w - 12
        bar_h = 3
        y = h // 2 - bar_h
        for i in range(3):
            painter.drawRoundedRect(6, y + i * 8, bar_w, bar_h, 2, 2)
