"""E-Mail-Parser: extrahiert Datum, Betrag und Verwendungszweck."""
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class KollekteData:
    datum: date
    betrag: float
    verwendungszweck: str
    raw_text: str


# Datum: "hier die Statistik zum Gottesdienst DD.MM.[YY[YY]] ..."
# Jahr ist optional — manche E-Mails senden nur DD.MM.
_DATE_PATTERN = re.compile(
    r"hier die Statistik zum Gottesdienst\s+"
    r"(\d{1,2}\.\d{1,2}\.(?:\d{4}|\d{2})?)",
    re.IGNORECASE,
)

# Betrag-Muster (am Zeilenende):
#   99,70       1.234,56        → deutsche Dezimalzahl (mit opt. €)
#   50.-        50,-            → Strich als Dezimalstelle → x.00
#   31€         31              → Ganzzahl mit oder ohne €
_RE_GERMAN_DECIMAL = re.compile(r"([\d\.]+,\d{2})\s*€?\s*$")
_RE_DASH_DECIMAL   = re.compile(r"(\d+)[.,-]-\s*€?\s*$")
_RE_INTEGER_EURO   = re.compile(r"(\d+)\s*€\s*$")


def _parse_date(date_str: str, fallback_year: Optional[int] = None) -> date:
    """Parst DD.MM.YYYY, DD.MM.YY und DD.MM. (Jahr aus fallback_year)."""
    # Vollständiges Datum mit 4- oder 2-stelligem Jahr
    for fmt in ("%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    # Datum ohne Jahr (z.B. "05.04.")
    date_str_clean = date_str.rstrip(".")
    year = fallback_year or datetime.now().year
    try:
        d = datetime.strptime(date_str_clean, "%d.%m").date()
        return d.replace(year=year)
    except ValueError:
        pass

    raise ValueError(f"Unbekanntes Datumsformat: {date_str!r}")


def _parse_german_float(amount_str: str) -> float:
    """Konvertiert '1.234,56' → 1234.56 und '99,70' → 99.70."""
    cleaned = amount_str.replace(".", "").replace(",", ".")
    return float(cleaned)


def _get_content_lines(text: str) -> list[str]:
    """Gibt nicht-leere Zeilen zurück, ohne die Disclaimer-Zeilen am Ende."""
    lines = [l.strip() for l in text.splitlines()]
    filtered = []
    for line in lines:
        if not line:
            continue
        if line.startswith("Dies ist eine automatisch"):
            break
        if line.startswith("Verantwortlich für den Versand"):
            break
        filtered.append(line)
    return filtered


def _extract_betrag_und_zweck(line: str) -> Optional[tuple[float, str]]:
    """
    Extrahiert (betrag, verwendungszweck) aus der letzten Inhaltszeile.
    Gibt None zurück wenn kein Betrag erkennbar ist.

    Unterstützte Formate:
      Stiftung für das Leben. 99,70          → Punkt-Trenner
      Kinder-u. Jugendarbeit, 231,00         → Komma-Trenner
      Christl. Jüdische Verständigung 147,29 → Leerzeichen
      134,00 €                               → Nur Betrag (kein Zweck)
      Kirchenmusik 31€                       → Ganzzahl mit €
      Ev. Bund 50.-                          → Strich statt Dezimale
    """
    line = line.strip()

    # 1) Deutsche Dezimalzahl (opt. €) am Ende
    m = _RE_GERMAN_DECIMAL.search(line)
    if m:
        betrag = _parse_german_float(m.group(1))
        zweck = line[:m.start()].strip().rstrip(".,")
        return betrag, zweck

    # 2) Strich-Dezimale: "50.-" oder "50,-"
    m = _RE_DASH_DECIMAL.search(line)
    if m:
        betrag = float(m.group(1))
        zweck = line[:m.start()].strip().rstrip(".,")
        return betrag, zweck

    # 3) Ganzzahl mit €: "31€"
    m = _RE_INTEGER_EURO.search(line)
    if m:
        betrag = float(m.group(1))
        zweck = line[:m.start()].strip().rstrip(".,")
        return betrag, zweck

    return None


def parse_email(body: str, received_date: Optional[date] = None) -> Optional[KollekteData]:
    """
    Parst den E-Mail-Body und gibt KollekteData zurück oder None bei Fehler.

    received_date wird verwendet um das Jahr zu ermitteln wenn die E-Mail
    kein Jahr im Datum enthält (Format DD.MM.).
    """
    date_match = _DATE_PATTERN.search(body)
    if not date_match:
        return None

    fallback_year = received_date.year if received_date else None
    datum = _parse_date(date_match.group(1), fallback_year=fallback_year)

    content_lines = _get_content_lines(body)
    if not content_lines:
        return None

    result = _extract_betrag_und_zweck(content_lines[-1])
    if result is None:
        return None

    betrag, verwendungszweck = result

    return KollekteData(
        datum=datum,
        betrag=betrag,
        verwendungszweck=verwendungszweck,
        raw_text=body,
    )


if __name__ == "__main__":
    from datetime import date as dt

    samples = [
        (
            "Format A: Punkt-Trenner, Jahr 2-stellig",
            """Hallo,
hier die Statistik zum Gottesdienst 22.03.26. Judika:
28
8
Stiftung für das Leben. 99,70
Dies ist eine automatisch erstellte E-Mail von https://termine.ekhn.de.""",
            None,
        ),
        (
            "Format B: Leerzeichen-Trenner, Jahr 4-stellig",
            "Hallo,\nhier die Statistik zum Gottesdienst 2.04.2026 Quasimodogeniti:\n43\n22\nKinder-u. Jugendarbeit eigene Gemeinde, 231,00",
            None,
        ),
        (
            "Format C: kein Jahr im Datum (Osternacht 05.04.)",
            """Hallo,\r\n\r\nhier die Statistik zum Gottesdienst 05.04. Osternacht:\r\n\r\n38\r\n\r\n9\r\n\r\nArbeit mit Kindern, Jugendlichen in Gemeinden, Dekanaten und Jugendwerken, 96,25\r\n\r\nDies ist eine automatisch erstellte E-Mail.""",
            dt(2026, 4, 5),
        ),
        (
            "Format D: Leerzeichen vor Betrag, kein Jahrestrennzeichen",
            """Hallo,\r\n\r\nhier die Statistik zum Gottesdienst 03.04.26. Karfreitag:\r\n\r\n43\r\n\r\n5\r\n\r\nChristl. Jüdische Verständigung 147,29\r\n\r\nDies ist eine automatisch erstellte E-Mail.""",
            None,
        ),
    ]

    for name, body, recv in samples:
        result = parse_email(body, received_date=recv)
        print(f"\n--- {name} ---")
        if result:
            print(f"  Datum:            {result.datum.strftime('%d.%m.%Y')}")
            print(f"  Betrag:           {result.betrag:.2f} €")
            print(f"  Verwendungszweck: {result.verwendungszweck}")
        else:
            print("  FEHLER: Konnte E-Mail nicht parsen.")
