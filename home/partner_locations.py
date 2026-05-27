"""
Puncte de lucru partener — helperi pentru cont, oferte, emailuri, Servicii.
"""

from __future__ import annotations

import unicodedata
from typing import TYPE_CHECKING
from urllib.parse import quote

from django.contrib.auth.models import User

from home.models import AccountProfile, PartnerLocation

if TYPE_CHECKING:
    from home.models import CollaboratorServiceOffer


def strip_d(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def norm_county(s: str) -> str:
    return strip_d(s).lower().strip()


def location_county_norm(loc: PartnerLocation) -> str:
    return norm_county(loc.judet or "")


def maps_query_for_location(loc: PartnerLocation) -> str:
    parts: list[str] = []
    for bit in (loc.adresa, loc.oras, loc.judet):
        s = (bit or "").strip()
        if s:
            parts.append(s)
    if parts:
        blob = " ".join(parts).lower()
        if "românia" not in blob and "romania" not in blob:
            parts.append("România")
        return ", ".join(parts)
    return ""


def google_maps_url(query: str) -> str:
    q = (query or "").strip()
    if not q:
        return ""
    return f"https://www.google.com/maps/search/?api=1&query={quote(q, safe='')}"


def user_can_manage_locations(user: User) -> bool:
    ap = getattr(user, "account_profile", None)
    return bool(
        ap
        and ap.role in (AccountProfile.ROLE_COLLAB, AccountProfile.ROLE_ORG)
        and getattr(user, "is_authenticated", False)
    )


def active_locations_for_user(user: User):
    return PartnerLocation.objects.filter(user=user, is_active=True).order_by(
        "-is_primary", "-is_sediu_social", "judet", "oras", "pk"
    )


def primary_location_for_user(user: User) -> PartnerLocation | None:
    return (
        PartnerLocation.objects.filter(user=user, is_active=True, is_primary=True)
        .order_by("-pk")
        .first()
    )


def sediu_social_for_user(user: User) -> PartnerLocation | None:
    return (
        PartnerLocation.objects.filter(user=user, is_active=True, is_sediu_social=True)
        .order_by("-pk")
        .first()
    )


def effective_location_for_offer(offer: CollaboratorServiceOffer) -> PartnerLocation | None:
    pl = getattr(offer, "partner_location", None)
    if pl and pl.is_active:
        return pl
    return primary_location_for_user(offer.collaborator)


def offer_county_norm(offer: CollaboratorServiceOffer) -> str:
    loc = effective_location_for_offer(offer)
    if loc:
        return location_county_norm(loc)
    prof = getattr(offer.collaborator, "profile", None)
    if prof:
        raw = (prof.company_judet or prof.judet or "").strip()
        return norm_county(raw)
    return ""


def location_display_label(loc: PartnerLocation) -> str:
    if (loc.label or "").strip():
        return loc.label.strip()
    return f"{loc.oras}, {loc.judet}".strip(", ")


def location_lines_for_display(loc: PartnerLocation, *, include_contact: bool = True) -> list[str]:
    lines: list[str] = []
    lines.append(f"Punct de lucru: {location_display_label(loc)}")
    if loc.is_sediu_social:
        lines.append("Tip: sediu social")
    elif loc.is_primary:
        lines.append("Tip: punct principal")
    if (loc.adresa or "").strip():
        lines.append(f"Adresă: {loc.adresa.strip()}")
    loc_bits = ", ".join(x for x in [(loc.oras or "").strip(), (loc.judet or "").strip()] if x)
    if loc_bits:
        lines.append(f"Localitate: {loc_bits}")
    if include_contact and (loc.phone or "").strip():
        lines.append(f"Telefon punct: {loc.phone.strip()}")
    return lines


def location_block_text(loc: PartnerLocation | None, collab_user: User) -> str:
    """Bloc text pentru email (punct + contact firmă)."""
    prof = getattr(collab_user, "profile", None)
    contact_person = (collab_user.get_full_name() or "").strip() or collab_user.username
    lines: list[str] = []
    if prof and (prof.company_display_name or "").strip():
        lines.append(f"Partener: {prof.company_display_name.strip()}")
    else:
        lines.append(f"Partener: {contact_person}")
    if loc:
        lines.extend(location_lines_for_display(loc))
    elif prof:
        addr = (prof.company_address or "").strip()
        if addr:
            lines.append(f"Adresă: {addr}")
        loc_bits = ", ".join(
            x for x in [(prof.company_oras or "").strip(), (prof.company_judet or "").strip()] if x
        )
        if loc_bits:
            lines.append(f"Localitate: {loc_bits}")
    if prof and (prof.phone or "").strip():
        lines.append(f"Telefon contact cont: {prof.phone.strip()}")
    if collab_user.email:
        lines.append(f"Email: {collab_user.email}")
    lines.append(f"Persoană de contact: {contact_person}")
    return "\n".join(lines)


def location_block_for_offer(offer: CollaboratorServiceOffer) -> str:
    loc = effective_location_for_offer(offer)
    return location_block_text(loc, offer.collaborator)


def maps_url_for_offer(offer: CollaboratorServiceOffer) -> str:
    loc = effective_location_for_offer(offer)
    if loc:
        return google_maps_url(maps_query_for_location(loc))
    prof = getattr(offer.collaborator, "profile", None)
    if not prof:
        return ""
    parts = []
    for bit in (prof.company_address, prof.company_oras, prof.company_judet):
        s = (bit or "").strip()
        if s:
            parts.append(s)
    if parts:
        parts.append("România")
        return google_maps_url(", ".join(parts))
    return ""


def claim_location_snapshot(loc: PartnerLocation | None) -> dict[str, str]:
    if not loc:
        return {
            "partner_location_label_snapshot": "",
            "partner_location_judet_snapshot": "",
            "partner_location_oras_snapshot": "",
            "partner_location_adresa_snapshot": "",
        }
    return {
        "partner_location_label_snapshot": location_display_label(loc)[:120],
        "partner_location_judet_snapshot": (loc.judet or "")[:120],
        "partner_location_oras_snapshot": (loc.oras or "")[:120],
        "partner_location_adresa_snapshot": (loc.adresa or "")[:255],
    }


def snapshot_block_from_claim(claim) -> str:
    """Text din snapshot salvat la claim (email istoric)."""
    lines: list[str] = []
    label = (claim.partner_location_label_snapshot or "").strip()
    if label:
        lines.append(f"Punct de lucru: {label}")
    jud = (claim.partner_location_judet_snapshot or "").strip()
    oras = (claim.partner_location_oras_snapshot or "").strip()
    if jud or oras:
        lines.append(f"Localitate: {', '.join(x for x in [oras, jud] if x)}")
    adr = (claim.partner_location_adresa_snapshot or "").strip()
    if adr:
        lines.append(f"Adresă: {adr}")
    return "\n".join(lines)


def create_locations_from_signup(user: User, data: dict, *, tip_partener: str = "") -> None:
    """
    După înregistrare colaborator/ONG: sediu social + punct principal.
    data: judet, oras, adresa_firma; opțional pl_* sau pl_same_as_sediu.
    """
    if PartnerLocation.objects.filter(user=user).exists():
        return
    jud = (data.get("judet") or "").strip()[:120]
    oras = (data.get("oras") or "").strip()[:120]
    adresa = (data.get("adresa_firma") or "").strip()[:255]
    same = data.get("pl_same_as_sediu") in (True, "on", "1", "da", "true")
    if same:
        pl_jud, pl_oras, pl_adresa = jud, oras, adresa
        pl_label = "Punct principal"
    else:
        pl_jud = (data.get("pl_judet") or jud).strip()[:120]
        pl_oras = (data.get("pl_oras") or oras).strip()[:120]
        pl_adresa = (data.get("pl_adresa") or "").strip()[:255]
        pl_label = (data.get("pl_label") or "Punct principal").strip()[:120]
    kind = ""
    tip = (tip_partener or "").strip().lower()
    if tip == "magazin":
        kind = PartnerLocation.KIND_MAGAZIN
    elif tip in ("cabinet", "cv"):
        kind = PartnerLocation.KIND_CABINET
    elif tip == "servicii":
        kind = PartnerLocation.KIND_SERVICII
    PartnerLocation.objects.create(
        user=user,
        label="Sediu social",
        judet=jud,
        oras=oras,
        adresa=adresa,
        kind=kind,
        is_sediu_social=True,
        is_primary=False,
        is_active=True,
    )
    PartnerLocation.objects.create(
        user=user,
        label=pl_label or "Punct principal",
        judet=pl_jud,
        oras=pl_oras,
        adresa=pl_adresa,
        phone=(data.get("pl_phone") or "").strip()[:40],
        kind=kind,
        is_sediu_social=False,
        is_primary=True,
        is_active=True,
    )


def backfill_locations_from_profile(user: User) -> int:
    """Creează sediu + punct principal din UserProfile dacă lipsesc."""
    if PartnerLocation.objects.filter(user=user).exists():
        return 0
    prof = getattr(user, "profile", None)
    if not prof:
        return 0
    jud = (prof.company_judet or prof.judet or "").strip()
    oras = (prof.company_oras or prof.oras or "").strip()
    if not jud or not oras:
        return 0
    kind = ""
    ct = (prof.collaborator_type or "").strip().lower()
    if ct == "magazin":
        kind = PartnerLocation.KIND_MAGAZIN
    elif ct in ("cabinet", "cv"):
        kind = PartnerLocation.KIND_CABINET
    elif ct == "servicii":
        kind = PartnerLocation.KIND_SERVICII
    adresa = (prof.company_address or "").strip()
    PartnerLocation.objects.create(
        user=user,
        label="Sediu social",
        judet=jud[:120],
        oras=oras[:120],
        adresa=adresa[:255],
        kind=kind,
        is_sediu_social=True,
        is_primary=False,
        is_active=True,
    )
    PartnerLocation.objects.create(
        user=user,
        label="Punct principal",
        judet=jud[:120],
        oras=oras[:120],
        adresa=adresa[:255],
        kind=kind,
        is_sediu_social=False,
        is_primary=True,
        is_active=True,
    )
    return 2
