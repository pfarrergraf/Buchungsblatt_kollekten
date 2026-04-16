# AI-Connect Plan

## 1. Ist-Analyse-Ergebnis

Die bestehende KI-Anbindung ist bewusst klein gehalten und funktioniert heute vor allem fuer OpenRouter. In `app/ai/provider.py` gibt es eine `AIProvider`-Abstraktion, einen `DisabledProvider`, eine wiederverwendbare `_ChatCompletionsProvider`-Basisklasse fuer OpenAI-kompatible Endpunkte sowie einen separaten `AnthropicProvider`. `OpenRouterProvider` und `OpenAIProvider` sind nur duenne Wrapper um `_ChatCompletionsProvider`; dadurch ist die Architektur schon nah an lokalen OpenAI-kompatiblen Servern wie LM Studio, Ollama und vLLM. Das Chat-Widget in `app/ai/chat_widget.py` arbeitet mit dem klassischen `messages`-Format (`system`, `user`, `assistant`) und reicht diese Liste unveraendert an den Provider weiter. Fuer OpenAI-kompatible Targets ist das passend.

Die eigentliche Luecke liegt nicht in der Chat-Logik, sondern in Konfiguration und UI. In `app/main_window.py` baut `EinstellungenTab._build_ki()` heute nur drei Felder: `provider`, `api_key` und `model`. In `config.py` existieren unter `DEFAULT_CONFIG["ai"]` ebenfalls nur `provider`, `api_key`, `model` und `openrouter_base_url`. Es gibt kein allgemeines `base_url`-Feld, keinen Schalter fuer lokale Server, keine Option fuer key-losen Betrieb und keine provider-spezifischen Hinweise. `_test_ai_connection()` testet OpenRouter sogar fest gegen `https://openrouter.ai/api/v1`, statt die konkrete Ziel-URL aus den Einstellungen zu verwenden.

Fuer lokale OpenAI-kompatible Loesungen ist das der Hauptblocker. `_ChatCompletionsProvider.is_available()` verlangt aktuell immer `api_key` und `model`; damit faellt ein typischer lokaler Betrieb ohne API-Key sofort durch. `_headers()` sendet immer `Authorization: Bearer ...`, obwohl lokale Targets auf `localhost` haeufig gar keine Authentifizierung nutzen. `get_provider()` kennt nur `disabled`, `openrouter`, `openai` und `anthropic`; LM Studio, Ollama und vLLM sind also weder als eigene Provider noch als generische OpenAI-kompatible Endpunkte konfigurierbar. Zusaetzlich ist die Fehlerbehandlung in `ChatWidget._on_error()` sprachlich stark auf OpenRouter zugeschnitten; fuer lokale Server waeren andere Hinweise sinnvoll, etwa "Server nicht gestartet", "Modell nicht geladen" oder "Base-URL falsch".

Kurz gesagt: Die bestehende Architektur reicht schon fuer die technische Anbindung mehrerer OpenAI-kompatibler Endpunkte, aber die App braucht eine allgemeinere KI-Konfiguration. Die groessten fehlenden Bausteine sind `base_url`, optionaler API-Key, bessere Provider-Auswahl fuer lokale Targets und ein Verbindungstest, der gegen den tatsaechlich konfigurierten Endpunkt prueft.

## 2. Bewertungsmatrix

Bewertungsskala: 1 bis 5 Punkte, 5 = best. Gesamtscore = gewichteter Mittelwert.

| Option | Einrichtungsaufwand 25% | Offline 20% | Datenschutz 20% | Kosten 15% | Antwortqualitaet 10% | Windows 10% | Gesamtscore |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Ollama | 5 | 5 | 5 | 5 | 4 | 5 | 4.9 |
| LM Studio | 5 | 5 | 5 | 5 | 4 | 5 | 4.9 |
| OpenAI direkt | 4 | 1 | 1 | 3 | 5 | 5 | 2.9 |
| Anthropic / Claude API | 3 | 1 | 1 | 2 | 5 | 5 | 2.6 |
| vLLM | 1 | 5 | 5 | 5 | 4 | 1 | 3.3 |
| Claude Code CLI als Proxy | 1 | 1 | 1 | 2 | 4 | 4 | 1.8 |

### Bewertungsnotizen

- Ollama und LM Studio liegen praktisch gleichauf. Ollama ist minimal einfacher fuer Endnutzer, LM Studio ist oft etwas einsteigerfreundlicher beim Modell-Management und beim lokalen OpenAI-kompatiblen Server.
- vLLM bekommt trotz starker Offline-/Datenschutz-Werte nur Platz 4, weil der Windows-Fit fuer dieses Projekt schwach ist. Laut offizieller Doku laeuft vLLM vollstaendig nur unter Linux; auf Windows ist WSL der realistische Weg.
- OpenAI direkt ist als Cloud-Fallback trotz Kosten auf Platz 3, weil es bereits fast im Code angelegt ist, die Qualitaet hoch ist und die Integration fuer die App am wenigsten Zusatzarbeit erzeugt.
- Anthropic faellt hinter OpenAI zurueck, weil das API-Format nicht zu eurer bestehenden OpenAI-kompatiblen Basisklasse passt und die Kosten fuer kurze Standard-Q&A typischerweise weniger attraktiv sind.
- Claude Code CLI ist keine gute Zieloption fuer diese App, weil die offizielle Doku keinen allgemeinen lokalen HTTP-Proxy fuer Modellaufrufe zeigt. Dokumentiert sind MCP- und Remote-Control-Szenarien, nicht ein `/v1/chat/completions`-Endpoint fuer Fremd-Apps.

## 3. Top-3-Ausformulierung

### Ollama
**Typ:** lokal

**Endpoint:** `http://localhost:11434/v1`

**Benoetigt:** Windows-Installation von Ollama, einmaliges Herunterladen eines Modells, z. B. kleine CPU-taugliche Modelle wie `smollm2:360m`, `qwen2.5:0.5b` oder `gemma3:1b`; fuer die App selbst ist kein API-Key noetig.

**Implementierung:** Kein vollstaendig neuer HTTP-Stack noetig. Am saubersten ist eine neue Option im Provider-Dropdown (`ollama`) plus allgemeine Felder `base_url` und optionaler `api_key`. Technisch kann Ollama entweder als eigene kleine Wrapper-Klasse auf `_ChatCompletionsProvider` basieren oder als generischer "OpenAI-kompatibel"-Provider konfiguriert werden. Zusaetzlich sollte `is_available()` lokale `localhost`-Endpoints ohne Key testen koennen.

**Verifikation:** Zuerst ohne echten Chat-Call `GET /api/tags` oder `GET /v1/models`, danach ein Mini-Call gegen `/v1/chat/completions` mit sehr kleinem `max_tokens`.

**Risiken / Einschraenkungen:** OpenAI-Kompatibilitaet ist laut offizieller Doku nur teilweise. Einige OpenAI-Felder oder Features koennen fehlen. Modellqualitaet haengt stark vom lokal geladenen Modell ab; auf typischen Office-PCs sind nur kleine Modelle realistisch.

### LM Studio
**Typ:** lokal

**Endpoint:** `http://localhost:1234/v1`

**Benoetigt:** Windows-Installation von LM Studio, Download eines passenden lokalen Modells, Start des lokalen Servers in der App oder per CLI; fuer lokale Nutzung ist in der Regel kein API-Key erforderlich.

**Implementierung:** Ebenfalls kein neuer HTTP-Stack. LM Studio ist explizit OpenAI-kompatibel; deshalb reicht dieselbe Generalisierung wie bei Ollama: `base_url`, optionaler `api_key`, besserer Connection-Test, lokaler Provider-Eintrag oder generischer OpenAI-kompatibler Modus. LM Studio ist besonders attraktiv, weil die bestehende `_ChatCompletionsProvider`-Basisklasse fast schon passt.

**Verifikation:** `GET /v1/models` gegen `http://localhost:1234/v1/models`, danach kurzer Test-Post gegen `/v1/chat/completions`.

**Risiken / Einschraenkungen:** Auch hier bestimmt das gewaehlte lokale Modell die Qualitaet. Fuer reine CPU-Office-PCs muessen sehr kleine oder stark quantisierte Modelle gewaehlt werden; gute UX braucht daher spaeter sinnvolle Modell-Empfehlungen in der UI oder Doku.

### OpenAI direkt
**Typ:** cloud

**Endpoint:** `https://api.openai.com/v1`

**Benoetigt:** OpenAI-API-Key und ein passendes Modell. Fuer kurze Q&A ist `gpt-4o-mini` der naheliegende Kosten-/Qualitaetsstartpunkt; OpenAI dokumentiert dafuer konkrete Tier-Rate-Limits. `gpt-5.4-mini` ist laut aktueller Modelldoku ebenfalls eine guenstige Low-Latency-Option, aber fuer euren vorhandenen Chat-Completions-Code ist `gpt-4o-mini` der konservativere Einstieg.

**Implementierung:** Fast keine strukturellen Aenderungen an der Provider-Logik selbst. Wichtig sind eher dieselben allgemeinen UI-Verbesserungen wie fuer lokale Targets: `base_url` zentralisieren, Verbindungstest korrigieren, bessere Statushinweise. Optional koennte die Standard-Modellempfehlung in der UI fuer OpenAI automatisch auf `gpt-4o-mini` gesetzt werden.

**Verifikation:** `GET /v1/models` mit Key oder kurzer Test-Call gegen `/v1/chat/completions` mit `gpt-4o-mini`.

**Risiken / Einschraenkungen:** Kein Offline-Betrieb, laufende Kosten, Datenschutz nicht lokal. Fuer kirchliche Verwaltungsdaten ist das nur dann passend, wenn Nutzung und Inhalte organisatorisch freigegeben sind.

## 4. Implementierungsplan

### Gemeinsame Basis fuer alle Top-3

- `app/ai/provider.py`
  - `_ChatCompletionsProvider` so erweitern, dass `api_key` optional sein kann.
  - `Authorization`-Header nur senden, wenn wirklich ein Key vorhanden ist.
  - `is_available()` fuer lokale OpenAI-kompatible Targets auch ohne Key erlauben.
  - `get_provider()` um lokale Optionen (`ollama`, `lmstudio`) oder alternativ einen generischen Provider-Typ wie `openai_compatible` erweitern.
  - OpenAI-Default-`base_url` nicht hart verdrahten, sondern aus Konfiguration lesen.

- `app/main_window.py`
  - In `_build_ki()` neue Felder einfuehren: `base_url`, optionaler `api_key`, evtl. ein Hilfe-Label mit Standardwerten pro Provider.
  - Provider-Dropdown um `Ollama` und `LM Studio` erweitern.
  - `Verbindung testen` so umbauen, dass immer die aktuell ausgewaehlte Provider-Konfiguration geprueft wird.
  - UI-Logik fuer lokale Provider: API-Key nicht erzwingen, Standard-URLs vorbelegen.

- `config.py`
  - `DEFAULT_CONFIG["ai"]` um allgemeine Felder erweitern, z. B. `base_url`, optional `local_mode`, evtl. provider-spezifische Defaults.
  - Bestehende Felder fuer Rueckwaertskompatibilitaet normalisieren, damit alte Konfigurationen nicht brechen.

- `app/ai/chat_widget.py`
  - Fehlertexte neutraler formulieren; nicht nur auf OpenRouter verweisen.
  - Bei lokalen Providern Hinweise wie "Server nicht gestartet" oder "kein Modell geladen" bevorzugen.

- `requirements.txt`
  - Fuer die reine HTTP-Anbindung der Top-3 ist voraussichtlich **keine neue Abhaengigkeit erforderlich**, weil `requests` ohnehin schon genutzt wird.
  - Optional: Falls spaeter eine native Ollama-Bibliothek bewusst genutzt werden soll, koennte `ollama` hinzukommen. Fuer die hier empfohlene HTTP-only-Strategie ist das nicht noetig.

### Spezifisch pro Top-3

#### Ollama
- `app/ai/provider.py`: entweder eigener `OllamaProvider` als schlanker Wrapper oder generische OpenAI-kompatible Konfiguration.
- `app/main_window.py`: Standard-`base_url` fuer Auswahl `ollama` auf `http://localhost:11434/v1` setzen.
- `config.py`: optional `ollama_base_url` nur dann, wenn ihr provider-spezifische Einzel-Felder statt eines allgemeinen `base_url` beibehalten wollt.

#### LM Studio
- `app/ai/provider.py`: gleicher Ansatz wie bei Ollama.
- `app/main_window.py`: Standard-`base_url` fuer Auswahl `lmstudio` auf `http://localhost:1234/v1` setzen.
- `config.py`: analog zu Ollama.

#### OpenAI direkt
- `app/ai/provider.py`: `OpenAIProvider` aus Konfiguration mit flexibler `base_url` initialisieren.
- `app/main_window.py`: sinnvolle Modell-Vorbelegung fuer OpenAI.
- `config.py`: allgemeines `base_url` statt nur `openrouter_base_url`.

## 5. Verifikations-Snippets

### Ollama

PowerShell:

```powershell
curl.exe http://localhost:11434/v1/models
```

Python:

```python
import requests
r = requests.post(
    "http://localhost:11434/v1/chat/completions",
    json={"model": "smollm2:360m", "messages": [{"role": "user", "content": "Hallo"}], "max_tokens": 30},
    timeout=20,
)
print(r.json()["choices"][0]["message"]["content"])
```

### LM Studio

PowerShell:

```powershell
curl.exe http://localhost:1234/v1/models
```

Python:

```python
import requests
r = requests.post(
    "http://localhost:1234/v1/chat/completions",
    json={"model": "qwen2.5-0.5b-instruct", "messages": [{"role": "user", "content": "Hallo"}], "max_tokens": 30},
    timeout=20,
)
print(r.json()["choices"][0]["message"]["content"])
```

Hinweis: Der Modellname muss zum lokal in LM Studio geladenen Modell passen.

### OpenAI direkt

PowerShell:

```powershell
curl.exe https://api.openai.com/v1/models -H "Authorization: Bearer $env:OPENAI_API_KEY"
```

Python:

```python
import os, requests
r = requests.post(
    "https://api.openai.com/v1/chat/completions",
    headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
    json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hallo"}], "max_tokens": 30},
    timeout=20,
)
print(r.json()["choices"][0]["message"]["content"])
```

### vLLM

PowerShell:

```powershell
curl.exe http://localhost:8000/v1/models
```

Python:

```python
import requests
r = requests.post(
    "http://localhost:8000/v1/chat/completions",
    json={"model": "Qwen/Qwen2.5-3B-Instruct", "messages": [{"role": "user", "content": "Hallo"}], "max_tokens": 30},
    timeout=20,
)
print(r.json()["choices"][0]["message"]["content"])
```

### Anthropic / Claude API

PowerShell:

```powershell
curl.exe https://api.anthropic.com/v1/models -H "x-api-key: $env:ANTHROPIC_API_KEY" -H "anthropic-version: 2023-06-01"
```

Python:

```python
import os, requests
r = requests.post(
    "https://api.anthropic.com/v1/messages",
    headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"},
    json={"model": "claude-3-5-haiku-latest", "max_tokens": 30, "messages": [{"role": "user", "content": "Hallo"}]},
    timeout=20,
)
print(r.json()["content"][0]["text"])
```

### Claude Code CLI

PowerShell:

```powershell
claude mcp serve
```

Hinweis: Das ist kein allgemeiner OpenAI-kompatibler HTTP-Test. Nach der offiziellen Doku ist Claude Code eher als MCP-/CLI-Werkzeug relevant, nicht als lokaler `/v1/chat/completions`-Proxy fuer Fremd-Apps.

## Quellen

- LM Studio App: https://lmstudio.ai/docs/app
- LM Studio OpenAI Compatibility: https://lmstudio.ai/docs/developer/openai-compat
- LM Studio Offline: https://lmstudio.ai/docs/app/offline
- LM Studio Server Settings: https://lmstudio.ai/docs/developer/core/server/settings
- Ollama Windows: https://docs.ollama.com/windows
- Ollama API: https://docs.ollama.com/api
- Ollama OpenAI Compatibility: https://docs.ollama.com/api/openai-compatibility
- Ollama Authentication: https://docs.ollama.com/api/authentication
- Ollama Library SmolLM2: https://ollama.com/library/smollm2:360m
- vLLM OpenAI-Compatible Server: https://docs.vllm.ai/en/latest/serving/openai_compatible_server/
- vLLM Installation: https://docs.vllm.ai/en/latest/getting_started/installation/
- vLLM Serve CLI: https://docs.vllm.ai/en/latest/cli/serve/
- OpenAI Chat Completions: https://platform.openai.com/docs/api-reference/chat/create-chat-completion
- OpenAI GPT-4o mini model page: https://developers.openai.com/api/docs/models/gpt-4o-mini
- OpenAI GPT-5.4 mini model page: https://developers.openai.com/api/docs/models/gpt-5.4-mini
- Anthropic Messages API: https://docs.anthropic.com/en/api/messages
- Anthropic OpenAI SDK compatibility: https://docs.anthropic.com/en/api/openai-sdk
- Anthropic model selection: https://docs.anthropic.com/en/docs/about-claude/models/choosing-a-model
- Anthropic model list: https://docs.anthropic.com/en/docs/about-claude/models/all-models
- Anthropic CLI/API docs: https://platform.claude.com/docs/en/api/sdks/cli
- Claude Code Remote Control docs: https://code.claude.com/docs/remote-control
- GitHub Beispiel `yjg30737/pyqt-openai`: https://github.com/yjg30737/pyqt-openai
- GitHub Beispiel `hyun-yang/MyChatGPT`: https://github.com/hyun-yang/MyChatGPT
- GitHub Beispiel `Lywald/MixAI`: https://github.com/Lywald/MixAI

## Kurz zur Subagent-Nutzung

Fuer diesen Plan wurden Subagents gezielt parallel eingesetzt: ein Agent fuer die lokale Ist-Analyse im Code, ein Agent fuer die Recherche der lokalen Optionen und ein Agent fuer Cloud-Optionen plus GitHub-Vorbilder. Der Effekt ist vor allem Zeitgewinn und saubere Aufgabentrennung; die eigentliche Bewertung und Endentscheidung wurden danach zentral zusammengefuehrt, damit der finale Plan konsistent bleibt.
