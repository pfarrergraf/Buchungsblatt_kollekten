documents_plan.md — Ausbauplan für Buchungsblätter, Verlauf, Rerun und Dokumente
Zielbild
Die App soll sich im Arbeitsalltag eines Sekretariats um die tatsächlich relevanten Objekte drehen: die erzeugten Buchungsblätter im xlsx-Format, deren Herkunft aus Outlook-E-Mails und die dafür nötigen Arbeitsdateien wie Vorlagen, Kollektenpläne und Referenzdateien.

Nach Umsetzung soll die App folgende Kernaufgaben zuverlässig unterstützen:

erzeugte Buchungsblatt-Dateien direkt öffnen
den zugehörigen Ordner öffnen oder die Datei im Explorer markieren
Einträge oder ganze Treffermengen gezielt löschen
gelöschte Einträge gezielt erneut verarbeiten
im Verlauf mehrere oder alle Monate/Jahre auswählen
xlsx-Dateien direkt per Outlook verschicken
die für die App wichtigen Arbeitsdateien sichtbar verwalten, öffnen und ersetzen
den Tab Dokumente in eine verständliche, verifizierbare Arbeitsdatei- und Quellenverwaltung überführen
Die Umsetzung soll so erfolgen, dass ein neues Sekretariat ohne technisches Vorwissen sehen kann:

welche Dateien die App braucht
wo diese liegen
ob sie gültig vorhanden sind
wie sie geöffnet oder ersetzt werden können
welche erzeugten Buchungsblätter bereits vorliegen
wie einzelne oder mehrere Buchungen erneut verarbeitet werden können
Produktentscheidungen
Diese Entscheidungen gelten als fest und sollen vom Implementierer nicht erneut entschieden werden:

1. Arbeitsobjekt
Primäres Arbeitsobjekt der App sind die erzeugten Buchungsblätter im xlsx-Format, nicht abstrakte Laufereignisse oder unsichtbare interne Zustände.

2. Rerun-Scope
Löschen + Rerun arbeitet standardmäßig selektiv auf der gewählten Auswahl, nicht global.

Bedeutung:

Wenn konkrete Zeilen ausgewählt sind, betrifft die Aktion nur diese Zeilen.
Wenn keine Zeilen markiert sind, betrifft die Aktion die aktuell gefilterte Treffermenge.
Ein globaler Komplett-Reset ist nicht Teil dieses Ausbaus.
3. Bulk-Interaktion
Mehrfachaktionen werden über Zeilen-Auswahl + Filter gesteuert.

Bedeutung:

Tabelle unterstützt Mehrfachmarkierung.
Monat/Jahr-Filter definieren die sichtbare Treffermenge.
Aktionen laufen zuerst auf markierten Zeilen, sonst auf gefilterter Treffermenge.
4. Versand
Im Verlauf sollen die ausgewählten Buchungsblatt-Dateien direkt als xlsx über Outlook verschickt werden.

Nicht Ziel dieser Erweiterung:

alternatives Mail-System
SMTP-Konfiguration
komplexe Versandprofile
gleichzeitiger Zwang zu PDF-Bericht plus XLSX
5. Dokumente-Tab
Der Tab Dokumente bleibt erhalten, wird aber fachlich neu ausgerichtet:

Arbeitsdateien als primärer Bereich
Suche in Zusatzquellen als zweiter Bereich
Die aktuelle Unsichtbarkeit und Unklarheit des Tabs gilt als Mangel und muss explizit behoben werden.

6. Sicherheit bei Löschoperationen
Destruktive Änderungen müssen robust und nachvollziehbar sein. Statt riskanter punktueller Excel-Manipulation ist für die erste belastbare Version ein kontrollierter Neuaufbau betroffener Monatsdateien erlaubt und bevorzugt.

Aktueller Ist-Stand
Die folgenden Punkte sind aus dem aktuellen Code abgeleitet und bilden die Ausgangslage:

Übersicht
UebersichtTab zeigt letzte Einträge in einer einfachen QTableWidget.
Die Tabelle ist derzeit nicht interaktiv im Sinne von Datei- oder Ordneraktionen.
Es gibt keine direkte Aktion zum Öffnen der xlsx-Datei.
Verlauf
VerlaufTab nutzt CollectionTable.
Monat ist aktuell eine einfache Einzelwahl per QComboBox.
Jahr ist aktuell ein einzelner QSpinBox-Wert.
Es gibt bereits einen PDF-/Druck-/Outlook-Berichtspfad über app/reporter.py.
Es gibt noch keinen Versand der tatsächlichen xlsx-Dateien aus der Verlaufsansicht.
Es gibt noch keine Delete- oder Rerun-Aktionen.
CollectionTable
Die Tabelle lädt Daten aus output/kollekten_uebersicht.xlsx.
Es gibt bereits Rechtsklick-Aktionen für:
Klassifizierung korrigieren…
In Explorer öffnen
target_file ist in den geladenen Datensätzen vorhanden und kann zum Dateiöffnen genutzt werden.
Rohdaten pro Zeile werden über Qt.UserRole gespeichert.
Dokumente
DocumenteTab basiert auf document_sources.
Die bestehende Logik ist eine allgemeine Quellen-/Suchverwaltung.
Sie zeigt nicht automatisch die wirklich relevanten App-Dateien aus config.
Es gibt aktuell keine klare Verwaltung für:
Vorlagen
Kollektenpläne
Referenzdateien
Das erklärt, warum der Tab fachlich unverständlich wirkt.
Persistenz / Laufzustand
processed_emails.json enthält verarbeitete Outlook-entry_ids.
run_history.json enthält Laufereignisse und Status.
main.py markiert E-Mails nach Verarbeitung als verarbeitet.
Für selektives Löschen und Rerun fehlt aktuell eine explizite, robuste Rücknahme- und Rekonstruktionslogik.
Zielstruktur der Erweiterung
Die Umsetzung soll drei fachliche Arbeitsräume sauber definieren:

1. Übersicht = Schnellzugriff
Zweck:

neueste Buchungen sehen
direkt die erzeugte Datei öffnen
schnell zum Ordner springen
2. Verlauf = Korrektur, Sammelaktionen, Rerun
Zweck:

filtern
mehrere Einträge auswählen
Dateien per E-Mail versenden
löschen
erneut verarbeiten
3. Dokumente = Arbeitsdateien + Zusatzquellen
Zweck:

erforderliche Eingabedateien sichtbar verwalten
Dateien prüfen, öffnen und ersetzen
optionale Zusatzquellen für Suche weiterhin anbieten
Detaillierter Umsetzungsplan
A. Übersicht: Buchungsblätter direkt bedienbar machen
A1. Verhalten
Die Tabelle Letzte Einträge soll nicht nur anzeigen, sondern direkte Dateiaktionen ermöglichen.

A2. Neue Interaktionen
Für jede Zeile mit vorhandenem target_file:

Doppelklick auf Spalte Datei öffnet die xlsx-Datei
Rechtsklick-Menü bietet:
Datei öffnen
Ordner öffnen
Im Explorer markieren
optional Per E-Mail senden
Falls Datei fehlt:
klare Meldung: Datei nicht gefunden
optional Fallback auf Ausgabeordner
A3. Technischer Ansatz
UebersichtTab.table speichert pro Zeile ebenfalls den zugrunde liegenden Datensatz oder mindestens den Dateipfad.
Für Datei öffnen auf Windows:
bevorzugt os.startfile(path)
Für Im Explorer markieren:
explorer /select, <datei>
Für Ordner öffnen:
explorer <ordner>
A4. UX-Anforderungen
Dateispalte visuell als klickbar wahrnehmbar machen
Bei fehlender Datei keine stille Nichtreaktion
Keine Doppelanlagen von Menüs und Logik; Wiederverwendung mit CollectionTable bevorzugen
B. Verlauf: aus einfacher Ansicht in echten Arbeitsbereich umbauen
B1. Filtermodell
Ziel
Monat und Jahr sollen nicht mehr nur Einzelwerte erlauben, sondern Mengen.

Gewünschtes Verhalten
Alle Monate
einzelne Monate
mehrere Monate
Alle Jahre
einzelne Jahre
mehrere Jahre
Empfohlene UI
Normale QComboBox und QSpinBox reichen dafür fachlich nicht mehr aus.

Stattdessen:

checkbare Auswahlkomponenten oder kleine Auswahl-Dialoge
Anzeige der aktiven Filter als kompakte Zusammenfassung, z. B.:
Monat: Alle
Monat: 01, 02, 03
Jahr: 2025, 2026
Filterregeln
Leere/ungefilterte Auswahl bedeutet Alle
Treffer sind Vereinigung der gewählten Monate innerhalb der gewählten Jahre
Nur Warnungen bleibt zusätzlicher boolescher Filter
B2. Mehrfachauswahl in der Tabelle
Ziel
Der Benutzer soll einzelne oder mehrere Zeilen markieren können.

Verhalten
Standard: Mehrfachauswahl aktiv
Wenn Zeilen markiert sind, beziehen sich Aktionen auf diese Auswahl
Wenn nichts markiert ist, beziehen sich Aktionen auf alle aktuell gefilterten Treffer
Benötigte Hilfsfunktionen
get_selected_records()
get_filtered_records()
get_effective_records() mit Priorität:
Auswahl vor Filtermenge
B3. Neue Aktionsleiste im Verlauf
Zusätzlich oder statt reinem Report-Dropdown soll es eine klare Aktionsleiste geben:

Datei öffnen
Ordner öffnen
Im Explorer markieren
XLSX per E-Mail senden
Löschen
Löschen + Rerun
bestehender Button Bericht erstellen bleibt separat
Aktionsregeln
Aktionen auf Datei-Ebene deduplizieren nach target_file
Aktionen auf Buchungs-Ebene deduplizieren nach entry_id
Falls Auswahl leer und Filter leer sind, werden alle aktuell sichtbaren Treffer verwendet
B4. XLSX per E-Mail senden
Ziel
Nicht nur PDF-Berichte, sondern die tatsächlichen Buchungsblätter versenden.

Verhalten
Aus den effektiven Records werden alle vorhandenen target_files ermittelt
Deduplizierung nach Pfad
Nur existierende Dateien werden angehängt
Outlook wird wie bisher per win32com genutzt
Empfänger aus bestehender cfg["mail"]["recipient_emails"]
E-Mail-Inhalt
Betreff enthält Zeitraum oder Anzahl Dateien
Body kurz und sachlich
keine PDFs automatisch mitschicken
Erfolgsmeldung nennt Anzahl Anhänge
Fehlermeldung nennt Anzahl nicht gefundener Dateien, falls relevant
Implementationshinweis
Neue dedizierte Funktion ergänzen, getrennt vom bestehenden PDF-Reportversand.

B5. Löschen
Ziel
Einträge gezielt aus der Arbeitsmenge entfernen.

Fachliche Bedeutung von „Löschen“
Löschen bedeutet nicht nur visuelles Ausblenden. Es bedeutet:

betroffene Buchungen sind nicht mehr im Verlauf sichtbar
betroffene Buchungen sind nicht mehr in der Übersichts-xlsx
betroffene Buchungen sind nicht mehr in den betroffenen Monatsdateien enthalten
bereits verarbeitete Outlook-E-Mails bleiben nur dann im processed-Status, wenn kein Rerun gewünscht ist
Standardverhalten für diese Ausbaustufe
Für Löschen ohne Rerun:

betroffene Buchungen aus Bestandsdaten entfernen
processed_emails nicht automatisch zurücksetzen
run_history um ein explizites Lösch-Ereignis ergänzen
Technischer Minimalbedarf
Der Datensatz pro Buchung muss stabil identifizierbar sein, mindestens über:

entry_id
target_file
Wenn diese Informationen heute nicht durchgängig aus der Übersichtsladung stammen, muss die Datenbasis erweitert werden.

B6. Löschen + Rerun
Ziel
Fehlerhafte oder geänderte Einträge gezielt neu erzeugen.

Fachliche Bedeutung
Löschen + Rerun bedeutet:

betroffene Buchungen aus Ausgabe und Übersicht entfernen
zugehörige E-Mails aus processed_emails zurücknehmen
relevante Historie protokollieren
erneute Verarbeitung dieser betroffenen E-Mails auslösen
betroffene Monatsdateien und die Übersicht wieder konsistent aufbauen
Wichtige Designentscheidung
Nicht versuchen, einzelne Excel-Zellen “minimalinvasiv” zu löschen, wenn das unnötig riskant ist.

Robuster Default:

betroffene Buchungsdatensätze identifizieren
betroffene Monatsdateien aus verbleibenden Daten neu erzeugen
selektive Outlook-E-Mails erneut laufen lassen
Voraussetzung
Es braucht eine kontrollierte Service-Schicht für:

Auswahl -> betroffene entry_id
Auswahl -> betroffene Monatsdateien
Rücknahme -> processed_emails
Rekonstruktion -> Übersicht + Monatsdateien
Benutzerführung
Vor Ausführung Bestätigungsdialog mit:

Anzahl gewählter Zeilen
Anzahl betroffener E-Mails
Anzahl betroffener Monatsdateien
Warnung, dass Dateien neu aufgebaut werden
Protokollierung
run_history soll zusätzliche Statusereignisse kennen, z. B.:

deleted
deleted_for_rerun
rerun_started
rerun_finished
rerun_failed
C. Datenbasis für selektive Mutation stabilisieren
Das ist der wichtigste technische Unterbau des gesamten Plans.

C1. Problem
Aktuell lädt die Tabelle primär aus kollekten_uebersicht.xlsx. Das ist gut für Anzeige, aber schwach für gezielte Rücknahme und Neuerzeugung.

C2. Ziel
Jede sichtbare Buchung braucht eine stabile Herkunft.

Mindestens nötig:

entry_id
booking_date
amount
purpose
scope
target_file
idealerweise eine interne Buchungs-ID oder ein vollständig serialisierter Datensatz
C3. Empfohlener Ansatz
Die App bekommt eine belastbare, maschinenlesbare Bestandsquelle für Buchungen, aus der:

Verlauf
Übersicht
Dateiaktionen
Delete
Rerun
einheitlich gespeist werden.

Mögliche Form
Eine zusätzliche JSON-State-Datei, z. B. als Buchungsindex.

Inhalt pro Buchung:

entry_id
received
booking_date
amount
purpose
scope
aobj
target_file
needs_review
status
optionale Referenz auf Monatsdatei
Warum
Das vermeidet fragile Rückschlüsse nur aus Excel-Anzeigezeilen.

C4. Verwendung
Excel-Dateien bleiben Arbeitsartefakte
JSON-Bestandsindex wird die operative Grundlage für Mutation
Übersichts- und Monats-xlsx werden daraus neu geschrieben oder aktualisiert
C5. Kompatibilität
Bestehende Daten sollen beim ersten Laden oder beim nächsten Run automatisch in die neue Struktur überführt werden, soweit möglich.

Wenn vollständige Rekonstruktion aus Altbestand nicht sicher möglich ist:

dann nur neue Runs garantieren vollständige Rückverfolgbarkeit
Altbestand im UI lesbar lassen, aber destruktive Aktionen für nicht rückverfolgbare Einträge ggf. deaktivieren oder eingeschränkt kennzeichnen
D. Dokumente-Tab fachlich neu strukturieren
D1. Grundproblem
Der Tab Dokumente ist aktuell als allgemeine Suchquellenverwaltung gebaut, nicht als sichtbare Verwaltung der benötigten Arbeitsdateien. Für Nutzer ist nicht erkennbar:

welche Dateien die App braucht
welche Dateien aus der Konfiguration kommen
ob diese vorhanden sind
wie man sie austauscht
D2. Zielstruktur des Tabs
Der Tab wird in zwei sichtbare Hauptbereiche geteilt:

Bereich 1: Arbeitsdateien
Pflichtbereich, immer sichtbar

Bereich 2: Zusatzquellen / Suche
Optionaler Bereich, nur für zusätzliche Recherche und Textextraktion

D3. Bereich „Arbeitsdateien“
Sichtbare Kategorien
Mindestens anzeigen:

Vorlage eigene Gemeinde
Vorlage zur Weiterleitung
Referenz Abrechnungsobjekte
Referenz Kollektenregeln
Referenz Manuelle Overrides
Kollektenplan-URL oder Jahresplandateien
weitere konfigurierte Referenzpfade aus config
Pro Eintrag anzeigen
fachlicher Name
Typ
aktueller Pfad oder URL
Status:
vorhanden
fehlt
ungültig
optional
letzte Prüfung
kurze Beschreibung des Zwecks
Aktionen pro Eintrag
Öffnen
Ordner öffnen
Ersetzen…
Neu zuweisen…
Prüfen
bei optionalen Einträgen: Entfernen
Verhalten
Beim Laden des Tabs wird sofort der Status aller Arbeitsdateien geprüft
Fehlende oder ungültige Dateien werden sichtbar hervorgehoben
Ein neues Sekretariat soll allein über diesen Bereich alle nötigen Dateien ergänzen können
D4. Bereich „Zusatzquellen / Suche“
Zweck
Optional zusätzliche PDFs, Ordner oder URLs für Volltextsuche

Verhalten
bisherige document_sources-Logik bleibt grundsätzlich nutzbar
aber nur als Zusatzfunktion
Suchquellen müssen sichtbar aufgelistet sein
Aktualisieren muss klar Erfolg oder Fehler melden
Suchtreffer müssen nachvollziehbar zur Quelle zeigen
Korrektur des derzeitigen Problems
Wenn heute “nichts sichtbar” ist, muss der neue Tab explizit leere Zustände darstellen:

Keine Zusatzquellen konfiguriert
Arbeitsdateien sind oben sichtbar
Mit + Hinzufügen können weitere PDFs, Ordner oder URLs für Suche ergänzt werden
D5. Verifikation im Tab selbst
Der Tab soll nicht nur verwalten, sondern sich selbst plausibel machen.

Dafür:

Statusanzeige je Datei/Quelle
Fehlertexte je fehlendem Pfad
Erfolgs-/Fehlermeldung bei Quelle aktualisieren
keine stillen Fehlschläge
E. Öffnen und Ersetzen von Arbeitsdateien
E1. Öffnen
Für alle konfigurierten Datei-Artefakte:

os.startfile(path) für Datei
explorer /select, path für Explorer-Markierung
explorer <ordner> für Ordner
E2. Ersetzen
Ersetzen bedeutet:

Dateiauswahldialog
neuer Pfad wird in config gespeichert
Status aktualisiert sich sofort
keine manuelle JSON-Bearbeitung nötig
E3. Besondere Fälle
URL-basierte Kollektenplanquelle
nicht “ersetzen”, sondern URL bearbeiten
optional zusätzlich lokale Jahresplandateien anzeigen
Pflichtdatei fehlt
prominenter Warnstatus
keine stille Folgefehlerkette an anderer Stelle
F. Benötigte UI-/API-/Service-Erweiterungen
F1. Neue UI-Funktionen
interaktive Dateispalten
Mehrfachauswahl in Tabellen
Mehrfachfilter für Monat/Jahr
Aktionsleiste im Verlauf
Arbeitsdateien-Statusliste im Dokumente-Tab
F2. Neue Service-Funktionen
Es wird eine zentrale Service-Schicht empfohlen für:

Buchungsdatensätze laden
Datensätze nach Filter/Auswahl auflösen
Dateipfade deduplizieren
xlsx per E-Mail senden
Buchungen löschen
Buchungen für Rerun zurücksetzen
Monatsdateien neu aufbauen
Übersicht neu aufbauen
Arbeitsdateien validieren
F3. Neue oder angepasste Persistenz
Benötigt:

stabiler Buchungsindex
erweiterte Historienereignisse
selektive Manipulation von processed_emails
G. Test- und Verifikationsplan
G1. Übersicht
Doppelklick auf Dateiname öffnet die richtige Datei
Explorer-Aktionen funktionieren
fehlende Datei wird sauber gemeldet
G2. Verlauf-Filter
Einzelauswahl Monat/Jahr wie bisher
Mehrfachmonat korrekt
Mehrfachjahr korrekt
Alle korrekt
Nur Warnungen kombiniert korrekt mit Mehrfachfiltern
G3. Verlauf-Mehrfachaktionen
Aktionen auf markierten Zeilen funktionieren
Aktionen ohne Markierung laufen auf Filtermenge
deduplizierte Dateiaktionen funktionieren
keine Mehrfachanhänge derselben Datei im Versand
G4. XLSX-Versand
Outlook-Mail wird erstellt/versendet
Anhänge sind tatsächlich xlsx
nicht vorhandene Dateien werden übersprungen und gemeldet
G5. Löschen
Eintrag verschwindet aus Verlauf
Eintrag verschwindet aus Übersicht
betroffene Monatsdatei wird korrekt neu erzeugt oder bereinigt
Historie enthält Lösch-Ereignis
G6. Löschen + Rerun
processed_emails wird für Auswahl korrekt zurückgenommen
erneuter Lauf erzeugt die betroffenen Einträge erneut
keine Verdopplung in Übersicht oder Monatsdatei
parse-failed-Fälle können erneut bearbeitet werden
G7. Dokumente
alle konfigurierten Arbeitsdateien sichtbar
fehlende Dateien sichtbar rot/als Warnung markiert
Öffnen/Ordner öffnen/Ersetzen funktioniert
Zusatzquellen bleiben bedienbar
Suche zeigt nur sinnvolle, nachvollziehbare Ergebnisse
G8. Regression
bestehende Klassifizierungskorrektur im Verlauf funktioniert weiter
PDF-Bericht aus Verlauf funktioniert weiter
normaler Run ohne UI-Sonderaktionen funktioniert weiter
H. Risiken und Gegenmaßnahmen
H1. Risiko: Selektives Excel-Löschen ist fehleranfällig
Gegenmaßnahme:

Monatsdateien lieber kontrolliert neu aus Bestandsdaten erzeugen
H2. Risiko: Altbestände sind nicht vollständig rückverfolgbar
Gegenmaßnahme:

neue persistente Buchungsbasis einführen
nicht rückverfolgbare Altzeilen als eingeschränkt behandelbar markieren
H3. Risiko: UI wird zu komplex
Gegenmaßnahme:

klare Trennung:
Übersicht = Schnellzugriff
Verlauf = Sammelaktionen
Dokumente = Arbeitsdateien + Zusatzquellen
H4. Risiko: stille Dateifehler
Gegenmaßnahme:

jeder Datei- und Quellenpfad bekommt sichtbare Statusprüfung
I. Reihenfolge der Umsetzung
Phase 1: Datenbasis und Dateiaktionen
stabile Herkunftsdaten pro Buchung
Datei öffnen / Ordner öffnen / Explorer markieren
Übersicht und Verlauf interaktiv machen
Phase 2: Verlauf ausbauen
Mehrfachauswahl
Mehrfachfilter Monat/Jahr
xlsx-Versand
Phase 3: Delete und Rerun
selektive Rücknahme
Monatsdateien und Übersicht konsistent neu erzeugen
Historie und processed_emails robust aktualisieren
Phase 4: Dokumente neu strukturieren
Arbeitsdateien aus config sichtbar machen
Öffnen / Ersetzen / Validieren
Zusatzquellen-Suche daneben stabilisieren
Phase 5: Verifikation
End-to-End-Test mit echten Buchungsblättern
Testfall neues Sekretariat: fehlende Dateien ergänzen, öffnen, austauschen, Run ausführen
J. Akzeptanzkriterien
Die Umsetzung gilt als fachlich fertig, wenn folgende Nutzerwege in der App ohne manuelle JSON-Bearbeitung möglich sind:

Ein Sekretariat kann in der Übersicht ein erzeugtes Buchungsblatt anklicken und öffnen.
Im Verlauf können mehrere Monate und/oder Jahre gleichzeitig gefiltert werden.
Im Verlauf können mehrere Zeilen markiert und die zugehörigen xlsx-Dateien per Outlook versendet werden.
Im Verlauf können ausgewählte Einträge gelöscht werden.
Im Verlauf können ausgewählte Einträge gelöscht und gezielt neu verarbeitet werden.
Im Dokumente-Tab sind Vorlagen, Referenzdateien und relevante Arbeitsdateien sofort sichtbar.
Diese Arbeitsdateien können geöffnet, geprüft und ersetzt werden.
Zusatzquellen für Suche bleiben nutzbar und verifiziert.
Keine der neuen Aktionen scheitert still; Fehler werden im UI verständlich gemeldet.
Die erzeugten xlsx-Bestände bleiben nach Delete/Rerun konsistent.
Annahmen
Outlook bleibt für den E-Mail-Versand gesetzt.
Windows ist die Zielplattform.
xlsx ist weiterhin das führende Artefakt der Facharbeit.
Eine zusätzliche persistente Bestandsdatei für Buchungen ist zulässig, wenn sie Delete/Rerun robust macht.
Für die erste Version ist Robustheit wichtiger als minimale interne Eleganz.