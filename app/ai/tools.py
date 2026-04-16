"""KI-Tool-Definitionen und Ausführungslogik."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Any

# ── Kanonische Tool-Definitionen ──────────────────────────────────────────────

_TOOLS: list[dict] = [
    {
        "name": "get_buchungen",
        "description": (
            "Listet verarbeitete Kollekten-Buchungen auf. "
            "Ohne Filter: alle vorhandenen Buchungen. "
            "Gibt Datum, Betrag, Verwendungszweck und Typ zurück."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "monat": {
                    "type": "integer",
                    "description": "Monat (1–12), optional. Wenn weggelassen: alle Monate.",
                },
                "jahr": {
                    "type": "integer",
                    "description": "Jahr z. B. 2026, optional. Wenn weggelassen: alle Jahre.",
                },
            },
        },
    },
    {
        "name": "get_zusammenfassung",
        "description": (
            "Gibt Summen (eigene Gemeinde / Weiterleitung / Gesamt) und Anzahl "
            "der Buchungen für einen Zeitraum zurück."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "monat": {"type": "integer", "description": "Monat (1–12), optional."},
                "jahr": {"type": "integer", "description": "Jahr z. B. 2026, optional."},
            },
        },
    },
    {
        "name": "konfiguration_info",
        "description": (
            "Gibt Informationen über die App-Konfiguration zurück: "
            "Gemeindename, konfigurierte Empfänger-E-Mail-Adressen, "
            "Status der Vorlage-Dateien."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "verarbeitung_starten",
        "description": (
            "Startet die Outlook-E-Mail-Verarbeitung: liest neue Kollekten-E-Mails "
            "und erstellt/aktualisiert die Buchungsblätter. "
            "Nur aufrufen, wenn der Nutzer das ausdrücklich bestätigt hat."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "dry_run": {
                    "type": "boolean",
                    "description": "Wenn true: nur simulieren, keine Dateien schreiben.",
                },
            },
        },
    },
    {
        "name": "buchungsblatt_versenden",
        "description": (
            "Versendet die erzeugten Buchungsblatt-Dateien (xlsx) für einen Monat "
            "per Outlook an die konfigurierten Empfänger. "
            "Nur aufrufen, wenn der Nutzer das ausdrücklich bestätigt hat."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "monat": {"type": "integer", "description": "Monat (1–12)."},
                "jahr": {"type": "integer", "description": "Jahr z. B. 2026."},
            },
            "required": ["monat", "jahr"],
        },
    },
]

# Tools, die eine Nutzerbestätigung erfordern
ACTION_TOOLS: frozenset[str] = frozenset({"verarbeitung_starten", "buchungsblatt_versenden"})


# ── Adapter: kanonisches Format → Provider-Format ─────────────────────────────

def to_anthropic_tools() -> list[dict]:
    """Konvertiert zu Anthropic tool_use-Format."""
    return [
        {"name": t["name"], "description": t["description"], "input_schema": t["parameters"]}
        for t in _TOOLS
    ]


def to_openai_tools() -> list[dict]:
    """Konvertiert zu OpenAI function-calling-Format."""
    return [
        {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}}
        for t in _TOOLS
    ]


# ── Ausführungslogik ──────────────────────────────────────────────────────────

def execute_tool(name: str, args: dict, cfg: dict) -> str:
    """Führt ein Lese-Tool aus. Aktions-Tools müssen über execute_action_tool laufen."""
    try:
        if name == "get_buchungen":
            return _get_buchungen(args, cfg)
        if name == "get_zusammenfassung":
            return _get_zusammenfassung(args, cfg)
        if name == "konfiguration_info":
            return _konfiguration_info(cfg)
        if name in ACTION_TOOLS:
            return "Dieses Tool erfordert eine explizite Nutzerbestätigung."
        return f"Unbekanntes Tool: {name}"
    except Exception as exc:
        return f"Fehler bei Tool '{name}': {exc}"


def execute_action_tool(name: str, args: dict, cfg: dict) -> str:
    """Führt ein Aktions-Tool aus (bereits vom Nutzer bestätigt)."""
    try:
        if name == "verarbeitung_starten":
            return _verarbeitung_starten(args, cfg)
        if name == "buchungsblatt_versenden":
            return _buchungsblatt_versenden(args, cfg)
        return f"Unbekanntes Aktions-Tool: {name}"
    except Exception as exc:
        return f"Fehler: {exc}"


def describe_action(name: str, args: dict, cfg: dict) -> str:
    """Gibt eine menschenlesbare Beschreibung des geplanten Aktions-Tools zurück."""
    recipients = cfg.get("mail", {}).get("recipient_emails", [])
    recipient_str = ", ".join(recipients) if recipients else "konfigurierte Empfänger"

    if name == "verarbeitung_starten":
        dry = args.get("dry_run", False)
        if dry:
            return "Outlook-E-Mails simuliert verarbeiten (Testlauf, keine Dateien)"
        return "Neue Outlook-E-Mails verarbeiten und Buchungsblätter erstellen"

    if name == "buchungsblatt_versenden":
        monat = int(args.get("monat", 0))
        jahr = int(args.get("jahr", 0))
        monat_name = _monat_name(monat)
        return f"Buchungsblätter {monat_name} {jahr} per Outlook an {recipient_str} versenden"

    return f"Aktion '{name}' ausführen"


# ── Interne Tool-Implementierungen ────────────────────────────────────────────

def _root() -> Path:
    return Path(__file__).parent.parent.parent


def _get_buchungen(args: dict, cfg: dict) -> str:
    sys.path.insert(0, str(_root()))
    from booking_store import get_booking_rows

    monat = args.get("monat")
    jahr = args.get("jahr")
    rows = get_booking_rows(cfg)

    filtered = [
        row for row in rows
        if (bd := _coerce_date(row.get("booking_date"))) is not None
        and (not monat or bd.month == int(monat))
        and (not jahr or bd.year == int(jahr))
    ]

    if not filtered:
        zeitraum = _zeitraum_str(monat, jahr)
        return f"Keine Buchungen gefunden{' für ' + zeitraum if zeitraum else ''}."

    lines = [f"Buchungen ({len(filtered)}):"]
    for row in sorted(filtered, key=lambda x: str(x.get("booking_date", ""))):
        bd = _coerce_date(row.get("booking_date"))
        scope = str(row.get("scope", ""))
        typ = "Weiterleit." if "weiter" in scope else "Eigene"
        lines.append(
            f"  {_fmt_date(bd)}  {_fmt_eur(row.get('amount')):>12}  "
            f"{str(row.get('purpose', ''))[:45]:<45}  {typ}"
        )
    return "\n".join(lines)


def _get_zusammenfassung(args: dict, cfg: dict) -> str:
    sys.path.insert(0, str(_root()))
    from booking_store import get_booking_rows

    monat = args.get("monat")
    jahr = args.get("jahr")
    rows = get_booking_rows(cfg)

    eigene = 0.0
    weiter = 0.0
    count = 0
    for row in rows:
        bd = _coerce_date(row.get("booking_date"))
        if bd is None:
            continue
        if monat and bd.month != int(monat):
            continue
        if jahr and bd.year != int(jahr):
            continue
        try:
            betrag = float(row.get("amount") or 0)
        except Exception:
            betrag = 0.0
        if "weiter" in str(row.get("scope", "")):
            weiter += betrag
        else:
            eigene += betrag
        count += 1

    zeitraum = _zeitraum_str(monat, jahr) or "Gesamt"
    return (
        f"Zusammenfassung {zeitraum}:\n"
        f"  Buchungen:          {count}\n"
        f"  Eigene Gemeinde:    {_fmt_eur(eigene)}\n"
        f"  Zur Weiterleitung:  {_fmt_eur(weiter)}\n"
        f"  Gesamt:             {_fmt_eur(eigene + weiter)}"
    )


def _konfiguration_info(cfg: dict) -> str:
    org = cfg.get("organization", {})
    gemeinde = org.get("gemeinde_name") or f"RV {org.get('rechtsträger_nr', '')}"
    recipients = cfg.get("mail", {}).get("recipient_emails", [])
    templates = cfg.get("templates", {})

    lines = [
        f"Gemeinde: {gemeinde}",
        f"Empfänger: {', '.join(recipients) if recipients else '(keine konfiguriert)'}",
    ]
    for key, label in [
        ("eigene_gemeinde", "Vorlage eigene Gemeinde"),
        ("zur_weiterleitung", "Vorlage zur Weiterleitung"),
    ]:
        path = templates.get(key, "")
        if path and Path(path).exists():
            lines.append(f"{label}: OK ({Path(path).name})")
        elif path:
            lines.append(f"{label}: FEHLT ({Path(path).name})")
        else:
            lines.append(f"{label}: nicht konfiguriert")
    return "\n".join(lines)


def _verarbeitung_starten(args: dict, cfg: dict) -> str:
    sys.path.insert(0, str(_root()))
    import main as m

    dry_run = bool(args.get("dry_run", False))
    processed, errors = m.run(dry_run=dry_run)
    if dry_run:
        return f"Testlauf abgeschlossen: {processed} Buchungen würden verarbeitet, {errors} Fehler."
    return f"Verarbeitung abgeschlossen: {processed} neue Buchungen, {errors} Fehler."


def _buchungsblatt_versenden(args: dict, cfg: dict) -> str:
    sys.path.insert(0, str(_root()))
    from booking_store import get_booking_rows
    from email_sender import send_attachments

    monat = int(args["monat"])
    jahr = int(args["jahr"])
    rows = get_booking_rows(cfg)

    paths: set[Path] = set()
    for row in rows:
        bd = _coerce_date(row.get("booking_date"))
        if bd and bd.month == monat and bd.year == jahr:
            tf = row.get("target_file")
            if tf and Path(tf).exists():
                paths.add(Path(tf))

    if not paths:
        return f"Keine Buchungsblatt-Dateien für {monat:02d}/{jahr} gefunden."

    monat_str = _monat_name(monat)
    subject = f"Kollekten-Buchungsblätter {monat_str} {jahr}"
    body = f"Anbei die Buchungsblätter für {monat_str} {jahr} ({len(paths)} Datei(en))."
    ok, count = send_attachments(cfg, sorted(paths), subject=subject, body=body)
    if ok:
        return f"E-Mail mit {count} Buchungsblatt-Datei(en) erfolgreich versendet."
    return "E-Mail konnte nicht versendet werden. Bitte Outlook und Konfiguration prüfen."


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────

def _coerce_date(value: Any):
    if value is None:
        return None
    if hasattr(value, "month"):
        return value
    if isinstance(value, str) and value:
        try:
            return date.fromisoformat(value[:10])
        except Exception:
            return None
    return None


def _fmt_date(v: Any) -> str:
    return v.strftime("%d.%m.%Y") if hasattr(v, "strftime") else str(v or "")


def _fmt_eur(v: Any) -> str:
    try:
        return "{:,.2f} €".format(float(v)).replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(v or "0,00 €")


def _monat_name(monat: int) -> str:
    namen = ["Januar", "Februar", "März", "April", "Mai", "Juni",
             "Juli", "August", "September", "Oktober", "November", "Dezember"]
    return namen[monat - 1] if 1 <= monat <= 12 else str(monat)


def _zeitraum_str(monat, jahr) -> str:
    if monat and jahr:
        return f"{_monat_name(int(monat))} {jahr}"
    if monat:
        return f"Monat {int(monat):02d}"
    if jahr:
        return str(jahr)
    return ""
