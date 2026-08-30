"""
The instrument strip under the canvas.

Built once per experiment, then only the numbers are rewritten each frame.
Rebuilding the widgets sixty times a second would thrash the layout engine
for no reason.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class _Cell(QWidget):
    def __init__(self, readout, palette, parent=None) -> None:
        super().__init__(parent)
        self.key = QLabel(readout.key.upper())
        self.value = QLabel(readout.value)
        self.unit = QLabel(readout.unit)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        row.addWidget(self.value)
        row.addWidget(self.unit, 0, Qt.AlignBottom)
        row.addStretch(1)

        column = QVBoxLayout(self)
        column.setContentsMargins(16, 11, 16, 12)
        column.setSpacing(2)
        column.addWidget(self.key)
        column.addLayout(row)

        accent = palette.measure if readout.derived else palette.text
        self.key.setStyleSheet(
            f"color:{palette.muted}; font-family:monospace; font-size:9px; letter-spacing:1.5px;")
        self.value.setStyleSheet(
            f"color:{accent}; font-family:monospace; font-size:19px; font-weight:600;")
        self.unit.setStyleSheet(f"color:{palette.muted}; font-size:11px;")


class ReadoutStrip(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self._cells: list = []
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(2, 2, 2, 2)
        self._layout.setSpacing(0)

    def build(self, model, palette) -> None:
        # setParent(None) before deleteLater, or the previous experiment's
        # cells keep painting until the event loop destroys them.
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self._cells.clear()

        readouts = model.readouts()
        for index, readout in enumerate(readouts):
            if index:
                divider = QFrame()
                divider.setFixedWidth(1)
                divider.setStyleSheet(f"background:{palette.line};")
                self._layout.addWidget(divider)
            cell = _Cell(readout, palette)
            self._cells.append(cell)
            self._layout.addWidget(cell, 1)

    def update_values(self, model) -> None:
        for cell, readout in zip(self._cells, model.readouts()):
            cell.value.setText(readout.value)
