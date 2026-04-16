# KI-Roadmap zur EKHN-Sekretariatssoftware

## Kurzfazit

Die bestehende App hat bereits eine gute Ausgangsbasis: lokale Daten, bestehende Aktionen, PWA/API und erste Tool-Use-Unterstützung in [`app/ai/tools.py`](C:/ai/Buchungsblatt_kollekten/app/ai/tools.py) sowie [`app/ai/chat_widget.py`](C:/ai/Buchungsblatt_kollekten/app/ai/chat_widget.py). Der nächste große Hebel ist nicht nur "mehr Chat", sondern eine saubere Agenten-Architektur mit drei Schichten:

1. sichere interne App-Tools für Lesen, Vorschlagen, Bestätigen, Ausführen
2. EKHN-/Kirchenrechts-Zugriff mit Quellen, Zitaten und Aktualitätsprüfung
3. Web-/Intranet-/Formular-Automation für alles, was keine offizielle API hat

Wenn ihr die App schrittweise zu einer echten Sekretariatssoftware für EKHN-Gemeindebüros ausbauen wollt, ist die strategisch beste Richtung:

- die App selbst als MCP-Server und als Actions-API verfügbar machen
- eine fachliche Wissensschicht für EKHN, Kirchenrecht, Formulare und Regionalverwaltungen aufbauen
- dann pro Prozessfamilie konkrete, bestätigungspflichtige Assistenten-Workflows ergänzen

---

## Was im Repo schon vorhanden ist

- KI-Provider-Abstraktion für OpenAI-kompatible Ziele und Anthropic in [`app/ai/provider.py`](C:/ai/Buchungsblatt_kollekten/app/ai/provider.py)
- Tool-Use mit Lese- und Aktions-Tools in [`app/ai/tools.py`](C:/ai/Buchungsblatt_kollekten/app/ai/tools.py)
- Nutzerbestätigung vor aktiven Schritten in [`app/ai/chat_widget.py`](C:/ai/Buchungsblatt_kollekten/app/ai/chat_widget.py)
- API/PWA-Basis über FastAPI in [`app/api`](C:/ai/Buchungsblatt_kollekten/app/api)
- Lauf-Auslösung per HTTP bereits vorhanden in [`app/api/routes/actions.py`](C:/ai/Buchungsblatt_kollekten/app/api/routes/actions.py)

Das ist wichtig, weil ihr nicht bei null startet. Die App ist schon nah an einem "action-oriented copilot", aber noch nicht an einem vollwertigen, quellengebundenen Sekretariatsagenten.

---

## Recherchestand EKHN und Rechtsquellen

### Handbuch Gemeindebüro

Eure lokale PDF-Datei `data/Handbuch Gemeindebüro Prozesse_Gesamt_2019_screen.pdf` ist nach heutigem Stand fachlich veraltet.

Die neueste öffentlich nachweisbare Quelle ist:

- EKHN-Artikel "Handbuch für Gemeindebüros überarbeitet", veröffentlicht am **04.12.2025**
- dort steht ausdrücklich, dass das Handbuch **im Intranet der EKHN vorgehalten und regelmäßig aktualisiert** wird
- neu genannt werden Stand Dezember 2025 u. a.:
  - Ausschreibung von Pfarrstellen im NBR
  - Dokumentenmanagementsystem (DMS) Digitale Aktenführung
  - Förderung der Chancengleichheit aller Mitarbeitenden
  - Geschenke
  - Kommunaler Abgabenbescheid – Grundsteuer
  - Zusammenlegung der Verwaltungen im Nachbarschaftsraum

Folgerung:

- die 2019er PDF sollte nur noch als Startkorpus gelten
- die KI muss eine **laufend aktualisierbare Wissensquelle** für das EKHN-Intranet bekommen
- für intern/VPN-gebundene Inhalte braucht ihr einen separaten Connector oder Browser-Agent mit Nutzerkonto

### Kirchenrecht

`kirchenrecht-ekhn.de` ist die richtige Hauptquelle für rechtliche Aussagen.

Für die Kollekten-Themen sind mindestens relevant:

- aktuelle **Kollektenverwaltungsordnung (KollVO)**
- aktuelle **Kollektenordnung**
- aktuelle **Kirchengemeindeordnung**
- ggf. Amtsblatt-Ausgaben und Synodaldrucksachen bei Änderungen

Besonders wichtig:

- die KollVO benennt Kollektenbeauftragte und Zuständigkeiten
- die neuere Kollektenordnung ist über Synodaldrucksachen und PDF-Versionen nachweisbar
- das Kirchenrechtsportal selbst zeigt laufende Aktualisierungen; die Übersichts-PDF "Das Recht der EKHN" hat Stand Anfang 2026

### EKHN-Digitalisierung / Systeme / Support

Öffentlich und halb-öffentlich auffindbar sind bereits wichtige Zielsysteme:

- **Kiris** ersetzt laut EKHN-Mitteilung seit Oktober 2025 das bisherige KirA
- **DMS / E-Akte** wird mit enaio schrittweise eingeführt
- auf `hilfe.ekhn.de` werden Supportwege, Fachverfahren und Anträge für Intranet, MACH, Kiris, DMS / E-Akte und Kita-Büro zentral gebündelt
- die Seite nennt auch VPN-gebundene Formulare und Supportwege
- die EKHN-Seite zu Regionalverwaltungen listet Aufgabenfelder und ist eine gute Grundlage für Routing-Logik

Folgerung:

- eure App sollte nicht nur "Kollekten" kennen, sondern mittelfristig die Prozesslandschaft **Kiris + MACH + DMS + Regionalverwaltung + Formulare + Kirchenrecht** abbilden

---

## Leitprinzipien für die Architektur

### 1. Nicht nur Chat, sondern Assistenz mit Zustandsmodell

Die KI sollte nicht frei "irgendwas tun", sondern immer entlang eines klaren Schemas arbeiten:

1. Anliegen erkennen
2. Datenquellen bestimmen
3. Entwurf / Vorschlag erzeugen
4. Nutzer bestätigen lassen
5. Aktion ausführen
6. Ergebnis dokumentieren
7. Quellen, Fristen und Folgeaufgaben speichern

### 2. Jede Fähigkeit als Tool, nicht als versteckter Prompt-Trick

Was die KI zuverlässig tun soll, braucht ein echtes Tool:

- Daten lesen
- Formulare herunterladen
- Kontakte und Regionalverwaltung finden
- Dokumente erzeugen
- Entwürfe per Outlook/E-Mail vorbereiten
- Fristen setzen
- Aktennotizen speichern
- Webformulare ausfüllen

### 3. Rechtliches immer mit Quellen + Warnhinweis

Die App darf rechtlich unterstützen, aber nie als verbindliche Rechtsberatung auftreten.

Empfohlene Standardformulierung:

`Hinweis: Dies ist keine verbindliche Rechtsberatung. Maßgeblich sind die jeweils aktuelle Fassung des Kirchenrechts der EKHN, die einschlägigen Ausführungsbestimmungen sowie im Zweifel die zuständige Regionalverwaltung oder der Stabsbereich Recht.`

Zusätzlich sollte die KI bei rechtlichen Antworten immer:

- konkrete Quelle nennen
- Datum / Stand nennen
- wenn möglich Paragraph oder Dokumenttitel angeben
- zwischen "geltendem Recht", "Verfahrenshinweis", "organisatorischer Empfehlung" unterscheiden

### 4. Erst native Schnittstelle, dann Web-Automation

Reihenfolge pro Integrationsziel:

1. offizielle API
2. strukturierter Download / Formularlink / PDF
3. MCP-Connector
4. Browser-/Computer-Use-Automation

Web-Automation ist wichtig, aber nicht euer Default.

---

## Große Liste möglicher Implementierungen

## A. Agenten-Grundlage und sichere Bedienbarkeit

### A1. Eigene App-Tools massiv ausbauen

Ergänzt zu den bestehenden Tools mindestens:

- `create_kollektenblatt(monat, jahr, scope)`
- `preview_kollektenblatt(monat, jahr, scope)`
- `list_output_files(monat, jahr)`
- `send_email_draft(recipients, subject, body, attachments)`
- `save_note(entity_type, entity_id, note)`
- `list_pending_tasks()`
- `create_follow_up(date, reason, related_entity)`
- `get_recent_errors()`
- `get_templates_status()`
- `search_documents(query, tags, date_range)`

Nutzen:

- weniger Halluzination
- sauberer Audit-Trail
- gute Grundlage für externe Agenten über MCP

### A2. Bestätigungsstufen einführen

Nicht nur "Bestätigen ja/nein", sondern Sicherheitsklassen:

- `read_only`
- `draft_only`
- `user_confirmed_send`
- `user_confirmed_write`
- `admin_only`

Beispiel:

- "Kollektenblätter für März 2026 erstellen" = `user_confirmed_write`
- "Mail versenden" = `user_confirmed_send`
- "Nur Entwurf erzeugen" = `draft_only`

### A3. Rollenmodell

Rollen wie:

- Gemeindesekretariat
- Pfarrteam
- Kirchenvorstand
- Regionalverwaltung
- IT/Admin

Damit könnt ihr später Tool-Sichtbarkeit und Freigaben steuern.

### A4. Erinnerbarer Gesprächskontext

Die KI soll Dinge dauerhaft lernen dürfen, aber nur in klaren Speichern:

- Stammdaten der Gemeinde
- bevorzugte Empfänger
- wiederkehrende Formulierungen
- Zuständigkeiten
- übliche Versandtage
- bevorzugte regionale Kontakte

Keine freie "Blackbox-Memory", sondern reviewbare, editierbare Einträge.

---

## B. MCP, externe Agenten und offene Integrationen

### B1. Die App als eigener MCP-Server

Das ist eine der wichtigsten Maßnahmen überhaupt.

Warum:

- Claude Code, ChatGPT, Codex, Cursor und andere MCP-fähige Clients könnten eure App direkt bedienen
- ihr entkoppelt "welches Modell" von "welche Gemeindesoftware-Funktion"
- Claude Code arbeitet laut deiner Beschreibung bereits daran; das passt perfekt zu dieser Richtung

MCP-Tools könnten sein:

- Buchungen lesen
- Monatszusammenfassung abrufen
- Kollektenblätter erstellen
- E-Mail-Entwürfe vorbereiten
- Dokumente suchen
- Fristen lesen/anlegen
- Regionalverwaltung suchen
- Rechtsquellen abrufen

Technisch empfehlenswert:

- lokaler STDIO-MCP-Server für Desktop-Nutzung
- optional Remote-MCP-Server über eure FastAPI/PWA-Schicht

### B2. MCP-Ressourcen statt nur Tools

Neben Tools auch Resources anbieten:

- Gemeindestammdaten
- aktueller Konfigurationsstand
- Vorlagenstatus
- Rechtssammlungen
- Prozesshandbücher
- Formularverzeichnis
- offene Aufgaben

### B3. Connector-/MCP-Gateway für EKHN-Quellen

Separater MCP-Server für:

- Kirchenrecht EKHN
- EKHN Hilfe
- Regionalverwaltungen
- Formularverzeichnis
- WissensWerte / Schulungslinks
- ggf. EKHN-intern via Nutzerbrowser / VPN

Das ist oft sauberer als alles direkt in die Desktop-App zu pressen.

### B4. ChatGPT-/OpenAI-Connector-Fähigkeit vorbereiten

Die OpenAI-Doku unterstützt heute MCP und Connectors im Responses API-Ökosystem. Damit könnt ihr später:

- eure App als Remote-MCP-Server bereitstellen
- rechtliche und organisatorische Datenquellen als eigene MCP-Server anbinden
- Deep-Research-Modelle gezielt auf eure Quellen loslassen

---

## C. Wissensschicht EKHN / Kirchenrecht / Formulare

### C1. Rechtskorpus mit Zitaten und Fundstellen

Baut einen rechtlichen Korpus aus:

- Kirchenrecht EKHN
- Amtsblatt
- Synodaldrucksachen
- Verordnungen
- Verwaltungsverordnungen
- Handreichungen mit Rechtsbezug

Antwortformat der KI:

- Kurzantwort
- Grundlage / Quelle
- Stand
- ggf. nächster Verfahrensschritt
- Standard-Hinweis "keine verbindliche Rechtsberatung"

### C2. Prozesskorpus Gemeindebüro

Quellen:

- lokales 2019-Handbuch
- aktuelles Intranet-Handbuch, sobald ihr Zugriff technisch eingebunden habt
- Prozess-PDFs und Arbeitshilfen
- DMS-/Kiris-/MACH-Anleitungen
- Regionalverwaltungs-Downloads

### C3. Formular- und Download-Katalog

Sehr sinnvoll wäre eine zentrale Tabelle / Index mit:

- Formularname
- Quelle/URL
- zuständige Stelle
- erforderliche Anhänge
- ob VPN nötig ist
- ob Login nötig ist
- Gültigkeitsstand
- letzte erfolgreiche Verwendung

So kann die KI bei Fragen wie "Welches Formular brauche ich für X?" direkt antworten und auf Wunsch den Entwurf vorbereiten.

### C4. Kontakt- und Zuständigkeitsgraph

Eigenes Verzeichnis:

- Regionalverwaltung
- Fachabteilungen
- meldewesen@ekhn.de
- Helpdesk
- Zuständige Pfarrpersonen
- Nachbarschaftsraumkontakte
- DMS/Kiris/MACH-Support

Mit Logik:

- Thema erkennen
- richtige Stelle vorschlagen
- Kontaktdaten ziehen
- E-Mail-Entwurf vorbereiten

### C5. Quellenbewertung

Priorisierung für Antworten:

1. Kirchenrecht EKHN
2. aktuelle EKHN-Hauptseiten
3. EKHN Hilfe / Supportseiten
4. Regionalverwaltungen
5. interne Dokumente
6. lokale ältere PDFs

Wenn eine Quelle älter ist als eine andere, muss die KI das offen sagen.

---

## D. Prozessautomation für das Gemeindesekretariat

### D1. Kollekten-Workflows vervollständigen

Sehr naheliegende Ausbaustufen:

- Monatsabschluss automatisch erkennen
- fehlende Kollekten markieren
- Plausibilitätsprüfung auf Summen, Doppelungen, Datumslücken
- Entwürfe für "eigene Gemeinde" und "Weiterleitung" getrennt erzeugen
- Versandvorschläge mit Empfängerauswahl
- Erinnerungen bei nicht versandten Monatsunterlagen

### D2. Eingangspost und E-Mails

KI-gestützte Funktionen:

- E-Mail-Klassifikation nach Vorgang
- Aktenzeichen / Frist / Kontakt extrahieren
- Vorschlag: beantworten, weiterleiten, ablegen, Aufgabe erzeugen
- Dubletten erkennen
- Wiedervorlagen erzeugen

### D3. Amtshandlungsnahe Büroprozesse

Ohne fachlich heikle Kernsysteme unkontrolliert zu schreiben, kann die KI helfen bei:

- Taufe: Unterlagen, Checklisten, Rückfragen, Terminvorbereitung
- Trauung: Unterlagencheck, Korrespondenz, Raum-/Terminabstimmung
- Bestattung: organisatorische Checklisten, Ansprechpartner, Dokumentenstatus
- Konfirmation: Listen, Elternkommunikation, Fristen, Materialanforderungen
- Eintritt/Wiederaufnahme: Unterlagenpfad und Kontaktweg

### D4. Gremien- und Sitzungshilfe

Sehr wertvoll für Sekretariate:

- Tagesordnungsentwürfe
- Beschlussvorlagen
- Serien-E-Mails an Gremien
- Aufgaben aus Protokollen extrahieren
- Beschlüsse mit Fristen verknüpfen
- Wiedervorlagen je Sitzung

### D5. Personal- und Verwaltungsassistenz

Mögliche Module:

- Urlaubs- und Abwesenheitsübersicht
- Stellenausschreibungs-Checklisten
- Einarbeitungslisten
- Kontaktmatrix Mitarbeitende
- Geschenk- und Jubiläumsprozesse
- Fortbildungsfristen

### D6. Immobilien, Bau, Grundsteuer

Weil das Handbuch 2025 diese Themen explizit erweitert:

- Grundsteuer-Bescheide erfassen
- Bauunterhaltungs-Vorgänge strukturieren
- regionale Zuständigkeit vorschlagen
- notwendige Unterlagenliste erzeugen
- Wiedervorlage und Statusübersicht

---

## E. Dokumente, Formulare und Akten

### E1. Dokumentenerzeugung mit Templates

Vorlagen für:

- Begleitschreiben
- Rückfragen an Regionalverwaltung
- Anschreiben an Gemeindeglieder
- interne Notizen
- Aktenvermerke
- Serienbriefe
- Beschlussentwürfe

### E2. Formular-Vorbefüllung

Die KI soll nicht nur sagen, welches Formular nötig ist, sondern:

- passende Vorlage finden
- Stammdaten eintragen
- bekannte Kontaktdaten vorschlagen
- fehlende Pflichtfelder markieren
- Entwurf als PDF/DOCX/XLSX ablegen

### E3. Dokumentenklassifikation und Ablagevorschläge

Für eingehende PDFs/Scans:

- Dokumenttyp erkennen
- Gemeinde / Person / Thema zuordnen
- sensible Daten erkennen
- Ablageort vorschlagen
- Metadaten erzeugen

### E4. DMS-/E-Akte-Vorbereitung

Wenn DMS / enaio eingeführt wird, braucht ihr früh eine neutrale Zwischenschicht:

- lokales Dokumentenregister
- Export-Metadaten
- spätere DMS-Connectoren

So bleibt die App nützlich, auch bevor eine echte DMS-Schreibschnittstelle da ist.

---

## F. Web-, Portal- und Intranet-Automation

### F1. Browser-Automation für EKHN-intern

Weil viele Dinge hinter VPN/Formularen/Portalen liegen, ist Browser-Automation mittelfristig unvermeidlich.

Einsatzfälle:

- Formulare öffnen
- Support-Anträge vorbereiten
- Downloads abholen
- Anleitungen suchen
- Statusseiten öffnen

Wichtig:

- nur nach Nutzerfreigabe
- wenn möglich mit Accessibility-/DOM-basierten Tools statt reinem Screenshot-Klicken

### F2. Sichere Browser-Sessions mit Profilen

Die KI sollte Login-Zustände nicht improvisieren.

Besser:

- dediziertes Browserprofil
- explizite Zustimmung bei Login-geschützten Schritten
- Sitzungen zeitlich begrenzen
- gespeicherte Sessions nur lokal und verschlüsselt

### F3. Download-Watcher

Wenn Browser-Automation Dateien herunterlädt:

- Datei automatisch erkennen
- klassifizieren
- Vorschau erzeugen
- Ablage vorschlagen
- Folgeaktion anbieten

---

## G. Rechtlicher Assistent mit belastbarer UX

### G1. "Rechtsauskunft" als eigener Modus

Die KI soll erkennen, wenn eine Anfrage eher juristisch ist, und dann den Modus wechseln:

- strengere Quellenpflicht
- Stand-Datum anzeigen
- Zitat / Paragraph bevorzugen
- Handlungsempfehlung vorsichtiger formulieren

### G2. Konflikt- und Unsicherheitslogik

Wenn mehrere Quellen nicht klar zusammenpassen:

- Konflikt markieren
- aktuelle und ältere Quelle gegenüberstellen
- an Regionalverwaltung / Stabsbereich Recht eskalieren

### G3. Prozess + Recht zusammenführen

Beispiel:

"Dürfen wir die Kollekte X so verwenden?"

Antwort der KI sollte sein:

- rechtliche Kurzbewertung
- Fundstelle
- organisatorischer Prüfpfad
- ggf. zuständige Stelle
- E-Mail-Entwurf für Rückfrage

Das ist viel nützlicher als reine Paragraphenwiedergabe.

---

## H. Suche, RAG und lokale Modelle

### H1. Hybride Suche

Empfohlene Architektur:

- BM25 / Schlüsselwortsuche
- Embedding-Suche
- Reranker
- Quellenzitate

Gerade für Kirchenrecht und Prozesshandbücher ist hybrid fast immer besser als "nur Vektor".

### H2. Dokumentsegmentierung

Chunks nicht nur nach Zeichen, sondern entlang von:

- Paragraphen
- Abschnittsüberschriften
- Formularfeldern
- Prozessschritten
- Seitenmetadaten

### H3. Antwort mit Belegstellen

Jede wissensbasierte Antwort sollte idealerweise enthalten:

- Antwort
- Quellenliste
- konkrete Fundstellen
- Stand / Abrufdatum
- Vertrauensgrad

### H4. Lokale und Cloud-Modelle trennen

Pragmatisches Modellkonzept:

- lokal für Klassifikation, Routing, einfache Extraktion
- Cloud für komplexes Reasoning, Rechtszusammenfassung, Multi-Step-Recherche
- sensible Daten optional nur lokal

### H5. Modellrouter

Ein Router entscheidet:

- kleine Aufgabe -> lokales / günstiges Modell
- rechtlich heikle Frage -> stärkeres Modell + Quellenpflicht
- Web-Recherche -> Such-/Deep-Research-Modell
- Formular-Extraktion -> Dokumentmodell

---

## I. Modelle, Libraries und Open-Source-Bausteine

## I1. Dokumentverarbeitung

### Docling

Sehr spannend für euch als Open-Source-Baustein:

- PDF, DOCX, XLSX, HTML und weitere Dokumente
- Fokus auf strukturierte Dokumentrepräsentation für GenAI
- gute Passung für Handbücher, Formulare, Rundschreiben, Scans

Mögliche Einsätze:

- EKHN-Handbücher in strukturierte Kapitel zerlegen
- Formulare in Felder / Abschnitte zerlegen
- Tabellen aus Verwaltungsdokumenten extrahieren

### LayoutLMv3

Sinnvoll für:

- Formularverständnis
- Dokumentlayout-Erkennung
- visuelle Fragen zu Scans

### Donut / DocVQA

Sinnvoll für:

- OCR-arme oder OCR-freie Frage-Antwort auf Formularbildern
- "Welche IBAN steht auf diesem eingescannten Formular?"

## I2. Retrieval und Ranking

### BGE-M3

Starke Option für:

- mehrsprachige Embeddings
- hybride Retrieval-Pipelines
- längere Dokumente

### bge-reranker-v2-m3

Gute Option für:

- multilinguales Reranking
- schnelle, lokal betreibbare Relevanzsortierung

### jina-reranker-v2-base-multilingual

Interessant für:

- mehrsprachiges Reranking
- längere Texte

Achtung:

- laut Modellkarte nicht automatisch frei für jeden kommerziellen Einsatz; Lizenz vor Einsatz prüfen

## I3. German Legal NLP

### flair/ner-german-legal

Nützlich für:

- Gesetzesverweise erkennen
- Institutionen / Verordnungen / Gerichte markieren
- Vorverarbeitung rechtlicher Texte

Nicht ausreichend allein für Rechtsauskunft, aber hilfreich als Extraktionsbaustein.

## I4. Browser- und Agenten-Tooling

### Playwright MCP

Stark für:

- deterministische Web-Automation
- strukturierte DOM-/Accessibility-basierte Bedienung
- gute Passung für Portale und Formulare

### browser-use

Interessant für:

- agentische Browser-Aufgaben
- Login-lastige Workflows
- Kombination mit eigenen Tools

Aber:

- operativ riskanter als Playwright für verlässliche Verwaltungsprozesse
- eher für "flexible Assistentenfälle" als für kritische Kernflows

## I5. MCP-Frameworks

### FastMCP

Sehr gute Option, um eure App-Funktionen als MCP-Server nach außen zu geben:

- schnell in Python
- passt gut zur bestehenden App
- produktionsnahe Patterns

---

## J. Konkrete Produktideen für die nächsten Ausbaustufen

## J1. Schnell nutzbar in 2 bis 4 Wochen

- Monatsworkflow für Kollekten komplett per Chat bedienbar
- Versand nur nach expliziter Bestätigung
- Quellengebundene Rechtsantworten nur für Kollektenrecht
- Formular- und Kontaktfinder für EKHN / Regionalverwaltung
- Dokumentensuche über vorhandene lokale Dateien
- gespeicherte Standardempfänger und Freigabemuster

## J2. Sehr wertvoll in 1 bis 3 Monaten

- eigener MCP-Server
- Rechts-/Prozess-RAG mit Zitation
- Formularregister mit Vorbefüllung
- Aufgaben- und Wiedervorlagenassistent
- Outlook-Mailbox-Klassifikation mit Ablagevorschlägen
- Regionalverwaltungs-Routing

## J3. Transformativ in 3 bis 9 Monaten

- Browser-Automation für EKHN-intern
- DMS-/E-Akte-Vorstufe mit Metadaten
- Assistenz für Amtshandlungsprozesse
- Protokoll- und Gremienassistenz
- standortübergreifendes Nachbarschaftsraum-Sekretariat
- organisationsweites Wissensnetz für mehrere Gemeinden

---

## Empfohlene Roadmap nach Priorität

## Phase 1: Sofort umsetzbar

- interne Tool-Landschaft erweitern
- Bestätigungsstufen einführen
- Rechts-Hinweis und Zitationspflicht in die KI-Antwortlogik einbauen
- Kollekten-Workflow Ende-zu-Ende chatfähig machen
- Formular-/Kontaktindex als lokale Datenstruktur anlegen

## Phase 2: Wissenszugriff professionalisieren

- Kirchenrecht-EKHN-Crawler/Indexer
- EKHN-Hilfe-Indexer
- Regionalverwaltungsverzeichnis
- Dokument- und Prozesskorpus
- hybride Suche mit Quellen

## Phase 3: Interoperabilität

- MCP-Server für eure App
- Remote-MCP oder API-Gateway
- Anbindung externer Assistenten

## Phase 4: Portale und Automation

- Playwright-basierte Portalautomation
- Download- und Formular-Pipeline
- Browserprofil- und Loginverwaltung

## Phase 5: Vollwertige Sekretariatssoftware

- Aufgaben/Wiedervorlagen
- DMS-/Akte-Modell
- Prozessmodule für Amtshandlungen, Gremien, Immobilien, Personal

---

## Meine konkrete Empfehlung

Wenn ihr nicht verzetteln wollt, würde ich die nächsten Schritte genau so schneiden:

1. **Kollekten-Agent sauber abschließen**
   - "Erstelle März 2026"
   - Vorschau
   - Bestätigung
   - Erzeugung
   - Versandentwurf
   - Versand

2. **Quellengebundene EKHN-/Kirchenrechtsauskunft hinzufügen**
   - mit Zitaten, Standdatum und Warnhinweis
   - zunächst nur auf Kirchenrecht EKHN + Handbuch + EKHN Hilfe

3. **Formular-/Kontaktfinder bauen**
   - Regionalverwaltung
   - Support
   - Formulare
   - VPN-Hinweise

4. **Die App als MCP-Server veröffentlichen**
   - damit Claude Code, ChatGPT oder andere Assistenten eure Software zuverlässig bedienen können

5. **Danach erst Browser-Automation**
   - gezielt für EKHN-intern und Formulare ohne offizielle Schnittstelle

---

## Offene Risiken

- EKHN-intern und VPN-gebundene Inhalte sind ohne Zugang technisch nicht vollständig crawlbar
- rechtliche Aussagen ohne Stand-/Quellenlogik wären zu riskant
- Browser-Automation ist fragiler als API-/MCP-Zugriffe
- Formularlandschaften ändern sich; ihr braucht ein Änderungsmonitoring
- Datenschutz und Rollenrechte müssen früh mitgedacht werden

---

## Quellen

### Repo

- [`app/ai/provider.py`](C:/ai/Buchungsblatt_kollekten/app/ai/provider.py)
- [`app/ai/tools.py`](C:/ai/Buchungsblatt_kollekten/app/ai/tools.py)
- [`app/ai/chat_widget.py`](C:/ai/Buchungsblatt_kollekten/app/ai/chat_widget.py)
- [`app/api/routes/actions.py`](C:/ai/Buchungsblatt_kollekten/app/api/routes/actions.py)
- [`data/Handbuch Gemeindebüro Prozesse_Gesamt_2019_screen.pdf`](C:/ai/Buchungsblatt_kollekten/data/Handbuch%20Gemeindeb%C3%BCro%20Prozesse_Gesamt_2019_screen.pdf)

### EKHN / Kirchenrecht

- EKHN: Handbuch für Gemeindebüros überarbeitet  
  https://www.ekhn.de/themen/kirchenverwaltung/infos/handbuch-fuer-gemeindebueros-ueberarbeitet

- EKHN Hilfe  
  https://hilfe.ekhn.de/

- EKHN: Regionalverwaltungen in der EKHN  
  https://www.ekhn.de/einrichtungen/regionalverwaltungen

- EKHN: EKHN führt Dokumentenmanagementsystem ein  
  https://www.ekhn.de/themen/kirchenverwaltung/infos/ekhn-fuehrt-dokumentenmanagementsystem-ein

- EKHN: Kiris kommt: Meldewesen wird ab Oktober 2025 umgestellt  
  https://www.ekhn.de/themen/kirchenverwaltung/infos/kiris-kommt-meldewesen-wird-ab-oktober-umgestellt

- Kirchenrecht EKHN: Kollektenverwaltungsordnung  
  https://www.kirchenrecht-ekhn.de/document/19041

- Kirchenrecht EKHN: Kollektenordnung / Synodaldrucksache-PDF  
  https://www.kirchenrecht-ekhn.de/synodalds/37449.pdf

- Kirchenrecht EKHN: Aktuelles  
  https://www.kirchenrecht-ekhn.de/document/aktuelles

- Kirchenrecht EKHN: Das Recht der EKHN  
  https://www.kirchenrecht-ekhn.de/pdf/19916.pdf

### Offizielle / technische Doku

- OpenAI Responses API  
  https://platform.openai.com/docs/api-reference/responses

- OpenAI MCP and Connectors  
  https://developers.openai.com/api/docs/guides/tools-connectors-mcp

- OpenAI File Search  
  https://developers.openai.com/api/docs/guides/tools-file-search

- OpenAI computer-use-preview  
  https://developers.openai.com/api/docs/models/computer-use-preview

- OpenAI text-embedding-3-large  
  https://developers.openai.com/api/docs/models/text-embedding-3-large

- OpenAI text-embedding-3-small  
  https://developers.openai.com/api/docs/models/text-embedding-3-small

- MCP Architecture  
  https://modelcontextprotocol.io/docs/learn/architecture

- FastMCP  
  https://gofastmcp.com/getting-started/welcome

### GitHub / Hugging Face

- Docling  
  https://github.com/docling-project/docling

- Microsoft Playwright MCP  
  https://github.com/microsoft/playwright-mcp

- browser-use  
  https://github.com/browser-use/browser-use

- Witsy  
  https://github.com/Kochava-Studios/witsy

- MyChatGPT  
  https://github.com/hyun-yang/MyChatGPT

- BGE-M3  
  https://huggingface.co/BAAI/bge-m3

- BGE Reranker v2 M3  
  https://huggingface.co/BAAI/bge-reranker-v2-m3

- Jina Reranker v2 multilingual  
  https://huggingface.co/jinaai/jina-reranker-v2-base-multilingual

- LayoutLMv3  
  https://huggingface.co/microsoft/layoutlmv3-base

- Donut DocVQA  
  https://huggingface.co/naver-clova-ix/donut-base-finetuned-docvqa

- Flair German Legal NER  
  https://huggingface.co/flair/ner-german-legal
