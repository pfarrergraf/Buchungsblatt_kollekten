from __future__ import annotations

import re
import webbrowser
from typing import Callable, NamedTuple

import requests
from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


APP_VERSION = "1.1.0"
GITHUB_REPO = "PLACEHOLDER/kollekten-automation"


class UpdateInfo(NamedTuple):
    version: str
    download_url: str
    release_notes: str


def _normalize_version(value: str) -> tuple[int, ...]:
    cleaned = value.strip().lower()
    if cleaned.startswith("v"):
        cleaned = cleaned[1:]
    parts = re.findall(r"\d+", cleaned)
    if not parts:
        return (0,)
    return tuple(int(part) for part in parts)


def _is_newer_version(current: str, candidate: str) -> bool:
    current_parts = _normalize_version(current)
    candidate_parts = _normalize_version(candidate)
    max_len = max(len(current_parts), len(candidate_parts))
    current_padded = current_parts + (0,) * (max_len - len(current_parts))
    candidate_padded = candidate_parts + (0,) * (max_len - len(candidate_parts))
    return candidate_padded > current_padded


def _pick_download_url(payload: dict) -> str:
    assets = payload.get("assets") or []
    for asset in assets:
        url = asset.get("browser_download_url", "")
        if url.lower().endswith(".exe"):
            return url
    for asset in assets:
        url = asset.get("browser_download_url", "")
        if url:
            return url
    return payload.get("browser_download_url", "") or payload.get("html_url", "")


def check_for_update() -> UpdateInfo | None:
    url = "https://api.github.com/repos/{0}/releases/latest".format(GITHUB_REPO)
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return None

    version = str(payload.get("tag_name") or "").strip()
    if not version or not _is_newer_version(APP_VERSION, version):
        return None

    download_url = _pick_download_url(payload)
    if not download_url:
        return None

    release_notes = str(payload.get("body") or "").strip()
    return UpdateInfo(version=version, download_url=download_url, release_notes=release_notes)


class UpdateBanner(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("updateBanner")
        self._info: UpdateInfo | None = None

        self._label = QLabel("")
        self._download_button = QPushButton("Jetzt herunterladen")
        self._later_button = QPushButton("Später")

        self._download_button.clicked.connect(self._open_download)
        self._later_button.clicked.connect(self.hide)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        layout.addWidget(self._label, 1)
        layout.addWidget(self._download_button)
        layout.addWidget(self._later_button)

        self.setStyleSheet(
            "QWidget#updateBanner { background-color: #FFF9C4; color: #3E2723; border: 1px solid #E6D97A; border-radius: 4px; }"
            "QWidget#updateBanner QLabel { color: #3E2723; }"
            "QWidget#updateBanner QPushButton { background-color: #FFFDE7; color: #3E2723; border: 1px solid #D6C65A; padding: 4px 10px; }"
            "QWidget#updateBanner QPushButton:hover { background-color: #FFF59D; }"
        )

    def set_update(self, info: UpdateInfo) -> None:
        self._info = info
        self._label.setText("Version {0} verfugbar".format(info.version))

    def _open_download(self) -> None:
        if self._info and self._info.download_url:
            webbrowser.open(self._info.download_url)


class _UpdateWorker(QObject):
    finished = Signal(object)

    def run(self) -> None:
        info = check_for_update()
        self.finished.emit(info)


class _CallbackRelay(QObject):
    def __init__(self, callback: Callable[[UpdateInfo | None], None]):
        super().__init__()
        self._callback = callback

    @Slot(object)
    def deliver(self, info: UpdateInfo | None) -> None:
        self._callback(info)


def start_background_check(callback: Callable[[UpdateInfo | None], None]) -> QThread:
    thread = QThread()
    worker = _UpdateWorker()
    relay = _CallbackRelay(callback)
    worker.moveToThread(thread)

    thread.started.connect(worker.run)
    worker.finished.connect(relay.deliver)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(relay.deleteLater)
    thread.finished.connect(thread.deleteLater)
    thread._relay = relay
    thread.start()
    return thread
