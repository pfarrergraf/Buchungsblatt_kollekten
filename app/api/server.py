"""FastAPI-Server für die Kollekten-Automation PWA."""
from __future__ import annotations

import logging
import sys
import threading
from pathlib import Path
from typing import Optional

log = logging.getLogger("api.server")

ROOT = Path(__file__).parent.parent.parent
STATIC_DIR = Path(__file__).parent / "static"


def _load_cfg() -> dict:
    sys.path.insert(0, str(ROOT))
    from config import load_config
    return load_config()


def _make_app():
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles

    from app.api.routes import actions, kollekten, live, status

    cfg = _load_cfg()
    api_cfg = cfg.get("api", {})
    token = str(api_cfg.get("token") or "").strip()

    app = FastAPI(
        title="Kollekten-Automation API",
        version="1.0",
        docs_url="/api/docs",
        redoc_url=None,
    )

    # CORS — erlaubt alle Origins (nur im LAN genutzt)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_cfg.get("cors_origins", ["*"]),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Optionaler Bearer-Token
    if token:
        @app.middleware("http")
        async def auth_middleware(request: Request, call_next):
            if request.url.path.startswith("/api/"):
                auth = request.headers.get("Authorization", "")
                if auth != f"Bearer {token}":
                    return JSONResponse({"error": "Nicht autorisiert"}, status_code=401)
            return await call_next(request)

    # API-Routen
    app.include_router(status.router, prefix="/api")
    app.include_router(kollekten.router, prefix="/api")
    app.include_router(actions.router, prefix="/api")
    app.include_router(live.router, prefix="/api")

    # Statische PWA-Dateien
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

        @app.get("/")
        def root():
            return FileResponse(str(STATIC_DIR / "index.html"))

        @app.get("/{path:path}")
        def spa_fallback(path: str):
            """Alle unbekannten Pfade → index.html (SPA-Routing)."""
            file = STATIC_DIR / path
            if file.exists() and file.is_file():
                return FileResponse(str(file))
            return FileResponse(str(STATIC_DIR / "index.html"))

    return app


# Singleton-App (wird beim Import einmal erstellt)
app = _make_app()


# ── Server-Thread ─────────────────────────────────────────────────────────────

class ApiServer:
    """
    Startet uvicorn in einem Daemon-Thread.
    Kann aus der Desktop-App heraus gestartet/gestoppt werden.
    """

    def __init__(self, port: int = 8765):
        self._port = port
        self._thread: Optional[threading.Thread] = None
        self._server = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="api-server"
        )
        self._thread.start()
        log.info("API-Server gestartet auf Port %d", self._port)

    def stop(self) -> None:
        if self._server:
            self._server.should_exit = True

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def _run(self) -> None:
        try:
            import uvicorn
            config = uvicorn.Config(
                app,
                host="0.0.0.0",
                port=self._port,
                log_level="warning",
                access_log=False,
            )
            self._server = uvicorn.Server(config)
            self._server.run()
        except Exception as exc:
            log.error("API-Server Fehler: %s", exc)
