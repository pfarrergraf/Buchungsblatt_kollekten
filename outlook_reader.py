"""Outlook-Anbindung via win32com: liest E-Mails aus den konfigurierten Absendern."""
from __future__ import annotations

import logging
from typing import Generator, Optional

from state_store import load_id_set, save_id_set
from state_store import remove_ids

log = logging.getLogger(__name__)


def _sender_filter(senders: list[str]) -> str:
    if not senders:
        senders = ["no-reply@ekhn.info"]
    filters = [f"[SenderEmailAddress] = '{sender}'" for sender in senders]
    if len(filters) == 1:
        return filters[0]
    return "(" + " OR ".join(filters) + ")"


def _iter_all_folders(folder):
    yield folder
    try:
        for subfolder in folder.Folders:
            yield from _iter_all_folders(subfolder)
    except Exception:
        pass


def get_new_emails(cfg: dict, year_filter: Optional[int] = None) -> Generator[dict, None, None]:
    """Gibt noch nicht verarbeitete E-Mails aus den konfigurierten Absendern zurück."""
    try:
        import win32com.client
    except ImportError as exc:
        raise RuntimeError(
            "pywin32 nicht installiert oder Outlook nicht verfuegbar. Bitte 'uv pip install pywin32' ausfuehren."
        ) from exc

    mail_cfg = cfg.get("mail", {})
    processed = load_id_set(cfg["state"]["processed_emails_file"])
    found = 0
    skipped = 0
    subject_filter = str(mail_cfg.get("subject_filter", "Gottesdienststatistik")).casefold()
    sender_filter = _sender_filter(list(mail_cfg.get("senders", [])))

    outlook = win32com.client.Dispatch("Outlook.Application")
    namespace = outlook.GetNamespace("MAPI")

    for store_idx in range(1, namespace.Stores.Count + 1):
        try:
            store = namespace.Stores[store_idx]
            root = store.GetRootFolder()
        except Exception as exc:
            log.debug("Store %d uebersprungen: %s", store_idx, exc)
            continue

        for folder in _iter_all_folders(root):
            try:
                restricted = folder.Items.Restrict(sender_filter)
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
                    entry_id = str(msg.EntryID)
                    if entry_id in processed:
                        skipped += 1
                        continue

                    if year_filter is not None:
                        received = getattr(msg, "ReceivedTime", None)
                        if received and received.year != year_filter:
                            continue

                    subject = getattr(msg, "Subject", "") or ""
                    if subject_filter and subject_filter not in subject.casefold():
                        continue

                    body = ""
                    try:
                        body = msg.Body or ""
                    except Exception:
                        pass

                    found += 1
                    yield {
                        "entry_id": entry_id,
                        "subject": subject,
                        "body": body,
                        "received": getattr(msg, "ReceivedTime", None),
                        "sender_email": getattr(msg, "SenderEmailAddress", ""),
                    }
                except Exception as exc:
                    log.warning("Fehler bei E-Mail %d: %s", i, exc)

    log.info(
        "Outlook-Suche abgeschlossen: %d neue E-Mails, %d bereits verarbeitet uebersprungen.",
        found,
        skipped,
    )


def get_emails_by_entry_ids(cfg: dict, entry_ids: set[str]) -> Generator[dict, None, None]:
    """Lädt gezielt Outlook-Nachrichten über EntryIDs."""
    if not entry_ids:
        return
    try:
        import win32com.client
    except ImportError as exc:
        raise RuntimeError(
            "pywin32 nicht installiert oder Outlook nicht verfuegbar. Bitte 'uv pip install pywin32' ausfuehren."
        ) from exc
    outlook = win32com.client.Dispatch("Outlook.Application")
    namespace = outlook.GetNamespace("MAPI")
    for entry_id in sorted(entry_ids):
        try:
            msg = namespace.GetItemFromID(entry_id)
        except Exception as exc:
            log.warning("Outlook-Eintrag %s nicht ladbar: %s", entry_id, exc)
            continue
        subject = getattr(msg, "Subject", "") or ""
        body = ""
        try:
            body = msg.Body or ""
        except Exception:
            pass
        yield {
            "entry_id": str(entry_id),
            "subject": subject,
            "body": body,
            "received": getattr(msg, "ReceivedTime", None),
            "sender_email": getattr(msg, "SenderEmailAddress", ""),
        }


def mark_processed(cfg: dict, entry_id: str) -> None:
    processed = load_id_set(cfg["state"]["processed_emails_file"])
    processed.add(entry_id)
    save_id_set(cfg["state"]["processed_emails_file"], processed)


def remove_processed_ids(cfg: dict, entry_ids: set[str]) -> None:
    remove_ids(cfg["state"]["processed_emails_file"], entry_ids)
