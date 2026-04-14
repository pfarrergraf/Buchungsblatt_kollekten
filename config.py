"""Konfiguration laden und speichern."""
import json
import os
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.json"

DEFAULTS = {
    "template_path": "",
    "output_dir": str(Path(__file__).parent),
    "sender_email": "no-reply@ekhn.info",
    "subject_filter": "Gottesdienststatistik",
    "processed_emails_file": str(Path(__file__).parent / "processed_emails.json"),
    "log_file": str(Path(__file__).parent / "kollekten.log"),
    "rechtsträger_nr": "",
    "bank_name": "",
    "bank_iban": "",
}


def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return {**DEFAULTS, **json.load(f)}
    return dict(DEFAULTS)


def save_config(cfg: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def setup_interactive() -> dict:
    """Fragt einmalig nach Pfaden und speichert sie in config.json."""
    cfg = load_config()

    print("=== Kollekten-Automation: Erstkonfiguration ===\n")

    # Template-Pfad
    current = cfg.get("template_path", "")
    prompt = f"Pfad zur Excel-Vorlage [{current}]: " if current else "Pfad zur Excel-Vorlage: "
    answer = input(prompt).strip()
    if answer:
        cfg["template_path"] = answer
    elif not current:
        raise ValueError("Vorlagenpfad darf nicht leer sein.")

    # Ausgabeverzeichnis
    current_out = cfg.get("output_dir", "")
    prompt_out = f"Ausgabeverzeichnis für monatliche Dateien [{current_out}]: "
    answer_out = input(prompt_out).strip()
    if answer_out:
        cfg["output_dir"] = answer_out

    save_config(cfg)
    print(f"\nKonfiguration gespeichert in: {CONFIG_FILE}\n")
    return cfg


def get_config() -> dict:
    """Gibt Konfiguration zurück; bricht ab wenn template_path fehlt."""
    cfg = load_config()
    if not cfg.get("template_path"):
        raise RuntimeError(
            "Keine Konfiguration gefunden. Bitte zuerst 'python config.py' ausführen."
        )
    return cfg


if __name__ == "__main__":
    setup_interactive()
