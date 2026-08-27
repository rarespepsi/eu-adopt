"""
Analiza → Audio/TV: prospecte media (radio / TV / presă) pentru parteneriate difuzare.
"""
from __future__ import annotations

import csv
import io
import re
from urllib.parse import quote

from django.db.models import Count, Q, QuerySet
from django.http import HttpRequest

from home.euadopt_public_contact import EUADOPT_PUBLIC_PHONE_DISPLAY
from home.models import MediaOutreachProspect

CSV_FIELDS = (
    "media_kind",
    "outlet_name",
    "contact_name",
    "email",
    "phone",
    "website",
    "judet",
    "oras",
    "notes",
    "source",
    "outreach_status",
)

_PHONE_DIGITS_RE = re.compile(r"\D+")


def normalize_media_kind(raw: str) -> str:
    v = (raw or "").strip().lower()
    aliases = {
        "radio": MediaOutreachProspect.KIND_RADIO,
        "tv": MediaOutreachProspect.KIND_TV,
        "televiziune": MediaOutreachProspect.KIND_TV,
        "television": MediaOutreachProspect.KIND_TV,
        "press": MediaOutreachProspect.KIND_PRESS,
        "presa": MediaOutreachProspect.KIND_PRESS,
        "ziar": MediaOutreachProspect.KIND_PRESS,
        "redactie": MediaOutreachProspect.KIND_PRESS,
        "redacție": MediaOutreachProspect.KIND_PRESS,
        "newspaper": MediaOutreachProspect.KIND_PRESS,
        "podcast": MediaOutreachProspect.KIND_PODCAST,
        "other": MediaOutreachProspect.KIND_OTHER,
        "altele": MediaOutreachProspect.KIND_OTHER,
    }
    return aliases.get(v, MediaOutreachProspect.KIND_PRESS)


def media_wa_digits(phone: str) -> str:
    d = _PHONE_DIGITS_RE.sub("", phone or "")
    if d.startswith("0") and len(d) >= 10:
        d = "40" + d[1:]
    if d.startswith("40"):
        return d
    if len(d) == 9:
        return "40" + d
    return d


def build_media_outreach_whatsapp_text(p: MediaOutreachProspect) -> str:
    who = (p.contact_name or "").strip() or (p.outlet_name or "").strip() or "Stimată redacție"
    outlet = (p.outlet_name or "").strip() or "postul dumneavoastră"
    return (
        f"Bună ziua, {who},\n\n"
        f"Sunt Adrian, de la EU-Adopt (eu-adopt.ro) — platformă națională/europeană "
        f"pentru animale, cu misiune de tip ONG, gratuită pentru adăposturi și parteneri.\n\n"
        f"Propunem un parteneriat cu {outlet}: câteva difuzări ale spotului nostru radio (~30s) "
        f"în schimbul promovării postului pe site (partener media).\n\n"
        f"Site: https://eu-adopt.ro/\n"
        f"Contact: contact@eu-adopt.ro · {EUADOPT_PUBLIC_PHONE_DISPLAY}\n\n"
        f"Dacă sunteți deschiși, vă trimit spotul pe email.\n\n"
        f"Cu respect,\n"
        f"Adrian · EU-Adopt"
    )


def build_media_wa_me_url(p: MediaOutreachProspect) -> str:
    digits = media_wa_digits(p.phone)
    if not digits:
        return ""
    text = build_media_outreach_whatsapp_text(p)
    return f"https://wa.me/{digits}?text={quote(text)}"


def media_prospects_filtered(request: HttpRequest) -> QuerySet[MediaOutreachProspect]:
    qs = MediaOutreachProspect.objects.all()
    kind = (request.GET.get("kind") or "").strip().lower()
    if kind in dict(MediaOutreachProspect.KIND_CHOICES):
        qs = qs.filter(media_kind=kind)
    status = (request.GET.get("status") or "").strip().lower()
    if status in dict(MediaOutreachProspect.STATUS_CHOICES):
        qs = qs.filter(outreach_status=status)
    judet = (request.GET.get("judet") or "").strip()
    if judet:
        qs = qs.filter(judet__icontains=judet)
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(outlet_name__icontains=q)
            | Q(contact_name__icontains=q)
            | Q(email__icontains=q)
            | Q(phone__icontains=q)
            | Q(oras__icontains=q)
            | Q(notes__icontains=q)
        )
    contact = (request.GET.get("contact") or "").strip().lower()
    if contact == "email":
        qs = qs.exclude(email="")
    elif contact == "phone":
        qs = qs.exclude(phone="")
    elif contact == "email_only":
        qs = qs.exclude(email="").filter(phone="")
    elif contact == "phone_only":
        qs = qs.exclude(phone="").filter(email="")
    elif contact == "both":
        qs = qs.exclude(email="").exclude(phone="")
    elif contact == "none":
        qs = qs.filter(email="", phone="")
    return qs


def media_kpi_counts() -> dict[str, int]:
    base = MediaOutreachProspect.objects.all()
    by_kind = {row["media_kind"]: row["c"] for row in base.values("media_kind").annotate(c=Count("id"))}
    return {
        "total": base.count(),
        "with_email": base.exclude(email="").count(),
        "with_phone": base.exclude(phone="").count(),
        "phone_only": base.exclude(phone="").filter(email="").count(),
        "radio": by_kind.get(MediaOutreachProspect.KIND_RADIO, 0),
        "tv": by_kind.get(MediaOutreachProspect.KIND_TV, 0),
        "press": by_kind.get(MediaOutreachProspect.KIND_PRESS, 0),
        "podcast": by_kind.get(MediaOutreachProspect.KIND_PODCAST, 0),
    }


def import_media_csv(text: str, *, default_source: str = "import CSV") -> dict[str, int]:
    """Import CSV; actualizează pe email (dacă e) sau creează rând nou. Returnează stats."""
    stats = {"created": 0, "updated": 0, "skipped": 0}
    # strip BOM
    if text.startswith("\ufeff"):
        text = text[1:]
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return stats
    for raw in reader:
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items() if k}
        outlet = row.get("outlet_name") or row.get("denumire") or row.get("name") or ""
        if not outlet:
            stats["skipped"] += 1
            continue
        kind = normalize_media_kind(row.get("media_kind") or row.get("tip") or "")
        email = (row.get("email") or "").strip().lower()
        phone = row.get("phone") or row.get("telefon") or ""
        contact = row.get("contact_name") or row.get("contact") or ""
        website = row.get("website") or row.get("site") or ""
        judet = row.get("judet") or ""
        oras = row.get("oras") or row.get("oraș") or ""
        notes = row.get("notes") or row.get("note") or ""
        source = row.get("source") or row.get("sursă") or default_source
        status_raw = (row.get("outreach_status") or row.get("status") or "").strip().lower()
        status = (
            status_raw
            if status_raw in dict(MediaOutreachProspect.STATUS_CHOICES)
            else MediaOutreachProspect.ST_NEW
        )

        obj = None
        # Nu unifica pe email singur (ex. office@digi.ro e partajat de mai multe branduri).
        if email:
            obj = MediaOutreachProspect.objects.filter(
                email__iexact=email,
                outlet_name__iexact=outlet,
            ).first()
        if obj is None:
            obj = MediaOutreachProspect.objects.filter(
                outlet_name__iexact=outlet,
                media_kind=kind,
                judet__iexact=judet,
            ).first()

        fields = {
            "media_kind": kind,
            "outlet_name": outlet[:255],
            "contact_name": contact[:200],
            "email": email[:254] if email else "",
            "phone": phone[:40],
            "website": website[:500],
            "judet": judet[:120],
            "oras": oras[:120],
            "notes": notes,
            "source": source[:120],
            "outreach_status": status,
        }
        if obj:
            for k, v in fields.items():
                setattr(obj, k, v)
            obj.save()
            stats["updated"] += 1
        else:
            MediaOutreachProspect.objects.create(**fields)
            stats["created"] += 1
    return stats


def export_media_csv(qs: QuerySet[MediaOutreachProspect]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for p in qs.iterator():
        writer.writerow(
            {
                "media_kind": p.media_kind,
                "outlet_name": p.outlet_name,
                "contact_name": p.contact_name,
                "email": p.email,
                "phone": p.phone,
                "website": p.website,
                "judet": p.judet,
                "oras": p.oras,
                "notes": p.notes,
                "source": p.source,
                "outreach_status": p.outreach_status,
            }
        )
    return buf.getvalue()
