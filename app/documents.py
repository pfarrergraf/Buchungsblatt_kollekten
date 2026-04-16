"""Dokument-Quellen-Verwaltung: lokale Dateien, Netzwerkpfade, URLs (Phase 5)."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import webbrowser
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
import sys


# ── Datenmodell ───────────────────────────────────────────────────────────────

@dataclass
class DocumentSource:
    name: str
    type: str          # "file" | "url" | "folder"
    path_or_url: str
    last_updated: str = ""   # ISO-Datum oder leer

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "DocumentSource":
        return cls(
            name=str(d.get("name", "")),
            type=str(d.get("type", "file")),
            path_or_url=str(d.get("path_or_url", "")),
            last_updated=str(d.get("last_updated", "")),
        )


@dataclass
class WorkFileEntry:
    key: str
    section: str
    label: str
    path_or_url: str
    kind: str = "file"  # "file" | "folder" | "url"
    required: bool = True
    description: str = ""
    index: int = -1
    can_remove: bool = False


@dataclass
class SearchResult:
    source_name: str
    snippet: str
    page: int = 0


# ── Config-I/O ────────────────────────────────────────────────────────────────

def load_sources(cfg: dict) -> list[DocumentSource]:
    raw = cfg.get("document_sources", [])
    return [DocumentSource.from_dict(item) for item in raw if isinstance(item, dict)]


def save_sources(cfg: dict, sources: list[DocumentSource]) -> None:
    cfg["document_sources"] = [s.to_dict() for s in sources]
    _save_config(cfg)


def _save_config(cfg: dict) -> None:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config import save_config
    save_config(cfg)


def load_workfiles(cfg: dict) -> list[WorkFileEntry]:
    templates = cfg.get("templates", {}) if isinstance(cfg.get("templates"), dict) else {}
    refs = cfg.get("reference_sources", {}) if isinstance(cfg.get("reference_sources"), dict) else {}
    entries: list[WorkFileEntry] = []

    def _add(key: str, section: str, label: str, path_or_url: str,
             kind: str = "file", required: bool = True, description: str = "",
             index: int = -1, can_remove: bool = False) -> None:
        entries.append(WorkFileEntry(
            key=key,
            section=section,
            label=label,
            path_or_url=str(path_or_url or ""),
            kind=kind,
            required=required,
            description=description,
            index=index,
            can_remove=can_remove,
        ))

    _add(
        "eigene_gemeinde",
        "Vorlagen",
        "Vorlage: eigene Gemeinde",
        templates.get("eigene_gemeinde", ""),
        description="Excel-Vorlage für Buchungsblätter der eigenen Gemeinde",
    )
    _add(
        "zur_weiterleitung",
        "Vorlagen",
        "Vorlage: zur Weiterleitung",
        templates.get("zur_weiterleitung", ""),
        description="Excel-Vorlage für weiterzuleitende Kollekten",
    )
    _add(
        "aobj_file",
        "Referenzen",
        "Referenz: Abrechnungsobjekte",
        refs.get("aobj_file", ""),
        description="Stammdaten für AObj-Zuordnungen",
    )
    _add(
        "rules_file",
        "Referenzen",
        "Referenz: Kollektenregeln",
        refs.get("rules_file", ""),
        description="Regelwerk für die automatische Zuordnung",
    )
    _add(
        "manual_overrides_file",
        "Referenzen",
        "Referenz: Manuelle Overrides",
        refs.get("manual_overrides_file", ""),
        description="Manuelle Korrekturregeln",
    )
    _add(
        "kollektenplan_url",
        "Pläne",
        "Kollektenplan-URL",
        refs.get("kollektenplan_url", ""),
        kind="url",
        required=False,
        description="Öffentlicher EKHN-Kollektenplan im Browser",
    )
    year_plan_files = refs.get("year_plan_files", [])
    if isinstance(year_plan_files, list):
        for index, raw_path in enumerate(year_plan_files):
            _add(
                "year_plan_files",
                "Pläne",
                f"Jahresplan-Datei {index + 1}",
                raw_path,
                description="Zusätzliche Jahresplandatei für die Referenzsuche",
                index=index,
                can_remove=True,
            )
    return entries


def workfile_status(entry: WorkFileEntry) -> tuple[str, str]:
    target = str(entry.path_or_url or "").strip()
    if entry.kind == "url":
        if not target:
            return ("Fehlt", "URL nicht gesetzt")
        parsed = urlparse(target)
        if parsed.scheme.lower() in {"http", "https"}:
            return ("OK", "URL konfiguriert")
        return ("Ungültig", "Keine gültige http(s)-URL")
    if not target:
        return ("Fehlt", "Pfad nicht gesetzt")
    path = Path(target)
    if entry.kind == "folder":
        return ("OK", "Ordner vorhanden") if path.exists() and path.is_dir() else ("Fehlt", "Ordner nicht gefunden")
    return ("OK", "Datei vorhanden") if path.exists() and path.is_file() else ("Fehlt", "Datei nicht gefunden")


def open_workfile(entry: WorkFileEntry, action: str = "open") -> None:
    target = str(entry.path_or_url or "").strip()
    if entry.kind == "url":
        if not target:
            raise FileNotFoundError("URL ist nicht konfiguriert.")
        webbrowser.open(target)
        return

    if not target:
        raise FileNotFoundError("Pfad ist nicht konfiguriert.")

    path = Path(target)
    if action == "folder":
        folder = path if entry.kind == "folder" else path.parent
        if not folder.exists():
            raise FileNotFoundError(f"Ordner nicht gefunden: {folder}")
        os.startfile(str(folder))
        return

    if action == "select":
        if path.exists():
            subprocess.Popen(["explorer", "/select,", str(path)])
            return
        folder = path.parent
        if folder.exists():
            os.startfile(str(folder))
            return
        raise FileNotFoundError(f"Pfad nicht gefunden: {path}")

    if not path.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {path}")
    os.startfile(str(path))


def update_workfile_path(cfg: dict, entry: WorkFileEntry, new_path: str) -> None:
    new_value = str(Path(new_path)) if entry.kind != "url" else str(new_path).strip()
    if entry.section == "Vorlagen":
        cfg.setdefault("templates", {})[entry.key] = new_value
    elif entry.section == "Referenzen" or (entry.section == "Pläne" and entry.key == "kollektenplan_url"):
        cfg.setdefault("reference_sources", {})[entry.key] = new_value
    elif entry.key == "year_plan_files":
        files = list(cfg.setdefault("reference_sources", {}).get("year_plan_files", []))
        if entry.index >= 0 and entry.index < len(files):
            files[entry.index] = new_value
        else:
            files.append(new_value)
        cfg["reference_sources"]["year_plan_files"] = files
    else:
        raise ValueError(f"Unbekannte Arbeitsdatei: {entry.key}")
    _save_config(cfg)


def add_year_plan_file(cfg: dict, new_path: str) -> None:
    ref = cfg.setdefault("reference_sources", {})
    files = list(ref.get("year_plan_files", []))
    files.append(str(Path(new_path)))
    ref["year_plan_files"] = files
    _save_config(cfg)


def remove_year_plan_file(cfg: dict, index: int) -> None:
    ref = cfg.setdefault("reference_sources", {})
    files = list(ref.get("year_plan_files", []))
    if 0 <= index < len(files):
        del files[index]
        ref["year_plan_files"] = files
        _save_config(cfg)


# ── Text-Extraktion ───────────────────────────────────────────────────────────

def _cache_path(key: str) -> Path:
    cache_dir = Path(__file__).parent.parent / "data" / "documents"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / (hashlib.md5(key.encode()).hexdigest() + ".txt")


def _extract_pdf_text(file_path: str) -> str:
    try:
        import pdfplumber
        texts: list[str] = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    texts.append(t)
        return "\n".join(texts)
    except Exception:
        return ""


def _extract_url_text(url: str) -> str:
    try:
        import requests
        r = requests.get(url, timeout=15, headers={"User-Agent": "kollekten-automation/1.0"})
        r.raise_for_status()
        content_type = r.headers.get("Content-Type", "")
        if "pdf" in content_type or url.lower().endswith(".pdf"):
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(r.content)
                tmp = f.name
            try:
                return _extract_pdf_text(tmp)
            finally:
                os.unlink(tmp)
        # HTML → einfacher Text
        try:
            from html.parser import HTMLParser

            class _TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.parts: list[str] = []
                    self._skip = False
                def handle_starttag(self, tag, attrs):
                    if tag in ("script", "style"):
                        self._skip = True
                def handle_endtag(self, tag):
                    if tag in ("script", "style"):
                        self._skip = False
                def handle_data(self, data):
                    if not self._skip:
                        stripped = data.strip()
                        if stripped:
                            self.parts.append(stripped)

            extractor = _TextExtractor()
            extractor.feed(r.text)
            return "\n".join(extractor.parts)
        except Exception:
            return r.text[:50000]
    except Exception:
        return ""


def _extract_folder_text(folder_path: str) -> str:
    parts: list[str] = []
    try:
        for pdf_file in sorted(Path(folder_path).glob("**/*.pdf"))[:20]:
            text = _extract_pdf_text(str(pdf_file))
            if text:
                parts.append(f"--- {pdf_file.name} ---\n{text}")
    except Exception:
        pass
    return "\n\n".join(parts)


def refresh_source(source: DocumentSource) -> str:
    """Extrahiert Text aus einer Quelle und speichert ihn im Cache."""
    cache = _cache_path(source.path_or_url)
    try:
        if source.type == "file":
            if source.path_or_url.lower().endswith(".pdf"):
                text = _extract_pdf_text(source.path_or_url)
            else:
                text = Path(source.path_or_url).read_text(encoding="utf-8", errors="replace")
        elif source.type == "url":
            text = _extract_url_text(source.path_or_url)
        elif source.type == "folder":
            text = _extract_folder_text(source.path_or_url)
        else:
            text = ""
        cache.write_text(text, encoding="utf-8")
        return text
    except Exception:
        return ""


def get_cached_text(source: DocumentSource) -> str:
    cache = _cache_path(source.path_or_url)
    if cache.exists():
        return cache.read_text(encoding="utf-8")
    return ""


# ── Suche ─────────────────────────────────────────────────────────────────────

def search_sources(query: str, sources: list[DocumentSource],
                   max_results: int = 20) -> list[SearchResult]:
    """Einfache Substring-Suche über alle gecachten Quellen."""
    if not query.strip():
        return []
    query_lower = query.lower()
    results: list[SearchResult] = []
    for source in sources:
        text = get_cached_text(source)
        if not text:
            continue
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if query_lower in line.lower():
                # Kontext: ±1 Zeile
                start = max(0, i - 1)
                end = min(len(lines), i + 2)
                snippet = " … ".join(lines[start:end]).strip()[:200]
                results.append(SearchResult(
                    source_name=source.name,
                    snippet=snippet,
                    page=0,
                ))
                if len(results) >= max_results:
                    return results
    return results
