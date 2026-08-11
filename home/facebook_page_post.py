"""
Postări automate pe pagina Facebook EU-Adopt (Graph API).

Animale noi publicate + campanii sterilizare noi → coadă → post imediat
(dacă sub plafonul zilnic), altfel așteaptă cronul.
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

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)

RO_TZ = ZoneInfo("Europe/Bucharest")

KIND_ANIMAL = "animal"
KIND_CAMPANIE = "campanie"

STATUS_PENDING = "pending"
STATUS_POSTED = "posted"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"


@dataclass
class FacebookPostResult:
    ok: bool
    facebook_post_id: str = ""
    error: str = ""
    deferred: bool = False  # sub plafon? False = așteaptă altă zi


def facebook_auto_post_enabled() -> bool:
    if not bool(getattr(settings, "FACEBOOK_AUTO_POST_ENABLED", False)):
        return False
    token = (getattr(settings, "FACEBOOK_PAGE_ACCESS_TOKEN", "") or "").strip()
    page_id = (getattr(settings, "FACEBOOK_PAGE_ID", "") or "").strip()
    return bool(token and page_id)


def facebook_max_posts_per_day() -> int:
    return max(1, int(getattr(settings, "FACEBOOK_MAX_POSTS_PER_DAY", 10) or 10))


def facebook_page_id() -> str:
    return (getattr(settings, "FACEBOOK_PAGE_ID", "") or "").strip()


def facebook_page_token() -> str:
    return (getattr(settings, "FACEBOOK_PAGE_ACCESS_TOKEN", "") or "").strip()


def facebook_graph_version() -> str:
    v = (getattr(settings, "FACEBOOK_GRAPH_API_VERSION", "") or "v21.0").strip()
    return v if v.startswith("v") else f"v{v}"


def site_base_url() -> str:
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


def posts_today_count() -> int:
    from home.models import FacebookOutboundPost

    now_ro = timezone.now().astimezone(RO_TZ)
    start = datetime(now_ro.year, now_ro.month, now_ro.day, tzinfo=RO_TZ)
    end = start + timedelta(days=1)
    return FacebookOutboundPost.objects.filter(
        status=STATUS_POSTED,
        posted_at__gte=start,
        posted_at__lt=end,
    ).count()


def remaining_posts_today() -> int:
    return max(0, facebook_max_posts_per_day() - posts_today_count())


def _species_ro(listing) -> str:
    sp = (getattr(listing, "species", "") or "").strip().lower()
    if sp == "dog":
        return "Câine"
    if sp == "cat":
        return "Pisică"
    return (getattr(listing, "species", "") or "Animal").strip() or "Animal"


def build_animal_message(listing) -> tuple[str, str, str]:
    """message, link, image_url"""
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


def _graph_post(path: str, params: dict[str, str]) -> dict[str, Any]:
    version = facebook_graph_version()
    page_id = facebook_page_id()
    url = f"https://graph.facebook.com/{version}/{page_id}/{path.lstrip('/')}"
    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
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


def post_to_facebook_page(*, message: str, link: str, image_url: str = "") -> FacebookPostResult:
    if not facebook_auto_post_enabled():
        return FacebookPostResult(ok=False, error="Facebook auto-post dezactivat / fără token")
    token = facebook_page_token()
    try:
        if image_url:
            raw = _graph_post(
                "photos",
                {
                    "url": image_url,
                    "caption": message[:2000],
                    "access_token": token,
                },
            )
            post_id = str(raw.get("post_id") or raw.get("id") or "").strip()
        else:
            payload = {
                "message": message[:2000],
                "access_token": token,
            }
            if link:
                payload["link"] = link
            raw = _graph_post("feed", payload)
            post_id = str(raw.get("id") or "").strip()
        if not post_id:
            return FacebookPostResult(ok=False, error="Răspuns FB fără id postare")
        return FacebookPostResult(ok=True, facebook_post_id=post_id)
    except Exception as exc:
        logger.exception("facebook_page_post failed")
        return FacebookPostResult(ok=False, error=str(exc)[:500])


def enqueue_animal(listing, *, schedule: bool = True) -> Any:
    """Creează rând coadă pentru animal publicat. Returnează FacebookOutboundPost sau None."""
    if not listing or not getattr(listing, "pk", None):
        return None
    if not getattr(listing, "is_published", False):
        return None
    if not facebook_auto_post_enabled():
        return None
    from home.models import FacebookOutboundPost

    row, created = FacebookOutboundPost.objects.get_or_create(
        kind=KIND_ANIMAL,
        object_id=int(listing.pk),
        defaults={"status": STATUS_PENDING},
    )
    if row.status == STATUS_POSTED:
        return row
    if row.status != STATUS_PENDING:
        row.status = STATUS_PENDING
        row.error = ""
        row.save(update_fields=["status", "error", "updated_at"])
    if schedule:
        _schedule_process(row.pk)
    return row


def enqueue_campanie(camp, *, schedule: bool = True) -> Any:
    if not camp or not getattr(camp, "pk", None):
        return None
    if not facebook_auto_post_enabled():
        return None
    from home.models import FacebookOutboundPost

    row, created = FacebookOutboundPost.objects.get_or_create(
        kind=KIND_CAMPANIE,
        object_id=int(camp.pk),
        defaults={"status": STATUS_PENDING},
    )
    if row.status == STATUS_POSTED:
        return row
    if row.status != STATUS_PENDING:
        row.status = STATUS_PENDING
        row.error = ""
        row.save(update_fields=["status", "error", "updated_at"])
    if schedule:
        _schedule_process(row.pk)
    return row


def _schedule_process(row_pk: int) -> None:
    def _run():
        try:
            process_outbound_row(row_pk)
        except Exception:
            logger.exception("facebook outbound process row=%s", row_pk)

    transaction.on_commit(lambda: threading.Thread(target=_run, daemon=True).start())


def process_outbound_row(row_pk: int) -> FacebookPostResult:
    from home.models import AnimalListing, CampanieSterilizare, FacebookOutboundPost

    try:
        row = FacebookOutboundPost.objects.get(pk=row_pk)
    except FacebookOutboundPost.DoesNotExist:
        return FacebookPostResult(ok=False, error="missing row")

    if row.status == STATUS_POSTED:
        return FacebookPostResult(ok=True, facebook_post_id=row.facebook_post_id)

    if not facebook_auto_post_enabled():
        return FacebookPostResult(ok=False, error="disabled")

    if remaining_posts_today() <= 0:
        row.status = STATUS_PENDING
        row.error = "Plafon zilnic atins — așteaptă ziua următoare"
        row.save(update_fields=["status", "error", "updated_at"])
        return FacebookPostResult(ok=False, deferred=True, error=row.error)

    message = link = image_url = ""
    if row.kind == KIND_ANIMAL:
        listing = AnimalListing.objects.filter(pk=row.object_id).first()
        if listing is None or not listing.is_published:
            row.status = STATUS_SKIPPED
            row.error = "Animal lipsă sau nepublicat"
            row.save(update_fields=["status", "error", "updated_at"])
            return FacebookPostResult(ok=False, error=row.error)
        message, link, image_url = build_animal_message(listing)
    elif row.kind == KIND_CAMPANIE:
        camp = CampanieSterilizare.objects.filter(pk=row.object_id).first()
        if camp is None:
            row.status = STATUS_SKIPPED
            row.error = "Campanie lipsă"
            row.save(update_fields=["status", "error", "updated_at"])
            return FacebookPostResult(ok=False, error=row.error)
        message, link, image_url = build_campanie_message(camp)
    else:
        row.status = STATUS_SKIPPED
        row.error = f"Kind necunoscut: {row.kind}"
        row.save(update_fields=["status", "error", "updated_at"])
        return FacebookPostResult(ok=False, error=row.error)

    result = post_to_facebook_page(message=message, link=link, image_url=image_url)
    if result.ok:
        row.status = STATUS_POSTED
        row.facebook_post_id = result.facebook_post_id
        row.posted_at = timezone.now()
        row.error = ""
        row.save(update_fields=["status", "facebook_post_id", "posted_at", "error", "updated_at"])
    else:
        row.status = STATUS_FAILED
        row.error = (result.error or "eroare")[:500]
        row.save(update_fields=["status", "error", "updated_at"])
    return result


def flush_pending(*, limit: int | None = None) -> dict[str, int]:
    """Procesează coada pending (și failed pentru retry ușor), respectând plafonul zilnic."""
    from home.models import FacebookOutboundPost

    stats = {"posted": 0, "deferred": 0, "failed": 0, "skipped": 0}
    if not facebook_auto_post_enabled():
        return stats

    cap = remaining_posts_today()
    if cap <= 0:
        stats["deferred"] = FacebookOutboundPost.objects.filter(status=STATUS_PENDING).count()
        return stats

    max_n = limit if limit is not None else cap
    max_n = min(max_n, cap)
    qs = FacebookOutboundPost.objects.filter(status__in=(STATUS_PENDING, STATUS_FAILED)).order_by(
        "created_at", "pk"
    )[:max_n]

    for row in qs:
        if remaining_posts_today() <= 0:
            stats["deferred"] += 1
            continue
        # failed → retry ca pending
        if row.status == STATUS_FAILED:
            row.status = STATUS_PENDING
            row.save(update_fields=["status", "updated_at"])
        result = process_outbound_row(row.pk)
        if result.ok:
            stats["posted"] += 1
        elif result.deferred:
            stats["deferred"] += 1
        elif (result.error or "").startswith("Animal") or (result.error or "").startswith("Campanie"):
            stats["skipped"] += 1
        else:
            stats["failed"] += 1
    return stats
