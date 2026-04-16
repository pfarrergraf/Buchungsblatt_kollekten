"""Outlook-E-Mail-Versand via win32com."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

log = logging.getLogger(__name__)


def _get_outlook():
    try:
        import win32com.client
        return win32com.client.Dispatch("Outlook.Application")
    except ImportError as exc:
        raise RuntimeError("pywin32 nicht installiert.") from exc


def notify_missing_amount(
    cfg: dict,
    *,
    original_subject: str,
    original_body: str,
    received: Optional[datetime],
    gottesdienst_date: Optional[str] = None,
    last_line: str = "",
) -> None:
    """Sendet eine Benachrichtigung wenn ein Kollektenbetrag fehlt."""
    recipients = cfg.get("mail", {}).get("recipient_emails", [])
    if not recipients:
        log.warning("Keine Empfänger konfiguriert – Benachrichtigung nicht gesendet.")
        return

    empfangen_str = received.strftime("%d.%m.%Y %H:%M") if received else "unbekannt"
    datum_str = gottesdienst_date or "unbekannt"

    betreff = f"Kollekte unvollständig – Betrag fehlt ({datum_str})"
    body = (
        f"Hallo,\n\n"
        f"folgende Gottesdienststatistik konnte nicht automatisch verarbeitet werden,\n"
        f"weil kein Kollektenbetrag erkannt wurde:\n\n"
        f"  Gottesdienst: {datum_str}\n"
        f"  E-Mail empfangen: {empfangen_str}\n"
        f"  Betreff: {original_subject}\n"
    )
    if last_line:
        body += f"  Letzte Zeile der E-Mail: \"{last_line}\"\n"
    body += (
        f"\nBitte den Betrag manuell nachprüfen und ggf. im System korrigieren.\n"
        f"Der Eintrag wurde nicht in die Excel-Datei übernommen.\n\n"
        f"--- Original-E-Mail ---\n{original_body[:1000]}"
    )

    try:
        outlook = _get_outlook()
        mail = outlook.CreateItem(0)  # olMailItem
        mail.To = "; ".join(recipients)
        mail.Subject = betreff
        mail.Body = body
        mail.Send()
        log.info("Benachrichtigung gesendet an %s: %s", recipients, betreff)
    except Exception as exc:
        log.error("Fehler beim Senden der Benachrichtigung: %s", exc)


def send_results(cfg: dict, generated_files: list) -> None:
    """Sendet generierte xlsx-Dateien als E-Mail-Anhänge."""
    recipients = cfg.get("mail", {}).get("recipient_emails", [])
    if not recipients:
        log.info("Keine Empfänger konfiguriert – Ergebnis-E-Mail übersprungen.")
        return
    if not generated_files:
        log.info("Keine generierten Dateien – Ergebnis-E-Mail übersprungen.")
        return

    months = sorted({f.stem.rsplit("_", 1)[0][-7:] for f in generated_files if hasattr(f, "stem")})
    betreff = f"Kollekten-Buchungsblätter {', '.join(months)}"
    anzahl = len(generated_files)
    body = (
        f"Anbei die generierten Kollekten-Buchungsblätter ({anzahl} Datei(en)).\n\n"
        f"Verarbeitete Monate: {', '.join(months) or 'unbekannt'}\n\n"
        f"Dieser Versand wurde automatisch durch die Kollekten-Automation erstellt."
    )

    try:
        outlook = _get_outlook()
        mail = outlook.CreateItem(0)
        mail.To = "; ".join(recipients)
        mail.Subject = betreff
        mail.Body = body
        for f in generated_files:
            mail.Attachments.Add(str(f))
        mail.Send()
        log.info("Ergebnis-E-Mail gesendet an %s mit %d Anhängen.", recipients, anzahl)
    except Exception as exc:
        log.error("Fehler beim Senden der Ergebnis-E-Mail: %s", exc)


def send_attachments(cfg: dict, attachments: list, *, subject: str, body: str) -> tuple[bool, int]:
    """Versendet beliebige Anhänge per Outlook."""
    recipients = cfg.get("mail", {}).get("recipient_emails", [])
    if not recipients:
        log.info("Keine Empfänger konfiguriert – E-Mail übersprungen.")
        return False, 0
    if not attachments:
        log.info("Keine Anhänge – E-Mail übersprungen.")
        return False, 0
    try:
        outlook = _get_outlook()
        mail = outlook.CreateItem(0)
        mail.To = "; ".join(recipients)
        mail.Subject = subject
        mail.Body = body
        count = 0
        for item in attachments:
            mail.Attachments.Add(str(item))
            count += 1
        mail.Send()
        log.info("E-Mail gesendet an %s mit %d Anhängen.", recipients, count)
        return True, count
    except Exception as exc:
        log.error("Fehler beim Senden der Anhang-E-Mail: %s", exc)
        return False, 0
