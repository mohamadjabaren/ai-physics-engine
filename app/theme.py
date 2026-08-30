"""
Design tokens and the global stylesheet.

Qt Style Sheets (QSS) are CSS-like, but they only understand literal colours —
there is no var(--accent). So the palette lives here as a dataclass and the
stylesheet is generated from it with an f-string. Swapping Palette instances
restyles the entire application in one call.
"""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor, QFontDatabase


@dataclass(frozen=True)
class Palette:
    name: str
    bg: str
    surface: str
    surface_alt: str
    line: str
    text: str
    muted: str
    accent: str
    accent_soft: str
    measure: str        # amber: measurements and theory-derived values
    good: str
    canvas: str
    trail: str

    def q(self, attr: str, alpha: int = 255) -> QColor:
        """Palette colour as a QColor, optionally with an alpha channel."""
        c = QColor(getattr(self, attr))
        c.setAlpha(alpha)
        return c


DARK = Palette(
    name="dark",
    bg="#0A0E14", surface="#121822", surface_alt="#171F2C", line="#232D3E",
    text="#E6ECF7", muted="#8794AC", accent="#6E7DFF", accent_soft="#1B2340",
    measure="#FFB454", good="#3DDCA6", canvas="#0D1219", trail="#6E7DFF",
)

LIGHT = Palette(
    name="light",
    bg="#EEF1F6", surface="#FFFFFF", surface_alt="#F6F8FC", line="#DDE3EE",
    text="#0F1724", muted="#5B677E", accent="#4553E0", accent_soft="#E8EBFB",
    measure="#B87309", good="#12A87C", canvas="#FBFCFE", trail="#4553E0",
)


def _first_available(candidates: list, fallback: str) -> str:
    """Pick the first font actually installed. Hard-coding one family is the
    classic way to make an app look great on your machine and wrong on every
    other one."""
    families = set(QFontDatabase.families())
    for name in candidates:
        if name in families:
            return name
    return fallback


def ui_font() -> str:
    return _first_available(
        ["Inter", "Space Grotesk", "SF Pro Text", "Segoe UI Variable", "Segoe UI",
         "Ubuntu", "Noto Sans", "DejaVu Sans"], "sans-serif")


def mono_font() -> str:
    return _first_available(
        ["JetBrains Mono", "IBM Plex Mono", "Cascadia Mono", "SF Mono", "Menlo",
         "Consolas", "Ubuntu Mono", "DejaVu Sans Mono"], "monospace")


def stylesheet(p: Palette) -> str:
    ui, mono = ui_font(), mono_font()
    return f"""
    /* Deliberately no background here. A blanket `QWidget {{ background }}`
       makes every child label and container paint the window colour on top of
       whatever card it sits in. Only real surfaces get a background. */
    QWidget {{
        color: {p.text};
        font-family: "{ui}";
        font-size: 14px;
    }}
    QMainWindow, QStackedWidget {{ background: {p.bg}; }}
    QLabel {{ background: transparent; }}
    QToolTip {{
        background: {p.surface_alt}; color: {p.text};
        border: 1px solid {p.line}; padding: 6px;
    }}

    /* ── Cards and panels ─────────────────────────────────────────────── */
    QFrame#Card {{
        background: {p.surface};
        border: 1px solid {p.line};
        border-radius: 14px;
    }}
    QFrame#CanvasFrame {{
        background: {p.canvas};
        border: 1px solid {p.line};
        border-radius: 14px;
    }}
    QLabel#Eyebrow {{
        color: {p.muted}; font-family: "{mono}"; font-size: 10px;
        font-weight: 600; letter-spacing: 2px;
    }}
    QLabel#Title      {{ font-size: 26px; font-weight: 700; }}
    QLabel#CardTitle  {{ font-size: 13px; font-weight: 600; }}
    QLabel#Tagline    {{ color: {p.muted}; font-size: 14px; }}
    QLabel#Muted      {{ color: {p.muted}; }}
    QLabel#Body       {{ color: {p.muted}; font-size: 13px; }}

    /* ── Buttons ──────────────────────────────────────────────────────── */
    QPushButton {{
        background: {p.surface_alt};
        border: 1px solid {p.line};
        border-radius: 10px;
        padding: 8px 16px;
        font-size: 13px;
        font-weight: 500;
    }}
    QPushButton:hover   {{ border-color: {p.accent}; }}
    QPushButton:pressed {{ background: {p.accent_soft}; }}

    QPushButton#Primary {{
        background: {p.accent}; border-color: {p.accent};
        color: #FFFFFF; font-weight: 600; padding: 9px 22px;
    }}
    QPushButton#Primary:hover {{ background: {p.accent}; border-color: {p.text}; }}

    QPushButton#Ghost {{ background: transparent; border-color: transparent; color: {p.muted}; }}
    QPushButton#Ghost:hover {{ color: {p.text}; border-color: {p.line}; }}

    QPushButton#NavPill {{
        background: transparent; border: none; border-radius: 9px;
        padding: 7px 15px; color: {p.muted};
    }}
    QPushButton#NavPill:hover {{ color: {p.text}; background: {p.surface_alt}; }}
    QPushButton#NavPill:checked {{ background: {p.accent}; color: #FFFFFF; font-weight: 600; }}

    QPushButton#SpeedPill {{
        background: transparent; border: none; border-radius: 7px;
        padding: 4px 12px; color: {p.muted}; font-family: "{mono}"; font-size: 12px;
    }}
    QPushButton#SpeedPill:checked {{ background: {p.accent_soft}; color: {p.accent}; font-weight: 600; }}

    QPushButton#PanelHeader {{
        background: transparent; border: none; border-radius: 0px;
        text-align: left; padding: 14px 16px; font-size: 13px; font-weight: 600;
    }}
    QPushButton#PanelHeader:hover {{ color: {p.accent}; }}

    /* ── Sliders ──────────────────────────────────────────────────────── */
    QSlider::groove:horizontal {{
        height: 5px; border-radius: 3px; background: {p.line};
    }}
    QSlider::sub-page:horizontal {{
        height: 5px; border-radius: 3px; background: {p.accent};
    }}
    QSlider::handle:horizontal {{
        width: 15px; height: 15px; margin: -6px 0; border-radius: 8px;
        background: {p.accent}; border: 3px solid {p.surface};
    }}
    QSlider::handle:horizontal:hover {{ border-color: {p.text}; }}

    /* ── Containers ───────────────────────────────────────────────────── */
    QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
    QScrollBar:vertical {{ background: transparent; width: 9px; margin: 0; }}
    QScrollBar::handle:vertical {{ background: {p.line}; border-radius: 4px; min-height: 40px; }}
    QScrollBar::handle:vertical:hover {{ background: {p.muted}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

    QFrame#Divider {{ background: {p.line}; border: none; max-height: 1px; }}
    QPlainTextEdit#Code {{
        background: {p.surface_alt}; border: none; border-radius: 10px;
        font-family: "{mono}"; font-size: 11px; color: {p.text}; padding: 10px;
    }}
    """
