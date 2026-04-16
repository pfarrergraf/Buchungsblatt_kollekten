# Kollekten-Automation — Startanleitung & Testhandbuch

## Schnellstart

### Desktop-App starten
```
cd C:\ai\Buchungsblatt_kollekten
.venv\Scripts\python app_entry.py
```

### Nur API-Server (ohne GUI, z.B. für Smartphone-Zugriff)
```
cd C:\ai\Buchungsblatt_kollekten
.venv\Scripts\python server_entry.py
```

### Smartphone-Tunnel (nur solange Terminal offen)
```
ssh -o ServerAliveInterval=30 -R 80:localhost:8765 nokey@localhost.run
```
→ Die angezeigte `https://xxxx.lhr.life`-URL im Handy-Browser öffnen  
→ Chrome: Menü (⋮) → „Zum Startbildschirm hinzufügen" → PWA installiert

---

## Was beim ersten Start passiert

1. App prüft ob `config.json` vollständig ist (Rechtsträger-Nr, beide Vorlagen)
2. Falls unvollständig → **Setup-Wizard** öffnet sich automatisch
3. Falls vollständig → direkt ins **Dashboard**

**Aktuelle Config ist vollständig** — der Wizard erscheint nicht.

---

## Was zu testen ist

### 1. App-Start
```
.venv\Scripts\python app_entry.py
```
Erwartetes Verhalten:
- Fenster öffnet sich (ca. 1–2 Sekunden)
- Header zeigt „Kollekten-Automation" in blau
- Tab „Übersicht" ist aktiv
- Linke Sidebar zeigt Gemeindename und nächsten Lauf
- Tabelle zeigt letzte Einträge (aus `output/kollekten_uebersicht.xlsx`)

### 2. Vorschau-Lauf (kein Schreiben, sicher zu testen)
- Button **„Vorschau"** klicken
- Fortschrittsbalken / Statuszeile zeigt Meldungen
- Am Ende: „X Kollekten verarbeitet, Y Fehler"
- Keine neuen Dateien in `output/` (dry-run schreibt nichts)

### 3. Echter Lauf
- Button **„Jetzt ausführen"** klicken
- Outlook muss offen und eingeloggt sein
- E-Mails von `no-reply@ekhn.info` mit Betreff „Gottesdienststatistik" werden verarbeitet
- Neue xlsx-Dateien in `output/eigene_gemeinde/` und `output/zur_weiterleitung/`
- `output/kollekten_uebersicht.xlsx` wird aktualisiert

### 4. Verlauf-Tab
- Tab „Verlauf" öffnen
- Tabelle zeigt alle bisherigen Kollekten mit Datum, Betrag, Zweck, Typ
- Filter nach Monat/Jahr funktioniert
- Einträge mit Warnung (!) sind gelb markiert

### 5. Einstellungen
- Tab „Einstellungen" → Sub-Tab „Allgemein"
  - Gemeindename, RV-Nr, Bank, IBAN sichtbar und editierbar
- Sub-Tab „PWA / API"
  - „API-Server aktivieren" einschalten → Port 8765
  - Speichern → App startet API-Server automatisch beim nächsten Start
- Sub-Tab „KI": Provider auf „Deaktiviert" lassen (kein Key nötig)

### 6. PWA / Smartphone
- In „Einstellungen → PWA / API": API aktivieren, Port 8765, Speichern
- `server_entry.py` starten (oder App neu starten)
- SSH-Tunnel starten (s.o.)
- Im Handy-Browser: Dashboard, Kollektenliste, Filter testen

---

## Bekannte Einschränkungen beim Testen

| Thema | Hinweis |
|---|---|
| Outlook | Muss lokal installiert und offen sein (win32com) |
| Templates | Pfade in config.json müssen existieren (aktuell: Downloads-Ordner) |
| Tray-Icon | Standardmäßig deaktiviert — erst nach Einstellung sichtbar |
| PWA-URL | Wechselt bei jedem Tunnel-Neustart (localhost.run kostenlos) |
| Gemeindename | Erscheint ggf. mit falschen Sonderzeichen → in Einstellungen korrigieren |

---

## Dateipfade (aktuell konfiguriert)

```
Vorlage eigene Gemeinde:
  C:\Users\Mein Computer\Downloads\12 RV RLW - KGM Buchungsblatt Kollekten und Spenden eigene Gemeinde 2026 V3.0-PNC.xlsx

Vorlage Weiterleitung:
  C:\Users\Mein Computer\Downloads\12 RV RLW - KGM Buchungsblatt Kollekten und Spenden zur Weiterleitung 2026 V3.0-PNC.xlsx

Ausgabe:
  C:\ai\Buchungsblatt_kollekten\output\

Übersicht:
  C:\ai\Buchungsblatt_kollekten\output\kollekten_uebersicht.xlsx

Log:
  C:\ai\Buchungsblatt_kollekten\kollekten.log

Laufverlauf:
  C:\ai\Buchungsblatt_kollekten\data\state\run_history.json
```

---

## Troubleshooting

**App startet nicht / Import-Fehler**
```
.venv\Scripts\python -c "from app.main_window import MainWindow; print('OK')"
```

**API-Server-Test (lokal)**
```
curl http://localhost:8765/api/status
```

**Abhängigkeiten nachinstallieren**
```
uv pip install -r requirements.txt
```

**Config zurücksetzen (Wizard erzwingen)**
```
del config.json
.venv\Scripts\python app_entry.py
```

**Log anzeigen**
```
type kollekten.log
```

---

## Versionsinformation

```
.venv\Scripts\python -c "from app.updater import APP_VERSION; print(APP_VERSION)"
```
