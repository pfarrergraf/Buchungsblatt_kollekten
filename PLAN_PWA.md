# Plan: Kollekten-App — Android-fähige PWA (Companion-App)

> **Prinzip: Additiv — kein bestehender Code wird verändert, nur ergänzt.**
> Verweist auf Hauptplan: `C:\Users\Mein Computer\.claude\plans\rosy-frolicking-dream.md`
> Verweist auf App-Checkliste: `c:\ai\Buchungsblatt_kollekten\CHECKLIST.md`
> Stand: 2026-04-15

---

## Ziel

Eine **Progressive Web App (PWA)**, die auf Android-Smartphones im Browser läuft
und sich per WLAN mit dem Windows-PC verbindet. Der PC bleibt die einzige Instanz,
die Outlook und Excel verarbeitet. Die App ist ein **Companion-Viewer + Remote-Control**.

**Nicht-Ziele (bewusst ausgeschlossen):**
- Keine Offline-Verarbeitung auf dem Handy
- Kein App Store, kein APK-Build
- Kein Cloud-Server, keine Telemetrie
- Kein Umbau der bestehenden Desktop-App

---

## Architektur

```
Windows-PC
├── Desktop-App (PySide6)  ← unverändert
└── FastAPI-Server :8765   ← NEU, optionaler Hintergrund-Thread
    ├── REST-API  /api/*
    └── Static    /        → HTML + JS + Icons

Android (Chrome / Samsung Internet)
└── http://192.168.x.x:8765  ←  PWA im Browser
    → "Zum Startbildschirm hinzufügen"
    → Sieht aus wie eine echte App
```

### Kommunikation

```
Android                    PC (FastAPI)               Bestandscode
  GET /api/status    →   liest run_history.json    ←  append_history()
  GET /api/kollekten →   liest overview.xlsx        ←  openpyxl
  POST /api/run      →   ruft main.run() auf        ←  main.py::run()
  GET /api/run/live  →   SSE-Stream (Fortschritt)   ←  logging-Handler
```

---

## Neue Dateien (Vollständige Liste)

```
app/api/
├── __init__.py
├── server.py              ← FastAPI-App + uvicorn-Thread
├── routes/
│   ├── __init__.py
│   ├── status.py          ← GET /api/status, /api/version
│   ├── kollekten.py       ← GET /api/kollekten, /api/kollekten/summary
│   ├── actions.py         ← POST /api/run, POST /api/run/dry
│   └── live.py            ← GET /api/run/live  (SSE)
└── static/
    ├── index.html         ← Haupt-UI (eine Datei, kein Build-Tool)
    ├── app.js             ← Vanilla JS (~300 Zeilen)
    ├── style.css          ← Mobile-first CSS
    ├── manifest.json      ← PWA-Manifest
    ├── sw.js              ← Service Worker (Cache + Offline-Seite)
    └── icons/
        ├── icon-192.png   ← aus assets/app.png skaliert
        └── icon-512.png

server_entry.py            ← NEU: Standalone-Starter (ohne Desktop-App)
```

### Änderungen an bestehenden Dateien (minimal, sicher)

| Datei | Änderung | Risiko |
|---|---|---|
| `config.py` | `DEFAULT_CONFIG` um `"api": {...}` erweitern | Null — rein additiv |
| `app/main_window.py` | EinstellungenTab: Checkbox "API-Server starten" + Port | Minimal |
| `requirements.txt` | `fastapi`, `uvicorn[standard]` hinzufügen | Null |

---

## Konfiguration (neu in config.json)

```json
"api": {
  "enabled": false,
  "port": 8765,
  "token": "",
  "allow_run": true,
  "cors_origins": ["*"]
}
```

- `enabled`: false = Server startet nicht (sicher by default)
- `token`: leer = kein Auth; gesetzt = Bearer-Token erforderlich
- `allow_run`: false = nur Lesezugriff (kein "Jetzt ausführen" vom Handy)

---

## API-Endpunkte (Spezifikation)

### GET /api/status
```json
{
  "version": "1.1.0",
  "gemeinde": "Ev. KG Oberlahnstein",
  "last_run": "2026-04-15T07:21:00",
  "last_run_processed": 13,
  "last_run_errors": 0,
  "is_running": false
}
```

### GET /api/kollekten?month=4&year=2026&only_warnings=false
```json
{
  "entries": [
    {
      "datum": "15.04.2026",
      "betrag": 99.70,
      "zweck": "Stiftung für das Leben",
      "typ": "zur_weiterleitung",
      "aobj": "3611",
      "needs_review": false
    }
  ],
  "count": 13
}
```

### GET /api/kollekten/summary?month=4&year=2026
```json
{
  "summe_eigene": 312.50,
  "summe_weiterleitung": 445.20,
  "summe_gesamt": 757.70,
  "count": 13
}
```

### POST /api/run  (nur wenn allow_run=true)
```json
// Request: {}  oder  {"dry_run": true}
// Response (sofort, Verarbeitung läuft im Hintergrund):
{
  "started": true,
  "run_id": "2026-04-15T08:00:00"
}
```

### GET /api/run/live  (Server-Sent Events)
```
data: {"type": "progress", "message": "Verarbeite E-Mail: Gottesdienst 15.04.26"}
data: {"type": "finished", "processed": 2, "errors": 0}
data: {"type": "error", "message": "Outlook nicht erreichbar"}
```

---

## PWA-Frontend (Screens)

### Screen 1: Dashboard
```
┌─────────────────────────────────┐
│  💶 Kollekten          [≡]      │
├─────────────────────────────────┤
│  Ev. KG Oberlahnstein           │
│                                 │
│  ┌──────────┐  ┌──────────┐    │
│  │ Letzter  │  │ Verarbei-│    │
│  │ Lauf     │  │ tet      │    │
│  │ 15.04.26 │  │ 13       │    │
│  └──────────┘  └──────────┘    │
│                                 │
│  ┌──────────┐  ┌──────────┐    │
│  │Eigene    │  │Weiter-   │    │
│  │312,50 €  │  │445,20 €  │    │
│  └──────────┘  └──────────┘    │
│                                 │
│  [▶ Jetzt ausführen]           │
│  [👁 Vorschau]                 │
└─────────────────────────────────┘
```

### Screen 2: Kollekten-Liste
```
┌─────────────────────────────────┐
│  ← Verlauf   Apr 2026  [Filter] │
├─────────────────────────────────┤
│  15.04  99,70 €   →             │
│  Stiftung für das Leben         │
├─────────────────────────────────┤
│  08.04  45,00 €   ✓             │
│  Kinder- und Jugendarbeit       │
├─────────────────────────────────┤
│  ⚠ 01.04  ??,?? €              │
│  Unbekannter Zweck              │
└─────────────────────────────────┘
```

### Screen 3: Live-Log (beim Ausführen)
```
┌─────────────────────────────────┐
│  ← Ausführung läuft…   ⏳       │
├─────────────────────────────────┤
│  ✓ Verarbeite E-Mail 1/3       │
│  ✓ Stiftung f.d. Leben 99,70   │
│  ✓ Kinder u. Jugend 45,00      │
│  ⏳ Suche weitere E-Mails…      │
│                                 │
│  ████████░░░░  67%             │
└─────────────────────────────────┘
```

### Offline-Screen
```
┌─────────────────────────────────┐
│          📡                     │
│  PC nicht erreichbar            │
│                                 │
│  Letzter bekannter Stand:       │
│  15.04.2026 — 13 Kollekten     │
│                                 │
│  [Erneut versuchen]            │
└─────────────────────────────────┘
```

---

## Implementierungsphasen

### Phase A: FastAPI-Backend (unabhängig von UI)
**Dateien:** `app/api/server.py`, `app/api/routes/*.py`
**Abhängigkeiten:** `fastapi`, `uvicorn`, bestehende `config.py`, `overview.py`
**Verifikation:** `curl http://localhost:8765/api/status` gibt JSON zurück
**Delegierbar an:** Claude Code, GPT-4.1, Copilot

Aufgaben:
1. `app/api/server.py` — FastAPI-App erstellen, CORS konfigurieren, Auth-Middleware
2. `app/api/routes/status.py` — liest `run_history.json` + `config.json`
3. `app/api/routes/kollekten.py` — liest `kollekten_uebersicht.xlsx` via openpyxl
4. `app/api/routes/actions.py` — startet `main.run()` in Thread, Lock gegen Doppelstart
5. `app/api/routes/live.py` — SSE-Endpoint, logging-Handler leitet in Event-Queue um
6. `server_entry.py` — standalone `uvicorn app.api.server:app --port 8765`

### Phase B: Config-Integration (minimal, sicher)
**Dateien:** `config.py` (nur DEFAULT_CONFIG erweitern), `app/main_window.py` (EinstellungenTab)
**Verifikation:** Checkbox in Einstellungen startet/stoppt Server
**Delegierbar an:** Claude Code

Aufgaben:
1. `config.py` — `"api": {"enabled": false, "port": 8765, "token": "", "allow_run": true}` zu `DEFAULT_CONFIG` hinzufügen
2. `app/main_window.py` EinstellungenTab "Ausführung": Checkbox + Port-SpinBox
3. `MainWindow._load_config()`: wenn `cfg["api"]["enabled"]`, API-Thread starten

### Phase C: PWA-Frontend (unabhängig vom Backend)
**Dateien:** `app/api/static/`
**Verifikation:** Öffne `http://localhost:8765` in Chrome Android → "Zum Startbildschirm"
**Delegierbar an:** GPT-4.1, Copilot (UI-Boilerplate)

Aufgaben:
1. `manifest.json` — App-Name, Icons, `display: standalone`, `theme_color: #2B579A`
2. `sw.js` — Cache-First für static assets, Network-First für `/api/*`, Offline-Fallback
3. `index.html` — Shell: Header, Bottom-Nav (Dashboard / Verlauf / ⚙), `<div id="app">`
4. `style.css` — Mobile-first, CSS-Variablen (`--accent: #2B579A`), Dark-Mode via `prefers-color-scheme`
5. `app.js` — Router (Hash-basiert), API-Client (fetch + error handling), Screens rendern

### Phase D: Icons generieren
**Dateien:** `app/api/static/icons/`
**Aufgabe:** `assets/app.png` via Pillow auf 192×192 und 512×512 skalieren
**Delegierbar an:** jeder Agent

### Phase E: Packaging (PyInstaller-Update)
**Dateien:** `kollekten_app.spec`
**Aufgabe:** `app/api/static/` zu `datas` hinzufügen, `fastapi`, `uvicorn` zu `hiddenimports`
**Verifikation:** `.exe` startet Server korrekt

---

## Sicherheitskonzept

| Szenario | Verhalten |
|---|---|
| Token leer | Kein Auth — nur im Heimnetz nutzen |
| Token gesetzt | Alle `/api/*` Requests brauchen `Authorization: Bearer <token>` |
| `allow_run: false` | POST /api/run gibt 403 zurück |
| Außerhalb WLAN | Server nicht erreichbar (kein Port-Forwarding nötig/empfohlen) |
| HTTPS | Optional: selbstsigniertes Zertifikat via `ssl_certfile` in uvicorn |

---

## Neue Abhängigkeiten

| Paket | Zweck | Installation |
|---|---|---|
| `fastapi` | REST-API Framework | `uv pip install fastapi` |
| `uvicorn[standard]` | ASGI-Server | `uv pip install uvicorn[standard]` |

Keine weiteren Abhängigkeiten. Kein Node.js, kein npm, kein Build-Tool.

---

## Konventionen für alle Agenten

**Bestehender Code darf NICHT verändert werden außer:**
1. `config.py` — nur `DEFAULT_CONFIG` um `"api":{...}` erweitern (kein bestehender Key angefasst)
2. `app/main_window.py` — nur in `EinstellungenTab._build_ausfuehrung()` und `MainWindow._load_config()` (je max. 10 neue Zeilen)

**FastAPI-Konventionen:**
- Alle Routes in `app/api/routes/*.py`, nie direkt in `server.py`
- Fehler immer als `{"error": "..."}` mit passendem HTTP-Status
- Keine sync-Funktionen die blockieren (→ `asyncio.to_thread` oder `BackgroundTasks`)
- Logging via `logging.getLogger("api.*")` — selber Logger wie Hauptapp

**Frontend-Konventionen:**
- Kein Framework (kein React, kein Vue) — Vanilla JS
- Kein Build-Tool — eine `index.html`, eine `app.js`, eine `style.css`
- API-Base-URL aus `window.location.origin` (funktioniert automatisch auf jedem Gerät)
- Farben aus CSS-Variablen, nie hardcoded

---

## Verifikations-Checkliste (manuell)

```
Phase A:
[ ] curl http://localhost:8765/api/status  → JSON
[ ] curl http://localhost:8765/api/kollekten?year=2026  → JSON mit Einträgen
[ ] curl -X POST http://localhost:8765/api/run  → {"started": true}
[ ] curl http://localhost:8765/api/run/live  → SSE-Events erscheinen

Phase B:
[ ] Checkbox in Einstellungen → Server startet/stoppt
[ ] config.json enthält "api"-Sektion nach Speichern

Phase C:
[ ] http://localhost:8765 öffnet Web-App im Browser
[ ] Chrome Android → Drei-Punkte-Menü → "Zum Startbildschirm" erscheint
[ ] App-Icon erscheint auf Home-Screen
[ ] Dashboard zeigt Gemeindename + Letzter Lauf + Summen
[ ] Verlauf-Tab zeigt Tabelle mit Einträgen
[ ] "Jetzt ausführen" → Fortschritts-Screen mit SSE-Updates
[ ] WiFi abschalten → Offline-Screen erscheint (cached)

Phase E:
[ ] pyinstaller kollekten_app.spec → .exe startet Server korrekt
[ ] Kein Fehler im Log beim ersten Start
```

---

## Delegierungs-Prompt für andere KI-Agenten

```
Du arbeitest an der Kollekten-Automation, einer Windows-Desktop-App für
evangelische Kirchengemeinden (EKHN). Wir erweitern sie um eine PWA.

PFLICHTLEKTÜRE:
- c:\ai\Buchungsblatt_kollekten\PLAN_PWA.md  ← dieser Plan
- c:\ai\Buchungsblatt_kollekten\CHECKLIST.md  ← App-Stand
- c:\ai\Buchungsblatt_kollekten\config.py      ← Config-Schema

REGEL: Bestehende Dateien NUR anfassen wenn im Plan explizit erlaubt.
       Alle neuen Dateien in app/api/ oder app/api/static/.

STACK: Python 3.11+, FastAPI, uvicorn, Vanilla JS (kein Framework)
VENV:  uv pip install (nie pip install)
PORT:  8765 (Standard)

DEINE AUFGABE: [hier Phase A/B/C/D/E und konkrete Datei eintragen]
```
