"""
SimulationCanvas — the widget that owns the clock and the paint loop.

This is the only place where wall-clock time meets the physics. It keeps a
QTimer running at roughly 60 Hz, measures the real elapsed time with
QElapsedTimer, and hands that dt to the model.
"""
from __future__ import annotations

from PySide6.QtCore import QElapsedTimer, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from app.render.scenes import SCENES
from app.theme import DARK, Palette


class SimulationCanvas(QWidget):
    """Renders one experiment and emits a signal after every frame.

    `frame_advanced` is how the dashboard learns that something changed. The
    canvas does not know what a readout strip or a telemetry plot is — it just
    announces the new state and lets whoever cares subscribe. That is Qt's
    signal/slot mechanism, and it is the reason this widget can be reused
    unchanged in a different window.
    """

    frame_advanced = Signal(object)      # carries the model
    run_state_changed = Signal(bool)

    MAX_DT = 0.05        # never advance more than 50 ms in one step

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(360)
        self.setAttribute(Qt.WA_StyledBackground, False)

        self.palette_tokens: Palette = DARK
        self.model = None
        self.scene = None
        self.speed = 1.0
        self._running = False

        self._clock = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(16)                   # ~60 frames per second
        self._timer.timeout.connect(self._advance)
        self._timer.start()

    # ── lifecycle ────────────────────────────────────────────────────────
    def load(self, experiment, params: dict) -> None:
        """Build a fresh model and scene. Called on experiment change, on any
        slider move, and on reset."""
        self.model = experiment.model_cls(params)
        self.scene = SCENES[experiment.scene_key](self.model)
        self.scene.resize(self.width(), self.height())
        self.scene.on_reset()
        self.update()

    def set_palette_tokens(self, pal: Palette) -> None:
        self.palette_tokens = pal
        self.update()

    # ── transport ────────────────────────────────────────────────────────
    @property
    def running(self) -> bool:
        return self._running

    def play(self) -> None:
        if self.model is None or self.model.finished:
            return
        self._running = True
        self._clock.restart()
        self.run_state_changed.emit(True)

    def pause(self) -> None:
        self._running = False
        self.run_state_changed.emit(False)

    def toggle(self) -> None:
        self.pause() if self._running else self.play()

    # ── the loop ─────────────────────────────────────────────────────────
    def _advance(self) -> None:
        if self.model is None:
            return
        if self._running:
            # Clamp dt. If the window was dragged or the machine stalled we do
            # not want to teleport the simulation forward by half a second.
            dt = min(self._clock.restart() / 1000.0, self.MAX_DT) * self.speed
            self.model.step(dt)
            if self.model.finished:
                self._running = False
                self.run_state_changed.emit(False)
            self.frame_advanced.emit(self.model)
        self.update()                                  # schedules paintEvent

    # ── painting ─────────────────────────────────────────────────────────
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.scene is not None:
            self.scene.resize(self.width(), self.height())

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        # Clip to a rounded rectangle so the simulation shares the corner
        # radius of the surrounding cards instead of poking out of them.
        frame = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        card = QPainterPath()
        card.addRoundedRect(frame, 14, 14)
        p.fillPath(card, QColor(self.palette_tokens.canvas))
        p.setClipPath(card)

        if self.scene is not None:
            self.scene.draw(p, self.palette_tokens)

        p.setClipping(False)
        p.setPen(QPen(QColor(self.palette_tokens.line), 1))
        p.setBrush(Qt.NoBrush)
        p.drawPath(card)
        p.end()
