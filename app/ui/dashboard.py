"""
The dashboard: a two-column grid, not a stack.

    ┌───────────────────────────────────────────┬──────────────────┐
    │  header: back · title · experiment pills  │                  │
    ├───────────────────────────────────────────┤   Parameters     │
    │                                           │   ─────────────  │
    │            simulation canvas              │   Theory      ▾  │
    │                                           │   ─────────────  │
    ├───────────────────────────────────────────┤   Predict     ▾  │
    │  transport: run · reset · speed           │   ─────────────  │
    ├───────────────────────────────────────────┤   Source      ▾  │
    │  readout strip                            │                  │
    ├───────────────────────────────────────────┤   (scrolls)      │
    │  telemetry plot                           │                  │
    └───────────────────────────────────────────┴──────────────────┘

The left column stretches; the right one is a fixed-width scrollable rail.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel,
                               QPlainTextEdit, QPushButton, QScrollArea,
                               QSizePolicy, QVBoxLayout, QWidget)

from app.core.catalog import EXPERIMENTS, experiment_by_id
from app.render.canvas import SimulationCanvas
from app.theme import Palette
from app.ui.widgets.formula import FormulaLabel
from app.ui.widgets.panels import CollapsiblePanel, ScenarioCard
from app.ui.widgets.parameter_slider import ParameterSlider
from app.ui.widgets.readout_strip import ReadoutStrip
from app.ui.widgets.telemetry import TelemetryPlot

SPEEDS = (0.25, 0.5, 1.0, 2.0)


class Dashboard(QWidget):
    back_requested = Signal()
    theme_toggled = Signal()

    def __init__(self, palette: Palette, parent=None) -> None:
        super().__init__(parent)
        self.tokens = palette
        self.experiment = EXPERIMENTS[0]
        self.params: dict = self.experiment.defaults()
        self.sliders: dict = {}
        self._formulas: list = []

        self._build_header()
        self._build_stage()
        self._build_sidebar()

        columns = QHBoxLayout()
        columns.setSpacing(18)
        columns.addWidget(self.stage, 1)
        columns.addWidget(self.rail, 0)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 20)
        root.setSpacing(16)
        root.addWidget(self.header)
        root.addLayout(columns, 1)

        self.load_experiment(self.experiment.id)

    # ── construction ─────────────────────────────────────────────────────
    def _build_header(self) -> None:
        self.header = QWidget()

        back = QPushButton("\u2190  Experiments")
        back.setObjectName("Ghost")
        back.setCursor(Qt.PointingHandCursor)
        back.clicked.connect(self.back_requested.emit)

        self.pill_group = QButtonGroup(self)
        self.pill_group.setExclusive(True)
        pills = QFrame()
        pills.setObjectName("Card")
        pill_row = QHBoxLayout(pills)
        pill_row.setContentsMargins(4, 4, 4, 4)
        pill_row.setSpacing(3)
        for experiment in EXPERIMENTS:
            pill = QPushButton(experiment.title)
            pill.setObjectName("NavPill")
            pill.setCheckable(True)
            pill.setCursor(Qt.PointingHandCursor)
            pill.clicked.connect(lambda _=False, e=experiment: self.load_experiment(e.id))
            self.pill_group.addButton(pill)
            pill_row.addWidget(pill)
            if experiment.id == self.experiment.id:
                pill.setChecked(True)

        theme = QPushButton("\u25d1")
        theme.setObjectName("Ghost")
        theme.setFixedWidth(42)
        theme.setToolTip("Switch theme")
        theme.setCursor(Qt.PointingHandCursor)
        theme.clicked.connect(self.theme_toggled.emit)

        row = QHBoxLayout(self.header)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(back)
        row.addStretch(1)
        row.addWidget(pills)
        row.addStretch(1)
        row.addWidget(theme)

    def _build_stage(self) -> None:
        self.stage = QWidget()

        self.eyebrow = QLabel()
        self.eyebrow.setObjectName("Eyebrow")
        self.title = QLabel()
        self.title.setObjectName("Title")
        self.tagline = QLabel()
        self.tagline.setObjectName("Tagline")
        self.tagline.setWordWrap(True)

        self.canvas = SimulationCanvas()
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.frame_advanced.connect(self._on_frame)
        self.canvas.run_state_changed.connect(self._sync_transport)

        self.run_button = QPushButton("Run")
        self.run_button.setObjectName("Primary")
        self.run_button.setCursor(Qt.PointingHandCursor)
        self.run_button.setMinimumWidth(118)
        self.run_button.clicked.connect(self._toggle_run)

        reset = QPushButton("Reset")
        reset.setCursor(Qt.PointingHandCursor)
        reset.clicked.connect(self.reset)

        speed_frame = QFrame()
        speed_frame.setObjectName("Card")
        speed_row = QHBoxLayout(speed_frame)
        speed_row.setContentsMargins(4, 4, 4, 4)
        speed_row.setSpacing(2)
        self.speed_group = QButtonGroup(self)
        for value in SPEEDS:
            pill = QPushButton(f"{value:g}\u00d7")
            pill.setObjectName("SpeedPill")
            pill.setCheckable(True)
            pill.setChecked(value == 1.0)
            pill.setCursor(Qt.PointingHandCursor)
            pill.clicked.connect(lambda _=False, v=value: self._set_speed(v))
            self.speed_group.addButton(pill)
            speed_row.addWidget(pill)

        transport = QHBoxLayout()
        transport.setSpacing(9)
        transport.addWidget(self.run_button)
        transport.addWidget(reset)
        transport.addStretch(1)
        transport.addWidget(speed_frame)

        self.readouts = ReadoutStrip()

        plot_card = QFrame()
        plot_card.setObjectName("Card")
        plot_card.setMinimumHeight(186)
        self.telemetry = TelemetryPlot()
        plot_layout = QVBoxLayout(plot_card)
        plot_layout.setContentsMargins(4, 4, 4, 4)
        plot_layout.addWidget(self.telemetry)

        layout = QVBoxLayout(self.stage)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self.eyebrow)
        layout.addWidget(self.title)
        layout.addWidget(self.tagline)
        layout.addWidget(self.canvas, 1)
        layout.addLayout(transport)
        layout.addWidget(self.readouts)
        layout.addWidget(plot_card)

    def _build_sidebar(self) -> None:
        self.rail = QScrollArea()
        self.rail.setWidgetResizable(True)
        self.rail.setFixedWidth(392)
        self.rail.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        inner = QWidget()
        self.rail_layout = QVBoxLayout(inner)
        self.rail_layout.setContentsMargins(0, 0, 10, 0)
        self.rail_layout.setSpacing(14)

        self.param_panel = CollapsiblePanel("Parameters", "inputs")
        self.theory_panel = CollapsiblePanel("The equations", "theory")
        self.scenario_panel = CollapsiblePanel("Predict, then test", "discovery")
        self.source_panel = CollapsiblePanel("The maths behind this scene", "source")

        self.code_view = QPlainTextEdit()
        self.code_view.setObjectName("Code")
        self.code_view.setReadOnly(True)
        self.code_view.setMinimumHeight(190)
        self.source_panel.add(self.code_view)
        self.source_panel.set_open(False)

        for panel in (self.param_panel, self.theory_panel,
                      self.scenario_panel, self.source_panel):
            self.rail_layout.addWidget(panel)
        self.rail_layout.addStretch(1)
        self.rail.setWidget(inner)

    def fit_nav_pills(self) -> None:
        """Reserve room for each pill's text.

        Must run *after* the window stylesheet has been applied: the font size
        comes from QSS, so measuring at construction time uses the wrong
        metrics and the labels get clipped mid-word.
        """
        for pill in self.pill_group.buttons():
            # Measure in bold: the selected pill is font-weight 600, so sizing
            # to the regular weight clips whichever tab is currently active.
            bold = QFont(pill.font())
            bold.setBold(True)
            width = QFontMetrics(bold).horizontalAdvance(pill.text())
            pill.setMinimumWidth(width + 38)
        self.header.updateGeometry()

    # ── loading an experiment ────────────────────────────────────────────
    def load_experiment(self, exp_id: str) -> None:
        self.experiment = experiment_by_id(exp_id)
        self.params = self.experiment.defaults()

        index = EXPERIMENTS.index(self.experiment) + 1
        self.eyebrow.setText(f"EXPERIMENT {index:02d}")
        self.title.setText(self.experiment.title)
        self.tagline.setText(self.experiment.tagline)
        self.code_view.setPlainText(self.experiment.code)

        for pill, experiment in zip(self.pill_group.buttons(), EXPERIMENTS):
            pill.setChecked(experiment.id == self.experiment.id)

        self._fill_parameters()
        self._fill_theory()
        self._fill_scenarios()

        self.telemetry.configure(self.experiment.graph, self.tokens)
        self.canvas.load(self.experiment, self.params)
        self.readouts.build(self.canvas.model, self.tokens)
        self._sync_transport(False)

    def _clear(self, panel: CollapsiblePanel) -> None:
        """Empty a panel before refilling it.

        setParent(None) is the important part. deleteLater() only schedules
        destruction for the next event-loop pass, so a widget taken out of the
        layout but still parented carries on painting at its old position --
        which stacks every experiment's controls on top of the last one.
        """
        while panel.body_layout.count():
            item = panel.body_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        panel.refresh_height()

    def _fill_parameters(self) -> None:
        self._clear(self.param_panel)
        self.sliders = {}
        for spec in self.experiment.parameters:
            slider = ParameterSlider(spec)
            slider.restyle(self.tokens)
            slider.value_changed.connect(self._on_parameter)
            self.param_panel.add(slider)
            self.sliders[spec.key] = slider

    def _fill_theory(self) -> None:
        self._clear(self.theory_panel)
        self._formulas = []
        for tex in self.experiment.formulas:
            formula = FormulaLabel(tex)
            formula.restyle(self.tokens)
            self.theory_panel.add(formula)
            self._formulas.append(formula)
        for paragraph in self.experiment.theory:
            label = QLabel(paragraph)
            label.setObjectName("Body")
            label.setWordWrap(True)
            self.theory_panel.add(label)

    def _fill_scenarios(self) -> None:
        self._clear(self.scenario_panel)
        for scenario in self.experiment.scenarios:
            card = ScenarioCard(scenario, self.tokens)
            card.apply_requested.connect(self._apply_scenario)
            self.scenario_panel.add(card)

    # ── slots ────────────────────────────────────────────────────────────
    def _on_parameter(self, key: str, value: float) -> None:
        """A slider moved: rebuild the model from the new numbers.

        Changing a parameter changes the initial conditions, so continuing the
        old run would be meaningless. Restarting is the honest behaviour.
        """
        self.params[key] = value
        was_running = self.canvas.running
        self.canvas.load(self.experiment, self.params)
        self.telemetry.clear()
        self.readouts.update_values(self.canvas.model)
        if was_running:
            self.canvas.play()

    def _apply_scenario(self, scenario) -> None:
        for key, value in scenario.params.items():
            self.params[key] = value
            if key in self.sliders:
                self.sliders[key].set_value(value)
        self.canvas.load(self.experiment, self.params)
        self.telemetry.clear()
        self.readouts.update_values(self.canvas.model)
        self.canvas.play()

    def _on_frame(self, model) -> None:
        self.readouts.update_values(model)
        self.telemetry.push(model.state())

    def _toggle_run(self) -> None:
        if self.canvas.model is not None and self.canvas.model.finished:
            self.reset()
        self.canvas.toggle()

    def reset(self) -> None:
        self.canvas.load(self.experiment, self.params)
        self.telemetry.clear()
        self.readouts.update_values(self.canvas.model)
        self._sync_transport(False)

    def _set_speed(self, value: float) -> None:
        self.canvas.speed = value

    def _sync_transport(self, running: bool) -> None:
        model = self.canvas.model
        if running:
            label = "Pause"
        elif model is None:
            label = "Run"
        elif model.finished:
            label = "Replay"
        elif model.t > 0:
            label = "Resume"
        else:
            label = "Run"
        self.run_button.setText(label)

    # ── theming ──────────────────────────────────────────────────────────
    def restyle(self, palette: Palette) -> None:
        self.tokens = palette
        self.canvas.set_palette_tokens(palette)
        self.telemetry.restyle(palette)
        self.readouts.build(self.canvas.model, palette)
        for slider in self.sliders.values():
            slider.restyle(palette)
        for formula in self._formulas:
            formula.restyle(palette)
        self._fill_scenarios()
