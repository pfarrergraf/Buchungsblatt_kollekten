"""Windows Task Scheduler fuer mehrere deklarative Zeitplaene."""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from config import get_config

TASK_NAME_PREFIX = "Kollekten-Automation"


def get_python_path() -> str:
    venv = Path(__file__).parent / ".venv" / "Scripts" / "python.exe"
    return str(venv) if venv.exists() else sys.executable


def build_task_command(script: Path, python: str) -> str:
    return f'"{python}" "{script}" run'


def create_tasks(cfg: dict) -> None:
    script = Path(__file__).parent / "main.py"
    python = get_python_path()
    for schedule in cfg.get("schedules", []):
        if not schedule.get("enabled", True):
            continue
        mode = str(schedule.get("mode", "now"))
        name = str(schedule.get("name", "default"))
        if mode == "now":
            command = [python, str(script), "run"]
            result = subprocess.run(command)
            if result.returncode != 0:
                sys.exit(result.returncode)
            print(f"[now] Sofortlauf erfolgreich: {' '.join(command)}")
            continue
        command = build_task_command(script, python)
        task_name = f"{TASK_NAME_PREFIX}-{_slug(name)}"
        _delete_task(task_name)
        args = _schtasks_args(task_name, command, schedule)
        result = subprocess.run(args, capture_output=True, text=True, encoding="cp850")
        if result.returncode == 0:
            print(f"Task '{task_name}' erfolgreich eingerichtet.")
            print(f"  Modus: {mode}")
            print(f"  Kommando: {command}")
        else:
            err = result.stderr.strip() or result.stdout.strip()
            print(f"FEHLER beim Erstellen von '{task_name}': {err}")
            sys.exit(1)


def _schtasks_args(task_name: str, command: str, schedule: dict) -> list[str]:
    mode = str(schedule.get("mode", "now"))
    time = str(schedule.get("time", "07:30"))
    date = str(schedule.get("date", ""))
    if mode in {"once", "on_date"}:
        if not date:
            raise ValueError(f"Zeitplan '{task_name}' braucht ein Datum.")
        dt = datetime.fromisoformat(f"{date}T{time}:00")
        return [
            "schtasks", "/Create", "/TN", task_name, "/TR", command,
            "/SC", "ONCE",
            "/SD", dt.strftime("%d.%m.%Y"),
            "/ST", dt.strftime("%H:%M"),
            "/IT", "/RL", "LIMITED", "/F",
        ]
    if mode == "monthly_start":
        return _monthly_args(task_name, command, time, month_interval=1)
    if mode == "monthly_end":
        return _monthly_last_day_args(task_name, command, time, months="*")
    if mode == "quarterly_start":
        return _monthly_args(task_name, command, time, month_interval=3)
    if mode == "quarterly_end":
        return _monthly_last_day_args(task_name, command, time, months="MAR,JUN,SEP,DEC")
    raise ValueError(f"Unbekannter Zeitplanmodus: {mode}")


def _monthly_args(task_name: str, command: str, time: str, *, month_interval: int = 1) -> list[str]:
    return [
        "schtasks", "/Create", "/TN", task_name, "/TR", command,
        "/SC", "MONTHLY", "/MO", str(month_interval), "/D", "1",
        "/ST", time,
        "/IT", "/RL", "LIMITED", "/F",
    ]


def _monthly_last_day_args(task_name: str, command: str, time: str, *, months: str) -> list[str]:
    return [
        "schtasks", "/Create", "/TN", task_name, "/TR", command,
        "/SC", "MONTHLY", "/MO", "LASTDAY", "/M", months,
        "/ST", time,
        "/IT", "/RL", "LIMITED", "/F",
    ]


def _delete_task(task_name: str) -> None:
    subprocess.run(["schtasks", "/Delete", "/TN", task_name, "/F"], capture_output=True)


def remove_task(name: str) -> None:
    task_name = f"{TASK_NAME_PREFIX}-{_slug(name)}"
    result = subprocess.run(["schtasks", "/Delete", "/TN", task_name, "/F"], capture_output=True, text=True, encoding="cp850")
    if result.returncode == 0:
        print(f"Task '{task_name}' entfernt.")
    else:
        print(f"Task nicht gefunden oder Fehler: {result.stderr.strip()}")


def _slug(value: str) -> str:
    slug = []
    for ch in value.lower():
        if ch.isalnum():
            slug.append(ch)
        elif slug and slug[-1] != "-":
            slug.append("-")
    return "".join(slug).strip("-") or "default"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Windows Task Scheduler fuer Kollekten-Automation")
    parser.add_argument("--remove", action="store_true", help="Task entfernen statt einrichten")
    parser.add_argument("--name", default="default", help="Name des Zeitplans")
    args = parser.parse_args(argv)
    if args.remove:
        remove_task(args.name)
        return
    cfg = get_config()
    create_tasks(cfg)


if __name__ == "__main__":
    main()
