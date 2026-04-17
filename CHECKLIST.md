# Kollekten-App — Implementierungs-Checkliste

> **Maschinenlesbare Checkliste** für Claude Code, Codex und andere KI-Agenten.
> Roadmap-Vollversion: `C:\Users\Mein Computer\.claude\plans\velvety-wiggling-rainbow.md`
> Aktueller Stand: **2026-04-17** — App-Version 1.1.0

---

## Kontext für KI-Agenten

**Projekt:** EKHN Gemeindesekretariat-Software — Windows-Desktop-App (PySide6) für Ev. Kirchengemeinden
**Stack:** Python 3.12, PySide6 6.11, pdfplumber, openpyxl, win32com, requests, fastapi, uvicorn
**Venv:** `.venv/` im Projektroot — immer `uv pip install`, nie `pip install`
**Startpunkt App:** `app_entry.py` → `app/main_window.py`
**Startpunkt API:** `server_entry.py` oder `.venv/Scripts/python -m uvicorn app.api.server:app --port 8765`
**Startpunkt CLI:** `main.py run --year 2026`
**Konfiguration:** `config.json` (V2-Schema, geladen via `config.py::get_config()`)
**Theme:** `app/theme/office2010.qss` — Office-2010-Blau (#2B579A), Segoe UI

---

## Ursprüngliche Phasen 1–9: Basis-App ✅ ABGESCHLOSSEN

### Phase 1: PySide6-Grundgerüst ✅
- [x] `app/main_window.py` — Hauptfenster mit Header, Tabs, Sidebar, StatusCards
- [x] `app/theme/office2010.qss` — vollständiges QSS-Theme
- [x] `app_entry.py` — Einstiegspunkt, First-Run-Erkennung
- [x] `assets/app.png`, `assets/app.ico` — Kirchenkreuz-Icon

### Phase 2: Setup-Wizard + Tray ✅
- [x] `app/setup_wizard.py` — 4-seitiger Wizard (Gemeinde, Vorlagen, Zeitplan, Test)
- [x] `app/autostart.py` — HKCU-Registry, kein Admin nötig
- [x] `app/tray.py` — pystray Daemon-Thread mit Menü + Benachrichtigungen

### Phase 3: Verlauf + Korrektur ✅
- [x] `app/widgets/collection_table.py` — CollectionTable mit 7 Spalten, Farbkodierung
- [x] `KorrekturDialog` — speichert in `data/reference/manual_overrides.json`
- [x] `VerlaufTab` — Filter Monat/Jahr/Warnungen, Statistikzeile, Bericht-Button

### Phase 4: Monatsbericht ✅
- [x] `app/reporter.py` — generate_monthly_report, Drucken/Vorschau/PDF/E-Mail

### Phase 5: Dokument-Suche ✅
- [x] `app/documents.py` — DocumentSource, PDF/URL/Ordner-Indexierung, Keyword-Suche
- [x] `DocumenteTab` — Quellenverwaltung, Suche mit HTML-Ergebnisanzeige

### Phase 6: KI-Integration Basis ✅
- [x] `app/ai/provider.py` — AIProvider ABC + DisabledProvider, OpenRouter, OpenAI, Anthropic, Ollama, LM Studio
- [x] `app/ai/chat_widget.py` — ChatWidget mit Bubble-UI, ChatWorker(QThread)
- [x] `app/ai/tools.py` — 13 Tools, TOOL_LEVELS, ACTION_TOOLS, to_anthropic_tools/to_openai_tools
- [x] `HilfeTab` — ChatWidget eingebettet, KI-Hinweis wenn deaktiviert

### Phase 7: Update-Mechanismus ✅
- [x] `app/updater.py` — GitHub Releases Check, UpdateBanner
- [ ] GitHub-Repo anlegen + GITHUB_REPO setzen (manuell)

### Phase 8: EinstellungenTab ✅
- [x] Sub-Tabs: Allgemein | Ausführung | PWA/API | KI | Über
- [x] KI-Einstellungen: Provider, API-Key, Modell, Verbindungstest

### Phase 9: Packaging ✅
- [x] `kollekten_app.spec` — PyInstaller-Spec
- [x] `installer/setup.nsi` — NSIS-Installer
- [ ] Build testen (manuell: `pyinstaller kollekten_app.spec`)

### FastAPI / PWA ✅
- [x] `app/api/server.py` — FastAPI + uvicorn in Daemon-Thread
- [x] `app/api/routes/` — status, kollekten (GET/summary), actions (POST run), live (SSE)
- [x] `app/api/static/` — PWA (index.html, app.js, manifest.json, sw.js)

---

## Roadmap Phase 1: KI-Tools & Sicherheitsstufen ✅ ABGESCHLOSSEN (2026-04-17)

### 1a. Bestätigungsstufen ✅
- [x] `TOOL_LEVELS` in `app/ai/tools.py`: read_only | draft_only | user_confirmed | user_confirmed_send | admin_only
- [x] `ACTION_TOOLS` aus TOOL_LEVELS abgeleitet (generisch)
- [x] `chat_widget.py._execute_call()` prüft Level, passender Dialog je Stufe
- [x] `user_confirmed_send` → QMessageBox.Warning mit E-Mail-Hinweis
- [x] System-Prompt mit Disclaimer + alle 13 Tools dokumentiert

### 1b+c. Wissens-Tools ✅
- [x] `suche_kirchenrecht(query)` — Keyword-Suche in `data/knowledge/kirchenrecht/*.pdf`
- [x] `suche_handbuch(prozess)` — Handbuch 2019, Cache in `data/knowledge/handbuch_2019.txt`
- [x] `_load_or_extract_text()` + `_keyword_snippets()` — PDF-Extraktion mit Caching

### 1d. Formular-Index ✅
- [x] `data/formulare/index.json` — 10 EKHN-Formulare (Spendenquittung, AAO, Taufregister, ...)
- [x] `get_formular_info(typ)` — Tool sucht nach ID, Name, Schlagworten

### 1e. Regionalverwaltungs-Index ✅
- [x] `data/kontakte/regionalverwaltungen.json` — 9 RV inkl. Stabsbereich Recht
- [x] `get_regionalverwaltung(thema)` — findet zuständige RV nach Thema + Gemeinde-Ort

### Weitere neue Tools ✅
- [x] `get_recent_errors(anzahl)` — liest kollekten.log
- [x] `get_kollektenplan(datum)` — aus `data/state/kollektenplan.json`
- [x] `liste_faellige_fristen(tage)` — aus `data/state/wiedervorlagen.json`
- [x] `save_note(entity_type, entity_id, note)` — in `data/state/notizen.json`

### Daten angelegt ✅
- [x] `data/knowledge/kirchenrecht/HINWEIS.txt` — Anleitung PDFs ablegen
- [x] `data/state/wiedervorlagen.json` — 7 vorausgefüllte Regelfristen (Handbuch-Quellen)
- [x] `data/state/kollektenplan.json` — leer, bereit zum Befüllen
- [x] `data/state/notizen.json` — leer, bereit
- [x] `data/formulare/templates/` — Verzeichnis für DOCX-Templates

---

## Roadmap Phase 2: Wiedervorlage-Tab ✅ ABGESCHLOSSEN (2026-04-17)

- [x] `app/tabs/verwaltung.py` — `VerwaltungTab(QWidget)`
- [x] Tabelle mit Farbkodierung: rot (überfällig), gelb (heute/morgen), lila (diese Woche), grau (erledigt)
- [x] CRUD: Neu / Bearbeiten (Doppelklick) / Erledigt / Löschen
- [x] Bearbeitungs-Dialog: Titel, QDateEdit, Kategorie, Priorität, AZ, Notiz, Erledigt-Checkbox
- [x] Filter: Kategorie-ComboBox, Status-ComboBox (Alle/Offen/Erledigt)
- [x] `get_faellige_anzahl() -> int` — für Startup-Hinweis
- [x] In `main_window.py` integriert als Tab "Verwaltung"
- [x] `_check_faellige_fristen()` in `MainWindow.__init__` → Statusbar-Hinweis beim Start

---

## Roadmap Phase 3: Gottesdienst-Tab ✅ ABGESCHLOSSEN (2026-04-17)

- [x] `app/tabs/gottesdienst.py` — `GottesdienstTab(QWidget)` mit Sub-Tabs
- [x] Sub-Tab "Gottesdienstplan": Monats-Navigation, Tabelle (Datum|Zeit|Ort|Pfarrer|Organist|Kollekte|Typ)
- [x] Sub-Tab "Import": Jahresplanung aus Excel/CSV importieren
  - [x] Automatische Spalten-Erkennung (Header-Zeile)
  - [x] Felder: Datum, Uhrzeit, Pfarrer/in, Organist, Kollekte Zweck, Ort
  - [x] Vorschau (5 Zeilen) vor Import
  - [x] Optional: bestehende Einträge überschreiben
  - [x] Kollektenplan parallel befüllen aus Kollekte-Spalte
- [x] Sub-Tab "Abkündigung": lokaler Generator (kein KI-Call nötig), Clipboard-Export
- [x] In `main_window.py` integriert als Tab "Gottesdienst"
- [x] Datenmodell: `data/state/gottesdienste.json` mit Feldern inkl. `organist`

---

## Roadmap Phase 4: Offline-KI (Ollama + ChromaDB) ⬜ OFFEN

- [ ] `app/ai/vector_store.py` — ChromaDB-Wrapper mit Ollama-Embeddings
- [ ] `app/ai/rag.py` — Hybrid-RAG (BM25 Keyword + semantisch)
- [ ] Ollama-Setup-Assistent in Einstellungen → KI
- [ ] KI-Wissensbasis-Tab in DocumenteTab (Indexieren/Status)
- [ ] `chromadb` in requirements.txt

---

## Roadmap Phase 5: EKHN-Wissen strukturiert ⬜ OFFEN

- [ ] Kirchenrecht-PDFs von kirchenrecht-ekhn.de einlesen + §-Chunk-Zerlegung
- [ ] Kollektenplan-PDF automatisch parsen (Regex)
- [ ] Konflikterkennung bei Rechtsquellen
- [ ] Formular-Assistent mit python-docx Templates

---

## Roadmap Phase 6: MCP-Server ⬜ OFFEN

- [ ] `app/mcp_server.py` — FastMCP stdio-Server
- [ ] Claude Desktop Config-Snippet in Einstellungen
- [ ] `fastmcp` in requirements.txt

---

## Roadmap Phase 7: Personal + Verwaltung ⬜ OFFEN

- [ ] `data/state/personal.json` — Mitarbeitende
- [ ] Sub-Tab "Personal" in VerwaltungTab
- [ ] Urlaubsplanung + Fehlzeiten
- [ ] KV-Sitzungsassistent (Tagesordnung, Protokoll → Beschlüsse)

---

## Roadmap Phase 8–9: Amtshandlungen + Browser-Automation ⬜ OFFEN

- [ ] Amtshandlungs-Checklisten (Taufe, Trauung, Bestattung, Konfirmation)
- [ ] Gemeindebrief-Assistent
- [ ] Playwright-MCP (nur nach expliziter Nutzerfreigabe, Phase 9)

---

## Ausstehende manuelle Schritte

1. Kirchenrecht-PDFs herunterladen → `data/knowledge/kirchenrecht/` (siehe HINWEIS.txt)
2. EKHN-Kollektenplan 2026/2027 PDF importieren → `data/state/kollektenplan.json`
3. Jahresplanung-Excel importieren (Gottesdienst-Tab → Import)
4. GitHub-Repo anlegen, `GITHUB_REPO` in `app/updater.py` setzen
5. `pyinstaller kollekten_app.spec` → Build testen
6. `makensis installer/setup.nsi` → Installer bauen

---

## Dateistruktur (Ist-Zustand 2026-04-17)

```
app/
├── __init__.py
├── main_window.py          ✅ Tabs: Übersicht|Verlauf|Dokumente|Gottesdienst|Verwaltung|Hilfe/KI|Einstellungen
├── setup_wizard.py         ✅
├── autostart.py            ✅
├── tray.py                 ✅
├── reporter.py             ✅
├── documents.py            ✅
├── updater.py              ✅
├── ai/
│   ├── provider.py         ✅ 6 Provider + Tool-Support
│   ├── chat_widget.py      ✅ Tool-Loop, 5 Bestätigungsstufen
│   └── tools.py            ✅ 13 Tools, TOOL_LEVELS
├── api/
│   ├── server.py           ✅ FastAPI + uvicorn
│   ├── routes/             ✅ status, kollekten, actions, live
│   └── static/             ✅ PWA (index.html, app.js, manifest.json)
├── tabs/
│   ├── __init__.py         ✅
│   ├── verwaltung.py       ✅ Wiedervorlage-Tab
│   └── gottesdienst.py     ✅ Gottesdienst-Tab + Jahresplanung-Import
├── widgets/
│   └── collection_table.py ✅
└── theme/
    └── office2010.qss      ✅

data/
├── formulare/
│   ├── index.json          ✅ 10 EKHN-Formulare
│   └── templates/          ✅ (leer, bereit für DOCX-Templates)
├── kontakte/
│   └── regionalverwaltungen.json  ✅ 9 RV + Stabsbereich Recht
├── knowledge/
│   ├── kirchenrecht/       ✅ (leer — PDFs manuell ablegen)
│   └── _cache/             ✅ (automatisch befüllt)
├── reference/
│   ├── kollektenregeln.json        ✅
│   ├── abrechnungsobjekte.json     ✅
│   └── manual_overrides.json       ✅
└── state/
    ├── bookings.json               ✅
    ├── wiedervorlagen.json         ✅ 7 Regelfristen vorausgefüllt
    ├── gottesdienste.json          ✅
    ├── kollektenplan.json          ✅
    └── notizen.json                ✅
```

---

## Codekonventionen (für KI-Agenten)

- Alle Python-Dateien: `from __future__ import annotations` am Anfang
- PySide6: `QAction` aus `PySide6.QtGui` (nicht `QtWidgets`!)
- Venv-Pakete: `uv pip install`, nie `pip install`
- Business-Logik nie direkt in `app/` importieren — immer `sys.path.insert(0, root)` dann `import`
- JSON-Store-Pfad: `Path(__file__).parent.parent.parent / "data" / "state" / "*.json"`
- Neue Tabs: als eigenständige Klasse in `app/tabs/`, dann in `main_window.py` einbinden
