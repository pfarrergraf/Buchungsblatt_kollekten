"""Zentrale Domänenmodelle für Kollekten, Partner und Klassifikation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional


Scope = str
TemplateKind = str
BookingType = str


@dataclass(frozen=True)
class PartnerInfo:
    """Empfänger-/Partnerdaten für Weiterleitungsfälle."""

    partner_nr: str = ""
    name_institution: str = ""
    anschrift: str = ""
    bankname: str = ""
    iban: str = ""
    bic: str = ""

    def is_empty(self) -> bool:
        return not any(
            [
                self.partner_nr.strip(),
                self.name_institution.strip(),
                self.anschrift.strip(),
                self.bankname.strip(),
                self.iban.strip(),
                self.bic.strip(),
            ]
        )


@dataclass(frozen=True)
class CollectionRecord:
    """Normalisierte Kollekte nach Parsing und Klassifikation."""

    entry_id: str
    subject: str
    received: Optional[datetime]
    booking_date: date
    amount: float
    purpose: str
    scope: Scope
    template_kind: TemplateKind
    booking_type: BookingType = ""
    aobj: str = ""
    sachkonto: str = ""
    partner: Optional[PartnerInfo] = None
    source_text: str = ""
    needs_review: bool = False
    match_reason: str = ""

    def to_overview_row(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "subject": self.subject,
            "received": self.received,
            "booking_date": self.booking_date,
            "amount": self.amount,
            "purpose": self.purpose,
            "scope": self.scope,
            "template_kind": self.template_kind,
            "booking_type": self.booking_type,
            "aobj": self.aobj,
            "sachkonto": self.sachkonto,
            "partner_nr": self.partner.partner_nr if self.partner else "",
            "partner_name": self.partner.name_institution if self.partner else "",
            "partner_iban": self.partner.iban if self.partner else "",
            "partner_bic": self.partner.bic if self.partner else "",
            "partner_bankname": self.partner.bankname if self.partner else "",
            "needs_review": self.needs_review,
            "match_reason": self.match_reason,
            "source_text": self.source_text,
        }


@dataclass(frozen=True)
class ScheduleSpec:
    """Deklarative Schedule-Beschreibung für Task Scheduler und Sofortlauf."""

    name: str
    mode: str
    enabled: bool = True
    target: str = "run"
    time: str = "07:30"
    date: str = ""
    monthly_day: str = "first"
    quarter_interval_months: int = 3
    command: str = ""

    def requires_task(self) -> bool:
        return self.enabled and self.mode not in {"now"}


@dataclass(frozen=True)
class ReferenceMatch:
    """Treffer aus der Referenzlogik."""

    pattern: str = ""
    scope: Scope = ""
    template_kind: TemplateKind = ""
    booking_type: BookingType = ""
    aobj: str = ""
    sachkonto: str = ""
    partner_nr: str = ""
    partner_name: str = ""
    reason: str = ""
    confidence: float = 0.0

