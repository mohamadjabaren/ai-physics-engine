"""
Collapsible panel and discovery card.

Both animate their own height with QPropertyAnimation. The Python gotcha
worth knowing: a QPropertyAnimation that nobody holds a reference to is
garbage-collected the instant the function returns, and the animation simply
never plays. Storing it on `self` is not tidiness, it is required.
"""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtWidgets import (QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel,
                               QPushButton, QVBoxLayout, QWidget)


class CollapsiblePanel(QFrame):
    """A card with a clickable header that animates its body open and shut."""

    def __init__(self, title: str, eyebrow: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")

        self.header = QPushButton(f"  {title}")
        self.header.setObjectName("PanelHeader")
        self.header.setCheckable(True)
        self.header.setChecked(True)
        self.header.setCursor(Qt.PointingHandCursor)
        self.header.clicked.connect(self._toggle)

        self.chevron = QLabel("\u25be")
        self.chevron.setObjectName("Muted")

        self.eyebrow = QLabel(eyebrow.upper())
        self.eyebrow.setObjectName("Eyebrow")

        head = QHBoxLayout()
        head.setContentsMargins(16, 0, 16, 0)
        head.setSpacing(8)
        head.addWidget(self.eyebrow)
        head.addWidget(self.header, 1)
        head.addWidget(self.chevron)

        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(16, 4, 16, 16)
        self.body_layout.setSpacing(17)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addLayout(head)
        outer.addWidget(self.body)

        self._animation = QPropertyAnimation(self.body, b"maximumHeight", self)
        self._animation.setDuration(220)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.finished.connect(self.refresh_height)

    def add(self, widget: QWidget) -> None:
        self.body_layout.addWidget(widget)
        self.refresh_height()

    def refresh_height(self) -> None:
        """Content changed. If the panel is open, lift the height cap so new
        content is not clipped by whatever the last animation left behind."""
        if self.header.isChecked():
            self.body.setMaximumHeight(16777215)

    def _toggle(self, checked: bool) -> None:
        self.chevron.setText("\u25be" if checked else "\u25b8")
        target = self.body.sizeHint().height() if checked else 0
        self._animation.stop()
        self._animation.setStartValue(self.body.height())
        self._animation.setEndValue(target)
        self._animation.start()

    def set_open(self, is_open: bool) -> None:
        self.header.setChecked(is_open)
        self.chevron.setText("\u25be" if is_open else "\u25b8")
        self.body.setMaximumHeight(16777215 if is_open else 0)


class ScenarioCard(QFrame):
    """Predict, then test.

    The question is shown first and the explanation stays hidden until the
    student has actually run it. That ordering is the whole point: reading the
    answer before predicting teaches nothing.
    """

    apply_requested = Signal(object)          # carries the Scenario

    def __init__(self, scenario, palette, parent=None) -> None:
        super().__init__(parent)
        self.scenario = scenario
        self.setObjectName("Scenario")
        self.setStyleSheet(
            f"QFrame#Scenario {{ border:1px solid {palette.line}; border-radius:10px; }}")

        title = QLabel(scenario.title)
        title.setStyleSheet("font-size:13px; font-weight:600;")

        ask = QLabel(scenario.ask)
        ask.setObjectName("Body")
        ask.setWordWrap(True)

        self.reveal = QLabel(scenario.reveal)
        self.reveal.setWordWrap(True)
        self.reveal.setVisible(False)
        self.reveal.setStyleSheet(
            f"color:{palette.text}; font-size:12px; padding-left:10px;"
            f"border-left:2px solid {palette.measure};")

        self.button = QPushButton("Run it and find out")
        self.button.setCursor(Qt.PointingHandCursor)
        self.button.clicked.connect(self._on_click)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(13, 12, 13, 13)
        layout.setSpacing(8)
        layout.addWidget(title)
        layout.addWidget(ask)
        layout.addWidget(self.reveal)
        layout.addWidget(self.button, 0, Qt.AlignLeft)

    def _on_click(self) -> None:
        self.apply_requested.emit(self.scenario)
        if not self.reveal.isVisible():
            self.reveal.setVisible(True)
            self._effect = QGraphicsOpacityEffect(self.reveal)
            self.reveal.setGraphicsEffect(self._effect)
            self._fade = QPropertyAnimation(self._effect, b"opacity", self)
            self._fade.setDuration(320)
            self._fade.setStartValue(0.0)
            self._fade.setEndValue(1.0)
            self._fade.start()
        self.button.setText("Run again")
