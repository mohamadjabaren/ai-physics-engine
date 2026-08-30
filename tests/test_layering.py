"""
Guard the architecture, not just the behaviour.

app/core/ is the pure physics layer. If someone (including future-you at 2am)
imports a Qt widget in there, this test fails and says so. An architecture
diagram in a README rots; an assertion does not.
"""
import pathlib
import re

CORE = pathlib.Path(__file__).resolve().parent.parent / "app" / "core"
BANNED = re.compile(r"^\s*(from|import)\s+(PySide6|PyQt|pyqtgraph|matplotlib|app\.(ui|render))", re.M)


def test_core_never_imports_the_gui():
    offenders = []
    for path in CORE.rglob("*.py"):
        for match in BANNED.finditer(path.read_text(encoding="utf-8")):
            offenders.append(f"{path.name}: {match.group(0).strip()}")
    assert not offenders, "app/core must stay GUI-free:\n" + "\n".join(offenders)


def test_core_runs_without_a_display():
    """Importing the physics must not require a window system."""
    import subprocess, sys, os
    env = dict(os.environ)
    env.pop("DISPLAY", None)
    result = subprocess.run(
        [sys.executable, "-c",
         "import sys; from app.core.catalog import EXPERIMENTS; "
         "assert 'PySide6' not in sys.modules; print(len(EXPERIMENTS))"],
        capture_output=True, text=True, env=env,
        cwd=str(pathlib.Path(__file__).resolve().parent.parent))
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "4"
