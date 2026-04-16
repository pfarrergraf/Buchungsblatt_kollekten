"""Operationen fuer Buchungsbestand, Delete und Rerun."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from booking_store import get_booking_rows, remove_bookings, row_to_record
from excel_writer import rebuild_outputs
from outlook_reader import remove_processed_ids
from state_store import append_history


def delete_records(cfg: dict, records: list[dict], *, for_rerun: bool = False) -> dict:
    entry_ids = {str(record.get("entry_id") or "") for record in records if str(record.get("entry_id") or "")}
    removed = remove_bookings(cfg, entry_ids)
    # rebuild_outputs MUST succeed before remove_processed_ids is called.
    # If Excel files are locked or the template is missing, we raise here so
    # processed_emails stays intact and the user can retry after fixing the issue.
    rebuild_outputs([row_to_record(row) for row in get_booking_rows(cfg, include_statuses={"ok"})], cfg)
    if for_rerun:
        remove_processed_ids(cfg, entry_ids)
    monthly_files = sorted({str(Path(row.get("target_file") or "").name) for row in removed if row.get("target_file")})
    append_history(
        cfg["state"]["run_history_file"],
        {
            "status": "deleted_for_rerun" if for_rerun else "deleted",
            "entry_ids": sorted(entry_ids),
            "count": len(entry_ids),
            "monthly_files": monthly_files,
        },
    )
    return {
        "entry_ids": sorted(entry_ids),
        "monthly_files": monthly_files,
        "count": len(entry_ids),
    }
