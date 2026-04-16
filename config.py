"""Konfiguration laden, normalisieren, interaktiv erfassen und speichern."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


CONFIG_FILE = Path(__file__).parent / "config.json"
CONFIG_EXAMPLE_FILE = Path(__file__).parent / "config.example.json"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
DEFAULT_LMSTUDIO_BASE_URL = "http://localhost:1234/v1"
DEFAULT_OPENROUTER_MODEL = "meta-llama/llama-3.1-8b-instruct:free"
DEFAULT_LOCAL_MODEL = "llama3.2:3b"


DEFAULT_CONFIG: dict[str, Any] = {
    "version": 2,
    "mail": {
        "senders": ["no-reply@ekhn.info"],
        "subject_filter": "Gottesdienststatistik",
        "recipient_emails": [],
    },
    "organization": {
        "rechtsträger_nr": "",
        "bank_name": "",
        "bank_iban": "",
        "bank_bic": "",
        "partner_defaults": {
            "partner_nr": "",
            "name_institution": "",
            "anschrift": "",
            "bankname": "",
            "iban": "",
            "bic": "",
        },
    },
    "templates": {
        "eigene_gemeinde": "",
        "zur_weiterleitung": "",
    },
    "output": {
        "root_dir": str(Path(__file__).parent / "output"),
        "overview_file": str(Path(__file__).parent / "output" / "kollekten_uebersicht.xlsx"),
    },
    "runtime": {
        "log_file": str(Path(__file__).parent / "kollekten.log"),
    },
    "state": {
        "processed_emails_file": str(Path(__file__).parent / "data" / "state" / "processed_emails.json"),
        "run_history_file": str(Path(__file__).parent / "data" / "state" / "run_history.json"),
        "booking_store_file": str(Path(__file__).parent / "data" / "state" / "bookings.json"),
    },
    "reference_sources": {
        "aobj_file": str(Path(__file__).parent / "data" / "reference" / "abrechnungsobjekte.json"),
        "rules_file": str(Path(__file__).parent / "data" / "reference" / "kollektenregeln.json"),
        "manual_overrides_file": str(Path(__file__).parent / "data" / "reference" / "manual_overrides.json"),
        "kollektenplan_url": "https://www.ekhn.de/themen/gottesdienst/gottesdienst-nachrichten/kollektenplan",
        "year_plan_files": [],
        "default_partner": {
            "partner_nr": "",
            "name_institution": "",
            "anschrift": "",
            "bankname": "",
            "iban": "",
            "bic": "",
        },
    },
    "schedules": [
        {"name": "default", "mode": "now", "enabled": True, "target": "run", "time": "07:30", "date": ""},
    ],
    "app": {
        "use_tray": False,
        "autostart": False,
        "font_size": 9,
        "theme": "office2010",
    },
    "ai": {
        "provider": "disabled",
        "api_key": "",
        "model": DEFAULT_OPENROUTER_MODEL,
        "base_url": DEFAULT_OPENROUTER_BASE_URL,
        "openrouter_base_url": DEFAULT_OPENROUTER_BASE_URL,
        "ollama_base_url": DEFAULT_OLLAMA_BASE_URL,
        "lmstudio_base_url": DEFAULT_LMSTUDIO_BASE_URL,
    },
    "document_sources": [],
    "api": {
        "enabled": False,
        "port": 8765,
        "token": "",
        "allow_run": True,
        "cors_origins": ["*"],
    },
}


def load_config() -> dict[str, Any]:
    """Lädt config.json und normalisiert alte und neue Formate."""
    if CONFIG_FILE.exists():
        with CONFIG_FILE.open(encoding="utf-8") as f:
            raw = json.load(f)
        return normalize_config(raw)
    if CONFIG_EXAMPLE_FILE.exists():
        with CONFIG_EXAMPLE_FILE.open(encoding="utf-8") as f:
            raw = json.load(f)
        return normalize_config(raw)
    return copy.deepcopy(DEFAULT_CONFIG)


def save_config(cfg: dict[str, Any]) -> None:
    normalized = normalize_config(cfg)
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_FILE.open("w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2, ensure_ascii=False)


def normalize_config(cfg: dict[str, Any]) -> dict[str, Any]:
    """Macht aus Legacy-Flat-Configs und neuen Nested-Configs ein gemeinsames Schema."""
    base = copy.deepcopy(DEFAULT_CONFIG)
    if "mail" in cfg or "organization" in cfg or "templates" in cfg:
        _deep_update(base, cfg)
    else:
        legacy = {
            "mail": {
                "senders": _legacy_senders(cfg),
                "subject_filter": cfg.get("subject_filter", base["mail"]["subject_filter"]),
                "recipient_emails": _split_emails(cfg.get("recipient_emails") or cfg.get("recipient_email", "")),
            },
            "organization": {
                "rechtsträger_nr": cfg.get("rechtsträger_nr", ""),
                "bank_name": cfg.get("bank_name", ""),
                "bank_iban": cfg.get("bank_iban", ""),
                "bank_bic": cfg.get("bank_bic", ""),
            },
            "templates": {
                "eigene_gemeinde": cfg.get("template_path", ""),
                "zur_weiterleitung": cfg.get("forwarding_template_path", ""),
            },
            "output": {
                "root_dir": cfg.get("output_dir", base["output"]["root_dir"]),
                "overview_file": cfg.get("overview_file", base["output"]["overview_file"]),
            },
            "runtime": {
                "log_file": cfg.get("log_file", base["runtime"]["log_file"]),
            },
            "state": {
                "processed_emails_file": cfg.get("processed_emails_file", base["state"]["processed_emails_file"]),
                "run_history_file": cfg.get("run_history_file", base["state"]["run_history_file"]),
                "booking_store_file": cfg.get("booking_store_file", base["state"]["booking_store_file"]),
            },
            "reference_sources": {
                "aobj_file": cfg.get("aobj_file", base["reference_sources"]["aobj_file"]),
                "rules_file": cfg.get("rules_file", base["reference_sources"]["rules_file"]),
                "manual_overrides_file": cfg.get("manual_overrides_file", base["reference_sources"]["manual_overrides_file"]),
                "kollektenplan_url": cfg.get("kollektenplan_url", base["reference_sources"]["kollektenplan_url"]),
                "year_plan_files": cfg.get("year_plan_files", []),
            },
            "schedules": cfg.get("schedules", base["schedules"]),
        }
        _deep_update(base, legacy)
    _normalize_ai(base, cfg)
    _normalize_lists(base)
    _normalize_paths(base)
    _normalize_schedules(base)
    return base


def _deep_update(target: dict[str, Any], update: dict[str, Any]) -> None:
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = value


def _legacy_senders(cfg: dict[str, Any]) -> list[str]:
    senders = cfg.get("senders")
    if isinstance(senders, list):
        return [str(item) for item in senders if str(item).strip()]
    sender = cfg.get("sender_email")
    return [str(sender)] if sender else ["no-reply@ekhn.info"]


def _split_emails(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = [part.strip() for part in value.replace(";", ",").split(",")]
        return [part for part in parts if part]
    return []


def _first_text(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _normalize_base_url(value: Any) -> str:
    return _first_text(value).rstrip("/")


def _ai_default_base_url(provider: str) -> str:
    if provider == "ollama":
        return DEFAULT_OLLAMA_BASE_URL
    if provider == "lmstudio":
        return DEFAULT_LMSTUDIO_BASE_URL
    if provider == "openai":
        return DEFAULT_OPENAI_BASE_URL
    return DEFAULT_OPENROUTER_BASE_URL


def _ai_default_model(provider: str) -> str:
    if provider in {"ollama", "lmstudio"}:
        return DEFAULT_LOCAL_MODEL
    return DEFAULT_OPENROUTER_MODEL


def _normalize_ai(cfg: dict[str, Any], raw: dict[str, Any]) -> None:
    raw_ai = raw.get("ai") if isinstance(raw.get("ai"), dict) else {}
    provider = _first_text(raw_ai.get("provider"), raw.get("provider"), cfg["ai"].get("provider")).lower() or "disabled"
    cfg["ai"]["provider"] = provider
    cfg["ai"]["api_key"] = _first_text(raw_ai.get("api_key"), raw.get("api_key"), cfg["ai"].get("api_key"))

    if provider in {"ollama", "lmstudio"}:
        explicit_base_url = _first_text(raw_ai.get("base_url"), raw.get("base_url"))
        if explicit_base_url and _normalize_base_url(explicit_base_url) not in {
            DEFAULT_OPENROUTER_BASE_URL,
            DEFAULT_OPENAI_BASE_URL,
        }:
            base_url = _normalize_base_url(explicit_base_url)
        else:
            base_url = _ai_default_base_url(provider)
    else:
        base_url = _normalize_base_url(
            _first_text(
                raw_ai.get("base_url"),
                raw_ai.get("openrouter_base_url"),
                raw.get("base_url"),
                raw.get("openrouter_base_url"),
                cfg["ai"].get("base_url"),
            )
        ) or _ai_default_base_url(provider)

    cfg["ai"]["base_url"] = base_url
    cfg["ai"]["openrouter_base_url"] = base_url
    cfg["ai"]["ollama_base_url"] = _normalize_base_url(
        _first_text(
            raw_ai.get("ollama_base_url"),
            raw.get("ollama_base_url"),
            cfg["ai"].get("ollama_base_url"),
        )
    ) or DEFAULT_OLLAMA_BASE_URL
    cfg["ai"]["lmstudio_base_url"] = _normalize_base_url(
        _first_text(
            raw_ai.get("lmstudio_base_url"),
            raw.get("lmstudio_base_url"),
            cfg["ai"].get("lmstudio_base_url"),
        )
    ) or DEFAULT_LMSTUDIO_BASE_URL

    model = _first_text(raw_ai.get("model"), raw.get("model"), cfg["ai"].get("model"))
    if provider in {"ollama", "lmstudio"} and (
        not model or _normalize_base_url(model) == _normalize_base_url(DEFAULT_OPENROUTER_MODEL)
    ):
        model = _ai_default_model(provider)
    cfg["ai"]["model"] = model or _ai_default_model(provider)


def _normalize_lists(cfg: dict[str, Any]) -> None:
    cfg["mail"]["senders"] = _split_emails(cfg["mail"].get("senders", [])) or ["no-reply@ekhn.info"]
    cfg["mail"]["recipient_emails"] = _split_emails(cfg["mail"].get("recipient_emails", []))
    cfg["reference_sources"]["year_plan_files"] = [
        str(Path(item)) for item in cfg["reference_sources"].get("year_plan_files", []) if str(item).strip()
    ]


def _normalize_paths(cfg: dict[str, Any]) -> None:
    output_root = Path(cfg["output"].get("root_dir") or (Path(__file__).parent / "output"))
    cfg["output"]["root_dir"] = str(output_root)
    overview_file = Path(cfg["output"].get("overview_file") or (output_root / "kollekten_uebersicht.xlsx"))
    cfg["output"]["overview_file"] = str(overview_file)
    cfg["runtime"]["log_file"] = str(Path(cfg["runtime"].get("log_file") or (Path(__file__).parent / "kollekten.log")))
    cfg["state"]["processed_emails_file"] = str(Path(cfg["state"]["processed_emails_file"]))
    cfg["state"]["run_history_file"] = str(Path(cfg["state"]["run_history_file"]))
    cfg["state"]["booking_store_file"] = str(Path(cfg["state"].get("booking_store_file") or (Path(__file__).parent / "data" / "state" / "bookings.json")))
    for key in ("aobj_file", "rules_file", "manual_overrides_file"):
        cfg["reference_sources"][key] = str(Path(cfg["reference_sources"][key]))
    for key in ("eigene_gemeinde", "zur_weiterleitung"):
        if cfg["templates"].get(key):
            cfg["templates"][key] = str(Path(cfg["templates"][key]))


def _normalize_schedules(cfg: dict[str, Any]) -> None:
    schedules = cfg.get("schedules", [])
    normalized = []
    if not isinstance(schedules, list):
        schedules = []
    for index, item in enumerate(schedules, start=1):
        if not isinstance(item, dict):
            continue
        schedule = {
            "name": str(item.get("name") or f"schedule-{index}"),
            "mode": str(item.get("mode", "now")),
            "enabled": bool(item.get("enabled", True)),
            "target": str(item.get("target", "run")),
            "time": str(item.get("time", "07:30")),
            "date": str(item.get("date", "")),
            "monthly_day": str(item.get("monthly_day", "first")),
            "quarter_interval_months": int(item.get("quarter_interval_months", 3)),
            "command": str(item.get("command", "")),
        }
        normalized.append(schedule)
    if not normalized:
        normalized = copy.deepcopy(DEFAULT_CONFIG["schedules"])
    cfg["schedules"] = normalized


def setup_interactive() -> dict[str, Any]:
    """Einmalige Konfiguration mit Fokus auf die neuen zentralen Stammdaten."""
    cfg = load_config()
    print("=== Kollekten-Automation: Erstkonfiguration ===\n")
    cfg["templates"]["eigene_gemeinde"] = _prompt(
        "Pfad zur Vorlage 'eigene Gemeinde'",
        cfg["templates"].get("eigene_gemeinde", ""),
        required=True,
    )
    cfg["templates"]["zur_weiterleitung"] = _prompt(
        "Pfad zur Vorlage 'zur Weiterleitung'",
        cfg["templates"].get("zur_weiterleitung", ""),
        required=True,
    )
    cfg["output"]["root_dir"] = _prompt(
        "Ausgabeverzeichnis fuer monatliche Dateien und Uebersicht",
        cfg["output"].get("root_dir", ""),
        required=True,
    )
    recipient_line = _prompt(
        "Empfaenger-E-Mail(s) fuer Berichte und Weiterleitung (kommagetrennt)",
        ", ".join(cfg["mail"].get("recipient_emails", [])),
        required=False,
    )
    cfg["mail"]["recipient_emails"] = _split_emails(recipient_line)
    cfg["mail"]["senders"] = _split_emails(
        _prompt(
            "Absender-E-Mail(s) fuer Outlook-Import",
            ", ".join(cfg["mail"].get("senders", [])),
            required=True,
        )
    )
    cfg["mail"]["subject_filter"] = _prompt(
        "Betreff-Filter",
        cfg["mail"].get("subject_filter", ""),
        required=True,
    )
    cfg["organization"]["rechtsträger_nr"] = _prompt(
        "Rechtstraeger-Nr.",
        cfg["organization"].get("rechtsträger_nr", ""),
        required=True,
    )
    cfg["organization"]["bank_name"] = _prompt(
        "Bankname",
        cfg["organization"].get("bank_name", ""),
        required=True,
    )
    cfg["organization"]["bank_iban"] = _prompt(
        "IBAN",
        cfg["organization"].get("bank_iban", ""),
        required=True,
    )
    cfg["organization"]["bank_bic"] = _prompt(
        "BIC (optional)",
        cfg["organization"].get("bank_bic", ""),
        required=False,
    )
    cfg["runtime"]["log_file"] = _prompt(
        "Logdatei",
        cfg["runtime"].get("log_file", str(Path(__file__).parent / "kollekten.log")),
        required=True,
    )
    _prompt_schedule_setup(cfg)
    save_config(cfg)
    print(f"\nKonfiguration gespeichert in: {CONFIG_FILE}\n")
    return cfg


def _prompt_schedule_setup(cfg: dict[str, Any]) -> None:
    print("\nZeitplanung:")
    print("  now = sofort und ohne Task")
    print("  once = einmalig zu Datum/Uhrzeit")
    print("  on_date = Alias fuer once")
    print("  monthly_start / monthly_end = monatlich am Anfang/Ende")
    print("  quarterly_start / quarterly_end = vierteljaehrlich am Anfang/Ende")
    schedules = []
    while True:
        index = len(schedules)
        defaults = cfg["schedules"][0] if index == 0 else {"name": f"schedule-{index + 1}", "mode": "now", "time": "07:30", "date": ""}
        mode = _prompt("Zeitplan-Modus", defaults.get("mode", "now"), required=True)
        name = _prompt("Name des Zeitplans", defaults.get("name", "default"), required=True)
        time_value = _prompt("Uhrzeit HH:MM", defaults.get("time", "07:30"), required=False)
        date_value = ""
        if mode in {"once", "on_date"}:
            date_value = _prompt("Datum YYYY-MM-DD", defaults.get("date", ""), required=True)
        schedules.append(
            {
                "name": name,
                "mode": mode,
                "enabled": True,
                "target": "run",
                "time": time_value or "07:30",
                "date": date_value,
                "monthly_day": "first" if mode.endswith("start") else "last" if mode.endswith("end") else "first",
                "quarter_interval_months": 3,
            }
        )
        add_more = input("Weiteren Zeitplan hinzufuegen? [j/N]: ").strip().lower()
        if add_more not in {"j", "ja", "y", "yes"}:
            break
    cfg["schedules"] = schedules


def _prompt(label: str, default: str, *, required: bool) -> str:
    suffix = f" [{default}]" if default else ""
    answer = input(f"{label}{suffix}: ").strip()
    if answer:
        return answer
    if default:
        return default
    if required:
        raise ValueError(f"{label} darf nicht leer sein.")
    return ""


def get_config() -> dict[str, Any]:
    cfg = load_config()
    if not cfg["templates"].get("eigene_gemeinde") and not cfg["templates"].get("zur_weiterleitung"):
        raise RuntimeError(
            "Keine Konfiguration gefunden. Bitte zuerst 'python main.py config' ausfuehren."
        )
    return cfg


def upgrade_and_save() -> dict[str, Any]:
    cfg = load_config()
    save_config(cfg)
    return cfg


if __name__ == "__main__":
    setup_interactive()
