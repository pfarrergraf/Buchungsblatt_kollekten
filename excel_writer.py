"""Excel-Schreiber: trägt Kollektendaten in die monatliche Datei ein."""
import logging
import shutil
from pathlib import Path

import openpyxl
from openpyxl.styles import numbers

from config import get_config
from parser import KollekteData

log = logging.getLogger(__name__)

SHEET_NAME = "eigene Gemeinde"
DATA_START_ROW = 17
COL_BETRAG = 1          # A
COL_KOLLEKTE_VOM = 6    # F
COL_VERWENDUNGSZWECK = 8  # H

def _get_monthly_path(datum, cfg: dict) -> Path:
    """Gibt den Pfad zur monatlichen Datei zurück; kopiert Vorlage und befüllt Header."""
    out = Path(cfg["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    filename = f"Kollekten_{datum.year}_{datum.month:02d}.xlsx"
    dest = out / filename
    if not dest.exists():
        shutil.copy2(cfg["template_path"], dest)
        _write_header_info(dest, cfg)
        log.info("Neue Monatsdatei erstellt: %s", dest)
    return dest


def _write_header_info(path: Path, cfg: dict) -> None:
    """Schreibt Rechtsträger-Nr., Bankname und IBAN in die neue Monatsdatei."""
    wb = openpyxl.load_workbook(path)
    ws = wb[SHEET_NAME]
    # L2: Rechtsträger-Nr. (aktiviert Formeln im Sheet, z.B. Gemeindename)
    rechtsträger_nr = cfg.get("rechtsträger_nr", "")
    if rechtsträger_nr:
        ws["L2"] = rechtsträger_nr
    # B11/B12: Bankname und IBAN direkt eintragen (Formeln brauchen RT-Lookup)
    ws["B11"] = cfg.get("bank_name", "")
    ws["B12"] = cfg.get("bank_iban", "")
    wb.save(path)


def _find_next_empty_row(ws) -> int:
    """Sucht die nächste leere Zeile ab DATA_START_ROW (Spalte A oder F)."""
    row = DATA_START_ROW
    while True:
        if ws.cell(row=row, column=COL_BETRAG).value is None and \
           ws.cell(row=row, column=COL_KOLLEKTE_VOM).value is None:
            return row
        row += 1


def write_kollekte(data: KollekteData) -> Path:
    """Schreibt eine Kollekte in die passende Monatsdatei. Gibt den Dateipfad zurück."""
    cfg = get_config()
    monthly_path = _get_monthly_path(data.datum, cfg)

    wb = openpyxl.load_workbook(monthly_path)

    if SHEET_NAME not in wb.sheetnames:
        raise ValueError(
            f"Sheet '{SHEET_NAME}' nicht gefunden in {monthly_path}. "
            f"Verfügbare Sheets: {wb.sheetnames}"
        )

    ws = wb[SHEET_NAME]
    row = _find_next_empty_row(ws)

    # Spalte A: Betrag (numerisch, Euro-Format)
    cell_betrag = ws.cell(row=row, column=COL_BETRAG, value=data.betrag)
    cell_betrag.number_format = '#,##0.00 €'

    # Spalte F: Datum DD.MM.YYYY
    cell_datum = ws.cell(row=row, column=COL_KOLLEKTE_VOM, value=data.datum)
    cell_datum.number_format = 'DD.MM.YYYY'

    # Spalte H: Verwendungszweck
    ws.cell(row=row, column=COL_VERWENDUNGSZWECK, value=data.verwendungszweck)

    wb.save(monthly_path)
    log.info(
        "Eingetragen in %s Zeile %d: %s | %.2f € | %s",
        monthly_path.name, row, data.datum, data.betrag, data.verwendungszweck,
    )
    return monthly_path
