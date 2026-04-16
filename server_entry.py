"""Standalone-Einstiegspunkt: startet nur den FastAPI-Server (ohne Desktop-App).

Nutzung:
    python server_entry.py [--port 8765] [--host 0.0.0.0]

Ideal für: Headless-Server, Remote-Zugriff ohne GUI, Entwicklung.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Kollekten-API-Server")
    parser.add_argument("--port", type=int, default=None, help="Port (Standard: aus config.json oder 8765)")
    parser.add_argument("--host", default="0.0.0.0", help="Bind-Adresse (Standard: 0.0.0.0)")
    parser.add_argument("--reload", action="store_true", help="Automatisches Neuladen bei Dateiänderungen")
    args = parser.parse_args()

    from config import load_config
    cfg = load_config()
    port = args.port or cfg.get("api", {}).get("port", 8765)

    import uvicorn
    from app.api.server import app

    print(f"Kollekten-API-Server startet auf http://{args.host}:{port}")
    print(f"  Docs:      http://localhost:{port}/api/docs")
    print(f"  PWA:       http://localhost:{port}/")
    print("  Ctrl+C zum Beenden\n")

    uvicorn.run(
        app,
        host=args.host,
        port=port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
