from PyQt6.QtCore import (
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
    QPoint, QRect, QTimer, QObject, QAbstractAnimation, pyqtSignal, pyqtProperty,
)
from PyQt6.QtWidgets import QWidget, QGraphicsOpacityEffect
from PyQt6.QtGui import QColor, QPainter, QPainterPath
from typing import Optional, Callable
import math

_active_fades: dict[int, QPropertyAnimation] = {}


def _stop_active_fade(widget: QWidget):
    anim = _active_fades.pop(id(widget), None)
    if anim is not None:
        try:
            anim.stop()
        except RuntimeError:
            pass
        try:
            widget.setGraphicsEffect(None)
        except RuntimeError:
            pass


class Animations:
    @staticmethod
    def fade_in(widget: QWidget, duration: int = 150, callback: Optional[Callable] = None) -> QPropertyAnimation:
        _stop_active_fade(widget)
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        effect.setOpacity(0.0)

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def cleanup():
            if _active_fades.get(id(widget)) is anim:
                _active_fades.pop(id(widget), None)
            try:
                widget.setGraphicsEffect(None)
            except RuntimeError:
                pass
            if callback:
                callback()

        _active_fades[id(widget)] = anim
        anim.finished.connect(cleanup)
        anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
        return anim

    @staticmethod
    def fade_out(widget: QWidget, duration: int = 150, callback: Optional[Callable] = None) -> QPropertyAnimation:
        _stop_active_fade(widget)
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        effect.setOpacity(1.0)

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(duration)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)

        def cleanup():
            if _active_fades.get(id(widget)) is anim:
                _active_fades.pop(id(widget), None)
            try:
                widget.setGraphicsEffect(None)
            except RuntimeError:
                pass
            if callback:
                callback()

        _active_fades[id(widget)] = anim
        anim.finished.connect(cleanup)
        anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
        return anim

    @staticmethod
    def slide_in(widget: QWidget, direction: str = "left", distance: int = 30, duration: int = 200, callback: Optional[Callable] = None) -> QPropertyAnimation:
        start_pos = widget.pos()
        if direction == "left":
            end_pos = QPoint(start_pos.x() + distance, start_pos.y())
            start_pos = QPoint(start_pos.x() - distance, start_pos.y())
        elif direction == "right":
            end_pos = QPoint(start_pos.x() - distance, start_pos.y())
            start_pos = QPoint(start_pos.x() + distance, start_pos.y())
        elif direction == "up":
            end_pos = QPoint(start_pos.x(), start_pos.y() + distance)
            start_pos = QPoint(start_pos.x(), start_pos.y() - distance)
        elif direction == "down":
            end_pos = QPoint(start_pos.x(), start_pos.y() - distance)
            start_pos = QPoint(start_pos.x(), start_pos.y() + distance)

        widget.move(start_pos)

        anim = QPropertyAnimation(widget, b"pos")
        anim.setDuration(duration)
        anim.setStartValue(start_pos)
        anim.setEndValue(end_pos)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        if callback:
            anim.finished.connect(callback)

        anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
        return anim

    @staticmethod
    def slide_fade_in(widget: QWidget, direction: str = "left", distance: int = 30, duration: int = 200, callback: Optional[Callable] = None) -> QParallelAnimationGroup:
        fade = Animations.fade_in(widget, duration)
        slide = Animations.slide_in(widget, direction, distance, duration)

        group = QParallelAnimationGroup()
        group.addAnimation(fade)
        group.addAnimation(slide)

        if callback:
            group.finished.connect(callback)

        group.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
        return group

    @staticmethod
    def pulse(widget: QWidget, color: str = "#89b4fa", duration: int = 1000, loops: int = 1) -> "PulseAnimation":
        anim = PulseAnimation(widget, color, duration, loops)
        anim.start()
        return anim


class PulseAnimation(QObject):
    finished = pyqtSignal()

    def __init__(self, widget: QWidget, color: str = "#89b4fa", duration: int = 1000, loops: int = 1, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._widget = widget
        self._color = color
        self._duration = max(100, duration)
        self._loops = max(0, loops)
        self._count = 0
        self._progress = 0.0
        self._original_style = widget.styleSheet()
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._progress = 0.0
        self._count = 0
        self._timer.start()

    def stop(self):
        self._timer.stop()
        try:
            self._widget.setStyleSheet(self._original_style)
        except RuntimeError:
            pass

    def _tick(self):
        self._progress += 33 / self._duration
        if self._progress >= 1.0:
            self._count += 1
            self._progress = 0.0
            if self._loops > 0 and self._count >= self._loops:
                self.stop()
                self.finished.emit()
                return

        wave = abs(math.sin(self._progress * math.pi))
        alpha = int(100 + 155 * wave)
        width = int(2 + 2 * wave)
        try:
            r = int(self._color[1:3], 16)
            g = int(self._color[3:5], 16)
            b = int(self._color[5:7], 16)
            self._widget.setStyleSheet(
                f"{self._original_style}; border: {width}px solid rgba({r},{g},{b},{alpha});"
            )
        except RuntimeError:
            self.stop()


class ShimmerEffect(QObject):
    def __init__(self, widget: QWidget):
        super().__init__(widget)
        self._widget = widget
        self._progress = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)

    @pyqtProperty(float)
    def progress(self) -> float:
        return self._progress

    @progress.setter
    def progress(self, value: float):
        self._progress = value
        self._widget.update()

    def start(self):
        self._progress = 0.0
        self._timer.start()

    def stop(self):
        self._timer.stop()
        self._progress = 0.0
        self._widget.update()

    def _tick(self):
        self._progress = (self._progress + 0.02) % 1.0
        self._widget.update()

    @staticmethod
    def paint_shimmer(painter: QPainter, rect: QRect, progress: float, base_color: str = "#313244", highlight_color: str = "#45475a"):
        painter.fillRect(rect, QColor(base_color))

        highlight_width = rect.width() // 3
        x = int(-highlight_width + progress * (rect.width() + highlight_width))

        gradient = QPainterPath()
        gradient.moveTo(x, rect.top())
        gradient.lineTo(x + highlight_width, rect.top())
        gradient.lineTo(x + highlight_width - 20, rect.bottom())
        gradient.lineTo(x - 20, rect.bottom())
        gradient.closeSubpath()

        painter.fillPath(gradient, QColor(highlight_color))


class ToastManager(QObject):
    _instance = None

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._parent = parent
        self._toasts = []

    @classmethod
    def instance(cls, parent: Optional[QWidget] = None) -> "ToastManager":
        if cls._instance is None:
            cls._instance = cls(parent)
        elif parent and cls._instance._parent is None:
            cls._instance._parent = parent
        return cls._instance

    def show(self, message: str, type: str = "info", duration: int = 3000):
        from .toast import Toast
        toast = Toast(message, type, duration, self._parent)
        self._toasts.append(toast)
        toast.closed.connect(lambda: self._toasts.remove(toast))
        self._reposition_toasts()
        toast.show()

    def _reposition_toasts(self):
        if not self._parent:
            return
        margin = 16
        geo = self._parent.geometry()
        y = geo.y() + margin
        for toast in self._toasts:
            toast.move(geo.x() + geo.width() - toast.width() - margin, y)
            y += toast.height() + 8


def attach_press_feedback(button, pressed_opacity: float = 0.75, duration: int = 60):
    effect = QGraphicsOpacityEffect(button)
    effect.setOpacity(1.0)
    button.setGraphicsEffect(effect)

    def press():
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(duration)
        anim.setStartValue(1.0)
        anim.setEndValue(pressed_opacity)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    def release():
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(duration)
        anim.setStartValue(pressed_opacity)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    button.pressed.connect(press)
    button.released.connect(release)