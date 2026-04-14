# Arbeitsanweisung für Claude Code

## Sofort ausführen (keine Rückfragen):

1. Installiere alle Requirements:
pip install -r requirements.txt

2. Erstelle alle Python-Dateien gemäß CLAUDE.md 3. Frage einmalig interaktiv: - Wo liegt die Excel-Vorlage? (Pfad) - Wo sollen die monatlichen Dateien gespeichert werden? - Speichere Antworten in `config.json` 4. Erstelle `scheduler_setup.py` das den Windows Task Scheduler mit `schtasks` einrichtet (alle 30 Min, beim Login starten) 5. Teste den Parser mit dieser Beispiel-E-Mail und zeige das Ergebnis:
Hallo, hier die Statistik zum Gottesdienst 2.04.2026 Quasimodogeniti: 43 22 Kinder-u. Jugendarbeit eigene Gemeinde, 231,00

6. Zeige am Ende eine Zusammenfassung was eingerichtet wurde. ## Nicht tun: - Keine GUI bauen - Kein Docker - Keine Cloud-Services - Nur lokales Windows + Outlook (win32com)