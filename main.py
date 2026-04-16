"""Hauptskript: Outlook lesen, klassifizieren, exportieren und Uebersicht pflegen."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from classification import classify_collection
from booking_store import upsert_booking
from config import get_config, save_config, setup_interactive, upgrade_and_save
from email_sender import notify_missing_amount
from excel_writer import write_collection
from outlook_reader import get_emails_by_entry_ids, get_new_emails, mark_processed
from parser import extract_partial_info, parse_email
from references import ensure_reference_files, load_reference_bundle
from state_store import append_history


def setup_logging(log_file: str) -> None:
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def run(year_filter: int | None = None, dry_run: bool = False, entry_ids: set[str] | None = None) -> tuple[int, int]:
    cfg = get_config()
    ensure_reference_files(cfg)
    setup_logging(cfg["runtime"]["log_file"])
    log = logging.getLogger("main")
    bundle = load_reference_bundle(cfg)
    log.info("=== Kollekten-Automation gestartet ===")
    processed_count = 0
    error_count = 0
    email_iter = get_emails_by_entry_ids(cfg, entry_ids) if entry_ids else get_new_emails(cfg, year_filter=year_filter)
    for email in email_iter:
        entry_id = email["entry_id"]
        log.info("Verarbeite E-Mail: %s (empfangen: %s)", email["subject"], email["received"])
        try:
            received = email["received"]
            recv_date = received.date() if received else None
            parsed = parse_email(email["body"], received_date=recv_date)
            if parsed is None:
                partial = extract_partial_info(email["body"], received_date=recv_date)
                log.warning(
                    "Kein Betrag gefunden (EntryID: %s, Gottesdienst: %s, Letzte Zeile: %r)",
                    entry_id, partial["datum_str"], partial["last_line"],
                )
                notify_missing_amount(
                    cfg,
                    original_subject=email["subject"],
                    original_body=email["body"],
                    received=email["received"],
                    gottesdienst_date=partial["datum_str"],
                    last_line=partial["last_line"],
                )
                mark_processed(cfg, entry_id)
                append_history(cfg["state"]["run_history_file"], {"entry_id": entry_id, "status": "parse_failed"})
                error_count += 1
                continue
            record = classify_collection(
                parsed,
                cfg,
                entry_id=entry_id,
                subject=email["subject"],
                received=email["received"],
                bundle=bundle,
            )
            dest = write_collection(record, cfg)
            upsert_booking(cfg, record, str(dest))
            mark_processed(cfg, entry_id)
            append_history(
                cfg["state"]["run_history_file"],
                {
                    "entry_id": entry_id,
                    "status": "ok",
                    "target_file": str(dest),
                    "scope": record.scope,
                },
            )
            processed_count += 1
            log.info(
                "OK: %s | %.2f EUR | %s -> %s",
                record.booking_date.strftime("%d.%m.%Y"),
                record.amount,
                record.purpose,
                dest.name,
            )
        except Exception as exc:
            log.error("Fehler bei EntryID %s: %s", entry_id, exc, exc_info=True)
            append_history(cfg["state"]["run_history_file"], {"entry_id": entry_id, "status": "error", "error": str(exc)})
            error_count += 1
    log.info("=== Fertig: %d verarbeitet, %d Fehler ===", processed_count, error_count)
    return processed_count, error_count


def bootstrap() -> None:
    cfg = setup_interactive()
    ensure_reference_files(cfg)
    save_config(cfg)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")

    run_parser = sub.add_parser("run", help="Outlook verarbeiten und Excel aktualisieren")
    run_parser.add_argument("--year", type=int, default=None, help="Nur E-Mails aus diesem Jahr verarbeiten")
    sub.add_parser("config", help="Interaktive Ersterfassung / Aktualisierung der Konfiguration")
    sub.add_parser("upgrade-config", help="Alte config.json in das neue Schema ueberfuehren")
    schedule_parser = sub.add_parser("schedule", help="Windows Task Scheduler Eintraege erzeugen")
    schedule_parser.add_argument("--remove", action="store_true", help="Einen bestehenden Task entfernen")
    schedule_parser.add_argument("--name", default="default", help="Name des Zeitplans")
    sub.add_parser("bootstrap", help="Konfiguration, Referenzen und Verzeichnisse initialisieren")
    args = parser.parse_args(argv)

    command = args.command or "run"
    if command == "config":
        setup_interactive()
        return
    if command == "upgrade-config":
        upgrade_and_save()
        return
    if command == "schedule":
        import scheduler_setup

        scheduler_setup.main(["--remove", "--name", args.name] if args.remove else ["--name", args.name])
        return
    if command == "bootstrap":
        bootstrap()
        return
    run(year_filter=getattr(args, "year", None))


if __name__ == "__main__":
    main()
