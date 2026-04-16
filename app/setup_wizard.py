"""Setup-Wizard: Ersteinrichtung der Kollekten-Automation (PySide6 QWizard)."""
from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal, QObject, QRegularExpression
from PySide6.QtGui import QFont, QRegularExpressionValidator, QIcon
from PySide6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QCheckBox,
    QRadioButton, QButtonGroup, QTimeEdit, QComboBox, QGroupBox,
    QTextEdit, QProgressBar, QWidget, QApplication,
)
from PySide6.QtCore import QTime


# ── Schritt 1: Gemeindedaten ────────────────────────────────────────────────

class GemeindePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Schritt 1 von 4 — Gemeindedaten")
        self.setSubTitle(
            "Bitte geben Sie die Daten Ihrer Kirchengemeinde ein.\n"
            "Diese erscheinen auf den Buchungsblättern."
        )
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(10)

        self.f_name = QLineEdit()
        self.f_name.setPlaceholderText("Ev. Kirchengemeinde Oberlahnstein")
        layout.addRow("Gemeindename:*", self.f_name)

        self.f_rtnr = QLineEdit()
        self.f_rtnr.setPlaceholderText("z.B. 6840")
        self.f_rtnr.setMaximumWidth(120)
        v = QRegularExpressionValidator(QRegularExpression(r"\d{4,6}"))
        self.f_rtnr.setValidator(v)
        layout.addRow("Rechtsträger-Nr.:*", self.f_rtnr)

        layout.addRow("", QLabel(""))  # Abstand

        bank_lbl = QLabel("Bankverbindung")
        bank_lbl.setObjectName("sectionHeader")
        layout.addRow(bank_lbl)

        self.f_bank = QLineEdit()
        self.f_bank.setPlaceholderText("Nassauische Sparkasse")
        layout.addRow("Bankname:*", self.f_bank)

        self.f_iban = QLineEdit()
        self.f_iban.setPlaceholderText("DE50 5105 0015 0656 2363 79")
        iban_v = QRegularExpressionValidator(QRegularExpression(r"[A-Z]{2}[\dA-Z ]{15,32}"))
        self.f_iban.setValidator(iban_v)
        layout.addRow("IBAN:*", self.f_iban)

        self.f_bic = QLineEdit()
        self.f_bic.setPlaceholderText("NASSDE55XXX")
        layout.addRow("BIC:", self.f_bic)

        # Pflichtfelder registrieren
        self.registerField("gemeinde_name*", self.f_name)
        self.registerField("rechtsträger_nr*", self.f_rtnr)
        self.registerField("bank_name*", self.f_bank)
        self.registerField("bank_iban*", self.f_iban)
        self.registerField("bank_bic", self.f_bic)

    def initializePage(self):
        """Vorbefüllen aus bestehender config.json."""
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from config import get_config
            cfg = get_config()
            org = cfg.get("organization", {})
            self.f_name.setText(org.get("gemeinde_name", ""))
            self.f_rtnr.setText(org.get("rechtsträger_nr", ""))
            self.f_bank.setText(org.get("bank_name", ""))
            self.f_iban.setText(org.get("bank_iban", ""))
            self.f_bic.setText(org.get("bank_bic", ""))
        except Exception:
            pass


# ── Schritt 2: Vorlagenpfade ─────────────────────────────────────────────────

class VorlagenPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Schritt 2 von 4 — Buchungsblatt-Vorlagen")
        self.setSubTitle(
            "Wählen Sie die Excel-Vorlagen aus, die von der EKHN bereitgestellt wurden.\n"
            "Sie finden diese normalerweise unter 'Downloads' oder auf dem EKHN-Intranet."
        )
        self._eigene_path = ""
        self._weiter_path = ""
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Eigene Gemeinde
        g1 = QGroupBox("Vorlage: eigene Gemeinde")
        g1_layout = QHBoxLayout(g1)
        self._lbl_eigene = QLabel("Keine Datei ausgewählt")
        self._lbl_eigene.setObjectName("hint")
        self._lbl_eigene.setWordWrap(True)
        btn1 = QPushButton("Durchsuchen…")
        btn1.clicked.connect(lambda: self._pick("eigene"))
        g1_layout.addWidget(self._lbl_eigene, stretch=1)
        g1_layout.addWidget(btn1)
        layout.addWidget(g1)

        # Zur Weiterleitung
        g2 = QGroupBox("Vorlage: zur Weiterleitung")
        g2_layout = QHBoxLayout(g2)
        self._lbl_weiter = QLabel("Keine Datei ausgewählt")
        self._lbl_weiter.setObjectName("hint")
        self._lbl_weiter.setWordWrap(True)
        btn2 = QPushButton("Durchsuchen…")
        btn2.clicked.connect(lambda: self._pick("weiter"))
        g2_layout.addWidget(self._lbl_weiter, stretch=1)
        g2_layout.addWidget(btn2)
        layout.addWidget(g2)

        hint = QLabel(
            "💡 Tipp: Neue Vorlagen werden jährlich von der EKHN bereitgestellt.\n"
            "Die Pfade können später unter Einstellungen → Allgemein geändert werden."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch()

    def _pick(self, kind: str):
        path, _ = QFileDialog.getOpenFileName(
            self, "Excel-Vorlage auswählen", "", "Excel-Dateien (*.xlsx *.xltx)"
        )
        if path:
            p = Path(path)
            label_text = f"{p.name}  ({p.stat().st_size // 1024} KB)"
            if kind == "eigene":
                self._eigene_path = path
                self._lbl_eigene.setText(label_text)
            else:
                self._weiter_path = path
                self._lbl_weiter.setText(label_text)
            self.completeChanged.emit()

    def isComplete(self):
        return bool(self._eigene_path and self._weiter_path)

    def initializePage(self):
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from config import get_config
            cfg = get_config()
            t = cfg.get("templates", {})
            e = t.get("eigene_gemeinde", "")
            w = t.get("zur_weiterleitung", "")
            if e and Path(e).exists():
                self._eigene_path = e
                self._lbl_eigene.setText(Path(e).name)
            if w and Path(w).exists():
                self._weiter_path = w
                self._lbl_weiter.setText(Path(w).name)
        except Exception:
            pass


# ── Schritt 3: Zeitplan + Tray ───────────────────────────────────────────────

class ZeitplanPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Schritt 3 von 4 — Ausführung")
        self.setSubTitle(
            "Wann soll die Automation nach neuen E-Mails suchen?\n"
            "Outlook muss dazu geöffnet sein."
        )
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Zeitplan
        g_schedule = QGroupBox("Zeitplan")
        g_schedule_layout = QVBoxLayout(g_schedule)

        self.rb_manual = QRadioButton("Manuell (nur auf Knopfdruck)")
        self.rb_daily = QRadioButton("Täglich um:")
        self.rb_weekly = QRadioButton("Wöchentlich:")

        self.rb_manual.setChecked(True)

        self._time_daily = QTimeEdit(QTime(7, 30))
        self._time_daily.setEnabled(False)
        self._time_daily.setDisplayFormat("HH:mm")
        self._time_daily.setFixedWidth(70)

        self._day_weekly = QComboBox()
        self._day_weekly.addItems(["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"])
        self._day_weekly.setFixedWidth(110)
        self._day_weekly.setEnabled(False)

        self._time_weekly = QTimeEdit(QTime(7, 30))
        self._time_weekly.setDisplayFormat("HH:mm")
        self._time_weekly.setFixedWidth(70)
        self._time_weekly.setEnabled(False)

        row_daily = QHBoxLayout()
        row_daily.addWidget(self.rb_daily)
        row_daily.addWidget(self._time_daily)
        row_daily.addStretch()

        row_weekly = QHBoxLayout()
        row_weekly.addWidget(self.rb_weekly)
        row_weekly.addWidget(self._day_weekly)
        row_weekly.addWidget(QLabel("um"))
        row_weekly.addWidget(self._time_weekly)
        row_weekly.addStretch()

        g_schedule_layout.addWidget(self.rb_manual)
        g_schedule_layout.addLayout(row_daily)
        g_schedule_layout.addLayout(row_weekly)

        self.rb_daily.toggled.connect(self._time_daily.setEnabled)
        self.rb_weekly.toggled.connect(self._day_weekly.setEnabled)
        self.rb_weekly.toggled.connect(self._time_weekly.setEnabled)

        layout.addWidget(g_schedule)

        # Tray / Autostart — OPT-IN
        g_background = QGroupBox("Hintergrundausführung (optional)")
        g_bg_layout = QVBoxLayout(g_background)

        self.chk_autostart = QCheckBox("Mit Windows starten")
        self.chk_tray = QCheckBox("Im Hintergrund laufen (Tray-Icon in Taskleiste)")

        # Beide standardmäßig DEAKTIVIERT — Opt-In!
        self.chk_autostart.setChecked(False)
        self.chk_tray.setChecked(False)

        hint_bg = QLabel(
            "Diese Einstellungen sind optional. Die App funktioniert auch ohne sie.\n"
            "Sie können jederzeit unter Einstellungen → Ausführung geändert werden."
        )
        hint_bg.setObjectName("hint")
        hint_bg.setWordWrap(True)

        g_bg_layout.addWidget(self.chk_autostart)
        g_bg_layout.addWidget(self.chk_tray)
        g_bg_layout.addWidget(hint_bg)
        layout.addWidget(g_background)

        layout.addStretch()

    def get_schedule_mode(self) -> str:
        if self.rb_daily.isChecked():
            return "daily"
        if self.rb_weekly.isChecked():
            return "weekly"
        return "manual"


# ── Schritt 4: Testlauf ──────────────────────────────────────────────────────

class _TestWorker(QObject):
    finished = Signal(int, int)
    log_line = Signal(str)
    error = Signal(str)

    def run(self):
        try:
            import logging
            sys.path.insert(0, str(Path(__file__).parent.parent))
            import main as m

            class Sink(logging.Handler):
                def __init__(self, signal):
                    super().__init__()
                    self.signal = signal
                def emit(self, record):
                    self.signal.emit(self.format(record))

            sink = Sink(self.log_line)
            sink.setFormatter(logging.Formatter("%(message)s"))
            logging.getLogger().addHandler(sink)

            processed, errors = m.run(dry_run=True)
            self.finished.emit(processed, errors)
        except Exception as exc:
            self.error.emit(str(exc))


class TestPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Schritt 4 von 4 — Testlauf")
        self.setSubTitle(
            "Klicken Sie auf 'Jetzt testen' um zu prüfen ob die Einrichtung funktioniert.\n"
            "Es werden keine Dateien verändert (Vorschau-Modus)."
        )
        self._complete = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self._btn_test = QPushButton("▶  Jetzt testen")
        self._btn_test.setObjectName("primaryButton")
        self._btn_test.setFixedHeight(32)
        self._btn_test.clicked.connect(self._run_test)
        layout.addWidget(self._btn_test)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # indeterminiert
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(160)
        self._log.setFont(QFont("Consolas", 8))
        layout.addWidget(self._log)

        self._lbl_result = QLabel("")
        self._lbl_result.setWordWrap(True)
        layout.addWidget(self._lbl_result)

        # Spendenhinweis
        layout.addStretch()
        donate_lbl = QLabel(
            "Kollekten-Automation ist kostenlos. "
            "Wenn Sie die App nützlich finden, freuen wir uns über eine Spende. "
            "<a href='https://paypal.me/kollekten'>Jetzt spenden</a>"
        )
        donate_lbl.setObjectName("hint")
        donate_lbl.setOpenExternalLinks(True)
        donate_lbl.setWordWrap(True)
        layout.addWidget(donate_lbl)

    def _run_test(self):
        self._btn_test.setEnabled(False)
        self._progress.setVisible(True)
        self._log.clear()

        self._worker = _TestWorker()
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.log_line.connect(lambda line: self._log.append(line))
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_done(self, processed: int, errors: int):
        self._progress.setVisible(False)
        self._btn_test.setEnabled(True)
        if processed == 0 and errors == 0:
            self._lbl_result.setText("ℹ Keine neuen E-Mails gefunden. Das ist normal wenn alles bereits verarbeitet wurde.")
        elif errors > 0:
            self._lbl_result.setText(
                f"⚠ {processed} Kollekten gefunden, {errors} Fehler. "
                f"Prüfen Sie das Log und die E-Mails."
            )
        else:
            self._lbl_result.setText(f"✓ {processed} Kollekten gefunden. Einrichtung erfolgreich!")
        self._complete = True
        self.completeChanged.emit()

    def _on_error(self, msg: str):
        self._progress.setVisible(False)
        self._btn_test.setEnabled(True)
        self._lbl_result.setText(f"✗ Fehler: {msg}")
        # Auch bei Fehler darf man fortfahren (Outlook ggf. nicht offen)
        self._complete = True
        self.completeChanged.emit()

    def isComplete(self):
        return self._complete


# ── Haupt-Wizard ─────────────────────────────────────────────────────────────

class SetupWizard(QWizard):
    """Geführte Ersteinrichtung — öffnet bei erstem Start oder aus Einstellungen."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kollekten-Automation — Einrichtung")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setMinimumSize(600, 480)
        self.resize(680, 520)

        icon_path = Path(__file__).parent.parent / "assets" / "app.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._page_gemeinde = GemeindePage()
        self._page_vorlagen = VorlagenPage()
        self._page_zeitplan = ZeitplanPage()
        self._page_test = TestPage()

        self.addPage(self._page_gemeinde)
        self.addPage(self._page_vorlagen)
        self.addPage(self._page_zeitplan)
        self.addPage(self._page_test)

        self.setButtonText(QWizard.WizardButton.FinishButton, "Fertigstellen")
        self.setButtonText(QWizard.WizardButton.NextButton, "Weiter →")
        self.setButtonText(QWizard.WizardButton.BackButton, "← Zurück")
        self.setButtonText(QWizard.WizardButton.CancelButton, "Abbrechen")

        # Beim Abschluss speichern
        self.accepted.connect(self._save_config)

    def _save_config(self):
        """Schreibt alle Wizard-Felder in config.json."""
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from config import get_config, save_config
            cfg = get_config()

            # Gemeindedaten
            cfg.setdefault("organization", {})
            cfg["organization"]["gemeinde_name"] = self.field("gemeinde_name")
            cfg["organization"]["rechtsträger_nr"] = self.field("rechtsträger_nr")
            cfg["organization"]["bank_name"] = self.field("bank_name")
            cfg["organization"]["bank_iban"] = self.field("bank_iban")
            cfg["organization"]["bank_bic"] = self.field("bank_bic")

            # Vorlagenpfade
            cfg.setdefault("templates", {})
            cfg["templates"]["eigene_gemeinde"] = self._page_vorlagen._eigene_path
            cfg["templates"]["zur_weiterleitung"] = self._page_vorlagen._weiter_path

            # Zeitplan
            mode = self._page_zeitplan.get_schedule_mode()
            cfg.setdefault("schedules", [])
            cfg["schedules"] = [{"name": "default", "mode": mode, "enabled": True,
                                  "target": "run", "time": "07:30", "date": ""}]

            # App-Einstellungen (Tray, Autostart)
            cfg.setdefault("app", {})
            use_tray = self._page_zeitplan.chk_tray.isChecked()
            use_autostart = self._page_zeitplan.chk_autostart.isChecked()
            cfg["app"]["use_tray"] = use_tray
            cfg["app"]["autostart"] = use_autostart

            save_config(cfg)

            # Autostart setzen/entfernen
            from app.autostart import set_autostart
            set_autostart(use_autostart)

        except Exception as exc:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Fehler beim Speichern",
                                f"Konfiguration konnte nicht gespeichert werden:\n{exc}")


def run_wizard(parent=None) -> bool:
    """Öffnet den Wizard. Gibt True zurück wenn der Nutzer fertiggestellt hat."""
    wizard = SetupWizard(parent)
    return wizard.exec() == QWizard.DialogCode.Accepted
