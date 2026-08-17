"""
Postări automate Facebook — multi-piață (RO/DE/FR/ES/COM).

Flux 1: animal / campanie site → delivery per piață configurată.
Flux 2 (mirror RO): în home.facebook_ro_mirror (oprit până la tokenuri).

Anti-buclă: doar RO e sursă Facebook pentru mirror; DE/FR/ES/COM niciodată.
Tokenurile nu se loghează. System User token din .env e convertit la Page token
via GET /me/accounts (New Page Experience cere Page token, eroare 190/2069032).
"""
from __future__ import annotations

import json
import logging
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from home.facebook_markets import (
    configured_markets,
    facebook_auto_post_enabled,
    facebook_graph_version,
    facebook_max_posts_per_day,
    market_creds,
    market_lang,
)

logger = logging.getLogger(__name__)

RO_TZ = ZoneInfo("Europe/Bucharest")

KIND_ANIMAL = "animal"
KIND_CAMPANIE = "campanie"
KIND_RO_MIRROR = "ro_mirror"

STATUS_PENDING = "pending"
STATUS_POSTED = "posted"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"
STATUS_PARTIAL = "partial"


@dataclass
class FacebookPostResult:
    ok: bool
    facebook_post_id: str = ""
    error: str = ""
    deferred: bool = False
    market: str = ""


def site_base_url() -> str:
    from django.conf import settings

    return (getattr(settings, "SITE_BASE_URL", "") or "https://eu-adopt.ro").rstrip("/")


def absolute_media_url(file_field) -> str:
    if not file_field:
        return ""
    try:
        url = file_field.url
    except Exception:
        return ""
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return site_base_url() + (url if url.startswith("/") else "/" + url)


def posts_today_count(market: str = "ro") -> int:
    from home.models import FacebookOutboundDelivery

    now_ro = timezone.now().astimezone(RO_TZ)
    start = datetime(now_ro.year, now_ro.month, now_ro.day, tzinfo=RO_TZ)
    end = start + timedelta(days=1)
    return FacebookOutboundDelivery.objects.filter(
        market=market,
        status=STATUS_POSTED,
        posted_at__gte=start,
        posted_at__lt=end,
    ).count()


def remaining_posts_today(market: str = "ro") -> int:
    return max(0, facebook_max_posts_per_day() - posts_today_count(market))


def _species_ro(listing) -> str:
    sp = (getattr(listing, "species", "") or "").strip().lower()
    if sp == "dog":
        return "Câine"
    if sp == "cat":
        return "Pisică"
    return (getattr(listing, "species", "") or "Animal").strip() or "Animal"


def build_animal_message(listing) -> tuple[str, str, str]:
    name = (listing.name or "Prieten").strip()
    species = _species_ro(listing)
    age = (listing.age_label or "").strip()
    city = (listing.city or "").strip()
    county = (listing.county or "").strip()
    loc = ", ".join(p for p in (city, county) if p)
    path = reverse("pets_single", args=[listing.pk])
    link = site_base_url() + path
    lines = [f"🐾 {name} — {species}"]
    if age:
        lines.append(f"Vârstă: {age}")
    if loc:
        lines.append(f"📍 {loc}")
    lines.append("")
    lines.append("Vezi detalii pe eu-adopt.ro:")
    lines.append(link)
    img = ""
    for attr in ("photo_1", "photo_2", "photo_3"):
        img = absolute_media_url(getattr(listing, attr, None))
        if img:
            break
    return "\n".join(lines), link, img


def build_campanie_message(camp) -> tuple[str, str, str]:
    species = camp.species_label()
    path = reverse("publicitate_campanii_judet", kwargs={"judet_slug": camp.judet_slug})
    link = site_base_url() + path
    lines = [
        "💉 Campanie gratuită de sterilizare",
        f"📍 {camp.localitate}, {camp.judet}",
        f"📅 {camp.date_start.isoformat()} – {camp.date_end.isoformat()}",
    ]
    if species and species != "—":
        lines.append(f"Pentru: {species}")
    lines.append("")
    lines.append("Detalii pe harta Campanii:")
    lines.append(link)
    img = absolute_media_url(getattr(camp, "photo", None))
    return "\n".join(lines), link, img


def translate_facebook_message(text: str, *, target_lang: str) -> str:
    """
    Gemini: păstrează sens, ton, linkuri; fără informații inventate.
    Dacă traducerea eșuează → textul original (RO).
    """
    raw = (text or "").strip()
    tl = (target_lang or "en").strip().lower()[:2]
    if not raw or tl == "ro":
        return raw
    try:
        from home.ugc_translate import _gemini_translate

        # Prompt mai strict pentru postări FB (linkuri intacte)
        translated = _gemini_translate_fb(raw, tl)
        if translated:
            return translated
        # fallback pe helperul UGC
        alt = _gemini_translate(raw, tl)
        return (alt or raw).strip() or raw
    except Exception:
        logger.exception("facebook translate failed lang=%s", tl)
        return raw


def _gemini_translate_fb(text: str, target_lang: str) -> str | None:
    from django.conf import settings

    api_key = getattr(settings, "EUADOPT_GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    from home.facebook_markets import MARKET_LANG_NAME

    lang_name = MARKET_LANG_NAME.get(target_lang, target_lang)
    primary = getattr(settings, "SITE_GUIDE_GEMINI_MODEL", "gemini-2.5-flash").strip()
    models = [primary]
    for alt in ("gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"):
        if alt not in models:
            models.append(alt)
    system = (
        f"You translate Facebook posts for the EU-Adopt pet adoption platform into {lang_name}. "
        "Rules: preserve meaning and tone; keep ALL URLs and links exactly unchanged; "
        "do not invent facts, ages, places, or medical claims; keep emoji; "
        "return ONLY the translated post text, no commentary."
    )
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": text}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048},
    }
    for model in models:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            f"?key={api_key}"
        )
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            parts = (
                ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
            )
            out = "".join((p.get("text") or "") for p in parts).strip()
            if out:
                return out
        except Exception:
            continue
    return None


def _graph_request(
    *,
    page_id: str,
    access_token: str,
    path: str,
    method: str = "POST",
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    version = facebook_graph_version()
    base = f"https://graph.facebook.com/{version}/{page_id}/{path.lstrip('/')}"
    params = dict(params or {})
    params["access_token"] = access_token
    if method.upper() == "GET":
        url = base + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, method="GET")
        body_data = None
    else:
        url = base
        body_data = urllib.parse.urlencode(params).encode("utf-8")
        req = urllib.request.Request(url, data=body_data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(err_body) if err_body else {}
        except json.JSONDecodeError:
            parsed = {"error": {"message": err_body or str(e)}}
        msg = ""
        err = parsed.get("error") if isinstance(parsed, dict) else None
        if isinstance(err, dict):
            msg = (err.get("message") or "").strip()
        raise RuntimeError(msg or f"Facebook HTTP {e.code}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Facebook network: {e.reason}") from e


def post_to_facebook_page(
    *,
    message: str,
    link: str,
    image_url: str = "",
    market: str = "ro",
) -> FacebookPostResult:
    if not facebook_auto_post_enabled() and market == "ro":
        # RO rămâne gated de flag-ul global; piețele mirror pot posta dacă au creds
        # (apelate din mirror cu check separat).
        pass
    creds = market_creds(market)
    if not creds.configured:
        return FacebookPostResult(ok=False, error=f"Piața {market} neconfigurată", market=market)
    if market == "ro" and not facebook_auto_post_enabled():
        return FacebookPostResult(ok=False, error="Facebook auto-post dezactivat", market=market)
    try:
        if image_url:
            raw = _graph_request(
                page_id=creds.page_id,
                access_token=creds.access_token,
                path="photos",
                method="POST",
                params={
                    "url": image_url,
                    "caption": message[:2000],
                },
            )
            post_id = str(raw.get("post_id") or raw.get("id") or "").strip()
        else:
            payload = {"message": message[:2000]}
            if link:
                payload["link"] = link
            raw = _graph_request(
                page_id=creds.page_id,
                access_token=creds.access_token,
                path="feed",
                method="POST",
                params=payload,
            )
            post_id = str(raw.get("id") or "").strip()
        if not post_id:
            return FacebookPostResult(ok=False, error="Răspuns FB fără id postare", market=market)
        return FacebookPostResult(ok=True, facebook_post_id=post_id, market=market)
    except Exception as exc:
        logger.exception("facebook_page_post failed market=%s", market)
        return FacebookPostResult(ok=False, error=str(exc)[:500], market=market)


def ensure_deliveries(outbound, markets: list[str] | None = None) -> list[Any]:
    from home.models import FacebookOutboundDelivery

    markets = markets if markets is not None else configured_markets()
    created = []
    for m in markets:
        d, _ = FacebookOutboundDelivery.objects.get_or_create(
            outbound=outbound,
            market=m,
            defaults={"status": STATUS_PENDING},
        )
        created.append(d)
    return created


def refresh_outbound_aggregate(outbound) -> None:
    from home.models import FacebookOutboundDelivery

    statuses = list(outbound.deliveries.values_list("status", flat=True))
    if not statuses:
        outbound.status = STATUS_PENDING
    elif all(s == STATUS_POSTED for s in statuses):
        outbound.status = STATUS_POSTED
        ro = outbound.deliveries.filter(market="ro", status=STATUS_POSTED).first()
        if ro:
            outbound.facebook_post_id = ro.facebook_post_id or outbound.facebook_post_id
            outbound.posted_at = ro.posted_at or outbound.posted_at
            outbound.error = ""
    elif all(s == STATUS_SKIPPED for s in statuses):
        outbound.status = STATUS_SKIPPED
    elif any(s == STATUS_POSTED for s in statuses) and any(
        s in (STATUS_FAILED, STATUS_PENDING) for s in statuses
    ):
        outbound.status = STATUS_PARTIAL
    elif any(s == STATUS_PENDING for s in statuses):
        outbound.status = STATUS_PENDING
    else:
        outbound.status = STATUS_FAILED
        last_err = (
            outbound.deliveries.exclude(error="")
            .order_by("-updated_at")
            .values_list("error", flat=True)
            .first()
        )
        outbound.error = (last_err or "")[:500]
    outbound.save(update_fields=["status", "facebook_post_id", "posted_at", "error", "updated_at"])


def enqueue_animal(listing, *, schedule: bool = True) -> Any:
    if not listing or not getattr(listing, "pk", None):
        return None
    if not getattr(listing, "is_published", False):
        return None
    if not facebook_auto_post_enabled():
        return None
    from home.models import FacebookOutboundPost

    row, _ = FacebookOutboundPost.objects.get_or_create(
        kind=KIND_ANIMAL,
        object_id=int(listing.pk),
        defaults={"status": STATUS_PENDING},
    )
    ensure_deliveries(row)
    if schedule:
        _schedule_process_outbound(row.pk)
    return row


def enqueue_campanie(camp, *, schedule: bool = True) -> Any:
    if not camp or not getattr(camp, "pk", None):
        return None
    if not facebook_auto_post_enabled():
        return None
    from home.models import FacebookOutboundPost

    row, _ = FacebookOutboundPost.objects.get_or_create(
        kind=KIND_CAMPANIE,
        object_id=int(camp.pk),
        defaults={"status": STATUS_PENDING},
    )
    ensure_deliveries(row)
    if schedule:
        _schedule_process_outbound(row.pk)
    return row


def _schedule_process_outbound(outbound_pk: int) -> None:
    def _run():
        try:
            process_outbound_row(outbound_pk)
        except Exception:
            logger.exception("facebook outbound process source=%s", outbound_pk)

    transaction.on_commit(lambda: threading.Thread(target=_run, daemon=True).start())


def _schedule_process_delivery(delivery_pk: int) -> None:
    def _run():
        try:
            process_delivery(delivery_pk)
        except Exception:
            logger.exception("facebook delivery process id=%s", delivery_pk)

    transaction.on_commit(lambda: threading.Thread(target=_run, daemon=True).start())


def _message_for_outbound(outbound) -> tuple[str, str, str]:
    from home.models import AnimalListing, CampanieSterilizare, FacebookRoInboundPost

    if outbound.kind == KIND_ANIMAL:
        listing = AnimalListing.objects.filter(pk=outbound.object_id).first()
        if listing is None or not listing.is_published:
            raise ValueError("Animal lipsă sau nepublicat")
        return build_animal_message(listing)
    if outbound.kind == KIND_CAMPANIE:
        camp = CampanieSterilizare.objects.filter(pk=outbound.object_id).first()
        if camp is None:
            raise ValueError("Campanie lipsă")
        return build_campanie_message(camp)
    if outbound.kind == KIND_RO_MIRROR:
        inbound = FacebookRoInboundPost.objects.filter(pk=outbound.object_id).first()
        if inbound is None:
            raise ValueError("Inbound RO lipsă")
        msg = (inbound.message or "").strip()
        link = (inbound.permalink or "").strip()
        img = (inbound.picture_url or "").strip()
        return msg, link, img
    raise ValueError(f"Kind necunoscut: {outbound.kind}")


def process_delivery(delivery_pk: int) -> FacebookPostResult:
    from home.models import FacebookOutboundDelivery

    try:
        delivery = FacebookOutboundDelivery.objects.select_related("outbound").get(pk=delivery_pk)
    except FacebookOutboundDelivery.DoesNotExist:
        return FacebookPostResult(ok=False, error="missing delivery")

    if delivery.status == STATUS_POSTED:
        return FacebookPostResult(
            ok=True,
            facebook_post_id=delivery.facebook_post_id,
            market=delivery.market,
        )

    market = delivery.market
    creds = market_creds(market)
    if not creds.configured:
        delivery.status = STATUS_SKIPPED
        delivery.error = f"Piața {market} fără credențiale"
        delivery.save(update_fields=["status", "error", "updated_at"])
        refresh_outbound_aggregate(delivery.outbound)
        return FacebookPostResult(ok=False, error=delivery.error, market=market)

    if market == "ro" and not facebook_auto_post_enabled():
        return FacebookPostResult(ok=False, error="disabled", market=market)

    # Plafon zilnic per piață (RO păstrează comportamentul existent)
    if remaining_posts_today(market) <= 0:
        delivery.status = STATUS_PENDING
        delivery.error = "Plafon zilnic atins — așteaptă ziua următoare"
        delivery.save(update_fields=["status", "error", "updated_at"])
        return FacebookPostResult(ok=False, deferred=True, error=delivery.error, market=market)

    try:
        message_ro, link, image_url = _message_for_outbound(delivery.outbound)
    except ValueError as exc:
        delivery.status = STATUS_SKIPPED
        delivery.error = str(exc)[:500]
        delivery.save(update_fields=["status", "error", "updated_at"])
        refresh_outbound_aggregate(delivery.outbound)
        return FacebookPostResult(ok=False, error=delivery.error, market=market)

    lang = market_lang(market)
    message = (
        message_ro
        if lang == "ro"
        else translate_facebook_message(message_ro, target_lang=lang)
    )

    delivery.attempt_count = int(delivery.attempt_count or 0) + 1
    delivery.save(update_fields=["attempt_count", "updated_at"])

    # Pentru mirror/site pe piețe non-RO: permitem post chiar dacă flag-ul e doar pentru RO
    # (tokenurile DE/... vor activa piețele).
    result = post_to_facebook_page(
        message=message,
        link=link,
        image_url=image_url,
        market=market,
    )
    if result.ok:
        delivery.status = STATUS_POSTED
        delivery.facebook_post_id = result.facebook_post_id
        delivery.posted_at = timezone.now()
        delivery.error = ""
        delivery.save(
            update_fields=["status", "facebook_post_id", "posted_at", "error", "updated_at"]
        )
    else:
        delivery.status = STATUS_FAILED
        delivery.error = (result.error or "eroare")[:500]
        delivery.save(update_fields=["status", "error", "updated_at"])
    refresh_outbound_aggregate(delivery.outbound)
    return result


def process_outbound_row(row_pk: int) -> FacebookPostResult:
    """Compat: procesează toate delivery-urile pending/failed ale sursei (izolat pe piață)."""
    from home.models import FacebookOutboundDelivery, FacebookOutboundPost

    try:
        outbound = FacebookOutboundPost.objects.get(pk=row_pk)
    except FacebookOutboundPost.DoesNotExist:
        return FacebookPostResult(ok=False, error="missing row")

    ensure_deliveries(outbound)
    last = FacebookPostResult(ok=False, error="no deliveries")
    any_ok = False
    any_deferred = False
    for d in FacebookOutboundDelivery.objects.filter(
        outbound=outbound, status__in=(STATUS_PENDING, STATUS_FAILED)
    ).order_by("market"):
        if d.status == STATUS_FAILED:
            d.status = STATUS_PENDING
            d.save(update_fields=["status", "updated_at"])
        last = process_delivery(d.pk)
        if last.ok:
            any_ok = True
        if last.deferred:
            any_deferred = True
    if any_ok:
        return FacebookPostResult(ok=True, facebook_post_id=outbound.facebook_post_id)
    if any_deferred:
        return FacebookPostResult(ok=False, deferred=True, error=last.error)
    return last


def flush_pending(*, limit: int | None = None) -> dict[str, int]:
    """Procesează delivery-uri pending/failed; eșec pe o piață nu oprește celelalte."""
    from home.models import FacebookOutboundDelivery

    stats = {"posted": 0, "deferred": 0, "failed": 0, "skipped": 0}
    if not facebook_auto_post_enabled() and not configured_markets(for_mirror_targets=True):
        return stats

    qs = FacebookOutboundDelivery.objects.filter(
        status__in=(STATUS_PENDING, STATUS_FAILED)
    ).order_by("created_at", "pk")
    if limit:
        qs = qs[: int(limit)]

    for delivery in qs:
        if delivery.status == STATUS_FAILED:
            delivery.status = STATUS_PENDING
            delivery.save(update_fields=["status", "updated_at"])
        # skip RO dacă auto-post off
        if delivery.market == "ro" and not facebook_auto_post_enabled():
            continue
        if delivery.market != "ro" and not market_creds(delivery.market).configured:
            continue
        result = process_delivery(delivery.pk)
        if result.ok:
            stats["posted"] += 1
        elif result.deferred:
            stats["deferred"] += 1
        elif delivery.status == STATUS_SKIPPED or (result.error or "").startswith(
            ("Animal", "Campanie", "Inbound")
        ):
            stats["skipped"] += 1
        else:
            stats["failed"] += 1
    return stats


# Alias vechi pentru importuri
def facebook_page_id() -> str:
    return market_creds("ro").page_id


def facebook_page_token() -> str:
    return market_creds("ro").access_token
