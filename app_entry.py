"""Einstiegspunkt der Kollekten-Automation App."""
from __future__ import annotations

import sys
from pathlib import Path

# Projektverzeichnis im Pfad
sys.path.insert(0, str(Path(__file__).parent))


def _needs_setup() -> bool:
    """True wenn Ersteinrichtung nötig (config fehlt oder unvollständig)."""
    try:
        from config import get_config
        cfg = get_config()
        org = cfg.get("organization", {})
        tpl = cfg.get("templates", {})
        required = [
            org.get("rechtsträger_nr", ""),
            tpl.get("eigene_gemeinde", ""),
            tpl.get("zur_weiterleitung", ""),
        ]
        return not all(required)
    except Exception:
        return True


def main():
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFont
    from app.main_window import MainWindow, load_theme
    from app.updater import APP_VERSION

    app = QApplication(sys.argv)
    app.setApplicationName("Kollekten-Automation")
    app.setApplicationVersion(APP_VERSION)
    load_theme(app)

    # Schriftgröße aus Config
    try:
        from config import get_config
        cfg = get_config()
        font_size = cfg.get("app", {}).get("font_size", 9)
        font = QFont("Segoe UI", font_size)
        app.setFont(font)
        use_tray = cfg.get("app", {}).get("use_tray", False)
    except Exception:
        use_tray = False

    # Ersteinrichtung falls nötig
    if _needs_setup():
        from app.setup_wizard import SetupWizard
        from PySide6.QtWidgets import QWizard
        wizard = SetupWizard()
        if wizard.exec() != QWizard.DialogCode.Accepted:
            sys.exit(0)

    # Hauptfenster
    window = MainWindow()
    window.show()

    # Tray (opt-in)
    tray = None
    if use_tray:
        try:
            from app.tray import TrayIcon
            tray = TrayIcon(
                on_open=lambda: (window.show(), window.raise_(), window.activateWindow()),
                on_run=lambda: window.tab_uebersicht.run_requested.emit(False),
                on_quit=app.quit,
            )
            tray.start()
        except Exception:
            pass  # Tray nicht verfügbar — kein Problem

    exit_code = app.exec()
    if tray:
        tray.stop()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
