# Kollekten-App — Implementierungs-Checkliste

> **Maschinenlesbare Checkliste** für Claude Code, GitHub Copilot, Codex und andere KI-Tools.
> Verweist auf den vollständigen Plan: `C:\Users\Mein Computer\.claude\plans\rosy-frolicking-dream.md`
> Aktueller Stand: 2026-04-15

---

## Kontext für KI-Agenten

**Projekt:** Kollekten-Automation — Windows-Desktop-App (PySide6) für Ev. Kirchengemeinden (EKHN)
**Stack:** Python 3.11+, PySide6 6.11, pystray, openpyxl, win32com, requests, pdfplumber
**Venv:** `.venv/` im Projektroot — immer `uv pip install`, nie `pip install`
**Startpunkt App:** `app_entry.py` → `app/main_window.py`
**Startpunkt CLI:** `main.py run --year 2026`
**Konfiguration:** `config.json` (V2-Schema, wird von `config.py::get_config()` geladen)
**Theme:** `app/theme/office2010.qss` — Office-2010-Blau (#2B579A), Segoe UI
**Tests:** `python app_entry.py` startet die GUI; `python main.py run --year 2026` testet CLI

---

## Phase 1: PySide6-Grundgerüst ✅ ABGESCHLOSSEN

- [x] PySide6 6.11, pystray, Pillow, requests, pdfplumber installiert
- [x] `app/` Verzeichnisstruktur angelegt (`widgets/`, `ai/`, `theme/`)
- [x] `app/theme/office2010.qss` — vollständiges QSS-Theme
- [x] `app/main_window.py` — Hauptfenster mit Header, Tabs, Sidebar, StatusCards, Tabelle
      Enthält: `UebersichtTab`, `VerlaufTab` (Platzhalter), `EinstellungenTab` (Platzhalter)
- [x] `app_entry.py` — Einstiegspunkt
- [x] `assets/app.png`, `assets/app.ico` — Kirchenkreuz-Icon
- [x] `main.run()` gibt `(processed_count, error_count)` zurück

**Verifikation:** `python app_entry.py` öffnet Fenster, blaues Header-Band, Office-Stil ✓

---

## Phase 2: Setup-Wizard + Tray ✅ ABGESCHLOSSEN

> Plan-Referenz: Abschnitt "Phase 2: Setup-Wizard + Tray (opt-in)"

### 2a. Setup-Wizard — `app/setup_wizard.py` ✅

- [x] `SetupWizard(QWizard)` mit 4 Pages
- [x] **Page 1 — GemeindePage**: gemeinde_name, rechtsträger_nr (4-6 Ziffern Validator), bank_name, bank_iban, bank_bic
- [x] **Page 2 — VorlagenPage**: 2 Dateidialoge für .xlsx, isComplete() erst true wenn beide gewählt
- [x] **Page 3 — ZeitplanPage**: Radio Manuell/Täglich/Wöchentlich + OPT-IN Checkboxen (Tray, Autostart — standardmäßig DEAKTIVIERT)
- [x] **Page 4 — TestPage**: run(dry_run=True) in QThread, Ergebnisanzeige, Spendenhinweis
- [x] `wizard.accept()` → `config.save_config()`, ruft `autostart.set_autostart()` auf

### 2b. Autostart-Registry — `app/autostart.py` ✅

- [x] `set_autostart(enabled, exe_path)` → HKCU Registry, kein Admin nötig
- [x] `is_autostart_enabled() -> bool`

### 2c. Tray — `app/tray.py` ✅

- [x] `TrayIcon(on_open, on_run, on_quit)` — pystray in Daemon-Thread
- [x] Menü: "Dashboard öffnen" | "Jetzt ausführen" | "─" | "Beenden"
- [x] `show_notification(title, msg)` via `icon.notify()`
- [x] Qt-sicher: `QTimer.singleShot(0, fn)` für UI-Callbacks

### 2d. First-Run-Erkennung — `app_entry.py` ✅

- [x] `_needs_setup()` prüft rechtsträger_nr + beide Template-Pfade
- [x] Wizard wird vor MainWindow geöffnet wenn nötig
- [x] `app.use_tray`, `app.autostart`, `app.font_size`, `app.theme` in DEFAULT_CONFIG

---

## Phase 3: Verlauf + Korrektur 🔄 TEILWEISE ABGESCHLOSSEN

> Plan-Referenz: Abschnitt "Phase 3: Verlauf + manuelle Korrektur"

### 3a. `app/widgets/collection_table.py` ✅

- [x] `CollectionTable(QTableWidget)` — 7 Spalten: Datum|Betrag|Verwendungszweck|Typ|AObj|⚠|Datei
- [x] Typ-Zellen farbig: grün (eigene), blau (Weiterleitung)
- [x] `needs_review`-Zeilen gelb hinterlegt
- [x] Daten aus `output/kollekten_uebersicht.xlsx` via openpyxl
- [x] Sortierung nach Datum absteigend
- [x] Rechtsklick: "Klassifizierung korrigieren…" | "In Explorer öffnen"
- [x] `load_data(cfg, month_filter, year_filter, only_warnings)` mit Filter-Support
- [x] `correction_saved = Signal(str, str, str)` — pattern, scope, aobj

### 3b. `KorrekturDialog` — in `collection_table.py` ✅

- [x] Scope-ComboBox: eigene_gemeinde | zur_weiterleitung
- [x] AObj-ComboBox (lädt aus abrechnungsobjekte.json, Fallback hardcoded)
- [x] Grundtext-Feld
- [x] Speichert in `data/reference/manual_overrides.json`

### 3c. `VerlaufTab` — Vollimplementierung in `main_window.py` ✅

- [x] Ersetze Platzhalter-QLabel durch echte CollectionTable-Integration
- [x] Filter-Leiste oben: Monat (QComboBox, 1-12 + "Alle"), Jahr (QSpinBox), "Nur Warnungen" (QCheckBox)
- [x] Statistik-Zeile unten: "Eigene: X,XX € | Weiterleitung: X,XX € | Gesamt: X,XX €"
- [x] "Bericht erstellen"-Button rechts (→ Phase 4, vorerst deaktiviert/Platzhalter)
- [x] Bei `correction_saved`-Signal: Tabelle neu laden

---

## Phase 4: Monatsbericht ✅ ABGESCHLOSSEN

> Plan-Referenz: Abschnitt "Monatsbericht"

### `app/reporter.py`

- [x] `generate_monthly_report(month, year, cfg) -> ReportData` — liest aus overview.xlsx
- [x] `print_report(report, parent)` via QPrinter + QPainter
- [x] `preview_report(report, parent)` via QPrintPreviewDialog
- [x] `export_pdf(report, path)` — QPrinter PDF-Format
- [x] `email_report(report, cfg)` — exportiert PDF, versendet via email_sender
- [x] Dropdown-Button "Bericht erstellen ▼" in VerlaufTab: Drucken | Vorschau | PDF | E-Mail

---

## Phase 5: Dokument-Suche ✅ ABGESCHLOSSEN

> Plan-Referenz: Abschnitt "Dokument-Suche (EKHN-Quellen)"

### `app/documents.py`

- [x] `DocumentSource` dataclass mit `to_dict` / `from_dict`
- [x] `load_sources(cfg)`, `save_sources(cfg, sources)`
- [x] `refresh_source(source)` — PDF via pdfplumber, URL via requests, Ordner rekursiv
      Caching in `data/documents/<md5>.txt`
- [x] `search_sources(query, sources)` — Substring-Matching, Kontext ±1 Zeile

### `DocumenteTab` — in `main_window.py` ✅

- [x] Tab "Dokumente" zwischen Verlauf und Hilfe
- [x] QListWidget mit Icons (📄/🌐/📁) + Datum
- [x] Buttons: "+ Hinzufügen" | "Aktualisieren" | "Löschen"
- [x] Hinzufügen-Dialog: Radio Datei/URL/Ordner + Dateidialog
- [x] Suchfeld + HTML-Ergebnisanzeige

---

## Phase 6: AI-Integration ✅ ABGESCHLOSSEN

> Plan-Referenz: Abschnitt "AI-Integration (optional, konfigurierbar)"

### `app/ai/provider.py`

- [x] `AIProvider(ABC)` mit `chat(messages: list[dict]) -> str`
      und `is_available() -> bool`, `name() -> str`
- [x] `DisabledProvider` — Standardfall, wirft `AIDisabledError`
- [x] `OpenRouterProvider(api_key, model)` — POST `https://openrouter.ai/api/v1/chat/completions`
      Header: `Authorization: Bearer <key>`, `HTTP-Referer: kollekten-automation`
      Kostenlose Modelle: `meta-llama/llama-3.1-8b-instruct:free`
- [x] `OpenAIProvider(api_key, model="gpt-4o-mini")` — openai SDK oder direktes requests
- [x] `AnthropicProvider(api_key, model="claude-haiku-4-5-20251001")` — anthropic SDK
- [x] `get_provider(cfg: dict) -> AIProvider` — Factory aus `cfg["ai"]["provider"]`

### `app/ai/chat_widget.py`

- [x] `ChatWidget(QWidget)` — Nachrichtenverlauf (HTML-Bubbles), Eingabe + Senden
- [x] `ChatWorker(QObject)` in QThread, nie blockierend
- [x] System-Prompt mit Gemeinde-Kontext + AObj-Codes
- [ ] Spezial-Commands: `/search <query>` → sucht in Dokument-Quellen
- [ ] Worker-Thread für API-Calls (nie blockierend)

### `HilfeTab` — in `main_window.py` ✅

- [x] Tab "Hilfe / KI" — ChatWidget eingebettet
- [x] Wenn KI deaktiviert: Hinweistext mit Verweis auf Einstellungen

---

## Phase 7: Update-Mechanismus ⬜ OFFEN

> Plan-Referenz: Abschnitt "Update-Mechanismus (GitHub Releases)"

### `app/updater.py`

- [x] `APP_VERSION = "1.0.0"` — zentrale Versionskonstante
- [x] `GITHUB_REPO = "PLACEHOLDER/kollekten-automation"` — Platzhalter, vor Release setzen
- [x] `check_for_update() -> UpdateInfo | None`
      GET `https://api.github.com/repos/{REPO}/releases/latest`
      Timeout 5s, Exception schlucken (nie blockieren)
      Vergleich: `semver`-Vergleich oder einfacher String-Vergleich "v1.0.1" > "v1.0.0"
- [x] `UpdateBanner(QWidget)` — kleines Banner oben im Hauptfenster
      "Version 1.1.0 verfügbar — [Herunterladen] [Später]"
      "Herunterladen" → `webbrowser.open(release_url)`
- [x] In `MainWindow.__init__`: Background-Check via `QTimer.singleShot(3000, ...)`

**Verifiziert:**

- [x] `python -c "from app.updater import check_for_update; print('updater OK')"`
- [x] `python -c "from app.ai.provider import get_provider; print('provider OK')"`

---

## Phase 8: EinstellungenTab ✅ ABGESCHLOSSEN

> Plan-Referenz: Abschnitt "Setup-Wizard, Schritt 3" + "AI-Integration"

### `EinstellungenTab` — Vollimplementierung in `main_window.py`

- [x] Sub-Tabs: "Allgemein" | "Ausführung" | "KI" | "Über"
- [x] Allgemein: Gemeindedaten, Vorlagenpfade (Dateidialog), Empfänger-E-Mails
- [x] Ausführung: Zeitplan-Radio + Tray/Autostart-Checkboxen (opt-in) + Schriftgröße
- [x] KI: Provider-Auswahl, API-Key (maskiert), Modell, [Verbindung testen]
- [x] Über: App-Name, Version, Spendenhinweis
- [x] Speichern: schreibt config.json, ruft autostart.set_autostart(), passt Schriftgröße an
- [x] `settings_saved` Signal → MainWindow lädt Config neu

---

## Phase 9: Packaging ✅ ABGESCHLOSSEN

> Plan-Referenz: Abschnitt "Phase 4: Packaging"

### PyInstaller

- [x] `kollekten_app.spec` — --windowed, --onedir, icon, datas, hiddenimports
- [ ] Build testen: `pyinstaller kollekten_app.spec`  ← manuell ausführen
- [ ] Testen auf sauberem Windows (ohne Python)

### NSIS Installer ✅

- [x] `installer/setup.nsi` — MUI2, Lizenz, Ziel PROGRAMFILES64, Startmenü, Desktop
- [x] `installer/license.txt` — Freeware-Lizenz
- [ ] `Kollekten-Setup-1.0.0.exe` bauen ← manuell: `makensis installer/setup.nsi`

---

## Konfigurationsfelder (noch hinzuzufügen)

Folgende Felder fehlen noch in `config.py::DEFAULT_CONFIG`:

```python
# In "app"-Sektion (neu):
"app": {
    "use_tray": False,          # Phase 2c
    "autostart": False,         # Phase 2b
    "font_size": 9,             # Phase 8
    "theme": "office2010",      # Zukunft
}

# In "ai"-Sektion (neu):
"ai": {
    "provider": "disabled",     # "disabled"|"openrouter"|"openai"|"anthropic"|"local"
    "api_key": "",
    "model": "meta-llama/llama-3.1-8b-instruct:free",
    "openrouter_base_url": "https://openrouter.ai/api/v1",
}

# In "document_sources" (neu):
"document_sources": []          # Liste von DocumentSource-Dicts
```

---

## Dateistruktur (Ist-Zustand 2026-04-15, Stand: alle Phasen abgeschlossen)

```
app/
├── __init__.py
├── main_window.py          ✅ Vollständig (alle Tabs)
├── setup_wizard.py         ✅ Phase 2a
├── autostart.py            ✅ Phase 2b
├── tray.py                 ✅ Phase 2c
├── reporter.py             ✅ Phase 4
├── documents.py            ✅ Phase 5
├── updater.py              ✅ Phase 7
├── ai/
│   ├── __init__.py         ✅
│   ├── provider.py         ✅ Phase 6a
│   └── chat_widget.py      ✅ Phase 6b
├── widgets/
│   ├── __init__.py         ✅
│   └── collection_table.py ✅ Phase 3a+3b
└── theme/
    └── office2010.qss      ✅ Phase 1

app_entry.py                ✅
assets/app.png + app.ico    ✅
kollekten_app.spec          ✅ Phase 9
installer/setup.nsi         ✅ Phase 9
installer/license.txt       ✅
```

## Verbleibende manuelle Schritte

1. `pyinstaller kollekten_app.spec` — baut `dist/Kollekten-Automation/`
2. `makensis installer/setup.nsi` — baut `Kollekten-Setup-1.0.0.exe`
3. Test auf sauberem Windows (ohne Python-Installation)
4. GitHub-Repo anlegen, `GITHUB_REPO` in `app/updater.py` setzen
5. Version `APP_VERSION` in `app/updater.py` bei Releases erhöhen

---

## Für andere KI-Agenten (Codex/Copilot)

**Codekonventionen:**
- Alle Dateien beginnen mit `from __future__ import annotations`
- PySide6 imports: immer aus `PySide6.QtWidgets`, `PySide6.QtCore`, `PySide6.QtGui`
- Keine f-Strings mit komplexen Ausdrücken (für Python 3.11 Kompatibilität)
- `objectName` für QSS-Styling: z.B. `widget.setObjectName("primaryButton")`
- Business-Logik (parser, classifier, excel_writer) NIEMALS in app/ importieren direkt —
  immer über `sys.path.insert(0, projektroot)` dann `import main` etc.

**Wichtige bestehende Funktionen:**
- `config.get_config() -> dict` — lädt und normalisiert config.json
- `config.save_config(cfg: dict)` — speichert config.json
- `main.run(year_filter, dry_run) -> (int, int)` — Hauptpipeline
- `references.find_reference_match(text, cfg) -> ReferenceMatch`
- `state_store.load_id_set(path) -> set[str]`

**Bekannte Fallstricke:**
- win32com nur auf Windows mit installiertem Outlook verfügbar
- openpyxl: timezone-aware datetimes müssen `.replace(tzinfo=None)` vor xlsx-Schreiben
- pystray: `icon.run()` blockiert — immer in eigenem Thread starten
- QThread + Worker-Pattern für alle blocking calls (Outlook, Excel, HTTP)
