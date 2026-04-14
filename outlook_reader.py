"""Outlook-Anbindung via win32com: liest E-Mails von no-reply@ekhn.info."""
import json
import logging
from pathlib import Path
from typing import Generator, Optional

log = logging.getLogger(__name__)

# Restrict-Filter: Absender — Outlook filtert nativ, kein Iterieren aller Mails
# Items.Restrict() nutzt JET-Syntax mit eckigen Klammern (kein @SQL= nötig)
_RESTRICT_FILTER = "[SenderEmailAddress] = 'no-reply@ekhn.info'"


def _load_processed(filepath: str) -> set:
    p = Path(filepath)
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def _save_processed(filepath: str, ids: set) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(sorted(ids), f, indent=2)


def _iter_all_folders(folder):
    """Rekursiv alle Unterordner eines Outlook-Ordners durchlaufen."""
    yield folder
    try:
        for subfolder in folder.Folders:
            yield from _iter_all_folders(subfolder)
    except Exception:
        pass


def get_new_emails(cfg: dict, year_filter: Optional[int] = None) -> Generator[dict, None, None]:
    """
    Gibt neue (noch nicht verarbeitete) E-Mails von no-reply@ekhn.info zurück.

    Verwendet Items.Restrict() mit Absender+Betreff-Filter — Outlook hängt nicht.
    year_filter: wenn gesetzt, werden nur E-Mails aus diesem Jahr geliefert.
    """
    try:
        import win32com.client
    except ImportError:
        raise RuntimeError(
            "pywin32 nicht installiert oder Outlook nicht verfügbar. "
            "Bitte 'uv pip install pywin32' und Outlook starten."
        )

    processed = _load_processed(cfg["processed_emails_file"])
    found = 0
    skipped = 0

    outlook = win32com.client.Dispatch("Outlook.Application")
    namespace = outlook.GetNamespace("MAPI")

    for store_idx in range(1, namespace.Stores.Count + 1):
        try:
            store = namespace.Stores[store_idx]
            root = store.GetRootFolder()
        except Exception as exc:
            log.debug("Store %d übersprungen: %s", store_idx, exc)
            continue

        for folder in _iter_all_folders(root):
            try:
                restricted = folder.Items.Restrict(_RESTRICT_FILTER)
                count = restricted.Count
            except Exception:
                continue

            if count == 0:
                continue

            log.debug("Ordner '%s': %d passende E-Mails", getattr(folder, "Name", "?"), count)

            for i in range(1, count + 1):
                try:
                    msg = restricted[i]
                except Exception as exc:
                    log.debug("Element %d nicht lesbar: %s", i, exc)
                    continue

                try:
                    entry_id = msg.EntryID

                    if entry_id in processed:
                        skipped += 1
                        continue

                    # Jahresfilter
                    if year_filter is not None:
                        received = getattr(msg, "ReceivedTime", None)
                        if received and received.year != year_filter:
                            continue

                    # Betreff-Filter: nur "Gottesdienststatistik"-Mails
                    subject = getattr(msg, "Subject", "") or ""
                    subject_filter = cfg.get("subject_filter", "Gottesdienststatistik")
                    if subject_filter.lower() not in subject.lower():
                        continue

                    body = ""
                    try:
                        body = msg.Body or ""
                    except Exception:
                        pass

                    found += 1
                    yield {
                        "entry_id": entry_id,
                        "subject": getattr(msg, "Subject", ""),
                        "body": body,
                        "received": getattr(msg, "ReceivedTime", None),
                    }

                except Exception as exc:
                    log.warning("Fehler bei E-Mail %d: %s", i, exc)
                    continue

    log.info(
        "Outlook-Suche abgeschlossen: %d neue E-Mails, %d bereits verarbeitet übersprungen.",
        found, skipped,
    )


def mark_processed(cfg: dict, entry_id: str) -> None:
    processed = _load_processed(cfg["processed_emails_file"])
    processed.add(entry_id)
    _save_processed(cfg["processed_emails_file"], processed)
