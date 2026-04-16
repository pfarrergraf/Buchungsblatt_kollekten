"""Referenzdaten, Stammdaten und Hilfsimporte für die Kollekten-Zuordnung."""
from __future__ import annotations

import json
import re
import urllib.request
from urllib.parse import urljoin
from pathlib import Path
from typing import Any

import openpyxl

from models import PartnerInfo, ReferenceMatch


REFERENCE_DIR = Path(__file__).parent / "data" / "reference"
STATE_DIR = Path(__file__).parent / "data" / "state"

DEFAULT_AOBJ_CATALOG = [
    {"code": "0110", "label": "Gottesdienst", "sachkonto": "", "category": "liturgie"},
    {"code": "0210", "label": "allg. kirchenmusikalischer Dienst", "sachkonto": "", "category": "musik"},
    {"code": "0220", "label": "Chorarbeit", "sachkonto": "", "category": "musik"},
    {"code": "0410", "label": "Christenlehre", "sachkonto": "", "category": "unterricht"},
    {"code": "0420", "label": "Konfirmandenunterricht", "sachkonto": "", "category": "unterricht"},
    {"code": "0430", "label": "Kinder- und Jugendarbeit", "sachkonto": "", "category": "jugend"},
    {"code": "0510", "label": "Allgemeine Gemeindearbeit", "sachkonto": "", "category": "gemeinde"},
]

DEFAULT_RULES = {
    "version": 1,
    "patterns": [
        {"pattern": "eigene Gemeinde", "scope": "eigene_gemeinde", "booking_type": "Kollekten", "aobj": "0110"},
        {"pattern": "Gottesdienst", "scope": "eigene_gemeinde", "booking_type": "Kollekten", "aobj": "0110"},
        {"pattern": "Kirchenmusik", "scope": "eigene_gemeinde", "booking_type": "Kollekten", "aobj": "0210"},
        {"pattern": "kirchenmusikal", "scope": "eigene_gemeinde", "booking_type": "Kollekten", "aobj": "0210"},
        {"pattern": "Chor", "scope": "eigene_gemeinde", "booking_type": "Kollekten", "aobj": "0220"},
        {"pattern": "Konfirm", "scope": "eigene_gemeinde", "booking_type": "Kollekten", "aobj": "0420"},
        {"pattern": "Kinder u. Jugendarbeit", "scope": "eigene_gemeinde", "booking_type": "Kollekten", "aobj": "0430"},
        {"pattern": "Kinder-u. Jugendarbeit", "scope": "eigene_gemeinde", "booking_type": "Kollekten", "aobj": "0430"},
        {"pattern": "Allgemeine Gemeindearbeit", "scope": "eigene_gemeinde", "booking_type": "Kollekten", "aobj": "0510"},
        {"pattern": "allgem. Gemeindearbeit", "scope": "eigene_gemeinde", "booking_type": "Kollekten", "aobj": "0510"},
        {"pattern": "Öffentlichkeitsarbeit eig. Gemeinde", "scope": "eigene_gemeinde", "booking_type": "Kollekten", "aobj": "0510"},
        {"pattern": "Bibelhaus", "scope": "zur_weiterleitung", "booking_type": "Kollekten"},
        {"pattern": "Brot für die Welt", "scope": "zur_weiterleitung", "booking_type": "Kollekten"},
        {"pattern": "Christl. Jüdische Verständigung", "scope": "zur_weiterleitung", "booking_type": "Kollekten"},
        {"pattern": "Diakonie", "scope": "zur_weiterleitung", "booking_type": "Kollekten"},
        {"pattern": "Inclusive Gemeindearbeit EKHN", "scope": "zur_weiterleitung", "booking_type": "Kollekten"},
        {"pattern": "JuLeiCa", "scope": "zur_weiterleitung", "booking_type": "Kollekten"},
        {"pattern": "Stiftung", "scope": "zur_weiterleitung", "booking_type": "Kollekten"},
        {"pattern": "Ev. Bund", "scope": "zur_weiterleitung", "booking_type": "Kollekten"},
        {"pattern": "Jüdische Verständigung", "scope": "zur_weiterleitung", "booking_type": "Kollekten"},
        {"pattern": "mAqom", "scope": "zur_weiterleitung", "booking_type": "Kollekten"},
        {"pattern": "Kirchenasyl", "scope": "zur_weiterleitung", "booking_type": "Kollekten"},
    ],
    "fallback": {"scope": "eigene_gemeinde", "booking_type": "Kollekten", "aobj": "0110", "sachkonto": ""},
}

DEFAULT_MANUAL_OVERRIDES = {"version": 1, "items": []}


def ensure_reference_files(cfg: dict) -> None:
    ref = _reference_paths(cfg)
    ref["dir"].mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not ref["aobj"].exists():
        _write_json(ref["aobj"], DEFAULT_AOBJ_CATALOG)
    if not ref["rules"].exists():
        _write_json(ref["rules"], DEFAULT_RULES)
    if not ref["overrides"].exists():
        _write_json(ref["overrides"], DEFAULT_MANUAL_OVERRIDES)


def _reference_paths(cfg: dict) -> dict[str, Path]:
    sources = cfg.get("reference_sources", {})
    return {
        "dir": REFERENCE_DIR,
        "aobj": Path(sources.get("aobj_file", REFERENCE_DIR / "abrechnungsobjekte.json")),
        "rules": Path(sources.get("rules_file", REFERENCE_DIR / "kollektenregeln.json")),
        "overrides": Path(sources.get("manual_overrides_file", REFERENCE_DIR / "manual_overrides.json")),
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_aobj_catalog(cfg: dict) -> list[dict[str, Any]]:
    paths = _reference_paths(cfg)
    data = _load_json(paths["aobj"], DEFAULT_AOBJ_CATALOG)
    return data if isinstance(data, list) else DEFAULT_AOBJ_CATALOG


def load_rules(cfg: dict) -> dict[str, Any]:
    paths = _reference_paths(cfg)
    data = _load_json(paths["rules"], DEFAULT_RULES)
    return data if isinstance(data, dict) else DEFAULT_RULES


def load_manual_overrides(cfg: dict) -> list[dict[str, Any]]:
    paths = _reference_paths(cfg)
    data = _load_json(paths["overrides"], DEFAULT_MANUAL_OVERRIDES)
    if isinstance(data, dict):
        return list(data.get("items", []))
    if isinstance(data, list):
        return data
    return []


def load_reference_bundle(cfg: dict) -> dict[str, Any]:
    ensure_reference_files(cfg)
    return {
        "aobj_catalog": load_aobj_catalog(cfg),
        "rules": load_rules(cfg),
        "manual_overrides": load_manual_overrides(cfg),
        "year_plans": import_year_plans(cfg),
        "remote_links": discover_kollektenplan_links(cfg),
    }


def import_year_plans(cfg: dict) -> list[dict[str, Any]]:
    source_paths = cfg.get("reference_sources", {}).get("year_plan_files", [])
    plans: list[dict[str, Any]] = []
    for raw_path in source_paths:
        path = Path(raw_path)
        if not path.exists():
            continue
        try:
            wb = openpyxl.load_workbook(path, data_only=False)
        except Exception:
            continue
        for sheet in wb.worksheets:
            for row in sheet.iter_rows():
                for cell in row:
                    value = cell.value
                    if not isinstance(value, str):
                        continue
                    text = value.strip()
                    if not text or len(text) < 3:
                        continue
                    plans.append(
                        {
                            "source_file": str(path),
                            "sheet": sheet.title,
                            "cell": cell.coordinate,
                            "text": text,
                            "highlighted": _looks_blue(cell),
                        }
                    )
    return plans


def _looks_blue(cell) -> bool:
    candidates = []
    for style_part in (cell.fill.fgColor, cell.font.color if cell.font else None):
        if style_part is None:
            continue
        color_type = getattr(style_part, "type", "")
        color_value = getattr(style_part, "rgb", "") or getattr(style_part, "indexed", "") or getattr(style_part, "theme", "")
        if color_type == "rgb" and isinstance(color_value, str):
            candidates.append(color_value.lower())
    for value in candidates:
        if "0000ff" in value or "00b0f0" in value:
            return True
    return False


def discover_kollektenplan_links(cfg: dict) -> list[dict[str, str]]:
    url = cfg.get("reference_sources", {}).get("kollektenplan_url", "")
    if not url:
        return []
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            html = response.read().decode("utf-8", errors="ignore")
    except Exception:
        return []
    links: list[dict[str, str]] = []
    for match in re.finditer(r'href=["\']([^"\']+\.pdf)["\']', html, re.IGNORECASE):
        href = match.group(1)
        if href.startswith("/"):
            href = urljoin(url, href)
        links.append({"url": href, "source_page": url})
    return links


def find_reference_match(text: str, cfg: dict, bundle: dict[str, Any] | None = None) -> ReferenceMatch:
    if bundle is None:
        bundle = load_reference_bundle(cfg)
    normalized = text.casefold()
    for override in bundle.get("manual_overrides", []):
        pattern = str(override.get("pattern", "")).strip()
        if not pattern:
            continue
        if pattern.casefold() in normalized:
            return ReferenceMatch(
                pattern=pattern,
                scope=str(override.get("scope", "")),
                template_kind=str(override.get("template_kind", "")),
                booking_type=str(override.get("booking_type", "")),
                aobj=str(override.get("aobj", "")),
                sachkonto=str(override.get("sachkonto", "")),
                partner_nr=str(override.get("partner_nr", "")),
                partner_name=str(override.get("partner_name", "")),
                reason=f"Manueller Override: {pattern}",
                confidence=1.0,
            )
    best: ReferenceMatch | None = None
    best_score = -1
    for rule in bundle.get("rules", {}).get("patterns", []):
        pattern = str(rule.get("pattern", "")).strip()
        if not pattern:
            continue
        if pattern.casefold() in normalized:
            scope = str(rule.get("scope", "")).strip()
            booking_type = str(rule.get("booking_type", "")).strip()
            aobj = str(rule.get("aobj", "")).strip()
            sachkonto = str(rule.get("sachkonto", "")).strip()
            template_kind = "zur_weiterleitung" if scope == "zur_weiterleitung" else "eigene_gemeinde"
            candidate = ReferenceMatch(
                pattern=pattern,
                scope=scope,
                template_kind=template_kind,
                booking_type=booking_type,
                aobj=aobj,
                sachkonto=sachkonto,
                reason=f"Regel: {pattern}",
                confidence=0.9,
            )
            score = len(pattern)
            if score > best_score:
                best = candidate
                best_score = score
    if best is not None:
        return best
    fallback = bundle.get("rules", {}).get("fallback", DEFAULT_RULES["fallback"])
    return ReferenceMatch(
        scope=str(fallback.get("scope", "eigene_gemeinde")),
        booking_type=str(fallback.get("booking_type", "Kollekten")),
        aobj=str(fallback.get("aobj", "")),
        sachkonto=str(fallback.get("sachkonto", "")),
        reason="Fallback-Regel",
        confidence=0.2,
    )


def resolve_partner(rule: ReferenceMatch, cfg: dict) -> PartnerInfo:
    partner_cfg = cfg.get("organization", {}).get("partner_defaults", {}) or cfg.get("reference_sources", {}).get("default_partner", {})
    return PartnerInfo(
        partner_nr=rule.partner_nr or str(partner_cfg.get("partner_nr", "") or ""),
        name_institution=rule.partner_name or str(partner_cfg.get("name_institution", "") or ""),
        anschrift=str(partner_cfg.get("anschrift", "") or ""),
        bankname=str(partner_cfg.get("bankname", "") or ""),
        iban=str(partner_cfg.get("iban", "") or ""),
        bic=str(partner_cfg.get("bic", "") or ""),
    )
