# Kollekten-App — Befehle & Testhandbuch

> Stand: 2026-04-17 | App-Version 1.1.0

---

## Schnellstart

### Desktop-App starten
```bash
cd C:\ai\Buchungsblatt_kollekten
.venv\Scripts\python app_entry.py
```

### Nur API-Server (ohne GUI)
```bash
.venv\Scripts\python -m uvicorn app.api.server:app --host 127.0.0.1 --port 8765 --reload
# oder:
.venv\Scripts\python server_entry.py
```

### CLI-Verarbeitung (ohne GUI)
```bash
.venv\Scripts\python main.py run --year 2026
.venv\Scripts\python main.py run --dry-run       # Testlauf, keine Dateien
```

---

## Import-Tests (Syntax-Check)

```bash
# Alle Module auf Importfehler prüfen
.venv\Scripts\python -c "from app.main_window import MainWindow; print('main_window OK')"
.venv\Scripts\python -c "from app.tabs.verwaltung import VerwaltungTab; print('verwaltung OK')"
.venv\Scripts\python -c "from app.tabs.gottesdienst import GottesdienstTab; print('gottesdienst OK')"
.venv\Scripts\python -c "from app.ai.tools import TOOL_LEVELS, to_anthropic_tools; print('tools OK')"
.venv\Scripts\python -c "from app.ai.provider import get_provider; print('provider OK')"
.venv\Scripts\python -c "from app.api.server import app; print('api OK')"
```

---

## API-Endpunkte (Server muss laufen)

```bash
# Status
curl http://127.0.0.1:8765/api/status

# Alle Kollekten
curl http://127.0.0.1:8765/api/kollekten

# Kollekten gefiltert (month/year, nicht monat/jahr!)
curl "http://127.0.0.1:8765/api/kollekten?month=4&year=2026"

# Nur Warnungen
curl "http://127.0.0.1:8765/api/kollekten?only_warnings=true"

# Zusammenfassung
curl "http://127.0.0.1:8765/api/kollekten/summary?month=4&year=2026"

# Swagger UI
# Browser: http://127.0.0.1:8765/api/docs

# PWA
# Browser: http://127.0.0.1:8765/
```

---

## KI-Tools testen

```bash
# Alle registrierten Tools anzeigen
.venv\Scripts\python -c "
from app.ai.tools import TOOL_LEVELS, to_anthropic_tools
tools = to_anthropic_tools()
for t in tools:
    level = TOOL_LEVELS.get(t['name'], '?')
    print(f'  [{level:20s}] {t[\"name\"]}')
"

# Einzelne Tool-Funktionen testen (ohne KI)
.venv\Scripts\python -c "
import sys; sys.path.insert(0, '.')
from config import get_config
from app.ai.tools import execute_tool
cfg = get_config()
print(execute_tool('get_zusammenfassung', {'monat': 4, 'jahr': 2026}, cfg))
"

.venv\Scripts\python -c "
import sys; sys.path.insert(0, '.')
from config import get_config
from app.ai.tools import execute_tool
cfg = get_config()
print(execute_tool('konfiguration_info', {}, cfg))
"

.venv\Scripts\python -c "
import sys; sys.path.insert(0, '.')
from config import get_config
from app.ai.tools import execute_tool
cfg = get_config()
print(execute_tool('liste_faellige_fristen', {'tage': 365}, cfg))
"

.venv\Scripts\python -c "
import sys; sys.path.insert(0, '.')
from config import get_config
from app.ai.tools import execute_tool
cfg = get_config()
print(execute_tool('get_formular_info', {'typ': 'spendenquittung'}, cfg))
"
```

---

## Wiedervorlagen / Fristen

```bash
# Fällige Fristen anzeigen
.venv\Scripts\python -c "
import json
from pathlib import Path
wv = json.loads(Path('data/state/wiedervorlagen.json').read_text(encoding='utf-8'))
offen = [e for e in wv if not e.get('erledigt')]
print(f'{len(offen)} offene Wiedervorlagen:')
for e in sorted(offen, key=lambda x: x.get('frist_datum', '')):
    print(f'  {e[\"frist_datum\"]}  {e[\"titel\"]}  [{e[\"kategorie\"]}]')
"
```

---

## Gottesdienst / Jahresplanung

```bash
# Gottesdienste anzeigen
.venv\Scripts\python -c "
import json
from pathlib import Path
gd = json.loads(Path('data/state/gottesdienste.json').read_text(encoding='utf-8'))
print(f'{len(gd)} Gottesdienste:')
for e in sorted(gd, key=lambda x: x.get('datum', ''))[:10]:
    print(f'  {e[\"datum\"]}  {e.get(\"uhrzeit\",\"\")}  {e.get(\"pfarrer_in\",\"\")}  {e.get(\"organist\",\"\")}  {e.get(\"kollekte_zweck\",\"\")}')
"

# Kollektenplan anzeigen
.venv\Scripts\python -c "
import json
from pathlib import Path
kp = json.loads(Path('data/state/kollektenplan.json').read_text(encoding='utf-8'))
print(f'{len(kp)} Kollektenplan-Eintraege')
for e in kp[:10]:
    print(f'  {e[\"datum\"]}  {e.get(\"zweck\",\"\")}')
"
```

---

## Abhängigkeiten

```bash
# Installieren
uv pip install -r requirements.txt

# Prüfen welche Pakete fehlen
.venv\Scripts\python -c "import pdfplumber, openpyxl, PySide6, requests, fastapi, uvicorn; print('alle OK')"

# Version anzeigen
.venv\Scripts\python -c "from app.updater import APP_VERSION; print('Version:', APP_VERSION)"
```

---

## Konfiguration

```bash
# Config anzeigen
.venv\Scripts\python -c "
import sys; sys.path.insert(0, '.')
from config import get_config
import json
cfg = get_config()
# Sensitive Felder ausblenden
safe = {k: v for k, v in cfg.items() if k not in ('ai',)}
print(json.dumps(safe, indent=2, ensure_ascii=False))
"

# Config zurücksetzen (erzwingt Setup-Wizard)
del config.json
.venv\Scripts\python app_entry.py
```

---

## Logs & Diagnose

```bash
# Letztes Log anzeigen
type kollekten.log

# Nur Fehler
findstr "ERROR\|CRITICAL" kollekten.log

# Verarbeitete E-Mail-IDs
.venv\Scripts\python -c "
from state_store import load_id_set
ids = load_id_set('data/state/processed_emails.json')
print(f'{len(ids)} verarbeitete E-Mails')
"
```

---

## Smartphone-Tunnel (localhost.run)

```bash
# Tunnel starten (solange Terminal offen)
ssh -o ServerAliveInterval=30 -R 80:localhost:8765 nokey@localhost.run
# → Angezeigte https://xxxx.lhr.life URL im Handy-Browser öffnen
# → Chrome: Menü → "Zum Startbildschirm hinzufügen" → PWA installiert
```

---

## Build & Packaging

```bash
# PyInstaller-Build
pyinstaller kollekten_app.spec

# NSIS-Installer (nach Build)
makensis installer\setup.nsi
```

---

## Bekannte Fallstricke

| Problem | Lösung |
|---------|--------|
| `ImportError: QAction from QtWidgets` | `QAction` ist in PySide6 6.x in `QtGui` |
| `win32com` nicht verfügbar | Outlook muss installiert sein |
| Schriftzeichen in Log falsch | Windows CP1252 → `errors="replace"` beim Lesen |
| API-Filter `monat=4` funktioniert nicht | Route nutzt `month`/`year` (Englisch!) |
| App startet nicht — fehlende Config | `del config.json` → Setup-Wizard |
| PDF zu groß für Read-Tool | pdfplumber direkt via Bash nutzen |
