"""
One labelled slider.

QSlider only works in integers, so a float parameter is mapped onto integer
ticks: tick i means `minimum + i * step`. Every float slider you have ever
used does some version of this.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget

from app.core.catalog import Parameter


class ParameterSlider(QWidget):
    value_changed = Signal(str, float)          # (parameter key, new value)

    def __init__(self, spec: Parameter, parent=None) -> None:
        super().__init__(parent)
        self.spec = spec
        self._ticks = max(1, round((spec.maximum - spec.minimum) / spec.step))

        self.name = QLabel(spec.label)
        self.readout = QLabel()
        self.readout.setObjectName("ValueChip")
        self.readout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, self._ticks)
        self.slider.setValue(self._to_tick(spec.value))
        # valueChanged fires continuously while dragging, which is what makes
        # the simulation feel live. sliderReleased would feel laggy.
        self.slider.valueChanged.connect(self._on_slider)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.addWidget(self.name)
        top.addStretch(1)
        top.addWidget(self.readout)

        scale = QHBoxLayout()
        scale.setContentsMargins(0, 0, 0, 0)
        for value, align in ((spec.minimum, Qt.AlignLeft), (spec.maximum, Qt.AlignRight)):
            tick = QLabel(f"{value:g}")
            tick.setObjectName("Tick")
            tick.setAlignment(align)
            scale.addWidget(tick)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.addLayout(top)
        layout.addWidget(self.slider)
        layout.addLayout(scale)

        self._refresh_readout(spec.value)

    # ── tick <-> float conversion ────────────────────────────────────────
    def _to_tick(self, value: float) -> int:
        return round((value - self.spec.minimum) / self.spec.step)

    def _to_value(self, tick: int) -> float:
        return self.spec.minimum + tick * self.spec.step

    # ── slots ────────────────────────────────────────────────────────────
    def _on_slider(self, tick: int) -> None:
        value = self._to_value(tick)
        self._refresh_readout(value)
        self.value_changed.emit(self.spec.key, value)

    def _refresh_readout(self, value: float) -> None:
        self.readout.setText(f"{value:.{self.spec.decimals}f} {self.spec.unit}")

    def set_value(self, value: float) -> None:
        """Move the slider from code (used by the discovery scenarios).
        blockSignals stops this from bouncing back as a user edit."""
        self.slider.blockSignals(True)
        self.slider.setValue(self._to_tick(value))
        self.slider.blockSignals(False)
        self._refresh_readout(value)

    def restyle(self, palette) -> None:
        self.readout.setStyleSheet(
            f"color:{palette.accent}; background:{palette.accent_soft};"
            f"border-radius:7px; padding:2px 9px; font-family:monospace; font-size:12px;")
        for tick in self.findChildren(QLabel):
            if tick.objectName() == "Tick":
                tick.setStyleSheet(f"color:{palette.muted}; font-family:monospace; font-size:10px;")
