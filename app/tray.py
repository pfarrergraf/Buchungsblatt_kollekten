"""System-Tray-Icon via pystray (opt-in, Daemon-Thread)."""
from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import Callable, Optional


def _load_image():
    """Lädt das App-Icon als PIL-Image."""
    from PIL import Image
    icon_path = Path(__file__).parent.parent / "assets" / "app.png"
    if icon_path.exists():
        return Image.open(str(icon_path))
    # Fallback: einfaches blaues Quadrat
    img = Image.new("RGB", (64, 64), "#2B579A")
    return img


class TrayIcon:
    """
    Kapselt das pystray.Icon und stellt Thread-sichere Callbacks bereit.

    Nutzung:
        tray = TrayIcon(
            on_open=lambda: window.show(),
            on_run=lambda: worker.start(),
            on_quit=app.quit,
        )
        tray.start()   # startet in eigenem Daemon-Thread
        tray.stop()    # sauber beenden
    """

    def __init__(
        self,
        on_open: Callable,
        on_run: Callable,
        on_quit: Callable,
    ):
        self._on_open = on_open
        self._on_run = on_run
        self._on_quit = on_quit
        self._icon = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Startet das Tray-Icon in einem Daemon-Thread."""
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_tray, daemon=True, name="tray-thread")
        self._thread.start()

    def stop(self):
        if self._icon:
            self._icon.stop()

    def show_notification(self, title: str, message: str):
        """Zeigt eine Balloon-Benachrichtigung (Windows Toast)."""
        if self._icon:
            try:
                self._icon.notify(message, title)
            except Exception:
                pass

    def _run_tray(self):
        try:
            import pystray
        except ImportError:
            return

        def on_open(icon, item):
            self._qt_invoke(self._on_open)

        def on_run(icon, item):
            self._qt_invoke(self._on_run)

        def on_quit(icon, item):
            icon.stop()
            self._qt_invoke(self._on_quit)

        menu = pystray.Menu(
            pystray.MenuItem("Dashboard öffnen", on_open, default=True),
            pystray.MenuItem("Jetzt ausführen", on_run),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Beenden", on_quit),
        )

        self._icon = pystray.Icon(
            name="KollektenAutomation",
            icon=_load_image(),
            title="Kollekten-Automation",
            menu=menu,
        )
        self._icon.run()

    @staticmethod
    def _qt_invoke(fn: Callable):
        """Ruft eine Qt-Funktion thread-sicher auf."""
        try:
            from PySide6.QtCore import QMetaObject, Qt
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                # Sicherster Weg: Lambda in Qt-Hauptthread einreihen
                from PySide6.QtCore import QTimer
                QTimer.singleShot(0, fn)
            else:
                fn()
        except Exception:
            fn()
