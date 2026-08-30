"""
Scene base class — the metres-to-pixels layer.

A Scene knows two things the model refuses to know: how big the widget is,
and how many pixels a metre is worth. It never computes physics; it reads a
model and paints it. Swap QPainter for OpenGL here and the physics is
untouched.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetrics, QPainter, QPen

from app.theme import Palette, mono_font


class Scene(ABC):
    """One drawing routine per experiment."""

    def __init__(self, model) -> None:
        self.model = model
        self.w = 0.0
        self.h = 0.0
        self.px_per_m = 1.0

    def resize(self, w: float, h: float) -> None:
        """Called whenever the canvas changes size. Scenes recompute their
        scale here, which is what makes the simulation genuinely responsive
        instead of a fixed-size bitmap."""
        self.w, self.h = float(w), float(h)
        self.layout()

    def layout(self) -> None:
        """Recompute px_per_m and any fixed geometry."""

    def on_reset(self) -> None:
        """Clear per-run state such as motion trails."""

    @abstractmethod
    def draw(self, p: QPainter, pal: Palette) -> None:
        ...


# ── shared painting helpers ──────────────────────────────────────────────────

def text(p: QPainter, s: str, x: float, y: float, colour: QColor,
         align: str = "left", size: int = 11, bold: bool = False) -> None:
    """Draw a label centred vertically on y. Qt anchors text at the baseline,
    which is almost never what you want, so this offsets by the font metrics."""
    font = QFont(mono_font(), size)
    font.setBold(bold)
    p.setFont(font)
    p.setPen(QPen(colour))

    metrics = QFontMetrics(font)
    width = metrics.horizontalAdvance(s)
    if align == "right":
        x -= width
    elif align == "center":
        x -= width / 2
    p.drawText(QPointF(x, y + metrics.capHeight() / 2), s)


def dashed(p: QPainter, x1: float, y1: float, x2: float, y2: float,
           colour: QColor, width: float = 1.0) -> None:
    pen = QPen(colour, width, Qt.DashLine)
    pen.setDashPattern([4, 5])
    p.setPen(pen)
    p.drawLine(QPointF(x1, y1), QPointF(x2, y2))


def energy_meter(p: QPainter, x: float, y: float, kinetic: float, pal: Palette) -> None:
    """Kinetic vs potential split. The pendulum and the spring both trade one
    for the other while the total stays fixed, which is easier to believe when
    you can watch the bar."""
    w, h = 140.0, 6.0
    text(p, "KINETIC", x, y - 11, pal.q("muted"), size=9)
    text(p, "POTENTIAL", x + w, y - 11, pal.q("muted"), align="right", size=9)

    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(pal.q("line")))
    p.drawRoundedRect(QRectF(x, y, w, h), 3, 3)
    p.setBrush(QBrush(pal.q("good")))
    p.drawRoundedRect(QRectF(x, y, max(2.0, w * kinetic), h), 3, 3)


def ground(p: QPainter, y: float, w: float, h: float, pal: Palette) -> None:
    # A translucent line colour rather than a surface colour: surface_alt is
    # almost exactly the canvas colour in the light theme, so the ground
    # disappeared entirely.
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(pal.q("line", 110)))
    p.drawRect(QRectF(0, y, w, h - y))
    p.setPen(QPen(pal.q("muted", 150), 1.5))
    p.drawLine(QPointF(0, y), QPointF(w, y))


def body(p: QPainter, x: float, y: float, r: float, pal: Palette) -> None:
    """The moving object, with a soft halo so it reads against the backdrop."""
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(pal.q("accent", 46)))
    p.drawEllipse(QPointF(x, y), r + 6, r + 6)
    p.setBrush(QBrush(pal.q("accent")))
    p.setPen(QPen(pal.q("text", 120), 1.5))
    p.drawEllipse(QPointF(x, y), r, r)
