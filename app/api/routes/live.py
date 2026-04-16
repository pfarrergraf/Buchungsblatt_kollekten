"""GET /api/run/live  —  Server-Sent Events für Lauf-Fortschritt."""
from __future__ import annotations

import asyncio
import logging
import queue
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()

# Globale Queue: main.run() schreibt rein, SSE-Client liest raus
_event_queue: queue.Queue = queue.Queue(maxsize=200)


def push_event(type_: str, message: str = "", **kwargs) -> None:
    """Von actions.py und dem Logging-Handler aufgerufen."""
    import json
    payload = {"type": type_, "message": message, **kwargs}
    try:
        _event_queue.put_nowait(json.dumps(payload))
    except queue.Full:
        pass


class _QueueHandler(logging.Handler):
    """Leitet Log-Nachrichten als SSE-Events in die Queue."""
    def emit(self, record: logging.LogRecord) -> None:
        push_event("progress", self.format(record))


_queue_handler = _QueueHandler()
_queue_handler.setFormatter(logging.Formatter("%(message)s"))


async def _generate(timeout: float = 120.0) -> AsyncGenerator[str, None]:
    import json
    yield "data: {}\n\n"  # keep-alive
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        try:
            msg = _event_queue.get_nowait()
            yield f"data: {msg}\n\n"
            data = json.loads(msg)
            if data.get("type") in ("finished", "error"):
                return
        except queue.Empty:
            await asyncio.sleep(0.2)
            yield ": keep-alive\n\n"


@router.get("/run/live")
def live_events() -> StreamingResponse:
    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
