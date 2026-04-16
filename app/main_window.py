"""Hauptfenster der Kollekten-Automation (PySide6, Office-2010-Stil)."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, QTimer, Qt, Signal, QObject
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QMenu,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from booking_store import get_booking_rows
from collection_ops import delete_records
from app.ai.chat_widget import ChatWidget
from app.documents import (
    DocumentSource,
    WorkFileEntry,
    add_year_plan_file,
    load_sources,
    load_workfiles,
    open_workfile,
    refresh_source,
    remove_year_plan_file,
    search_sources,
    save_sources,
    update_workfile_path,
    workfile_status,
)
from app.updater import APP_VERSION, UpdateInfo, UpdateBanner, start_background_check
from app.widgets.collection_table import CollectionTable
from email_sender import send_attachments
from file_actions import existing_paths, open_file, open_folder, reveal_in_explorer


class RunWorker(QObject):
    finished = Signal(int, int)
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, year_filter: Optional[int] = None, dry_run: bool = False, entry_ids: Optional[set[str]] = None):
        super().__init__()
        self.year_filter = year_filter
        self.dry_run = dry_run
        self.entry_ids = entry_ids or set()

    def run(self):
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            import logging
            import main as m

            class QtHandler(logging.Handler):
                def __init__(self, signal):
                    super().__init__()
                    self.signal = signal

                def emit(self, record):
                    self.signal.emit(self.format(record))

            handler = QtHandler(self.progress)
            handler.setFormatter(logging.Formatter("%(message)s"))
            root_logger = logging.getLogger()
            root_logger.addHandler(handler)
            try:
                processed, errors = m.run(year_filter=self.year_filter, dry_run=self.dry_run, entry_ids=self.entry_ids)
            finally:
                root_logger.removeHandler(handler)
            self.finished.emit(processed, errors)
        except Exception as exc:
            self.error.emit(str(exc))


class MultiSelectMenuButton(QPushButton):
    changed = Signal()

    def __init__(self, label: str, values: list[tuple[str, int]], parent=None):
        super().__init__(parent)
        self._base_label = label
        self._values = values
        self._selected: set[int] = set()
        self._menu = QMenu(self)
        self._actions: dict[int, QAction] = {}
        self._build_menu()
        self.setMenu(self._menu)
        self._update_text()

    def _build_menu(self) -> None:
        act_all = self._menu.addAction("Alle")
        act_all.triggered.connect(self.clear_selection)
        self._menu.addSeparator()
        for text, value in self._values:
            action = self._menu.addAction(text)
            action.setCheckable(True)
            action.toggled.connect(lambda checked, v=value: self._toggle_value(v, checked))
            self._actions[value] = action

    def _toggle_value(self, value: int, checked: bool) -> None:
        if checked:
            self._selected.add(value)
        else:
            self._selected.discard(value)
        self._update_text()
        self.changed.emit()

    def _update_text(self) -> None:
        if not self._selected:
            self.setText(f"{self._base_label}: Alle")
            return
        labels = [text for text, value in self._values if value in self._selected]
        shown = ", ".join(labels[:4])
        if len(labels) > 4:
            shown += " …"
        self.setText(f"{self._base_label}: {shown}")

    def selected_values(self) -> set[int]:
        return set(self._selected)

    def set_selected_values(self, values: set[int]) -> None:
        self._selected = set(values)
        for value, action in self._actions.items():
            action.blockSignals(True)
            action.setChecked(value in self._selected)
            action.blockSignals(False)
        self._update_text()

    def clear_selection(self) -> None:
        self.set_selected_values(set())
        self.changed.emit()


def _make_status_card(title: str, value: str, kind: str = "normal") -> QFrame:
    card = QFrame()
    card_kind = {"ok": "statusCardOk", "warn": "statusCardWarn", "error": "statusCardError"}
    card.setObjectName(card_kind.get(kind, "statusCard"))
    layout = QVBoxLayout(card)
    layout.setContentsMargins(8, 6, 8, 6)
    layout.setSpacing(2)

    lbl_title = QLabel(title)
    lbl_title.setObjectName("hint")
    layout.addWidget(lbl_title)

    lbl_value = QLabel(value)
    lbl_value.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
    layout.addWidget(lbl_value)

    return card


def _set_card_value(card: QFrame, text: str, new_object_name: str | None = None):
    labels = card.findChildren(QLabel)
    if len(labels) >= 2:
        labels[1].setText(text)
    if new_object_name and card.objectName() != new_object_name:
        card.setObjectName(new_object_name)
        card.style().unpolish(card)
        card.style().polish(card)


class UebersichtTab(QWidget):
    run_requested = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._recent_records: list[dict] = []
        self._build_ui()

    def _build_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(170)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(8, 16, 8, 8)
        sb_layout.setSpacing(0)

        self._lbl_gemeinde_name = QLabel("—")
        self._lbl_gemeinde_name.setObjectName("sidebarValue")
        self._lbl_gemeinde_name.setWordWrap(True)
        lbl_g = QLabel("Gemeinde")
        lbl_g.setObjectName("sidebarLabel")
        sb_layout.addWidget(lbl_g)
        sb_layout.addWidget(self._lbl_gemeinde_name)
        sb_layout.addSpacing(12)

        self._lbl_next_run = QLabel("—")
        self._lbl_next_run.setObjectName("sidebarValue")
        lbl_n = QLabel("Nächster Lauf")
        lbl_n.setObjectName("sidebarLabel")
        sb_layout.addWidget(lbl_n)
        sb_layout.addWidget(self._lbl_next_run)
        sb_layout.addStretch()
        outer.addWidget(sidebar)

        main = QWidget()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        lbl_title = QLabel("Übersicht")
        lbl_title.setObjectName("sectionHeader")
        main_layout.addWidget(lbl_title)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(8)
        self._card_last_run = _make_status_card("Letzter Lauf", "—")
        self._card_processed = _make_status_card("Verarbeitet", "—", "ok")
        self._card_warnings = _make_status_card("Warnungen", "—")
        cards_row.addWidget(self._card_last_run)
        cards_row.addWidget(self._card_processed)
        cards_row.addWidget(self._card_warnings)
        cards_row.addStretch()
        main_layout.addLayout(cards_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.btn_run = QPushButton("▶  Jetzt ausführen")
        self.btn_run.setObjectName("primaryButton")
        self.btn_run.setFixedHeight(30)
        self.btn_run.clicked.connect(lambda: self.run_requested.emit(False))

        self.btn_preview = QPushButton("👁  Vorschau")
        self.btn_preview.setFixedHeight(30)
        self.btn_preview.clicked.connect(lambda: self.run_requested.emit(True))

        btn_row.addWidget(self.btn_run)
        btn_row.addWidget(self.btn_preview)
        btn_row.addStretch()
        main_layout.addLayout(btn_row)

        lbl_recent = QLabel("Letzte Einträge")
        lbl_recent.setObjectName("sectionHeader")
        main_layout.addWidget(lbl_recent)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Datum", "Betrag", "Verwendungszweck", "Typ", "Datei"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.cellDoubleClicked.connect(self._on_double_click)
        main_layout.addWidget(self.table)
        outer.addWidget(main)

    def update_status(self, last_run: Optional[datetime], processed: int, warnings: int):
        run_str = last_run.strftime("%d.%m.%Y %H:%M") if last_run else "—"
        _set_card_value(self._card_last_run, run_str)
        _set_card_value(self._card_processed, str(processed))
        _set_card_value(self._card_warnings, str(warnings), "statusCardWarn" if warnings > 0 else "statusCardOk")

    def update_sidebar(self, gemeinde_name: str, next_run: str):
        self._lbl_gemeinde_name.setText(gemeinde_name or "—")
        self._lbl_next_run.setText(next_run or "Manuell")

    def add_recent_entry(self, datum: str, betrag: str, zweck: str, typ: str, datei: str, record: dict | None = None):
        row = self.table.rowCount()
        self.table.insertRow(row)
        typ_icon = "→ Weiterleit." if "weiter" in typ else "✓ Eigene"
        for col, val in enumerate([datum, betrag, zweck, typ_icon, datei]):
            item = QTableWidgetItem(val)
            if col in (0, 1, 3):
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, col, item)
        self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, record or {})

    def set_running(self, running: bool):
        self.btn_run.setEnabled(not running)
        self.btn_preview.setEnabled(not running)
        self.btn_run.setText("⏳ Läuft..." if running else "▶  Jetzt ausführen")

    def _current_record(self, row: int) -> dict | None:
        item = self.table.item(row, 0)
        if not item:
            return None
        record = item.data(Qt.ItemDataRole.UserRole)
        return record if isinstance(record, dict) else None

    def _on_double_click(self, row: int, col: int) -> None:
        if col != 4:
            return
        record = self._current_record(row)
        if not record or not open_file(str(record.get("target_file") or "")):
            QMessageBox.warning(self, "Datei fehlt", "Die zugehörige Buchungsblatt-Datei wurde nicht gefunden.")

    def _show_context_menu(self, pos) -> None:
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        record = self._current_record(row)
        if not record:
            return
        menu = QMenu(self)
        act_open = menu.addAction("Datei öffnen")
        act_folder = menu.addAction("Ordner öffnen")
        act_select = menu.addAction("Im Explorer markieren")
        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        target = str(record.get("target_file") or "")
        ok = True
        if action == act_open:
            ok = open_file(target)
        elif action == act_folder:
            ok = open_folder(target)
        elif action == act_select:
            ok = reveal_in_explorer(target)
        if action is not None and not ok:
            QMessageBox.warning(self, "Datei fehlt", "Die zugehörige Buchungsblatt-Datei wurde nicht gefunden.")


class VerlaufTab(QWidget):
    rerun_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cfg: dict | None = None
        self._selected_months: set[int] = set()
        self._selected_years: set[int] = set()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        lbl = QLabel("Verlauf & Korrektur")
        lbl.setObjectName("sectionHeader")
        layout.addWidget(lbl)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        self.month_picker = MultiSelectMenuButton("Monat", [(f"{month:02d}", month) for month in range(1, 13)])
        filter_row.addWidget(self.month_picker)

        year_values = [(str(year), year) for year in range(1990, 2101)]
        self.year_picker = MultiSelectMenuButton("Jahr", year_values)
        self.year_picker.set_selected_values({datetime.now().year})
        filter_row.addWidget(self.year_picker)

        self.only_warnings = QCheckBox("Nur Warnungen")
        filter_row.addWidget(self.only_warnings)

        self.btn_open = QPushButton("Datei öffnen")
        self.btn_open.clicked.connect(self._open_selected_files)
        self.btn_folder = QPushButton("Ordner öffnen")
        self.btn_folder.clicked.connect(lambda: self._open_selected_files(mode="folder"))
        self.btn_explorer = QPushButton("Im Explorer markieren")
        self.btn_explorer.clicked.connect(lambda: self._open_selected_files(mode="select"))
        self.btn_email_xlsx = QPushButton("XLSX per E-Mail senden")
        self.btn_email_xlsx.clicked.connect(self._email_selected_files)
        self.btn_delete = QPushButton("Löschen")
        self.btn_delete.clicked.connect(self._delete_selected_records)
        self.btn_rerun = QPushButton("Löschen + Rerun")
        self.btn_rerun.setObjectName("primaryButton")
        self.btn_rerun.clicked.connect(self._delete_and_rerun_selected_records)

        self.report_button = QPushButton("Bericht erstellen ▼")
        self.report_button.setToolTip("Monatsbericht drucken, als PDF speichern oder per E-Mail senden")
        self.report_button.clicked.connect(self._show_report_menu)
        for button in (
            self.btn_open,
            self.btn_folder,
            self.btn_explorer,
            self.btn_email_xlsx,
            self.btn_delete,
            self.btn_rerun,
        ):
            filter_row.addWidget(button)
        filter_row.addStretch()
        filter_row.addWidget(self.report_button)
        layout.addLayout(filter_row)

        self.table = CollectionTable()
        layout.addWidget(self.table)

        stats_row = QHBoxLayout()
        self.stats_label = QLabel("Eigene: 0,00 € | Weiterleitung: 0,00 € | Gesamt: 0,00 €")
        self.stats_label.setObjectName("hint")
        stats_row.addWidget(self.stats_label)
        stats_row.addStretch()
        layout.addLayout(stats_row)

        self.month_picker.changed.connect(self.reload)
        self.year_picker.changed.connect(self.reload)
        self.only_warnings.toggled.connect(self.reload)
        self.table.correction_saved.connect(self._on_correction_saved)

    def load_data(self, cfg: dict):
        self._cfg = cfg
        self.reload()

    def reload(self):
        if not self._cfg:
            return
        self._selected_months = self.month_picker.selected_values()
        self._selected_years = self.year_picker.selected_values()
        only_warnings = self.only_warnings.isChecked()
        self.table.load_data(
            self._cfg,
            only_warnings=only_warnings,
            months_filter=self._selected_months,
            years_filter=self._selected_years,
        )
        self._update_stats()

    def _update_stats(self):
        own_total = 0.0
        forward_total = 0.0
        for record in self.table.get_filtered_records():
            if self.only_warnings.isChecked() and not record.get("needs_review", False):
                continue
            try:
                amount = float(record.get("amount") or 0)
            except Exception:
                amount = 0.0
            scope = str(record.get("scope") or "")
            if "weiter" in scope:
                forward_total += amount
            else:
                own_total += amount
        total = own_total + forward_total
        self.stats_label.setText(
            "Eigene: {0} | Weiterleitung: {1} | Gesamt: {2}".format(
                _format_eur(own_total),
                _format_eur(forward_total),
                _format_eur(total),
            )
        )

    def _on_correction_saved(self, _pattern: str, _scope: str, _aobj: str):
        self.reload()

    def _show_report_menu(self) -> None:
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        act_print = menu.addAction("Drucken…")
        act_preview = menu.addAction("Vorschau…")
        act_pdf = menu.addAction("Als PDF speichern…")
        act_email = menu.addAction("Per E-Mail senden")
        action = menu.exec(self.report_button.mapToGlobal(
            self.report_button.rect().bottomLeft()
        ))
        if action is None:
            return
        self._run_report_action(action, act_print, act_preview, act_pdf, act_email)

    def _run_report_action(self, action, act_print, act_preview, act_pdf, act_email) -> None:
        if self._cfg is None:
            return
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        from app.reporter import generate_monthly_report, print_report, preview_report, export_pdf, email_report
        from datetime import datetime
        month = min(self._selected_months) if self._selected_months else datetime.now().month
        year = min(self._selected_years) if self._selected_years else datetime.now().year
        report = generate_monthly_report(month, year, self._cfg)

        if action == act_print:
            print_report(report, self)
        elif action == act_preview:
            preview_report(report, self)
        elif action == act_pdf:
            default_name = "Kollekten_{:02d}_{}.pdf".format(month, year)
            path, _ = QFileDialog.getSaveFileName(
                self, "PDF speichern", default_name, "PDF-Dateien (*.pdf)"
            )
            if path:
                if export_pdf(report, path):
                    QMessageBox.information(self, "PDF erstellt", f"Gespeichert: {path}")
                else:
                    QMessageBox.warning(self, "Fehler", "PDF konnte nicht erstellt werden.")
        elif action == act_email:
            if email_report(report, self._cfg):
                QMessageBox.information(self, "E-Mail gesendet", "Bericht wurde per Outlook versendet.")
            else:
                QMessageBox.warning(self, "Fehler", "E-Mail konnte nicht gesendet werden.")

    def _effective_records(self) -> list[dict]:
        return self.table.get_effective_records()

    def _effective_files(self) -> list[Path]:
        return existing_paths([str(record.get("target_file") or "") for record in self._effective_records()])

    def _open_selected_files(self, mode: str = "open") -> None:
        files = self._effective_files()
        if not files:
            QMessageBox.information(self, "Keine Datei", "Für die aktuelle Auswahl wurden keine vorhandenen Buchungsblätter gefunden.")
            return
        action = {"open": open_file, "folder": open_folder, "select": reveal_in_explorer}[mode]
        failed = 0
        for file_path in files:
            if not action(str(file_path)):
                failed += 1
        if failed:
            QMessageBox.warning(self, "Teilweise fehlgeschlagen", f"{failed} Datei(en) konnten nicht geöffnet werden.")

    def _email_selected_files(self) -> None:
        if self._cfg is None:
            return
        files = self._effective_files()
        if not files:
            QMessageBox.information(self, "Keine Dateien", "Für die aktuelle Auswahl wurden keine vorhandenen Buchungsblätter gefunden.")
            return
        months = sorted({path.stem.replace("Kollekten_", "") for path in files})
        subject = "Kollekten-Buchungsblätter {0}".format(", ".join(months))
        body = (
            "Anbei die ausgewählten Kollekten-Buchungsblätter als Excel-Dateien.\n\n"
            "Dateien: {0}\nZeitraum: {1}".format(len(files), ", ".join(months))
        )
        ok, count = send_attachments(self._cfg, files, subject=subject, body=body)
        if ok:
            QMessageBox.information(self, "E-Mail gesendet", f"{count} XLSX-Datei(en) wurden per Outlook versendet.")
        else:
            QMessageBox.warning(self, "Fehler", "Die XLSX-Dateien konnten nicht versendet werden.")

    def _delete_selected_records(self) -> None:
        self._run_delete_flow(for_rerun=False)

    def _delete_and_rerun_selected_records(self) -> None:
        self._run_delete_flow(for_rerun=True)

    def _run_delete_flow(self, *, for_rerun: bool) -> None:
        if self._cfg is None:
            return
        records = self._effective_records()
        if not records:
            QMessageBox.information(self, "Keine Auswahl", "Es gibt keine passenden Einträge für diese Aktion.")
            return
        entry_ids = {str(record.get("entry_id") or "") for record in records if str(record.get("entry_id") or "")}
        monthly_files = sorted({Path(str(record.get("target_file") or "")).name for record in records if record.get("target_file")})
        text = (
            f"Es werden {len(records)} Einträge, {len(entry_ids)} E-Mails und {len(monthly_files)} Monatsdatei(en) betroffen.\n\n"
            "Die betroffenen Buchungsdateien werden danach konsistent neu aufgebaut."
        )
        title = "Löschen + Rerun" if for_rerun else "Einträge löschen"
        if QMessageBox.question(self, title, text) != QMessageBox.StandardButton.Yes:
            return
        summary = delete_records(self._cfg, records, for_rerun=for_rerun)
        self.reload()
        if for_rerun and summary["entry_ids"]:
            self.rerun_requested.emit(set(summary["entry_ids"]))



class DocumenteTab(QWidget):
    """Quellen-Verwaltung + Suche für EKHN-Dokumente (Phase 5)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cfg: Optional[dict] = None
        self._sources: list[DocumentSource] = []
        self._workfiles: list[WorkFileEntry] = []
        self._build_ui()

    def _build_ui(self):
        from PySide6.QtWidgets import (
            QAbstractItemView,
            QFileDialog,
            QGroupBox,
            QInputDialog,
            QListWidget,
            QSplitter,
            QMessageBox,
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        lbl = QLabel("Dokumente / Arbeitsdateien")
        lbl.setObjectName("sectionHeader")
        layout.addWidget(lbl)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter)

        # Linke Seite: Arbeitsdateien
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        grp_workfiles = QGroupBox("Arbeitsdateien")
        grp_workfiles_layout = QVBoxLayout(grp_workfiles)
        grp_workfiles_layout.setContentsMargins(12, 12, 12, 12)
        grp_workfiles_layout.setSpacing(8)

        self._workfile_hint = QLabel("")
        self._workfile_hint.setObjectName("hint")
        self._workfile_hint.setWordWrap(True)
        grp_workfiles_layout.addWidget(self._workfile_hint)

        self._workfiles_table = QTableWidget(0, 5)
        self._workfiles_table.setHorizontalHeaderLabels([
            "Bereich", "Name", "Pfad / URL", "Status", "Hinweis"
        ])
        self._workfiles_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._workfiles_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._workfiles_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._workfiles_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._workfiles_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._workfiles_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._workfiles_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._workfiles_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._workfiles_table.setAlternatingRowColors(True)
        self._workfiles_table.verticalHeader().setVisible(False)
        self._workfiles_table.itemSelectionChanged.connect(self._update_workfile_buttons)
        self._workfiles_table.itemDoubleClicked.connect(lambda *_: self._open_selected_workfile())
        grp_workfiles_layout.addWidget(self._workfiles_table)

        btn_row1 = QHBoxLayout()
        btn_row1.setSpacing(6)
        self._btn_workfile_open = QPushButton("Öffnen")
        self._btn_workfile_open.clicked.connect(self._open_selected_workfile)
        self._btn_workfile_folder = QPushButton("Ordner öffnen")
        self._btn_workfile_folder.clicked.connect(lambda: self._open_selected_workfile("folder"))
        self._btn_workfile_select = QPushButton("Im Explorer markieren")
        self._btn_workfile_select.clicked.connect(lambda: self._open_selected_workfile("select"))
        self._btn_workfile_replace = QPushButton("Ersetzen…")
        self._btn_workfile_replace.clicked.connect(self._replace_selected_workfile)
        self._btn_workfile_check = QPushButton("Prüfen")
        self._btn_workfile_check.clicked.connect(self._check_selected_workfile)
        for button in (
            self._btn_workfile_open,
            self._btn_workfile_folder,
            self._btn_workfile_select,
            self._btn_workfile_replace,
            self._btn_workfile_check,
        ):
            btn_row1.addWidget(button)
        btn_row1.addStretch()
        grp_workfiles_layout.addLayout(btn_row1)

        btn_row2 = QHBoxLayout()
        btn_row2.setSpacing(6)
        self._btn_yearplan_add = QPushButton("+ Jahresplandatei")
        self._btn_yearplan_add.clicked.connect(self._add_year_plan_file)
        self._btn_workfile_remove = QPushButton("Entfernen")
        self._btn_workfile_remove.clicked.connect(self._remove_selected_workfile)
        btn_row2.addWidget(self._btn_yearplan_add)
        btn_row2.addWidget(self._btn_workfile_remove)
        btn_row2.addStretch()
        grp_workfiles_layout.addLayout(btn_row2)

        left_layout.addWidget(grp_workfiles)
        splitter.addWidget(left)

        # Rechte Seite: Zusatzquellen + Suche
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        grp_sources = QGroupBox("Zusatzquellen")
        grp_sources_layout = QVBoxLayout(grp_sources)
        grp_sources_layout.setContentsMargins(12, 12, 12, 12)
        grp_sources_layout.setSpacing(8)

        self._sources_hint = QLabel("")
        self._sources_hint.setObjectName("hint")
        self._sources_hint.setWordWrap(True)
        grp_sources_layout.addWidget(self._sources_hint)

        self._list = QListWidget()
        self._list.setFixedHeight(140)
        grp_sources_layout.addWidget(self._list)

        source_btn_row = QHBoxLayout()
        source_btn_row.setSpacing(6)
        btn_add = QPushButton("+ Hinzufügen")
        btn_add.setObjectName("primaryButton")
        btn_add.clicked.connect(self._add_source)
        btn_refresh = QPushButton("Aktualisieren")
        btn_refresh.clicked.connect(self._refresh_selected)
        btn_del = QPushButton("Löschen")
        btn_del.clicked.connect(self._delete_selected)
        for b in (btn_add, btn_refresh, btn_del):
            source_btn_row.addWidget(b)
        source_btn_row.addStretch()
        grp_sources_layout.addLayout(source_btn_row)

        right_layout.addWidget(grp_sources)

        grp_search = QGroupBox("Suche in Zusatzquellen")
        grp_search_layout = QVBoxLayout(grp_search)
        grp_search_layout.setContentsMargins(12, 12, 12, 12)
        grp_search_layout.setSpacing(8)

        search_row = QHBoxLayout()
        search_row.setSpacing(6)
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("In Dokumenten suchen…")
        self._search_input.returnPressed.connect(self._do_search)
        btn_search = QPushButton("Suchen")
        btn_search.clicked.connect(self._do_search)
        search_row.addWidget(self._search_input)
        search_row.addWidget(btn_search)
        grp_search_layout.addLayout(search_row)

        self._results = QTextEdit()
        self._results.setReadOnly(True)
        self._results.setPlaceholderText("Suchergebnisse erscheinen hier…")
        grp_search_layout.addWidget(self._results)

        right_layout.addWidget(grp_search)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        self._btn_workfile_open.setEnabled(False)
        self._btn_workfile_folder.setEnabled(False)
        self._btn_workfile_select.setEnabled(False)
        self._btn_workfile_replace.setEnabled(False)
        self._btn_workfile_check.setEnabled(False)
        self._btn_workfile_remove.setEnabled(False)

    def load_data(self, cfg: dict) -> None:
        self._cfg = cfg
        self._workfiles = load_workfiles(cfg)
        self._sources = load_sources(cfg)
        self._refresh_workfiles()
        self._refresh_list()
        self._refresh_source_hint()

    def _refresh_workfiles(self) -> None:
        self._workfiles_table.setRowCount(0)
        missing = 0
        year_plans = 0
        for entry in self._workfiles:
            status, detail = workfile_status(entry)
            if status != "OK":
                missing += 1
            if entry.key == "year_plan_files":
                year_plans += 1
            row = self._workfiles_table.rowCount()
            self._workfiles_table.insertRow(row)
            values = [entry.section, entry.label, entry.path_or_url, status, detail]
            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setToolTip(entry.description or str(val))
                if col == 2:
                    item.setToolTip(str(entry.path_or_url or ""))
                self._workfiles_table.setItem(row, col, item)
            self._workfiles_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, entry)
            if status == "OK":
                bg = "#E8F5E9"
            elif status == "Ungültig":
                bg = "#FFF3E0"
            else:
                bg = "#FFEBEE"
            for col in range(self._workfiles_table.columnCount()):
                item = self._workfiles_table.item(row, col)
                if item:
                    item.setBackground(QColor(bg))
        summary = f"{len(self._workfiles)} Arbeitsdateien konfiguriert."
        if missing:
            summary += f" {missing} Eintrag(e) benötigen Aufmerksamkeit."
        if year_plans:
            summary += f" {year_plans} Jahresplandatei(en) konfiguriert."
        else:
            summary += " Keine Jahresplandateien konfiguriert. Mit + Jahresplandatei hinzufügen."
        self._workfile_hint.setText(summary)
        self._update_workfile_buttons()

    def _refresh_list(self) -> None:
        self._list.clear()
        icons = {"file": "📄", "url": "🌐", "folder": "📁"}
        for source in self._sources:
            icon = icons.get(source.type, "📄")
            item_text = f"{icon}  {source.name}"
            if source.last_updated:
                item_text += f"  [{source.last_updated[:10]}]"
            self._list.addItem(item_text)
        self._refresh_source_hint()

    def _refresh_source_hint(self) -> None:
        if self._sources:
            self._sources_hint.setText(f"{len(self._sources)} Zusatzquelle(n) konfiguriert.")
        else:
            self._sources_hint.setText(
                "Keine Zusatzquellen konfiguriert. Mit + Hinzufügen können PDFs, Ordner oder URLs ergänzt werden."
            )

    def _current_workfile(self) -> Optional[WorkFileEntry]:
        row = self._workfiles_table.currentRow()
        if row < 0:
            return None
        item = self._workfiles_table.item(row, 0)
        if not item:
            return None
        entry = item.data(Qt.ItemDataRole.UserRole)
        return entry if isinstance(entry, WorkFileEntry) else None

    def _update_workfile_buttons(self) -> None:
        entry = self._current_workfile()
        enabled = entry is not None
        self._btn_workfile_open.setEnabled(enabled)
        self._btn_workfile_folder.setEnabled(enabled)
        self._btn_workfile_select.setEnabled(enabled)
        self._btn_workfile_replace.setEnabled(enabled)
        self._btn_workfile_check.setEnabled(enabled)
        self._btn_workfile_remove.setEnabled(bool(entry and entry.can_remove))

    def _open_selected_workfile(self, action: str = "open") -> None:
        from PySide6.QtWidgets import QMessageBox
        entry = self._current_workfile()
        if entry is None:
            return
        try:
            open_workfile(entry, action)
        except Exception as exc:
            QMessageBox.warning(self, "Arbeitsdatei öffnen", str(exc))

    def _check_selected_workfile(self) -> None:
        from PySide6.QtWidgets import QMessageBox
        entry = self._current_workfile()
        if entry is None:
            return
        status, detail = workfile_status(entry)
        self._refresh_workfiles()
        if status == "OK":
            QMessageBox.information(self, "Arbeitsdatei geprüft", f"{entry.label}: {detail}")
        else:
            QMessageBox.warning(self, "Arbeitsdatei geprüft", f"{entry.label}: {detail}")

    def _replace_selected_workfile(self) -> None:
        from PySide6.QtWidgets import QMessageBox, QFileDialog, QInputDialog
        entry = self._current_workfile()
        if entry is None or self._cfg is None:
            return
        new_path = ""
        if entry.kind == "url":
            new_path, ok = QInputDialog.getText(
                self,
                "URL ersetzen",
                f"Neue URL für '{entry.label}':",
                text=entry.path_or_url,
            )
            if not ok:
                return
        else:
            if entry.key in {"aobj_file", "rules_file", "manual_overrides_file"}:
                filter_text = "JSON-Dateien (*.json);;Alle Dateien (*.*)"
                new_path, _ = QFileDialog.getOpenFileName(self, "Datei ersetzen", entry.path_or_url, filter_text)
            else:
                new_path, _ = QFileDialog.getOpenFileName(self, "Datei ersetzen", entry.path_or_url, "Excel-Dateien (*.xlsx *.xls *.xltx);;Alle Dateien (*.*)")
            if not new_path:
                return
        try:
            update_workfile_path(self._cfg, entry, new_path)
            self._workfiles = load_workfiles(self._cfg)
            self._refresh_workfiles()
            # Validate that the new path is actually usable
            updated_entry = next((e for e in self._workfiles if e.key == entry.key), None)
            if updated_entry is not None:
                status, detail = workfile_status(updated_entry)
                if status != "OK":
                    QMessageBox.warning(
                        self,
                        "Arbeitsdatei ersetzt – Warnung",
                        f"'{entry.label}' wurde gespeichert, ist aber nicht nutzbar:\n{detail}\n\nBitte wähle eine gültige Datei.",
                    )
                    return
            QMessageBox.information(self, "Arbeitsdatei ersetzt", f"'{entry.label}' wurde aktualisiert.")
        except Exception as exc:
            QMessageBox.warning(self, "Arbeitsdatei ersetzen", str(exc))

    def _add_year_plan_file(self) -> None:
        from PySide6.QtWidgets import QMessageBox, QFileDialog
        if self._cfg is None:
            return
        new_path, _ = QFileDialog.getOpenFileName(
            self,
            "Jahresplandatei hinzufügen",
            "",
            "Excel-Dateien (*.xlsx *.xls *.xltx);;Alle Dateien (*.*)",
        )
        if not new_path:
            return
        try:
            add_year_plan_file(self._cfg, new_path)
            self._workfiles = load_workfiles(self._cfg)
            self._refresh_workfiles()
            QMessageBox.information(self, "Jahresplandatei hinzugefügt", Path(new_path).name)
        except Exception as exc:
            QMessageBox.warning(self, "Jahresplandatei hinzufügen", str(exc))

    def _remove_selected_workfile(self) -> None:
        from PySide6.QtWidgets import QMessageBox
        entry = self._current_workfile()
        if entry is None or self._cfg is None or not entry.can_remove:
            return
        if QMessageBox.question(
            self,
            "Jahresplandatei entfernen",
            f"'{entry.label}' aus den konfigurierten Jahresplandateien entfernen?",
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            remove_year_plan_file(self._cfg, entry.index)
            self._workfiles = load_workfiles(self._cfg)
            self._refresh_workfiles()
        except Exception as exc:
            QMessageBox.warning(self, "Jahresplandatei entfernen", str(exc))

    def _add_source(self) -> None:
        from PySide6.QtWidgets import (
            QDialog, QDialogButtonBox, QFormLayout, QRadioButton, QFileDialog
        )
        dlg = QDialog(self)
        dlg.setWindowTitle("Quelle hinzufügen")
        dlg.setMinimumWidth(440)

        vl = QVBoxLayout(dlg)
        fl = QFormLayout()
        fl.setSpacing(8)

        # Typ-Auswahl
        type_widget = QWidget()
        type_row = QHBoxLayout(type_widget)
        type_row.setContentsMargins(0, 0, 0, 0)
        rb_file = QRadioButton("Datei (PDF)")
        rb_url = QRadioButton("URL")
        rb_folder = QRadioButton("Ordner")
        rb_file.setChecked(True)
        type_row.addWidget(rb_file)
        type_row.addWidget(rb_url)
        type_row.addWidget(rb_folder)
        fl.addRow("Typ:", type_widget)

        # Pfad / URL mit Durchsuchen-Button
        path_widget = QWidget()
        path_row = QHBoxLayout(path_widget)
        path_row.setContentsMargins(0, 0, 0, 0)
        path_row.setSpacing(4)
        ed_path = QLineEdit()
        ed_path.setPlaceholderText("Pfad oder URL eingeben…")
        btn_browse = QPushButton("…")
        btn_browse.setFixedWidth(28)
        path_row.addWidget(ed_path)
        path_row.addWidget(btn_browse)
        fl.addRow("Pfad / URL:", path_widget)

        ed_name = QLineEdit()
        ed_name.setPlaceholderText("Anzeigename (optional)")
        fl.addRow("Name:", ed_name)

        vl.addLayout(fl)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        vl.addWidget(btns)

        def _pick():
            if rb_url.isChecked():
                return
            if rb_folder.isChecked():
                path = QFileDialog.getExistingDirectory(dlg, "Ordner wählen")
            else:
                path, _ = QFileDialog.getOpenFileName(dlg, "Datei wählen", "", "PDF (*.pdf);;Alle (*.*)")
            if path:
                ed_path.setText(path)
                if not ed_name.text():
                    ed_name.setText(Path(path).name)

        btn_browse.clicked.connect(_pick)
        rb_url.toggled.connect(lambda on: btn_browse.setEnabled(not on))

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        path_val = ed_path.text().strip()
        if not path_val:
            return
        name_val = ed_name.text().strip() or Path(path_val).name
        src_type = "url" if rb_url.isChecked() else ("folder" if rb_folder.isChecked() else "file")
        source = DocumentSource(name=name_val, type=src_type, path_or_url=path_val)
        self._sources.append(source)
        if self._cfg is not None:
            save_sources(self._cfg, self._sources)
        self._refresh_list()

    def _refresh_selected(self) -> None:
        from PySide6.QtWidgets import QMessageBox
        row = self._list.currentRow()
        if row < 0 or row >= len(self._sources):
            return
        source = self._sources[row]
        text = refresh_source(source)
        from datetime import date
        source.last_updated = date.today().isoformat()
        if self._cfg is not None:
            save_sources(self._cfg, self._sources)
        self._refresh_list()
        preview = text[:200] + "…" if len(text) > 200 else text
        QMessageBox.information(self, "Aktualisiert",
                                f"'{source.name}' aktualisiert.\n\n{preview or '(kein Text extrahiert)'}")

    def _delete_selected(self) -> None:
        from PySide6.QtWidgets import QMessageBox
        row = self._list.currentRow()
        if row < 0 or row >= len(self._sources):
            return
        source = self._sources[row]
        if QMessageBox.question(self, "Löschen",
                                f"'{source.name}' aus der Liste entfernen?") == QMessageBox.StandardButton.Yes:
            self._sources.pop(row)
            if self._cfg is not None:
                save_sources(self._cfg, self._sources)
            self._refresh_list()

    def _do_search(self) -> None:
        query = self._search_input.text().strip()
        if not query:
            return
        results = search_sources(query, self._sources)
        if not results:
            self._results.setPlainText("Keine Treffer gefunden.")
            return
        lines = [f"<b>{len(results)} Treffer für '{query}':</b><br>"]
        for r in results:
            lines.append(
                f"<b>{r.source_name}:</b> {r.snippet.replace('<', '&lt;').replace('>', '&gt;')}<br>"
            )
        self._results.setHtml("".join(lines))


class HilfeTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)
        lbl = QLabel("Hilfe / KI-Assistent")
        lbl.setObjectName("sectionHeader")
        layout.addWidget(lbl)
        self.chat = ChatWidget()
        layout.addWidget(self.chat)

    def configure(self, cfg: dict) -> None:
        self.chat.configure(cfg)


class EinstellungenTab(QWidget):
    """Einstellungen mit Sub-Tabs: Allgemein | Ausführung | KI | Über."""

    settings_saved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cfg: Optional[dict] = None
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 16, 20, 16)
        outer.setSpacing(12)

        lbl = QLabel("Einstellungen")
        lbl.setObjectName("sectionHeader")
        outer.addWidget(lbl)

        sub_tabs = QTabWidget()
        sub_tabs.tabBar().setExpanding(False)
        sub_tabs.addTab(self._build_allgemein(), "Allgemein")
        sub_tabs.addTab(self._build_ausfuehrung(), "Ausführung")
        sub_tabs.addTab(self._build_api(), "PWA / API")
        sub_tabs.addTab(self._build_ki(), "KI")
        sub_tabs.addTab(self._build_ueber(), "Über")
        outer.addWidget(sub_tabs)

        btn_row = QHBoxLayout()
        btn_save = QPushButton("Speichern")
        btn_save.setObjectName("primaryButton")
        btn_save.clicked.connect(self._save)
        btn_row.addStretch()
        btn_row.addWidget(btn_save)
        outer.addLayout(btn_row)

    # ── Sub-Tab Allgemein ─────────────────────────────────────────────────────

    def _build_allgemein(self) -> QWidget:
        w = QWidget()
        form = QVBoxLayout(w)
        form.setContentsMargins(12, 12, 12, 12)
        form.setSpacing(8)

        from PySide6.QtWidgets import QFormLayout, QFileDialog
        fl = QFormLayout()
        fl.setSpacing(6)

        self._ed_gemeinde = QLineEdit()
        self._ed_rechtsträger = QLineEdit()
        self._ed_bank_name = QLineEdit()
        self._ed_iban = QLineEdit()
        self._ed_bic = QLineEdit()
        self._ed_recipients = QLineEdit()
        self._ed_recipients.setPlaceholderText("kommagetrennt, z.B. max@ekhn.de, anna@ekhn.de")

        fl.addRow("Gemeindename:", self._ed_gemeinde)
        fl.addRow("Rechtsträger-Nr.:", self._ed_rechtsträger)
        fl.addRow("Bank:", self._ed_bank_name)
        fl.addRow("IBAN:", self._ed_iban)
        fl.addRow("BIC:", self._ed_bic)
        fl.addRow("Empfänger-E-Mails:", self._ed_recipients)
        form.addLayout(fl)

        # Vorlagenpfade
        def _make_file_row(label: str, attr: str) -> QHBoxLayout:
            row = QHBoxLayout()
            row.setSpacing(6)
            ed = QLineEdit()
            setattr(self, attr, ed)
            btn = QPushButton("…")
            btn.setFixedWidth(28)
            def _pick(checked=False, _ed=ed):
                path, _ = QFileDialog.getOpenFileName(w, "Vorlage wählen", "", "Excel (*.xlsx *.xls)")
                if path:
                    _ed.setText(path)
            btn.clicked.connect(_pick)
            row.addWidget(ed)
            row.addWidget(btn)
            return row

        from PySide6.QtWidgets import QFormLayout as QFL2
        fl2 = QFL2()
        fl2.setSpacing(6)
        fl2.addRow("Vorlage eigene Gemeinde:", _make_file_row("", "_ed_tpl_eigene"))
        fl2.addRow("Vorlage Weiterleitung:", _make_file_row("", "_ed_tpl_weiter"))
        form.addLayout(fl2)
        form.addStretch()
        return w

    # ── Sub-Tab Ausführung ────────────────────────────────────────────────────

    def _build_ausfuehrung(self) -> QWidget:
        from PySide6.QtWidgets import QGroupBox, QRadioButton
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        grp = QGroupBox("Zeitplan")
        grp_l = QVBoxLayout(grp)
        self._rb_manual = QRadioButton("Manuell (kein automatischer Start)")
        self._rb_daily = QRadioButton("Täglich")
        self._rb_weekly = QRadioButton("Wöchentlich")
        self._rb_manual.setChecked(True)
        grp_l.addWidget(self._rb_manual)
        grp_l.addWidget(self._rb_daily)
        grp_l.addWidget(self._rb_weekly)
        layout.addWidget(grp)

        # Tray / Autostart
        from PySide6.QtWidgets import QGroupBox as QGB2
        grp2 = QGB2("Hintergrund")
        grp2_l = QVBoxLayout(grp2)
        self._cb_tray = QCheckBox("Im Hintergrund laufen (Tray-Icon)")
        self._cb_autostart = QCheckBox("Mit Windows starten")
        hint_tray = QLabel("Diese Einstellungen können jederzeit geändert werden.")
        hint_tray.setObjectName("hint")
        hint_tray.setWordWrap(True)
        grp2_l.addWidget(self._cb_tray)
        grp2_l.addWidget(self._cb_autostart)
        grp2_l.addWidget(hint_tray)
        layout.addWidget(grp2)

        # Schriftgröße
        from PySide6.QtWidgets import QFormLayout
        fl = QFormLayout()
        self._spin_font = QSpinBox()
        self._spin_font.setRange(8, 16)
        self._spin_font.setValue(9)
        fl.addRow("Schriftgröße (pt):", self._spin_font)
        layout.addLayout(fl)
        layout.addStretch()
        return w

    # ── Sub-Tab PWA / API ─────────────────────────────────────────────────────

    def _build_api(self) -> QWidget:
        from PySide6.QtWidgets import QFormLayout, QGroupBox
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        grp = QGroupBox("Smartphone-Zugriff (PWA)")
        grp_l = QVBoxLayout(grp)

        self._cb_api_enabled = QCheckBox("API-Server aktivieren")
        grp_l.addWidget(self._cb_api_enabled)

        fl = QFormLayout()
        fl.setSpacing(6)
        self._spin_api_port = QSpinBox()
        self._spin_api_port.setRange(1024, 65535)
        self._spin_api_port.setValue(8765)
        fl.addRow("Port:", self._spin_api_port)

        self._ed_api_token = QLineEdit()
        self._ed_api_token.setEchoMode(QLineEdit.EchoMode.Password)
        self._ed_api_token.setPlaceholderText("Leer lassen = kein Passwortschutz")
        fl.addRow("Bearer-Token:", self._ed_api_token)
        grp_l.addLayout(fl)

        self._lbl_api_url = QLabel("")
        self._lbl_api_url.setObjectName("hint")
        self._lbl_api_url.setWordWrap(True)
        grp_l.addWidget(self._lbl_api_url)

        btn_toggle = QPushButton("Server starten / stoppen")
        btn_toggle.clicked.connect(self._toggle_api_server)
        grp_l.addWidget(btn_toggle)

        hint = QLabel(
            "Öffne die URL im Browser deines Smartphones (selbes WLAN).\n"
            "Zum Installieren: Menü → 'Zum Startbildschirm hinzufügen'."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        grp_l.addWidget(hint)

        layout.addWidget(grp)
        layout.addStretch()

        self._cb_api_enabled.toggled.connect(self._update_api_url_label)
        self._spin_api_port.valueChanged.connect(self._update_api_url_label)
        return w

    def _update_api_url_label(self):
        import socket
        port = self._spin_api_port.value()
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
        except Exception:
            ip = "192.168.x.x"
        self._lbl_api_url.setText(f"PWA-Adresse: http://{ip}:{port}/")

    def _toggle_api_server(self):
        mw = self.window()
        if hasattr(mw, "_toggle_api_server"):
            mw._toggle_api_server()

    # ── Sub-Tab KI ────────────────────────────────────────────────────────────

    def _build_ki(self) -> QWidget:
        from PySide6.QtWidgets import QFormLayout
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        fl = QFormLayout()
        fl.setSpacing(6)

        self._cb_provider = QComboBox()
        self._cb_provider.addItem("Deaktiviert", "disabled")
        self._cb_provider.addItem("OpenRouter (empfohlen, kostenlos)", "openrouter")
        self._cb_provider.addItem("Ollama (lokal)", "ollama")
        self._cb_provider.addItem("LM Studio (lokal)", "lmstudio")
        self._cb_provider.addItem("OpenAI", "openai")
        self._cb_provider.addItem("Anthropic (Claude)", "anthropic")
        fl.addRow("KI-Provider:", self._cb_provider)

        self._ed_api_key = QLineEdit()
        self._ed_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._ed_api_key.setPlaceholderText("API-Schlüssel")
        fl.addRow("API-Key:", self._ed_api_key)

        self._ed_base_url = QLineEdit()
        self._ed_base_url.setPlaceholderText("https://openrouter.ai/api/v1")
        fl.addRow("Base-URL:", self._ed_base_url)

        self._ed_model = QLineEdit()
        self._ed_model.setPlaceholderText("meta-llama/llama-3.1-8b-instruct:free")
        fl.addRow("Modell:", self._ed_model)
        layout.addLayout(fl)

        self._lbl_ai_help = QLabel("")
        self._lbl_ai_help.setObjectName("hint")
        self._lbl_ai_help.setWordWrap(True)
        layout.addWidget(self._lbl_ai_help)

        btn_test = QPushButton("Verbindung testen")
        btn_test.clicked.connect(self._test_ai_connection)
        self._lbl_ai_status = QLabel("")
        self._lbl_ai_status.setObjectName("hint")
        layout.addWidget(btn_test)
        layout.addWidget(self._lbl_ai_status)
        layout.addStretch()

        self._cb_provider.currentIndexChanged.connect(self._update_ai_provider_fields)
        self._update_ai_provider_fields()
        return w

    def _test_ai_connection(self):
        from app.ai.provider import get_provider, DisabledProvider
        test_cfg = {
            "ai": {
                "provider": self._cb_provider.currentData(),
                "api_key": self._ed_api_key.text().strip(),
                "base_url": self._ed_base_url.text().strip(),
                "model": self._ed_model.text().strip(),
                "openrouter_base_url": self._ed_base_url.text().strip() or "https://openrouter.ai/api/v1",
            }
        }
        provider = get_provider(test_cfg)
        if isinstance(provider, DisabledProvider):
            self._lbl_ai_status.setText("KI deaktiviert.")
            return
        if not self._ed_base_url.text().strip() and self._cb_provider.currentData() != "anthropic":
            self._lbl_ai_status.setText("Bitte zuerst eine Base-URL eintragen.")
            return
        self._lbl_ai_status.setText("Teste Verbindung…")
        ok = provider.is_available()
        if ok:
            self._lbl_ai_status.setText("✓ Verbindung erfolgreich.")
        else:
            provider_name = str(self._cb_provider.currentData() or "")
            if provider_name in {"ollama", "lmstudio"}:
                self._lbl_ai_status.setText(
                    "✗ Verbindung fehlgeschlagen. Server antwortet nicht erfolgreich. Bitte Base-URL, Modell und ggf. lokalen Server-Key prüfen."
                )
            else:
                self._lbl_ai_status.setText("✗ Verbindung fehlgeschlagen. Bitte URL, Modell und ggf. API-Key prüfen.")

    def _ai_provider_defaults(self, provider_name: str) -> tuple[str, str, str]:
        provider_name = str(provider_name or "disabled")
        if provider_name == "openrouter":
            return (
                "https://openrouter.ai/api/v1",
                "meta-llama/llama-3.1-8b-instruct:free",
                "Cloud-Provider mit OpenAI-kompatibler API. API-Key erforderlich.",
            )
        if provider_name == "ollama":
            return (
                "http://localhost:11434/v1",
                "smollm2:360m",
                "Lokaler Server. Meist kein API-Key noetig; Modell muss in Ollama vorhanden sein.",
            )
        if provider_name == "lmstudio":
            return (
                "http://localhost:1234/v1",
                "",
                "Lokaler OpenAI-kompatibler Server. Modellname muss zum in LM Studio geladenen Modell passen.",
            )
        if provider_name == "openai":
            return (
                "https://api.openai.com/v1",
                "gpt-4o-mini",
                "OpenAI-API mit API-Key. Fuer euren Chat-Completions-Flow ist `gpt-4o-mini` ein solider Start.",
            )
        if provider_name == "anthropic":
            return (
                "https://api.anthropic.com/v1",
                "claude-3-5-haiku-latest",
                "Anthropic nutzt die native Messages-API. API-Key erforderlich.",
            )
        return ("", "", "KI ist deaktiviert.")

    def _update_ai_provider_fields(self) -> None:
        provider_name = str(self._cb_provider.currentData() or "disabled")
        default_url, default_model, help_text = self._ai_provider_defaults(provider_name)
        known_urls = {
            "https://openrouter.ai/api/v1",
            "http://localhost:11434/v1",
            "http://localhost:1234/v1",
            "https://api.openai.com/v1",
            "https://api.anthropic.com/v1",
            "",
        }
        known_models = {
            "meta-llama/llama-3.1-8b-instruct:free",
            "smollm2:360m",
            "llama3.2:3b",
            "gpt-4o-mini",
            "claude-3-5-haiku-latest",
            "",
        }
        if self._ed_base_url.text().strip() in known_urls:
            self._ed_base_url.setText(default_url)
        self._ed_base_url.setPlaceholderText(default_url or "Base-URL")
        if self._ed_model.text().strip() in known_models:
            self._ed_model.setText(default_model)
        self._ed_model.setPlaceholderText(default_model or "Modellname")
        if provider_name in {"ollama", "lmstudio"}:
            self._ed_api_key.setPlaceholderText("Optional fuer lokale Gateways, sonst leer lassen")
        elif provider_name == "disabled":
            self._ed_api_key.setPlaceholderText("Nicht erforderlich")
        else:
            self._ed_api_key.setPlaceholderText("API-Schluessel")
        fields_enabled = provider_name != "disabled"
        self._ed_api_key.setEnabled(fields_enabled)
        self._ed_base_url.setEnabled(fields_enabled and provider_name != "anthropic")
        self._ed_model.setEnabled(fields_enabled)
        self._lbl_ai_help.setText(help_text)

    # ── Sub-Tab Über ──────────────────────────────────────────────────────────

    def _build_ueber(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        lbl_name = QLabel("Kollekten-Automation")
        lbl_name.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_version = QLabel(f"Version {APP_VERSION}")
        lbl_version.setObjectName("hint")

        lbl_desc = QLabel(
            "Automatisierte Verarbeitung von Kollekten-E-Mails\n"
            "für evangelische Kirchengemeinden (EKHN)."
        )
        lbl_desc.setWordWrap(True)

        self._lbl_spendenintro = QLabel(
            "Wenn dir die App Zeit spart, Fehler reduziert oder einfach etwas Ruhe in den Alltag bringt, "
            "freuen wir uns sehr über eine freiwillige Spende für die KI-Arbeit in der Evangelischen Kirchengemeinde Oberlahnstein."
        )
        self._lbl_spendenintro.setWordWrap(True)

        self._spenden_frame = QFrame()
        self._spenden_frame.setObjectName("statusCard")
        spenden_layout = QHBoxLayout(self._spenden_frame)
        spenden_layout.setContentsMargins(16, 14, 16, 14)
        spenden_layout.setSpacing(18)

        text_col = QVBoxLayout()
        text_col.setSpacing(8)

        self._lbl_spendenmotiv = QLabel(
            "Schon ein kleiner Beitrag hilft, hilfreiche digitale Werkzeuge weiterzuentwickeln, "
            "zu pflegen und mit Freude für Gemeinden nutzbar zu machen."
        )
        self._lbl_spendenmotiv.setWordWrap(True)

        self._lbl_bankdaten = QLabel("")
        self._lbl_bankdaten.setTextFormat(Qt.TextFormat.RichText)
        self._lbl_bankdaten.setWordWrap(True)

        self._lbl_qr_motivation = QLabel(
            "Am einfachsten geht es oft direkt mit der Banking-App: QR-Code scannen, Betrag anpassen, fertig. "
            "Das spart Tippfehler und macht Spenden angenehm leicht."
        )
        self._lbl_qr_motivation.setWordWrap(True)

        self._lbl_qr_generator = QLabel(
            "Für eigene Spendenaktionen gibt es auch einen QR-Code-Generator. "
            "Pfarrer Benjamin Graf stellt ihn kostenlos zur Verfügung: "
            "<a href='mailto:benjamin.graf@ekhn.de'>benjamin.graf@ekhn.de</a>."
        )
        self._lbl_qr_generator.setOpenExternalLinks(True)
        self._lbl_qr_generator.setWordWrap(True)
        self._lbl_qr_generator.setObjectName("hint")

        text_col.addWidget(self._lbl_spendenmotiv)
        text_col.addWidget(self._lbl_bankdaten)
        text_col.addWidget(self._lbl_qr_motivation)
        text_col.addWidget(self._lbl_qr_generator)
        text_col.addStretch()

        qr_col = QVBoxLayout()
        qr_col.setSpacing(6)
        qr_col.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self._lbl_qr_image = QLabel()
        self._lbl_qr_image.setObjectName("qrCodeLabel")
        self._lbl_qr_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_qr_image.setMinimumSize(180, 180)
        self._lbl_qr_image.setScaledContents(False)

        self._lbl_qr_caption = QLabel("Spenden-QR-Code")
        self._lbl_qr_caption.setObjectName("hint")
        self._lbl_qr_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_qr_caption.setWordWrap(True)

        qr_col.addWidget(self._lbl_qr_image)
        qr_col.addWidget(self._lbl_qr_caption)

        spenden_layout.addLayout(text_col, 1)
        spenden_layout.addLayout(qr_col)

        for widget in (lbl_name, lbl_version, lbl_desc, self._lbl_spendenintro, self._spenden_frame):
            layout.addWidget(widget)
        layout.addStretch()
        return w

    # ── Laden / Speichern ─────────────────────────────────────────────────────

    def load_from_config(self, cfg: dict) -> None:
        self._cfg = cfg
        org = cfg.get("organization", {})
        self._ed_gemeinde.setText(org.get("gemeinde_name", ""))
        self._ed_rechtsträger.setText(org.get("rechtsträger_nr", ""))
        self._ed_bank_name.setText(org.get("bank_name", ""))
        self._ed_iban.setText(org.get("bank_iban", ""))
        self._ed_bic.setText(org.get("bank_bic", ""))
        self._ed_recipients.setText(", ".join(cfg.get("mail", {}).get("recipient_emails", [])))
        tpl = cfg.get("templates", {})
        self._ed_tpl_eigene.setText(tpl.get("eigene_gemeinde", ""))
        self._ed_tpl_weiter.setText(tpl.get("zur_weiterleitung", ""))

        app_cfg = cfg.get("app", {})
        self._cb_tray.setChecked(app_cfg.get("use_tray", False))
        self._cb_autostart.setChecked(app_cfg.get("autostart", False))
        self._spin_font.setValue(app_cfg.get("font_size", 9))
        self._spin_font.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)

        api_cfg = cfg.get("api", {})
        self._cb_api_enabled.setChecked(api_cfg.get("enabled", False))
        self._spin_api_port.setValue(api_cfg.get("port", 8765))
        self._spin_api_port.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        self._ed_api_token.setText(api_cfg.get("token", ""))
        self._update_api_url_label()

        ai_cfg = cfg.get("ai", {})
        provider_val = ai_cfg.get("provider", "disabled")
        for i in range(self._cb_provider.count()):
            if self._cb_provider.itemData(i) == provider_val:
                self._cb_provider.setCurrentIndex(i)
                break
        self._ed_api_key.setText(ai_cfg.get("api_key", ""))
        base_url = ai_cfg.get("base_url", "")
        if not base_url and provider_val == "openrouter":
            base_url = ai_cfg.get("openrouter_base_url", "")
        self._ed_base_url.setText(base_url)
        self._ed_model.setText(ai_cfg.get("model", ""))
        self._update_ai_provider_fields()

        mode = "now"
        schedules = cfg.get("schedules", [])
        if schedules:
            mode = schedules[0].get("mode", "now")
        if mode == "now":
            self._rb_manual.setChecked(True)
        elif "monthly" in mode or "quarterly" in mode:
            self._rb_weekly.setChecked(True)
        else:
            self._rb_daily.setChecked(True)

        self._update_ueber_section(org)

    def _update_ueber_section(self, org: dict) -> None:
        gemeinde = org.get("gemeinde_name", "Evangelische Kirchengemeinde Oberlahnstein")
        bank_name = org.get("bank_name", "Nassauische Sparkasse")
        iban = org.get("bank_iban", "DE50 5105 0015 0656 2363 79")
        bic = org.get("bank_bic", "NASSDE55XXX")
        self._lbl_bankdaten.setText(
            "<b>Spendenkonto {0}</b><br>"
            "Bank: {1}<br>"
            "IBAN: <span style='font-family: Consolas, monospace;'>{2}</span><br>"
            "BIC: <span style='font-family: Consolas, monospace;'>{3}</span>".format(
                gemeinde,
                bank_name,
                iban,
                bic or "—",
            )
        )

        qr_path = Path(__file__).parent.parent / "assets" / "QR_KI-Arbeit.png"
        if qr_path.exists():
            pixmap = QPixmap(str(qr_path))
            if not pixmap.isNull():
                self._lbl_qr_image.setPixmap(
                    pixmap.scaled(180, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                )
                self._lbl_qr_caption.setText("QR-Code für eine schnelle Spende per Banking-App")
                return
        self._lbl_qr_image.setText("QR-Code nicht gefunden")
        self._lbl_qr_caption.setText("Bitte Datei assets/QR_KI-Arbeit.png prüfen")

    def _save(self) -> None:
        if self._cfg is None:
            return
        from PySide6.QtWidgets import QMessageBox
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from config import save_config
            from app.autostart import set_autostart

            org = self._cfg.setdefault("organization", {})
            org["gemeinde_name"] = self._ed_gemeinde.text().strip()
            org["rechtsträger_nr"] = self._ed_rechtsträger.text().strip()
            org["bank_name"] = self._ed_bank_name.text().strip()
            org["bank_iban"] = self._ed_iban.text().strip()
            org["bank_bic"] = self._ed_bic.text().strip()

            mail = self._cfg.setdefault("mail", {})
            mail["recipient_emails"] = [
                e.strip() for e in self._ed_recipients.text().split(",") if e.strip()
            ]

            tpl = self._cfg.setdefault("templates", {})
            tpl["eigene_gemeinde"] = self._ed_tpl_eigene.text().strip()
            tpl["zur_weiterleitung"] = self._ed_tpl_weiter.text().strip()

            app_cfg = self._cfg.setdefault("app", {})
            use_tray = self._cb_tray.isChecked()
            autostart = self._cb_autostart.isChecked()
            app_cfg["use_tray"] = use_tray
            app_cfg["autostart"] = autostart
            app_cfg["font_size"] = self._spin_font.value()

            api_cfg = self._cfg.setdefault("api", {})
            api_cfg["enabled"] = self._cb_api_enabled.isChecked()
            api_cfg["port"] = self._spin_api_port.value()
            api_cfg["token"] = self._ed_api_token.text().strip()

            ai_cfg = self._cfg.setdefault("ai", {})
            ai_cfg["provider"] = self._cb_provider.currentData()
            ai_cfg["api_key"] = self._ed_api_key.text().strip()
            ai_cfg["base_url"] = self._ed_base_url.text().strip()
            ai_cfg["model"] = self._ed_model.text().strip()
            if ai_cfg["provider"] == "openrouter":
                ai_cfg["openrouter_base_url"] = ai_cfg["base_url"]

            save_config(self._cfg)
            set_autostart(autostart)

            font_size = self._spin_font.value()
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.setFont(QFont("Segoe UI", font_size))

            self.settings_saved.emit()
            QMessageBox.information(self, "Gespeichert", "Einstellungen wurden gespeichert.")
        except Exception as exc:
            QMessageBox.warning(self, "Fehler", f"Konnte nicht speichern:\n{exc}")


def _format_eur(value: float) -> str:
    return f"{value:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._thread: Optional[QThread] = None
        self._worker: Optional[RunWorker] = None
        self._update_thread: Optional[QThread] = None
        self._last_run: Optional[datetime] = None
        self._processed = 0
        self._warnings = 0
        self._cfg = None
        self._api_server = None
        self._setup_window()
        self._load_config()
        self._refresh_ui()
        QTimer.singleShot(3000, self._start_update_check)
        QTimer.singleShot(1000, self._maybe_start_api_server)

    def _setup_window(self):
        self.setWindowTitle("Kollekten-Automation")
        self.setMinimumSize(860, 560)
        self.resize(1080, 700)

        icon_path = Path(__file__).parent.parent / "assets" / "app.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        header = QWidget()
        header.setObjectName("headerBar")
        header.setFixedHeight(48)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(12, 0, 12, 0)

        lbl_app = QLabel("Kollekten-Automation")
        lbl_app.setObjectName("appTitle")
        h_layout.addWidget(lbl_app)
        h_layout.addStretch()

        lbl_version = QLabel(f"v{APP_VERSION}")
        lbl_version.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 8pt;")
        h_layout.addWidget(lbl_version)

        self.update_banner = UpdateBanner()
        self.update_banner.hide()

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.tabBar().setExpanding(False)

        self.tab_uebersicht = UebersichtTab()
        self.tab_verlauf = VerlaufTab()
        self.tab_dokumente = DocumenteTab()
        self.tab_hilfe = HilfeTab()
        self.tab_einstellungen = EinstellungenTab()

        self.tabs.addTab(self.tab_uebersicht, "Übersicht")
        self.tabs.addTab(self.tab_verlauf, "Verlauf")
        self.tabs.addTab(self.tab_dokumente, "Dokumente")
        self.tabs.addTab(self.tab_hilfe, "Hilfe / KI")
        self.tabs.addTab(self.tab_einstellungen, "Einstellungen")

        self.tab_uebersicht.run_requested.connect(self._start_run)
        self.tab_verlauf.rerun_requested.connect(self._start_rerun)
        self.tab_einstellungen.settings_saved.connect(self._on_settings_saved)

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(header)
        central_layout.addWidget(self.update_banner)
        central_layout.addWidget(self.tabs)
        self.setCentralWidget(central)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Bereit")

    def _load_config(self):
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from config import get_config

            self._cfg = get_config()
        except Exception as exc:
            self.statusBar().showMessage(f"Konfiguration nicht gefunden: {exc}")

    def _refresh_ui(self):
        if not self._cfg:
            return
        org = self._cfg.get("organization", {})
        gemeinde = org.get("gemeinde_name") or f"RV {org.get('rechtsträger_nr', '—')}"
        self.tab_uebersicht.update_sidebar(gemeinde, self._describe_next_run())
        self.tab_uebersicht.update_status(self._last_run, self._processed, self._warnings)
        self.tab_verlauf.load_data(self._cfg)
        self.tab_dokumente.load_data(self._cfg)
        self.tab_hilfe.configure(self._cfg)
        self.tab_einstellungen.load_from_config(self._cfg)
        self._reload_recent_entries()

    def _describe_next_run(self) -> str:
        schedules = self._cfg.get("schedules", []) if self._cfg else []
        active = [schedule for schedule in schedules if schedule.get("enabled", True)]
        if not active:
            return "Manuell"
        first = active[0]
        mode = str(first.get("mode", "now"))
        time = str(first.get("time", "07:30"))
        if mode == "now":
            return "Manuell"
        if mode in {"once", "on_date"}:
            return f"{first.get('date', '—')} {time}"
        labels = {
            "monthly_start": f"Monatsanfang {time}",
            "monthly_end": f"Monatsende {time}",
            "quarterly_start": f"Quartalsanfang {time}",
            "quarterly_end": f"Quartalsende {time}",
        }
        return labels.get(mode, time)

    def _start_update_check(self):
        if self._update_thread is not None:
            return
        self._update_thread = start_background_check(self._handle_update_result)
        self._update_thread.finished.connect(self._clear_update_thread)

    def _clear_update_thread(self):
        self._update_thread = None

    def _handle_update_result(self, info: UpdateInfo | None):
        if info is None:
            return
        self.update_banner.set_update(info)
        self.update_banner.show()

    def _start_run(self, dry_run: bool):
        self._start_run_worker(dry_run=dry_run, entry_ids=None)

    def _start_rerun(self, entry_ids: set[str]) -> None:
        self._start_run_worker(dry_run=False, entry_ids=entry_ids)

    def _start_run_worker(self, *, dry_run: bool, entry_ids: set[str] | None):
        if self._thread and self._thread.isRunning():
            return

        self.tab_uebersicht.set_running(True)
        mode = "Rerun" if entry_ids else ("Vorschau" if dry_run else "Ausführung")
        self.statusBar().showMessage(f"{mode} läuft…")

        self._worker = RunWorker(dry_run=dry_run, entry_ids=entry_ids)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_run_finished)
        self._worker.error.connect(self._on_run_error)
        self._worker.progress.connect(lambda msg: self.statusBar().showMessage(msg))
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._clear_run_thread)
        self._thread.start()

    def _clear_run_thread(self):
        self._thread = None
        self._worker = None

    def _on_run_finished(self, processed: int, errors: int):
        self._last_run = datetime.now()
        self._processed += processed
        self._warnings = errors
        self.tab_uebersicht.set_running(False)
        self.tab_uebersicht.update_status(self._last_run, self._processed, errors)
        status = f"✓ {processed} Kollekten verarbeitet"
        if errors:
            status += f"  ⚠ {errors} Fehler"
        self.statusBar().showMessage(status)
        self._reload_recent_entries()
        self.tab_verlauf.reload()

    def _on_settings_saved(self) -> None:
        self._load_config()
        if self._cfg:
            self._refresh_ui()

    def _on_run_error(self, msg: str):
        self.tab_uebersicht.set_running(False)
        self.statusBar().showMessage(f"Fehler: {msg}")
        QMessageBox.critical(self, "Fehler", f"Ausführung fehlgeschlagen:\n\n{msg}")

    def _reload_recent_entries(self):
        if not self._cfg:
            return
        try:
            self.tab_uebersicht.table.setRowCount(0)
            rows = get_booking_rows(self._cfg, include_statuses={"ok"})
            for record in rows[-20:][::-1]:
                booking_date = record.get("booking_date")
                if hasattr(booking_date, "strftime"):
                    datum = booking_date.strftime("%Y-%m-%d")
                else:
                    datum = str(booking_date or "—")[:10]
                betrag = _format_eur(float(record.get("amount") or 0))
                zweck = str(record.get("purpose") or "—")[:50]
                scope = str(record.get("scope") or "")
                datei = Path(str(record.get("target_file") or "—")).name
                self.tab_uebersicht.add_recent_entry(datum, betrag, zweck, scope, datei, record=record)
        except Exception:
            pass

    def _maybe_start_api_server(self):
        if not self._cfg:
            return
        if self._cfg.get("api", {}).get("enabled", False):
            self._start_api_server()

    def _start_api_server(self):
        if self._api_server and self._api_server.is_running():
            return
        try:
            from app.api.server import ApiServer
            port = (self._cfg or {}).get("api", {}).get("port", 8765)
            self._api_server = ApiServer(port=port)
            self._api_server.start()
            import socket
            try:
                ip = socket.gethostbyname(socket.gethostname())
            except Exception:
                ip = "localhost"
            self.statusBar().showMessage(f"API-Server aktiv: http://{ip}:{port}/")
        except Exception as exc:
            self.statusBar().showMessage(f"API-Server Fehler: {exc}")

    def _toggle_api_server(self):
        if self._api_server and self._api_server.is_running():
            self._api_server.stop()
            self._api_server = None
            self.statusBar().showMessage("API-Server gestoppt.")
        else:
            self._start_api_server()

    def closeEvent(self, event):
        if self._api_server:
            self._api_server.stop()
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from config import get_config

            cfg = get_config()
            use_tray = cfg.get("app", {}).get("use_tray", False)
        except Exception:
            use_tray = False

        if use_tray:
            event.ignore()
            self.hide()
        else:
            event.accept()


def load_theme(app: QApplication) -> None:
    qss_path = Path(__file__).parent / "theme" / "office2010.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))


def run_app() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Kollekten-Automation")
    app.setApplicationVersion(APP_VERSION)
    load_theme(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(run_app())
