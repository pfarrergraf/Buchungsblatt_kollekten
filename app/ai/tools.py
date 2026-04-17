"""KI-Tool-Definitionen und Ausführungslogik."""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

# ── Kanonische Tool-Definitionen ──────────────────────────────────────────────

_TOOLS: list[dict] = [
    # ── Bestehende Lese-Tools ─────────────────────────────────────────────────
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
    # ── Neues Wissens-Tool: Kirchenrecht ──────────────────────────────────────
    {
        "name": "suche_kirchenrecht",
        "description": (
            "Durchsucht lokal gespeicherte Kirchenrecht-Dokumente (EKHN) nach einem "
            "Stichwort oder einer Frage. Gibt relevante Textabschnitte mit Quellenangabe "
            "und Seitenzahl zurück. Immer mit Disclaimer verwenden."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Suchbegriff oder Frage, z. B. 'Kollektenzweck ändern' oder 'Kirchenvorstand Aufgaben'",
                },
            },
            "required": ["query"],
        },
    },
    # ── Neues Wissens-Tool: Handbuch ──────────────────────────────────────────
    {
        "name": "suche_handbuch",
        "description": (
            "Durchsucht das Handbuch Gemeindebüro EKHN (Stand 08/2019) nach einem Prozess "
            "oder Thema. Gibt relevante Abschnitte mit Seitenangabe zurück. "
            "Antworten immer mit 'Stand: 08/2019' kennzeichnen."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prozess": {
                    "type": "string",
                    "description": "Prozessname oder Thema, z. B. 'Spendenquittung ausstellen' oder 'Urlaubsplanung'",
                },
            },
            "required": ["prozess"],
        },
    },
    # ── Neues Tool: Formular-Info ─────────────────────────────────────────────
    {
        "name": "get_formular_info",
        "description": (
            "Findet Informationen zu einem EKHN-Formular: wo es zu finden ist, "
            "ob VPN benötigt wird, Zuständigkeit und ggf. lokale Vorlage."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "typ": {
                    "type": "string",
                    "description": "Formulartyp oder Stichwort, z. B. 'Spendenquittung', 'Ausgabeanordnung', 'Urlaubsantrag'",
                },
            },
            "required": ["typ"],
        },
    },
    # ── Neues Tool: Regionalverwaltung ────────────────────────────────────────
    {
        "name": "get_regionalverwaltung",
        "description": (
            "Gibt Kontaktdaten der zuständigen Regionalverwaltung für ein Thema zurück. "
            "Themen: Personal, Finanzen, Bau, Kiris, MACH, Gemeindeleitung."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "thema": {
                    "type": "string",
                    "description": "Thema oder Stichwort, z. B. 'Personal', 'MACH', 'Baumaßnahme'",
                },
            },
            "required": ["thema"],
        },
    },
    # ── Neues Tool: Fehler-Log ────────────────────────────────────────────────
    {
        "name": "get_recent_errors",
        "description": (
            "Gibt die letzten Fehlermeldungen aus dem Anwendungs-Log zurück. "
            "Hilfreich zur Diagnose von Problemen."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "anzahl": {
                    "type": "integer",
                    "description": "Maximale Anzahl Fehler (Standard: 10).",
                },
            },
        },
    },
    # ── Neues Tool: Kollektenplan ─────────────────────────────────────────────
    {
        "name": "get_kollektenplan",
        "description": (
            "Gibt den geplanten Kollektenzweck für ein bestimmtes Datum aus dem "
            "EKHN-Kollektenplan zurück, falls vorhanden."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "datum": {
                    "type": "string",
                    "description": "Datum im Format YYYY-MM-DD, z. B. '2026-04-19'",
                },
            },
            "required": ["datum"],
        },
    },
    # ── Neues Tool: Fällige Fristen ───────────────────────────────────────────
    {
        "name": "liste_faellige_fristen",
        "description": (
            "Listet Wiedervorlagen und Fristen auf, die innerhalb der nächsten N Tage fällig sind."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "tage": {
                    "type": "integer",
                    "description": "Anzahl Tage voraus (Standard: 7).",
                },
            },
        },
    },
    # ── Aktions-Tools (erfordern Nutzerbestätigung) ───────────────────────────
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
    {
        "name": "save_note",
        "description": (
            "Speichert eine Aktennotiz zu einem Vorgang (z. B. Buchung, Gemeinde, Sitzung). "
            "Nur aufrufen, wenn der Nutzer das ausdrücklich möchte."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "description": "Kategorie der Notiz, z. B. 'buchung', 'gottesdienst', 'allgemein'",
                },
                "entity_id": {
                    "type": "string",
                    "description": "Optionale ID oder Bezeichnung des Vorgangs",
                },
                "note": {
                    "type": "string",
                    "description": "Text der Aktennotiz",
                },
            },
            "required": ["entity_type", "note"],
        },
    },
]

# ── Bestätigungsstufen ────────────────────────────────────────────────────────
# read_only:           sofort ausführen, kein Dialog
# draft_only:          Vorschau im Chat, kein Speichern/Versand
# user_confirmed:      QMessageBox (neutral)
# user_confirmed_send: QMessageBox mit rotem E-Mail-Hinweis
# admin_only:          künftig: PIN-Bestätigung (Phase 8+)

TOOL_LEVELS: dict[str, str] = {
    "get_buchungen":           "read_only",
    "get_zusammenfassung":     "read_only",
    "konfiguration_info":      "read_only",
    "suche_kirchenrecht":      "read_only",
    "suche_handbuch":          "read_only",
    "get_formular_info":       "read_only",
    "get_regionalverwaltung":  "read_only",
    "get_recent_errors":       "read_only",
    "get_kollektenplan":       "read_only",
    "liste_faellige_fristen":  "read_only",
    "verarbeitung_starten":    "user_confirmed",
    "buchungsblatt_versenden": "user_confirmed_send",
    "save_note":               "user_confirmed",
}

# Rückwärtskompatibel: alle Tools, die eine Bestätigung erfordern
ACTION_TOOLS: frozenset[str] = frozenset(
    name for name, level in TOOL_LEVELS.items()
    if level in ("user_confirmed", "user_confirmed_send", "admin_only")
)


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
        {"type": "function", "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["parameters"],
        }}
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
        if name == "suche_kirchenrecht":
            return _suche_kirchenrecht(args, cfg)
        if name == "suche_handbuch":
            return _suche_handbuch(args, cfg)
        if name == "get_formular_info":
            return _get_formular_info(args, cfg)
        if name == "get_regionalverwaltung":
            return _get_regionalverwaltung(args, cfg)
        if name == "get_recent_errors":
            return _get_recent_errors(args, cfg)
        if name == "get_kollektenplan":
            return _get_kollektenplan(args, cfg)
        if name == "liste_faellige_fristen":
            return _liste_faellige_fristen(args, cfg)
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
        if name == "save_note":
            return _save_note(args, cfg)
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

    if name == "save_note":
        entity_type = args.get("entity_type", "allgemein")
        note = str(args.get("note", ""))[:80]
        return f"Aktennotiz speichern ({entity_type}): {note}"

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


def _suche_kirchenrecht(args: dict, cfg: dict) -> str:
    """Keyword-Suche in lokal gespeicherten Kirchenrecht-PDFs."""
    query = str(args.get("query", "")).strip()
    if not query:
        return "Bitte einen Suchbegriff angeben."

    kirchenrecht_dir = _root() / "data" / "knowledge" / "kirchenrecht"
    if not kirchenrecht_dir.exists():
        return (
            "Kirchenrecht-Ordner noch nicht vorhanden. "
            "Bitte PDFs von kirchenrecht-ekhn.de herunterladen und in "
            "'data/knowledge/kirchenrecht/' ablegen."
        )

    pdf_files = list(kirchenrecht_dir.glob("*.pdf")) + list(kirchenrecht_dir.glob("*.txt"))
    if not pdf_files:
        return (
            "Noch keine Kirchenrecht-Dokumente indexiert. "
            "Bitte PDFs von kirchenrecht-ekhn.de herunterladen und in "
            "'data/knowledge/kirchenrecht/' ablegen."
        )

    results = []
    terms = [t.lower() for t in query.split() if len(t) > 2]

    for doc_path in pdf_files:
        text = _load_or_extract_text(doc_path)
        if not text:
            continue
        snippets = _keyword_snippets(text, terms, doc_path.name, max_snippets=3)
        results.extend(snippets)

    if not results:
        return (
            f"Keine Treffer für '{query}' in den Kirchenrecht-Dokumenten gefunden.\n"
            "Hinweis: Dies ist keine verbindliche Rechtsberatung. "
            "Maßgeblich ist die jeweils aktuelle Fassung des Kirchenrechts der EKHN."
        )

    output = [f"Kirchenrecht-Suchergebnis für '{query}' ({len(results)} Treffer):\n"]
    for r in results[:5]:
        output.append(r)
    output.append(
        "\nHinweis: Dies ist keine verbindliche Rechtsberatung. "
        "Maßgeblich ist die jeweils aktuelle Fassung des Kirchenrechts der EKHN "
        "sowie im Zweifel die zuständige Regionalverwaltung oder der Stabsbereich Recht "
        "(Kirchenverwaltung Darmstadt)."
    )
    return "\n".join(output)


def _suche_handbuch(args: dict, cfg: dict) -> str:
    """Keyword-Suche im Handbuch Gemeindebüro."""
    prozess = str(args.get("prozess", "")).strip()
    if not prozess:
        return "Bitte einen Prozessnamen oder ein Thema angeben."

    # Gecachte Text-Version bevorzugen
    cache_path = _root() / "data" / "knowledge" / "handbuch_2019.txt"
    if cache_path.exists():
        text = cache_path.read_text(encoding="utf-8", errors="replace")
    else:
        # Versuche, das Original-PDF zu finden
        knowledge_dir = _root() / "data"
        pdf_candidates = list(knowledge_dir.glob("Handbuch*.pdf")) + list(knowledge_dir.glob("handbuch*.pdf"))
        if not pdf_candidates:
            return (
                "Handbuch Gemeindebüro nicht gefunden. "
                "Bitte das PDF in 'data/' ablegen (Name beginnt mit 'Handbuch')."
            )
        text = _load_or_extract_text(pdf_candidates[0])
        if text:
            # Cache anlegen
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(text, encoding="utf-8")

    if not text:
        return "Handbuch konnte nicht gelesen werden."

    terms = [t.lower() for t in prozess.split() if len(t) > 2]
    snippets = _keyword_snippets(text, terms, "Handbuch Gemeindebüro (Stand 08/2019)", max_snippets=4)

    if not snippets:
        return f"Keine Treffer für '{prozess}' im Handbuch Gemeindebüro gefunden. (Stand: 08/2019)"

    output = [f"Handbuch Gemeindebüro – Suchergebnis für '{prozess}' (Stand: 08/2019):\n"]
    output.extend(snippets[:4])
    return "\n".join(output)


def _get_formular_info(args: dict, cfg: dict) -> str:
    """Findet Formular-Informationen aus dem lokalen Index."""
    typ = str(args.get("typ", "")).strip().lower()
    index_path = _root() / "data" / "formulare" / "index.json"

    if not index_path.exists():
        return (
            "Formular-Index noch nicht vorhanden. "
            "Bitte 'data/formulare/index.json' anlegen."
        )

    try:
        formulare = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception as e:
        return f"Formular-Index konnte nicht gelesen werden: {e}"

    # Suche nach ID oder Name
    matches = [
        f for f in formulare
        if typ in f.get("id", "").lower()
        or typ in f.get("name", "").lower()
        or any(typ in k.lower() for k in f.get("schlagworte", []))
    ]

    if not matches:
        alle = ", ".join(f.get("name", f.get("id", "")) for f in formulare)
        return f"Kein Formular für '{typ}' gefunden.\nVerfügbare Formulare: {alle}"

    lines = []
    for f in matches[:3]:
        lines.append(f"Formular: {f.get('name', f.get('id', ''))}")
        lines.append(f"  Zuständigkeit: {f.get('zustaendigkeit', 'nicht angegeben')}")
        lines.append(f"  Quelle: {f.get('quelle', 'nicht angegeben')}")
        if f.get("vpn_erforderlich"):
            lines.append("  Hinweis: VPN-Zugang erforderlich")
        if f.get("url"):
            lines.append(f"  URL: {f['url']}")
        if f.get("vorlage_lokal"):
            lp = _root() / f["vorlage_lokal"]
            status = "vorhanden" if lp.exists() else "nicht gefunden"
            lines.append(f"  Lokale Vorlage: {f['vorlage_lokal']} ({status})")
        lines.append(f"  Stand: {f.get('stand', 'unbekannt')}")
        lines.append("")
    return "\n".join(lines)


def _get_regionalverwaltung(args: dict, cfg: dict) -> str:
    """Gibt Kontaktdaten der Regionalverwaltung zurück."""
    thema = str(args.get("thema", "")).strip().lower()
    index_path = _root() / "data" / "kontakte" / "regionalverwaltungen.json"

    # Konfig: Gemeinde-Ort für automatische RV-Zuordnung
    org = cfg.get("organization", {})
    gemeinde_ort = str(org.get("ort") or org.get("gemeinde_name") or "").lower()

    if not index_path.exists():
        return (
            "Regionalverwaltungs-Index noch nicht vorhanden. "
            "Bitte 'data/kontakte/regionalverwaltungen.json' anlegen."
        )

    try:
        rv_list = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception as e:
        return f"Regionalverwaltungs-Index konnte nicht gelesen werden: {e}"

    # Zuständige RV für Gemeinde-Ort
    zustaendig = None
    if gemeinde_ort:
        for rv in rv_list:
            zustaendig_fuer = [z.lower() for z in rv.get("zustaendig_fuer", [])]
            if any(gemeinde_ort in z or z in gemeinde_ort for z in zustaendig_fuer):
                zustaendig = rv
                break

    # Themen-Suche
    thema_treffer = []
    if thema:
        for rv in rv_list:
            themen = [t.lower() for t in rv.get("themen", [])]
            if any(thema in t or t in thema for t in themen):
                thema_treffer.append(rv)

    result = []
    if zustaendig:
        result.append(f"Zuständige Regionalverwaltung für {gemeinde_ort.title()}:")
        result.append(_fmt_rv(zustaendig))

    if thema_treffer and thema:
        if not zustaendig or thema_treffer[0] != zustaendig:
            result.append(f"\nRegionalverwaltungen für Thema '{thema}':")
            for rv in thema_treffer[:2]:
                result.append(_fmt_rv(rv))

    if not result:
        alle = ", ".join(rv.get("name", "") for rv in rv_list[:5])
        return (
            f"Keine Regionalverwaltung für '{thema}' oder '{gemeinde_ort}' gefunden.\n"
            f"Bekannte Regionalverwaltungen: {alle}"
        )

    return "\n".join(result)


def _fmt_rv(rv: dict) -> str:
    lines = [f"  {rv.get('name', '')}"]
    if rv.get("telefon"):
        lines.append(f"    Telefon: {rv['telefon']}")
    if rv.get("email"):
        lines.append(f"    E-Mail:  {rv['email']}")
    if rv.get("url"):
        lines.append(f"    Web:     {rv['url']}")
    themen = rv.get("themen", [])
    if themen:
        lines.append(f"    Themen:  {', '.join(themen)}")
    return "\n".join(lines)


def _get_recent_errors(args: dict, cfg: dict) -> str:
    """Liest die letzten Fehler aus dem Log."""
    anzahl = int(args.get("anzahl") or 10)
    log_path = _root() / "kollekten.log"
    if not log_path.exists():
        return "Keine Log-Datei gefunden."

    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception as e:
        return f"Log-Datei konnte nicht gelesen werden: {e}"

    error_lines = [l for l in lines if "ERROR" in l or "CRITICAL" in l or "WARNING" in l]
    recent = error_lines[-anzahl:] if error_lines else []

    if not recent:
        return "Keine Fehler oder Warnungen im Log gefunden."
    return f"Letzte {len(recent)} Einträge (ERROR/WARNING):\n" + "\n".join(recent)


def _get_kollektenplan(args: dict, cfg: dict) -> str:
    """Gibt den geplanten Kollektenzweck für ein Datum zurück."""
    datum_str = str(args.get("datum", "")).strip()
    plan_path = _root() / "data" / "state" / "kollektenplan.json"

    if not plan_path.exists():
        return (
            "Kollektenplan noch nicht hinterlegt. "
            "Bitte den EKHN-Kollektenplan-PDF importieren oder "
            "'data/state/kollektenplan.json' manuell anlegen."
        )

    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except Exception as e:
        return f"Kollektenplan konnte nicht gelesen werden: {e}"

    # Exakter Treffer
    for eintrag in plan:
        if eintrag.get("datum") == datum_str:
            zweck = eintrag.get("zweck", "")
            empfaenger = eintrag.get("empfaenger", "")
            aobj = eintrag.get("aobj_vorschlag", "")
            return (
                f"Kollekte am {datum_str}:\n"
                f"  Zweck:     {zweck}\n"
                f"  Empfänger: {empfaenger}\n"
                + (f"  AObj:      {aobj}\n" if aobj else "")
            )

    return f"Kein Eintrag im Kollektenplan für {datum_str} gefunden."


def _liste_faellige_fristen(args: dict, cfg: dict) -> str:
    """Listet fällige Wiedervorlagen auf."""
    tage = int(args.get("tage") or 7)
    wv_path = _root() / "data" / "state" / "wiedervorlagen.json"

    if not wv_path.exists():
        return "Noch keine Wiedervorlagen angelegt."

    try:
        eintraege = json.loads(wv_path.read_text(encoding="utf-8"))
    except Exception as e:
        return f"Wiedervorlagen konnten nicht gelesen werden: {e}"

    heute = date.today()
    faellig = []
    for e in eintraege:
        if e.get("erledigt"):
            continue
        frist_str = e.get("frist_datum", "")
        try:
            frist = date.fromisoformat(frist_str)
        except Exception:
            continue
        delta = (frist - heute).days
        if delta <= tage:
            faellig.append((delta, frist, e))

    if not faellig:
        return f"Keine Wiedervorlagen fällig in den nächsten {tage} Tagen."

    faellig.sort(key=lambda x: x[1])
    lines = [f"Fällige Wiedervorlagen (nächste {tage} Tage): {len(faellig)} Einträge\n"]
    for delta, frist, e in faellig:
        if delta < 0:
            status = f"ÜBERFÄLLIG seit {-delta} Tag(en)"
        elif delta == 0:
            status = "HEUTE fällig"
        else:
            status = f"in {delta} Tag(en)"
        lines.append(
            f"  [{status}] {frist.strftime('%d.%m.%Y')}  "
            f"{e.get('titel', '')} "
            f"[{e.get('kategorie', '')}]"
        )
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


def _save_note(args: dict, cfg: dict) -> str:
    """Speichert eine Aktennotiz."""
    entity_type = str(args.get("entity_type", "allgemein"))
    entity_id = str(args.get("entity_id", ""))
    note = str(args.get("note", "")).strip()

    if not note:
        return "Notiz-Text darf nicht leer sein."

    notizen_path = _root() / "data" / "state" / "notizen.json"
    notizen_path.parent.mkdir(parents=True, exist_ok=True)

    notizen: list[dict] = []
    if notizen_path.exists():
        try:
            notizen = json.loads(notizen_path.read_text(encoding="utf-8"))
        except Exception:
            notizen = []

    import uuid
    neuer_eintrag = {
        "id": str(uuid.uuid4()),
        "entity_type": entity_type,
        "entity_id": entity_id,
        "note": note,
        "erstellt_am": datetime.now().isoformat(timespec="seconds"),
    }
    notizen.append(neuer_eintrag)
    notizen_path.write_text(
        json.dumps(notizen, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return f"Aktennotiz gespeichert ({entity_type}{': ' + entity_id if entity_id else ''})."


# ── Hilfs-Funktionen für Textsuche ───────────────────────────────────────────

def _load_or_extract_text(doc_path: Path) -> str:
    """Lädt Text aus Cache oder extrahiert ihn aus PDF."""
    cache_dir = _root() / "data" / "knowledge" / "_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    import hashlib
    cache_key = hashlib.md5(str(doc_path).encode()).hexdigest()
    cache_file = cache_dir / (cache_key + ".txt")

    if cache_file.exists() and cache_file.stat().st_mtime >= doc_path.stat().st_mtime:
        return cache_file.read_text(encoding="utf-8", errors="replace")

    if doc_path.suffix.lower() == ".txt":
        text = doc_path.read_text(encoding="utf-8", errors="replace")
    else:
        try:
            import pdfplumber
            texts: list[str] = []
            with pdfplumber.open(str(doc_path)) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        texts.append(t)
            text = "\n".join(texts)
        except Exception:
            return ""

    if text:
        cache_file.write_text(text, encoding="utf-8")
    return text


def _keyword_snippets(
    text: str, terms: list[str], source_name: str, max_snippets: int = 3
) -> list[str]:
    """Gibt Textabschnitte zurück, in denen alle Suchbegriffe vorkommen."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    results = []

    for para in paragraphs:
        para_lower = para.lower()
        if all(t in para_lower for t in terms):
            snippet = para[:400].replace("\n", " ")
            results.append(f"[{source_name}]\n  {snippet}\n")
            if len(results) >= max_snippets:
                break

    # Fallback: zeilenbasiert, wenn keine Absatz-Treffer
    if not results:
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if all(t in line.lower() for t in terms):
                context_lines = lines[max(0, i - 1): i + 3]
                snippet = " ".join(context_lines)[:400]
                results.append(f"[{source_name}]\n  {snippet}\n")
                if len(results) >= max_snippets:
                    break

    return results


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
