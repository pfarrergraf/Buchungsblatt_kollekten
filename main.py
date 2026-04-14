"""Hauptskript: liest Outlook-E-Mails und schreibt Kollektendaten nach Excel."""
import argparse
import logging
import sys
from pathlib import Path

from config import get_config
from excel_writer import write_kollekte
from outlook_reader import get_new_emails, mark_processed
from parser import parse_email


def setup_logging(log_file: str) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def run(year_filter=None) -> None:
    cfg = get_config()
    setup_logging(cfg["log_file"])
    log = logging.getLogger("main")

    if year_filter:
        log.info("=== Kollekten-Automation gestartet (nur Jahr %d) ===", year_filter)
    else:
        log.info("=== Kollekten-Automation gestartet ===")

    processed_count = 0
    error_count = 0

    for email in get_new_emails(cfg, year_filter=year_filter):
        entry_id = email["entry_id"]
        log.info("Verarbeite E-Mail: %s (empfangen: %s)", email["subject"], email["received"])

        try:
            received = email["received"]
            recv_date = received.date() if received else None
            data = parse_email(email["body"], received_date=recv_date)
            if data is None:
                log.warning("E-Mail konnte nicht geparst werden (EntryID: %s)", entry_id)
                # Trotzdem als verarbeitet markieren, um Endlosschleife zu vermeiden
                mark_processed(cfg, entry_id)
                error_count += 1
                continue

            dest = write_kollekte(data)
            mark_processed(cfg, entry_id)
            processed_count += 1
            log.info(
                "OK: %s | %.2f € | %s → %s",
                data.datum.strftime("%d.%m.%Y"),
                data.betrag,
                data.verwendungszweck,
                dest.name,
            )

        except Exception as exc:
            log.error("Fehler bei EntryID %s: %s", entry_id, exc, exc_info=True)
            error_count += 1

    log.info(
        "=== Fertig: %d verarbeitet, %d Fehler ===",
        processed_count,
        error_count,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=None, help="Nur E-Mails aus diesem Jahr verarbeiten")
    args = parser.parse_args()
    run(year_filter=args.year)
