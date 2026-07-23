"""
PUB EU direct (doar superuser): aleg caseta → perioadă → upload → live pe market=eu.
Fără tarife, fără coș.
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from home.models import ReclamaSlotNote
from home.pub_markets import PUB_MARKET_EU
from home.pub_slot_defaults import pub_slot_fetch_notes, pub_slot_live_creative

logger = logging.getLogger(__name__)

# Pagini relevante pe site-urile EU (fără Shop/Servicii/Adăpost)
PUB_EU_DIRECT_SECTIONS: tuple[tuple[str, str], ...] = (
    ("home", "Home"),
    ("pt", "Prietenul tău / Find a friend"),
    ("transport", "Transport"),
    ("mypet", "MyPet"),
    ("i_love", "I Love"),
)

_PT_MAIN_SLOTS = frozenset({"P4.3", "P5.1", "P5.2", "P5.3"})


def _eu_direct_slot_rows(section: str) -> list[dict]:
    from home.views import PUBLICITATE_SLOT_MAP

    rows = list(PUBLICITATE_SLOT_MAP.get(section) or [])
    if section == "pt":
        return [r for r in rows if (r.get("code") or "") in _PT_MAIN_SLOTS]
    return rows


def _parse_iso_date(raw: str) -> date | None:
    s = (raw or "").strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _save_eu_upload(uploaded, prefix: str) -> str:
    """Salvează fișier în media; returnează URL public (/media/...)."""
    if not uploaded:
        return ""
    name = Path(getattr(uploaded, "name", "") or "file.bin").name
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)[:120] or "file.bin"
    stamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    path = default_storage.save(f"pub_eu/{prefix}/{stamp}_{safe}", uploaded)
    url = default_storage.url(path)
    return url or ""


def _build_eu_note_json(
    *,
    img_url: str,
    video_url: str,
    link: str,
    alt: str,
    start: date | None,
    end: date | None,
    plain_text: str = "",
) -> str:
    if plain_text.strip() and not img_url and not video_url:
        # Burtieră tip text
        return plain_text.strip()[:8000]
    payload: dict = {
        "img": img_url or "",
        "video": video_url or "",
        "link": (link or "").strip(),
        "alt": (alt or "").strip() or "EU-Adopt",
    }
    if start and end:
        payload["assets"] = [
            {
                "img": img_url or "",
                "video": video_url or "",
                "link": (link or "").strip(),
                "alt": (alt or "").strip() or "EU-Adopt",
                "start": start.isoformat(),
                "end": end.isoformat(),
            }
        ]
    return json.dumps(payload, ensure_ascii=False)


@login_required
@require_http_methods(["GET", "POST"])
def publicitate_eu_direct_view(request):
    """Superuser: publică direct pe Publi EU, fără coș/tarife."""
    if not getattr(request.user, "is_superuser", False):
        messages.error(request, "Doar superuser poate folosi PUB EU direct.")
        return redirect("home")

    section = (request.GET.get("sect") or request.POST.get("sect") or "home").strip().lower()
    allowed_sects = {s for s, _ in PUB_EU_DIRECT_SECTIONS}
    if section not in allowed_sects:
        section = "home"
    slots = _eu_direct_slot_rows(section)
    slot_codes = {(r.get("code") or "").strip() for r in slots}

    selected = (request.GET.get("slot") or request.POST.get("slot") or "").strip()
    if selected and selected not in slot_codes:
        selected = ""
    # Nu auto-selectăm prima casetă: userul apasă pe hartă

    if request.method == "POST":
        action = (request.POST.get("action") or "publish").strip().lower()
        slot = (request.POST.get("slot") or "").strip()
        if slot not in slot_codes:
            messages.error(request, "Caseta selectată nu e validă.")
            return redirect(f"{reverse('publicitate_eu_direct')}?sect={section}")

        if action == "clear":
            ReclamaSlotNote.objects.filter(
                section=section, slot_code=slot, market=PUB_MARKET_EU
            ).delete()
            messages.success(request, f"Șters pe EU: {section}/{slot}.")
            return redirect(f"{reverse('publicitate_eu_direct')}?sect={section}&slot={slot}")

        start = _parse_iso_date(request.POST.get("start_date") or "")
        end = _parse_iso_date(request.POST.get("end_date") or "")
        if start and end and end < start:
            messages.error(request, "Data de final trebuie să fie după data de început.")
            return redirect(f"{reverse('publicitate_eu_direct')}?sect={section}&slot={slot}")

        link = (request.POST.get("link") or "").strip()
        alt = (request.POST.get("alt") or "").strip()
        plain = (request.POST.get("plain_text") or "").strip()
        keep_media = (request.POST.get("keep_media") or "") == "1"

        existing = (
            ReclamaSlotNote.objects.filter(
                section=section, slot_code=slot, market=PUB_MARKET_EU
            ).first()
        )
        prev_img = ""
        prev_video = ""
        if existing and keep_media:
            try:
                from home.views import _pt_pub_slot_parse_note

                parsed = _pt_pub_slot_parse_note(existing) or {}
                prev_img = (parsed.get("img") or "").strip()
                prev_video = (parsed.get("video") or "").strip()
            except Exception:
                pass

        img_url = prev_img
        video_url = prev_video
        up_img = request.FILES.get("image")
        up_vid = request.FILES.get("video")
        if up_img and up_vid:
            messages.error(request, "Alegeți fie imagine, fie video — nu ambele.")
            return redirect(f"{reverse('publicitate_eu_direct')}?sect={section}&slot={slot}")
        try:
            max_mb = 8
            from django.conf import settings as dj_settings

            max_mb = max(1, int(getattr(dj_settings, "PUBLICITATE_CREATIVE_MAX_UPLOAD_MB", 8)))
        except Exception:
            max_mb = 8
        max_b = max_mb * 1024 * 1024
        if up_img:
            if up_img.size > max_b:
                messages.error(request, f"Imaginea depășește {max_mb} MB.")
                return redirect(f"{reverse('publicitate_eu_direct')}?sect={section}&slot={slot}")
            img_url = _save_eu_upload(up_img, f"{section}_{slot}")
            video_url = ""
        elif up_vid:
            if up_vid.size > max_b:
                messages.error(request, f"Video-ul depășește {max_mb} MB.")
                return redirect(f"{reverse('publicitate_eu_direct')}?sect={section}&slot={slot}")
            video_url = _save_eu_upload(up_vid, f"{section}_{slot}")
            img_url = ""

        is_burtiera = section == "home" and slot == "Burtieră"
        if is_burtiera:
            if not plain and not link:
                messages.error(request, "Burtieră: completați text sau link.")
                return redirect(f"{reverse('publicitate_eu_direct')}?sect={section}&slot={slot}")
            body = plain or link
            if link and not plain:
                body = link
            note_text = body[:8000]
        else:
            if not img_url and not video_url and not link:
                messages.error(request, "Încărcați o imagine/video sau setați un link.")
                return redirect(f"{reverse('publicitate_eu_direct')}?sect={section}&slot={slot}")
            note_text = _build_eu_note_json(
                img_url=img_url,
                video_url=video_url,
                link=link,
                alt=alt,
                start=start,
                end=end,
                plain_text="",
            )

        note, _created = ReclamaSlotNote.objects.update_or_create(
            section=section,
            slot_code=slot,
            market=PUB_MARKET_EU,
            defaults={"text": note_text, "updated_by": request.user},
        )
        period = ""
        if start and end:
            period = f" ({start.isoformat()} → {end.isoformat()})"
        messages.success(
            request,
            f"Live pe EU: {section}/{slot}{period}. Vizibil pe .com / .de / .fr / .es.",
        )
        return redirect(f"{reverse('publicitate_eu_direct')}?sect={section}&slot={slot}")

    # GET — aceeași hartă (wire) ca PUB, fără coș/tarife; panou stânga = upload EU
    from home.views import _publicitate_harta_context

    current = None
    creative = None
    form_start = ""
    form_end = ""
    form_link = ""
    form_alt = ""
    form_plain = ""
    if selected:
        notes = pub_slot_fetch_notes(section, [selected], market=PUB_MARKET_EU)
        current = notes.get(selected)
        if current:
            creative = pub_slot_live_creative(
                section, selected, current, market=PUB_MARKET_EU, lang="en"
            )
            try:
                from home.views import _pt_pub_slot_parse_note

                parsed = _pt_pub_slot_parse_note(current) or {}
                form_link = (parsed.get("link") or "").strip()
                form_alt = (parsed.get("alt") or "").strip()
                assets = parsed.get("assets") or []
                if isinstance(assets, list) and assets:
                    a0 = assets[0] if isinstance(assets[0], dict) else {}
                    form_start = (a0.get("start") or "").strip()
                    form_end = (a0.get("end") or "").strip()
                    if not form_link:
                        form_link = (a0.get("link") or "").strip()
                    if not form_alt:
                        form_alt = (a0.get("alt") or "").strip()
                if section == "home" and selected == "Burtieră":
                    form_plain = (getattr(current, "text", None) or "")[:8000]
            except Exception:
                pass

    today = timezone.localdate()
    default_end = today + timedelta(days=365)
    ctx = _publicitate_harta_context(request, "harta")
    # Doar paginile EU (fără Servicii / Shop / cos_pub)
    eu_codes = {s for s, _ in PUB_EU_DIRECT_SECTIONS}
    ctx["pub_sections"] = [
        {"code": code, "label": label} for code, label in PUB_EU_DIRECT_SECTIONS
    ]
    if section not in eu_codes:
        section = "home"
    ctx["pub_selected_section"] = section
    ctx["pub_initial_slot"] = selected or ""
    ctx["pub_eu_direct_mode"] = True
    ctx["pub_nav"] = "eu_direct"
    ctx["eu_slot"] = selected
    ctx["eu_note"] = current
    ctx["eu_creative"] = creative
    ctx["eu_today"] = form_start or today.isoformat()
    ctx["eu_default_end"] = form_end or default_end.isoformat()
    ctx["eu_form_link"] = form_link
    ctx["eu_form_alt"] = form_alt
    ctx["eu_form_plain"] = form_plain
    return render(request, "anunturi/publicitate_harta.html", ctx)
