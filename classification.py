"""Zuordnung von geparsten E-Mails zu Scope, AObj und Exportziel."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from models import CollectionRecord
from references import find_reference_match, load_reference_bundle, resolve_partner


def classify_collection(
    parsed_email: Any,
    cfg: dict,
    *,
    entry_id: str = "",
    subject: str = "",
    received: datetime | None = None,
    bundle: dict[str, Any] | None = None,
) -> CollectionRecord:
    bundle = bundle or load_reference_bundle(cfg)
    purpose = getattr(parsed_email, "verwendungszweck", "") or ""
    context = purpose or getattr(parsed_email, "raw_text", "")
    match = find_reference_match(context, cfg, bundle=bundle)
    scope = match.scope or "eigene_gemeinde"
    template_kind = match.template_kind or ("zur_weiterleitung" if scope == "zur_weiterleitung" else "eigene_gemeinde")
    booking_type = match.booking_type or _guess_booking_type(context)
    aobj = match.aobj or _default_aobj_for_booking_type(booking_type, bundle, scope)
    sachkonto = match.sachkonto or _default_sachkonto_for_booking_type(booking_type, bundle, scope)
    partner = resolve_partner(match, cfg) if scope == "zur_weiterleitung" else None
    needs_review = match.confidence < 0.5
    reason = match.reason
    if needs_review:
        reason = f"{reason} | manuelle Pruefung empfohlen"
    return CollectionRecord(
        entry_id=entry_id,
        subject=subject,
        received=received,
        booking_date=getattr(parsed_email, "datum"),
        amount=getattr(parsed_email, "betrag"),
        purpose=purpose,
        scope=scope,
        template_kind=template_kind,
        booking_type=booking_type,
        aobj=aobj,
        sachkonto=sachkonto,
        partner=partner,
        source_text=getattr(parsed_email, "raw_text", ""),
        needs_review=needs_review,
        match_reason=reason,
    )


def _guess_booking_type(text: str) -> str:
    lowered = text.casefold()
    if "spende" in lowered:
        return "Spenden"
    return "Kollekten"


def _default_aobj_for_booking_type(booking_type: str, bundle: dict[str, Any], scope: str) -> str:
    fallback = bundle.get("rules", {}).get("fallback", {})
    if scope == "zur_weiterleitung":
        return str(fallback.get("aobj", "") or "")
    if booking_type == "Spenden":
        return "0110"
    return str(fallback.get("aobj", "") or "0110")


def _default_sachkonto_for_booking_type(booking_type: str, bundle: dict[str, Any], scope: str) -> str:
    fallback = bundle.get("rules", {}).get("fallback", {})
    if scope == "zur_weiterleitung":
        return str(fallback.get("sachkonto", "") or "")
    return str(fallback.get("sachkonto", "") or "")
