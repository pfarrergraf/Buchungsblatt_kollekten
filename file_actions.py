"""Datei- und Explorer-Aktionen fuer die Desktop-App."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


def existing_paths(paths: list[str]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for value in paths:
        if not value:
            continue
        path = Path(value)
        key = str(path).lower()
        if key in seen or not path.exists():
            continue
        seen.add(key)
        result.append(path)
    return result


def open_file(path_str: str) -> bool:
    path = Path(path_str)
    if not path.exists():
        return False
    os.startfile(str(path))
    return True


def open_folder(path_str: str) -> bool:
    path = Path(path_str)
    folder = path if path.is_dir() else path.parent
    if not folder.exists():
        return False
    subprocess.Popen(["explorer", str(folder)])
    return True


def reveal_in_explorer(path_str: str) -> bool:
    path = Path(path_str)
    if not path.exists():
        return False
    subprocess.Popen(["explorer", "/select,", str(path)])
    return True
