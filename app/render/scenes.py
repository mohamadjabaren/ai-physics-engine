"""
The four scenes. Each one is a pure drawing routine over a model.

Every scene follows the same shape:
    layout()  — work out px_per_m and fixed geometry for the current widget size
    draw()    — paint the bodies, then the measurement annotations on top
"""
from __future__ import annotations

import math
from collections import deque

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QPainter, QPainterPath, QPen

from app.render.scene import Scene, body, dashed, energy_meter, ground, text
from app.theme import Palette


class FreeFallScene(Scene):
    RADIUS = 15.0

    def layout(self) -> None:
        self.ground_y = self.h - 62
        self.top_y = 64
        self.x = self.w * 0.46
        span = self.ground_y - self.RADIUS - self.top_y
        self.px_per_m = span / self.model.p["height"]

    def y_of(self, metres: float) -> float:
        """Screen y grows downwards, physical height grows upwards. This one
        line is the whole coordinate system."""
        return self.ground_y - self.RADIUS - metres * self.px_per_m

    def draw(self, p: QPainter, pal: Palette) -> None:
        m = self.model
        ground(p, self.ground_y, self.w, self.h, pal)

        # Measuring rule down the left of the drop, ticked every quarter.
        rule_x = self.x - 120
        p.setPen(QPen(pal.q("line"), 1))
        p.drawLine(QPointF(rule_x, self.y_of(m.p["height"])), QPointF(rule_x, self.y_of(0)))
        for i in range(5):
            metres = m.p["height"] * i / 4
            y = self.y_of(metres)
            p.setPen(QPen(pal.q("line"), 1))
            p.drawLine(QPointF(rule_x - 5, y), QPointF(rule_x + 5, y))
            text(p, f"{metres:.0f} m", rule_x - 11, y, pal.q("muted"), align="right", size=10)

        ball_y = self.y_of(m.y)
        dashed(p, rule_x, ball_y, self.x - self.RADIUS - 6, ball_y, pal.q("measure", 170))
        body(p, self.x, ball_y, self.RADIUS, pal)
        text(p, f"{m.v:.1f} m/s", self.x + self.RADIUS + 16, ball_y, pal.q("measure"), size=12, bold=True)

        if m.finished:
            text(p, f"IMPACT  \u00b7  {m.v:.1f} m/s after {m.t:.2f} s",
                 self.w / 2, self.ground_y + 28, pal.q("measure"), align="center", size=12, bold=True)


class ProjectileScene(Scene):
    RADIUS = 10.0

    def __init__(self, model) -> None:
        super().__init__(model)
        self.trail: deque = deque(maxlen=600)

    def on_reset(self) -> None:
        self.trail.clear()

    def layout(self) -> None:
        self.ground_y = self.h - 58
        self.origin_x = 78.0
        # Auto-zoom: choose the scale that fits the whole arc on both axes.
        r = max(self.model.range(), 1.0)
        a = max(self.model.apex(), 1.0)
        self.px_per_m = min((self.w - self.origin_x - 80) / r, (self.ground_y - 74) / a)

    def to_px(self, xm: float, ym: float) -> QPointF:
        return QPointF(self.origin_x + xm * self.px_per_m, self.ground_y - ym * self.px_per_m)

    def draw(self, p: QPainter, pal: Palette) -> None:
        m = self.model
        ground(p, self.ground_y, self.w, self.h, pal)

        pos = self.to_px(m.x, max(0.0, m.y))
        if not self.trail or (pos - self.trail[-1]).manhattanLength() > 9:
            self.trail.append(pos)

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(pal.q("trail", 110)))
        for pt in self.trail:
            p.drawEllipse(pt, 2.4, 2.4)

        # Apex crosshair, drawn where the closed form says it should be.
        apex = self.to_px(m.range() / 2, m.apex())
        dashed(p, self.origin_x, apex.y(), self.w - 40, apex.y(), pal.q("line"))
        p.setPen(QPen(pal.q("measure"), 1.4))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(apex, 6, 6)
        text(p, f"apex {m.apex():.1f} m", apex.x() + 13, apex.y() - 13, pal.q("measure"), size=11)

        # Range bracket along the ground.
        end = self.to_px(m.range(), 0.0)
        by = self.ground_y + 22
        p.setPen(QPen(pal.q("measure"), 1.2))
        p.drawLine(QPointF(self.origin_x, by - 5), QPointF(self.origin_x, by + 5))
        p.drawLine(QPointF(self.origin_x, by), QPointF(end.x(), by))
        p.drawLine(QPointF(end.x(), by - 5), QPointF(end.x(), by + 5))
        text(p, f"range {m.range():.1f} m", (self.origin_x + end.x()) / 2, by + 16,
             pal.q("measure"), align="center", size=11)

        # Launch angle indicator.
        th = math.radians(m.p["angle"])
        p.setPen(QPen(pal.q("muted"), 1.4))
        rect = QRectF(self.origin_x - 34, self.ground_y - 34, 68, 68)
        p.drawArc(rect, 0, int(math.degrees(th) * 16))
        p.drawLine(QPointF(self.origin_x, self.ground_y),
                   QPointF(self.origin_x + math.cos(th) * 54, self.ground_y - math.sin(th) * 54))
        text(p, f"{m.p['angle']:.0f}\u00b0", self.origin_x + 42, self.ground_y - 18, pal.q("muted"), size=11)

        body(p, pos.x(), pos.y(), self.RADIUS, pal)


class PendulumScene(Scene):
    BOB_R = 17.0

    def layout(self) -> None:
        self.pivot = QPointF(self.w / 2, 74)
        self.px_per_m = min(132.0, (self.h - self.pivot.y() - 62) / self.model.p["length"])
        self.len_px = self.model.p["length"] * self.px_per_m

    def bob_at(self, theta: float) -> QPointF:
        return QPointF(self.pivot.x() + math.sin(theta) * self.len_px,
                       self.pivot.y() + math.cos(theta) * self.len_px)

    def draw(self, p: QPainter, pal: Palette) -> None:
        m = self.model
        th0 = math.radians(m.p["angle"])

        dashed(p, self.pivot.x(), self.pivot.y(),
               self.pivot.x(), self.pivot.y() + self.len_px + 30, pal.q("line"))

        # The arc the bob is allowed to sweep. Qt angles are in 1/16 degree,
        # measured anticlockwise from 3 o'clock — hence the conversion.
        rect = QRectF(self.pivot.x() - self.len_px, self.pivot.y() - self.len_px,
                      self.len_px * 2, self.len_px * 2)
        p.setPen(QPen(pal.q("line"), 1.5))
        p.setBrush(Qt.NoBrush)
        start = int((-90 - m.p["angle"]) * 16)
        p.drawArc(rect, start, int(2 * m.p["angle"] * 16))

        for sign in (-1, 1):
            pt = self.bob_at(sign * th0)
            p.setPen(QPen(pal.q("measure"), 1.3))
            p.drawEllipse(pt, 4, 4)

        pos = self.bob_at(m.theta)
        p.setPen(QPen(pal.q("muted"), 2.5))
        p.drawLine(self.pivot, pos)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(pal.q("muted")))
        p.drawEllipse(self.pivot, 5, 5)
        body(p, pos.x(), pos.y(), self.BOB_R, pal)

        text(p, f"\u03b8 = {math.degrees(m.theta):+.1f}\u00b0",
             self.pivot.x() + 18, self.pivot.y() - 4, pal.q("measure"), size=12, bold=True)
        text(p, f"L = {m.p['length']:.2f} m",
             self.pivot.x() - 18, self.pivot.y() + self.len_px / 2, pal.q("muted"), align="right", size=11)

        energy_meter(p, 34, self.h - 34, m.kinetic_fraction(), pal)


class SpringScene(Scene):
    BOX_W, BOX_H = 78.0, 56.0
    COILS = 11

    def layout(self) -> None:
        self.anchor = QPointF(self.w / 2, 88)
        self.rest_px = min(200.0, (self.h - 260))
        self.eq_y = self.anchor.y() + self.rest_px
        # Keep the block clear of the ceiling at maximum amplitude.
        head_room = self.rest_px - self.BOX_H / 2 - 24
        self.px_per_m = min(250.0, head_room / self.model.p["amplitude"])

    def draw(self, p: QPainter, pal: Palette) -> None:
        m = self.model
        amp_px = m.p["amplitude"] * self.px_per_m
        block_y = self.eq_y + m.x * self.px_per_m

        # Ceiling slab with hatching.
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(pal.q("surface_alt")))
        p.drawRect(QRectF(self.anchor.x() - 100, self.anchor.y() - 26, 200, 26))
        p.setPen(QPen(pal.q("line"), 1))
        for i in range(11):
            x = self.anchor.x() - 96 + i * 19
            p.drawLine(QPointF(x, self.anchor.y()), QPointF(x + 11, self.anchor.y() - 12))
        p.drawLine(QPointF(self.anchor.x() - 100, self.anchor.y()),
                   QPointF(self.anchor.x() + 100, self.anchor.y()))

        # The coil: a zigzag between anchor and the top of the block. Points
        # alternate left and right of the centre line, so the spring visibly
        # bunches up as the block rises.
        top = block_y - self.BOX_H / 2
        path = QPainterPath(self.anchor)
        span = top - self.anchor.y()
        for i in range(1, self.COILS):
            offset = 13 if i % 2 == 0 else -13
            path.lineTo(self.anchor.x() + offset, self.anchor.y() + span * i / self.COILS)
        path.lineTo(QPointF(self.anchor.x(), top))
        p.setPen(QPen(pal.q("muted"), 2.4))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

        dashed(p, self.anchor.x() - 148, self.eq_y, self.anchor.x() + 52, self.eq_y, pal.q("line"))
        text(p, "x = 0", self.anchor.x() - 156, self.eq_y, pal.q("muted"), align="right", size=10)

        # Amplitude bracket.
        bx = self.anchor.x() + 78
        p.setPen(QPen(pal.q("measure"), 1.2))
        for sign in (-1, 1):
            y = self.eq_y + sign * amp_px
            p.drawLine(QPointF(bx - 18, y), QPointF(bx + 18, y))
        p.drawLine(QPointF(bx, self.eq_y - amp_px), QPointF(bx, self.eq_y + amp_px))
        text(p, f"A = {m.p['amplitude']:.2f} m", bx + 28, self.eq_y, pal.q("measure"), size=11)

        # The block.
        rect = QRectF(self.anchor.x() - self.BOX_W / 2, block_y - self.BOX_H / 2, self.BOX_W, self.BOX_H)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(pal.q("accent", 46)))
        p.drawRoundedRect(rect.adjusted(-5, -5, 5, 5), 12, 12)
        p.setBrush(QBrush(pal.q("accent")))
        p.setPen(QPen(pal.q("text", 120), 1.5))
        p.drawRoundedRect(rect, 9, 9)

        text(p, f"x = {m.x:+.3f} m", self.anchor.x() - self.BOX_W / 2 - 16, block_y,
             pal.q("measure"), align="right", size=12, bold=True)
        energy_meter(p, 34, self.h - 34, m.kinetic_fraction(), pal)


SCENES = {
    "free_fall": FreeFallScene,
    "projectile": ProjectileScene,
    "pendulum": PendulumScene,
    "spring": SpringScene,
}
