"""Wiedervorlagen / Fristen-Management Tab."""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

_DATA_FILE = Path(__file__).parent.parent.parent / "data" / "state" / "wiedervorlagen.json"

_KATEGORIEN = ["Finanzen", "Personal", "Gebäude", "Gottesdienst", "Kirchenvorstand", "Allgemein"]
_PRIORITAETEN = ["hoch", "normal", "niedrig"]

_COLOR_OVERDUE = QColor("#FFEBEE")
_COLOR_SOON = QColor("#FFF8E1")
_COLOR_WEEK = QColor("#F3E5F5")
_COLOR_DONE = QColor("#EEEEEE")


def _load_data() -> list[dict]:
    if _DATA_FILE.exists():
        try:
            return json.loads(_DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_data(entries: list[dict]) -> None:
    _DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    _DATA_FILE.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_date(value: str) -> Optional[date]:
    try:
        return date.fromisoformat(value)
    except Exception:
        return None


def _row_color(entry: dict) -> Optional[QColor]:
    if entry.get("erledigt"):
        return _COLOR_DONE
    frist = _parse_date(entry.get("frist_datum", ""))
    if frist is None:
        return None
    today = date.today()
    delta = (frist - today).days
    if delta < 0:
        return _COLOR_OVERDUE
    if delta <= 1:
        return _COLOR_SOON
    if delta <= 7:
        return _COLOR_WEEK
    return None


def _status_icon(entry: dict) -> str:
    if entry.get("erledigt"):
        return "✓"
    frist = _parse_date(entry.get("frist_datum", ""))
    if frist and frist < date.today():
        return "!"
    return "·"


def _sort_key(entry: dict):
    erledigt = 1 if entry.get("erledigt") else 0
    frist_str = entry.get("frist_datum", "9999-12-31") or "9999-12-31"
    return (erledigt, frist_str)


class _EditDialog(QDialog):
    def __init__(self, entry: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self._entry = entry or {}
        self.setWindowTitle("Wiedervorlage bearbeiten" if entry else "Neue Wiedervorlage")
        self.setMinimumWidth(440)
        self._build_ui()
        if entry:
            self._load_values(entry)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(8)

        self._ed_titel = QLineEdit()
        self._ed_titel.setPlaceholderText("Kurztitel der Wiedervorlage")
        form.addRow("Titel:", self._ed_titel)

        self._ed_frist = QDateEdit()
        self._ed_frist.setCalendarPopup(True)
        self._ed_frist.setDisplayFormat("dd.MM.yyyy")
        from PySide6.QtCore import QDate
        self._ed_frist.setDate(QDate.currentDate())
        form.addRow("Frist:", self._ed_frist)

        self._cb_kategorie = QComboBox()
        for k in _KATEGORIEN:
            self._cb_kategorie.addItem(k)
        form.addRow("Kategorie:", self._cb_kategorie)

        self._cb_prioritaet = QComboBox()
        for p in _PRIORITAETEN:
            self._cb_prioritaet.addItem(p)
        form.addRow("Priorität:", self._cb_prioritaet)

        self._ed_az = QLineEdit()
        self._ed_az.setPlaceholderText("Aktenzeichen")
        form.addRow("AZ:", self._ed_az)

        self._ed_notiz = QTextEdit()
        self._ed_notiz.setPlaceholderText("Notizen zur Wiedervorlage…")
        self._ed_notiz.setFixedHeight(80)
        form.addRow("Notiz:", self._ed_notiz)

        self._cb_erledigt = QCheckBox("Erledigt")
        form.addRow("", self._cb_erledigt)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_values(self, entry: dict) -> None:
        from PySide6.QtCore import QDate
        self._ed_titel.setText(entry.get("titel", ""))
        frist = _parse_date(entry.get("frist_datum", ""))
        if frist:
            self._ed_frist.setDate(QDate(frist.year, frist.month, frist.day))
        idx = self._cb_kategorie.findText(entry.get("kategorie", ""))
        if idx >= 0:
            self._cb_kategorie.setCurrentIndex(idx)
        idx = self._cb_prioritaet.findText(entry.get("prioritaet", "normal"))
        if idx >= 0:
            self._cb_prioritaet.setCurrentIndex(idx)
        self._ed_az.setText(entry.get("az", ""))
        self._ed_notiz.setPlainText(entry.get("notiz", ""))
        self._cb_erledigt.setChecked(bool(entry.get("erledigt", False)))

    def _on_accept(self) -> None:
        if not self._ed_titel.text().strip():
            QMessageBox.warning(self, "Pflichtfeld", "Bitte einen Titel eingeben.")
            return
        self.accept()

    def get_values(self) -> dict:
        qd = self._ed_frist.date()
        frist = date(qd.year(), qd.month(), qd.day()).isoformat()
        return {
            "titel": self._ed_titel.text().strip(),
            "frist_datum": frist,
            "kategorie": self._cb_kategorie.currentText(),
            "prioritaet": self._cb_prioritaet.currentText(),
            "az": self._ed_az.text().strip(),
            "notiz": self._ed_notiz.toPlainText().strip(),
            "erledigt": self._cb_erledigt.isChecked(),
        }


class VerwaltungTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: list[dict] = []
        self._build_ui()
        self._load()

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        lbl = QLabel("Wiedervorlagen / Fristen")
        lbl.setObjectName("sectionHeader")
        layout.addWidget(lbl)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self._btn_neu = QPushButton("Neu")
        self._btn_neu.setObjectName("primaryButton")
        self._btn_neu.clicked.connect(self._on_neu)

        self._btn_erledigt = QPushButton("Erledigt")
        self._btn_erledigt.clicked.connect(self._on_toggle_erledigt)

        self._btn_loeschen = QPushButton("Löschen")
        self._btn_loeschen.clicked.connect(self._on_loeschen)

        toolbar.addWidget(self._btn_neu)
        toolbar.addWidget(self._btn_erledigt)
        toolbar.addWidget(self._btn_loeschen)
        toolbar.addSpacing(16)

        lbl_kat = QLabel("Kategorie:")
        lbl_kat.setObjectName("hint")
        toolbar.addWidget(lbl_kat)

        self._cb_filter_kat = QComboBox()
        self._cb_filter_kat.addItem("Alle")
        for k in _KATEGORIEN:
            self._cb_filter_kat.addItem(k)
        self._cb_filter_kat.currentIndexChanged.connect(self._refresh_table)
        toolbar.addWidget(self._cb_filter_kat)

        lbl_status = QLabel("Status:")
        lbl_status.setObjectName("hint")
        toolbar.addWidget(lbl_status)

        self._cb_filter_status = QComboBox()
        self._cb_filter_status.addItems(["Alle", "Offen", "Erledigt"])
        self._cb_filter_status.currentIndexChanged.connect(self._refresh_table)
        toolbar.addWidget(self._cb_filter_status)

        toolbar.addSpacing(16)
        self._lbl_count = QLabel("0 Einträge")
        self._lbl_count.setObjectName("hint")
        toolbar.addWidget(self._lbl_count)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Tabelle
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(["", "Frist", "Titel", "Kategorie", "AZ", "Notiz"])
        header = self._table.horizontalHeader()
        col_widths = [30, 100, 300, 120, 120, 200]
        for i, w in enumerate(col_widths):
            self._table.setColumnWidth(i, w)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        for i in range(5):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)

        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(False)
        self._table.verticalHeader().setVisible(False)
        self._table.itemDoubleClicked.connect(self._on_double_click)

        layout.addWidget(self._table)

    # ── Daten laden / speichern ────────────────────────────────────────────────

    def _load(self) -> None:
        self._entries = _load_data()
        self._refresh_table()

    def _save(self) -> None:
        _save_data(self._entries)

    # ── Tabelle befüllen ───────────────────────────────────────────────────────

    def _filtered_entries(self) -> list[dict]:
        kat_filter = self._cb_filter_kat.currentText()
        status_filter = self._cb_filter_status.currentText()

        result = []
        for entry in self._entries:
            if kat_filter != "Alle" and entry.get("kategorie") != kat_filter:
                continue
            if status_filter == "Offen" and entry.get("erledigt"):
                continue
            if status_filter == "Erledigt" and not entry.get("erledigt"):
                continue
            result.append(entry)

        result.sort(key=_sort_key)
        return result

    def _refresh_table(self) -> None:
        filtered = self._filtered_entries()
        self._table.setRowCount(0)

        italic_font = QFont()
        italic_font.setItalic(True)

        for entry in filtered:
            row = self._table.rowCount()
            self._table.insertRow(row)

            frist = _parse_date(entry.get("frist_datum", ""))
            frist_str = frist.strftime("%d.%m.%Y") if frist else ""

            icon_item = QTableWidgetItem(_status_icon(entry))
            icon_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if entry.get("erledigt"):
                icon_item.setForeground(QColor("#4CAF50"))
            elif _status_icon(entry) == "!":
                icon_item.setForeground(QColor("#F44336"))

            values = [
                icon_item,
                QTableWidgetItem(frist_str),
                QTableWidgetItem(entry.get("titel", "")),
                QTableWidgetItem(entry.get("kategorie", "")),
                QTableWidgetItem(entry.get("az", "")),
                QTableWidgetItem(entry.get("notiz", "").replace("\n", " ")),
            ]
            for col, item in enumerate(values):
                if isinstance(item, str):
                    item = QTableWidgetItem(item)
                if col == 1:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                color = _row_color(entry)
                if color:
                    item.setBackground(color)
                if entry.get("erledigt"):
                    item.setForeground(QColor("#9E9E9E"))
                    item.setFont(italic_font)
                # store entry id on first column for lookup
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, entry.get("id"))
                self._table.setItem(row, col, item)

        total = len(filtered)
        self._lbl_count.setText(f"{total} {'Eintrag' if total == 1 else 'Einträge'}")

    # ── Aktionen ───────────────────────────────────────────────────────────────

    def _current_entry_id(self) -> Optional[str]:
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _find_entry(self, entry_id: str) -> Optional[dict]:
        for entry in self._entries:
            if entry.get("id") == entry_id:
                return entry
        return None

    def _on_neu(self) -> None:
        dlg = _EditDialog(parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        values = dlg.get_values()
        new_entry = {
            "id": str(uuid.uuid4()),
            "erstellt_am": date.today().isoformat(),
            "quelle": "",
            **values,
        }
        self._entries.append(new_entry)
        self._save()
        self._refresh_table()

    def _on_toggle_erledigt(self) -> None:
        entry_id = self._current_entry_id()
        if not entry_id:
            QMessageBox.information(self, "Keine Auswahl", "Bitte einen Eintrag auswählen.")
            return
        entry = self._find_entry(entry_id)
        if entry is None:
            return
        entry["erledigt"] = not entry.get("erledigt", False)
        self._save()
        self._refresh_table()

    def _on_loeschen(self) -> None:
        entry_id = self._current_entry_id()
        if not entry_id:
            QMessageBox.information(self, "Keine Auswahl", "Bitte einen Eintrag auswählen.")
            return
        entry = self._find_entry(entry_id)
        if entry is None:
            return
        titel = entry.get("titel", "")
        reply = QMessageBox.question(
            self,
            "Löschen",
            f"Eintrag '{titel}' wirklich löschen?",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._entries = [e for e in self._entries if e.get("id") != entry_id]
        self._save()
        self._refresh_table()

    def _on_double_click(self, item: QTableWidgetItem) -> None:
        entry_id = self._current_entry_id()
        if not entry_id:
            return
        entry = self._find_entry(entry_id)
        if entry is None:
            return
        dlg = _EditDialog(entry=entry, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        values = dlg.get_values()
        entry.update(values)
        self._save()
        self._refresh_table()

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_faellige_anzahl(self) -> int:
        """Gibt Anzahl der heute oder morgen fälligen, nicht erledigten Einträge zurück."""
        today = date.today()
        count = 0
        for entry in self._entries:
            if entry.get("erledigt"):
                continue
            frist = _parse_date(entry.get("frist_datum", ""))
            if frist is None:
                continue
            delta = (frist - today).days
            if 0 <= delta <= 1:
                count += 1
        return count
