"""Windows Task Scheduler einrichten via schtasks (ohne Admin-Rechte)."""
import subprocess
import sys
from pathlib import Path

TASK_NAME = "Kollekten-Automation"
INTERVAL_MINUTES = 30


def get_python_path() -> str:
    """Gibt den Python-Interpreter im venv zurück."""
    venv = Path(__file__).parent / ".venv" / "Scripts" / "python.exe"
    if venv.exists():
        return str(venv)
    return sys.executable


def setup_task() -> None:
    script = Path(__file__).parent / "main.py"
    python = get_python_path()

    # Kommando das der Task ausführt
    command = f'"{python}" "{script}"'

    # Alten Task löschen falls vorhanden (Fehler ignorieren)
    subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        capture_output=True,
    )

    # Task anlegen: alle 30 Minuten, nur wenn Benutzer eingeloggt (/IT)
    # /SC MINUTE /MO 30  → alle 30 Minuten
    # /IT                → nur interaktiv (kein Admin nötig)
    # /RL LIMITED        → mit normalen Rechten ausführen
    result = subprocess.run(
        [
            "schtasks", "/Create",
            "/TN", TASK_NAME,
            "/TR", command,
            "/SC", "MINUTE",
            "/MO", str(INTERVAL_MINUTES),
            "/IT",
            "/RL", "LIMITED",
            "/F",
        ],
        capture_output=True,
        text=True,
        encoding="cp850",
    )

    if result.returncode == 0:
        print(f"Task '{TASK_NAME}' erfolgreich eingerichtet.")
        print(f"  Python:   {python}")
        print(f"  Skript:   {script}")
        print(f"  Interval: alle {INTERVAL_MINUTES} Minuten")
        print()
        print("Hinweis: Der Task startet automatisch alle 30 Min, solange Sie")
        print("eingeloggt sind. Zum manuellen Start: schtasks /Run /TN", TASK_NAME)
    else:
        err = result.stderr.strip() or result.stdout.strip()
        print(f"FEHLER beim Erstellen des Tasks:\n{err}")
        print()
        print("Tipp: Alternativ manuell starten mit:")
        print(f"  {command}")
        sys.exit(1)


def remove_task() -> None:
    result = subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        capture_output=True,
        text=True,
        encoding="cp850",
    )
    if result.returncode == 0:
        print(f"Task '{TASK_NAME}' entfernt.")
    else:
        print(f"Task nicht gefunden oder Fehler: {result.stderr.strip()}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Windows Task Scheduler für Kollekten-Automation")
    parser.add_argument("--remove", action="store_true", help="Task entfernen statt einrichten")
    args = parser.parse_args()

    if args.remove:
        remove_task()
    else:
        setup_task()
