"""GET /api/status  —  Letzter Lauf, Version, Gemeinde."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi import APIRouter

router = APIRouter()

ROOT = Path(__file__).parent.parent.parent.parent


def _load_cfg() -> dict:
    sys.path.insert(0, str(ROOT))
    from config import load_config
    return load_config()


def _last_run(cfg: dict) -> dict:
    """Liest den letzten Eintrag aus run_history.json."""
    try:
        path = Path(cfg["state"]["run_history_file"])
        if not path.exists():
            return {}
        with path.open(encoding="utf-8") as f:
            history = json.load(f)
        if not isinstance(history, list) or not history:
            return {}
        last = history[-1]
        return last
    except Exception:
        return {}


@router.get("/status")
def get_status() -> dict:
    try:
        cfg = _load_cfg()
        org = cfg.get("organization", {})
        gemeinde = (
            org.get("gemeinde_name")
            or "RV {}".format(org.get("rechtsträger_nr", ""))
        )
        last = _last_run(cfg)
        from app.updater import APP_VERSION
        return {
            "version": APP_VERSION,
            "gemeinde": gemeinde,
            "last_run": last.get("timestamp") or last.get("ts"),
            "last_run_processed": last.get("processed", 0),
            "last_run_errors": last.get("errors", 0),
            "is_running": _RunState.running,
        }
    except Exception as exc:
        return {"error": str(exc)}


class _RunState:
    """Einfacher globaler Flag — wird von actions.py gesetzt."""
    running: bool = False
