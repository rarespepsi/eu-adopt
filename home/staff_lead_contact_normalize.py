"""Normalizare câmpuri contact prospecte (telefon multiplu, note suplimentare)."""

from __future__ import annotations

import re

from home.models import StaffOnboardingLead

PHONE_SPLIT_RE = re.compile(r"[/;,|]+|\s{2,}")
PHONE_KEEP_RE = re.compile(r"[^\d+]")


def split_phone_field(raw: str | None) -> list[str]:
    """Extrage numere distincte din câmp combinat (/, spații duble, etc.)."""
    text = (raw or "").replace("\xa0", " ").strip()
    if not text:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for part in PHONE_SPLIT_RE.split(text):
        cleaned = re.sub(r"\s+", " ", part.strip())
        if not cleaned:
            continue
        digits = PHONE_KEEP_RE.sub("", cleaned)
        if len(digits) < 7:
            continue
        key = digits[-10:] if len(digits) >= 10 else digits
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned[:40])
    return out


def _extras_note(label: str, extras: list[str], notes: str) -> str:
    line = f"{label}: {', '.join(extras)}"
    if line in (notes or ""):
        return notes or ""
    base = (notes or "").rstrip()
    return f"{base}\n{line}".strip() if base else line


def normalize_lead_phone(lead: StaffOnboardingLead, *, save: bool = False) -> bool:
    """Păstrează primul telefon pe lead; restul în notes. Returnează True dacă s-a schimbat ceva."""
    phones = split_phone_field(lead.phone)
    if not phones:
        return False
    primary = phones[0]
    notes = lead.notes or ""
    changed = False
    if len(phones) > 1:
        new_notes = _extras_note("Telefoane suplimentare", phones[1:], notes)
        if new_notes != notes:
            notes = new_notes
            changed = True
    if (lead.phone or "").strip() != primary:
        lead.phone = primary
        changed = True
    if changed:
        lead.notes = notes
        if save:
            lead.save(update_fields=["phone", "notes", "updated_at"])
    return changed


def lead_has_multi_phone(raw: str | None) -> bool:
    return len(split_phone_field(raw)) > 1
