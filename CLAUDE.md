# EKHN Gemeindesekretariat-Software

## Projekt-Überblick

Windows-Desktop-App (PySide6) für evangelische Kirchengemeinden (EKHN).
Automatisiert Kollekten-E-Mails → Excel-Buchungsblätter und wächst zur vollständigen Sekretariatssoftware.

**Stack:** Python 3.12, PySide6 6.11, pdfplumber, openpyxl, win32com, requests, fastapi, uvicorn
**Venv:** `.venv/` — immer `uv pip install`, nie `pip install`
**Start:** `app_entry.py` → `app/main_window.py`
**API:** `app/api/server.py` auf Port 8765

## E-Mail-Format (Eingehend von no-reply@ekhn.info)

```
Hallo,
hier die Statistik zum Gottesdienst 22.03.26. Judika:
28
8
Stiftung für das Leben. 99,70
```

Zu extrahieren: Datum aus Zeile 1, Betrag = Zahl nach letztem Komma, Zweck = Text vor letztem Komma.

## Aufgabe (original)

1. Microsoft Outlook (lokal, via win32com) nach E-Mails von no-reply@ekhn.info durchsuchen
2. E-Mails mit Muster "hier die Statistik zum Gottesdienst" erkennen
3. Datum, Betrag, Verwendungszweck extrahieren
4. Monatliche Excel-Datei befüllen (eine Kopie der Vorlage pro Monat)
5. Als Windows-Task-Scheduler-Job alle 30 Minuten laufen

## Excel-Spalten (Sheet: "eigene Gemeinde")

- Spalte A (Betrag): numerisch, Format €
- Spalte F (Kollekte vom): Datum DD.MM.YYYY
- Spalte H (Verwendungszweck): Text
- Daten ab Zeile 17, eine Zeile pro Eintrag

## Aktuelle Tabs (app/main_window.py)

1. **Übersicht** — Dashboard, Run-Button, Status-Cards
2. **Verlauf** — CollectionTable mit Filter + Bericht-Export
3. **Dokumente** — Quellenverwaltung + Keyword-Suche
4. **Gottesdienst** — Jahresplan (Pfarrer, Organist, Kollekte), Import, Abkündigung
5. **Verwaltung** — Wiedervorlagen/Fristen (CRUD, Farbkodierung)
6. **Hilfe / KI** — ChatWidget mit Tool-Use (13 Tools, 5 Bestätigungsstufen)
7. **Einstellungen** — Allgemein, Ausführung, PWA/API, KI, Über

## KI-Tools (app/ai/tools.py)

| Tool | Stufe |
|------|-------|
| get_buchungen, get_zusammenfassung, konfiguration_info | read_only |
| suche_kirchenrecht, suche_handbuch | read_only |
| get_formular_info, get_regionalverwaltung | read_only |
| get_recent_errors, get_kollektenplan, liste_faellige_fristen | read_only |
| verarbeitung_starten | user_confirmed |
| buchungsblatt_versenden | user_confirmed_send |
| save_note | user_confirmed |

## Daten-Verzeichnisse

```
data/
├── formulare/index.json          10 EKHN-Formulare
├── kontakte/regionalverwaltungen.json  9 RV + Stabsbereich Recht
├── knowledge/kirchenrecht/       PDFs hier ablegen (kirchenrecht-ekhn.de)
├── reference/kollektenregeln.json  Klassifizierungsregeln
└── state/
    ├── wiedervorlagen.json       Fristen + Wiedervorlagen
    ├── gottesdienste.json        Gottesdienstplan (inkl. Pfarrer, Organist)
    ├── kollektenplan.json        EKHN-Kollektenplan (aus Jahresplanung-Import)
    └── notizen.json              Aktennotizen
```

## Codekonventionen

- Alle Dateien: `from __future__ import annotations` am Anfang
- `QAction` aus `PySide6.QtGui` (nicht `QtWidgets`!)
- Business-Logik nie direkt in `app/` importieren — immer `sys.path.insert(0, root)`
- JSON-Store-Pfad: `Path(__file__).parent.parent.parent / "data" / "state" / "*.json"`
- Neue Tabs: als eigenständige Klasse in `app/tabs/`, dann in `main_window.py` einbinden
- win32com nur auf Windows mit installiertem Outlook

## Wichtige Funktionen

- `config.get_config() -> dict` — lädt und normalisiert config.json
- `main.run(year_filter, dry_run) -> (int, int)` — Hauptpipeline
- `app/ai/tools.py::execute_tool(name, args, cfg)` — read-only Tools
- `app/ai/tools.py::execute_action_tool(name, args, cfg)` — nach Bestätigung
- `booking_store.get_booking_rows(cfg)` — Buchungsdaten laden

## Systemgrenzen

- **Kiris** (ersetzt KirA seit Okt. 2025): nur via VPN + Login, kein API-Zugriff
- **MACH** (Finanzbuchhaltung): nur via VPN + Login, kein API-Zugriff
- **kirchenrecht-ekhn.de**: öffentlich, PDFs downloadbar und lokal indexierbar
