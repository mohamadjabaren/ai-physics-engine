"""
LaTeX formulas without a TeX installation.

matplotlib ships `mathtext`, its own renderer for a large subset of TeX. We
rasterise each formula once to a transparent PNG and cache the bytes, so
reopening the theory panel costs nothing.

If matplotlib is missing the app still runs — it falls back to showing the
LaTeX source. A portfolio project that crashes on an optional dependency is a
bad look in a live demo.
"""
from __future__ import annotations

from functools import lru_cache
from io import BytesIO

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy

try:
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    MATHTEXT = True
except ImportError:                                     # pragma: no cover
    MATHTEXT = False


@lru_cache(maxsize=256)
def _render_png(tex: str, colour: str, fontsize: int, dpi: int) -> bytes:
    """Rasterise one formula. Cached on the arguments, so the second call for
    the same formula and theme is free."""
    fig = Figure(figsize=(0.01, 0.01))
    FigureCanvasAgg(fig)                                # attach a backend
    fig.patch.set_alpha(0.0)
    fig.text(0, 0, f"${tex}$", fontsize=fontsize, color=colour)

    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=dpi, transparent=True,
                bbox_inches="tight", pad_inches=0.10)
    return buffer.getvalue()


class FormulaLabel(QLabel):
    """A single centred, rendered equation."""

    def __init__(self, tex: str, parent=None) -> None:
        super().__init__(parent)
        self.tex = tex
        self._source: QPixmap | None = None     # full-resolution render
        self.setAlignment(Qt.AlignCenter)
        # Ignored horizontally: a wide equation must never widen its container.
        # Without this a long formula pushes the whole sidebar past the edge of
        # its scroll area and every control to its left gets clipped.
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

    def restyle(self, palette, fontsize: int = 13) -> None:
        """Re-render for the current theme.

        The glyphs are baked into a bitmap, so a theme change means rasterising
        again — there is no such thing as recolouring a pixmap after the fact.
        The card background has to move with it or you get dark-on-dark.
        """
        colour = palette.text
        self.setStyleSheet(
            f"background:{palette.surface_alt}; border-radius:9px; padding:9px;")

        if not MATHTEXT:
            self.setText(self.tex)
            self.setStyleSheet(
                f"color:{palette.muted}; background:{palette.surface_alt};"
                f"border-radius:9px; padding:9px; font-family:monospace; font-size:11px;")
            return

        ratio = self.devicePixelRatioF() or 1.0
        try:
            png = _render_png(self.tex, colour, fontsize, int(100 * ratio))
        except Exception:                               # malformed TeX, missing glyph
            self.setText(self.tex)
            return

        pixmap = QPixmap()
        pixmap.loadFromData(png, "PNG")
        pixmap.setDevicePixelRatio(ratio)
        self._source = pixmap
        self._fit()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit()

    def _fit(self) -> None:
        """Shrink the rendered equation to the width actually available.

        Rescaling from the original render each time, rather than from the
        last scaled copy, keeps it sharp: repeatedly scaling an already scaled
        bitmap compounds the blur.
        """
        if self._source is None:
            return
        ratio = self._source.devicePixelRatio() or 1.0
        available = max(60, self.width() - 20)
        logical_width = self._source.width() / ratio

        pixmap = self._source
        if logical_width > available:
            pixmap = self._source.scaledToWidth(
                int(available * ratio), Qt.SmoothTransformation)
            pixmap.setDevicePixelRatio(ratio)

        self.setPixmap(pixmap)
        self.setMinimumHeight(int(pixmap.height() / ratio) + 20)
