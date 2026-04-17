"""Chat-Widget für den KI-Assistenten mit Tool-Use-Unterstützung."""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.ai.provider import AIDisabledError, AIProvider, DisabledProvider, get_provider
from app.ai.tools import TOOL_LEVELS


# ── Worker ────────────────────────────────────────────────────────────────────

class ChatWorker(QObject):
    response = Signal(str)
    error = Signal(str)
    finished = Signal()
    status = Signal(str)          # Zwischenmeldung (Tool läuft…)
    confirm_needed = Signal(str, str)  # (tool_name, menschenlesbare Beschreibung)

    def __init__(self, provider: AIProvider, messages: list[dict], cfg: dict):
        super().__init__()
        self._provider = provider
        self._messages = messages
        self._cfg = cfg
        self._confirm_event = threading.Event()
        self._confirmed = False

    def set_confirm_result(self, confirmed: bool) -> None:
        """Wird vom Haupt-Thread aufgerufen, nachdem der Nutzer entschieden hat."""
        self._confirmed = confirmed
        self._confirm_event.set()

    def run(self) -> None:
        try:
            if getattr(self._provider, "supports_tools", False):
                self._run_tool_loop()
            else:
                text = self._provider.chat(self._messages)
                self.response.emit(text)
        except AIDisabledError:
            self.error.emit("KI nicht aktiviert.")
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            self.finished.emit()

    def _run_tool_loop(self) -> None:
        from app.ai.tools import (
            ACTION_TOOLS, describe_action,
            execute_action_tool, execute_tool,
            to_anthropic_tools, to_openai_tools,
        )

        provider_name = getattr(self._provider, "name", "")
        tools_schema = to_anthropic_tools() if provider_name == "anthropic" else to_openai_tools()
        messages = list(self._messages)

        for _ in range(10):  # Sicherheits-Limit
            result = self._provider.chat_with_tools(messages, tools_schema)

            if result["type"] == "text":
                self.response.emit(result["content"])
                messages.append({"role": "assistant", "content": result["content"]})
                return

            # Tool-Aufrufe verarbeiten
            calls = result["calls"]
            if provider_name == "anthropic":
                messages.append({"role": "assistant", "content": result["raw_content"]})
                tool_results = []
                for call in calls:
                    tool_result = self._execute_call(call, describe_action, execute_tool, execute_action_tool)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": call["id"],
                        "content": tool_result,
                    })
                messages.append({"role": "user", "content": tool_results})
            else:
                # OpenAI-Format
                messages.append(result["raw_message"])
                for call in calls:
                    tool_result = self._execute_call(call, describe_action, execute_tool, execute_action_tool)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": tool_result,
                    })

        self.response.emit("(Maximale Tool-Iterationen erreicht – bitte erneut versuchen.)")

    def _execute_call(self, call: dict, describe_fn, read_fn, action_fn) -> str:
        name = call["name"]
        args = call["args"]
        level = TOOL_LEVELS.get(name, "read_only")

        if level == "read_only":
            self.status.emit(f"Lese Daten ({name}) …")
            return read_fn(name, args, self._cfg)

        # Aktions-Tools: immer Bestätigung einholen
        description = describe_fn(name, args, self._cfg)
        self.status.emit(f"Warte auf Bestätigung: {description}")
        self._confirm_event.clear()
        self._confirmed = False
        # Stufe mit in die Beschreibung kodieren (für den Dialog)
        self.confirm_needed.emit(name + "|" + level, description)
        self._confirm_event.wait(timeout=120)
        if not self._confirmed:
            return "Aktion wurde vom Nutzer abgebrochen."
        self.status.emit(f"Führe aus: {description} …")
        return action_fn(name, args, self._cfg)


# ── Chat-Widget ───────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "Du bist ein hilfreicher Sekretariatsassistent für evangelische Kirchengemeinden (EKHN). "
    "Du hilfst bei Kollekten, Buchungsblättern, Kirchenrecht und Gemeindeverwaltung.\n"
    "Gemeinde: {gemeinde}\n\n"
    "== Lese-Tools (sofort ausführen) ==\n"
    "- get_buchungen: Buchungen abrufen (optional nach Monat/Jahr filtern)\n"
    "- get_zusammenfassung: Summen und Anzahl für einen Zeitraum\n"
    "- konfiguration_info: Gemeindename, Empfänger, Vorlagen-Status\n"
    "- suche_kirchenrecht: Kirchenrecht EKHN nach Stichwort durchsuchen\n"
    "- suche_handbuch: Handbuch Gemeindebüro (Stand 08/2019) durchsuchen\n"
    "- get_formular_info: Informationen zu EKHN-Formularen\n"
    "- get_regionalverwaltung: Kontaktdaten der zuständigen Regionalverwaltung\n"
    "- get_recent_errors: Letzte Fehler aus dem Anwendungs-Log\n"
    "- get_kollektenplan: Kollektenzweck für ein Datum aus dem Jahresplan\n"
    "- liste_faellige_fristen: Fällige Wiedervorlagen und Fristen\n\n"
    "== Aktions-Tools (Nutzerbestätigung erforderlich) ==\n"
    "- verarbeitung_starten: Neue Outlook-E-Mails verarbeiten und Buchungsblätter erstellen\n"
    "- buchungsblatt_versenden: Buchungsblätter (xlsx) per Outlook versenden (E-Mail-Versand!)\n"
    "- save_note: Aktennotiz speichern\n\n"
    "== Wichtige Regeln ==\n"
    "1. Lese-Tools direkt aufrufen – kein Dialog nötig.\n"
    "2. Aktions-Tools erst aufrufen, wenn der Nutzer explizit zustimmt.\n"
    "3. Bei kirchenrechtlichen Fragen: immer Quelle, §, Stand nennen + Disclaimer.\n"
    "4. Antworte immer auf Deutsch, präzise und freundlich.\n"
    "5. Beträge immer in Euro mit deutschem Zahlenformat (z. B. 231,00 €).\n\n"
    "== Rechtlicher Disclaimer (bei jedem Kirchenrechtsbezug wiederholen) ==\n"
    "Hinweis: Dies ist keine verbindliche Rechtsberatung. Maßgeblich ist die jeweils "
    "aktuelle Fassung des Kirchenrechts der EKHN sowie im Zweifel die zuständige "
    "Regionalverwaltung oder der Stabsbereich Recht (Kirchenverwaltung Darmstadt)."
)

_BUBBLE_USER = (
    '<div style="text-align:right;margin:4px 0;">'
    '<span style="display:inline-block;background:#BBDEFB;color:#0D47A1;'
    'border-radius:10px 10px 0 10px;padding:6px 10px;max-width:85%;">{text}</span></div>'
)
_BUBBLE_ASSISTANT = (
    '<div style="text-align:left;margin:4px 0;">'
    '<span style="display:inline-block;background:#FAFAFA;color:#212121;'
    'border:1px solid #E0E0E0;border-radius:10px 10px 10px 0;'
    'padding:6px 10px;max-width:85%;">{text}</span></div>'
)
_BUBBLE_STATUS = (
    '<div style="text-align:left;margin:2px 0;">'
    '<span style="display:inline-block;background:#FFF8E1;color:#795548;'
    'border-radius:6px;padding:3px 8px;font-size:0.85em;">{text}</span></div>'
)
_BUBBLE_ERROR = (
    '<div style="text-align:left;margin:4px 0;">'
    '<span style="display:inline-block;background:#FFCDD2;color:#B71C1C;'
    'border-radius:10px;padding:6px 10px;">{text}</span></div>'
)


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br>")
    )


class _SendLineEdit(QLineEdit):
    send_triggered = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.send_triggered.emit()
        else:
            super().keyPressEvent(event)


class ChatWidget(QWidget):
    """
    KI-Chat mit Tool-Use-Unterstützung.
    Die KI kann Buchungen lesen, Verarbeitung starten und Dateien versenden –
    jeweils mit Nutzerbestätigung für Aktionen.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("chatWidget")
        self._provider: AIProvider = DisabledProvider()
        self._messages: list[dict] = []
        self._thread: Optional[QThread] = None
        self._worker: Optional[ChatWorker] = None
        self._gemeinde = ""
        self._cfg: dict = {}
        self._build_ui()
        self._update_provider_hint()

    # ── Öffentliche API ───────────────────────────────────────────────────────

    def configure(self, cfg: dict) -> None:
        self._cfg = cfg
        try:
            self._provider = get_provider(cfg)
        except Exception:
            self._provider = DisabledProvider()
        org = cfg.get("organization", {})
        self._gemeinde = org.get("gemeinde_name") or "RV {}".format(org.get("rechtsträger_nr", ""))
        self._reset_history()
        self._update_provider_hint()

    # ── UI-Aufbau ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self._hint_label = QLabel()
        self._hint_label.setObjectName("hint")
        self._hint_label.setWordWrap(True)
        self._hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._hint_label)

        self._history = QTextEdit()
        self._history.setReadOnly(True)
        self._history.setObjectName("chatHistory")
        self._history.setMinimumHeight(200)
        self._history.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self._history)

        input_row = QHBoxLayout()
        input_row.setSpacing(6)
        self._input = _SendLineEdit()
        self._input.setPlaceholderText(
            "Frage stellen oder Aufgabe beschreiben …  "
            "(z. B. 'Zeig mir die Kollekten vom letzten Monat')"
        )
        self._input.send_triggered.connect(self._send)
        input_row.addWidget(self._input)

        self._send_btn = QPushButton("Senden")
        self._send_btn.setObjectName("primaryButton")
        self._send_btn.setFixedWidth(80)
        self._send_btn.clicked.connect(self._send)
        input_row.addWidget(self._send_btn)
        layout.addLayout(input_row)

    def _update_provider_hint(self) -> None:
        disabled = isinstance(self._provider, DisabledProvider)
        self._hint_label.setVisible(disabled)
        self._input.setEnabled(not disabled)
        self._send_btn.setEnabled(not disabled)
        if disabled:
            self._hint_label.setText(
                "KI-Assistent nicht aktiviert.\n"
                "Bitte unter Einstellungen → KI einen Provider konfigurieren\n"
                "(z. B. OpenRouter, Ollama, LM Studio oder Anthropic)."
            )

    # ── Chat-Logik ────────────────────────────────────────────────────────────

    def _reset_history(self) -> None:
        self._messages = [
            {"role": "system", "content": _SYSTEM_PROMPT.format(gemeinde=self._gemeinde)}
        ]
        self._history.clear()

    def _clear_thread(self) -> None:
        self._thread = None
        self._worker = None
        self._set_busy(False)

    def _send(self) -> None:
        text = self._input.text().strip()
        if not text or self._thread is not None:
            return
        self._input.clear()
        self._messages.append({"role": "user", "content": text})
        self._append_bubble(_BUBBLE_USER, text)
        self._set_busy(True)

        self._worker = ChatWorker(self._provider, list(self._messages), self._cfg)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.response.connect(self._on_response)
        self._worker.error.connect(self._on_error)
        self._worker.status.connect(self._on_status)
        self._worker.confirm_needed.connect(self._on_confirm_needed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._clear_thread)
        self._thread.start()

    def _on_response(self, text: str) -> None:
        self._messages.append({"role": "assistant", "content": text})
        self._append_bubble(_BUBBLE_ASSISTANT, text)

    def _on_status(self, text: str) -> None:
        self._append_bubble(_BUBBLE_STATUS, text)

    def _on_confirm_needed(self, tool_name_level: str, description: str) -> None:
        """Läuft im Haupt-Thread – zeigt Bestätigungsdialog (stufenangepasst)."""
        # tool_name_level enthält "tool_name|level" oder nur "tool_name"
        parts = tool_name_level.split("|", 1)
        level = parts[1] if len(parts) > 1 else "user_confirmed"

        if level == "user_confirmed_send":
            msg_text = (
                f"Die KI möchte folgende Aktion ausführen:\n\n"
                f"{description}\n\n"
                f"⚠ Es wird eine E-Mail versendet. Ausführen?"
            )
            box = QMessageBox(
                QMessageBox.Icon.Warning,
                "E-Mail-Versand bestätigen",
                msg_text,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                self,
            )
            box.setDefaultButton(QMessageBox.StandardButton.No)
        else:
            msg_text = (
                f"Die KI möchte folgende Aktion ausführen:\n\n"
                f"{description}\n\n"
                f"Ausführen?"
            )
            box = QMessageBox(
                QMessageBox.Icon.Question,
                "Aktion bestätigen",
                msg_text,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                self,
            )
            box.setDefaultButton(QMessageBox.StandardButton.No)

        confirmed = box.exec() == QMessageBox.StandardButton.Yes
        if self._worker:
            self._worker.set_confirm_result(confirmed)

    def _on_error(self, msg: str) -> None:
        msg_l = msg.lower()
        provider_name = getattr(self._provider, "name", "")
        provider_label = {
            "openrouter": "OpenRouter", "openai": "OpenAI", "anthropic": "Anthropic",
            "ollama": "Ollama", "lmstudio": "LM Studio",
        }.get(provider_name, "dem KI-Provider")

        if "429" in msg or "too many requests" in msg_l:
            display = "Rate-Limit erreicht. Bitte kurz warten und dann erneut senden."
        elif "401" in msg or "403" in msg or "authentication" in msg_l or "unauthorized" in msg_l:
            if provider_name in {"ollama", "lmstudio"}:
                display = (
                    f"{provider_label} verlangt Authentifizierung. "
                    "Bitte Key unter Einstellungen → KI eintragen."
                )
            else:
                display = "API-Key ungültig oder abgelaufen. Bitte unter Einstellungen → KI prüfen."
        elif "connect" in msg_l or "timeout" in msg_l or "network" in msg_l:
            if provider_name in {"ollama", "lmstudio"}:
                display = f"Keine Verbindung zu {provider_label}. Bitte lokalen Server starten."
            else:
                display = f"Keine Verbindung zu {provider_label}. Bitte Netzwerk prüfen."
        elif "model" in msg_l and ("not found" in msg_l or "does not exist" in msg_l):
            display = "Das konfigurierte Modell wurde nicht gefunden oder ist nicht geladen."
        else:
            display = f"Fehler: {msg}"
        self._append_bubble(_BUBBLE_ERROR, display)

    def _append_bubble(self, template: str, text: str) -> None:
        self._history.append(template.format(text=_escape(text)))
        self._history.verticalScrollBar().setValue(self._history.verticalScrollBar().maximum())

    def _set_busy(self, busy: bool) -> None:
        self._input.setEnabled(not busy)
        self._send_btn.setEnabled(not busy)
        self._send_btn.setText("…" if busy else "Senden")
