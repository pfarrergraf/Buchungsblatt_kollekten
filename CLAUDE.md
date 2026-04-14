# Kollekten-Automation: Outlook → Excel

## Ziel
Automatisch E-Mails von no-reply@ekhn.info aus Microsoft Outlook auslesen
und Kollektendaten in eine Excel-Datei eintragen (eine Datei pro Monat).

## Aufgabe
Richte eine vollständige Python-Automation ein, die:
1. Microsoft Outlook (lokal, via win32com) nach E-Mails von no-reply@ekhn.info durchsucht
2. E-Mails mit dem Muster "hier die Statistik zum Gottesdienst" erkennt
3. Datum, Betrag und Verwendungszweck extrahiert
4. Eine monatliche Excel-Datei befüllt (Vorlage: siehe unten)
5. Als Windows-Task-Scheduler-Job alle 30 Minuten läuft

## E-Mail-Format (Beispiel)
Hallo,
hier die Statistik zum Gottesdienst 22.03.26. Judika:
28
8
Stiftung für das Leben. 99,70
Dies ist eine automatisch erstellte E-Mail von https://termine.ekhn.de. Bitte antworten Sie nur an die angegebene Antwort-Adresse: kirchengemeinde.oberlahnstein@ekhn.de 
Verantwortlich für den Versand dieser E-Mails ist: Ev. Kirchengemeinde 

## Zu extrahierende Felder - **Datum**: aus der Zeile "hier die Statistik zum Gottesdienst DD.MM.YY ..." - **Betrag**: letzte Zeile, Zahl nach dem Komma (z.B. "231,00" → 231.00) - **Verwendungszweck**: letzte Zeile, Text vor dem Komma ## Excel-Spalten (Sheet: "eigene Gemeinde") - **Spalte A** (Betrag): numerisch, Format € - **Spalte F** (Kollekte vom): Datum DD.MM.YYYY - **Spalte H** (Verwendungszweck): Text - Daten starten ab Zeile 17, eine Zeile pro Eintrag - Spalte B (AObj) und D (Sachkonto): leer lassen ## Excel-Vorlage Die Vorlagendatei heißt: `12 RV RLW - KGM Buchungsblatt Kollekten und Spenden eigene Gemeinde 2026 V3.0.xlsx` Für jeden Monat wird eine Kopie erstellt: `Kollekten_YYYY_MM.xlsx` ## Wichtige Hinweise - Bereits verarbeitete E-Mails in `processed_emails.json` speichern (per EntryID) - Keine E-Mail doppelt verarbeiten - Datumsformate berücksichtigen: "02.04.26" und "02.04.2026" beide parsen - Deutsche Dezimalzahlen: "231,00" → float 231.00 - Fehler in `kollekten.log` loggen ## Setup-Schritte (führe alle aus) 1. `requirements.txt` erstellen und installieren 2. `pyproject.toml` erstellen 3. `config.py` mit Pfaden erstellen (interaktiv nach Vorlagenpfad fragen) 4. `parser.py` – E-Mail-Parser 5. `excel_writer.py` – Excel-Schreiber (openpyxl) 6. `outlook_reader.py` – Outlook-Anbindung (win32com) 7. `main.py` – Hauptskript 8. `scheduler_setup.py` – Windows Task Scheduler einrichten 9. Alles testen mit einer Beispiel-E-Mail