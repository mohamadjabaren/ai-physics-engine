"""
The experiment catalogue — pure data.

To add a fifth experiment you write a model class in model.py, a scene class
in app/render/scenes.py, and one Experiment entry here. Nothing else changes:
the sliders, readouts, theory panel, telemetry axes and discovery cards are
all generated from this description.

Note `scene_key` rather than a Scene class. Naming the scene by string keeps
this module free of any import from the render layer, which is what lets the
core stay Qt-free.
"""
from __future__ import annotations

from dataclasses import dataclass

from .model import FreeFallModel, PendulumModel, ProjectileModel, SpringModel


@dataclass(frozen=True)
class Parameter:
    key: str
    label: str
    value: float
    minimum: float
    maximum: float
    step: float
    unit: str

    @property
    def decimals(self) -> int:
        """How many decimal places the step implies, for display."""
        text = f"{self.step:g}"
        return len(text.split(".")[1]) if "." in text else 0


@dataclass(frozen=True)
class Series:
    key: str        # a key of model.state()
    name: str
    unit: str
    axis: str = "left"   # "left" or "right"


@dataclass(frozen=True)
class Graph:
    x_key: str
    x_label: str
    series: tuple


@dataclass(frozen=True)
class Scenario:
    """A predict-then-test card. The answer stays hidden until it is run."""
    title: str
    ask: str
    reveal: str
    params: dict


@dataclass(frozen=True)
class Experiment:
    id: str
    title: str
    tagline: str
    model_cls: type
    scene_key: str
    parameters: tuple
    formulas: tuple      # LaTeX source, rendered by matplotlib mathtext
    theory: tuple
    scenarios: tuple
    graph: Graph
    code: str

    def defaults(self) -> dict:
        return {p.key: p.value for p in self.parameters}

    def parameter(self, key: str) -> Parameter:
        return next(p for p in self.parameters if p.key == key)


EXPERIMENTS = (
    Experiment(
        id="free_fall",
        title="Free Fall",
        tagline="One force, one equation. Drop something and watch gravity do all the work.",
        model_cls=FreeFallModel,
        scene_key="free_fall",
        parameters=(
            Parameter("gravity", "Gravity", 9.8, 1.0, 25.0, 0.1, "m/s\u00b2"),
            Parameter("height", "Drop height", 80.0, 10.0, 200.0, 5.0, "m"),
        ),
        formulas=(
            r"h(t) = h_0 - \frac{1}{2}\,g\,t^2",
            r"v(t) = g\,t",
            r"t_{fall} = \sqrt{\frac{2h_0}{g}}\qquad v_{impact} = \sqrt{2\,g\,h_0}",
        ),
        theory=(
            "With no air resistance the only force is weight, so every object accelerates "
            "at the same rate g \u2014 a feather and a hammer land together. David Scott "
            "actually tested this on the Moon during Apollo 15.",
            "Mass appears nowhere in these equations. That is the whole surprise of free "
            "fall, and it is why this panel has no mass slider.",
        ),
        scenarios=(
            Scenario("Drop it on the Moon",
                     "Lunar gravity is about 6\u00d7 weaker. Does the fall take 6\u00d7 longer?",
                     "No \u2014 about 2.5\u00d7 longer. Time depends on \u221a(1/g), not 1/g, so a "
                     "sixfold drop in gravity stretches the fall by \u221a6 \u2248 2.45.",
                     {"gravity": 1.6}),
            Scenario("Double the height",
                     "From 160 m instead of 80 m, is the impact speed doubled?",
                     "No \u2014 it rises by \u221a2 \u2248 1.41\u00d7. Impact speed goes as \u221ah\u2080, so "
                     "doubling the drop only multiplies the speed by 1.41.",
                     {"height": 160.0, "gravity": 9.8}),
            Scenario("Stand on Jupiter",
                     "At g = 24.8 m/s\u00b2, how long does an 80 m fall last?",
                     "About 2.5 s instead of 4.0 s. Check the fall-time readout against "
                     "\u221a(2h\u2080/g).",
                     {"gravity": 24.8, "height": 80.0}),
        ),
        graph=Graph("t", "Time (s)", (
            Series("y", "Height", "m", "left"),
            Series("v", "Speed", "m/s", "right"),
        )),
        code=(
            "def step(self, dt):\n"
            "    self.t += dt\n"
            "    g, h0 = self.p['gravity'], self.p['height']\n\n"
            "    self.y = h0 - 0.5 * g * self.t ** 2   # h(t) = h0 - 1/2 g t^2\n"
            "    self.v = g * self.t                   # v(t) = g t\n\n"
            "    if self.y <= 0.0:                     # landed\n"
            "        self.t = math.sqrt(2 * h0 / g)\n"
            "        self.v = math.sqrt(2 * g * h0)\n"
            "        self.finished = True"
        ),
    ),

    Experiment(
        id="projectile",
        title="Projectile Motion",
        tagline="Horizontal and vertical motion are independent \u2014 two 1-D problems in a trench coat.",
        model_cls=ProjectileModel,
        scene_key="projectile",
        parameters=(
            Parameter("gravity", "Gravity", 9.8, 1.0, 25.0, 0.1, "m/s\u00b2"),
            Parameter("v0", "Launch speed", 25.0, 5.0, 60.0, 1.0, "m/s"),
            Parameter("angle", "Launch angle", 45.0, 5.0, 85.0, 1.0, "\u00b0"),
        ),
        formulas=(
            r"x(t) = v_0\cos\theta\,t \qquad y(t) = v_0\sin\theta\,t - \frac{1}{2}g t^2",
            r"R = \frac{v_0^{2}\sin 2\theta}{g}",
            r"H = \frac{(v_0\sin\theta)^2}{2g} \qquad T = \frac{2v_0\sin\theta}{g}",
        ),
        theory=(
            "The horizontal velocity v\u2080cos\u03b8 never changes, because nothing pushes "
            "sideways. The vertical velocity is a free-fall problem happening at the same "
            "time. Solve them separately, then plot one against the other.",
            "Because sin 2\u03b8 peaks at \u03b8 = 45\u00b0, that angle gives maximum range on flat "
            "ground \u2014 and any two angles adding to 90\u00b0 land in exactly the same place.",
        ),
        scenarios=(
            Scenario("The 30\u00b0 / 60\u00b0 twins",
                     "Two shells fired at 30\u00b0 and 60\u00b0 with the same speed. Which travels further?",
                     "Neither \u2014 the ranges are identical, because sin 60\u00b0 = sin 120\u00b0. The "
                     "60\u00b0 shot just spends far longer in the air and climbs much higher.",
                     {"angle": 30.0, "v0": 25.0, "gravity": 9.8}),
            Scenario("Hunt for maximum range",
                     "Which launch angle sends it furthest across flat ground?",
                     "45\u00b0 exactly. Drag the angle slider either side of it and watch the "
                     "range readout fall away symmetrically.",
                     {"angle": 45.0, "v0": 25.0, "gravity": 9.8}),
            Scenario("Artillery on the Moon",
                     "Same cannon, lunar gravity. How much further does the shell fly?",
                     "About 6\u00d7 further, since range is inversely proportional to g. This is "
                     "the one case where the relationship really is linear.",
                     {"gravity": 1.6, "angle": 45.0, "v0": 25.0}),
        ),
        graph=Graph("x", "Distance (m)", (
            Series("y", "Height", "m", "left"),
        )),
        code=(
            "def step(self, dt):\n"
            "    self.t += dt\n"
            "    g, v0 = self.p['gravity'], self.p['v0']\n"
            "    th = math.radians(self.p['angle'])\n\n"
            "    self.x = v0 * math.cos(th) * self.t                       # constant vx\n"
            "    self.y = v0 * math.sin(th) * self.t - 0.5 * g * self.t**2  # free fall\n\n"
            "def range(self):\n"
            "    return self.p['v0']**2 * math.sin(2 * math.radians(self.p['angle'])) \\\n"
            "           / self.p['gravity']"
        ),
    ),

    Experiment(
        id="pendulum",
        title="Simple Pendulum",
        tagline="The equation everyone memorises is an approximation. Here you can measure how wrong it gets.",
        model_cls=PendulumModel,
        scene_key="pendulum",
        parameters=(
            Parameter("gravity", "Gravity", 9.8, 1.0, 25.0, 0.1, "m/s\u00b2"),
            Parameter("length", "String length", 1.5, 0.3, 4.5, 0.1, "m"),
            Parameter("angle", "Release angle", 30.0, 5.0, 75.0, 1.0, "\u00b0"),
        ),
        formulas=(
            r"\ddot{\theta} = -\frac{g}{L}\sin\theta",
            r"T_0 = 2\pi\sqrt{\frac{L}{g}}",
            r"T \approx T_0\left(1 + \frac{\theta_0^{2}}{16} + \frac{11\theta_0^{4}}{3072}\right)",
        ),
        theory=(
            "The true equation of motion contains sin \u03b8 and has no closed-form solution. "
            "The famous T = 2\u03c0\u221a(L/g) comes from assuming sin \u03b8 \u2248 \u03b8, which only holds "
            "for small swings.",
            "This simulation integrates the real equation, so the two period readouts "
            "disagree \u2014 by 0.4% at 15\u00b0, but more than 7% at 60\u00b0. Period depends on "
            "length and gravity only: mass never enters.",
        ),
        scenarios=(
            Scenario("Break the small-angle rule",
                     "Release from 70\u00b0 instead of 10\u00b0. How far off is the textbook period?",
                     "About 10% slow \u2014 the real pendulum takes noticeably longer than "
                     "2\u03c0\u221a(L/g) predicts. Compare 'T textbook' and 'T actual'.",
                     {"angle": 70.0, "length": 1.5, "gravity": 9.8}),
            Scenario("Four times the length",
                     "Going from 1 m to 4 m \u2014 does the period quadruple?",
                     "It doubles. Period grows with \u221aL, so four times the length gives "
                     "exactly twice the period.",
                     {"length": 4.0, "angle": 20.0, "gravity": 9.8}),
            Scenario("A clock on the Moon",
                     "A pendulum clock keeps perfect time on Earth. What happens on the Moon?",
                     "It runs about 2.5\u00d7 slow \u2014 \u221a(9.8/1.6). Your one-second pendulum now "
                     "takes almost two and a half seconds per swing.",
                     {"gravity": 1.6, "length": 1.0, "angle": 15.0}),
        ),
        graph=Graph("t", "Time (s)", (
            Series("theta_deg", "Angle", "\u00b0", "left"),
        )),
        code=(
            "# Semi-implicit (symplectic) Euler: velocity first, THEN position.\n"
            "# That order conserves energy; the naive order does not.\n"
            "def step(self, dt):\n"
            "    g, L = self.p['gravity'], self.p['length']\n"
            "    h = dt / self.SUBSTEPS\n\n"
            "    for _ in range(self.SUBSTEPS):\n"
            "        alpha = -(g / L) * math.sin(self.theta)  # exact, not sin x ~ x\n"
            "        self.omega += alpha * h\n"
            "        self.theta += self.omega * h\n"
            "    self.t += dt"
        ),
    ),

    Experiment(
        id="spring",
        title="Spring Oscillation",
        tagline="Hooke's law in one line, and the cleanest harmonic motion you will ever plot.",
        model_cls=SpringModel,
        scene_key="spring",
        parameters=(
            Parameter("mass", "Mass", 1.0, 0.1, 10.0, 0.1, "kg"),
            Parameter("stiffness", "Spring constant", 20.0, 5.0, 100.0, 1.0, "N/m"),
            Parameter("amplitude", "Amplitude", 0.30, 0.05, 0.60, 0.01, "m"),
        ),
        formulas=(
            r"F = -k\,x",
            r"x(t) = A\cos(\omega t) \qquad \omega = \sqrt{\frac{k}{m}}",
            r"T = 2\pi\sqrt{\frac{m}{k}} \qquad E = \frac{1}{2}k A^{2}",
        ),
        theory=(
            "Hooke's law says the restoring force is proportional to displacement and "
            "points the other way. That minus sign is what makes it oscillate instead of "
            "running away.",
            "The period depends on mass and stiffness but not on amplitude. Pull it twice "
            "as far and it still takes the same time to return. Energy sloshes between "
            "kinetic and potential while the total \u00bdkA\u00b2 stays fixed.",
        ),
        scenarios=(
            Scenario("Amplitude does nothing",
                     "Double the amplitude. Does each oscillation take longer?",
                     "Not at all \u2014 the period is unchanged. The mass travels twice as far "
                     "but moves twice as fast, and the two effects cancel exactly.",
                     {"amplitude": 0.60, "mass": 1.0, "stiffness": 20.0}),
            Scenario("Four times the mass",
                     "Load 4 kg instead of 1 kg on the same spring. How much slower?",
                     "Exactly twice as slow \u2014 T grows with \u221am. Watch the velocity trace "
                     "flatten out on the telemetry plot.",
                     {"mass": 4.0, "stiffness": 20.0, "amplitude": 0.30}),
            Scenario("A quarter cycle out of phase",
                     "Where is the mass fastest \u2014 at the ends of the swing, or the middle?",
                     "In the middle, at x = 0, where all the energy is kinetic. Displacement "
                     "and velocity sit a quarter cycle apart, which is why the two traces "
                     "cross at their peaks.",
                     {"mass": 1.0, "stiffness": 40.0, "amplitude": 0.40}),
        ),
        graph=Graph("t", "Time (s)", (
            Series("x", "Displacement", "m", "left"),
            Series("v", "Velocity", "m/s", "right"),
        )),
        code=(
            "def omega(self):\n"
            "    return math.sqrt(self.p['stiffness'] / self.p['mass'])\n\n"
            "def step(self, dt):\n"
            "    self.t += dt\n"
            "    w, a = self.omega(), self.p['amplitude']\n\n"
            "    self.x = a * math.cos(w * self.t)        # displacement\n"
            "    self.v = -a * w * math.sin(w * self.t)   # velocity = dx/dt"
        ),
    ),
)


def experiment_by_id(exp_id: str) -> Experiment:
    return next(e for e in EXPERIMENTS if e.id == exp_id)
