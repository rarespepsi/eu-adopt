"""
Auto-publicare din CampanieDiscoverHit → CampanieSterilizare + enqueue Facebook.

Reguli stricte (evită dubluri / zgomot / articole greșite de județ):
- URL non-junk, cu „steriliz” în titlu/snippet
- dată extrasă ≥ min_date și încă vizibilă pe hartă (date_end+3 ≥ today)
- og:image descărcabil (afiș obligatoriu pe model)
- dedupe pe link normalizat + judet+localitate+date_start+date_end
"""
from __future__ import annotations

import logging
import re
import tempfile
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from django.contrib.auth import get_user_model
from django.core.files import File
from django.db import transaction
from django.utils import timezone

from home.campanii_discover import (
    CampanieCandidate,
    fetch_og_image,
    is_junk_campaign_url,
    parse_campaign_dates,
)
from home.campanii_ro import resolve_campanii_judet
from home.models import CampanieDiscoverHit, CampanieSterilizare
from home.ro_location import fold_key
from home.shelter_directory import normalize_external_link

logger = logging.getLogger(__name__)
User = get_user_model()

_DEFAULT_MIN = date(2026, 8, 1)
_UA = {"User-Agent": "Mozilla/5.0 (compatible; EU-Adopt-campanii/1.0)"}

_LOC_PATTERNS = (
    re.compile(
        r"\b(?:la|în|in|din|pe raza(?:\s+municipiului)?|municipiului|ora[sș]ului|comunei)\s+"
        r"([A-ZĂÂÎȘȚ][\wĂÂÎȘȚăâîșț\- ]{2,40})",
        re.I,
    ),
    re.compile(r"\b([A-ZĂÂÎȘȚ][\wĂÂÎȘȚăâîșț\- ]{2,40})\s*[:\-–]\s*Campanie", re.I),
)


def publisher_user():
    """Doar superuser-ul site-ului — niciodată useri Cont (ex. IoanaSerbacov)."""
    qs = User.objects.filter(is_superuser=True).order_by("id")
    n = qs.count()
    if n == 0:
        logger.error("no superuser for campanii discover publish")
        return None
    if n > 1:
        logger.warning("multiple superusers (%s) — using lowest id", n)
    return qs.first()


def normalize_hit_url(url: str) -> str:
    raw = (url or "").strip()
    n = normalize_external_link(raw) or raw
    return n.split("#")[0].rstrip("/")[:500]


def guess_localitate(title: str, snippet: str, judet_name: str, main_city: str = "") -> str:
    blob = f"{title} {snippet}"
    for pat in _LOC_PATTERNS:
        m = pat.search(blob)
        if not m:
            continue
        loc = re.sub(r"\s+", " ", m.group(1)).strip(" .,;:")
        if len(loc) < 3:
            continue
        low = fold_key(loc)
        if low in ("romania", "judet", "județul", "campanie", "sterilizare"):
            continue
        if fold_key(judet_name) in low and len(low) <= len(fold_key(judet_name)) + 2:
            continue
        return loc[:120]
    if main_city:
        return main_city[:120]
    return (judet_name or "—")[:120]


def classify_candidate(
    cand: CampanieCandidate,
    *,
    min_date: date | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Returnează status + câmpuri derivate pentru upsert."""
    today = today or date.today()
    min_date = min_date or _DEFAULT_MIN
    url = (cand.url or "").strip()
    title = cand.title or ""
    snippet = cand.snippet or ""
    blob = f"{title} {snippet}"

    if is_junk_campaign_url(url):
        return {"status": CampanieDiscoverHit.STATUS_SKIPPED, "skip_reason": "junk_url"}

    if "steriliz" not in fold_key(blob):
        return {"status": CampanieDiscoverHit.STATUS_SKIPPED, "skip_reason": "no_steriliz_keyword"}

    # Facebook fără og:image util → nu auto-publicăm
    if "facebook.com" in url.lower() or "fb.me" in url.lower():
        return {
            "status": CampanieDiscoverHit.STATUS_SKIPPED,
            "skip_reason": "facebook_no_afis_auto",
        }

    dates = parse_campaign_dates(f"{cand.guessed_dates} {blob} {url}")
    if not dates:
        return {"status": CampanieDiscoverHit.STATUS_SKIPPED, "skip_reason": "no_date"}

    newest = max(dates)
    oldest_relevant = min(d for d in dates if d >= min_date) if any(d >= min_date for d in dates) else None
    if oldest_relevant is None:
        return {
            "status": CampanieDiscoverHit.STATUS_QUARANTINE,
            "skip_reason": f"before_min_date:{newest.isoformat()}",
            "date_start": newest,
            "date_end": newest,
        }

    # eveniment pe o zi = newest dacă e singura dată recentă; altfel span
    recent = sorted(d for d in dates if d >= min_date)
    d0 = recent[0]
    d1 = recent[-1]
    # ongoing hints
    if re.search(r"limita fondurilor|încep[aă]nd cu|continua|continuă", blob, re.I):
        d1 = max(d1, date(today.year, 12, 31))

    if d1 + timedelta(days=3) < today:
        return {
            "status": CampanieDiscoverHit.STATUS_QUARANTINE,
            "skip_reason": f"expired:{d1.isoformat()}",
            "date_start": d0,
            "date_end": d1,
        }

    judet = resolve_campanii_judet(cand.judet_slug or cand.judet)
    main = ""
    if judet and judet.main_cities:
        main = judet.main_cities[0]
    loc = guess_localitate(title, snippet, cand.judet, main)

    return {
        "status": CampanieDiscoverHit.STATUS_NEW,
        "skip_reason": "",
        "date_start": d0,
        "date_end": d1,
        "localitate_guess": loc,
    }


def upsert_candidates(
    rows: list[CampanieCandidate],
    *,
    min_date: date | None = None,
    fetch_images: bool = True,
) -> dict[str, int]:
    stats = {"created": 0, "updated": 0, "skipped": 0}
    today = date.today()
    for cand in rows:
        url_norm = normalize_hit_url(cand.url)
        if not url_norm:
            stats["skipped"] += 1
            continue
        meta = classify_candidate(cand, min_date=min_date, today=today)
        image_url = (cand.image_url or "").strip()
        if fetch_images and not image_url and meta.get("status") == CampanieDiscoverHit.STATUS_NEW:
            image_url = fetch_og_image(cand.url)
        fields = {
            "judet": cand.judet[:64],
            "judet_slug": cand.judet_slug[:80],
            "judet_code": (cand.judet_code or "")[:8],
            "title": (cand.title or "")[:300],
            "snippet": (cand.snippet or "")[:500],
            "image_url": image_url[:500],
            "guessed_dates": (cand.guessed_dates or "")[:120],
            "source": (cand.source or "")[:16],
            "query": (cand.query or "")[:240],
            "localitate_guess": (meta.get("localitate_guess") or "")[:120],
            "date_start": meta.get("date_start"),
            "date_end": meta.get("date_end"),
        }
        hit = CampanieDiscoverHit.objects.filter(url_norm=url_norm).first()
        if hit is None:
            hit = CampanieDiscoverHit.objects.filter(url=cand.url[:500]).first()
        if hit is None:
            hit = CampanieDiscoverHit.objects.create(
                url=cand.url[:500],
                url_norm=url_norm,
                status=meta["status"],
                skip_reason=(meta.get("skip_reason") or "")[:240],
                **fields,
            )
            stats["created"] += 1
            continue

        for k, v in fields.items():
            setattr(hit, k, v)
        if hit.status != CampanieDiscoverHit.STATUS_PUBLISHED:
            hit.status = meta["status"]
            hit.skip_reason = (meta.get("skip_reason") or "")[:240]
        if not hit.url_norm:
            hit.url_norm = url_norm
        hit.save()
        stats["updated"] += 1
    return stats


def _download_image(url: str) -> Path | None:
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers=_UA)
        data = urllib.request.urlopen(req, timeout=25).read()
        if len(data) < 800:
            return None
        suffix = ".jpg"
        low = url.lower()
        if ".png" in low:
            suffix = ".png"
        elif ".webp" in low:
            suffix = ".webp"
        fd, path = tempfile.mkstemp(prefix="camp_disc_", suffix=suffix)
        import os

        os.close(fd)
        p = Path(path)
        p.write_bytes(data)
        return p
    except Exception:
        logger.debug("image download failed %s", url, exc_info=True)
        return None


def _already_on_map(link: str, judet_slug: str, localitate: str, d0: date, d1: date) -> CampanieSterilizare | None:
    """Dedupe față de ORICE campanie pe hartă (inclusiv useri) — nu republicăm."""
    link_n = normalize_hit_url(link)
    if link_n:
        hit = CampanieSterilizare.objects.filter(link=link_n).first()
        if hit:
            return hit
        base = link_n.split("?")[0]
        if len(base) > 20:
            hit = CampanieSterilizare.objects.filter(link__startswith=base[:180]).first()
            if hit:
                return hit
    return CampanieSterilizare.objects.filter(
        judet_slug=judet_slug,
        localitate=localitate,
        date_start=d0,
        date_end=d1,
    ).first()


def reassign_discover_owned_to_superuser(*, pks: list[int] | None = None) -> int:
    """Mută campaniile create greșit pe user → pe unicul superuser. Nu atinge alte conturi."""
    owner = publisher_user()
    if not owner:
        return 0
    qs = CampanieSterilizare.objects.filter(pk__in=pks) if pks else CampanieSterilizare.objects.none()
    n = 0
    for obj in qs:
        if obj.user_id == owner.id:
            continue
        # doar cele din fluxul discover (pk-uri explicite) — nu mutăm Serbacov / ONG
        obj.user = owner
        obj.save(update_fields=["user", "updated_at"])
        n += 1
    return n


def publish_new_hits(
    *,
    limit: int = 8,
    dry_run: bool = False,
) -> dict[str, int]:
    """Publică hit-uri status=new cu afiș pe hartă + enqueue FB."""
    stats = {"published": 0, "skipped": 0, "errors": 0, "dry": 0}
    user = publisher_user()
    if not user:
        logger.error("no publisher user for campanii discover")
        stats["errors"] += 1
        return stats

    qs = (
        CampanieDiscoverHit.objects.filter(status=CampanieDiscoverHit.STATUS_NEW)
        .exclude(image_url="")
        .exclude(date_start__isnull=True)
        .exclude(date_end__isnull=True)
        .order_by("date_start", "id")[: max(1, int(limit))]
    )

    for hit in qs:
        if not hit.image_url:
            hit.status = CampanieDiscoverHit.STATUS_SKIPPED
            hit.skip_reason = "no_image"
            hit.save(update_fields=["status", "skip_reason", "last_seen_at"])
            stats["skipped"] += 1
            continue
        if not hit.date_start or not hit.date_end:
            hit.status = CampanieDiscoverHit.STATUS_SKIPPED
            hit.skip_reason = "no_dates"
            hit.save(update_fields=["status", "skip_reason", "last_seen_at"])
            stats["skipped"] += 1
            continue
        if hit.date_end + timedelta(days=3) < date.today():
            hit.status = CampanieDiscoverHit.STATUS_QUARANTINE
            hit.skip_reason = "expired_at_publish"
            hit.save(update_fields=["status", "skip_reason", "last_seen_at"])
            stats["skipped"] += 1
            continue

        judet = resolve_campanii_judet(hit.judet_slug or hit.judet)
        if not judet:
            hit.status = CampanieDiscoverHit.STATUS_SKIPPED
            hit.skip_reason = "bad_judet"
            hit.save(update_fields=["status", "skip_reason", "last_seen_at"])
            stats["skipped"] += 1
            continue

        localitate = (hit.localitate_guess or judet.name).strip()[:120]
        link_n = normalize_hit_url(hit.url)
        exists = _already_on_map(link_n, judet.slug, localitate, hit.date_start, hit.date_end)
        if exists:
            hit.status = CampanieDiscoverHit.STATUS_PUBLISHED
            hit.campanie = exists
            hit.skip_reason = f"already_on_map:{exists.pk}"
            hit.published_at = timezone.now()
            hit.save(
                update_fields=[
                    "status",
                    "campanie",
                    "skip_reason",
                    "published_at",
                    "last_seen_at",
                ]
            )
            stats["skipped"] += 1
            continue

        if dry_run:
            stats["dry"] += 1
            continue

        photo_path = _download_image(hit.image_url)
        if not photo_path:
            # retry fetch og
            fresh = fetch_og_image(hit.url)
            if fresh:
                hit.image_url = fresh[:500]
                hit.save(update_fields=["image_url", "last_seen_at"])
                photo_path = _download_image(fresh)
        if not photo_path:
            hit.status = CampanieDiscoverHit.STATUS_SKIPPED
            hit.skip_reason = "image_download_failed"
            hit.save(update_fields=["status", "skip_reason", "last_seen_at"])
            stats["skipped"] += 1
            continue

        try:
            with transaction.atomic():
                obj = CampanieSterilizare(
                    user=user,
                    judet=judet.name,
                    judet_slug=judet.slug,
                    localitate=localitate,
                    species_dogs=True,
                    species_cats=True,
                    date_start=hit.date_start,
                    date_end=hit.date_end,
                    link=link_n,
                )
                fname = f"disc-{judet.slug}-{hit.date_start.isoformat()}-{hit.pk}.jpg"
                with photo_path.open("rb") as fh:
                    obj.photo.save(fname, File(fh), save=True)
                try:
                    from home.facebook_page_post import enqueue_campanie

                    enqueue_campanie(obj)
                except Exception:
                    logger.exception("enqueue_campanie failed for hit %s", hit.pk)
                hit.status = CampanieDiscoverHit.STATUS_PUBLISHED
                hit.campanie = obj
                hit.published_at = timezone.now()
                hit.skip_reason = ""
                hit.save(
                    update_fields=[
                        "status",
                        "campanie",
                        "published_at",
                        "skip_reason",
                        "last_seen_at",
                    ]
                )
                stats["published"] += 1
        except Exception:
            logger.exception("publish failed hit %s", hit.pk)
            stats["errors"] += 1
        finally:
            try:
                photo_path.unlink(missing_ok=True)
            except Exception:
                pass

    return stats


def run_discover_refresh(
    *,
    all_judete: bool = True,
    empty_only: bool = False,
    judet_slugs: list[str] | None = None,
    limit_judete: int = 0,
    max_per_query: int = 6,
    sleep_s: float = 1.0,
    include_smeura: bool = True,
    auto_publish: bool = False,
    publish_limit: int = 8,
    dry_run: bool = False,
    min_date: date | None = None,
    out_csv: Path | None = None,
) -> dict[str, Any]:
    from home.campanii_discover import (
        discover_all_judete,
        discover_empty_judete,
        write_candidates_csv,
    )

    if judet_slugs:
        rows = discover_empty_judete(
            judet_slugs=judet_slugs,
            limit_judete=limit_judete,
            max_per_query=max_per_query,
            sleep_s=sleep_s,
            include_smeura=include_smeura,
            fetch_images=False,
        )
    elif empty_only:
        rows = discover_empty_judete(
            limit_judete=limit_judete,
            max_per_query=max_per_query,
            sleep_s=sleep_s,
            include_smeura=include_smeura,
            fetch_images=False,
        )
    else:
        rows = discover_all_judete(
            limit_judete=limit_judete,
            max_per_query=max_per_query,
            sleep_s=sleep_s,
            include_smeura=include_smeura,
            fetch_images=False,
        )

    upsert = upsert_candidates(rows, min_date=min_date, fetch_images=True)
    pub = {"published": 0, "skipped": 0, "errors": 0, "dry": 0}
    if auto_publish:
        pub = publish_new_hits(limit=publish_limit, dry_run=dry_run)

    csv_path = ""
    if out_csv is not None:
        write_candidates_csv(Path(out_csv), rows)
        csv_path = str(out_csv)

    return {
        "candidates": len(rows),
        "upsert": upsert,
        "publish": pub,
        "csv": csv_path,
    }
