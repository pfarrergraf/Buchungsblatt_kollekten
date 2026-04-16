"""POST /api/run  —  Verarbeitung starten (optional, wenn allow_run=true)."""
from __future__ import annotations

import logging
import sys
import threading
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.api.routes.live import _queue_handler, push_event
from app.api.routes.status import _RunState

router = APIRouter()
ROOT = Path(__file__).parent.parent.parent.parent

_lock = threading.Lock()


def _load_cfg() -> dict:
    sys.path.insert(0, str(ROOT))
    from config import load_config
    return load_config()


def _do_run(dry_run: bool) -> None:
    sys.path.insert(0, str(ROOT))
    root_logger = logging.getLogger()
    root_logger.addHandler(_queue_handler)
    _RunState.running = True
    try:
        import main as m
        processed, errors = m.run(dry_run=dry_run)
        push_event("finished", processed=processed, errors=errors)
    except Exception as exc:
        push_event("error", message=str(exc))
    finally:
        root_logger.removeHandler(_queue_handler)
        _RunState.running = False


@router.post("/run")
def start_run(background_tasks: BackgroundTasks, dry_run: bool = False) -> dict:
    cfg = _load_cfg()
    if not cfg.get("api", {}).get("allow_run", True):
        raise HTTPException(status_code=403, detail="Ausführung per API deaktiviert.")
    if _RunState.running:
        raise HTTPException(status_code=409, detail="Läuft bereits.")
    if not _lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Läuft bereits.")
    _lock.release()
    background_tasks.add_task(_do_run, dry_run)
    return {"started": True, "run_id": datetime.now().isoformat(), "dry_run": dry_run}
