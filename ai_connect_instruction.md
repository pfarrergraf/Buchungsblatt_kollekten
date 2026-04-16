# AI-Connect — Recherche- und Planungsauftrag

## Kontext

Die Kollekten-Automation (PySide6 Desktop-App + FastAPI PWA) hat einen KI-Assistenten-Tab.
Die Anbindung läuft über `app/ai/provider.py` mit einer abstrakten `AIProvider`-Klasse
und einer `_ChatCompletionsProvider`-Basisklasse (OpenAI-kompatibles API-Format).

**Aktueller Stand:**
- OpenRouter (cloud, kostenlose + kostenpflichtige Modelle) — implementiert, funktioniert
- OpenAI — implementiert (Basisklasse), nicht getestet
- Anthropic — implementiert (eigenes Format), nicht getestet
- LM Studio, vLLM, Claude Code CLI — **noch nicht vorhanden**

**Ziel dieses Auftrags:**
Recherchiere, plane und bewertet die besten 3 Anbindungsoptionen für die App — mit
Fokus auf: einfache Einrichtung für technisch halbkundige Nutzer (Kirchensekretariate),
lokale Datenhaltung wo möglich, Offline-Fähigkeit, keine monatlichen Pflichtkosten.

---

## Aufgaben (sequentiell abarbeiten)

### 1. Ist-Analyse — bestehender Code lesen

Lies diese Dateien vollständig:
- `app/ai/provider.py` — Provider-Abstraktion, bestehende Implementierungen
- `app/ai/chat_widget.py` — wie Provider aufgerufen wird (messages-Format, Fehlerbehandlung)
- `app/main_window.py` → Klasse `EinstellungenTab`, Methode `_build_ki()` — UI-Felder

Notiere: Welche Felder hat die UI (Provider, API-Key, Modell)? Welche Lücken gibt es
für lokale Modelle (kein Key, andere Base-URL, kein cloud-Endpoint)?

---

### 2. Optionen recherchieren

Für jede Option: offizielle Doku lesen, GitHub-Repos durchsuchen, typische
Python-Integrationsmuster identifizieren.

#### Option A — LM Studio (lokal, kein GPU nötig)
- Doku: https://lmstudio.ai/docs/local-server
- GitHub suchen: `lmstudio python client openai compatible`
- Fragen: Welchen Port/Endpoint nutzt LM Studio? Ist es OpenAI-kompatibel?
  Welche Modelle laufen CPU-only auf einem normalen Windows-PC (8 GB RAM)?
  Wie startet man den Server per API oder CLI automatisch?

#### Option B — vLLM (lokal, GPU empfohlen)
- Doku: https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html
- GitHub: https://github.com/vllm-project/vllm
- Fragen: Ist vLLM auf Windows nativ verfügbar oder nur WSL/Docker?
  OpenAI-kompatibel? Welche Modelle sind für 8 GB VRAM geeignet?
  Startbefehl, typischer Port?

#### Option C — Ollama (lokal, einfachste Installation)
- Doku: https://ollama.com/
- GitHub: https://github.com/ollama/ollama
- Fragen: Windows-native? OpenAI-kompatibler Endpoint (`/v1/chat/completions`)?
  Auto-Download von Modellen? Welche Modelle < 4 GB für CPU?
  Python-Integration via `ollama` PyPI-Paket vs. direkte HTTP-Calls?

#### Option D — OpenAI direkt (cloud, kostenpflichtig)
- Doku: https://platform.openai.com/docs/api-reference/chat
- Fragen: Welches Modell ist günstigsten für kurze Q&A (gpt-4o-mini)?
  Rate-Limits auf Starter-Tier? Unterschied zu OpenRouter-OpenAI-Proxy?

#### Option E — Anthropic / Claude API (cloud)
- Doku: https://docs.anthropic.com/en/api/messages
- Fragen: Warum schlägt der bestehende Code fehl? System-Message-Format korrekt?
  `max_tokens` Pflicht? Welches Modell günstigsten (claude-haiku-3-5)?

#### Option F — Claude Code CLI als lokaler Proxy
- GitHub: https://github.com/anthropics/claude-code
- Fragen: Hat Claude Code einen lokalen HTTP-Server-Modus?
  Gibt es einen `--serve`-Flag oder MCP-Server-Endpoint?
  Kann man es als OpenAI-kompatiblen Proxy nutzen?

---

### 3. GitHub-Vorbilder suchen

Suche auf GitHub nach Python-Desktop-Apps (PySide6 / PyQt) die mehrere AI-Provider
einbinden. Stichwörter: `pyside6 ai provider openai ollama`, `pyqt llm provider abstraction`.
Notiere 2–3 Repos mit deren Ansatz (wie sie Provider wechseln, Konfiguration speichern).

---

### 4. Bewertungsmatrix erstellen

Bewerte alle gefundenen Optionen nach diesen Kriterien (1–5 Punkte, 5 = best):

| Kriterium              | Gewicht |
|------------------------|---------|
| Einrichtungsaufwand    | 25%     |
| Offline-fähig          | 20%     |
| Datenschutz (lokal)    | 20%     |
| Kosten                 | 15%     |
| Antwortqualität        | 10%     |
| Windows-Kompatibilität | 10%     |

Erstelle eine Tabelle: Optionen × Kriterien × Gesamtscore.

---

### 5. Top 3 ausformulieren

Für die drei besten Optionen schreibe jeweils:

```
### [Name]
**Typ:** lokal / cloud
**Endpoint:** http://localhost:PORT/v1  oder  https://api.xyz.com/v1
**Benötigt:** [was der Nutzer installieren/konfigurieren muss]
**Implementierung:** [neue Klasse in provider.py? Erweiterung bestehender? UI-Änderungen?]
**Verifikation:** [wie testen wir ob es funktioniert, ohne echte Chat-Calls zu verschwenden]
**Risiken / Einschränkungen:** [was kann schiefgehen]
```

---

### 6. Implementierungsplan skizzieren

Für jede der Top-3-Optionen: welche Dateien müssen geändert werden?

Erwartete Änderungen:
- `app/ai/provider.py` → neue Provider-Klasse(n)
- `app/main_window.py` → `_build_ki()` neue UI-Felder (Base-URL, Modell-Dropdown)
- `config.py` → `DEFAULT_CONFIG["ai"]` neue Felder
- `requirements.txt` → neue Abhängigkeiten (z.B. `ollama`, kein für HTTP-only)

---

### 7. Verifikationsplan

Für jede Option: wie testen wir *vor* Einbau ob die Integration klappt?
Schreibe konkrete curl-Befehle oder Python-Snippets (< 10 Zeilen) die den Endpunkt testen.

Beispiel-Template:
```python
# Verifikation: LM Studio
import requests
r = requests.post("http://localhost:1234/v1/chat/completions",
    json={"model": "???", "messages": [{"role":"user","content":"Hallo"}], "max_tokens": 50})
print(r.json()["choices"][0]["message"]["content"])
```

---

## Output-Format

Erstelle eine Datei `ai_connect_plan.md` mit:
1. Ist-Analyse-Ergebnis (½ Seite)
2. Bewertungsmatrix (Tabelle)
3. Top-3-Ausformulierung
4. Implementierungsplan (Dateiliste + Änderungsumfang)
5. Verifikations-Snippets

**Schreibe keinen Code** in dieser Phase — nur Recherche, Analyse und Plan.
Der Plan wird dann in einer separaten Session umgesetzt.

---

## Hinweise für den recherchierenden Agenten

- Prüfe bei lokalen Optionen immer: Windows 11 ohne Admin-Rechte installierbar?
- Nutzer haben typisch: 8–16 GB RAM, keine dedizierte GPU (Intel/AMD iGPU)
- Der bestehende `_ChatCompletionsProvider` funktioniert für jeden OpenAI-kompatiblen Endpoint
  — lokale Lösungen die dieses Format sprechen brauchen **keine neue Klasse**, nur neue Config-Felder
- Priorität: was ein Kirchensekretariat ohne IT-Kenntnisse in < 30 Minuten einrichten kann
