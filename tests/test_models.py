"""
Physics tests. These import app.core only — no Qt, no display, no window.
That is the payoff of the layering: the maths is testable in isolation.

Run with:  python -m pytest tests -v
"""
import math

from app.core.model import FreeFallModel, PendulumModel, ProjectileModel, SpringModel


def run(model, seconds, dt=1 / 120):
    model.reset()
    steps = int(seconds / dt)
    for _ in range(steps):
        model.step(dt)
        if model.finished:
            break
    return model


# ── Free fall ────────────────────────────────────────────────────────────────
def test_free_fall_matches_closed_form():
    m = run(FreeFallModel({"gravity": 9.8, "height": 80.0}), 10)
    assert math.isclose(m.t, math.sqrt(2 * 80 / 9.8), rel_tol=1e-9)
    assert math.isclose(m.v, math.sqrt(2 * 9.8 * 80), rel_tol=1e-9)


def test_free_fall_is_independent_of_mass():
    """There is no mass parameter at all — the API itself encodes the physics."""
    assert "mass" not in FreeFallModel({"gravity": 9.8, "height": 80.0}).p


# ── Projectile ───────────────────────────────────────────────────────────────
def test_projectile_range_and_flight_time():
    m = run(ProjectileModel({"gravity": 9.8, "v0": 25.0, "angle": 45.0}), 10)
    assert math.isclose(m.x, 25 ** 2 / 9.8, rel_tol=1e-9)
    assert math.isclose(m.t, 2 * 25 * math.sin(math.pi / 4) / 9.8, rel_tol=1e-9)


def test_complementary_angles_share_a_range():
    a = ProjectileModel({"gravity": 9.8, "v0": 25.0, "angle": 30.0})
    b = ProjectileModel({"gravity": 9.8, "v0": 25.0, "angle": 60.0})
    assert math.isclose(a.range(), b.range(), rel_tol=1e-12)


# ── Pendulum ─────────────────────────────────────────────────────────────────
def measured_period(model, dt=1 / 480):
    """Time a full cycle by watching for sign changes of theta."""
    model.reset()
    prev, crossings, t = model.theta, [], 0.0
    while t < 40 and len(crossings) < 3:
        model.step(dt)
        t += dt
        if (prev > 0) != (model.theta > 0):
            crossings.append(t)
        prev = model.theta
    return crossings[2] - crossings[0]


def test_integrated_period_matches_series_expansion():
    """The headline claim of the app: the integrator agrees with the exact
    period formula across the whole angle range, not just small angles."""
    for deg in (5, 15, 30, 60, 75):
        m = PendulumModel({"gravity": 9.8, "length": 1.5, "angle": float(deg)})
        assert math.isclose(measured_period(m), m.period_true(), rel_tol=0.01), deg


def test_small_angle_error_grows_with_amplitude():
    errs = []
    for deg in (5, 15, 30, 60, 75):
        m = PendulumModel({"gravity": 9.8, "length": 1.5, "angle": float(deg)})
        errs.append(m.period_true() / m.period_small_angle() - 1)
    assert errs == sorted(errs)
    assert errs[0] < 0.001          # 5 deg: the approximation is excellent
    assert errs[-1] > 0.10          # 75 deg: it is badly wrong


def test_symplectic_integrator_conserves_energy():
    """Naive Euler would let this drift upwards without bound."""
    m = PendulumModel({"gravity": 9.8, "length": 1.5, "angle": 45.0})
    m.reset()
    g, L = 9.8, 1.5
    e0 = g * L * (1 - math.cos(math.radians(45)))
    worst = 0.0
    for _ in range(int(60 * 120)):
        m.step(1 / 120)
        e = 0.5 * (L * m.omega) ** 2 + g * L * (1 - math.cos(m.theta))
        worst = max(worst, abs(e - e0) / e0)
    assert worst < 0.01, f"energy drifted {worst:.3%} over 60 s"


def test_period_ignores_amplitude_only_in_the_limit():
    long_p = PendulumModel({"gravity": 9.8, "length": 4.0, "angle": 20.0})
    short_p = PendulumModel({"gravity": 9.8, "length": 1.0, "angle": 20.0})
    assert math.isclose(long_p.period_small_angle() / short_p.period_small_angle(), 2.0, rel_tol=1e-12)


# ── Spring ───────────────────────────────────────────────────────────────────
def test_spring_period_and_mass_scaling():
    light = SpringModel({"mass": 1.0, "stiffness": 20.0, "amplitude": 0.3})
    heavy = SpringModel({"mass": 4.0, "stiffness": 20.0, "amplitude": 0.3})
    assert math.isclose(light.period(), 2 * math.pi * math.sqrt(1 / 20), rel_tol=1e-12)
    assert math.isclose(heavy.period() / light.period(), 2.0, rel_tol=1e-12)


def test_spring_period_ignores_amplitude():
    small = SpringModel({"mass": 1.0, "stiffness": 20.0, "amplitude": 0.1})
    big = SpringModel({"mass": 1.0, "stiffness": 20.0, "amplitude": 0.6})
    assert math.isclose(small.period(), big.period(), rel_tol=1e-12)


def test_spring_conserves_total_energy():
    m = run(SpringModel({"mass": 1.0, "stiffness": 20.0, "amplitude": 0.3}), 3)
    total = 0.5 * 1.0 * m.v ** 2 + 0.5 * 20.0 * m.x ** 2
    assert math.isclose(total, m.total_energy(), rel_tol=1e-9)


def test_kinetic_fraction_stays_in_range():
    m = SpringModel({"mass": 2.0, "stiffness": 35.0, "amplitude": 0.25})
    m.reset()
    for _ in range(2000):
        m.step(1 / 120)
        assert 0.0 <= m.kinetic_fraction() <= 1.0
