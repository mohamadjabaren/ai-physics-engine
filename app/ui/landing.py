"""
The landing screen.

The hero is not a stock illustration — it is the physics engine running. Two
SpringModel oscillators drive the x and y of a single point, and the trail it
leaves is a Lissajous figure. Their frequency ratio is 1.51 rather than a
clean 1.5, so the curve never quite closes and slowly precesses forever.

That means the first thing a visitor sees is the same code that powers the
experiments, which is a better argument for the project than any screenshot.
"""
from __future__ import annotations

import math
from collections import deque

from PySide6.QtCore import (QEasingCurve, QPointF, QPropertyAnimation, Qt,
                            QTimer, Signal)
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QFrame, QGraphicsOpacityEffect, QGridLayout,
                               QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
                               QWidget)

from app.core.catalog import EXPERIMENTS
from app.core.model import SpringModel
from app.theme import DARK, Palette


def fade_in(widget: QWidget, delay_ms: int, duration: int = 460) -> QPropertyAnimation:
    """Fade a widget in after a delay, and return the animation.

    Two things here are not optional:

    1. The caller MUST keep the returned object alive. An unreferenced
       QPropertyAnimation is garbage-collected immediately and never runs —
       the most common Qt-in-Python surprise there is.
    2. The graphics effect is removed once the fade finishes. Leaving a
       QGraphicsOpacityEffect attached forces every later repaint through an
       offscreen buffer, and this page repaints at 60 Hz because of the hero.
    """
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0.0)
    widget.setGraphicsEffect(effect)

    animation = QPropertyAnimation(effect, b"opacity", widget)
    animation.setDuration(duration)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.OutCubic)
    animation.finished.connect(lambda: widget.setGraphicsEffect(None))
    QTimer.singleShot(delay_ms, animation.start)
    return animation


class HeroCanvas(QWidget):
    """A live Lissajous curve traced by two of the engine's own oscillators."""

    TRAIL = 1100

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(340, 300)
        self.tokens: Palette = DARK

        # Same SpringModel used by the Spring experiment. omega = sqrt(k/m),
        # so these two run at 4.472 and 6.753 rad/s — a ratio of 1.510.
        self.osc_x = SpringModel({"mass": 1.0, "stiffness": 20.0, "amplitude": 1.0})
        self.osc_y = SpringModel({"mass": 1.0, "stiffness": 45.6, "amplitude": 1.0})
        self.points: deque = deque(maxlen=self.TRAIL)

        # Run the oscillators forward before the first paint, so the figure is
        # already drawn when the window opens instead of growing from a dot.
        for _ in range(self.TRAIL):
            self._integrate()

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def set_palette_tokens(self, tokens: Palette) -> None:
        self.tokens = tokens
        self.update()

    def _integrate(self) -> None:
        dt = 1 / 60
        self.osc_x.step(dt)
        self.osc_y.step(dt)
        self.points.append((self.osc_x.x, self.osc_y.x))

    def _tick(self) -> None:
        self._integrate()
        self.update()

    def paintEvent(self, event) -> None:
        if len(self.points) < 2:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        cx, cy = self.width() / 2, self.height() / 2
        # The curve reaches sqrt(2) * amplitude at the diagonals, so the scale
        # has to leave room for that or it clips against the widget edge.
        scale = min(self.width(), self.height()) * 0.32
        mapped = [QPointF(cx + x * scale, cy + y * scale) for x, y in self.points]

        # Faint guide circle, so the curve has something to sit inside.
        p.setPen(QPen(self.tokens.q("line"), 1))
        p.drawEllipse(QPointF(cx, cy), scale * 1.45, scale * 1.45)

        # Draw the trail in chunks of rising opacity: the oldest section is
        # nearly invisible, the newest is bright. Cheaper than setting a pen
        # per point, and it reads as motion.
        chunks = 16
        size = max(2, len(mapped) // chunks)
        for index in range(0, len(mapped) - 1, size):
            segment = mapped[index:index + size + 1]
            alpha = int(18 + 210 * (index / max(1, len(mapped))))
            path = QPainterPath(segment[0])
            for point in segment[1:]:
                path.lineTo(point)
            p.setPen(QPen(self.tokens.q("accent", alpha), 1.7))
            p.drawPath(path)

        head = mapped[-1]
        p.setPen(Qt.NoPen)
        p.setBrush(self.tokens.q("accent", 60))
        p.drawEllipse(head, 11, 11)
        p.setBrush(self.tokens.q("measure"))
        p.drawEllipse(head, 4.5, 4.5)
        p.end()


class ExperimentCard(QPushButton):
    """One clickable tile in the experiment picker."""

    def __init__(self, index: int, experiment, palette: Palette, parent=None) -> None:
        super().__init__(parent)
        self.experiment = experiment
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(112)

        number = QLabel(f"{index:02d}")
        number.setStyleSheet(
            f"color:{palette.accent}; font-family:monospace; font-size:11px; font-weight:700;")
        title = QLabel(experiment.title)
        title.setStyleSheet("font-size:15px; font-weight:600;")
        summary = QLabel(", ".join(p.label.lower() for p in experiment.parameters))
        summary.setStyleSheet(f"color:{palette.muted}; font-size:11.5px;")
        summary.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(3)
        layout.addWidget(number)
        layout.addWidget(title)
        layout.addWidget(summary)
        layout.addStretch(1)

        self.setStyleSheet(f"""
            QPushButton {{ background:{palette.surface}; border:1px solid {palette.line};
                           border-radius:14px; text-align:left; padding:0px; }}
            QPushButton:hover {{ border-color:{palette.accent}; background:{palette.surface_alt}; }}
        """)


class LandingPage(QWidget):
    experiment_chosen = Signal(str)      # experiment id

    def __init__(self, palette: Palette, parent=None) -> None:
        super().__init__(parent)
        self.tokens = palette
        self._animations: list = []      # keep the fades alive
        self._build()

    def _build(self) -> None:
        p = self.tokens

        self.hero = HeroCanvas()
        self.hero.set_palette_tokens(p)

        eyebrow = QLabel("INTERACTIVE MECHANICS LAB")
        eyebrow.setObjectName("Eyebrow")

        title = QLabel("AI Physics\nEngine")
        title.setStyleSheet("font-size:46px; font-weight:700; line-height:100%;")

        rule = QFrame()
        rule.setFixedSize(56, 3)
        rule.setStyleSheet(f"background:{p.accent}; border-radius:2px;")

        pitch = QLabel(
            "Four classical experiments you can take apart. Drag a parameter and the "
            "simulation, the readouts and the live plot all move together \u2014 because "
            "every number on screen is computed from the equation shown beside it.")
        pitch.setObjectName("Body")
        pitch.setWordWrap(True)
        pitch.setMaximumWidth(430)

        facts = QVBoxLayout()
        facts.setSpacing(9)
        for head, detail in (
            ("Measured, not fudged", "readouts trace back to a formula you can check by hand"),
            ("Predict, then test", "each scenario asks before it answers"),
            ("Physics apart from pixels", "the model layer has no idea a screen exists"),
        ):
            row = QHBoxLayout()
            row.setSpacing(10)
            dot = QLabel("\u25aa")
            dot.setStyleSheet(f"color:{p.measure}; font-size:13px;")
            label = QLabel(f"<b>{head}</b> \u2014 {detail}")
            label.setObjectName("Body")
            label.setWordWrap(True)
            row.addWidget(dot, 0, Qt.AlignTop)
            row.addWidget(label, 1)
            facts.addLayout(row)

        copy = QVBoxLayout()
        copy.setSpacing(14)
        copy.addStretch(1)
        copy.addWidget(eyebrow)
        copy.addWidget(title)
        copy.addWidget(rule)
        copy.addWidget(pitch)
        copy.addLayout(facts)
        copy.addStretch(1)

        top = QHBoxLayout()
        top.setSpacing(48)
        top.addWidget(self.hero, 5)
        top.addLayout(copy, 6)

        picker_label = QLabel("CHOOSE AN EXPERIMENT")
        picker_label.setObjectName("Eyebrow")

        cards = QGridLayout()
        cards.setSpacing(14)
        self.cards: list = []
        for index, experiment in enumerate(EXPERIMENTS):
            card = ExperimentCard(index + 1, experiment, p)
            card.clicked.connect(
                lambda _=False, e=experiment: self.experiment_chosen.emit(e.id))
            cards.addWidget(card, 0, index)
            self.cards.append(card)

        root = QVBoxLayout(self)
        root.setContentsMargins(52, 36, 52, 40)
        root.setSpacing(26)
        root.addLayout(top, 1)
        root.addWidget(picker_label)
        root.addLayout(cards)

        # Staggered entrance. Order matters: the eye should land on the hero,
        # then the headline, then the choices.
        self._blocks = [self.hero, eyebrow, title, rule, pitch, picker_label] + self.cards
        self._revealed = False

    def showEvent(self, event) -> None:
        """Start the entrance animation the first time the page is displayed.

        Animating from __init__ is fragile: the widget is not on screen yet,
        and if anything stops the animation from starting the content is left
        permanently at zero opacity — a blank landing page. Tying it to
        showEvent, and backstopping it below, means the worst case is that the
        animation is skipped, never that the page disappears.
        """
        super().showEvent(event)
        if self._revealed:
            return
        self._revealed = True

        for order, widget in enumerate(self._blocks):
            self._animations.append(fade_in(widget, delay_ms=90 + order * 75))

        # Safety net: whatever happened above, everything is visible by now.
        total = 90 + len(self._blocks) * 75 + 700
        QTimer.singleShot(total, self._reveal_everything)

    def _reveal_everything(self) -> None:
        for widget in self._blocks:
            widget.setGraphicsEffect(None)
