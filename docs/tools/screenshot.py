"""Offscreen screenshot harness (development only, not part of the app)."""
import pathlib
import sys, time
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from app.ui.window import MainWindow

app = QApplication(sys.argv)
w = MainWindow(); w.resize(1440, 900); w.show()

def pump(seconds):
    """Let real time pass — Qt animations and QTimers are wall-clock driven."""
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.004)

def grab(name):
    pump(0.25); w.grab().save(name); print("saved", name)

def sequence():
    pump(1.6)                              # landing entrance finishes
    grab("shots/01_landing.png")

    w.open_experiment("pendulum"); w.dashboard.canvas.play()
    pump(1.4); grab("shots/02_pendulum.png")

    w.open_experiment("projectile"); w.dashboard.canvas.play()
    pump(1.8); grab("shots/03_projectile.png")

    w.open_experiment("spring"); w.dashboard.canvas.play()
    pump(1.6); grab("shots/04_spring.png")

    w.open_experiment("free_fall"); w.dashboard.canvas.play()
    pump(1.6); w.toggle_theme(); pump(0.5)
    grab("shots/05_freefall_light.png")
    app.quit()

QTimer.singleShot(60, sequence)
sys.exit(app.exec())
