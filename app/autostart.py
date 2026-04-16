"""Windows-Autostart via Registry (HKCU, kein Admin nötig)."""
from __future__ import annotations

import sys
from pathlib import Path

APP_NAME = "KollektenAutomation"
REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _get_exe_path() -> str:
    """Gibt den Pfad zur aktuell laufenden .exe oder python.exe zurück."""
    if getattr(sys, "frozen", False):
        # PyInstaller-Bundle
        return sys.executable
    # Entwicklungsmodus: starte app_entry.py über Python
    python = Path(sys.executable)
    entry = Path(__file__).parent.parent / "app_entry.py"
    return f'"{python}" "{entry}"'


def set_autostart(enabled: bool, exe_path: str | None = None) -> None:
    """Setzt oder entfernt den Autostart-Eintrag in der Registry."""
    if sys.platform != "win32":
        return
    import winreg
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REG_KEY,
            0, winreg.KEY_SET_VALUE
        )
        if enabled:
            path = exe_path or _get_exe_path()
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, path)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception:
        pass


def is_autostart_enabled() -> bool:
    """Prüft ob der Autostart-Eintrag gesetzt ist."""
    if sys.platform != "win32":
        return False
    import winreg
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REG_KEY,
            0, winreg.KEY_READ
        )
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False
