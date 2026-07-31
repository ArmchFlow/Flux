from PyQt6.QtCore import Qt, QTimer, QRectF, QEvent, QPoint
from PyQt6.QtGui import QColor, QPainter, QRadialGradient, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QDialog
from typing import Optional, Callable

import math

from core.translations import tr


class SpeedResultDialog(QDialog):
    def __init__(self, down_mbit: float, up_mbit: float, parent=None):
        super().__init__(parent)
        self.setObjectName("speedResultDialog")
        self.setWindowTitle(tr("speed_test"))
        self.setModal(True)
        self.setMinimumWidth(340)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 28)
        layout.setSpacing(6)

        title = QLabel(tr("speed_test"))
        title.setObjectName("speedResultTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        down_lbl = QLabel(tr("speed_down"))
        down_lbl.setObjectName("speedResultLabel")
        down_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(down_lbl)

        down_val = QLabel(f"\u2193 {down_mbit:.0f} {tr('speed_mbps')}")
        down_val.setObjectName("speedResultValueDown")
        down_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(down_val)

        up_lbl = QLabel(tr("speed_up"))
        up_lbl.setObjectName("speedResultLabel")
        up_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        up_lbl.setContentsMargins(0, 8, 0, 0)
        layout.addWidget(up_lbl)

        up_val = QLabel(f"\u2191 {up_mbit:.0f} {tr('speed_mbps')}")
        up_val.setObjectName("speedResultValueUp")
        up_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(up_val)

        ok_btn = QPushButton(tr("close"))
        ok_btn.setObjectName("successBtn")
        ok_btn.setMinimumHeight(38)
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)


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


class _ButtonOverlay(QWidget):
    MARGIN = 0

    def __init__(self, target: QWidget, color: str = "#1e1e2e"):
        parent = target.parentWidget() or target.window()
        super().__init__(parent)
        self._target = target
        self._color = QColor(color)
        self._running = False
        self._timer = QTimer(self)
        self._timer.setInterval(25)
        self._timer.timeout.connect(self._tick)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        target.installEventFilter(self)
        self._sync_geometry()
        self.hide()

    def _sync_geometry(self):
        m = self.MARGIN
        tl = self._target.mapTo(self.parentWidget(), QPoint(0, 0))
        self.setGeometry(tl.x() - m, tl.y() - m,
                         self._target.width() + 2 * m, self._target.height() + 2 * m)

    def eventFilter(self, obj, event):
        if obj is self._target:
            t = event.type()
            if t in (QEvent.Type.Resize, QEvent.Type.Move):
                self._sync_geometry()
            elif t == QEvent.Type.Hide:
                self._timer.stop()
                self.hide()
            elif t == QEvent.Type.Show and self._running:
                self._sync_geometry()
                self.show()
                self._timer.start()
        return super().eventFilter(obj, event)

    def start(self):
        self._running = True
        self._sync_geometry()
        self.show()
        self._timer.start()

    def stop(self):
        self._running = False
        self._timer.stop()
        self.hide()

    def _tick(self):
        self.update()


class TrailRingOverlay(_ButtonOverlay):
    MARGIN = 6

    def __init__(self, target: QWidget, color: str = "#ffffff", dots: int = 18):
        super().__init__(target, color)
        self._dots = max(6, dots)
        self._head = 0.0
        self._alpha = 255
        self._fading = False
        self._fade_step = 0.0

    def start(self):
        self._head = 0.0
        self._alpha = 255
        self._fading = False
        super().start()

    def fade_out(self, duration_ms: int = 250):
        if not self._running:
            return
        self._fading = True
        self._fade_step = 255.0 * 25 / max(1, duration_ms)
        self._timer.start()

    def _tick(self):
        if self._fading:
            self._alpha -= self._fade_step
            if self._alpha <= 0:
                self.stop()
                return
        else:
            self._head = (self._head - 0.025) % 1.0
        self.update()

    def paintEvent(self, event):
        if self._alpha <= 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()).adjusted(2.0, 2.0, -2.0, -2.0), 9, 9)

        n = self._dots
        for i in range(n):
            t = (self._head + i * (0.5 / n)) % 1.0
            pt = path.pointAtPercent(t)
            k = 1.0 - i / n
            alpha = int(self._alpha * k * k)
            if alpha <= 0:
                continue
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(self._color.red(), self._color.green(), self._color.blue(), alpha))
            painter.drawEllipse(pt, 2.8 * k, 2.8 * k)


class PulseHitOverlay(_ButtonOverlay):
    def __init__(self, target: QWidget, color: str = "#1e1e2e"):
        super().__init__(target, color)
        self._progress = 0.0

    def play(self):
        self._progress = 0.0
        self.start()

    def _tick(self):
        self._progress += 25 / 450.0
        if self._progress >= 1.0:
            self.stop()
            return
        self.update()

    def paintEvent(self, event):
        if self._progress >= 1.0:
            return
        k = self._progress
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()).adjusted(2.5, 2.5, -2.5, -2.5), 8, 8)

        center = QRectF(self.rect()).center()
        scale = 1.0 + 0.06 * k
        painter.translate(center)
        painter.scale(scale, scale)
        painter.translate(-center)

        pen = QPen(QColor(self._color.red(), self._color.green(), self._color.blue(),
                          int(220 * (1.0 - k) ** 1.3)), 2.5 + 2.5 * k)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
