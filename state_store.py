"""Persistenter Lauf-State für verarbeitete E-Mails und Historie."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_id_set(path: str | Path) -> set[str]:
    p = Path(path)
    if not p.exists():
        return set()
    with p.open(encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return {str(item) for item in data}
    if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
        return {str(item) for item in data["items"]}
    return set()


def save_id_set(path: str | Path, ids: set[str]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(sorted(ids), f, indent=2, ensure_ascii=False)


def remove_ids(path: str | Path, ids_to_remove: set[str]) -> None:
    if not ids_to_remove:
        return
    current = load_id_set(path)
    current -= ids_to_remove
    save_id_set(path, current)


def append_history(path: str | Path, event: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload: list[dict[str, Any]] = []
    if p.exists():
        with p.open(encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, list):
            payload = raw
    payload.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **event,
        }
    )
    with p.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
