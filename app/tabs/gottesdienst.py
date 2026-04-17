"""Gottesdienst-Tab: Gottesdienstplan-Verwaltung und Abkündigungs-Generator."""
from __future__ import annotations

import csv
import json
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QDate, QTime, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

# ── Pfade ─────────────────────────────────────────────────────────────────────

_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "state"
_GOTTESDIENSTE_PATH = _DATA_DIR / "gottesdienste.json"
_KOLLEKTENPLAN_PATH = _DATA_DIR / "kollektenplan.json"

_LITURGIE_TYPEN = [
    "Hauptgottesdienst",
    "Abendmahlsgottesdienst",
    "Taufgottesdienst",
    "Andacht",
    "Sonstiges",
]

# ── JSON I/O ──────────────────────────────────────────────────────────────────


def _load_json(path: Path, default) -> list | dict:
    if not path.exists():
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(default), encoding="utf-8")
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save_json(path: Path, data) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Datums-Parsing ─────────────────────────────────────────────────────────────


def _parse_date_value(val) -> Optional[str]:
    """Wandelt verschiedene Datumsformate in ISO-String (YYYY-MM-DD) um.

    Unterstützt: DD.MM.YYYY, DD.MM.YY, YYYY-MM-DD sowie openpyxl datetime-Objekte.
    """
    if val is None:
        return None
    # openpyxl liefert datetime- oder date-Objekte direkt
    if isinstance(val, (datetime, date)):
        if isinstance(val, datetime):
            return val.date().isoformat()
        return val.isoformat()
    s = str(val).strip()
    if not s:
        return None
    # YYYY-MM-DD
    if len(s) == 10 and s[4] == "-":
        try:
            date.fromisoformat(s)
            return s
        except Exception:
            pass
    # DD.MM.YYYY
    if len(s) == 10 and s[2] == "." and s[5] == ".":
        try:
            d = datetime.strptime(s, "%d.%m.%Y")
            return d.date().isoformat()
        except Exception:
            pass
    # DD.MM.YY
    if len(s) == 8 and s[2] == "." and s[5] == ".":
        try:
            d = datetime.strptime(s, "%d.%m.%y")
            return d.date().isoformat()
        except Exception:
            pass
    return None


# ── Dialog ────────────────────────────────────────────────────────────────────


class GottesdienstDialog(QDialog):
    """Bearbeitungs-Dialog für einen einzelnen Gottesdienst-Eintrag."""

    def __init__(self, entry: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gottesdienst bearbeiten" if entry else "Neuer Gottesdienst")
        self.setMinimumWidth(460)
        self._entry = entry or {}
        self._build_ui()
        if entry:
            self._populate(entry)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(8)

        self._ed_datum = QDateEdit()
        self._ed_datum.setCalendarPopup(True)
        self._ed_datum.setDisplayFormat("dd.MM.yyyy")
        self._ed_datum.setDate(QDate.currentDate())

        self._ed_uhrzeit = QTimeEdit()
        self._ed_uhrzeit.setDisplayFormat("HH:mm")
        self._ed_uhrzeit.setTime(QTime(10, 0))

        self._ed_ort = QLineEdit()
        self._ed_ort.setPlaceholderText("z.B. Pauluskirche")

        self._cb_liturgie = QComboBox()
        for typ in _LITURGIE_TYPEN:
            self._cb_liturgie.addItem(typ)

        self._ed_pfarrer = QLineEdit()
        self._ed_pfarrer.setPlaceholderText("Name der Pfarrperson")

        self._ed_organist = QLineEdit()
        self._ed_organist.setPlaceholderText("Name des Organisten / der Organistin")

        self._ed_kollekte_zweck = QLineEdit()
        self._ed_kollekte_zweck.setPlaceholderText("Verwendungszweck der Kollekte")

        self._ed_kollekte_aobj = QLineEdit()
        self._ed_kollekte_aobj.setPlaceholderText("AObj-Nummer (optional)")

        self._ed_besonderheiten = QLineEdit()
        self._ed_besonderheiten.setPlaceholderText("z.B. Taufe, Abendmahl, …")

        self._ed_notiz = QTextEdit()
        self._ed_notiz.setPlaceholderText("Interne Notiz …")
        self._ed_notiz.setFixedHeight(72)

        form.addRow("Datum:", self._ed_datum)
        form.addRow("Uhrzeit:", self._ed_uhrzeit)
        form.addRow("Ort:", self._ed_ort)
        form.addRow("Liturgie-Typ:", self._cb_liturgie)
        form.addRow("Pfarrer/in:", self._ed_pfarrer)
        form.addRow("Organist/in:", self._ed_organist)
        form.addRow("Kollekte Zweck:", self._ed_kollekte_zweck)
        form.addRow("AObj:", self._ed_kollekte_aobj)
        form.addRow("Besonderheiten:", self._ed_besonderheiten)
        form.addRow("Notiz:", self._ed_notiz)

        layout.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Save).setText("Speichern")
        btns.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _populate(self, entry: dict) -> None:
        if entry.get("datum"):
            try:
                d = date.fromisoformat(entry["datum"])
                self._ed_datum.setDate(QDate(d.year, d.month, d.day))
            except Exception:
                pass
        if entry.get("uhrzeit"):
            try:
                h, m = map(int, entry["uhrzeit"].split(":"))
                self._ed_uhrzeit.setTime(QTime(h, m))
            except Exception:
                pass
        self._ed_ort.setText(entry.get("ort", ""))
        idx = self._cb_liturgie.findText(entry.get("liturgie_typ", ""))
        if idx >= 0:
            self._cb_liturgie.setCurrentIndex(idx)
        self._ed_pfarrer.setText(entry.get("pfarrer_in", ""))
        self._ed_organist.setText(entry.get("organist", ""))
        self._ed_kollekte_zweck.setText(entry.get("kollekte_zweck", ""))
        self._ed_kollekte_aobj.setText(entry.get("kollekte_aobj", ""))
        self._ed_besonderheiten.setText(entry.get("besonderheiten", ""))
        self._ed_notiz.setPlainText(entry.get("notiz", ""))

    def get_data(self) -> dict:
        qd = self._ed_datum.date()
        qt = self._ed_uhrzeit.time()
        return {
            "id": self._entry.get("id") or str(uuid.uuid4()),
            "datum": f"{qd.year():04d}-{qd.month():02d}-{qd.day():02d}",
            "uhrzeit": f"{qt.hour():02d}:{qt.minute():02d}",
            "ort": self._ed_ort.text().strip(),
            "liturgie_typ": self._cb_liturgie.currentText(),
            "pfarrer_in": self._ed_pfarrer.text().strip(),
            "organist": self._ed_organist.text().strip(),
            "kollekte_zweck": self._ed_kollekte_zweck.text().strip(),
            "kollekte_aobj": self._ed_kollekte_aobj.text().strip(),
            "besonderheiten": self._ed_besonderheiten.text().strip(),
            "notiz": self._ed_notiz.toPlainText().strip(),
        }


# ── Sub-Tab 1: Gottesdienstplan ───────────────────────────────────────────────


class _PlanTab(QWidget):
    """Monatliche Listenansicht aller Gottesdienste."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_year = date.today().year
        self._current_month = date.today().month
        self._gottesdienste: list[dict] = []
        self._build_ui()
        self._load_and_refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # Monats-Navigation
        nav_row = QHBoxLayout()
        nav_row.setSpacing(8)

        self._btn_prev = QPushButton("<")
        self._btn_prev.setFixedWidth(32)
        self._btn_prev.clicked.connect(self._prev_month)

        self._lbl_month = QLabel()
        self._lbl_month.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_month.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self._lbl_month.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self._btn_next = QPushButton(">")
        self._btn_next.setFixedWidth(32)
        self._btn_next.clicked.connect(self._next_month)

        nav_row.addWidget(self._btn_prev)
        nav_row.addWidget(self._lbl_month)
        nav_row.addWidget(self._btn_next)
        layout.addLayout(nav_row)

        # Tabelle – erweitert um Organist-Spalte
        cols = ["Datum", "Zeit", "Ort", "Pfarrer*in", "Organist", "Kollekte", "Typ", "Besonderheiten"]
        col_widths = [100, 60, 120, 140, 130, 180, 130, 160]

        self._table = QTableWidget(0, len(cols))
        self._table.setHorizontalHeaderLabels(cols)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)

        hdr = self._table.horizontalHeader()
        for i, w in enumerate(col_widths):
            if i == len(col_widths) - 1:
                hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            else:
                self._table.setColumnWidth(i, w)
                hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)

        self._table.cellDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._table)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_new = QPushButton("Neuer Gottesdienst")
        self._btn_new.setObjectName("primaryButton")
        self._btn_new.clicked.connect(self._new_entry)

        self._btn_edit = QPushButton("Bearbeiten")
        self._btn_edit.clicked.connect(self._edit_selected)

        self._btn_delete = QPushButton("Löschen")
        self._btn_delete.clicked.connect(self._delete_selected)

        btn_row.addWidget(self._btn_new)
        btn_row.addWidget(self._btn_edit)
        btn_row.addWidget(self._btn_delete)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    # ── Daten ─────────────────────────────────────────────────────────────────

    def _load_and_refresh(self) -> None:
        self._gottesdienste = _load_json(_GOTTESDIENSTE_PATH, [])  # type: ignore[assignment]
        self._refresh_table()

    def _save(self) -> None:
        _save_json(_GOTTESDIENSTE_PATH, self._gottesdienste)

    def _refresh_table(self) -> None:
        self._lbl_month.setText(
            datetime(self._current_year, self._current_month, 1).strftime("%B %Y")
        )
        month_entries = [
            g for g in self._gottesdienste
            if self._entry_in_month(g, self._current_year, self._current_month)
        ]
        month_entries.sort(key=lambda g: (g.get("datum", ""), g.get("uhrzeit", "")))

        today_str = date.today().isoformat()
        self._table.setRowCount(0)

        for entry in month_entries:
            row = self._table.rowCount()
            self._table.insertRow(row)

            datum_str = entry.get("datum", "")
            try:
                d = date.fromisoformat(datum_str)
                datum_disp = d.strftime("%d.%m.%Y")
            except Exception:
                datum_disp = datum_str

            values = [
                datum_disp,
                entry.get("uhrzeit", ""),
                entry.get("ort", ""),
                entry.get("pfarrer_in", ""),
                entry.get("organist", ""),
                entry.get("kollekte_zweck", ""),
                entry.get("liturgie_typ", ""),
                entry.get("besonderheiten", ""),
            ]

            is_past = datum_str < today_str
            is_today = datum_str == today_str

            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setData(Qt.ItemDataRole.UserRole, entry.get("id"))
                if is_today:
                    item.setBackground(QColor("#E3F2FD"))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                elif is_past:
                    item.setForeground(QColor("#9E9E9E"))
                self._table.setItem(row, col, item)

    @staticmethod
    def _entry_in_month(entry: dict, year: int, month: int) -> bool:
        try:
            d = date.fromisoformat(entry.get("datum", ""))
            return d.year == year and d.month == month
        except Exception:
            return False

    def _selected_entry_id(self) -> Optional[str]:
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _find_entry(self, entry_id: str) -> Optional[dict]:
        return next((g for g in self._gottesdienste if g.get("id") == entry_id), None)

    # ── Navigationsbuttons ────────────────────────────────────────────────────

    def _prev_month(self) -> None:
        self._current_month -= 1
        if self._current_month < 1:
            self._current_month = 12
            self._current_year -= 1
        self._refresh_table()

    def _next_month(self) -> None:
        self._current_month += 1
        if self._current_month > 12:
            self._current_month = 1
            self._current_year += 1
        self._refresh_table()

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def _new_entry(self) -> None:
        dlg = GottesdienstDialog(parent=self)
        # Pre-fill date to first day of current month view
        dlg._ed_datum.setDate(QDate(self._current_year, self._current_month, 1))
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._gottesdienste.append(dlg.get_data())
            self._save()
            self._refresh_table()

    def _edit_selected(self) -> None:
        entry_id = self._selected_entry_id()
        if not entry_id:
            QMessageBox.information(self, "Kein Eintrag", "Bitte zuerst einen Gottesdienst auswählen.")
            return
        entry = self._find_entry(entry_id)
        if not entry:
            return
        dlg = GottesdienstDialog(entry=entry, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            updated = dlg.get_data()
            idx = next(
                (i for i, g in enumerate(self._gottesdienste) if g.get("id") == entry_id), None
            )
            if idx is not None:
                self._gottesdienste[idx] = updated
                self._save()
                self._refresh_table()

    def _delete_selected(self) -> None:
        entry_id = self._selected_entry_id()
        if not entry_id:
            QMessageBox.information(self, "Kein Eintrag", "Bitte zuerst einen Gottesdienst auswählen.")
            return
        entry = self._find_entry(entry_id)
        if not entry:
            return
        try:
            d = date.fromisoformat(entry.get("datum", ""))
            datum_disp = d.strftime("%d.%m.%Y")
        except Exception:
            datum_disp = entry.get("datum", "?")
        answer = QMessageBox.question(
            self,
            "Gottesdienst löschen",
            f"Gottesdienst vom {datum_disp} wirklich löschen?",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._gottesdienste = [g for g in self._gottesdienste if g.get("id") != entry_id]
            self._save()
            self._refresh_table()

    def _on_double_click(self, row: int, _col: int) -> None:
        item = self._table.item(row, 0)
        if not item:
            return
        entry_id = item.data(Qt.ItemDataRole.UserRole)
        entry = self._find_entry(entry_id) if entry_id else None
        if not entry:
            return
        dlg = GottesdienstDialog(entry=entry, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            updated = dlg.get_data()
            idx = next(
                (i for i, g in enumerate(self._gottesdienste) if g.get("id") == entry_id), None
            )
            if idx is not None:
                self._gottesdienste[idx] = updated
                self._save()
                self._refresh_table()


# ── Sub-Tab 2: Abkündigung ────────────────────────────────────────────────────


class _AbkuendigungTab(QWidget):
    """Generator für die Abkündigung (lokal, ohne KI)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Eingabezeile
        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        lbl_date = QLabel("Datum des Gottesdienstes:")
        input_row.addWidget(lbl_date)

        self._ed_datum = QDateEdit()
        self._ed_datum.setCalendarPopup(True)
        self._ed_datum.setDisplayFormat("dd.MM.yyyy")
        self._ed_datum.setDate(QDate.currentDate())
        self._ed_datum.setFixedWidth(130)
        input_row.addWidget(self._ed_datum)

        self._btn_generate = QPushButton("Abkündigung generieren")
        self._btn_generate.setObjectName("primaryButton")
        self._btn_generate.clicked.connect(self._generate)
        input_row.addWidget(self._btn_generate)
        input_row.addStretch()
        layout.addLayout(input_row)

        # Textbereich
        self._text_output = QTextEdit()
        self._text_output.setReadOnly(True)
        self._text_output.setPlaceholderText(
            "Hier erscheint der generierte Abkündigungstext …"
        )
        layout.addWidget(self._text_output)

        # Kopieren
        btn_row = QHBoxLayout()
        self._btn_copy = QPushButton("In Zwischenablage kopieren")
        self._btn_copy.clicked.connect(self._copy_to_clipboard)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_copy)
        layout.addLayout(btn_row)

    def _generate(self) -> None:
        qd = self._ed_datum.date()
        chosen_date = date(qd.year(), qd.month(), qd.day())
        chosen_iso = chosen_date.isoformat()

        gottesdienste: list[dict] = _load_json(_GOTTESDIENSTE_PATH, [])  # type: ignore[assignment]
        kollektenplan: list[dict] = _load_json(_KOLLEKTENPLAN_PATH, [])  # type: ignore[assignment]

        # Letzter Gottesdienst VOR dem gewählten Datum mit Kollekte-Buchung
        past = [
            g for g in gottesdienste
            if g.get("datum", "") < chosen_iso and g.get("kollekte_zweck", "").strip()
        ]
        past.sort(key=lambda g: (g.get("datum", ""), g.get("uhrzeit", "")))
        last_gd = past[-1] if past else None

        # Nächsten Kollektenzweck aus dem Kollektenplan für das gewählte Datum
        plan_zweck = self._find_kollektenplan_zweck(kollektenplan, chosen_date)

        # Text aufbauen
        date_disp = chosen_date.strftime("%d.%m.%Y")
        lines: list[str] = [f"Abkündigung – {date_disp}", ""]

        if last_gd:
            try:
                ld = date.fromisoformat(last_gd["datum"])
                last_datum_disp = ld.strftime("%d.%m.%Y")
            except Exception:
                last_datum_disp = last_gd.get("datum", "?")
            last_zweck = last_gd.get("kollekte_zweck", "unbekannt")
            lines.append(
                f"Herzlichen Dank für Ihre Kollekte am {last_datum_disp} für {last_zweck}."
            )
        else:
            lines.append(
                "Hinweis: Es wurde kein vorheriger Gottesdienst mit Kollekte-Buchung gefunden."
            )

        lines.append("")

        if plan_zweck:
            lines.append(f"Die heutige Kollekte gilt: {plan_zweck}.")
        else:
            lines.append("Die heutige Kollekte gilt: bitte eintragen.")

        self._text_output.setPlainText("\n".join(lines))

    @staticmethod
    def _find_kollektenplan_zweck(
        kollektenplan: list[dict], target: date
    ) -> Optional[str]:
        """Gibt den Kollektenzweck aus dem Plan für das Zieldatum zurück.

        Sucht zuerst exakte Datum-Übereinstimmung, dann nächsten Eintrag >= target.
        """
        target_iso = target.isoformat()
        for entry in kollektenplan:
            eintrag_datum = entry.get("datum", "") or entry.get("date", "")
            if eintrag_datum == target_iso:
                return str(entry.get("zweck", "") or entry.get("kollekte_zweck", "") or "")

        # Nächster Eintrag auf oder nach dem Datum
        candidates = [
            e for e in kollektenplan
            if (e.get("datum") or e.get("date", "")) >= target_iso
        ]
        candidates.sort(key=lambda e: e.get("datum") or e.get("date") or "")
        if candidates:
            best = candidates[0]
            return str(best.get("zweck", "") or best.get("kollekte_zweck", "") or "")
        return None

    def _copy_to_clipboard(self) -> None:
        text = self._text_output.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(text)


# ── Sub-Tab 3: Import ─────────────────────────────────────────────────────────

# Spaltenzuordnung: (Anzeigename, interner Schlüssel)
_IMPORT_SPALTEN = [
    ("Spalte Datum", "datum"),
    ("Spalte Uhrzeit", "uhrzeit"),
    ("Spalte Pfarrer/in", "pfarrer_in"),
    ("Spalte Organist", "organist"),
    ("Spalte Kollekte Zweck", "kollekte_zweck"),
    ("Spalte Ort", "ort"),
]

_NO_COLUMN = "– keine –"


class _ImportTab(QWidget):
    """Import von Jahresplanung aus Excel-/CSV-Datei."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._headers: list[str] = []
        self._rows: list[list] = []   # raw data rows (ohne Header)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # Titel
        title = QLabel("Jahresplanung aus Excel-Datei importieren")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(title)

        # Datei-Auswahl
        file_row = QHBoxLayout()
        file_row.setSpacing(8)
        self._ed_filepath = QLineEdit()
        self._ed_filepath.setReadOnly(True)
        self._ed_filepath.setPlaceholderText("Noch keine Datei gewählt …")
        self._btn_choose = QPushButton("Datei wählen …")
        self._btn_choose.clicked.connect(self._choose_file)
        file_row.addWidget(self._ed_filepath, 1)
        file_row.addWidget(self._btn_choose)
        layout.addLayout(file_row)

        # Spaltenzuordnung
        form = QFormLayout()
        form.setSpacing(8)
        self._col_combos: dict[str, QComboBox] = {}
        for label, key in _IMPORT_SPALTEN:
            cb = QComboBox()
            cb.addItem(_NO_COLUMN)
            self._col_combos[key] = cb
            form.addRow(f"{label}:", cb)
        layout.addLayout(form)

        # Option: Überschreiben
        self._chk_overwrite = QCheckBox("Bestehende Einträge überschreiben (gleicher Tag)")
        layout.addWidget(self._chk_overwrite)

        # Vorschau-Tabelle
        self._preview_table = QTableWidget(0, 0)
        self._preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._preview_table.setAlternatingRowColors(True)
        self._preview_table.verticalHeader().setVisible(False)
        self._preview_table.setMinimumHeight(140)
        layout.addWidget(self._preview_table)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._btn_preview = QPushButton("Vorschau")
        self._btn_preview.clicked.connect(self._show_preview)
        self._btn_import = QPushButton("Importieren")
        self._btn_import.setObjectName("primaryButton")
        self._btn_import.clicked.connect(self._do_import)
        self._lbl_status = QLabel("")
        btn_row.addWidget(self._btn_preview)
        btn_row.addWidget(self._btn_import)
        btn_row.addStretch()
        btn_row.addWidget(self._lbl_status)
        layout.addLayout(btn_row)

    # ── Datei wählen ──────────────────────────────────────────────────────────

    def _choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Jahresplanung öffnen",
            "",
            "Tabellen (*.xlsx *.xls *.csv);;Alle Dateien (*)",
        )
        if not path:
            return
        self._ed_filepath.setText(path)
        self._lbl_status.setText("")
        try:
            headers, rows = _read_file(path)
        except Exception as exc:
            QMessageBox.critical(self, "Fehler beim Lesen", str(exc))
            return
        self._headers = headers
        self._rows = rows
        self._populate_combos(headers)
        self._preview_table.setRowCount(0)
        self._preview_table.setColumnCount(0)

    def _populate_combos(self, headers: list[str]) -> None:
        """Befüllt alle Spalten-ComboBoxen mit den erkannten Spaltenbezeichnungen."""
        # Automatische Zuordnung nach Schlüsselwörtern
        auto_map: dict[str, str] = {}
        for h in headers:
            hl = h.lower()
            if any(k in hl for k in ("datum", "date")):
                auto_map.setdefault("datum", h)
            if any(k in hl for k in ("uhrzeit", "zeit", "time")):
                auto_map.setdefault("uhrzeit", h)
            if any(k in hl for k in ("pfarrer", "pfarrerin", "pfarr")):
                auto_map.setdefault("pfarrer_in", h)
            if any(k in hl for k in ("organist", "orgel", "musik")):
                auto_map.setdefault("organist", h)
            if any(k in hl for k in ("kollekte", "zweck", "verwendung")):
                auto_map.setdefault("kollekte_zweck", h)
            if any(k in hl for k in ("ort", "kirche", "location")):
                auto_map.setdefault("ort", h)

        for key, cb in self._col_combos.items():
            cb.blockSignals(True)
            cb.clear()
            cb.addItem(_NO_COLUMN)
            for h in headers:
                cb.addItem(h)
            # Auto-Vorauswahl
            if key in auto_map:
                idx = cb.findText(auto_map[key])
                if idx >= 0:
                    cb.setCurrentIndex(idx)
            cb.blockSignals(False)

    # ── Vorschau ──────────────────────────────────────────────────────────────

    def _show_preview(self) -> None:
        if not self._headers:
            QMessageBox.information(self, "Keine Datei", "Bitte zuerst eine Datei wählen.")
            return
        preview_rows = self._rows[:5]
        self._preview_table.setRowCount(len(preview_rows))
        self._preview_table.setColumnCount(len(self._headers))
        self._preview_table.setHorizontalHeaderLabels(self._headers)
        for r, row in enumerate(preview_rows):
            for c, val in enumerate(row):
                self._preview_table.setItem(r, c, QTableWidgetItem(str(val) if val is not None else ""))
        self._preview_table.resizeColumnsToContents()

    # ── Import ────────────────────────────────────────────────────────────────

    def _do_import(self) -> None:
        if not self._headers:
            QMessageBox.information(self, "Keine Datei", "Bitte zuerst eine Datei wählen.")
            return

        # Spaltenzuordnung auslesen
        col_idx: dict[str, Optional[int]] = {}
        for key, cb in self._col_combos.items():
            text = cb.currentText()
            if text == _NO_COLUMN:
                col_idx[key] = None
            else:
                try:
                    col_idx[key] = self._headers.index(text)
                except ValueError:
                    col_idx[key] = None

        if col_idx["datum"] is None:
            QMessageBox.warning(self, "Keine Datum-Spalte", "Bitte mindestens die Datum-Spalte zuordnen.")
            return

        overwrite = self._chk_overwrite.isChecked()

        # Bestehende Daten laden
        gottesdienste: list[dict] = _load_json(_GOTTESDIENSTE_PATH, [])  # type: ignore[assignment]
        kollektenplan: list[dict] = _load_json(_KOLLEKTENPLAN_PATH, [])  # type: ignore[assignment]

        # Index der bestehenden GD nach Datum
        existing_by_date: dict[str, int] = {
            g["datum"]: i for i, g in enumerate(gottesdienste) if g.get("datum")
        }
        # Index des bestehenden Kollektenplans nach Datum
        kp_by_date: dict[str, int] = {
            e["datum"]: i for i, e in enumerate(kollektenplan) if e.get("datum")
        }

        added = 0
        skipped = 0
        kp_added = 0

        for raw_row in self._rows:
            def _cell(key: str) -> str:
                idx = col_idx.get(key)
                if idx is None or idx >= len(raw_row):
                    return ""
                val = raw_row[idx]
                return str(val).strip() if val is not None else ""

            datum_iso = _parse_date_value(
                raw_row[col_idx["datum"]] if col_idx["datum"] is not None and col_idx["datum"] < len(raw_row) else None
            )
            if not datum_iso:
                skipped += 1
                continue

            new_entry: dict = {
                "id": str(uuid.uuid4()),
                "datum": datum_iso,
                "uhrzeit": _cell("uhrzeit"),
                "ort": _cell("ort"),
                "liturgie_typ": "",
                "pfarrer_in": _cell("pfarrer_in"),
                "organist": _cell("organist"),
                "kollekte_zweck": _cell("kollekte_zweck"),
                "kollekte_aobj": "",
                "besonderheiten": "",
                "notiz": "",
            }

            if datum_iso in existing_by_date:
                if overwrite:
                    # ID des bestehenden Eintrags behalten
                    existing_idx = existing_by_date[datum_iso]
                    new_entry["id"] = gottesdienste[existing_idx].get("id", new_entry["id"])
                    gottesdienste[existing_idx] = new_entry
                    added += 1
                else:
                    skipped += 1
            else:
                gottesdienste.append(new_entry)
                existing_by_date[datum_iso] = len(gottesdienste) - 1
                added += 1

            # Kollektenplan parallel befüllen
            zweck = _cell("kollekte_zweck")
            if zweck:
                kp_entry = {
                    "datum": datum_iso,
                    "zweck": zweck,
                    "empfaenger": "",
                    "aobj_vorschlag": "",
                }
                if datum_iso in kp_by_date:
                    if overwrite:
                        kollektenplan[kp_by_date[datum_iso]] = kp_entry
                        kp_added += 1
                else:
                    kollektenplan.append(kp_entry)
                    kp_by_date[datum_iso] = len(kollektenplan) - 1
                    kp_added += 1

        _save_json(_GOTTESDIENSTE_PATH, gottesdienste)
        _save_json(_KOLLEKTENPLAN_PATH, kollektenplan)

        self._lbl_status.setText(
            f"{added} neue Einträge importiert, {skipped} übersprungen"
            + (f", {kp_added} Kollektenplan-Einträge" if kp_added else "")
        )
        QMessageBox.information(
            self,
            "Import abgeschlossen",
            f"{added} Gottesdienst-Einträge importiert.\n"
            f"{skipped} Einträge übersprungen.\n"
            + (f"{kp_added} Kollektenplan-Einträge aktualisiert." if kp_added else ""),
        )


# ── Datei-Reader ──────────────────────────────────────────────────────────────


def _read_file(path: str) -> tuple[list[str], list[list]]:
    """Liest eine Excel- oder CSV-Datei und gibt (headers, rows) zurück.

    Die erste nicht-leere Zeile wird als Header-Zeile verwendet.
    """
    p = Path(path)
    suffix = p.suffix.lower()

    if suffix in (".xlsx", ".xls"):
        return _read_excel(path)
    elif suffix == ".csv":
        return _read_csv(path)
    else:
        raise ValueError(f"Nicht unterstütztes Dateiformat: {suffix}")


def _read_excel(path: str) -> tuple[list[str], list[list]]:
    try:
        import openpyxl
    except ImportError as exc:
        raise ImportError("openpyxl ist nicht installiert. Bitte 'uv pip install openpyxl' ausführen.") from exc

    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active

    all_rows: list[list] = []
    for row in ws.iter_rows(values_only=True):
        all_rows.append(list(row))

    # Erste nicht-leere Zeile als Header
    header_idx = 0
    for i, row in enumerate(all_rows):
        if any(cell is not None and str(cell).strip() for cell in row):
            header_idx = i
            break

    headers = [str(c).strip() if c is not None else f"Spalte {j+1}" for j, c in enumerate(all_rows[header_idx])]
    data_rows = all_rows[header_idx + 1:]
    # Leere Zeilen am Ende entfernen
    data_rows = [r for r in data_rows if any(c is not None and str(c).strip() for c in r)]
    return headers, data_rows


def _read_csv(path: str) -> tuple[list[str], list[list]]:
    # Versuche Encoding und Delimiter automatisch zu erkennen
    for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            with open(path, newline="", encoding=encoding) as f:
                sample = f.read(4096)
            break
        except UnicodeDecodeError:
            continue
    else:
        encoding = "latin-1"

    # Delimiter erkennen
    import io
    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(sample, delimiters=",;\t|")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ";"

    all_rows: list[list] = []
    with open(path, newline="", encoding=encoding) as f:
        reader = csv.reader(f, delimiter=delimiter)
        for row in reader:
            all_rows.append(row)

    # Erste nicht-leere Zeile als Header
    header_idx = 0
    for i, row in enumerate(all_rows):
        if any(str(c).strip() for c in row):
            header_idx = i
            break

    headers = [str(c).strip() if c else f"Spalte {j+1}" for j, c in enumerate(all_rows[header_idx])]
    data_rows = all_rows[header_idx + 1:]
    data_rows = [r for r in data_rows if any(str(c).strip() for c in r)]
    return headers, data_rows


# ── Haupt-Widget ──────────────────────────────────────────────────────────────


class GottesdienstTab(QWidget):
    """Tab für Gottesdienst-Management und Abkündigungs-Generator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sub_tabs = QTabWidget()
        sub_tabs.tabBar().setExpanding(False)

        self._plan_tab = _PlanTab()
        self._import_tab = _ImportTab()
        self._abkuendigung_tab = _AbkuendigungTab()

        sub_tabs.addTab(self._plan_tab, "Gottesdienstplan")
        sub_tabs.addTab(self._import_tab, "Import")
        sub_tabs.addTab(self._abkuendigung_tab, "Abkündigung")

        layout.addWidget(sub_tabs)
