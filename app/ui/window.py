"""
The main window: a QStackedWidget holding the landing page and the dashboard.

QStackedWidget is Qt's card stack — many children, one visible. It is the
natural way to do screens in a desktop app, and it keeps both pages alive so
switching back is instant.
"""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QGraphicsOpacityEffect, QMainWindow, QStackedWidget

from app.theme import DARK, LIGHT, stylesheet
from app.ui.dashboard import Dashboard
from app.ui.landing import LandingPage


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI Physics Engine")
        self.resize(1440, 900)
        self.setMinimumSize(1180, 760)

        self.tokens = DARK

        self.stack = QStackedWidget()
        self.landing = LandingPage(self.tokens)
        self.dashboard = Dashboard(self.tokens)
        self.stack.addWidget(self.landing)
        self.stack.addWidget(self.dashboard)
        self.setCentralWidget(self.stack)

        self.landing.experiment_chosen.connect(self.open_experiment)
        self.dashboard.back_requested.connect(self.show_landing)
        self.dashboard.theme_toggled.connect(self.toggle_theme)

        QShortcut(QKeySequence(Qt.Key_Space), self, self.dashboard._toggle_run)
        QShortcut(QKeySequence("R"), self, self.dashboard.reset)
        QShortcut(QKeySequence("T"), self, self.toggle_theme)
        QShortcut(QKeySequence("Escape"), self, self.show_landing)

        self.setStyleSheet(stylesheet(self.tokens))
        self.dashboard.fit_nav_pills()

    def open_experiment(self, exp_id: str) -> None:
        self.dashboard.load_experiment(exp_id)
        self._switch_to(self.dashboard)

    def show_landing(self) -> None:
        self.dashboard.canvas.pause()
        self._switch_to(self.landing)

    def _switch_to(self, page) -> None:
        self.stack.setCurrentWidget(page)
        effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(effect)
        self._transition = QPropertyAnimation(effect, b"opacity", self)
        self._transition.setDuration(260)
        self._transition.setStartValue(0.0)
        self._transition.setEndValue(1.0)
        self._transition.setEasingCurve(QEasingCurve.OutCubic)
        # Drop the effect when finished: a permanent QGraphicsOpacityEffect
        # forces every repaint through an offscreen buffer, which costs frames.
        self._transition.finished.connect(lambda: page.setGraphicsEffect(None))
        self._transition.start()

    def toggle_theme(self) -> None:
        self.tokens = LIGHT if self.tokens.name == "dark" else DARK
        self.setStyleSheet(stylesheet(self.tokens))
        self.dashboard.fit_nav_pills()
        self.landing.tokens = self.tokens
        self.landing.hero.set_palette_tokens(self.tokens)
        self.dashboard.restyle(self.tokens)
