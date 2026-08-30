"""
Live telemetry plot.

pyqtgraph rather than matplotlib: matplotlib is built for publication figures
and redraws far too slowly for a 60 Hz stream. pyqtgraph draws straight onto
Qt's scene graph and handles tens of thousands of points without complaint.

Two series with different units (metres and metres per second) need two y
axes. pyqtgraph has no built-in twin axis, so the right-hand one is a second
ViewBox laid over the first, kept in step by hand — this is the standard
recipe from the pyqtgraph examples.
"""
from __future__ import annotations

import pyqtgraph as pg
from PySide6.QtWidgets import QVBoxLayout, QWidget


class TelemetryPlot(QWidget):
    FLUSH_EVERY = 3          # append to the curves every Nth frame

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        pg.setConfigOptions(antialias=True)

        self.widget = pg.PlotWidget()
        self.plot = self.widget.getPlotItem()
        self.plot.showGrid(x=True, y=True, alpha=0.12)
        self.plot.setMenuEnabled(False)

        self.right_box = pg.ViewBox()
        self.plot.showAxis("right")
        self.plot.scene().addItem(self.right_box)
        self.plot.getAxis("right").linkToView(self.right_box)
        self.right_box.setXLink(self.plot)
        self.plot.vb.sigResized.connect(self._sync_right_box)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 2)
        layout.addWidget(self.widget)

        self.graph = None
        self.curves: list = []
        self.buffers: list = []
        self._frames = 0

    def _sync_right_box(self) -> None:
        """Keep the overlaid ViewBox exactly on top of the main one."""
        self.right_box.setGeometry(self.plot.vb.sceneBoundingRect())
        self.right_box.linkedViewChanged(self.plot.vb, self.right_box.XAxis)

    def configure(self, graph, palette) -> None:
        """Rebuild axes and curves for a new experiment."""
        self.graph = graph
        self.right_box.clear()
        self.plot.clear()
        self.curves, self.buffers = [], []

        self.widget.setBackground(palette.surface)
        axis_pen = pg.mkPen(palette.line)
        text_pen = pg.mkPen(palette.muted)
        label_style = {"color": palette.muted, "font-size": "10pt"}

        for name in ("left", "bottom", "right"):
            axis = self.plot.getAxis(name)
            axis.setPen(axis_pen)
            axis.setTextPen(text_pen)

        self.plot.setLabel("bottom", graph.x_label, **label_style)
        left = [s for s in graph.series if s.axis == "left"]
        right = [s for s in graph.series if s.axis == "right"]
        self.plot.setLabel("left", f"{left[0].name} ({left[0].unit})", **label_style)

        if right:
            self.plot.getAxis("right").setLabel(f"{right[0].name} ({right[0].unit})", **label_style)
            self.plot.showAxis("right")
        else:
            self.plot.hideAxis("right")

        colours = (palette.accent, palette.measure)
        for index, series in enumerate(graph.series):
            pen = pg.mkPen(colours[index % 2], width=2)
            curve = pg.PlotDataItem(pen=pen, name=series.name)
            if series.axis == "right":
                self.right_box.addItem(curve)
            else:
                self.plot.addItem(curve)
            self.curves.append(curve)
            self.buffers.append(([], []))

        self._lock_axis_scales()
        self._sync_right_box()

    def _lock_axis_scales(self) -> None:
        """Force every axis to plot raw SI values.

        pyqtgraph likes to relabel 0.2 s as "200" with a "(x0.001)" multiplier
        on the axis title. Turning that off is not enough on its own:
        enableAutoSIPrefix() calls updateAutoSIPrefix() internally, which bakes
        a scale factor from whatever range the axis happens to hold at that
        moment -- which, when switching experiments, is the *previous* one. Go
        from the spring (0.3 m) to free fall (80 m) and the heights come out
        multiplied by a thousand.

        There is no public setter for the residual factor, so it is cleared
        directly and the cached tick painting is discarded.
        """
        for name in ("left", "bottom", "right"):
            axis = self.plot.getAxis(name)
            axis.enableAutoSIPrefix(False)
            axis.autoSIPrefixScale = 1.0
            axis.labelUnitPrefix = ""
            axis.picture = None
            axis.update()

    def restyle(self, palette) -> None:
        """Recolour for a new theme while keeping the data on screen.

        Calling configure() again would work, but it rebuilds the curves and
        throws away the run in progress. Changing the theme should not cost
        the student their experiment.
        """
        self.widget.setBackground(palette.surface)
        for name in ("left", "bottom", "right"):
            axis = self.plot.getAxis(name)
            axis.setPen(pg.mkPen(palette.line))
            axis.setTextPen(pg.mkPen(palette.muted))
        colours = (palette.accent, palette.measure)
        for index, curve in enumerate(self.curves):
            curve.setPen(pg.mkPen(colours[index % 2], width=2))

    def clear(self) -> None:
        self.buffers = [([], []) for _ in self.curves]
        for curve in self.curves:
            curve.setData([], [])

    def push(self, state: dict) -> None:
        """Buffer one sample and redraw every few frames."""
        if self.graph is None:
            return
        x = state.get(self.graph.x_key)
        for (xs, ys), series in zip(self.buffers, self.graph.series):
            xs.append(x)
            ys.append(state.get(series.key, 0.0))

        self._frames += 1
        if self._frames % self.FLUSH_EVERY == 0:
            for curve, (xs, ys) in zip(self.curves, self.buffers):
                curve.setData(xs, ys)
            self.right_box.enableAutoRange(axis=pg.ViewBox.YAxis)
